"""
Modulo de Protecao de Hardware e Circuit Breaker para PDV do Caixa (Fase 3).

Principios Arquiteturais:
1. Zero Sobrecarga Externa: Monitoramento nativo Win32 via ctypes (GlobalMemoryStatusEx
   e GetSystemTimes) sem adicionar bibliotecas externas pesadas como psutil.
2. Prioridade Absoluta ao PDV: Se a maquina do caixa apresentar consumo elevado de
   CPU ou RAM (padrao > 80% CPU ou > 85% RAM), o Circuit Breaker entra no estado OPEN,
   rejeitando consultas analiticas pesadas para nao travar notas fiscais ou liberacao de bicos.
3. Maquina de Estados Resiliente: Transicoes CLOSED -> OPEN -> HALF_OPEN -> CLOSED
   com histerese e cooldown configuravel via variaveis de ambiente.
4. Fallback Multiplataforma Defensivo: Suporte continuo a ambientes Linux / CI.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from enum import Enum
from typing import Any

logger = logging.getLogger("aura.resource_watchdog")

# Constantes de Limiares Padrao
DEFAULT_MAX_CPU_PERCENT: float = 80.0
DEFAULT_MAX_RAM_PERCENT: float = 85.0
DEFAULT_CIRCUIT_COOLDOWN_SEC: float = 30.0

PROTECTION_MESSAGE: str = (
    "Modo de Protecao do Caixa Ativo: O hardware local esta sob carga elevada (CPU/RAM > 80%). "
    "A consulta analitica pesada foi temporariamente adiada para priorizar o faturamento da pista."
)


class CircuitState(str, Enum):
    """Estados possiveis do Hardware Circuit Breaker."""

    CLOSED = "CLOSED"  # Operacao normal: ferramentas pesadas permitidas
    OPEN = "OPEN"  # Bloqueio ativo: hardware sob estresse, rejeita tarefas pesadas
    HALF_OPEN = "HALF_OPEN"  # Testando recuperacao do hardware apos cooldown


class HardwareCircuitBreaker:
    """
    Guardiao de estabilidade do host do PDV e Hardware Circuit Breaker.
    Monitora CPU e RAM do computador local via Win32 ctypes e protege o PDV.
    """

    def __init__(
        self,
        max_cpu_percent: float | None = None,
        max_ram_percent: float | None = None,
        cooldown_sec: float | None = None,
        force_os: str | None = None,
    ) -> None:
        env_cpu = os.getenv("AURA_MAX_CPU_PERCENT")
        env_ram = os.getenv("AURA_MAX_RAM_PERCENT")
        env_cd = os.getenv("AURA_CIRCUIT_COOLDOWN_SEC")

        self.max_cpu_percent: float = float(
            max_cpu_percent if max_cpu_percent is not None else (env_cpu or DEFAULT_MAX_CPU_PERCENT)
        )
        self.max_ram_percent: float = float(
            max_ram_percent if max_ram_percent is not None else (env_ram or DEFAULT_MAX_RAM_PERCENT)
        )
        self.cooldown_sec: float = float(
            cooldown_sec if cooldown_sec is not None else (env_cd or DEFAULT_CIRCUIT_COOLDOWN_SEC)
        )

        self._force_os: str | None = force_os
        self._lock = threading.RLock()
        self._state: str = CircuitState.CLOSED.value
        self._last_state_change: float = time.time()
        self._tripped_count: int = 0

        # Historico de execucoes analiticas pesadas
        self._execution_history: list[dict[str, float]] = []
        self._last_execution_duration: float = 0.0

        # Metricas simuladas para injecao em suites de teste
        self._simulated_metrics: dict[str, float] | None = None

        # Estado para medicao de CPU
        self._last_cpu_check: float = time.time()
        self._last_cpu_percent: float = 0.0
        self._last_sys_idle_time: int = 0
        self._last_sys_kernel_time: int = 0
        self._last_sys_user_time: int = 0

        # Cache de metricas para evitar sobrecarga de chamadas de kernel
        self._cache_ttl_sec: float = 1.0
        self._cached_metrics: dict[str, Any] = {}

        self._init_os_handles()
        self.sample(force=True)

    def _init_os_handles(self) -> None:
        """Inicializa handles e estruturas de dados nativas do SO."""
        target_os = (self._force_os or sys.platform).lower()
        self._is_windows = target_os.startswith("win")

        if self._is_windows:
            try:
                import ctypes
                from ctypes import wintypes

                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", wintypes.DWORD),
                        ("dwMemoryLoad", wintypes.DWORD),
                        ("ullTotalPhys", ctypes.c_uint64),
                        ("ullAvailPhys", ctypes.c_uint64),
                        ("ullTotalPageFile", ctypes.c_uint64),
                        ("ullAvailPageFile", ctypes.c_uint64),
                        ("ullTotalVirtual", ctypes.c_uint64),
                        ("ullAvailVirtual", ctypes.c_uint64),
                        ("ullAvailExtendedVirtual", ctypes.c_uint64),
                    ]

                self._ctypes = ctypes
                self._wintypes = wintypes
                self._stat_struct = MEMORYSTATUSEX
                self._kernel32 = ctypes.windll.kernel32

            except (AttributeError, OSError, TypeError, ValueError) as exc:
                logger.debug("Win32 ctypes initialization falhou, usando fallback: %s", exc)
                self._is_windows = False

    def _read_win32_metrics(self) -> tuple[float, float, float, float]:
        """Le metricas de CPU e RAM diretamente do Windows via Win32 ctypes."""
        # 1. Leitura de RAM via GlobalMemoryStatusEx
        stat = self._stat_struct()
        stat.dwLength = self._ctypes.sizeof(self._stat_struct)

        ram_pct = 0.0
        avail_mb = 0.0
        total_mb = 0.0

        if self._kernel32.GlobalMemoryStatusEx(self._ctypes.byref(stat)):
            total_mb = round(stat.ullTotalPhys / (1024 * 1024), 1)
            avail_mb = round(stat.ullAvailPhys / (1024 * 1024), 1)
            ram_pct = float(stat.dwMemoryLoad)

        # 2. Leitura de CPU do sistema via GetSystemTimes
        cpu_pct = self._last_cpu_percent
        now = time.time()
        dt = now - self._last_cpu_check

        sys_idle = self._wintypes.FILETIME()
        sys_kernel = self._wintypes.FILETIME()
        sys_user = self._wintypes.FILETIME()

        if self._kernel32.GetSystemTimes(
            self._ctypes.byref(sys_idle),
            self._ctypes.byref(sys_kernel),
            self._ctypes.byref(sys_user),
        ):
            idle = (sys_idle.dwHighDateTime << 32) + sys_idle.dwLowDateTime
            kernel = (sys_kernel.dwHighDateTime << 32) + sys_kernel.dwLowDateTime
            user = (sys_user.dwHighDateTime << 32) + sys_user.dwLowDateTime

            if self._last_sys_idle_time > 0 and dt >= 0.1:
                d_idle = idle - self._last_sys_idle_time
                d_kernel = kernel - self._last_sys_kernel_time
                d_user = user - self._last_sys_user_time
                sys_total = d_kernel + d_user
                if sys_total > 0:
                    host_busy = max(0, sys_total - d_idle)
                    cpu_pct = max(0.0, min(100.0, round((host_busy / sys_total) * 100.0, 1)))
                    self._last_cpu_percent = cpu_pct
                    self._last_sys_idle_time = idle
                    self._last_sys_kernel_time = kernel
                    self._last_sys_user_time = user
                    self._last_cpu_check = now
            elif self._last_sys_idle_time == 0:
                self._last_sys_idle_time = idle
                self._last_sys_kernel_time = kernel
                self._last_sys_user_time = user
                self._last_cpu_check = now

        return cpu_pct, ram_pct, avail_mb, total_mb

    def _read_fallback_metrics(self) -> tuple[float, float, float, float]:
        """Fallback defensivo para Linux, containers e ambientes de teste CI."""
        avail_mb = 4096.0
        total_mb = 8192.0
        ram_pct = 50.0

        try:
            if os.path.exists("/proc/meminfo"):
                mem: dict[str, int] = {}
                with open("/proc/meminfo", "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            val_str = parts[1].split()[0]
                            mem[parts[0].strip()] = int(val_str)
                if "MemTotal" in mem and "MemAvailable" in mem:
                    tot_kb = mem["MemTotal"]
                    avail_kb = mem["MemAvailable"]
                    total_mb = round(tot_kb / 1024.0, 1)
                    avail_mb = round(avail_kb / 1024.0, 1)
                    ram_pct = round(((tot_kb - avail_kb) / tot_kb) * 100.0, 1)
        except (OSError, ValueError, KeyError):
            pass

        cpu_pct = 10.0
        try:
            if os.path.exists("/proc/stat"):
                with open("/proc/stat", "r", encoding="utf-8") as f:
                    cpu_line = f.readline()
                    fields = [float(x) for x in cpu_line.strip().split()[1:]]
                    idle_t = fields[3]
                    total_t = sum(fields)
                    if self._last_sys_idle_time > 0:
                        d_total = total_t - self._last_sys_user_time
                        d_idle = idle_t - self._last_sys_idle_time
                        if d_total > 0:
                            cpu_pct = max(
                                0.0,
                                min(100.0, round(((d_total - d_idle) / d_total) * 100.0, 1)),
                            )
                    self._last_sys_user_time = int(total_t)
                    self._last_sys_idle_time = int(idle_t)
            elif hasattr(os, "getloadavg"):
                load1 = os.getloadavg()[0]
                cores = os.cpu_count() or 1
                cpu_pct = max(0.0, min(100.0, round((load1 / cores) * 100.0, 1)))
        except (OSError, ValueError, IndexError):
            pass

        return cpu_pct, ram_pct, avail_mb, total_mb

    def _read_raw_metrics(self) -> tuple[float, float, float, float]:
        """Obtem metricas brutas do sistema ou simuladas para testes."""
        if self._simulated_metrics is not None:
            cpu = float(self._simulated_metrics.get("cpu_percent", 10.0))
            ram = float(self._simulated_metrics.get("ram_percent", 40.0))
            avail = float(self._simulated_metrics.get("ram_available_mb", 4096.0))
            total = float(self._simulated_metrics.get("ram_total_mb", 8192.0))
            return cpu, ram, avail, total

        if self._is_windows:
            try:
                return self._read_win32_metrics()
            except (AttributeError, OSError, TypeError, ValueError) as exc:
                logger.debug("Falha na amostragem Win32, ativando fallback: %s", exc)
                return self._read_fallback_metrics()
        else:
            return self._read_fallback_metrics()

    def sample(self, force: bool = False) -> dict[str, Any]:
        """
        Amostra as metricas do host e atualiza a maquina de estados do Circuit Breaker.
        Aplica cache com TTL curto (1s) para garantir sub-milissegundo em chamadas repetidas.
        """
        with self._lock:
            now = time.time()
            if (
                not force
                and self._cached_metrics
                and (now - self._cached_metrics.get("updated_at", 0)) < self._cache_ttl_sec
            ):
                return dict(self._cached_metrics)

            cpu_pct, ram_pct, avail_mb, total_mb = self._read_raw_metrics()
            is_overload = (cpu_pct >= self.max_cpu_percent) or (ram_pct >= self.max_ram_percent)

            if self._state == CircuitState.CLOSED.value:
                if is_overload:
                    self._state = CircuitState.OPEN.value
                    self._last_state_change = now
                    self._tripped_count += 1
                    logger.warning(
                        "Hardware Circuit Breaker TRIP: CLOSED -> OPEN (CPU: %.1f%% / limiar %.1f%%, RAM: %.1f%% / limiar %.1f%%)",
                        cpu_pct,
                        self.max_cpu_percent,
                        ram_pct,
                        self.max_ram_percent,
                    )

            elif self._state == CircuitState.OPEN.value:
                time_in_open = now - self._last_state_change
                if time_in_open >= self.cooldown_sec:
                    self._state = CircuitState.HALF_OPEN.value
                    self._last_state_change = now
                    logger.info(
                        "Hardware Circuit Breaker: OPEN -> HALF_OPEN (cooldown de %.1fs expirou, testando recuperacao)",
                        self.cooldown_sec,
                    )

            elif self._state == CircuitState.HALF_OPEN.value and is_overload:
                self._state = CircuitState.OPEN.value
                self._last_state_change = now
                self._tripped_count += 1
                logger.warning(
                    "Hardware Circuit Breaker: HALF_OPEN -> OPEN (hardware sob sobrecarga: CPU %.1f%%, RAM %.1f%%)",
                    cpu_pct,
                    ram_pct,
                )

            cooldown_remaining = 0.0
            if self._state == CircuitState.OPEN.value:
                cooldown_remaining = max(
                    0.0, round(self.cooldown_sec - (now - self._last_state_change), 1)
                )

            self._cached_metrics = {
                "cpu_percent": cpu_pct,
                "ram_percent": ram_pct,
                "ram_available_mb": avail_mb,
                "ram_total_mb": total_mb,
                "circuit_state": self._state,
                "is_heavy_allowed": (self._state == CircuitState.CLOSED.value),
                "tripped_count": self._tripped_count,
                "cooldown_sec": self.cooldown_sec,
                "cooldown_remaining_sec": cooldown_remaining,
                "max_cpu_percent": self.max_cpu_percent,
                "max_ram_percent": self.max_ram_percent,
                "is_windows": self._is_windows,
                "updated_at": now,
                "last_execution_duration": self._last_execution_duration,
                "execution_history_count": len(self._execution_history),
            }
            return dict(self._cached_metrics)

    def get_system_metrics(self) -> dict[str, Any]:
        """
        Retorna as metricas atuais do sistema e o estado operacional do circuito.
        Campos garantidos: cpu_percent, ram_percent, ram_available_mb, circuit_state.
        """
        return self.sample()

    def is_heavy_operation_allowed(self) -> bool:
        """
        Verifica se operacoes analiticas pesadas sao permitidas no momento.
        Retorna True se o circuito estiver CLOSED (ou se recuperou com sucesso em HALF_OPEN).
        Retorna False se o circuito estiver OPEN para blindar o computador do caixa.
        """
        with self._lock:
            now = time.time()
            if self._state == CircuitState.OPEN.value:
                time_in_open = now - self._last_state_change
                if time_in_open >= self.cooldown_sec:
                    # Cooldown expirou, transita para HALF_OPEN e avalia recuperacao
                    self._state = CircuitState.HALF_OPEN.value
                    self._last_state_change = now
                    logger.info(
                        "Hardware Circuit Breaker: OPEN -> HALF_OPEN (cooldown de %.1fs expirou, testando recuperacao)",
                        self.cooldown_sec,
                    )
                    metrics = self.sample(force=True)
                    if not (metrics["cpu_percent"] >= self.max_cpu_percent or metrics["ram_percent"] >= self.max_ram_percent):
                        self._state = CircuitState.CLOSED.value
                        self._last_state_change = now
                        self._cached_metrics["circuit_state"] = CircuitState.CLOSED.value
                        self._cached_metrics["is_heavy_allowed"] = True
                        logger.info(
                            "Hardware Circuit Breaker: HALF_OPEN -> CLOSED (hardware recuperado: CPU %.1f%%, RAM %.1f%%)",
                            metrics["cpu_percent"],
                            metrics["ram_percent"],
                        )
                        return True
                    else:
                        self._state = CircuitState.OPEN.value
                        self._last_state_change = now
                        self._tripped_count += 1
                        self._cached_metrics["circuit_state"] = CircuitState.OPEN.value
                        self._cached_metrics["is_heavy_allowed"] = False
                        self._cached_metrics["tripped_count"] = self._tripped_count
                        logger.warning(
                            "Hardware Circuit Breaker: HALF_OPEN -> OPEN (hardware sob sobrecarga: CPU %.1f%%, RAM %.1f%%)",
                            metrics["cpu_percent"],
                            metrics["ram_percent"],
                        )
                        return False
                return False

            elif self._state == CircuitState.HALF_OPEN.value:
                metrics = self.sample(force=True)
                if not (metrics["cpu_percent"] >= self.max_cpu_percent or metrics["ram_percent"] >= self.max_ram_percent):
                    self._state = CircuitState.CLOSED.value
                    self._last_state_change = now
                    self._cached_metrics["circuit_state"] = CircuitState.CLOSED.value
                    self._cached_metrics["is_heavy_allowed"] = True
                    logger.info(
                        "Hardware Circuit Breaker: HALF_OPEN -> CLOSED (hardware recuperado: CPU %.1f%%, RAM %.1f%%)",
                        metrics["cpu_percent"],
                        metrics["ram_percent"],
                    )
                    return True
                else:
                    self._state = CircuitState.OPEN.value
                    self._last_state_change = now
                    self._tripped_count += 1
                    self._cached_metrics["circuit_state"] = CircuitState.OPEN.value
                    self._cached_metrics["is_heavy_allowed"] = False
                    self._cached_metrics["tripped_count"] = self._tripped_count
                    logger.warning(
                        "Hardware Circuit Breaker: HALF_OPEN -> OPEN (hardware sob sobrecarga: CPU %.1f%%, RAM %.1f%%)",
                        metrics["cpu_percent"],
                        metrics["ram_percent"],
                    )
                    return False

            else:
                # CLOSED: amostra se o cache expirou para verificar se houve sobrecarga
                if (now - self._cached_metrics.get("updated_at", 0)) >= self._cache_ttl_sec:
                    metrics = self.sample(force=True)
                    return metrics["circuit_state"] == CircuitState.CLOSED.value
                return True

    def record_execution_impact(self, duration_sec: float) -> None:
        """Registra o impacto e duracao de uma ferramenta analitica pesada executada."""
        with self._lock:
            dur = max(0.0, float(duration_sec))
            self._last_execution_duration = round(dur, 4)
            self._execution_history.append({"timestamp": time.time(), "duration_sec": dur})
            if len(self._execution_history) > 100:
                self._execution_history.pop(0)
            if self._cached_metrics:
                self._cached_metrics["last_execution_duration"] = self._last_execution_duration
                self._cached_metrics["execution_history_count"] = len(self._execution_history)

    # -------------------------------------------------------------------------
    # METODOS DE CONTROLE OPERACIONAL E TESTES UNITARIOS
    # -------------------------------------------------------------------------

    def trip(self, reason: str = "manual") -> None:
        """Forca o desarme do circuito para o estado OPEN."""
        with self._lock:
            now = time.time()
            self._state = CircuitState.OPEN.value
            self._last_state_change = now
            self._tripped_count += 1
            self._cached_metrics.clear()
            logger.warning("Hardware Circuit Breaker desarmado manualmente para OPEN: %s", reason)

    def reset(self) -> None:
        """Reseta o circuito para o estado CLOSED."""
        with self._lock:
            now = time.time()
            self._state = CircuitState.CLOSED.value
            self._last_state_change = now
            self._cached_metrics.clear()
            logger.info("Hardware Circuit Breaker resetado para CLOSED.")

    def set_state(self, state: str) -> None:
        """Define o estado do circuito diretamente (para testes controlados)."""
        with self._lock:
            norm_state = state.strip().upper()
            if norm_state not in (
                CircuitState.CLOSED.value,
                CircuitState.OPEN.value,
                CircuitState.HALF_OPEN.value,
            ):
                raise ValueError(f"Estado de circuito invalido: {state}")
            self._state = norm_state
            self._last_state_change = time.time()
            self._cached_metrics.clear()

    def set_simulated_metrics(
        self,
        cpu_percent: float | None = None,
        ram_percent: float | None = None,
        ram_available_mb: float | None = None,
        ram_total_mb: float | None = None,
    ) -> None:
        """Injeta metricas simuladas para testes unitarios confiaveis e deterministicos."""
        with self._lock:
            self._simulated_metrics = {
                "cpu_percent": float(cpu_percent if cpu_percent is not None else 10.0),
                "ram_percent": float(ram_percent if ram_percent is not None else 40.0),
                "ram_available_mb": float(
                    ram_available_mb if ram_available_mb is not None else 4096.0
                ),
                "ram_total_mb": float(ram_total_mb if ram_total_mb is not None else 8192.0),
            }
            self._cached_metrics.clear()

    def clear_simulated_metrics(self) -> None:
        """Remove a simulacao de metricas, restaurando leitura real do sistema."""
        with self._lock:
            self._simulated_metrics = None
            self._cached_metrics.clear()


# Alias canonico para paridade com o Sentinel
ResourceWatchdog = HardwareCircuitBreaker

# -----------------------------------------------------------------------------
# SINGLETON THREAD-SAFE
# -----------------------------------------------------------------------------

_GLOBAL_WATCHDOG: HardwareCircuitBreaker | None = None
_WATCHDOG_LOCK = threading.Lock()


def get_resource_watchdog() -> HardwareCircuitBreaker:
    """Retorna a instancia singleton thread-safe do HardwareCircuitBreaker."""
    global _GLOBAL_WATCHDOG
    if _GLOBAL_WATCHDOG is None:
        with _WATCHDOG_LOCK:
            if _GLOBAL_WATCHDOG is None:
                _GLOBAL_WATCHDOG = HardwareCircuitBreaker()
    return _GLOBAL_WATCHDOG


def reset_resource_watchdog() -> None:
    """Reseta o singleton global do watchdog (utilizado em suites de teste)."""
    global _GLOBAL_WATCHDOG
    with _WATCHDOG_LOCK:
        _GLOBAL_WATCHDOG = None
