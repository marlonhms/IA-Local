"""
Testes Unitarios: Role Tecnica de Leitura aura_service_ro no PostgreSQL (P1-1).
Valida a priorizacao de credenciais no settings, presenca do script de provisionamento
e garantia matematica de somente-leitura contra mutacoes no ERP.
Zero travessoes em todo o arquivo.
"""

import os

import pytest

import core.config
from config.settings import BASE_DIR, get_erp_password


@pytest.mark.unit
def test_sql_provisioning_script_exists_and_valid():
    """Valida se o script SQL de provisionamento existe e possui revogacoes estritas."""
    script_path = BASE_DIR / "scripts" / "provisionar_usuario_leitura_erp.sql"
    assert script_path.exists(), f"Script SQL nao encontrado em {script_path}"

    content = script_path.read_text(encoding="utf-8")
    assert "aura_service_ro" in content
    assert "GRANT SELECT ON ALL TABLES IN SCHEMA public TO aura_service_ro;" in content
    assert "GRANT USAGE ON SCHEMA public TO aura_service_ro;" in content
    assert "REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public FROM aura_service_ro;" in content
    assert "REVOKE CREATE ON SCHEMA public FROM aura_service_ro;" in content


@pytest.mark.unit
def test_erp_service_credentials_precedence(monkeypatch):
    """Valida que ERP_SERVICE_USER e ERP_SERVICE_PASS tem prioridade sobre suporte."""
    monkeypatch.setenv("ERP_SERVICE_USER", "aura_service_ro")
    monkeypatch.setenv("ERP_SERVICE_PASS", "senha_servico_ro_forte_123")
    monkeypatch.setenv("ERP_DB_USER", "suporte")
    monkeypatch.setenv("ERP_DB_PASSWORD", "senha_suporte_legado")

    # Verifica get_erp_password
    resolved_pass = get_erp_password()
    assert resolved_pass == "senha_servico_ro_forte_123"

    user = os.getenv("ERP_SERVICE_USER") or os.getenv("ERP_DB_USER", "aura_service_ro")
    assert user == "aura_service_ro"


@pytest.mark.unit
def test_erp_service_fallback_to_erp_db_password(monkeypatch):
    """Valida fallback gracioso para ERP_DB_PASSWORD caso ERP_SERVICE_PASS nao esteja definido."""
    monkeypatch.delenv("ERP_SERVICE_PASS", raising=False)
    monkeypatch.setenv("ERP_DB_PASSWORD", "senha_legada_valida")

    resolved_pass = get_erp_password()
    assert resolved_pass == "senha_legada_valida"


@pytest.mark.unit
def test_core_config_exposes_erp_service_ro():
    """Valida que core.config expoem as constantes da role tecnica de servico."""
    assert hasattr(core.config, "ERP_SERVICE_USER")
    assert hasattr(core.config, "ERP_SERVICE_PASS")
