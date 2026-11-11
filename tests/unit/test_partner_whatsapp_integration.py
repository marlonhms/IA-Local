"""
Testes Unitarios e de Integracao: Conector AURA Local + Painel WhatsApp CRM (Fases 1 e 2).
Valida:
1. Flexibilizacao de autenticacao de parceiro (X-Partner-Key, X-Tenant-Key, X-Aura-Key).
2. Endpoint unificado /api/v1/partner/stations/{station_id}/whatsapp-snapshot.
3. Despachador transacional dispatch_painel_whatsapp_event integrado a Outbox SQLite WAL.
4. Integracao das funcoes de notificacao (turno, tanque, sangria, lmc) com o Painel WhatsApp.

Regra estrita: Zero travessoes Unicode em todo o arquivo.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from core.aura_api import app
from core.outbox import AuraTransactionalOutbox
from core.partner_api import PartnerStagingStore, get_partner_staging_store
from core.webhooks import (
    AlertaLMCCompliancePayload,
    AlertaSangriaPayload,
    AlertaTanquePayload,
    TurnoResumoPayload,
    dispatch_painel_whatsapp_event,
    notify_alerta_lmc,
    notify_alerta_sangria,
    notify_alerta_tanque,
    notify_fechamento_turno,
)


@pytest.fixture
def mock_staging_store(tmp_path):
    """Cria uma instancia isolada de staging store para testes."""
    return PartnerStagingStore(staging_dir=tmp_path / "staging")


@pytest.fixture
def test_client(mock_staging_store):
    """Cliente de teste com injecao do staging store isolado."""
    app.dependency_overrides[get_partner_staging_store] = lambda: mock_staging_store
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def memory_outbox():
    """Instancia de Outbox em memoria para testes sem persistencia em disco."""
    return AuraTransactionalOutbox(db_path=":memory:")


def test_verify_partner_auth_with_tenant_and_aura_keys(test_client):
    """Valida que verify_partner_auth aceita X-Tenant-Key e X-Aura-Key."""
    # 1. Sem autenticacao -> 401
    res_no_auth = test_client.get("/api/v1/partner/stations/posto_01/status")
    assert res_no_auth.status_code == 401

    # 2. Com X-Partner-Key valida -> 200
    res_partner_key = test_client.get(
        "/api/v1/partner/stations/posto_01/status",
        headers={"X-Partner-Key": "aura-partner-default-key", "X-Station-ID": "posto_01"},
    )
    assert res_partner_key.status_code == 200

    # 3. Com X-Tenant-Key valida -> 200
    res_tenant_key = test_client.get(
        "/api/v1/partner/stations/posto_01/status",
        headers={"X-Tenant-Key": "whsec_partner_fuel_bi_2026", "X-Station-ID": "posto_01"},
    )
    assert res_tenant_key.status_code == 200

    # 4. Com X-Aura-Key valida -> 200
    res_aura_key = test_client.get(
        "/api/v1/partner/stations/posto_01/status",
        headers={"X-Aura-Key": "whsec_partner_fuel_bi_2026", "X-Station-ID": "posto_01"},
    )
    assert res_aura_key.status_code == 200


def test_whatsapp_snapshot_endpoint_structure(test_client, mock_staging_store):
    """Valida o contrato e formato de resposta do endpoint /stations/{id}/whatsapp-snapshot."""
    # Sincroniza dados minimos em staging para a estacao posto_teste
    mock_staging_store.save_raw_data(
        "posto_teste",
        {
            "tanques": [
                {
                    "codtan": "1",
                    "prl_ds_produto_lmc": "Gasolina Comum",
                    "volume": 8500.0,
                    "capacidade": 15000.0,
                    "iniciodia": 9000.0,
                }
            ],
            "fechabomba": [
                {
                    "codbom": "1",
                    "encltsa": 1000.0,
                    "enclts": 1500.0,
                    "preco": 5.89,
                    "encdinh": 2945.0,
                }
            ],
        },
    )

    response = test_client.get(
        "/api/v1/partner/stations/posto_teste/whatsapp-snapshot",
        headers={"X-Partner-Key": "aura-partner-default-key", "X-Station-ID": "posto_teste"},
    )

    assert response.status_code == 200
    data = response.json()

    # Valida campos compativeis com LiveStationKpiSnapshot
    assert data["success"] is True
    assert data["stationCode"] == "posto_teste"
    assert "Posto POSTO_TESTE" in data["stationName"]
    assert data["source"] == "local_bi_tunnel"
    assert isinstance(data["litragemDia"], (int, float))
    assert isinstance(data["margemMediaLitro"], (int, float))
    assert isinstance(data["mixAditivadaPct"], (int, float))
    assert isinstance(data["conversaoConvenienciaPct"], (int, float))
    assert isinstance(data["alertaAtivo"], str)
    assert isinstance(data["recomendacaoConsultiva"], str)
    assert "whatsapp_formatted_text" in data
    assert "summary" in data
    assert "detailed_telemetry" in data


@pytest.mark.anyio
async def test_dispatch_painel_whatsapp_event_success(memory_outbox):
    """Valida despacho bem-sucedido via Transactional Outbox para o Painel WhatsApp."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '{"success": true, "mode": "authenticated_live"}'

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        res = await dispatch_painel_whatsapp_event(
            event_type="ANOMALIA_OPERACIONAL_ESTOQUE",
            filial_id="posto_01",
            metrics={
                "periodo": "Hoje",
                "indicadorPrincipal": "Autonomia Critica",
                "variacaoPct": -15.0,
                "detalheOperacional": "Tanque 01 com 12h de autonomia.",
            },
            aura_raw_context={"tanque_id": "1", "combustivel": "Gasolina"},
            phone="5511999998888",
            events_url="http://test-server:3000/api/aura/events",
            outbox=memory_outbox,
            idempotency_key="test_snap_001",
        )

        assert res.success is True
        assert res.service == "painel_whatsapp"
        assert res.status_code == 200
        assert res.outbox_status == "DELIVERED"
        assert mock_post.called

        # Inspeciona os headers e body enviados
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["headers"]["X-Station-ID"] == "posto_01"
        assert call_kwargs["json"]["eventType"] == "ANOMALIA_OPERACIONAL_ESTOQUE"
        assert call_kwargs["json"]["clientPhone"] == "5511999998888"


@pytest.mark.anyio
async def test_dispatch_painel_whatsapp_event_retry_on_failure(memory_outbox):
    """Valida persistencia na Outbox como FAILED_RETRY quando o servidor do CRM falha."""
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.text = "Service Unavailable"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        res = await dispatch_painel_whatsapp_event(
            event_type="ALERTA_MARGEM_RENTABILIDADE",
            filial_id="posto_01",
            metrics={"indicadorPrincipal": "Margem", "variacaoPct": -5.0, "detalheOperacional": "Queda."},
            phone="5511999998888",
            events_url="http://test-server:3000/api/aura/events",
            outbox=memory_outbox,
            idempotency_key="test_fail_002",
        )

        assert res.success is False
        assert res.service == "painel_whatsapp"
        assert res.status_code == 503
        assert res.outbox_status == "FAILED_RETRY"

        # Verifica que a mensagem esta salva no SQLite WAL
        saved_msg = memory_outbox.get_message(res.outbox_message_id)
        assert saved_msg is not None
        assert saved_msg.status == "FAILED_RETRY"
        assert saved_msg.attempt_count == 1


@pytest.mark.anyio
async def test_notify_fechamento_turno_integrates_painel_whatsapp(memory_outbox):
    """Valida que notify_fechamento_turno despacha para n8n, Evolution e Painel WhatsApp."""
    payload = TurnoResumoPayload(
        turno_id="TURNO_1",
        filial_id="posto_01",
        faturamento_total=15420.50,
        litros_vendidos=2610.0,
        quebra_caixa=0.0,
        status_conciliacao="CONCILIADO",
        bicos_analisados=8,
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"success": true}'

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        results = await notify_fechamento_turno(
            payload=payload,
            phone="5511999998888",
            webhook_url="http://mock-n8n:5678/webhook",
            outbox=memory_outbox,
            idempotency_key="test_turno_integrated_001",
        )

        assert "n8n" in results
        assert "evolution" in results
        assert "painel_whatsapp" in results
        assert results["painel_whatsapp"]["success"] is True


def test_partner_quick_action_approve_fuel_order(test_client):
    """Valida aprovacao de pedido de combustivel via resposta '1' do WhatsApp."""
    resp = test_client.post(
        "/api/v1/partner/stations/posto_01/quick-action",
        headers={"X-Partner-Key": "aura-partner-default-key", "X-Station-ID": "posto_01"},
        json={
            "action_type": "PROGRAMAR_PEDIDO_COMBUSTIVEL",
            "option_key": "1",
            "voucher_id": "vch_diesel_99",
            "actor_phone": "5511999998888",
            "parameters": {"tanque_id": "2", "litros": 10000.0},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["action_executed"] == "PROGRAMAR_PEDIDO_COMBUSTIVEL"
    assert data["status"] == "COMPLETED"
    assert "Pedido de combustivel confirmado com sucesso" in data["confirmation_text"]
    assert data["voucher_id"] == "vch_diesel_99"


def test_partner_quick_action_snooze_alert(test_client):
    """Valida silenciamento de alerta operacional via resposta '2' do WhatsApp."""
    resp = test_client.post(
        "/api/v1/partner/stations/posto_01/quick-action",
        headers={"X-Partner-Key": "aura-partner-default-key", "X-Station-ID": "posto_01"},
        json={
            "action_type": "TANQUE_CRITICO",
            "option_key": "2",
            "actor_phone": "5511999998888",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["action_executed"] == "SILENCIAR_ALERTA"
    assert data["status"] == "SNOOZED"
    assert "silenciado temporariamente por 6 horas" in data["confirmation_text"]


def test_partner_memory_sync_and_get_facts(test_client):
    """Valida ciclo completo de sincronizacao de memoria entre WhatsApp e AURA."""
    # 1. Sincroniza um novo apelido e regra do posto
    sync_resp = test_client.post(
        "/api/v1/partner/stations/posto_01/memory-sync",
        headers={"X-Partner-Key": "aura-partner-default-key", "X-Station-ID": "posto_01"},
        json={
            "category": "apelido_produto",
            "key": "v-power",
            "content": "No posto chamamos Gasolina Aditivada de V-Power.",
            "confidence": 0.98,
            "status": "ativo",
            "source": "whatsapp_mural",
            "metadata": {"informado_por": "Gerente Carlos"},
        },
    )
    assert sync_resp.status_code == 200
    sync_data = sync_resp.json()
    assert sync_data["success"] is True
    assert sync_data["category"] == "apelido_produto"
    assert sync_data["key"] == "v-power"

    # 2. Consulta fatos ativos da estacao
    get_resp = test_client.get(
        "/api/v1/partner/stations/posto_01/memory-facts",
        headers={"X-Partner-Key": "aura-partner-default-key", "X-Station-ID": "posto_01"},
    )
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["success"] is True
    assert get_data["count"] >= 1

    keys = [f["chave"] for f in get_data["facts"]]
    assert "v-power" in keys



@pytest.mark.anyio
async def test_notify_alerta_tanque_integrates_painel_whatsapp(memory_outbox):
    """Valida que notify_alerta_tanque despacha para o Painel WhatsApp."""
    payload = AlertaTanquePayload(
        tanque_id="2",
        combustivel="Diesel S10",
        filial_id="posto_01",
        volume_atual_litros=2100.0,
        capacidade_total_litros=15000.0,
        autonomia_horas=12.5,
        previsao_esgotamento="2026-11-05 23:30",
        urgencia="ALTA",
        compartimentos_5k=2,
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"success": true}'

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        results = await notify_alerta_tanque(
            payload=payload,
            phone="5511999998888",
            webhook_url="http://mock-n8n:5678/webhook",
            outbox=memory_outbox,
            idempotency_key="test_tanque_integrated_001",
        )

        assert "painel_whatsapp" in results
        assert results["painel_whatsapp"]["success"] is True


def test_partner_quick_action_approve_fuel_order(test_client):
    """Valida aprovacao de pedido de combustivel via resposta '1' do WhatsApp."""
    resp = test_client.post(
        "/api/v1/partner/stations/posto_01/quick-action",
        headers={"X-Partner-Key": "aura-partner-default-key", "X-Station-ID": "posto_01"},
        json={
            "action_type": "PROGRAMAR_PEDIDO_COMBUSTIVEL",
            "option_key": "1",
            "voucher_id": "vch_diesel_99",
            "actor_phone": "5511999998888",
            "parameters": {"tanque_id": "2", "litros": 10000.0},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["action_executed"] == "PROGRAMAR_PEDIDO_COMBUSTIVEL"
    assert data["status"] == "COMPLETED"
    assert "Pedido de combustivel confirmado com sucesso" in data["confirmation_text"]
    assert data["voucher_id"] == "vch_diesel_99"


def test_partner_quick_action_snooze_alert(test_client):
    """Valida silenciamento de alerta operacional via resposta '2' do WhatsApp."""
    resp = test_client.post(
        "/api/v1/partner/stations/posto_01/quick-action",
        headers={"X-Partner-Key": "aura-partner-default-key", "X-Station-ID": "posto_01"},
        json={
            "action_type": "TANQUE_CRITICO",
            "option_key": "2",
            "actor_phone": "5511999998888",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["action_executed"] == "SILENCIAR_ALERTA"
    assert data["status"] == "SNOOZED"
    assert "silenciado temporariamente por 6 horas" in data["confirmation_text"]


def test_partner_memory_sync_and_get_facts(test_client):
    """Valida ciclo completo de sincronizacao de memoria entre WhatsApp e AURA."""
    # 1. Sincroniza um novo apelido e regra do posto
    sync_resp = test_client.post(
        "/api/v1/partner/stations/posto_01/memory-sync",
        headers={"X-Partner-Key": "aura-partner-default-key", "X-Station-ID": "posto_01"},
        json={
            "category": "apelido_produto",
            "key": "v-power",
            "content": "No posto chamamos Gasolina Aditivada de V-Power.",
            "confidence": 0.98,
            "status": "ativo",
            "source": "whatsapp_mural",
            "metadata": {"informado_por": "Gerente Carlos"},
        },
    )
    assert sync_resp.status_code == 200
    sync_data = sync_resp.json()
    assert sync_data["success"] is True
    assert sync_data["category"] == "apelido_produto"
    assert sync_data["key"] == "v-power"

    # 2. Consulta fatos ativos da estacao
    get_resp = test_client.get(
        "/api/v1/partner/stations/posto_01/memory-facts",
        headers={"X-Partner-Key": "aura-partner-default-key", "X-Station-ID": "posto_01"},
    )
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["success"] is True
    assert get_data["count"] >= 1

    keys = [f["chave"] for f in get_data["facts"]]
    assert "v-power" in keys

