"""
Testes Unitarios: Gerenciador de Configuracoes de Automacao da AURA.
Valida o comportamento do modelo Pydantic, mesclagem parcial,
persistencia atomica em JSON e estado padrao sob demanda.
Zero travessoes em todo o arquivo.
"""

import json
from pathlib import Path

import pytest

from core.automation_config import (
    AutomationSettingsManager,
)


@pytest.fixture
def temp_config_file(tmp_path: Path):
    """Cria um caminho temporario para os testes sem afetar o arquivo real."""
    return tmp_path / "test_automation_settings.json"


@pytest.mark.unit
def test_automation_settings_default_is_disabled(temp_config_file):
    """Garante que a configuracao padrao inicia 100% desativada (sob demanda)."""
    manager = AutomationSettingsManager(file_path=temp_config_file)
    settings = manager.get_settings()

    assert settings.master_enabled is False
    assert settings.shift_audit.enabled is False
    assert settings.tank_alerts.enabled is False
    assert settings.pumps_audit.enabled is False
    assert "06:05" in settings.shift_audit.schedules
    assert settings.tank_alerts.min_autonomy_hours == 12


@pytest.mark.unit
def test_automation_settings_update_partial(temp_config_file):
    """Valida a atualizacao parcial via deep merge e persistencia em disco."""
    manager = AutomationSettingsManager(file_path=temp_config_file)

    # Ativa apenas o master e a auditoria de turnos
    updates = {
        "master_enabled": True,
        "shift_audit": {
            "enabled": True,
            "cash_tolerance_reais": 80.0,
        },
    }
    updated = manager.update_settings(updates, updated_by="gerente_teste")

    assert updated.master_enabled is True
    assert updated.shift_audit.enabled is True
    assert updated.shift_audit.cash_tolerance_reais == 80.0
    # Campos nao mencionados devem manter os valores padrao
    assert updated.tank_alerts.enabled is False
    assert updated.shift_audit.schedules == ["06:05", "14:05", "22:05"]
    assert updated.updated_by == "gerente_teste"

    # Confirma que foi salvo no disco
    assert temp_config_file.exists()
    disk_data = json.loads(temp_config_file.read_text(encoding="utf-8"))
    assert disk_data["master_enabled"] is True
    assert disk_data["shift_audit"]["cash_tolerance_reais"] == 80.0


@pytest.mark.unit
def test_automation_settings_reload_from_disk(temp_config_file):
    """Verifica se uma nova instancia carrega corretamente o que foi salvo no arquivo."""
    manager1 = AutomationSettingsManager(file_path=temp_config_file)
    manager1.update_settings({
        "master_enabled": True,
        "tank_alerts": {
            "enabled": True,
            "min_autonomy_hours": 8,
        },
    })

    # Nova instancia apontando para o mesmo arquivo
    manager2 = AutomationSettingsManager(file_path=temp_config_file)
    loaded = manager2.get_settings()

    assert loaded.master_enabled is True
    assert loaded.tank_alerts.enabled is True
    assert loaded.tank_alerts.min_autonomy_hours == 8
