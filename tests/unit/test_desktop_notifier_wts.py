"""
Testes Unitarios da Fase 4 (Roadmap Sentinel-AURA):
Notificador Desktop HITL Sessao 0 para Sessao 1 (WTSSendMessageW).

Valida:
1. Invocacao nativa de WTSSendMessageW (wtsapi32) e WTSGetActiveConsoleSessionId (kernel32)
   com flags MB_TOPMOST (0x00040000), MB_SETFOREGROUND (0x00010000) e MB_SYSTEMMODAL (0x00001000).
2. Captura de respostas HITL [Sim / Nao]: IDYES (6), IDNO (7) e IDTIMEOUT (32000).
3. Controle de deduplicacao e cooldown anti-spam de alertas no caixa.
4. Fallback seguro quando session_id == 0xFFFFFFFF (sem operador logado), Linux/CI,
   pytest sem mock ou AURA_DESKTOP_NOTIFY_ENABLED=false.
5. Integracao com AuraProactiveDaemon para sangrias urgentes e tanques criticos.
6. Endpoints FastAPI (/api/v1/aura/desktop/notify, /confirm e /history).
7. Ausencia estrita de travessoes (\\u2014, \\u2013) em todo o codigo e documentacao da Fase 4.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from core.aura_api import create_aura_app, set_desktop_notifier
from core.aura_engine import AuraEngine, AuraSessionMemory
from core.desktop_notifier import (
    IDNO,
    IDOK,
    IDTIMEOUT,
    IDYES,
    INVALID_SESSION_ID,
    MB_ICONERROR,
    MB_ICONINFORMATION,
    MB_ICONQUESTION,
    MB_ICONWARNING,
    MB_SETFOREGROUND,
    MB_SYSTEMMODAL,
    MB_TOPMOST,
    MB_YESNO,
    WTS_CURRENT_SERVER_HANDLE,
    DesktopConfirmationResult,
    DesktopNotificationResult,
    DesktopNotifier,
    get_desktop_notifier,
    reset_desktop_notifier,
)
from core.proactive_daemon import AuraProactiveDaemon


@pytest.fixture(autouse=True)
def _clean_notifier_singleton() -> Any:
    """Garante isolamento do singleton global entre cada teste."""
    reset_desktop_notifier()
    set_desktop_notifier(None)
    yield
    reset_desktop_notifier()
    set_desktop_notifier(None)


def _make_wts_mocks(
    session_id: int = 1,
    response_code: int = IDOK,
    call_ok: int = 1,
) -> tuple[MagicMock, MagicMock]:
    """Cria mocks configurados de kernel32 e wtsapi32 simulando o Windows Terminal Services."""
    mock_k32 = MagicMock()
    mock_k32.WTSGetActiveConsoleSessionId.return_value = session_id

    mock_wts = MagicMock()

    def _side_effect(
        h_server: int,
        sess_id: int,
        p_title: str,
        title_len: int,
        p_msg: str,
        msg_len: int,
        style: int,
        timeout: int,
        p_response: Any,
        b_wait: bool,
    ) -> int:
        if call_ok and p_response is not None:
            p_response.contents.value = response_code
        return call_ok

    mock_wts.WTSSendMessageW.side_effect = _side_effect
    return mock_k32, mock_wts


# =============================================================================
# 1. INVOCACAO WIN32 WTSSendMessageW E FLAGS TOPMOST / SYSTEMMODAL
# =============================================================================


class TestWTSSendMessageInvocation:
    """Testa invocacao de WTSGetActiveConsoleSessionId e WTSSendMessageW via mocks."""

    def test_notify_operator_invokes_wts_on_session_1_with_topmost_flags(self) -> None:
        """Verifica que notify_operator descobre a Sessao 1 e chama WTSSendMessageW com as flags corretas."""
        mock_k32, mock_wts = _make_wts_mocks(session_id=1, response_code=IDOK)
        notifier = DesktopNotifier(
            force_os="nt",
            kernel32=mock_k32,
            wtsapi32=mock_wts,
            cooldown_sec=300.0,
        )

        title = "Alerta de Sangria Urgente"
        message = "Caixa 01 acumula R$ 2.850,00 em especie. Realize sangria imediata."
        res = notifier.notify_operator(
            title=title,
            message=message,
            severity="critical",
            timeout_sec=20,
            alert_key="SANGRIA:POSTO_01:CX01",
        )

        assert isinstance(res, DesktopNotificationResult)
        assert res.success is True
        assert res.delivered is True
        assert res.simulated is False
        assert res.suppressed_by_cooldown is False
        assert res.session_id == 1
        assert res.response_code == IDOK
        assert res.response_label == "OK"

        mock_k32.WTSGetActiveConsoleSessionId.assert_called_once()
        mock_wts.WTSSendMessageW.assert_called_once()

        call_args = mock_wts.WTSSendMessageW.call_args[0]
        assert call_args[0] == WTS_CURRENT_SERVER_HANDLE
        assert call_args[1] == 1  # SessionId
        assert call_args[2] == title
        assert call_args[3] == len(title.encode("utf-16-le"))
        assert call_args[4] == message
        assert call_args[5] == len(message.encode("utf-16-le"))

        style = call_args[6]
        assert (style & MB_TOPMOST) == MB_TOPMOST
        assert (style & MB_SETFOREGROUND) == MB_SETFOREGROUND
        assert (style & MB_SYSTEMMODAL) == MB_SYSTEMMODAL
        assert (style & MB_ICONERROR) == MB_ICONERROR

        assert call_args[7] == 20  # Timeout
        assert call_args[9] is True  # bWait

    def test_severity_icon_mapping(self) -> None:
        """Valida que cada nivel de severidade mapeia para o icone Win32 correspondente."""
        style_info = DesktopNotifier.build_notification_style("info")
        assert (style_info & MB_ICONINFORMATION) == MB_ICONINFORMATION
        assert (style_info & MB_TOPMOST) == MB_TOPMOST

        style_warn = DesktopNotifier.build_notification_style("warning")
        assert (style_warn & MB_ICONWARNING) == MB_ICONWARNING
        assert (style_warn & MB_SETFOREGROUND) == MB_SETFOREGROUND

        style_crit = DesktopNotifier.build_notification_style("critical")
        assert (style_crit & MB_ICONERROR) == MB_ICONERROR
        assert (style_crit & MB_SYSTEMMODAL) == MB_SYSTEMMODAL

    def test_wts_failure_returns_graceful_error_result(self) -> None:
        """Se WTSSendMessageW retornar 0 ou lancar OSError, nao deve propagar excecao."""
        mock_k32, mock_wts = _make_wts_mocks(session_id=2, response_code=0, call_ok=0)
        notifier = DesktopNotifier(force_os="nt", kernel32=mock_k32, wtsapi32=mock_wts)

        res = notifier.notify_operator("Titulo", "Mensagem de teste")
        assert res.success is False
        assert res.delivered is False
        assert res.status == "error"

        # Simula OSError na chamada ctypes
        mock_wts.WTSSendMessageW.side_effect = OSError("Falha de RPC no servico WTS")
        res_exc = notifier.notify_operator("Titulo 2", "Mensagem 2")
        assert res_exc.success is False
        assert res_exc.delivered is False
        assert res_exc.status == "error"
        assert "Falha de RPC" in (res_exc.reason or "")


# =============================================================================
# 2. RESPOSTAS HITL [SIM / NAO]: IDYES (6), IDNO (7) E IDTIMEOUT (32000)
# =============================================================================


class TestHITLOperatorConfirmation:
    """Testa captura das respostas do operador: IDYES (6), IDNO (7) e IDTIMEOUT (32000)."""

    def test_confirmation_approved_on_idyes(self) -> None:
        """Quando o operador clica em [Sim] (IDYES = 6), approved deve ser True."""
        mock_k32, mock_wts = _make_wts_mocks(session_id=1, response_code=IDYES)
        notifier = DesktopNotifier(force_os="nt", kernel32=mock_k32, wtsapi32=mock_wts)

        res = notifier.request_operator_confirmation(
            title="Confirmar Pedido de Combustivel",
            message="Autorizar compra de 15.000 L de Gasolina Comum?",
            timeout_sec=30,
            action_key="act_fuel_order_01",
        )

        assert isinstance(res, DesktopConfirmationResult)
        assert res.approved is True
        assert res.response_code == IDYES
        assert res.response_label == "YES"
        assert res.timed_out is False
        assert res.simulated is False
        assert res.session_id == 1
        assert res.status == "approved"

        call_args = mock_wts.WTSSendMessageW.call_args[0]
        style = call_args[6]
        assert (style & MB_YESNO) == MB_YESNO
        assert (style & MB_ICONQUESTION) == MB_ICONQUESTION
        assert (style & MB_TOPMOST) == MB_TOPMOST
        assert (style & MB_SETFOREGROUND) == MB_SETFOREGROUND
        assert (style & MB_SYSTEMMODAL) == MB_SYSTEMMODAL
        assert call_args[7] == 30
        assert call_args[9] is True

    def test_confirmation_rejected_on_idno(self) -> None:
        """Quando o operador clica em [Nao] (IDNO = 7), approved deve ser False."""
        mock_k32, mock_wts = _make_wts_mocks(session_id=1, response_code=IDNO)
        notifier = DesktopNotifier(force_os="nt", kernel32=mock_k32, wtsapi32=mock_wts)

        res = notifier.request_operator_confirmation(
            title="Confirmar Repasse de Preco",
            message="Deseja aplicar aumento de R$ 0,10 na Gasolina?",
            timeout_sec=25,
            action_key="act_price_01",
        )

        assert res.approved is False
        assert res.response_code == IDNO
        assert res.response_label == "NO"
        assert res.timed_out is False
        assert res.simulated is False
        assert res.status == "rejected"

    def test_confirmation_rejected_on_idtimeout(self) -> None:
        """Quando o dialogo expira sem resposta (IDTIMEOUT = 32000), approved=False e timed_out=True."""
        mock_k32, mock_wts = _make_wts_mocks(session_id=1, response_code=IDTIMEOUT)
        notifier = DesktopNotifier(force_os="nt", kernel32=mock_k32, wtsapi32=mock_wts)

        res = notifier.request_operator_confirmation(
            title="Confirmar Fechamento",
            message="Homologar fechamento automatico do turno?",
            timeout_sec=10,
            action_key="act_shift_close",
        )

        assert res.approved is False
        assert res.response_code == IDTIMEOUT
        assert res.response_label == "TIMEOUT"
        assert res.timed_out is True
        assert res.simulated is False
        assert res.status == "timeout"


# =============================================================================
# 3. DEDUPLICACAO E COOLDOWN ANTI-SPAM NO CAIXA
# =============================================================================


class TestDesktopNotifierCooldown:
    """Testa bloqueio de popups repetidos dentro da janela de cooldown."""

    def test_cooldown_suppresses_repeated_alert_key(self) -> None:
        """Disparos consecutivos com o mesmo alert_key devem ser suprimidos sem chamar WTSSendMessageW."""
        mock_k32, mock_wts = _make_wts_mocks(session_id=1, response_code=IDOK)
        notifier = DesktopNotifier(
            force_os="nt",
            kernel32=mock_k32,
            wtsapi32=mock_wts,
            cooldown_sec=300.0,
        )

        # 1o disparo: entregue ao desktop
        r1 = notifier.notify_operator(
            title="Tanque 01 Critico",
            message="Saldo abaixo de 10%",
            alert_key="TANQUE_01",
        )
        assert r1.delivered is True
        assert r1.suppressed_by_cooldown is False
        assert mock_wts.WTSSendMessageW.call_count == 1

        # 2o disparo imediato com mesma chave: suprimido
        r2 = notifier.notify_operator(
            title="Tanque 01 Critico",
            message="Saldo abaixo de 10%",
            alert_key="TANQUE_01",
        )
        assert r2.delivered is False
        assert r2.suppressed_by_cooldown is True
        assert r2.suppressed is True
        assert r2.status == "cooldown_suppressed"
        assert mock_wts.WTSSendMessageW.call_count == 1

        # Chave diferente: entregue normalmente
        r3 = notifier.notify_operator(
            title="Tanque 02 Critico",
            message="Saldo abaixo de 15%",
            alert_key="TANQUE_02",
        )
        assert r3.delivered is True
        assert r3.suppressed_by_cooldown is False
        assert mock_wts.WTSSendMessageW.call_count == 2

        # Limpeza do cooldown de TANQUE_01 permite novo envio
        notifier.clear_cooldown("TANQUE_01")
        r4 = notifier.notify_operator(
            title="Tanque 01 Critico",
            message="Saldo abaixo de 8%",
            alert_key="TANQUE_01",
        )
        assert r4.delivered is True
        assert mock_wts.WTSSendMessageW.call_count == 3

    def test_concurrent_cooldown_prevents_toctou_duplicate_popups(self) -> None:
        """Multiplas threads disparando o mesmo alert_key simultaneamente nao devem duplicar popups."""
        import threading
        import time

        mock_k32 = MagicMock()
        mock_k32.WTSGetActiveConsoleSessionId.return_value = 1
        mock_wts = MagicMock()

        def _slow_wts(
            h_server: int,
            sess_id: int,
            p_title: str,
            title_len: int,
            p_msg: str,
            msg_len: int,
            style: int,
            timeout: int,
            p_response: Any,
            b_wait: bool,
        ) -> int:
            time.sleep(0.05)
            if p_response is not None:
                p_response.contents.value = IDOK
            return 1

        mock_wts.WTSSendMessageW.side_effect = _slow_wts
        notifier = DesktopNotifier(
            force_os="nt",
            kernel32=mock_k32,
            wtsapi32=mock_wts,
            cooldown_sec=300.0,
        )

        results: list[DesktopNotificationResult] = []
        lock = threading.Lock()
        barrier = threading.Barrier(5)

        def _worker() -> None:
            barrier.wait()
            res = notifier.notify_operator(
                title="Sangria Concorrente",
                message="Caixa 01 acima do limite",
                alert_key="CONC_SANGRIA_CX01",
            )
            with lock:
                results.append(res)

        threads = [threading.Thread(target=_worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 5
        delivered_count = sum(1 for r in results if r.delivered)
        suppressed_count = sum(1 for r in results if r.suppressed_by_cooldown)
        assert delivered_count == 1
        assert suppressed_count == 4
        assert mock_wts.WTSSendMessageW.call_count == 1

    def test_failed_wts_or_no_session_rolls_back_cooldown(self) -> None:
        """Se WTSSendMessageW falhar ou nao houver sessao (0xFFFFFFFF), o cooldown nao deve bloquear nova tentativa."""
        mock_k32, mock_wts = _make_wts_mocks(session_id=INVALID_SESSION_ID, response_code=IDOK)
        notifier = DesktopNotifier(
            force_os="nt",
            kernel32=mock_k32,
            wtsapi32=mock_wts,
            cooldown_sec=300.0,
        )

        # 1. Sem sessao ativa (0xFFFFFFFF) -> nao deve reter cooldown
        r1 = notifier.notify_operator("Alerta", "Sem sessao", alert_key="KEY_RETRY")
        assert r1.status == "no_session"
        assert notifier.is_in_cooldown("KEY_RETRY") is False

        # 2. Operador faz login (session_id=1), mas WTS falha na 1a tentativa (call_ok=0)
        mock_k32.WTSGetActiveConsoleSessionId.return_value = 1
        mock_wts.WTSSendMessageW.side_effect = None
        mock_wts.WTSSendMessageW.return_value = 0
        r2 = notifier.notify_operator("Alerta", "Falha WTS", alert_key="KEY_RETRY")
        assert r2.status == "error"
        assert notifier.is_in_cooldown("KEY_RETRY") is False

        # 3. WTS recupera -> entrega com sucesso e registra cooldown
        _, mock_wts_ok = _make_wts_mocks(session_id=1, response_code=IDOK, call_ok=1)
        notifier.wtsapi32 = mock_wts_ok
        r3 = notifier.notify_operator("Alerta", "Sucesso WTS", alert_key="KEY_RETRY")
        assert r3.delivered is True
        assert notifier.is_in_cooldown("KEY_RETRY") is True


# =============================================================================
# 4. FALLBACK SEGURO (SEM SESSAO ATIVA 0xFFFFFFFF, LINUX/CI, DESABILITADO)
# =============================================================================


class TestHeadlessAndSessionZeroFallbacks:
    """Testa seguranca operacional quando nao ha operador logado ou fora do Windows."""

    def test_fallback_when_no_active_console_session_0xffffffff(self) -> None:
        """Quando WTSGetActiveConsoleSessionId retorna 0xFFFFFFFF, nao chama WTSSendMessageW."""
        mock_k32, mock_wts = _make_wts_mocks(session_id=INVALID_SESSION_ID)
        notifier = DesktopNotifier(force_os="nt", kernel32=mock_k32, wtsapi32=mock_wts)

        res_notify = notifier.notify_operator("Alerta Sem Sessao", "Ninguem logado no console")
        assert res_notify.success is True
        assert res_notify.delivered is False
        assert res_notify.simulated is True
        assert res_notify.session_id == INVALID_SESSION_ID
        assert res_notify.status == "no_session"
        mock_wts.WTSSendMessageW.assert_not_called()

        res_confirm = notifier.request_operator_confirmation(
            "Confirmacao Sem Sessao", "Aprovar pedido?"
        )
        assert res_confirm.approved is False
        assert res_confirm.simulated is True
        assert res_confirm.session_id == INVALID_SESSION_ID
        assert res_confirm.status == "no_session"
        mock_wts.WTSSendMessageW.assert_not_called()

    def test_signed_minus_one_normalized_to_0xffffffff(self) -> None:
        """Retorno -1 (signed 32-bit c_int) de WTSGetActiveConsoleSessionId deve ser tratado como 0xFFFFFFFF."""
        mock_k32, mock_wts = _make_wts_mocks(session_id=-1)
        notifier = DesktopNotifier(force_os="nt", kernel32=mock_k32, wtsapi32=mock_wts)

        assert notifier.get_active_console_session_id() == INVALID_SESSION_ID
        res = notifier.notify_operator("Teste -1", "Mensagem")
        assert res.session_id == INVALID_SESSION_ID
        assert res.simulated is True
        mock_wts.WTSSendMessageW.assert_not_called()

    def test_linux_non_windows_fallback(self) -> None:
        """Em sistemas nao-Windows (force_os='posix'), opera em modo simulado sem erro."""
        notifier = DesktopNotifier(force_os="posix")

        res_n = notifier.notify_operator("Alerta Linux", "Rodando em container CI")
        assert res_n.success is True
        assert res_n.simulated is True
        assert res_n.status == "simulated"

        res_c = notifier.request_operator_confirmation("Confirmacao Linux", "Aprovar?")
        assert res_c.approved is False
        assert res_c.simulated is True
        assert res_c.status == "simulated"

    def test_monkeypatch_os_name_posix_triggers_fallback_on_windows(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Quando os.name != 'nt' via monkeypatch (sem force_os), deve operar em modo fallback simulado."""
        import os as _os

        monkeypatch.setattr(_os, "name", "posix")
        mock_k32, mock_wts = _make_wts_mocks(session_id=1, response_code=IDOK)
        notifier = DesktopNotifier(kernel32=mock_k32, wtsapi32=mock_wts)

        res = notifier.notify_operator("Alerta OS Posix", "Teste os.name != nt")
        assert res.simulated is True
        assert res.delivered is False
        assert res.status == "simulated"
        mock_wts.WTSSendMessageW.assert_not_called()

    def test_custom_simplenamespace_and_lambda_win32_stubs_detected(self) -> None:
        """Objetos SimpleNamespace e funcoes lambda devem ser reconhecidos como doubles validos sob pytest."""
        from types import SimpleNamespace

        calls: list[int] = []

        def _custom_send(
            h_server: int,
            sess_id: int,
            p_title: str,
            title_len: int,
            p_msg: str,
            msg_len: int,
            style: int,
            timeout: int,
            p_response: Any,
            b_wait: bool,
        ) -> int:
            calls.append(sess_id)
            if p_response is not None:
                p_response.contents.value = IDYES
            return 1

        k32_ns = SimpleNamespace(WTSGetActiveConsoleSessionId=lambda: 3)
        wts_ns = SimpleNamespace(WTSSendMessageW=_custom_send)
        notifier = DesktopNotifier(force_os="nt", kernel32=k32_ns, wtsapi32=wts_ns)

        res = notifier.request_operator_confirmation("Confirmacao Lambda", "Autorizar?")
        assert res.approved is True
        assert res.simulated is False
        assert res.session_id == 3
        assert calls == [3]

    def test_disabled_via_env_variable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Quando AURA_DESKTOP_NOTIFY_ENABLED=false, opera em fallback desabilitado."""
        monkeypatch.setenv("AURA_DESKTOP_NOTIFY_ENABLED", "false")
        mock_k32, mock_wts = _make_wts_mocks(session_id=1)
        notifier = DesktopNotifier(force_os="nt", kernel32=mock_k32, wtsapi32=mock_wts)

        res = notifier.notify_operator("Alerta Desativado", "Teste env")
        assert res.simulated is True
        assert res.delivered is False
        assert res.status == "disabled"
        mock_wts.WTSSendMessageW.assert_not_called()

    def test_core_lazy_exports_and_singleton(self) -> None:
        """Verifica exportacoes PEP 562 em core/__init__.py e singleton get_desktop_notifier."""
        import core

        assert core.DesktopNotifier is DesktopNotifier
        assert core.get_desktop_notifier is get_desktop_notifier
        assert core.DesktopNotificationResult is DesktopNotificationResult
        assert core.DesktopConfirmationResult is DesktopConfirmationResult

        n1 = get_desktop_notifier()
        n2 = get_desktop_notifier()
        assert n1 is n2


# =============================================================================
# 5. INTEGRACAO COM AuraProactiveDaemon E ENDPOINTS FASTAPI
# =============================================================================


class TestDaemonAndFastAPIIntegration:
    """Testa integracao com AuraProactiveDaemon e endpoints HTTP FastAPI."""

    @pytest.mark.asyncio
    async def test_proactive_daemon_triggers_desktop_notifier_on_critical_alerts(self) -> None:
        """AuraProactiveDaemon deve acionar DesktopNotifier para tanque critico e sangria urgente."""
        mock_k32, mock_wts = _make_wts_mocks(session_id=1, response_code=IDOK)
        notifier = DesktopNotifier(
            force_os="nt",
            kernel32=mock_k32,
            wtsapi32=mock_wts,
            cooldown_sec=300.0,
        )

        daemon = AuraProactiveDaemon(
            db_path=":memory:",
            filial_id="posto_01",
            dispatch_enabled=False,
            desktop_notifier=notifier,
        )

        tanques = [
            {
                "tanque_id": "TQ-01",
                "combustivel": "GASOLINA COMUM",
                "capacidade_total_litros": 20000.0,
                "volume_atual_litros": 1500.0,  # 7.5% -> CRITICAL
                "autonomia_horas": 6.0,
            }
        ]
        caixas = [
            {
                "caixa_id": "CX-01",
                "saldo_dinheiro": 3200.0,
                "minutos_sem_sangria": 95,
                "operador": "Operador Turno",
            }
        ]

        alerts = await daemon.evaluate_rules(tanques=tanques, caixas=caixas)
        assert len(alerts) == 2
        assert mock_wts.WTSSendMessageW.call_count == 2

        for alert in alerts:
            assert "desktop_notifier" in alert.dispatch_results
            assert alert.dispatch_results["desktop_notifier"]["delivered"] is True
            assert alert.dispatch_results["desktop_notifier"]["session_id"] == 1

        history = notifier.get_history(limit=10)
        assert len(history) == 2

    def test_fastapi_desktop_notify_confirm_and_history_endpoints(self) -> None:
        """Valida POST /desktop/notify, POST /desktop/confirm e GET /desktop/history."""
        mock_k32, mock_wts = _make_wts_mocks(session_id=1, response_code=IDYES)
        notifier = DesktopNotifier(
            force_os="nt",
            kernel32=mock_k32,
            wtsapi32=mock_wts,
            cooldown_sec=300.0,
        )

        mem = AuraSessionMemory(db_path=":memory:")
        engine = AuraEngine(session_memory=mem)
        # Instancia daemon sem passar desktop_notifier explicitamente para validar sincronizacao em create_aura_app
        daemon = AuraProactiveDaemon(
            db_path=":memory:",
            dispatch_enabled=False,
        )
        app = create_aura_app(engine=engine, daemon=daemon, desktop_notifier=notifier)
        assert daemon.desktop_notifier is notifier
        client = TestClient(app)

        # 1. POST /api/v1/aura/desktop/notify
        resp_notify = client.post(
            "/api/v1/aura/desktop/notify",
            json={
                "title": "Sangria Urgente Caixa 02",
                "message": "Saldo em gaveta acima do limite de seguranca.",
                "severity": "critical",
                "timeout_sec": 15,
                "alert_key": "API_SANGRIA_CX02",
            },
        )
        assert resp_notify.status_code == 200
        data_notify = resp_notify.json()
        assert data_notify["success"] is True
        assert data_notify["delivered"] is True
        assert data_notify["session_id"] == 1
        assert data_notify["alert_key"] == "API_SANGRIA_CX02"

        # 2. POST /api/v1/aura/desktop/confirm
        resp_confirm = client.post(
            "/api/v1/aura/desktop/confirm",
            json={
                "title": "Aprovar Compra de Diesel S10",
                "message": "Confirmar pedido de 10.000 L de Diesel S10?",
                "timeout_sec": 30,
                "action_key": "API_PEDIDO_DIESEL",
            },
        )
        assert resp_confirm.status_code == 200
        data_confirm = resp_confirm.json()
        assert data_confirm["approved"] is True
        assert data_confirm["response_code"] == IDYES
        assert data_confirm["response_label"] == "YES"
        assert data_confirm["timed_out"] is False

        # 3. GET /api/v1/aura/desktop/history
        resp_hist = client.get("/api/v1/aura/desktop/history?limit=10")
        assert resp_hist.status_code == 200
        data_hist = resp_hist.json()
        assert data_hist["total"] == 2
        assert len(data_hist["history"]) == 2

        # Filtro por event_type=confirmation
        resp_hist_conf = client.get("/api/v1/aura/desktop/history?event_type=confirmation")
        assert resp_hist_conf.status_code == 200
        assert resp_hist_conf.json()["total"] == 1
        assert resp_hist_conf.json()["history"][0]["action_key"] == "API_PEDIDO_DIESEL"


# =============================================================================
# 6. VERIFICACAO DE ZERO TRAVESSOES
# =============================================================================


class TestPhase4ZeroDashes:
    """Valida ausencia estrita de travessoes proibidos (\\u2014, \\u2013) nos arquivos da Fase 4."""

    def test_zero_prohibited_dashes_in_phase_4_files(self) -> None:
        base_dir = Path(__file__).resolve().parent.parent.parent
        phase4_files = [
            base_dir / "core" / "desktop_notifier.py",
            base_dir / "core" / "proactive_daemon.py",
            base_dir / "core" / "aura_api.py",
            base_dir / "core" / "__init__.py",
            base_dir / "ROADMAP_SENTINEL_AURA.md",
            base_dir / "docs" / "ROADMAP_SENTINEL_AURA.md",
            base_dir / "tests" / "unit" / "test_desktop_notifier_wts.py",
        ]

        prohibited_bytes = [b"\xe2\x80\x94", b"\xe2\x80\x93"]

        for file_path in phase4_files:
            assert file_path.exists(), f"Arquivo esperado nao encontrado: {file_path}"
            content = file_path.read_bytes()
            for bad in prohibited_bytes:
                assert bad not in content, (
                    f"Arquivo {file_path.name} contem travessao proibido ({bad!r})!"
                )
