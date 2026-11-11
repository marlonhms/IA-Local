"""
Testes unitarios para os endpoints do Motor Preditivo Universal da AURA Partner API (Sprint 1).
Cobre os 6 segmentos de negocio (Varejo, SaaS/B2B, Clinicas, E-commerce, Logistica e Postos).
Regra estrita: Zero travessoes Unicode em todo o arquivo.
"""

import pytest
from fastapi.testclient import TestClient

from core.aura_api import create_aura_app
from core.partner_api import DEFAULT_PARTNER_API_KEY


@pytest.fixture
def client():
    app = create_aura_app()
    with TestClient(app) as c:
        yield c


def test_list_segments(client):
    headers = {"X-Partner-Key": DEFAULT_PARTNER_API_KEY}
    resp = client.get("/api/v1/partner/segments", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["count"] == 6
    segments = [s["segment"] for s in data["segments"]]
    assert "varejo" in segments
    assert "saas_b2b" in segments
    assert "saude_clinicas" in segments
    assert "ecommerce" in segments
    assert "logistica" in segments
    assert "postos_redes" in segments


def test_predictive_runout_critical_retail(client):
    headers = {"X-Partner-Key": DEFAULT_PARTNER_API_KEY}
    payload = {
        "segment": "varejo",
        "current_stock_or_capacity": 15.0,
        "burn_rate_per_hour": 3.0,
        "reorder_lead_time_hours": 24.0,
        "cost_per_unit_or_hour": 90.0,
        "urgency_price_delta_pct": 10.0,
        "resource_name": "Calcado Masculino Nobuck",
        "unit_label": "pares",
    }
    resp = client.post("/api/v1/partner/predictive-runout", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["segment"] == "varejo"
    assert data["hoursRemaining"] == 5.0
    assert data["daysRemaining"] == 0.2
    assert data["status"] == "critical"
    assert data["anticipationSavingsBrl"] > 0
    assert "esgota em 5.0h" in data["headline"]
    assert data["suggestedQuickAction"]["commandCode"] == "1"


def test_predictive_leakage_office_b2b(client):
    headers = {"X-Partner-Key": DEFAULT_PARTNER_API_KEY}
    payload = {
        "segment": "saas_b2b",
        "gross_monthly_revenue_brl": 150000.0,
        "unbilled_or_wasted_hours": 20.0,
        "hourly_rate_brl": 190.0,
        "cold_abandoned_leads_count": 10,
        "average_ticket_brl": 2500.0,
        "lead_to_sale_conversion_rate_pct": 20.0,
    }
    resp = client.post("/api/v1/partner/predictive-leakage", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["segment"] == "saas_b2b"
    assert data["totalMonthlyLeakageBrl"] == 8800.0
    assert data["annualizedLeakageBrl"] == 105600.0
    assert len(data["leakageBreakdown"]) == 2
    assert "Detector de Fuga" in data["headline"]
    assert data["stoppagePlan"]["projectedRecoveryBrl"] > 0


def test_predictive_rfm_churn_batch(client):
    headers = {"X-Partner-Key": DEFAULT_PARTNER_API_KEY}
    payload = {
        "segment": "saude_clinicas",
        "customers": [
            {
                "id": "c1",
                "name": "Maria Silva",
                "phone": "5527999990001",
                "last_purchase_days_ago": 70,
                "frequency_tier": "vip",
                "average_spend_brl": 800.0,
                "preferred_item_or_service": "Harmonizacao Facial",
            },
            {
                "id": "c2",
                "name": "Joao Pedro",
                "phone": "5527999990002",
                "last_purchase_days_ago": 15,
                "frequency_tier": "regular",
                "average_spend_brl": 300.0,
                "preferred_item_or_service": "Profilaxia",
            },
        ],
        "inactivity_threshold_days": 60,
    }
    resp = client.post("/api/v1/partner/predictive-rfm", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["totalCustomersAudited"] == 2
    assert data["atRiskCustomersCount"] == 1
    assert data["readyToSendBatch"][0]["customerId"] == "c1"
    assert "Maria Silva" in data["readyToSendBatch"][0]["customerName"]
    assert "Harmonizacao Facial" in data["readyToSendBatch"][0]["personalizedMessage"]
    assert data["projectedRecoverableRevenueBrl"] > 0


def test_segment_baseline_endpoint(client):
    headers = {"X-Partner-Key": DEFAULT_PARTNER_API_KEY}
    for seg in ["varejo", "saas_b2b", "saude_clinicas", "ecommerce", "logistica", "postos_redes"]:
        resp = client.get(f"/api/v1/partner/segments/{seg}/baseline", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["segment"] == seg
        assert "runOutTelemetry" in data
        assert "leakageTelemetry" in data
        assert "rfmTelemetry" in data


def test_morning_briefing_endpoint(client):
    headers = {"X-Partner-Key": DEFAULT_PARTNER_API_KEY}
    for seg in ["varejo", "saas_b2b", "postos_redes"]:
        payload = {
            "segment": seg,
            "manager_name": "Marlon Henrique",
            "business_name": f"Unidade Teste {seg.upper()}",
            "station_id": "posto_01",
        }
        resp = client.post("/api/v1/partner/morning-briefing", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["segment"] == seg
        assert "oralVoiceScript" in data
        assert len(data["oralVoiceScript"]) > 50
        assert "Marlon Henrique" in data["oralVoiceScript"]
        assert "whatsappExecutiveText" in data
        assert "RADAR COGNITIVO EXECUTIVO" in data["whatsappExecutiveText"]
        assert len(data["suggestedActions"]) == 3
        codes = [a["code"] for a in data["suggestedActions"]]
        assert "1" in codes
        assert "2" in codes
        assert "3" in codes


def test_quick_action_delegation(client):
    headers = {"X-Partner-Key": DEFAULT_PARTNER_API_KEY}
    payload = {
        "station_id": "posto_01",
        "action_type": "DELEGAR_EQUIPE",
        "option_key": "2",
        "actor_name": "Marlon Gestor",
    }
    resp = client.post("/api/v1/partner/stations/posto_01/quick-action", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["status"] == "DELEGATED"
    assert "DELEGADO" in data["confirmation_text"]
    assert "encaminhado" in data["confirmation_text"]


def test_quick_action_snooze_option_3(client):
    headers = {"X-Partner-Key": DEFAULT_PARTNER_API_KEY}
    payload = {
        "station_id": "posto_01",
        "action_type": "SILENCIAR_ALERTA",
        "option_key": "3",
        "actor_name": "Marlon Gestor",
    }
    resp = client.post("/api/v1/partner/stations/posto_01/quick-action", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["status"] == "SNOOZED"
    assert "silenciado" in data["confirmation_text"]
    assert "6 horas" in data["confirmation_text"]

