"""Testes unitarios deterministicos para o Motor What-If, RulesEvaluator,
isolamento por pack_id/tenant_id, schema de memoria e endpoint Zero-LLM (Fase 1).
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from config.settings import BASE_DIR
from core.aura_api import create_aura_app, get_local_session_token
from core.domain.domain_pack_loader import DomainPackConfig
from core.domain.fuel_convenience.simulator import FuelConvenienceSimulator
from core.domain.simulator_contract import (
    DomainSimulatorRegistry,
    UniversalDomainSimulator,
)
from core.migrations import AuraMigrationManager
from core.simulation import (
    BusinessProfileSnapshotRecord,
    BusinessRule,
    RulesEvaluator,
    ShockVector,
    SimulationBaseline,
    SimulationEngine,
    SimulationRecomputeRequest,
    SimulationRepository,
    set_simulation_repository,
)


def _create_in_memory_sim_db() -> tuple[AuraMigrationManager, sqlite3.Connection, SimulationRepository]:
    manager = AuraMigrationManager(db_path=":memory:")
    manager.upgrade("head")
    conn = manager._shared_memory_conn
    assert conn is not None
    repo = SimulationRepository(connection=conn, dialect="sqlite")
    return manager, conn, repo


def _default_baseline() -> SimulationBaseline:
    return SimulationBaseline(
        unit_price=100.0,
        unit_cost=70.0,
        daily_volume=200.0,
        volume_std_dev_pct=4.0,
        cost_std_dev_pct=1.5,
        elasticity_mean=-1.2,
        elasticity_std_dev=0.2,
        receivable_days=15.0,
        payable_days=30.0,
        annual_capital_cost_pct=12.0,
        fixed_daily_cost=1000.0,
    )


@pytest.mark.unit
def test_monte_carlo_reproducibility_with_fixed_seed_and_latency() -> None:
    """Mesma seed e 5.000 iteracoes devem produzir resultados identicos e < 100ms."""
    engine = SimulationEngine()
    req = SimulationRecomputeRequest(
        tenant_id="tenant_alpha",
        pack_id="retail_supermarket",
        simulation_id="sim_repro_01",
        scenario_type="price_discount_change",
        horizon_days=30,
        baseline=_default_baseline(),
        shocks=ShockVector(price_delta_pct=4.0, discount_pct=1.0),
        iterations=5000,
        seed=202611,
    )

    res_a = engine.run_simulation(req)
    res_b = engine.run_simulation(req)

    assert res_a.llm_calls == 0
    assert res_a.monte_carlo.iterations == 5000
    assert res_a.monte_carlo.seed == 202611
    assert res_a.monte_carlo.p10 <= res_a.monte_carlo.p50 <= res_a.monte_carlo.p90
    assert res_a.monte_carlo == res_b.monte_carlo
    assert res_a.sensitivity == res_b.sensitivity
    assert res_a.projected_metrics == res_b.projected_metrics
    assert res_a.elapsed_ms < 100.0
    assert res_b.elapsed_ms < 100.0

    # Seed diferente deve produzir distribuicao amostral distinta
    req_other_seed = req.model_copy(update={"seed": 9999})
    res_c = engine.run_simulation(req_other_seed)
    assert res_c.monte_carlo.p50 != res_a.monte_carlo.p50 or res_c.monte_carlo.std_dev != res_a.monte_carlo.std_dev


@pytest.mark.unit
@pytest.mark.parametrize("horizon_days", [30, 60, 90])
def test_three_universal_scenarios_and_horizons(horizon_days: int) -> None:
    """Valida matematica deterministica dos 3 cenarios universais em 30/60/90 dias."""
    engine = SimulationEngine()
    baseline = _default_baseline()

    # 1. Alteracao de preco/desconto
    r_price = engine.run_simulation(
        SimulationRecomputeRequest(
            tenant_id="t1",
            pack_id="wholesale_distribution",
            scenario_type="price_discount_change",
            horizon_days=horizon_days,  # type: ignore[arg-type]
            baseline=baseline,
            shocks=ShockVector(price_delta_pct=-10.0, discount_pct=0.0),
            seed=42,
        )
    )
    assert r_price.horizon_days == horizon_days
    assert r_price.projected_metrics["projected_unit_margin_brl"] == pytest.approx(20.0, abs=0.01)
    assert len(r_price.sensitivity) == 2

    # 2. Variacao de custo/fornecedor sem repasse reduz lucro projetado
    r_cost = engine.run_simulation(
        SimulationRecomputeRequest(
            tenant_id="t1",
            pack_id="wholesale_distribution",
            scenario_type="cost_supplier_variation",
            horizon_days=horizon_days,  # type: ignore[arg-type]
            baseline=baseline,
            shocks=ShockVector(supplier_cost_delta_pct=15.0, cost_passthrough_pct=0.0),
            seed=42,
        )
    )
    assert r_cost.monte_carlo.p50 < 0.0
    assert r_cost.projected_metrics["projected_unit_margin_brl"] < 30.0

    # 3. Mudanca de prazo/fluxo de caixa: aumentar recebimento e reduzir pagamento consome caixa e gera custo
    r_cash_bad = engine.run_simulation(
        SimulationRecomputeRequest(
            tenant_id="t1",
            pack_id="wholesale_distribution",
            scenario_type="payment_term_cashflow",
            horizon_days=horizon_days,  # type: ignore[arg-type]
            baseline=baseline,
            shocks=ShockVector(receivable_days_delta=10.0, payable_days_delta=-5.0),
            seed=42,
        )
    )
    assert r_cash_bad.projected_metrics["working_capital_delta_brl"] > 0.0
    assert r_cash_bad.monte_carlo.p50 < 0.0

    # Reduzir recebimento e alongar pagamento libera caixa e gera ganho financeiro
    r_cash_good = engine.run_simulation(
        SimulationRecomputeRequest(
            tenant_id="t1",
            pack_id="wholesale_distribution",
            scenario_type="payment_term_cashflow",
            horizon_days=horizon_days,  # type: ignore[arg-type]
            baseline=baseline,
            shocks=ShockVector(receivable_days_delta=-5.0, payable_days_delta=10.0),
            seed=42,
        )
    )
    assert r_cash_good.projected_metrics["working_capital_delta_brl"] < 0.0
    assert r_cash_good.monte_carlo.p50 > 0.0


@pytest.mark.unit
def test_strict_pack_id_isolation_and_no_posto_fallback() -> None:
    """Packs nao-posto nao usam FuelConvenienceSimulator nem importam PostoTools."""
    registry = DomainSimulatorRegistry()

    sim_super = registry.resolve("retail_supermarket")
    sim_pharma = registry.resolve("pharmacy_health")
    sim_custom = registry.resolve("clinica_veterinaria")
    sim_fuel = registry.resolve("fuel_convenience")

    assert type(sim_super) is UniversalDomainSimulator
    assert sim_super.pack_id == "retail_supermarket"
    assert type(sim_pharma) is UniversalDomainSimulator
    assert sim_pharma.pack_id == "pharmacy_health"
    assert type(sim_custom) is UniversalDomainSimulator
    assert sim_custom.pack_id == "clinica_veterinaria"
    assert isinstance(sim_fuel, FuelConvenienceSimulator)
    assert sim_fuel.pack_id == "fuel_convenience"

    # Garante via AST que nenhum modulo de simulacao importa ou referencia PostoTools ou google.genai
    import ast

    sim_files = [
        BASE_DIR / "core" / "domain" / "simulator_contract.py",
        BASE_DIR / "core" / "domain" / "fuel_convenience" / "simulator.py",
        BASE_DIR / "core" / "simulation" / "engine.py",
        BASE_DIR / "core" / "simulation" / "rules_evaluator.py",
        BASE_DIR / "core" / "simulation" / "repository.py",
        BASE_DIR / "core" / "simulation" / "api.py",
    ]
    for path in sim_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "google.genai" not in alias.name, f"Import LLM proibido em {path}"
                    assert "core.tools" not in alias.name, f"Import PostoTools proibido em {path}"
            elif isinstance(node, ast.ImportFrom):
                mod_name = node.module or ""
                assert "google.genai" not in mod_name, f"Import LLM proibido em {path}"
                assert "core.tools" not in mod_name, f"Import PostoTools proibido em {path}"
                for alias in node.names:
                    assert alias.name != "PostoTools", f"Import PostoTools proibido em {path}"
            elif isinstance(node, ast.Name):
                assert node.id != "PostoTools", f"Uso de PostoTools proibido em {path}"


@pytest.mark.unit
def test_rules_evaluator_binary_yaml_and_active_memory_rules() -> None:
    """RulesEvaluator avalia YAML + business_memory_rules 'active' e ignora 'candidate'/'rejected'."""
    evaluator = RulesEvaluator()
    pack_cfg = DomainPackConfig(
        pack_id="retail_supermarket",
        pack_name="Supermercado",
        vertical="supermarket_retail",
        hard_rules=[
            {
                "rule_id": "yaml_min_margin",
                "rule_key": "margem_minima_yaml",
                "metric": "projected_margin_pct",
                "operator": ">=",
                "threshold_value": 25.0,
                "severity": "CRITICAL",
                "description": "Piso de margem da rede",
            }
        ],
    )

    memory_rules = [
        BusinessRule(
            rule_id="mem_active_p10",
            tenant_id="tenant_a",
            pack_id="retail_supermarket",
            rule_key="p10_floor",
            metric="net_profit_delta_p10_brl",
            operator=">=",
            threshold_value=-1000.0,
            severity="HIGH",
            status="active",
        ),
        BusinessRule(
            rule_id="mem_candidate_ignored",
            tenant_id="tenant_a",
            pack_id="retail_supermarket",
            rule_key="candidate_should_not_fire",
            metric="projected_margin_pct",
            operator=">=",
            threshold_value=90.0,
            severity="CRITICAL",
            status="candidate",
        ),
        BusinessRule(
            rule_id="mem_rejected_ignored",
            tenant_id="tenant_a",
            pack_id="retail_supermarket",
            rule_key="rejected_should_not_fire",
            metric="projected_margin_pct",
            operator=">=",
            threshold_value=90.0,
            severity="CRITICAL",
            status="rejected",
        ),
        BusinessRule(
            rule_id="mem_other_tenant_ignored",
            tenant_id="tenant_b",
            pack_id="retail_supermarket",
            rule_key="other_tenant",
            metric="projected_margin_pct",
            operator=">=",
            threshold_value=90.0,
            severity="CRITICAL",
            status="active",
        ),
        BusinessRule(
            rule_id="mem_other_pack_ignored",
            tenant_id="tenant_a",
            pack_id="fuel_convenience",
            rule_key="other_pack",
            metric="projected_margin_pct",
            operator=">=",
            threshold_value=90.0,
            severity="CRITICAL",
            status="active",
        ),
        BusinessRule(
            rule_id="mem_between_band",
            tenant_id="tenant_a",
            pack_id="retail_supermarket",
            rule_key="wc_band",
            metric="working_capital_delta_brl",
            operator="between",
            threshold_value=-5000.0,
            threshold_upper=5000.0,
            severity="MEDIUM",
            status="active",
        ),
    ]

    violations = evaluator.evaluate(
        metrics={
            "projected_margin_pct": 22.0,
            "net_profit_delta_p10_brl": -2500.0,
            "working_capital_delta_brl": 6500.0,
        },
        tenant_id="tenant_a",
        pack_id="retail_supermarket",
        pack_config=pack_cfg,
        memory_rules=memory_rules,
    )

    violated_ids = [v.rule_id for v in violations]
    assert violated_ids == ["yaml_min_margin", "mem_active_p10", "mem_between_band"]
    assert violations[0].source == "yaml"
    assert violations[1].source == "business_memory"


@pytest.mark.unit
def test_repository_isolation_immutability_and_zero_pii_signals() -> None:
    """Valida isolamento (tenant_id, pack_id), imutabilidade de snapshots e zero PII."""
    manager, _conn, repo = _create_in_memory_sim_db()
    try:
        # 1. Business Profile Snapshot isolado
        repo.save_business_profile_snapshot(
            BusinessProfileSnapshotRecord(
                snapshot_id="prof_1",
                tenant_id="tenant_1",
                pack_id="pharmacy_health",
                reference_period="2026-10",
                means={"ticket_medio": 85.4},
                std_devs={"ticket_medio": 12.1},
                seasonality={"fri": 1.18},
                abc_curve={"A": 0.72, "B": 0.2, "C": 0.08},
                sample_size=1420,
            )
        )
        assert repo.get_latest_business_profile("tenant_1", "pharmacy_health") is not None
        assert repo.get_latest_business_profile("tenant_2", "pharmacy_health") is None
        assert repo.get_latest_business_profile("tenant_1", "fuel_convenience") is None

        # 2. Rules filtradas por tenant_id + pack_id + status
        repo.save_business_rule(
            BusinessRule(
                rule_id="r_active_1",
                tenant_id="tenant_1",
                pack_id="pharmacy_health",
                rule_key="min_margin",
                metric="projected_margin_pct",
                operator=">=",
                threshold_value=28.0,
                status="active",
                origin="operator_chat",
                author="gestor",
            )
        )
        repo.save_business_rule(
            BusinessRule(
                rule_id="r_cand_1",
                tenant_id="tenant_1",
                pack_id="pharmacy_health",
                rule_key="cand_margin",
                metric="projected_margin_pct",
                operator=">=",
                threshold_value=35.0,
                status="candidate",
                origin="ai_suggestion",
                author="aura",
            )
        )
        active_rules = repo.list_business_rules("tenant_1", "pharmacy_health", status="active")
        assert [r.rule_id for r in active_rules] == ["r_active_1"]
        assert repo.list_business_rules("tenant_2", "pharmacy_health", status="active") == []

        # 3. operator_intent_signals sem PII
        sig_id = repo.record_operator_intent_signal(
            tenant_id="tenant_1",
            pack_id="pharmacy_health",
            entity_type="cliente 123.456.789-09",
            metric_key="margem_liquida",
            topic_key="contato joao@empresa.com.br",
            intent_name="simular_cenario_what_if",
        )
        # Segundo hit incrementa contagem
        sig_id_2 = repo.record_operator_intent_signal(
            tenant_id="tenant_1",
            pack_id="pharmacy_health",
            entity_type="cliente 123.456.789-09",
            metric_key="margem_liquida",
            topic_key="contato joao@empresa.com.br",
            intent_name="simular_cenario_what_if",
        )
        assert sig_id == sig_id_2
        cur = _conn.cursor()
        cur.execute(
            "SELECT entity_type, topic_key, hit_count FROM operator_intent_signals WHERE signal_id = ?;",
            (sig_id,),
        )
        row = cur.fetchone()
        cur.close()
        assert row is not None
        assert "123.456.789-09" not in row[0]
        assert "joao@empresa.com.br" not in row[1]
        assert row[2] == 2

        # 4. simulation_snapshots imutavel + realized_outcome unico
        engine = SimulationEngine()
        req = SimulationRecomputeRequest(
            tenant_id="tenant_1",
            pack_id="pharmacy_health",
            simulation_id="sim_immut_001",
            scenario_type="price_discount_change",
            horizon_days=60,
            baseline=_default_baseline(),
            shocks=ShockVector(price_delta_pct=2.0),
            seed=77,
            persist_snapshot=True,
        )
        engine.run_simulation(req, repository=repo)

        # Sobrescrever simulation_id existente deve falhar
        with pytest.raises(ValueError, match="imutavel"):
            engine.run_simulation(req, repository=repo)

        # Isolamento por tenant_id e pack_id na leitura
        assert repo.get_simulation_snapshot("sim_immut_001", "tenant_2", "pharmacy_health") is None
        assert repo.get_simulation_snapshot("sim_immut_001", "tenant_1", "fuel_convenience") is None
        snap = repo.get_simulation_snapshot("sim_immut_001", "tenant_1", "pharmacy_health")
        assert snap is not None
        assert snap["horizon_days"] == 60

        # Registro posterior do resultado realizado (unico)
        assert repo.record_realized_outcome(
            "sim_immut_001",
            "tenant_1",
            "pharmacy_health",
            {"realized_delta_brl": 12450.0},
        ) is True
        with pytest.raises(ValueError, match="imutavel"):
            repo.record_realized_outcome(
                "sim_immut_001",
                "tenant_1",
                "pharmacy_health",
                {"realized_delta_brl": 99999.0},
            )
    finally:
        manager.close()


@pytest.mark.unit
def test_recompute_endpoint_zero_llm_auth_and_recompute_by_simulation_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valida POST /api/v1/simulate/recompute com auth dual, Zero-LLM e lookup por simulation_id."""
    monkeypatch.setenv("AURA_API_KEY", "sim-test-secret-key")
    monkeypatch.setenv("AURA_ENFORCE_ADMIN_AUTH", "1")

    manager, _conn, repo = _create_in_memory_sim_db()
    set_simulation_repository(repo)
    try:
        app = create_aura_app()
        client = TestClient(app)

        body = {
            "tenant_id": "tenant_api",
            "pack_id": "retail_supermarket",
            "simulation_id": "sim_api_001",
            "scenario_type": "price_discount_change",
            "horizon_days": 30,
            "baseline": _default_baseline().model_dump(),
            "shocks": {"price_delta_pct": 5.0, "discount_pct": 0.0},
            "iterations": 5000,
            "seed": 123,
            "persist_snapshot": True,
        }

        # 1. Acesso via Tailscale / LAN sem X-API-Key deve retornar 401
        r_unauth = client.post(
            "/api/v1/simulate/recompute",
            json=body,
            headers={"Origin": "https://aura-edge.ts.net"},
        )
        assert r_unauth.status_code == 401

        # 2. Acesso localhost sem cookie e sem key com AURA_ENFORCE_ADMIN_AUTH=1 deve retornar 401
        r_local_no_auth = client.post("/api/v1/simulate/recompute", json=body)
        assert r_local_no_auth.status_code == 401

        # 3. Acesso autorizado via X-API-Key persiste snapshot inicial
        r_ok = client.post(
            "/api/v1/simulate/recompute",
            json=body,
            headers={"X-API-Key": "sim-test-secret-key"},
        )
        assert r_ok.status_code == 200
        data_ok = r_ok.json()
        assert data_ok["llm_calls"] == 0
        assert data_ok["elapsed_ms"] < 100.0
        assert data_ok["monte_carlo"]["iterations"] == 5000
        assert data_ok["monte_carlo"]["seed"] == 123

        # 4. Recalculo via slider usando apenas simulation_id + novo choque + cookie HttpOnly local
        recompute_body = {
            "tenant_id": "tenant_api",
            "pack_id": "retail_supermarket",
            "simulation_id": "sim_api_001",
            "scenario_type": "price_discount_change",
            "horizon_days": 30,
            "shocks": {"price_delta_pct": -8.0, "discount_pct": 2.0},
            "iterations": 5000,
            "seed": 123,
            "persist_snapshot": False,
        }
        cookie_client = TestClient(app, cookies={"aura_local_session": get_local_session_token()})
        r_slider = cookie_client.post(
            "/api/v1/simulate/recompute",
            json=recompute_body,
        )
        assert r_slider.status_code == 200
        data_slider = r_slider.json()
        assert data_slider["llm_calls"] == 0
        assert data_slider["elapsed_ms"] < 100.0
        assert data_slider["monte_carlo"]["p50"] != data_ok["monte_carlo"]["p50"]

        # 5. simulation_id inexistente para outro tenant retorna 404 (isolamento)
        recompute_other_tenant = dict(recompute_body, tenant_id="other_tenant")
        r_not_found = client.post(
            "/api/v1/simulate/recompute",
            json=recompute_other_tenant,
            headers={"X-API-Key": "sim-test-secret-key"},
        )
        assert r_not_found.status_code == 404
    finally:
        set_simulation_repository(None)
        manager.close()


@pytest.mark.unit
def test_zero_em_dashes_in_simulation_files() -> None:
    """Garante conformidade estrita com a regra de zero travessoes nos novos modulos."""
    files = [
        BASE_DIR / "alembic" / "versions" / "0003_simulation_and_business_memory.py",
        BASE_DIR / "core" / "domain" / "simulator_contract.py",
        BASE_DIR / "core" / "domain" / "fuel_convenience" / "__init__.py",
        BASE_DIR / "core" / "domain" / "fuel_convenience" / "simulator.py",
        BASE_DIR / "core" / "simulation" / "__init__.py",
        BASE_DIR / "core" / "simulation" / "models.py",
        BASE_DIR / "core" / "simulation" / "rules_evaluator.py",
        BASE_DIR / "core" / "simulation" / "repository.py",
        BASE_DIR / "core" / "simulation" / "engine.py",
        BASE_DIR / "core" / "simulation" / "api.py",
        Path(__file__),
    ]
    for path in files:
        content = path.read_text(encoding="utf-8")
        assert "\u2014" not in content, f"Travessao encontrado em {path}"
        assert "\u2013" not in content, f"Meia-risca encontrada em {path}"
