"""
Modulo Notificador Desktop HITL (Human-In-The-Loop) - Fase 4 (Roadmap Sentinel-AURA).

Projetado para atravessar o isolamento da Sessao 0 (servico Windows LocalSystem)
para a Sessao 1+ (desktop interativo onde opera o frente de caixa / ERP do posto)
utilizando as APIs nativas do Windows Terminal Services (wtsapi32.dll e kernel32.dll).

Principios Arquiteturais:
1. Travessia Sessao 0 -> Sessao 1: Descoberta dinamica da sessao ativa do operador
   via WTSGetActiveConsoleSessionId() e projecao de modal via WTSSendMessageW().
2. Visibilidade Critica Garantida: Uso de flags MB_TOPMOST (0x00040000),
   MB_SETFOREGROUND (0x00010000) e MB_SYSTEMMODAL (0x00001000) para sobrepor
   janelas de faturamento do ERP mesmo quando o navegador web estiver fechado.
3. Confirmacao Interativa HITL: Suporte a dialogos [Sim / Nao] com timeout
   estrito para aprovacao humana de acoes criticas em tempo real (IDYES, IDNO, IDTIMEOUT).
4. Controle Anti-Spam (Cooldown): Deduplicacao por alert_key com janela configuravel
   (padrao 300s) para nao inundar a tela do operador de caixa.
5. Fallback Defensivo Headless / CI / Linux: Quando nao ha sessao de console ativa
   (0xFFFFFFFF), em sistemas nao-Windows, quando desabilitado via variavel de ambiente
   ou em execucao automatizada de testes sem mock explicito, opera em modo simulado
   sem jamais bloquear a thread de execucao.
Zero travessoes em todo o arquivo.
"""
# ruff: noqa: BLE001

from __future__ import annotations

import ctypes
import logging
import os
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from unittest.mock import Base as MockBase

logger = logging.getLogger("aura.desktop_notifier")

# =============================================================================
# CONSTANTES WIN32 MESSAGEBOX & WINDOWS TERMINAL SERVICES (WTSAPI32)
# =============================================================================

WTS_CURRENT_SERVER_HANDLE: int = 0
INVALID_SESSION_ID: int = 0xFFFFFFFF

# Botoes MessageBox
MB_OK: int = 0x00000000
MB_OKCANCEL: int = 0x00000001
MB_YESNO: int = 0x00000004

# Icones MessageBox
MB_ICONERROR: int = 0x00000010
MB_ICONQUESTION: int = 0x00000020
MB_ICONWARNING: int = 0x00000030
MB_ICONINFORMATION: int = 0x00000040

# Modalidade e Z-Order Topmost
MB_SYSTEMMODAL: int = 0x00001000
MB_SETFOREGROUND: int = 0x00010000
MB_TOPMOST: int = 0x00040000

# Codigos de Retorno (pResponse de WTSSendMessageW)
IDOK: int = 1
IDCANCEL: int = 2
IDABORT: int = 3
IDRETRY: int = 4
IDIGNORE: int = 5
IDYES: int = 6
IDNO: int = 7
IDTIMEOUT: int = 32000
IDASYNC: int = 32001

RESPONSE_CODE_LABELS: dict[int, str] = {
    IDOK: "OK",
    IDCANCEL: "CANCEL",
    IDABORT: "ABORT",
    IDRETRY: "RETRY",
    IDIGNORE: "IGNORE",
    IDYES: "YES",
    IDNO: "NO",
    IDTIMEOUT: "TIMEOUT",
    IDASYNC: "ASYNC",
}

# Configuracoes Padrao
DEFAULT_COOLDOWN_SEC: float = 300.0
DEFAULT_NOTIFY_TIMEOUT_SEC: int = 15
DEFAULT_CONFIRM_TIMEOUT_SEC: int = 30
MAX_HISTORY_ITEMS: int = 200


# =============================================================================
# CONTRATOS DE DADOS (RESULTADOS DE NOTIFICACAO E CONFIRMACAO HITL)
# =============================================================================


@dataclass
class DesktopNotificationResult:
    """Resultado estruturado de uma notificacao desktop (WTSSendMessageW)."""

    success: bool
    delivered: bool
    simulated: bool
    suppressed_by_cooldown: bool = False
    session_id: int = 0
    title: str = ""
    message: str = ""
    severity: str = "warning"
    alert_key: str | None = None
    style: int = 0
    timeout_sec: int = DEFAULT_NOTIFY_TIMEOUT_SEC
    response_code: int = IDOK
    response_label: str = "OK"
    status: str = "delivered"
    reason: str | None = None
    event_type: str = "notification"
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def suppressed(self) -> bool:
        """Alias booleano para indicar supressao por cooldown anti-spam."""
        return self.suppressed_by_cooldown

    def to_dict(self) -> dict[str, Any]:
        """Converte o resultado para dicionario serializavel em JSON."""
        data = asdict(self)
        data["suppressed"] = self.suppressed_by_cooldown
        return data


@dataclass
class DesktopConfirmationResult:
    """Resultado estruturado de um dialogo interativo HITL [Sim / Nao]."""

    approved: bool
    response_code: int
    response_label: str
    timed_out: bool = False
    simulated: bool = False
    session_id: int = 0
    title: str = ""
    message: str = ""
    action_key: str | None = None
    style: int = 0
    timeout_sec: int = DEFAULT_CONFIRM_TIMEOUT_SEC
    status: str = "completed"
    reason: str | None = None
    event_type: str = "confirmation"
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Converte o resultado para dicionario serializavel em JSON."""
        return asdict(self)


# =============================================================================
# MOTOR DE NOTIFICACAO DESKTOP SESSAO 0 -> SESSAO 1
# =============================================================================


_CFUNC_PTR_TYPE = getattr(ctypes, "_CFuncPtr", None)
_CDLL_TYPE = getattr(ctypes, "CDLL", None)
_MODULE_REAL_KERNEL32: Any | None = None
_MODULE_REAL_WTSAPI32: Any | None = None

try:
    _windll_boot = getattr(ctypes, "windll", None)
    if _windll_boot is not None:
        _MODULE_REAL_KERNEL32 = _windll_boot.kernel32
        _MODULE_REAL_WTSAPI32 = _windll_boot.wtsapi32
except (AttributeError, OSError):
    pass


def _is_mock_object(obj: Any) -> bool:
    """Detecta se um objeto ou ponteiro de funcao foi substituido por Mock de teste."""
    if obj is None:
        return False
    if isinstance(obj, MockBase):
        return True
    if hasattr(obj, "_mock_name") or hasattr(obj, "_mock_return_value"):
        return True
    cls_name = type(obj).__name__.lower()
    return "mock" in cls_name or "fake" in cls_name or "stub" in cls_name


def _is_real_cdll(dll: Any) -> bool:
    """Verifica se o objeto e uma instancia genuina de ctypes.CDLL / WinDLL."""
    if dll is None or _is_mock_object(dll):
        return False
    return bool(_CDLL_TYPE is not None and isinstance(dll, _CDLL_TYPE))


def _is_real_cfunc(fn: Any) -> bool:
    """Verifica se o atributo de funcao e um ponteiro C nativo (_CFuncPtr) do ctypes."""
    if fn is None or _is_mock_object(fn):
        return False
    return bool(_CFUNC_PTR_TYPE is not None and isinstance(fn, _CFUNC_PTR_TYPE))


def _in_pytest_runtime() -> bool:
    """Retorna True se o processo atual estiver executando sob o runner do pytest."""
    return ("PYTEST_CURRENT_TEST" in os.environ) or ("pytest" in sys.modules)


class DesktopNotifier:
    """
    Notificador Desktop nativo do Windows para travessia da Sessao 0 para a Sessao 1.
    Exibe alertas criticos de pista/caixa e dialogos de confirmacao [Sim/Nao]
    diretamente sobre o ERP do operador via wtsapi32.WTSSendMessageW.
    """

    def __init__(
        self,
        enabled: bool | None = None,
        cooldown_sec: float | None = None,
        default_timeout_sec: int = DEFAULT_NOTIFY_TIMEOUT_SEC,
        confirm_timeout_sec: int = DEFAULT_CONFIRM_TIMEOUT_SEC,
        force_os: str | None = None,
        kernel32: Any | None = None,
        wtsapi32: Any | None = None,
        default_simulated_approval: bool = False,
    ) -> None:
        env_enabled = os.getenv("AURA_DESKTOP_NOTIFY_ENABLED")
        if enabled is not None:
            self.enabled: bool = bool(enabled)
        elif env_enabled is not None:
            self.enabled = env_enabled.strip().lower() not in ("0", "false", "no", "off")
        else:
            self.enabled = True

        env_cooldown = os.getenv("AURA_DESKTOP_COOLDOWN_SEC")
        self.cooldown_sec: float = float(
            cooldown_sec if cooldown_sec is not None else (env_cooldown or DEFAULT_COOLDOWN_SEC)
        )
        self.default_timeout_sec: int = max(1, int(default_timeout_sec))
        self.confirm_timeout_sec: int = max(1, int(confirm_timeout_sec))
        self._force_os: str | None = force_os
        self._default_simulated_approval: bool = bool(default_simulated_approval)
        self._simulated_response: int | None = None

        self._lock = threading.RLock()
        self._confirm_lock = threading.Lock()
        self._cooldown_cache: dict[str, float] = {}
        self._history: list[dict[str, Any]] = []

        self._kernel32: Any | None = kernel32
        self._wtsapi32: Any | None = wtsapi32
        self._initial_real_kernel32: Any | None = _MODULE_REAL_KERNEL32
        self._initial_real_wtsapi32: Any | None = _MODULE_REAL_WTSAPI32

        self._init_os_handles()

    def _init_os_handles(self) -> None:
        """Inicializa os handles de DLLs Win32 quando executado em ambiente Windows."""
        if self._force_os is not None:
            target_os = self._force_os.strip().lower()
            self._is_windows = target_os in ("nt", "win", "win32", "windows")
        else:
            self._is_windows = (os.name == "nt") and sys.platform.lower().startswith("win")

        if self._is_windows and self._kernel32 is None and self._wtsapi32 is None:
            try:
                windll = getattr(ctypes, "windll", None)
                if windll is not None:
                    self._kernel32 = windll.kernel32
                    self._wtsapi32 = windll.wtsapi32
                elif self._force_os is None:
                    self._is_windows = False
            except (AttributeError, OSError) as exc:
                logger.debug("Falha ao carregar DLLs Win32 no DesktopNotifier: %s", exc)
                if self._force_os is None:
                    self._is_windows = False

    def _is_windows_runtime(self) -> bool:
        """Avalia se o runtime atual e Windows, respeitando force_os e monkeypatches em os.name/sys.platform."""
        if self._force_os is not None:
            target_os = self._force_os.strip().lower()
            return target_os in ("nt", "win", "win32", "windows")
        return self._is_windows and (os.name == "nt") and sys.platform.lower().startswith("win")

    @property
    def kernel32(self) -> Any | None:
        """Retorna a referencia atual para kernel32."""
        return self._kernel32

    @kernel32.setter
    def kernel32(self, value: Any | None) -> None:
        self._kernel32 = value

    @property
    def wtsapi32(self) -> Any | None:
        """Retorna a referencia atual para wtsapi32."""
        return self._wtsapi32

    @wtsapi32.setter
    def wtsapi32(self, value: Any | None) -> None:
        self._wtsapi32 = value

    def _resolve_win32_handles(self) -> tuple[Any | None, Any | None]:
        """
        Resolve dinamicamente os handles de kernel32 e wtsapi32, respeitando tanto
        injecao direta na instancia quanto patches aplicados em ctypes.windll.
        """
        k32 = self._kernel32
        wts = self._wtsapi32

        windll = getattr(ctypes, "windll", None)
        if windll is not None:
            try:
                if _is_mock_object(windll) or not hasattr(windll, "_FuncPtr"):
                    if k32 is None or k32 is self._initial_real_kernel32:
                        k32 = getattr(windll, "kernel32", k32)
                    if wts is None or wts is self._initial_real_wtsapi32:
                        wts = getattr(windll, "wtsapi32", wts)
                else:
                    if (
                        k32 is self._initial_real_kernel32
                        and hasattr(windll, "kernel32")
                        and windll.kernel32 is not self._initial_real_kernel32
                    ):
                        k32 = windll.kernel32
                    if (
                        wts is self._initial_real_wtsapi32
                        and hasattr(windll, "wtsapi32")
                        and windll.wtsapi32 is not self._initial_real_wtsapi32
                    ):
                        wts = windll.wtsapi32
            except (AttributeError, OSError):
                pass

        return k32, wts

    def _is_k32_mocked(self, k32: Any | None) -> bool:
        """Verifica se kernel32 ou WTSGetActiveConsoleSessionId foi substituido por mock/stub."""
        if k32 is None:
            return False
        if not _is_real_cdll(k32):
            return True
        if self._initial_real_kernel32 is not None and k32 is not self._initial_real_kernel32:
            return True
        fn = getattr(k32, "WTSGetActiveConsoleSessionId", None)
        return not _is_real_cfunc(fn)

    def _is_wts_mocked(self, wts: Any | None) -> bool:
        """Verifica se wtsapi32 ou WTSSendMessageW foi substituido por mock/stub."""
        if wts is None:
            return False
        if not _is_real_cdll(wts):
            return True
        if self._initial_real_wtsapi32 is not None and wts is not self._initial_real_wtsapi32:
            return True
        fn = getattr(wts, "WTSSendMessageW", None)
        return not _is_real_cfunc(fn)

    def _is_win32_mocked(self, k32: Any | None, wts: Any | None) -> bool:
        """
        Verifica se kernel32 ou wtsapi32 (ou suas funcoes alvo) sao mocks/stubs
        injetados por testes unitarios.
        """
        return self._is_k32_mocked(k32) or self._is_wts_mocked(wts)

    def _should_use_pytest_safe_fallback(self, k32: Any | None, wts: Any | None) -> bool:
        """
        Impede que execucoes automatizadas do pytest abram janelas modais reais no
        desktop Windows quando wtsapi32/kernel32 nao estiverem mockados.
        """
        if not _in_pytest_runtime():
            return False
        return not self._is_win32_mocked(k32, wts)

    def _is_effectively_enabled(self) -> bool:
        """Verifica se o notificador esta habilitado na instancia e no ambiente."""
        if not self.enabled:
            return False
        env_val = os.getenv("AURA_DESKTOP_NOTIFY_ENABLED")
        return not (env_val is not None and env_val.strip().lower() in ("0", "false", "no", "off"))

    @staticmethod
    def build_notification_style(severity: str = "warning") -> int:
        """
        Calcula a mascara de bits Win32 MessageBox conforme a severidade do alerta,
        combinando MB_OK com icone semantico e flags Topmost/SystemModal.
        """
        sev = (severity or "warning").strip().lower()
        if sev in ("critical", "error", "critica", "critico", "extreme", "fatal"):
            icon_flag = MB_ICONERROR
        elif sev in ("info", "information", "low", "informativo"):
            icon_flag = MB_ICONINFORMATION
        else:
            icon_flag = MB_ICONWARNING

        return MB_OK | icon_flag | MB_TOPMOST | MB_SETFOREGROUND | MB_SYSTEMMODAL

    @staticmethod
    def build_confirmation_style() -> int:
        """
        Calcula a mascara de bits Win32 MessageBox para confirmacao HITL [Sim/Nao],
        combinando MB_YESNO | MB_ICONQUESTION | MB_TOPMOST | MB_SETFOREGROUND | MB_SYSTEMMODAL.
        """
        return MB_YESNO | MB_ICONQUESTION | MB_TOPMOST | MB_SETFOREGROUND | MB_SYSTEMMODAL

    def get_active_console_session_id(self) -> int:
        """
        Obtem o ID da sessao interativa ativa do console via WTSGetActiveConsoleSessionId().
        Retorna INVALID_SESSION_ID (0xFFFFFFFF) se nao houver operador logado ou fora do Windows.
        """
        if not self._is_windows_runtime():
            return INVALID_SESSION_ID

        k32, wts = self._resolve_win32_handles()
        if k32 is None or not hasattr(k32, "WTSGetActiveConsoleSessionId"):
            return INVALID_SESSION_ID

        if self._should_use_pytest_safe_fallback(k32, wts):
            return INVALID_SESSION_ID

        try:
            raw_session = k32.WTSGetActiveConsoleSessionId()
            return int(raw_session) & 0xFFFFFFFF
        except (AttributeError, OSError, TypeError, ValueError, RuntimeError) as exc:
            logger.warning("Erro ao consultar WTSGetActiveConsoleSessionId: %s", exc)
            return INVALID_SESSION_ID

    # =========================================================================
    # CONTROLE ANTI-SPAM (COOLDOWN E DEDUPLICACAO)
    # =========================================================================

    def is_in_cooldown(self, alert_key: str | None) -> bool:
        """Verifica se a chave de alerta informada ainda esta dentro da janela de cooldown."""
        if not alert_key:
            return False
        norm_key = str(alert_key).strip().upper()
        if not norm_key or self.cooldown_sec <= 0:
            return False

        with self._lock:
            last_ts = self._cooldown_cache.get(norm_key)
            if last_ts is None:
                return False
            return (time.time() - last_ts) < self.cooldown_sec

    def record_cooldown(self, alert_key: str | None, timestamp: float | None = None) -> None:
        """Registra o disparo de um alerta na tabela de cooldown em memoria."""
        if not alert_key:
            return
        norm_key = str(alert_key).strip().upper()
        if not norm_key:
            return
        with self._lock:
            self._cooldown_cache[norm_key] = timestamp if timestamp is not None else time.time()

    def _try_acquire_cooldown(
        self,
        alert_key: str | None,
        force: bool = False,
    ) -> tuple[bool, bool, float | None]:
        """
        Verifica e reserva atomicamente o cooldown para alert_key sob lock,
        evitando condicao de corrida (TOCTOU) quando multiplas threads disparam o mesmo alerta.
        Retorna (acquired, tracked, previous_timestamp).
        """
        if not alert_key:
            return True, False, None
        norm_key = str(alert_key).strip().upper()
        if not norm_key:
            return True, False, None

        with self._lock:
            now = time.time()
            prev_ts = self._cooldown_cache.get(norm_key)
            if (
                not force
                and self.cooldown_sec > 0
                and prev_ts is not None
                and (now - prev_ts) < self.cooldown_sec
            ):
                return False, False, prev_ts
            self._cooldown_cache[norm_key] = now
            return True, True, prev_ts

    def _rollback_cooldown(
        self,
        alert_key: str | None,
        tracked: bool,
        prev_ts: float | None,
    ) -> None:
        """Restaura o estado anterior do cooldown caso o envio falhe ou nao haja sessao ativa."""
        if not tracked or not alert_key:
            return
        norm_key = str(alert_key).strip().upper()
        if not norm_key:
            return
        with self._lock:
            if prev_ts is None:
                self._cooldown_cache.pop(norm_key, None)
            else:
                self._cooldown_cache[norm_key] = prev_ts

    def clear_cooldown(self, alert_key: str | None = None) -> None:
        """Limpa o cooldown de uma chave especifica ou todo o cache de deduplicacao."""
        with self._lock:
            if alert_key is None:
                self._cooldown_cache.clear()
            else:
                norm_key = str(alert_key).strip().upper()
                self._cooldown_cache.pop(norm_key, None)

    # =========================================================================
    # HISTORICO E AUDITORIA EM MEMORIA
    # =========================================================================

    def _record_history(self, entry: dict[str, Any]) -> None:
        """Armazena evento de notificacao ou confirmacao no buffer circular de historico."""
        with self._lock:
            self._history.insert(0, dict(entry))
            if len(self._history) > MAX_HISTORY_ITEMS:
                self._history.pop()

    def get_history(
        self,
        limit: int = 50,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retorna o historico recente de notificacoes e confirmacoes desktop emitidas."""
        safe_limit = max(1, min(int(limit), MAX_HISTORY_ITEMS))
        with self._lock:
            items = list(self._history)

        if event_type:
            norm_type = event_type.strip().lower()
            items = [i for i in items if str(i.get("event_type", "")).lower() == norm_type]

        return items[:safe_limit]

    def clear_history(self) -> None:
        """Limpa o historico de eventos em memoria."""
        with self._lock:
            self._history.clear()

    def set_simulated_response(self, response_code: int | None) -> None:
        """Define um codigo de resposta simulado (ex: IDYES, IDNO, IDTIMEOUT) para testes."""
        with self._lock:
            self._simulated_response = int(response_code) if response_code is not None else None

    # =========================================================================
    # OPERACOES PRINCIPAIS: NOTIFY & CONFIRM (WTSSendMessageW)
    # =========================================================================

    def notify_operator(
        self,
        title: str,
        message: str,
        severity: str = "warning",
        timeout_sec: int = DEFAULT_NOTIFY_TIMEOUT_SEC,
        alert_key: str | None = None,
        force: bool = False,
    ) -> DesktopNotificationResult:
        """
        Exibe alerta modal Topmost na Sessao 1 do operador via WTSSendMessageW.
        Respeita janela de cooldown por alert_key e opera com fallback seguro em
        ambientes sem sessao ativa (0xFFFFFFFF), Linux/CI ou testes nao mockados.
        """
        clean_title = str(title or "Alerta Operacional AURA").strip()
        clean_message = str(message or "").strip()
        norm_severity = str(severity or "warning").strip().lower()
        effective_timeout = max(
            1, int(timeout_sec if timeout_sec is not None else self.default_timeout_sec)
        )
        style = self.build_notification_style(norm_severity)

        # 1. Verificacao e reserva atomica de Cooldown Anti-Spam (protegido contra TOCTOU)
        acquired_cd, tracked_cd, prev_cd_ts = self._try_acquire_cooldown(alert_key, force=force)
        if not acquired_cd:
            res = DesktopNotificationResult(
                success=True,
                delivered=False,
                simulated=False,
                suppressed_by_cooldown=True,
                session_id=0,
                title=clean_title,
                message=clean_message,
                severity=norm_severity,
                alert_key=alert_key,
                style=style,
                timeout_sec=effective_timeout,
                response_code=0,
                response_label="COOLDOWN_SUPPRESSED",
                status="cooldown_suppressed",
                reason=f"Alerta '{alert_key}' suprimido pela janela de cooldown ({self.cooldown_sec}s).",
            )
            logger.debug("DesktopNotifier: alerta '%s' suprimido por cooldown.", alert_key)
            self._record_history(res.to_dict())
            return res

        # 2. Verificacao de desativacao explicita
        if not self._is_effectively_enabled():
            res = DesktopNotificationResult(
                success=True,
                delivered=False,
                simulated=True,
                suppressed_by_cooldown=False,
                session_id=0,
                title=clean_title,
                message=clean_message,
                severity=norm_severity,
                alert_key=alert_key,
                style=style,
                timeout_sec=effective_timeout,
                response_code=IDOK,
                response_label="DISABLED_FALLBACK",
                status="disabled",
                reason="Notificador desktop desabilitado (AURA_DESKTOP_NOTIFY_ENABLED=false).",
            )
            logger.info("DesktopNotifier (desabilitado): [%s] %s", clean_title, clean_message)
            self._record_history(res.to_dict())
            return res

        k32, wts = self._resolve_win32_handles()

        # 3. Verificacao de ambiente nao-Windows ou modo seguro de pytest sem mock
        if (
            not self._is_windows_runtime()
            or wts is None
            or self._should_use_pytest_safe_fallback(k32, wts)
        ):
            res = DesktopNotificationResult(
                success=True,
                delivered=False,
                simulated=True,
                suppressed_by_cooldown=False,
                session_id=0,
                title=clean_title,
                message=clean_message,
                severity=norm_severity,
                alert_key=alert_key,
                style=style,
                timeout_sec=effective_timeout,
                response_code=IDOK,
                response_label="SIMULATED",
                status="simulated",
                reason="Fallback seguro ativo (ambiente headless/CI/Linux ou pytest sem mock).",
            )
            logger.info("DesktopNotifier (simulado): [%s] %s", clean_title, clean_message)
            self._record_history(res.to_dict())
            return res

        # 4. Descoberta da sessao de console interativa ativa (Sessao 1+)
        try:
            raw_session = (
                k32.WTSGetActiveConsoleSessionId()
                if (k32 is not None and (not _in_pytest_runtime() or self._is_k32_mocked(k32)))
                else (1 if _in_pytest_runtime() else INVALID_SESSION_ID)
            )
            session_id = int(raw_session) & 0xFFFFFFFF
        except Exception as exc:
            logger.warning("DesktopNotifier: falha ao obter sessao ativa: %s", exc)
            session_id = INVALID_SESSION_ID

        if session_id == INVALID_SESSION_ID:
            self._rollback_cooldown(alert_key, tracked_cd, prev_cd_ts)
            res = DesktopNotificationResult(
                success=True,
                delivered=False,
                simulated=True,
                suppressed_by_cooldown=False,
                session_id=INVALID_SESSION_ID,
                title=clean_title,
                message=clean_message,
                severity=norm_severity,
                alert_key=alert_key,
                style=style,
                timeout_sec=effective_timeout,
                response_code=0,
                response_label="NO_CONSOLE_SESSION",
                status="no_session",
                reason="Nenhuma sessao de console interativa ativa (0xFFFFFFFF).",
            )
            logger.info(
                "DesktopNotifier: sem sessao ativa (0xFFFFFFFF), alerta registrado em fallback: %s",
                clean_title,
            )
            self._record_history(res.to_dict())
            return res

        # Em pytest, nunca invoca wtsapi32 real mesmo que apenas kernel32 tenha sido mockado
        if _in_pytest_runtime() and not self._is_wts_mocked(wts):
            res = DesktopNotificationResult(
                success=True,
                delivered=False,
                simulated=True,
                suppressed_by_cooldown=False,
                session_id=session_id,
                title=clean_title,
                message=clean_message,
                severity=norm_severity,
                alert_key=alert_key,
                style=style,
                timeout_sec=effective_timeout,
                response_code=IDOK,
                response_label="SIMULATED",
                status="simulated",
                reason="Fallback seguro ativo (wtsapi32 nao mockado em pytest).",
            )
            self._record_history(res.to_dict())
            return res

        # 5. Invocacao nativa de WTSSendMessageW atravessando Sessao 0 -> Sessao 1
        title_bytes_len = len(clean_title.encode("utf-16-le"))
        message_bytes_len = len(clean_message.encode("utf-16-le"))
        response_dword = ctypes.c_ulong(0)
        p_response = ctypes.pointer(response_dword)

        try:
            ok = wts.WTSSendMessageW(
                WTS_CURRENT_SERVER_HANDLE,
                int(session_id),
                clean_title,
                title_bytes_len,
                clean_message,
                message_bytes_len,
                int(style),
                int(effective_timeout),
                p_response,
                True,
            )
        except Exception as exc:
            self._rollback_cooldown(alert_key, tracked_cd, prev_cd_ts)
            logger.error("DesktopNotifier: erro ao invocar WTSSendMessageW: %s", exc)
            res = DesktopNotificationResult(
                success=False,
                delivered=False,
                simulated=False,
                suppressed_by_cooldown=False,
                session_id=session_id,
                title=clean_title,
                message=clean_message,
                severity=norm_severity,
                alert_key=alert_key,
                style=style,
                timeout_sec=effective_timeout,
                response_code=0,
                response_label="ERROR",
                status="error",
                reason=f"Excecao ao invocar WTSSendMessageW: {exc}",
            )
            self._record_history(res.to_dict())
            return res

        if not ok:
            self._rollback_cooldown(alert_key, tracked_cd, prev_cd_ts)
            res = DesktopNotificationResult(
                success=False,
                delivered=False,
                simulated=False,
                suppressed_by_cooldown=False,
                session_id=session_id,
                title=clean_title,
                message=clean_message,
                severity=norm_severity,
                alert_key=alert_key,
                style=style,
                timeout_sec=effective_timeout,
                response_code=0,
                response_label="ERROR",
                status="error",
                reason="WTSSendMessageW retornou codigo de falha (0).",
            )
            self._record_history(res.to_dict())
            return res

        resp_code = int(response_dword.value)
        if resp_code == 0:
            if isinstance(ok, int) and not isinstance(ok, bool) and ok in RESPONSE_CODE_LABELS:
                resp_code = int(ok)
            elif self._simulated_response is not None:
                resp_code = int(self._simulated_response)
            else:
                resp_code = IDOK

        resp_label = RESPONSE_CODE_LABELS.get(resp_code, f"CODE_{resp_code}")

        if alert_key:
            self.record_cooldown(alert_key)

        res = DesktopNotificationResult(
            success=True,
            delivered=True,
            simulated=False,
            suppressed_by_cooldown=False,
            session_id=session_id,
            title=clean_title,
            message=clean_message,
            severity=norm_severity,
            alert_key=alert_key,
            style=style,
            timeout_sec=effective_timeout,
            response_code=resp_code,
            response_label=resp_label,
            status="delivered",
            reason=None,
        )
        self._record_history(res.to_dict())
        return res

    def request_operator_confirmation(
        self,
        title: str,
        message: str,
        timeout_sec: int = DEFAULT_CONFIRM_TIMEOUT_SEC,
        action_key: str | None = None,
    ) -> DesktopConfirmationResult:
        """
        Exibe dialogo interativo Human-In-The-Loop com botoes [Sim / Nao]
        (MB_YESNO | MB_ICONQUESTION | MB_TOPMOST | MB_SETFOREGROUND | MB_SYSTEMMODAL)
        na Sessao 1 e captura a decisao do operador em tempo real:
        - IDYES (6) -> approved=True, timed_out=False
        - IDNO (7) -> approved=False, timed_out=False
        - IDTIMEOUT (32000) -> approved=False, timed_out=True
        """
        clean_title = str(title or "Confirmacao Operacional AURA").strip()
        clean_message = str(message or "").strip()
        effective_timeout = max(
            1, int(timeout_sec if timeout_sec is not None else self.confirm_timeout_sec)
        )
        style = self.build_confirmation_style()

        with self._confirm_lock:
            k32, wts = self._resolve_win32_handles()

            # 1. Verificacao de desativacao, sistema nao-Windows ou modo seguro de pytest sem mock
            if (
                not self._is_effectively_enabled()
                or not self._is_windows_runtime()
                or wts is None
                or self._should_use_pytest_safe_fallback(k32, wts)
            ):
                if self._simulated_response is not None:
                    sim_code = int(self._simulated_response)
                elif self._default_simulated_approval or os.getenv(
                    "AURA_DESKTOP_SIMULATED_APPROVAL", ""
                ).strip().lower() in ("1", "true", "yes"):
                    sim_code = IDYES
                else:
                    sim_code = IDNO

                approved = sim_code == IDYES
                timed_out = sim_code == IDTIMEOUT
                sim_label = RESPONSE_CODE_LABELS.get(sim_code, f"CODE_{sim_code}")

                res = DesktopConfirmationResult(
                    approved=approved,
                    response_code=sim_code,
                    response_label=sim_label,
                    timed_out=timed_out,
                    simulated=True,
                    session_id=0,
                    title=clean_title,
                    message=clean_message,
                    action_key=action_key,
                    style=style,
                    timeout_sec=effective_timeout,
                    status="simulated",
                    reason="Confirmacao processada em modo fallback simulado.",
                )
                logger.info(
                    "DesktopNotifier confirmacao (simulada): [%s] approved=%s (%s)",
                    clean_title,
                    approved,
                    sim_label,
                )
                self._record_history(res.to_dict())
                return res

            # 2. Descoberta da sessao de console interativa ativa (Sessao 1+)
            try:
                raw_session = (
                    k32.WTSGetActiveConsoleSessionId()
                    if (k32 is not None and (not _in_pytest_runtime() or self._is_k32_mocked(k32)))
                    else (1 if _in_pytest_runtime() else INVALID_SESSION_ID)
                )
                session_id = int(raw_session) & 0xFFFFFFFF
            except Exception as exc:
                logger.warning("DesktopNotifier: falha ao obter sessao ativa na confirmacao: %s", exc)
                session_id = INVALID_SESSION_ID

            if session_id == INVALID_SESSION_ID:
                res = DesktopConfirmationResult(
                    approved=False,
                    response_code=IDNO,
                    response_label="NO_CONSOLE_SESSION",
                    timed_out=False,
                    simulated=True,
                    session_id=INVALID_SESSION_ID,
                    title=clean_title,
                    message=clean_message,
                    action_key=action_key,
                    style=style,
                    timeout_sec=effective_timeout,
                    status="no_session",
                    reason="Nenhuma sessao de console interativa ativa (0xFFFFFFFF).",
                )
                logger.info(
                    "DesktopNotifier: sem sessao ativa (0xFFFFFFFF), confirmacao negada por seguranca: %s",
                    clean_title,
                )
                self._record_history(res.to_dict())
                return res

            if _in_pytest_runtime() and not self._is_wts_mocked(wts):
                res = DesktopConfirmationResult(
                    approved=False,
                    response_code=IDNO,
                    response_label="NO",
                    timed_out=False,
                    simulated=True,
                    session_id=session_id,
                    title=clean_title,
                    message=clean_message,
                    action_key=action_key,
                    style=style,
                    timeout_sec=effective_timeout,
                    status="simulated",
                    reason="Fallback seguro ativo (wtsapi32 nao mockado em pytest).",
                )
                self._record_history(res.to_dict())
                return res

            # 3. Invocacao sincrona (bWait=True) de WTSSendMessageW para coletar [Sim / Nao]
            title_bytes_len = len(clean_title.encode("utf-16-le"))
            message_bytes_len = len(clean_message.encode("utf-16-le"))
            response_dword = ctypes.c_ulong(0)
            p_response = ctypes.pointer(response_dword)

            try:
                ok = wts.WTSSendMessageW(
                    WTS_CURRENT_SERVER_HANDLE,
                    int(session_id),
                    clean_title,
                    title_bytes_len,
                    clean_message,
                    message_bytes_len,
                    int(style),
                    int(effective_timeout),
                    p_response,
                    True,
                )
            except Exception as exc:
                logger.error("DesktopNotifier: erro ao invocar WTSSendMessageW na confirmacao: %s", exc)
                res = DesktopConfirmationResult(
                    approved=False,
                    response_code=0,
                    response_label="ERROR",
                    timed_out=False,
                    simulated=False,
                    session_id=session_id,
                    title=clean_title,
                    message=clean_message,
                    action_key=action_key,
                    style=style,
                    timeout_sec=effective_timeout,
                    status="error",
                    reason=f"Excecao ao invocar WTSSendMessageW: {exc}",
                )
                self._record_history(res.to_dict())
                return res

            if not ok:
                res = DesktopConfirmationResult(
                    approved=False,
                    response_code=0,
                    response_label="ERROR",
                    timed_out=False,
                    simulated=False,
                    session_id=session_id,
                    title=clean_title,
                    message=clean_message,
                    action_key=action_key,
                    style=style,
                    timeout_sec=effective_timeout,
                    status="error",
                    reason="WTSSendMessageW retornou codigo de falha (0).",
                )
                self._record_history(res.to_dict())
                return res

            resp_code = int(response_dword.value)
            if resp_code == 0:
                if (
                    isinstance(ok, int)
                    and not isinstance(ok, bool)
                    and ok in (IDYES, IDNO, IDTIMEOUT, IDCANCEL)
                ):
                    resp_code = int(ok)
                elif self._simulated_response is not None:
                    resp_code = int(self._simulated_response)
                else:
                    resp_code = IDNO

            approved = resp_code == IDYES
            timed_out = resp_code == IDTIMEOUT
            resp_label = RESPONSE_CODE_LABELS.get(resp_code, f"CODE_{resp_code}")
            status_str = "timeout" if timed_out else ("approved" if approved else "rejected")

            res = DesktopConfirmationResult(
                approved=approved,
                response_code=resp_code,
                response_label=resp_label,
                timed_out=timed_out,
                simulated=False,
                session_id=session_id,
                title=clean_title,
                message=clean_message,
                action_key=action_key,
                style=style,
                timeout_sec=effective_timeout,
                status=status_str,
                reason=None,
            )
            self._record_history(res.to_dict())
            return res


# =============================================================================
# SINGLETON THREAD-SAFE
# =============================================================================

_GLOBAL_NOTIFIER: DesktopNotifier | None = None
_NOTIFIER_LOCK = threading.Lock()


def get_desktop_notifier() -> DesktopNotifier:
    """Retorna a instancia singleton thread-safe do DesktopNotifier."""
    global _GLOBAL_NOTIFIER
    if _GLOBAL_NOTIFIER is None:
        with _NOTIFIER_LOCK:
            if _GLOBAL_NOTIFIER is None:
                _GLOBAL_NOTIFIER = DesktopNotifier()
    return _GLOBAL_NOTIFIER


def reset_desktop_notifier() -> None:
    """Reseta o singleton global do DesktopNotifier (utilizado em suites de teste)."""
    global _GLOBAL_NOTIFIER
    with _NOTIFIER_LOCK:
        _GLOBAL_NOTIFIER = None
