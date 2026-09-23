"""Add user authorized programs and team governance with multiple leaders.

Revision ID: c7d8e9f0a1b2
Revises: a1b2c3d4e5f6
Create Date: 2026-09-23 12:55:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "c7d8e9f0a1b2"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create rol_equipo enum
    rol_equipo_enum = postgresql.ENUM(
        "LIDER",
        "CO_LIDER",
        "INSTRUCTOR",
        "TRANSVERSAL",
        "COLABORADOR",
        name="rol_equipo",
        create_type=False,
    )
    rol_equipo_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create usuarios_programas_autorizados table
    op.create_table(
        "usuarios_programas_autorizados",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "usuario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "programa_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("programas_formacion.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asignado_por",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "fecha_asignacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "activo",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
        sa.UniqueConstraint(
            "usuario_id",
            "programa_id",
            name="uq_usuario_programa_autorizado",
        ),
    )
    op.create_index(
        "ix_usuarios_programas_usuario_id",
        "usuarios_programas_autorizados",
        ["usuario_id"],
    )
    op.create_index(
        "ix_usuarios_programas_programa_id",
        "usuarios_programas_autorizados",
        ["programa_id"],
    )
    op.create_index(
        "ix_usuarios_programas_activo",
        "usuarios_programas_autorizados",
        ["activo"],
    )

    # 3. Add columns to equipos_ejecutores
    op.add_column(
        "equipos_ejecutores",
        sa.Column(
            "programa_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("programas_formacion.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.add_column(
        "equipos_ejecutores",
        sa.Column(
            "max_members",
            sa.Integer(),
            server_default="5",
            nullable=False,
        ),
    )
    op.add_column(
        "equipos_ejecutores",
        sa.Column(
            "leaders_can_manage_members",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
    )
    op.add_column(
        "equipos_ejecutores",
        sa.Column(
            "descripcion",
            sa.Text(),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_equipos_ejecutores_programa_id",
        "equipos_ejecutores",
        ["programa_id"],
    )

    # 4. Add rol_equipo to equipos_ejecutores_miembros
    op.add_column(
        "equipos_ejecutores_miembros",
        sa.Column(
            "rol_equipo",
            rol_equipo_enum,
            server_default="INSTRUCTOR",
            nullable=False,
        ),
    )
    op.create_index(
        "ix_equipos_ejecutores_miembros_rol_equipo",
        "equipos_ejecutores_miembros",
        ["rol_equipo"],
    )


def downgrade() -> None:
    op.drop_index("ix_equipos_ejecutores_miembros_rol_equipo", table_name="equipos_ejecutores_miembros")
    op.drop_column("equipos_ejecutores_miembros", "rol_equipo")

    op.drop_index("ix_equipos_ejecutores_programa_id", table_name="equipos_ejecutores")
    op.drop_column("equipos_ejecutores", "descripcion")
    op.drop_column("equipos_ejecutores", "leaders_can_manage_members")
    op.drop_column("equipos_ejecutores", "max_members")
    op.drop_column("equipos_ejecutores", "programa_id")

    op.drop_index("ix_usuarios_programas_activo", table_name="usuarios_programas_autorizados")
    op.drop_index("ix_usuarios_programas_programa_id", table_name="usuarios_programas_autorizados")
    op.drop_index("ix_usuarios_programas_usuario_id", table_name="usuarios_programas_autorizados")
    op.drop_table("usuarios_programas_autorizados")

    rol_equipo_enum = postgresql.ENUM(
        "LIDER",
        "CO_LIDER",
        "INSTRUCTOR",
        "TRANSVERSAL",
        "COLABORADOR",
        name="rol_equipo",
    )
    rol_equipo_enum.drop(op.get_bind(), checkfirst=True)
