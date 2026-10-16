"""
Modulo do Sentinela de Resiliencia e Auto-Healing Local no Windows (P3-5).
Monitora periodicamente a porta 8000 e a saude da AURA, eliminando processos
zumbis presos em STOP_PENDING e reciclando servicos locais em menos de 2 segundos.
Inclui protecao inteligente contra flapping (maximo 3 reinicios em 5 minutos).
Zero travessoes em todo o arquivo.
"""
# ruff: noqa: BLE001, S110

from __future__ import annotations

import json
import os
import re
import shlex
import signal
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from config.settings import BASE_DIR
from core.logger import logger

DEFAULT_EVENTS_FILE = BASE_DIR / "data" / "watchdog_events.json"


@dataclass
class WatchdogHealthResult:
    """Resultado estruturado de uma verificacao de saude executada pelo sentinela."""

    healthy: bool
    status_code: int | None = None
    response_time_ms: float = 0.0
    endpoint: str = "/api/v1/aura/telemetry/metrics"
    port: int = 8000
    pid: int | None = None
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Converte o resultado para dicionario serializavel."""
        return asdict(self)


@dataclass
class WatchdogIncidentEvent:
    """Evento ou incidente registrado pelo sentinela de auto-healing."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    event_type: str = "HEALTH_CHECK"
    port: int = 8000
    target_pid: int | None = None
    reason: str = ""
    action_taken: str = ""
    success: bool = True
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Converte o evento para dicionario serializavel."""
        return asdict(self)


class AuraWatchdogSentinel:
    """
    Sentinela de Resiliencia e Auto-Healing Local (P3-5).
    Monitora a saude da aplicacao e realiza recuperacao automatica caso o servidor
    fique preso, retenha a porta TCP sem responder ou sofra falha no servico Windows.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        health_endpoint: str = "/api/v1/aura/telemetry/metrics",
        fallback_endpoints: list[str] | None = None,
        http_timeout_seconds: float = 3.0,
        check_interval_seconds: float = 30.0,
        service_name: str = "AuraBackendService",
        restart_command: list[str] | str | None = None,
        restart_handler: Callable[[], bool] | None = None,
        max_restart_attempts: int = 3,
        cooldown_window_seconds: float = 300.0,
        log_file_path: Path | str | None = DEFAULT_EVENTS_FILE,
        enable_auto_healing: bool = True,
        graceful_termination_timeout_seconds: float = 1.5,
        recycle_timeout_seconds: float = 2.0,
    ) -> None:
        self.host = host
        self.port = port
        self.health_endpoint = health_endpoint
        self.fallback_endpoints = fallback_endpoints or ["/", "/favicon.ico"]
        self.http_timeout_seconds = http_timeout_seconds
        self.check_interval_seconds = check_interval_seconds
        self.service_name = service_name
        self.restart_command = restart_command
        self.restart_handler = restart_handler
        self.max_restart_attempts = max_restart_attempts
        self.cooldown_window_seconds = cooldown_window_seconds
        self.log_file_path = Path(log_file_path) if log_file_path else None
        self.enable_auto_healing = enable_auto_healing
        self.graceful_termination_timeout_seconds = graceful_termination_timeout_seconds
        self.recycle_timeout_seconds = recycle_timeout_seconds

        self._healing_history: list[float] = []
        self._lock = threading.Lock()
        self._file_lock = threading.Lock()
        self._is_running = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_health_result: WatchdogHealthResult | None = None
        self._contingency_active = False
        self._contingency_reason: str | None = None

    @staticmethod
    def parse_netstat_output(output: str, port: int) -> int | None:
        """
        Localiza o PID ouvindo na porta TCP especificada no output do netstat.
        Exemplo de linha: TCP 127.0.0.1:8000 0.0.0.0:0 LISTENING 1234
        """
        pattern_listening = re.compile(rf"^\s*TCP\s+\S*:{port}\s+\S+\s+LISTENING\s+(\d+)", re.IGNORECASE)
        pattern_any = re.compile(rf"^\s*TCP\s+\S*:{port}\s+\S+\s+(\S+)\s+(\d+)", re.IGNORECASE)

        fallback_pid: int | None = None
        for line in output.splitlines():
            match_listen = pattern_listening.search(line)
            if match_listen:
                try:
                    pid = int(match_listen.group(1))
                    if pid > 0:
                        return pid
                except (ValueError, IndexError):
                    pass

            if fallback_pid is None:
                match_any = pattern_any.search(line)
                if match_any:
                    try:
                        pid = int(match_any.group(2))
                        if pid > 0:
                            fallback_pid = pid
                    except (ValueError, IndexError):
                        pass

        return fallback_pid

    @staticmethod
    def parse_sc_queryex_output(output: str) -> int | None:
        """
        Localiza o PID retido no servico do Windows a partir da saida de sc queryex.
        Exemplo: PID : 3456
        """
        pattern = re.compile(r"PID\s*:\s*(\d+)", re.IGNORECASE)
        for line in output.splitlines():
            match = pattern.search(line)
            if match:
                try:
                    pid = int(match.group(1))
                    if pid > 0:
                        return pid
                except (ValueError, IndexError):
                    continue
        return None

    def find_pid_by_port(self, port: int | None = None) -> int | None:
        """Localiza o processo que esta escutando na porta TCP."""
        target_port = port or self.port
        # 1. Tenta via psutil (mais confiavel se disponivel)
        try:
            import psutil
            for conn in psutil.net_connections(kind="tcp"):
                if (
                    conn.laddr
                    and conn.laddr.port == target_port
                    and getattr(conn, "status", None) in ("LISTEN", getattr(psutil, "CONN_LISTEN", "LISTEN"))
                    and conn.pid
                    and conn.pid > 0
                ):
                    return conn.pid
        except Exception:
            pass

        # 2. Fallback via netstat no Windows
        if sys.platform == "win32":
            try:
                res = subprocess.run(
                    ["netstat", "-ano", "-p", "tcp"],
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=3.0,
                    check=False,
                )
                return self.parse_netstat_output(res.stdout, target_port)
            except Exception:
                pass
        else:
            try:
                res = subprocess.run(
                    ["lsof", "-i", f":{target_port}", "-t"],
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=2.0,
                    check=False,
                )
                if res.returncode == 0 and res.stdout.strip():
                    pids = res.stdout.strip().split()
                    if pids:
                        return int(pids[0])
            except Exception:
                pass

        return None

    def find_service_pid(self, service_name: str | None = None) -> int | None:
        """Identifica o PID associado ao servico Windows, mesmo em STOP_PENDING."""
        svc = service_name or self.service_name
        if sys.platform != "win32":
            return None
        try:
            res = subprocess.run(
                ["sc.exe", "queryex", svc],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=3.0,
                check=False,
            )
            return self.parse_sc_queryex_output(res.stdout)
        except Exception:
            pass
        return None

    def is_pid_alive(self, pid: int) -> bool:
        """Verifica se um determinado PID existe e esta ativo no sistema."""
        if pid <= 0:
            return False
        try:
            import psutil
            return bool(psutil.pid_exists(pid))
        except Exception:
            pass
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def terminate_pid(self, pid: int, timeout: float | None = None) -> bool:
        """
        Encerra defensivamente o processo:
        1. Tenta encerramento gracioso via SIGTERM (incluindo subprocessos filhos).
        2. Aguarda ate timeout segundos (padrao 1.5s).
        3. Se persistir, executa encerramento forcado da arvore (taskkill /F /T /PID ou SIGKILL).
        Retorna True se o processo nao estiver mais ativo.
        """
        if pid <= 0 or pid == os.getpid():
            logger.warning("PID %s invalido ou auto-preservativo ignorado para encerramento", pid)
            return False

        wait_timeout = timeout if timeout is not None else self.graceful_termination_timeout_seconds

        if not self.is_pid_alive(pid):
            return True

        # Etapa 1: Encerramento gracioso
        logger.info("Solicitando encerramento gracioso do PID %s (timeout: %.1fs)", pid, wait_timeout)
        terminated = False
        try:
            import psutil
            proc = psutil.Process(pid)
            try:
                children = proc.children(recursive=True)
            except Exception:
                children = []
            for child in children:
                try:
                    child.terminate()
                except Exception:
                    pass
            proc.terminate()
            try:
                proc.wait(timeout=wait_timeout)
                terminated = True
            except psutil.NoSuchProcess:
                terminated = True
            except psutil.TimeoutExpired:
                pass
        except Exception:
            try:
                os.kill(pid, signal.SIGTERM)
                deadline = time.time() + wait_timeout
                while time.time() < deadline:
                    if not self.is_pid_alive(pid):
                        terminated = True
                        break
                    time.sleep(0.05)
            except Exception:
                pass

        if terminated or not self.is_pid_alive(pid):
            logger.info("Processo PID %s finalizado com sucesso de forma limpa", pid)
            return True

        # Etapa 2: Encerramento forcado
        logger.warning("Processo PID %s retido apos %.1fs. Executando encerramento forcado...", pid, wait_timeout)
        if sys.platform == "win32":
            try:
                res = subprocess.run(
                    ["taskkill.exe", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=2.0,
                    check=False,
                )
                if res.returncode != 0:
                    logger.warning(
                        "taskkill no PID %s retornou codigo %s: %s",
                        pid,
                        res.returncode,
                        (res.stderr or res.stdout).strip(),
                    )
            except Exception as e:
                logger.error("Falha ao invocar taskkill no PID %s: %s", pid, e)
        else:
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception as e:
                logger.error("Falha ao invocar SIGKILL no PID %s: %s", pid, e)

        time.sleep(0.1)
        is_dead = not self.is_pid_alive(pid)
        if is_dead:
            logger.info("Processo PID %s eliminado via encerramento forcado", pid)
        else:
            logger.error("Falha ao eliminar processo PID %s; ainda consta como ativo", pid)
        return is_dead

    def recycle_server(self) -> bool:
        """
        Dispara a reciclagem do servidor local em menos de 2 segundos.
        Usa restart_handler injetado, restart_command ou comandos do servico Windows.
        """
        start_time = time.perf_counter()

        # 1. Handler customizado injetado
        if self.restart_handler is not None:
            try:
                res = bool(self.restart_handler())
                elapsed = time.perf_counter() - start_time
                logger.info("Restart handler customizado finalizado em %.3fs (resultado: %s)", elapsed, res)
                return res
            except Exception as e:
                logger.error("Falha no restart_handler customizado: %s", e)
                return False

        # 2. Comando customizado
        if self.restart_command:
            try:
                cmd = self.restart_command
                if isinstance(cmd, str):
                    cmd_list = shlex.split(cmd) if sys.platform != "win32" else cmd
                else:
                    cmd_list = cmd
                subprocess.Popen(
                    cmd_list,
                    cwd=str(BASE_DIR),
                    shell=isinstance(cmd_list, str),
                )
                elapsed = time.perf_counter() - start_time
                logger.info("Comando de reciclagem disparado em %.3fs", elapsed)
                return True
            except Exception as e:
                logger.error("Falha ao executar restart_command: %s", e)
                return False

        # 3. Servico Windows nativo via nssm ou net start
        if sys.platform == "win32":
            try:
                nssm_bin = BASE_DIR / "bin" / "nssm.exe"
                if nssm_bin.exists():
                    res = subprocess.run(
                        [str(nssm_bin), "start", self.service_name],
                        capture_output=True,
                        text=True,
                        errors="replace",
                        timeout=self.recycle_timeout_seconds,
                        check=False,
                    )
                    if res.returncode == 0:
                        elapsed = time.perf_counter() - start_time
                        logger.info("Servico Windows %s iniciado via nssm em %.3fs", self.service_name, elapsed)
                        return True
                    logger.warning(
                        "Falha ao iniciar via nssm (codigo %s): %s",
                        res.returncode,
                        (res.stderr or res.stdout).strip(),
                    )

                res = subprocess.run(
                    ["net", "start", self.service_name],
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=self.recycle_timeout_seconds,
                    check=False,
                )
                if res.returncode == 0:
                    elapsed = time.perf_counter() - start_time
                    logger.info("Servico Windows %s iniciado via net start em %.3fs", self.service_name, elapsed)
                    return True
                logger.warning(
                    "Falha ao iniciar via net start (codigo %s): %s",
                    res.returncode,
                    (res.stderr or res.stdout).strip(),
                )
            except Exception as e:
                logger.warning("Falha ao iniciar servico Windows %s: %s", self.service_name, e)
                return False

        return False

    def _perform_http_get(self, url: str, timeout: float) -> tuple[int | None, float, str | None]:
        """Executa chamada HTTP GET e calcula a latencia de resposta em milissegundos."""
        start = time.perf_counter()
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                resp = client.get(url)
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                return resp.status_code, elapsed_ms, None
        except httpx.TimeoutException:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return None, elapsed_ms, f"HTTP timeout excedido ({timeout}s)"
        except httpx.ConnectError as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return None, elapsed_ms, f"Conexao recusada na porta ({exc})"
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return None, elapsed_ms, f"Falha na requisicao HTTP: {exc}"

    def check_health(self, endpoint: str | None = None) -> WatchdogHealthResult:
        """
        Executa verificacao ativa de saude HTTP na porta 8000.
        Retorna WatchdogHealthResult detalhado com latencia, codigo HTTP e PID.
        """
        target_endpoint = endpoint or self.health_endpoint
        url = f"http://{self.host}:{self.port}{target_endpoint}"
        pid = self.find_pid_by_port(self.port)
        if pid is None:
            pid = self.find_service_pid(self.service_name)

        status_code, elapsed_ms, error = self._perform_http_get(url, timeout=self.http_timeout_seconds)

        if status_code is not None and 200 <= status_code < 300:
            result = WatchdogHealthResult(
                healthy=True,
                status_code=status_code,
                response_time_ms=round(elapsed_ms, 2),
                endpoint=target_endpoint,
                port=self.port,
                pid=pid,
                error=None,
            )
        else:
            # Tenta endpoints de contingencia/fallback caso a rota retorne 404
            if status_code == 404 and self.fallback_endpoints:
                for fallback in self.fallback_endpoints:
                    fb_url = f"http://{self.host}:{self.port}{fallback}"
                    fb_code, fb_elapsed, _fb_err = self._perform_http_get(fb_url, timeout=self.http_timeout_seconds)
                    if fb_code is not None and 200 <= fb_code < 300:
                        result = WatchdogHealthResult(
                            healthy=True,
                            status_code=fb_code,
                            response_time_ms=round(fb_elapsed, 2),
                            endpoint=fallback,
                            port=self.port,
                            pid=pid,
                            error=None,
                        )
                        with self._lock:
                            self._last_health_result = result
                        return result

            err_msg = error or f"HTTP status code {status_code}"
            if pid is not None and ("timeout" in err_msg.lower() or "recusada" in err_msg.lower()):
                err_msg = f"{err_msg} (PID {pid} retendo porta {self.port} sem responder)"

            result = WatchdogHealthResult(
                healthy=False,
                status_code=status_code,
                response_time_ms=round(elapsed_ms, 2),
                endpoint=target_endpoint,
                port=self.port,
                pid=pid,
                error=err_msg,
            )

        with self._lock:
            self._last_health_result = result

        return result

    def _prune_healing_history(self, current_time: float | None = None) -> None:
        """Remove reinicializacoes mais antigas que a janela de cooldown."""
        now = current_time if current_time is not None else time.time()
        cutoff = now - self.cooldown_window_seconds
        self._healing_history = [t for t in self._healing_history if t >= cutoff]
        if len(self._healing_history) < self.max_restart_attempts:
            self._contingency_active = False
            self._contingency_reason = None

    def is_flapping(self) -> bool:
        """Informa se a taxa de reinicializacoes excedeu o limite seguro anti-flapping."""
        with self._lock:
            self._prune_healing_history()
            return len(self._healing_history) >= self.max_restart_attempts

    def can_heal(self) -> bool:
        """Informa se o sentinela tem autorizacao operacional para auto-healing."""
        with self._lock:
            self._prune_healing_history()
            return self.enable_auto_healing and (len(self._healing_history) < self.max_restart_attempts)

    def reset_contingency(self) -> None:
        """Limpa historico de reinicios e desativa estado de contingencia."""
        with self._lock:
            self._healing_history.clear()
            self._contingency_active = False
            self._contingency_reason = None
            logger.info("Modo de contingencia do sentinela resetado com sucesso")

    def record_event(self, event: WatchdogIncidentEvent) -> None:
        """Registra o incidente no log estruturado e no arquivo JSON local."""
        log_data = event.to_dict()
        if event.event_type in ("FLAPPING_CONTINGENCY", "AUTO_HEAL_FAILED"):
            logger.error(
                "AuraWatchdogSentinel [%s]: %s (PID=%s, Port=%s)",
                event.event_type,
                event.reason,
                event.target_pid,
                event.port,
            )
        elif event.event_type == "AUTO_HEAL_SUCCESS":
            logger.warning(
                "AuraWatchdogSentinel [%s]: %s (PID=%s, Port=%s, Acao=%s)",
                event.event_type,
                event.reason,
                event.target_pid,
                event.port,
                event.action_taken,
            )
        else:
            logger.info("AuraWatchdogSentinel [%s]: %s", event.event_type, event.reason)

        if self.log_file_path:
            with self._file_lock:
                try:
                    p = self.log_file_path
                    p.parent.mkdir(parents=True, exist_ok=True)
                    events: list[dict[str, Any]] = []
                    if p.exists():
                        try:
                            content = p.read_text(encoding="utf-8")
                            if content.strip():
                                parsed = json.loads(content)
                                if isinstance(parsed, list):
                                    events = parsed
                        except Exception:
                            events = []
                    events.append(log_data)
                    if len(events) > 500:
                        events = events[-500:]
                    tmp_file = p.with_suffix(".tmp")
                    tmp_file.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
                    tmp_file.replace(p)
                except Exception as exc:
                    logger.warning("Nao foi possivel persistir incidente em %s: %s", self.log_file_path, exc)

    def get_recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retorna os eventos mais recentes persistidos no arquivo JSON."""
        if not self.log_file_path:
            return []
        p = self.log_file_path
        if not p.exists():
            return []
        with self._file_lock:
            try:
                content = p.read_text(encoding="utf-8")
                if not content.strip():
                    return []
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    return parsed[-limit:]
            except Exception as exc:
                logger.warning("Falha ao ler eventos do watchdog em %s: %s", self.log_file_path, exc)
                return []
        return []

    def heal_process(self, pid: int | None = None, reason: str = "Health check failed") -> bool:
        """
        Ciclo atomico de auto-healing:
        1. Valida politica anti-flapping (maximo 3 reinicios em 5 min).
        2. Localiza o PID retendo a porta ou travado.
        3. Encerra o processo zumbi (gracioso / forcado).
        4. Recicla o servidor local em menos de 2 segundos.
        5. Registra o incidente estruturado no logger e JSON.
        """
        if not self.enable_auto_healing:
            logger.warning("Auto-healing desativado nas configuracoes do sentinela")
            return False

        blocked_event: WatchdogIncidentEvent | None = None
        with self._lock:
            now = time.time()
            self._prune_healing_history(now)
            if len(self._healing_history) >= self.max_restart_attempts:
                self._contingency_active = True
                self._contingency_reason = (
                    f"Limite anti-flapping atingido: {len(self._healing_history)}/{self.max_restart_attempts} "
                    f"tentativas na janela de {int(self.cooldown_window_seconds)}s"
                )
                blocked_event = WatchdogIncidentEvent(
                    event_type="FLAPPING_CONTINGENCY",
                    port=self.port,
                    target_pid=pid,
                    reason=self._contingency_reason,
                    action_taken="AUTO_HEAL_BLOCKED",
                    success=False,
                    details={
                        "healing_history_count": len(self._healing_history),
                        "cooldown_window_seconds": self.cooldown_window_seconds,
                    },
                )
        if blocked_event:
            self.record_event(blocked_event)
            return False

        target_pid = pid
        if target_pid is None:
            target_pid = self.find_pid_by_port(self.port)
        if target_pid is None:
            target_pid = self.find_service_pid(self.service_name)

        logger.warning(
            "Auto-Healing acionado na porta %s (PID alvo: %s, motivo: %s)",
            self.port,
            target_pid,
            reason,
        )

        killed = True
        if target_pid is not None and target_pid > 0 and target_pid != os.getpid():
            killed = self.terminate_pid(target_pid, self.graceful_termination_timeout_seconds)

        recycled = self.recycle_server()

        with self._lock:
            self._healing_history.append(time.time())
            if len(self._healing_history) >= self.max_restart_attempts:
                self._contingency_active = True
                self._contingency_reason = (
                    f"Limite anti-flapping atingido: {len(self._healing_history)}/{self.max_restart_attempts} "
                    f"tentativas na janela de {int(self.cooldown_window_seconds)}s"
                )

        success = killed and recycled
        event_type = "AUTO_HEAL_SUCCESS" if success else "AUTO_HEAL_FAILED"
        action_taken = f"KILLED_PID_{target_pid}_AND_RECYCLED" if target_pid else "RECYCLED_WITHOUT_PID"

        event = WatchdogIncidentEvent(
            event_type=event_type,
            port=self.port,
            target_pid=target_pid,
            reason=reason,
            action_taken=action_taken,
            success=success,
            details={
                "killed_process": killed,
                "recycled_server": recycled,
                "target_pid": target_pid,
            },
        )
        self.record_event(event)
        return success

    def start(self) -> None:
        """Inicia o sentinela em segundo plano de forma thread-safe."""
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                name="AuraWatchdogSentinelThread",
                daemon=True,
            )
            self._thread.start()
            logger.info("Sentinela AuraWatchdogSentinel iniciado (intervalo: %.1fs)", self.check_interval_seconds)

    def stop(self, timeout: float = 5.0) -> None:
        """Interrompe o sentinela e aguarda finalizacao da thread."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        with self._lock:
            self._is_running = False
            self._thread = None
            logger.info("Sentinela AuraWatchdogSentinel encerrado com sucesso")

    def _run_loop(self) -> None:
        """Loop continuo de monitoramento e cura."""
        try:
            while not self._stop_event.is_set():
                try:
                    health = self.check_health()
                    if not health.healthy and self.enable_auto_healing:
                        self.heal_process(pid=health.pid, reason=health.error or "Health check falhou")
                except Exception as exc:
                    logger.error("Erro inesperado no ciclo do sentinela: %s", exc)

                self._stop_event.wait(timeout=self.check_interval_seconds)
        finally:
            with self._lock:
                self._is_running = False
                self._thread = None

    def get_status(self) -> dict[str, Any]:
        """Retorna o diagnostico consolidado de status do sentinela."""
        with self._lock:
            self._prune_healing_history()
            is_active = self._is_running and (self._thread is not None and self._thread.is_alive())
            flapping = len(self._healing_history) >= self.max_restart_attempts
            status_label = "contingency" if flapping else ("running" if is_active else "idle")
            return {
                "status": status_label,
                "is_running": is_active,
                "host": self.host,
                "port": self.port,
                "health_endpoint": self.health_endpoint,
                "service_name": self.service_name,
                "auto_healing_enabled": self.enable_auto_healing,
                "is_flapping": flapping,
                "contingency_active": self._contingency_active,
                "contingency_reason": self._contingency_reason,
                "recent_healing_attempts": len(self._healing_history),
                "max_restart_attempts": self.max_restart_attempts,
                "cooldown_window_seconds": self.cooldown_window_seconds,
                "last_health_result": self._last_health_result.to_dict() if self._last_health_result else None,
                "timestamp": datetime.now(UTC).isoformat(),
            }
