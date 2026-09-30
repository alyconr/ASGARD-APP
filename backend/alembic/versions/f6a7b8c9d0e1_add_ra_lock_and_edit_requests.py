"""Add Learning Result locking, edit requests, and official version history.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-30 10:25:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    estado_revision_planeacion = postgresql.ENUM(
        "DRAFT",
        "IN_REVIEW",
        "OBSERVED",
        "APPROVED",
        "CHANGES_ALLOWED",
        name="estado_revision_planeacion",
        create_type=False,
    )
    estado_aprobacion_planeacion = postgresql.ENUM(
        "PENDING",
        "APPROVED",
        "PREVIOUS_VERSION_APPROVED",
        "REJECTED",
        name="estado_aprobacion_planeacion",
        create_type=False,
    )
    estado_edicion_ra = postgresql.ENUM(
        "EDITABLE",
        "LOCKED",
        name="estado_edicion_ra",
        create_type=False,
    )
    estado_solicitud_reapertura = postgresql.ENUM(
        "PENDING",
        "APPROVED",
        "PARTIALLY_APPROVED",
        "REJECTED",
        "COMPLETED",
        "CANCELLED",
        name="estado_solicitud_reapertura",
        create_type=False,
    )

    bind = op.get_bind()
    estado_revision_planeacion.create(bind, checkfirst=True)
    estado_aprobacion_planeacion.create(bind, checkfirst=True)
    estado_edicion_ra.create(bind, checkfirst=True)
    estado_solicitud_reapertura.create(bind, checkfirst=True)

    # 1. resultados_aprendizaje columns
    op.add_column(
        "resultados_aprendizaje",
        sa.Column(
            "edit_status",
            estado_edicion_ra,
            nullable=False,
            server_default="EDITABLE",
        ),
    )
    op.add_column(
        "resultados_aprendizaje",
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "resultados_aprendizaje",
        sa.Column("locked_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "resultados_aprendizaje",
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "resultados_aprendizaje",
        sa.Column("unlocked_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "resultados_aprendizaje",
        sa.Column("unlock_request_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "resultados_aprendizaje",
        sa.Column("approved_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "resultados_aprendizaje",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_resultados_aprendizaje_edit_status",
        "resultados_aprendizaje",
        ["edit_status"],
    )

    # 2. planeacion_resultados columns
    op.add_column(
        "planeacion_resultados",
        sa.Column(
            "edit_status",
            estado_edicion_ra,
            nullable=False,
            server_default="EDITABLE",
        ),
    )
    op.add_column(
        "planeacion_resultados",
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "planeacion_resultados",
        sa.Column("locked_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "planeacion_resultados",
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "planeacion_resultados",
        sa.Column("unlocked_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "planeacion_resultados",
        sa.Column("unlock_request_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "planeacion_resultados",
        sa.Column("approved_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "planeacion_resultados",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 3. planeaciones_pedagogicas columns
    op.add_column(
        "planeaciones_pedagogicas",
        sa.Column(
            "review_status",
            estado_revision_planeacion,
            nullable=False,
            server_default="DRAFT",
        ),
    )
    op.add_column(
        "planeaciones_pedagogicas",
        sa.Column(
            "approval_status",
            estado_aprobacion_planeacion,
            nullable=False,
            server_default="PENDING",
        ),
    )
    op.add_column(
        "planeaciones_pedagogicas",
        sa.Column(
            "edit_status",
            estado_edicion_ra,
            nullable=False,
            server_default="EDITABLE",
        ),
    )
    op.add_column(
        "planeaciones_pedagogicas",
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "planeaciones_pedagogicas",
        sa.Column("locked_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "planeaciones_pedagogicas",
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "planeaciones_pedagogicas",
        sa.Column("unlocked_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "planeaciones_pedagogicas",
        sa.Column("unlock_request_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "planeaciones_pedagogicas",
        sa.Column("official_storage_key", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "planeaciones_pedagogicas",
        sa.Column("official_file_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "planeaciones_pedagogicas",
        sa.Column("official_checksum_sha256", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "planeaciones_pedagogicas",
        sa.Column("official_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "planeaciones_pedagogicas",
        sa.Column("official_approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "planeaciones_pedagogicas",
        sa.Column("official_approved_by", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # 4. planeacion_documento_configs columns
    op.add_column(
        "planeacion_documento_configs",
        sa.Column("official_storage_key", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "planeacion_documento_configs",
        sa.Column("official_file_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "planeacion_documento_configs",
        sa.Column("official_checksum_sha256", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "planeacion_documento_configs",
        sa.Column("official_version", sa.Integer(), nullable=False, server_default="0"),
    )

    # 5. planning_edit_requests table
    op.create_table(
        "planning_edit_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "planning_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("planeaciones_pedagogicas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("equipos_ejecutores.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "referencia_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "requested_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("requested_changes", sa.Text(), nullable=False),
        sa.Column(
            "status",
            estado_solicitud_reapertura,
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "reviewed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("admin_response", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_planning_edit_requests_planning_status",
        "planning_edit_requests",
        ["planning_id", "status"],
    )
    op.create_index(
        "ix_planning_edit_requests_team_status",
        "planning_edit_requests",
        ["team_id", "status"],
    )

    # 6. planning_edit_request_items table
    op.create_table(
        "planning_edit_request_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("planning_edit_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "learning_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resultados_aprendizaje.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requested", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint(
            "request_id",
            "learning_result_id",
            name="uq_edit_request_item_ra",
        ),
    )
    op.create_index(
        "ix_planning_edit_request_items_request",
        "planning_edit_request_items",
        ["request_id"],
    )
    op.create_index(
        "ix_planning_edit_request_items_ra",
        "planning_edit_request_items",
        ["learning_result_id"],
    )

    # 7. learning_result_versions table
    op.create_table(
        "learning_result_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "planning_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("planeaciones_pedagogicas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "learning_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resultados_aprendizaje.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("snapshot_data", postgresql.JSONB(), nullable=False),
        sa.Column(
            "approved_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "approved_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("is_official", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index(
        "ix_learning_result_versions_planning_ra",
        "learning_result_versions",
        ["planning_id", "learning_result_id", "version_number"],
    )

    # 8. Data migration for already approved deliveries with download enabled
    op.execute(
        """
        UPDATE planeaciones_pedagogicas p
        SET
            review_status = 'APPROVED',
            approval_status = 'APPROVED',
            edit_status = 'LOCKED',
            locked_at = COALESCE(e.fecha_aprobacion, NOW()),
            locked_by = e.aprobado_por_id,
            official_storage_key = p.storage_key,
            official_file_name = p.file_name,
            official_checksum_sha256 = p.checksum_sha256,
            official_version = e.version,
            official_approved_at = COALESCE(e.fecha_aprobacion, NOW()),
            official_approved_by = e.aprobado_por_id
        FROM entregas_revision_curricular e
        WHERE e.proyecto_id = p.proyecto_id
          AND e.estado = 'APROBADO'
          AND e.descarga_habilitada = TRUE
          AND p.estado = 'COMPLETO';
        """
    )
    op.execute(
        """
        UPDATE resultados_aprendizaje r
        SET
            edit_status = 'LOCKED',
            locked_at = COALESCE(p.locked_at, NOW()),
            locked_by = p.locked_by,
            approved_version = GREATEST(p.official_version, 1),
            approved_at = COALESCE(p.official_approved_at, NOW())
        FROM planeacion_resultados pr
        JOIN planeaciones_pedagogicas p ON p.id = pr.planeacion_id
        WHERE pr.resultado_id = r.id
          AND p.approval_status = 'APPROVED'
          AND p.edit_status = 'LOCKED';
        """
    )
    op.execute(
        """
        UPDATE planeacion_resultados pr
        SET
            edit_status = 'LOCKED',
            locked_at = COALESCE(p.locked_at, NOW()),
            locked_by = p.locked_by,
            approved_version = GREATEST(p.official_version, 1),
            approved_at = COALESCE(p.official_approved_at, NOW())
        FROM planeaciones_pedagogicas p
        WHERE p.id = pr.planeacion_id
          AND p.approval_status = 'APPROVED'
          AND p.edit_status = 'LOCKED';
        """
    )
    op.execute(
        """
        UPDATE planeacion_documento_configs c
        SET
            official_storage_key = c.storage_key,
            official_file_name = c.file_name,
            official_checksum_sha256 = c.checksum_sha256,
            official_version = e.version
        FROM entregas_revision_curricular e
        WHERE e.proyecto_id = c.proyecto_id
          AND e.estado = 'APROBADO'
          AND e.descarga_habilitada = TRUE;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_learning_result_versions_planning_ra", table_name="learning_result_versions")
    op.drop_table("learning_result_versions")

    op.drop_index("ix_planning_edit_request_items_ra", table_name="planning_edit_request_items")
    op.drop_index("ix_planning_edit_request_items_request", table_name="planning_edit_request_items")
    op.drop_table("planning_edit_request_items")

    op.drop_index("ix_planning_edit_requests_team_status", table_name="planning_edit_requests")
    op.drop_index("ix_planning_edit_requests_planning_status", table_name="planning_edit_requests")
    op.drop_table("planning_edit_requests")

    op.drop_column("planeacion_documento_configs", "official_version")
    op.drop_column("planeacion_documento_configs", "official_checksum_sha256")
    op.drop_column("planeacion_documento_configs", "official_file_name")
    op.drop_column("planeacion_documento_configs", "official_storage_key")

    op.drop_column("planeaciones_pedagogicas", "official_approved_by")
    op.drop_column("planeaciones_pedagogicas", "official_approved_at")
    op.drop_column("planeaciones_pedagogicas", "official_version")
    op.drop_column("planeaciones_pedagogicas", "official_checksum_sha256")
    op.drop_column("planeaciones_pedagogicas", "official_file_name")
    op.drop_column("planeaciones_pedagogicas", "official_storage_key")
    op.drop_column("planeaciones_pedagogicas", "unlock_request_id")
    op.drop_column("planeaciones_pedagogicas", "unlocked_by")
    op.drop_column("planeaciones_pedagogicas", "unlocked_at")
    op.drop_column("planeaciones_pedagogicas", "locked_by")
    op.drop_column("planeaciones_pedagogicas", "locked_at")
    op.drop_column("planeaciones_pedagogicas", "edit_status")
    op.drop_column("planeaciones_pedagogicas", "approval_status")
    op.drop_column("planeaciones_pedagogicas", "review_status")

    op.drop_column("planeacion_resultados", "approved_at")
    op.drop_column("planeacion_resultados", "approved_version")
    op.drop_column("planeacion_resultados", "unlock_request_id")
    op.drop_column("planeacion_resultados", "unlocked_by")
    op.drop_column("planeacion_resultados", "unlocked_at")
    op.drop_column("planeacion_resultados", "locked_by")
    op.drop_column("planeacion_resultados", "locked_at")
    op.drop_column("planeacion_resultados", "edit_status")

    op.drop_index("ix_resultados_aprendizaje_edit_status", table_name="resultados_aprendizaje")
    op.drop_column("resultados_aprendizaje", "approved_at")
    op.drop_column("resultados_aprendizaje", "approved_version")
    op.drop_column("resultados_aprendizaje", "unlock_request_id")
    op.drop_column("resultados_aprendizaje", "unlocked_by")
    op.drop_column("resultados_aprendizaje", "unlocked_at")
    op.drop_column("resultados_aprendizaje", "locked_by")
    op.drop_column("resultados_aprendizaje", "locked_at")
    op.drop_column("resultados_aprendizaje", "edit_status")

    bind = op.get_bind()
    postgresql.ENUM(name="estado_solicitud_reapertura").drop(bind, checkfirst=True)
    postgresql.ENUM(name="estado_edicion_ra").drop(bind, checkfirst=True)
    postgresql.ENUM(name="estado_aprobacion_planeacion").drop(bind, checkfirst=True)
    postgresql.ENUM(name="estado_revision_planeacion").drop(bind, checkfirst=True)
