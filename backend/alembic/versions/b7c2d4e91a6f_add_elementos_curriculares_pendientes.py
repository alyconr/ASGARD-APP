"""Add curricular pending assignment rows

Revision ID: b7c2d4e91a6f
Revises: af3db3c40926
Create Date: 2026-05-11 10:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c2d4e91a6f"
down_revision: Union[str, Sequence[str], None] = "af3db3c40926"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


tipo_elemento_enum = sa.Enum(
    "CONOCIMIENTO",
    "CRITERIO",
    name="tipo_elemento_curricular_pendiente",
    create_type=False,
)
motivo_pendiente_enum = sa.Enum(
    "COMPETENCIA_NO_IDENTIFICADA",
    "RESULTADO_NO_IDENTIFICADO",
    "ASOCIACION_AMBIGUA",
    name="motivo_pendiente_asignacion",
    create_type=False,
)
estado_conciliacion_enum = sa.Enum(
    "PENDIENTE",
    "ASIGNADO",
    name="estado_conciliacion_pendiente",
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    tipo_elemento_enum.create(bind, checkfirst=True)
    motivo_pendiente_enum.create(bind, checkfirst=True)
    estado_conciliacion_enum.create(bind, checkfirst=True)
    op.create_table(
        "elementos_curriculares_pendientes",
        sa.Column("referencia_id", sa.UUID(), nullable=False),
        sa.Column("programa_id", sa.UUID(), nullable=True),
        sa.Column("tipo_elemento", tipo_elemento_enum, nullable=False),
        sa.Column(
            "tipo_conocimiento",
            postgresql.ENUM(
                "SABER",
                "PROCESO",
                name="tipo_conocimiento",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("competencia_id_origen_excel", sa.String(length=100), nullable=True),
        sa.Column("rap_id_origen_excel", sa.String(length=100), nullable=True),
        sa.Column("motivo", motivo_pendiente_enum, nullable=False),
        sa.Column(
            "estado",
            estado_conciliacion_enum,
            nullable=False,
            server_default="PENDIENTE",
        ),
        sa.Column("competencia_destino_id", sa.UUID(), nullable=True),
        sa.Column("resultado_destino_id", sa.UUID(), nullable=True),
        sa.Column("elemento_creado_id", sa.UUID(), nullable=True),
        sa.Column("orden", sa.Integer(), nullable=True),
        sa.Column("raw_excel", sa.JSON(), nullable=True),
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(descripcion) <> ''",
            name="elemento_curricular_pendiente_descripcion_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["competencia_destino_id"],
            ["competencias.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["programa_id"],
            ["programas_formacion.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resultado_destino_id"],
            ["resultados_aprendizaje.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_elementos_curriculares_pendientes_programa_id",
        "elementos_curriculares_pendientes",
        ["programa_id"],
        unique=False,
    )
    op.create_index(
        "ix_elementos_curriculares_pendientes_referencia_estado",
        "elementos_curriculares_pendientes",
        ["referencia_id", "estado"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_elementos_curriculares_pendientes_referencia_estado",
        table_name="elementos_curriculares_pendientes",
    )
    op.drop_index(
        "ix_elementos_curriculares_pendientes_programa_id",
        table_name="elementos_curriculares_pendientes",
    )
    op.drop_table("elementos_curriculares_pendientes")
    bind = op.get_bind()
    estado_conciliacion_enum.drop(bind, checkfirst=True)
    motivo_pendiente_enum.drop(bind, checkfirst=True)
    tipo_elemento_enum.drop(bind, checkfirst=True)
