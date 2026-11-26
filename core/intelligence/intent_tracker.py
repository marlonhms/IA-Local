"""Telemetria de Intencao do Operador com Sanitizacao LGPD e Promocao de Foco (Fase 2).

Registra em operator_intent_signals quais entidades, categorias e metricas
o operador consulta com recorrencia (zero PII) e promove topicos recorrentes
para monitoramento prioritario no BusinessProfiler e sugestao de simulacao.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta

from core.intelligence.models import (
    OperatorIntentRecord,
    PromotedMonitorTarget,
    SuggestedSimulationCard,
)
from core.sanitizer import sanitize_text
from core.simulation.models import ScenarioType, ShockVector
from core.simulation.repository import SimulationRepository, _sanitize_signal_token

_METRIC_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("margin_pct", ("margem", "rentabilidade", "lucratividade", "markup")),
    ("unit_cost", ("custo", "fornecedor", "compra", "aquisicao", "pauta")),
    ("net_cashflow_brl", ("caixa", "fluxo", "recebimento", "pagamento", "capital de giro", "prazo")),
    ("daily_volume", ("volume", "giro", "litragem", "demanda", "estoque", "autonomia")),
)

_ENTITY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("combustivel", ("gasolina", "etanol", "diesel", "gnv", "arla", "combustivel", "pista", "tanque")),
    ("conveniencia", ("conveniencia", "loja", "cerveja", "refrigerante", "bebida", "cafe", "lanche")),
    ("fornecedor", ("fornecedor", "distribuidora", "compra", "nota fiscal", "danfe")),
    ("financeiro_caixa", ("caixa", "receber", "pagar", "cartao", "pix", "tef", "fluxo")),
    ("estoque", ("estoque", "produto", "categoria", "sku", "giro")),
)


def _normalize_ascii(text: str) -> str:
    table = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
        "aaaaaeeeeiiiiooooouuuucaaaaaeeeeiiiiooooouuuuc",
    )
    return text.translate(table).lower()


class IntentTracker:
    """Rastreia sinais sanitizados de consulta e promove topicos recorrentes."""

    def __init__(
        self,
        repository: SimulationRepository,
        recurrence_threshold: int = 3,
        window_days: int = 7,
    ) -> None:
        self._repo = repository
        self._recurrence_threshold = max(1, int(recurrence_threshold))
        self._window_days = max(1, int(window_days))

    @staticmethod
    def _infer_metric_key(sanitized_norm: str, intent_name: str) -> str:
        for metric_key, kws in _METRIC_KEYWORDS:
            if any(kw in sanitized_norm for kw in kws):
                return metric_key
        norm_intent = _normalize_ascii(intent_name or "")
        if "margem" in norm_intent or "preco" in norm_intent:
            return "margin_pct"
        if "estoque" in norm_intent or "tanque" in norm_intent:
            return "daily_volume"
        if "caixa" in norm_intent or "financeir" in norm_intent:
            return "net_cashflow_brl"
        return "daily_volume"

    @staticmethod
    def _infer_entity_type(sanitized_norm: str, pack_id: str) -> str:
        for entity_type, kws in _ENTITY_KEYWORDS:
            if any(kw in sanitized_norm for kw in kws):
                return entity_type
        return _sanitize_signal_token(f"ops_{pack_id}", max_len=48)

    @staticmethod
    def _build_simulation_suggestion(
        tenant_id: str,
        pack_id: str,
        topic_key: str,
        entity_type: str,
        metric_key: str,
        hit_count: int,
    ) -> SuggestedSimulationCard:
        if metric_key == "unit_cost":
            scenario: ScenarioType = "cost_supplier_variation"
            shocks = ShockVector(supplier_cost_delta_pct=5.0, cost_passthrough_pct=50.0)
            title = f"Simular impacto de custo em {entity_type}"
        elif metric_key == "net_cashflow_brl":
            scenario = "payment_term_cashflow"
            shocks = ShockVector(receivable_days_delta=-3.0, payable_days_delta=5.0)
            title = f"Simular alivio de fluxo de caixa ({entity_type})"
        elif metric_key == "daily_volume":
            scenario = "price_discount_change"
            shocks = ShockVector(discount_pct=2.0)
            title = f"Simular elasticidade de giro em {entity_type}"
        else:
            scenario = "price_discount_change"
            shocks = ShockVector(price_delta_pct=2.5)
            title = f"Simular ajuste de margem em {entity_type}"

        card_seed = f"{tenant_id}:{pack_id}:{topic_key}:{metric_key}"
        card_id = f"card_{uuid.uuid5(uuid.NAMESPACE_DNS, card_seed).hex[:12]}"
        return SuggestedSimulationCard(
            card_id=card_id,
            tenant_id=tenant_id,
            pack_id=pack_id,
            topic_key=topic_key,
            entity_type=entity_type,
            metric_key=metric_key,
            hit_count=hit_count,
            recommended_scenario=scenario,
            suggested_shocks=shocks,
            title=title,
            reason=(
                f"Topico '{topic_key}' consultado {hit_count} vezes na janela recente; "
                "simulacao pronta para avaliacao."
            ),
        )

    def record_query(
        self,
        tenant_id: str,
        pack_id: str,
        raw_query: str,
        intent_name: str,
        entity_type: str | None = None,
        metric_key: str | None = None,
        topic_key: str | None = None,
        increment: int = 1,
    ) -> OperatorIntentRecord:
        """Sanitiza consulta via LGPD e registra sinal agregado em operator_intent_signals."""
        norm_pack = pack_id.strip().lower()
        sanitized_query = sanitize_text(raw_query or "")
        # Remove marcadores [REDACTED:...] antes de inferir tokens de negocio
        cleaned_for_nlp = re.sub(r"\[REDACTED:[A-Z0-9_]+\]", " ", sanitized_query)
        norm_query = _normalize_ascii(cleaned_for_nlp)

        resolved_metric = _sanitize_signal_token(
            sanitize_text(metric_key) if metric_key else self._infer_metric_key(norm_query, intent_name)
        )
        resolved_entity = _sanitize_signal_token(
            sanitize_text(entity_type) if entity_type else self._infer_entity_type(norm_query, norm_pack)
        )
        resolved_topic = _sanitize_signal_token(
            sanitize_text(topic_key) if topic_key else f"{resolved_entity}:{resolved_metric}"
        )
        resolved_intent = _sanitize_signal_token(sanitize_text(intent_name or "geral"))

        signal_id = self._repo.record_operator_intent_signal(
            tenant_id=tenant_id,
            pack_id=norm_pack,
            entity_type=resolved_entity,
            metric_key=resolved_metric,
            topic_key=resolved_topic,
            intent_name=resolved_intent,
            increment=increment,
        )

        return OperatorIntentRecord(
            signal_id=signal_id,
            tenant_id=tenant_id,
            pack_id=norm_pack,
            entity_type=resolved_entity,
            metric_key=resolved_metric,
            topic_key=resolved_topic,
            intent_name=resolved_intent,
            hit_count=max(1, int(increment)),
            last_seen_at=datetime.now(UTC).isoformat(),
        )

    def evaluate_recurrence(
        self,
        tenant_id: str,
        pack_id: str,
        window_days: int | None = None,
        min_hits: int | None = None,
    ) -> tuple[list[PromotedMonitorTarget], list[SuggestedSimulationCard]]:
        """Identifica topicos recorrentes e retorna alvos prioritarios + cards sugeridos."""
        norm_pack = pack_id.strip().lower()
        days = max(1, int(window_days if window_days is not None else self._window_days))
        threshold = max(1, int(min_hits if min_hits is not None else self._recurrence_threshold))
        since_dt = datetime.now(UTC) - timedelta(days=days)

        signals = self._repo.list_recent_intent_signals(
            tenant_id=tenant_id,
            pack_id=norm_pack,
            since_dt=since_dt,
            limit=50,
        )

        promoted: list[PromotedMonitorTarget] = []
        cards: list[SuggestedSimulationCard] = []
        for sig in signals:
            hits = int(sig.get("hit_count", 0))
            if hits < threshold:
                continue
            entity_type = str(sig["entity_type"])
            metric_key = str(sig["metric_key"])
            topic_key = str(sig["topic_key"])
            promoted.append(
                PromotedMonitorTarget(
                    tenant_id=tenant_id,
                    pack_id=norm_pack,
                    entity_type=entity_type,
                    metric_key=metric_key,
                    topic_key=topic_key,
                    hit_count=hits,
                )
            )
            cards.append(
                self._build_simulation_suggestion(
                    tenant_id=tenant_id,
                    pack_id=norm_pack,
                    topic_key=topic_key,
                    entity_type=entity_type,
                    metric_key=metric_key,
                    hit_count=hits,
                )
            )

        return promoted, cards

    def get_priority_metrics(
        self,
        tenant_id: str,
        pack_id: str,
        window_days: int | None = None,
        min_hits: int | None = None,
    ) -> set[str]:
        """Retorna o conjunto de metricas promovidas para monitoramento prioritario."""
        promoted, _ = self.evaluate_recurrence(
            tenant_id=tenant_id,
            pack_id=pack_id,
            window_days=window_days,
            min_hits=min_hits,
        )
        return {item.metric_key for item in promoted}


__all__ = ["IntentTracker"]
