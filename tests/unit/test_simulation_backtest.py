"""Testes unitarios deterministicos da Fase 3: Backtesting (30/60/90d),
SQL Read-Only via sqlglot, Auto-Calibracao HiC, Proveniencia e Feed de Governanca.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from config.settings import BASE_DIR
from core.aura_api import create_aura_app, get_local_session_token
from core.intelligence import (
    IntentTracker,
    MemoryManager,
    set_memory_manager,
)
from core.migrations import AuraMigrationManager
from core.simulation import (
    ShockVector,
    SimulationBacktester,
    SimulationBaseline,
    SimulationEngine,
    SimulationRecomputeRequest,
    SimulationRepository,
    build_readonly_realized_sql,
    set_simulation_backtester,
    set_simulation_repository,
)
from core.tenancy import ReadOnlySQLViolationError


def _create_in_memory_db() -> tuple[AuraMigrationManager, sqlite3.Connection, SimulationRepository]:
    manager = AuraMigrationManager(db_path=":memory:")
    manager.upgrade("head")
    conn = manager._shared_memory_conn
    assert conn is not None
    repo = SimulationRepository(connection=conn, dialect="sqlite")
    return manager, conn, repo


def _sample_baseline() -> SimulationBaseline:
    return SimulationBaseline(
        unit_price=6.20,
        unit_cost=5.40,
        daily_volume=10000.0,
        volume_std_dev_pct=4.0,
        cost_std_dev_pct=1.5,
        elasticity_mean=-1.2,
        elasticity_std_dev=0.2,
        receivable_days=10.0,
        payable_days=20.0,
        annual_capital_cost_pct=10.75,
        fixed_daily_cost=1500.0,
    )


def _insert_aged_snapshot(
    repo: SimulationRepository,
    conn: sqlite3.Connection,
    simulation_id: str,
    tenant_id: str,
    pack_id: str,
    horizon_days: int,
    age_days: int,
    p10: float,
    p50: float,
    p90: float,
) -> None:
    engine = SimulationEngine()
    res = engine.run_simulation(
        SimulationRecomputeRequest(
            tenant_id=tenant_id,
            pack_id=pack_id,
            simulation_id=simulation_id,
            scenario_type="price_discount_change",
            horizon_days=horizon_days,  # type: ignore[arg-type]
            baseline=_sample_baseline(),
            shocks=ShockVector(price_delta_pct=2.0),
            iterations=200,
            seed=42,
        )
    )
    repo.save_simulation_snapshot(
        simulation_id=simulation_id,
        tenant_id=tenant_id,
        pack_id=pack_id,
        scenario_type="price_discount_change",
        horizon_days=horizon_days,
        baseline=_sample_baseline(),
        shocks=ShockVector(price_delta_pct=2.0),
        p10_value=p10,
        p50_value=p50,
        p90_value=p90,
        sensitivity=res.sensitivity,
        violated_rules=res.violated_rules,
        seed=42,
        iterations=200,
        created_by="operator",
    )
    created_dt = (datetime.now(UTC) - timedelta(days=age_days)).strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.cursor()
    cur.execute(
        "UPDATE simulation_snapshots SET created_at = ? WHERE simulation_id = ?;",
        (created_dt, simulation_id),
    )
    conn.commit()
    cur.close()


@pytest.mark.unit
def test_readonly_backtest_sql_enforces_sqlglot_and_blocks_mutations() -> None:
    """Query SQL de backtest passa por sqlglot e rejeita DML/TRIM em JOIN."""
    safe_sql = build_readonly_realized_sql()
    assert safe_sql.upper().startswith("SELECT")
    assert "TRIM(" not in safe_sql.upper()

    with pytest.raises(ReadOnlySQLViolationError):
        build_readonly_realized_sql("DELETE FROM pedido WHERE 1=1")

    with pytest.raises(ReadOnlySQLViolationError):
        build_readonly_realized_sql(
            "SELECT * FROM pedido p INNER JOIN itemped i ON TRIM(i.ped_cd_pedido) = p.ped_cd_pedido"
        )


@pytest.mark.unit
def test_matured_snapshots_isolation_and_backtest_calibration_hic() -> None:
    """Separa snapshots vencidos (30/60/90d), calcula erro % e gera regra candidate HiC."""
    manager, conn, repo = _create_in_memory_db()
    try:
        # 2 snapshots vencidos no tenant_a/fuel_convenience + 1 nao vencido + 1 outro tenant
        _insert_aged_snapshot(repo, conn, "sim_due_30", "tenant_a", "fuel_convenience", 30, 35, 800.0, 1000.0, 1200.0)
        _insert_aged_snapshot(repo, conn, "sim_due_60", "tenant_a", "fuel_convenience", 60, 65, 1600.0, 2000.0, 2400.0)
        _insert_aged_snapshot(repo, conn, "sim_fresh_90", "tenant_a", "fuel_convenience", 90, 10, 2500.0, 3000.0, 3500.0)
        _insert_aged_snapshot(repo, conn, "sim_other_tenant", "tenant_b", "fuel_convenience", 30, 40, 800.0, 1000.0, 1200.0)

        matured = repo.list_matured_snapshots(
            tenant_id="tenant_a",
            pack_id="fuel_convenience",
            as_of_dt=datetime.now(UTC),
            only_pending=True,
        )
        assert [m["simulation_id"] for m in matured] == ["sim_due_60", "sim_due_30"]

        # Realizado consistentemente ~25% abaixo do P50 para acionar sugestao de calibracao
        realized_map = {
            "sim_due_30": 750.0,
            "sim_due_60": 1500.0,
        }
        backtester = SimulationBacktester(
            repository=repo,
            realized_fetcher=lambda snap, _s, _e: realized_map.get(snap["simulation_id"]),
            bias_threshold_pct=10.0,
            min_calibration_samples=2,
        )

        run_res = backtester.run_backtest(tenant_id="tenant_a", pack_id="fuel_convenience")
        assert run_res.llm_calls == 0
        assert run_res.evaluated_count == 2
        by_id = {item.simulation_id: item for item in run_res.items}
        assert by_id["sim_due_30"].error_brl == -250.0
        assert by_id["sim_due_30"].error_pct == 25.0
        assert by_id["sim_due_30"].within_p10_p90 is False

        assert run_res.calibration_proposal is not None
        assert run_res.calibration_proposal.status == "candidate"
        assert run_res.calibration_proposal.suggested_factor == pytest.approx(0.75, abs=0.001)

        # Regra deve estar estritamente como candidate (nunca active sem HiC)
        candidates = repo.list_business_rules("tenant_a", "fuel_convenience", status="candidate")
        actives = repo.list_business_rules("tenant_a", "fuel_convenience", status="active")
        assert len(candidates) == 1
        assert candidates[0].rule_key == "elasticity_calibration_factor"
        assert len(actives) == 0

        # Segunda execucao nao deve reavaliar snapshots ja auditados (append-only)
        run_again = backtester.run_backtest(tenant_id="tenant_a", pack_id="fuel_convenience")
        assert run_again.evaluated_count == 0

        scorecard = backtester.build_scorecard("tenant_a", "fuel_convenience")
        assert scorecard.projected_brl == 3000.0
        assert scorecard.realized_brl == 2250.0
        assert scorecard.mean_abs_error_pct == 25.0
        assert scorecard.hit_rate_pct == 0.0
        assert scorecard.pending_calibration is not None
        assert scorecard.pending_calibration.rule_id == candidates[0].rule_id
    finally:
        manager.close()


@pytest.mark.unit
def test_phase3_api_endpoints_backtest_suggestions_and_provenance() -> None:
    """Valida endpoints /recompute (provenance), /backtest/* e /memory/suggestions com auth."""
    manager, conn, repo = _create_in_memory_db()
    _insert_aged_snapshot(repo, conn, "sim_api_30", "tenant_api", "fuel_convenience", 30, 40, 900.0, 1000.0, 1100.0)
    _insert_aged_snapshot(repo, conn, "sim_api_60", "tenant_api", "fuel_convenience", 60, 70, 1800.0, 2000.0, 2200.0)

    tracker = IntentTracker(repository=repo, recurrence_threshold=3, window_days=7)
    for _ in range(3):
        tracker.record_query(
            tenant_id="tenant_api",
            pack_id="fuel_convenience",
            raw_query="Como esta a margem liquida da gasolina aditivada?",
            intent_name="margin_analysis",
        )

    backtester = SimulationBacktester(
        repository=repo,
        realized_fetcher=lambda snap, _s, _e: 800.0 if snap["simulation_id"] == "sim_api_30" else 1600.0,
        bias_threshold_pct=10.0,
        min_calibration_samples=2,
    )
    mem_mgr = MemoryManager(repository=repo)
    set_simulation_repository(repo)
    set_simulation_backtester(backtester)
    set_memory_manager(mem_mgr)

    try:
        app = create_aura_app()
        client = TestClient(app)
        token = get_local_session_token()
        client.cookies.set("aura_session_token", token)

        # 1. Recompute retorna proveniencia transparente e zero tokens LLM
        rec_resp = client.post(
            "/api/v1/simulate/recompute",
            json={
                "tenant_id": "tenant_api",
                "pack_id": "fuel_convenience",
                "scenario_type": "price_discount_change",
                "horizon_days": 30,
                "baseline": _sample_baseline().model_dump(),
                "shocks": {"price_delta_pct": 1.5, "discount_pct": 0.5},
                "iterations": 300,
                "seed": 42,
            },
        )
        assert rec_resp.status_code == 200
        rec_data = rec_resp.json()
        assert rec_data["llm_calls"] == 0
        assert rec_data["provenance"]["baseline_source"] == "erp_historical"
        assert rec_data["provenance"]["yaml_rules_count"] >= 1

        # 2. Executa backtesting e consulta scorecard
        bt_resp = client.post(
            "/api/v1/simulate/backtest/run",
            json={"tenant_id": "tenant_api", "pack_id": "fuel_convenience"},
        )
        assert bt_resp.status_code == 200
        bt_data = bt_resp.json()
        assert bt_data["evaluated_count"] == 2
        assert bt_data["calibration_proposal"]["status"] == "candidate"
        cal_rule_id = bt_data["calibration_proposal"]["rule_id"]

        sc_resp = client.get(
            "/api/v1/simulate/backtest/scorecard",
            params={"tenant_id": "tenant_api", "pack_id": "fuel_convenience"},
        )
        assert sc_resp.status_code == 200
        sc_data = sc_resp.json()
        assert sc_data["projected_brl"] == 3000.0
        assert sc_data["realized_brl"] == 2400.0
        assert sc_data["pending_calibration"]["rule_id"] == cal_rule_id

        # 3. Feed consolidado HiC traz regra candidate + simulacao sugerida pelo profiler/tracker
        sug_resp = client.get(
            "/api/v1/memory/suggestions",
            params={"tenant_id": "tenant_api", "pack_id": "fuel_convenience"},
        )
        assert sug_resp.status_code == 200
        sug_data = sug_resp.json()
        assert sug_data["llm_calls"] == 0
        assert len(sug_data["candidate_rules"]) == 1
        assert len(sug_data["suggested_simulations"]) >= 1

        # 4. Aprovacao HiC promove calibracao para active e limpa pending_calibration do scorecard
        dec_resp = client.post(
            f"/api/v1/memory/rules/{cal_rule_id}/decision",
            json={
                "tenant_id": "tenant_api",
                "pack_id": "fuel_convenience",
                "decision": "approve",
                "decided_by": "gerente_01",
                "reason": "Aprovado apos auditoria de backtest.",
            },
        )
        assert dec_resp.status_code == 200
        assert dec_resp.json()["new_status"] == "active"

        sc_after = client.get(
            "/api/v1/simulate/backtest/scorecard",
            params={"tenant_id": "tenant_api", "pack_id": "fuel_convenience"},
        )
        assert sc_after.status_code == 200
        assert sc_after.json()["pending_calibration"] is None
    finally:
        set_simulation_backtester(None)
        set_simulation_repository(None)
        set_memory_manager(None)
        manager.close()


@pytest.mark.unit
def test_zero_unicode_dashes_in_phase3_artifacts() -> None:
    """Garante ausencia absoluta de travessoes nos arquivos da Fase 3."""
    files = [
        BASE_DIR / "core" / "simulation" / "backtest.py",
        BASE_DIR / "core" / "simulation" / "models.py",
        BASE_DIR / "core" / "simulation" / "repository.py",
        BASE_DIR / "core" / "simulation" / "api.py",
        BASE_DIR / "core" / "intelligence" / "api.py",
        BASE_DIR / "core" / "intelligence" / "models.py",
        BASE_DIR / "web-frontend" / "src" / "types" / "aura-contracts.ts",
        BASE_DIR / "web-frontend" / "src" / "api" / "aura-client.ts",
        BASE_DIR / "AuraBackend.spec",
        Path(__file__),
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "\u2014" not in text, f"Travessao em {path}"
        assert "\u2013" not in text, f"Meia-risca em {path}"
