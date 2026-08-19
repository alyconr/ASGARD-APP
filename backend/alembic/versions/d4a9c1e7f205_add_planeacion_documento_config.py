"""add planeacion documento config

Revision ID: d4a9c1e7f205
Revises: 5c2f8a91d7b3
Create Date: 2026-07-29 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d4a9c1e7f205"
down_revision: Union[str, Sequence[str], None] = "5c2f8a91d7b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add official planning document metadata."""
    op.add_column(
        "programas_formacion",
        sa.Column("modalidad_formacion", sa.String(length=150), nullable=True),
    )
    op.create_table(
        "planeacion_documento_config",
        sa.Column("proyecto_id", sa.UUID(), nullable=False),
        sa.Column("fecha_elaboracion", sa.Date(), nullable=True),
        sa.Column("clasificacion_informacion", sa.String(length=40), nullable=True),
        sa.Column(
            "equipo_gestion_curricular",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("regional", sa.Text(), nullable=True),
        sa.Column("centro_formacion", sa.Text(), nullable=True),
        sa.Column("storage_key", sa.String(length=500), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("fecha_generacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
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
            "clasificacion_informacion IS NULL OR "
            "clasificacion_informacion IN "
            "('PUBLICA', 'PUBLICA_CLASIFICADA', 'PUBLICA_RESERVADA')",
            name="ck_planeacion_documento_config_clasificacion",
        ),
        sa.ForeignKeyConstraint(
            ["proyecto_id"],
            ["proyectos_formativos.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "proyecto_id",
            name="uq_planeacion_documento_config_proyecto_id",
        ),
    )
    op.create_index(
        "ix_planeacion_documento_config_proyecto_id",
        "planeacion_documento_config",
        ["proyecto_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove official planning document metadata."""
    op.drop_index(
        "ix_planeacion_documento_config_proyecto_id",
        table_name="planeacion_documento_config",
    )
    op.drop_table("planeacion_documento_config")
    op.drop_column("programas_formacion", "modalidad_formacion")
