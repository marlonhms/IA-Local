"""Motor Deterministico de Backtesting e Auto-Calibracao What-If (Fase 3).

Compara snapshots vencidos (30/60/90d) com resultados realizados no ERP via
SQL estritamente read-only validado por sqlglot (assert_readonly_safe_sql),
registra o desfecho append-only e gera propostas de calibracao sujeitas a
governanca HiC (status='candidate'). Zero LLM e zero travessoes.
"""

from __future__ import annotations

import logging
import re
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable, Mapping

import sqlglot
from sqlglot import exp

from core.simulation.models import (
    BacktestItemResult,
    BacktestRunResponse,
    BusinessRule,
    CalibrationProposal,
    HorizonDays,
    RealizedRoiScorecardResponse,
    ScenarioType,
)
from core.simulation.repository import SimulationRepository, _parse_utc_timestamp
from core.tenancy import ReadOnlySQLViolationError, assert_readonly_safe_sql

logger = logging.getLogger("AuraSimulationBacktest")

_ROUND_2 = Decimal("0.01")
_PARAM_PLACEHOLDER_RE = re.compile(r"%s|\?")
_FORBIDDEN_JOIN_TRIM_FUNCS = frozenset({"trim", "btrim", "ltrim", "rtrim"})

DEFAULT_REALIZED_PROFIT_SQL = """
SELECT
    COALESCE(SUM(i.ipe_vl_total - (i.ipe_qt_item * COALESCE(i.ipe_vl_custo, 0))), 0) AS realized_gross_profit_brl
FROM pedido p
INNER JOIN itemped i ON i.ped_cd_pedido = p.ped_cd_pedido
WHERE p.ped_st_cancelado = 'N'
  AND p.ped_dt_emissao >= %s
  AND p.ped_dt_emissao < %s
""".strip()


def _round_money(value: float) -> float:
    """Arredondamento financeiro deterministico ABNT/SEFAZ (ROUND_HALF_UP)."""
    return float(Decimal(str(value)).quantize(_ROUND_2, rounding=ROUND_HALF_UP))


def build_readonly_realized_sql(custom_sql: str | None = None) -> str:
    """Valida e retorna query SQL read-only via sqlglot Postgres (sem TRIM em JOIN)."""
    sql = (custom_sql or DEFAULT_REALIZED_PROFIT_SQL).strip()
    validated = assert_readonly_safe_sql(sql)

    idx = 0

    def _sub_bind(_m: re.Match[str]) -> str:
        nonlocal idx
        idx += 1
        return f"${idx}"

    ast_sql = _PARAM_PLACEHOLDER_RE.sub(_sub_bind, validated.rstrip(";"))
    tree = sqlglot.parse_one(ast_sql, read="postgres")
    for join_node in tree.find_all(exp.Join):
        for clause_key in ("on", "using"):
            clause = join_node.args.get(clause_key)
            if clause is None:
                continue
            for node in clause.walk():
                if isinstance(node, exp.Trim):
                    raise ReadOnlySQLViolationError(
                        "Consulta SQL rejeitada: uso de TRIM() em clausula JOIN e proibido."
                    )
                if isinstance(node, (exp.Anonymous, exp.Func)):
                    fn_names = {
                        str(getattr(node, "name", "") or "").strip().lower(),
                        str(node.sql_name() if hasattr(node, "sql_name") else "").strip().lower(),
                    }
                    if fn_names & _FORBIDDEN_JOIN_TRIM_FUNCS:
                        raise ReadOnlySQLViolationError(
                            "Consulta SQL rejeitada: uso de TRIM() em clausula JOIN e proibido."
                        )
    return validated


def _baseline_horizon_profit(snapshot: Mapping[str, Any]) -> float:
    """Calcula lucro baseline do horizonte a partir de baseline_t0_json quando disponivel."""
    baseline = snapshot.get("baseline") or {}
    if not isinstance(baseline, Mapping):
        return 0.0
    try:
        unit_price = float(baseline.get("unit_price", 0.0) or 0.0)
        unit_cost = float(baseline.get("unit_cost", 0.0) or 0.0)
        daily_volume = float(baseline.get("daily_volume", 0.0) or 0.0)
        fixed_daily_cost = float(baseline.get("fixed_daily_cost", 0.0) or 0.0)
        horizon_days = int(snapshot.get("horizon_days", 30) or 30)
        return _round_money((((unit_price - unit_cost) * daily_volume) - fixed_daily_cost) * horizon_days)
    except (TypeError, ValueError):
        return 0.0


class SimulationBacktester:
    """Avalia snapshots vencidos (30/60/90d) contra valores realizados e sugere calibracao HiC."""

    def __init__(
        self,
        repository: SimulationRepository,
        realized_fetcher: Callable[[dict[str, Any], datetime, datetime], float | None] | None = None,
        bias_threshold_pct: float = 10.0,
        min_calibration_samples: int = 2,
    ) -> None:
        self._repo = repository
        self._realized_fetcher = realized_fetcher
        self._bias_threshold_pct = max(1.0, float(bias_threshold_pct))
        self._min_calibration_samples = max(1, int(min_calibration_samples))

    def _fetch_realized_delta_from_erp(
        self,
        snapshot: dict[str, Any],
        window_start: datetime,
        window_end: datetime,
    ) -> float | None:
        """Executa consulta read-only validada no ERP para apurar lucro realizado da janela."""
        if self._realized_fetcher is not None:
            return self._realized_fetcher(snapshot, window_start, window_end)

        pack_id = str(snapshot.get("pack_id", "")).strip().lower()
        if pack_id != "fuel_convenience":
            return None

        safe_sql = build_readonly_realized_sql()
        try:
            from core.db_pool import get_erp_db_connection

            with get_erp_db_connection(timeout=3) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(safe_sql, (window_start, window_end))
                    row = cur.fetchone()
                finally:
                    cur.close()
            if not row or row[0] is None:
                return None
            realized_gross_profit = float(row[0])
            baseline_profit = _baseline_horizon_profit(snapshot)
            return _round_money(realized_gross_profit - baseline_profit)
        except Exception as exc:  # noqa: BLE001
            with suppress(Exception):
                logger.debug("ERP indisponivel para backtest read-only (%s): %s", snapshot.get("simulation_id"), exc)
            return None

    @staticmethod
    def compute_backtest_metrics(
        snapshot: Mapping[str, Any],
        realized_brl: float,
        realized_at: str | None = None,
    ) -> BacktestItemResult:
        """Calcula erro absoluto, erro percentual e aderencia a banda P10-P90."""
        p10 = float(snapshot["p10_value"])
        p50 = float(snapshot["p50_value"])
        p90 = float(snapshot["p90_value"])
        realized_rounded = _round_money(float(realized_brl))

        error_brl = _round_money(realized_rounded - p50)
        denom = max(abs(p50), 1.0)
        error_pct = round((abs(realized_rounded - p50) / denom) * 100.0, 2)
        low_band = min(p10, p90)
        high_band = max(p10, p90)
        within_band = low_band <= realized_rounded <= high_band

        horizon_raw = int(snapshot.get("horizon_days", 30))
        horizon: HorizonDays = horizon_raw if horizon_raw in (30, 60, 90) else 30  # type: ignore[assignment]
        scenario: ScenarioType = str(snapshot.get("scenario_type", "price_discount_change"))  # type: ignore[assignment]

        return BacktestItemResult(
            simulation_id=str(snapshot["simulation_id"]),
            scenario_type=scenario,
            horizon_days=horizon,
            created_at=str(snapshot["created_at"]) if snapshot.get("created_at") is not None else None,
            realized_at=realized_at or (str(snapshot["realized_at"]) if snapshot.get("realized_at") is not None else None),
            predicted_p10_brl=_round_money(p10),
            predicted_p50_brl=_round_money(p50),
            predicted_p90_brl=_round_money(p90),
            realized_brl=realized_rounded,
            error_brl=error_brl,
            error_pct=error_pct,
            within_p10_p90=within_band,
        )

    @staticmethod
    def _extract_realized_value(snapshot: Mapping[str, Any]) -> float | None:
        outcome = snapshot.get("realized_outcome")
        if not isinstance(outcome, Mapping):
            return None
        for key in ("realized_brl", "realized_net_delta_brl", "net_profit_delta_brl"):
            if outcome.get(key) is not None:
                try:
                    return float(outcome[key])
                except (TypeError, ValueError):
                    return None
        return None

    def _propose_calibration_if_needed(
        self,
        tenant_id: str,
        pack_id: str,
        realized_items: list[BacktestItemResult],
        dry_run: bool = False,
    ) -> CalibrationProposal | None:
        """Gera proposta HiC (status='candidate') de ajuste de elasticidade quando ha vies sistematico."""
        if len(realized_items) < self._min_calibration_samples:
            return None

        signed_biases = [
            ((item.realized_brl - item.predicted_p50_brl) / max(abs(item.predicted_p50_brl), 1.0)) * 100.0
            for item in realized_items
        ]
        mean_bias_pct = round(sum(signed_biases) / len(signed_biases), 2)
        if abs(mean_bias_pct) < self._bias_threshold_pct:
            return None

        sum_p50 = sum(item.predicted_p50_brl for item in realized_items)
        sum_realized = sum(item.realized_brl for item in realized_items)
        if abs(sum_p50) > 1e-6 and (sum_p50 * sum_realized) >= 0:
            raw_ratio = sum_realized / sum_p50
        else:
            raw_ratio = 1.0 + (mean_bias_pct / 100.0)

        suggested_factor = round(max(0.50, min(1.50, raw_ratio)), 4)
        norm_pack = pack_id.strip().lower()
        rule_id = f"cal_{tenant_id}_{norm_pack}_elasticity"
        reason = (
            f"Backtesting sobre {len(realized_items)} simulacoes identificou vies medio de "
            f"{mean_bias_pct:+.2f}% entre P50 previsto e realizado; fator sugerido {suggested_factor:.4f}."
        )

        if not dry_run:
            existing = self._repo.get_business_rule(
                rule_id=rule_id,
                tenant_id=tenant_id,
                pack_id=norm_pack,
            )
            if existing is None or existing.status != "active":
                rule = BusinessRule(
                    rule_id=rule_id,
                    tenant_id=tenant_id,
                    pack_id=norm_pack,
                    rule_key="elasticity_calibration_factor",
                    metric="elasticity_calibration_factor",
                    operator="==",
                    threshold_value=suggested_factor,
                    severity="MEDIUM",
                    status="candidate",
                    source="business_memory",
                    origin="backtest_calibration",
                    author="backtest_engine",
                    description=reason,
                )
                self._repo.save_business_rule(rule)

        return CalibrationProposal(
            rule_id=rule_id,
            tenant_id=tenant_id,
            pack_id=norm_pack,
            metric="elasticity_calibration_factor",
            current_factor=1.0,
            suggested_factor=suggested_factor,
            mean_bias_pct=mean_bias_pct,
            sample_size=len(realized_items),
            status="candidate",
            reason=reason,
        )

    def run_backtest(
        self,
        tenant_id: str,
        pack_id: str,
        as_of: datetime | None = None,
        limit: int = 50,
        dry_run: bool = False,
    ) -> BacktestRunResponse:
        """Apura snapshots vencidos (30/60/90d), persiste outcomes e sugere calibracao HiC."""
        norm_pack = pack_id.strip().lower()
        ref_dt = as_of or datetime.now(UTC)
        matured = self._repo.list_matured_snapshots(
            tenant_id=tenant_id,
            pack_id=norm_pack,
            as_of_dt=ref_dt,
            only_pending=True,
            limit=limit,
        )

        evaluated_items: list[BacktestItemResult] = []
        now_iso = datetime.now(UTC).isoformat()

        for snap in matured:
            created_dt = _parse_utc_timestamp(snap.get("created_at"))
            if created_dt is None:
                continue
            window_end = created_dt + timedelta(days=int(snap["horizon_days"]))
            realized_brl = self._fetch_realized_delta_from_erp(snap, created_dt, window_end)
            if realized_brl is None:
                continue

            item = self.compute_backtest_metrics(
                snap,
                realized_brl=realized_brl,
                realized_at=now_iso if not dry_run else None,
            )
            evaluated_items.append(item)

            if not dry_run:
                self._repo.record_realized_outcome(
                    simulation_id=item.simulation_id,
                    tenant_id=tenant_id,
                    pack_id=norm_pack,
                    realized_outcome={
                        "realized_brl": item.realized_brl,
                        "predicted_p10_brl": item.predicted_p10_brl,
                        "predicted_p50_brl": item.predicted_p50_brl,
                        "predicted_p90_brl": item.predicted_p90_brl,
                        "error_brl": item.error_brl,
                        "error_pct": item.error_pct,
                        "within_p10_p90": item.within_p10_p90,
                        "evaluated_as_of": ref_dt.astimezone(UTC).isoformat(),
                    },
                )

        all_realized_snaps = self._repo.list_realized_snapshots(
            tenant_id=tenant_id,
            pack_id=norm_pack,
            limit=200,
        )
        all_realized_items: list[BacktestItemResult] = []
        for snap in all_realized_snaps:
            realized_val = self._extract_realized_value(snap)
            if realized_val is not None:
                all_realized_items.append(self.compute_backtest_metrics(snap, realized_val))
        if dry_run:
            seen_ids = {item.simulation_id for item in all_realized_items}
            for item in evaluated_items:
                if item.simulation_id not in seen_ids:
                    all_realized_items.append(item)

        proposal = self._propose_calibration_if_needed(
            tenant_id=tenant_id,
            pack_id=norm_pack,
            realized_items=all_realized_items,
            dry_run=dry_run,
        )

        return BacktestRunResponse(
            tenant_id=tenant_id,
            pack_id=norm_pack,
            evaluated_count=len(evaluated_items),
            items=evaluated_items,
            calibration_proposal=proposal,
            llm_calls=0,
        )

    def build_scorecard(
        self,
        tenant_id: str,
        pack_id: str,
        limit: int = 20,
    ) -> RealizedRoiScorecardResponse:
        """Agrega Previsto (P50) vs. Realizado, hit-rate P10-P90 e calibracao HiC pendente."""
        norm_pack = pack_id.strip().lower()
        realized_snaps = self._repo.list_realized_snapshots(
            tenant_id=tenant_id,
            pack_id=norm_pack,
            limit=limit,
        )

        items: list[BacktestItemResult] = []
        for snap in realized_snaps:
            realized_val = self._extract_realized_value(snap)
            if realized_val is not None:
                items.append(self.compute_backtest_metrics(snap, realized_val))

        count = len(items)
        projected_brl = _round_money(sum(it.predicted_p50_brl for it in items))
        realized_brl = _round_money(sum(it.realized_brl for it in items))
        within_hits = sum(1 for it in items if it.within_p10_p90)
        hit_rate_pct = round((within_hits / count) * 100.0, 2) if count > 0 else 0.0
        mean_abs_error_pct = round(sum(it.error_pct for it in items) / count, 2) if count > 0 else 0.0
        roi_multiple = round(realized_brl / projected_brl, 2) if abs(projected_brl) > 1e-6 else 0.0
        max_horizon = max((int(it.horizon_days) for it in items), default=90)

        pending_calibration: CalibrationProposal | None = None
        candidate_rules = self._repo.list_business_rules(
            tenant_id=tenant_id,
            pack_id=norm_pack,
            status="candidate",
        )
        for rule in candidate_rules:
            if rule.origin == "backtest_calibration" or rule.rule_key == "elasticity_calibration_factor":
                signed_biases = [
                    ((it.realized_brl - it.predicted_p50_brl) / max(abs(it.predicted_p50_brl), 1.0)) * 100.0
                    for it in items
                ]
                mean_bias = round(sum(signed_biases) / len(signed_biases), 2) if signed_biases else 0.0
                pending_calibration = CalibrationProposal(
                    rule_id=rule.rule_id,
                    tenant_id=rule.tenant_id,
                    pack_id=rule.pack_id,
                    metric=rule.metric,
                    current_factor=1.0,
                    suggested_factor=float(rule.threshold_value),
                    mean_bias_pct=mean_bias,
                    sample_size=count,
                    status=rule.status,
                    reason=rule.description,
                )
                break

        return RealizedRoiScorecardResponse(
            tenant_id=tenant_id,
            pack_id=norm_pack,
            period_days=max_horizon,
            projected_brl=projected_brl,
            realized_brl=realized_brl,
            total_realized_brl=realized_brl,
            hit_rate_pct=hit_rate_pct,
            mean_abs_error_pct=mean_abs_error_pct,
            roi_multiple=roi_multiple,
            audited_actions_count=count,
            items=items,
            pending_calibration=pending_calibration,
            llm_calls=0,
        )


__all__ = [
    "DEFAULT_REALIZED_PROFIT_SQL",
    "SimulationBacktester",
    "build_readonly_realized_sql",
]
