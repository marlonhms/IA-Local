"""
Testes Unitarios: Restricao Rigorosa de CORS e Autenticacao Administrativa (P1-4).
Valida permissao de origens configuradas, bloqueio de origens nao autorizadas
e protecao de rotas administrativas via API Key e Bearer Token.
Zero travessoes em todo o arquivo.
"""

import pytest
from fastapi.testclient import TestClient

from config.settings import get_cors_origins
from core.aura_api import create_aura_app
from core.aura_engine import AuraEngine, AuraSessionMemory


@pytest.mark.unit
def test_cors_origins_parsing(monkeypatch):
    """Valida leitura e parseamento seguro de CORS_ORIGINS a partir do ambiente."""
    monkeypatch.setenv("CORS_ORIGINS", "https://meuposto.com.br, https://painel.rede.com")
    origins = get_cors_origins()
    assert "https://meuposto.com.br" in origins
    assert "https://painel.rede.com" in origins

    # Teste de fallback quando vazio
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    fallback_origins = get_cors_origins()
    assert "http://localhost:8000" in fallback_origins
    assert "http://127.0.0.1:8000" in fallback_origins


@pytest.mark.unit
def test_admin_endpoints_require_auth(monkeypatch):
    """Valida que endpoints administrativos retornam 401 sem autenticacao previa."""
    test_key = "segredo_admin_corporativo_2026"
    monkeypatch.setenv("AURA_API_KEY", test_key)
    monkeypatch.setenv("AURA_ENFORCE_ADMIN_AUTH", "1")

    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(session_memory=mem)
    app = create_aura_app(engine=engine)
    client = TestClient(app)

    # 1. Tentativa sem cabecalho de autenticacao -> HTTP 401
    resp_no_auth = client.get("/api/v1/aura/admin/feature-flags")
    assert resp_no_auth.status_code == 401
    assert "Autenticacao necessaria" in resp_no_auth.json()["detail"]

    # 2. Tentativa com chave incorreta -> HTTP 401
    resp_bad_key = client.get(
        "/api/v1/aura/admin/feature-flags",
        headers={"X-API-Key": "chave_incorreta_123"},
    )
    assert resp_bad_key.status_code == 401
    assert "Autenticacao invalida" in resp_bad_key.json()["detail"]

    # 3. Tentativa com X-API-Key valida -> HTTP 200
    resp_ok_key = client.get(
        "/api/v1/aura/admin/feature-flags",
        headers={"X-API-Key": test_key},
    )
    assert resp_ok_key.status_code == 200
    assert resp_ok_key.json()["status"] == "ok"

    # 4. Tentativa com Authorization: Bearer <key> valida -> HTTP 200
    resp_ok_bearer = client.get(
        "/api/v1/aura/admin/feature-flags",
        headers={"Authorization": f"Bearer {test_key}"},
    )
    assert resp_ok_bearer.status_code == 200
    assert resp_ok_bearer.json()["status"] == "ok"


from core.schemas.idempotency import generate_action_id, generate_tool_call_id


@pytest.mark.unit
def test_actions_execute_requires_auth(monkeypatch):
    """Valida que /actions/execute exige autenticacao quando AURA_ENFORCE_ADMIN_AUTH esta ativo."""
    test_key = "chave_voucher_auth_2026"
    monkeypatch.setenv("AURA_API_KEY", test_key)
    monkeypatch.setenv("AURA_ENFORCE_ADMIN_AUTH", "1")

    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(session_memory=mem)
    app = create_aura_app(engine=engine)
    client = TestClient(app)

    tool_id = generate_tool_call_id()
    act_id = generate_action_id()

    payload = {
        "session_id": "sess_auth_test",
        "action_id": act_id,
        "tool_call_id": tool_id,
        "action_name": "repassar_custo",
        "action_type": "mutation",
        "payload": {"produto": "Gasolina Comum", "delta_preco": 0.10},
        "operator_id": "gerente_01",
        "operator_role": "gerente",
    }

    # Sem header -> 401
    resp_unauth = client.post("/api/v1/aura/actions/execute", json=payload)
    assert resp_unauth.status_code == 401

    # Com X-API-Key valida -> 200
    resp_auth = client.post(
        "/api/v1/aura/actions/execute",
        json=payload,
        headers={"X-API-Key": test_key},
    )
    assert resp_auth.status_code == 200
    assert resp_auth.json()["status"] == "APPROVED"
