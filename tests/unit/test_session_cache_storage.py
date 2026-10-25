"""
Testes Unitarios - Cache Local de Conversas e Persistencia de Sessoes (Dual-Layer).
Valida o armazenamento duravel no SQLite WAL (AuraSessionMemory),
os endpoints REST (/api/v1/aura/sessions) e o contrato do cache IndexedDB frontend.
Zero travessoes em todo o modulo.
"""

import pytest
from fastapi.testclient import TestClient

from core.aura_api import app
from core.aura_engine import AuraSessionMemory


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def memory_db():
    return AuraSessionMemory(":memory:")


def test_session_memory_crud(memory_db):
    """Valida ciclo completo de sessao e mensagens no AuraSessionMemory."""
    # 1. Cria mensagens em duas sessoes distintas
    memory_db.save_message(
        session_id="sessao_alpha",
        role="user",
        content="Como fecharam as formas de pagamento do dia?",
        intent="formas_pagamento",
    )
    memory_db.save_message(
        session_id="sessao_alpha",
        role="assistant",
        content="Turno 1 conciliado com faturamento de R$ 23.47 no Caixa 007.",
        intent="formas_pagamento",
        metadata={"envelope": {"client_component": "PaymentMethodsBreakdownUI"}},
    )

    memory_db.save_message(
        session_id="sessao_beta",
        role="user",
        content="Qual a situacao de autonomia dos tanques de diesel?",
        intent="previsao_tanques",
    )

    # 2. Lista sessoes e valida metadados
    sessoes = memory_db.list_sessions(limit=10)
    assert len(sessoes) == 2

    # Verifica sessao alpha
    s_alpha = next((s for s in sessoes if s["session_id"] == "sessao_alpha"), None)
    assert s_alpha is not None
    assert s_alpha["message_count"] == 2
    assert "formas de pagamento" in s_alpha["title"].lower()

    # Verifica sessao beta
    s_beta = next((s for s in sessoes if s["session_id"] == "sessao_beta"), None)
    assert s_beta is not None
    assert s_beta["message_count"] == 1
    assert "tanques de diesel" in s_beta["title"].lower()

    # 3. Recupera historico detalhado da sessao alpha
    msgs_alpha = memory_db.get_session_messages("sessao_alpha")
    assert len(msgs_alpha) == 2
    assert msgs_alpha[0]["role"] == "user"
    assert msgs_alpha[1]["role"] == "assistant"
    assert msgs_alpha[1]["metadata"]["envelope"]["client_component"] == "PaymentMethodsBreakdownUI"

    # 4. Deleta sessao alpha e verifica isolamento
    assert memory_db.delete_session("sessao_alpha") is True
    sessoes_apos = memory_db.list_sessions(limit=10)
    assert len(sessoes_apos) == 1
    assert sessoes_apos[0]["session_id"] == "sessao_beta"
    assert len(memory_db.get_session_messages("sessao_alpha")) == 0


def test_api_sessions_endpoints(test_client):
    """Valida os endpoints REST de listagem, historico e delecao de sessoes."""
    # 1. GET /api/v1/aura/sessions
    resp_list = test_client.get("/api/v1/aura/sessions?limit=5")
    assert resp_list.status_code == 200
    data_list = resp_list.json()
    assert data_list["status"] == "success"
    assert isinstance(data_list["sessions"], list)

    # 2. GET /api/v1/aura/sessions/{session_id}
    test_sid = "test_mock_session_404"
    resp_get = test_client.get(f"/api/v1/aura/sessions/{test_sid}")
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert data_get["status"] == "success"
    assert data_get["session_id"] == test_sid
    assert isinstance(data_get["messages"], list)

    # 3. DELETE /api/v1/aura/sessions/{session_id}
    resp_del = test_client.delete(f"/api/v1/aura/sessions/{test_sid}")
    assert resp_del.status_code == 200
    data_del = resp_del.json()
    assert data_del["status"] == "success"
    assert data_del["deleted"] is True


def test_frontend_storage_contract():
    """Valida a integridade do script frontend aura-storage.js e montagem no HTML."""
    from pathlib import Path

    storage_js = Path("web/js/aura-storage.js")
    assert storage_js.exists(), "web/js/aura-storage.js deve existir"

    content = storage_js.read_text(encoding="utf-8")
    assert "class AuraLocalCacheManager" in content
    assert "window.AuraStorage" in content
    assert "AuraChatCacheDB" in content
    assert "saveMessage" in content
    assert "getMessages" in content
    assert "getActiveSessionId" in content
    assert "startNewSession" in content

    index_html = Path("web/index.html").read_text(encoding="utf-8")
    assert "aura-storage.js" in index_html, "web/index.html deve carregar aura-storage.js"


def test_zero_travessoes_storage():
    """Garante ausencia total de travessoes proibidos (\\u2014, \\u2013)."""
    with open(__file__, "r", encoding="utf-8") as f:
        content = f.read()
    assert "\u2014" not in content, "Travessao em-dash detectado"
    assert "\u2013" not in content, "Travessao en-dash detectado"
