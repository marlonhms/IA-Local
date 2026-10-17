"""
Modulo de Integracao Nativa com o Service Control Manager (SCM) do Windows.
Implementa a Fase 1 do Roadmap Sentinel-AURA:
- Arquitetura Supervisor-Worker nativa (fim da dependencia de nssm.exe)
- Loop de reciclagem in-process ultrarrapido (< 1s) em caso de queda do worker
- Registro, partida, parada e politicas de auto-recuperacao via sc.exe
- Gravacao atomica de estado de saude (service_health.json) e logs rotativos
Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SERVICE_NAME = "AuraBackendService"
LEGACY_SERVICE_NAMES = ["AURA_Core_Engine", "AuraService"]
SERVICE_DISPLAY_NAME = "Aura Cognitive Service"
SERVICE_DESCRIPTION = (
    "Servico Cognitivo e Assistente Operacional de Pista e Retaguarda AURA."
)
SERVICE_VERSION = "2.1.0-PRO"
DEFAULT_POSTGRES_DEPENDENCY = "postgresql-x64-16"

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000 if os.name == "nt" else 0)

try:
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil
except ImportError:
    win32event = None
    win32service = None
    win32serviceutil = None
    servicemanager = None


def get_aura_data_dir() -> Path:
    """Retorna o diretorio de dados persistentes da AURA."""
    env_dir = os.getenv("AURA_DATA_DIR")
    if env_dir:
        path = Path(env_dir)
    else:
        path = PROJECT_ROOT / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logs_dir() -> Path:
    """Retorna o diretorio de logs rotativos do servico AURA."""
    env_logs = os.getenv("AURA_LOGS_DIR")
    if env_logs:
        path = Path(env_logs)
    else:
        path = PROJECT_ROOT / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_state_dir() -> Path:
    """Retorna o diretorio de estado operacional (service_health.json)."""
    state_dir = get_aura_data_dir() / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def is_running_as_service() -> bool:
    """Detecta se o processo atual foi iniciado em contexto de servico Windows (Sessao 0)."""
    if os.getenv("AURA_SERVICE_CONTEXT") == "1":
        return True
    if any(arg in sys.argv for arg in ("--service", "--service-worker")):
        return True
    return False


def configure_service_logging(log_level: int = logging.INFO) -> logging.Logger:
    """Configura logs rotacionados em logs/aura_service.log (5 MB x 5 backups) e console."""
    logs_dir = get_logs_dir()
    log_file = logs_dir / "aura_service.log"

    logger = logging.getLogger("aura.service")
    logger.setLevel(log_level)

    # Evita duplicar handlers se chamado multiplas vezes
    for h in list(logger.handlers):
        logger.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)

    logger.info("Logging de servico inicializado em: %s", log_file)
    return logger


def write_health_state(status: str, details: Optional[Dict[str, Any]] = None) -> Path:
    """Registra atomicamente o estado de saude do servico em data/state/service_health.json."""
    state_dir = get_state_dir()
    health_file = state_dir / "service_health.json"

    payload: Dict[str, Any] = {
        "service_name": SERVICE_NAME,
        "display_name": SERVICE_DISPLAY_NAME,
        "version": SERVICE_VERSION,
        "status": status,
        "is_service": is_running_as_service(),
        "pid": os.getpid(),
        "updated_at": time.time(),
        "details": details or {},
    }

    temp_file = health_file.with_suffix(f".{os.getpid()}.tmp")
    try:
        temp_file.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        temp_file.replace(health_file)
    except Exception as exc:
        logging.getLogger("aura.service").warning(
            "Falha ao gravar service_health.json: %s", exc
        )
        try:
            temp_file.unlink(missing_ok=True)
        except Exception:
            pass

    return health_file


def read_health_state() -> Optional[Dict[str, Any]]:
    """Le o arquivo service_health.json se existir e for valido."""
    health_file = get_state_dir() / "service_health.json"
    if not health_file.is_file():
        return None
    try:
        return json.loads(health_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def build_worker_command(exe_path: Optional[str] = None) -> List[str]:
    """Constroi a linha de comando para iniciar o processo filho (--service-worker)."""
    target_exe = exe_path or sys.executable
    if getattr(sys, "frozen", False):
        return [ os.path.abspath(target_exe), "--service-worker" ]
    server_script = str(PROJECT_ROOT / "server.py")
    return [ os.path.abspath(target_exe), server_script, "--service-worker" ]


def build_service_binpath(exe_path: Optional[str] = None) -> str:
    """Constroi a string binPath formatada com aspas para o registro no sc.exe."""
    target_exe = exe_path or sys.executable
    if getattr(sys, "frozen", False):
        return f'"{os.path.abspath(target_exe)}" --service'
    server_script = str(PROJECT_ROOT / "server.py")
    return f'"{os.path.abspath(target_exe)}" "{server_script}" --service'


def run_service_supervisor_loop(
    stop_requested_fn: Callable[[], bool],
    spawn_worker_fn: Optional[Callable[[], Any]] = None,
    max_restarts: int = 3,
    restart_delay_sec: float = 0.2,
    poll_interval_sec: float = 0.2,
    stable_uptime_reset_sec: float = 300.0,
) -> Dict[str, Any]:
    """
    Executa o loop Supervisor-Worker com reciclagem in-process (< 1s).
    Se o worker cair inesperadamente, o supervisor o reinicia imediatamente ate `max_restarts`.
    Se o worker permanecer estavel por `stable_uptime_reset_sec`, o contador de falhas e zerado.
    """
    logger = logging.getLogger("aura.service")

    if spawn_worker_fn is None:
        cmd = build_worker_command()
        work_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else str(PROJECT_ROOT)
        env = os.environ.copy()
        env["AURA_SERVICE_CONTEXT"] = "1"
        env["AURA_AUTO_OPEN"] = "0"

        def _default_spawn():
            return subprocess.Popen(
                cmd,
                cwd=work_dir,
                env=env,
                creationflags=CREATE_NO_WINDOW,
            )

        spawn_worker_fn = _default_spawn

    restart_count = 0
    total_spawns = 0
    worker = None
    last_exit_code: Optional[int] = None

    try:
        while not stop_requested_fn():
            worker_start_ts = time.monotonic()
            worker = spawn_worker_fn()
            total_spawns += 1
            worker_pid = getattr(worker, "pid", None)

            write_health_state(
                "RUNNING",
                {
                    "service_host": True,
                    "worker_pid": worker_pid,
                    "restart_count": restart_count,
                    "total_spawns": total_spawns,
                },
            )
            logger.info(
                "Worker da AURA iniciado (PID=%s, ciclo=%d, reinicios=%d).",
                worker_pid,
                total_spawns,
                restart_count,
            )

            # Monitora o processo filho enquanto aguarda evento de parada
            while not stop_requested_fn():
                exit_code = worker.poll()
                if exit_code is not None:
                    last_exit_code = exit_code
                    break
                time.sleep(poll_interval_sec)

            if stop_requested_fn():
                break

            # Se chegou aqui, o worker finalizou sem que o servico tenha pedido parada
            uptime = time.monotonic() - worker_start_ts
            if uptime >= stable_uptime_reset_sec:
                restart_count = 0

            restart_count += 1
            logger.warning(
                "Worker finalizou inesperadamente com codigo %s apos %.2fs. Tentativa de reciclagem %d/%d.",
                last_exit_code,
                uptime,
                restart_count,
                max_restarts,
            )

            if restart_count > max_restarts:
                logger.error(
                    "Limite de %d reciclagens in-process atingido. Encerrando supervisor para acionar auto-restart do SCM.",
                    max_restarts,
                )
                write_health_state(
                    "FAILED",
                    {
                        "service_host": True,
                        "last_exit_code": last_exit_code,
                        "restart_count": restart_count,
                    },
                )
                break

            write_health_state(
                "RECYCLING",
                {
                    "service_host": True,
                    "last_exit_code": last_exit_code,
                    "restart_count": restart_count,
                },
            )
            if restart_delay_sec > 0:
                time.sleep(restart_delay_sec)

    finally:
        if worker is not None and worker.poll() is None:
            try:
                worker.terminate()
                worker.wait(timeout=10)
            except Exception:
                try:
                    worker.kill()
                except Exception:
                    pass
        write_health_state(
            "STOPPED",
            {
                "service_host": True,
                "last_exit_code": last_exit_code,
                "restart_count": restart_count,
                "total_spawns": total_spawns,
            },
        )

    return {
        "total_spawns": total_spawns,
        "restart_count": restart_count,
        "last_exit_code": last_exit_code,
    }


if win32serviceutil is not None:

    class AuraWindowsService(win32serviceutil.ServiceFramework):
        """Host nativo do Windows SCM que supervisiona o processo worker da AURA."""

        _svc_name_ = SERVICE_NAME
        _svc_display_name_ = SERVICE_DISPLAY_NAME
        _svc_description_ = SERVICE_DESCRIPTION

        def __init__(self, args: Any) -> None:
            super().__init__(args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)

        def SvcStop(self) -> None:
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)

        def SvcDoRun(self) -> None:
            configure_service_logging()
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)

            def _is_stop_signaled() -> bool:
                return (
                    win32event.WaitForSingleObject(self.stop_event, 0)
                    == win32event.WAIT_OBJECT_0
                )

            run_service_supervisor_loop(stop_requested_fn=_is_stop_signaled)


def run_windows_service_dispatcher() -> bool:
    """Registra e inicia o dispatcher oficial do Windows SCM."""
    if os.name != "nt" or win32serviceutil is None or servicemanager is None:
        print(
            "[!] Host de servico Windows indisponivel neste ambiente (requer Windows + pywin32)."
        )
        return False

    servicemanager.Initialize()
    try:
        servicemanager.PrepareToHostSingle(AuraWindowsService)
    except Exception as exc:
        logging.getLogger("aura.service").error(
            "Falha em PrepareToHostSingle: %s", exc
        )
        return False
    servicemanager.StartServiceCtrlDispatcher()
    return True


def _parse_sc_query_state(output: str) -> str:
    """Extrai o estado padronizado da saida do comando sc.exe query."""
    out = output.upper()
    if "RUNNING" in out:
        return "RUNNING"
    if "STOPPED" in out:
        return "STOPPED"
    if "START_PENDING" in out:
        return "STARTING"
    if "STOP_PENDING" in out:
        return "STOPPING"
    return "UNKNOWN"


def get_windows_service_status(service_name: str = SERVICE_NAME) -> str:
    """Consulta o status atual do servico no Windows SCM via sc.exe query."""
    if os.name != "nt":
        return "NON_WINDOWS"

    res = subprocess.run(
        ["sc.exe", "query", service_name],
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    if res.returncode != 0 and service_name == SERVICE_NAME:
        for leg in LEGACY_SERVICE_NAMES:
            res_leg = subprocess.run(
                ["sc.exe", "query", leg],
                capture_output=True,
                text=True,
                errors="replace",
                check=False,
            )
            if res_leg.returncode == 0:
                res = res_leg
                break

    if res.returncode != 0:
        return "NOT_INSTALLED"
    return _parse_sc_query_state(res.stdout)


def get_installed_service_info() -> Dict[str, Any]:
    """Retorna informacoes detalhadas do servico instalado e estado de saude."""
    status = get_windows_service_status()
    health = read_health_state()
    info: Dict[str, Any] = {
        "service_name": SERVICE_NAME,
        "display_name": SERVICE_DISPLAY_NAME,
        "status": status,
        "installed": status not in ("NOT_INSTALLED", "NON_WINDOWS"),
        "version": (health or {}).get("version") or SERVICE_VERSION,
        "bin_path": None,
        "data_dir": str(get_aura_data_dir()),
        "logs_dir": str(get_logs_dir()),
        "health": health,
    }

    if os.name == "nt" and info["installed"]:
        try:
            res = subprocess.run(
                ["sc.exe", "qc", SERVICE_NAME],
                capture_output=True,
                text=True,
                errors="replace",
                check=False,
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    line_up = line.upper()
                    if "BINARY_PATH_NAME" in line_up or "CAMINHO_BIN" in line_up:
                        parts = line.split(":", 1)
                        if len(parts) > 1:
                            info["bin_path"] = parts[1].strip()
        except Exception:
            pass

    return info


def is_postgres_service_present(pg_service: str = DEFAULT_POSTGRES_DEPENDENCY) -> bool:
    """Verifica se o servico do PostgreSQL nativo existe no SCM do Windows."""
    if os.name != "nt" or not pg_service:
        return False
    res = subprocess.run(
        ["sc.exe", "query", pg_service],
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    return res.returncode == 0


def install_windows_service(
    exe_path: Optional[str] = None,
    depend_service: Optional[str] = DEFAULT_POSTGRES_DEPENDENCY,
) -> bool:
    """
    Registra ou atualiza o servico nativo AuraBackendService no Windows SCM via sc.exe.
    Configura inicializacao automatica e acoes de recuperacao (5s, 10s, 30s).
    """
    if os.name != "nt":
        print("[!] Instalacao de servico Windows disponivel apenas em sistemas Windows.")
        return False

    bin_path = build_service_binpath(exe_path)

    # Remove servicos legados (ex: criados via NSSM anteriormente)
    for leg in LEGACY_SERVICE_NAMES:
        res_leg = subprocess.run(
            ["sc.exe", "query", leg],
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
        )
        if res_leg.returncode == 0:
            print(f"[*] Migrando servico legado '{leg}' para '{SERVICE_NAME}'...")
            subprocess.run(
                ["sc.exe", "stop", leg], capture_output=True, errors="replace", check=False
            )
            time.sleep(0.5)
            subprocess.run(
                ["sc.exe", "delete", leg], capture_output=True, errors="replace", check=False
            )

    current_status = get_windows_service_status(SERVICE_NAME)
    use_depend = bool(depend_service and is_postgres_service_present(depend_service))

    if current_status != "NOT_INSTALLED":
        print(
            f"[*] Servico {SERVICE_NAME} ja registrado (Status: {current_status}). Atualizando configuracao..."
        )
        cmd_config = [
            "sc.exe",
            "config",
            SERVICE_NAME,
            "binPath=",
            bin_path,
            "start=",
            "auto",
            "DisplayName=",
            SERVICE_DISPLAY_NAME,
        ]
        if use_depend and depend_service:
            cmd_config.extend(["depend=", depend_service])

        res_cfg = subprocess.run(
            cmd_config, capture_output=True, text=True, errors="replace", check=False
        )
        if res_cfg.returncode != 0:
            print(f"[!] Erro ao reconfigurar servico: {res_cfg.stderr or res_cfg.stdout}")
            return False
    else:
        print(f"[*] Criando servico nativo {SERVICE_NAME} com binPath: {bin_path}...")
        cmd_create = [
            "sc.exe",
            "create",
            SERVICE_NAME,
            "binPath=",
            bin_path,
            "start=",
            "auto",
            "DisplayName=",
            SERVICE_DISPLAY_NAME,
        ]
        if use_depend and depend_service:
            cmd_create.extend(["depend=", depend_service])

        res_create = subprocess.run(
            cmd_create, capture_output=True, text=True, errors="replace", check=False
        )
        if res_create.returncode != 0:
            print(f"[!] Erro ao criar servico: {res_create.stderr or res_create.stdout}")
            return False

    # Configura descricao do servico
    subprocess.run(
        ["sc.exe", "description", SERVICE_NAME, SERVICE_DESCRIPTION],
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )

    # Configura politica de auto-recuperacao do SCM (restart apos 5s, 10s e 30s)
    subprocess.run(
        [
            "sc.exe",
            "failure",
            SERVICE_NAME,
            "reset=",
            "86400",
            "actions=",
            "restart/5000/restart/10000/restart/30000",
        ],
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )

    print(
        f"[OK] Servico {SERVICE_NAME} configurado com sucesso (SCM Nativo + Auto-Restart 5s/10s/30s)."
    )
    return True


def uninstall_windows_service() -> bool:
    """Para e remove o servico AuraBackendService e eventuais servicos legados."""
    if os.name != "nt":
        return False

    for svc in [SERVICE_NAME] + LEGACY_SERVICE_NAMES:
        subprocess.run(
            ["sc.exe", "stop", svc], capture_output=True, errors="replace", check=False
        )
        subprocess.run(
            ["sc.exe", "delete", svc], capture_output=True, errors="replace", check=False
        )
    print(f"[OK] Servico {SERVICE_NAME} removido com sucesso.")
    return True


def start_windows_service() -> bool:
    """Inicia o servico AuraBackendService no Windows SCM."""
    if os.name != "nt":
        return False
    print(f"[*] Iniciando servico {SERVICE_NAME}...")
    res = subprocess.run(
        ["sc.exe", "start", SERVICE_NAME],
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    if res.returncode == 0 or "ALREADY_RUNNING" in (res.stdout + res.stderr).upper() or "1056" in (res.stdout + res.stderr):
        print(f"[OK] Servico {SERVICE_NAME} em execucao.")
        return True
    print(f"[!] Erro ao iniciar servico: {res.stderr or res.stdout}")
    return False


def stop_windows_service() -> bool:
    """Para o servico AuraBackendService no Windows SCM."""
    if os.name != "nt":
        return False
    print(f"[*] Parando servico {SERVICE_NAME}...")
    res = subprocess.run(
        ["sc.exe", "stop", SERVICE_NAME],
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    if res.returncode == 0 or "1062" in (res.stdout + res.stderr):
        print(f"[OK] Servico {SERVICE_NAME} parado.")
        return True
    print(f"[!] Erro ao parar servico: {res.stderr or res.stdout}")
    return False
