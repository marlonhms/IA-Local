"""Terceira revisao declarativa: Simulacao What-If e Memoria Persistente do Negocio (Fase 1).

Revision ID: 0003_simulation_memory
Revises: 0002_compliance
Create Date: 2026-11-26 15:35:00
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

from typing import Any

revision: str = "0003_simulation_memory"
down_revision: str | None = "0002_compliance"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

UPGRADE_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS business_profile_snapshots (
        snapshot_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        pack_id TEXT NOT NULL,
        reference_period TEXT NOT NULL,
        means_json TEXT NOT NULL,
        std_devs_json TEXT NOT NULL,
        seasonality_json TEXT NOT NULL,
        abc_curve_json TEXT NOT NULL,
        sample_size INTEGER NOT NULL DEFAULT 0,
        computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_bps_tenant_pack_computed
    ON business_profile_snapshots (tenant_id, pack_id, computed_at);
    """,
    """
    CREATE TABLE IF NOT EXISTS business_memory_rules (
        rule_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        pack_id TEXT NOT NULL,
        rule_key TEXT NOT NULL,
        metric TEXT NOT NULL,
        operator TEXT NOT NULL CHECK (operator IN ('>=', '<=', '>', '<', '==', '!=', 'between')),
        threshold_value REAL NOT NULL,
        threshold_upper REAL,
        severity TEXT NOT NULL DEFAULT 'HIGH' CHECK (severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'INFO')),
        status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'active', 'rejected')),
        origin TEXT NOT NULL,
        author TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_bmr_tenant_pack_status
    ON business_memory_rules (tenant_id, pack_id, status);
    """,
    """
    CREATE TABLE IF NOT EXISTS operator_intent_signals (
        signal_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        pack_id TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        metric_key TEXT NOT NULL,
        topic_key TEXT NOT NULL,
        intent_name TEXT NOT NULL,
        hit_count INTEGER NOT NULL DEFAULT 1,
        first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_ois_tenant_pack_topic
    ON operator_intent_signals (tenant_id, pack_id, topic_key, last_seen_at);
    """,
    """
    CREATE TABLE IF NOT EXISTS simulation_snapshots (
        simulation_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        pack_id TEXT NOT NULL,
        scenario_type TEXT NOT NULL,
        horizon_days INTEGER NOT NULL CHECK (horizon_days IN (30, 60, 90)),
        baseline_t0_json TEXT NOT NULL,
        shock_params_json TEXT NOT NULL,
        p10_value REAL NOT NULL,
        p50_value REAL NOT NULL,
        p90_value REAL NOT NULL,
        sensitivity_json TEXT NOT NULL,
        violated_rules_json TEXT NOT NULL,
        seed INTEGER NOT NULL,
        iterations INTEGER NOT NULL DEFAULT 5000,
        created_by TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        realized_outcome_json TEXT,
        realized_at TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_sim_snap_tenant_pack_created
    ON simulation_snapshots (tenant_id, pack_id, created_at);
    """,
]

DOWNGRADE_STATEMENTS: list[str] = [
    "DROP INDEX IF EXISTS idx_sim_snap_tenant_pack_created;",
    "DROP TABLE IF EXISTS simulation_snapshots;",
    "DROP INDEX IF EXISTS idx_ois_tenant_pack_topic;",
    "DROP TABLE IF EXISTS operator_intent_signals;",
    "DROP INDEX IF EXISTS idx_bmr_tenant_pack_status;",
    "DROP TABLE IF EXISTS business_memory_rules;",
    "DROP INDEX IF EXISTS idx_bps_tenant_pack_computed;",
    "DROP TABLE IF EXISTS business_profile_snapshots;",
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
    """Aplica as tabelas de memoria do negocio e simulacao What-If da AURA."""
    _run_statements(UPGRADE_STATEMENTS, connection=connection)


def downgrade(connection: Any = None) -> None:
    """Reverte as estruturas da revisao 0003_simulation_memory."""
    _run_statements(DOWNGRADE_STATEMENTS, connection=connection)
