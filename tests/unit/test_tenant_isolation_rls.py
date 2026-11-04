"""
Suite de Testes de Isolamento Multi-Tenant e Row-Level Security (RLS) (Fase 8).
Valida isolamento matematico de chunks pgvector na VPS, protecao contra SQL injection,
politicas de escopo, middleware de tenancy e ausencia de vazamento cross-tenant.
Zero travessoes em todo o modulo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Self
import pytest
from starlette.testclient import TestClient

from core.aura_api import create_aura_app
from core.aura_engine import AuraEngine
from core.tenancy import (
    CrossTenantAccessError,
    TenantContext,
    inject_rls_tenant_context,
    load_pgvector_rls_sql,
    validate_tenant_id,
)


class FakeRlsVectorSession:
    """Simulador de sessao PostgreSQL com RLS para aura_conhecimento_chunks."""

    def __init__(self, chunks: list[dict[str, Any]]) -> None:
        self._chunks = list(chunks)
        self.guc_settings: dict[str, str] = {}
        self.executed_queries: list[tuple[str, Any]] = []

    def cursor(self) -> FakeRlsVectorCursor:
        return FakeRlsVectorCursor(self)

    def select_visible_chunks(self) -> list[dict[str, Any]]:
        """
        Aplica a politica escopo_leitura:
        camada IN ('core', 'vertical', 'erp') OR tenant_id = current_setting('aura.tenant_id', true)
        """
        active_tenant = self.guc_settings.get("aura.tenant_id", "")
        visible = []
        for ch in self._chunks:
            camada = ch.get("camada")
            t_id = ch.get("tenant_id")
            if camada in ("core", "vertical", "erp"):
                visible.append(dict(ch))
            elif camada == "tenant" and t_id == active_tenant:
                visible.append(dict(ch))
        return visible


class FakeRlsVectorCursor:
    """Cursor simulado para injecao e validacao de RLS."""

    def __init__(self, session: FakeRlsVectorSession) -> None:
        self._session = session
        self.closed = False

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()

    def execute(self, sql: str, params: Any = None) -> None:
        self._session.executed_queries.append((sql, params))
        if "aura.tenant_id" in sql and params:
            val = params[0] if isinstance(params, (tuple, list)) else params
            self._session.guc_settings["aura.tenant_id"] = str(val)

    def close(self) -> None:
        self.closed = True


def test_validate_tenant_id_safety():
    """Garante que tenant_id aceita identificadores validos e rejeita SQL injection."""
    assert validate_tenant_id("posto_central") == "posto_central"
    assert validate_tenant_id("tenant-123.filial_9") == "tenant-123.filial_9"

    # Tentativas maliciosas de SQL Injection e bypass
    malicious_inputs = [
        "",
        "   ",
        "' OR 1=1 --",
        "posto; DROP TABLE aura_chunks;",
        "posto' UNION SELECT * FROM users --",
        "posto/*comentario*/",
        "a" * 100,  # Ultrapassa 64 chars
        None,
        12345,
    ]
    for bad in malicious_inputs:
        with pytest.raises(CrossTenantAccessError):
            validate_tenant_id(bad)


def test_inject_rls_tenant_context_execution():
    """Valida injecao de SET SESSION / LOCAL aura.tenant_id na sessao de banco."""
    session = FakeRlsVectorSession([])
    inject_rls_tenant_context(session, tenant_id="posto_alpha", session_scope=True)
    assert session.guc_settings.get("aura.tenant_id") == "posto_alpha"
    assert getattr(session, "_rls_tenant_id", None) == "posto_alpha"


def test_pgvector_rls_sql_script_integrity():
    """Valida sintaxe e presenca de diretivas de seguranca no DDL da Fase 8."""
    sql = load_pgvector_rls_sql()
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "FORCE ROW LEVEL SECURITY" in sql
    assert "escopo_leitura" in sql
    assert "escopo_escrita_tenant" in sql
    assert "aura_app_vps" in sql
    assert "NOBYPASSRLS" in sql


def test_simulated_pgvector_multi_tenant_isolation():
    """
    Testa que chunks da camada 'tenant' nunca vazam entre tenants,
    enquanto camadas comuns ('core', 'erp', 'vertical') permanecem compartilhadas.
    """
    mock_chunks = [
        {"id": 1, "camada": "core", "tenant_id": "posto_local", "conteudo": "Regra ANP 800"},
        {"id": 2, "camada": "erp", "tenant_id": "posto_local", "conteudo": "Manual NFe webPosto"},
        {"id": 3, "camada": "tenant", "tenant_id": "posto_alpha", "conteudo": "Regra Segredo do Posto Alpha"},
        {"id": 4, "camada": "tenant", "tenant_id": "posto_beta", "conteudo": "Regra Segredo do Posto Beta"},
    ]

    session = FakeRlsVectorSession(mock_chunks)

    # Sessao configurada como posto_alpha
    inject_rls_tenant_context(session, tenant_id="posto_alpha")
    visible_alpha = session.select_visible_chunks()
    contents_alpha = [c["conteudo"] for c in visible_alpha]

    assert "Regra ANP 800" in contents_alpha
    assert "Manual NFe webPosto" in contents_alpha
    assert "Regra Segredo do Posto Alpha" in contents_alpha
    assert "Regra Segredo do Posto Beta" not in contents_alpha  # ISOLADO

    # Sessao configurada como posto_beta
    inject_rls_tenant_context(session, tenant_id="posto_beta")
    visible_beta = session.select_visible_chunks()
    contents_beta = [c["conteudo"] for c in visible_beta]

    assert "Regra ANP 800" in contents_beta
    assert "Manual NFe webPosto" in contents_beta
    assert "Regra Segredo do Posto Beta" in contents_beta
    assert "Regra Segredo do Posto Alpha" not in contents_beta  # ISOLADO


def test_api_tenant_headers_and_memory_isolation():
    """Valida que a API REST isola dados de acordo com os headers X-Tenant-ID."""
    engine = AuraEngine(tenant_id="posto_local", session_memory=None)
    # Garante banco limpo em memoria para os testes da API
    engine._session_memory.db_path = ":memory:"
    engine._tenant_memory = None  # Forca inicializacao com :memory:
    app = create_aura_app(engine=engine)
    client = TestClient(app)

    # 1. Posto Alpha cadastra uma regra via API
    resp_alpha = client.post(
        "/api/v1/aura/memory/tenant",
        headers={"X-Tenant-ID": "tenant_posto_a", "X-Filial-ID": "1"},
        json={
            "categoria": "regra_posto",
            "chave": "regra_alfa",
            "conteudo": "Posto Alpha fecha as 23h",
            "status": "ativo",
        },
    )
    assert resp_alpha.status_code == 200
    fact_a = resp_alpha.json()["fact"]
    assert fact_a["tenant_id"] == "tenant_posto_a"

    # 2. Posto Beta lista memorias: fato do Posto Alpha nao pode aparecer
    resp_beta_list = client.get(
        "/api/v1/aura/memory/tenant",
        headers={"X-Tenant-ID": "tenant_posto_b", "X-Filial-ID": "1"},
    )
    assert resp_beta_list.status_code == 200
    facts_beta = resp_beta_list.json()["facts"]
    assert len(facts_beta) == 0

    # 3. Posto Alpha lista memorias: fato deve aparecer
    resp_alpha_list = client.get(
        "/api/v1/aura/memory/tenant",
        headers={"X-Tenant-ID": "tenant_posto_a", "X-Filial-ID": "1"},
    )
    assert resp_alpha_list.status_code == 200
    facts_alpha = resp_alpha_list.json()["facts"]
    assert len(facts_alpha) == 1
    assert facts_alpha[0]["chave"] == "regra_alfa"

    # 4. Posto Beta tenta aprovar/modificar fato do Posto Alpha: deve retornar 404
    resp_cross_approve = client.post(
        f"/api/v1/aura/memory/tenant/{fact_a['id']}/approve",
        headers={"X-Tenant-ID": "tenant_posto_b", "X-Filial-ID": "1"},
        json={"approved_by": "gestor_beta"},
    )
    assert resp_cross_approve.status_code == 404


def test_zero_unicode_dashes_in_tenant_isolation_files():
    """Garante ausencia total de travessoes Unicode (U+2014 e U+2013)."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    files = [
        "scripts/setup_pgvector_rls.sql",
        "tests/unit/test_tenant_isolation_rls.py",
    ]
    for fname in files:
        content = (base_dir / fname).read_text(encoding="utf-8")
        assert "\u2014" not in content, f"Travessao em {fname}"
        assert "\u2013" not in content, f"Meia-risca em {fname}"
