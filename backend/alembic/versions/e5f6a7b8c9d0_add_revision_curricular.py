"""Add curricular submission, pedagogical review and feedback tables.

Revision ID: e5f6a7b8c9d0
Revises: b1c2d3e4f5a6
Create Date: 2026-09-27 16:55:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Enums
    estado_entrega = postgresql.ENUM(
        "BORRADOR",
        "ENVIADO_REVISION",
        "EN_REVISION",
        "AJUSTES_SOLICITADOS",
        "AJUSTES_EN_PROGRESO",
        "REENVIADO",
        "APROBADO",
        name="estado_entrega_revision",
        create_type=False,
    )
    estado_entrega.create(op.get_bind(), checkfirst=True)

    tipo_elemento_obs = postgresql.ENUM(
        "PROCESO_GENERAL",
        "PROGRAMA",
        "PROYECTO",
        "PLANEACION",
        "CONFIGURACION_DOCUMENTAL",
        "SECCION",
        name="tipo_elemento_observacion",
        create_type=False,
    )
    tipo_elemento_obs.create(op.get_bind(), checkfirst=True)

    estado_obs = postgresql.ENUM(
        "PENDIENTE",
        "AJUSTE_REPORTADO",
        "RESUELTO",
        name="estado_observacion_revision",
        create_type=False,
    )
    estado_obs.create(op.get_bind(), checkfirst=True)

    # 2. Table: entregas_revision_curricular
    op.create_table(
        "entregas_revision_curricular",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "proceso_curricular_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("procesos_curriculares.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("referencia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "equipo_ejecutor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("equipos_ejecutores.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "programa_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("programas_formacion.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "proyecto_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("proyectos_formativos.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False, default=1, server_default="1"),
        sa.Column(
            "estado",
            estado_entrega,
            nullable=False,
            default="BORRADOR",
            server_default="BORRADOR",
        ),
        sa.Column(
            "enviado_por_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("fecha_envio", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "revisado_por_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("fecha_inicio_revision", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "ajustes_solicitados_por_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("fecha_ajustes_solicitados", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "aprobado_por_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("fecha_aprobacion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("descarga_habilitada", sa.Boolean(), nullable=False, default=False, server_default="false"),
        sa.Column(
            "descarga_habilitada_por_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("fecha_descarga_habilitada", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snapshot_metadatos", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("notas_entrega", sa.Text(), nullable=True),
        sa.Column("notas_aprobacion", sa.Text(), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("proceso_curricular_id", "version", name="uq_entrega_proceso_version"),
    )
    op.create_index("ix_entregas_revision_proceso_id", "entregas_revision_curricular", ["proceso_curricular_id"])
    op.create_index("ix_entregas_revision_referencia_id", "entregas_revision_curricular", ["referencia_id"])
    op.create_index("ix_entregas_revision_equipo_id", "entregas_revision_curricular", ["equipo_ejecutor_id"])
    op.create_index("ix_entregas_revision_programa_id", "entregas_revision_curricular", ["programa_id"])
    op.create_index("ix_entregas_revision_proyecto_id", "entregas_revision_curricular", ["proyecto_id"])
    op.create_index("ix_entregas_revision_estado", "entregas_revision_curricular", ["estado"])
    op.create_index("ix_entregas_revision_version", "entregas_revision_curricular", ["version"])

    # 3. Table: observaciones_revision_curricular
    op.create_table(
        "observaciones_revision_curricular",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "entrega_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("entregas_revision_curricular.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_type", tipo_elemento_obs, nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("section_key", sa.String(100), nullable=True),
        sa.Column("comentario", sa.Text(), nullable=False),
        sa.Column(
            "estado",
            estado_obs,
            nullable=False,
            default="PENDIENTE",
            server_default="PENDIENTE",
        ),
        sa.Column(
            "creado_por_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "ajuste_reportado_por_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("fecha_ajuste_reportado", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comentario_ajuste", sa.Text(), nullable=True),
        sa.Column(
            "resuelto_por_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("fecha_resolucion", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_observaciones_entrega_id", "observaciones_revision_curricular", ["entrega_id"])
    op.create_index("ix_observaciones_target_type", "observaciones_revision_curricular", ["target_type"])
    op.create_index("ix_observaciones_target_id", "observaciones_revision_curricular", ["target_id"])
    op.create_index("ix_observaciones_estado", "observaciones_revision_curricular", ["estado"])


def downgrade() -> None:
    op.drop_table("observaciones_revision_curricular")
    op.drop_table("entregas_revision_curricular")
    op.execute("DROP TYPE IF EXISTS estado_observacion_revision")
    op.execute("DROP TYPE IF EXISTS tipo_elemento_observacion")
    op.execute("DROP TYPE IF EXISTS estado_entrega_revision")
