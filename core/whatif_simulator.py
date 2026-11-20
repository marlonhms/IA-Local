"""
Motor Contrafactual What-If - Gemeo Digital Financeiro (Fase 3 - Roadmap Next-Gen).
Simula variacoes de preco com elasticidade, migracao de meios de pagamento (Cartao -> PIX)
e compra em lote vs. custo de carregamento Selic de forma 100% deterministica em Python
(CPU-only, < 50ms, zero consumo de tokens LLM em sliders interativos).
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import uuid
from contextlib import suppress
from typing import Any

from core.schemas.genui import (
    GenUIEnvelope,
    WhatIfScenarioOutcome,
    WhatIfSimulationProps,
)

DEFAULT_SELIC_ANNUAL_PCT = 10.75
DEFAULT_ELASTICITY_PROFILE = {
    "conservador": -0.9,
    "base": -1.4,
    "otimista": -1.9,
}


def get_current_selic_rate(fallback: float = DEFAULT_SELIC_ANNUAL_PCT) -> float:
    """Consulta taxa Selic anualizada do repositorio publico BACEN local com fallback seguro."""
    with suppress(Exception):
        from core.integrations.public_data.repository import get_active_public_data_repo

        repo = get_active_public_data_repo()
        indicators = repo.get_macro_indicators() if hasattr(repo, "get_macro_indicators") else {}
        if isinstance(indicators, dict):
            for key in (
                "selic_diaria_aa",
                "selic_meta_copom_valor",
                "selic_meta_anual",
                "taxa_selic_anual_pct",
                "selic",
            ):
                if indicators.get(key):
                    return float(indicators[key])
    return float(fallback)


def simulate_price_change(
    product_name: str,
    current_price: float,
    unit_cost: float,
    daily_volume: float,
    price_delta: float,
    horizon_days: int = 30,
    cross_sell_margin_per_extra_unit: float = 0.0,
    base_elasticity: float | None = None,
) -> dict[str, Any]:
    """
    Simula alteracao de preco em 3 cenarios (conservador, base, otimista) e calcula
    o ponto de equilibrio exato em unidades diarias e variacao percentual.
    """
    if current_price <= 0:
        raise ValueError("current_price deve ser maior que zero.")
    if daily_volume <= 0:
        raise ValueError("daily_volume deve ser maior que zero.")
    if horizon_days < 1:
        raise ValueError("horizon_days deve ser pelo menos 1.")

    new_price = round(float(current_price) + float(price_delta), 4)
    current_margin = round(float(current_price) - float(unit_cost), 4)
    new_margin = round(new_price - float(unit_cost), 4)

    if current_margin <= 0:
        raise ValueError("Margem unitaria atual ja e zero ou negativa.")
    if new_margin <= 0:
        raise ValueError("Preco simulado resulta em margem unitaria zero ou negativa.")

    price_change_pct = float(price_delta) / float(current_price)
    break_even_daily_volume = round((float(daily_volume) * current_margin) / new_margin, 2)
    break_even_delta_units = round(break_even_daily_volume - float(daily_volume), 2)
    break_even_delta_pct = round((break_even_delta_units / float(daily_volume)) * 100.0, 2)
    current_daily_profit = float(daily_volume) * current_margin

    profile = dict(DEFAULT_ELASTICITY_PROFILE)
    if base_elasticity is not None:
        eb = float(base_elasticity)
        profile = {
            "conservador": round(eb * 0.65, 2),
            "base": round(eb, 2),
            "otimista": round(eb * 1.35, 2),
        }

    scenarios: list[WhatIfScenarioOutcome] = []
    for name, elasticity in profile.items():
        vol_change_pct = elasticity * price_change_pct
        proj_vol = round(max(0.0, float(daily_volume) * (1.0 + vol_change_pct)), 2)
        extra_vol = max(0.0, proj_vol - float(daily_volume))
        proj_daily_profit = round(
            (proj_vol * new_margin) + (extra_vol * max(0.0, float(cross_sell_margin_per_extra_unit))),
            2,
        )
        horizon_net_delta = round((proj_daily_profit - current_daily_profit) * int(horizon_days), 2)
        scenarios.append(
            WhatIfScenarioOutcome(
                name=name,
                elasticity=elasticity,
                projected_daily_volume=proj_vol,
                projected_daily_profit_brl=proj_daily_profit,
                horizon_net_delta_brl=horizon_net_delta,
            )
        )

    base_sc = next(s for s in scenarios if s.name == "base")
    if base_sc.horizon_net_delta_brl > 0:
        recommendation = (
            f"Cenario viavel no modo base (+R$ {base_sc.horizon_net_delta_brl:.2f} em {horizon_days} dias; "
            f"ponto de equilibrio exige {break_even_delta_pct:+.2f}% de volume)."
        )
    elif price_delta < 0:
        recommendation = (
            f"ALERTA_DESTRUICAO_MARGEM: reducao de R$ {abs(price_delta):.2f} exige "
            f"{break_even_delta_pct:+.2f}% de volume apenas para empatar ({break_even_daily_volume:.0f} un/dia)."
        )
    else:
        recommendation = (
            f"Impacto base em {horizon_days} dias: R$ {base_sc.horizon_net_delta_brl:.2f}; "
            f"ponto de equilibrio em {break_even_daily_volume:.0f} un/dia ({break_even_delta_pct:+.2f}%)."
        )

    props = WhatIfSimulationProps(
        simulation_type="price_change",
        title=f"Simulador What-If de Preco: {product_name}",
        recommendation=recommendation,
        horizon_days=int(horizon_days),
        metrics={
            "product_name": product_name,
            "current_price": round(float(current_price), 4),
            "new_price": new_price,
            "unit_cost": round(float(unit_cost), 4),
            "current_margin_unit": current_margin,
            "new_margin_unit": new_margin,
            "daily_volume": round(float(daily_volume), 2),
            "break_even_daily_volume": break_even_daily_volume,
            "break_even_delta_units": break_even_delta_units,
            "break_even_delta_pct": break_even_delta_pct,
        },
        scenarios=scenarios,
    )
    envelope = GenUIEnvelope(
        tool_call_id=str(uuid.uuid4()),
        component_name="WhatIfSimulatorUI",
        intent="simular_cenario_what_if",
        executive_summary=recommendation,
        props=props,
    )

    return {
        "success": True,
        "simulation_type": "price_change",
        "product_name": product_name,
        "current_margin_unit": round(current_margin, 2),
        "new_margin_unit": round(new_margin, 2),
        "break_even_daily_volume": break_even_daily_volume,
        "break_even_delta_pct": break_even_delta_pct,
        "scenarios": [s.model_dump() for s in scenarios],
        "recommendation": recommendation,
        "genui_envelope": envelope.model_dump(mode="json"),
    }


def simulate_payment_mix_shift(
    monthly_card_revenue_brl: float,
    shift_pct: float,
    card_fee_pct: float = 2.4,
    pix_fee_pct: float = 0.2,
    pix_discount_pct: float = 1.0,
) -> dict[str, Any]:
    """
    Simula economia liquida mensal ao migrar parcela de vendas no cartao para PIX
    com desconto controlado na bomba ou no caixa.
    """
    if monthly_card_revenue_brl <= 0:
        raise ValueError("monthly_card_revenue_brl deve ser maior que zero.")
    if not (0.0 < shift_pct <= 100.0):
        raise ValueError("shift_pct deve estar entre 0 e 100.")

    monthly_shifted_brl = round(float(monthly_card_revenue_brl) * (float(shift_pct) / 100.0), 2)
    fee_savings_brl = round(monthly_shifted_brl * ((float(card_fee_pct) - float(pix_fee_pct)) / 100.0), 2)
    discount_cost_brl = round(monthly_shifted_brl * (float(pix_discount_pct) / 100.0), 2)
    net_monthly_gain_brl = round(fee_savings_brl - discount_cost_brl, 2)

    if net_monthly_gain_brl > 0:
        recommendation = (
            f"Migracao de {shift_pct:.1f}% para PIX gera economia liquida de R$ {net_monthly_gain_brl:.2f}/mes "
            f"(taxas evitadas R$ {fee_savings_brl:.2f} - desconto R$ {discount_cost_brl:.2f})."
        )
    else:
        recommendation = (
            f"ALERTA_DESCONTO_EXCESSIVO: desconto de {pix_discount_pct:.2f}% supera economia de taxa "
            f"(resultado liquido R$ {net_monthly_gain_brl:.2f}/mes)."
        )

    props = WhatIfSimulationProps(
        simulation_type="payment_mix_shift",
        title="Simulador What-If: Migracao Cartao -> PIX",
        recommendation=recommendation,
        horizon_days=30,
        metrics={
            "monthly_card_revenue_brl": round(float(monthly_card_revenue_brl), 2),
            "shift_pct": round(float(shift_pct), 2),
            "monthly_shifted_brl": monthly_shifted_brl,
            "fee_savings_brl": fee_savings_brl,
            "discount_cost_brl": discount_cost_brl,
            "net_monthly_gain_brl": net_monthly_gain_brl,
        },
        scenarios=[],
    )
    envelope = GenUIEnvelope(
        tool_call_id=str(uuid.uuid4()),
        component_name="WhatIfSimulatorUI",
        intent="simular_cenario_what_if",
        executive_summary=recommendation,
        props=props,
    )

    return {
        "success": True,
        "simulation_type": "payment_mix_shift",
        "monthly_shifted_brl": monthly_shifted_brl,
        "fee_savings_brl": fee_savings_brl,
        "discount_cost_brl": discount_cost_brl,
        "net_monthly_gain_brl": net_monthly_gain_brl,
        "recommendation": recommendation,
        "genui_envelope": envelope.model_dump(mode="json"),
    }


def simulate_inventory_purchase(
    purchase_total_brl: float,
    supplier_discount_pct: float,
    extra_days_in_stock: int,
    selic_annual_pct: float | None = None,
) -> dict[str, Any]:
    """
    Compara ganho de desconto na compra em lote contra custo de capital parado pela Selic.
    """
    if purchase_total_brl <= 0:
        raise ValueError("purchase_total_brl deve ser maior que zero.")
    if extra_days_in_stock < 0:
        raise ValueError("extra_days_in_stock nao pode ser negativo.")

    effective_selic = float(selic_annual_pct) if selic_annual_pct is not None else get_current_selic_rate()
    discount_gain_brl = round(float(purchase_total_brl) * (float(supplier_discount_pct) / 100.0), 2)
    selic_carry_cost_brl = round(
        float(purchase_total_brl) * ((effective_selic / 100.0) * (float(extra_days_in_stock) / 365.0)),
        2,
    )
    net_purchase_gain_brl = round(discount_gain_brl - selic_carry_cost_brl, 2)

    if net_purchase_gain_brl > 0:
        recommendation = (
            f"Compra em lote vantajosa: ganho liquido de R$ {net_purchase_gain_brl:.2f} "
            f"(desconto R$ {discount_gain_brl:.2f} > carregamento Selic {effective_selic:.2f}% de R$ {selic_carry_cost_brl:.2f})."
        )
    else:
        recommendation = (
            f"ALERTA_CAPITAL_PARADO: custo Selic ({effective_selic:.2f}% a.a.) em {extra_days_in_stock} dias "
            f"(R$ {selic_carry_cost_brl:.2f}) anula o desconto de R$ {discount_gain_brl:.2f}."
        )

    props = WhatIfSimulationProps(
        simulation_type="inventory_purchase",
        title="Simulador What-If: Compra em Lote vs. Selic",
        recommendation=recommendation,
        horizon_days=max(1, int(extra_days_in_stock)),
        metrics={
            "purchase_total_brl": round(float(purchase_total_brl), 2),
            "supplier_discount_pct": round(float(supplier_discount_pct), 2),
            "extra_days_in_stock": int(extra_days_in_stock),
            "selic_annual_pct": round(effective_selic, 2),
            "discount_gain_brl": discount_gain_brl,
            "selic_carry_cost_brl": selic_carry_cost_brl,
            "net_purchase_gain_brl": net_purchase_gain_brl,
        },
        scenarios=[],
    )
    envelope = GenUIEnvelope(
        tool_call_id=str(uuid.uuid4()),
        component_name="WhatIfSimulatorUI",
        intent="simular_cenario_what_if",
        executive_summary=recommendation,
        props=props,
    )

    return {
        "success": True,
        "simulation_type": "inventory_purchase",
        "selic_annual_pct": round(effective_selic, 2),
        "discount_gain_brl": discount_gain_brl,
        "selic_carry_cost_brl": selic_carry_cost_brl,
        "net_purchase_gain_brl": net_purchase_gain_brl,
        "recommendation": recommendation,
        "genui_envelope": envelope.model_dump(mode="json"),
    }


def run_whatif_simulation(payload: dict[str, Any]) -> dict[str, Any]:
    """Despacha simulacao contrafactual deterministica a partir de payload estruturado."""
    sim_type = str(payload.get("simulation_type") or "price_change").strip().lower()

    if sim_type == "price_change":
        return simulate_price_change(
            product_name=str(payload.get("product_name") or "Gasolina Comum"),
            current_price=float(payload["current_price"]),
            unit_cost=float(payload["unit_cost"]),
            daily_volume=float(payload["daily_volume"]),
            price_delta=float(payload["price_delta"]),
            horizon_days=int(payload.get("horizon_days", 30)),
            cross_sell_margin_per_extra_unit=float(payload.get("cross_sell_margin_per_extra_unit", 0.0)),
            base_elasticity=float(payload["base_elasticity"]) if payload.get("base_elasticity") is not None else None,
        )

    if sim_type == "payment_mix_shift":
        return simulate_payment_mix_shift(
            monthly_card_revenue_brl=float(payload["monthly_card_revenue_brl"]),
            shift_pct=float(payload["shift_pct"]),
            card_fee_pct=float(payload.get("card_fee_pct", 2.4)),
            pix_fee_pct=float(payload.get("pix_fee_pct", 0.2)),
            pix_discount_pct=float(payload.get("pix_discount_pct", 1.0)),
        )

    if sim_type == "inventory_purchase":
        return simulate_inventory_purchase(
            purchase_total_brl=float(payload["purchase_total_brl"]),
            supplier_discount_pct=float(payload["supplier_discount_pct"]),
            extra_days_in_stock=int(payload["extra_days_in_stock"]),
            selic_annual_pct=float(payload["selic_annual_pct"]) if payload.get("selic_annual_pct") is not None else None,
        )

    raise ValueError(f"simulation_type desconhecido: '{sim_type}'.")
