"""Testes Unitarios do Motor Universal de ROI para Varejo e Micro-Bots (AURA).

Valida:
1. Calculo deterministico de ROI para as 5 verticais do varejo.
2. Endpoint universal /api/v1/partner/stores/{store_id}/roi-diagnostic e retrocompatibilidade com stations.
3. Squad de Micro-Bots (RagMissTrackerBot, PartnerSyncContractBot, WeeklyRetailRoiDigestBot) e Zero-Token Gate.
Regra estrita: Zero travessoes Unicode em todo o arquivo.
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from fastapi.testclient import TestClient

from core.aura_api import create_aura_app
from core.ops_micro_bots import (
    PartnerSyncContractBot,
    RagMissTrackerBot,
    WeeklyRetailRoiDigestBot,
)
from core.partner_api import (
    PartnerStagingStore,
    get_partner_staging_store,
    set_partner_staging_store,
)
from core.retail_roi_engine import compute_universal_retail_roi

PARTNER_TEST_KEY = "teste-parceiro-chave-secreta-2026"


@pytest.fixture
def temp_staging_store(tmp_path) -> PartnerStagingStore:
    """Fixture que cria uma instancia temporaria e isolada do staging store."""
    staging_dir = tmp_path / "partner_staging"
    store = PartnerStagingStore(staging_dir=staging_dir)
    set_partner_staging_store(store)
    return store


@pytest.fixture
def partner_client(temp_staging_store: PartnerStagingStore, monkeypatch) -> TestClient:
    """Cliente HTTP com app FastAPI da AURA e chave padrao."""
    monkeypatch.setenv("AURA_PARTNER_API_KEY", PARTNER_TEST_KEY)
    app = create_aura_app()
    return TestClient(app)


def test_universal_retail_roi_all_five_verticals(temp_staging_store: PartnerStagingStore):
    """Valida o calculo deterministico dos 5 vetores para todas as verticais de varejo."""
    verticals = [
        ("retail_supermarket", "supermarket_retail", "Abrappe"),
        ("pharmacy_health", "pharmacy_retail", "SNGPC"),
        ("wholesale_distribution", "wholesale_distribution", "Expedicao"),
        ("autocenter_parts", "autocenter_retail", "Fluidos"),
        ("fuel_convenience", "fuel_retail", "ANP"),
    ]

    for pack_id, expected_vertical, expected_shield in verticals:
        res = compute_universal_retail_roi(
            store_id=f"loja_{pack_id}",
            staging_store=temp_staging_store,
            domain_pack=pack_id,
            monthly_subscription_brl=490.0,
        )

        assert res["domain_pack_id"] == pack_id
        assert res["vertical"] == expected_vertical
        assert expected_shield in res["regulatory_shield"]["compliance_target"]

        vectors = res["universal_vectors_brl"]
        assert len(vectors) == 5
        assert vectors["inventory_and_perishability_shrinkage_brl"] > 0
        assert vectors["pos_cancellations_and_rupture_brl"] > 0
        assert vectors["checkout_and_cash_discrepancy_brl"] > 0
        assert vectors["procurement_and_markdown_arbitrage_brl"] > 0
        assert vectors["working_capital_and_acquirer_erosion_brl"] > 0

        summary = res["summary"]
        assert summary["total_monthly_leakage_brl"] > 0
        assert summary["estimated_monthly_recovery_brl"] > 0
        assert summary["roi_multiple"] >= 3.0
        assert summary["guarantee_3x_met"] is True


def test_partner_universal_retail_store_endpoint(
    partner_client: TestClient,
    temp_staging_store: PartnerStagingStore,
):
    """Valida endpoint /stores/{store_id}/roi-diagnostic com autenticacao e multi-vertical."""
    headers = {
        "X-Partner-Key": PARTNER_TEST_KEY,
        "X-Station-ID": "supermercado_01",
    }

    # Chamada default (retail_supermarket)
    resp = partner_client.get(
        "/api/v1/partner/stores/supermercado_01/roi-diagnostic?monthly_fee=490.0",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["store_id"] == "supermercado_01"
    assert data["domain_pack_id"] == "retail_supermarket"
    assert data["summary"]["guarantee_3x_met"] is True
    assert "vocabulary_applied" in data
    assert "checkout" in data["vocabulary_applied"]["equipment"]

    # Chamada para farmacia
    headers["X-Station-ID"] = "drogaria_01"
    resp_pharm = partner_client.get(
        "/api/v1/partner/stores/drogaria_01/roi-diagnostic?domain_pack=pharmacy_health",
        headers=headers,
    )
    assert resp_pharm.status_code == 200
    data_pharm = resp_pharm.json()
    assert data_pharm["domain_pack_id"] == "pharmacy_health"
    assert "balcao_dispensacao" in data_pharm["vocabulary_applied"]["equipment"]

    # Chamada para autocenter
    headers["X-Station-ID"] = "box_01"
    resp_auto = partner_client.get(
        "/api/v1/partner/stores/box_01/roi-diagnostic?domain_pack=autocenter_parts",
        headers=headers,
    )
    assert resp_auto.status_code == 200
    data_auto = resp_auto.json()
    assert data_auto["domain_pack_id"] == "autocenter_parts"
    assert "elevador_box" in data_auto["vocabulary_applied"]["equipment"]


def test_partner_station_endpoint_retrocompatibility(
    partner_client: TestClient,
    temp_staging_store: PartnerStagingStore,
):
    """Comprova que endpoint existente /stations/{station_id}/roi-diagnostic continua funcionando intacto."""
    headers = {
        "X-Partner-Key": PARTNER_TEST_KEY,
        "X-Station-ID": "posto_01",
    }
    resp = partner_client.get(
        "/api/v1/partner/stations/posto_01/roi-diagnostic",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["station_id"] == "posto_01"
    assert "breakdown_brl" in data
    assert "summary" in data
    assert data["summary"]["guarantee_3x_met"] is True


def test_rag_miss_tracker_bot_zero_token_gate():
    """Valida Zero-Token Gate do RagMissTrackerBot quando nao ha misses no RAG."""
    bot = RagMissTrackerBot(score_threshold=0.45)

    # 1. Sem queries ou queries com score alto -> Zero-Token Gate ativado
    clean_logs = [
        {"query": "como emitir cupom", "rag_score": 0.88, "vertical": "retail_supermarket"},
        {"query": "fechar caixa", "rag_score": 0.92, "vertical": "retail_supermarket"},
    ]
    res_clean = bot.run(clean_logs)
    assert res_clean.zero_token_gate_triggered is True
    assert res_clean.llm_called is False
    assert res_clean.tokens_used == 0
    assert res_clean.status == "NO_MISS_DETECTED"

    # 2. Com query de baixo score -> identifica lacuna com custo zero de LLM
    gapped_logs = [
        {"query": "rejeicao sped registro c113", "rag_score": 0.32, "vertical": "fuel_retail"},
        {"query": "balanco sngpc erro lote", "rag_score": 0.28, "vertical": "pharmacy_retail"},
    ]
    res_gaps = bot.run(gapped_logs)
    assert res_gaps.zero_token_gate_triggered is False
    assert res_gaps.llm_called is False
    assert res_gaps.tokens_used == 0
    assert res_gaps.status == "GAPS_IDENTIFIED"
    assert "fuel_retail" in res_gaps.payload["gaps_by_vertical"]
    assert "pharmacy_retail" in res_gaps.payload["gaps_by_vertical"]


def test_partner_sync_contract_bot_zero_token_gate():
    """Valida Zero-Token Gate do PartnerSyncContractBot quando lote e compativel."""
    bot = PartnerSyncContractBot()

    # Lote limpo
    res_clean = bot.run(quarantined_count=0, warnings=[], station_id="station_clean")
    assert res_clean.zero_token_gate_triggered is True
    assert res_clean.llm_called is False
    assert res_clean.tokens_used == 0
    assert res_clean.status == "CONTRACT_CLEAN"

    # Lote com violacao
    res_warn = bot.run(
        quarantined_count=2,
        warnings=["Tanque 1 com capacidade negativa"],
        station_id="station_err",
    )
    assert res_warn.zero_token_gate_triggered is False
    assert res_warn.llm_called is False
    assert res_warn.tokens_used == 0
    assert res_warn.status == "CONTRACT_VIOLATION_DETECTED"
    assert len(res_warn.payload["corrective_guidance"]) >= 2


def test_weekly_retail_roi_digest_bot(temp_staging_store: PartnerStagingStore):
    """Valida geracao de relatorio semanal de ROI com zero tokens de LLM."""
    bot = WeeklyRetailRoiDigestBot()
    stores = ["supermercado_sp", "drogaria_rj", "distribuidora_mg"]

    digest = bot.run(
        store_ids=stores,
        staging_store=temp_staging_store,
        domain_pack="retail_supermarket",
        monthly_subscription_brl=490.0,
    )

    assert digest.bot_name == "WeeklyRetailRoiDigestBot"
    assert digest.llm_called is False
    assert digest.tokens_used == 0
    assert digest.status == "DIGEST_GENERATED"
    assert digest.payload["stores_count"] == 3
    assert digest.payload["total_net_roi_90d_brl"] > 0
    assert digest.payload["all_guarantees_met"] is True
