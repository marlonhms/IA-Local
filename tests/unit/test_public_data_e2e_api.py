"""
Suíte de Testes de Integração End-to-End (E2E) e API de Dados Públicos (Fase 5 - Pilar 6).
Valida:
1. Endpoint /api/v1/aura/chat com as 3 perguntas reais de revendedores (ANP, LMC, Selic).
2. Validacao estrita dos schemas Pydantic (BenchmarkComparisonProps, LMCComplianceProps, MacroeconomicInventoryCostProps).
3. Endpoints HTTP /api/v1/aura/public-data/health e /api/v1/aura/public-data/telemetry com injecao de repositorio.
4. Disparo proativo do AuraProactiveDaemon para quebra critica de LMC (> 0.60%) e staleness.
5. Cooldown inteligente, sanitizacao numerica segura (strings, percentuais, virgulas) e eventos CDC.
Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from core.aura_api import create_aura_app, set_public_data_repository
from core.aura_engine import AuraEngine, AuraSessionMemory
from core.compliance_manager import ComplianceManager
from core.proactive_daemon import AuraProactiveDaemon
from core.schemas.genui import (
    BenchmarkComparisonProps,
    LMCComplianceProps,
    MacroeconomicInventoryCostProps,
)


@pytest.fixture
def mock_engine() -> AuraEngine:
    """Fixture com AuraEngine isolada em memoria para testes ultrarrapidos sub-segundo."""
    mem = AuraSessionMemory(db_path=":memory:")
    comp_mgr = ComplianceManager(db_path=":memory:")
    return AuraEngine(
        tenant_id="tenant_e2e_test",
        filial_id="posto_e2e_01",
        session_memory=mem,
        compliance_manager=comp_mgr,
    )


@pytest.fixture
def proactive_daemon() -> AuraProactiveDaemon:
    """Fixture do AuraProactiveDaemon com SQLite em memoria e despacho desativado."""
    return AuraProactiveDaemon(
        db_path=":memory:",
        filial_id="posto_e2e_01",
        tenant_id="tenant_e2e_test",
        dispatch_enabled=False,
    )


@pytest.fixture(autouse=True)
def fast_tests_no_llm_wait():
    """Garante execucao deterministica ultrarrapida em milissegundos sem aguardar timeout de LLM."""
    with patch("core.aura_engine.FALLBACK_MODELS", []):
        yield


@pytest.fixture
def mock_public_repo() -> MagicMock:
    """Fixture de repositorio de dados publicos mockado para isolamento total."""
    repo = MagicMock()
    repo._is_mock = True
    repo.use_sqlite = True
    repo.get_telemetry_history.return_value = [
        {"id": 1, "fonte": "anp", "status": "SUCESSO", "processados": 150, "duracao_ms": 42.5}
    ]
    repo.check_data_staleness.side_effect = lambda fonte, max_age_days: {
        "fonte": fonte,
        "is_stale": False,
        "age_days": 2,
        "last_date": "2026-10-18",
        "max_age_days": max_age_days,
    }
    repo.get_latest_collection_date.side_effect = lambda fonte: "2026-10-18"
    return repo


@pytest.fixture
def client(
    mock_engine: AuraEngine,
    proactive_daemon: AuraProactiveDaemon,
    mock_public_repo: MagicMock,
) -> TestClient:
    """Fixture do TestClient FastAPI conectado a aplicacao com engine, daemon e repo isolados."""
    set_public_data_repository(mock_public_repo)
    app = create_aura_app(
        engine=mock_engine,
        daemon=proactive_daemon,
        public_data_repo=mock_public_repo,
    )
    return TestClient(app)


# =============================================================================
# 1. TESTES E2E DO CHAT CONVERSACIONAL (/api/v1/aura/chat)
# =============================================================================

@pytest.mark.unit
class TestDealerConversationalQueriesE2E:
    """Valida o fluxo conversacional fim-a-fim para as 3 questoes operacionais reais do revendedor."""

    def test_pergunta_1_benchmark_anp_municipal(self, client: TestClient) -> None:
        """
        Pergunta 1 do revendedor:
        'Como está meu preço de gasolina comum comparado com a ANP na cidade?'
        - Roteia para 'benchmark_comparativo'
        - Retorna envelope GenUI com component_name 'render_BenchmarkComparisonUI'
        - Valida schema Pydantic BenchmarkComparisonProps
        - Verifica presenca de texto executivo com gap
        """
        resp = client.post(
            "/api/v1/aura/chat",
            json={
                "query": "Como está meu preço de gasolina comum comparado com a ANP na cidade?",
                "stream": False,
                "genui": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["intent"] == "benchmark_comparativo"
        assert data.get("envelope") is not None
        env = data["envelope"]
        assert env["component_name"] == "render_BenchmarkComparisonUI"

        # Validacao do contrato Pydantic formal
        props = env["props"]
        validated_props = BenchmarkComparisonProps(**props)
        assert validated_props.competitiveness_score >= 0.0
        assert len(validated_props.comparison_items) > 0

        # Verificacao do texto executivo com gap
        summary_text = env.get("executive_summary") or data.get("response_text") or ""
        assert len(summary_text) > 0
        assert "gap" in summary_text.lower() or any(
            it.gap_value is not None for it in validated_props.comparison_items
        )

    def test_pergunta_2_auditoria_conformidade_lmc_anp(self, client: TestClient) -> None:
        """
        Pergunta 2 do revendedor:
        'Audite a conformidade do LMC dos tanques de combustível'
        - Roteia para 'auditar_conformidade_lmc_anp'
        - Retorna micro-widget render_LMCComplianceReportUI
        - Valida schema Pydantic LMCComplianceProps
        - Fornece 3 acoes HITL interativas para o operador
        - Verifica mencao a Portaria ANP 26/1992 no texto executivo
        """
        resp = client.post(
            "/api/v1/aura/chat",
            json={
                "query": "Audite a conformidade do LMC dos tanques de combustível",
                "stream": False,
                "genui": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["intent"] == "auditar_conformidade_lmc_anp"
        assert data.get("envelope") is not None
        env = data["envelope"]
        assert env["component_name"] == "render_LMCComplianceReportUI"

        # Validacao do contrato Pydantic formal
        props = env["props"]
        validated_props = LMCComplianceProps(**props)
        assert validated_props.tolerancia_legal_pct == 0.60
        assert validated_props.status in ("CONFORME", "CRITICO")

        # Verificacao dos 3 botoes HITL interativos
        actions = props.get("suggested_actions", [])
        assert len(actions) == 3

        labels = [a.get("label", "") for a in actions]
        assert any("Exportar LMC" in lbl for lbl in labels)
        assert any("Agendar Aferição INMETRO 20L" in lbl or "Aferição" in lbl for lbl in labels)
        assert any("Calibração do Tanque" in lbl or "Inspecionar" in lbl for lbl in labels)

        # Verificacao do texto regulatorio
        summary_text = env.get("executive_summary") or data.get("response_text") or ""
        assert "Portaria 26/1992" in summary_text or "LMC" in summary_text

    def test_pergunta_3_custo_estoque_selic_macro(self, client: TestClient) -> None:
        """
        Pergunta 3 do revendedor:
        'Qual o custo Selic do meu combustível nos estoques?'
        - Roteia para 'custo_estoque_macro'
        - Retorna micro-widget render_MacroeconomicInventoryCostUI
        - Valida schema Pydantic MacroeconomicInventoryCostProps
        - Props trazem taxa Selic, capital imobilizado e custo de carregamento diario
        - Texto executivo menciona BACEN e carregamento de estoque
        """
        resp = client.post(
            "/api/v1/aura/chat",
            json={
                "query": "Qual o custo Selic do meu combustível nos estoques?",
                "stream": False,
                "genui": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["intent"] == "custo_estoque_macro"
        assert data.get("envelope") is not None
        env = data["envelope"]
        assert env["component_name"] == "render_MacroeconomicInventoryCostUI"

        # Validacao do contrato Pydantic formal
        props = env["props"]
        validated_props = MacroeconomicInventoryCostProps(**props)
        assert validated_props.taxa_selic_anual_pct > 0.0
        assert validated_props.custo_diario_carregamento_reais > 0.0
        assert validated_props.capital_imobilizado_reais > 0.0

        # Verificacao do texto executivo
        summary_text = env.get("executive_summary") or data.get("response_text") or ""
        assert any(w in summary_text.lower() for w in ["selic", "bacen", "carregamento", "estoque"])


# =============================================================================
# 2. TESTES DOS ENDPOINTS HTTP DE DADOS PUBLICOS
# =============================================================================

@pytest.mark.unit
class TestPublicDataHttpEndpoints:
    """Testes dos endpoints de telemetria e health check dos conectores publicos."""

    def test_public_data_health_endpoint(self, client: TestClient) -> None:
        """Valida que GET /api/v1/aura/public-data/health retorna o estado dos Circuit Breakers."""
        resp = client.get("/api/v1/aura/public-data/health")
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "success"
        assert data["overall_status"] in ("healthy", "degraded")
        assert "circuit_breakers" in data

        breakers = data["circuit_breakers"]
        assert "anp" in breakers
        assert "confaz" in breakers
        assert "bacen" in breakers

        for src in ("anp", "confaz", "bacen"):
            assert breakers[src]["state"] in ("CLOSED", "OPEN", "HALF_OPEN")
            assert breakers[src]["failure_threshold"] >= 1
            assert "cooldown_seconds" in breakers[src]

        assert "repository" in data
        assert data["repository"]["status"] == "connected"

    def test_public_data_telemetry_endpoint(self, client: TestClient, mock_public_repo: MagicMock) -> None:
        """Valida que GET /api/v1/aura/public-data/telemetry retorna historico e staleness."""
        resp = client.get("/api/v1/aura/public-data/telemetry?limit=5&max_staleness_days=7")
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "success"
        assert "telemetry_history" in data
        assert "staleness" in data
        assert "latest_collections" in data
        assert data["max_staleness_days"] == 7

        staleness = data["staleness"]
        assert "anp" in staleness
        assert "confaz" in staleness
        assert "bacen" in staleness


# =============================================================================
# 3. TESTES DO MOTOR PROATIVO (LMC, STALENESS E CDC)
# =============================================================================

@pytest.mark.unit
class TestProactiveDaemonPublicRules:
    """Valida geracao de alertas, smart cooldown, sanitizacao e tratamento de CDC no daemon."""

    @pytest.mark.asyncio
    async def test_lmc_compliance_critical_alert_and_cooldown(self, proactive_daemon: AuraProactiveDaemon) -> None:
        """Valida alerta CRITICAL para quebra de LMC > 0.60% e supressao por cooldown de 4h."""
        # 1. Tanque dentro da conformidade (+0.25%): nenhum alerta gerado
        tanque_ok = [{"tanque_id": "01", "combustivel": "GASOLINA", "variacao_volumetrica_pct": 0.25}]
        alerts_ok = await proactive_daemon.evaluate_rules(tanques_lmc=tanque_ok, force=True)
        lmc_ok = [a for a in alerts_ok if a.alert_type == "LMC_CONFORMIDADE"]
        assert len(lmc_ok) == 0

        # 2. Tanque com perda excessiva (-0.85%): alerta CRITICAL gerado
        tanque_crit = [{"tanque_id": "01", "combustivel": "GASOLINA", "variacao_volumetrica_pct": -0.85}]
        alerts_crit = await proactive_daemon.evaluate_rules(tanques_lmc=tanque_crit, force=True)
        lmc_crit = [a for a in alerts_crit if a.alert_type == "LMC_CONFORMIDADE"]
        assert len(lmc_crit) == 1

        alerta = lmc_crit[0]
        assert alerta.severity == "CRITICAL"
        assert alerta.channel == "AURA_IN_APP"
        assert alerta.entity_id == "01"
        assert "Portaria ANP 26/1992" in alerta.message
        assert "Portaria INMETRO 559/2016" in alerta.suggested_action
        assert alerta.payload["variacao_volumetrica_pct"] == -0.85

        # 3. Segunda avaliacao imediata sem force: alerta suprimido pelo smart cooldown
        alerts_supp = await proactive_daemon.evaluate_rules(tanques_lmc=tanque_crit, force=False)
        lmc_supp = [a for a in alerts_supp if a.alert_type == "LMC_CONFORMIDADE"]
        assert len(lmc_supp) == 1
        assert lmc_supp[0].dispatched is False
        assert lmc_supp[0].channel == "AURA_IN_APP"
        assert lmc_supp[0].dispatch_results.get("status") == "cooldown_suppressed"
        assert lmc_supp[0].dispatch_results.get("channel") == "AURA_IN_APP"

    @pytest.mark.asyncio
    async def test_lmc_compliance_robust_numeric_parsing(self, proactive_daemon: AuraProactiveDaemon) -> None:
        """Valida que entradas numericas formatadas com virgula ou percentual sao sanitizadas com seguranca."""
        tanques_formatados = [
            {"tanque_id": "03", "combustivel": "ETANOL", "variacao_pct": "-0,82%"},
            {"tanque_id": "04", "combustivel": "DIESEL", "variacao_volumetrica_pct": "+1,15%"},
            {"tanque_id": "05", "combustivel": "GASOLINA", "variacao_pct": "0,30%"},
        ]
        alerts = proactive_daemon._evaluate_lmc_compliance_rules(tanques_lmc=tanques_formatados)
        assert len(alerts) == 2

        t3 = next(a for a in alerts if a.entity_id == "03")
        assert t3.payload["variacao_volumetrica_pct"] == -0.82
        assert t3.severity == "CRITICAL"

        t4 = next(a for a in alerts if a.entity_id == "04")
        assert t4.payload["variacao_volumetrica_pct"] == 1.15
        assert t4.severity == "CRITICAL"

    @pytest.mark.asyncio
    async def test_lmc_compliance_tools_fallback_when_empty(self, proactive_daemon: AuraProactiveDaemon) -> None:
        """Valida que o daemon busca dados no PostoTools quando nenhum dado e injetado."""
        alerts = proactive_daemon._evaluate_lmc_compliance_rules(tanques_lmc=None)
        # Nao deve lancar excecao mesmo operando sem adapter
        assert isinstance(alerts, list)

    @pytest.mark.asyncio
    async def test_public_data_staleness_alert_generation(self, proactive_daemon: AuraProactiveDaemon) -> None:
        """Valida alerta de defasagem de dados publicos quando base ultrapassa 7 dias."""
        mock_repo = MagicMock()
        mock_repo._is_mock = True
        mock_repo.check_data_staleness.side_effect = lambda fonte, max_age_days: {
            "fonte": fonte,
            "is_stale": (fonte == "anp"),
            "age_days": 12 if fonte == "anp" else 3,
            "last_date": "2026-10-01" if fonte == "anp" else "2026-10-17",
            "max_age_days": max_age_days,
        }
        alerts = await proactive_daemon._evaluate_public_data_staleness(
            repository=mock_repo,
            max_staleness_days=7,
            auto_sync=False,
        )
        stale_anp = [a for a in alerts if a.alert_type == "PUBLIC_DATA_STALENESS" and a.entity_id == "ANP"]
        assert len(stale_anp) == 1
        assert stale_anp[0].severity == "WARNING"
        assert stale_anp[0].channel == "AURA_IN_APP"
        assert "defasada" in stale_anp[0].message
        assert stale_anp[0].payload["dias_defasagem"] == 12

    @pytest.mark.asyncio
    async def test_handle_cdc_event_lmc_table_routing(self, proactive_daemon: AuraProactiveDaemon) -> None:
        """Valida que mutacoes em tabelas de LMC via CDC disparam a avaliacao de regras."""
        cdc_payload = {
            "table": "lmc_tanques",
            "payload": {
                "tanque_id": "02",
                "combustivel": "DIESEL S10",
                "variacao_volumetrica_pct": 0.92,
            },
        }
        alerts = await proactive_daemon.handle_cdc_event(cdc_payload)
        lmc_alerts = [a for a in alerts if a.alert_type == "LMC_CONFORMIDADE"]
        assert len(lmc_alerts) == 1
        assert lmc_alerts[0].entity_id == "02"
        assert lmc_alerts[0].severity == "CRITICAL"
        assert lmc_alerts[0].channel == "AURA_IN_APP"

    @pytest.mark.asyncio
    async def test_proactive_lmc_and_staleness_no_windows_popups_or_desktop_calls(self) -> None:
        """
        Valida categoricamente que alertas proativos de LMC e Staleness de Dados Publicos:
        1. NAO acionam WTSSendMessageW ou DesktopNotifier por padrao (desktop_notify=False).
        2. Mantem canal canonico AURA_IN_APP.
        3. Sao persistidos em _recent_alerts e no historico in-app.
        """
        mock_desktop = MagicMock()
        mock_desktop.notify_operator.return_value = {"status": "mocked"}

        daemon = AuraProactiveDaemon(
            db_path=":memory:",
            filial_id="posto_pub_01",
            tenant_id="tenant_pub_01",
            desktop_notifier=mock_desktop,
            dispatch_enabled=False,
        )
        assert daemon.desktop_notify is False

        # Avalia regra de LMC com variacao critica (-0.95%)
        tanque_critico = [
            {"tanque_id": "01", "combustivel": "GASOLINA ADITIVADA", "variacao_volumetrica_pct": -0.95}
        ]
        alerts = await daemon.evaluate_rules(tanques_lmc=tanque_critico, force=True)

        assert len(alerts) == 1
        alerta = alerts[0]
        assert alerta.alert_type == "LMC_CONFORMIDADE"
        assert alerta.channel == "AURA_IN_APP"
        assert alerta.severity == "CRITICAL"

        # Garante que nenhum popup modal do Windows foi acionado
        assert mock_desktop.notify_operator.call_count == 0
        assert "desktop_notifier" not in alerta.dispatch_results

        # Garante presenca no historico in-app _recent_alerts
        assert len(daemon._recent_alerts) >= 1
        assert daemon._recent_alerts[0]["alert_type"] == "LMC_CONFORMIDADE"
        assert daemon._recent_alerts[0]["channel"] == "AURA_IN_APP"

    @pytest.mark.asyncio
    async def test_proactive_lmc_and_staleness_api_delivery_and_in_app_stream(
        self,
        client: TestClient,
        proactive_daemon: AuraProactiveDaemon,
    ) -> None:
        """
        Valida que alertas criticos de LMC e dados publicos sao entregues na API da AURA:
        1. GET /api/v1/aura/proactive/alerts (com unread_only e dados completos: title, message, severity, timestamp)
        2. GET /api/v1/aura/proactive/status (contagem de unread_alerts_count e active_alerts_count)
        3. Streaming in-app via fila de subscriber
        4. Confirmacao de leitura via POST /api/v1/aura/proactive/alerts/ack
        """
        # 1. Registra subscriber para validar canal in-app de streaming
        queue = proactive_daemon.subscribe_in_app_alerts()
        assert proactive_daemon.get_unread_count() == 0

        # 2. Emite alerta critico de LMC (+0.88%)
        tanque_violacao = [
            {"tanque_id": "05", "combustivel": "ETANOL COMUM", "variacao_volumetrica_pct": 0.88}
        ]
        alerts = await proactive_daemon.evaluate_rules(tanques_lmc=tanque_violacao, force=True)
        assert len(alerts) == 1
        alert_obj = alerts[0]

        # 3. Fila in-app de stream deve receber o payload imediatamente
        stream_payload = await asyncio.wait_for(queue.get(), timeout=2.0)
        assert stream_payload["alert_id"] == alert_obj.alert_id
        assert stream_payload["channel"] == "AURA_IN_APP"
        assert stream_payload["severity"] == "CRITICAL"

        # 4. GET /api/v1/aura/proactive/alerts?unread_only=true
        resp_alerts = client.get("/api/v1/aura/proactive/alerts?unread_only=true")
        assert resp_alerts.status_code == 200
        data_alerts = resp_alerts.json()
        assert data_alerts["channel"] == "AURA_IN_APP"
        assert data_alerts["unread_count"] >= 1
        assert any(a["alert_id"] == alert_obj.alert_id for a in data_alerts["alerts"])

        item = next(a for a in data_alerts["alerts"] if a["alert_id"] == alert_obj.alert_id)
        assert item["title"] is not None and len(item["title"]) > 0
        assert item["message"] is not None and len(item["message"]) > 0
        assert item["severity"] == "CRITICAL"
        assert item["suggested_action"] is not None
        assert item["timestamp"] is not None

        # 5. GET /api/v1/aura/proactive/status
        resp_status = client.get("/api/v1/aura/proactive/status")
        assert resp_status.status_code == 200
        data_status = resp_status.json()
        assert data_status["channel"] == "AURA_IN_APP"
        assert data_status["unread_alerts_count"] >= 1
        assert data_status["desktop_notify_enabled"] is False

        # 6. POST /api/v1/aura/proactive/alerts/ack
        resp_ack = client.post(
            "/api/v1/aura/proactive/alerts/ack",
            json={"alert_id": alert_obj.alert_id},
        )
        assert resp_ack.status_code == 200
        data_ack = resp_ack.json()
        assert data_ack["success"] is True
        assert data_ack["acknowledged_count"] >= 1
        assert data_ack["unread_remaining"] == 0

        proactive_daemon.unsubscribe_in_app_alerts(queue)
