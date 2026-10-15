"""
Endpoints HTTP de Integração FastAPI para o Motor Cognitivo AURA.
(Server-Sent Events / SSE, Invocação Direta de Intenções e Diagnóstico de Postos)

Conectores:
1. POST /api/v1/aura/chat: Suporte a streaming SSE em tempo real ou resposta síncrona JSON
2. POST /api/v1/aura/execute-intent: Invocação direta das 12 ferramentas analíticas (Run-Out, LMC, Turno, RCA...)
3. GET  /api/v1/aura/stations: Lista filiais homologadas e status de conexão ERP/pgvector
4. GET  /api/v1/aura/health: Health check de prontidão operacional
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config.settings import AURA_API_KEY, get_cors_origins
from core.aura_engine import (
    AuraEngine,
    StationStatus,
)
from core.automation_config import (
    AutomationSettings,
    get_automation_settings,
    update_automation_settings,
)
from core.config import (
    get_feature_flags,
    is_genui_enabled,
    resolve_genui_flag,
    update_feature_flags,
)
from core.logger import current_client_ip, current_request_id, logger
from core.schemas.genui import (
    ActionAuditLogRecord,
    ActionExecuteRequest,
    ActionVoucher,
    generate_action_voucher_signature,
)
from core.schemas.idempotency import generate_uuid4
from core.webhooks import (
    AlertaTanquePayload,
    TurnoResumoPayload,
    notify_alerta_tanque,
    notify_fechamento_turno,
)

# Router oficial da AURA
router = APIRouter(prefix="/api/v1/aura", tags=["AURA Core Engine"])

# Instância Singleton do Motor (pode ser injetada externamente)
_engine_instance: AuraEngine | None = None


def get_aura_engine() -> AuraEngine:
    """Dependency Provider para obter a instância ativa do motor AURA."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AuraEngine()
    return _engine_instance


def set_aura_engine(engine: AuraEngine):
    """Permite sobrescrever ou injetar uma instância customizada do motor."""
    global _engine_instance
    _engine_instance = engine


def verify_admin_auth(request: Request = None) -> bool:
    """
    Valida autenticacao por API Key (header X-API-Key) ou Bearer Token (Authorization)
    para endpoints administrativos e operacoes transacionais (P1-4).
    """
    configured_key = os.getenv("AURA_API_KEY") or AURA_API_KEY
    enforce_auth = os.getenv("AURA_ENFORCE_ADMIN_AUTH", "0").lower() in ("1", "true", "yes")

    provided_key = None
    if request is not None:
        header_key = request.headers.get("x-api-key")
        if header_key:
            provided_key = header_key.strip()
        else:
            auth_header = request.headers.get("authorization", "")
            if auth_header.lower().startswith("bearer "):
                provided_key = auth_header[7:].strip()

    if provided_key is not None:
        if provided_key == configured_key:
            return True
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticacao invalida: X-API-Key ou Bearer Token incorreto.",
        )

    if enforce_auth and configured_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticacao necessaria: cabecalho X-API-Key ou Bearer Token ausente.",
        )

    return True


# =============================================================================
# PAYLOADS DE REQUISIÇÃO
# =============================================================================

class ChatRequest(BaseModel):
    """Contrato de entrada para conversação com a AURA."""
    query: str = Field(..., min_length=1, description="Pergunta ou instrução do usuário")
    session_id: str | None = Field(default=None, description="Identificador da sessão para continuidade")
    stream: bool = Field(default=True, description="Se true, retorna Server-Sent Events (SSE)")
    tenant_id: str | None = Field(default=None, description="Identificador do cliente/rede")
    filial_id: str | None = Field(default=None, description="Identificador da filial do posto")
    context: dict[str, Any] | None = Field(default=None, description="Contexto extra opcional injetado pelo chamador")
    genui: bool | None = Field(default=None, description="Feature flag GenUI override (True=ativa, False=desativa)")
    enable_genui: bool | None = Field(default=None, description="Alias para genui")


class TelemetryReportRequest(BaseModel):
    """Payload para envio de metricas de UX e hidratacao pelo frontend (F9-02)."""
    metric_type: str | None = Field(default=None, description="Tipo da metrica (ex: hydration, rollback, ttft)")
    hydration_ms: float | None = Field(default=None, description="Tempo de hidratacao em milissegundos")
    ttft_ms: float | None = Field(default=None, description="TTFT percebido no cliente")
    action_status: str | None = Field(default=None, description="Status da acao: requested, approved, rolled_back")
    is_rollback: bool | None = Field(default=False, description="Indica se a acao sofreu rollback")
    is_security_block: bool | None = Field(default=False, description="Indica se houve bloqueio de seguranca")
    session_id: str | None = None
    tool_call_id: str | None = None
    action_id: str | None = None
    reason: str | None = None
    details: dict[str, Any] | None = None


class FeatureFlagsUpdateRequest(BaseModel):
    """Payload para comutacao a quente de feature flags no runtime (F9-03)."""
    ENABLE_GENUI: bool | None = None
    enable_genui: bool | None = None
    flags: dict[str, Any] | None = None


class ExecuteIntentRequest(BaseModel):
    """Contrato de invocação direta de ferramenta analítica sem prompt de LLM."""
    tool_name: str = Field(..., description="Nome da ferramenta (ex: previsao_tanques, lmc_anp, auditoria_turno)")
    params: dict[str, Any] | None = Field(default_factory=dict, description="Parâmetros específicos da ferramenta")
    tenant_id: str | None = Field(default=None, description="Identificador do cliente")
    filial_id: str | None = Field(default=None, description="Identificador da filial")


# =============================================================================
# ROTAS HTTP
# =============================================================================

@router.post("/chat", summary="Chat Cognitivo com a AURA (SSE ou JSON)")
@router.post("/chat/stream", summary="Chat Cognitivo com a AURA em Streaming SSE")
async def chat_endpoint(
    req: ChatRequest,
    request: Request = None,
    genui: str | None = Query(None, description="Feature flag GenUI override (1=ativa, 0=desativa)"),
    engine: AuraEngine = Depends(get_aura_engine),
):
    """
    Envia pergunta para a AURA.
    - Se stream=true (padrao): Transmite resposta via Server-Sent Events (SSE).
    - Se stream=false: Retorna modelo estruturado consolidado AuraResponse.
    - Suporta override dinamico de Feature Flag GenUI via query param ?genui=1/0, header X-GenUI-Enabled e body.
    """
    header_genui = request.headers.get("x-genui-enabled") if request is not None else None
    body_genui = req.genui if req.genui is not None else req.enable_genui
    effective_genui = resolve_genui_flag(
        query_param=genui,
        header_val=header_genui,
        body_val=body_genui,
    )

    should_stream = req.stream or (request is not None and request.url.path.endswith("/stream"))

    if should_stream:
        async def event_generator():
            async for chunk in engine.ask_stream(
                query=req.query,
                context=req.context,
                session_id=req.session_id,
                tenant_id=req.tenant_id,
                filial_id=req.filial_id,
                enable_genui=effective_genui,
            ):
                yield chunk.to_sse()

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-GenUI-Enabled": "1" if effective_genui else "0",
            },
        )
    else:
        response = await engine.ask(
            query=req.query,
            context=req.context,
            session_id=req.session_id,
            tenant_id=req.tenant_id,
            filial_id=req.filial_id,
            enable_genui=effective_genui,
        )
        return response


@router.get("/chat/stream", summary="Chat Cognitivo com a AURA em Streaming SSE via GET (EventSource)")
async def chat_stream_get_endpoint(
    request: Request,
    query: str = Query(..., min_length=1, description="Pergunta ou instrucao do usuario"),
    session_id: str | None = Query(None, description="Identificador da sessao"),
    tenant_id: str | None = Query(None, description="Identificador do cliente"),
    filial_id: str | None = Query(None, description="Identificador da filial"),
    genui: str | None = Query(None, description="Feature flag GenUI override (1=ativa, 0=desativa)"),
    engine: AuraEngine = Depends(get_aura_engine),
):
    """
    Streaming SSE via requisicao GET para total compatibilidade com clientes EventSource padrao do navegador.
    """
    header_genui = request.headers.get("x-genui-enabled") if request is not None else None
    effective_genui = resolve_genui_flag(
        query_param=genui,
        header_val=header_genui,
        body_val=None,
    )

    async def event_generator():
        async for chunk in engine.ask_stream(
            query=query,
            session_id=session_id,
            tenant_id=tenant_id,
            filial_id=filial_id,
            enable_genui=effective_genui,
        ):
            yield chunk.to_sse()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-GenUI-Enabled": "1" if effective_genui else "0",
        },
    )


@router.post("/execute-intent", summary="Execução Direta de Ferramenta Analítica")
async def execute_intent_endpoint(
    req: ExecuteIntentRequest,
    engine: AuraEngine = Depends(get_aura_engine),
):
    """
    Invoca diretamente uma das 12 ferramentas analíticas (ex: Run-Out, LMC, Pista, Conciliação, Causa-Raiz RCA),
    sem latência de síntese de LLM. Retorna os dados analíticos estruturados em JSON.
    """
    result = await engine.execute_tool(
        tool_name=req.tool_name,
        params=req.params,
    )
    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result,
        )
    return result


def _dispatch_business_action(
    action_name: str,
    action_type: str,
    payload: dict[str, Any],
    operator_id: str,
) -> dict[str, Any]:
    """
    Executa as rotinas de negocio autorizadas para a operacao do posto e conveniencia.
    Trata pedidos de combustivel, estancamento de quebra, ajuste de margem e conciliacao.
    """
    act = (action_name or "").lower().strip()
    operacao = str(payload.get("operacao") or "").lower().strip()
    act_combined = f"{act} {operacao}".strip()

    # Repasse de custo no preco (Simulacao Preditiva)
    if any(k in act_combined for k in ["repassar_custo", "repassar"]):
        return {
            "status": "APPROVED",
            "tipo": "REPASSE_CUSTO",
            "produto": payload.get("produto") or "Gasolina Comum",
            "delta_preco": float(payload.get("delta_preco") or 0.10),
            "elasticidade": float(payload.get("elasticidade") or -0.65),
            "executado_por": operator_id,
            "confirmacao_erp": f"REP-{int(datetime.now(UTC).timestamp())}",
        }

    # Absorcao de margem operacional
    if any(k in act_combined for k in ["absorver_margem", "absorver"]):
        return {
            "status": "APPROVED",
            "tipo": "ABSORCAO_MARGEM",
            "impacto_margem_pct": float(payload.get("impacto_margem_pct") or -0.5),
            "executado_por": operator_id,
            "confirmacao_erp": f"ABS-{int(datetime.now(UTC).timestamp())}",
        }

    # Revisao de estrategia de precos (Benchmark)
    if any(k in act_combined for k in ["revisar_estrategia", "revisar"]):
        return {
            "status": "APPROVED",
            "tipo": "REVISAO_ESTRATEGIA",
            "escopo": payload.get("escopo") or "Precos e Margem Competitiva",
            "executado_por": operator_id,
            "confirmacao_erp": f"ESTR-{int(datetime.now(UTC).timestamp())}",
        }

    # Auditoria de concorrencia no raio
    if any(k in act_combined for k in ["auditar_concorrencia", "concorrencia"]):
        return {
            "status": "APPROVED",
            "tipo": "AUDITORIA_CONCORRENCIA",
            "raio_km": float(payload.get("raio_km") or 3.0),
            "executado_por": operator_id,
            "confirmacao_erp": f"BENCH-{int(datetime.now(UTC).timestamp())}",
        }

    # Abertura de chamado TEF (Fuga Financeira)
    if any(k in act_combined for k in ["abrir_chamado_tef", "tef", "chamado"]):
        return {
            "status": "APPROVED",
            "tipo": "CHAMADO_TEF",
            "terminal": payload.get("terminal") or "POS Sem Fio 03",
            "motivo": payload.get("motivo") or "Divergencia de liquidacao TEF",
            "executado_por": operator_id,
            "protocolo_chamado": f"TEF-{int(datetime.now(UTC).timestamp())}",
            "confirmacao_erp": f"TEF-{int(datetime.now(UTC).timestamp())}",
        }

    # Lancamento de campanha de incentivo a frentistas
    if any(k in act_combined for k in ["lancar_campanha_frentistas", "campanha", "frentistas"]):
        return {
            "status": "APPROVED",
            "tipo": "CAMPANHA_FRENTISTAS",
            "meta_conversao_pct": float(payload.get("meta_conversao_pct") or 25.0),
            "bonificacao_reais": float(payload.get("bonificacao_reais") or 1.50),
            "executado_por": operator_id,
            "confirmacao_erp": f"CAMP-{int(datetime.now(UTC).timestamp())}",
        }

    # Ativacao de combo no PDV / Vendas Cruzadas
    if any(k in act_combined for k in ["ativar_combo_pdv", "ativar_combo", "combo"]):
        origem = payload.get("origem") or "Gasolina Aditivada"
        recomendado = payload.get("recomendado") or "Aditivo Flex STP"
        return {
            "status": "APPROVED",
            "tipo": "ATIVACAO_COMBO_PDV",
            "origem": str(origem),
            "recomendado": str(recomendado),
            "desconto_combo_pct": float(payload.get("desconto_pct") or 5.0),
            "executado_por": operator_id,
            "confirmacao_erp": f"COMBO-{int(datetime.now(UTC).timestamp())}",
        }

    # Pedido de combustivel / Carreta
    if any(k in act_combined for k in ["combustivel", "combustível", "pedido", "carreta", "fuel", "tank"]):
        litros = payload.get("litros") or payload.get("volume") or 15000
        combustivel = payload.get("combustivel") or payload.get("produto") or "GASOLINA COMUM"
        fornecedor = payload.get("fornecedor") or "Distribuidora Oficial"
        return {
            "status": "APPROVED",
            "tipo": "PEDIDO_COMBUSTIVEL",
            "litros": float(litros),
            "combustivel": str(combustivel).upper(),
            "fornecedor": str(fornecedor),
            "executado_por": operator_id,
            "data_programada": payload.get("data_programada") or datetime.now(UTC).strftime("%Y-%m-%d"),
            "confirmacao_erp": f"PED-{int(datetime.now(UTC).timestamp())}",
        }

    # Estancamento de quebra / Sangria de caixa
    if any(k in act for k in ["quebra", "sangria", "caixa", "furo", "estancar"]):
        valor = payload.get("valor") or 85.0
        turno = payload.get("turno") or 1
        return {
            "status": "APPROVED",
            "tipo": "ESTANCAMENTO_QUEBRA",
            "valor": float(valor),
            "turno": int(turno),
            "operador_notificado": payload.get("operador") or operator_id,
            "motivo": payload.get("motivo") or "Quebra divergente estancada preventivamente",
            "confirmacao_erp": f"SANGRIA-{int(datetime.now(UTC).timestamp())}",
        }

    # Ajuste de margem / Reprecificacao
    if any(k in act for k in ["margem", "preco", "preço", "reprecificar", "ajuste_margem"]):
        produto = payload.get("produto") or "Gasolina Aditivada"
        novo_preco = payload.get("novo_preco") or payload.get("preco") or 6.19
        return {
            "status": "APPROVED",
            "tipo": "AJUSTE_MARGEM",
            "produto": str(produto),
            "novo_preco": float(novo_preco),
            "margem_alvo_pct": float(payload.get("margem_alvo_pct") or 18.0),
            "confirmacao_erp": f"PREC-{int(datetime.now(UTC).timestamp())}",
        }

    # Reconciliacao / Homologacao de turno
    if any(k in act for k in ["conciliar", "conciliação", "conciliacao", "turno", "homologar"]):
        turno = payload.get("turno") or 1
        return {
            "status": "APPROVED",
            "tipo": "CONCILIACAO_TURNO",
            "turno": int(turno),
            "data": payload.get("data") or datetime.now(UTC).strftime("%Y-%m-%d"),
            "score": float(payload.get("score") or 98.5),
            "status_fiscal": "HOMOLOGADO",
            "confirmacao_erp": f"HOMOL-{int(datetime.now(UTC).timestamp())}",
        }

    # Padrao / Generico
    return {
        "status": "APPROVED",
        "tipo": action_name,
        "action_type": action_type,
        "executado_por": operator_id,
        "payload": payload,
        "confirmacao_erp": f"TX-{int(datetime.now(UTC).timestamp())}",
    }


# =============================================================================
# GOVERNANCA RBAC DE OPERADORES & HUMAN-IN-THE-LOOP (F7-03)
# =============================================================================

VALID_OPERATOR_ROLES = {"frentista", "caixa", "gerente", "administrador"}

ROLE_HIERARCHY_LEVELS = {
    "frentista": 1,
    "caixa": 2,
    "gerente": 3,
    "administrador": 4,
}

# Acoes de mutacao de alto impacto (exigem perfil 'gerente' ou 'administrador' - nivel >= 3)
HIGH_IMPACT_MUTATION_KEYWORDS = [
    "pedido_combustivel",
    "pedido",
    "combustivel",
    "combustível",
    "carreta",
    "ajustar_margem",
    "ajuste_margem",
    "margem",
    "travar_preco",
    "preco",
    "preço",
    "reprecificar",
    "homologar_cenario",
    "aplicar_cenario",
    "cenario",
    "bonificar",
    "campanha_frentistas",
]

# Acoes de caixa (exigem ao menos 'caixa', 'gerente' ou 'administrador' - nivel >= 2)
CASHIER_MUTATION_KEYWORDS = [
    "estancar_quebra",
    "estancar",
    "quebra",
    "forcar_sangria",
    "sangria",
    "caixa",
    "furo",
    "conciliar",
    "conciliacao",
    "conciliação",
    "homologar_turno",
    "fechamento",
    "homologar_fechamento",
    "auditar_cancelamentos",
]


def evaluate_action_permission(
    action_name: str,
    action_type: str,
    operator_role: str | None = "gerente"
) -> tuple[bool, int, str]:
    """
    Avalia a autorizacao do operador com base no perfil RBAC (F7-03).
    Retorna (autorizado: bool, nivel_minimo: int, mensagem: str).
    """
    role = (operator_role or "gerente").strip().lower()
    if role not in VALID_OPERATOR_ROLES:
        return (
            False,
            99,
            f"Autorizacao negada: perfil de operador '{operator_role}' desconhecido. Perfis permitidos: {', '.join(sorted(VALID_OPERATOR_ROLES))}."
        )

    act_type = (action_type or "mutation").strip().lower()

    # Acoes de inspecao e navegacao sao permitidas para qualquer role (nivel >= 1)
    if act_type in ("inspection", "navigation"):
        return (True, 1, "Acao de inspecao autorizada para todos os perfis.")

    # Acoes de mutacao transacional
    act_clean = (action_name or "").lower().replace("-", "_").strip()
    is_high_impact = any(k in act_clean for k in HIGH_IMPACT_MUTATION_KEYWORDS)
    is_cashier = any(k in act_clean for k in CASHIER_MUTATION_KEYWORDS)

    if is_high_impact:
        required_level = 3  # gerente ou administrador
        required_role_name = "gerente"
    elif is_cashier:
        required_level = 2  # caixa, gerente ou administrador
        required_role_name = "caixa"
    else:
        # Por padrao, mutacoes nao classificadas exigem nivel gerente para seguranca estrita
        required_level = 3
        required_role_name = "gerente"

    op_level = ROLE_HIERARCHY_LEVELS.get(role, 1)
    if op_level < required_level:
        return (
            False,
            required_level,
            f"Autorizacao negada: operador com perfil '{role}' nao possui permissao para executar a acao '{action_name}'. Perfil minimo exigido: '{required_role_name}'."
        )

    return (True, required_level, "Acao autorizada com sucesso.")


@router.post(
    "/actions/execute",
    response_model=ActionVoucher,
    summary="Execucao Transacional de Acoes GenUI (Human-in-the-Loop Gateway)",
    dependencies=[Depends(verify_admin_auth)],
)
async def execute_action_endpoint(
    req: ActionExecuteRequest,
    request: Request,
    engine: AuraEngine = Depends(get_aura_engine),
):
    """
    Executa acoes transacionais autorizadas pelo operador (Camada 3 de micro-widgets GenUI).
    Garante idempotencia estrita via action_id, valida RBAC do operador (F7-03),
    registra o voucher auditavel assinado com HMAC-SHA256, persiste a trilha de
    auditoria duravel no SQLite (F7-04) e injeta a confirmacao na memoria de sessao.
    """
    mem = engine.session_memory
    client_ip = None
    if request is not None:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        elif request.headers.get("x-real-ip"):
            client_ip = request.headers.get("x-real-ip").strip()
        elif getattr(request, "client", None) is not None:
            client_ip = request.client.host

    action_name = req.action_name or "acao_executiva"
    payload = req.payload or {}
    operator = req.operator_id or "operador_01"
    op_role = req.operator_role or "gerente"
    act_type = (req.action_type or "mutation").strip().lower()

    # Telemetria SRE (F9-02): Registrar solicitacao de acao transacional
    engine.telemetry.record_action_requested(action_id=req.action_id, session_id=req.session_id)

    # 1. F7-03: Validacao de permissao e perfil de operador (RBAC) ANTES de qualquer processamento
    # Evita que um operador desautorizado obtenha vouchers ou contorne o bloqueio via replay de action_id
    is_authorized, min_level, reason = evaluate_action_permission(
        action_name=action_name,
        action_type=act_type,
        operator_role=op_role,
    )

    if not is_authorized:
        # F9-02: Registrar bloqueio de seguranca na telemetria
        engine.telemetry.record_security_block(
            reason=reason,
            session_id=req.session_id,
            tool_call_id=req.tool_call_id,
        )
        # F7-04: Registro imediato de tentativa rejeitada na trilha de auditoria
        mem.save_audit_log(
            session_id=req.session_id,
            tool_call_id=req.tool_call_id,
            action_id=req.action_id,
            action_name=action_name,
            action_type=act_type,
            operator_id=operator,
            operator_role=op_role,
            authorized=False,
            status="REJECTED_FORBIDDEN",
            details={
                "motivo": reason,
                "payload": payload,
            },
            client_ip=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason,
        )

    # 2. Validacao estrita de idempotencia: se action_id ja existe e operador esta autorizado, retorna voucher sem reprocessar
    existing_voucher = mem.get_action_voucher(req.action_id)
    if existing_voucher is not None:
        return existing_voucher

    # 3. Execucao da rotina de negocio autorizada
    try:
        details = _dispatch_business_action(
            action_name=action_name,
            action_type=req.action_type,
            payload=payload,
            operator_id=operator,
        )
    except Exception as exc:
        # F9-02: Registrar rollback transacional na telemetria
        engine.telemetry.record_action_rolled_back(
            action_id=req.action_id,
            session_id=req.session_id,
            reason=str(exc),
        )
        mem.save_audit_log(
            session_id=req.session_id,
            tool_call_id=req.tool_call_id,
            action_id=req.action_id,
            action_name=action_name,
            action_type=req.action_type,
            operator_id=operator,
            operator_role=op_role,
            authorized=True,
            status="FAILED",
            details={"error": str(exc), "payload": payload},
            client_ip=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha na execucao da rotina transacional: {exc}",
        )

    # 4. Geracao do Comprovante (Action Voucher)
    voucher_id = generate_uuid4()
    ts_now = datetime.now(UTC).isoformat()
    signature = generate_action_voucher_signature(
        voucher_id=voucher_id,
        action_id=req.action_id,
        tool_call_id=req.tool_call_id,
        status="APPROVED",
        timestamp=ts_now,
    )

    voucher = ActionVoucher(
        voucher_id=voucher_id,
        action_id=req.action_id,
        tool_call_id=req.tool_call_id,
        status="APPROVED",
        timestamp=ts_now,
        action_name=action_name,
        details=details,
        signature=signature,
    )

    # 5. Persistencia do Voucher no SQLite (garantia de idempotencia duravel)
    mem.save_action_voucher(
        voucher=voucher,
        session_id=req.session_id,
        operator_id=operator,
        action_type=req.action_type,
        payload=payload,
    )

    # 6. F5-02: Injecao direta de mensagem canonica com role: 'tool' no historico da sessao
    if req.session_id:
        tool_payload = {
            "status": "APPROVED",
            "action_id": req.action_id,
            "voucher_id": voucher.voucher_id,
            "details": details,
        }
        mem.save_message(
            session_id=req.session_id,
            role="tool",
            content=json.dumps(tool_payload, ensure_ascii=False),
            intent=action_name,
            tool_call_id=req.tool_call_id,
            name=action_name,
            metadata={
                "voucher_id": voucher.voucher_id,
                "operator_id": operator,
                "operator_role": op_role,
                "signature": signature,
                "action_type": req.action_type,
            }
        )

    # 7. F7-04: Persistencia da execucao homologada na trilha de auditoria
    mem.save_audit_log(
        session_id=req.session_id,
        tool_call_id=req.tool_call_id,
        action_id=req.action_id,
        action_name=action_name,
        action_type=req.action_type,
        operator_id=operator,
        operator_role=op_role,
        authorized=True,
        status="APPROVED",
        details={
            "voucher_id": voucher.voucher_id,
            "business_details": details,
            "payload": payload,
        },
        client_ip=client_ip,
    )

    # F9-02: Registrar acao aprovada com sucesso na telemetria
    engine.telemetry.record_action_approved(action_id=req.action_id, session_id=req.session_id)

    return voucher


@router.get(
    "/audit/logs",
    response_model=list[ActionAuditLogRecord],
    summary="Consulta da Trilha de Auditoria Transacional (OWASP LLM & Governanca)",
    dependencies=[Depends(verify_admin_auth)],
)
async def get_audit_logs_endpoint(
    session_id: str | None = Query(None, description="Filtrar por session_id"),
    action_id: str | None = Query(None, description="Filtrar por action_id"),
    operator_id: str | None = Query(None, description="Filtrar por operator_id"),
    status: str | None = Query(None, description="Filtrar por status (APPROVED, REJECTED_FORBIDDEN, FAILED)"),
    limit: int = Query(50, ge=1, le=500, description="Limite maximo de registros retornados"),
    engine: AuraEngine = Depends(get_aura_engine),
):
    """
    Consulta os registros duraveis de auditoria de acoes executadas ou rejeitadas pelo RBAC (F7-04).
    """
    norm_status = status.strip().upper() if status else None
    logs = engine.get_audit_logs(
        session_id=session_id,
        action_id=action_id,
        operator_id=operator_id,
        status=norm_status,
        limit=limit,
    )
    return logs


# =============================================================================
# TELEMETRIA SRE & OBSERVABILIDADE (F9-02)
# =============================================================================

@router.get("/telemetry/metrics", summary="Metricas Consolidadas de Observabilidade e SRE")
async def get_telemetry_metrics_endpoint(
    engine: AuraEngine = Depends(get_aura_engine),
):
    """
    Retorna consolidado de SLIs de SRE em JSON:
    - ttft_ms (avg, min, max, last, count)
    - hydration_ms (avg, min, max, last, count)
    - total_actions_requested, total_actions_approved, total_actions_rolled_back
    - security_blocks
    - action_success_rate_pct
    - feature_flags
    """
    return engine.telemetry.get_metrics_summary()


@router.post("/telemetry/report", summary="Reporte de Metricas de UX pelo Cliente")
async def report_telemetry_endpoint(
    req: TelemetryReportRequest,
    engine: AuraEngine = Depends(get_aura_engine),
):
    """
    Permite que o frontend reporte metricas percebidas (tempo de hidratacao real, latencia, rollbacks).
    """
    result = engine.telemetry.record_client_report(req.model_dump())
    return {"status": "ok", **result}


# =============================================================================
# CONTINGENCIA & GESTAO DE FEATURE FLAGS (CIRCUIT BREAKER - F9-03)
# =============================================================================

@router.get(
    "/admin/feature-flags",
    summary="Inspecao de Feature Flags Ativas (Circuit Breaker)",
    dependencies=[Depends(verify_admin_auth)],
)
async def get_feature_flags_endpoint():
    """
    Retorna o status atual das feature flags ativas no runtime.
    """
    return {
        "status": "ok",
        "ENABLE_GENUI": is_genui_enabled(),
        "flags": get_feature_flags(),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.post(
    "/admin/feature-flags",
    summary="Atualizacao a Quente de Feature Flags (Circuit Breaker)",
    dependencies=[Depends(verify_admin_auth)],
)
async def update_feature_flags_endpoint(req: FeatureFlagsUpdateRequest):
    """
    Permite alterar a quente o valor de ENABLE_GENUI ou outras flags no runtime,
    viabilizando rollback ou comutacao imediata para contingencia sem restart de servidor.
    """
    updates = {}
    if req.ENABLE_GENUI is not None:
        updates["ENABLE_GENUI"] = req.ENABLE_GENUI
    if req.enable_genui is not None:
        updates["ENABLE_GENUI"] = req.enable_genui
    if req.flags and isinstance(req.flags, dict):
        updates.update(req.flags)

    updated_flags = update_feature_flags(updates)
    return {
        "status": "updated",
        "ENABLE_GENUI": is_genui_enabled(),
        "flags": updated_flags,
        "timestamp": datetime.now(UTC).isoformat(),
    }


# =============================================================================
# CENTRAL DE AUTOMACAO & MONITORAMENTO CONFIGURAVEL (P1 / FRENTE 1)
# =============================================================================

@router.get(
    "/admin/automation-settings",
    summary="Consulta das Configuracoes e Toggles de Automacao da AURA",
    dependencies=[Depends(verify_admin_auth)],
)
async def get_automation_settings_endpoint():
    """
    Retorna as configuracoes e toggles ativos de automacao em segundo plano.
    Permite verificar o Master Switch, regras de turno, tanques e pista.
    """
    settings = get_automation_settings()
    return {
        "status": "ok",
        "settings": settings.model_dump(),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.post(
    "/admin/automation-settings",
    summary="Atualizacao a Quente de Configuracoes e Toggles de Automacao",
    dependencies=[Depends(verify_admin_auth)],
)
async def update_automation_settings_endpoint(
    req: dict[str, Any] = Body(..., description="Payload de configuracao parcial ou completo"),
    request: Request = None,
):
    """
    Atualiza as regras e interruptores de automacao em tempo de execucao,
    persistindo as alteracoes em JSON local e sincronizando feature flags.
    """
    updated_by = "gestor"
    if request and request.headers.get("X-Operator-Role"):
        updated_by = request.headers.get("X-Operator-Role")

    try:
        updated = update_automation_settings(req, updated_by=updated_by)
        return {
            "status": "updated",
            "settings": updated.model_dump(),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        logger.error(f"Erro ao atualizar configuracoes de automacao: {exc}")
        raise HTTPException(
            status_code=400,
            detail={"error": f"Erro de validacao nas configuracoes: {exc!s}"},
        )


# =============================================================================
# ESTEIRA DE WEBHOOKS ASSINCRONOS (WHATSAPP, N8N, EVOLUTION API - P1-7)
# =============================================================================

@router.post(
    "/webhooks/turno-fechamento",
    summary="Despacho de Resumo de Turno para Webhooks n8n e WhatsApp",
    dependencies=[Depends(verify_admin_auth)],
)
async def dispatch_turno_fechamento_endpoint(
    req: TurnoResumoPayload,
    phone: str | None = Query(None, description="Telefone WhatsApp de destino opcional"),
    webhook_url: str | None = Query(None, description="URL do webhook n8n opcional"),
):
    """
    Dispara o resumo consolidado de fechamento de turno para o n8n e Evolution API.
    """
    res = await notify_fechamento_turno(payload=req, phone=phone, webhook_url=webhook_url)
    return {"status": "dispatched", "details": res}


@router.post(
    "/webhooks/alerta-tanque",
    summary="Despacho de Alerta de Ruptura de Tanque para n8n e WhatsApp",
    dependencies=[Depends(verify_admin_auth)],
)
async def dispatch_alerta_tanque_endpoint(
    req: AlertaTanquePayload,
    phone: str | None = Query(None, description="Telefone WhatsApp de destino opcional"),
    webhook_url: str | None = Query(None, description="URL do webhook n8n opcional"),
):
    """
    Dispara alerta urgente de nivel critico de combustivel para o n8n e Evolution API.
    """
    res = await notify_alerta_tanque(payload=req, phone=phone, webhook_url=webhook_url)
    return {"status": "dispatched", "details": res}

@router.get("/stations", response_model=list[StationStatus], summary="Diagnóstico e Status das Estações")
async def stations_endpoint(
    engine: AuraEngine = Depends(get_aura_engine),
):
    """
    Lista postos/filiais homologados e verifica o status da conexão do banco ERP (5433)
    e banco vetorial pgvector (5433), além de latência e saúde de observabilidade.
    """
    station_info = await asyncio.to_thread(engine.get_stations_status)
    return [station_info]


@router.get("/health", summary="Health Check Operacional")
async def health_endpoint():
    """Health check ultrarrápido para balanceadores de carga e orquestradores."""
    return {
        "status": "healthy",
        "service": "AURA Core Engine",
        "version": "1.0.0",
    }


# =============================================================================
# CONFORMIDADE JURIDICA E OPT-IN DO LOJISTA (LGPD & CLEAN ROOM - BLOCO 6)
# =============================================================================

@router.get(
    "/compliance/status",
    summary="Verificacao de Conformidade Juridica e Opt-In LGPD",
)
async def get_compliance_status_endpoint(
    cnpj: str | None = Query(None, description="CNPJ opcional do estabelecimento comercial"),
    engine: AuraEngine = Depends(get_aura_engine),
):
    """
    Retorna o status completo de conformidade juridica e tecnica do estabelecimento,
    incluindo conferencia de hash do termo formal, role read-only e isolamento AUPS.
    """
    result = await asyncio.to_thread(engine.check_compliance_opt_in, cnpj)
    return result


@router.get(
    "/compliance/term",
    summary="Conteudo Integral do Termo de Interoperabilidade e Hash SHA-256",
)
async def get_compliance_term_endpoint(
    engine: AuraEngine = Depends(get_aura_engine),
):
    """
    Retorna o conteudo textual integral do termo formal de interoperabilidade v1.1
    e seu respectivo hash criptografico SHA-256 para exibicao e auditoria no frontend.
    """
    try:
        content = await asyncio.to_thread(engine.compliance_manager.get_term_content)
        term_hash = await asyncio.to_thread(engine.compliance_manager.compute_term_hash)
        return {
            "status": "ok",
            "versao": "1.1",
            "version": "1.1",
            "title": "Termo de Interoperabilidade e Tratamento de Dados v1.1 - AURA Clean Room",
            "hash_sha256": term_hash,
            "content_markdown": content,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Falha ao carregar termo de conformidade: {exc!s}"},
        ) from exc


@router.post(
    "/compliance/opt-in",
    summary="Registro Formal de Opt-In de Interoperabilidade pelo Lojista",
    dependencies=[Depends(verify_admin_auth)],
)
async def register_compliance_opt_in_endpoint(
    payload: dict[str, Any] = Body(..., description="Dados formais do opt-in do lojista"),
    engine: AuraEngine = Depends(get_aura_engine),
):
    """
    Registra duravelmente o opt-in de interoperabilidade do lojista em SQLite e JSON.
    """
    try:
        record = await asyncio.to_thread(engine.compliance_manager.register_opt_in, payload)
        verif = await asyncio.to_thread(engine.compliance_manager.verify_compliance, record.loja_cnpj)
        return {
            "status": "ok",
            "sucesso": True,
            "opt_in": record.model_dump(),
            "verification": verif.model_dump(),
        }
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Falha ao registrar opt-in: {exc!s}"},
        ) from exc


# =============================================================================
# FACTORY DA APLICAÇÃO STANDALONE
# =============================================================================

def create_aura_app(engine: AuraEngine | None = None) -> FastAPI:
    """Cria e configura uma instância completa da aplicação FastAPI para a AURA."""
    if engine is not None:
        set_aura_engine(engine)

    app = FastAPI(
        title="AURA Core Engine API",
        description="Motor Cognitivo Headless Desacoplado para Postos de Combustíveis e PDV",
        version="1.0.0",
    )

    # Middleware de Correlacao X-Request-ID e Logging Estruturado JSON (P1-6)
    @app.middleware("http")
    async def request_correlation_logging_middleware(request: Request, call_next):
        req_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        token_req = current_request_id.set(req_id)

        client_ip = request.headers.get("x-forwarded-for")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        elif request.headers.get("x-real-ip"):
            client_ip = request.headers.get("x-real-ip").strip()
        elif request.client:
            client_ip = request.client.host
        else:
            client_ip = "127.0.0.1"
        token_ip = current_client_ip.set(client_ip)

        t0 = time.perf_counter()
        try:
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            response.headers["X-Request-ID"] = req_id

            if request.url.path.startswith("/api/"):
                logger.info(
                    f"{request.method} {request.url.path} - status {response.status_code} ({elapsed_ms:.1f}ms)",
                    extra={
                        "request_id": req_id,
                        "client_ip": client_ip,
                        "route": request.url.path,
                        "method": request.method,
                        "status_code": response.status_code,
                        "elapsed_ms": elapsed_ms,
                    }
                )
            return response
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            logger.error(
                f"Erro nao tratado em {request.method} {request.url.path}: {exc}",
                extra={
                    "request_id": req_id,
                    "client_ip": client_ip,
                    "route": request.url.path,
                    "method": request.method,
                    "elapsed_ms": elapsed_ms,
                },
                exc_info=True,
            )
            raise exc
        finally:
            current_request_id.reset(token_req)
            current_client_ip.reset(token_ip)

    # Middleware CORS com Origens Restritas Parametrizadas (P1-4)
    cors_origins = get_cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Registra rotas da API
    app.include_router(router)

    # Montagem do Painel Web SPA Local da AURA
    web_dir = Path(__file__).resolve().parent.parent / "web"
    if web_dir.exists():
        vendor_dir = web_dir / "static" / "vendor"
        if vendor_dir.exists():
            app.mount("/static/vendor", StaticFiles(directory=str(vendor_dir)), name="static_vendor")
            app.mount("/vendor", StaticFiles(directory=str(vendor_dir)), name="vendor")
        app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

        @app.get("/favicon.ico", include_in_schema=False)
        async def serve_favicon():
            svg_icon = (
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
                '<circle cx="16" cy="16" r="14" fill="#07090e" stroke="#06b6d4" stroke-width="2"/>'
                '<circle cx="16" cy="16" r="6" fill="#10b981"/>'
                '<path d="M16 4 L16 10 M16 22 L16 28 M4 16 L10 16 M22 16 L28 16" stroke="#7c3aed" stroke-width="2"/>'
                '</svg>'
            )
            return Response(content=svg_icon, media_type="image/svg+xml")

        @app.get("/", include_in_schema=False)
        @app.get("/dashboard", include_in_schema=False)
        async def serve_dashboard():
            index_file = web_dir / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file))
            return {"service": "AURA Core Engine API", "status": "online"}

        @app.get("/showcase", include_in_schema=False)
        @app.get("/apresentacao", include_in_schema=False)
        async def serve_showcase():
            showcase_file = web_dir / "showcase.html"
            if showcase_file.exists():
                return FileResponse(str(showcase_file))
            index_file = web_dir / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file))
            return {"service": "AURA Showcase", "status": "online"}

    return app


# Instancia padrao da aplicacao ASGI para execucao direta via uvicorn (ex: uvicorn core.aura_api:app)
app = create_aura_app()

