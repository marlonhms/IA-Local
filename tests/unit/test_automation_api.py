"""
Testes Unitarios: Endpoints FastAPI da Central de Automacoes da AURA.
Valida o retorno das configuracoes ativas, atualizacao a quente e autenticacao.
Zero travessoes em todo o arquivo.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.aura_api import create_aura_app
from core.aura_engine import AuraEngine, AuraSessionMemory
from core.automation_config import AutomationSettingsManager


@pytest.fixture
def test_client(tmp_path: Path, monkeypatch):
    """Cria um TestClient isolado apontando para arquivo temporario."""
    test_file = tmp_path / "api_test_automations.json"
    test_manager = AutomationSettingsManager(file_path=test_file)
    monkeypatch.setattr("core.aura_api.get_automation_settings", test_manager.get_settings)
    monkeypatch.setattr("core.aura_api.update_automation_settings", test_manager.update_settings)

    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(session_memory=mem)
    app = create_aura_app(engine=engine)
    return TestClient(app)


@pytest.mark.unit
def test_get_automation_settings_endpoint(test_client):
    """Valida a consulta das configuracoes de automacao via HTTP GET."""
    res = test_client.get("/api/v1/aura/admin/automation-settings")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "settings" in data
    assert data["settings"]["master_enabled"] is False
    assert data["settings"]["shift_audit"]["enabled"] is False


@pytest.mark.unit
def test_update_automation_settings_endpoint(test_client):
    """Valida a atualizacao a quente via HTTP POST."""
    payload = {
        "master_enabled": True,
        "shift_audit": {
            "enabled": True,
            "schedules": ["06:00", "14:00", "22:00"],
            "cash_tolerance_reais": 100.0,
        },
        "tank_alerts": {
            "enabled": True,
            "min_autonomy_hours": 10,
        },
    }

    res = test_client.post(
        "/api/v1/aura/admin/automation-settings",
        json=payload,
        headers={"X-Operator-Role": "administrador"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "updated"
    assert data["settings"]["master_enabled"] is True
    assert data["settings"]["shift_audit"]["enabled"] is True
    assert data["settings"]["shift_audit"]["schedules"] == ["06:00", "14:00", "22:00"]
    assert data["settings"]["shift_audit"]["cash_tolerance_reais"] == 100.0
    assert data["settings"]["tank_alerts"]["min_autonomy_hours"] == 10
    assert data["settings"]["updated_by"] == "administrador"

    # Confirma que o GET subsequente reflete as mudancas
    get_res = test_client.get("/api/v1/aura/admin/automation-settings")
    assert get_res.status_code == 200
    assert get_res.json()["settings"]["master_enabled"] is True
