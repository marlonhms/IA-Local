"""
Testes Unitarios do Modulo de Transcricao de Voz (Groq Whisper Cloud).
Valida endpoints /api/v1/aura/voice/status e /api/v1/aura/voice/transcribe.
Zero travessoes em todo o arquivo.
"""

import os
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from core.aura_api import app

client = TestClient(app)


def test_voice_status_endpoint():
    """Valida retorno do status do servico de voz."""
    resp = client.get("/api/v1/aura/voice/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "service" in data
    assert "Groq Whisper" in data["service"]
    assert "status" in data
    assert "has_api_key" in data


def test_voice_transcribe_missing_api_key(monkeypatch):
    """Garante erro 503 explicativo caso a GROQ_API_KEY nao esteja presente."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    resp = client.post(
        "/api/v1/aura/voice/transcribe",
        headers={"Content-Type": "audio/webm"},
        content=b"\x00" * 500,
    )
    assert resp.status_code == 503
    assert "GROQ_API_KEY" in resp.json()["detail"]


def test_voice_transcribe_empty_audio(monkeypatch):
    """Garante erro 400 se o audio for vazio."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_mock_test_key_123456")
    resp = client.post(
        "/api/v1/aura/voice/transcribe",
        headers={"Content-Type": "audio/webm"},
        content=b"",
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_voice_transcribe_success_mock(monkeypatch):
    """Valida fluxo de sucesso com mock da API Groq Whisper."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_mock_test_key_123456")

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: {"text": "qual o volume do tanque dois"}

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        resp = client.post(
            "/api/v1/aura/voice/transcribe",
            headers={"Content-Type": "audio/webm"},
            content=b"\x1aE\xdf\xa3" + b"\x00" * 400,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["text"] == "qual o volume do tanque dois"
        assert "duration_ms" in data


def test_zero_unicode_dashes_in_voice_api():
    """Garante zero travessoes unicode em core/voice_api.py."""
    with open("ia-banco-local/core/voice_api.py", "r", encoding="utf-8") as f:
        txt = f.read()
    assert "\u2014" not in txt, "Em-dash encontrado em voice_api.py"
    assert "\u2013" not in txt, "En-dash encontrado em voice_api.py"
