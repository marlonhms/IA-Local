"""Motor Deterministico What-If com Monte Carlo (5.000 iteracoes) (Fase 1).

Executa em Python puro (<100ms), Zero-LLM, com isolamento estrito por pack_id
via DomainSimulatorRegistry e avaliacao binaria via RulesEvaluator.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import math
import random
import time
import uuid
from contextlib import suppress
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

from core.domain.domain_pack_loader import DomainPackConfig, load_domain_pack
from core.domain.simulator_contract import (
    BaseDomainSimulator,
    DomainSimulatorRegistry,
    get_default_simulator_registry,
)
from core.simulation.models import (
    BusinessRule,
    MonteCarloBands,
    ScenarioType,
    SensitivityDriver,
    ShockVector,
    SimulationBaseline,
    SimulationRecomputeRequest,
    SimulationRecomputeResponse,
)
from core.simulation.repository import SimulationRepository
from core.simulation.rules_evaluator import RulesEvaluator

_ROUND_2 = Decimal("0.01")

_SENSITIVITY_PARAMS_BY_SCENARIO: dict[ScenarioType, list[tuple[str, float]]] = {
    "price_discount_change": [
        ("price_delta_pct", 1.0),
        ("discount_pct", 1.0),
    ],
    "cost_supplier_variation": [
        ("supplier_cost_delta_pct", 1.0),
        ("cost_passthrough_pct", 10.0),
    ],
    "payment_term_cashflow": [
        ("receivable_days_delta", 1.0),
        ("payable_days_delta", 1.0),
        ("capital_cost_delta_pct", 1.0),
    ],
}


def _round_money(value: float) -> float:
    """Arredondamento financeiro deterministico ABNT/SEFAZ (ROUND_HALF_UP)."""
    return float(Decimal(str(value)).quantize(_ROUND_2, rounding=ROUND_HALF_UP))


def _percentile(sorted_vals: list[float], pct: float) -> float:
    """Calcula percentil por interpolacao linear sobre lista ja ordenada."""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = (pct / 100.0) * (len(sorted_vals) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac


class SimulationEngine:
    """Motor generico agnostico de dominio para simulacao What-If e Monte Carlo."""

    def __init__(
        self,
        simulator_registry: DomainSimulatorRegistry | None = None,
        rules_evaluator: RulesEvaluator | None = None,
    ) -> None:
        self._registry = simulator_registry or get_default_simulator_registry()
        self._rules_evaluator = rules_evaluator or RulesEvaluator()

    @staticmethod
    def _resolve_pack_config(
        pack_id: str,
        explicit_pack_config: DomainPackConfig | None,
    ) -> DomainPackConfig | None:
        if explicit_pack_config is not None:
            return explicit_pack_config
        with suppress(FileNotFoundError, ValueError, TypeError):
            return load_domain_pack(pack_id)
        return None

    @staticmethod
    def _compute_sensitivity(
        simulator: BaseDomainSimulator,
        scenario_type: ScenarioType,
        baseline: SimulationBaseline,
        shocks: ShockVector,
        horizon_days: int,
        base_net_delta: float,
    ) -> list[SensitivityDriver]:
        params = _SENSITIVITY_PARAMS_BY_SCENARIO.get(scenario_type, [])
        raw_impacts: list[tuple[str, float]] = []

        for param_name, step in params:
            current_val = float(getattr(shocks, param_name))
            perturbed_shocks = shocks.model_copy(update={param_name: current_val + step})
            # Garante limites validos quando discount_pct ou cost_passthrough_pct forem perturbados
            if param_name == "discount_pct" and perturbed_shocks.discount_pct > 99.9:
                perturbed_shocks = shocks.model_copy(update={param_name: current_val - step})
            outcome = simulator.evaluate_deterministic(
                scenario_type=scenario_type,
                baseline=baseline,
                shocks=perturbed_shocks,
                horizon_days=horizon_days,  # type: ignore[arg-type]
            )
            impact = outcome.net_profit_delta_brl - base_net_delta
            raw_impacts.append((param_name, impact))

        total_abs = sum(abs(imp) for _, imp in raw_impacts)
        drivers: list[SensitivityDriver] = []
        for param_name, impact in raw_impacts:
            impact_rounded = _round_money(impact)
            pct = round((abs(impact) / total_abs) * 100.0, 2) if total_abs > 1e-9 else 0.0
            direction = (
                "positive"
                if impact_rounded > 0
                else ("negative" if impact_rounded < 0 else "neutral")
            )
            drivers.append(
                SensitivityDriver(
                    parameter=param_name,
                    impact_brl=impact_rounded,
                    impact_pct=pct,
                    direction=direction,  # type: ignore[arg-type]
                )
            )
        drivers.sort(key=lambda d: abs(d.impact_brl), reverse=True)
        return drivers

    def run_simulation(
        self,
        request: SimulationRecomputeRequest,
        repository: SimulationRepository | None = None,
        pack_config: DomainPackConfig | None = None,
        memory_rules: Sequence[BusinessRule] | None = None,
    ) -> SimulationRecomputeResponse:
        """Executa simulacao Monte Carlo deterministica + avaliacao binaria de regras."""
        started = time.perf_counter()

        simulation_id = request.simulation_id or f"sim_{uuid.uuid4().hex[:12]}"
        baseline = request.baseline
        if baseline is None:
            if repository is None or not request.simulation_id:
                raise ValueError(
                    "baseline obrigatorio quando simulation_id nao referencia snapshot persistido."
                )
            snapshot = repository.get_simulation_snapshot(
                simulation_id=request.simulation_id,
                tenant_id=request.tenant_id,
                pack_id=request.pack_id,
            )
            if snapshot is None:
                raise LookupError(
                    f"Simulacao '{request.simulation_id}' nao encontrada para tenant '{request.tenant_id}' e pack '{request.pack_id}'."
                )
            baseline = SimulationBaseline.model_validate(snapshot["baseline"])

        simulator = self._registry.resolve(request.pack_id)
        resolved_pack_cfg = self._resolve_pack_config(request.pack_id, pack_config)

        # Monte Carlo (5.000 iteracoes padrao) com gerador pseudoaleatorio isolado por seed
        rng = random.Random(request.seed)
        outcomes: list[float] = []
        positive_count = 0

        for _ in range(request.iterations):
            res = simulator.evaluate_iteration(
                scenario_type=request.scenario_type,
                baseline=baseline,
                shocks=request.shocks,
                horizon_days=request.horizon_days,
                rng=rng,
            )
            val = res.net_profit_delta_brl
            outcomes.append(val)
            if val > 0.0:
                positive_count += 1

        outcomes.sort()
        n = len(outcomes)
        p10 = _round_money(_percentile(outcomes, 10.0))
        p50 = _round_money(_percentile(outcomes, 50.0))
        p90 = _round_money(_percentile(outcomes, 90.0))
        mean_val = sum(outcomes) / n
        variance = sum((x - mean_val) ** 2 for x in outcomes) / n
        std_dev = _round_money(math.sqrt(variance))
        prob_positive_pct = round((positive_count / n) * 100.0, 2)

        bands = MonteCarloBands(
            p10=p10,
            p50=p50,
            p90=p90,
            mean=_round_money(mean_val),
            std_dev=std_dev,
            prob_positive_pct=prob_positive_pct,
            iterations=request.iterations,
            seed=request.seed,
        )

        det_outcome = simulator.evaluate_deterministic(
            scenario_type=request.scenario_type,
            baseline=baseline,
            shocks=request.shocks,
            horizon_days=request.horizon_days,
        )

        sensitivity = self._compute_sensitivity(
            simulator=simulator,
            scenario_type=request.scenario_type,
            baseline=baseline,
            shocks=request.shocks,
            horizon_days=int(request.horizon_days),
            base_net_delta=det_outcome.net_profit_delta_brl,
        )

        projected_metrics: dict[str, float] = {
            "baseline_horizon_profit_brl": _round_money(det_outcome.baseline_horizon_profit_brl),
            "projected_p50_horizon_profit_brl": _round_money(det_outcome.baseline_horizon_profit_brl + p50),
            "projected_p10_horizon_profit_brl": _round_money(det_outcome.baseline_horizon_profit_brl + p10),
            "projected_p90_horizon_profit_brl": _round_money(det_outcome.baseline_horizon_profit_brl + p90),
            "net_profit_delta_p10_brl": p10,
            "net_profit_delta_p50_brl": p50,
            "net_profit_delta_p90_brl": p90,
            "projected_unit_margin_brl": _round_money(det_outcome.projected_unit_margin_brl),
            "projected_margin_pct": round(det_outcome.projected_margin_pct, 2),
            "working_capital_delta_brl": _round_money(det_outcome.working_capital_delta_brl),
        }
        for key, val in det_outcome.extra_metrics.items():
            if isinstance(val, (int, float)) and key not in projected_metrics:
                projected_metrics[key] = round(float(val), 4)

        active_memory_rules = memory_rules
        if active_memory_rules is None and repository is not None:
            active_memory_rules = repository.list_business_rules(
                tenant_id=request.tenant_id,
                pack_id=request.pack_id,
                status="active",
            )

        extra_yaml_rules = simulator.extract_yaml_rules(
            pack_config=resolved_pack_cfg,
            tenant_id=request.tenant_id,
        )

        violated_rules = self._rules_evaluator.evaluate(
            metrics=projected_metrics,
            tenant_id=request.tenant_id,
            pack_id=request.pack_id,
            pack_config=resolved_pack_cfg,
            memory_rules=active_memory_rules,
            extra_yaml_rules=extra_yaml_rules,
        )

        if request.persist_snapshot and repository is not None:
            repository.save_simulation_snapshot(
                simulation_id=simulation_id,
                tenant_id=request.tenant_id,
                pack_id=request.pack_id,
                scenario_type=request.scenario_type,
                horizon_days=int(request.horizon_days),
                baseline=baseline,
                shocks=request.shocks,
                p10_value=p10,
                p50_value=p50,
                p90_value=p90,
                sensitivity=sensitivity,
                violated_rules=violated_rules,
                seed=request.seed,
                iterations=request.iterations,
                created_by=request.created_by,
            )

        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)

        return SimulationRecomputeResponse(
            simulation_id=simulation_id,
            tenant_id=request.tenant_id,
            pack_id=request.pack_id.strip().lower(),
            scenario_type=request.scenario_type,
            horizon_days=request.horizon_days,
            monte_carlo=bands,
            projected_metrics=projected_metrics,
            sensitivity=sensitivity,
            violated_rules=violated_rules,
            is_compliant=(len(violated_rules) == 0),
            elapsed_ms=elapsed_ms,
            llm_calls=0,
        )


__all__ = ["SimulationEngine"]
