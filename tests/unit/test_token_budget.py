"""
Testes Unitarios do Modulo de Orcamento e Telemetria de Tokens da AURA.
Cobre calculo deterministico de precos (FiscalLLM), politicas orcamentarias,
evitacao de custos via cache local e telemetria SRE.
Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

import pytest
from core.token_budget import (
    DEFAULT_MODEL_PRICING,
    DEFAULT_USD_TO_BRL,
    TokenBudgetManager,
    calculate_avoided_cost,
    calculate_token_cost,
)
from core.telemetry import AuraSRETelemetry
from core.sanitizer import sanitize_erp_brand_names


def test_pricing_calculation_deterministic():
    """Valida conversao deterministica de tokens em custos USD e BRL."""
    # 1.000.000 tokens de input no gemini-2.5-flash = 0.10 USD
    calc_in = calculate_token_cost(
        model_name="gemini-2.5-flash",
        prompt_tokens=1_000_000,
        completion_tokens=0,
        usd_to_brl=5.80,
    )
    assert round(calc_in["cost_usd"], 4) == 0.1000
    assert round(calc_in["cost_brl"], 4) == 0.5800

    # 1.000.000 tokens de output no gemini-2.5-flash = 0.40 USD
    calc_out = calculate_token_cost(
        model_name="gemini-2.5-flash",
        prompt_tokens=0,
        completion_tokens=1_000_000,
        usd_to_brl=5.80,
    )
    assert round(calc_out["cost_usd"], 4) == 0.4000
    assert round(calc_out["cost_brl"], 4) == 2.3200


def test_avoided_cost_local_cache():
    """Valida calculo de economia gerada (avoided cost) por resposta via cache local."""
    avoided_brl = calculate_avoided_cost(
        model_name="gemini-2.5-flash",
        estimated_prompt_tokens=2000,
        estimated_completion_tokens=500,
        usd_to_brl=5.80,
    )
    assert avoided_brl > 0.0


def test_token_budget_manager_ledger_and_policy():
    """Valida persistencia SQLite do ledger de consumo e governanca orcamentaria."""
    manager = TokenBudgetManager(db_path=":memory:")

    # 1. Registra consumo inicial
    rec1 = manager.record_usage(
        session_id="sess_001",
        filial_id="posto_piloto",
        prompt_tokens=50_000,
        completion_tokens=10_000,
        model_name="gemini-2.5-flash",
        cached=False,
    )
    assert rec1["total_tokens"] == 60_000
    assert rec1["cost_brl"] > 0.0
    assert rec1["avoided_cost_brl"] == 0.0

    # 2. Registra consulta atendida em cache local (economia financeira)
    rec2 = manager.record_usage(
        session_id="sess_002",
        filial_id="posto_piloto",
        prompt_tokens=40_000,
        completion_tokens=5_000,
        model_name="gemini-2.5-flash",
        cached=True,
    )
    assert rec2["cost_brl"] == 0.0
    assert rec2["avoided_cost_brl"] > 0.0

    # 3. Consulta status do orcamento da filial
    status = manager.get_budget_status(filial_id="posto_piloto")
    assert status["filial_id"] == "posto_piloto"
    assert status["total_tokens_consumed"] == 60_000
    assert status["total_cost_brl"] > 0.0
    assert status["total_avoided_cost_brl"] > 0.0

    # 4. Atualiza meta personalizada de orcamento (R$ 5,00)
    updated = manager.update_budget_policy(
        filial_id="posto_piloto",
        monthly_budget_brl=5.0,
        alert_threshold_pct=50.0,
        enforcement_mode="smart_pacing",
    )
    assert updated["status"] == "updated"
    assert updated["policy"]["monthly_budget_brl"] == 5.0
    assert updated["policy"]["alert_threshold_pct"] == 50.0
    assert updated["policy"]["enforcement_mode"] == "smart_pacing"


def test_telemetry_token_usage_integration():
    """Valida integracao dos contadores de token com o coletor SRE AuraSRETelemetry."""
    tel = AuraSRETelemetry()
    tel.reset()

    tel.record_token_usage(
        prompt_tokens=1200,
        completion_tokens=400,
        model_name="gemini-2.5-flash",
        cost_brl=0.025,
        avoided_cost_brl=0.010,
        session_id="sess_sre_001",
    )

    metrics = tel.get_metrics_summary()
    assert "token_usage" in metrics
    t_usage = metrics["token_usage"]
    assert t_usage["total_tokens"] == 1600
    assert t_usage["prompt_tokens"] == 1200
    assert t_usage["completion_tokens"] == 400
    assert t_usage["total_cost_brl"] == 0.025
    assert t_usage["total_avoided_cost_brl"] == 0.010


def test_confluence_url_preservation_in_brand_sanitizer():
    """Valida que URLs oficiais do Confluence nao sofram corrupcao no sanitizador."""
    orig_url = "https://qualityautomacao.atlassian.net/wiki/spaces/webposto/pages/5865540"
    raw_text = f"Para saber como usar o webposto, consulte o manual em {orig_url} no seu navegador."
    cleaned = sanitize_erp_brand_names(raw_text)

    # A URL DEVE permanecer rigorosamente intacta (com 'spaces/webposto/pages')
    assert orig_url in cleaned
    # O texto fora da URL deve ter sido sanitizado para 'seu ERP'
    assert "como usar o seu ERP" in cleaned
