"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
Zero travessoes em todo o arquivo.
"""

from __future__ import annotations

from typing import Any

# Identificadores de revisao utilizados pelo Alembic e pelo AuraMigrationManager
revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: tuple[str, ...] | None = ${repr(branch_labels)}
depends_on: tuple[str, ...] | None = ${repr(depends_on)}


def upgrade(connection: Any = None) -> None:
    ${upgrades if upgrades else "pass"}


def downgrade(connection: Any = None) -> None:
    ${downgrades if downgrades else "pass"}
