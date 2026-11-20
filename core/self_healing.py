"""
Modulo de Self-Healing de Infraestrutura Local AURA (Fase 1A - Roadmap Next-Gen).
Detecta e recupera automaticamente incidentes on-premise no Windows (role PostgreSQL
bloqueada, servico parado, Evolution API desconectada e pressao de disco/RAM)
com controle estrito de cooldown e circuit breaker para evitar loops infinitos.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import ctypes
import json
import os
import sqlite3
import subprocess
import sys
import threading
import uuid
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import httpx
import psutil
from pydantic import BaseModel, Field

from config.settings import BASE_DIR
from core.logger import logger

DEFAULT_HEALING_DB_PATH = BASE_DIR / "data" / "aura_self_healing.db"
MAX_REPAIR_ATTEMPTS_IN_WINDOW = 2
REPAIR_WINDOW_MINUTES = 30
DEFAULT_COOLDOWN_SECONDS = 900


class IncidentType(str, Enum):
    """Tipos canonicos de incidentes monitorados pelo motor de self-healing."""

    ERP_ROLE_LOCKED = "ERP_ROLE_LOCKED"
    PG_SERVICE_DOWN = "PG_SERVICE_DOWN"
    EVOLUTION_DISCONNECTED = "EVOLUTION_DISCONNECTED"
    DISK_PRESSURE = "DISK_PRESSURE"
    RAM_PRESSURE = "RAM_PRESSURE"


class HealingActionResult(BaseModel):
    """Resultado estruturado de uma tentativa de diagnostico e auto-cura."""

    incident_id: str = Field(default_factory=lambda: f"heal_{uuid.uuid4().hex[:12]}")
    incident_type: IncidentType
    severity: str = "WARNING"
    action_taken: str
    resolved: bool
    skipped_by_cooldown: bool = False
    circuit_open: bool = False
    detected_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    cooldown_until: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


def _is_windows_admin() -> bool:
    """Verifica se o processo atual possui privilegios administrativos no Windows."""
    if sys.platform != "win32":
        return os.geteuid() == 0 if hasattr(os, "geteuid") else False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def _parse_iso(ts: str | None) -> datetime | None:
    """Converte timestamp ISO-8601 em datetime UTC aware."""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except ValueError:
        return None


class AuraSelfHealer:
    """
    Motor de auto-cura operacional para ambiente on-premise Windows (CPU-only).
    Mantem historico persistente em SQLite WAL e aplica cooldown + circuit breaker.
    """

    def __init__(
        self,
        db_path: Path | str = DEFAULT_HEALING_DB_PATH,
        cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
        max_attempts_in_window: int = MAX_REPAIR_ATTEMPTS_IN_WINDOW,
        window_minutes: int = REPAIR_WINDOW_MINUTES,
        repair_script_path: Path | str | None = None,
    ) -> None:
        self.db_path_str = str(db_path)
        self.cooldown_seconds = cooldown_seconds
        self.max_attempts_in_window = max_attempts_in_window
        self.window_minutes = window_minutes
        self.repair_script_path = Path(
            repair_script_path
            if repair_script_path is not None
            else BASE_DIR / "automacoes" / "reparar_banco.ps1"
        )
        self._lock = threading.Lock()
        self._mem_conn: sqlite3.Connection | None = None

        if self.db_path_str != ":memory:":
            Path(self.db_path_str).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """Abre conexao SQLite configurada com WAL e timeout seguro."""
        if self.db_path_str == ":memory:":
            if self._mem_conn is None:
                self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._mem_conn.row_factory = sqlite3.Row
            return self._mem_conn

        conn = sqlite3.connect(self.db_path_str, timeout=5.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _close_conn(self, conn: sqlite3.Connection) -> None:
        """Fecha conexao SQLite apenas se nao for instancia compartilhada em memoria."""
        if self.db_path_str != ":memory:":
            conn.close()

    def _init_db(self) -> None:
        """Inicializa tabela e indice de eventos de self-healing."""
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS aura_healing_events (
                        id TEXT PRIMARY KEY,
                        incident_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        detected_at TEXT NOT NULL,
                        action_taken TEXT NOT NULL,
                        resolved INTEGER NOT NULL DEFAULT 0,
                        cooldown_until TEXT,
                        details_json TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_healing_type_time
                    ON aura_healing_events(incident_type, detected_at)
                    """
                )
                conn.commit()
            finally:
                self._close_conn(conn)

    def _record_event(self, result: HealingActionResult) -> None:
        """Persiste resultado de auto-cura na tabela aura_healing_events."""
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO aura_healing_events (
                        id, incident_type, severity, detected_at,
                        action_taken, resolved, cooldown_until, details_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.incident_id,
                        result.incident_type.value,
                        result.severity,
                        result.detected_at,
                        result.action_taken,
                        1 if result.resolved else 0,
                        result.cooldown_until,
                        json.dumps(result.details, ensure_ascii=False),
                    ),
                )
                conn.commit()
            finally:
                self._close_conn(conn)
        logger.info(
            "SelfHealing evento [%s] action=%s resolved=%s",
            result.incident_type.value,
            result.action_taken,
            result.resolved,
        )

    def _check_guardrails(self, incident_type: IncidentType) -> tuple[bool, bool, str | None]:
        """
        Avalia cooldown ativo e limite de tentativas na janela.
        Retorna (skip_by_cooldown, circuit_open, cooldown_until_iso).
        """
        now = datetime.now(UTC)
        window_start = (now - timedelta(minutes=self.window_minutes)).isoformat()

        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    """
                    SELECT detected_at, resolved, cooldown_until, action_taken
                    FROM aura_healing_events
                    WHERE incident_type = ? AND detected_at >= ?
                    ORDER BY detected_at DESC
                    """,
                    (incident_type.value, window_start),
                ).fetchall()
            finally:
                self._close_conn(conn)

        if not rows:
            return False, False, None

        latest = rows[0]
        latest_cooldown = _parse_iso(latest["cooldown_until"])
        if latest_cooldown and latest_cooldown > now:
            return True, latest["action_taken"].startswith("CIRCUIT_OPEN"), latest["cooldown_until"]

        attempts = sum(
            1
            for r in rows
            if not str(r["action_taken"]).startswith(("SKIPPED_", "NO_ACTION_HEALTHY"))
        )
        if attempts >= self.max_attempts_in_window:
            cooldown_iso = (now + timedelta(seconds=self.cooldown_seconds)).isoformat()
            return True, True, cooldown_iso

        return False, False, None

    def _notify_critical_manual(self, title: str, message: str, alert_key: str) -> None:
        """Dispara alerta nao bloqueante via desktop_notifier quando intervencao manual e exigida."""
        with suppress(Exception):
            from core.desktop_notifier import get_desktop_notifier

            notifier = get_desktop_notifier()
            notifier.notify(title=title, message=message, alert_key=alert_key, severity="CRITICAL")

    @staticmethod
    def diagnose_erp_error(raw_error: str) -> IncidentType | None:
        """Classifica erro bruto do PostgreSQL/libpq em tipo de incidente acionavel."""
        if not raw_error:
            return None
        lowered = raw_error.lower()
        if (
            "nao tem permissao para conectar" in lowered
            or "não tem permissão para conectar" in lowered
            or "not permitted to log in" in lowered
            or "rolcanlogin" in lowered
        ):
            return IncidentType.ERP_ROLE_LOCKED
        if (
            "connection refused" in lowered
            or "recusada" in lowered
            or "could not connect" in lowered
            or "falhou" in lowered and "5433" in lowered and "senha" not in lowered
        ):
            return IncidentType.PG_SERVICE_DOWN
        return None

    def heal_erp_role_locked(self, dry_run: bool = False) -> HealingActionResult:
        """
        Tenta recuperar role tecnica aura_service_ro quando revogada por sincronizacao do ERP.
        Respeita cooldown e verifica privilegio antes de acionar script elevado.
        """
        skip, circuit_open, cooldown_iso = self._check_guardrails(IncidentType.ERP_ROLE_LOCKED)
        if skip:
            action = (
                "CIRCUIT_OPEN_MANUAL_INTERVENTION_REQUIRED"
                if circuit_open
                else "SKIPPED_BY_COOLDOWN"
            )
            res = HealingActionResult(
                incident_type=IncidentType.ERP_ROLE_LOCKED,
                severity="CRITICAL" if circuit_open else "WARNING",
                action_taken=action,
                resolved=False,
                skipped_by_cooldown=True,
                circuit_open=circuit_open,
                cooldown_until=cooldown_iso,
                details={"reason": "Limite de auto-reparos ou cooldown ativo."},
            )
            self._record_event(res)
            if circuit_open:
                self._notify_critical_manual(
                    title="AURA Self-Healing: Intervencao Manual Necessaria",
                    message="Role aura_service_ro bloqueada repetidamente. Execute automacoes/reparar_banco_posto.bat como Admin.",
                    alert_key="self_healing_erp_role_circuit_open",
                )
            return res

        next_cooldown = (datetime.now(UTC) + timedelta(seconds=self.cooldown_seconds)).isoformat()
        if dry_run:
            res = HealingActionResult(
                incident_type=IncidentType.ERP_ROLE_LOCKED,
                severity="WARNING",
                action_taken="DRY_RUN_REPAIR_SIMULATED",
                resolved=True,
                cooldown_until=next_cooldown,
                details={"script": str(self.repair_script_path)},
            )
            self._record_event(res)
            return res

        if not self.repair_script_path.is_file():
            res = HealingActionResult(
                incident_type=IncidentType.ERP_ROLE_LOCKED,
                severity="CRITICAL",
                action_taken="REPAIR_SCRIPT_NOT_FOUND",
                resolved=False,
                cooldown_until=next_cooldown,
                details={"expected_path": str(self.repair_script_path)},
            )
            self._record_event(res)
            return res

        if not _is_windows_admin():
            res = HealingActionResult(
                incident_type=IncidentType.ERP_ROLE_LOCKED,
                severity="CRITICAL",
                action_taken="ADMIN_PRIVILEGE_REQUIRED_MANUAL_REPAIR",
                resolved=False,
                cooldown_until=next_cooldown,
                details={"hint": "Execute automacoes/REPARAR_AUTENTICACAO_BANCO.bat como Administrador."},
            )
            self._record_event(res)
            self._notify_critical_manual(
                title="AURA: Permissao ERP Bloqueada",
                message="A role aura_service_ro foi bloqueada pelo ERP. Execute REPARAR_AUTENTICACAO_BANCO.bat como Admin.",
                alert_key="self_healing_erp_admin_needed",
            )
            return res

        try:
            proc = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(self.repair_script_path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            ok = proc.returncode == 0 and "AURA_OK" in (proc.stdout + proc.stderr or "AURA_OK")
            if proc.returncode == 0:
                with suppress(Exception):
                    from core.db_pool import close_all_pools

                    close_all_pools()
            res = HealingActionResult(
                incident_type=IncidentType.ERP_ROLE_LOCKED,
                severity="INFO" if proc.returncode == 0 else "CRITICAL",
                action_taken="EXECUTED_REPAIR_SCRIPT_AND_RESET_POOLS" if proc.returncode == 0 else "REPAIR_SCRIPT_FAILED",
                resolved=proc.returncode == 0 and ok,
                cooldown_until=next_cooldown,
                details={
                    "returncode": proc.returncode,
                    "stdout_tail": (proc.stdout or "")[-400:],
                },
            )
        except (OSError, subprocess.SubprocessError) as exc:
            res = HealingActionResult(
                incident_type=IncidentType.ERP_ROLE_LOCKED,
                severity="CRITICAL",
                action_taken="REPAIR_EXECUTION_EXCEPTION",
                resolved=False,
                cooldown_until=next_cooldown,
                details={"error": str(exc)},
            )

        self._record_event(res)
        return res

    def heal_pg_service_down(
        self, service_name: str = "postgresql-x64-16", dry_run: bool = False
    ) -> HealingActionResult:
        """Tenta reiniciar o servico Windows do PostgreSQL 16 respeitando cooldown."""
        skip, circuit_open, cooldown_iso = self._check_guardrails(IncidentType.PG_SERVICE_DOWN)
        if skip:
            res = HealingActionResult(
                incident_type=IncidentType.PG_SERVICE_DOWN,
                severity="CRITICAL" if circuit_open else "WARNING",
                action_taken="CIRCUIT_OPEN_MANUAL_INTERVENTION_REQUIRED" if circuit_open else "SKIPPED_BY_COOLDOWN",
                resolved=False,
                skipped_by_cooldown=True,
                circuit_open=circuit_open,
                cooldown_until=cooldown_iso,
                details={"service_name": service_name},
            )
            self._record_event(res)
            return res

        next_cooldown = (datetime.now(UTC) + timedelta(seconds=self.cooldown_seconds)).isoformat()
        if dry_run:
            res = HealingActionResult(
                incident_type=IncidentType.PG_SERVICE_DOWN,
                severity="WARNING",
                action_taken="DRY_RUN_PG_START_SIMULATED",
                resolved=True,
                cooldown_until=next_cooldown,
                details={"service_name": service_name},
            )
            self._record_event(res)
            return res

        try:
            proc = subprocess.run(
                ["net", "start", service_name],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            resolved = proc.returncode == 0 or "already been started" in (proc.stdout + proc.stderr).lower()
            if resolved:
                with suppress(Exception):
                    from core.db_pool import close_all_pools

                    close_all_pools()
            res = HealingActionResult(
                incident_type=IncidentType.PG_SERVICE_DOWN,
                severity="INFO" if resolved else "CRITICAL",
                action_taken="NET_START_POSTGRESQL" if resolved else "NET_START_FAILED",
                resolved=resolved,
                cooldown_until=next_cooldown,
                details={"returncode": proc.returncode, "service_name": service_name},
            )
        except (OSError, subprocess.SubprocessError) as exc:
            res = HealingActionResult(
                incident_type=IncidentType.PG_SERVICE_DOWN,
                severity="CRITICAL",
                action_taken="PG_RESTART_EXCEPTION",
                resolved=False,
                cooldown_until=next_cooldown,
                details={"error": str(exc)},
            )

        self._record_event(res)
        return res

    def check_evolution_health(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        instance: str | None = None,
    ) -> HealingActionResult:
        """Verifica conectividade da instancia WhatsApp na Evolution API sem travar outbox."""
        url = (api_url or os.getenv("EVOLUTION_API_URL", "")).rstrip("/")
        key = api_key or os.getenv("EVOLUTION_API_KEY", "")
        inst = instance or os.getenv("EVOLUTION_INSTANCE", "webposto-n3")

        if not url:
            return HealingActionResult(
                incident_type=IncidentType.EVOLUTION_DISCONNECTED,
                severity="INFO",
                action_taken="EVOLUTION_URL_NOT_CONFIGURED",
                resolved=True,
                details={"configured": False},
            )

        endpoint = f"{url}/instance/connectionState/{inst}"
        try:
            resp = httpx.get(endpoint, headers={"apikey": key} if key else {}, timeout=3.0)
            data = resp.json() if resp.status_code == 200 else {}
            state = str(data.get("instance", {}).get("state", "unknown")).lower()
            if resp.status_code == 200 and state == "open":
                return HealingActionResult(
                    incident_type=IncidentType.EVOLUTION_DISCONNECTED,
                    severity="INFO",
                    action_taken="NO_ACTION_HEALTHY",
                    resolved=True,
                    details={"instance": inst, "state": state},
                )
            res = HealingActionResult(
                incident_type=IncidentType.EVOLUTION_DISCONNECTED,
                severity="WARNING",
                action_taken="EVOLUTION_RECONNECT_ALERT_LOGGED",
                resolved=False,
                details={"instance": inst, "status_code": resp.status_code, "state": state},
            )
        except (httpx.HTTPError, ValueError, OSError) as exc:
            res = HealingActionResult(
                incident_type=IncidentType.EVOLUTION_DISCONNECTED,
                severity="WARNING",
                action_taken="EVOLUTION_UNREACHABLE",
                resolved=False,
                details={"instance": inst, "error": str(exc)},
            )

        self._record_event(res)
        return res

    def heal_resource_pressure(
        self,
        disk_threshold_pct: float = 90.0,
        ram_threshold_pct: float = 92.0,
        dry_run: bool = False,
    ) -> list[HealingActionResult]:
        """Monitora uso de disco e RAM, executando trim de working set sob pressao."""
        results: list[HealingActionResult] = []
        disk_pct = float(psutil.disk_usage(str(BASE_DIR)).percent)
        ram_pct = float(psutil.virtual_memory().percent)

        if ram_pct >= ram_threshold_pct:
            trimmed = False
            if not dry_run:
                with suppress(Exception):
                    from core.resource_watchdog import trim_process_working_set

                    trimmed = bool(trim_process_working_set())
            res = HealingActionResult(
                incident_type=IncidentType.RAM_PRESSURE,
                severity="WARNING",
                action_taken="TRIM_PROCESS_WORKING_SET" if not dry_run else "DRY_RUN_RAM_TRIM",
                resolved=trimmed or dry_run,
                details={"ram_percent": ram_pct, "threshold_pct": ram_threshold_pct},
            )
            self._record_event(res)
            results.append(res)

        if disk_pct >= disk_threshold_pct:
            res = HealingActionResult(
                incident_type=IncidentType.DISK_PRESSURE,
                severity="CRITICAL",
                action_taken="DISK_PRESSURE_ALERT_RECORDED",
                resolved=False,
                details={"disk_percent": disk_pct, "threshold_pct": disk_threshold_pct},
            )
            self._record_event(res)
            results.append(res)

        return results

    def get_status(self, limit: int = 20) -> dict[str, Any]:
        """Retorna historico recente de eventos e status de circuit breaker por incidente."""
        now = datetime.now(UTC)
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    """
                    SELECT id, incident_type, severity, detected_at,
                           action_taken, resolved, cooldown_until, details_json
                    FROM aura_healing_events
                    ORDER BY detected_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            finally:
                self._close_conn(conn)

        events: list[dict[str, Any]] = []
        for r in rows:
            details: dict[str, Any] = {}
            with suppress(Exception):
                details = json.loads(r["details_json"])
            events.append(
                {
                    "id": r["id"],
                    "incident_type": r["incident_type"],
                    "severity": r["severity"],
                    "detected_at": r["detected_at"],
                    "action_taken": r["action_taken"],
                    "resolved": bool(r["resolved"]),
                    "cooldown_until": r["cooldown_until"],
                    "details": details if isinstance(details, dict) else {},
                }
            )

        guardrails: dict[str, Any] = {}
        for inc_type in IncidentType:
            skip, circuit_open, cooldown_iso = self._check_guardrails(inc_type)
            guardrails[inc_type.value] = {
                "cooldown_active": skip,
                "circuit_open": circuit_open,
                "cooldown_until": cooldown_iso,
            }

        return {
            "status": "degraded" if any(g["circuit_open"] for g in guardrails.values()) else "healthy",
            "guardrails": guardrails,
            "recent_events_count": len(events),
            "recent_events": events,
            "timestamp": now.isoformat(),
        }


_self_healer_lock = threading.Lock()
_self_healer_singleton: AuraSelfHealer | None = None


def get_self_healer() -> AuraSelfHealer:
    """Retorna instancia singleton thread-safe do AuraSelfHealer."""
    global _self_healer_singleton
    with _self_healer_lock:
        if _self_healer_singleton is None:
            _self_healer_singleton = AuraSelfHealer()
        return _self_healer_singleton


def set_self_healer(healer: AuraSelfHealer | None) -> None:
    """Permite injetar instancia customizada em testes."""
    global _self_healer_singleton
    with _self_healer_lock:
        _self_healer_singleton = healer


def reset_self_healer() -> None:
    """Reinicia o singleton do AuraSelfHealer."""
    set_self_healer(None)
