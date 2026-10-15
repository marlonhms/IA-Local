"""Segunda revisao declarativa: Compliance Opt-In e Automacoes (P2-1).

Revision ID: 0002_compliance
Revises: 0001_initial
Create Date: 2026-10-15 12:30:00
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

from typing import Any

revision: str = "0002_compliance"
down_revision: str | None = "0001_initial"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

UPGRADE_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS aura_compliance_optin (
        optin_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        filial_id TEXT NOT NULL,
        operator_id TEXT NOT NULL,
        operator_role TEXT NOT NULL,
        scope TEXT NOT NULL,
        accepted INTEGER NOT NULL DEFAULT 1,
        policy_version TEXT NOT NULL DEFAULT '1.1',
        signature_hash TEXT NOT NULL,
        accepted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        revoked_at TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_aura_compliance_tenant_filial
    ON aura_compliance_optin(tenant_id, filial_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_aura_compliance_operator
    ON aura_compliance_optin(operator_id, accepted);
    """,
    """
    CREATE TABLE IF NOT EXISTS aura_automations (
        automation_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL DEFAULT 'default',
        filial_id TEXT NOT NULL DEFAULT '1',
        master_enabled INTEGER NOT NULL DEFAULT 0,
        shift_audit_json TEXT NOT NULL,
        tank_alerts_json TEXT NOT NULL,
        pumps_audit_json TEXT NOT NULL,
        notifications_json TEXT NOT NULL,
        updated_by TEXT NOT NULL DEFAULT 'gestor',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_aura_automations_tenant_filial
    ON aura_automations(tenant_id, filial_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_aura_automations_master_enabled
    ON aura_automations(master_enabled);
    """,
]

DOWNGRADE_STATEMENTS: list[str] = [
    "DROP INDEX IF EXISTS idx_aura_automations_master_enabled;",
    "DROP INDEX IF EXISTS idx_aura_automations_tenant_filial;",
    "DROP TABLE IF EXISTS aura_automations;",
    "DROP INDEX IF EXISTS idx_aura_compliance_operator;",
    "DROP INDEX IF EXISTS idx_aura_compliance_tenant_filial;",
    "DROP TABLE IF EXISTS aura_compliance_optin;",
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
    """Aplica as tabelas de compliance opt-in e automacoes da AURA."""
    _run_statements(UPGRADE_STATEMENTS, connection=connection)


def downgrade(connection: Any = None) -> None:
    """Reverte as estruturas da revisao 0002_compliance."""
    _run_statements(DOWNGRADE_STATEMENTS, connection=connection)
