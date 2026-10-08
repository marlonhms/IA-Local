"""
Endpoints HTTP de Integração FastAPI para o Motor Cognitivo AURA.
(Server-Sent Events / SSE, Invocação Direta de Intenções e Diagnóstico de Postos)

Conectores:
1. POST /api/v1/aura/chat: Suporte a streaming SSE em tempo real ou resposta síncrona JSON
2. POST /api/v1/aura/execute-intent: Invocação direta das 11 ferramentas analíticas (Run-Out, LMC, Turno...)
3. GET  /api/v1/aura/stations: Lista filiais homologadas e status de conexão ERP/pgvector
4. GET  /api/v1/aura/health: Health check de prontidão operacional
"""

from __future__ import annotations

import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query, Request, status
from fastapi.responses import StreamingResponse, FileResponse, Response
from datetime import datetime, timezone
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.aura_engine import (
    AuraEngine,
    AuraChunk,
    AuraResponse,
    StationStatus,
)
from core.schemas.genui import (
    ActionExecuteRequest,
    ActionVoucher,
    ActionAuditLogRecord,
    generate_action_voucher_signature,
)
from core.schemas.idempotency import generate_uuid4


# Router oficial da AURA
router = APIRouter(prefix="/api/v1/aura", tags=["AURA Core Engine"])

# Instância Singleton do Motor (pode ser injetada externamente)
_engine_instance: Optional[AuraEngine] = None


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


# =============================================================================
# PAYLOADS DE REQUISIÇÃO
# =============================================================================

class ChatRequest(BaseModel):
    """Contrato de entrada para conversação com a AURA."""
    query: str = Field(..., min_length=1, description="Pergunta ou instrução do usuário")
    session_id: Optional[str] = Field(default=None, description="Identificador da sessão para continuidade")
    stream: bool = Field(default=True, description="Se true, retorna Server-Sent Events (SSE)")
    tenant_id: Optional[str] = Field(default=None, description="Identificador do cliente/rede")
    filial_id: Optional[str] = Field(default=None, description="Identificador da filial do posto")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Contexto extra opcional injetado pelo chamador")


class ExecuteIntentRequest(BaseModel):
    """Contrato de invocação direta de ferramenta analítica sem prompt de LLM."""
    tool_name: str = Field(..., description="Nome da ferramenta (ex: previsao_tanques, lmc_anp, auditoria_turno)")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Parâmetros específicos da ferramenta")
    tenant_id: Optional[str] = Field(default=None, description="Identificador do cliente")
    filial_id: Optional[str] = Field(default=None, description="Identificador da filial")


# =============================================================================
# ROTAS HTTP
# =============================================================================

@router.post("/chat", summary="Chat Cognitivo com a AURA (SSE ou JSON)")
async def chat_endpoint(
    req: ChatRequest,
    engine: AuraEngine = Depends(get_aura_engine),
):
    """
    Envia pergunta para a AURA.
    - Se stream=true (padrão): Transmite resposta via Server-Sent Events (SSE).
    - Se stream=false: Retorna modelo estruturado consolidado AuraResponse.
    """
    if req.stream:
        async def event_generator():
            async for chunk in engine.ask_stream(
                query=req.query,
                context=req.context,
                session_id=req.session_id,
                tenant_id=req.tenant_id,
                filial_id=req.filial_id,
            ):
                yield chunk.to_sse()

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        response = await engine.ask(
            query=req.query,
            context=req.context,
            session_id=req.session_id,
            tenant_id=req.tenant_id,
            filial_id=req.filial_id,
        )
        return response


@router.post("/execute-intent", summary="Execução Direta de Ferramenta Analítica")
async def execute_intent_endpoint(
    req: ExecuteIntentRequest,
    engine: AuraEngine = Depends(get_aura_engine),
):
    """
    Invoca diretamente uma das 11 ferramentas analíticas (ex: Run-Out, LMC, Pista, Conciliação),
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
    payload: Dict[str, Any],
    operator_id: str,
) -> Dict[str, Any]:
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
            "confirmacao_erp": f"REP-{int(datetime.now(timezone.utc).timestamp())}",
        }

    # Absorcao de margem operacional
    if any(k in act_combined for k in ["absorver_margem", "absorver"]):
        return {
            "status": "APPROVED",
            "tipo": "ABSORCAO_MARGEM",
            "impacto_margem_pct": float(payload.get("impacto_margem_pct") or -0.5),
            "executado_por": operator_id,
            "confirmacao_erp": f"ABS-{int(datetime.now(timezone.utc).timestamp())}",
        }

    # Revisao de estrategia de precos (Benchmark)
    if any(k in act_combined for k in ["revisar_estrategia", "revisar"]):
        return {
            "status": "APPROVED",
            "tipo": "REVISAO_ESTRATEGIA",
            "escopo": payload.get("escopo") or "Precos e Margem Competitiva",
            "executado_por": operator_id,
            "confirmacao_erp": f"ESTR-{int(datetime.now(timezone.utc).timestamp())}",
        }

    # Auditoria de concorrencia no raio
    if any(k in act_combined for k in ["auditar_concorrencia", "concorrencia"]):
        return {
            "status": "APPROVED",
            "tipo": "AUDITORIA_CONCORRENCIA",
            "raio_km": float(payload.get("raio_km") or 3.0),
            "executado_por": operator_id,
            "confirmacao_erp": f"BENCH-{int(datetime.now(timezone.utc).timestamp())}",
        }

    # Abertura de chamado TEF (Fuga Financeira)
    if any(k in act_combined for k in ["abrir_chamado_tef", "tef", "chamado"]):
        return {
            "status": "APPROVED",
            "tipo": "CHAMADO_TEF",
            "terminal": payload.get("terminal") or "POS Sem Fio 03",
            "motivo": payload.get("motivo") or "Divergencia de liquidacao TEF",
            "executado_por": operator_id,
            "protocolo_chamado": f"TEF-{int(datetime.now(timezone.utc).timestamp())}",
            "confirmacao_erp": f"TEF-{int(datetime.now(timezone.utc).timestamp())}",
        }

    # Lancamento de campanha de incentivo a frentistas
    if any(k in act_combined for k in ["lancar_campanha_frentistas", "campanha", "frentistas"]):
        return {
            "status": "APPROVED",
            "tipo": "CAMPANHA_FRENTISTAS",
            "meta_conversao_pct": float(payload.get("meta_conversao_pct") or 25.0),
            "bonificacao_reais": float(payload.get("bonificacao_reais") or 1.50),
            "executado_por": operator_id,
            "confirmacao_erp": f"CAMP-{int(datetime.now(timezone.utc).timestamp())}",
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
            "confirmacao_erp": f"COMBO-{int(datetime.now(timezone.utc).timestamp())}",
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
            "data_programada": payload.get("data_programada") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "confirmacao_erp": f"PED-{int(datetime.now(timezone.utc).timestamp())}",
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
            "confirmacao_erp": f"SANGRIA-{int(datetime.now(timezone.utc).timestamp())}",
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
            "confirmacao_erp": f"PREC-{int(datetime.now(timezone.utc).timestamp())}",
        }

    # Reconciliacao / Homologacao de turno
    if any(k in act for k in ["conciliar", "conciliação", "conciliacao", "turno", "homologar"]):
        turno = payload.get("turno") or 1
        return {
            "status": "APPROVED",
            "tipo": "CONCILIACAO_TURNO",
            "turno": int(turno),
            "data": payload.get("data") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "score": float(payload.get("score") or 98.5),
            "status_fiscal": "HOMOLOGADO",
            "confirmacao_erp": f"HOMOL-{int(datetime.now(timezone.utc).timestamp())}",
        }

    # Padrao / Generico
    return {
        "status": "APPROVED",
        "tipo": action_name,
        "action_type": action_type,
        "executado_por": operator_id,
        "payload": payload,
        "confirmacao_erp": f"TX-{int(datetime.now(timezone.utc).timestamp())}",
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
    operator_role: Optional[str] = "gerente"
) -> Tuple[bool, int, str]:
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

    # Acoes de inspecao e navegacao sao permitidas para qualquer role (nivel >= 1)
    if action_type in ("inspection", "navigation"):
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
    summary="Execucao Transacional de Acoes GenUI (Human-in-the-Loop Gateway)"
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
    if request is not None and getattr(request, "client", None) is not None:
        client_ip = request.client.host

    # 1. Validacao estrita de idempotencia: se action_id ja existe, retorna voucher sem reprocessar
    existing_voucher = mem.get_action_voucher(req.action_id)
    if existing_voucher is not None:
        return existing_voucher

    action_name = req.action_name or "acao_executiva"
    payload = req.payload or {}
    operator = req.operator_id or "operador_01"
    op_role = req.operator_role or "gerente"

    # 2. F7-03: Validacao de permissao e perfil de operador (RBAC)
    is_authorized, min_level, reason = evaluate_action_permission(
        action_name=action_name,
        action_type=req.action_type,
        operator_role=op_role,
    )

    if not is_authorized:
        # F7-04: Registro de tentativa rejeitada na trilha de auditoria
        mem.save_audit_log(
            session_id=req.session_id,
            tool_call_id=req.tool_call_id,
            action_id=req.action_id,
            action_name=action_name,
            action_type=req.action_type,
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

    # 3. Execucao da rotina de negocio autorizada
    try:
        details = _dispatch_business_action(
            action_name=action_name,
            action_type=req.action_type,
            payload=payload,
            operator_id=operator,
        )
    except Exception as exc:
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
    ts_now = datetime.now(timezone.utc).isoformat()
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

    return voucher


@router.get(
    "/audit/logs",
    response_model=List[ActionAuditLogRecord],
    summary="Consulta da Trilha de Auditoria Transacional (OWASP LLM & Governanca)"
)
async def get_audit_logs_endpoint(
    session_id: Optional[str] = Query(None, description="Filtrar por session_id"),
    action_id: Optional[str] = Query(None, description="Filtrar por action_id"),
    operator_id: Optional[str] = Query(None, description="Filtrar por operator_id"),
    status: Optional[str] = Query(None, description="Filtrar por status (APPROVED, REJECTED_FORBIDDEN, FAILED)"),
    limit: int = Query(50, ge=1, le=500, description="Limite maximo de registros retornados"),
    engine: AuraEngine = Depends(get_aura_engine),
):
    """
    Consulta os registros duraveis de auditoria de acoes executadas ou rejeitadas pelo RBAC (F7-04).
    """
    logs = engine.get_audit_logs(
        session_id=session_id,
        action_id=action_id,
        operator_id=operator_id,
        status=status,
        limit=limit,
    )
    return logs



@router.get("/stations", response_model=List[StationStatus], summary="Diagnóstico e Status das Estações")
async def stations_endpoint(
    engine: AuraEngine = Depends(get_aura_engine),
):
    """
    Lista postos/filiais homologados e verifica o status da conexão do banco ERP (5433)
    e banco vetorial pgvector (5434), além de latência e saúde de observabilidade.
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
# FACTORY DA APLICAÇÃO STANDALONE
# =============================================================================

def create_aura_app(engine: Optional[AuraEngine] = None) -> FastAPI:
    """Cria e configura uma instância completa da aplicação FastAPI para a AURA."""
    if engine is not None:
        set_aura_engine(engine)

    app = FastAPI(
        title="AURA Core Engine API",
        description="Motor Cognitivo Headless Desacoplado para Postos de Combustíveis e PDV",
        version="1.0.0",
    )

    # Middleware CORS para integração local fluida
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Registra rotas da API
    app.include_router(router)

    # Montagem do Painel Web SPA Local da AURA
    web_dir = Path(__file__).resolve().parent.parent / "web"
    if web_dir.exists():
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
