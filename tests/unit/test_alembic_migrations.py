"""
Testes unitarios para o Versionamento Declarativo de Esquemas com Alembic (P2-1).
Valida alembic.ini, alembic/env.py, revisoes 0001_initial e 0002_compliance,
idempotencia de upgrade/downgrade, tabela alembic_version e ausencia de travessoes.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest

from config.settings import BASE_DIR
from core.migrations import (
    AuraMigrationManager,
    get_database_url,
    run_startup_migrations,
)


@pytest.mark.unit
def test_alembic_ini_and_templates_exist() -> None:
    """Verifica a presenca e configuracao correta de alembic.ini, env.py e script.py.mako."""
    ini_path = BASE_DIR / "alembic.ini"
    env_path = BASE_DIR / "alembic" / "env.py"
    mako_path = BASE_DIR / "alembic" / "script.py.mako"

    assert ini_path.exists(), "alembic.ini deve existir na raiz do projeto"
    assert env_path.exists(), "alembic/env.py deve existir"
    assert mako_path.exists(), "alembic/script.py.mako deve existir"

    parser = configparser.ConfigParser()
    parser.read(ini_path, encoding="utf-8")
    assert parser.has_section("alembic")
    assert parser.get("alembic", "script_location") == "alembic"
    assert "sqlite" in parser.get("alembic", "sqlalchemy.url")


@pytest.mark.unit
def test_env_get_database_url_targets() -> None:
    """Valida a resolucao de URLs de banco para SQLite e PostgreSQL."""
    sqlite_url = get_database_url("sqlite")
    assert sqlite_url.startswith("sqlite:///")
    assert "aura_sessions.db" in sqlite_url

    pg_url = get_database_url("postgres")
    assert pg_url.startswith("postgresql+psycopg2://")
    assert "posto_ai" in pg_url

    custom_url = get_database_url("sqlite:///:memory:")
    assert custom_url == "sqlite:///:memory:"


@pytest.mark.unit
def test_revision_history_and_topology() -> None:
    """Garante que as revisoes 0001_initial e 0002_compliance formam uma cadeia linear integra."""
    manager = AuraMigrationManager(db_path=":memory:")
    try:
        history = manager.get_revision_history()
        assert len(history) >= 2
        assert history[0]["revision"] == "0001_initial"
        assert history[0]["down_revision"] is None
        assert history[0]["applied"] is False

        assert history[1]["revision"] == "0002_compliance"
        assert history[1]["down_revision"] == "0001_initial"
        assert history[1]["applied"] is False
    finally:
        manager.close()


@pytest.mark.unit
def test_idempotent_upgrade_head_and_alembic_version_table(tmp_path: Path) -> None:
    """
    Valida que upgrade('head') cria todas as tabelas declaradas, grava a revisao
    em alembic_version e e 100% idempotente em chamadas subsequentes.
    """
    db_file = tmp_path / "aura_test_migrations.db"
    manager = AuraMigrationManager(db_path=db_file)

    assert manager.get_current_revision() is None

    applied_first = manager.upgrade("head")
    assert applied_first == ["0001_initial", "0002_compliance"]
    assert manager.get_current_revision() == "0002_compliance"

    # Segunda execucao deve ser no-op (idempotente)
    applied_second = manager.upgrade("head")
    assert applied_second == []
    assert manager.get_current_revision() == "0002_compliance"

    # Verifica integridade de todas as tabelas gerenciadas pela AURA
    integrity = manager.verify_schema_integrity()
    assert integrity["valid"] is True
    assert integrity["current_revision"] == "0002_compliance"
    assert integrity["missing_tables"] == []

    expected_tables = {
        "alembic_version",
        "aura_sessions",
        "aura_messages",
        "aura_action_vouchers",
        "aura_action_audit_log",
        "aura_telemetry_metrics",
        "intencoes_vetores",
        "produtos_vetores",
        "conhecimento_operacional",
        "aura_compliance_optin",
        "aura_automations",
    }
    assert expected_tables.issubset(set(integrity["present_tables"]))


@pytest.mark.unit
def test_stepwise_upgrade_and_downgrade_cycle() -> None:
    """Testa migracao passo a passo (0001 -> 0002 -> 0001 -> base) em SQLite em memoria."""
    manager = AuraMigrationManager(db_path=":memory:")
    try:
        # 1. Upgrade apenas para 0001_initial
        applied = manager.upgrade("0001_initial")
        assert applied == ["0001_initial"]
        assert manager.get_current_revision() == "0001_initial"
        tables_v1 = set(manager.list_existing_tables())
        assert "aura_sessions" in tables_v1
        assert "produtos_vetores" in tables_v1
        assert "aura_compliance_optin" not in tables_v1

        # 2. Upgrade para head (0002_compliance)
        applied_v2 = manager.upgrade("head")
        assert applied_v2 == ["0002_compliance"]
        assert manager.get_current_revision() == "0002_compliance"
        tables_v2 = set(manager.list_existing_tables())
        assert "aura_compliance_optin" in tables_v2
        assert "aura_automations" in tables_v2

        # 3. Downgrade parcial para 0001_initial
        reverted_v2 = manager.downgrade("0001_initial")
        assert reverted_v2 == ["0002_compliance"]
        assert manager.get_current_revision() == "0001_initial"
        tables_after_down1 = set(manager.list_existing_tables())
        assert "aura_compliance_optin" not in tables_after_down1
        assert "aura_automations" not in tables_after_down1
        assert "aura_sessions" in tables_after_down1

        # 4. Downgrade completo para base
        reverted_base = manager.downgrade("base")
        assert reverted_base == ["0001_initial"]
        assert manager.get_current_revision() is None
        tables_after_base = set(manager.list_existing_tables())
        assert "aura_sessions" not in tables_after_base
        assert "alembic_version" in tables_after_base
    finally:
        manager.close()


@pytest.mark.unit
def test_run_startup_migrations_helper(tmp_path: Path) -> None:
    """Verifica a funcao utilitaria de startup run_startup_migrations."""
    db_file = tmp_path / "startup_aura.db"
    result = run_startup_migrations(db_path=db_file)
    assert result["valid"] is True
    assert result["current_revision"] == "0002_compliance"
    assert result["applied_revisions"] == ["0001_initial", "0002_compliance"]


@pytest.mark.unit
def test_zero_em_dashes_in_migration_files() -> None:
    """Garante conformidade estrita com a regra de zero travessoes nos arquivos de P2-1."""
    files_to_check = [
        BASE_DIR / "alembic.ini",
        BASE_DIR / "alembic" / "env.py",
        BASE_DIR / "alembic" / "script.py.mako",
        BASE_DIR / "alembic" / "versions" / "0001_initial_aura_schema.py",
        BASE_DIR / "alembic" / "versions" / "0002_compliance_and_automations.py",
        BASE_DIR / "core" / "migrations.py",
        Path(__file__),
    ]
    for path in files_to_check:
        content = path.read_text(encoding="utf-8")
        assert "\u2014" not in content, f"Travessao (em-dash) encontrado em {path}"
        assert "\u2013" not in content, f"Meia-risca (en-dash) encontrada em {path}"
