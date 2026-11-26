"""Repositorio Persistente para Simulacao What-If e Memoria do Negocio (Fase 1).

Opera sobre PostgreSQL (posto_ai via core.db_pool) ou SQLite injetado (testes),
mantendo isolamento estrito por (tenant_id, pack_id), imutabilidade de
simulation_snapshots e sanitizacao LGPD (zero PII) em operator_intent_signals.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
import re
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, Iterator

from core.sanitizer import sanitize_text
from core.simulation.models import (
    BusinessProfileSnapshotRecord,
    BusinessRule,
    RuleViolation,
    SensitivityDriver,
    ShockVector,
    SimulationBaseline,
)

_REDACTION_MARKER_RE = re.compile(r"\[REDACTED:([A-Z0-9_]+)\]")
_LONG_DIGITS_RE = re.compile(r"\d{7,}")
_NON_SLUG_RE = re.compile(r"[^a-z0-9_:-]+")


def _sanitize_signal_token(value: str, max_len: int = 64) -> str:
    """Sanitiza um token de telemetria removendo PII e convertendo para slug seguro."""
    raw = str(value or "").strip()
    if not raw:
        return "unknown"

    cleaned = sanitize_text(raw)
    cleaned = _REDACTION_MARKER_RE.sub(lambda m: f"redacted_{m.group(1).lower()}", cleaned)
    cleaned = _LONG_DIGITS_RE.sub("redacted_num", cleaned)
    slug = _NON_SLUG_RE.sub("_", cleaned.lower()).strip("_")
    return (slug or "unknown")[:max_len]


class SimulationRepository:
    """Camada de persistencia isolada por tenant_id e pack_id."""

    def __init__(self, connection: Any = None, dialect: str | None = None) -> None:
        self._external_conn = connection
        self._dialect = dialect

    def _resolve_dialect(self, conn: Any) -> str:
        if self._dialect:
            return self._dialect
        mod = type(conn).__module__.lower()
        return "sqlite" if "sqlite" in mod else "postgresql"

    def _ph(self, conn: Any) -> str:
        return "?" if self._resolve_dialect(conn) == "sqlite" else "%s"

    @contextmanager
    def _connection_scope(self, tenant_id: str) -> Iterator[Any]:
        if self._external_conn is not None:
            yield self._external_conn
            if hasattr(self._external_conn, "commit"):
                self._external_conn.commit()
            return

        from core.db_pool import get_vector_db_connection

        with get_vector_db_connection(tenant_id=tenant_id) as conn:
            yield conn
            if hasattr(conn, "commit"):
                conn.commit()

    def save_business_profile_snapshot(
        self,
        record: BusinessProfileSnapshotRecord,
    ) -> str:
        """Persiste um snapshot estatistico historico isolado por tenant_id e pack_id."""
        with self._connection_scope(record.tenant_id) as conn:
            p = self._ph(conn)
            cur = conn.cursor()
            try:
                cur.execute(
                    f"""
                    INSERT INTO business_profile_snapshots (
                        snapshot_id, tenant_id, pack_id, reference_period,
                        means_json, std_devs_json, seasonality_json, abc_curve_json,
                        sample_size
                    ) VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p});
                    """,
                    (
                        record.snapshot_id,
                        record.tenant_id,
                        record.pack_id.strip().lower(),
                        record.reference_period,
                        json.dumps(record.means, ensure_ascii=False),
                        json.dumps(record.std_devs, ensure_ascii=False),
                        json.dumps(record.seasonality, ensure_ascii=False),
                        json.dumps(record.abc_curve, ensure_ascii=False),
                        int(record.sample_size),
                    ),
                )
            finally:
                cur.close()
        return record.snapshot_id

    def get_latest_business_profile(
        self,
        tenant_id: str,
        pack_id: str,
    ) -> BusinessProfileSnapshotRecord | None:
        """Retorna o snapshot estatistico mais recente do tenant_id e pack_id."""
        norm_pack = pack_id.strip().lower()
        with self._connection_scope(tenant_id) as conn:
            p = self._ph(conn)
            cur = conn.cursor()
            try:
                cur.execute(
                    f"""
                    SELECT snapshot_id, tenant_id, pack_id, reference_period,
                           means_json, std_devs_json, seasonality_json, abc_curve_json,
                           sample_size
                    FROM business_profile_snapshots
                    WHERE tenant_id = {p} AND pack_id = {p}
                    ORDER BY computed_at DESC, rowid DESC
                    LIMIT 1;
                    """
                    if self._resolve_dialect(conn) == "sqlite"
                    else f"""
                    SELECT snapshot_id, tenant_id, pack_id, reference_period,
                           means_json, std_devs_json, seasonality_json, abc_curve_json,
                           sample_size
                    FROM business_profile_snapshots
                    WHERE tenant_id = {p} AND pack_id = {p}
                    ORDER BY computed_at DESC
                    LIMIT 1;
                    """,
                    (tenant_id, norm_pack),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return BusinessProfileSnapshotRecord(
                    snapshot_id=str(row[0]),
                    tenant_id=str(row[1]),
                    pack_id=str(row[2]),
                    reference_period=str(row[3]),
                    means=json.loads(row[4]),
                    std_devs=json.loads(row[5]),
                    seasonality=json.loads(row[6]),
                    abc_curve=json.loads(row[7]),
                    sample_size=int(row[8]),
                )
            finally:
                cur.close()

    def save_business_rule(self, rule: BusinessRule) -> str:
        """Insere ou atualiza regra estruturada em business_memory_rules."""
        norm_pack = rule.pack_id.strip().lower()
        with self._connection_scope(rule.tenant_id) as conn:
            p = self._ph(conn)
            cur = conn.cursor()
            try:
                cur.execute(
                    f"SELECT rule_id FROM business_memory_rules WHERE rule_id = {p};",
                    (rule.rule_id,),
                )
                exists = cur.fetchone() is not None
                if exists:
                    cur.execute(
                        f"""
                        UPDATE business_memory_rules
                        SET rule_key = {p}, metric = {p}, operator = {p},
                            threshold_value = {p}, threshold_upper = {p},
                            severity = {p}, status = {p}, origin = {p},
                            author = {p}, description = {p}, updated_at = CURRENT_TIMESTAMP
                        WHERE rule_id = {p} AND tenant_id = {p} AND pack_id = {p};
                        """,
                        (
                            rule.rule_key,
                            rule.metric,
                            rule.operator,
                            float(rule.threshold_value),
                            float(rule.threshold_upper) if rule.threshold_upper is not None else None,
                            rule.severity,
                            rule.status,
                            rule.origin,
                            rule.author,
                            rule.description,
                            rule.rule_id,
                            rule.tenant_id,
                            norm_pack,
                        ),
                    )
                else:
                    cur.execute(
                        f"""
                        INSERT INTO business_memory_rules (
                            rule_id, tenant_id, pack_id, rule_key, metric,
                            operator, threshold_value, threshold_upper,
                            severity, status, origin, author, description
                        ) VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p});
                        """,
                        (
                            rule.rule_id,
                            rule.tenant_id,
                            norm_pack,
                            rule.rule_key,
                            rule.metric,
                            rule.operator,
                            float(rule.threshold_value),
                            float(rule.threshold_upper) if rule.threshold_upper is not None else None,
                            rule.severity,
                            rule.status,
                            rule.origin,
                            rule.author,
                            rule.description,
                        ),
                    )
            finally:
                cur.close()
        return rule.rule_id

    def list_business_rules(
        self,
        tenant_id: str,
        pack_id: str,
        status: str | None = "active",
    ) -> list[BusinessRule]:
        """Lista regras do tenant_id e pack_id filtrando opcionalmente por status."""
        norm_pack = pack_id.strip().lower()
        with self._connection_scope(tenant_id) as conn:
            p = self._ph(conn)
            cur = conn.cursor()
            try:
                if status is not None:
                    cur.execute(
                        f"""
                        SELECT rule_id, tenant_id, pack_id, rule_key, metric,
                               operator, threshold_value, threshold_upper,
                               severity, status, origin, author, description
                        FROM business_memory_rules
                        WHERE tenant_id = {p} AND pack_id = {p} AND status = {p}
                        ORDER BY created_at ASC, rule_id ASC;
                        """,
                        (tenant_id, norm_pack, status),
                    )
                else:
                    cur.execute(
                        f"""
                        SELECT rule_id, tenant_id, pack_id, rule_key, metric,
                               operator, threshold_value, threshold_upper,
                               severity, status, origin, author, description
                        FROM business_memory_rules
                        WHERE tenant_id = {p} AND pack_id = {p}
                        ORDER BY created_at ASC, rule_id ASC;
                        """,
                        (tenant_id, norm_pack),
                    )
                rows = cur.fetchall()
                return [
                    BusinessRule(
                        rule_id=str(r[0]),
                        tenant_id=str(r[1]),
                        pack_id=str(r[2]),
                        rule_key=str(r[3]),
                        metric=str(r[4]),
                        operator=str(r[5]),  # type: ignore[arg-type]
                        threshold_value=float(r[6]),
                        threshold_upper=float(r[7]) if r[7] is not None else None,
                        severity=str(r[8]),  # type: ignore[arg-type]
                        status=str(r[9]),  # type: ignore[arg-type]
                        source="business_memory",
                        origin=str(r[10]),
                        author=str(r[11]),
                        description=str(r[12] or ""),
                    )
                    for r in rows
                ]
            finally:
                cur.close()

    def get_business_rule(
        self,
        rule_id: str,
        tenant_id: str,
        pack_id: str,
    ) -> BusinessRule | None:
        """Retorna uma regra especifica isolada por rule_id, tenant_id e pack_id."""
        norm_pack = pack_id.strip().lower()
        with self._connection_scope(tenant_id) as conn:
            p = self._ph(conn)
            cur = conn.cursor()
            try:
                cur.execute(
                    f"""
                    SELECT rule_id, tenant_id, pack_id, rule_key, metric,
                           operator, threshold_value, threshold_upper,
                           severity, status, origin, author, description
                    FROM business_memory_rules
                    WHERE rule_id = {p} AND tenant_id = {p} AND pack_id = {p}
                    LIMIT 1;
                    """,
                    (rule_id, tenant_id, norm_pack),
                )
                r = cur.fetchone()
                if not r:
                    return None
                return BusinessRule(
                    rule_id=str(r[0]),
                    tenant_id=str(r[1]),
                    pack_id=str(r[2]),
                    rule_key=str(r[3]),
                    metric=str(r[4]),
                    operator=str(r[5]),  # type: ignore[arg-type]
                    threshold_value=float(r[6]),
                    threshold_upper=float(r[7]) if r[7] is not None else None,
                    severity=str(r[8]),  # type: ignore[arg-type]
                    status=str(r[9]),  # type: ignore[arg-type]
                    source="business_memory",
                    origin=str(r[10]),
                    author=str(r[11]),
                    description=str(r[12] or ""),
                )
            finally:
                cur.close()

    def update_business_rule_status(
        self,
        rule_id: str,
        tenant_id: str,
        pack_id: str,
        new_status: str,
        decided_by: str | None = None,
        description_suffix: str | None = None,
    ) -> BusinessRule | None:
        """Atualiza o status HiC de uma regra isolada por tenant_id e pack_id."""
        if new_status not in ("candidate", "active", "rejected"):
            raise ValueError(f"Status de regra invalido: '{new_status}'.")
        existing = self.get_business_rule(
            rule_id=rule_id,
            tenant_id=tenant_id,
            pack_id=pack_id,
        )
        if existing is None:
            return None

        norm_pack = pack_id.strip().lower()
        updated_desc = existing.description
        if description_suffix:
            clean_suffix = sanitize_text(description_suffix).strip()
            if clean_suffix:
                updated_desc = f"{updated_desc} | {clean_suffix}".strip(" |")
        updated_author = _sanitize_signal_token(decided_by, max_len=64) if decided_by else existing.author

        with self._connection_scope(tenant_id) as conn:
            p = self._ph(conn)
            cur = conn.cursor()
            try:
                cur.execute(
                    f"""
                    UPDATE business_memory_rules
                    SET status = {p}, author = {p}, description = {p},
                        updated_at = CURRENT_TIMESTAMP
                    WHERE rule_id = {p} AND tenant_id = {p} AND pack_id = {p};
                    """,
                    (
                        new_status,
                        updated_author,
                        updated_desc,
                        rule_id,
                        tenant_id,
                        norm_pack,
                    ),
                )
            finally:
                cur.close()

        return self.get_business_rule(
            rule_id=rule_id,
            tenant_id=tenant_id,
            pack_id=pack_id,
        )

    def record_operator_intent_signal(
        self,
        tenant_id: str,
        pack_id: str,
        entity_type: str,
        metric_key: str,
        topic_key: str,
        intent_name: str,
        increment: int = 1,
    ) -> str:
        """Registra telemetria agregada de intencao com sanitizacao estrita zero-PII."""
        norm_pack = pack_id.strip().lower()
        safe_entity = _sanitize_signal_token(entity_type)
        safe_metric = _sanitize_signal_token(metric_key)
        safe_topic = _sanitize_signal_token(topic_key)
        safe_intent = _sanitize_signal_token(intent_name)
        inc = max(1, int(increment))

        with self._connection_scope(tenant_id) as conn:
            p = self._ph(conn)
            cur = conn.cursor()
            try:
                cur.execute(
                    f"""
                    SELECT signal_id, hit_count
                    FROM operator_intent_signals
                    WHERE tenant_id = {p} AND pack_id = {p}
                      AND entity_type = {p} AND metric_key = {p}
                      AND topic_key = {p} AND intent_name = {p}
                    LIMIT 1;
                    """,
                    (tenant_id, norm_pack, safe_entity, safe_metric, safe_topic, safe_intent),
                )
                row = cur.fetchone()
                if row:
                    signal_id = str(row[0])
                    cur.execute(
                        f"""
                        UPDATE operator_intent_signals
                        SET hit_count = hit_count + {p}, last_seen_at = CURRENT_TIMESTAMP
                        WHERE signal_id = {p};
                        """,
                        (inc, signal_id),
                    )
                    return signal_id

                signal_id = f"sig_{uuid.uuid4().hex[:16]}"
                cur.execute(
                    f"""
                    INSERT INTO operator_intent_signals (
                        signal_id, tenant_id, pack_id, entity_type,
                        metric_key, topic_key, intent_name, hit_count
                    ) VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p});
                    """,
                    (
                        signal_id,
                        tenant_id,
                        norm_pack,
                        safe_entity,
                        safe_metric,
                        safe_topic,
                        safe_intent,
                        inc,
                    ),
                )
                return signal_id
            finally:
                cur.close()

    def list_recent_intent_signals(
        self,
        tenant_id: str,
        pack_id: str,
        since_dt: datetime,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Lista sinais de intencao recentes do tenant_id e pack_id dentro da janela."""
        norm_pack = pack_id.strip().lower()
        safe_limit = max(1, min(500, int(limit)))
        utc_dt = since_dt.astimezone(UTC) if since_dt.tzinfo else since_dt.replace(tzinfo=UTC)

        with self._connection_scope(tenant_id) as conn:
            dialect = self._resolve_dialect(conn)
            p = self._ph(conn)
            since_param = (
                utc_dt.strftime("%Y-%m-%d %H:%M:%S")
                if dialect == "sqlite"
                else utc_dt.isoformat()
            )
            cur = conn.cursor()
            try:
                cur.execute(
                    f"""
                    SELECT signal_id, tenant_id, pack_id, entity_type,
                           metric_key, topic_key, intent_name, hit_count,
                           first_seen_at, last_seen_at
                    FROM operator_intent_signals
                    WHERE tenant_id = {p} AND pack_id = {p} AND last_seen_at >= {p}
                    ORDER BY hit_count DESC, last_seen_at DESC
                    LIMIT {p};
                    """,
                    (tenant_id, norm_pack, since_param, safe_limit),
                )
                rows = cur.fetchall()
                return [
                    {
                        "signal_id": str(r[0]),
                        "tenant_id": str(r[1]),
                        "pack_id": str(r[2]),
                        "entity_type": str(r[3]),
                        "metric_key": str(r[4]),
                        "topic_key": str(r[5]),
                        "intent_name": str(r[6]),
                        "hit_count": int(r[7]),
                        "first_seen_at": str(r[8]) if r[8] is not None else None,
                        "last_seen_at": str(r[9]) if r[9] is not None else None,
                    }
                    for r in rows
                ]
            finally:
                cur.close()

    def save_simulation_snapshot(
        self,
        simulation_id: str,
        tenant_id: str,
        pack_id: str,
        scenario_type: str,
        horizon_days: int,
        baseline: SimulationBaseline,
        shocks: ShockVector,
        p10_value: float,
        p50_value: float,
        p90_value: float,
        sensitivity: list[SensitivityDriver],
        violated_rules: list[RuleViolation],
        seed: int,
        iterations: int,
        created_by: str,
    ) -> str:
        """Grava snapshot imutavel de simulacao; rejeita sobrescrita do mesmo simulation_id."""
        norm_pack = pack_id.strip().lower()
        with self._connection_scope(tenant_id) as conn:
            p = self._ph(conn)
            cur = conn.cursor()
            try:
                cur.execute(
                    f"SELECT 1 FROM simulation_snapshots WHERE simulation_id = {p};",
                    (simulation_id,),
                )
                if cur.fetchone() is not None:
                    raise ValueError(
                        f"simulation_snapshot '{simulation_id}' e imutavel e nao pode ser sobrescrito."
                    )

                cur.execute(
                    f"""
                    INSERT INTO simulation_snapshots (
                        simulation_id, tenant_id, pack_id, scenario_type, horizon_days,
                        baseline_t0_json, shock_params_json,
                        p10_value, p50_value, p90_value,
                        sensitivity_json, violated_rules_json,
                        seed, iterations, created_by
                    ) VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p});
                    """,
                    (
                        simulation_id,
                        tenant_id,
                        norm_pack,
                        scenario_type,
                        int(horizon_days),
                        json.dumps(baseline.model_dump(mode="json"), ensure_ascii=False),
                        json.dumps(shocks.model_dump(mode="json"), ensure_ascii=False),
                        float(p10_value),
                        float(p50_value),
                        float(p90_value),
                        json.dumps([s.model_dump(mode="json") for s in sensitivity], ensure_ascii=False),
                        json.dumps([v.model_dump(mode="json") for v in violated_rules], ensure_ascii=False),
                        int(seed),
                        int(iterations),
                        _sanitize_signal_token(created_by, max_len=64),
                    ),
                )
            finally:
                cur.close()
        return simulation_id

    def get_simulation_snapshot(
        self,
        simulation_id: str,
        tenant_id: str,
        pack_id: str,
    ) -> dict[str, Any] | None:
        """Busca snapshot imutavel estritamente isolado por (simulation_id, tenant_id, pack_id)."""
        norm_pack = pack_id.strip().lower()
        with self._connection_scope(tenant_id) as conn:
            p = self._ph(conn)
            cur = conn.cursor()
            try:
                cur.execute(
                    f"""
                    SELECT simulation_id, tenant_id, pack_id, scenario_type, horizon_days,
                           baseline_t0_json, shock_params_json,
                           p10_value, p50_value, p90_value,
                           sensitivity_json, violated_rules_json,
                           seed, iterations, created_by, created_at,
                           realized_outcome_json, realized_at
                    FROM simulation_snapshots
                    WHERE simulation_id = {p} AND tenant_id = {p} AND pack_id = {p}
                    LIMIT 1;
                    """,
                    (simulation_id, tenant_id, norm_pack),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "simulation_id": str(row[0]),
                    "tenant_id": str(row[1]),
                    "pack_id": str(row[2]),
                    "scenario_type": str(row[3]),
                    "horizon_days": int(row[4]),
                    "baseline": json.loads(row[5]),
                    "shocks": json.loads(row[6]),
                    "p10_value": float(row[7]),
                    "p50_value": float(row[8]),
                    "p90_value": float(row[9]),
                    "sensitivity": json.loads(row[10]),
                    "violated_rules": json.loads(row[11]),
                    "seed": int(row[12]),
                    "iterations": int(row[13]),
                    "created_by": str(row[14]),
                    "created_at": str(row[15]) if row[15] is not None else None,
                    "realized_outcome": json.loads(row[16]) if row[16] else None,
                    "realized_at": str(row[17]) if row[17] is not None else None,
                }
            finally:
                cur.close()

    def record_realized_outcome(
        self,
        simulation_id: str,
        tenant_id: str,
        pack_id: str,
        realized_outcome: dict[str, Any],
    ) -> bool:
        """Registra o desfecho real posterior de forma unica (append-only sobre realized_outcome)."""
        norm_pack = pack_id.strip().lower()
        with self._connection_scope(tenant_id) as conn:
            p = self._ph(conn)
            cur = conn.cursor()
            try:
                cur.execute(
                    f"""
                    SELECT realized_outcome_json
                    FROM simulation_snapshots
                    WHERE simulation_id = {p} AND tenant_id = {p} AND pack_id = {p}
                    LIMIT 1;
                    """,
                    (simulation_id, tenant_id, norm_pack),
                )
                row = cur.fetchone()
                if row is None:
                    return False
                if row[0] is not None:
                    raise ValueError(
                        f"Resultado realizado de '{simulation_id}' ja foi registrado e e imutavel."
                    )

                now_iso = datetime.now(UTC).isoformat()
                cur.execute(
                    f"""
                    UPDATE simulation_snapshots
                    SET realized_outcome_json = {p}, realized_at = {p}
                    WHERE simulation_id = {p} AND tenant_id = {p} AND pack_id = {p};
                    """,
                    (
                        json.dumps(realized_outcome, ensure_ascii=False),
                        now_iso,
                        simulation_id,
                        tenant_id,
                        norm_pack,
                    ),
                )
                return True
            finally:
                cur.close()


__all__ = ["SimulationRepository"]
