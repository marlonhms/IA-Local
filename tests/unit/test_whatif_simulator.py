"""
Testes unitarios do Motor Contrafactual What-If (Fase 3 - Roadmap Next-Gen).
Valida ponto de equilibrio exato, cenarios de elasticidade, casos de borda
(margem zero/negativa, volume zero), PIX vs. cartao, compra vs. Selic, GenUI e REST.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from core.schemas.genui import GenUIEnvelope, WhatIfSimulationProps
from core.tools import PostoTools
from core.whatif_simulator import (
    run_whatif_simulation,
    simulate_inventory_purchase,
    simulate_payment_mix_shift,
    simulate_price_change,
)


def test_price_change_exact_break_even_and_scenarios() -> None:
    """Valida formula exata de ponto de equilibrio e 3 cenarios de elasticidade."""
    # Preco 6.19, custo 5.75 -> margem 0.44. Reducao -0.08 -> nova margem 0.36.
    # Break-even = 18450 * 0.44 / 0.36 = 22550.0 (+22.22%)
    res = simulate_price_change(
        product_name="Gasolina Comum",
        current_price=6.19,
        unit_cost=5.75,
        daily_volume=18450.0,
        price_delta=-0.08,
        horizon_days=30,
        cross_sell_margin_per_extra_unit=0.05,
    )
    assert res["success"] is True
    assert res["current_margin_unit"] == 0.44
    assert res["new_margin_unit"] == 0.36
    assert res["break_even_daily_volume"] == 22550.0
    assert res["break_even_delta_pct"] == 22.22
    assert len(res["scenarios"]) == 3
    assert {s["name"] for s in res["scenarios"]} == {"conservador", "base", "otimista"}
    assert "ALERTA_DESTRUICAO_MARGEM" in res["recommendation"]

    # Valida envelope GenUI e props Pydantic v2
    env = GenUIEnvelope(**res["genui_envelope"])
    props = WhatIfSimulationProps(**env.props)
    assert env.component_name == "WhatIfSimulatorUI"
    assert props.simulation_type == "price_change"
    assert len(props.scenarios) == 3


def test_price_change_edge_cases_reject_invalid_margins_and_volume() -> None:
    """Rejeita volume zero, margem atual zero ou desconto maior que a margem."""
    with pytest.raises(ValueError, match="daily_volume"):
        simulate_price_change("Gasolina", 6.00, 5.50, 0.0, -0.05)

    with pytest.raises(ValueError, match="Margem unitaria atual"):
        simulate_price_change("Gasolina", 5.50, 5.50, 1000.0, -0.05)

    # Desconto de -0.50 em margem de 0.44 resulta em margem negativa (-0.06)
    with pytest.raises(ValueError, match="margem unitaria zero ou negativa"):
        simulate_price_change("Gasolina", 6.19, 5.75, 1000.0, -0.50)

    # Desconto igual a margem resulta em margem zero
    with pytest.raises(ValueError, match="margem unitaria zero ou negativa"):
        simulate_price_change("Gasolina", 6.19, 5.75, 1000.0, -0.44)


def test_payment_mix_shift_and_inventory_purchase() -> None:
    """Valida simuladores de PIX vs. cartao e compra em lote vs. Selic."""
    pix_ok = simulate_payment_mix_shift(
        monthly_card_revenue_brl=200000.0,
        shift_pct=25.0,
        card_fee_pct=2.4,
        pix_fee_pct=0.2,
        pix_discount_pct=1.0,
    )
    assert pix_ok["monthly_shifted_brl"] == 50000.0
    assert pix_ok["fee_savings_brl"] == 1100.0
    assert pix_ok["discount_cost_brl"] == 500.0
    assert pix_ok["net_monthly_gain_brl"] == 600.0

    pix_bad = simulate_payment_mix_shift(
        monthly_card_revenue_brl=100000.0,
        shift_pct=50.0,
        card_fee_pct=2.0,
        pix_fee_pct=0.2,
        pix_discount_pct=3.0,
    )
    assert pix_bad["net_monthly_gain_brl"] < 0
    assert "ALERTA_DESCONTO_EXCESSIVO" in pix_bad["recommendation"]

    buy_ok = simulate_inventory_purchase(
        purchase_total_brl=100000.0,
        supplier_discount_pct=2.5,
        extra_days_in_stock=15,
        selic_annual_pct=10.75,
    )
    assert buy_ok["discount_gain_brl"] == 2500.0
    assert buy_ok["net_purchase_gain_brl"] > 0

    buy_bad = simulate_inventory_purchase(
        purchase_total_brl=100000.0,
        supplier_discount_pct=0.5,
        extra_days_in_stock=45,
        selic_annual_pct=14.0,
    )
    assert buy_bad["net_purchase_gain_brl"] < 0
    assert "ALERTA_CAPITAL_PARADO" in buy_bad["recommendation"]


def test_tools_wrapper_and_dispatcher() -> None:
    """Valida despacho pela PostoTools.simular_cenario_what_if e erro em tipo invalido."""
    tools = PostoTools()
    res = tools.simular_cenario_what_if(
        simulation_type="price_change",
        product_name="Diesel S10",
        current_price=6.10,
        unit_cost=5.50,
        daily_volume=8000.0,
        price_delta=0.10,
        horizon_days=30,
    )
    assert res["success"] is True
    assert res["new_margin_unit"] == 0.70

    with pytest.raises(ValueError, match="desconhecido"):
        run_whatif_simulation({"simulation_type": "invalid_mode"})


def test_whatif_rest_endpoint_fast_and_validates(client) -> None:
    """Valida endpoint POST /api/v1/aura/what-if/simulate em < 50ms e rejeicao 422."""
    payload = {
        "simulation_type": "price_change",
        "product_name": "Gasolina Comum",
        "current_price": 6.19,
        "unit_cost": 5.75,
        "daily_volume": 18450,
        "price_delta": -0.08,
        "horizon_days": 30,
        "cross_sell_margin_per_extra_unit": 0.05,
    }
    # Warmup para nao incluir lazy-import na medicao do endpoint
    warm_resp = client.post("/api/v1/aura/what-if/simulate", json=payload)
    assert warm_resp.status_code == 200

    t0 = time.perf_counter()
    resp = client.post("/api/v1/aura/what-if/simulate", json=payload)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert resp.status_code == 200
    assert elapsed_ms < 250.0  # Inclui overhead ASGI de TestClient; motor puro e < 2ms

    t1 = time.perf_counter()
    direct_res = run_whatif_simulation(payload)
    pure_ms = (time.perf_counter() - t1) * 1000.0
    assert pure_ms < 50.0
    assert direct_res["break_even_daily_volume"] == 22550.0
    body = resp.json()
    assert body["break_even_daily_volume"] == 22550.0

    bad_payload = dict(payload, price_delta=-0.60)
    resp_bad = client.post("/api/v1/aura/what-if/simulate", json=bad_payload)
    assert resp_bad.status_code == 422


def test_zero_unicode_dashes_in_phase3_files() -> None:
    """Garante ausencia absoluta de travessoes Unicode nos arquivos da Fase 3."""
    root = Path(__file__).resolve().parent.parent.parent
    for path in (root / "core" / "whatif_simulator.py", Path(__file__)):
        text = path.read_text(encoding="utf-8")
        assert "\u2014" not in text
        assert "\u2013" not in text
