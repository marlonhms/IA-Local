"""
Testes Unitarios do Sentinela de Resiliencia e Auto-Healing AURA (Fase P3-5).
Valida:
1. Verificacao de servidor saudavel (HTTP 200).
2. Deteccao de anomalias (timeout, conexao recusada, erro 500).
3. Fallback defensivo para rotas alternativas.
4. Parsing de PIDs via netstat e sc queryex do Windows.
5. Encerramento gracioso (SIGTERM) e forcado (taskkill/SIGKILL).
6. Auto-healing atomico com reciclagem do servidor em menos de 2 segundos.
7. Blindagem anti-flapping (maximo 3 tentativas em 5 minutos).
8. Ciclo de vida start() e stop() em background thread-safe.
9. Persistencia de incidentes em JSON e diagnostico de status.
10. CLI scripts/watchdog_sentinel.py (--once, --status, --no-heal).
11. Regra inegociavel de ZERO travessoes.
"""

from __future__ import annotations

import os
import signal
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from config.settings import BASE_DIR
from core.watchdog import (
    AuraWatchdogSentinel,
    WatchdogHealthResult,
)
from scripts.watchdog_sentinel import format_health_line
from scripts.watchdog_sentinel import main as cli_main


@pytest.fixture
def temp_events_file(tmp_path: Path) -> Path:
    """Retorna caminho temporario para persistencia de eventos do watchdog."""
    return tmp_path / "watchdog_test_events.json"


@pytest.fixture
def sentinel(temp_events_file: Path) -> AuraWatchdogSentinel:
    """Instancia padrao do sentinela isolada para testes."""
    return AuraWatchdogSentinel(
        host="127.0.0.1",
        port=8000,
        health_endpoint="/api/v1/aura/telemetry/metrics",
        fallback_endpoints=["/", "/favicon.ico"],
        http_timeout_seconds=3.0,
        check_interval_seconds=30.0,
        service_name="AuraBackendService",
        log_file_path=temp_events_file,
        enable_auto_healing=True,
        max_restart_attempts=3,
        cooldown_window_seconds=300.0,
        graceful_termination_timeout_seconds=1.5,
        recycle_timeout_seconds=2.0,
    )


# =============================================================================
# 1. VERIFICACAO DE SAUDE HTTP E DETECCAO DE ANOMALIAS
# =============================================================================

@pytest.mark.unit
def test_check_health_server_healthy(sentinel: AuraWatchdogSentinel) -> None:
    """Verifica que resposta HTTP 200 e classificada como saudavel."""
    with patch.object(sentinel, "_perform_http_get", return_value=(200, 15.4, None)), \
         patch.object(sentinel, "find_pid_by_port", return_value=5432):
        result = sentinel.check_health()

        assert result.healthy is True
        assert result.status_code == 200
        assert result.response_time_ms == 15.4
        assert result.pid == 5432
        assert result.port == 8000
        assert result.error is None


@pytest.mark.unit
def test_check_health_timeout_anomaly(sentinel: AuraWatchdogSentinel) -> None:
    """Verifica deteccao de timeout HTTP (> 3s) e associacao de PID retido."""
    with patch.object(sentinel, "_perform_http_get", return_value=(None, 3005.0, "HTTP timeout excedido (3.0s)")), \
         patch.object(sentinel, "find_pid_by_port", return_value=8888):
        result = sentinel.check_health()

        assert result.healthy is False
        assert result.status_code is None
        assert result.response_time_ms == 3005.0
        assert result.pid == 8888
        assert "timeout" in result.error.lower()
        assert "PID 8888" in result.error


@pytest.mark.unit
def test_check_health_connection_refused(sentinel: AuraWatchdogSentinel) -> None:
    """Verifica deteccao de conexao recusada quando a porta esta fechada."""
    with patch.object(sentinel, "_perform_http_get", return_value=(None, 2.0, "Conexao recusada na porta")), \
         patch.object(sentinel, "find_pid_by_port", return_value=None), \
         patch.object(sentinel, "find_service_pid", return_value=None):
        result = sentinel.check_health()

        assert result.healthy is False
        assert result.status_code is None
        assert result.pid is None
        assert "recusada" in result.error.lower()


@pytest.mark.unit
def test_check_health_internal_server_error_500(sentinel: AuraWatchdogSentinel) -> None:
    """Verifica deteccao de status HTTP 500 como anomalia."""
    with patch.object(sentinel, "_perform_http_get", return_value=(500, 45.0, None)), \
         patch.object(sentinel, "find_pid_by_port", return_value=1234):
        result = sentinel.check_health()

        assert result.healthy is False
        assert result.status_code == 500
        assert result.pid == 1234
        assert "500" in result.error


@pytest.mark.unit
def test_check_health_fallback_success_when_metrics_404(sentinel: AuraWatchdogSentinel) -> None:
    """Verifica que fallback para '/' tem sucesso se endpoint de metricas retornar 404."""
    def fake_get(url: str, timeout: float):
        if "metrics" in url:
            return 404, 10.0, None
        return 200, 8.0, None

    with patch.object(sentinel, "_perform_http_get", side_effect=fake_get), \
         patch.object(sentinel, "find_pid_by_port", return_value=9999):
        result = sentinel.check_health()

        assert result.healthy is True
        assert result.status_code == 200
        assert result.endpoint == "/"
        assert result.pid == 9999


# =============================================================================
# 2. PARSING DE PIDS VIA NETSTAT E SC QUERYEX (WINDOWS)
# =============================================================================

@pytest.mark.unit
def test_parse_netstat_output_ipv4_and_ipv6() -> None:
    """Valida extracao correta do PID escutando na porta 8000 via saida de netstat."""
    sample_output = """
Active Connections

  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING       1124
  TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING       4568
  TCP    0.0.0.0:18000          0.0.0.0:0              LISTENING       9999
  TCP    127.0.0.1:5432         0.0.0.0:0              LISTENING       2400
  TCP    [::]:8000              [::]:0                 LISTENING       4568
"""
    pid_8000 = AuraWatchdogSentinel.parse_netstat_output(sample_output, 8000)
    assert pid_8000 == 4568

    pid_5432 = AuraWatchdogSentinel.parse_netstat_output(sample_output, 5432)
    assert pid_5432 == 2400

    pid_not_found = AuraWatchdogSentinel.parse_netstat_output(sample_output, 9090)
    assert pid_not_found is None


@pytest.mark.unit
def test_parse_sc_queryex_output_stop_pending() -> None:
    """Valida identificacao do PID retido em servico preso em STOP_PENDING."""
    sample_sc = """
SERVICE_NAME: AuraBackendService
        TYPE               : 10  WIN32_OWN_PROCESS
        STATE              : 3  STOP_PENDING
                                (STOPPABLE, NOT_PAUSABLE, ACCEPTS_SHUTDOWN)
        WIN32_EXIT_CODE    : 0  (0x0)
        SERVICE_EXIT_CODE  : 0  (0x0)
        CHECKPOINT         : 0x0
        WAIT_HINT          : 0x0
        PID                : 7120
        FLAGS              :
"""
    pid = AuraWatchdogSentinel.parse_sc_queryex_output(sample_sc)
    assert pid == 7120

    sample_no_pid = "SERVICE_NAME: AuraBackendService\n        STATE: 1 STOPPED\n        PID : 0"
    assert AuraWatchdogSentinel.parse_sc_queryex_output(sample_no_pid) is None


# =============================================================================
# 3. ENCERRAMENTO DEFENSIVO DE PIDS (GRACIOSO E FORCADO)
# =============================================================================

@pytest.mark.unit
def test_terminate_pid_self_preservation_guard(sentinel: AuraWatchdogSentinel) -> None:
    """Garante que o sentinela nunca tenta encerrar o proprio PID ou PIDs invalidos."""
    assert sentinel.terminate_pid(os.getpid()) is False
    assert sentinel.terminate_pid(0) is False
    assert sentinel.terminate_pid(-1) is False


@pytest.mark.unit
def test_terminate_pid_graceful_success(sentinel: AuraWatchdogSentinel) -> None:
    """Valida encerramento gracioso via SIGTERM / terminate()."""
    pytest.importorskip("psutil")
    mock_proc = MagicMock()
    mock_proc.wait.return_value = None

    with patch("psutil.pid_exists", side_effect=[True, False]), \
         patch("psutil.Process", return_value=mock_proc):
        success = sentinel.terminate_pid(12345, timeout=1.5)

        assert success is True
        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once_with(timeout=1.5)


@pytest.mark.unit
def test_terminate_pid_forced_on_timeout(sentinel: AuraWatchdogSentinel) -> None:
    """Valida que processo persistente sofre taskkill / SIGKILL forcado apos timeout."""
    psutil = pytest.importorskip("psutil")

    mock_proc = MagicMock()
    mock_proc.wait.side_effect = psutil.TimeoutExpired(1.5)

    # pid_exists: inicialmente vivo, depois do taskkill/kill, morto
    with patch("psutil.pid_exists", side_effect=[True, True, False]), \
         patch("psutil.Process", return_value=mock_proc), \
         patch("subprocess.run") as mock_subproc, \
         patch("os.kill") as mock_os_kill:
        success = sentinel.terminate_pid(23456, timeout=1.5)

        assert success is True
        mock_proc.terminate.assert_called_once()
        if sys.platform == "win32":
            mock_subproc.assert_called_once()
            args = mock_subproc.call_args[0][0]
            assert "taskkill.exe" in args[0]
            assert "23456" in args
        else:
            mock_os_kill.assert_called_with(23456, signal.SIGKILL)


# =============================================================================
# 4. RECICLAGEM E AUTO-HEALING ATOMICO
# =============================================================================

@pytest.mark.unit
def test_recycle_server_with_custom_handler(sentinel: AuraWatchdogSentinel) -> None:
    """Verifica reciclagem disparada por restart_handler customizado."""
    handler_called = False

    def my_handler() -> bool:
        nonlocal handler_called
        handler_called = True
        return True

    sentinel.restart_handler = my_handler
    assert sentinel.recycle_server() is True
    assert handler_called is True


@pytest.mark.unit
def test_heal_process_success_cycle(sentinel: AuraWatchdogSentinel) -> None:
    """Valida ciclo completo de auto-healing com encerramento de PID e reciclagem."""
    sentinel.restart_handler = lambda: True

    with patch.object(sentinel, "find_pid_by_port", return_value=6677), \
         patch.object(sentinel, "terminate_pid", return_value=True) as mock_term:
        success = sentinel.heal_process(reason="Teste unitario de auto-healing")

        assert success is True
        mock_term.assert_called_once_with(6677, 1.5)
        assert len(sentinel._healing_history) == 1

        # Verifica persistencia do evento
        events = sentinel.get_recent_events(limit=5)
        assert len(events) >= 1
        last_event = events[-1]
        assert last_event["event_type"] == "AUTO_HEAL_SUCCESS"
        assert last_event["target_pid"] == 6677
        assert last_event["success"] is True


@pytest.mark.unit
def test_heal_process_disabled(sentinel: AuraWatchdogSentinel) -> None:
    """Valida que auto-healing nao executa quando enable_auto_healing=False."""
    sentinel.enable_auto_healing = False
    assert sentinel.heal_process() is False
    assert len(sentinel._healing_history) == 0


# =============================================================================
# 5. BLINDAGEM ANTI-FLAPPING & COOLDOWN
# =============================================================================

@pytest.mark.unit
def test_flapping_protection_blocks_after_max_attempts(sentinel: AuraWatchdogSentinel) -> None:
    """Valida bloqueio de reinicios e ativacao de contingencia ao atingir 3 tentativas."""
    sentinel.restart_handler = lambda: True
    sentinel.max_restart_attempts = 3
    sentinel.cooldown_window_seconds = 300.0

    with patch.object(sentinel, "terminate_pid", return_value=True):
        # 3 tentativas autorizadas
        assert sentinel.heal_process(pid=1001) is True
        assert sentinel.heal_process(pid=1002) is True
        assert sentinel.heal_process(pid=1003) is True
        assert sentinel.is_flapping() is True

        # 4a tentativa deve ser sumariamente bloqueada
        assert sentinel.heal_process(pid=1004) is False
        assert sentinel.get_status()["status"] == "contingency"
        assert sentinel._contingency_active is True
        assert "Limite anti-flapping" in sentinel._contingency_reason

        # Evento de contingencia registrado
        events = sentinel.get_recent_events(limit=10)
        flapping_events = [e for e in events if e["event_type"] == "FLAPPING_CONTINGENCY"]
        assert len(flapping_events) >= 1


@pytest.mark.unit
def test_cooldown_window_expiry_allows_healing_again(sentinel: AuraWatchdogSentinel) -> None:
    """Valida que apos o decurso da janela de cooldown, o sentinela autoriza nova cura."""
    sentinel.restart_handler = lambda: True
    sentinel.max_restart_attempts = 2
    sentinel.cooldown_window_seconds = 60.0

    # Adiciona duas tentativas no passado (ha 70 segundos atras)
    old_time = 1000.0
    sentinel._healing_history = [old_time, old_time + 1.0]

    # Agora sao 1075.0 (passaram-se 75s, janela de 60s expirou)
    with patch("time.time", return_value=1075.0), \
         patch.object(sentinel, "terminate_pid", return_value=True):
        assert sentinel.is_flapping() is False
        assert sentinel.can_heal() is True
        assert sentinel.heal_process(pid=5001) is True


@pytest.mark.unit
def test_reset_contingency_manually(sentinel: AuraWatchdogSentinel) -> None:
    """Valida limpeza manual do estado de contingencia."""
    sentinel._healing_history = [1.0, 2.0, 3.0]
    sentinel._contingency_active = True
    sentinel._contingency_reason = "Bloqueio de teste"

    sentinel.reset_contingency()
    assert sentinel.is_flapping() is False
    assert sentinel._contingency_active is False
    assert sentinel._contingency_reason is None
    assert len(sentinel._healing_history) == 0


# =============================================================================
# 6. CICLO DE VIDA THREAD-SAFE (START / STOP / LOOP)
# =============================================================================

@pytest.mark.unit
def test_sentinel_background_thread_start_and_stop(sentinel: AuraWatchdogSentinel) -> None:
    """Valida inicializacao e parada graciosa da thread de monitoramento."""
    sentinel.check_interval_seconds = 0.05
    with patch.object(sentinel, "check_health", return_value=WatchdogHealthResult(healthy=True)):
        sentinel.start()
        assert sentinel._is_running is True
        assert sentinel._thread is not None
        assert sentinel._thread.is_alive()

        sentinel.stop(timeout=1.0)
        assert sentinel._is_running is False
        assert sentinel._thread is None


@pytest.mark.unit
def test_get_status_payload_structure(sentinel: AuraWatchdogSentinel) -> None:
    """Valida contrato do dicionario de status emitido por get_status()."""
    status = sentinel.get_status()
    assert "status" in status
    assert "is_running" in status
    assert "port" in status
    assert status["port"] == 8000
    assert "auto_healing_enabled" in status
    assert "is_flapping" in status
    assert "recent_healing_attempts" in status
    assert "timestamp" in status


# =============================================================================
# 7. CLI UTILITARIO SCRIPTS/WATCHDOG_SENTINEL.PY
# =============================================================================

@pytest.mark.unit
def test_cli_format_health_line() -> None:
    """Valida formatacao de linha de status da CLI."""
    res_ok = WatchdogHealthResult(
        healthy=True,
        status_code=200,
        response_time_ms=12.5,
        port=8000,
        pid=1234,
        error=None,
    )
    line_ok = format_health_line(res_ok)
    assert "[OK]" in line_ok
    assert "Porta: 8000" in line_ok
    assert "PID: 1234" in line_ok
    assert "12.5ms" in line_ok

    res_fail = WatchdogHealthResult(
        healthy=False,
        status_code=None,
        response_time_ms=3000.0,
        port=8000,
        pid=None,
        error="Timeout HTTP excedido",
    )
    line_fail = format_health_line(res_fail)
    assert "[FALHA]" in line_fail
    assert "Timeout HTTP excedido" in line_fail


@pytest.mark.unit
def test_cli_main_status_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """Valida execucao da CLI com flag --status."""
    test_args = ["watchdog_sentinel.py", "--status", "--port", "8000"]
    with patch.object(sys, "argv", test_args):
        ret = cli_main()
        assert ret == 0
        captured = capsys.readouterr()
        assert "AURA: SENTINELA DE RESILIENCIA" in captured.out
        assert "Porta Monitorada      : 8000" in captured.out


@pytest.mark.unit
def test_cli_main_once_healthy(capsys: pytest.CaptureFixture[str]) -> None:
    """Valida execucao da CLI com flag --once quando o servidor esta saudavel."""
    test_args = ["watchdog_sentinel.py", "--once", "--port", "8000"]
    fake_res = WatchdogHealthResult(
        healthy=True,
        status_code=200,
        response_time_ms=10.0,
        port=8000,
        pid=9999,
    )
    with patch.object(sys, "argv", test_args), \
         patch.object(AuraWatchdogSentinel, "check_health", return_value=fake_res):
        ret = cli_main()
        assert ret == 0
        captured = capsys.readouterr()
        assert "[OK]" in captured.out
        assert "PID: 9999" in captured.out


@pytest.mark.unit
def test_cli_main_once_unhealthy_with_healing(capsys: pytest.CaptureFixture[str]) -> None:
    """Valida execucao da CLI com flag --once disparando auto-healing em falha."""
    test_args = ["watchdog_sentinel.py", "--once", "--port", "8000"]
    fake_res = WatchdogHealthResult(
        healthy=False,
        status_code=None,
        response_time_ms=3000.0,
        port=8000,
        pid=8888,
        error="Timeout",
    )
    with patch.object(sys, "argv", test_args), \
         patch.object(AuraWatchdogSentinel, "check_health", return_value=fake_res), \
         patch.object(AuraWatchdogSentinel, "heal_process", return_value=True) as mock_heal:
        ret = cli_main()
        assert ret == 0
        mock_heal.assert_called_once_with(pid=8888, reason="Timeout")
        captured = capsys.readouterr()
        assert "[FALHA]" in captured.out
        assert "Disparando rotina de Auto-Healing" in captured.out
        assert "SUCESSO" in captured.out


# =============================================================================
# 8. CASOS CRITICOS DE RECICLAGEM, TREE-KILL E CONSISTENCIA OPERACIONAL
# =============================================================================

@pytest.mark.unit
def test_recycle_server_nssm_failure_falls_back_to_net_start(sentinel: AuraWatchdogSentinel) -> None:
    """Verifica que se o nssm start falhar, ha fallback para net start com sucesso."""
    mock_nssm_fail = MagicMock(returncode=1, stderr="Acesso negado", stdout="")
    mock_net_ok = MagicMock(returncode=0, stderr="", stdout="")

    with patch("sys.platform", "win32"), \
         patch.object(Path, "exists", return_value=True), \
         patch("subprocess.run", side_effect=[mock_nssm_fail, mock_net_ok]) as mock_subproc:
        res = sentinel.recycle_server()

        assert res is True
        assert mock_subproc.call_count == 2
        # Primeira tentativa via nssm
        first_call = mock_subproc.call_args_list[0][0][0]
        assert "nssm.exe" in first_call[0]
        assert "start" in first_call
        # Segunda tentativa via net start
        second_call = mock_subproc.call_args_list[1][0][0]
        assert second_call == ["net", "start", sentinel.service_name]


@pytest.mark.unit
def test_recycle_server_both_nssm_and_net_start_fail_returns_false(sentinel: AuraWatchdogSentinel) -> None:
    """Verifica que se nssm e net start falharem, recycle_server retorna False sem falso positivo."""
    mock_nssm_fail = MagicMock(returncode=1, stderr="Can't open service", stdout="")
    mock_net_fail = MagicMock(returncode=2, stderr="Servico nao pode ser iniciado", stdout="")

    with patch("sys.platform", "win32"), \
         patch.object(Path, "exists", return_value=True), \
         patch("subprocess.run", side_effect=[mock_nssm_fail, mock_net_fail]):
        res = sentinel.recycle_server()
        assert res is False


@pytest.mark.unit
def test_terminate_pid_tree_kill_includes_children_and_taskkill_flags(sentinel: AuraWatchdogSentinel) -> None:
    """Verifica encerramento recursivo de filhos no psutil e taskkill com flag /T."""
    psutil = pytest.importorskip("psutil")

    mock_child = MagicMock()
    mock_proc = MagicMock()
    mock_proc.children.return_value = [mock_child]
    mock_proc.wait.side_effect = psutil.TimeoutExpired(1.5)

    with patch("psutil.pid_exists", side_effect=[True, True, False]), \
         patch("psutil.Process", return_value=mock_proc), \
         patch("subprocess.run") as mock_subproc:
        success = sentinel.terminate_pid(34567, timeout=1.5)

        assert success is True
        # Verifica encerramento gracioso do filho
        mock_child.terminate.assert_called_once()
        mock_proc.terminate.assert_called_once()

        # Verifica taskkill com flag /T de arvore de processos no Windows
        if sys.platform == "win32":
            args = mock_subproc.call_args[0][0]
            assert "taskkill.exe" in args[0]
            assert "/T" in args
            assert "/F" in args
            assert "34567" in args


@pytest.mark.unit
def test_parse_netstat_output_ignores_outgoing_connection() -> None:
    """Verifica que o parser ignora conexoes de saida e detecta porta retida em CLOSE_WAIT."""
    output_with_outbound = """
Active Connections

  Proto  Local Address          Foreign Address        State           PID
  TCP    192.168.1.5:49152      192.168.1.1:8000       ESTABLISHED     9999
  TCP    127.0.0.1:8000         127.0.0.1:51234        CLOSE_WAIT      7777
"""
    # Nao deve associar PID 9999 (porta 8000 no Foreign Address)
    pid_retido = AuraWatchdogSentinel.parse_netstat_output(output_with_outbound, 8000)
    assert pid_retido == 7777


@pytest.mark.unit
def test_perform_http_get_follow_redirects(sentinel: AuraWatchdogSentinel) -> None:
    """Verifica que client httpx e configurado para seguir redirecionamentos."""
    with patch("httpx.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_instance
        mock_resp = MagicMock(status_code=200)
        mock_instance.get.return_value = mock_resp

        code, _elapsed, err = sentinel._perform_http_get("http://127.0.0.1:8000/", timeout=2.0)
        assert code == 200
        assert err is None
        # Confirma que follow_redirects=True foi repassado ao httpx.Client
        mock_client_cls.assert_called_once_with(timeout=2.0, follow_redirects=True)


@pytest.mark.unit
def test_run_loop_cleans_up_is_running_on_exit(sentinel: AuraWatchdogSentinel) -> None:
    """Verifica garantia do bloco finally em _run_loop desativando _is_running."""
    sentinel._is_running = True
    sentinel._stop_event.set()  # Forca saida imediata do loop
    sentinel._run_loop()

    assert sentinel._is_running is False
    assert sentinel._thread is None


@pytest.mark.unit
def test_check_health_fallback_to_aura_health(sentinel: AuraWatchdogSentinel) -> None:
    """Verifica fallback customizado para /api/v1/aura/health caso metricas retorne 404."""
    sentinel.fallback_endpoints = ["/api/v1/aura/health", "/", "/favicon.ico"]

    def fake_get(url: str, timeout: float):
        if "metrics" in url:
            return 404, 5.0, None
        if "/api/v1/aura/health" in url:
            return 200, 7.0, None
        return 404, 5.0, None

    with patch.object(sentinel, "_perform_http_get", side_effect=fake_get), \
         patch.object(sentinel, "find_pid_by_port", return_value=3333):
        res = sentinel.check_health()
        assert res.healthy is True
        assert res.status_code == 200
        assert res.endpoint == "/api/v1/aura/health"


@pytest.mark.unit
def test_contingency_consistency_at_max_attempts(sentinel: AuraWatchdogSentinel) -> None:
    """Verifica consistencia imediata de status de contingencia ao esgotar o teto de reinicios."""
    sentinel.restart_handler = lambda: True
    sentinel.max_restart_attempts = 2
    sentinel.cooldown_window_seconds = 60.0

    with patch.object(sentinel, "terminate_pid", return_value=True):
        assert sentinel.heal_process(pid=2001) is True
        assert sentinel.heal_process(pid=2002) is True

        st = sentinel.get_status()
        assert st["status"] == "contingency"
        assert st["contingency_active"] is True
        assert "Limite anti-flapping" in str(st["contingency_reason"])


# =============================================================================
# 9. REGRA INEGCIAVEL: ZERO TRAVESSOES
# =============================================================================

@pytest.mark.unit
def test_zero_travessoes_in_watchdog_files() -> None:
    """
    Garante ausencia total de travessoes (\\u2014, \\u2013) em:
    - core/watchdog.py
    - scripts/watchdog_sentinel.py
    - tests/unit/test_watchdog_sentinel.py
    """
    arquivos = [
        BASE_DIR / "core" / "watchdog.py",
        BASE_DIR / "scripts" / "watchdog_sentinel.py",
        BASE_DIR / "tests" / "unit" / "test_watchdog_sentinel.py",
    ]

    for arq in arquivos:
        assert arq.exists(), f"Arquivo nao encontrado: {arq}"
        conteudo = arq.read_text(encoding="utf-8")
        assert "\u2014" not in conteudo, f"Travessao em-dash (\\u2014) detectado em {arq.name}"
        assert "\u2013" not in conteudo, f"Travessao en-dash (\\u2013) detectado em {arq.name}"
