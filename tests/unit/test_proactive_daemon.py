"""
Testes Unitarios do Motor de Alertas Proativos de Pista (P3-2).
Valida:
1. Deteccao de tanques criticos (< 24h autonomia ou < 20% vol) com sugestao de 5.000 L.
2. Deteccao de sangrias pendentes e retencao em gaveta (> R$ 1.500 e > 45 min).
3. Politica inteligente de deduplicacao e cooldown anti-spam.
4. Persistencia e consulta com filtros em historico SQLite e memoria.
5. Ciclo de vida start() e stop() do daemon.
6. Endpoints FastAPI (/status, /evaluate, /alerts) via TestClient.
7. Regra inegociavel de ZERO travessoes.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from config.settings import BASE_DIR
from core.aura_api import create_aura_app
from core.aura_engine import AuraEngine, AuraSessionMemory
from core.proactive_daemon import AuraProactiveDaemon


@pytest.fixture
def memory_daemon() -> AuraProactiveDaemon:
    """Instancia isolada do daemon apontando para SQLite em memoria."""
    return AuraProactiveDaemon(
        db_path=":memory:",
        filial_id="posto_teste",
        tank_autonomy_threshold_hours=24.0,
        tank_volume_pct_threshold=0.20,
        cashier_max_cash_drawer=1500.0,
        cashier_idle_bleed_minutes=45,
        dispatch_enabled=False,
    )


# =============================================================================
# 1. TESTES DE REGRAS DE TANQUES CRITICOS E COMPARTIMENTOS DE 5.000 L
# =============================================================================

@pytest.mark.unit
def test_tank_rule_critical_volume_and_5k_compartments(memory_daemon: AuraProactiveDaemon) -> None:
    """
    Tanque com volume abaixo de 20% deve gerar alerta e sugerir bocas de 5.000 L.
    Capacidade: 20.000 L, Volume: 3.000 L (15%) -> Ullage: 17.000 L -> 3 bocas de 5.000 L (15.000 L).
    """
    tanques = [
        {
            "tanque_id": "TQ-01",
            "combustivel": "GASOLINA COMUM",
            "capacidade_total_litros": 20000.0,
            "volume_atual_litros": 3000.0,
            "autonomia_horas": 30.0,  # Autonomia acima de 24h, mas volume abaixo de 20%
        }
    ]

    alerts = memory_daemon.evaluate_tank_rules(tanques=tanques)
    assert len(alerts) == 1
    alert = alerts[0]

    assert alert.alert_type == "TANQUE_CRITICO"
    assert alert.entity_id == "TQ-01"
    assert alert.severity == "HIGH"
    assert alert.payload["compartimentos_5k"] == 3
    assert alert.payload["volume_sugerido_litros"] == 15000.0
    assert alert.payload["espaco_livre_ullage_litros"] == 17000.0
    assert "3 compartimento(s) de 5.000 L (15.000 L)" in alert.suggested_action


@pytest.mark.unit
def test_tank_rule_critical_autonomy_below_24h(memory_daemon: AuraProactiveDaemon) -> None:
    """
    Tanque com volume acima de 20%, mas com autonomia inferior a 24 horas deve disparar alerta.
    Capacidade: 30.000 L, Volume: 7.500 L (25%), Consumo: 500 L/h -> Autonomia: 15.0h (< 24h).
    Ullage: 22.500 L -> 4 bocas de 5.000 L (20.000 L).
    """
    tanques = [
        {
            "tanque_id": "TQ-02",
            "combustivel": "ETANOL",
            "capacidade_total_litros": 30000.0,
            "volume_atual_litros": 7500.0,
            "consumo_horario_litros": 500.0,  # 7500 / 500 = 15.0h
        }
    ]

    alerts = memory_daemon.evaluate_tank_rules(tanques=tanques)
    assert len(alerts) == 1
    alert = alerts[0]

    assert alert.alert_type == "TANQUE_CRITICO"
    assert alert.entity_id == "TQ-02"
    assert alert.payload["autonomia_horas"] == 15.0
    assert alert.payload["compartimentos_5k"] == 4
    assert alert.payload["volume_sugerido_litros"] == 20000.0


@pytest.mark.unit
def test_tank_rule_normal_safe_no_alert(memory_daemon: AuraProactiveDaemon) -> None:
    """Tanque com saldo confortavel e autonomia segura nao deve gerar alerta."""
    tanques = [
        {
            "tanque_id": "TQ-03",
            "combustivel": "DIESEL S10",
            "capacidade_total_litros": 30000.0,
            "volume_atual_litros": 24000.0,  # 80% ocupado
            "autonomia_horas": 72.0,
        }
    ]

    alerts = memory_daemon.evaluate_tank_rules(tanques=tanques)
    assert len(alerts) == 0


@pytest.mark.unit
def test_tank_rule_extreme_critical_severity(memory_daemon: AuraProactiveDaemon) -> None:
    """Tanque com autonomia < 12h ou volume < 10% deve receber severidade CRITICAL."""
    tanques = [
        {
            "tanque_id": "TQ-04",
            "combustivel": "GASOLINA ADITIVADA",
            "capacidade_total_litros": 15000.0,
            "volume_atual_litros": 1200.0,  # 8% (extremo)
            "autonomia_horas": 8.0,         # 8h (extremo)
        }
    ]

    alerts = memory_daemon.evaluate_tank_rules(tanques=tanques)
    assert len(alerts) == 1
    assert alerts[0].severity == "CRITICAL"
    assert alerts[0].payload["urgencia"] == "CRITICA"


# =============================================================================
# 2. TESTES DE MONITORAMENTO DE SANGRIAS E RETENCAO DE CAIXA
# =============================================================================

@pytest.mark.unit
def test_cashier_rule_triggers_on_excess_and_time(memory_daemon: AuraProactiveDaemon) -> None:
    """
    Caixa com valor > R$ 1.500 e tempo > 45 min sem sangria deve disparar alerta.
    Saldo: R$ 2.400,00, Tempo: 60 min -> Excesso: R$ 900,00.
    """
    caixas = [
        {
            "caixa_id": "PDV-01",
            "saldo_dinheiro": 2400.0,
            "minutos_sem_sangria": 60,
            "operador": "Frentista Joao",
        }
    ]

    alerts = memory_daemon.evaluate_cashier_rules(caixas=caixas)
    assert len(alerts) == 1
    alert = alerts[0]

    assert alert.alert_type == "SANGRIA_PENDENTE"
    assert alert.entity_id == "PDV-01"
    assert alert.severity == "HIGH"
    assert alert.payload["saldo_dinheiro"] == 2400.0
    assert alert.payload["teto_seguro"] == 1500.0
    assert alert.payload["excesso_dinheiro"] == 900.0
    assert alert.payload["minutos_sem_sangria"] == 60
    assert "no minimo R$ 900,00" in alert.suggested_action


@pytest.mark.unit
def test_cashier_rule_high_cash_but_recently_bled(memory_daemon: AuraProactiveDaemon) -> None:
    """Caixa com valor alto, mas com sangria recente (< 45 min) nao deve disparar alerta."""
    caixas = [
        {
            "caixa_id": "PDV-02",
            "saldo_dinheiro": 2800.0,
            "minutos_sem_sangria": 20,  # Apenas 20 min desde a ultima sangria
        }
    ]

    alerts = memory_daemon.evaluate_cashier_rules(caixas=caixas)
    assert len(alerts) == 0


@pytest.mark.unit
def test_cashier_rule_idle_time_long_but_low_cash(memory_daemon: AuraProactiveDaemon) -> None:
    """Caixa sem sangria ha muito tempo, mas com pouco dinheiro (< teto) nao deve disparar alerta."""
    caixas = [
        {
            "caixa_id": "PDV-03",
            "saldo_dinheiro": 600.0,  # Abaixo de R$ 1.500
            "minutos_sem_sangria": 120,
        }
    ]

    alerts = memory_daemon.evaluate_cashier_rules(caixas=caixas)
    assert len(alerts) == 0


@pytest.mark.unit
def test_cashier_rule_extreme_excess_critical_severity(memory_daemon: AuraProactiveDaemon) -> None:
    """Caixa com excesso superior a R$ 1.000 ou tempo > 90 min deve ter severidade CRITICAL."""
    caixas = [
        {
            "caixa_id": "PDV-04",
            "saldo_dinheiro": 3600.0,  # Excesso de R$ 2.100 (> 1000)
            "minutos_sem_sangria": 95,
        }
    ]

    alerts = memory_daemon.evaluate_cashier_rules(caixas=caixas)
    assert len(alerts) == 1
    assert alerts[0].severity == "CRITICAL"


# =============================================================================
# 3. TESTES DE COOLDOWN E DEDUPLICACAO DE ALERTAS
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_cooldown_prevents_duplicate_dispatch() -> None:
    """Garante que repeticao do mesmo alerta dentro do periodo de cooldown seja suprimida."""
    daemon = AuraProactiveDaemon(
        db_path=":memory:",
        cooldown_seconds_by_type={"TANQUE_CRITICO": 7200.0},
        dispatch_enabled=True,
    )

    mock_tanques = [
        {
            "tanque_id": "TQ-01",
            "combustivel": "GASOLINA COMUM",
            "capacidade_total_litros": 20000.0,
            "volume_atual_litros": 2500.0,
            "autonomia_horas": 10.0,
        }
    ]

    with patch("core.proactive_daemon.notify_alerta_tanque", new_callable=AsyncMock) as mock_notify:
        mock_notify.return_value = {"n8n": {"success": True}}

        # Primeiro ciclo: dispara normalmente
        alerts_1 = await daemon.evaluate_rules(tanques=mock_tanques)
        assert len(alerts_1) == 1
        assert alerts_1[0].dispatched is True
        assert mock_notify.call_count == 1

        # Segundo ciclo imediato: deve ser suprimido pelo cooldown (sem novo envio WhatsApp/n8n)
        alerts_2 = await daemon.evaluate_rules(tanques=mock_tanques)
        assert len(alerts_2) == 1
        assert alerts_2[0].dispatched is False
        assert alerts_2[0].dispatch_results.get("status") == "cooldown_suppressed"
        # Nao houve nova chamada ao despachador
        assert mock_notify.call_count == 1

        # Terceiro ciclo forcado com force=True: deve ignorar cooldown
        alerts_3 = await daemon.evaluate_rules(tanques=mock_tanques, force=True)
        assert len(alerts_3) == 1
        assert alerts_3[0].dispatched is True
        assert mock_notify.call_count == 2


@pytest.mark.unit
def test_cooldown_isolation_between_entities(memory_daemon: AuraProactiveDaemon) -> None:
    """Garante que cooldown de uma entidade nao bloqueie outras entidades do mesmo tipo."""
    memory_daemon.record_cooldown("TANQUE_CRITICO", "TQ-01")

    # TQ-01 esta em cooldown
    assert memory_daemon.is_in_cooldown("TANQUE_CRITICO", "TQ-01") is True
    # TQ-02 nao esta em cooldown
    assert memory_daemon.is_in_cooldown("TANQUE_CRITICO", "TQ-02") is False

    # Limpeza seletiva
    memory_daemon.clear_cooldown(alert_type="TANQUE_CRITICO", entity_id="TQ-01")
    assert memory_daemon.is_in_cooldown("TANQUE_CRITICO", "TQ-01") is False


# =============================================================================
# 4. TESTES DE PERSISTENCIA SQLITE E CONSULTA DE HISTORICO
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_alert_persistence_and_filtering(memory_daemon: AuraProactiveDaemon) -> None:
    """Valida armazenamento local em SQLite e recuperacao com filtros e paginacao."""
    tanques = [
        {
            "tanque_id": "TQ-01",
            "capacidade_total_litros": 20000.0,
            "volume_atual_litros": 2000.0,
            "autonomia_horas": 8.0,
        }
    ]
    caixas = [
        {
            "caixa_id": "PDV-01",
            "saldo_dinheiro": 2500.0,
            "minutos_sem_sangria": 50,
        }
    ]

    await memory_daemon.evaluate_rules(tanques=tanques, caixas=caixas)

    # Consulta sem filtro
    all_alerts = memory_daemon.get_recent_alerts(limit=50)
    assert len(all_alerts) == 2

    # Filtro por tipo de alerta
    tank_only = memory_daemon.get_recent_alerts(alert_type="TANQUE_CRITICO")
    assert len(tank_only) == 1
    assert tank_only[0]["alert_type"] == "TANQUE_CRITICO"

    cashier_only = memory_daemon.get_recent_alerts(alert_type="SANGRIA_PENDENTE")
    assert len(cashier_only) == 1
    assert cashier_only[0]["alert_type"] == "SANGRIA_PENDENTE"

    # Paginacao com limit=1
    page1 = memory_daemon.get_recent_alerts(limit=1, offset=0)
    page2 = memory_daemon.get_recent_alerts(limit=1, offset=1)
    assert len(page1) == 1
    assert len(page2) == 1
    assert page1[0]["alert_id"] != page2[0]["alert_id"]


# =============================================================================
# 5. TESTES DO CICLO DE VIDA (START / STOP) E STATUS
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_daemon_start_stop_lifecycle() -> None:
    """Valida inicializacao e encerramento gracioso do daemon em background."""
    daemon = AuraProactiveDaemon(
        db_path=":memory:",
        evaluation_interval_seconds=0.1,
        dispatch_enabled=False,
    )

    status_initial = daemon.get_status()
    assert status_initial["active"] is False

    await daemon.start()
    assert daemon.get_status()["active"] is True

    await daemon.stop()
    assert daemon.get_status()["active"] is False


# =============================================================================
# 6. TESTES DOS ENDPOINTS FASTAPI COM TESTCLIENT
# =============================================================================

@pytest.fixture
def api_client() -> TestClient:
    """Cria TestClient isolado com daemon proativo em memoria."""
    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(session_memory=mem)
    daemon = AuraProactiveDaemon(
        db_path=":memory:",
        filial_id="posto_api_test",
        dispatch_enabled=False,
    )
    app = create_aura_app(engine=engine, daemon=daemon)
    return TestClient(app)


@pytest.mark.unit
def test_api_proactive_status_endpoint(api_client: TestClient) -> None:
    """Valida endpoint GET /api/v1/aura/proactive/status."""
    resp = api_client.get("/api/v1/aura/proactive/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "active" in data
    assert "rules_evaluated_count" in data
    assert "status" in data
    assert data["filial_id"] == "posto_api_test"


@pytest.mark.unit
def test_api_proactive_evaluate_endpoint(api_client: TestClient) -> None:
    """Valida endpoint POST /api/v1/aura/proactive/evaluate."""
    body = {
        "tanques": [
            {
                "tanque_id": "TQ-09",
                "combustivel": "GASOLINA COMUM",
                "capacidade_total_litros": 20000.0,
                "volume_atual_litros": 2500.0,  # 12.5%
                "autonomia_horas": 12.0,
            }
        ],
        "caixas": [
            {
                "caixa_id": "PDV-02",
                "saldo_dinheiro": 2200.0,
                "minutos_sem_sangria": 65,
            }
        ],
        "force": True,
    }

    resp = api_client.post("/api/v1/aura/proactive/evaluate", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["alerts_generated"] == 2
    assert len(data["alerts"]) == 2

    types = {a["alert_type"] for a in data["alerts"]}
    assert "TANQUE_CRITICO" in types
    assert "SANGRIA_PENDENTE" in types


@pytest.mark.unit
def test_api_proactive_alerts_list_endpoint(api_client: TestClient) -> None:
    """Valida endpoint GET /api/v1/aura/proactive/alerts."""
    # Gera alertas via POST
    api_client.post(
        "/api/v1/aura/proactive/evaluate",
        json={
            "tanques": [
                {
                    "tanque_id": "TQ-99",
                    "capacidade_total_litros": 20000.0,
                    "volume_atual_litros": 1000.0,
                    "autonomia_horas": 5.0,
                }
            ],
            "force": True,
        },
    )

    # Consulta alertas gerados via GET
    resp = api_client.get("/api/v1/aura/proactive/alerts?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert "alerts" in data
    assert any(a["entity_id"] == "TQ-99" for a in data["alerts"])


# =============================================================================
# 7. TESTES DE REGRAS DE FECHAMENTO DE TURNO E DESPACHO
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_turn_rule_shift_closure_and_dispatch() -> None:
    """Valida geracao de alerta de fechamento de turno e despacho assincrono via webhook."""
    daemon = AuraProactiveDaemon(
        db_path=":memory:",
        turno_max_quebra_caixa=50.0,
        dispatch_enabled=True,
    )

    turnos = [
        {
            "turno_id": "TURNO-NOITE-01",
            "filial_id": "posto_central",
            "data": "2026-10-16",
            "faturamento_total": 45200.0,
            "litros_vendidos": 7800.0,
            "quebra_caixa": -85.50,  # Excede R$ 50,00 de tolerancia
            "status_conciliacao": "ALERTA",
            "bicos_analisados": 16,
            "observacoes": "Diferenca na gaveta do bico 04",
        }
    ]

    with patch("core.proactive_daemon.notify_fechamento_turno", new_callable=AsyncMock) as mock_notify:
        mock_notify.return_value = {"n8n": {"success": True}, "evolution": {"success": True}}

        alerts = await daemon.evaluate_rules(turnos=turnos)
        assert len(alerts) == 1
        alert = alerts[0]

        assert alert.alert_type == "FECHAMENTO_TURNO"
        assert alert.entity_id == "TURNO-NOITE-01"
        assert alert.severity == "CRITICAL"
        assert alert.dispatched is True
        assert alert.payload["quebra_caixa"] == -85.50
        assert "Auditar gaveta e sangrias" in alert.suggested_action
        assert mock_notify.call_count == 1

        # Segundo ciclo imediato deve suprimir pelo cooldown
        alerts_suppressed = await daemon.evaluate_rules(turnos=turnos)
        assert len(alerts_suppressed) == 1
        assert alerts_suppressed[0].dispatched is False
        assert alerts_suppressed[0].dispatch_results.get("status") == "cooldown_suppressed"
        assert mock_notify.call_count == 1


# =============================================================================
# 8. TESTE DE RESILIENCIA: PERSISTENCIA DE COOLDOWN EM REINICIALIZACAO (SQLITE)
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_cooldown_persists_across_daemon_restart(tmp_path: Path) -> None:
    """
    Garante que o cooldown de alertas sobreviva a reinicializacoes do processo Python
    consultando o historico do SQLite local.
    """
    db_file = tmp_path / "test_restart_cooldown.db"

    # Daemon 1 executa e dispara alerta
    daemon1 = AuraProactiveDaemon(
        db_path=db_file,
        filial_id="posto_restart",
        cooldown_seconds_by_type={"TANQUE_CRITICO": 7200.0},
        dispatch_enabled=True,
    )

    tanques = [
        {
            "tanque_id": "TQ-RESTART",
            "combustivel": "DIESEL S10",
            "capacidade_total_litros": 20000.0,
            "volume_atual_litros": 2000.0,
            "autonomia_horas": 8.0,
        }
    ]

    with patch("core.proactive_daemon.notify_alerta_tanque", new_callable=AsyncMock) as mock_notify:
        mock_notify.return_value = {"n8n": {"success": True}}
        alerts1 = await daemon1.evaluate_rules(tanques=tanques)
        assert len(alerts1) == 1
        assert alerts1[0].dispatched is True
        assert mock_notify.call_count == 1

    # Daemon 1 encerra (simula encerramento do processo ou queda do servico)
    del daemon1

    # Daemon 2 inicializa do zero com memoria limpa mas mesmo banco SQLite
    daemon2 = AuraProactiveDaemon(
        db_path=db_file,
        filial_id="posto_restart",
        cooldown_seconds_by_type={"TANQUE_CRITICO": 7200.0},
        dispatch_enabled=True,
    )

    # Memoria interna esta vazia
    assert len(daemon2._cooldown_cache) == 0

    with patch("core.proactive_daemon.notify_alerta_tanque", new_callable=AsyncMock) as mock_notify2:
        # Avaliacao sem force: DEVE consultar o SQLite e suprimir novo disparo
        alerts2 = await daemon2.evaluate_rules(tanques=tanques, force=False)
        assert len(alerts2) == 1
        assert alerts2[0].dispatched is False
        assert alerts2[0].dispatch_results.get("status") == "cooldown_suppressed"
        # Nao deve ter realizado despacho externo
        assert mock_notify2.call_count == 0

    # Limpeza explicita de cooldown deve permitir re-disparo
    daemon2.clear_cooldown(alert_type="TANQUE_CRITICO", entity_id="TQ-RESTART")
    with patch("core.proactive_daemon.notify_alerta_tanque", new_callable=AsyncMock) as mock_notify3:
        mock_notify3.return_value = {"n8n": {"success": True}}
        alerts3 = await daemon2.evaluate_rules(tanques=tanques, force=False)
        assert len(alerts3) == 1
        assert alerts3[0].dispatched is True
        assert mock_notify3.call_count == 1


# =============================================================================
# 9. TESTES DE ROBUSTEZ: LIMITES, VALORES NEGATIVOS E ZERO EM TANQUES
# =============================================================================

@pytest.mark.unit
def test_tank_rule_handles_negative_and_zero_values(memory_daemon: AuraProactiveDaemon) -> None:
    """Garante comportamento seguro e sem excecoes quando o ERP envia capacidades ou volumes anomalos."""
    tanques = [
        {
            "tanque_id": "TQ-ANOMALO-1",
            "combustivel": "GASOLINA COMUM",
            "capacidade_total_litros": -1000.0,  # Capacidade negativa
            "volume_atual_litros": -50.0,       # Volume negativo
            "autonomia_horas": 0.0,             # Esgotamento imediato
        },
        {
            "tanque_id": "TQ-ANOMALO-2",
            "combustivel": "ETANOL",
            "capacidade_total_litros": 0.0,      # Capacidade zero
            "volume_atual_litros": 100.0,
            "autonomia_horas": 10.0,
        },
    ]

    alerts = memory_daemon.evaluate_tank_rules(tanques=tanques)
    assert len(alerts) == 2

    a1 = next(a for a in alerts if a.entity_id == "TQ-ANOMALO-1")
    assert a1.payload["previsao_esgotamento"] == "Esgotado / Imediata"
    assert a1.payload["compartimentos_5k"] == 0
    assert a1.payload["capacidade_total_litros"] == 0.0
    assert a1.payload["volume_atual_litros"] == 0.0

    a2 = next(a for a in alerts if a.entity_id == "TQ-ANOMALO-2")
    assert a2.payload["compartimentos_5k"] == 0


# =============================================================================
# 10. TESTES DE INTEGRACAO COM CHANGE DATA CAPTURE (CDC)
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_cdc_event_triggers_rule_evaluation(memory_daemon: AuraProactiveDaemon) -> None:
    """Valida que mutacoes recebidas via CDC acionem o daemon de forma direcionada."""
    cdc_event_tanque = {
        "table": "tanques",
        "payload": {
            "tanque_id": "TQ-CDC-01",
            "combustivel": "DIESEL",
            "capacidade_total_litros": 15000.0,
            "volume_atual_litros": 1200.0,  # 8%
            "autonomia_horas": 6.0,
        },
    }

    alerts = await memory_daemon.handle_cdc_event(cdc_event_tanque)
    assert len(alerts) == 1
    assert alerts[0].alert_type == "TANQUE_CRITICO"
    assert alerts[0].entity_id == "TQ-CDC-01"


# =============================================================================
# 11. TESTE DE THREAD-SAFETY E CONCORRENCIA
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_rule_evaluations_thread_safe(memory_daemon: AuraProactiveDaemon) -> None:
    """Valida estabilidade sob chamadas assincronas concorrentes sem travar o SQLite."""
    import asyncio

    tanques = [
        {
            "tanque_id": f"TQ-CONC-{i}",
            "capacidade_total_litros": 20000.0,
            "volume_atual_litros": 2000.0,
            "autonomia_horas": 10.0,
        }
        for i in range(5)
    ]

    tasks = [
        memory_daemon.evaluate_rules(tanques=[t], force=True)
        for t in tanques
    ]
    results = await asyncio.gather(*tasks)
    assert len(results) == 5
    for r in results:
        assert len(r) == 1

    status = memory_daemon.get_status()
    assert status["status"] == "healthy"
    assert status["rules_evaluated_count"] >= 15


# =============================================================================
# 12. TESTE DE ENDPOINT COM TURNOS NA API
# =============================================================================

@pytest.mark.unit
def test_api_proactive_evaluate_with_turnos(api_client: TestClient) -> None:
    """Valida avaliacao sincrona de fechamento de turnos via API."""
    body = {
        "turnos": [
            {
                "turno_id": "TURNO-API-01",
                "faturamento_total": 32000.0,
                "litros_vendidos": 6000.0,
                "quebra_caixa": -120.0,
                "status_conciliacao": "ALERTA",
            }
        ],
        "force": True,
    }

    resp = api_client.post("/api/v1/aura/proactive/evaluate", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["alerts_generated"] == 1
    assert data["alerts"][0]["alert_type"] == "FECHAMENTO_TURNO"
    assert data["alerts"][0]["entity_id"] == "TURNO-API-01"


# =============================================================================
# 13. TESTES DE CANAL IN-APP EXCLUSIVO DA AURA (SEM POPUPS DO WINDOWS)
# =============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_proactive_daemon_defaults_to_in_app_no_windows_popups() -> None:
    """Valida que o daemon nao dispara WTSSendMessageW por padrao e usa estritamente canal AURA_IN_APP."""
    mock_notifier = MagicMock()
    mock_notifier.notify_operator.return_value = {"status": "mocked"}

    daemon = AuraProactiveDaemon(
        db_path=":memory:",
        filial_id="posto_in_app_01",
        desktop_notifier=mock_notifier,
    )
    assert daemon.desktop_notify is False

    tanques = [
        {
            "tanque_id": "TQ-CRIT-01",
            "combustivel": "GASOLINA COMUM",
            "capacidade_total_litros": 20000.0,
            "volume_atual_litros": 1000.0,
            "autonomia_horas": 4.0,
        }
    ]

    with patch("core.proactive_daemon.notify_alerta_tanque", new_callable=AsyncMock) as mock_notify:
        mock_notify.return_value = {"success": True}
        alerts = await daemon.evaluate_rules(tanques=tanques, force=True)

    assert len(alerts) == 1
    assert alerts[0].channel == "AURA_IN_APP"
    # Notificador desktop do Windows NAO deve ter sido invocado
    assert mock_notifier.notify_operator.call_count == 0
    # dispatch_results deve ter canal AURA_IN_APP e nenhuma entrega desktop
    assert alerts[0].dispatch_results.get("channel") == "AURA_IN_APP"
    assert "desktop_notifier" not in alerts[0].dispatch_results


@pytest.mark.unit
@pytest.mark.asyncio
async def test_proactive_daemon_in_app_subscribers_and_unread_lifecycle() -> None:
    """Valida ciclo de vida dos alertas in-app: unread count, queue streaming e acknowledge."""
    daemon = AuraProactiveDaemon(db_path=":memory:", filial_id="posto_sub_01")
    queue = daemon.subscribe_in_app_alerts()
    assert daemon.get_unread_count() == 0

    tanques = [
        {
            "tanque_id": "TQ-SUB-01",
            "combustivel": "ETANOL",
            "capacidade_total_litros": 15000.0,
            "volume_atual_litros": 800.0,
            "autonomia_horas": 3.0,
        }
    ]

    with patch("core.proactive_daemon.notify_alerta_tanque", new_callable=AsyncMock) as mock_notify:
        mock_notify.return_value = {"success": True}
        alerts = await daemon.evaluate_rules(tanques=tanques, force=True)

    assert len(alerts) == 1
    assert daemon.get_unread_count() == 1

    # Fila de subscriber SSE recebeu o alerta
    streamed = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert streamed["entity_id"] == "TQ-SUB-01"
    assert streamed["channel"] == "AURA_IN_APP"

    # Leitura pendente sem marcar como lido
    pending = daemon.get_unread_in_app_alerts(mark_read=False)
    assert len(pending) == 1
    assert daemon.get_unread_count() == 1

    # Validacao de persistencia no historico in-app _recent_alerts
    assert len(daemon._recent_alerts) == 1
    assert daemon._recent_alerts[0]["entity_id"] == "TQ-SUB-01"
    assert daemon._recent_alerts[0]["channel"] == "AURA_IN_APP"

    # Confirmacao / acknowledge
    ack_count = daemon.mark_alerts_as_read(alerts[0].alert_id)
    assert ack_count == 1
    assert daemon.get_unread_count() == 0

    daemon.unsubscribe_in_app_alerts(queue)


@pytest.mark.unit
def test_api_proactive_unread_and_ack_endpoints(api_client: TestClient) -> None:
    """Valida endpoints HTTP /proactive/alerts?unread_only=true e /proactive/alerts/ack."""
    # 1. Avalia alerta para popular fila in-app
    eval_resp = api_client.post(
        "/api/v1/aura/proactive/evaluate",
        json={
            "tanques": [
                {
                    "tanque_id": "TQ-API-UNREAD",
                    "combustivel": "DIESEL",
                    "capacidade_total_litros": 30000.0,
                    "volume_atual_litros": 1200.0,
                    "autonomia_horas": 5.0,
                }
            ],
            "force": True,
        },
    )
    assert eval_resp.status_code == 200
    alert_id = eval_resp.json()["alerts"][0]["alert_id"]

    # 2. Consulta alertas nao lidos via GET /proactive/alerts?unread_only=true
    list_resp = api_client.get("/api/v1/aura/proactive/alerts?unread_only=true")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["channel"] == "AURA_IN_APP"
    assert list_data["unread_count"] >= 1
    assert any(a["alert_id"] == alert_id for a in list_data["alerts"])

    # 3. Faz acknowledge via POST /proactive/alerts/ack
    ack_resp = api_client.post(
        "/api/v1/aura/proactive/alerts/ack",
        json={"alert_id": alert_id},
    )
    assert ack_resp.status_code == 200
    ack_data = ack_resp.json()
    assert ack_data["success"] is True
    assert ack_data["acknowledged_count"] >= 1
    assert ack_data["channel"] == "AURA_IN_APP"


# =============================================================================
# 14. REGRA INEFAVEL: ZERO TRAVESSOES
# =============================================================================

@pytest.mark.unit
def test_zero_travessoes_in_proactive_modules() -> None:
    """Garante ausencia estrita de travessoes em todos os modulos criados e modificados."""
    files_to_check = [
        BASE_DIR / "core" / "proactive_daemon.py",
        BASE_DIR / "core" / "webhook_dispatcher.py",
        BASE_DIR / "core" / "webhooks.py",
        BASE_DIR / "core" / "aura_api.py",
        BASE_DIR / "core" / "aura_engine.py",
        BASE_DIR / "web" / "js" / "aura-api.js",
        BASE_DIR / "web" / "js" / "aura-chat.js",
        BASE_DIR / "web" / "index.html",
        BASE_DIR / "docs" / "roadmap_producao_enterprise.md",
        BASE_DIR / "docs" / "guia_operacional_apis_publicas.md",
        BASE_DIR / "docs" / "roadmap_integracao_apis_publicas.md",
        BASE_DIR / "tests" / "unit" / "test_proactive_daemon.py",
        BASE_DIR / "tests" / "unit" / "test_public_data_e2e_api.py",
    ]

    for file_path in files_to_check:
        assert file_path.exists(), f"Arquivo nao encontrado: {file_path}"
        content = file_path.read_text(encoding="utf-8")
        assert "\u2014" not in content, f"Travessao em-dash (\\u2014) encontrado em {file_path.name}"
        assert "\u2013" not in content, f"Travessao en-dash (\\u2013) encontrado em {file_path.name}"
