"""
Bridge Full-Duplex de Voz em Tempo Real (Gemini Live API <-> AURA WebSocket).
Conecta cliente Android/Web via WS /api/v1/voice/live ao endpoint oficial
BidiGenerateContent da Gemini Live API com:
- Audio PCM 16-bit mono 16 kHz (entrada) e 24 kHz (saida)
- Corte instantaneo por interrupcao (barge_in_clear)
- Execucao nao-bloqueante de toolCall via asyncio.to_thread + GenUI simultaneo
- Travas de custo (INACTIVITY_TIMEOUT_SECONDS = 45, MAX_SESSION_SECONDS = 600)
  e registro de uso em TokenBudgetManager (core/token_budget.py)
- Zero GPU local e zero travessoes em todo o modulo.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from config.settings import AURA_API_KEY, GEMINI_API_KEY
from core.logger import logger
from core.sanitizer import sanitize_dict, sanitize_text
from core.schemas.genui import GenUIEnvelope
from core.token_budget import TokenBudgetManager

GEMINI_LIVE_WS_BASE = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
)
DEFAULT_GEMINI_LIVE_MODEL = os.getenv(
    "GEMINI_LIVE_MODEL",
    "models/gemini-2.0-flash-live-001",
)
INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 24000
INACTIVITY_TIMEOUT_SECONDS = 45
MAX_SESSION_SECONDS = 600

voice_live_router = APIRouter(tags=["AURA Live Voice Bridge"])

UpstreamConnector = Callable[[str], Awaitable[Any]]
ToolExecutor = Callable[[str, dict[str, Any]], dict[str, Any]]

_upstream_connector_override: UpstreamConnector | None = None
_token_budget_override: TokenBudgetManager | None = None


def set_voice_live_upstream_connector(connector: UpstreamConnector | None) -> None:
    """Permite injetar factory customizada de WebSocket upstream (ex: mocks em testes)."""
    global _upstream_connector_override
    _upstream_connector_override = connector


def set_voice_live_token_budget(manager: TokenBudgetManager | None) -> None:
    """Permite injetar TokenBudgetManager especifico para testes ou ambientes isolados."""
    global _token_budget_override
    _token_budget_override = manager


def build_gemini_live_ws_url(api_key: str) -> str:
    """Constroi a URL WSS autenticada do endpoint Gemini Live API."""
    clean_key = (api_key or "").strip()
    if not clean_key:
        return GEMINI_LIVE_WS_BASE
    sep = "&" if "?" in GEMINI_LIVE_WS_BASE else "?"
    return f"{GEMINI_LIVE_WS_BASE}{sep}key={clean_key}"


VOICE_LIVE_TOOL_DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "auditoria_turno",
        "description": "Audita fechamento de turno, caixa e conciliacao TEF/Dinheiro.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "data": {"type": "STRING", "description": "Data YYYY-MM-DD opcional."},
                "turno": {"type": "STRING", "description": "Identificador do turno opcional."},
            },
        },
    },
    {
        "name": "previsao_tanques",
        "description": "Consulta autonomia, estoque volumetrico e risco de ruptura dos tanques.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "filtro_combustivel": {
                    "type": "STRING",
                    "description": "Filtro opcional de combustivel.",
                },
            },
        },
    },
    {
        "name": "investigar_causa_raiz",
        "description": "Executa investigacao forense de causa-raiz (RCA) para quebras ou perdas.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "data": {"type": "STRING", "description": "Data YYYY-MM-DD opcional."},
                "turno": {"type": "STRING", "description": "Turno opcional."},
                "caixa_id": {"type": "STRING", "description": "Caixa ou PDV opcional."},
                "bico": {"type": "STRING", "description": "Bico ou bomba opcional."},
            },
        },
    },
    {
        "name": "simular_cenario_what_if",
        "description": (
            "Executa simulacao deterministica What-If de reajuste de preco, "
            "mix de pagamento ou compra antecipada."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "simulation_type": {
                    "type": "STRING",
                    "description": "price_change, payment_mix_shift ou inventory_purchase.",
                },
                "product_name": {"type": "STRING", "description": "Nome do produto."},
                "current_price": {"type": "NUMBER", "description": "Preco atual em BRL."},
                "unit_cost": {"type": "NUMBER", "description": "Custo unitario em BRL."},
                "daily_volume": {"type": "NUMBER", "description": "Volume medio diario."},
                "price_delta": {"type": "NUMBER", "description": "Variacao de preco em BRL."},
                "horizon_days": {"type": "INTEGER", "description": "Horizonte em dias."},
            },
            "required": ["product_name", "current_price", "unit_cost", "daily_volume", "price_delta"],
        },
    },
    {
        "name": "diagnosticar_grafo_causal",
        "description": "Rastreia cadeias causais entre anomalias LMC, tanques, NFe e fornecedores.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "anomaly_node_id": {"type": "STRING", "description": "No alvo da anomalia."},
                "time_window_hours": {"type": "INTEGER", "description": "Janela em horas."},
                "max_hops": {"type": "INTEGER", "description": "Profundidade maxima de saltos."},
            },
            "required": ["anomaly_node_id"],
        },
    },
    {
        "name": "consultar_roi_realizado",
        "description": "Consulta scorecard de ROI realizado das decisoes aplicadas.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "period_days": {"type": "INTEGER", "description": "Janela de dias."},
            },
        },
    },
]


def build_gemini_setup_payload(
    model: str | None = None,
    system_instruction: str | None = None,
    voice_name: str = "Aoede",
) -> dict[str, Any]:
    """Constroi o payload inicial de handshake setup para Gemini Live API."""
    eff_model = (model or DEFAULT_GEMINI_LIVE_MODEL).strip()
    if not eff_model.startswith("models/"):
        eff_model = f"models/{eff_model}"

    instruction_text = system_instruction or (
        "Voce e a AURA, assistente executiva de voz em tempo real para postos de combustiveis "
        "e varejo no Brasil. Responda em portugues brasileiro de forma direta, objetiva e "
        "natural para audio. Nunca invente numeros nem exponha CPF, CNPJ ou dados pessoais. "
        "Use ferramentas analiticas antes de afirmar metricas operacionais."
    )

    return {
        "setup": {
            "model": eff_model,
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": voice_name,
                        }
                    }
                },
            },
            "systemInstruction": {
                "parts": [{"text": instruction_text}],
            },
            "tools": [
                {"functionDeclarations": VOICE_LIVE_TOOL_DECLARATIONS},
            ],
            "inputAudioTranscription": {},
            "outputAudioTranscription": {},
        }
    }


def _parse_sample_rate(mime_type: str, default_rate: int = OUTPUT_SAMPLE_RATE) -> int:
    """Extrai rate=NNNN de mimeType audio/pcm;rate=24000 quando informado."""
    lower = (mime_type or "").lower()
    if "rate=" not in lower:
        return default_rate
    tail = lower.split("rate=", 1)[1]
    digits = []
    for ch in tail:
        if ch.isdigit():
            digits.append(ch)
        else:
            break
    if not digits:
        return default_rate
    try:
        return int("".join(digits))
    except ValueError as exc:
        logger.debug("[AURA VoiceLive] Sample rate invalido em '%s': %s", mime_type, exc)
        return default_rate


async def _default_upstream_connect(url: str) -> Any:
    """Abre conexao WebSocket upstream via pacote websockets."""
    import websockets

    return await websockets.connect(url, open_timeout=15.0)


def _sanitize_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitiza um dicionario contra PII retornando apenas o payload limpo."""
    cleaned, _ = sanitize_dict(data)
    return cleaned


def execute_voice_tool_sync(
    tool_name: str,
    args: dict[str, Any] | None = None,
    tenant_id: str = "default_tenant",
    filial_id: str = "00001",
) -> dict[str, Any]:
    """
    Executa de forma sincrona e read-only/analitica uma ferramenta solicitada pelo Gemini Live.
    Projetada para rodar dentro de asyncio.to_thread(...) sem bloquear o streaming de audio.
    """
    norm = (tool_name or "").strip().lower().replace("-", "_").replace(" ", "_")
    params = dict(args or {})

    try:
        if norm in ("simular_cenario_what_if", "what_if", "whatif"):
            from core.whatif_simulator import run_whatif_simulation

            if "simulation_type" not in params and "scenario_type" in params:
                params["simulation_type"] = params["scenario_type"]
            res = run_whatif_simulation(params)
            return _sanitize_payload(res)

        if norm in ("diagnosticar_grafo_causal", "causal_graph_trace", "grafo_causal"):
            from core.causal_graph import AuraCausalGraph

            graph = AuraCausalGraph()
            anomaly_id = str(
                params.get("anomaly_node_id") or params.get("target_node") or "ANOMALY:latest"
            )
            res = graph.trace_root_cause(
                tenant_id=tenant_id,
                anomaly_node_id=anomaly_id,
                max_hops=int(params.get("max_hops", 4)),
                time_window_hours=int(params.get("time_window_hours", 72)),
            )
            return _sanitize_payload(res)

        if norm in ("consultar_roi_realizado", "roi_realizado"):
            from core.outcome_tracker import OutcomeTracker

            tracker = OutcomeTracker()
            scorecard = tracker.get_realized_roi_scorecard(
                period_days=int(params.get("period_days", params.get("days", 30))),
                tenant_id=tenant_id,
            )
            res = scorecard.model_dump(mode="json") if hasattr(scorecard, "model_dump") else dict(scorecard)
            return _sanitize_payload(res)

        # Ferramentas canonicas do posto via PostoTools (execucao sincrona read-only)
        from core.tools import PostoTools

        posto = PostoTools()
        if norm in ("auditoria_turno", "auditar_fechamento_turno", "fechamento_turno"):
            raw = posto.auditar_fechamento_turno(
                data=params.get("data"),
                turno=params.get("turno"),
            )
        elif norm in ("previsao_tanques", "prever_esgotamento_tanques", "tanques"):
            raw = posto.prever_esgotamento_tanques(
                filtro_combustivel=params.get("filtro_combustivel") or params.get("combustivel"),
            )
        elif norm in ("investigar_causa_raiz", "investigar_causa_raiz_turno", "rca"):
            raw = posto.investigar_causa_raiz_turno(
                data=params.get("data"),
                turno=params.get("turno"),
                caixa_id=params.get("caixa_id"),
                bico=params.get("bico"),
            )
        else:
            raw = {
                "status": "unsupported_tool",
                "tool_name": norm,
                "message": f"Ferramenta '{norm}' nao habilitada no modo voz ao vivo.",
            }
        return _sanitize_payload(raw if isinstance(raw, dict) else {"data": raw})
    except Exception as exc:  # noqa: BLE001
        logger.warning("[AURA VoiceLive] Falha ao executar tool '%s': %s", norm, exc)
        return {
            "status": "error",
            "tool_name": norm,
            "error": sanitize_text(str(exc)),
        }


def build_voice_genui_card(
    tool_name: str,
    tool_result: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Converte o resultado sanitizado de uma toolCall em um GenUIEnvelope validado
    para renderizacao simultanea na UI enquanto a AURA fala.
    """
    if not isinstance(tool_result, dict) or tool_result.get("status") == "error":
        return None

    sanitized_result = _sanitize_payload(tool_result)
    existing_env = sanitized_result.get("genui_envelope")
    if isinstance(existing_env, dict) and existing_env.get("component_name"):
        return existing_env

    norm = (tool_name or "").strip().lower().replace("-", "_").replace(" ", "_")
    call_uuid = str(uuid.uuid4())

    # Tenta mapeamento canonico existente no AuraEngine primeiro
    try:
        from core.aura_engine import (
            GENUI_COMPONENT_REGISTRY_MAP,
            build_canonical_genui_envelope,
        )

        if norm in GENUI_COMPONENT_REGISTRY_MAP:
            summary_text = str(
                sanitized_result.get("resumo_executivo")
                or sanitized_result.get("summary")
                or f"Resultado em tempo real de {norm}."
            )
            env = build_canonical_genui_envelope(
                intencao=norm,
                tool_call_id=call_uuid,
                resultado_bruto=sanitized_result,
                executive_summary=sanitize_text(summary_text),
            )
            if env is not None:
                return env.model_dump(mode="json")
    except Exception as exc:  # noqa: BLE001
        logger.debug("[AURA VoiceLive] Fallback para envelope modular GenUI (%s): %s", norm, exc)

    # Envelopes dedicados das Fases 2, 3, 4 ou card modular seguro
    if norm in ("simular_cenario_what_if", "what_if", "whatif"):
        component_name = "WhatIfSimulatorUI"
        client_component = "WhatIfSimulatorUI"
        summary = str(
            sanitized_result.get("recommendation")
            or f"Simulacao What-If de {sanitized_result.get('product_name', 'produto')}."
        )
    elif norm in ("consultar_roi_realizado", "roi_realizado"):
        component_name = "RealizedRoiScorecardUI"
        client_component = "RealizedRoiScorecardUI"
        summary = f"ROI realizado acumulado de R$ {sanitized_result.get('total_realized_brl', 0.0):.2f}."
    elif norm in ("diagnosticar_grafo_causal", "causal_graph_trace", "grafo_causal"):
        component_name = "render_RootCauseAnalysisUI"
        client_component = "RootCauseAnalysisWidget"
        paths = sanitized_result.get("paths") or []
        summary = f"Grafo causal rastreador: {len(paths)} caminho(s) provavel(is) encontrado(s)."
    else:
        component_name = "render_GenerativeModularCardUI"
        client_component = "GenerativeModularCardUI"
        summary = f"Atualizacao ao vivo de {norm}."

    envelope = GenUIEnvelope(
        schema_version="1.0",
        tool_call_id=call_uuid,
        component_name=component_name,
        client_component=client_component,
        intent=norm,
        executive_summary=sanitize_text(summary)[:240],
        props=sanitized_result,
        actions=[],
        ttl_seconds=300,
    )
    return envelope.model_dump(mode="json")


@dataclass
class VoiceLiveSessionStats:
    """Resumo consolidado da sessao full-duplex de voz ao vivo."""

    session_id: str
    tenant_id: str
    filial_id: str
    model: str
    duration_seconds: float
    close_reason: str
    audio_chunks_in: int = 0
    audio_chunks_out: int = 0
    tool_calls_count: int = 0
    barge_in_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


def _authorize_websocket(websocket: WebSocket) -> bool:
    """
    Aplica a politica dual de autenticacao (Carbon Core P0.1) para conexoes WebSocket:
    - Valida X-API-Key, Authorization Bearer ou query api_key via hmac.compare_digest;
    - Exige API Key obrigatoria para IPs externos (LAN/WAN);
    - Valida Origin anti-CSRF e cookie HttpOnly 'aura_local_session' para localhost.
    """
    from core.aura_api import authorize_admin_request

    client_host = websocket.client.host if websocket.client else None
    query_key = websocket.query_params.get("api_key")
    allowed, _, _ = authorize_admin_request(
        headers=websocket.headers,
        cookies=websocket.cookies,
        client_host=client_host,
        query_api_key=str(query_key) if query_key else None,
    )
    return allowed


class VoiceLiveBridgeSession:
    """
    Orquestrador assincrono bidirecional de uma sessao de voz Full-Duplex.
    """

    def __init__(
        self,
        client_ws: WebSocket,
        session_id: str | None = None,
        tenant_id: str = "default_tenant",
        filial_id: str = "00001",
        api_key: str | None = None,
        model: str | None = None,
        inactivity_timeout_seconds: float | None = None,
        max_session_seconds: float | None = None,
        upstream_connector: UpstreamConnector | None = None,
        tool_executor: ToolExecutor | None = None,
        token_budget_manager: TokenBudgetManager | None = None,
    ) -> None:
        self.client_ws = client_ws
        self.session_id = session_id or f"voice_{uuid.uuid4().hex[:12]}"
        self.tenant_id = tenant_id or "default_tenant"
        self.filial_id = filial_id or "00001"
        self.api_key = (api_key if api_key is not None else os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY).strip()
        self.model = (model or DEFAULT_GEMINI_LIVE_MODEL).strip()
        self.inactivity_timeout_seconds = float(
            INACTIVITY_TIMEOUT_SECONDS if inactivity_timeout_seconds is None else inactivity_timeout_seconds
        )
        self.max_session_seconds = float(
            MAX_SESSION_SECONDS if max_session_seconds is None else max_session_seconds
        )

        self._upstream_connector = upstream_connector or _upstream_connector_override or _default_upstream_connect
        self._tool_executor = tool_executor
        self._token_budget = token_budget_manager or _token_budget_override

        self._upstream_ws: Any = None
        self._started_at = time.monotonic()
        self._last_activity = self._started_at
        self._stop_event = asyncio.Event()
        self._send_client_lock = asyncio.Lock()
        self._send_upstream_lock = asyncio.Lock()
        self._close_reason = "completed"
        self._tool_tasks: set[asyncio.Task[Any]] = set()

        self._audio_chunks_in = 0
        self._audio_chunks_out = 0
        self._tool_calls_count = 0
        self._barge_in_count = 0
        self._prompt_tokens = 0
        self._completion_tokens = 0

    def _touch_activity(self) -> None:
        self._last_activity = time.monotonic()

    def _request_stop(self, reason: str) -> None:
        if not self._stop_event.is_set():
            self._close_reason = reason
            self._stop_event.set()

    async def _send_to_client(self, payload: dict[str, Any]) -> None:
        async with self._send_client_lock:
            try:
                await self.client_ws.send_json(payload)
            except Exception:  # noqa: BLE001
                self._request_stop("client_disconnected")

    async def _send_to_upstream(self, payload: dict[str, Any]) -> None:
        if self._upstream_ws is None:
            return
        raw = json.dumps(payload, ensure_ascii=False)
        async with self._send_upstream_lock:
            try:
                await self._upstream_ws.send(raw)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[AURA VoiceLive] Falha ao enviar ao upstream: %s", exc)
                self._request_stop("upstream_send_error")

    async def _dispatch_tool_call(self, fn_call: dict[str, Any]) -> None:
        call_id = str(fn_call.get("id") or uuid.uuid4().hex[:8])
        fn_name = str(fn_call.get("name") or "")
        args = fn_call.get("args") or {}
        if not isinstance(args, dict):
            args = {}

        self._tool_calls_count += 1
        self._touch_activity()

        if self._tool_executor is not None:
            result = await asyncio.to_thread(self._tool_executor, fn_name, args)
        else:
            result = await asyncio.to_thread(
                execute_voice_tool_sync,
                fn_name,
                args,
                self.tenant_id,
                self.filial_id,
            )

        sanitized = _sanitize_payload(
            result if isinstance(result, dict) else {"data": result}
        )

        # Responde primeiro ao Gemini Live para a AURA continuar a narracao sem travar
        await self._send_to_upstream(
            {
                "toolResponse": {
                    "functionResponses": [
                        {
                            "id": call_id,
                            "name": fn_name,
                            "response": {"result": sanitized},
                        }
                    ]
                }
            }
        )

        # Emite card GenUI simultaneo para a UI renderizar enquanto a AURA fala
        card = build_voice_genui_card(fn_name, sanitized)
        if card is not None:
            await self._send_to_client(
                {
                    "type": "genui_card",
                    "tool_name": fn_name,
                    "envelope": card,
                }
            )

    async def _handle_upstream_payload(self, data: dict[str, Any]) -> None:
        if "setupComplete" in data:
            await self._send_to_client(
                {
                    "type": "session_ready",
                    "session_id": self.session_id,
                    "model": self.model,
                    "input_sample_rate": INPUT_SAMPLE_RATE,
                    "output_sample_rate": OUTPUT_SAMPLE_RATE,
                }
            )

        usage = data.get("usageMetadata")
        if isinstance(usage, dict):
            self._prompt_tokens = max(
                self._prompt_tokens,
                int(usage.get("promptTokenCount") or 0),
            )
            self._completion_tokens = max(
                self._completion_tokens,
                int(usage.get("responseTokenCount") or usage.get("candidatesTokenCount") or 0),
            )

        server_content = data.get("serverContent")
        if isinstance(server_content, dict):
            if server_content.get("interrupted") is True:
                self._barge_in_count += 1
                await self._send_to_client({"type": "barge_in_clear"})

            in_tr = server_content.get("inputTranscription")
            if isinstance(in_tr, dict) and in_tr.get("text"):
                self._touch_activity()
                await self._send_to_client(
                    {
                        "type": "transcript",
                        "role": "user",
                        "text": sanitize_text(str(in_tr["text"])),
                    }
                )

            out_tr = server_content.get("outputTranscription")
            if isinstance(out_tr, dict) and out_tr.get("text"):
                await self._send_to_client(
                    {
                        "type": "transcript",
                        "role": "model",
                        "text": sanitize_text(str(out_tr["text"])),
                    }
                )

            model_turn = server_content.get("modelTurn")
            if isinstance(model_turn, dict):
                for part in model_turn.get("parts") or []:
                    if not isinstance(part, dict):
                        continue
                    inline = part.get("inlineData")
                    if isinstance(inline, dict):
                        mime = str(inline.get("mimeType") or "")
                        b64_data = inline.get("data")
                        if mime.lower().startswith("audio/pcm") and b64_data:
                            self._audio_chunks_out += 1
                            await self._send_to_client(
                                {
                                    "type": "audio_out",
                                    "pcm16_b64": str(b64_data),
                                    "sample_rate": _parse_sample_rate(mime, OUTPUT_SAMPLE_RATE),
                                }
                            )
                    elif part.get("text"):
                        await self._send_to_client(
                            {
                                "type": "transcript",
                                "role": "model",
                                "text": sanitize_text(str(part["text"])),
                            }
                        )

        tool_call = data.get("toolCall")
        if isinstance(tool_call, dict):
            for fn_call in tool_call.get("functionCalls") or []:
                if isinstance(fn_call, dict) and fn_call.get("name"):
                    task = asyncio.create_task(self._dispatch_tool_call(fn_call))
                    self._tool_tasks.add(task)
                    task.add_done_callback(self._tool_tasks.discard)

    async def _client_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                msg = await self.client_ws.receive()
            except WebSocketDisconnect:
                self._request_stop("client_disconnected")
                break
            except Exception:  # noqa: BLE001
                self._request_stop("client_receive_error")
                break

            msg_type = msg.get("type")
            if msg_type == "websocket.disconnect":
                self._request_stop("client_disconnected")
                break

            raw_bytes = msg.get("bytes")
            raw_text = msg.get("text")

            if raw_bytes is not None:
                self._touch_activity()
                self._audio_chunks_in += 1
                b64 = base64.b64encode(raw_bytes).decode("ascii")
                await self._send_to_upstream(
                    {
                        "realtimeInput": {
                            "mediaChunks": [
                                {
                                    "mimeType": f"audio/pcm;rate={INPUT_SAMPLE_RATE}",
                                    "data": b64,
                                }
                            ]
                        }
                    }
                )
                continue

            if raw_text is None:
                continue

            try:
                payload = json.loads(raw_text)
            except json.JSONDecodeError:
                continue

            if not isinstance(payload, dict):
                continue

            ev_type = str(payload.get("type") or "").strip().lower()
            if ev_type == "audio_chunk":
                pcm_b64 = str(payload.get("pcm16_b64") or "").strip()
                if not pcm_b64:
                    continue
                sample_rate = int(payload.get("sample_rate") or INPUT_SAMPLE_RATE)
                self._touch_activity()
                self._audio_chunks_in += 1
                await self._send_to_upstream(
                    {
                        "realtimeInput": {
                            "mediaChunks": [
                                {
                                    "mimeType": f"audio/pcm;rate={sample_rate}",
                                    "data": pcm_b64,
                                }
                            ]
                        }
                    }
                )
            elif ev_type == "text_input":
                text_val = str(payload.get("text") or "").strip()
                if text_val:
                    self._touch_activity()
                    await self._send_to_upstream(
                        {
                            "clientContent": {
                                "turns": [{"role": "user", "parts": [{"text": text_val}]}],
                                "turnComplete": True,
                            }
                        }
                    )
            elif ev_type == "client_interrupt":
                self._touch_activity()
                self._barge_in_count += 1
                await self._send_to_client({"type": "barge_in_clear"})
            elif ev_type == "session_end":
                self._request_stop("client_session_end")
                break

    async def _upstream_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                raw_msg = await self._upstream_ws.recv()
            except Exception:  # noqa: BLE001
                self._request_stop("upstream_closed")
                break

            if raw_msg is None:
                self._request_stop("upstream_closed")
                break

            if isinstance(raw_msg, bytes):
                raw_msg = raw_msg.decode("utf-8", errors="replace")

            try:
                data = json.loads(raw_msg)
            except json.JSONDecodeError:
                continue

            if isinstance(data, dict):
                await self._handle_upstream_payload(data)

    async def _watchdog_loop(self) -> None:
        inact_limit = max(0.05, self.inactivity_timeout_seconds)
        max_limit = max(0.1, self.max_session_seconds)
        poll_interval = min(0.25, inact_limit / 4.0)

        inact_label = (
            f"inactivity_timeout_{int(self.inactivity_timeout_seconds)}s"
            if float(self.inactivity_timeout_seconds).is_integer()
            else f"inactivity_timeout_{self.inactivity_timeout_seconds:.2f}s"
        )
        max_label = (
            f"max_session_{int(self.max_session_seconds)}s"
            if float(self.max_session_seconds).is_integer()
            else f"max_session_{self.max_session_seconds:.2f}s"
        )

        while not self._stop_event.is_set():
            await asyncio.sleep(poll_interval)
            now = time.monotonic()
            if (now - self._started_at) >= max_limit:
                self._request_stop(max_label)
                break
            if (now - self._last_activity) >= inact_limit:
                self._request_stop(inact_label)
                break

    def _record_session_budget(self, duration_seconds: float) -> None:
        """Registra duracao e tokens da sessao Live no TokenBudgetManager."""
        try:
            mgr = self._token_budget or TokenBudgetManager()
            eff_prompt = self._prompt_tokens
            eff_completion = self._completion_tokens
            # Fallback conservador caso Gemini Live nao envie usageMetadata antes do fechamento
            if eff_prompt == 0 and (self._audio_chunks_in > 0 or duration_seconds >= 1.0):
                eff_prompt = max(1, round(duration_seconds * 25))
            if eff_completion == 0 and self._audio_chunks_out > 0:
                eff_completion = max(1, round(self._audio_chunks_out * 15))

            mgr.record_usage(
                session_id=self.session_id,
                filial_id=self.filial_id,
                tenant_id=self.tenant_id,
                model_name="gemini-2.5-flash",
                prompt_tokens=eff_prompt,
                completion_tokens=eff_completion,
                agent_role="voice_live_bridge",
                intent_category=f"voice_live_{round(duration_seconds)}s",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[AURA VoiceLive] Nao foi possivel registrar uso no TokenBudget: %s", exc)

    async def run(self) -> VoiceLiveSessionStats:
        """Executa o ciclo completo da sessao full-duplex de voz ao vivo."""
        await self.client_ws.accept()

        # Quando usa o conector padrao real, exige GEMINI_API_KEY
        uses_default_upstream = self._upstream_connector is _default_upstream_connect
        if uses_default_upstream and not self.api_key:
            await self._send_to_client(
                {
                    "type": "session_closed",
                    "reason": "missing_gemini_api_key",
                    "duration_seconds": 0.0,
                }
            )
            try:
                await self.client_ws.close(code=status.WS_1011_INTERNAL_ERROR)
            except Exception as exc:  # noqa: BLE001
                logger.debug("[AURA VoiceLive] Falha ao fechar WS apos missing key: %s", exc)
            return VoiceLiveSessionStats(
                session_id=self.session_id,
                tenant_id=self.tenant_id,
                filial_id=self.filial_id,
                model=self.model,
                duration_seconds=0.0,
                close_reason="missing_gemini_api_key",
            )

        url = build_gemini_live_ws_url(self.api_key)
        worker_tasks: list[asyncio.Task[Any]] = []
        try:
            self._upstream_ws = await self._upstream_connector(url)
            setup_payload = build_gemini_setup_payload(model=self.model)
            await self._send_to_upstream(setup_payload)

            worker_tasks = [
                asyncio.create_task(self._client_loop()),
                asyncio.create_task(self._upstream_loop()),
                asyncio.create_task(self._watchdog_loop()),
            ]

            await self._stop_event.wait()
        except Exception as exc:  # noqa: BLE001
            logger.error("[AURA VoiceLive] Erro ao conectar no Gemini Live: %s", exc)
            self._request_stop("upstream_connect_error")
        finally:
            duration = round(max(0.0, time.monotonic() - self._started_at), 3)

            for task in list(self._tool_tasks):
                if not task.done():
                    task.cancel()
            for task in worker_tasks:
                if not task.done():
                    task.cancel()
            if worker_tasks:
                await asyncio.gather(*worker_tasks, return_exceptions=True)

            if self._close_reason not in ("client_disconnected",):
                await self._send_to_client(
                    {
                        "type": "session_closed",
                        "reason": self._close_reason,
                        "duration_seconds": duration,
                    }
                )

            if self._upstream_ws is not None:
                try:
                    await self._upstream_ws.close()
                except Exception as exc:  # noqa: BLE001
                    logger.debug("[AURA VoiceLive] Falha ao fechar upstream: %s", exc)

            if self._close_reason not in ("client_disconnected",):
                try:
                    await self.client_ws.close()
                except Exception as exc:  # noqa: BLE001
                    logger.debug("[AURA VoiceLive] Falha ao fechar client WS: %s", exc)

            self._record_session_budget(duration)

        return VoiceLiveSessionStats(
            session_id=self.session_id,
            tenant_id=self.tenant_id,
            filial_id=self.filial_id,
            model=self.model,
            duration_seconds=duration,
            close_reason=self._close_reason,
            audio_chunks_in=self._audio_chunks_in,
            audio_chunks_out=self._audio_chunks_out,
            tool_calls_count=self._tool_calls_count,
            barge_in_count=self._barge_in_count,
            prompt_tokens=self._prompt_tokens,
            completion_tokens=self._completion_tokens,
        )


@voice_live_router.websocket("/api/v1/voice/live")
async def voice_live_websocket_endpoint(
    websocket: WebSocket,
    session_id: str | None = None,
    tenant_id: str = "default_tenant",
    filial_id: str = "00001",
    model: str | None = None,
) -> None:
    """
    Endpoint WebSocket Full-Duplex para conversacao de voz em tempo real via Gemini Live API.
    """
    if not _authorize_websocket(websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    bridge = VoiceLiveBridgeSession(
        client_ws=websocket,
        session_id=session_id,
        tenant_id=tenant_id,
        filial_id=filial_id,
        model=model,
    )
    await bridge.run()
