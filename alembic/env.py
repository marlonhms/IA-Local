"""
Ambiente de execucao de migracoes Alembic da AURA (P2-1).
Suporta execucao em SQLite local (aura_local_memory.db / aura_sessions.db)
e PostgreSQL vetorial (posto_ai), via SQLAlchemy/Alembic ou AuraMigrationManager.
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path
from urllib.parse import quote_plus

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import BASE_DIR, DB_VECTOR_CONFIG


def get_database_url(target_db: str | None = None) -> str:
    """
    Resolve a URL de conexao para as migracoes da AURA.
    Prioridade:
    1. Argumento explicito target_db ('sqlite', 'postgres' ou URL direta)
    2. Variavel de ambiente AURA_MIGRATION_DB_URL
    3. SQLite local padrao (data/aura_sessions.db)
    """
    explicit = target_db or os.getenv("AURA_MIGRATION_DB_URL", "").strip()
    if explicit:
        if explicit == "postgres":
            user = quote_plus(str(DB_VECTOR_CONFIG.get("user", "postgres")))
            password = quote_plus(str(DB_VECTOR_CONFIG.get("password", "")))
            host = DB_VECTOR_CONFIG.get("host", "localhost")
            port = DB_VECTOR_CONFIG.get("port", 5433)
            dbname = DB_VECTOR_CONFIG.get("dbname", "posto_ai")
            return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
        if explicit == "sqlite":
            db_file = BASE_DIR / "data" / "aura_sessions.db"
            return f"sqlite:///{db_file.as_posix()}"
        return explicit

    default_sqlite = BASE_DIR / "data" / "aura_sessions.db"
    return f"sqlite:///{default_sqlite.as_posix()}"


def run_migrations_via_manager(db_url: str | None = None) -> list[str]:
    """
    Executa migracoes ate 'head' usando o AuraMigrationManager nativo,
    sem exigir instancia externa do SQLAlchemy caso indisponivel no ambiente.
    """
    from core.migrations import AuraMigrationManager

    url = get_database_url(db_url)
    manager = AuraMigrationManager(db_url=url)
    return manager.upgrade("head")


def _run_alembic_context() -> None:
    """Executa o contexto padrao do Alembic CLI quando invocado via comando 'alembic'."""
    try:
        from sqlalchemy import engine_from_config, pool

        from alembic import context
    except ImportError:
        run_migrations_via_manager()
        return

    try:
        config = context.config
    except (AttributeError, NameError, RuntimeError):
        return

    if getattr(config, "config_file_name", None) is not None:
        fileConfig(config.config_file_name)

    resolved_url = get_database_url()
    config.set_main_option("sqlalchemy.url", resolved_url)
    target_metadata = None

    if context.is_offline_mode():
        context.configure(
            url=resolved_url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
        with context.begin_transaction():
            context.run_migrations()
    else:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()


if __name__ == "env_py":
    _run_alembic_context()
