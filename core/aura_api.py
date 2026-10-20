"""
Endpoints HTTP de Integração FastAPI para o Motor Cognitivo AURA.
(Server-Sent Events / SSE, Invocação Direta de Intenções e Diagnóstico de Postos)

Conectores:
1. POST /api/v1/aura/chat: Suporte a streaming SSE em tempo real ou resposta síncrona JSON
2. POST /api/v1/aura/execute-intent: Invocação direta das 12 ferramentas analíticas (Run-Out, LMC, Turno, RCA...)
3. GET  /api/v1/aura/stations: Lista filiais homologadas e status de conexão ERP/pgvector
4. GET  /api/v1/aura/health: Health check de prontidão operacional
"""
# ruff: noqa: B008, BLE001, RUF059, TRY201

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    Body,
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config.settings import AURA_API_KEY, get_cors_origins
from core.aura_engine import (
    AuraChunk,
    AuraChunkType,
    AuraEngine,
    StationStatus,
)
from core.automation_config import (
    get_automation_settings,
    update_automation_settings,
)
from core.command_journal import (
    AuraCommandJournal,
    CommandJournalStatus,
    get_command_journal,
)
from core.command_journal import (
    set_command_journal as _set_global_command_journal,
)
from core.config import (
    get_feature_flags,
    is_genui_enabled,
    resolve_genui_flag,
    update_feature_flags,
)
from core.desktop_notifier import DesktopNotifier, get_desktop_notifier
from core.logger import current_client_ip, current_request_id, logger
from core.outbox import (
    AuraTransactionalOutbox,
    get_transactional_outbox,
)
from core.outbox import (
    set_transactional_outbox as _set_global_outbox,
)
from core.proactive_daemon import AuraProactiveDaemon
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
_daemon_instance: AuraProactiveDaemon | None = None
_desktop_notifier_instance: DesktopNotifier | None = None
_outbox_instance: AuraTransactionalOutbox | None = None
_command_journal_instance: AuraCommandJournal | None = None
_public_data_repo_instance: Any | None = None


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


def get_proactive_daemon() -> AuraProactiveDaemon:
    """Dependency Provider para obter a instancia ativa do daemon proativo."""
    global _daemon_instance
    if _daemon_instance is None:
        _daemon_instance = AuraProactiveDaemon(
            desktop_notifier=None,
            desktop_notify=False,
        )
    return _daemon_instance


def set_proactive_daemon(daemon: AuraProactiveDaemon | None) -> None:
    """Permite sobrescrever ou injetar uma instancia customizada do daemon proativo."""
    global _daemon_instance
    _daemon_instance = daemon
    if _daemon_instance is not None and _desktop_notifier_instance is not None:
        _daemon_instance.desktop_notifier = _desktop_notifier_instance


def get_active_desktop_notifier() -> DesktopNotifier:
    """Dependency Provider para obter a instancia ativa do notificador desktop HITL."""
    if _desktop_notifier_instance is not None:
        return _desktop_notifier_instance
    return get_desktop_notifier()


def set_desktop_notifier(notifier: DesktopNotifier | None) -> None:
    """Permite sobrescrever ou injetar uma instancia customizada do notificador desktop."""
    global _desktop_notifier_instance
    _desktop_notifier_instance = notifier
    if notifier is not None and _daemon_instance is not None:
        _daemon_instance.desktop_notifier = notifier


def get_active_outbox() -> AuraTransactionalOutbox:
    """Dependency Provider para obter a instancia ativa da Transactional Outbox."""
    if _outbox_instance is not None:
        return _outbox_instance
    return get_transactional_outbox()


def set_transactional_outbox(outbox: AuraTransactionalOutbox | None) -> None:
    """Permite sobrescrever ou injetar uma instancia customizada da Transactional Outbox."""
    global _outbox_instance
    _outbox_instance = outbox
    _set_global_outbox(outbox)


def get_active_command_journal() -> AuraCommandJournal:
    """Dependency Provider para obter a instancia ativa do Persist-First Command Journal."""
    return get_command_journal()


def set_command_journal(journal: AuraCommandJournal | None) -> None:
    """Permite sobrescrever ou injetar uma instancia customizada do Command Journal."""
    global _command_journal_instance
    _command_journal_instance = journal
    _set_global_command_journal(journal)


def get_active_public_data_repo() -> Any:
    """Dependency Provider para obter o repositorio ativo de dados publicos."""
    global _public_data_repo_instance
    if _public_data_repo_instance is not None:
        return _public_data_repo_instance
    from core.integrations.public_data import get_public_data_repository

    return get_public_data_repository()


def set_public_data_repository(repo: Any | None) -> None:
    """Permite sobrescrever ou injetar instancia customizada do repositorio de dados publicos."""
    global _public_data_repo_instance
    _public_data_repo_instance = repo


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
            # Despacho de alertas proativos pendentes in-app da AURA
            try:
                daemon_inst = get_proactive_daemon()
                pending = daemon_inst.get_unread_in_app_alerts(filial_id=req.filial_id, mark_read=False)
                for palert in pending:
                    alert_dict = palert if isinstance(palert, dict) else palert.to_dict()
                    chunk = AuraChunk(
                        chunk_type=AuraChunkType.PROACTIVE_ALERT,
                        data=alert_dict,
                        title=alert_dict.get("title"),
                        text=alert_dict.get("message"),
                        session_id=req.session_id,
                    )
                    yield chunk.to_sse()
            except Exception as exc:
                logger.debug(f"AuraAPI: Nenhum alerta proativo no stream POST: {exc}")

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
        # Despacho de alertas proativos pendentes in-app da AURA
        try:
            daemon_inst = get_proactive_daemon()
            pending = daemon_inst.get_unread_in_app_alerts(filial_id=filial_id, mark_read=False)
            for palert in pending:
                alert_dict = palert if isinstance(palert, dict) else palert.to_dict()
                chunk = AuraChunk(
                    chunk_type=AuraChunkType.PROACTIVE_ALERT,
                    data=alert_dict,
                    title=alert_dict.get("title"),
                    text=alert_dict.get("message"),
                    session_id=session_id,
                )
                yield chunk.to_sse()
        except Exception as exc:
            logger.debug(f"AuraAPI: Nenhum alerta proativo no stream GET: {exc}")

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


class ActionRollbackRequest(BaseModel):
    """Modelo de requisicao para rollback transacional de um Action Voucher (Fase 6)."""

    action_id: str | None = Field(default=None, description="UUID v4 da acao transacional a estornar")
    voucher_id: str | None = Field(default=None, description="UUID v4 opcional do voucher a estornar")
    command_key: str | None = Field(default=None, description="Chave deterministica opcional no Command Journal")
    idempotency_key: str | None = Field(default=None, description="Alias opcional para command_key")
    session_id: str = Field(default="", description="Identificador da sessao conversacional")
    tool_call_id: str | None = Field(default=None, description="UUID v4 opcional da invocacao original")
    action_name: str = Field(default="", description="Nome opcional da acao transacional")
    reason: str = Field(
        default="Rollback transacional solicitado pelo operador",
        description="Justificativa do estorno transacional",
    )
    motivo: str | None = Field(default=None, description="Alias em portugues para reason")
    operator_id: str = Field(default="operador_01", description="Identificador do operador responsavel pelo estorno")
    operator_role: str = Field(default="gerente", description="Perfil RBAC do operador")
    payload: dict[str, Any] = Field(default_factory=dict, description="Metadados complementares de rollback")


class JournalRecoverRequest(BaseModel):
    """Payload opcional para recuperacao de comandos orfaos em RUNNING no Command Journal."""

    stale_after_sec: float | None = Field(
        default=None,
        ge=0.0,
        description="Tempo minimo em segundos para considerar um comando RUNNING como orfao (0 = todos)",
    )
    error_message: str | None = Field(
        default=None,
        description="Mensagem forense opcional a registrar nos comandos recuperados",
    )


@router.post(
    "/actions/execute",
    response_model=ActionVoucher,
    summary="Execucao Transacional de Acoes GenUI com Persist-First Command Journal (Fase 6)",
    dependencies=[Depends(verify_admin_auth)],
)
async def execute_action_endpoint(
    req: ActionExecuteRequest,
    request: Request,
    engine: AuraEngine = Depends(get_aura_engine),
    journal: AuraCommandJournal = Depends(get_active_command_journal),
):
    """
    Executa acoes transacionais autorizadas pelo operador (Camada 3 de micro-widgets GenUI).
    Garante protocolo Persist-First via AuraCommandJournal (gravando RUNNING no SQLite WAL
    antes de qualquer efeito colateral), idempotencia estrita via command_key / action_id,
    bloqueio de corrida concorrente (HTTP 409 Conflict), validacao RBAC (F7-03),
    assinatura HMAC-SHA256 e trilha de auditoria duravel (F7-04).
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
    command_key = (
        req.idempotency_key.strip()
        if (req.idempotency_key and req.idempotency_key.strip())
        else f"voucher:{req.action_id}:execute"
    )

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

    # 2. Fase 6: Persist-First Atomic Claim no AuraCommandJournal (status = RUNNING no SQLite WAL)
    acq = journal.begin_command(
        command_key=command_key,
        action_id=req.action_id,
        action_type=act_type,
        actor=operator,
        request_payload={
            "session_id": req.session_id,
            "tool_call_id": req.tool_call_id,
            "action_id": req.action_id,
            "action_name": action_name,
            "action_type": act_type,
            "operator_id": operator,
            "operator_role": op_role,
            "payload": payload,
        },
        allow_retry=True,
    )

    if acq.already_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conflito de concorrencia: o comando '{command_key}' ja esta em execucao (RUNNING).",
        )

    if acq.already_rolled_back:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Acao '{req.action_id}' ('{command_key}') ja sofreu rollback (ROLLED_BACK) e nao pode ser reexecutada.",
        )

    if acq.already_completed:
        existing_voucher = mem.get_action_voucher(req.action_id)
        if existing_voucher is not None:
            if existing_voucher.status == "ROLLED_BACK":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Acao '{req.action_id}' ja sofreu rollback (ROLLED_BACK).",
                )
            return existing_voucher
        if isinstance(acq.result_payload, dict) and "voucher_id" in acq.result_payload:
            return ActionVoucher(**acq.result_payload)

    # 2.1 Compatibilidade retroativa: se o voucher ja existir em AuraSessionMemory (ex: pre-populado)
    existing_voucher = mem.get_action_voucher(req.action_id)
    if existing_voucher is not None:
        if existing_voucher.status == "ROLLED_BACK":
            journal.mark_rolled_back(
                command_key=command_key,
                rollback_payload=existing_voucher.model_dump(mode="json"),
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Acao '{req.action_id}' ja sofreu rollback (ROLLED_BACK).",
            )
        journal.complete_command(
            command_key=command_key,
            result_payload=existing_voucher.model_dump(mode="json"),
        )
        return existing_voucher

    # 3. Execucao da rotina de negocio autorizada (com estado RUNNING ja persistido em disco)
    try:
        details = await asyncio.to_thread(
            _dispatch_business_action,
            action_name=action_name,
            action_type=req.action_type,
            payload=payload,
            operator_id=operator,
        )
    except Exception as exc:
        journal.fail_command(
            command_key=command_key,
            error_message=str(exc),
            result_payload={"error": str(exc), "action_id": req.action_id},
        )
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
            details={"error": str(exc), "payload": payload, "command_key": command_key},
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

    # 5. Persistencia do Voucher no SQLite e transicao RUNNING -> COMPLETED no Command Journal
    mem.save_action_voucher(
        voucher=voucher,
        session_id=req.session_id,
        operator_id=operator,
        action_type=req.action_type,
        payload=payload,
    )
    journal.complete_command(
        command_key=command_key,
        result_payload=voucher.model_dump(mode="json"),
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
                "command_key": command_key,
            },
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
            "command_key": command_key,
            "business_details": details,
            "payload": payload,
        },
        client_ip=client_ip,
    )

    # F9-02: Registrar acao aprovada com sucesso na telemetria
    engine.telemetry.record_action_approved(action_id=req.action_id, session_id=req.session_id)

    return voucher


@router.post(
    "/actions/rollback",
    summary="Rollback Transacional de Action Voucher e Atualizacao do Command Journal (Fase 6)",
    dependencies=[Depends(verify_admin_auth)],
)
async def rollback_action_endpoint(
    req: ActionRollbackRequest,
    request: Request,
    engine: AuraEngine = Depends(get_aura_engine),
    journal: AuraCommandJournal = Depends(get_active_command_journal),
) -> dict[str, Any]:
    """
    Estorna um Action Voucher previamente homologado, atualizando o estado para ROLLED_BACK
    tanto no AuraCommandJournal quanto em AuraSessionMemory, re-assinando o voucher
    com HMAC-SHA256 e registrando a operacao na trilha de auditoria e telemetria.
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

    operator = (req.operator_id or "operador_01").strip()
    op_role = (req.operator_role or "gerente").strip().lower()
    eff_reason = (
        req.motivo.strip()
        if (req.motivo and req.motivo.strip())
        else (req.reason or "Rollback transacional solicitado pelo operador").strip()
    )

    existing_voucher = None
    if req.action_id:
        existing_voucher = mem.get_action_voucher(req.action_id)
    if existing_voucher is None and req.voucher_id:
        existing_voucher = mem.get_action_voucher_by_voucher_id(req.voucher_id)

    eff_action_id = (
        req.action_id
        or (existing_voucher.action_id if existing_voucher is not None else "")
        or ""
    ).strip()

    candidate_key = (
        (req.command_key or req.idempotency_key or "").strip()
        or (f"voucher:{eff_action_id}:execute" if eff_action_id else "")
    )
    journal_entry = journal.get_entry(candidate_key) if candidate_key else None
    if journal_entry is None and eff_action_id:
        journal_entry = journal.get_entry_by_action_id(eff_action_id)
    if not eff_action_id and journal_entry is not None:
        eff_action_id = journal_entry.action_id

    act_name = (
        req.action_name
        or (existing_voucher.action_name if existing_voucher is not None else "")
        or (journal_entry.action_type if journal_entry is not None else "")
        or "pedido_combustivel"
    )

    is_authorized, _, auth_reason = evaluate_action_permission(
        action_name=act_name,
        action_type="mutation",
        operator_role=op_role,
    )
    if not is_authorized:
        engine.telemetry.record_security_block(
            reason=auth_reason,
            session_id=req.session_id,
            tool_call_id=req.tool_call_id or "call_rollback",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=auth_reason,
        )

    if existing_voucher is None and journal_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voucher ou comando para action_id '{eff_action_id or candidate_key}' nao encontrado para rollback.",
        )

    if journal_entry is not None and journal_entry.status not in (
        CommandJournalStatus.COMPLETED.value,
        CommandJournalStatus.ROLLED_BACK.value,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Nao e possivel realizar rollback de comando no status '{journal_entry.status}'.",
        )

    rolled_back_voucher = (
        mem.rollback_action_voucher(
            action_id=eff_action_id,
            reason=eff_reason,
            operator_id=operator,
        )
        if existing_voucher is not None
        else None
    )

    ts_now = datetime.now(UTC).isoformat()
    rollback_meta: dict[str, Any] = {
        "action_id": eff_action_id,
        "reason": eff_reason,
        "rolled_back_by": operator,
        "operator_role": op_role,
        "rolled_back_at": ts_now,
        **(req.payload or {}),
    }
    if rolled_back_voucher is not None:
        rollback_meta["voucher_id"] = rolled_back_voucher.voucher_id
        rollback_meta["signature"] = rolled_back_voucher.signature

    if journal_entry is not None:
        journal_entry = journal.mark_rolled_back(
            command_key=journal_entry.command_key,
            rollback_payload=rollback_meta,
        )

    engine.telemetry.record_action_rolled_back(
        action_id=eff_action_id,
        session_id=req.session_id,
        reason=eff_reason,
    )

    eff_tool_call_id = (
        req.tool_call_id
        or (rolled_back_voucher.tool_call_id if rolled_back_voucher is not None else None)
        or "call_00000000-0000-4000-8000-000000000000"
    )
    mem.save_audit_log(
        session_id=req.session_id,
        tool_call_id=eff_tool_call_id,
        action_id=eff_action_id,
        action_name=act_name,
        action_type="mutation",
        operator_id=operator,
        operator_role=op_role,
        authorized=True,
        status="ROLLED_BACK",
        details=rollback_meta,
        client_ip=client_ip,
    )

    return {
        "status": "ROLLED_BACK",
        "success": True,
        "rolled_back": True,
        "action_id": eff_action_id,
        "voucher_id": (
            rolled_back_voucher.voucher_id
            if rolled_back_voucher is not None
            else (journal_entry.journal_id if journal_entry is not None else "")
        ),
        "tool_call_id": eff_tool_call_id,
        "action_name": act_name,
        "command_key": journal_entry.command_key if journal_entry is not None else candidate_key,
        "journal_status": journal_entry.status if journal_entry is not None else "ROLLED_BACK",
        "journal_id": journal_entry.journal_id if journal_entry is not None else None,
        "reason": eff_reason,
        "operator_id": operator,
        "timestamp": rolled_back_voucher.timestamp if rolled_back_voucher is not None else ts_now,
        "details": rolled_back_voucher.details if rolled_back_voucher is not None else rollback_meta,
        "signature": rolled_back_voucher.signature if rolled_back_voucher is not None else "",
        "voucher": rolled_back_voucher.model_dump(mode="json") if rolled_back_voucher is not None else None,
        "journal_entry": journal_entry.to_dict() if journal_entry is not None else None,
    }


@router.get(
    "/actions/journal",
    summary="Auditoria e Estatisticas do Persist-First Command Journal (Fase 6)",
    tags=["AURA Command Journal"],
    dependencies=[Depends(verify_admin_auth)],
)
async def actions_journal_endpoint(
    action_id: str | None = Query(default=None, description="Filtro opcional por action_id"),
    status: str | None = Query(
        default=None,
        description="Filtro opcional por status: RUNNING, COMPLETED, FAILED, ROLLED_BACK, INTERRUPTED_BY_CRASH",
    ),
    limit: int = Query(default=50, ge=1, le=500, description="Limite maximo de entradas retornadas"),
    journal: AuraCommandJournal = Depends(get_active_command_journal),
) -> dict[str, Any]:
    """
    Retorna as entradas recentes do Command Journal e as estatisticas consolidadas:
    running, completed, failed, rolled_back, interrupted_by_crash, total.
    """
    entries = await asyncio.to_thread(
        journal.list_entries,
        action_id=action_id,
        status=status,
        limit=limit,
    )
    stats = await asyncio.to_thread(journal.get_stats)
    return {
        "status": "ok",
        **stats,
        "count": len(entries),
        "limit": limit,
        "action_id_filter": action_id,
        "status_filter": status,
        "stats": stats,
        "entries": entries,
        "items": entries,
    }


@router.post(
    "/actions/journal/recover",
    summary="Crash Recovery de Comandos Orfaos em RUNNING no Command Journal (Fase 6)",
    tags=["AURA Command Journal"],
    dependencies=[Depends(verify_admin_auth)],
)
async def actions_journal_recover_endpoint(
    req: JournalRecoverRequest | None = Body(default=None),
    stale_after_sec: float | None = Query(
        default=None,
        ge=0.0,
        description="Tempo minimo em segundos para considerar RUNNING como orfao",
    ),
    journal: AuraCommandJournal = Depends(get_active_command_journal),
) -> dict[str, Any]:
    """
    Executa recover_interrupted_commands() no Command Journal, transitando comandos orfaos
    em RUNNING para INTERRUPTED_BY_CRASH e retornando a quantidade recuperada.
    """
    eff_stale = (
        req.stale_after_sec
        if (req is not None and req.stale_after_sec is not None)
        else stale_after_sec
    )
    eff_msg = req.error_message if req is not None else None
    recovered = await asyncio.to_thread(
        journal.recover_interrupted_commands,
        stale_after_sec=eff_stale,
        error_message=eff_msg,
    )
    stats = await asyncio.to_thread(journal.get_stats)
    return {
        "status": "recovered",
        "success": True,
        "recovered_count": recovered,
        "recovered": recovered,
        "stats": stats,
        "timestamp": datetime.now(UTC).isoformat(),
    }


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


@router.get("/metrics/prometheus", summary="Exportador Prometheus OpenMetrics (P2-4)")
async def get_prometheus_metrics_endpoint(
    engine: AuraEngine = Depends(get_aura_engine),
) -> Response:
    """
    Exporta todas as metricas operacionais e SLIs da AURA no padrao OpenMetrics / Prometheus.
    """
    payload = engine.telemetry.export_prometheus_metrics()
    return Response(
        content=payload,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )



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
# ENDPOINTS DO MOTOR DE ALERTAS PROATIVOS (P3-2)
# =============================================================================

class ProactiveEvaluateRequest(BaseModel):
    """Modelo de requisicao para forcar avaliacao imediata de alertas proativos."""
    tanques: list[dict[str, Any]] | None = Field(default=None, description="Leituras customizadas de tanques")
    caixas: list[dict[str, Any]] | None = Field(default=None, description="Sessoes customizadas de caixas")
    turnos: list[dict[str, Any]] | None = Field(default=None, description="Fechamentos customizados de turno")
    force: bool = Field(default=False, description="Se True, ignora cooldown e forca avaliacao")


@router.get(
    "/proactive/status",
    summary="Status do Motor de Alertas Proativos de Pista (P3-2)",
    tags=["AURA Proactive Alerts"],
)
async def get_proactive_daemon_status(
    daemon: AuraProactiveDaemon = Depends(get_proactive_daemon),
) -> dict[str, Any]:
    """Retorna estado operacional do daemon proativo, metricas de regras e contadores."""
    return daemon.get_status()


@router.post(
    "/proactive/evaluate",
    summary="Forca Execucao Imediata de Ciclo de Avaliacao de Regras (P3-2)",
    tags=["AURA Proactive Alerts"],
)
async def evaluate_proactive_rules_endpoint(
    request: ProactiveEvaluateRequest | None = Body(default=None),
    daemon: AuraProactiveDaemon = Depends(get_proactive_daemon),
) -> dict[str, Any]:
    """Forca avaliacao de regras analiticas de tanques, sangrias e turnos com retorno sincrono."""
    tanques = request.tanques if request else None
    caixas = request.caixas if request else None
    turnos = request.turnos if request else None
    force = request.force if request else False

    alerts = await daemon.evaluate_rules(tanques=tanques, caixas=caixas, turnos=turnos, force=force)
    return {
        "success": True,
        "alerts_generated": len(alerts),
        "alerts": [a.to_dict() if hasattr(a, "to_dict") else a for a in alerts],
    }


@router.get(
    "/proactive/alerts",
    summary="Historico de Alertas Proativos Emitidos (P3-2)",
    tags=["AURA Proactive Alerts"],
)
async def list_proactive_alerts_endpoint(
    limit: int = Query(default=50, ge=1, le=200, description="Limite de registros retornados"),
    offset: int = Query(default=0, ge=0, description="Deslocamento para paginacao"),
    alert_type: str | None = Query(default=None, description="Filtro por tipo de alerta"),
    severity: str | None = Query(default=None, description="Filtro por severidade"),
    filial_id: str | None = Query(default=None, description="Filtro por identificador de filial"),
    unread_only: bool = Query(default=False, description="Se True, retorna apenas alertas in-app nao lidos"),
    daemon: AuraProactiveDaemon = Depends(get_proactive_daemon),
) -> dict[str, Any]:
    """Lista alertas recentes emitidos com suporte a paginacao e filtros."""
    if unread_only:
        alerts = daemon.get_unread_in_app_alerts(filial_id=filial_id)
    else:
        alerts = daemon.get_recent_alerts(
            limit=limit,
            offset=offset,
            alert_type=alert_type,
            severity=severity,
            filial_id=filial_id,
        )
    return {
        "total": len(alerts),
        "limit": limit,
        "offset": offset,
        "unread_count": daemon.get_unread_count(),
        "channel": "AURA_IN_APP",
        "alerts": alerts,
    }


class ProactiveAlertAckRequest(BaseModel):
    """Requisicao para confirmacao (acknowledge) de alertas proativos in-app."""

    alert_id: str | None = Field(
        default=None,
        description="ID do alerta especifico a ser confirmado ou None para marcar todos como lidos",
    )


@router.post(
    "/proactive/alerts/ack",
    summary="Confirma e Marca Alertas Proativos In-App como Lidos na AURA",
    tags=["AURA Proactive Alerts"],
)
async def acknowledge_proactive_alerts_endpoint(
    request: ProactiveAlertAckRequest | None = Body(default=None),
    daemon: AuraProactiveDaemon = Depends(get_proactive_daemon),
) -> dict[str, Any]:
    """Marca alerta(s) proativo(s) in-app como lidos, decrementando contador na AURA."""
    alert_id = request.alert_id if request else None
    acknowledged = daemon.mark_alerts_as_read(alert_id=alert_id)
    return {
        "success": True,
        "acknowledged_count": acknowledged,
        "unread_remaining": daemon.get_unread_count(),
        "channel": "AURA_IN_APP",
    }


@router.get(
    "/proactive/stream",
    summary="Streaming SSE de Alertas Proativos em Tempo Real na AURA",
    tags=["AURA Proactive Alerts"],
)
async def proactive_stream_endpoint(
    request: Request,
    filial_id: str | None = Query(None, description="Filtro opcional por filial"),
    daemon: AuraProactiveDaemon = Depends(get_proactive_daemon),
):
    """
    Canal SSE dedicado para a interface da AURA receber notificacoes proativas em tempo real.
    Emite alertas pendentes imediatamente e novos alertas gerados pelo daemon.
    """
    queue = daemon.subscribe_in_app_alerts()

    async def event_generator():
        try:
            # 1. Envia alertas pendentes no momento da conexao
            pending = daemon.get_unread_in_app_alerts(filial_id=filial_id, mark_read=False)
            for alert in pending:
                chunk = AuraChunk(
                    chunk_type=AuraChunkType.PROACTIVE_ALERT,
                    data=alert,
                    title=alert.get("title"),
                    text=alert.get("message"),
                )
                yield chunk.to_sse()

            # 2. Aguarda novos alertas na fila
            while True:
                if await request.is_disconnected():
                    break
                try:
                    alert = await asyncio.wait_for(queue.get(), timeout=15.0)
                    if filial_id and alert.get("filial_id") and alert.get("filial_id") != str(filial_id).strip():
                        continue
                    chunk = AuraChunk(
                        chunk_type=AuraChunkType.PROACTIVE_ALERT,
                        data=alert,
                        title=alert.get("title"),
                        text=alert.get("message"),
                    )
                    yield chunk.to_sse()
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            daemon.unsubscribe_in_app_alerts(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =============================================================================
# ENDPOINTS DO NOTIFICADOR DESKTOP HITL SESSAO 0 -> SESSAO 1 (FASE 4)
# =============================================================================


class DesktopNotifyRequest(BaseModel):
    """Payload de requisicao para disparo de notificacao modal desktop (WTSSendMessageW)."""

    title: str = Field(..., min_length=1, description="Titulo da notificacao desktop")
    message: str = Field(..., min_length=1, description="Mensagem exibida no modal do caixa")
    severity: str = Field(
        default="warning",
        description="Severidade visual: info, warning, critical ou error",
    )
    timeout_sec: int = Field(
        default=15,
        ge=1,
        le=300,
        description="Tempo limite do modal em segundos",
    )
    alert_key: str | None = Field(
        default=None,
        description="Chave opcional de deduplicacao e cooldown anti-spam",
    )
    force: bool = Field(
        default=False,
        description="Se True, ignora a janela de cooldown para este disparo",
    )


class DesktopConfirmRequest(BaseModel):
    """Payload de requisicao para confirmacao HITL [Sim / Nao] no desktop do operador."""

    title: str = Field(..., min_length=1, description="Titulo do dialogo de confirmacao HITL")
    message: str = Field(..., min_length=1, description="Pergunta exibida ao operador do caixa")
    timeout_sec: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Tempo limite em segundos para resposta humana",
    )
    action_key: str | None = Field(
        default=None,
        description="Identificador opcional da acao transacional",
    )


@router.post(
    "/desktop/notify",
    summary="Dispara Notificacao Modal Desktop Sessao 0 -> Sessao 1 (WTSSendMessageW)",
    tags=["AURA Desktop Notifier HITL"],
)
async def desktop_notify_endpoint(
    req: DesktopNotifyRequest,
    notifier: DesktopNotifier = Depends(get_active_desktop_notifier),
) -> dict[str, Any]:
    """Dispara notificacao desktop (ou simulada em fallback) e retorna o resultado estruturado."""
    res = await asyncio.to_thread(
        notifier.notify_operator,
        title=req.title,
        message=req.message,
        severity=req.severity,
        timeout_sec=req.timeout_sec,
        alert_key=req.alert_key,
        force=req.force,
    )
    return res.to_dict()


@router.post(
    "/desktop/confirm",
    summary="Solicita Confirmacao HITL [Sim/Nao] ao Operador na Sessao 1 (WTSSendMessageW)",
    tags=["AURA Desktop Notifier HITL"],
)
async def desktop_confirm_endpoint(
    req: DesktopConfirmRequest,
    notifier: DesktopNotifier = Depends(get_active_desktop_notifier),
) -> dict[str, Any]:
    """Solicita confirmacao HITL [Sim/Nao] ao operador e retorna a decisao em tempo real."""
    res = await asyncio.to_thread(
        notifier.request_operator_confirmation,
        title=req.title,
        message=req.message,
        timeout_sec=req.timeout_sec,
        action_key=req.action_key,
    )
    return res.to_dict()


@router.get(
    "/desktop/history",
    summary="Historico Recente de Notificacoes e Confirmacoes Desktop (Fase 4)",
    tags=["AURA Desktop Notifier HITL"],
)
async def desktop_history_endpoint(
    limit: int = Query(default=50, ge=1, le=200, description="Limite de eventos retornados"),
    event_type: str | None = Query(
        default=None,
        description="Filtro opcional por tipo: notification ou confirmation",
    ),
    notifier: DesktopNotifier = Depends(get_active_desktop_notifier),
) -> dict[str, Any]:
    """Retorna historico recente de notificacoes e confirmacoes desktop emitidas."""
    items = notifier.get_history(limit=limit, event_type=event_type)
    return {
        "total": len(items),
        "limit": limit,
        "history": items,
        "items": items,
    }


# =============================================================================
# ENDPOINTS DA TRANSACTIONAL OUTBOX (SQLITE WAL - FASE 5)
# =============================================================================


class OutboxFlushRequest(BaseModel):
    """Payload opcional para drenagem manual imediata da Outbox."""

    limit: int | None = Field(default=None, ge=1, le=500, description="Quantidade maxima de mensagens no lote")
    force: bool | None = Field(
        default=None,
        description="Se True, processa imediatamente mesmo mensagens aguardando backoff",
    )


class OutboxRequeueRequest(BaseModel):
    """Payload opcional para reenfileiramento de mensagens Dead Letter (DLQ)."""

    limit: int | None = Field(default=None, ge=1, le=500, description="Quantidade maxima de mensagens reabilitadas")


@router.get(
    "/outbox/stats",
    summary="Estatisticas Consolidadas da Transactional Outbox (Fase 5)",
    tags=["AURA Transactional Outbox"],
)
async def outbox_stats_endpoint(
    outbox: AuraTransactionalOutbox = Depends(get_active_outbox),
) -> dict[str, Any]:
    """
    Retorna as estatisticas da fila Outbox:
    pending, processing, delivered, failed_retry, dead_letter, total.
    """
    stats = await asyncio.to_thread(outbox.get_stats)
    return {
        "status": "ok",
        **stats,
    }


@router.get(
    "/outbox/messages",
    summary="Lista Mensagens da Transactional Outbox (Fase 5)",
    tags=["AURA Transactional Outbox"],
)
async def outbox_messages_endpoint(
    status: str | None = Query(
        default=None,
        description="Filtro opcional por status: PENDING, PROCESSING, DELIVERED, FAILED_RETRY, DEAD_LETTER",
    ),
    limit: int = Query(default=50, ge=1, le=500, description="Limite maximo de mensagens retornadas"),
    outbox: AuraTransactionalOutbox = Depends(get_active_outbox),
) -> dict[str, Any]:
    """Lista mensagens persistidas na Outbox com filtro opcional por status."""
    items = await asyncio.to_thread(outbox.list_messages, status=status, limit=limit)
    return {
        "total": len(items),
        "limit": limit,
        "status_filter": status,
        "messages": items,
        "items": items,
    }


@router.post(
    "/outbox/flush",
    summary="Processa Imediatamente um Lote Pendente da Outbox (Fase 5)",
    tags=["AURA Transactional Outbox"],
)
async def outbox_flush_endpoint(
    req: OutboxFlushRequest | None = Body(default=None),
    limit: int = Query(default=20, ge=1, le=500, description="Limite do lote"),
    force: bool = Query(default=True, description="Ignorar agendamento de backoff para flush imediato"),
    outbox: AuraTransactionalOutbox = Depends(get_active_outbox),
) -> dict[str, Any]:
    """Drena imediatamente um lote pendente (process_pending_batch) e retorna o resumo."""
    eff_limit = req.limit if (req is not None and req.limit is not None) else limit
    eff_force = req.force if (req is not None and req.force is not None) else force
    batch_res = await asyncio.to_thread(
        outbox.process_pending_batch,
        limit=eff_limit,
        force=eff_force,
    )
    return {
        "status": "flushed",
        "success": True,
        **batch_res.to_dict(),
    }


@router.post(
    "/outbox/requeue-dlq",
    summary="Reenfileira Mensagens da Dead Letter Queue para PENDING (Fase 5)",
    tags=["AURA Transactional Outbox"],
)
async def outbox_requeue_dlq_endpoint(
    req: OutboxRequeueRequest | None = Body(default=None),
    limit: int = Query(default=50, ge=1, le=500, description="Limite de mensagens reabilitadas"),
    outbox: AuraTransactionalOutbox = Depends(get_active_outbox),
) -> dict[str, Any]:
    """Move mensagens com status DEAD_LETTER de volta para PENDING com attempt_count=0."""
    eff_limit = req.limit if (req is not None and req.limit is not None) else limit
    requeued = await asyncio.to_thread(outbox.requeue_dead_letters, limit=eff_limit)
    return {
        "status": "requeued",
        "success": True,
        "requeued_count": requeued,
        "requeued": requeued,
    }


# =============================================================================
# ENDPOINTS DE DADOS PUBLICOS E DADOS ABERTOS GOVERNAMENTAIS (PILAR 6 - FASE 5)
# =============================================================================

@router.get(
    "/public-data/health",
    summary="Health Check de Conectores e Circuit Breakers de Dados Publicos (Fase 5)",
    tags=["AURA Public Data"],
)
async def public_data_health_endpoint() -> dict[str, Any]:
    """
    Retorna o estado de saude operacional dos conectores publicos (ANP, CONFAZ, BACEN),
    o estado atual dos Circuit Breakers e a prontidao do repositorio local.
    """
    try:
        from core.integrations.public_data import (
            CircuitState,
            get_public_data_repository,
        )
        from scripts.sync_public_data import get_default_connectors

        repo = get_active_public_data_repo()
        anp_con, confaz_con, bacen_con = get_default_connectors()

        breakers = {
            "anp": {
                "state": anp_con.circuit_breaker.state.value,
                "consecutive_failures": anp_con.circuit_breaker.consecutive_failures,
                "failure_count": anp_con.circuit_breaker.consecutive_failures,
                "failure_threshold": anp_con.circuit_breaker.failure_threshold,
                "cooldown_seconds": anp_con.circuit_breaker.cooldown_seconds,
            },
            "confaz": {
                "state": confaz_con.circuit_breaker.state.value,
                "consecutive_failures": confaz_con.circuit_breaker.consecutive_failures,
                "failure_count": confaz_con.circuit_breaker.consecutive_failures,
                "failure_threshold": confaz_con.circuit_breaker.failure_threshold,
                "cooldown_seconds": confaz_con.circuit_breaker.cooldown_seconds,
            },
            "bacen": {
                "state": bacen_con.circuit_breaker.state.value,
                "consecutive_failures": bacen_con.circuit_breaker.consecutive_failures,
                "failure_count": bacen_con.circuit_breaker.consecutive_failures,
                "failure_threshold": bacen_con.circuit_breaker.failure_threshold,
                "cooldown_seconds": bacen_con.circuit_breaker.cooldown_seconds,
            },
        }

        all_closed = all(b["state"] == CircuitState.CLOSED.value for b in breakers.values())
        overall_status = "healthy" if all_closed else "degraded"

        return {
            "status": "success",
            "overall_status": overall_status,
            "circuit_breakers": breakers,
            "repository": {
                "status": "connected",
                "use_sqlite_fallback": getattr(repo, "use_sqlite", False),
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        logger.error(f"Erro ao consultar health de dados publicos: {exc}", exc_info=True)
        return {
            "status": "error",
            "overall_status": "unhealthy",
            "error": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        }


@router.get(
    "/public-data/telemetry",
    summary="Telemetria e Auditoria de Defasagem de Dados Publicos (Fase 5)",
    tags=["AURA Public Data"],
)
async def public_data_telemetry_endpoint(
    fonte: str | None = Query(None, description="Filtro opcional por fonte: anp, confaz, bacen"),
    limit: int = Query(default=20, ge=1, le=100, description="Limite de registros de historico"),
    max_staleness_days: int = Query(default=7, ge=1, le=30, description="Tolerancia maxima de dias"),
) -> dict[str, Any]:
    """
    Retorna o historico recente de sincronizacoes, data da ultima coleta por fonte
    e diagnostico de defasagem (staleness) com base no limiar configurado.
    """
    try:
        repo = get_active_public_data_repo()
        history = repo.get_telemetry_history(fonte=fonte, limit=limit)

        staleness_anp = repo.check_data_staleness(fonte="anp", max_age_days=max_staleness_days)
        staleness_confaz = repo.check_data_staleness(fonte="confaz", max_age_days=max_staleness_days)
        staleness_bacen = repo.check_data_staleness(fonte="bacen", max_age_days=max_staleness_days)

        latest_collections = {
            "anp": repo.get_latest_collection_date(fonte="anp"),
            "confaz": repo.get_latest_collection_date(fonte="confaz"),
            "bacen": repo.get_latest_collection_date(fonte="bacen"),
        }

        return {
            "status": "success",
            "total_records": len(history),
            "telemetry_history": history,
            "staleness": {
                "anp": staleness_anp,
                "confaz": staleness_confaz,
                "bacen": staleness_bacen,
            },
            "latest_collections": latest_collections,
            "max_staleness_days": max_staleness_days,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        logger.error(f"Erro ao consultar telemetria de dados publicos: {exc}", exc_info=True)
        return {
            "status": "error",
            "error": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        }


# =============================================================================
# FACTORY DA APLICAÇÃO STANDALONE
# =============================================================================

def create_aura_app(
    engine: AuraEngine | None = None,
    daemon: AuraProactiveDaemon | None = None,
    desktop_notifier: DesktopNotifier | None = None,
    outbox: AuraTransactionalOutbox | None = None,
    command_journal: AuraCommandJournal | None = None,
    public_data_repo: Any | None = None,
) -> FastAPI:
    """Cria e configura uma instância completa da aplicação FastAPI para a AURA."""
    if engine is not None:
        set_aura_engine(engine)
    if daemon is not None:
        set_proactive_daemon(daemon)
    if desktop_notifier is not None:
        set_desktop_notifier(desktop_notifier)
    if outbox is not None:
        set_transactional_outbox(outbox)
    if command_journal is not None:
        set_command_journal(command_journal)
    if public_data_repo is not None:
        set_public_data_repository(public_data_repo)

    elif (
        engine is not None
        and getattr(engine, "_session_memory", None) is not None
        and getattr(engine.session_memory, "db_path", None) == ":memory:"
        and not os.getenv("AURA_COMMAND_JOURNAL_DB_PATH")
        and _command_journal_instance is None
    ):
        _set_global_command_journal(AuraCommandJournal(db_path=":memory:"))

    app = FastAPI(
        title="AURA Core Engine API",
        description="Motor Cognitivo Headless Desacoplado para Postos de Combustíveis e PDV",
        version="1.0.0",
    )

    @app.on_event("startup")
    async def startup_proactive_daemon():
        if os.getenv("AURA_PROACTIVE_DAEMON_AUTOSTART", "0").lower() in ("1", "true", "yes"):
            d = get_proactive_daemon()
            await d.start()

    @app.on_event("shutdown")
    async def shutdown_proactive_daemon():
        d = get_proactive_daemon()
        await d.stop()

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
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|100\.\d{1,3}\.\d{1,3}\.\d{1,3}|.*\.ts\.net|marlonh-supwp)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Registra rotas da API
    app.include_router(router)

    @app.get(
        "/metrics",
        tags=["SRE Observability"],
        summary="Exportador Prometheus OpenMetrics (P2-4)",
    )
    async def root_prometheus_metrics_endpoint(
        engine_dep: AuraEngine = Depends(get_aura_engine),
    ) -> Response:
        """
        Endpoint canonico /metrics para scrape de servidores Prometheus e Grafana.
        """
        payload = engine_dep.telemetry.export_prometheus_metrics()
        return Response(
            content=payload,
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )


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

        @app.get("/icon.svg", include_in_schema=False)
        async def serve_icon():
            icon_file = web_dir / "icon.svg"
            if not icon_file.exists():
                icon_file = web_dir / "static" / "icon.svg"
            if icon_file.exists():
                return FileResponse(
                    str(icon_file),
                    media_type="image/svg+xml",
                )
            return Response(
                content='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" rx="100" fill="#07090e"/></svg>',
                media_type="image/svg+xml",
            )

        @app.get("/manifest.json", include_in_schema=False)
        async def serve_manifest():
            manifest_file = web_dir / "manifest.json"
            if manifest_file.exists():
                return FileResponse(
                    str(manifest_file),
                    media_type="application/manifest+json",
                )
            return Response(
                content="{}",
                media_type="application/manifest+json",
            )

        @app.get("/sw.js", include_in_schema=False)
        async def serve_service_worker():
            sw_file = web_dir / "sw.js"
            if sw_file.exists():
                return FileResponse(
                    str(sw_file),
                    media_type="application/javascript; charset=utf-8",
                    headers={"Service-Worker-Allowed": "/"},
                )
            return Response(
                content="// AURA Offline Service Worker",
                media_type="application/javascript; charset=utf-8",
            )

        @app.get("/", include_in_schema=False)
        @app.get("/dashboard", include_in_schema=False)
        @app.get("/index.html", include_in_schema=False)
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

