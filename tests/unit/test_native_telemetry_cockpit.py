"""
Testes Unitarios do Cockpit Nativo de Telemetria Ultraleve AURA (Fase P3-1).

Valida:
1. Coleta enriquecida em `AuraSRETelemetry.get_metrics_summary()` contendo:
   - SLIs de latencia TTFT e percentis (P50, P90, P95, P99)
   - Hidratacao de micro-widgets GenUI
   - Metricas de recursos do processo local (RAM RSS em MB, Uptime, PID)
   - Amostras recentes de TTFT para projecao de curva
2. Rota FastAPI `GET /api/v1/aura/telemetry/metrics` respondendo com payload integro
3. Presenca dos elementos do Cockpit no frontend (`web/index.html`):
   - Botao no cabecalho (`#btn-open-telemetry`) com badge de pulso
   - Item no menu lateral (`#sidebar-btn-open-telemetry`)
   - Modal executivo (`#aura-telemetry-modal`) e canvas nativo (`#telemetry-ttft-canvas`)
   - Script modular `aura-telemetry.js`
4. Regra inegociavel de ZERO travessoes (`\\u2014`, `\\u2013`).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from config.settings import BASE_DIR
from core.aura_api import create_aura_app
from core.aura_engine import AuraEngine, AuraSessionMemory
from core.telemetry import AuraSRETelemetry


@pytest.fixture
def test_client() -> TestClient:
    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(
        tenant_id="test_telemetry_tenant",
        filial_id="filial_01",
        session_memory=mem,
    )
    engine.telemetry.record_ttft(ms=512.5)
    engine.telemetry.record_ttft(ms=704.0)
    engine.telemetry.record_hydration(ms=340.0)
    engine.telemetry.record_action_requested()
    engine.telemetry.record_action_approved()
    engine.telemetry.record_security_block(reason="test_block")

    app = create_aura_app(engine)
    return TestClient(app)


def test_telemetry_summary_contains_process_and_samples() -> None:
    """Valida presenca de process_metrics e recent_ttft_samples no resumo de telemetria."""
    mem = AuraSessionMemory(db_path=":memory:")
    tel = AuraSRETelemetry(session_memory=mem)
    tel.record_ttft(ms=350.0)
    tel.record_ttft(ms=820.0)

    summary = tel.get_metrics_summary()
    assert summary["status"] == "ok"
    assert "ttft_ms" in summary
    assert summary["ttft_ms"]["p50"] > 0
    assert summary["ttft_ms"]["count"] >= 2

    assert "process_metrics" in summary
    proc = summary["process_metrics"]
    assert "rss_memory_mb" in proc
    assert proc["rss_memory_mb"] >= 0
    assert "uptime_seconds" in proc
    assert proc["pid"] == os.getpid()

    assert "recent_ttft_samples" in summary
    assert isinstance(summary["recent_ttft_samples"], list)
    assert len(summary["recent_ttft_samples"]) >= 2


def test_api_telemetry_metrics_endpoint(test_client: TestClient) -> None:
    """Garante resposta HTTP 200 com contrato valido no endpoint /api/v1/aura/telemetry/metrics."""
    resp = test_client.get("/api/v1/aura/telemetry/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "ttft_ms" in data
    assert "hydration_ms" in data
    assert "process_metrics" in data
    assert "db_pool" in data
    assert data["total_actions_requested"] >= 1
    assert data["total_actions_approved"] >= 1
    assert data["security_blocks"] >= 1


def test_frontend_contains_telemetry_cockpit_markup() -> None:
    """Verifica presenca de todos os componentes do Cockpit Nativo no HTML do frontend."""
    index_path = BASE_DIR / "web" / "index.html"
    assert index_path.is_file(), "web/index.html nao encontrado"
    html = index_path.read_text(encoding="utf-8")

    assert 'id="btn-open-telemetry"' in html
    assert 'id="sidebar-btn-open-telemetry"' in html
    assert 'id="aura-telemetry-modal"' in html
    assert 'id="telemetry-ttft-canvas"' in html
    assert 'id="header-telemetry-badge"' in html
    assert 'src="/static/js/aura-telemetry.js' in html


def test_aura_telemetry_js_file_integrity() -> None:
    """Valida integridade do script modular web/js/aura-telemetry.js."""
    js_path = BASE_DIR / "web" / "js" / "aura-telemetry.js"
    assert js_path.is_file(), "web/js/aura-telemetry.js nao encontrado"
    content = js_path.read_text(encoding="utf-8")

    assert "class AuraTelemetryCoordinator" in content
    assert "drawLatencyCanvas" in content
    assert "fetchCockpitData" in content
    assert "window.auraTelemetry" in content


def test_zero_em_dashes_in_telemetry_cockpit() -> None:
    """Garante ausencia absoluta de travessoes nos arquivos da Fase P3-1."""
    target_files = [
        BASE_DIR / "core" / "telemetry.py",
        BASE_DIR / "web" / "js" / "aura-telemetry.js",
        Path(__file__),
    ]
    for p in target_files:
        text = p.read_text(encoding="utf-8")
        assert "\u2014" not in text, f"Travessao longo detectado em {p.name}"
        assert "\u2013" not in text, f"Travessao medio detectado em {p.name}"
