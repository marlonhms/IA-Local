"""Testes unitarios deterministicos da Fase 2 (Inteligencia Proativa, Telemetria
de Intencao, Memoria Institucional HiC, Seguranca SQL e Economia de Tokens LLM).
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from config.settings import BASE_DIR
from core.aura_api import create_aura_app, get_local_session_token
from core.aura_engine import AuraEngine
from core.intelligence import (
    FUEL_CONVENIENCE_SQL_TEMPLATES,
    BusinessProfiler,
    IntentTracker,
    MemoryManager,
    MetricSeriesPoint,
    SecondOrderSynthesizer,
    set_memory_manager,
    validate_profiler_sql,
)
from core.migrations import AuraMigrationManager
from core.simulation import (
    ShockVector,
    SimulationBaseline,
    SimulationEngine,
    SimulationRecomputeRequest,
    SimulationRepository,
)
from core.tenancy import ReadOnlySQLViolationError


def _create_in_memory_db() -> tuple[AuraMigrationManager, sqlite3.Connection, SimulationRepository]:
    manager = AuraMigrationManager(db_path=":memory:")
    manager.upgrade("head")
    conn = manager._shared_memory_conn
    assert conn is not None
    repo = SimulationRepository(connection=conn, dialect="sqlite")
    return manager, conn, repo


def _stable_history() -> list[MetricSeriesPoint]:
    return [
        MetricSeriesPoint(
            ref_date=f"2026-11-{10 + idx:02d}",
            margin_pct=20.0 + (0.2 if idx % 2 == 0 else -0.2),
            daily_volume=1000.0 + (10.0 if idx % 2 == 0 else -10.0),
            unit_cost=4.0 + (0.02 if idx % 2 == 0 else -0.02),
            unit_price=5.0,
            net_cashflow_brl=2500.0 + (50.0 if idx % 2 == 0 else -50.0),
        )
        for idx in range(10)
    ]


@pytest.mark.unit
def test_profiler_no_anomaly_triggers_zero_simulations_and_zero_llm_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sem desvio estatistico relevante, nao dispara simulacao nem chama LLM."""
    manager, conn, repo = _create_in_memory_db()
    llm_called = {"count": 0}

    def _fail_if_llm_called(*_args: Any, **_kwargs: Any) -> Any:
        llm_called["count"] += 1
        raise AssertionError("LLM nao deve ser acionado quando nao ha anomalia.")

    monkeypatch.setattr("core.intelligence.synthesizer.get_genai_client", _fail_if_llm_called)

    try:
        synth = SecondOrderSynthesizer()
        profiler = BusinessProfiler(repository=repo, synthesizer=synth)
        history = _stable_history()
        normal_current = MetricSeriesPoint(
            ref_date="2026-11-20",
            margin_pct=20.1,
            daily_volume=1005.0,
            unit_cost=4.01,
            unit_price=5.0,
            net_cashflow_brl=2510.0,
        )

        alert = profiler.run_sentinel_cycle(
            tenant_id="tenant_posto",
            pack_id="fuel_convenience",
            history=history,
            current=normal_current,
            enable_llm_synthesis=True,
        )
        assert alert is None
        assert llm_called["count"] == 0

        profile = repo.get_latest_business_profile("tenant_posto", "fuel_convenience")
        assert profile is not None
        assert profile.sample_size == 11
        assert 19.5 <= profile.means["margin_pct"] <= 20.5

        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM simulation_snapshots;")
        assert cur.fetchone()[0] == 0
        cur.close()
    finally:
        manager.close()


@pytest.mark.unit
def test_profiler_detects_margin_cost_volume_cashflow_anomalies_and_drafts_simulation() -> None:
    """Detecta desvios reais via Z-score/IQR e gera rascunho automatico no SimulationEngine."""
    manager, _conn, repo = _create_in_memory_db()
    try:
        profiler = BusinessProfiler(repository=repo)
        history = _stable_history()

        # 1. Queda acentuada de margem + alta de custo + queda de giro + choque de caixa
        anomalous_current = MetricSeriesPoint(
            ref_date="2026-11-20",
            margin_pct=11.0,
            daily_volume=600.0,
            unit_cost=4.85,
            unit_price=5.0,
            net_cashflow_brl=-1200.0,
        )

        alert = profiler.run_sentinel_cycle(
            tenant_id="tenant_posto",
            pack_id="fuel_convenience",
            history=history,
            current=anomalous_current,
            enable_llm_synthesis=False,
        )
        assert alert is not None
        assert alert.llm_calls == 0
        detected_metrics = {a.metric for a in alert.anomalies}
        assert {"margin_pct", "daily_volume", "unit_cost", "net_cashflow_brl"} <= detected_metrics
        assert all(a.method in ("z_score", "iqr", "both") for a in alert.anomalies)

        sim = alert.draft_simulation
        assert sim.llm_calls == 0
        assert sim.monte_carlo.p10 <= sim.monte_carlo.p50 <= sim.monte_carlo.p90
        saved = repo.get_simulation_snapshot(
            simulation_id=sim.simulation_id,
            tenant_id="tenant_posto",
            pack_id="fuel_convenience",
        )
        assert saved is not None
        assert saved["created_by"] == "sentinel_profiler"

        # 2. Caso especifico de choque apenas no fluxo de caixa dispara cenario payment_term_cashflow
        cash_only_current = MetricSeriesPoint(
            ref_date="2026-11-21",
            margin_pct=20.0,
            daily_volume=1000.0,
            unit_cost=4.0,
            unit_price=5.0,
            net_cashflow_brl=-900.0,
        )
        cash_alert = profiler.run_sentinel_cycle(
            tenant_id="tenant_posto",
            pack_id="fuel_convenience",
            history=history,
            current=cash_only_current,
            enable_llm_synthesis=False,
        )
        assert cash_alert is not None
        assert cash_alert.anomalies[0].metric == "net_cashflow_brl"
        assert cash_alert.draft_simulation.scenario_type == "payment_term_cashflow"
    finally:
        manager.close()


@pytest.mark.unit
def test_profiler_sql_validation_blocks_mutations_and_trim_in_joins() -> None:
    """Queries do profiler passam por sqlglot Postgres read-only e bloqueiam TRIM em JOIN."""
    for name, sql in FUEL_CONVENIENCE_SQL_TEMPLATES.items():
        validated = validate_profiler_sql(sql)
        assert validated == sql, f"Template {name} deveria passar na validacao"

    with pytest.raises(ReadOnlySQLViolationError):
        validate_profiler_sql(
            "SELECT p.ped_cd_pedido FROM pedido p "
            "INNER JOIN itemped i ON TRIM(i.ped_cd_pedido) = TRIM(p.ped_cd_pedido)"
        )

    with pytest.raises(ReadOnlySQLViolationError):
        validate_profiler_sql("DELETE FROM pedido WHERE emp_cd_empresa = %s")


@pytest.mark.unit
def test_intent_tracker_sanitizes_pii_and_promotes_recurring_topics() -> None:
    """Telemetria remove PII (CPF, CNPJ, placa, email, telefone, cliente) e promove foco recorrente."""
    manager, conn, repo = _create_in_memory_db()
    try:
        tracker = IntentTracker(repository=repo, recurrence_threshold=3, window_days=7)
        pii_query = (
            "Cliente Joao Silva CPF 123.456.789-09 CNPJ 12.345.678/0001-95 "
            "placa ABC-1234 email joao@posto.com tel (11) 98765-4321 "
            "qual a margem da gasolina aditivada hoje?"
        )

        for _ in range(3):
            rec = tracker.record_query(
                tenant_id="tenant_alpha",
                pack_id="fuel_convenience",
                raw_query=pii_query,
                intent_name="vendas_analitico",
            )
            assert rec.metric_key == "margin_pct"
            assert rec.entity_type == "combustivel"

        cur = conn.cursor()
        cur.execute("SELECT entity_type, metric_key, topic_key, intent_name, hit_count FROM operator_intent_signals;")
        rows = cur.fetchall()
        cur.close()
        assert len(rows) == 1
        row_text = " ".join(str(x) for x in rows[0]).lower()
        for forbidden_pii in ("12345678909", "12345678", "joao", "abc-1234", "98765", "@"):
            assert forbidden_pii not in row_text
        assert rows[0][4] == 3

        promoted, cards = tracker.evaluate_recurrence(
            tenant_id="tenant_alpha",
            pack_id="fuel_convenience",
        )
        assert len(promoted) == 1
        assert promoted[0].metric_key == "margin_pct"
        assert len(cards) == 1
        assert cards[0].recommended_scenario == "price_discount_change"
        assert cards[0].hit_count == 3

        # Verifica promocao no profiler: desvio moderado (1.8 sigma) e detectado com foco prioritario
        profiler = BusinessProfiler(repository=repo, z_threshold=2.0, iqr_multiplier=2.5)
        history = _stable_history()
        # Media ~20.0, std ~0.21; 19.62 fica em ~-1.8 sigma (abaixo de 2.0, acima de 1.7)
        mild_drop = MetricSeriesPoint(
            ref_date="2026-11-22",
            margin_pct=19.62,
            daily_volume=1000.0,
            unit_cost=4.0,
            unit_price=5.0,
            net_cashflow_brl=2500.0,
        )
        assert profiler.detect_anomalies(history, mild_drop, priority_metrics=set()) == []
        priority_set = tracker.get_priority_metrics("tenant_alpha", "fuel_convenience")
        findings_priority = profiler.detect_anomalies(history, mild_drop, priority_metrics=priority_set)
        assert len(findings_priority) == 1
        assert findings_priority[0].metric == "margin_pct"
        assert findings_priority[0].is_priority_monitored is True
    finally:
        manager.close()


@pytest.mark.unit
def test_memory_manager_candidate_rules_blocked_until_hic_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regras extraidas nascem candidate, sao bloqueadas ate decisao HiC via API e passam a valer apos approve."""
    monkeypatch.setenv("AURA_API_KEY", "mem-test-secret-key")
    monkeypatch.setenv("AURA_ENFORCE_ADMIN_AUTH", "1")

    manager, _conn, repo = _create_in_memory_db()
    mem_mgr = MemoryManager(repository=repo)
    set_memory_manager(mem_mgr)

    try:
        # 1. Extracao deterministica de duas regras candidatas via chat do operador
        cand_approve = mem_mgr.extract_candidate_from_message(
            message="Corrigindo: nunca operar com margem abaixo de 18% na loja (CPF 123.456.789-09).",
            tenant_id="tenant_hic",
            pack_id="retail_supermarket",
        )
        cand_reject = mem_mgr.extract_candidate_from_message(
            message="Regra: custo unitario maximo de 5,00 reais.",
            tenant_id="tenant_hic",
            pack_id="retail_supermarket",
        )
        assert cand_approve is not None
        assert cand_approve.status == "candidate"
        assert cand_approve.metric == "projected_margin_pct"
        assert cand_approve.operator == ">="
        assert cand_approve.threshold_value == 18.0
        assert "123.456.789-09" not in cand_approve.description

        assert cand_reject is not None
        assert cand_reject.status == "candidate"

        # 2. Enquanto candidate: bloqueada no SimulationEngine e no contexto LLM do AuraEngine
        sim_engine = SimulationEngine()
        sim_req = SimulationRecomputeRequest(
            tenant_id="tenant_hic",
            pack_id="retail_supermarket",
            scenario_type="price_discount_change",
            horizon_days=30,
            baseline=SimulationBaseline(unit_price=10.0, unit_cost=8.5, daily_volume=100.0),
            shocks=ShockVector(discount_pct=0.0),
            iterations=200,
        )
        # Margem atual ~15%, menor que 18% -> violaria se estivesse active, mas candidate deve ser ignorada!
        res_before = sim_engine.run_simulation(sim_req, repository=repo)
        assert res_before.is_compliant is True
        assert res_before.violated_rules == []

        aura = AuraEngine(
            tenant_id="tenant_hic",
            pack_id="retail_supermarket",
            memory_manager=mem_mgr,
        )
        assert aura.format_active_business_rules_for_prompt("tenant_hic", "retail_supermarket") == ""

        # 3. API HiC: listar candidatos e decidir
        app = create_aura_app()
        client = TestClient(app)

        # Sem auth retorna 401
        assert client.get(
            "/api/v1/memory/rules",
            params={"tenant_id": "tenant_hic", "pack_id": "retail_supermarket"},
        ).status_code == 401

        cookie_client = TestClient(app, cookies={"aura_local_session": get_local_session_token()})
        r_list = cookie_client.get(
            "/api/v1/memory/rules",
            params={"tenant_id": "tenant_hic", "pack_id": "retail_supermarket", "status": "candidate"},
        )
        assert r_list.status_code == 200
        assert r_list.json()["total"] == 2

        # Rejeita cand_reject
        r_rej = client.post(
            f"/api/v1/memory/rules/{cand_reject.rule_id}/decision",
            json={
                "tenant_id": "tenant_hic",
                "pack_id": "retail_supermarket",
                "decision": "reject",
                "decided_by": "diretor_ops",
                "reason": "Custo varia por safra",
            },
            headers={"X-API-Key": "mem-test-secret-key"},
        )
        assert r_rej.status_code == 200
        assert r_rej.json()["new_status"] == "rejected"

        # Segunda decisao na mesma regra retorna 409 Conflict
        r_dup = client.post(
            f"/api/v1/memory/rules/{cand_reject.rule_id}/decision",
            json={
                "tenant_id": "tenant_hic",
                "pack_id": "retail_supermarket",
                "decision": "approve",
                "decided_by": "diretor_ops",
            },
            headers={"X-API-Key": "mem-test-secret-key"},
        )
        assert r_dup.status_code == 409

        # Aprova cand_approve
        r_app = client.post(
            f"/api/v1/memory/rules/{cand_approve.rule_id}/decision",
            json={
                "tenant_id": "tenant_hic",
                "pack_id": "retail_supermarket",
                "decision": "approve",
                "decided_by": "gerente_loja",
                "reason": "Meta minima aprovada",
            },
            headers={"X-API-Key": "mem-test-secret-key"},
        )
        assert r_app.status_code == 200
        assert r_app.json()["previous_status"] == "candidate"
        assert r_app.json()["new_status"] == "active"

        # 4. Apos aprovacao: ativa no SimulationEngine e visivel no contexto LLM (rejeitada continua fora)
        res_after = sim_engine.run_simulation(sim_req, repository=repo)
        assert res_after.is_compliant is False
        assert len(res_after.violated_rules) == 1
        assert res_after.violated_rules[0].rule_id == cand_approve.rule_id

        llm_block = aura.format_active_business_rules_for_prompt("tenant_hic", "retail_supermarket")
        assert "projected_margin_pct >= 18.0" in llm_block
        assert "projected_unit_cost" not in llm_block
    finally:
        set_memory_manager(None)
        manager.close()


@pytest.mark.unit
def test_strict_pack_id_isolation_across_intelligence_layer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Garante isolamento estrito por pack_id sem vazamento ou fallback para PostoTools."""
    monkeypatch.setenv("AURA_API_KEY", "iso-test-secret-key")
    monkeypatch.setenv("AURA_ENFORCE_ADMIN_AUTH", "1")

    manager, _conn, repo = _create_in_memory_db()
    mem_mgr = MemoryManager(repository=repo)
    set_memory_manager(mem_mgr)

    try:
        profiler = BusinessProfiler(repository=repo)
        tracker = IntentTracker(repository=repo, recurrence_threshold=2)

        # 1. Profiler ERP bloqueia pack diferente de fuel_convenience sem provedor registrado
        with pytest.raises(LookupError):
            profiler.fetch_series_from_erp(
                cursor=object(),
                pack_id="retail_supermarket",
                filial_id=1,
            )

        # 2. Sinais e regras de fuel_convenience nao vazam para health_pharmacy
        for _ in range(3):
            tracker.record_query("t1", "fuel_convenience", "margem da gasolina", "vendas_analitico")

        assert tracker.get_priority_metrics("t1", "fuel_convenience") == {"margin_pct"}
        assert tracker.get_priority_metrics("t1", "health_pharmacy") == set()

        rule = mem_mgr.extract_candidate_from_message(
            "Regra: nunca operar com margem abaixo de 15%.",
            tenant_id="t1",
            pack_id="fuel_convenience",
        )
        assert rule is not None
        assert mem_mgr.list_rules("t1", "health_pharmacy") == []

        app = create_aura_app()
        client = TestClient(app)
        r_cross = client.post(
            f"/api/v1/memory/rules/{rule.rule_id}/decision",
            json={
                "tenant_id": "t1",
                "pack_id": "health_pharmacy",
                "decision": "approve",
                "decided_by": "admin",
            },
            headers={"X-API-Key": "iso-test-secret-key"},
        )
        assert r_cross.status_code == 404
    finally:
        set_memory_manager(None)
        manager.close()


@pytest.mark.unit
def test_economic_llm_synthesizer_uses_singleton_compact_sanitized_json_and_pgvector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Singleton LLM recebe apenas JSON compacto sanitizado + trechos pgvector sanitizados."""
    manager, _conn, repo = _create_in_memory_db()
    captured_calls: list[dict[str, Any]] = []

    class _FakeModels:
        def generate_content(self, model: str, contents: str) -> Any:
            captured_calls.append({"model": model, "contents": contents})
            return SimpleNamespace(
                text="1. Efeito na margem liquida. 2. Pressao de caixa. 3. Cliente [REDACTED:PERSON] ignorado."
            )

    fake_client = SimpleNamespace(models=_FakeModels())
    monkeypatch.setattr("core.intelligence.synthesizer.get_genai_client", lambda api_key=None: fake_client)

    def _fake_pgvector_retriever(query: str, pack_id: str, top_k: int) -> list[dict[str, Any]]:
        assert pack_id == "fuel_convenience"
        return [
            {
                "content": (
                    "Manual de precificacao: reajuste na bomba exige revisao de concorrencia. "
                    "Contato Joao Silva CPF 123.456.789-09."
                )
            }
        ][:top_k]

    try:
        synth = SecondOrderSynthesizer(
            model_name="models/gemini-2.5-flash",
            rag_retriever=_fake_pgvector_retriever,
        )
        profiler = BusinessProfiler(repository=repo, synthesizer=synth)
        history = _stable_history()
        drop_point = MetricSeriesPoint(
            ref_date="2026-11-25",
            margin_pct=10.5,
            daily_volume=1000.0,
            unit_cost=4.47,
            unit_price=5.0,
            net_cashflow_brl=2500.0,
        )

        alert = profiler.run_sentinel_cycle(
            tenant_id="tenant_eco",
            pack_id="fuel_convenience",
            history=history,
            current=drop_point,
            enable_llm_synthesis=True,
        )
        assert alert is not None
        assert alert.llm_calls == 1
        assert len(captured_calls) == 1

        prompt_sent = captured_calls[0]["contents"]
        assert "123.456.789-09" not in prompt_sent
        assert "DADOS_COMPACTOS_JSON:" in prompt_sent
        assert "CONTEXTO_PGVECTOR:" in prompt_sent
        # Garante payload enxuto (< 3 KB) em vez de despejar historico bruto
        assert len(prompt_sent) < 3000
        json_part = prompt_sent.split("DADOS_COMPACTOS_JSON: ", 1)[1].split("\nCONTEXTO_PGVECTOR:", 1)[0]
        parsed_json = json.loads(json_part)
        assert parsed_json["pack_id"] == "fuel_convenience"
        assert "p50" in parsed_json["simulation"]
        assert len(alert.rag_references) == 1
        assert "123.456.789-09" not in alert.rag_references[0]
    finally:
        manager.close()


@pytest.mark.unit
def test_zero_em_dashes_in_intelligence_files() -> None:
    """Garante conformidade estrita com a regra de zero travessoes nos modulos da Fase 2."""
    files = [
        BASE_DIR / "core" / "intelligence" / "__init__.py",
        BASE_DIR / "core" / "intelligence" / "models.py",
        BASE_DIR / "core" / "intelligence" / "profiler.py",
        BASE_DIR / "core" / "intelligence" / "intent_tracker.py",
        BASE_DIR / "core" / "intelligence" / "memory_manager.py",
        BASE_DIR / "core" / "intelligence" / "synthesizer.py",
        BASE_DIR / "core" / "intelligence" / "api.py",
        BASE_DIR / "core" / "simulation" / "repository.py",
        Path(__file__),
    ]
    for path in files:
        content = path.read_text(encoding="utf-8")
        assert "\u2014" not in content, f"Travessao encontrado em {path}"
        assert "\u2013" not in content, f"Meia-risca encontrada em {path}"
