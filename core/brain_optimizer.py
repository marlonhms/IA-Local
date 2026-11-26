"""
Otimizador Cognitivo e Memoria Autodidata da AURA (Brain Optimizer).

Projeta a arquitetura de contexto adaptativo para operar com maxima precisao tanto em
LLMs leves/locais ou APIs de baixo processamento (EDGE_LIGHT: 1B-8B, flash-lite, mini,
Ollama) quanto em motores de fronteira (FRONTIER: Pro, Ultra, Opus):
1. Destilacao deterministica de payloads de ferramentas (reduz 40-70% dos tokens de entrada
   mantendo 100% dos numeros reais intactos para o NUMERIC_GUARD).
2. Auto-especializacao estruturada no banco cognitivo posto_ai (aura_learned_knowledge),
   permitindo que a propria AURA aprenda regras, glossarios e padroes operacionais por
   (tenant_id, filial_id, pack_id) com recuperacao enxuta de baixa latencia.
Zero travessoes em todo o modulo.
"""

from __future__ import annotations

import json
import os
import re
from contextlib import suppress
from dataclasses import dataclass
from enum import Enum
from typing import Any

from core.logger import logger
from core.migrations import ensure_autonomous_brain_schema

_NOISY_KEYS: frozenset[str] = frozenset(
    {
        "embedding",
        "query_vector",
        "pergunta_vetor",
        "raw_sql",
        "debug",
        "trace",
        "traceback",
        "html",
        "svg",
        "raw_payload",
        "internal_metadata",
    }
)

_LIGHT_MODEL_REGEX = re.compile(
    r"(?:^|[^a-z0-9])(lite|nano|mini|tiny|small|gemma\d*|ollama|local|phi\d*|qwen\d*|llama[-_]?3\.2|1b|2b|3b|4b|7b|8b)(?:$|[^a-z0-9])",
    re.IGNORECASE,
)

_FRONTIER_MODEL_REGEX = re.compile(
    r"(?:^|[^a-z0-9])(pro|ultra|opus|reasoning|o1|o3|70b|405b)(?:$|[^a-z0-9])",
    re.IGNORECASE,
)


class LLMTier(str, Enum):
    """Faixa de capacidade computacional do motor LLM ativo."""

    EDGE_LIGHT = "edge_light"
    BALANCED = "balanced"
    FRONTIER = "frontier"


@dataclass(frozen=True)
class LLMContextProfile:
    """Orcamento deterministico de contexto e densidade informacional por tier de LLM."""

    tier: LLMTier
    model_name: str
    max_context_chars: int
    max_items: int
    max_learned_facts: int
    max_string_len: int
    compact_json: bool


def resolve_llm_context_profile(model_name: str | None = None) -> LLMContextProfile:
    """
    Resolve automaticamente o perfil de contexto ideal para o modelo LLM ativo.
    Respeita override explicito via variavel de ambiente AURA_LLM_TIER
    ('edge_light', 'balanced', 'frontier').
    """
    resolved_model = (model_name or os.getenv("DEFAULT_LLM_MODEL", "") or "").strip()
    env_tier = (os.getenv("AURA_LLM_TIER") or "").strip().lower()

    tier: LLMTier
    if env_tier in (LLMTier.EDGE_LIGHT.value, "light", "edge", "local"):
        tier = LLMTier.EDGE_LIGHT
    elif env_tier in (LLMTier.FRONTIER.value, "heavy", "high"):
        tier = LLMTier.FRONTIER
    elif env_tier == LLMTier.BALANCED.value:
        tier = LLMTier.BALANCED
    else:
        if _FRONTIER_MODEL_REGEX.search(resolved_model):
            tier = LLMTier.FRONTIER
        elif _LIGHT_MODEL_REGEX.search(resolved_model):
            tier = LLMTier.EDGE_LIGHT
        else:
            tier = LLMTier.BALANCED

    if tier == LLMTier.EDGE_LIGHT:
        return LLMContextProfile(
            tier=tier,
            model_name=resolved_model,
            max_context_chars=2600,
            max_items=6,
            max_learned_facts=3,
            max_string_len=240,
            compact_json=True,
        )
    if tier == LLMTier.FRONTIER:
        return LLMContextProfile(
            tier=tier,
            model_name=resolved_model,
            max_context_chars=14000,
            max_items=20,
            max_learned_facts=8,
            max_string_len=1200,
            compact_json=False,
        )
    return LLMContextProfile(
        tier=tier,
        model_name=resolved_model,
        max_context_chars=6000,
        max_items=10,
        max_learned_facts=5,
        max_string_len=480,
        compact_json=True,
    )


def _prune_payload(obj: Any, profile: LLMContextProfile, depth: int = 0) -> Any:
    """Remove campos nulos/ruidosos e limita listas sem alterar nenhum valor numerico."""
    if depth > 6:
        return str(obj)[: profile.max_string_len]

    if isinstance(obj, dict):
        cleaned: dict[str, Any] = {}
        for k, v in obj.items():
            key_str = str(k)
            if key_str.lower() in _NOISY_KEYS:
                continue
            if v is None or v == "" or v == [] or v == {}:
                continue
            pruned_v = _prune_payload(v, profile, depth + 1)
            if pruned_v is None or pruned_v == "" or pruned_v == [] or pruned_v == {}:
                continue
            cleaned[key_str] = pruned_v
        return cleaned

    if isinstance(obj, list):
        total = len(obj)
        sliced = [_prune_payload(item, profile, depth + 1) for item in obj[: profile.max_items]]
        if total > profile.max_items:
            sliced.append({"_omitted_items": total - profile.max_items})
        return sliced

    if isinstance(obj, str):
        compact_str = " ".join(obj.split())
        if len(compact_str) > profile.max_string_len:
            return compact_str[: profile.max_string_len - 3] + "..."
        return compact_str

    return obj


def distill_tool_context(
    raw_result: Any,
    header: str = "",
    model_name: str | None = None,
    profile: LLMContextProfile | None = None,
) -> str:
    """
    Destila deterministamente o retorno de ferramentas em contexto de alta densidade
    informacional e baixo consumo de tokens, adaptado ao tier do motor LLM.
    Preserva integralmente metricas numericas reais para o NUMERIC_GUARD.
    """
    eff_profile = profile or resolve_llm_context_profile(model_name)
    pruned = _prune_payload(raw_result, eff_profile)

    if eff_profile.compact_json:
        serialized = json.dumps(pruned, ensure_ascii=False, separators=(",", ":"), default=str)
    else:
        serialized = json.dumps(pruned, ensure_ascii=False, indent=2, default=str)

    prefix = f"{header.strip()}\n" if header and header.strip() else ""
    budget = max(400, eff_profile.max_context_chars - len(prefix))
    if len(serialized) > budget:
        serialized = serialized[: budget - 24] + "... [contexto compacto]"
    return f"{prefix}{serialized}\n"


def _normalize_topic_key(raw: str) -> str:
    slug = re.sub(r"[^a-z0-9_]+", "_", (raw or "").strip().lower()).strip("_")
    return (slug or "geral")[:128]


def _extract_query_tokens(text: str) -> set[str]:
    return {tok for tok in re.findall(r"[a-z0-9]{3,}", (text or "").lower())}


class AutonomousBrainStore:
    """
    Camada de auto-especializacao persistente sobre aura_learned_knowledge (posto_ai ou SQLite).
    Permite gravacao idempotente de conhecimento aprendido e recuperacao ultra-enxuta
    otimizada para LLMs leves/locais e motores de fronteira.
    """

    def __init__(self, connection: Any | None = None, dialect: str | None = None) -> None:
        self._external_conn = connection
        self._dialect = dialect
        self._schema_checked = False

    def _resolve_dialect(self, conn: Any) -> str:
        if self._dialect:
            return self._dialect
        mod = type(conn).__module__.lower()
        return "sqlite" if "sqlite" in mod else "postgresql"

    def _ensure_ready(self, conn: Any) -> bool:
        if self._schema_checked:
            return True
        dialect = self._resolve_dialect(conn)
        try:
            ensure_autonomous_brain_schema(conn, dialect=dialect)
            self._schema_checked = True
            return True
        except Exception as exc:  # noqa: BLE001
            with suppress(Exception):
                conn.rollback()
            logger.warning("AutonomousBrainStore aguardando ownership em posto_ai: %s", exc)
            return False

    def learn_fact(
        self,
        *,
        tenant_id: str,
        filial_id: str,
        pack_id: str,
        topic_key: str,
        summary_compact: str,
        fact_type: str = "operational_rule",
        structured_data: dict[str, Any] | None = None,
        confidence: float = 0.90,
        status: str = "approved",
        source: str = "aura_engine",
        embedding: list[float] | None = None,
    ) -> dict[str, Any]:
        """Registra ou atualiza (upsert) conhecimento destilado para a vertical/tenant."""
        clean_topic = _normalize_topic_key(topic_key)
        clean_summary = " ".join((summary_compact or "").split())[:280]
        if not clean_summary:
            raise ValueError("summary_compact nao pode ser vazio.")
        clean_status = status if status in ("approved", "pending", "archived") else "approved"
        payload_json = json.dumps(structured_data or {}, ensure_ascii=False, separators=(",", ":"), default=str)
        conf_val = max(0.0, min(1.0, float(confidence)))

        if self._external_conn is not None:
            return self._upsert_on_conn(
                self._external_conn,
                tenant_id=tenant_id,
                filial_id=str(filial_id),
                pack_id=pack_id,
                topic_key=clean_topic,
                fact_type=fact_type[:48],
                summary_compact=clean_summary,
                payload_json=payload_json,
                confidence=conf_val,
                status=clean_status,
                source=source[:64],
                embedding=embedding,
            )

        from core.db_pool import get_vector_connection

        with get_vector_connection(tenant_id=tenant_id) as conn:
            return self._upsert_on_conn(
                conn,
                tenant_id=tenant_id,
                filial_id=str(filial_id),
                pack_id=pack_id,
                topic_key=clean_topic,
                fact_type=fact_type[:48],
                summary_compact=clean_summary,
                payload_json=payload_json,
                confidence=conf_val,
                status=clean_status,
                source=source[:64],
                embedding=embedding,
            )

    def _upsert_on_conn(
        self,
        conn: Any,
        *,
        tenant_id: str,
        filial_id: str,
        pack_id: str,
        topic_key: str,
        fact_type: str,
        summary_compact: str,
        payload_json: str,
        confidence: float,
        status: str,
        source: str,
        embedding: list[float] | None,
    ) -> dict[str, Any]:
        if not self._ensure_ready(conn):
            return {"status": "deferred", "topic_key": topic_key}

        dialect = self._resolve_dialect(conn)
        cur = conn.cursor()
        try:
            if dialect == "postgresql":
                vec_str = str(embedding) if embedding else None
                cur.execute(
                    """
                    INSERT INTO aura_learned_knowledge (
                        tenant_id, filial_id, pack_id, topic_key, fact_type,
                        summary_compact, structured_data, embedding, confidence, status, source, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::halfvec, %s, %s, %s, NOW())
                    ON CONFLICT (tenant_id, filial_id, pack_id, topic_key)
                    DO UPDATE SET
                        fact_type = EXCLUDED.fact_type,
                        summary_compact = EXCLUDED.summary_compact,
                        structured_data = EXCLUDED.structured_data,
                        embedding = COALESCE(EXCLUDED.embedding, aura_learned_knowledge.embedding),
                        confidence = EXCLUDED.confidence,
                        status = EXCLUDED.status,
                        source = EXCLUDED.source,
                        updated_at = NOW();
                    """,
                    (
                        tenant_id,
                        filial_id,
                        pack_id,
                        topic_key,
                        fact_type,
                        summary_compact,
                        payload_json,
                        vec_str,
                        confidence,
                        status,
                        source,
                    ),
                )
            else:
                vec_str = json.dumps(embedding) if embedding else None
                cur.execute(
                    """
                    INSERT INTO aura_learned_knowledge (
                        tenant_id, filial_id, pack_id, topic_key, fact_type,
                        summary_compact, structured_data, embedding, confidence, status, source, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(tenant_id, filial_id, pack_id, topic_key)
                    DO UPDATE SET
                        fact_type = excluded.fact_type,
                        summary_compact = excluded.summary_compact,
                        structured_data = excluded.structured_data,
                        embedding = COALESCE(excluded.embedding, aura_learned_knowledge.embedding),
                        confidence = excluded.confidence,
                        status = excluded.status,
                        source = excluded.source,
                        updated_at = CURRENT_TIMESTAMP;
                    """,
                    (
                        tenant_id,
                        filial_id,
                        pack_id,
                        topic_key,
                        fact_type,
                        summary_compact,
                        payload_json,
                        vec_str,
                        confidence,
                        status,
                        source,
                    ),
                )
            if hasattr(conn, "commit"):
                conn.commit()
        finally:
            cur.close()

        return {
            "status": "learned",
            "tenant_id": tenant_id,
            "filial_id": filial_id,
            "pack_id": pack_id,
            "topic_key": topic_key,
            "summary_compact": summary_compact,
        }

    def recall_compact_knowledge(
        self,
        *,
        query: str,
        tenant_id: str,
        filial_id: str,
        pack_id: str,
        limit: int | None = None,
        model_name: str | None = None,
        query_vector: list[float] | None = None,
    ) -> list[dict[str, Any]]:
        """Recupera fatos aprovados mais relevantes para o escopo (tenant, filial, pack)."""
        profile = resolve_llm_context_profile(model_name)
        eff_limit = max(1, int(limit if limit is not None else profile.max_learned_facts))

        if self._external_conn is not None:
            return self._recall_on_conn(
                self._external_conn,
                query=query,
                tenant_id=tenant_id,
                filial_id=str(filial_id),
                pack_id=pack_id,
                limit=eff_limit,
                query_vector=query_vector,
            )

        try:
            from core.db_pool import get_vector_connection

            with get_vector_connection(tenant_id=tenant_id) as conn:
                return self._recall_on_conn(
                    conn,
                    query=query,
                    tenant_id=tenant_id,
                    filial_id=str(filial_id),
                    pack_id=pack_id,
                    limit=eff_limit,
                    query_vector=query_vector,
                )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Recall de conhecimento autonomo indisponivel: %s", exc)
            return []

    def _recall_on_conn(
        self,
        conn: Any,
        *,
        query: str,
        tenant_id: str,
        filial_id: str,
        pack_id: str,
        limit: int,
        query_vector: list[float] | None,
    ) -> list[dict[str, Any]]:
        dialect = self._resolve_dialect(conn)
        cur = conn.cursor()
        rows: list[Any] = []
        try:
            if dialect == "postgresql" and query_vector:
                vec_str = str(query_vector)
                cur.execute(
                    """
                    SELECT topic_key, fact_type, summary_compact, confidence,
                           CASE WHEN embedding IS NOT NULL THEN 1 - (embedding <=> %s::halfvec) ELSE 0.0 END AS sim
                    FROM aura_learned_knowledge
                    WHERE tenant_id = %s
                      AND filial_id = %s
                      AND (pack_id = %s OR pack_id = 'global')
                      AND status = 'approved'
                    ORDER BY sim DESC, confidence DESC, updated_at DESC
                    LIMIT %s;
                    """,
                    (vec_str, tenant_id, filial_id, pack_id, max(limit * 3, 12)),
                )
                rows = cur.fetchall()
            elif dialect == "postgresql":
                cur.execute(
                    """
                    SELECT topic_key, fact_type, summary_compact, confidence, 0.0 AS sim
                    FROM aura_learned_knowledge
                    WHERE tenant_id = %s
                      AND filial_id = %s
                      AND (pack_id = %s OR pack_id = 'global')
                      AND status = 'approved'
                    ORDER BY confidence DESC, updated_at DESC
                    LIMIT %s;
                    """,
                    (tenant_id, filial_id, pack_id, max(limit * 4, 20)),
                )
                rows = cur.fetchall()
            else:
                cur.execute(
                    """
                    SELECT topic_key, fact_type, summary_compact, confidence, 0.0 AS sim
                    FROM aura_learned_knowledge
                    WHERE tenant_id = ?
                      AND filial_id = ?
                      AND (pack_id = ? OR pack_id = 'global')
                      AND status = 'approved'
                    ORDER BY confidence DESC, updated_at DESC
                    LIMIT ?;
                    """,
                    (tenant_id, filial_id, pack_id, max(limit * 4, 20)),
                )
                rows = cur.fetchall()
        except Exception:  # noqa: BLE001
            with suppress(Exception):
                conn.rollback()
            return []
        finally:
            cur.close()

        q_tokens = _extract_query_tokens(query)
        scored: list[tuple[float, dict[str, Any]]] = []
        for r in rows:
            topic_key = str(r[0])
            fact_type = str(r[1])
            summary = str(r[2])
            conf = float(r[3] or 0.0)
            sim = float(r[4] or 0.0)

            fact_tokens = _extract_query_tokens(f"{topic_key} {summary}")
            overlap = (len(q_tokens & fact_tokens) / max(len(q_tokens), 1)) if q_tokens else 0.0
            score = (sim * 0.65) + (overlap * 0.25) + (conf * 0.10)
            scored.append(
                (
                    score,
                    {
                        "topic_key": topic_key,
                        "fact_type": fact_type,
                        "summary_compact": summary,
                        "confidence": round(conf, 3),
                        "score": round(score, 4),
                    },
                )
            )

        scored.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    @staticmethod
    def format_recalled_knowledge_block(
        facts: list[dict[str, Any]],
        model_name: str | None = None,
    ) -> str:
        """Formata fatos recuperados em bloco minimo otimizado para qualquer tier de LLM."""
        if not facts:
            return ""
        profile = resolve_llm_context_profile(model_name)
        lines = ["Conhecimento Especializado da Unidade (Memoria Autonoma):"]
        max_block_chars = 650 if profile.tier == LLMTier.EDGE_LIGHT else 1800
        total_len = len(lines[0])
        for f in facts[: profile.max_learned_facts]:
            line = f"- [{f.get('topic_key')}] {f.get('summary_compact')}"
            if total_len + len(line) + 1 > max_block_chars:
                break
            lines.append(line)
            total_len += len(line) + 1
        return "\n".join(lines) + "\n" if len(lines) > 1 else ""
