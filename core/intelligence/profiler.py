"""Worker de Profiling Estatistico e Sentinelas Proativas (Fase 2).

Executa queries read-only validadas via assert_readonly_safe_sql (sqlglot Postgres,
proibindo TRIM() em clausulas JOIN), calcula perfil estatistico deterministico
(media, desvio padrao, IQR, sazonalidade, curva ABC), detecta desvios reais em
margem, giro, custo ou fluxo de caixa e dispara rascunho de simulacao somente
quando ha anomalia relevante. Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import math
import re
import uuid
from datetime import UTC, datetime
from typing import Any, Callable, Sequence

import sqlglot
from sqlglot import exp

from core.intelligence.models import (
    AnomalyDirection,
    AnomalyFinding,
    AnomalyMetric,
    AnomalyMethod,
    AnomalySeverity,
    MetricSeriesPoint,
    ProactiveAlert,
)
from core.intelligence.synthesizer import SecondOrderSynthesizer
from core.simulation.engine import SimulationEngine
from core.simulation.models import (
    BusinessProfileSnapshotRecord,
    ShockVector,
    SimulationBaseline,
    SimulationRecomputeRequest,
)
from core.simulation.repository import SimulationRepository
from core.tenancy import ReadOnlySQLViolationError, assert_readonly_safe_sql

_PARAM_PLACEHOLDER_RE = re.compile(r"%s|\?")
_FORBIDDEN_JOIN_TRIM_FUNCS = frozenset({"trim", "btrim", "ltrim", "rtrim"})

FUEL_CONVENIENCE_SQL_TEMPLATES: dict[str, str] = {
    "daily_sales": """
WITH daily_sales AS (
    SELECT
        DATE(p.ped_dt_emissao) AS ref_date,
        COALESCE(SUM(i.ipe_qt_item), 0) AS daily_volume,
        COALESCE(SUM(i.ipe_vl_total), 0) AS daily_revenue,
        COALESCE(SUM(i.ipe_qt_item * COALESCE(i.ipe_vl_custo, 0)), 0) AS daily_cost
    FROM pedido p
    INNER JOIN itemped i ON i.ped_cd_pedido = p.ped_cd_pedido
    WHERE p.emp_cd_empresa = %s
      AND p.ped_dt_emissao >= CURRENT_DATE - (%s * INTERVAL '1 day')
      AND p.ped_st_cancelado = 'N'
    GROUP BY DATE(p.ped_dt_emissao)
)
SELECT
    ref_date,
    daily_volume,
    daily_revenue,
    daily_cost,
    CASE
        WHEN daily_revenue > 0 THEN ((daily_revenue - daily_cost) / daily_revenue) * 100.0
        ELSE 0.0
    END AS margin_pct,
    CASE
        WHEN daily_volume > 0 THEN daily_revenue / daily_volume
        ELSE 0.0
    END AS unit_price,
    CASE
        WHEN daily_volume > 0 THEN daily_cost / daily_volume
        ELSE 0.0
    END AS unit_cost
FROM daily_sales
ORDER BY ref_date ASC
""".strip(),
    "daily_cashflow": """
WITH cash_in AS (
    SELECT
        DATE(r.rec_dt_vencimento) AS ref_date,
        COALESCE(SUM(r.rec_vl_valor), 0) AS inflow_brl
    FROM receber r
    WHERE r.emp_cd_empresa = %s
      AND r.rec_dt_vencimento >= CURRENT_DATE - (%s * INTERVAL '1 day')
    GROUP BY DATE(r.rec_dt_vencimento)
),
cash_out AS (
    SELECT
        DATE(pg.pag_dt_vencimento) AS ref_date,
        COALESCE(SUM(pg.pag_vl_valor), 0) AS outflow_brl
    FROM pagar pg
    WHERE pg.emp_cd_empresa = %s
      AND pg.pag_dt_vencimento >= CURRENT_DATE - (%s * INTERVAL '1 day')
    GROUP BY DATE(pg.pag_dt_vencimento)
)
SELECT
    COALESCE(ci.ref_date, co.ref_date) AS ref_date,
    COALESCE(ci.inflow_brl, 0) AS inflow_brl,
    COALESCE(co.outflow_brl, 0) AS outflow_brl,
    COALESCE(ci.inflow_brl, 0) - COALESCE(co.outflow_brl, 0) AS net_cashflow_brl
FROM cash_in ci
FULL OUTER JOIN cash_out co ON co.ref_date = ci.ref_date
ORDER BY ref_date ASC
""".strip(),
    "abc_curve": """
SELECT
    pr.pro_cd_produto AS entity_id,
    pr.pro_ds_produto AS entity_label,
    COALESCE(SUM(i.ipe_vl_total), 0) AS total_revenue,
    COALESCE(SUM(i.ipe_qt_item), 0) AS total_volume
FROM pedido p
INNER JOIN itemped i ON i.ped_cd_pedido = p.ped_cd_pedido
INNER JOIN produtos pr ON pr.pro_cd_produto = i.pro_cd_produto
WHERE p.emp_cd_empresa = %s
  AND p.ped_dt_emissao >= CURRENT_DATE - (%s * INTERVAL '1 day')
  AND p.ped_st_cancelado = 'N'
GROUP BY pr.pro_cd_produto, pr.pro_ds_produto
ORDER BY total_revenue DESC
LIMIT %s
""".strip(),
}

PackSeriesProvider = Callable[[Any, int, int, int], tuple[list[MetricSeriesPoint], list[dict[str, Any]]]]
_PACK_QUERY_PROVIDERS: dict[str, PackSeriesProvider] = {}


def register_pack_query_provider(pack_id: str, provider: PackSeriesProvider) -> None:
    """Registra um provedor de leitura ERP especifico para um pack_id."""
    norm = (pack_id or "").strip().lower()
    if not norm:
        raise ValueError("pack_id nao pode ser vazio ao registrar provedor de profiling.")
    _PACK_QUERY_PROVIDERS[norm] = provider


def validate_profiler_sql(sql: str) -> str:
    """Valida query read-only via assert_readonly_safe_sql e proibe TRIM() em JOINs."""
    assert_readonly_safe_sql(sql)

    idx = 0

    def _sub_bind(_m: re.Match[str]) -> str:
        nonlocal idx
        idx += 1
        return f"${idx}"

    ast_sql = _PARAM_PLACEHOLDER_RE.sub(_sub_bind, sql.strip().rstrip(";"))
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
    return sql


def execute_readonly_query(
    cursor: Any,
    sql: str,
    params: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    """Executa query SQL validada e retorna linhas como lista de dicionarios."""
    validate_profiler_sql(sql)
    cursor.execute(sql, params)
    rows = cursor.fetchall() or []
    description = getattr(cursor, "description", None) or []
    columns = [str(col[0]) for col in description]
    if not columns:
        return []
    return [dict(zip(columns, row)) for row in rows]


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = (pct / 100.0) * (len(sorted_vals) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac


def _compute_mean_std(values: Sequence[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    n = len(values)
    mean_val = sum(values) / n
    if n < 2:
        return mean_val, 0.0
    var_val = sum((x - mean_val) ** 2 for x in values) / (n - 1)
    return mean_val, math.sqrt(max(0.0, var_val))


def _compute_iqr_bounds(values: Sequence[float], multiplier: float) -> tuple[float, float]:
    ordered = sorted(float(v) for v in values)
    q1 = _percentile(ordered, 25.0)
    q3 = _percentile(ordered, 75.0)
    iqr = q3 - q1
    return q1 - (multiplier * iqr), q3 + (multiplier * iqr)


def _compute_seasonality_by_weekday(series: Sequence[MetricSeriesPoint]) -> dict[str, dict[str, float]]:
    buckets: dict[str, list[MetricSeriesPoint]] = {}
    for pt in series:
        try:
            dt = datetime.fromisoformat(str(pt.ref_date)[:10])
            day_key = str(dt.weekday())
        except ValueError:
            day_key = "unknown"
        buckets.setdefault(day_key, []).append(pt)

    summary: dict[str, dict[str, float]] = {}
    for day_key, pts in sorted(buckets.items()):
        vols = [float(p.daily_volume) for p in pts if p.daily_volume is not None]
        margins = [float(p.margin_pct) for p in pts if p.margin_pct is not None]
        entry: dict[str, float] = {"count": float(len(pts))}
        if vols:
            entry["mean_daily_volume"] = round(sum(vols) / len(vols), 4)
        if margins:
            entry["mean_margin_pct"] = round(sum(margins) / len(margins), 4)
        summary[day_key] = entry
    return summary


def _compute_abc_curve(items: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {"items": [], "counts": {"A": 0, "B": 0, "C": 0}}
    normalized: list[dict[str, Any]] = []
    total_rev = 0.0
    for item in items:
        rev = max(0.0, float(item.get("total_revenue", 0.0) or 0.0))
        total_rev += rev
        normalized.append(
            {
                "entity_id": str(item.get("entity_id", "")),
                "entity_label": str(item.get("entity_label", "")),
                "total_revenue": round(rev, 2),
                "total_volume": round(float(item.get("total_volume", 0.0) or 0.0), 3),
            }
        )
    normalized.sort(key=lambda x: x["total_revenue"], reverse=True)
    cum_rev = 0.0
    counts = {"A": 0, "B": 0, "C": 0}
    for item in normalized:
        cum_rev += item["total_revenue"]
        share_pct = (cum_rev / total_rev) * 100.0 if total_rev > 0 else 100.0
        if share_pct <= 80.0 or counts["A"] == 0:
            cls = "A"
        elif share_pct <= 95.0:
            cls = "B"
        else:
            cls = "C"
        item["abc_class"] = cls
        item["cumulative_share_pct"] = round(share_pct, 2)
        counts[cls] += 1
    return {"items": normalized[:25], "counts": counts}


class BusinessProfiler:
    """Calcula perfil estatistico do negocio e aciona sentinelas deterministicas."""

    def __init__(
        self,
        repository: SimulationRepository,
        simulation_engine: SimulationEngine | None = None,
        synthesizer: SecondOrderSynthesizer | None = None,
        z_threshold: float = 2.0,
        iqr_multiplier: float = 1.5,
    ) -> None:
        self._repo = repository
        self._engine = simulation_engine or SimulationEngine()
        self._synthesizer = synthesizer
        self._z_threshold = float(z_threshold)
        self._iqr_multiplier = float(iqr_multiplier)

    def fetch_series_from_erp(
        self,
        cursor: Any,
        pack_id: str,
        filial_id: int,
        lookback_days: int = 30,
        top_n_abc: int = 50,
    ) -> tuple[list[MetricSeriesPoint], list[dict[str, Any]]]:
        """Executa queries read-only estritamente isoladas pelo pack_id ativo."""
        norm_pack = (pack_id or "").strip().lower()
        if not norm_pack:
            raise ValueError("pack_id obrigatorio para leitura de serie estatistica.")

        if norm_pack in _PACK_QUERY_PROVIDERS:
            return _PACK_QUERY_PROVIDERS[norm_pack](cursor, filial_id, lookback_days, top_n_abc)

        if norm_pack != "fuel_convenience":
            raise LookupError(
                f"Nenhum provedor ERP analitico registrado para pack_id '{norm_pack}' (fallback bloqueado)."
            )

        sales_rows = execute_readonly_query(
            cursor,
            FUEL_CONVENIENCE_SQL_TEMPLATES["daily_sales"],
            (int(filial_id), int(lookback_days)),
        )
        cash_rows = execute_readonly_query(
            cursor,
            FUEL_CONVENIENCE_SQL_TEMPLATES["daily_cashflow"],
            (int(filial_id), int(lookback_days), int(filial_id), int(lookback_days)),
        )
        abc_rows = execute_readonly_query(
            cursor,
            FUEL_CONVENIENCE_SQL_TEMPLATES["abc_curve"],
            (int(filial_id), int(lookback_days), int(top_n_abc)),
        )

        by_date: dict[str, dict[str, Any]] = {}
        for row in sales_rows:
            key = str(row.get("ref_date"))
            by_date[key] = {
                "ref_date": key,
                "margin_pct": float(row["margin_pct"]) if row.get("margin_pct") is not None else None,
                "daily_volume": float(row["daily_volume"]) if row.get("daily_volume") is not None else None,
                "unit_cost": float(row["unit_cost"]) if row.get("unit_cost") is not None else None,
                "unit_price": float(row["unit_price"]) if row.get("unit_price") is not None else None,
            }
        for row in cash_rows:
            key = str(row.get("ref_date"))
            entry = by_date.setdefault(key, {"ref_date": key})
            if row.get("net_cashflow_brl") is not None:
                entry["net_cashflow_brl"] = float(row["net_cashflow_brl"])

        points = [MetricSeriesPoint.model_validate(by_date[k]) for k in sorted(by_date.keys())]
        return points, abc_rows

    def compute_and_save_profile(
        self,
        tenant_id: str,
        pack_id: str,
        series: Sequence[MetricSeriesPoint],
        reference_period: str = "last_30d",
        abc_items: Sequence[dict[str, Any]] | None = None,
    ) -> BusinessProfileSnapshotRecord:
        """Calcula estatisticas base e grava snapshot em business_profile_snapshots."""
        norm_pack = pack_id.strip().lower()
        metric_names = ("margin_pct", "daily_volume", "unit_cost", "unit_price", "net_cashflow_brl")
        means: dict[str, float] = {}
        std_devs: dict[str, float] = {}

        for name in metric_names:
            vals = [float(getattr(pt, name)) for pt in series if getattr(pt, name) is not None]
            if vals:
                m_val, s_val = _compute_mean_std(vals)
                means[name] = round(m_val, 4)
                std_devs[name] = round(s_val, 4)

        record = BusinessProfileSnapshotRecord(
            snapshot_id=f"prof_{uuid.uuid4().hex[:14]}",
            tenant_id=tenant_id,
            pack_id=norm_pack,
            reference_period=reference_period,
            means=means,
            std_devs=std_devs,
            seasonality=_compute_seasonality_by_weekday(series),
            abc_curve=_compute_abc_curve(abc_items or []),
            sample_size=len(series),
        )
        self._repo.save_business_profile_snapshot(record)
        return record

    def detect_anomalies(
        self,
        history: Sequence[MetricSeriesPoint],
        current: MetricSeriesPoint,
        priority_metrics: set[str] | None = None,
    ) -> list[AnomalyFinding]:
        """Detecta desvios reais (Z-score / IQR) em margem, giro, custo e fluxo de caixa."""
        monitored: tuple[AnomalyMetric, ...] = (
            "margin_pct",
            "daily_volume",
            "unit_cost",
            "net_cashflow_brl",
        )
        priority = {m.strip().lower() for m in (priority_metrics or set())}
        findings: list[AnomalyFinding] = []

        for metric in monitored:
            observed_raw = getattr(current, metric)
            if observed_raw is None:
                continue
            observed = float(observed_raw)
            hist_vals = [float(getattr(pt, metric)) for pt in history if getattr(pt, metric) is not None]
            if len(hist_vals) < 4:
                continue

            is_priority = metric in priority
            eff_z = self._z_threshold * (0.85 if is_priority else 1.0)
            eff_iqr = self._iqr_multiplier * (0.85 if is_priority else 1.0)

            mean_val, std_val = _compute_mean_std(hist_vals)
            iqr_low, iqr_high = _compute_iqr_bounds(hist_vals, eff_iqr)

            z_score = (observed - mean_val) / std_val if std_val > 1e-9 else 0.0
            z_hit = std_val > 1e-9 and abs(z_score) >= eff_z

            iqr_span = iqr_high - iqr_low
            if iqr_span > 1e-9:
                iqr_hit = observed < iqr_low or observed > iqr_high
            else:
                rel_diff = abs(observed - mean_val) / max(1.0, abs(mean_val))
                iqr_hit = rel_diff >= (0.04 if is_priority else 0.06)

            if not z_hit and not iqr_hit:
                continue

            if z_hit and iqr_hit:
                method: AnomalyMethod = "both"
            elif z_hit:
                method = "z_score"
            else:
                method = "iqr"

            direction: AnomalyDirection = "drop" if observed < mean_val else "spike"
            abs_z = abs(z_score)
            if abs_z >= 3.0:
                severity: AnomalySeverity = "CRITICAL"
            elif abs_z >= 2.2 or method == "both":
                severity = "HIGH"
            else:
                severity = "MEDIUM"

            findings.append(
                AnomalyFinding(
                    metric=metric,
                    observed_value=round(observed, 4),
                    baseline_mean=round(mean_val, 4),
                    baseline_std_dev=round(std_val, 4),
                    z_score=round(z_score, 3),
                    iqr_lower=round(iqr_low, 4),
                    iqr_upper=round(iqr_high, 4),
                    method=method,
                    severity=severity,
                    direction=direction,
                    is_priority_monitored=is_priority,
                )
            )

        sev_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}
        findings.sort(key=lambda f: (sev_rank.get(f.severity, 9), -abs(f.z_score)))
        return findings

    @staticmethod
    def build_draft_simulation_request(
        tenant_id: str,
        pack_id: str,
        history: Sequence[MetricSeriesPoint],
        current: MetricSeriesPoint,
        anomalies: Sequence[AnomalyFinding],
    ) -> SimulationRecomputeRequest:
        """Constroi rascunho deterministico de simulacao aderente a anomalia principal."""
        prices = [float(p.unit_price) for p in history if p.unit_price is not None and p.unit_price > 0]
        costs = [float(p.unit_cost) for p in history if p.unit_cost is not None and p.unit_cost >= 0]
        vols = [float(p.daily_volume) for p in history if p.daily_volume is not None and p.daily_volume > 0]
        margins = [float(p.margin_pct) for p in history if p.margin_pct is not None]

        mean_price = (sum(prices) / len(prices)) if prices else (current.unit_price or 10.0)
        mean_vol, std_vol = _compute_mean_std(vols) if vols else (current.daily_volume or 100.0, 0.0)
        mean_cost, std_cost = _compute_mean_std(costs) if costs else (current.unit_cost or 0.0, 0.0)

        if not costs and margins and mean_price > 0:
            mean_margin_pct = sum(margins) / len(margins)
            mean_cost = max(0.0, mean_price * (1.0 - (mean_margin_pct / 100.0)))

        vol_std_pct = (std_vol / mean_vol) * 100.0 if mean_vol > 1e-9 else 5.0
        cost_std_pct = (std_cost / mean_cost) * 100.0 if mean_cost > 1e-9 else 2.0

        baseline = SimulationBaseline(
            unit_price=round(max(0.01, float(mean_price)), 4),
            unit_cost=round(max(0.0, float(mean_cost)), 4),
            daily_volume=round(max(1.0, float(mean_vol)), 4),
            volume_std_dev_pct=round(max(0.5, min(50.0, vol_std_pct)), 2),
            cost_std_dev_pct=round(max(0.5, min(50.0, cost_std_pct)), 2),
            receivable_days=current.receivable_days,
            payable_days=current.payable_days,
            fixed_daily_cost=current.fixed_daily_cost,
        )

        primary = anomalies[0]
        if primary.metric == "unit_cost":
            rel_cost = ((primary.observed_value - primary.baseline_mean) / max(0.01, primary.baseline_mean)) * 100.0
            scenario_type = "cost_supplier_variation"
            shocks = ShockVector(
                supplier_cost_delta_pct=round(max(1.0, min(50.0, abs(rel_cost))), 2),
                cost_passthrough_pct=60.0,
            )
        elif primary.metric == "net_cashflow_brl":
            scenario_type = "payment_term_cashflow"
            shocks = ShockVector(
                receivable_days_delta=-3.0,
                payable_days_delta=5.0,
            )
        elif primary.metric == "daily_volume" and primary.direction == "drop":
            scenario_type = "price_discount_change"
            shocks = ShockVector(discount_pct=2.0)
        else:
            gap = abs(primary.baseline_mean - primary.observed_value)
            scenario_type = "price_discount_change"
            shocks = ShockVector(price_delta_pct=round(max(1.5, min(8.0, gap)), 2))

        return SimulationRecomputeRequest(
            tenant_id=tenant_id,
            pack_id=pack_id.strip().lower(),
            scenario_type=scenario_type,  # type: ignore[arg-type]
            horizon_days=30,
            baseline=baseline,
            shocks=shocks,
            iterations=5000,
            seed=42,
            persist_snapshot=True,
            created_by="sentinel_profiler",
        )

    def run_sentinel_cycle(
        self,
        tenant_id: str,
        pack_id: str,
        history: Sequence[MetricSeriesPoint],
        current: MetricSeriesPoint,
        priority_metrics: set[str] | None = None,
        reference_period: str = "last_30d",
        abc_items: Sequence[dict[str, Any]] | None = None,
        enable_llm_synthesis: bool = True,
    ) -> ProactiveAlert | None:
        """Executa ciclo completo: snapshot + deteccao + simulacao condicional + sintese."""
        norm_pack = pack_id.strip().lower()
        snapshot = self.compute_and_save_profile(
            tenant_id=tenant_id,
            pack_id=norm_pack,
            series=[*history, current],
            reference_period=reference_period,
            abc_items=abc_items,
        )

        anomalies = self.detect_anomalies(
            history=history,
            current=current,
            priority_metrics=priority_metrics,
        )
        if not anomalies:
            return None

        draft_req = self.build_draft_simulation_request(
            tenant_id=tenant_id,
            pack_id=norm_pack,
            history=history,
            current=current,
            anomalies=anomalies,
        )
        active_rules = self._repo.list_business_rules(
            tenant_id=tenant_id,
            pack_id=norm_pack,
            status="active",
        )
        draft_sim = self._engine.run_simulation(
            request=draft_req,
            repository=self._repo,
            memory_rules=active_rules,
        )

        synthesis: str | None = None
        rag_refs: list[str] = []
        llm_calls = 0
        if self._synthesizer is not None and enable_llm_synthesis:
            synthesis, rag_refs, llm_calls = self._synthesizer.synthesize(
                tenant_id=tenant_id,
                pack_id=norm_pack,
                anomalies=anomalies,
                simulation=draft_sim,
                active_rules=active_rules,
                allow_llm=True,
            )

        return ProactiveAlert(
            alert_id=f"alt_{uuid.uuid4().hex[:14]}",
            tenant_id=tenant_id,
            pack_id=norm_pack,
            snapshot_id=snapshot.snapshot_id,
            anomalies=anomalies,
            draft_simulation=draft_sim,
            second_order_synthesis=synthesis,
            rag_references=rag_refs,
            llm_calls=llm_calls,
            created_at=datetime.now(UTC).isoformat(),
        )


__all__ = [
    "BusinessProfiler",
    "FUEL_CONVENIENCE_SQL_TEMPLATES",
    "PackSeriesProvider",
    "execute_readonly_query",
    "register_pack_query_provider",
    "validate_profiler_sql",
]
