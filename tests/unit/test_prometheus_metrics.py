"""
Suite de testes unitarios para o Exportador Prometheus (/metrics)
e Manifesto de Observabilidade SRE Grafana (P2-4).
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from core.aura_api import create_aura_app
from core.telemetry import AuraSRETelemetry

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def test_telemetry_p2_4_operational_metrics_collection() -> None:
    """Valida a coleta de latencia vetorial, cache do router, pool de conexoes e ferramentas."""
    telemetry = AuraSRETelemetry(session_memory=None, max_samples=100)
    telemetry.reset()

    telemetry.record_ttft(120.5)
    telemetry.record_ttft(240.0)
    telemetry.record_hydration(45.0)

    telemetry.record_vector_search_latency(15.2)
    telemetry.record_vector_search_latency(28.4)
    telemetry.record_vector_search_latency(62.0)

    telemetry.record_router_cache_hit(True)
    telemetry.record_router_cache_hit(True)
    telemetry.record_router_cache_hit(True)
    telemetry.record_router_cache_hit(False)

    telemetry.record_db_pool_stats(active_erp=4, active_vec=2, wait_ms=3.75)

    telemetry.record_tool_execution("previsao_tanques", status="success", latency_ms=85.0)
    telemetry.record_tool_execution("previsao_tanques", status="success", latency_ms=95.0)
    telemetry.record_tool_execution("auditoria_turno", status="error", latency_ms=110.0)

    summary = telemetry.get_metrics_summary()
    assert summary["status"] == "ok"
    assert summary["vector_search_ms"]["count"] == 3
    assert summary["vector_search_ms"]["p50"] == 28.4
    assert summary["router_cache_hits"] == 3
    assert summary["router_cache_misses"] == 1
    assert summary["router_cache_hit_ratio"] == 0.75
    assert summary["db_pool"]["active_erp"] == 4
    assert summary["db_pool"]["active_vec"] == 2
    assert summary["db_pool"]["wait_ms"] == 3.75
    assert summary["tool_executions"]["previsao_tanques"]["success"] == 2
    assert summary["tool_executions"]["auditoria_turno"]["error"] == 1


def test_export_prometheus_metrics_openmetrics_format() -> None:
    """Valida a formatacao rigorosa OpenMetrics / Prometheus gerada por export_prometheus_metrics()."""
    telemetry = AuraSRETelemetry(session_memory=None, max_samples=100)
    telemetry.reset()

    telemetry.record_ttft(150.0)
    telemetry.record_hydration(35.0)
    telemetry.record_vector_search_latency(22.5)
    telemetry.record_action_requested("act_1")
    telemetry.record_action_approved("act_1")
    telemetry.record_action_rolled_back("act_2", reason="timeout")
    telemetry.record_security_block(reason="RBAC block")
    telemetry.record_router_cache_hit(True)
    telemetry.record_router_cache_hit(False)
    telemetry.record_db_pool_stats(active_erp=3, active_vec=1, wait_ms=2.5)
    telemetry.record_tool_execution("lmc_anp", status="success", latency_ms=42.0)

    prom_text = telemetry.export_prometheus_metrics()

    assert "# HELP aura_ttft_ms" in prom_text
    assert "# TYPE aura_ttft_ms summary" in prom_text
    assert 'aura_ttft_ms{quantile="0.5"} 150.00' in prom_text
    assert "aura_ttft_ms_count 1" in prom_text

    assert "# TYPE aura_vector_search_latency_ms summary" in prom_text
    assert 'aura_vector_search_latency_ms{quantile="0.95"} 22.50' in prom_text

    assert "aura_actions_requested_total 1" in prom_text
    assert "aura_actions_approved_total 1" in prom_text
    assert "aura_actions_rolled_back_total 1" in prom_text
    assert "aura_security_blocks_total 1" in prom_text

    assert "aura_router_cache_hits_total 1" in prom_text
    assert "aura_router_cache_misses_total 1" in prom_text
    assert "aura_router_cache_hit_ratio 0.5000" in prom_text

    assert 'aura_db_pool_active_connections{pool="erp"} 3' in prom_text
    assert 'aura_db_pool_active_connections{pool="vector"} 1' in prom_text
    assert "aura_db_pool_wait_ms 2.50" in prom_text

    assert 'aura_tool_executions_total{tool_name="lmc_anp",status="success"} 1' in prom_text
    assert 'aura_tool_execution_latency_ms_sum{tool_name="lmc_anp"} 42.00' in prom_text


def test_fastapi_metrics_endpoints() -> None:
    """Valida os endpoints HTTP GET /metrics e GET /api/v1/aura/metrics/prometheus."""
    telemetry = AuraSRETelemetry(session_memory=None, max_samples=50)
    telemetry.reset()
    telemetry.record_ttft(99.0)
    telemetry.record_router_cache_hit(True)
    telemetry.record_db_pool_stats(active_erp=5, active_vec=2, wait_ms=1.2)
    telemetry.record_tool_execution("fechamento_turno", status="success", latency_ms=60.0)

    mock_engine = MagicMock()
    mock_engine.telemetry = telemetry

    app = create_aura_app(engine=mock_engine)
    client = TestClient(app)

    for path in ("/metrics", "/api/v1/aura/metrics/prometheus"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        assert "version=0.0.4" in resp.headers["content-type"]
        body = resp.text
        assert "aura_ttft_ms" in body
        assert "aura_router_cache_hits_total 1" in body
        assert 'aura_db_pool_active_connections{pool="erp"} 5' in body
        assert 'aura_tool_executions_total{tool_name="fechamento_turno",status="success"} 1' in body


def test_grafana_dashboard_manifest_structure() -> None:
    """Valida a existencia e estrutura declarativa do manifesto Grafana SRE."""
    dashboard_path = BASE_DIR / "deploy" / "grafana_dashboard_aura.json"
    assert dashboard_path.exists(), "Manifesto deploy/grafana_dashboard_aura.json deve existir"

    raw = dashboard_path.read_text(encoding="utf-8")
    data = json.loads(raw)

    assert data["uid"] == "aura-sre-fleet-v1"
    assert "panels" in data and len(data["panels"]) >= 5

    all_exprs = [
        target["expr"]
        for panel in data["panels"]
        for target in panel.get("targets", [])
        if "expr" in target
    ]
    joined_exprs = " ".join(all_exprs)
    assert "aura_ttft_ms" in joined_exprs
    assert "aura_vector_search_latency_ms" in joined_exprs
    assert "aura_router_cache_hit_ratio" in joined_exprs
    assert "aura_db_pool_active_connections" in joined_exprs
    assert "aura_tool_executions_total" in joined_exprs
    assert "aura_security_blocks_total" in joined_exprs


def test_zero_travessoes_in_p2_4_files() -> None:
    """Garante ausencia total de travessoes nos arquivos de P2-4."""
    files_to_check = [
        BASE_DIR / "core" / "telemetry.py",
        BASE_DIR / "core" / "aura_api.py",
        BASE_DIR / "deploy" / "grafana_dashboard_aura.json",
        BASE_DIR / "tests" / "unit" / "test_prometheus_metrics.py",
    ]
    for path in files_to_check:
        content = path.read_text(encoding="utf-8")
        assert "\u2014" not in content, f"Travessao (em-dash) encontrado em {path.name}"
        assert "\u2013" not in content, f"Travessao (en-dash) encontrado em {path.name}"
