"""
Testes Unitarios da Fase 3 (Roadmap Sentinel-AURA):
Hardware Circuit Breaker para PDV do Caixa & Protecao de Hardware Local.

Valida:
1. Leitura nativa de metricas de CPU e RAM no Windows via ctypes e fallback defensivo Linux/CI.
2. Maquina de estados do Circuit Breaker (CLOSED -> OPEN -> HALF_OPEN -> CLOSED).
3. Teste de cooldown com histerese e retentativa controlada.
4. Integracao com AuraEngine (execute_tool_direct, ask_stream e ask com degradacao graciosa).
5. Integracao com AuraProactiveDaemon (bloqueio do ciclo em estado OPEN e exposicao de status).
6. Ausencia total de travessoes (\\u2014, \\u2013) em todo o codigo e documentacao da Fase 3.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from core.aura_engine import (
    AuraChunkType,
    AuraEngine,
)
from core.proactive_daemon import AuraProactiveDaemon
from core.resource_watchdog import (
    CircuitState,
    HardwareCircuitBreaker,
    get_resource_watchdog,
    reset_resource_watchdog,
)


@pytest.fixture(autouse=True)
def _clean_watchdog_state() -> Any:
    """Garante isolamento de estado entre testes resetando o singleton do watchdog."""
    reset_resource_watchdog()
    yield
    reset_resource_watchdog()


@pytest.fixture
def test_watchdog() -> HardwareCircuitBreaker:
    """Instancia isolada do HardwareCircuitBreaker com cooldown curto para testes."""
    return HardwareCircuitBreaker(
        max_cpu_percent=80.0,
        max_ram_percent=85.0,
        cooldown_sec=0.1,
    )


# =============================================================================
# 1. LEITURA DE MÉTRICAS NATIVAS WIN32 E FALLBACK LINUX/CI
# =============================================================================


class TestHardwareMetricsCollection:
    """Testa coleta de CPU e RAM via Win32 ctypes e fallback defensivo."""

    def test_read_metrics_live_system(self, test_watchdog: HardwareCircuitBreaker) -> None:
        """Verifica que a amostragem em tempo real retorna valores coerentes."""
        metrics = test_watchdog.get_system_metrics()
        assert "cpu_percent" in metrics
        assert "ram_percent" in metrics
        assert "ram_available_mb" in metrics
        assert "circuit_state" in metrics
        assert metrics["cpu_percent"] >= 0.0
        assert metrics["ram_percent"] >= 0.0
        assert metrics["circuit_state"] in ("CLOSED", "OPEN", "HALF_OPEN")

    def test_linux_fallback_mode(self) -> None:
        """Verifica que a execucao forçada em modo Linux/fallback nao gera excecoes."""
        wb = HardwareCircuitBreaker(force_os="linux", cooldown_sec=1.0)
        metrics = wb.get_system_metrics()
        assert metrics["is_windows"] is False
        assert metrics["cpu_percent"] >= 0.0
        assert metrics["ram_available_mb"] > 0.0
        assert metrics["ram_total_mb"] > 0.0
        assert metrics["circuit_state"] == CircuitState.CLOSED.value

    def test_simulated_metrics_injection(self, test_watchdog: HardwareCircuitBreaker) -> None:
        """Verifica injecao controlada de metricas para testes deterministicos."""
        test_watchdog.set_simulated_metrics(
            cpu_percent=45.5,
            ram_percent=60.2,
            ram_available_mb=3500.0,
            ram_total_mb=8000.0,
        )
        m = test_watchdog.sample(force=True)
        assert m["cpu_percent"] == 45.5
        assert m["ram_percent"] == 60.2
        assert m["ram_available_mb"] == 3500.0
        assert m["ram_total_mb"] == 8000.0

        test_watchdog.clear_simulated_metrics()


# =============================================================================
# 2. TRANSIÇÕES DE ESTADO DO CIRCUIT BREAKER
# =============================================================================


class TestCircuitBreakerStateTransitions:
    """Testa a maquina de estados: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""

    def test_initial_state_is_closed(self, test_watchdog: HardwareCircuitBreaker) -> None:
        """O circuito recem-criado deve iniciar em CLOSED e permitir operacoes pesadas."""
        assert test_watchdog.get_system_metrics()["circuit_state"] == CircuitState.CLOSED.value
        assert test_watchdog.is_heavy_operation_allowed() is True

    def test_transitions_to_open_on_cpu_overload(
        self, test_watchdog: HardwareCircuitBreaker
    ) -> None:
        """Sobrecarga de CPU (> 80%) deve acionar o desarme para OPEN."""
        test_watchdog.set_simulated_metrics(cpu_percent=88.0, ram_percent=40.0)
        test_watchdog.sample(force=True)

        assert test_watchdog.get_system_metrics()["circuit_state"] == CircuitState.OPEN.value
        assert test_watchdog.is_heavy_operation_allowed() is False
        assert test_watchdog.get_system_metrics()["tripped_count"] >= 1

    def test_transitions_to_open_on_ram_overload(
        self, test_watchdog: HardwareCircuitBreaker
    ) -> None:
        """Sobrecarga de RAM (> 85%) deve acionar o desarme para OPEN."""
        test_watchdog.set_simulated_metrics(cpu_percent=20.0, ram_percent=92.0)
        test_watchdog.sample(force=True)

        assert test_watchdog.get_system_metrics()["circuit_state"] == CircuitState.OPEN.value
        assert test_watchdog.is_heavy_operation_allowed() is False

    def test_cooldown_recovery_to_half_open_and_closed(
        self, test_watchdog: HardwareCircuitBreaker
    ) -> None:
        """Apos o cooldown, o circuito transita para HALF_OPEN e em seguida para CLOSED quando normalizado."""
        test_watchdog.set_simulated_metrics(cpu_percent=95.0, ram_percent=50.0)
        test_watchdog.sample(force=True)
        assert test_watchdog.is_heavy_operation_allowed() is False
        assert test_watchdog.get_system_metrics()["circuit_state"] == CircuitState.OPEN.value

        # Normaliza o hardware simulado
        test_watchdog.set_simulated_metrics(cpu_percent=25.0, ram_percent=45.0)

        # Aguarda o cooldown expirar (0.1s configurado no fixture)
        time.sleep(0.12)

        # Estado apos cooldown deve ser HALF_OPEN (testando recuperacao)
        metrics_after_cooldown = test_watchdog.get_system_metrics()
        assert metrics_after_cooldown["circuit_state"] == CircuitState.HALF_OPEN.value

        # Invocacao da operacao deve avaliar a recuperacao e transitar HALF_OPEN -> CLOSED
        allowed = test_watchdog.is_heavy_operation_allowed()
        assert allowed is True
        assert test_watchdog.get_system_metrics()["circuit_state"] == CircuitState.CLOSED.value

    def test_cooldown_recovery_re_trips_if_still_overloaded(
        self, test_watchdog: HardwareCircuitBreaker
    ) -> None:
        """Se o cooldown expirar mas o hardware continuar sob estresse, re-desarma para OPEN."""
        test_watchdog.set_simulated_metrics(cpu_percent=90.0, ram_percent=50.0)
        test_watchdog.sample(force=True)
        assert test_watchdog.is_heavy_operation_allowed() is False

        # Mantem o hardware sobrecarregado
        time.sleep(0.12)

        allowed = test_watchdog.is_heavy_operation_allowed()
        assert allowed is False
        assert test_watchdog.get_system_metrics()["circuit_state"] == CircuitState.OPEN.value

    def test_manual_trip_and_reset(self, test_watchdog: HardwareCircuitBreaker) -> None:
        """Verifica metodos operacionais manuais de trip e reset."""
        test_watchdog.trip("teste de seguranca")
        assert test_watchdog.is_heavy_operation_allowed() is False
        m_trip = test_watchdog.get_system_metrics()
        assert m_trip["circuit_state"] == CircuitState.OPEN.value
        assert m_trip["cooldown_remaining_sec"] > 0.0

        test_watchdog.reset()
        assert test_watchdog.is_heavy_operation_allowed() is True
        m_reset = test_watchdog.get_system_metrics()
        assert m_reset["circuit_state"] == CircuitState.CLOSED.value
        assert m_reset["cooldown_remaining_sec"] == 0.0

    def test_set_state_direct(self, test_watchdog: HardwareCircuitBreaker) -> None:
        """Verifica definicao direta de estado e rejeicao de estado invalido."""
        test_watchdog.set_state("HALF_OPEN")
        assert test_watchdog.get_system_metrics()["circuit_state"] == CircuitState.HALF_OPEN.value

        test_watchdog.set_state("CLOSED")
        assert test_watchdog.get_system_metrics()["circuit_state"] == CircuitState.CLOSED.value

        test_watchdog.set_state("OPEN")
        assert test_watchdog.get_system_metrics()["circuit_state"] == CircuitState.OPEN.value

        with pytest.raises(ValueError):
            test_watchdog.set_state("ESTADO_DESCONHECIDO")

    def test_record_execution_impact(self, test_watchdog: HardwareCircuitBreaker) -> None:
        """Verifica o registro de duracao de tarefas pesadas."""
        test_watchdog.record_execution_impact(1.452)
        m = test_watchdog.get_system_metrics()
        assert m["last_execution_duration"] == 1.452
        assert m["execution_history_count"] == 1

    def test_environment_variable_thresholds(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verifica leitura de limites por variaveis de ambiente."""
        monkeypatch.setenv("AURA_MAX_CPU_PERCENT", "65.5")
        monkeypatch.setenv("AURA_MAX_RAM_PERCENT", "72.0")
        monkeypatch.setenv("AURA_CIRCUIT_COOLDOWN_SEC", "15.0")

        cb = HardwareCircuitBreaker()
        assert cb.max_cpu_percent == 65.5
        assert cb.max_ram_percent == 72.0
        assert cb.cooldown_sec == 15.0

    def test_singleton_accessor(self) -> None:
        """Verifica que get_resource_watchdog retorna a mesma instancia singleton."""
        w1 = get_resource_watchdog()
        w2 = get_resource_watchdog()
        assert w1 is w2
        reset_resource_watchdog()
        w3 = get_resource_watchdog()
        assert w3 is not w1

    def test_core_package_lazy_exports(self) -> None:
        """Verifica que o pacote core expoe os simbolos do watchdog via lazy exports."""
        import core

        assert hasattr(core, "HardwareCircuitBreaker")
        assert hasattr(core, "CircuitState")
        assert hasattr(core, "ResourceWatchdog")
        assert hasattr(core, "get_resource_watchdog")
        assert core.HardwareCircuitBreaker is HardwareCircuitBreaker


# =============================================================================
# 3. INTEGRAÇÃO COM O MOTOR COGNITIVO (AuraEngine)
# =============================================================================


class TestAuraEngineCircuitBreakerIntegration:
    """Testa protecao de ferramentas pesadas no AuraEngine quando o circuito esta OPEN."""

    @pytest.mark.asyncio
    async def test_execute_tool_direct_heavy_tool_blocked_when_open(self) -> None:
        """Quando OPEN, ferramentas analiticas pesadas sao barradas imediatamente."""
        wd = HardwareCircuitBreaker(cooldown_sec=30.0)
        wd.trip("simulacao de estresse PDV")
        engine = AuraEngine(watchdog=wd)

        # conveniencia_vendas_cruzadas e ferramenta analitica pesada
        res = await engine.execute_tool_direct("conveniencia_vendas_cruzadas", {"produto": "OLEO"})

        assert res["status"] == "circuit_open"
        assert res["data"]["circuit_open"] is True
        assert res["data"]["circuit_state"] == "OPEN"
        assert "Modo de Protecao do Caixa Ativo" in res["data"]["message"]

    @pytest.mark.asyncio
    async def test_execute_tool_direct_fuga_financeira_blocked_when_open(self) -> None:
        """Auditoria de fuga financeira tambem e protegida pelo Circuit Breaker."""
        wd = HardwareCircuitBreaker(cooldown_sec=30.0)
        wd.trip("teste fuga financeira")
        engine = AuraEngine(watchdog=wd)

        res = await engine.execute_tool_direct("auditoria_fuga_financeira", {"data": "2026-10-15"})
        assert res["status"] == "circuit_open"
        assert res["data"]["circuit_open"] is True
        assert "Modo de Protecao do Caixa Ativo" in res["data"]["message"]

    @pytest.mark.asyncio
    async def test_execute_tool_direct_light_tool_allowed_when_open(self) -> None:
        """Ferramentas leves essenciais (como dados_filial) continuam operando normalmente."""
        wd = HardwareCircuitBreaker(cooldown_sec=30.0)
        wd.trip("estresse de background")
        engine = AuraEngine(watchdog=wd)

        # Mock dos dados de filial para nao depender de conexao real com banco
        engine.get_dados_filial = MagicMock(return_value={"filial_id": "posto_01", "razao": "Posto Central"})

        res = await engine.execute_tool_direct("dados_filial")
        assert res["status"] == "success"
        assert res["data"]["filial_id"] == "posto_01"

    @pytest.mark.asyncio
    async def test_ask_stream_heavy_tool_returns_graceful_synthesis_when_open(self) -> None:
        """Em ask_stream, se o circuito estiver OPEN, devolve sintese leve sem acionar a LLM."""
        wd = HardwareCircuitBreaker(cooldown_sec=30.0)
        wd.trip("estresse de pista")
        engine = AuraEngine(watchdog=wd)

        chunks: list[Any] = []
        async for chunk in engine.ask_stream("auditoria de fuga financeira no caixa"):
            chunks.append(chunk)

        # Verifica presenca dos chunks essenciais
        types = [c.chunk_type for c in chunks]
        assert AuraChunkType.INTENT in types
        assert AuraChunkType.TOOL_RESULT in types
        assert AuraChunkType.DELTA in types
        assert AuraChunkType.DONE in types

        # O texto do delta deve conter a mensagem oficial de protecao do caixa
        delta_chunk = next(c for c in chunks if c.chunk_type == AuraChunkType.DELTA)
        assert "Modo de Protecao do Caixa Ativo" in delta_chunk.text

    @pytest.mark.asyncio
    async def test_ask_stream_does_not_emit_ui_skeleton_when_circuit_open(self) -> None:
        """Quando o circuito estiver OPEN, nao emite UI_SKELETON para evitar loader pendente no front."""
        wd = HardwareCircuitBreaker(cooldown_sec=30.0)
        wd.trip("estresse no caixa")
        engine = AuraEngine(watchdog=wd)

        chunks: list[Any] = []
        async for chunk in engine.ask_stream("auditoria de fuga financeira no caixa", enable_genui=True):
            chunks.append(chunk)

        types = [c.chunk_type for c in chunks]
        assert AuraChunkType.UI_SKELETON not in types

    @pytest.mark.asyncio
    async def test_ask_full_query_returns_graceful_response_when_open(self) -> None:
        """Em ask() completo, a resposta final traz o aviso de contingencia leve."""
        wd = HardwareCircuitBreaker(cooldown_sec=30.0)
        wd.trip("estresse no fechamento")
        engine = AuraEngine(watchdog=wd)

        res = await engine.ask("fazer auditoria de fuga financeira")
        assert "Modo de Protecao do Caixa Ativo" in res.response_text
        assert res.tool_result is not None
        assert res.tool_result.get("circuit_open") is True


# =============================================================================
# 4. INTEGRAÇÃO COM O DAEMON PROATIVO (AuraProactiveDaemon)
# =============================================================================


class TestAuraProactiveDaemonCircuitBreakerIntegration:
    """Testa prevencao de sobrecarga no AuraProactiveDaemon sob circuito OPEN."""

    @pytest.mark.asyncio
    async def test_evaluate_rules_skipped_when_circuit_open(
        self, test_watchdog: HardwareCircuitBreaker
    ) -> None:
        """Se o watchdog estiver OPEN, o ciclo de avaliacao de regras e pulado para proteger o PDV."""
        test_watchdog.trip("CPU alta no caixa")
        daemon = AuraProactiveDaemon(
            db_path=":memory:",
            dispatch_enabled=False,
            watchdog=test_watchdog,
        )

        alerts = await daemon.evaluate_rules()
        assert alerts == []

    @pytest.mark.asyncio
    async def test_evaluate_rules_executes_when_circuit_closed(
        self, test_watchdog: HardwareCircuitBreaker
    ) -> None:
        """Se o watchdog estiver CLOSED, o daemon opera normalmente."""
        test_watchdog.reset()
        daemon = AuraProactiveDaemon(
            db_path=":memory:",
            dispatch_enabled=False,
            watchdog=test_watchdog,
        )

        tanque_critico = {
            "tanque_id": "01",
            "combustivel": "GASOLINA COMUM",
            "volume_atual": 2000.0,
            "capacidade_total": 20000.0,
            "autonomia_horas": 10.0,
            "venda_media_hora": 200.0,
        }

        alerts = await daemon.evaluate_rules(tanques=[tanque_critico])
        assert len(alerts) >= 1
        assert alerts[0].alert_type == "TANQUE_CRITICO"

    def test_daemon_status_reports_circuit_state(
        self, test_watchdog: HardwareCircuitBreaker
    ) -> None:
        """O status operacional do daemon reporta o estado do Circuit Breaker."""
        test_watchdog.trip("teste de status")
        daemon = AuraProactiveDaemon(
            db_path=":memory:",
            watchdog=test_watchdog,
        )

        st = daemon.get_status()
        assert st["circuit_state"] == "OPEN"
        assert st["is_heavy_allowed"] is False


# =============================================================================
# 5. VERIFICAÇÃO DE ZERO TRAVESSÕES
# =============================================================================


class TestProhibitedCharactersAbsence:
    """Valida ausencia estrita de travessoes proibidos (\\u2014, \\u2013)."""

    def test_zero_prohibited_dashes_in_phase_3_files(self) -> None:
        base_dir = Path(__file__).resolve().parent.parent.parent
        phase3_files = [
            base_dir / "core" / "resource_watchdog.py",
            base_dir / "core" / "aura_engine.py",
            base_dir / "core" / "proactive_daemon.py",
            base_dir / "core" / "__init__.py",
            base_dir / "tests" / "unit" / "test_hardware_circuit_breaker.py",
        ]

        prohibited_bytes = [b"\xe2\x80\x94", b"\xe2\x80\x93"]

        for file_path in phase3_files:
            if not file_path.exists():
                continue
            content = file_path.read_bytes()
            for bad in prohibited_bytes:
                assert bad not in content, f"Arquivo {file_path.name} contem travessao proibido ({bad})!"
