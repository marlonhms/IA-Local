"""
Suite de testes unitarios para a Fase 4: Loop Fechado de Acao (Actionable BI),
Transactional Outbox Dispatch, Player de Audio Waveform e Contratos Apple Studio.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.aura_api import (
    create_aura_app,
    set_proactive_daemon,
    set_transactional_outbox,
)
from core.outbox import AuraTransactionalOutbox
from core.proactive_daemon import AuraProactiveDaemon
from core.schemas.genui import (
    ActionableDirectivePayload,
    ExecutiveExceptionCard,
)


@pytest.fixture
def test_outbox(tmp_path: Path) -> AuraTransactionalOutbox:
    """Instancia isolada da outbox SQLite WAL em diretorio temporario."""
    db_file = tmp_path / "test_outbox_p4.db"
    return AuraTransactionalOutbox(db_path=db_file)


@pytest.fixture
def test_daemon(tmp_path: Path) -> AuraProactiveDaemon:
    """Instancia do daemon proativo para testes."""
    return AuraProactiveDaemon(filial_id="posto_p4_test", desktop_notify=False)


@pytest.fixture
def client(test_outbox: AuraTransactionalOutbox, test_daemon: AuraProactiveDaemon):
    """Cliente HTTP FastAPI com outbox e daemon injetados."""
    set_transactional_outbox(test_outbox)
    set_proactive_daemon(test_daemon)
    app = create_aura_app()
    with TestClient(app) as test_client:
        yield test_client
    set_transactional_outbox(None)
    set_proactive_daemon(None)


def test_actionable_directive_payload_schema() -> None:
    """Valida a criacao, campos obrigatorios e validacoes de ActionableDirectivePayload."""
    directive = ActionableDirectivePayload(
        title="Reposicao Emergencial Tanque 02",
        category="runout_estoque",
        financial_impact_brl=14850.00,
        roteiro_voz_consultor="Tanque 02 em nivel critico com autonomia de 14 horas.",
        treinamento_equipe_15s="Oferecer Gasolina Comum prioritariamente na pista.",
        campanha_clientes_whatsapp="Alerta VIP: Abasteca Gasolina Aditivada hoje.",
        status="pending",
        canal_despacho="in_app_cockpit",
    )

    assert directive.directive_id.startswith("dir_")
    assert directive.title == "Reposicao Emergencial Tanque 02"
    assert directive.financial_impact_brl == 14850.00
    assert "14 horas" in directive.roteiro_voz_consultor
    assert "Gasolina Comum" in directive.treinamento_equipe_15s
    assert directive.status == "pending"

    # Validacao de campos obrigatorios vazios
    with pytest.raises(ValueError):
        ActionableDirectivePayload(
            title="",
            roteiro_voz_consultor="Briefing",
            treinamento_equipe_15s="Treinamento",
        )

    with pytest.raises(ValueError):
        ActionableDirectivePayload(
            title="Titulo",
            roteiro_voz_consultor="",
            treinamento_equipe_15s="Treinamento",
        )


def test_executive_exception_card_with_directive(test_daemon: AuraProactiveDaemon) -> None:
    """Valida que o feed zero-click embute diretivas de acao estruturadas em cada card."""
    cards = test_daemon.generate_executive_zero_click_feed(tenant_id="posto_alpha", force_refresh=True)
    assert len(cards) >= 3

    # Verifica que todos os cards possuem diretivas ricas pre-configuradas
    for card in cards:
        assert isinstance(card, ExecutiveExceptionCard)
        assert card.financial_impact_brl > 0
        assert card.directive is not None
        assert isinstance(card.directive, ActionableDirectivePayload)
        assert card.directive.card_id == card.card_id
        assert len(card.directive.roteiro_voz_consultor) > 10
        assert len(card.directive.treinamento_equipe_15s) > 5


def test_dispatch_actionable_directive_endpoint(client: TestClient, test_outbox: AuraTransactionalOutbox) -> None:
    """Valida o despacho da diretiva na outbox via POST /api/v1/aura/directives/dispatch."""
    payload = {
        "directive_id": "dir_test_401",
        "card_id": "card_test_runout_01",
        "title": "Ordem Emergencial Tanque 02",
        "category": "runout_estoque",
        "financial_impact_brl": 14850.00,
        "roteiro_voz_consultor": "Tanque 02 de aditivada atinge nivel critico em 14h.",
        "treinamento_equipe_15s": "Frentistas devem priorizar comum.",
        "campanha_clientes_whatsapp": "Campanha promocional relampago.",
        "canal_despacho": "outbox_webhook",
        "idempotency_key": "idem_test_p4_001",
        "operator_id": "gerente_roberto",
    }

    res = client.post("/api/v1/aura/directives/dispatch", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["success"] is True
    assert data["directive_id"] == "dir_test_401"
    assert data["financial_impact_brl"] == 14850.00
    assert "outbox_message_id" in data
    assert data["operator_id"] == "gerente_roberto"

    # Confere persistencia fisica na outbox SQLite WAL
    stats = test_outbox.get_stats()
    assert stats["total"] >= 1
    assert stats["pending"] >= 1

    # Testa idempotencia (segundo envio com a mesma idempotency_key nao duplica a mensagem)
    res2 = client.post("/api/v1/aura/directives/dispatch", json=payload)
    assert res2.status_code == 200
    stats2 = test_outbox.get_stats()
    assert stats2["total"] == stats["total"]


def test_recent_directives_endpoint(client: TestClient) -> None:
    """Valida listagem de diretivas recentes via GET /api/v1/aura/directives/recent."""
    # Dispara uma diretiva
    payload = {
        "directive_id": "dir_test_recent_01",
        "title": "Ajuste de Margem Gasolina Comum",
        "category": "margem_conversao",
        "financial_impact_brl": 2457.00,
        "roteiro_voz_consultor": "Repasse tecnico de 8 centavos na gasolina comum.",
        "treinamento_equipe_15s": "Focar em aditivacao e lubrificantes.",
        "canal_despacho": "outbox_webhook",
    }
    client.post("/api/v1/aura/directives/dispatch", json=payload)

    res = client.get("/api/v1/aura/directives/recent?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["total"] >= 1
    assert any(d["directive_id"] == "dir_test_recent_01" for d in data["directives"])


def test_directive_audio_waveform_endpoint(client: TestClient) -> None:
    """Valida geracao de waveform e tempo estimado de audio para o briefing de voz."""
    # Primeiro grava uma diretiva com texto conhecido
    payload = {
        "directive_id": "dir_waveform_test_99",
        "title": "Briefing de Seguranca de Caixa",
        "category": "caixa_sangria",
        "financial_impact_brl": 3450.00,
        "roteiro_voz_consultor": "Aviso gerencial: O PDV 01 ultrapassou o teto maximo em mil novecentos e cinquenta reais sem sangria ha mais de uma hora. Recolha para o cofre central.",
        "treinamento_equipe_15s": "Organizar malotes em 3 minutos.",
    }
    client.post("/api/v1/aura/directives/dispatch", json=payload)

    res = client.get("/api/v1/aura/directives/dir_waveform_test_99/audio-waveform")
    assert res.status_code == 200
    data = res.json()

    assert data["directive_id"] == "dir_waveform_test_99"
    assert data["estimated_duration_sec"] >= 10
    assert ":" in data["formatted_duration"]
    assert len(data["waveform_bars"]) == 36
    assert all(15 <= bar <= 100 for bar in data["waveform_bars"])


def test_zero_click_feed_endpoint_includes_directives(client: TestClient) -> None:
    """Valida que o endpoint GET /api/v1/cockpit/zero-click-feed retorna o objeto directive no JSON."""
    res = client.get("/api/v1/cockpit/zero-click-feed?limit=5&force_refresh=true")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["cards"]) >= 3

    for card_data in data["cards"]:
        assert "directive" in card_data
        assert card_data["directive"] is not None
        dir_obj = card_data["directive"]
        assert "roteiro_voz_consultor" in dir_obj
        assert "treinamento_equipe_15s" in dir_obj
        assert "financial_impact_brl" in dir_obj


def test_ausencia_travessoes_em_fase4() -> None:
    """Garante ausencia total de travessoes Unicode nas fontes da Fase 4."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    files_to_check = [
        base_dir / "core" / "schemas" / "genui.py",
        base_dir / "core" / "proactive_daemon.py",
        base_dir / "core" / "aura_api.py",
        base_dir / "web" / "index.html",
        base_dir / "web" / "js" / "aura-cockpit.js",
        base_dir / "web-frontend" / "src" / "types" / "aura-contracts.ts",
        base_dir / "web-frontend" / "src" / "api" / "aura-client.ts",
        Path(__file__),
    ]

    for p in files_to_check:
        assert p.exists(), f"Arquivo nao encontrado: {p}"
        text = p.read_text(encoding="utf-8")
        assert "\u2014" not in text, f"Travessao em-dash (\\u2014) detectado em {p.name}"
        assert "\u2013" not in text, f"Travessao en-dash (\\u2013) detectado em {p.name}"
