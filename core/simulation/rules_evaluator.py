"""Avaliador Binario Deterministico de Regras Duras (Fase 1).

Combina regras declarativas do YAML do Domain Pack ativo com regras de negocio
persistidas em business_memory_rules (exclusivamente status='active') para
tenant_id e pack_id especificos. Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from core.domain.domain_pack_loader import DomainPackConfig
from core.simulation.models import (
    BusinessRule,
    RuleOperator,
    RuleViolation,
)

_SEVERITY_ORDER: dict[str, int] = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "INFO": 3,
}


def _evaluate_binary_condition(
    observed: float,
    operator: RuleOperator,
    threshold: float,
    threshold_upper: float | None = None,
) -> bool:
    """Retorna True se a condicao da regra for satisfeita, False se violada."""
    if operator == ">=":
        return observed >= threshold
    if operator == "<=":
        return observed <= threshold
    if operator == ">":
        return observed > threshold
    if operator == "<":
        return observed < threshold
    if operator == "==":
        return abs(observed - threshold) <= 1e-9
    if operator == "!=":
        return abs(observed - threshold) > 1e-9
    if operator == "between":
        upper = threshold_upper if threshold_upper is not None else threshold
        low = min(threshold, upper)
        high = max(threshold, upper)
        return low <= observed <= high
    raise ValueError(f"Operador de regra nao suportado: '{operator}'.")


class RulesEvaluator:
    """Avalia regras duras (YAML + business_memory_rules ativas) de forma binaria."""

    @staticmethod
    def _extract_pack_yaml_rules(
        pack_config: DomainPackConfig | None,
        tenant_id: str,
    ) -> list[BusinessRule]:
        if pack_config is None or not pack_config.hard_rules:
            return []

        valid_ops = {">=", "<=", ">", "<", "==", "!=", "between"}
        valid_sevs = {"CRITICAL", "HIGH", "MEDIUM", "INFO"}
        extracted: list[BusinessRule] = []
        for idx, raw in enumerate(pack_config.hard_rules):
            if not isinstance(raw, dict):
                continue
            metric = str(raw.get("metric") or "").strip()
            op = str(raw.get("operator") or "").strip()
            if not metric or op not in valid_ops or "threshold_value" not in raw:
                continue
            sev = str(raw.get("severity") or "HIGH").strip().upper()
            rule_key = str(raw.get("rule_key") or f"yaml_{metric}_{idx}")
            rule_id = str(raw.get("rule_id") or f"yaml:{pack_config.pack_id}:{rule_key}")
            upper_raw = raw.get("threshold_upper")
            extracted.append(
                BusinessRule(
                    rule_id=rule_id,
                    tenant_id=tenant_id,
                    pack_id=pack_config.pack_id,
                    rule_key=rule_key,
                    metric=metric,
                    operator=op,  # type: ignore[arg-type]
                    threshold_value=float(raw["threshold_value"]),
                    threshold_upper=float(upper_raw) if upper_raw is not None else None,
                    severity=sev if sev in valid_sevs else "HIGH",  # type: ignore[arg-type]
                    status="active",
                    source="yaml",
                    origin="domain_pack_yaml",
                    author="domain_pack",
                    description=str(raw.get("description") or ""),
                )
            )
        return extracted

    def evaluate(
        self,
        metrics: Mapping[str, float],
        tenant_id: str,
        pack_id: str,
        pack_config: DomainPackConfig | None = None,
        memory_rules: Sequence[BusinessRule] | None = None,
        extra_yaml_rules: Sequence[BusinessRule] | None = None,
    ) -> list[RuleViolation]:
        """Executa avaliacao binaria e retorna lista estruturada de regras violadas."""
        norm_tenant = tenant_id.strip()
        norm_pack = pack_id.strip().lower()

        rules_by_id: dict[str, BusinessRule] = {}

        for rule in self._extract_pack_yaml_rules(pack_config=pack_config, tenant_id=norm_tenant):
            if rule.pack_id.strip().lower() == norm_pack:
                rules_by_id[rule.rule_id] = rule

        if extra_yaml_rules:
            for rule in extra_yaml_rules:
                if rule.pack_id.strip().lower() == norm_pack and rule.status == "active":
                    rules_by_id[rule.rule_id] = rule

        if memory_rules:
            for rule in memory_rules:
                if (
                    rule.status == "active"
                    and rule.tenant_id.strip() == norm_tenant
                    and rule.pack_id.strip().lower() == norm_pack
                ):
                    rules_by_id[rule.rule_id] = rule

        violations: list[RuleViolation] = []
        for rule in rules_by_id.values():
            if rule.metric not in metrics:
                continue
            observed = float(metrics[rule.metric])
            passed = _evaluate_binary_condition(
                observed=observed,
                operator=rule.operator,
                threshold=float(rule.threshold_value),
                threshold_upper=float(rule.threshold_upper) if rule.threshold_upper is not None else None,
            )
            if not passed:
                if rule.operator == "between":
                    upper = rule.threshold_upper if rule.threshold_upper is not None else rule.threshold_value
                    target_desc = f"entre {rule.threshold_value} e {upper}"
                else:
                    target_desc = f"{rule.operator} {rule.threshold_value}"

                desc_prefix = f"{rule.description}: " if rule.description else ""
                violations.append(
                    RuleViolation(
                        rule_id=rule.rule_id,
                        source=rule.source,
                        rule_key=rule.rule_key,
                        metric=rule.metric,
                        operator=rule.operator,
                        threshold=float(rule.threshold_value),
                        threshold_upper=float(rule.threshold_upper) if rule.threshold_upper is not None else None,
                        observed_value=round(observed, 4),
                        severity=rule.severity,
                        message=(
                            f"{desc_prefix}Metrica '{rule.metric}' ({observed:.2f}) "
                            f"viola regra ativa [{rule.rule_key}] ({target_desc})."
                        ),
                    )
                )

        violations.sort(key=lambda v: (_SEVERITY_ORDER.get(v.severity, 9), v.rule_id))
        return violations


__all__ = ["RulesEvaluator"]
