"""
Testes Unitarios: Esteira de Webhooks Assincronos para WhatsApp (P1-7).
Valida contratos Pydantic, formatadores de mensagens executivas,
despachadores HTTP com mock e endpoints de integracao n8n/Evolution API.
Zero travessoes em todo o arquivo.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from core.aura_api import create_aura_app
from core.aura_engine import AuraEngine, AuraSessionMemory
from core.webhooks import (
    AlertaTanquePayload,
    TurnoResumoPayload,
    dispatch_n8n_webhook,
    format_alerta_tanque_whatsapp_message,
    format_turno_whatsapp_message,
)


@pytest.mark.unit
def test_format_turno_whatsapp_message():
    """Valida a formatacao executiva do card de resumo de turno."""
    payload = TurnoResumoPayload(
        turno_id="Turno Manha (06h - 14h)",
        filial_id="posto_central_01",
        data="2026-10-13",
        faturamento_total=45850.75,
        litros_vendidos=7620.4,
        quebra_caixa=0.0,
        status_conciliacao="CONCILIADO",
        bicos_analisados=16,
    )
    msg = format_turno_whatsapp_message(payload)
    assert "AURA | FECHAMENTO DE TURNO" in msg
    assert "posto_central_01" in msg
    assert "45.\u200b850,75" in msg
    assert "7.\u200b620,4 L" in msg
    assert "CONCILIADO" in msg


@pytest.mark.unit
def test_format_alerta_tanque_whatsapp_message():
    """Valida a formatacao executiva de alerta de ruptura de combustivel."""
    payload = AlertaTanquePayload(
        tanque_id="TQ-01",
        combustivel="GASOLINA ADITIVADA",
        filial_id="posto_central_01",
        volume_atual_litros=1800.0,
        capacidade_total_litros=15000.0,
        autonomia_horas=4.5,
        previsao_esgotamento="Hoje as 18:30",
        urgencia="ALTA",
    )
    msg = format_alerta_tanque_whatsapp_message(payload)
    assert "AURA | ALERTA OPERACIONAL DE TANQUES" in msg
    assert "GASOLINA ADITIVADA" in msg
    assert "4.5 horas" in msg
    assert "ALTA" in msg


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dispatch_n8n_webhook_graceful_missing_url(monkeypatch):
    """Valida retorno seguro quando N8N_WEBHOOK_URL nao esta definida."""
    monkeypatch.setattr("core.webhooks.N8N_WEBHOOK_URL", "")
    res = await dispatch_n8n_webhook(event_type="test", payload={"foo": "bar"})
    assert res.success is False
    assert "nao definida" in res.error


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dispatch_n8n_webhook_mocked():
    """Valida despacho HTTP com sucesso para webhook n8n via mock."""
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"message": "Workflow started"}'

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await dispatch_n8n_webhook(
            event_type="turno_fechamento",
            payload={"teste": 123},
            webhook_url="http://mock-n8n:5678/webhook/test",
        )
        assert res.success is True
        assert res.status_code == 200


@pytest.mark.unit
def test_webhooks_fastapi_endpoints(monkeypatch):
    """Valida os endpoints FastAPI de webhooks com autenticacao."""
    test_key = "webhook_secret_key_2026"
    monkeypatch.setenv("AURA_API_KEY", test_key)
    monkeypatch.setenv("AURA_ENFORCE_ADMIN_AUTH", "1")

    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(session_memory=mem)
    app = create_aura_app(engine=engine)
    client = TestClient(app)

    payload_turno = {
        "turno_id": "T1",
        "filial_id": "posto_01",
        "data": "2026-10-13",
        "faturamento_total": 12000.0,
        "litros_vendidos": 2000.0,
        "quebra_caixa": 0.0,
        "status_conciliacao": "CONCILIADO",
        "bicos_analisados": 8,
    }

    # Sem auth -> 401
    resp_unauth = client.post("/api/v1/aura/webhooks/turno-fechamento", json=payload_turno)
    assert resp_unauth.status_code == 401

    # Com auth -> 200
    resp_auth = client.post(
        "/api/v1/aura/webhooks/turno-fechamento",
        json=payload_turno,
        headers={"X-API-Key": test_key},
    )
    assert resp_auth.status_code == 200
    assert resp_auth.json()["status"] == "dispatched"
