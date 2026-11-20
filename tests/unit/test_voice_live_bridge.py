"""
Testes unitarios da Fase 6: Voz Full-Duplex em Tempo Real (Gemini Live API <-> AURA).
Valida handshake setup, repasse de audio 16kHz/24kHz, interrupcao barge_in_clear,
execucao nao-bloqueante de toolCall + emissao de genui_card sanitizado,
fechamento automatico por inatividade (45s padrao) e registro em TokenBudgetManager.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import asyncio
import base64
import json
import sqlite3
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import core.voice_live_bridge as vlb
from core.aura_api import create_aura_app
from core.token_budget import TokenBudgetManager


class _FakeGeminiLiveUpstream:
    """Mock bidirecional em memoria simulando o WebSocket oficial da Gemini Live API."""

    def __init__(self, script_events: list[dict[str, Any]] | None = None) -> None:
        self.sent_messages: list[dict[str, Any]] = []
        self._incoming_queue: asyncio.Queue[str | None] = asyncio.Queue()
        self.closed = False
        self._script_events = list(script_events or [])
        self._setup_received = asyncio.Event()

    async def send(self, raw: str) -> None:
        payload = json.loads(raw)
        self.sent_messages.append(payload)
        if "setup" in payload and not self._setup_received.is_set():
            self._setup_received.set()
            await self._incoming_queue.put(json.dumps({"setupComplete": {}}))
            for ev in self._script_events:
                await self._incoming_queue.put(json.dumps(ev))

    async def recv(self) -> str | None:
        return await self._incoming_queue.get()

    async def push_server_event(self, event: dict[str, Any]) -> None:
        await self._incoming_queue.put(json.dumps(event))

    async def close(self) -> None:
        if not self.closed:
            self.closed = True
            await self._incoming_queue.put(None)


@pytest.fixture()
def isolated_voice_bridge(tmp_path, monkeypatch):
    """Configura TokenBudgetManager em tmp_path e limpa overrides ao finalizar."""
    budget_db = tmp_path / "voice_budget.db"
    budget_mgr = TokenBudgetManager(db_path=budget_db)
    vlb.set_voice_live_token_budget(budget_mgr)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-live-key")
    yield budget_mgr, budget_db
    vlb.set_voice_live_upstream_connector(None)
    vlb.set_voice_live_token_budget(None)


def test_constants_match_phase6_spec() -> None:
    """Garante constantes obrigatorias de audio, modelo, endpoint e travas de custo."""
    assert vlb.INACTIVITY_TIMEOUT_SECONDS == 45
    assert vlb.MAX_SESSION_SECONDS == 600
    assert vlb.INPUT_SAMPLE_RATE == 16000
    assert vlb.OUTPUT_SAMPLE_RATE == 24000
    assert "BidiGenerateContent" in vlb.build_gemini_live_ws_url("k123")


def test_handshake_audio_streaming_and_barge_in(isolated_voice_bridge) -> None:
    """
    Valida handshake setup com Gemini Live, envio de audio_chunk 16 kHz,
    recepcao de audio_out 24 kHz + transcricao sanitizada e evento barge_in_clear.
    """
    _, budget_db = isolated_voice_bridge
    sample_in = base64.b64encode(b"\x01\x00" * 160).decode("ascii")
    sample_out = base64.b64encode(b"\x02\x00" * 240).decode("ascii")

    upstream = _FakeGeminiLiveUpstream(
        script_events=[
            {
                "serverContent": {
                    "inputTranscription": {"text": "Qual a quebra do turno com CPF 123.456.789-00?"},
                    "modelTurn": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "audio/pcm;rate=24000",
                                    "data": sample_out,
                                }
                            }
                        ]
                    },
                    "outputTranscription": {"text": "A quebra de caixa do turno foi zero."},
                },
                "usageMetadata": {"promptTokenCount": 120, "responseTokenCount": 45},
            },
            {"serverContent": {"interrupted": True}},
        ]
    )

    async def _connector(_url: str):
        return upstream

    vlb.set_voice_live_upstream_connector(_connector)
    app = create_aura_app()
    client = TestClient(app)

    received: list[dict[str, Any]] = []
    with client.websocket_connect("/api/v1/voice/live?session_id=vs_test_1&filial_id=00001") as ws:
        # 1. Handshake session_ready
        ready = ws.receive_json()
        received.append(ready)
        assert ready["type"] == "session_ready"
        assert ready["input_sample_rate"] == 16000
        assert ready["output_sample_rate"] == 24000

        # 2. Envia audio PCM 16 kHz do cliente para AURA -> Gemini Live
        ws.send_json({"type": "audio_chunk", "pcm16_b64": sample_in, "sample_rate": 16000})

        # Coleta mensagens ate barge_in_clear
        for _ in range(8):
            ev = ws.receive_json()
            received.append(ev)
            if ev["type"] == "barge_in_clear":
                break

        # Encerra sessão pelo cliente
        ws.send_json({"type": "session_end"})
        closed_ev = ws.receive_json()
        assert closed_ev["type"] == "session_closed"
        assert closed_ev["reason"] == "client_session_end"

    # Valida frame setup enviado ao Gemini Live
    setup_frames = [m for m in upstream.sent_messages if "setup" in m]
    assert len(setup_frames) == 1
    assert setup_frames[0]["setup"]["generationConfig"]["responseModalities"] == ["AUDIO"]

    # Valida encaminhamento do audio PCM 16 kHz ao upstream
    media_frames = [m for m in upstream.sent_messages if "realtimeInput" in m]
    assert len(media_frames) == 1
    chunk = media_frames[0]["realtimeInput"]["mediaChunks"][0]
    assert chunk["mimeType"] == "audio/pcm;rate=16000"
    assert chunk["data"] == sample_in

    # Valida audio_out 24 kHz, transcricao com PII mascarado e barge_in_clear
    types = [e["type"] for e in received]
    assert "audio_out" in types
    assert "barge_in_clear" in types

    audio_out = next(e for e in received if e["type"] == "audio_out")
    assert audio_out["sample_rate"] == 24000
    assert audio_out["pcm16_b64"] == sample_out

    user_tr = next(e for e in received if e.get("type") == "transcript" and e.get("role") == "user")
    assert "123.456.789-00" not in user_tr["text"]

    # Valida registro no TokenBudgetManager
    with sqlite3.connect(budget_db) as conn:
        row = conn.execute(
            "SELECT prompt_tokens, completion_tokens, agent_role FROM aura_token_ledger WHERE session_id = ?",
            ("vs_test_1",),
        ).fetchone()
    assert row is not None
    assert row[0] == 120
    assert row[1] == 45
    assert row[2] == "voice_live_bridge"


def test_async_tool_call_sends_tool_response_and_genui_card(isolated_voice_bridge) -> None:
    """
    Valida que toolCall executa de forma assincrona (via to_thread), envia toolResponse
    para a Gemini Live API e emite genui_card valido com tool_call_id UUID v4 ao cliente.
    """
    upstream = _FakeGeminiLiveUpstream(
        script_events=[
            {
                "toolCall": {
                    "functionCalls": [
                        {
                            "id": "call-whatif-01",
                            "name": "simular_cenario_what_if",
                            "args": {
                                "scenario_type": "price_change",
                                "product_name": "Gasolina Comum",
                                "current_price": 5.89,
                                "unit_cost": 5.10,
                                "daily_volume": 8000,
                                "price_delta": 0.15,
                                "horizon_days": 30,
                            },
                        }
                    ]
                }
            }
        ]
    )

    async def _connector(_url: str):
        return upstream

    vlb.set_voice_live_upstream_connector(_connector)
    app = create_aura_app()
    client = TestClient(app)

    genui_event: dict[str, Any] | None = None
    with client.websocket_connect("/api/v1/voice/live?session_id=vs_tool_1") as ws:
        ready = ws.receive_json()
        assert ready["type"] == "session_ready"

        genui_event = ws.receive_json()
        ws.send_json({"type": "session_end"})
        closed_ev = ws.receive_json()
        assert closed_ev["type"] == "session_closed"

    assert genui_event is not None
    assert genui_event["type"] == "genui_card"
    assert genui_event["tool_name"] == "simular_cenario_what_if"

    envelope = genui_event["envelope"]
    assert envelope["component_name"] == "WhatIfSimulatorUI"
    assert uuid.UUID(envelope["tool_call_id"]).version == 4
    assert envelope["props"]["scenarios"]

    # Valida retorno toolResponse enviado ao upstream
    tool_resps = [m for m in upstream.sent_messages if "toolResponse" in m]
    assert len(tool_resps) == 1
    fn_resp = tool_resps[0]["toolResponse"]["functionResponses"][0]
    assert fn_resp["id"] == "call-whatif-01"
    assert fn_resp["name"] == "simular_cenario_what_if"
    assert "scenarios" in fn_resp["response"]["result"]


def test_inactivity_timeout_closes_session_automatically(isolated_voice_bridge, monkeypatch) -> None:
    """
    Valida que sessao ociosa sem chunks/fala e encerrada automaticamente por
    INACTIVITY_TIMEOUT_SECONDS (usando timeout reduzido no teste via monkeypatch).
    """
    monkeypatch.setattr(vlb, "INACTIVITY_TIMEOUT_SECONDS", 0.15)
    upstream = _FakeGeminiLiveUpstream(script_events=[])

    async def _connector(_url: str):
        return upstream

    vlb.set_voice_live_upstream_connector(_connector)
    app = create_aura_app()
    client = TestClient(app)

    with client.websocket_connect("/api/v1/voice/live?session_id=vs_idle_1") as ws:
        ready = ws.receive_json()
        assert ready["type"] == "session_ready"
        closed = ws.receive_json()
        assert closed["type"] == "session_closed"
        assert closed["reason"].startswith("inactivity_timeout_")


def test_websocket_auth_enforced_when_configured(isolated_voice_bridge, monkeypatch) -> None:
    """Garante bloqueio WS 1008 quando AURA_ENFORCE_ADMIN_AUTH=1 e chave ausente/invalida."""
    monkeypatch.setenv("AURA_ENFORCE_ADMIN_AUTH", "1")
    monkeypatch.setenv("AURA_API_KEY", "secret-aura-live")

    upstream = _FakeGeminiLiveUpstream()

    async def _connector(_url: str):
        return upstream

    vlb.set_voice_live_upstream_connector(_connector)
    app = create_aura_app()
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/api/v1/voice/live"):
        pass

    with client.websocket_connect(
        "/api/v1/voice/live?session_id=vs_auth_ok",
        headers={"X-API-Key": "secret-aura-live"},
    ) as ws:
        ready = ws.receive_json()
        assert ready["type"] == "session_ready"
        ws.send_json({"type": "client_interrupt"})
        barge_ev = ws.receive_json()
        assert barge_ev["type"] == "barge_in_clear"
        ws.send_json({"type": "session_end"})
        closed = ws.receive_json()
        assert closed["type"] == "session_closed"


def test_max_session_cap_closes_active_session(isolated_voice_bridge, monkeypatch) -> None:
    """
    Valida que sessao continua e encerrada ao atingir MAX_SESSION_SECONDS mesmo sem
    inatividade, mantendo a trava dura de custo.
    """
    monkeypatch.setattr(vlb, "MAX_SESSION_SECONDS", 0.18)
    monkeypatch.setattr(vlb, "INACTIVITY_TIMEOUT_SECONDS", 5.0)
    upstream = _FakeGeminiLiveUpstream(script_events=[])

    async def _connector(_url: str):
        return upstream

    vlb.set_voice_live_upstream_connector(_connector)
    app = create_aura_app()
    client = TestClient(app)

    with client.websocket_connect("/api/v1/voice/live?session_id=vs_cap_1") as ws:
        ready = ws.receive_json()
        assert ready["type"] == "session_ready"
        closed = ws.receive_json()
        assert closed["type"] == "session_closed"
        assert closed["reason"].startswith("max_session_")
