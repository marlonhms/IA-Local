"""
Testes unitarios do motor de Self-Healing Local AURA (Fase 1A).
Valida diagnostico, SQLite WAL, cooldown, circuit breaker, mocks de subprocess/httpx
e endpoint HTTP /api/v1/aura/self-healing/status.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.self_healing import (
    AuraSelfHealer,
    IncidentType,
    reset_self_healer,
    set_self_healer,
)


def test_diagnose_erp_error_patterns() -> None:
    """Identifica corretamente erro de role bloqueada e servico PostgreSQL parado."""
    assert (
        AuraSelfHealer.diagnose_erp_error(
            'FATAL: a função de banco de dados (role) "aura_service_ro" não tem permissão para conectar'
        )
        == IncidentType.ERP_ROLE_LOCKED
    )
    assert (
        AuraSelfHealer.diagnose_erp_error('FATAL: role "aura_service_ro" is not permitted to log in')
        == IncidentType.ERP_ROLE_LOCKED
    )
    assert (
        AuraSelfHealer.diagnose_erp_error("connection to server at 127.0.0.1, port 5433 failed: Connection refused")
        == IncidentType.PG_SERVICE_DOWN
    )
    assert AuraSelfHealer.diagnose_erp_error("timeout de leitura qualquer") is None


def test_heal_erp_role_cooldown_and_circuit_breaker(tmp_path: Path) -> None:
    """Valida bloqueio por cooldown e abertura do circuit breaker apos atingir limite."""
    db_file = tmp_path / "healing.db"
    dummy_script = tmp_path / "reparar_banco.ps1"
    dummy_script.write_text("Write-Host 'AURA_OK'\n", encoding="utf-8")

    # Cooldown ativo bloqueia segunda chamada imediata
    healer_cd = AuraSelfHealer(
        db_path=db_file,
        cooldown_seconds=900,
        max_attempts_in_window=2,
        repair_script_path=dummy_script,
    )
    first = healer_cd.heal_erp_role_locked(dry_run=True)
    assert first.resolved is True
    assert first.skipped_by_cooldown is False

    second = healer_cd.heal_erp_role_locked(dry_run=True)
    assert second.skipped_by_cooldown is True
    assert second.action_taken == "SKIPPED_BY_COOLDOWN"

    # Sem cooldown entre tentativas, apos 2 tentativas na janela abre circuit breaker
    healer_cb = AuraSelfHealer(
        db_path=tmp_path / "healing_cb.db",
        cooldown_seconds=0,
        max_attempts_in_window=2,
        repair_script_path=dummy_script,
    )
    assert healer_cb.heal_erp_role_locked(dry_run=True).circuit_open is False
    assert healer_cb.heal_erp_role_locked(dry_run=True).circuit_open is False

    third = healer_cb.heal_erp_role_locked(dry_run=True)
    assert third.circuit_open is True
    assert third.skipped_by_cooldown is True
    assert third.action_taken == "CIRCUIT_OPEN_MANUAL_INTERVENTION_REQUIRED"

    status = healer_cb.get_status()
    assert status["status"] == "degraded"
    assert status["guardrails"]["ERP_ROLE_LOCKED"]["circuit_open"] is True


def test_heal_erp_role_privileged_and_unprivileged(tmp_path: Path) -> None:
    """Executa script quando admin e registra alerta seguro quando sem privilegio."""
    dummy_script = tmp_path / "reparar_banco.ps1"
    dummy_script.write_text("# ok\n", encoding="utf-8")

    healer_non_admin = AuraSelfHealer(
        db_path=":memory:",
        cooldown_seconds=0,
        repair_script_path=dummy_script,
    )
    with patch("core.self_healing._is_windows_admin", return_value=False):
        res_na = healer_non_admin.heal_erp_role_locked(dry_run=False)
    assert res_na.resolved is False
    assert res_na.action_taken == "ADMIN_PRIVILEGE_REQUIRED_MANUAL_REPAIR"

    healer_admin = AuraSelfHealer(
        db_path=":memory:",
        cooldown_seconds=0,
        repair_script_path=dummy_script,
    )
    mock_proc = SimpleNamespace(returncode=0, stdout="[SUCESSO] AURA_OK", stderr="")
    with (
        patch("core.self_healing._is_windows_admin", return_value=True),
        patch("core.self_healing.subprocess.run", return_value=mock_proc) as run_mock,
        patch("core.db_pool.close_all_pools") as close_pools_mock,
    ):
        res_ok = healer_admin.heal_erp_role_locked(dry_run=False)

    assert res_ok.resolved is True
    assert res_ok.action_taken == "EXECUTED_REPAIR_SCRIPT_AND_RESET_POOLS"
    assert run_mock.call_count == 1
    assert close_pools_mock.call_count == 1


def test_evolution_health_and_resource_pressure() -> None:
    """Valida verificacao da Evolution API e mitigacao de pressao de RAM/disco."""
    healer = AuraSelfHealer(db_path=":memory:", cooldown_seconds=0)

    healthy_resp = SimpleNamespace(status_code=200, json=lambda: {"instance": {"state": "open"}})
    with patch("core.self_healing.httpx.get", return_value=healthy_resp):
        evo_ok = healer.check_evolution_health("http://127.0.0.1:8080", "k", "webposto-n3")
    assert evo_ok.resolved is True
    assert evo_ok.action_taken == "NO_ACTION_HEALTHY"

    closed_resp = SimpleNamespace(status_code=200, json=lambda: {"instance": {"state": "close"}})
    with patch("core.self_healing.httpx.get", return_value=closed_resp):
        evo_down = healer.check_evolution_health("http://127.0.0.1:8080", "k", "webposto-n3")
    assert evo_down.resolved is False
    assert evo_down.action_taken == "EVOLUTION_RECONNECT_ALERT_LOGGED"

    with (
        patch("core.self_healing.psutil.disk_usage", return_value=SimpleNamespace(percent=95.0)),
        patch("core.self_healing.psutil.virtual_memory", return_value=SimpleNamespace(percent=96.0)),
        patch("core.resource_watchdog.trim_process_working_set", return_value=True),
    ):
        res_list = healer.heal_resource_pressure(disk_threshold_pct=90.0, ram_threshold_pct=92.0)

    types = {r.incident_type for r in res_list}
    assert types == {IncidentType.RAM_PRESSURE, IncidentType.DISK_PRESSURE}


def test_self_healing_fastapi_endpoint(client, tmp_path: Path) -> None:
    """Valida rota GET /api/v1/aura/self-healing/status com TestClient."""
    healer = AuraSelfHealer(db_path=tmp_path / "api_heal.db", cooldown_seconds=60)
    healer.heal_erp_role_locked(dry_run=True)
    set_self_healer(healer)
    try:
        resp = client.get("/api/v1/aura/self-healing/status?limit=5")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["recent_events_count"] == 1
        assert body["recent_events"][0]["incident_type"] == "ERP_ROLE_LOCKED"
    finally:
        reset_self_healer()


def test_db_pool_triggers_role_self_healing_only_for_role_locked(tmp_path: Path) -> None:
    """Valida que db_pool aciona auto-cura apenas para erro de role bloqueada e sem deadlock."""
    from core import db_pool

    dummy_script = tmp_path / "reparar_banco.ps1"
    dummy_script.write_text("# ok\n", encoding="utf-8")
    healer = AuraSelfHealer(
        db_path=tmp_path / "pool_heal.db",
        cooldown_seconds=60,
        repair_script_path=dummy_script,
    )
    set_self_healer(healer)
    mock_proc = SimpleNamespace(returncode=0, stdout="AURA_OK", stderr="")
    try:
        # Erro generico nao deve acionar auto-cura
        assert db_pool._trigger_role_self_healing_if_needed("timeout qualquer", background=False) is False

        # Erro de role bloqueada deve acionar heal_erp_role_locked e resetar pools sem deadlock
        with (
            patch("core.self_healing._is_windows_admin", return_value=True),
            patch("core.self_healing.subprocess.run", return_value=mock_proc) as run_mock,
        ):
            triggered = db_pool._trigger_role_self_healing_if_needed(
                'FATAL: a função de banco de dados (role) "aura_service_ro" não tem permissão para conectar',
                background=False,
            )

        assert triggered is True
        assert run_mock.call_count == 1
        assert healer.get_status()["recent_events_count"] == 1
        assert healer.get_status()["recent_events"][0]["resolved"] is True
    finally:
        reset_self_healer()
