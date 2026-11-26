"""Sintetizador Economico de Consequencias de Segunda Ordem (Fase 2).

Utiliza exclusivamente o cliente singleton core.llm_client.get_genai_client(),
recebendo apenas JSON compacto sanitizado do desvio/simulacao + trechos
sanitizados do pgvector, e somente quando uma anomalia real e detectada.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Sequence

from core.intelligence.models import AnomalyFinding
from core.llm_client import get_genai_client
from core.sanitizer import sanitize_dict, sanitize_text
from core.simulation.models import BusinessRule, SimulationRecomputeResponse

logger = logging.getLogger("AuraSecondOrderSynthesizer")

RAGRetrieverFn = Callable[[str, str, int], list[dict[str, Any]]]


def _resolve_default_model() -> str:
    try:
        from config.settings import DEFAULT_LLM_MODEL

        if DEFAULT_LLM_MODEL:
            return str(DEFAULT_LLM_MODEL)
    except Exception:
        pass
    return "models/gemini-2.5-flash"


class SecondOrderSynthesizer:
    """Sintetiza impactos de segunda ordem com orcamento minimo de tokens."""

    def __init__(
        self,
        model_name: str | None = None,
        rag_retriever: RAGRetrieverFn | None = None,
        api_key: str | None = None,
    ) -> None:
        self._model_name = model_name or _resolve_default_model()
        self._rag_retriever = rag_retriever
        self._api_key = api_key

    def build_compact_payload(
        self,
        tenant_id: str,
        pack_id: str,
        anomalies: Sequence[AnomalyFinding],
        simulation: SimulationRecomputeResponse,
        active_rules: Sequence[BusinessRule] | None = None,
    ) -> dict[str, Any]:
        """Monta JSON enxuto e sanitizado (LGPD) sem dados brutos ou regras candidate."""
        norm_pack = pack_id.strip().lower()
        approved_rules = [
            {
                "rule_key": r.rule_key,
                "metric": r.metric,
                "operator": r.operator,
                "threshold": r.threshold_value,
            }
            for r in (active_rules or [])
            if r.status == "active" and r.tenant_id == tenant_id and r.pack_id.strip().lower() == norm_pack
        ][:6]

        raw_payload: dict[str, Any] = {
            "pack_id": norm_pack,
            "anomalies": [
                {
                    "metric": a.metric,
                    "observed": round(a.observed_value, 4),
                    "baseline_mean": round(a.baseline_mean, 4),
                    "z_score": round(a.z_score, 3),
                    "direction": a.direction,
                    "severity": a.severity,
                    "priority": a.is_priority_monitored,
                }
                for a in list(anomalies)[:4]
            ],
            "simulation": {
                "simulation_id": simulation.simulation_id,
                "scenario_type": simulation.scenario_type,
                "horizon_days": simulation.horizon_days,
                "p10": simulation.monte_carlo.p10,
                "p50": simulation.monte_carlo.p50,
                "p90": simulation.monte_carlo.p90,
                "prob_positive_pct": simulation.monte_carlo.prob_positive_pct,
                "top_drivers": [
                    {
                        "param": d.parameter,
                        "impact_brl": d.impact_brl,
                        "direction": d.direction,
                    }
                    for d in simulation.sensitivity[:3]
                ],
                "violated_rules": [
                    {"rule_key": v.rule_key, "severity": v.severity}
                    for v in simulation.violated_rules[:5]
                ],
            },
            "active_rules": approved_rules,
        }
        sanitized_payload, _ = sanitize_dict(raw_payload)
        return sanitized_payload

    def fetch_rag_snippets(
        self,
        query_text: str,
        pack_id: str,
        top_k: int = 3,
    ) -> list[str]:
        """Busca trechos relevantes do pgvector e aplica sanitizacao LGPD."""
        clean_query = sanitize_text(query_text or "").strip()
        if not clean_query or top_k <= 0:
            return []

        raw_docs: list[dict[str, Any]] = []
        if self._rag_retriever is not None:
            raw_docs = list(self._rag_retriever(clean_query, pack_id.strip().lower(), top_k) or [])
        else:
            try:
                from core.rag_engine import HybridRAGEngine

                rag = HybridRAGEngine()
                search_fn = getattr(rag, "search_hybrid_conhecimento", None) or getattr(rag, "search_hybrid", None)
                if callable(search_fn):
                    res = search_fn(clean_query, top_k=top_k)
                    if isinstance(res, dict) and isinstance(res.get("results"), list):
                        raw_docs = [item for item in res["results"] if isinstance(item, dict)]
                    elif isinstance(res, list):
                        raw_docs = [item for item in res if isinstance(item, dict)]
            except Exception as exc:  # noqa: BLE001
                logger.debug("pgvector indisponivel durante sintese proativa: %s", exc)
                return []

        snippets: list[str] = []
        for doc in raw_docs[:top_k]:
            raw_text = (
                doc.get("content")
                or doc.get("conteudo")
                or doc.get("snippet")
                or doc.get("text")
                or doc.get("title")
                or ""
            )
            cleaned = sanitize_text(str(raw_text)).strip()
            if cleaned:
                snippets.append(cleaned[:280])
        return snippets

    @staticmethod
    def _build_deterministic_fallback(
        compact_payload: dict[str, Any],
    ) -> str:
        anomalies = compact_payload.get("anomalies") or []
        sim = compact_payload.get("simulation") or {}
        if not anomalies:
            return "Nenhuma anomalia estatistica relevante detectada."
        top_a = anomalies[0]
        return (
            f"Desvio {top_a.get('severity')} em {top_a.get('metric')} "
            f"(observado={top_a.get('observed')}, media={top_a.get('baseline_mean')}, "
            f"z={top_a.get('z_score')}). "
            f"Simulacao {sim.get('scenario_type')} ({sim.get('horizon_days')}d) "
            f"projeta P50={sim.get('p50')} BRL (P10={sim.get('p10')}, P90={sim.get('p90')})."
        )

    def synthesize(
        self,
        tenant_id: str,
        pack_id: str,
        anomalies: Sequence[AnomalyFinding],
        simulation: SimulationRecomputeResponse,
        active_rules: Sequence[BusinessRule] | None = None,
        allow_llm: bool = True,
    ) -> tuple[str, list[str], int]:
        """Gera sintese de segunda ordem apenas se houver anomalia real."""
        if not anomalies:
            return "", [], 0

        compact_payload = self.build_compact_payload(
            tenant_id=tenant_id,
            pack_id=pack_id,
            anomalies=anomalies,
            simulation=simulation,
            active_rules=active_rules,
        )
        metrics_query = " ".join(str(a.metric) for a in anomalies[:3])
        rag_query = f"{pack_id.strip().lower()} {simulation.scenario_type} {metrics_query}"
        snippets = self.fetch_rag_snippets(query_text=rag_query, pack_id=pack_id, top_k=3)

        if not allow_llm:
            return self._build_deterministic_fallback(compact_payload), snippets, 0

        prompt = (
            "Voce e o analista executivo de segunda ordem da AURA. "
            "Nao recalcule numeros nem invente metricas fora do JSON abaixo. "
            "Explique em ate 3 bullets curtos os efeitos colaterais operacionais e de caixa "
            "deste desvio e cenario simulado.\n"
            f"DADOS_COMPACTOS_JSON: {json.dumps(compact_payload, ensure_ascii=False)}\n"
            f"CONTEXTO_PGVECTOR: {json.dumps(snippets, ensure_ascii=False)}"
        )

        try:
            client = get_genai_client(api_key=self._api_key)
            response = client.models.generate_content(
                model=self._model_name,
                contents=prompt,
            )
            raw_text = str(getattr(response, "text", "") or "").strip()
            if raw_text:
                return sanitize_text(raw_text), snippets, 1
        except Exception as exc:  # noqa: BLE001
            logger.debug("Fallback deterministico na sintese de segunda ordem: %s", exc)

        return self._build_deterministic_fallback(compact_payload), snippets, 0


__all__ = ["RAGRetrieverFn", "SecondOrderSynthesizer"]
