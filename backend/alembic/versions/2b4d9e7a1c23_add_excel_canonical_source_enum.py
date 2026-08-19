"""Add document evidence and canonical Excel load sources.

Revision ID: 2b4d9e7a1c23
Revises: 9b30c7f3d4a1
Create Date: 2026-05-07 00:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "2b4d9e7a1c23"
down_revision = "9b30c7f3d4a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add enum values used by TASK-08.5."""
    op.execute(
        "ALTER TYPE tipo_fuente_cargue ADD VALUE IF NOT EXISTS 'PDF_EVIDENCIA'",
    )
    op.execute(
        "ALTER TYPE tipo_fuente_cargue ADD VALUE IF NOT EXISTS 'EXCEL_CANONICO'",
    )


def downgrade() -> None:
    """PostgreSQL enum values are intentionally not removed on downgrade."""
