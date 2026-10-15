"""
Gerenciador Declarativo de Migracoes de Esquemas da AURA (P2-1).
Executa migracoes estruturais baseadas nas revisoes de alembic/versions/ de forma
idempotente, mantendo o historico oficial na tabela alembic_version.
Compativel com SQLite (:memory: ou arquivo) e PostgreSQL (psycopg2).
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

import configparser
import importlib.util
import os
import sqlite3
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from config.settings import BASE_DIR, DB_VECTOR_CONFIG
from core.logger import logger

EXPECTED_TABLES_BY_REVISION: dict[str, list[str]] = {
    "0001_initial": [
        "aura_sessions",
        "aura_messages",
        "aura_action_vouchers",
        "aura_action_audit_log",
        "aura_telemetry_metrics",
        "intencoes_vetores",
        "produtos_vetores",
        "conhecimento_operacional",
    ],
    "0002_compliance": [
        "aura_compliance_optin",
        "aura_automations",
    ],
}


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


@dataclass(frozen=True)
class RevisionScript:
    """Representa um script de revisao declarativa carregado de alembic/versions."""

    revision: str
    down_revision: str | None
    filename: str
    doc: str
    upgrade_fn: Callable[[Any], None]
    downgrade_fn: Callable[[Any], None]


class AuraMigrationManager:
    """
    Motor declarativo de migracoes de banco de dados compativel com o padrao Alembic.
    Gerencia upgrade, downgrade, inspecao de revisao atual e verificacao de integridade.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        db_url: str | None = None,
        connection: Any = None,
        versions_dir: str | Path | None = None,
        ini_path: str | Path | None = None,
    ) -> None:
        self.ini_path = Path(ini_path) if ini_path else BASE_DIR / "alembic.ini"
        self.versions_dir = (
            Path(versions_dir)
            if versions_dir
            else self._resolve_versions_dir_from_ini()
        )
        self._external_conn = connection
        self._shared_memory_conn: sqlite3.Connection | None = None

        resolved_target = self._resolve_db_target(db_path=db_path, db_url=db_url)
        self.db_url = resolved_target["db_url"]
        self.db_path = resolved_target["db_path"]
        self.dialect = resolved_target["dialect"]

        if self._external_conn is None and self.dialect == "sqlite" and self.db_path == ":memory:":
            self._shared_memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared_memory_conn.row_factory = sqlite3.Row

    def _resolve_versions_dir_from_ini(self) -> Path:
        """Le script_location do alembic.ini ou utiliza o diretorio padrao alembic/versions."""
        if self.ini_path.exists():
            parser = configparser.ConfigParser()
            parser.read(self.ini_path, encoding="utf-8")
            if parser.has_option("alembic", "script_location"):
                script_loc = parser.get("alembic", "script_location").strip()
                return (self.ini_path.parent / script_loc / "versions").resolve()
        return (BASE_DIR / "alembic" / "versions").resolve()

    def _resolve_db_target(
        self, db_path: str | Path | None, db_url: str | None
    ) -> dict[str, str]:
        """Normaliza o alvo de conexao em db_url, db_path e dialect."""
        if db_url:
            clean_url = db_url.strip()
            if clean_url.startswith("postgres"):
                return {"db_url": clean_url, "db_path": "", "dialect": "postgresql"}
            if clean_url.startswith("sqlite:///"):
                raw_path = clean_url[len("sqlite:///") :]
                if raw_path in ("", ":memory:"):
                    return {
                        "db_url": "sqlite:///:memory:",
                        "db_path": ":memory:",
                        "dialect": "sqlite",
                    }
                return {
                    "db_url": clean_url,
                    "db_path": str(Path(raw_path)),
                    "dialect": "sqlite",
                }

        if db_path is not None:
            raw_str = str(db_path).strip()
            if raw_str == ":memory:":
                return {
                    "db_url": "sqlite:///:memory:",
                    "db_path": ":memory:",
                    "dialect": "sqlite",
                }
            resolved = Path(raw_str)
            resolved.parent.mkdir(parents=True, exist_ok=True)
            return {
                "db_url": f"sqlite:///{resolved.as_posix()}",
                "db_path": str(resolved),
                "dialect": "sqlite",
            }

        default_file = BASE_DIR / "data" / "aura_sessions.db"
        default_file.parent.mkdir(parents=True, exist_ok=True)
        return {
            "db_url": f"sqlite:///{default_file.as_posix()}",
            "db_path": str(default_file),
            "dialect": "sqlite",
        }

    @contextmanager
    def _connection(self):
        """Fornece conexao transacional segura para SQLite ou PostgreSQL."""
        if self._external_conn is not None:
            yield self._external_conn
            if hasattr(self._external_conn, "commit"):
                self._external_conn.commit()
            return

        if self._shared_memory_conn is not None:
            yield self._shared_memory_conn
            self._shared_memory_conn.commit()
            return

        if self.dialect == "postgresql":
            import psycopg2

            dsn = self.db_url.replace("postgresql+psycopg2://", "postgresql://")
            conn = psycopg2.connect(dsn)
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()
            return

        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _ensure_version_table(self, conn: Any) -> None:
        """Garante a criacao da tabela oficial alembic_version."""
        sql = """
        CREATE TABLE IF NOT EXISTS alembic_version (
            version_num VARCHAR(32) NOT NULL,
            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
        );
        """
        cur = conn.cursor()
        try:
            cur.execute(sql)
        finally:
            cur.close()

    def _load_revisions(self) -> list[RevisionScript]:
        """Carrega e ordena topologicamente todos os scripts de revisao em alembic/versions."""
        if not self.versions_dir.exists():
            return []

        by_down: dict[str | None, RevisionScript] = {}
        all_scripts: dict[str, RevisionScript] = {}

        for py_file in sorted(self.versions_dir.glob("*.py")):
            if py_file.name.startswith("__"):
                continue
            spec = importlib.util.spec_from_file_location(
                f"aura_alembic_rev_{py_file.stem}", py_file
            )
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            rev_id = getattr(module, "revision", None)
            if not rev_id:
                continue
            down_rev = getattr(module, "down_revision", None)
            doc_line = (getattr(module, "__doc__", "") or "").strip().splitlines()
            summary = doc_line[0] if doc_line else py_file.stem

            script = RevisionScript(
                revision=str(rev_id),
                down_revision=str(down_rev) if down_rev is not None else None,
                filename=py_file.name,
                doc=summary,
                upgrade_fn=module.upgrade,
                downgrade_fn=module.downgrade,
            )
            by_down[script.down_revision] = script
            all_scripts[script.revision] = script

        ordered: list[RevisionScript] = []
        current_down: str | None = None
        visited: set[str] = set()
        while current_down in by_down:
            nxt = by_down[current_down]
            if nxt.revision in visited:
                break
            ordered.append(nxt)
            visited.add(nxt.revision)
            current_down = nxt.revision

        for rev_id, script in all_scripts.items():
            if rev_id not in visited:
                ordered.append(script)

        return ordered

    def get_current_revision(self) -> str | None:
        """Retorna o identificador da revisao atualmente gravada em alembic_version."""
        with self._connection() as conn:
            self._ensure_version_table(conn)
            cur = conn.cursor()
            try:
                cur.execute("SELECT version_num FROM alembic_version LIMIT 1;")
                row = cur.fetchone()
                if not row:
                    return None
                return str(row[0])
            finally:
                cur.close()

    def _set_current_revision(self, conn: Any, version_num: str | None) -> None:
        """Atualiza de forma atomica o ponteiro de versao na tabela alembic_version."""
        self._ensure_version_table(conn)
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM alembic_version;")
            if version_num is not None:
                placeholder = "%s" if self.dialect == "postgresql" else "?"
                cur.execute(
                    f"INSERT INTO alembic_version (version_num) VALUES ({placeholder});",
                    (version_num,),
                )
        finally:
            cur.close()

    def get_revision_history(self) -> list[dict[str, Any]]:
        """Retorna a cadeia ordenada de revisoes e indica quais estao aplicadas."""
        revisions = self._load_revisions()
        current = self.get_current_revision()

        applied_set: set[str] = set()
        if current is not None:
            for rev in revisions:
                applied_set.add(rev.revision)
                if rev.revision == current:
                    break

        return [
            {
                "revision": rev.revision,
                "down_revision": rev.down_revision,
                "filename": rev.filename,
                "description": rev.doc,
                "applied": rev.revision in applied_set,
                "is_current_head": rev.revision == current,
            }
            for rev in revisions
        ]

    def upgrade(self, target: str = "head") -> list[str]:
        """
        Aplica de forma idempotente as revisoes pendentes ate a revisao alvo ('head' ou ID).
        Retorna a lista de IDs de revisoes efetivamente executadas nesta chamada.
        """
        revisions = self._load_revisions()
        if not revisions:
            return []

        target_rev = revisions[-1].revision if target == "head" else target
        known_ids = [r.revision for r in revisions]
        if target_rev not in known_ids:
            raise ValueError(f"Revisao de destino desconhecida para upgrade: {target}")

        current = self.get_current_revision()
        if current == target_rev:
            return []

        start_idx = 0
        if current is not None:
            if current not in known_ids:
                raise ValueError(f"Revisao atual no banco ({current}) nao consta no historico.")
            curr_idx = known_ids.index(current)
            target_idx = known_ids.index(target_rev)
            if curr_idx >= target_idx:
                return []
            start_idx = curr_idx + 1
        else:
            target_idx = known_ids.index(target_rev)

        to_apply = revisions[start_idx : target_idx + 1]
        applied: list[str] = []

        with self._connection() as conn:
            self._ensure_version_table(conn)
            for rev in to_apply:
                logger.info(f"Aplicando migracao Alembic: {rev.revision} ({rev.filename})")
                rev.upgrade_fn(conn)
                self._set_current_revision(conn, rev.revision)
                applied.append(rev.revision)

        return applied

    def downgrade(self, target: str | None = "base") -> list[str]:
        """
        Reverte de forma idempotente as revisoes aplicadas ate o estado alvo ('base', None ou ID).
        Retorna a lista de IDs de revisoes revertidas na ordem de execucao.
        """
        revisions = self._load_revisions()
        if not revisions:
            return []

        current = self.get_current_revision()
        if current is None:
            return []

        known_ids = [r.revision for r in revisions]
        if current not in known_ids:
            raise ValueError(f"Revisao atual ({current}) desconhecida.")

        curr_idx = known_ids.index(current)
        if target in ("base", None, ""):
            stop_idx = -1
        else:
            if target not in known_ids:
                raise ValueError(f"Revisao de destino desconhecida para downgrade: {target}")
            stop_idx = known_ids.index(target)

        if curr_idx <= stop_idx:
            return []

        reverted: list[str] = []
        with self._connection() as conn:
            self._ensure_version_table(conn)
            for idx in range(curr_idx, stop_idx, -1):
                rev = revisions[idx]
                logger.info(f"Revertendo migracao Alembic: {rev.revision} ({rev.filename})")
                rev.downgrade_fn(conn)
                self._set_current_revision(conn, rev.down_revision)
                reverted.append(rev.revision)

        return reverted

    def list_existing_tables(self) -> list[str]:
        """Lista todas as tabelas presentes no banco de dados configurado."""
        with self._connection() as conn:
            cur = conn.cursor()
            try:
                if self.dialect == "postgresql":
                    cur.execute(
                        """
                        SELECT tablename FROM pg_catalog.pg_tables
                        WHERE schemaname = 'public'
                        ORDER BY tablename;
                        """
                    )
                else:
                    cur.execute(
                        """
                        SELECT name FROM sqlite_master
                        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                        ORDER BY name;
                        """
                    )
                return [str(r[0]) for r in cur.fetchall()]
            finally:
                cur.close()

    def verify_schema_integrity(self) -> dict[str, Any]:
        """
        Audita a integridade do esquema atual comparando as tabelas existentes
        com as tabelas declaradas ate a revisao ativa em alembic_version.
        """
        current_rev = self.get_current_revision()
        present_tables = set(self.list_existing_tables())
        revisions = self._load_revisions()

        expected_tables: list[str] = ["alembic_version"]
        if current_rev is not None:
            for rev in revisions:
                expected_tables.extend(EXPECTED_TABLES_BY_REVISION.get(rev.revision, []))
                if rev.revision == current_rev:
                    break

        missing = [t for t in expected_tables if t not in present_tables]
        return {
            "valid": len(missing) == 0 and current_rev is not None,
            "current_revision": current_rev,
            "expected_tables": expected_tables,
            "present_tables": sorted(present_tables),
            "missing_tables": missing,
        }

    def close(self) -> None:
        """Fecha a conexao compartilhada em memoria caso ativa."""
        if self._shared_memory_conn is not None:
            self._shared_memory_conn.close()
            self._shared_memory_conn = None


def run_startup_migrations(db_path: str | Path | None = None) -> dict[str, Any]:
    """
    Rotina utilitaria de inicializacao para aplicar migracoes pendentes ate 'head'
    e retornar o diagnostico de integridade do esquema.
    """
    manager = AuraMigrationManager(db_path=db_path)
    applied = manager.upgrade("head")
    integrity = manager.verify_schema_integrity()
    return {
        "applied_revisions": applied,
        "current_revision": integrity["current_revision"],
        "valid": integrity["valid"],
    }
