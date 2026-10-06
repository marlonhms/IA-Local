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
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import StreamingResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.aura_engine import (
    AuraEngine,
    AuraChunk,
    AuraResponse,
    StationStatus,
)

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

    return app
