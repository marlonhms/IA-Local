"""
Testes Unitarios: Carbon Core P0.1 - Hardening de Credenciais, Fim do Fallback suporte
e Autenticacao Hibrida (Localhost HttpOnly SameSite=Strict + Origin Check vs LAN X-API-Key).
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import core.db_pool as db_pool
import core.voice_live_bridge as vlb
from config.settings import (
    BASE_DIR,
    VECTOR_DB_DRIVER_OPTIONS,
    resolve_runtime_secret,
)
from core.aura_api import (
    LOCAL_SESSION_COOKIE_NAME,
    create_aura_app,
    get_local_session_token,
)
from core.aura_engine import AuraEngine, AuraSessionMemory
from core.partner_api import PartnerStagingStore, set_partner_staging_store


@pytest.mark.unit
def test_zero_hardcoded_legacy_ro_password_in_repository() -> None:
    """Garante zero ocorrencia da credencial legada hardcoded no codigo do repositorio."""
    forbidden_literal = "364" + "768"
    scan_exts = {".py", ".sql", ".ps1", ".bat", ".yaml", ".yml", ".json"}
    skip_dirs = {".git", "__pycache__", ".venv", "venv", "node_modules", "evals", "data", "backups"}

    hits: list[str] = []
    for path in BASE_DIR.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.suffix.lower() not in scan_exts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if forbidden_literal in text:
            hits.append(str(path.relative_to(BASE_DIR)))

    assert hits == [], f"Credencial hardcoded encontrada nos arquivos: {hits}"


@pytest.mark.unit
def test_build_role_candidates_excludes_suporte_by_default(monkeypatch) -> None:
    """Garante que _build_role_candidates nunca inclui a role privilegiada 'suporte' por padrao."""
    monkeypatch.delenv("ERP_ALLOW_SUPORTE_FALLBACK", raising=False)
    monkeypatch.setattr(db_pool, "_last_working_erp_cred", None)
    monkeypatch.setattr(db_pool, "_is_pool_mocked", lambda _fn: False)

    candidates = db_pool._build_role_candidates("suporte", "senha_teste_ro")
    roles = [user for user, _ in candidates]

    assert "aura_service_ro" in roles
    assert "suporte" not in roles


@pytest.mark.unit
def test_vector_db_driver_options_include_timeouts() -> None:
    """Garante presenca de statement_timeout e lock_timeout em VECTOR_DB_DRIVER_OPTIONS."""
    assert "statement_timeout=5000" in VECTOR_DB_DRIVER_OPTIONS
    assert "lock_timeout=1500" in VECTOR_DB_DRIVER_OPTIONS


@pytest.mark.unit
def test_resolve_runtime_secret_generates_ephemeral_outside_ci(monkeypatch) -> None:
    """Fora de CI/PYTEST e sem env explicita, gera segredo criptografico efemero de alta entropia."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("AURA_TEST_EPHEMERAL_SECRET", raising=False)

    sec1 = resolve_runtime_secret("AURA_TEST_EPHEMERAL_SECRET", "known_static_default")
    sec2 = resolve_runtime_secret("AURA_TEST_EPHEMERAL_SECRET", "known_static_default")

    assert sec1 != "known_static_default"
    assert len(sec1) >= 32
    assert sec1 != sec2


@pytest.mark.unit
def test_hybrid_auth_localhost_cookie_vs_lan_block_and_evil_origin(monkeypatch) -> None:
    """
    Valida a politica dual P0.1:
    1. Acesso LAN (192.168.1.50) sem X-API-Key -> 401 Unauthorized.
    2. Acesso LAN (192.168.1.50) com X-API-Key valida -> 200 OK.
    3. Acesso localhost (127.0.0.1) em '/' emite cookie HttpOnly; SameSite=Strict
       que autentica /api/v1/aura/admin/feature-flags com 200 OK.
    4. Acesso localhost (127.0.0.1) com Origin malicioso (https://evil.example) -> 403 Forbidden.
    """
    admin_key = "chave-admin-p0-segura-2026"
    monkeypatch.setenv("AURA_API_KEY", admin_key)
    monkeypatch.delenv("AURA_ENFORCE_ADMIN_AUTH", raising=False)

    mem = AuraSessionMemory(db_path=":memory:")
    engine = AuraEngine(session_memory=mem)
    app = create_aura_app(engine=engine)

    # 1. Cliente LAN (192.168.1.50) sem X-API-Key -> 401
    lan_client = TestClient(app, client=("192.168.1.50", 51234))
    resp_lan_no_key = lan_client.get("/api/v1/aura/admin/feature-flags")
    assert resp_lan_no_key.status_code == 401
    assert "LAN" in resp_lan_no_key.json()["detail"] or "Autenticacao necessaria" in resp_lan_no_key.json()["detail"]

    # LAN tambem nao pode receber cookie de sessao local ao visitar '/'
    resp_lan_root = lan_client.get("/")
    assert LOCAL_SESSION_COOKIE_NAME not in resp_lan_root.cookies

    # 2. Cliente LAN com X-API-Key valida -> 200
    resp_lan_with_key = lan_client.get(
        "/api/v1/aura/admin/feature-flags",
        headers={"X-API-Key": admin_key},
    )
    assert resp_lan_with_key.status_code == 200
    assert resp_lan_with_key.json()["status"] == "ok"

    # 3. Cliente localhost (127.0.0.1) sem cookie nem API Key -> 401
    local_client = TestClient(app, client=("127.0.0.1", 52000))
    resp_local_no_cookie = local_client.get("/api/v1/aura/admin/feature-flags")
    assert resp_local_no_cookie.status_code == 401

    # Ao acessar '/', recebe cookie HttpOnly; SameSite=Strict
    resp_local_root = local_client.get("/")
    assert resp_local_root.status_code == 200
    set_cookie_hdr = resp_local_root.headers.get("set-cookie", "")
    assert LOCAL_SESSION_COOKIE_NAME in set_cookie_hdr
    assert "httponly" in set_cookie_hdr.lower()
    assert "samesite=strict" in set_cookie_hdr.lower()
    assert local_client.cookies.get(LOCAL_SESSION_COOKIE_NAME) == get_local_session_token()

    # Com cookie de mesma origem em localhost -> 200 OK
    resp_local_ok = local_client.get(
        "/api/v1/aura/admin/feature-flags",
        headers={"Origin": "http://127.0.0.1:8000"},
    )
    assert resp_local_ok.status_code == 200
    assert resp_local_ok.json()["status"] == "ok"

    # 4. Localhost com Origin externo (DNS rebinding / CSRF) -> 403 Forbidden
    resp_evil_origin = local_client.get(
        "/api/v1/aura/admin/feature-flags",
        headers={"Origin": "https://evil.example"},
    )
    assert resp_evil_origin.status_code == 403


@pytest.mark.unit
def test_websocket_lan_blocked_without_api_key(monkeypatch) -> None:
    """Garante que WebSocket /api/v1/voice/live bloqueia acesso LAN sem X-API-Key (WS 1008)."""
    monkeypatch.setenv("AURA_API_KEY", "ws-lan-secret-key")
    monkeypatch.delenv("AURA_ENFORCE_ADMIN_AUTH", raising=False)

    app = create_aura_app()
    lan_client = TestClient(app, client=("192.168.1.50", 54321))

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with lan_client.websocket_connect("/api/v1/voice/live"):
            pass
    assert exc_info.value.code == 1008


@pytest.mark.unit
def test_partner_acl_admin_key_isolation_and_raw_sync_limits(tmp_path: Path, monkeypatch) -> None:
    """
    Valida P0.1 no Partner Gateway:
    - Chave admin (AURA_API_KEY) nao e aceita em verify_partner_auth (401).
    - PARTNER_STATION_ACL bloqueia parceiro fora do escopo da estacao com 403.
    - RawSyncPayload acima de 10.000 registros retorna 422.
    """
    admin_key = "only-admin-key-xyz"
    partner_key_a = "partner-key-alpha-2026"
    monkeypatch.setenv("AURA_API_KEY", admin_key)
    monkeypatch.setenv("AURA_PARTNER_API_KEY", partner_key_a)
    monkeypatch.setenv(
        "PARTNER_STATION_ACL",
        json.dumps({partner_key_a: ["posto_autorizado_01"]}),
    )

    store = PartnerStagingStore(staging_dir=tmp_path / "staging")
    set_partner_staging_store(store)
    try:
        app = create_aura_app()
        client = TestClient(app)

        # 1. Admin key rejeitada no Partner API
        resp_admin = client.post(
            "/api/v1/partner/stations/posto_autorizado_01/raw-sync",
            headers={"X-Partner-Key": admin_key},
            json={"tanques": [{"codtan": "1"}]},
        )
        assert resp_admin.status_code == 401

        # 2. Parceiro fora da ACL da estacao recebe 403
        resp_forbidden = client.post(
            "/api/v1/partner/stations/posto_nao_autorizado_99/raw-sync",
            headers={"X-Partner-Key": partner_key_a},
            json={"tanques": [{"codtan": "1"}]},
        )
        assert resp_forbidden.status_code == 403

        # 3. Parceiro autorizado na estacao dentro da ACL recebe 200
        resp_allowed = client.post(
            "/api/v1/partner/stations/posto_autorizado_01/raw-sync",
            headers={"X-Partner-Key": partner_key_a},
            json={"tanques": [{"codtan": "1", "volatu": 10000, "capmax": 30000}]},
        )
        assert resp_allowed.status_code == 200

        # 4. RawSyncPayload acima de 10.000 registros retorna 422
        oversized_rows = [{"codi": str(i)} for i in range(10001)]
        resp_oversized = client.post(
            "/api/v1/partner/stations/posto_autorizado_01/raw-sync",
            headers={"X-Partner-Key": partner_key_a},
            json={"pedido": oversized_rows},
        )
        assert resp_oversized.status_code == 422
    finally:
        set_partner_staging_store(None)
