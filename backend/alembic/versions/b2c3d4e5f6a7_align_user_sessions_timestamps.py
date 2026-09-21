"""Align user_sessions timestamps to fecha_creacion and fecha_actualizacion.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-21 10:15:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [c["name"] for c in insp.get_columns("user_sessions")]

    if "created_at" in columns and "fecha_creacion" not in columns:
        op.alter_column("user_sessions", "created_at", new_column_name="fecha_creacion")
    elif "fecha_creacion" not in columns:
        op.add_column(
            "user_sessions",
            sa.Column(
                "fecha_creacion",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )

    if "updated_at" in columns and "fecha_actualizacion" not in columns:
        op.alter_column("user_sessions", "updated_at", new_column_name="fecha_actualizacion")
    elif "fecha_actualizacion" not in columns:
        op.add_column(
            "user_sessions",
            sa.Column(
                "fecha_actualizacion",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = [c["name"] for c in insp.get_columns("user_sessions")]

    if "fecha_creacion" in columns and "created_at" not in columns:
        op.alter_column("user_sessions", "fecha_creacion", new_column_name="created_at")

    if "fecha_actualizacion" in columns and "updated_at" not in columns:
        op.alter_column("user_sessions", "fecha_actualizacion", new_column_name="updated_at")
