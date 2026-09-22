"""Add creado_por_id column to especialidades table for ownership tracking.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-22 13:15:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [c["name"] for c in insp.get_columns("especialidades")]

    if "creado_por_id" not in columns:
        op.add_column(
            "especialidades",
            sa.Column("creado_por_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            "fk_especialidades_creado_por_id_usuarios",
            "especialidades",
            "usuarios",
            ["creado_por_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(
            "ix_especialidades_creado_por_id",
            "especialidades",
            ["creado_por_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_especialidades_creado_por_id", table_name="especialidades")
    op.drop_constraint("fk_especialidades_creado_por_id_usuarios", "especialidades", type_="foreignkey")
    op.drop_column("especialidades", "creado_por_id")
