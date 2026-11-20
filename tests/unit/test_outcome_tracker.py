"""
Testes unitarios do modulo Closed-Loop ROI Tracking (Fase 2 - Roadmap Next-Gen).
Valida integracao com AuraCommandJournal, calculo deterministico com sazonalidade,
ciclo T+24h -> T+7d -> COMPLETED, aprendizado em TenantMemoryManager, GenUI e API REST.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.command_journal import AuraCommandJournal
from core.outcome_tracker import (
    OutcomeStatus,
    OutcomeTracker,
    compute_realized_impact,
    reset_outcome_tracker,
    set_outcome_tracker,
)
from core.schemas.genui import RealizedRoiScorecardProps
from core.tenant_memory import TenantMemoryManager


def test_compute_realized_impact_seasonality() -> None:
    """Valida formula deterministica descontando sazonalidade do dia da semana."""
    # Baseline = 1000/dia, sexta-feira tem fator 1.2 -> esperado 1200/dia.
    # Observado = 1500/dia -> delta = +300/dia * 7 dias = +2100.00
    realized, conf = compute_realized_impact(
        baseline_daily_profit_brl=1000.0,
        observed_daily_profit_brl=1500.0,
        seasonality_factor=1.2,
        days_elapsed=7,
    )
    assert realized == 2100.0
    assert conf == 0.85

    realized_base, conf_base = compute_realized_impact(
        baseline_daily_profit_brl=0.0,
        observed_daily_profit_brl=250.0,
        seasonality_factor=1.0,
        days_elapsed=1,
    )
    assert realized_base == 250.0
    assert conf_base == 0.65


def test_command_journal_hook_and_idempotency(tmp_path: Path) -> None:
    """Aprovacao/conclusao de comando no journal cria outcome PENDING_24H idempotente."""
    tracker = OutcomeTracker(db_path=tmp_path / "outcomes.db")
    set_outcome_tracker(tracker)
    try:
        journal = AuraCommandJournal(db_path=tmp_path / "journal.db")
        acq = journal.begin_command(
            command_key="cmd-roi-001",
            action_id="act-001",
            action_type="CONVENIENCE_COMBO",
            actor="gestor",
            request_payload={
                "tenant_id": "posto_vip",
                "filial_id": "1",
                "product": "combo_cafe_pao",
                "predicted_impact_brl": 3200.0,
                "baseline_daily_profit_brl": 1200.0,
            },
        )
        assert acq.acquired is True
        entry = journal.complete_command("cmd-roi-001", result_payload={"ok": True})

        # Repetir registro nao pode duplicar
        dup = tracker.register_from_command(entry)
        scorecard = tracker.get_realized_roi_scorecard(period_days=30, tenant_id="posto_vip")
        assert len(scorecard.items) == 1
        assert scorecard.items[0].outcome_id == dup["outcome_id"]
        assert scorecard.items[0].status == OutcomeStatus.PENDING_24H.value
        assert scorecard.total_predicted_brl == 3200.0
    finally:
        reset_outcome_tracker()


def test_lifecycle_transitions_and_tenant_memory_learning(tmp_path: Path) -> None:
    """Ciclo 24h -> 7d -> 30d -> COMPLETED grava estrategia validada na TenantMemory."""
    mem = TenantMemoryManager(db_path=tmp_path / "tenant_mem.db")
    tracker = OutcomeTracker(db_path=tmp_path / "outcomes.db", tenant_memory=mem)

    created = tracker.register_outcome(
        command_id="cmd-life-01",
        tenant_id="posto_01",
        filial_id="1",
        action_type="PIX_SHIFT",
        target_entity="pista_pix",
        baseline_snapshot={"daily_profit_brl": 2000.0},
        predicted_impact_brl=4500.0,
    )
    oid = created["outcome_id"]
    assert created["status"] == OutcomeStatus.PENDING_24H.value

    step_24h = tracker.audit_outcome(oid, observed_daily_profit_brl=2200.0, seasonality_factor=1.0)
    assert step_24h["status"] == OutcomeStatus.PENDING_7D.value
    assert step_24h["realized_24h_brl"] == 200.0

    step_7d = tracker.audit_outcome(oid, observed_daily_profit_brl=2250.0, seasonality_factor=1.0)
    assert step_7d["status"] == OutcomeStatus.PENDING_30D.value
    assert step_7d["realized_7d_brl"] == 1750.0

    step_30d = tracker.audit_outcome(oid, observed_daily_profit_brl=2180.0, seasonality_factor=1.0)
    assert step_30d["status"] == OutcomeStatus.COMPLETED.value
    assert step_30d["realized_30d_brl"] == 5400.0

    facts = mem.list_facts(tenant_id="posto_01", status="ativo")
    assert any(f.categoria == "estrategia_validada" and "5400.00" in f.conteudo for f in facts)


def test_audit_pending_outcomes_time_windows(tmp_path: Path) -> None:
    """Varredura periodica audita apenas janelas temporais vencidas."""
    tracker = OutcomeTracker(db_path=":memory:")
    t0 = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
    rec = tracker.register_outcome(
        command_id="cmd-win-01",
        tenant_id="posto_01",
        filial_id="1",
        action_type="FUEL_ORDER",
        target_entity="tanque_1",
        baseline_snapshot={"daily_profit_brl": 1000.0},
        predicted_impact_brl=1500.0,
        created_at=t0.isoformat(),
    )

    # 12h depois ainda nao venceu T+24h
    early = tracker.audit_pending_outcomes(
        metric_fetcher=lambda _o: (1200.0, 1.0),
        now=t0 + timedelta(hours=12),
    )
    assert early == []

    # 25h depois audita T+24h
    due_24h = tracker.audit_pending_outcomes(
        metric_fetcher=lambda _o: (1200.0, 1.0),
        now=t0 + timedelta(hours=25),
    )
    assert len(due_24h) == 1
    assert due_24h[0]["outcome_id"] == rec["outcome_id"]
    assert due_24h[0]["status"] == OutcomeStatus.PENDING_7D.value


def test_roi_realized_and_feedback_endpoints(client, tmp_path: Path) -> None:
    """Valida endpoints GET /roi-realized, POST /outcomes/{id}/feedback e schema GenUI."""
    tracker = OutcomeTracker(db_path=tmp_path / "api_outcomes.db")
    rec = tracker.register_outcome(
        command_id="cmd-api-01",
        tenant_id="posto_01",
        filial_id="1",
        action_type="PRICE_ADJUST",
        target_entity="gasolina_aditivada",
        baseline_snapshot={"daily_profit_brl": 1000.0},
        predicted_impact_brl=1000.0,
    )
    tracker.audit_outcome(rec["outcome_id"], observed_daily_profit_brl=1300.0, seasonality_factor=1.0)

    set_outcome_tracker(tracker)
    try:
        resp_get = client.get("/api/v1/aura/roi-realized?period_days=30")
        assert resp_get.status_code == 200
        data = resp_get.json()
        scorecard = RealizedRoiScorecardProps(**data)
        assert scorecard.total_predicted_brl == 1000.0
        assert scorecard.total_realized_brl == 300.0
        assert scorecard.hit_rate_pct == 100.0

        resp_fb = client.post(
            f"/api/v1/aura/outcomes/{rec['outcome_id']}/feedback",
            json={"feedback": "CONFIRMED", "note": "Bateu exatamente com o caixa"},
        )
        assert resp_fb.status_code == 200
        assert resp_fb.json()["outcome"]["manager_feedback"] == "CONFIRMED"

        resp_bad = client.post(
            f"/api/v1/aura/outcomes/{rec['outcome_id']}/feedback",
            json={"feedback": "INVALID"},
        )
        assert resp_bad.status_code == 422

        resp_404 = client.post(
            "/api/v1/aura/outcomes/out_inexistente/feedback",
            json={"feedback": "DISPUTED"},
        )
        assert resp_404.status_code == 404
    finally:
        reset_outcome_tracker()


async def test_proactive_daemon_runs_outcome_audits_if_due(tmp_path: Path) -> None:
    """Valida execucao do gancho de auditoria periodica no AuraProactiveDaemon."""
    from core.proactive_daemon import AuraProactiveDaemon

    tracker = OutcomeTracker(db_path=tmp_path / "daemon_outcomes.db")
    t0 = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
    tracker.register_outcome(
        command_id="cmd-daemon-01",
        tenant_id="posto_01",
        filial_id="1",
        action_type="LOSS_AUDIT",
        target_entity="caixa_1",
        baseline_snapshot={"daily_profit_brl": 900.0},
        predicted_impact_brl=500.0,
        created_at=t0.isoformat(),
    )
    set_outcome_tracker(tracker)
    try:
        daemon = AuraProactiveDaemon(db_path=":memory:")
        res = await daemon.run_outcome_audits_if_due(force=True)
        assert isinstance(res, list)
    finally:
        reset_outcome_tracker()


def test_zero_unicode_dashes_in_phase2_files() -> None:
    """Garante ausencia absoluta de travessoes Unicode nos arquivos da Fase 2."""
    root = Path(__file__).resolve().parent.parent.parent
    for path in (root / "core" / "outcome_tracker.py", Path(__file__)):
        text = path.read_text(encoding="utf-8")
        assert "\u2014" not in text
        assert "\u2013" not in text
