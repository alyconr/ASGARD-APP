"""Sprint B: Organizational admin schema evolution (Usuario estado, area, credentials lifecycle, indexes).

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-09-21 07:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "f4a5b6c7d8e9"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create postgresql enum type for estado_usuario
    estado_usuario_enum = postgresql.ENUM(
        "ACTIVO",
        "INACTIVO",
        "BLOQUEADO",
        name="estado_usuario",
        create_type=False,
    )
    estado_usuario_enum.create(op.get_bind(), checkfirst=True)

    # 2. Add new columns to usuarios
    op.add_column("usuarios", sa.Column("area", sa.String(length=100), nullable=True))
    op.add_column(
        "usuarios",
        sa.Column(
            "estado",
            sa.Enum("ACTIVO", "INACTIVO", "BLOQUEADO", name="estado_usuario"),
            nullable=True,
            server_default="ACTIVO",
        ),
    )
    op.add_column(
        "usuarios",
        sa.Column(
            "debe_cambiar_password",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "usuarios",
        sa.Column("ultimo_acceso", sa.DateTime(timezone=True), nullable=True),
    )

    # 3. Migrate existing boolean activo values to new estado enum
    op.execute(sa.text("UPDATE usuarios SET estado = 'ACTIVO' WHERE activo = true"))
    op.execute(sa.text("UPDATE usuarios SET estado = 'INACTIVO' WHERE activo = false"))
    op.alter_column("usuarios", "estado", nullable=False, server_default="ACTIVO")

    # 4. Drop redundant activo boolean column
    op.drop_column("usuarios", "activo")

    # 5. Create new indices
    op.create_index("ix_usuarios_estado", "usuarios", ["estado"])
    op.create_index("ix_usuarios_area", "usuarios", ["area"])
    op.create_index("ix_equipos_ejecutores_estado", "equipos_ejecutores", ["estado"])


def downgrade() -> None:
    op.drop_index("ix_equipos_ejecutores_estado", table_name="equipos_ejecutores")
    op.drop_index("ix_usuarios_area", table_name="usuarios")
    op.drop_index("ix_usuarios_estado", table_name="usuarios")

    op.add_column(
        "usuarios",
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=True),
    )
    op.execute(sa.text("UPDATE usuarios SET activo = (estado = 'ACTIVO')"))
    op.alter_column("usuarios", "activo", nullable=False)

    op.drop_column("usuarios", "ultimo_acceso")
    op.drop_column("usuarios", "debe_cambiar_password")
    op.drop_column("usuarios", "estado")
    op.drop_column("usuarios", "area")

    estado_usuario_enum = postgresql.ENUM(
        "ACTIVO",
        "INACTIVO",
        "BLOQUEADO",
        name="estado_usuario",
        create_type=False,
    )
    estado_usuario_enum.drop(op.get_bind(), checkfirst=True)
