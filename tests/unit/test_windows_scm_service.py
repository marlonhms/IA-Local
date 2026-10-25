"""
Testes Unitarios da Fase 1 (Roadmap Sentinel-AURA):
Fundacao do Servico Windows SCM Nativo (Fim do NSSM) & Supervisor-Worker.

Valida:
1. Gravacao e leitura atomica de `service_health.json` (`write_health_state`, `read_health_state`).
2. Loop Supervisor-Worker (`run_service_supervisor_loop`):
   - Reciclagem in-process em menos de 1 segundo quando o worker cai inesperadamente.
   - Respeito ao teto `max_restarts` (3 tentativas) antes de delegar ao SCM.
   - Encerramento limpo imediato quando o `stop_event` e sinalizado.
3. Comandos administrativos via `sc.exe` (`install_windows_service`, `uninstall_windows_service`,
   `start_windows_service`, `stop_windows_service`, `get_windows_service_status`, `get_installed_service_info`).
4. Processamento de argumentos CLI no `server.py` (`--service`, `--service-worker`, `--install-service`, etc.).
5. Existencia, estrutura e conformidade ASCII puro de `scripts/gerenciar_servico_aura.bat`.
6. Ausencia total de travessoes (`\\u2014`, `\\u2013`) em todos os artefatos da Fase 1.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, List

import pytest

import core.service as aura_service
import server as aura_server
from core.service import (
    PROJECT_ROOT,
    SERVICE_DISPLAY_NAME,
    SERVICE_NAME,
    SERVICE_VERSION,
    build_service_binpath,
    build_worker_command,
    configure_service_logging,
    get_installed_service_info,
    get_windows_service_status,
    install_windows_service,
    read_health_state,
    run_service_supervisor_loop,
    start_windows_service,
    stop_windows_service,
    uninstall_windows_service,
    write_health_state,
)


class DummyWorkerProcess:
    """Processo worker simulado para testar o loop Supervisor-Worker em sub-segundo."""

    def __init__(self, pid: int, exit_after_polls: int = 1, exit_code: int = 1) -> None:
        self.pid = pid
        self.exit_after_polls = exit_after_polls
        self.exit_code = exit_code
        self.polls = 0
        self.terminated = False
        self.killed = False
        self.returncode: int | None = None

    def poll(self) -> int | None:
        self.polls += 1
        if self.terminated or self.killed:
            self.returncode = 0
            return 0
        if self.exit_after_polls >= 0 and self.polls >= self.exit_after_polls:
            self.returncode = self.exit_code
            return self.exit_code
        return None

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = 0

    def wait(self, timeout: float | None = None) -> int:
        self.returncode = 0
        return 0

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9


def test_health_state_atomic_write_and_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Garante escrita atomica e leitura confiavel de service_health.json."""
    monkeypatch.setenv("AURA_DATA_DIR", str(tmp_path / "data"))

    health_path = write_health_state(
        "RUNNING", {"service_host": True, "worker_pid": 4321}
    )
    assert health_path.is_file()

    state = read_health_state()
    assert state is not None
    assert state["service_name"] == SERVICE_NAME
    assert state["display_name"] == SERVICE_DISPLAY_NAME
    assert state["version"] == SERVICE_VERSION
    assert state["status"] == "RUNNING"
    assert state["details"]["worker_pid"] == 4321


def test_configure_service_logging_creates_log_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Valida criacao do arquivo de log rotativo aura_service.log."""
    logs_dir = tmp_path / "logs"
    monkeypatch.setenv("AURA_LOGS_DIR", str(logs_dir))

    logger = configure_service_logging()
    logger.info("Mensagem de teste do servico SCM nativo.")

    for h in list(logger.handlers):
        h.flush()
        h.close()
        logger.removeHandler(h)

    log_file = logs_dir / "aura_service.log"
    assert log_file.is_file()
    content = log_file.read_text(encoding="utf-8")
    assert "Mensagem de teste do servico SCM nativo." in content


def test_build_worker_command_and_binpath() -> None:
    """Valida a geracao dos comandos --service e --service-worker."""
    worker_cmd = build_worker_command("C:/Python312/python.exe")
    assert worker_cmd[-1] == "--service-worker"
    assert "server.py" in worker_cmd[1]

    bin_path = build_service_binpath("C:/Python312/python.exe")
    assert "--service" in bin_path
    assert "server.py" in bin_path


def test_supervisor_recycles_crashed_worker_under_one_second(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Criterio de Aceite da Fase 1:
    Quando o processo worker e finalizado inesperadamente, o supervisor pai recicla
    o processo em menos de 1 segundo sem derrubar o servico no SCM.
    """
    monkeypatch.setenv("AURA_DATA_DIR", str(tmp_path / "data"))

    spawned_workers: List[DummyWorkerProcess] = []
    stop_flag = {"stop": False}

    def _spawn() -> DummyWorkerProcess:
        idx = len(spawned_workers) + 1
        # Os dois primeiros workers caem imediatamente (exit_code=1); o 3o fica vivo e recebe stop
        if idx < 3:
            w = DummyWorkerProcess(pid=1000 + idx, exit_after_polls=1, exit_code=1)
        else:
            w = DummyWorkerProcess(pid=1000 + idx, exit_after_polls=-1, exit_code=0)
        spawned_workers.append(w)
        return w

    def _stop_requested() -> bool:
        # Quando o 3o worker ja tiver sido iniciado e sondado ao menos 1 vez, solicita parada
        if len(spawned_workers) == 3 and spawned_workers[2].polls >= 1:
            stop_flag["stop"] = True
        return stop_flag["stop"]

    start_ts = time.perf_counter()
    summary = run_service_supervisor_loop(
        stop_requested_fn=_stop_requested,
        spawn_worker_fn=_spawn,
        max_restarts=3,
        restart_delay_sec=0.02,
        poll_interval_sec=0.01,
    )
    elapsed = time.perf_counter() - start_ts

    # Reciclagem de 2 quedas + parada limpa em menos de 1 segundo
    assert elapsed < 1.0, f"Reciclagem demorou {elapsed:.2f}s (limite < 1.0s)"
    assert summary["total_spawns"] == 3
    assert summary["restart_count"] == 2
    assert spawned_workers[2].terminated is True

    final_state = read_health_state()
    assert final_state is not None
    assert final_state["status"] == "STOPPED"


def test_supervisor_stops_after_max_restarts_exceeded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Valida que apos 3 reciclagens consecutivas sem sucesso o supervisor delega ao SCM."""
    monkeypatch.setenv("AURA_DATA_DIR", str(tmp_path / "data"))

    spawns = 0

    def _spawn_failing() -> DummyWorkerProcess:
        nonlocal spawns
        spawns += 1
        return DummyWorkerProcess(pid=2000 + spawns, exit_after_polls=1, exit_code=137)

    summary = run_service_supervisor_loop(
        stop_requested_fn=lambda: False,
        spawn_worker_fn=_spawn_failing,
        max_restarts=3,
        restart_delay_sec=0.01,
        poll_interval_sec=0.01,
    )

    # 1 inicial + 3 reciclagens = 4 spawns; na 4a queda (restart_count=4 > 3), encerra
    assert summary["total_spawns"] == 4
    assert summary["restart_count"] == 4
    assert summary["last_exit_code"] == 137


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="Requer sistema operacional Windows nativo para operacoes com sc.exe e caminhos de servico",
)
def test_windows_service_lifecycle_commands_via_sc_exe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Testa install, start, stop, status, info e uninstall via sc.exe mockado."""
    monkeypatch.setenv("AURA_DATA_DIR", str(tmp_path / "data"))

    executed_cmds: List[List[str]] = []
    service_installed = {"state": "NOT_INSTALLED"}

    def _mock_subprocess_run(cmd: List[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        executed_cmds.append(cmd)
        verb = cmd[1] if len(cmd) > 1 else ""
        target = cmd[2] if len(cmd) > 2 else ""

        if verb == "query":
            if target == "postgresql-x64-16":
                return subprocess.CompletedProcess(cmd, 0, stdout="STATE : 4  RUNNING\n", stderr="")
            if target == SERVICE_NAME:
                if service_installed["state"] == "NOT_INSTALLED":
                    return subprocess.CompletedProcess(cmd, 1060, stdout="", stderr="Does not exist")
                return subprocess.CompletedProcess(
                    cmd, 0, stdout=f"SERVICE_NAME: {SERVICE_NAME}\n        STATE : {service_installed['state']}\n", stderr=""
                )
            return subprocess.CompletedProcess(cmd, 1060, stdout="", stderr="")

        if verb == "create":
            service_installed["state"] = "1  STOPPED"
            return subprocess.CompletedProcess(cmd, 0, stdout="[SC] CreateService SUCCESS", stderr="")

        if verb in ("config", "description", "failure"):
            return subprocess.CompletedProcess(cmd, 0, stdout="[SC] SUCCESS", stderr="")

        if verb == "start":
            service_installed["state"] = "4  RUNNING"
            return subprocess.CompletedProcess(cmd, 0, stdout="STATE : 4  RUNNING", stderr="")

        if verb == "stop":
            service_installed["state"] = "1  STOPPED"
            return subprocess.CompletedProcess(cmd, 0, stdout="STATE : 1  STOPPED", stderr="")

        if verb == "delete":
            service_installed["state"] = "NOT_INSTALLED"
            return subprocess.CompletedProcess(cmd, 0, stdout="[SC] DeleteService SUCCESS", stderr="")

        if verb == "qc":
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout='        BINARY_PATH_NAME   : "C:\\Python312\\python.exe" "C:\\Aura\\server.py" --service\n',
                stderr="",
            )

        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(aura_service.subprocess, "run", _mock_subprocess_run)

    # 1. Antes de instalar
    assert get_windows_service_status() == "NOT_INSTALLED"

    # 2. Instalacao com dependencia postgresql-x64-16 e politica de auto-recuperacao
    assert install_windows_service() is True
    assert get_windows_service_status() == "STOPPED"

    # Verifica se sc.exe failure foi configurado com restart/5000/restart/10000/restart/30000
    failure_cmds = [c for c in executed_cmds if len(c) > 1 and c[1] == "failure"]
    assert len(failure_cmds) == 1
    assert "restart/5000/restart/10000/restart/30000" in failure_cmds[0]

    # 3. Partida do servico
    assert start_windows_service() is True
    assert get_windows_service_status() == "RUNNING"

    # 4. Consulta de informacoes detalhadas (sc.exe qc)
    info = get_installed_service_info()
    assert info["installed"] is True
    assert info["status"] == "RUNNING"
    assert "--service" in (info["bin_path"] or "")

    # 5. Parada e desinstalacao
    assert stop_windows_service() is True
    assert get_windows_service_status() == "STOPPED"
    assert uninstall_windows_service() is True
    assert get_windows_service_status() == "NOT_INSTALLED"


def test_server_handle_service_cli_args(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Valida todos os switches administrativos em server.handle_service_cli_args."""
    monkeypatch.setattr(aura_server, "get_windows_service_status", lambda: "RUNNING")
    monkeypatch.setattr(
        aura_server,
        "get_installed_service_info",
        lambda: {"service_name": SERVICE_NAME, "status": "RUNNING", "installed": True},
    )
    monkeypatch.setattr(aura_server, "install_windows_service", lambda: True)
    monkeypatch.setattr(aura_server, "uninstall_windows_service", lambda: True)
    monkeypatch.setattr(aura_server, "start_windows_service", lambda: True)
    monkeypatch.setattr(aura_server, "stop_windows_service", lambda: True)
    monkeypatch.setattr(aura_server, "run_windows_service_dispatcher", lambda: True)

    assert aura_server.handle_service_cli_args([]) is None
    assert aura_server.handle_service_cli_args(["--version"]) == 0
    assert aura_server.handle_service_cli_args(["--service-status"]) == 0
    out_status = capsys.readouterr().out
    assert "RUNNING" in out_status

    assert aura_server.handle_service_cli_args(["--service-info"]) == 0
    out_info = json.loads(capsys.readouterr().out)
    assert out_info["service_name"] == SERVICE_NAME

    assert aura_server.handle_service_cli_args(["--install-service"]) == 0
    assert aura_server.handle_service_cli_args(["--start-service"]) == 0
    assert aura_server.handle_service_cli_args(["--stop-service"]) == 0
    assert aura_server.handle_service_cli_args(["--uninstall-service"]) == 0
    assert aura_server.handle_service_cli_args(["--service"]) == 0

    # --service-worker configura variaveis de contexto e retorna None para prosseguir ao Uvicorn
    assert aura_server.handle_service_cli_args(["--service-worker"]) is None


def test_gerenciar_servico_aura_bat_and_ps1_compliance() -> None:
    """Valida scripts/gerenciar_servico_aura.bat e scripts/instalar_posto.ps1 (ASCII puro e sem NSSM)."""
    bat_path = PROJECT_ROOT / "scripts" / "gerenciar_servico_aura.bat"
    assert bat_path.is_file(), "Script scripts/gerenciar_servico_aura.bat nao encontrado"

    bat_content = bat_path.read_text(encoding="utf-8")
    assert all(ord(c) < 128 for c in bat_content), "gerenciar_servico_aura.bat deve ser 100% ASCII puro"
    for flag in (
        "--install-service",
        "--start-service",
        "--stop-service",
        "--service-status",
        "--service-info",
        "--uninstall-service",
    ):
        assert flag in bat_content, f"Flag {flag} ausente em gerenciar_servico_aura.bat"

    ps1_path = PROJECT_ROOT / "scripts" / "instalar_posto.ps1"
    ps1_content = ps1_path.read_text(encoding="utf-8")
    assert "--install-service" in ps1_content
    assert "restart/5000/restart/10000/restart/30000" in ps1_content


def test_zero_em_dashes_in_phase1_files() -> None:
    """Garante ausencia absoluta de travessoes em todos os arquivos da Fase 1."""
    files = [
        PROJECT_ROOT / "core" / "service.py",
        PROJECT_ROOT / "server.py",
        PROJECT_ROOT / "scripts" / "gerenciar_servico_aura.bat",
        PROJECT_ROOT / "scripts" / "instalar_posto.ps1",
        Path(__file__),
    ]
    for path in files:
        content = path.read_text(encoding="utf-8")
        assert "\u2014" not in content, f"Travessao longo encontrado em {path.name}"
        assert "\u2013" not in content, f"Travessao medio encontrado em {path.name}"
