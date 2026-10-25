"""
Suite de testes unitarios para a Fase 2: Feed Executivo Zero-Click e Telemetria de Seguranca Auditavel.
Valida geracao de cards, ordenacao por impacto financeiro em R$, respeito ao Circuit Breaker e cache TTL,
endpoints da API FastAPI e integridade dos contratos.
Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.aura_api import create_aura_app
from core.compliance_manager import ComplianceManager
from core.proactive_daemon import (
    AuraProactiveDaemon,
    generate_executive_zero_click_feed,
    set_proactive_daemon_singleton,
)
from core.resource_watchdog import HardwareCircuitBreaker
from core.sanitizer import central_log_sanitizer
from core.schemas.genui import (
    ExecutiveExceptionCard,
    GenUIActionOption,
)


@pytest.fixture
def mock_watchdog() -> HardwareCircuitBreaker:
    """Watchdog com circuito fechado e metricas estaveis para testes."""
    wb = HardwareCircuitBreaker(force_os="linux")
    wb.reset()
    return wb


@pytest.fixture
def proactive_daemon(mock_watchdog: HardwareCircuitBreaker) -> AuraProactiveDaemon:
    """Daemon proativo isolado em memoria com watchdog controlado."""
    daemon = AuraProactiveDaemon(
        db_path=":memory:",
        filial_id="posto_teste_01",
        tenant_id="tenant_teste",
        watchdog=mock_watchdog,
        desktop_notify=False,
    )
    return daemon


@pytest.fixture
def api_client(proactive_daemon: AuraProactiveDaemon) -> TestClient:
    """Cliente de teste FastAPI com daemon proativo injetado."""
    app = create_aura_app(daemon=proactive_daemon)
    return TestClient(app)


# =============================================================================
# 1. TESTES DO CONTRATO PYDANTIC v2 ExecutiveExceptionCard
# =============================================================================

def test_executive_exception_card_contract_validation() -> None:
    """Valida a estrutura do schema ExecutiveExceptionCard e anatomia executiva da AURA."""
    action = GenUIActionOption(
        action_id="act_4f9a12c8-1234-4567-89ab-cdef01234567",
        label="Autorizar Sangria",
        action_type="mutation",
        payload={"caixa_id": "01", "valor": 1500.0},
    )

    card = ExecutiveExceptionCard(
        card_id="card_test_01",
        title="Alerta de Sangria: PDV 01",
        category="caixa_sangria",
        severity="HIGH",
        financial_impact_brl=2500.00,
        diagnostico_direto="Caixa 01 acumula R$ 2.500,00 em especie ha mais de 45 minutos.",
        prova_matematica="Saldo apurado: R$ 2.500,00 vs teto R$ 1.500,00 (+66,7%).",
        acao_recomendada_hitl=action,
        urgency_timeframe="turno_atual",
    )

    assert card.card_id == "card_test_01"
    assert card.severity == "HIGH"
    assert card.financial_impact_brl == 2500.00
    assert "Caixa 01" in card.diagnostico_direto
    assert isinstance(card.acao_recomendada_hitl, GenUIActionOption)

    d = card.model_dump()
    assert d["financial_impact_brl"] == 2500.00
    assert d["category"] == "caixa_sangria"
    assert "created_at" in d


def test_executive_exception_card_empty_fields_rejection() -> None:
    """Garante que campos obrigatorios nao possam ser vazios."""
    action = GenUIActionOption(
        action_id="act_4f9a12c8-1234-4567-89ab-cdef01234567",
        label="Acao",
        action_type="inspection",
    )

    with pytest.raises(ValueError, match="title nao pode ser vazio"):
        ExecutiveExceptionCard(
            card_id="c1",
            title="   ",
            category="runout_estoque",
            financial_impact_brl=100.0,
            diagnostico_direto="Diagnostico",
            prova_matematica="Calculo",
            acao_recomendada_hitl=action,
        )

    with pytest.raises(ValueError, match="diagnostico_direto nao pode ser vazio"):
        ExecutiveExceptionCard(
            card_id="c2",
            title="Titulo",
            category="runout_estoque",
            financial_impact_brl=100.0,
            diagnostico_direto="",
            prova_matematica="Calculo",
            acao_recomendada_hitl=action,
        )


def test_executive_exception_card_numeric_validation() -> None:
    """Valida rejeicao de valores invalidos em financial_impact_brl."""
    import math

    action = GenUIActionOption(
        action_id="act_4f9a12c8-1234-4567-89ab-cdef01234567",
        label="Acao",
        action_type="inspection",
    )

    with pytest.raises(ValueError, match="financial_impact_brl deve ser maior ou igual a zero"):
        ExecutiveExceptionCard(
            card_id="c_neg",
            title="Titulo",
            category="caixa_sangria",
            financial_impact_brl=-150.0,
            diagnostico_direto="Diagnostico",
            prova_matematica="Calculo",
            acao_recomendada_hitl=action,
        )

    with pytest.raises(ValueError, match="financial_impact_brl deve ser um numero finito valido"):
        ExecutiveExceptionCard(
            card_id="c_nan",
            title="Titulo",
            category="caixa_sangria",
            financial_impact_brl=math.nan,
            diagnostico_direto="Diagnostico",
            prova_matematica="Calculo",
            acao_recomendada_hitl=action,
        )


# =============================================================================
# 2. TESTES DO GERADOR DO FEED ZERO-CLICK E ORDENACAO POR IMPACTO FINANCEIRO
# =============================================================================

def test_generate_zero_click_feed_returns_sorted_by_financial_impact(
    proactive_daemon: AuraProactiveDaemon,
) -> None:
    """Valida geracao de cards e ordenacao estrita pelo maior impacto financeiro em R$ (DESC)."""
    feed = proactive_daemon.generate_executive_zero_click_feed(
        tenant_id="posto_alpha",
        force_refresh=True,
        limit=5,
    )

    assert len(feed) >= 3, "Feed deve conter ao menos 3 cards de excecao e oportunidade"
    assert len(feed) <= 5

    # Valida ordenacao estritamente decrescente por financial_impact_brl
    for i in range(len(feed) - 1):
        assert feed[i].financial_impact_brl >= feed[i + 1].financial_impact_brl, (
            f"Card {i} (R$ {feed[i].financial_impact_brl}) deve ser >= Card {i+1} (R$ {feed[i+1].financial_impact_brl})"
        )

    # Valida categorias vitais esperadas
    categories = {c.category for c in feed}
    expected_categories = {"runout_estoque", "caixa_sangria", "margem_conversao"}
    assert expected_categories.issubset(categories)

    # Valida integridade da anatomia executiva em todos os cards
    for card in feed:
        assert card.card_id
        assert card.title
        assert card.financial_impact_brl > 0
        assert card.diagnostico_direto
        assert card.prova_matematica
        assert card.acao_recomendada_hitl


def test_generate_zero_click_feed_respects_circuit_breaker(
    proactive_daemon: AuraProactiveDaemon,
    mock_watchdog: HardwareCircuitBreaker,
) -> None:
    """Garante protecao do PDV: se Circuit Breaker estiver OPEN, respeita a trava e usa cache."""
    # 1. Gera e popula cache com circuito fechado
    feed_initial = proactive_daemon.generate_executive_zero_click_feed(
        tenant_id="posto_beta",
        force_refresh=True,
    )
    assert len(feed_initial) > 0

    # 2. Dispara o circuit breaker para OPEN (simula sobrecarga de hardware no PDV)
    mock_watchdog.trip(reason="Teste de sobrecarga de CPU do caixa")
    assert not mock_watchdog.is_heavy_operation_allowed()

    # 3. Chamada normal deve retornar cache existente protegido sem travar PDV
    feed_guarded = proactive_daemon.generate_executive_zero_click_feed(
        tenant_id="posto_beta",
        force_refresh=False,
    )
    assert len(feed_guarded) == len(feed_initial)

    # 4. Para tenant sem cache previo durante circuito aberto, retorna lista vazia segura
    feed_empty = proactive_daemon.generate_executive_zero_click_feed(
        tenant_id="tenant_sem_cache",
        force_refresh=False,
    )
    assert feed_empty == []

    # 5. Mesmo com force_refresh=True, o Hardware Circuit Breaker DEVE proteger a maquina
    # e retornar o cache protegido sem disparar recomputacao
    feed_guarded_force = proactive_daemon.generate_executive_zero_click_feed(
        tenant_id="posto_beta",
        force_refresh=True,
    )
    assert len(feed_guarded_force) == len(feed_initial)
    assert [c.card_id for c in feed_guarded_force] == [c.card_id for c in feed_initial]


def test_generate_zero_click_feed_cache_ttl(
    proactive_daemon: AuraProactiveDaemon,
) -> None:
    """Valida o funcionamento do cache TTL evitando recomputacoes desnecessarias."""
    proactive_daemon.clear_zero_click_cache()

    feed_1 = proactive_daemon.generate_executive_zero_click_feed(tenant_id="posto_gamma")
    feed_2 = proactive_daemon.generate_executive_zero_click_feed(tenant_id="posto_gamma")

    assert [c.card_id for c in feed_1] == [c.card_id for c in feed_2]

    # Forcando refresh
    feed_3 = proactive_daemon.generate_executive_zero_click_feed(
        tenant_id="posto_gamma",
        force_refresh=True,
    )
    assert len(feed_3) == len(feed_1)


def test_module_level_generate_executive_zero_click_feed(
    proactive_daemon: AuraProactiveDaemon,
) -> None:
    """Valida funcao utilitaria em nivel de modulo."""
    set_proactive_daemon_singleton(proactive_daemon)
    try:
        cards = generate_executive_zero_click_feed(tenant_id="modulo_teste")
        assert len(cards) >= 3
        assert isinstance(cards[0], ExecutiveExceptionCard)
    finally:
        set_proactive_daemon_singleton(None)


# =============================================================================
# 3. TESTES DA TELEMETRIA DE SEGURANCA AUDITAVEL (ComplianceManager)
# =============================================================================

def test_live_security_telemetry_payload() -> None:
    """Valida o metodo get_live_security_telemetry no ComplianceManager."""
    mgr = ComplianceManager(db_path=":memory:")

    # Executa sanitizacao para incrementar contador de PII
    central_log_sanitizer.sanitize_text("Cliente CPF 529.982.247-25 realizou abastecimento.")

    telemetry = mgr.get_live_security_telemetry()

    assert telemetry["status"] == "success"
    assert "timestamp" in telemetry

    # 1. Sessao PostgreSQL
    pg = telemetry["postgresql_session"]
    assert "default_transaction_read_only" in pg
    assert "statement_timeout" in pg
    assert "lock_timeout" in pg
    assert pg["role"] in ("aura_service_ro", "suporte")

    # 2. Hardware Circuit Breaker
    cb = telemetry["hardware_circuit_breaker"]
    assert cb["circuit_state"] in ("FECHADO_SEGURO", "ABERTO_PROTECAO_PDV")
    assert "cpu_percent" in cb
    assert "ram_percent" in cb

    # 3. Contador de PII
    pii = telemetry["pii_sanitization"]
    assert pii["total_sanitized_entities"] >= 1
    assert "category_counts" in pii

    # 4. Hash SHA-256 do Termo
    term = telemetry["clean_room_active_term"]
    assert "term_hash_sha256" in term
    assert len(term["term_hash_sha256"]) == 64

    # 5. Script SQL Auditavel
    sql = telemetry["sql_role_script"]
    assert "CREATE ROLE aura_service_ro" in sql
    assert "REVOKE INSERT, UPDATE, DELETE, TRUNCATE" in sql

    # 6. Diagrama de 3 Camadas
    layers = telemetry["architecture_layers"]
    assert len(layers) == 3
    assert layers[0]["layer"] == 1
    assert layers[1]["layer"] == 2
    assert layers[2]["layer"] == 3


def test_pii_sanitization_session_counter() -> None:
    """Valida contagem acumulada e reset de contadores no CentralLogSanitizer."""
    initial_count = central_log_sanitizer.get_total_sanitized_count()

    texto = "Frentista Jose portador do CPF 52998224725 cadastrou placa ABC-1234 e tel 11987654321."
    clean_text, counts = central_log_sanitizer.sanitize_text(texto)
    assert "[REDACTED:CPF]" in clean_text
    assert counts.get("cpf", 0) >= 1
    new_count = central_log_sanitizer.get_total_sanitized_count()
    assert new_count >= initial_count + 1

    stats = central_log_sanitizer.get_category_counts()
    assert "cpf" in stats

    # Reset
    central_log_sanitizer.reset_counters()
    assert central_log_sanitizer.get_total_sanitized_count() == 0


# =============================================================================
# 4. TESTES DOS ENDPOINTS REST E STREAMING DA API (FastAPI)
# =============================================================================

def test_api_cockpit_zero_click_feed_endpoint(api_client: TestClient) -> None:
    """Valida o endpoint GET /api/v1/cockpit/zero-click-feed em modo JSON."""
    response = api_client.get("/api/v1/cockpit/zero-click-feed?tenant_id=teste_pdv&limit=5")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["tenant_id"] == "teste_pdv"
    assert data["total_cards"] >= 3
    assert len(data["cards"]) <= 5

    # Valida ordenacao decrescente
    cards = data["cards"]
    for i in range(len(cards) - 1):
        assert cards[i]["financial_impact_brl"] >= cards[i + 1]["financial_impact_brl"]


def test_api_cockpit_zero_click_feed_alias_endpoint(api_client: TestClient) -> None:
    """Valida alias GET /api/v1/aura/cockpit/zero-click-feed."""
    response = api_client.get("/api/v1/aura/cockpit/zero-click-feed?tenant_id=teste_alias")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["cards"]) >= 3


def test_api_cockpit_zero_click_feed_streaming_sse(api_client: TestClient) -> None:
    """Valida streaming SSE do feed zero-click com transmissao progressiva de cards."""
    response = api_client.get(
        "/api/v1/cockpit/zero-click-feed?stream=true",
        headers={"Accept": "text/event-stream"},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    body = response.text
    assert "event: zero_click_card" in body
    assert "event: done" in body
    assert "financial_impact_brl" in body


def test_api_security_telemetry_endpoint(api_client: TestClient) -> None:
    """Valida o endpoint GET /api/v1/aura/security/telemetry."""
    response = api_client.get("/api/v1/aura/security/telemetry")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert "postgresql_session" in data
    assert "hardware_circuit_breaker" in data
    assert "pii_sanitization" in data
    assert "clean_room_active_term" in data
    assert "sql_role_script" in data
    assert "architecture_layers" in data


def test_api_compliance_security_telemetry_alias(api_client: TestClient) -> None:
    """Valida o alias GET /api/v1/aura/compliance/security/telemetry."""
    response = api_client.get("/api/v1/aura/compliance/security/telemetry")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["architecture_layers"]) == 3


def test_dynamic_timeout_parsing_in_compliance_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida extracao dinamica de statement_timeout, lock_timeout e dbname na telemetria."""
    from config import settings

    custom_cfg = {
        "host": "localhost",
        "port": 5433,
        "dbname": "posto_filial_02",
        "user": "aura_custom_ro",
        "password": "secret_password",
        "connect_timeout": 5,
        "options": "-c default_transaction_read_only=on -c statement_timeout=5500 -c lock_timeout=1200",
    }
    monkeypatch.setattr(settings, "DB_ERP_CONFIG", custom_cfg)

    mgr = ComplianceManager(db_path=":memory:")
    telemetry = mgr.get_live_security_telemetry()

    pg = telemetry["postgresql_session"]
    assert pg["default_transaction_read_only"] == "on"
    assert pg["statement_timeout"] == "5500ms"
    assert pg["lock_timeout"] == "1200ms"
    assert pg["role"] == "aura_custom_ro"
    assert pg["database"] == "posto_filial_02"


# =============================================================================
# 5. TESTE DE AUDITORIA: ZERO TRAVESSOES EM ARQUIVOS MODIFICADOS/CRIADOS
# =============================================================================

def test_zero_travessoes_in_phase_2_files() -> None:
    """Garante ausencia total de travessoes (em-dash / en-dash) nos arquivos da Fase 2."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    files_to_check = [
        base_dir / "core" / "schemas" / "genui.py",
        base_dir / "core" / "proactive_daemon.py",
        base_dir / "core" / "compliance_manager.py",
        base_dir / "core" / "sanitizer.py",
        base_dir / "core" / "aura_api.py",
        base_dir / "web-frontend" / "src" / "types" / "aura-contracts.ts",
        base_dir / "web-frontend" / "src" / "api" / "aura-client.ts",
        base_dir / "web" / "index.html",
        base_dir / "web" / "showcase.html",
        base_dir / "web" / "js" / "aura-cockpit.js",
        base_dir / "web" / "js" / "aura-security-architecture.js",
        base_dir / "tests" / "unit" / "test_zero_click_cockpit_and_security.py",
        base_dir / "tests" / "unit" / "test_frontend_typescript_contracts.py",
    ]

    for path in files_to_check:
        assert path.exists(), f"Arquivo obrigatorio {path.name} nao encontrado"
        content = path.read_text(encoding="utf-8")
        assert "\u2014" not in content, f"Travessao em-dash (\\u2014) detectado em {path.name}"
        assert "\u2013" not in content, f"Travessao en-dash (\\u2013) detectado em {path.name}"

