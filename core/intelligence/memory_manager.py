"""Gerenciador de Memoria Institucional com Governanca HiC (Fase 2).

Extrai regras tacitas/correcoes do operador sempre como status='candidate',
bloqueia regras nao aprovadas tanto no calculo quanto no contexto do LLM
e processa decisoes explicitas de aprovacao/rejeicao (Human-in-Command).
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Literal

from core.intelligence.models import RuleDecisionResponse
from core.sanitizer import sanitize_text
from core.simulation.models import BusinessRule, RuleOperator, RuleSeverity, RuleStatus
from core.simulation.repository import SimulationRepository, _sanitize_signal_token

_RULE_TRIGGER_RE = re.compile(
    r"\b(?:regra|corrigindo|correcao|na verdade|nunca|jamais|sempre|nao aceitar|"
    r"nao operar|nao vender|piso|teto|minimo|minima|maximo|maxima|limite)\b",
    re.IGNORECASE,
)

_BETWEEN_RE = re.compile(
    r"\bentre\s+(-?\d+(?:[.,]\d+)?)\s*%?\s*(?:e|a)\s+(-?\d+(?:[.,]\d+)?)\s*%?",
    re.IGNORECASE,
)

_COMPARISON_RE = re.compile(
    r"(?P<phrase>nunca\s+abaixo\s+de|nao\s+(?:aceitar|operar|vender)\s+abaixo\s+de|"
    r"nunca\s+acima\s+de|nao\s+(?:aceitar|operar|vender)\s+acima\s+de|"
    r"no\s+minimo|minimo\s+de|minima\s+de|pelo\s+menos|piso\s+de|acima\s+de|maior\s+que|"
    r"no\s+maximo|maximo\s+de|maxima\s+de|teto\s+de|limite\s+de|abaixo\s+de|menor\s+que|"
    r">=|<=|>|<)\s*(?:de\s+|e\s+)?(?P<val>-?\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)

_METRIC_ALIASES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("projected_unit_margin_brl", "min_unit_margin_brl", ("margem unitaria", "lucro unitario", "centavos")),
    ("projected_margin_pct", "margin_pct_guard", ("margem", "rentabilidade", "markup")),
    ("projected_unit_cost", "unit_cost_guard", ("custo unitario", "custo")),
    ("effective_receivable_days", "receivable_days_guard", ("prazo de recebimento", "recebimento", "recebiveis")),
    ("effective_payable_days", "payable_days_guard", ("prazo de pagamento", "fornecedor")),
    ("projected_daily_volume", "daily_volume_guard", ("volume", "giro", "litragem")),
    ("working_capital_delta_brl", "working_capital_guard", ("capital de giro", "caixa")),
)


def _normalize_ascii(text: str) -> str:
    table = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
        "aaaaaeeeeiiiiooooouuuucaaaaaeeeeiiiiooooouuuuc",
    )
    return text.translate(table).lower()


def _parse_float(raw: str) -> float:
    return float(raw.replace(",", ".").strip())


def _infer_operator(phrase: str, norm_text: str) -> RuleOperator:
    p = " ".join(phrase.lower().split())
    if p in (">=", "<=", ">", "<"):
        return p  # type: ignore[return-value]
    if "nunca abaixo" in p or "nao aceitar abaixo" in p or "nao operar abaixo" in p or "nao vender abaixo" in p:
        return ">="
    if "nunca acima" in p or "nao aceitar acima" in p or "nao operar acima" in p or "nao vender acima" in p:
        return "<="
    if any(tok in p for tok in ("no minimo", "minimo", "minima", "pelo menos", "piso")):
        return ">="
    if any(tok in p for tok in ("no maximo", "maximo", "maxima", "teto", "limite")):
        return "<="
    if "abaixo de" in p or "menor que" in p:
        if any(neg in norm_text for neg in ("nunca", "jamais", "nao aceitar", "nao operar", "nao vender")):
            return ">="
        return "<"
    if "acima de" in p or "maior que" in p:
        if any(neg in norm_text for neg in ("nunca", "jamais", "nao aceitar", "nao operar", "nao vender")):
            return "<="
        return ">"
    return ">="


class MemoryManager:
    """Gerencia extracao, isolamento e aprovacao HiC de regras de negocio."""

    def __init__(self, repository: SimulationRepository) -> None:
        self._repo = repository

    def extract_candidate_from_message(
        self,
        message: str,
        tenant_id: str,
        pack_id: str,
        author: str = "operator",
        origin: str = "chat_operator_correction",
        severity: RuleSeverity = "HIGH",
    ) -> BusinessRule | None:
        """Extrai regra estruturada deterministica e salva SEMPRE com status='candidate'."""
        sanitized = sanitize_text(message or "").strip()
        if not sanitized:
            return None

        norm = _normalize_ascii(sanitized)
        if not _RULE_TRIGGER_RE.search(norm):
            return None

        metric: str | None = None
        base_key: str | None = None
        for m_name, key_prefix, aliases in _METRIC_ALIASES:
            if any(alias in norm for alias in aliases):
                metric = m_name
                base_key = key_prefix
                break
        if metric is None or base_key is None:
            return None

        operator: RuleOperator | None = None
        threshold_val: float | None = None
        threshold_upper: float | None = None

        between_m = _BETWEEN_RE.search(norm)
        if between_m:
            operator = "between"
            v1 = _parse_float(between_m.group(1))
            v2 = _parse_float(between_m.group(2))
            threshold_val = min(v1, v2)
            threshold_upper = max(v1, v2)
        else:
            comp_m = _COMPARISON_RE.search(norm)
            if comp_m:
                operator = _infer_operator(comp_m.group("phrase"), norm)
                threshold_val = _parse_float(comp_m.group("val"))

        if operator is None or threshold_val is None:
            return None

        norm_pack = pack_id.strip().lower()
        rule_id = f"rule_{uuid.uuid4().hex[:12]}"
        rule = BusinessRule(
            rule_id=rule_id,
            tenant_id=tenant_id,
            pack_id=norm_pack,
            rule_key=f"{base_key}_{rule_id[-6:]}",
            metric=metric,
            operator=operator,
            threshold_value=threshold_val,
            threshold_upper=threshold_upper,
            severity=severity,
            status="candidate",
            source="business_memory",
            origin=_sanitize_signal_token(origin, max_len=48),
            author=_sanitize_signal_token(author, max_len=64),
            description=sanitized[:280],
        )
        self._repo.save_business_rule(rule)
        return rule

    def propose_candidate_rule(self, rule: BusinessRule) -> BusinessRule:
        """Persiste regra explicitamente proposta sempre forcando status='candidate'."""
        candidate = rule.model_copy(
            update={
                "pack_id": rule.pack_id.strip().lower(),
                "status": "candidate",
                "source": "business_memory",
                "author": _sanitize_signal_token(rule.author, max_len=64),
                "description": sanitize_text(rule.description or "")[:280],
            }
        )
        self._repo.save_business_rule(candidate)
        return candidate

    def list_rules(
        self,
        tenant_id: str,
        pack_id: str,
        status: RuleStatus | None = None,
    ) -> list[BusinessRule]:
        """Lista regras do tenant_id e pack_id com filtro opcional por status."""
        return self._repo.list_business_rules(
            tenant_id=tenant_id,
            pack_id=pack_id.strip().lower(),
            status=status,
        )

    def list_active_rules_for_context(
        self,
        tenant_id: str,
        pack_id: str,
    ) -> list[BusinessRule]:
        """Retorna EXCLUSIVAMENTE regras com status='active' (bloqueia candidate/rejected)."""
        norm_pack = pack_id.strip().lower()
        rules = self._repo.list_business_rules(
            tenant_id=tenant_id,
            pack_id=norm_pack,
            status="active",
        )
        return [
            r
            for r in rules
            if r.status == "active"
            and r.tenant_id == tenant_id
            and r.pack_id.strip().lower() == norm_pack
        ]

    def format_active_rules_for_llm(
        self,
        tenant_id: str,
        pack_id: str,
    ) -> str:
        """Formata apenas regras aprovadas (status='active') para contexto do LLM."""
        active_rules = self.list_active_rules_for_context(tenant_id=tenant_id, pack_id=pack_id)
        if not active_rules:
            return ""
        lines = ["REGRAS DE NEGOCIO APROVADAS (MEMORIA INSTITUCIONAL):"]
        for r in active_rules[:10]:
            if r.operator == "between" and r.threshold_upper is not None:
                cond = f"entre {r.threshold_value} e {r.threshold_upper}"
            else:
                cond = f"{r.operator} {r.threshold_value}"
            desc = sanitize_text(r.description or r.rule_key)
            lines.append(f"- [{r.severity}] {r.metric} {cond} ({desc})")
        return "\n".join(lines)

    def decide_rule(
        self,
        rule_id: str,
        tenant_id: str,
        pack_id: str,
        decision: Literal["approve", "reject"],
        decided_by: str = "operator",
        reason: str = "",
    ) -> RuleDecisionResponse:
        """Aprova ou rejeita regra candidate sob governanca HiC."""
        norm_pack = pack_id.strip().lower()
        existing = self._repo.get_business_rule(
            rule_id=rule_id,
            tenant_id=tenant_id,
            pack_id=norm_pack,
        )
        if existing is None:
            raise LookupError(
                f"Regra '{rule_id}' nao encontrada para tenant '{tenant_id}' e pack '{norm_pack}'."
            )
        if existing.status != "candidate":
            raise ValueError(
                f"Regra '{rule_id}' ja possui decisao final ('{existing.status}') e nao esta mais em 'candidate'."
            )

        new_status: RuleStatus = "active" if decision == "approve" else "rejected"
        safe_decider = _sanitize_signal_token(decided_by, max_len=64)
        clean_reason = sanitize_text(reason or "").strip()
        audit_note = f"HiC {decision} por {safe_decider}" + (f": {clean_reason}" if clean_reason else "")

        updated = self._repo.update_business_rule_status(
            rule_id=rule_id,
            tenant_id=tenant_id,
            pack_id=norm_pack,
            new_status=new_status,
            decided_by=safe_decider,
            description_suffix=audit_note,
        )
        if updated is None:
            raise LookupError(f"Regra '{rule_id}' nao encontrada ao persistir decisao.")

        return RuleDecisionResponse(
            rule_id=updated.rule_id,
            tenant_id=updated.tenant_id,
            pack_id=updated.pack_id,
            previous_status=existing.status,
            new_status=updated.status,
            decided_by=safe_decider,
            decided_at=datetime.now(UTC).isoformat(),
            rule=updated,
        )


__all__ = ["MemoryManager"]
