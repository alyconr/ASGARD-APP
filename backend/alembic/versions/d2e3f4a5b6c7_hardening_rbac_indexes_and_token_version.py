"""Hardening RBAC indexes and token version for session revocation.

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-09-19 13:22:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add token_version to usuarios
    op.add_column(
        "usuarios",
        sa.Column("token_version", sa.Integer(), server_default="1", nullable=False),
    )

    # 2. Add performance & integrity indexes on procesos_curriculares
    op.create_index(
        "ix_procesos_curriculares_programa_id",
        "procesos_curriculares",
        ["programa_id"],
        unique=False,
    )
    op.create_index(
        "ix_procesos_curriculares_proyecto_id",
        "procesos_curriculares",
        ["proyecto_id"],
        unique=False,
    )

    # 3. Add index on active membership for dynamic scope evaluation
    op.create_index(
        "ix_equipos_ejecutores_miembros_activo",
        "equipos_ejecutores_miembros",
        ["activo"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_equipos_ejecutores_miembros_activo", table_name="equipos_ejecutores_miembros")
    op.drop_index("ix_procesos_curriculares_proyecto_id", table_name="procesos_curriculares")
    op.drop_index("ix_procesos_curriculares_programa_id", table_name="procesos_curriculares")
    op.drop_column("usuarios", "token_version")
