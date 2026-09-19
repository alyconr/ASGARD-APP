"""add_rbac_and_process_scope

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
Create Date: 2026-09-19 12:00:00.000000

"""

from typing import Sequence, Union
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "b0c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Coordinaciones
    op.create_table(
        "coordinaciones",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coordinaciones_codigo", "coordinaciones", ["codigo"], unique=True)

    # 2. Especialidades
    op.create_table(
        "especialidades",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("coordinacion_id", sa.UUID(), nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["coordinacion_id"], ["coordinaciones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_especialidades_codigo", "especialidades", ["codigo"], unique=True)
    op.create_index("ix_especialidades_coordinacion_id", "especialidades", ["coordinacion_id"], unique=False)

    # 3. Roles
    op.create_table(
        "roles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("nombre", sa.String(length=50), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roles_nombre", "roles", ["nombre"], unique=True)

    # 4. Usuarios
    op.create_table(
        "usuarios",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("apellido", sa.String(length=100), nullable=False),
        sa.Column("telefono", sa.String(length=50), nullable=True),
        sa.Column("coordinacion_id", sa.UUID(), nullable=True),
        sa.Column("especialidad_id", sa.UUID(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["coordinacion_id"], ["coordinaciones.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["especialidad_id"], ["especialidades.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usuarios_email", "usuarios", ["email"], unique=True)
    op.create_index("ix_usuarios_coordinacion_id", "usuarios", ["coordinacion_id"], unique=False)
    op.create_index("ix_usuarios_especialidad_id", "usuarios", ["especialidad_id"], unique=False)

    # 5. Usuario_Roles
    op.create_table(
        "usuario_roles",
        sa.Column("usuario_id", sa.UUID(), nullable=False),
        sa.Column("rol_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["rol_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("usuario_id", "rol_id"),
    )
    op.create_index("ix_usuario_roles_rol_id", "usuario_roles", ["rol_id"], unique=False)
    op.create_index("ix_usuario_roles_usuario_id", "usuario_roles", ["usuario_id"], unique=False)

    # 6. Enums
    estado_equipo = postgresql.ENUM("ACTIVO", "INACTIVO", name="estado_equipo", create_type=False)
    estado_equipo.create(op.get_bind(), checkfirst=True)

    tipo_necesidad_proceso = postgresql.ENUM(
        "CREAR_PLANEACION", "ACTUALIZAR_PLANEACION", "CREAR_GUIA", "AJUSTAR_GUIA",
        name="tipo_necesidad_proceso", create_type=False
    )
    tipo_necesidad_proceso.create(op.get_bind(), checkfirst=True)

    estado_scope_proceso = postgresql.ENUM(
        "ASIGNADO", "SIN_ASIGNAR",
        name="estado_scope_proceso", create_type=False
    )
    estado_scope_proceso.create(op.get_bind(), checkfirst=True)

    # 7. Equipos Ejecutores
    op.create_table(
        "equipos_ejecutores",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("coordinacion_id", sa.UUID(), nullable=False),
        sa.Column("especialidad_id", sa.UUID(), nullable=False),
        sa.Column("lider_id", sa.UUID(), nullable=False),
        sa.Column("estado", estado_equipo, nullable=False, server_default="ACTIVO"),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["coordinacion_id"], ["coordinaciones.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["especialidad_id"], ["especialidades.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["lider_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_equipos_ejecutores_coordinacion_id", "equipos_ejecutores", ["coordinacion_id"], unique=False)
    op.create_index("ix_equipos_ejecutores_especialidad_id", "equipos_ejecutores", ["especialidad_id"], unique=False)
    op.create_index("ix_equipos_ejecutores_lider_id", "equipos_ejecutores", ["lider_id"], unique=False)

    # 8. Equipos Ejecutores Miembros
    op.create_table(
        "equipos_ejecutores_miembros",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("equipo_id", sa.UUID(), nullable=False),
        sa.Column("usuario_id", sa.UUID(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("asignado_por", sa.UUID(), nullable=True),
        sa.Column("fecha_asignacion", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asignado_por"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["equipo_id"], ["equipos_ejecutores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("equipo_id", "usuario_id", name="uq_equipo_usuario_miembro"),
    )
    op.create_index("ix_equipos_ejecutores_miembros_equipo_id", "equipos_ejecutores_miembros", ["equipo_id"], unique=False)
    op.create_index("ix_equipos_ejecutores_miembros_usuario_id", "equipos_ejecutores_miembros", ["usuario_id"], unique=False)

    # 9. Procesos Curriculares
    op.create_table(
        "procesos_curriculares",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("referencia_id", sa.UUID(), nullable=False),
        sa.Column("coordinacion_id", sa.UUID(), nullable=True),
        sa.Column("especialidad_id", sa.UUID(), nullable=True),
        sa.Column("equipo_ejecutor_id", sa.UUID(), nullable=True),
        sa.Column("lider_id", sa.UUID(), nullable=True),
        sa.Column("tipo_necesidad", tipo_necesidad_proceso, nullable=False, server_default="CREAR_PLANEACION"),
        sa.Column("estado_scope", estado_scope_proceso, nullable=False, server_default="SIN_ASIGNAR"),
        sa.Column("programa_id", sa.UUID(), nullable=True),
        sa.Column("proyecto_id", sa.UUID(), nullable=True),
        sa.Column("creado_por", sa.UUID(), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["coordinacion_id"], ["coordinaciones.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["creado_por"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["equipo_ejecutor_id"], ["equipos_ejecutores.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["especialidad_id"], ["especialidades.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lider_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["programa_id"], ["programas_formacion.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["proyecto_id"], ["proyectos_formativos.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_procesos_curriculares_referencia_id", "procesos_curriculares", ["referencia_id"], unique=True)
    op.create_index("ix_procesos_curriculares_equipo_id", "procesos_curriculares", ["equipo_ejecutor_id"], unique=False)
    op.create_index("ix_procesos_curriculares_lider_id", "procesos_curriculares", ["lider_id"], unique=False)
    op.create_index("ix_procesos_curriculares_estado_scope", "procesos_curriculares", ["estado_scope"], unique=False)

    # Seed initial roles
    roles_table = sa.table(
        "roles",
        sa.column("id", sa.UUID()),
        sa.column("nombre", sa.String()),
        sa.column("descripcion", sa.String()),
    )
    op.bulk_insert(
        roles_table,
        [
            {"id": uuid.uuid4(), "nombre": "SUPERADMIN", "descripcion": "Superadministrador del sistema"},
            {"id": uuid.uuid4(), "nombre": "ADMIN", "descripcion": "Administrador del Equipo Pedagógico"},
            {"id": uuid.uuid4(), "nombre": "LIDER_EQUIPO_EJECUTOR", "descripcion": "Líder de Equipo Ejecutor"},
            {"id": uuid.uuid4(), "nombre": "USUARIO_ADICIONAL", "descripcion": "Usuario de Apoyo en Equipo Ejecutor"},
        ],
    )


def downgrade() -> None:
    op.drop_table("procesos_curriculares")
    op.drop_table("equipos_ejecutores_miembros")
    op.drop_table("equipos_ejecutores")
    op.execute("DROP TYPE IF EXISTS estado_scope_proceso")
    op.execute("DROP TYPE IF EXISTS tipo_necesidad_proceso")
    op.execute("DROP TYPE IF EXISTS estado_equipo")
    op.drop_table("usuario_roles")
    op.drop_table("usuarios")
    op.drop_table("roles")
    op.drop_table("especialidades")
    op.drop_table("coordinaciones")
