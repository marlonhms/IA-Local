"""
Modulo de Memoria de Resultado - Closed-Loop ROI Tracking (Fase 2 - Roadmap Next-Gen).
Audita em T+24h, T+7d e T+30d o impacto financeiro real no ERP das acoes aprovadas
pelo gestor no AuraCommandJournal, descontando sazonalidade semanal e alimentando
automaticamente a TenantMemoryManager com estrategias comprovadas.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from config.settings import BASE_DIR
from core.logger import logger
from core.schemas.genui import RealizedRoiItem, RealizedRoiScorecardProps

DEFAULT_OUTCOMES_DB_PATH = BASE_DIR / "data" / "aura_outcomes.db"
VALID_FEEDBACKS = {"CONFIRMED", "DISPUTED"}


class OutcomeStatus(str, Enum):
    """Estados do ciclo de auditoria de resultado de uma recomendacao."""

    PENDING_24H = "PENDING_24H"
    PENDING_7D = "PENDING_7D"
    PENDING_30D = "PENDING_30D"
    COMPLETED = "COMPLETED"
    INCONCLUSIVE = "INCONCLUSIVE"


class OutcomeFeedbackRequest(BaseModel):
    """Payload de confirmacao ou contestacao do gestor sobre um outcome."""

    feedback: str = Field(..., description="CONFIRMED ou DISPUTED")
    note: str | None = Field(default=None, description="Observacao opcional do gestor")


def compute_realized_impact(
    baseline_daily_profit_brl: float,
    observed_daily_profit_brl: float,
    seasonality_factor: float = 1.0,
    days_elapsed: int = 1,
) -> tuple[float, float]:
    """
    Calcula o impacto financeiro realizado descontando a sazonalidade do dia da semana.
    Retorna (realized_brl, attribution_confidence).
    """
    safe_seasonality = float(seasonality_factor) if seasonality_factor and seasonality_factor > 0 else 1.0
    safe_days = max(1, int(days_elapsed))
    expected_without_action = float(baseline_daily_profit_brl) * safe_seasonality
    daily_delta = float(observed_daily_profit_brl) - expected_without_action
    realized_brl = round(daily_delta * safe_days, 2)
    confidence = 0.85 if baseline_daily_profit_brl > 0 and safe_seasonality != 1.0 else 0.65
    return realized_brl, confidence


def _parse_iso_utc(ts: str | None) -> datetime:
    """Converte timestamp ISO-8601 em datetime UTC aware."""
    if not ts:
        return datetime.now(UTC)
    dt = datetime.fromisoformat(ts)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


class OutcomeTracker:
    """
    Rastreador de retorno financeiro realizado (Closed-Loop ROI Tracking).
    Persiste auditorias em SQLite WAL sem gravar nada no ERP transacional.
    """

    def __init__(
        self,
        db_path: Path | str = DEFAULT_OUTCOMES_DB_PATH,
        tenant_memory: Any | None = None,
    ) -> None:
        self.db_path_str = str(db_path)
        self._tenant_memory = tenant_memory
        self._lock = threading.Lock()
        self._mem_conn: sqlite3.Connection | None = None

        if self.db_path_str != ":memory:":
            Path(self.db_path_str).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """Abre conexao SQLite configurada com WAL e timeout seguro."""
        if self.db_path_str == ":memory:":
            if self._mem_conn is None:
                self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._mem_conn.row_factory = sqlite3.Row
            return self._mem_conn

        conn = sqlite3.connect(self.db_path_str, timeout=5.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _close_conn(self, conn: sqlite3.Connection) -> None:
        """Fecha conexao SQLite caso nao seja instancia compartilhada em memoria."""
        if self.db_path_str != ":memory:":
            conn.close()

    def _init_db(self) -> None:
        """Inicializa tabela aura_decision_outcomes e indice por tenant/status."""
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS aura_decision_outcomes (
                        outcome_id TEXT PRIMARY KEY,
                        command_id TEXT NOT NULL UNIQUE,
                        tenant_id TEXT NOT NULL,
                        filial_id TEXT NOT NULL,
                        action_type TEXT NOT NULL,
                        target_entity TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        baseline_snapshot_json TEXT NOT NULL,
                        predicted_impact_brl REAL NOT NULL,
                        check_24h_at TEXT,
                        realized_24h_brl REAL,
                        check_7d_at TEXT,
                        realized_7d_brl REAL,
                        check_30d_at TEXT,
                        realized_30d_brl REAL,
                        attribution_confidence REAL DEFAULT 0.0,
                        status TEXT NOT NULL DEFAULT 'PENDING_24H',
                        manager_feedback TEXT
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_outcomes_status_tenant
                    ON aura_decision_outcomes(tenant_id, status)
                    """
                )
                conn.commit()
            finally:
                self._close_conn(conn)

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        """Converte linha SQLite em dicionario Python serializavel."""
        baseline: dict[str, Any] = {}
        with suppress(json.JSONDecodeError, TypeError):
            baseline = json.loads(row["baseline_snapshot_json"] or "{}")

        latest_realized = (
            row["realized_30d_brl"]
            if row["realized_30d_brl"] is not None
            else (
                row["realized_7d_brl"]
                if row["realized_7d_brl"] is not None
                else (row["realized_24h_brl"] if row["realized_24h_brl"] is not None else 0.0)
            )
        )
        return {
            "outcome_id": row["outcome_id"],
            "command_id": row["command_id"],
            "tenant_id": row["tenant_id"],
            "filial_id": row["filial_id"],
            "action_type": row["action_type"],
            "target_entity": row["target_entity"],
            "created_at": row["created_at"],
            "baseline_snapshot": baseline,
            "predicted_impact_brl": float(row["predicted_impact_brl"]),
            "check_24h_at": row["check_24h_at"],
            "realized_24h_brl": row["realized_24h_brl"],
            "check_7d_at": row["check_7d_at"],
            "realized_7d_brl": row["realized_7d_brl"],
            "check_30d_at": row["check_30d_at"],
            "realized_30d_brl": row["realized_30d_brl"],
            "latest_realized_brl": float(latest_realized),
            "attribution_confidence": float(row["attribution_confidence"] or 0.0),
            "status": row["status"],
            "manager_feedback": row["manager_feedback"],
        }

    def register_outcome(
        self,
        command_id: str,
        tenant_id: str,
        filial_id: str,
        action_type: str,
        target_entity: str,
        baseline_snapshot: dict[str, Any],
        predicted_impact_brl: float,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        """
        Registra de forma idempotente uma acao aprovada para acompanhamento em T+24h/7d/30d.
        Se command_id ja existir, retorna o registro existente sem duplicar.
        """
        cmd_id = str(command_id or "").strip()
        if not cmd_id:
            raise ValueError("command_id e obrigatorio para register_outcome.")

        with self._lock:
            conn = self._connect()
            try:
                existing = conn.execute(
                    "SELECT * FROM aura_decision_outcomes WHERE command_id = ?",
                    (cmd_id,),
                ).fetchone()
                if existing is not None:
                    return self._row_to_dict(existing)

                outcome_id = f"out_{uuid.uuid4().hex[:12]}"
                ts = created_at or datetime.now(UTC).isoformat()
                baseline_json = json.dumps(baseline_snapshot or {}, ensure_ascii=False)
                conn.execute(
                    """
                    INSERT INTO aura_decision_outcomes (
                        outcome_id, command_id, tenant_id, filial_id, action_type,
                        target_entity, created_at, baseline_snapshot_json,
                        predicted_impact_brl, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        outcome_id,
                        cmd_id,
                        str(tenant_id or "posto_local").strip(),
                        str(filial_id or "1").strip(),
                        str(action_type or "GENERIC_ACTION").strip(),
                        str(target_entity or "geral").strip(),
                        ts,
                        baseline_json,
                        round(float(predicted_impact_brl or 0.0), 2),
                        OutcomeStatus.PENDING_24H.value,
                    ),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT * FROM aura_decision_outcomes WHERE outcome_id = ?",
                    (outcome_id,),
                ).fetchone()
                return self._row_to_dict(row)
            finally:
                self._close_conn(conn)

    def register_from_command(self, entry: Any) -> dict[str, Any]:
        """Extrai contexto financeiro de uma entrada do AuraCommandJournal e registra outcome."""
        req = getattr(entry, "request_payload", None)
        if not isinstance(req, dict):
            req = {}
        res = getattr(entry, "result_payload", None)
        if not isinstance(res, dict):
            res = {}

        command_id = str(
            getattr(entry, "journal_id", None)
            or getattr(entry, "command_key", None)
            or getattr(entry, "action_id", "")
        )
        tenant_id = str(req.get("tenant_id") or res.get("tenant_id") or "posto_local")
        filial_id = str(req.get("filial_id") or req.get("station_id") or res.get("filial_id") or "1")
        action_type = str(getattr(entry, "action_type", None) or req.get("action_type") or "EXECUTIVE_ACTION")
        target_entity = str(
            req.get("target_entity")
            or req.get("product")
            or req.get("fuel_type")
            or req.get("entity_id")
            or res.get("target_entity")
            or "operacao_geral"
        )
        predicted = float(
            req.get("predicted_impact_brl")
            or res.get("predicted_impact_brl")
            or res.get("estimated_monthly_recovery_brl")
            or 0.0
        )
        baseline_daily_profit = float(
            req.get("baseline_daily_profit_brl")
            or res.get("baseline_daily_profit_brl")
            or 0.0
        )
        baseline_snapshot = {
            "daily_profit_brl": baseline_daily_profit,
            "request_action_id": getattr(entry, "action_id", None),
            "actor": getattr(entry, "actor", "gestor"),
        }
        return self.register_outcome(
            command_id=command_id,
            tenant_id=tenant_id,
            filial_id=filial_id,
            action_type=action_type,
            target_entity=target_entity,
            baseline_snapshot=baseline_snapshot,
            predicted_impact_brl=predicted,
        )

    def get_outcome(self, outcome_id: str) -> dict[str, Any] | None:
        """Retorna um outcome especifico por outcome_id."""
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM aura_decision_outcomes WHERE outcome_id = ?",
                    (outcome_id,),
                ).fetchone()
                return self._row_to_dict(row) if row else None
            finally:
                self._close_conn(conn)

    def _learn_validated_strategy(self, outcome: dict[str, Any], realized_brl: float) -> None:
        """Registra estrategia comprovada na camada TenantMemoryManager quando positiva."""
        if realized_brl <= 0:
            return
        mem = self._tenant_memory
        if mem is None:
            if self.db_path_str == ":memory:":
                return
            try:
                from core.tenant_memory import TenantMemoryManager

                mem = TenantMemoryManager()
            except (ImportError, OSError):
                return

        with suppress(ValueError, OSError, sqlite3.Error):
            filial_digits = "".join(ch for ch in str(outcome.get("filial_id", "1")) if ch.isdigit())
            filial_num = int(filial_digits) if filial_digits else 1
            mem.learn_fact(
                tenant_id=str(outcome["tenant_id"]),
                filial_id=filial_num,
                categoria="estrategia_validada",
                chave=f"{outcome['action_type']}:{outcome['target_entity']}"[:100],
                conteudo=(
                    f"Acao {outcome['action_type']} em {outcome['target_entity']} gerou retorno "
                    f"auditado de R$ {realized_brl:.2f} (confianca {outcome['attribution_confidence']:.0%})."
                ),
                status="ativo",
                origem="api",
                confianca=float(outcome["attribution_confidence"] or 0.8),
                metadata={
                    "outcome_id": outcome["outcome_id"],
                    "predicted_brl": outcome["predicted_impact_brl"],
                    "realized_brl": realized_brl,
                },
            )

    def audit_outcome(
        self,
        outcome_id: str,
        observed_daily_profit_brl: float,
        seasonality_factor: float = 1.0,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Executa a auditoria da proxima janela pendente (24h -> 7d -> 30d -> COMPLETED),
        calculando impacto realizado deterministico e gravando aprendizado quando concluido.
        """
        audit_dt = now or datetime.now(UTC)
        audit_iso = audit_dt.isoformat()

        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM aura_decision_outcomes WHERE outcome_id = ?",
                    (outcome_id,),
                ).fetchone()
                if row is None:
                    raise KeyError(f"Outcome '{outcome_id}' nao encontrado.")

                current = self._row_to_dict(row)
                status = current["status"]
                if status in (OutcomeStatus.COMPLETED.value, OutcomeStatus.INCONCLUSIVE.value):
                    return current

                baseline_profit = float(current["baseline_snapshot"].get("daily_profit_brl", 0.0))

                if status == OutcomeStatus.PENDING_24H.value:
                    realized, conf = compute_realized_impact(
                        baseline_profit, observed_daily_profit_brl, seasonality_factor, days_elapsed=1
                    )
                    next_status = OutcomeStatus.PENDING_7D.value
                    conn.execute(
                        """
                        UPDATE aura_decision_outcomes
                        SET check_24h_at = ?, realized_24h_brl = ?, attribution_confidence = ?, status = ?
                        WHERE outcome_id = ?
                        """,
                        (audit_iso, realized, conf, next_status, outcome_id),
                    )
                elif status == OutcomeStatus.PENDING_7D.value:
                    realized, conf = compute_realized_impact(
                        baseline_profit, observed_daily_profit_brl, seasonality_factor, days_elapsed=7
                    )
                    next_status = OutcomeStatus.PENDING_30D.value
                    conn.execute(
                        """
                        UPDATE aura_decision_outcomes
                        SET check_7d_at = ?, realized_7d_brl = ?, attribution_confidence = ?, status = ?
                        WHERE outcome_id = ?
                        """,
                        (audit_iso, realized, conf, next_status, outcome_id),
                    )
                else:
                    realized, conf = compute_realized_impact(
                        baseline_profit, observed_daily_profit_brl, seasonality_factor, days_elapsed=30
                    )
                    next_status = OutcomeStatus.COMPLETED.value
                    conn.execute(
                        """
                        UPDATE aura_decision_outcomes
                        SET check_30d_at = ?, realized_30d_brl = ?, attribution_confidence = ?, status = ?
                        WHERE outcome_id = ?
                        """,
                        (audit_iso, realized, conf, next_status, outcome_id),
                    )

                conn.commit()
                updated_row = conn.execute(
                    "SELECT * FROM aura_decision_outcomes WHERE outcome_id = ?",
                    (outcome_id,),
                ).fetchone()
                updated = self._row_to_dict(updated_row)
            finally:
                self._close_conn(conn)

        if updated["status"] == OutcomeStatus.COMPLETED.value:
            self._learn_validated_strategy(updated, updated["latest_realized_brl"])

        return updated

    def audit_pending_outcomes(
        self,
        metric_fetcher: Callable[[dict[str, Any]], tuple[float, float] | None] | None = None,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Varre auditorias pendentes cuja janela temporal ja venceu (T+24h, T+7d, T+30d).
        Projetado para execucao periodica no AuraProactiveDaemon (a cada 6h).
        """
        current_dt = now or datetime.now(UTC)
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    """
                    SELECT * FROM aura_decision_outcomes
                    WHERE status IN ('PENDING_24H', 'PENDING_7D', 'PENDING_30D')
                    ORDER BY created_at ASC
                    """
                ).fetchall()
                candidates = [self._row_to_dict(r) for r in rows]
            finally:
                self._close_conn(conn)

        audited: list[dict[str, Any]] = []
        for item in candidates:
            created_dt = _parse_iso_utc(item["created_at"])
            status = item["status"]
            required_delta = (
                timedelta(hours=24)
                if status == OutcomeStatus.PENDING_24H.value
                else (timedelta(days=7) if status == OutcomeStatus.PENDING_7D.value else timedelta(days=30))
            )
            if current_dt - created_dt < required_delta:
                continue

            if metric_fetcher is None:
                continue

            fetched = metric_fetcher(item)
            if fetched is None:
                continue
            observed_daily_profit, seasonality = fetched
            audited.append(
                self.audit_outcome(
                    outcome_id=item["outcome_id"],
                    observed_daily_profit_brl=observed_daily_profit,
                    seasonality_factor=seasonality,
                    now=current_dt,
                )
            )
        return audited

    def record_feedback(
        self, outcome_id: str, feedback: str, note: str | None = None
    ) -> dict[str, Any]:
        """Registra confirmacao (CONFIRMED) ou contestacao (DISPUTED) do gestor."""
        norm_fb = str(feedback or "").strip().upper()
        if norm_fb not in VALID_FEEDBACKS:
            raise ValueError(f"Feedback invalido: '{feedback}'. Use CONFIRMED ou DISPUTED.")

        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM aura_decision_outcomes WHERE outcome_id = ?",
                    (outcome_id,),
                ).fetchone()
                if row is None:
                    raise KeyError(f"Outcome '{outcome_id}' nao encontrado.")

                baseline = json.loads(row["baseline_snapshot_json"] or "{}")
                if note:
                    baseline["manager_note"] = note.strip()

                conn.execute(
                    """
                    UPDATE aura_decision_outcomes
                    SET manager_feedback = ?, baseline_snapshot_json = ?
                    WHERE outcome_id = ?
                    """,
                    (norm_fb, json.dumps(baseline, ensure_ascii=False), outcome_id),
                )
                conn.commit()
                updated = conn.execute(
                    "SELECT * FROM aura_decision_outcomes WHERE outcome_id = ?",
                    (outcome_id,),
                ).fetchone()
                return self._row_to_dict(updated)
            finally:
                self._close_conn(conn)

    def get_realized_roi_scorecard(
        self, period_days: int = 30, tenant_id: str | None = None
    ) -> RealizedRoiScorecardProps:
        """Consolida scorecard de retorno previsto vs. realizado no periodo."""
        cutoff = (datetime.now(UTC) - timedelta(days=max(1, int(period_days)))).isoformat()
        with self._lock:
            conn = self._connect()
            try:
                if tenant_id:
                    rows = conn.execute(
                        """
                        SELECT * FROM aura_decision_outcomes
                        WHERE created_at >= ? AND tenant_id = ?
                        ORDER BY created_at DESC
                        """,
                        (cutoff, tenant_id),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT * FROM aura_decision_outcomes
                        WHERE created_at >= ?
                        ORDER BY created_at DESC
                        """,
                        (cutoff,),
                    ).fetchall()
                records = [self._row_to_dict(r) for r in rows]
            finally:
                self._close_conn(conn)

        total_predicted = round(sum(r["predicted_impact_brl"] for r in records), 2)
        total_realized = round(sum(r["latest_realized_brl"] for r in records), 2)

        audited_records = [r for r in records if r["status"] != OutcomeStatus.PENDING_24H.value]
        positive_hits = sum(1 for r in audited_records if r["latest_realized_brl"] > 0)
        hit_rate = round((positive_hits / len(audited_records)) * 100.0, 2) if audited_records else 0.0

        sorted_records = sorted(records, key=lambda x: x["latest_realized_brl"], reverse=True)[:5]
        items: list[RealizedRoiItem] = []
        for r in sorted_records:
            pred = r["predicted_impact_brl"]
            real = r["latest_realized_brl"]
            accuracy = round((real / pred) * 100.0, 2) if pred > 0 else (100.0 if real > 0 else 0.0)
            items.append(
                RealizedRoiItem(
                    outcome_id=r["outcome_id"],
                    action_type=r["action_type"],
                    target_entity=r["target_entity"],
                    predicted_impact_brl=pred,
                    realized_impact_brl=real,
                    accuracy_pct=accuracy,
                    status=r["status"],
                    manager_feedback=r["manager_feedback"],
                )
            )

        return RealizedRoiScorecardProps(
            period_days=int(period_days),
            total_predicted_brl=total_predicted,
            total_realized_brl=total_realized,
            hit_rate_pct=hit_rate,
            items=items,
        )


_tracker_lock = threading.Lock()
_tracker_singleton: OutcomeTracker | None = None


def get_registered_outcome_tracker() -> OutcomeTracker | None:
    """Retorna instancia explicitamente injetada sem criar banco em disco por acidente."""
    with _tracker_lock:
        return _tracker_singleton


def get_outcome_tracker() -> OutcomeTracker:
    """Retorna singleton thread-safe do OutcomeTracker."""
    global _tracker_singleton
    with _tracker_lock:
        if _tracker_singleton is None:
            _tracker_singleton = OutcomeTracker()
            logger.info("OutcomeTracker inicializado em %s", _tracker_singleton.db_path_str)
        return _tracker_singleton


def set_outcome_tracker(tracker: OutcomeTracker | None) -> None:
    """Permite injetar instancia isolada de OutcomeTracker em testes."""
    global _tracker_singleton
    with _tracker_lock:
        _tracker_singleton = tracker


def reset_outcome_tracker() -> None:
    """Reseta singleton do OutcomeTracker."""
    set_outcome_tracker(None)
