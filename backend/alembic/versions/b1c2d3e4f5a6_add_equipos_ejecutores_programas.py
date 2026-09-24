"""Add authorized training programs table to executing teams.

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-09-24 08:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "b1c2d3e4f5a6"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "equipos_ejecutores_programas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "equipo_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("equipos_ejecutores.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "programa_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("programas_formacion.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("codigo_programa", sa.String(100), nullable=False),
        sa.Column("nombre_programa", sa.Text(), nullable=False),
        sa.Column("activo", sa.Boolean(), default=True, server_default="true", nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("equipo_id", "codigo_programa", name="uq_equipo_codigo_programa"),
    )

    op.create_index(
        "ix_equipos_ejecutores_programas_equipo_id",
        "equipos_ejecutores_programas",
        ["equipo_id"],
    )
    op.create_index(
        "ix_equipos_ejecutores_programas_programa_id",
        "equipos_ejecutores_programas",
        ["programa_id"],
    )
    op.create_index(
        "ix_equipos_ejecutores_programas_codigo",
        "equipos_ejecutores_programas",
        ["codigo_programa"],
    )

    # Backfill authorized programs from existing processes
    op.execute(
        """
        INSERT INTO equipos_ejecutores_programas (id, equipo_id, programa_id, codigo_programa, nombre_programa, activo, fecha_creacion, fecha_actualizacion)
        SELECT gen_random_uuid(), p.equipo_ejecutor_id, p.programa_id, prog.codigo_programa, prog.nombre_programa, true, now(), now()
        FROM procesos_curriculares p
        JOIN programas_formacion prog ON p.programa_id = prog.id
        WHERE p.equipo_ejecutor_id IS NOT NULL AND p.programa_id IS NOT NULL
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_equipos_ejecutores_programas_codigo", table_name="equipos_ejecutores_programas")
    op.drop_index("ix_equipos_ejecutores_programas_programa_id", table_name="equipos_ejecutores_programas")
    op.drop_index("ix_equipos_ejecutores_programas_equipo_id", table_name="equipos_ejecutores_programas")
    op.drop_table("equipos_ejecutores_programas")
