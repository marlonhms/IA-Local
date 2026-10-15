"""Revisao inicial do esquema declarativo da AURA (P2-1).

Revision ID: 0001_initial
Revises: None
Create Date: 2026-10-15 12:00:00
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

from typing import Any

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

UPGRADE_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS aura_sessions (
        session_id TEXT PRIMARY KEY,
        tenant_id TEXT,
        filial_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS aura_messages (
        id INTEGER PRIMARY KEY,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        intent TEXT,
        metadata TEXT,
        tool_call_id TEXT,
        name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES aura_sessions(session_id)
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_aura_messages_session
    ON aura_messages(session_id, created_at);
    """,
    """
    CREATE TABLE IF NOT EXISTS aura_action_vouchers (
        voucher_id TEXT PRIMARY KEY,
        action_id TEXT UNIQUE NOT NULL,
        tool_call_id TEXT NOT NULL,
        session_id TEXT,
        action_name TEXT NOT NULL,
        action_type TEXT DEFAULT 'mutation',
        operator_id TEXT,
        status TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        payload TEXT,
        details TEXT,
        signature TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_aura_vouchers_action
    ON aura_action_vouchers(action_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_aura_vouchers_session
    ON aura_action_vouchers(session_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS aura_action_audit_log (
        audit_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        session_id TEXT,
        tool_call_id TEXT NOT NULL,
        action_id TEXT NOT NULL,
        action_name TEXT NOT NULL,
        action_type TEXT NOT NULL,
        operator_id TEXT,
        operator_role TEXT,
        authorized INTEGER NOT NULL,
        status TEXT NOT NULL,
        details TEXT,
        client_ip TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_aura_audit_action
    ON aura_action_audit_log(action_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS aura_telemetry_metrics (
        id INTEGER PRIMARY KEY,
        timestamp TEXT NOT NULL,
        metric_type TEXT NOT NULL,
        metric_value REAL NOT NULL,
        session_id TEXT,
        tool_call_id TEXT,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_aura_telemetry_metrics_type
    ON aura_telemetry_metrics(metric_type);
    """,
    """
    CREATE TABLE IF NOT EXISTS aura_sre_telemetry (
        id INTEGER PRIMARY KEY,
        timestamp TEXT NOT NULL,
        metric_type TEXT NOT NULL,
        metric_value REAL NOT NULL,
        session_id TEXT,
        tool_call_id TEXT,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS intencoes_vetores (
        id INTEGER PRIMARY KEY,
        intencao VARCHAR(80) NOT NULL,
        descricao TEXT,
        exemplo_frase TEXT NOT NULL,
        embedding TEXT,
        codfilial INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_intencoes_vetores_intencao
    ON intencoes_vetores(intencao);
    """,
    """
    CREATE TABLE IF NOT EXISTS produtos_vetores (
        codpro VARCHAR(10) PRIMARY KEY,
        nompro VARCHAR(120) NOT NULL,
        grupo VARCHAR(50),
        codbar VARCHAR(20),
        unidade VARCHAR(10),
        preco NUMERIC(15, 2),
        texto_busca TEXT NOT NULL,
        embedding TEXT,
        hash_md5 VARCHAR(32),
        atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_produtos_vetores_hash_md5
    ON produtos_vetores(hash_md5);
    """,
    """
    CREATE TABLE IF NOT EXISTS conhecimento_operacional (
        id INTEGER PRIMARY KEY,
        modulo VARCHAR(80) NOT NULL,
        topico VARCHAR(120) NOT NULL,
        titulo VARCHAR(200) NOT NULL,
        subtitulo TEXT,
        conteudo TEXT NOT NULL,
        elementos_ui TEXT,
        ui_action VARCHAR(120),
        tags TEXT,
        embedding TEXT,
        hash_md5 VARCHAR(32),
        atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_conhecimento_operacional_topico
    ON conhecimento_operacional(modulo, topico);
    """,
]

DOWNGRADE_STATEMENTS: list[str] = [
    "DROP INDEX IF EXISTS idx_conhecimento_operacional_topico;",
    "DROP TABLE IF EXISTS conhecimento_operacional;",
    "DROP INDEX IF EXISTS idx_produtos_vetores_hash_md5;",
    "DROP TABLE IF EXISTS produtos_vetores;",
    "DROP INDEX IF EXISTS idx_intencoes_vetores_intencao;",
    "DROP TABLE IF EXISTS intencoes_vetores;",
    "DROP TABLE IF EXISTS aura_sre_telemetry;",
    "DROP INDEX IF EXISTS idx_aura_telemetry_metrics_type;",
    "DROP TABLE IF EXISTS aura_telemetry_metrics;",
    "DROP INDEX IF EXISTS idx_aura_audit_action;",
    "DROP TABLE IF EXISTS aura_action_audit_log;",
    "DROP INDEX IF EXISTS idx_aura_vouchers_session;",
    "DROP INDEX IF EXISTS idx_aura_vouchers_action;",
    "DROP TABLE IF EXISTS aura_action_vouchers;",
    "DROP INDEX IF EXISTS idx_aura_messages_session;",
    "DROP TABLE IF EXISTS aura_messages;",
    "DROP TABLE IF EXISTS aura_sessions;",
]


def _run_statements(statements: list[str], connection: Any = None) -> None:
    """Executa lista de instrucoes DDL via conexao injetada ou contexto Alembic."""
    if connection is not None:
        if hasattr(connection, "cursor"):
            cur = connection.cursor()
            try:
                for stmt in statements:
                    cur.execute(stmt)
            finally:
                cur.close()
        else:
            for stmt in statements:
                connection.execute(stmt)
        return

    from alembic import op

    for stmt in statements:
        op.execute(stmt)


def upgrade(connection: Any = None) -> None:
    """Aplica as tabelas base da AURA de forma idempotente."""
    _run_statements(UPGRADE_STATEMENTS, connection=connection)


def downgrade(connection: Any = None) -> None:
    """Reverte as tabelas base da revisao 0001_initial."""
    _run_statements(DOWNGRADE_STATEMENTS, connection=connection)
