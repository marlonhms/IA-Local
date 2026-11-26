"""Contrato de Adaptadores de Dominio para Simulacao What-If (Fase 1).

Define a interface BaseDomainSimulator, a implementacao agnostica
UniversalDomainSimulator (3 cenarios universais) e o registro estrito
DomainSimulatorRegistry isolado por pack_id (zero fallback para PostoTools).
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import importlib
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from core.domain.domain_pack_loader import DomainPackConfig
from core.simulation.models import (
    BusinessRule,
    HorizonDays,
    RuleOperator,
    RuleSeverity,
    ScenarioType,
    ShockVector,
    SimulationBaseline,
)

logger = logging.getLogger("DomainSimulatorContract")

UNIVERSAL_SCENARIOS: tuple[ScenarioType, ...] = (
    "price_discount_change",
    "cost_supplier_variation",
    "payment_term_cashflow",
)

_VALID_OPERATORS: frozenset[str] = frozenset({">=", "<=", ">", "<", "==", "!=", "between"})
_VALID_SEVERITIES: frozenset[str] = frozenset({"CRITICAL", "HIGH", "MEDIUM", "INFO"})


@dataclass(frozen=True)
class IterationOutcome:
    """Resultado de uma iteracao individual (ou deterministica) de simulacao."""

    net_profit_delta_brl: float
    projected_horizon_profit_brl: float
    baseline_horizon_profit_brl: float
    projected_unit_margin_brl: float
    projected_margin_pct: float
    working_capital_delta_brl: float
    extra_metrics: dict[str, float] = field(default_factory=dict)


class BaseDomainSimulator(ABC):
    """Contrato abstrato obrigatorio para simuladores especializados por pack_id."""

    pack_id: str = "universal"
    supported_scenarios: tuple[ScenarioType, ...] = UNIVERSAL_SCENARIOS

    @abstractmethod
    def evaluate_iteration(
        self,
        scenario_type: ScenarioType,
        baseline: SimulationBaseline,
        shocks: ShockVector,
        horizon_days: HorizonDays,
        rng: random.Random | None = None,
    ) -> IterationOutcome:
        """Executa uma iteracao estocastica (quando rng != None) ou deterministica."""

    def evaluate_deterministic(
        self,
        scenario_type: ScenarioType,
        baseline: SimulationBaseline,
        shocks: ShockVector,
        horizon_days: HorizonDays,
    ) -> IterationOutcome:
        """Executa o calculo pontual sem ruido aleatorio."""
        return self.evaluate_iteration(
            scenario_type=scenario_type,
            baseline=baseline,
            shocks=shocks,
            horizon_days=horizon_days,
            rng=None,
        )

    def extract_yaml_rules(
        self,
        pack_config: DomainPackConfig | None,
        tenant_id: str,
    ) -> list[BusinessRule]:
        """Extrai regras duras declaradas no YAML do Domain Pack ativo."""
        if pack_config is None or not pack_config.hard_rules:
            return []

        rules: list[BusinessRule] = []
        for idx, raw_rule in enumerate(pack_config.hard_rules):
            if not isinstance(raw_rule, dict):
                continue
            metric = str(raw_rule.get("metric") or "").strip()
            op_raw = str(raw_rule.get("operator") or "").strip()
            if not metric or op_raw not in _VALID_OPERATORS:
                continue
            if "threshold_value" not in raw_rule:
                continue

            sev_raw = str(raw_rule.get("severity") or "HIGH").strip().upper()
            severity: RuleSeverity = sev_raw if sev_raw in _VALID_SEVERITIES else "HIGH"  # type: ignore[assignment]
            operator: RuleOperator = op_raw  # type: ignore[assignment]
            rule_key = str(raw_rule.get("rule_key") or f"yaml_{metric}_{idx}")
            rule_id = str(raw_rule.get("rule_id") or f"yaml:{pack_config.pack_id}:{rule_key}")

            upper_raw = raw_rule.get("threshold_upper")
            threshold_upper = float(upper_raw) if upper_raw is not None else None

            rules.append(
                BusinessRule(
                    rule_id=rule_id,
                    tenant_id=tenant_id,
                    pack_id=pack_config.pack_id,
                    rule_key=rule_key,
                    metric=metric,
                    operator=operator,
                    threshold_value=float(raw_rule["threshold_value"]),
                    threshold_upper=threshold_upper,
                    severity=severity,
                    status="active",
                    source="yaml",
                    origin="domain_pack_yaml",
                    author="domain_pack",
                    description=str(raw_rule.get("description") or ""),
                )
            )
        return rules


class UniversalDomainSimulator(BaseDomainSimulator):
    """Implementacao agnostica de dominio para os 3 cenarios universais."""

    def __init__(self, pack_id: str = "universal") -> None:
        self.pack_id = pack_id

    @staticmethod
    def _sample_normal(rng: random.Random | None, mean: float, std_dev: float) -> float:
        if rng is None or std_dev <= 0.0:
            return mean
        return rng.gauss(mean, std_dev)

    def evaluate_iteration(
        self,
        scenario_type: ScenarioType,
        baseline: SimulationBaseline,
        shocks: ShockVector,
        horizon_days: HorizonDays,
        rng: random.Random | None = None,
    ) -> IterationOutcome:
        days = int(horizon_days)

        # Amostragem estocastica de volume base, custo unitario e elasticidade
        vol_factor = 1.0 + self._sample_normal(rng, 0.0, baseline.volume_std_dev_pct / 100.0)
        base_daily_vol = max(0.0, baseline.daily_volume * max(0.05, vol_factor))

        cost_factor = 1.0 + self._sample_normal(rng, 0.0, baseline.cost_std_dev_pct / 100.0)
        base_unit_cost = max(0.0, baseline.unit_cost * max(0.05, cost_factor))

        elasticity = self._sample_normal(rng, baseline.elasticity_mean, baseline.elasticity_std_dev)

        base_unit_margin = baseline.unit_price - base_unit_cost
        baseline_horizon_profit = (base_unit_margin * base_daily_vol - baseline.fixed_daily_cost) * days

        if scenario_type == "price_discount_change":
            new_price = max(
                0.01,
                baseline.unit_price
                * (1.0 + shocks.price_delta_pct / 100.0)
                * (1.0 - shocks.discount_pct / 100.0),
            )
            price_change_pct = (new_price - baseline.unit_price) / baseline.unit_price
            proj_daily_vol = max(0.0, base_daily_vol * (1.0 + elasticity * price_change_pct))
            new_cost = base_unit_cost
            wc_delta = 0.0
            carry_cost = 0.0

        elif scenario_type == "cost_supplier_variation":
            cost_mult = max(0.01, 1.0 + shocks.supplier_cost_delta_pct / 100.0)
            new_cost = base_unit_cost * cost_mult
            raw_cost_delta = baseline.unit_cost * (shocks.supplier_cost_delta_pct / 100.0)
            passthrough_price_delta = raw_cost_delta * (shocks.cost_passthrough_pct / 100.0)
            new_price = max(0.01, baseline.unit_price + passthrough_price_delta)
            price_change_pct = (new_price - baseline.unit_price) / baseline.unit_price
            proj_daily_vol = max(0.0, base_daily_vol * (1.0 + elasticity * price_change_pct))
            wc_delta = 0.0
            carry_cost = 0.0

        elif scenario_type == "payment_term_cashflow":
            new_price = baseline.unit_price
            new_cost = base_unit_cost
            proj_daily_vol = base_daily_vol
            daily_revenue = new_price * proj_daily_vol
            daily_cogs = new_cost * proj_daily_vol
            wc_delta = (daily_revenue * shocks.receivable_days_delta) - (
                daily_cogs * shocks.payable_days_delta
            )
            effective_annual_rate = max(
                0.0,
                (baseline.annual_capital_cost_pct + shocks.capital_cost_delta_pct) / 100.0,
            )
            carry_cost = wc_delta * effective_annual_rate * (days / 365.0)

        else:
            raise ValueError(f"Cenario de simulacao nao suportado: '{scenario_type}'.")

        proj_unit_margin = new_price - new_cost
        proj_margin_pct = (proj_unit_margin / new_price) * 100.0 if new_price > 0 else 0.0
        proj_horizon_profit = ((proj_unit_margin * proj_daily_vol - baseline.fixed_daily_cost) * days) - carry_cost
        net_delta = proj_horizon_profit - baseline_horizon_profit

        extra = dict(baseline.extra_metrics)
        extra["projected_daily_volume"] = proj_daily_vol
        extra["projected_unit_price"] = new_price
        extra["projected_unit_cost"] = new_cost
        extra["effective_receivable_days"] = baseline.receivable_days + shocks.receivable_days_delta
        extra["effective_payable_days"] = baseline.payable_days + shocks.payable_days_delta

        return IterationOutcome(
            net_profit_delta_brl=net_delta,
            projected_horizon_profit_brl=proj_horizon_profit,
            baseline_horizon_profit_brl=baseline_horizon_profit,
            projected_unit_margin_brl=proj_unit_margin,
            projected_margin_pct=proj_margin_pct,
            working_capital_delta_brl=wc_delta,
            extra_metrics=extra,
        )


class DomainSimulatorRegistry:
    """Registro estrito de adaptadores de simulacao por pack_id (sem fallback para PostoTools)."""

    def __init__(self) -> None:
        self._registry: dict[str, type[BaseDomainSimulator]] = {}

    def register(self, pack_id: str, simulator_cls: type[BaseDomainSimulator]) -> None:
        """Registra um adaptador de simulador para um pack_id especifico."""
        key = pack_id.strip().lower()
        if not key:
            raise ValueError("pack_id nao pode ser vazio ao registrar simulador.")
        self._registry[key] = simulator_cls

    def resolve(self, pack_id: str) -> BaseDomainSimulator:
        """Resolve o simulador para o pack_id informado.

        Ordem de resolucao estrita:
        1. Adaptador explicitamente registrado para pack_id.
        2. Descoberta dinamica em core.domain.<pack_id>.simulator (se existir).
        3. UniversalDomainSimulator(pack_id=pack_id) agnostico.
        Nunca faz fallback para fuel_convenience ou PostoTools.
        """
        norm_pack = (pack_id or "").strip().lower()
        if not norm_pack:
            raise ValueError("pack_id obrigatorio para resolver simulador de dominio.")

        if norm_pack in self._registry:
            return self._registry[norm_pack]()

        module_name = f"core.domain.{norm_pack}.simulator"
        try:
            mod = importlib.import_module(module_name)
        except ModuleNotFoundError:
            mod = None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Erro ao importar adaptador de simulacao %s: %s", module_name, exc)
            mod = None

        if mod is not None:
            factory = getattr(mod, "get_simulator", None)
            if callable(factory):
                instance = factory()
                if isinstance(instance, BaseDomainSimulator):
                    return instance
            sim_cls = getattr(mod, "DomainSimulator", None)
            if isinstance(sim_cls, type) and issubclass(sim_cls, BaseDomainSimulator):
                self._registry[norm_pack] = sim_cls
                return sim_cls()

        return UniversalDomainSimulator(pack_id=norm_pack)

    def has_dedicated_adapter(self, pack_id: str) -> bool:
        """Indica se o pack_id possui adaptador dedicado (registrado ou descoberto)."""
        norm_pack = (pack_id or "").strip().lower()
        sim = self.resolve(norm_pack)
        return type(sim) is not UniversalDomainSimulator


_DEFAULT_REGISTRY = DomainSimulatorRegistry()


def get_default_simulator_registry() -> DomainSimulatorRegistry:
    """Retorna o registro padrao singleton de simuladores por dominio."""
    return _DEFAULT_REGISTRY


__all__ = [
    "BaseDomainSimulator",
    "DomainSimulatorRegistry",
    "IterationOutcome",
    "UNIVERSAL_SCENARIOS",
    "UniversalDomainSimulator",
    "get_default_simulator_registry",
]
