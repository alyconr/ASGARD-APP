"""ORM models for Pedagogical Planning entities."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.shared.enums import (
    EstadoAprobacionPlaneacion,
    EstadoBloque,
    EstadoEdicionRA,
    EstadoRevisionPlaneacion,
)
from src.infrastructure.db.base import Base
from src.infrastructure.db.models.curriculum import (
    Conocimiento,
    CriterioEvaluacion,
    ResultadoAprendizaje,
)
from src.infrastructure.db.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    build_postgres_enum,
)

if TYPE_CHECKING:
    from src.infrastructure.db.models.proyecto import (
        ActividadProyecto,
        FaseProyecto,
        ProyectoFormativo,
    )

CLASIFICACIONES_INFORMACION = (
    "PUBLICA",
    "PUBLICA_CLASIFICADA",
    "PUBLICA_RESERVADA",
)

estado_revision_planeacion_enum = build_postgres_enum(
    EstadoRevisionPlaneacion, "estado_revision_planeacion"
)
estado_aprobacion_planeacion_enum = build_postgres_enum(
    EstadoAprobacionPlaneacion, "estado_aprobacion_planeacion"
)
estado_edicion_ra_enum = build_postgres_enum(EstadoEdicionRA, "estado_edicion_ra")


# Many-to-Many Association Tables
planeacion_resultados = Table(
    "planeacion_resultados",
    Base.metadata,
    Column(
        "planeacion_id",
        UUID(as_uuid=True),
        ForeignKey("planeaciones_pedagogicas.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "resultado_id",
        UUID(as_uuid=True),
        ForeignKey("resultados_aprendizaje.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "edit_status",
        estado_edicion_ra_enum,
        nullable=False,
        default=EstadoEdicionRA.EDITABLE,
        server_default=EstadoEdicionRA.EDITABLE.value,
    ),
    Column("locked_at", DateTime(timezone=True), nullable=True),
    Column(
        "locked_by",
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column("unlocked_at", DateTime(timezone=True), nullable=True),
    Column(
        "unlocked_by",
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column("unlock_request_id", UUID(as_uuid=True), nullable=True),
    Column("approved_version", Integer, nullable=False, default=0, server_default="0"),
    Column("approved_at", DateTime(timezone=True), nullable=True),
)

planeacion_conocimientos = Table(
    "planeacion_conocimientos",
    Base.metadata,
    Column(
        "planeacion_id",
        UUID(as_uuid=True),
        ForeignKey("planeaciones_pedagogicas.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "conocimiento_id",
        UUID(as_uuid=True),
        ForeignKey("conocimientos.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

planeacion_criterios = Table(
    "planeacion_criterios",
    Base.metadata,
    Column(
        "planeacion_id",
        UUID(as_uuid=True),
        ForeignKey("planeaciones_pedagogicas.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "criterio_id",
        UUID(as_uuid=True),
        ForeignKey("criterios_evaluacion.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class PlaneacionPedagogica(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Integrated pedagogical planning for one project activity.

    The planning identity is the learning activity built on top of a
    project phase/activity pair. Competencies are derived from the many
    to many learning results, which are the real source of truth.
    """

    __tablename__ = "planeaciones_pedagogicas"
    __table_args__ = (
        Index("ix_planeaciones_pedagogicas_proyecto_id", "proyecto_id"),
        Index("ix_planeaciones_pedagogicas_actividad_id", "actividad_id"),
    )

    proyecto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("proyectos_formativos.id", ondelete="CASCADE"),
        nullable=False,
    )
    fase_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fases_proyecto.id", ondelete="SET NULL"),
        nullable=True,
    )
    actividad_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("actividades_proyecto.id", ondelete="SET NULL"),
        nullable=True,
    )

    estado: Mapped[EstadoBloque] = mapped_column(
        SqlEnum(EstadoBloque, name="estado_bloque", create_type=False),
        nullable=False,
        default=EstadoBloque.BORRADOR,
    )

    # Separated review, approval, and edit status dimensions
    review_status: Mapped[EstadoRevisionPlaneacion] = mapped_column(
        estado_revision_planeacion_enum,
        nullable=False,
        default=EstadoRevisionPlaneacion.DRAFT,
        server_default=EstadoRevisionPlaneacion.DRAFT.value,
    )
    approval_status: Mapped[EstadoAprobacionPlaneacion] = mapped_column(
        estado_aprobacion_planeacion_enum,
        nullable=False,
        default=EstadoAprobacionPlaneacion.PENDING,
        server_default=EstadoAprobacionPlaneacion.PENDING.value,
    )
    edit_status: Mapped[EstadoEdicionRA] = mapped_column(
        estado_edicion_ra_enum,
        nullable=False,
        default=EstadoEdicionRA.EDITABLE,
        server_default=EstadoEdicionRA.EDITABLE.value,
    )
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    locked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    unlocked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    unlocked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    unlock_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    datos_complementarios: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Storage Info (current working version)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fecha_generacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Official Approved Snapshot (preserved during reopening until new approval)
    official_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    official_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    official_checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    official_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    official_approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    official_approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __init__(self, **kwargs: Any) -> None:
        if "review_status" not in kwargs or kwargs["review_status"] is None:
            kwargs["review_status"] = EstadoRevisionPlaneacion.DRAFT
        if "approval_status" not in kwargs or kwargs["approval_status"] is None:
            kwargs["approval_status"] = EstadoAprobacionPlaneacion.PENDING
        if "edit_status" not in kwargs or kwargs["edit_status"] is None:
            kwargs["edit_status"] = EstadoEdicionRA.EDITABLE
        super().__init__(**kwargs)

    # Relationships
    proyecto: Mapped[ProyectoFormativo] = relationship()
    fase: Mapped[FaseProyecto | None] = relationship()
    actividad: Mapped[ActividadProyecto | None] = relationship()

    resultados: Mapped[list[ResultadoAprendizaje]] = relationship(
        secondary=planeacion_resultados,
    )
    conocimientos: Mapped[list[Conocimiento]] = relationship(
        secondary=planeacion_conocimientos,
    )
    criterios: Mapped[list[CriterioEvaluacion]] = relationship(
        secondary=planeacion_criterios,
    )


class PlaneacionDocumentoConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Shared institutional metadata and consolidated planning artifact."""

    __tablename__ = "planeacion_documento_config"
    __table_args__ = (
        UniqueConstraint(
            "proyecto_id",
            name="uq_planeacion_documento_config_proyecto_id",
        ),
        CheckConstraint(
            "clasificacion_informacion IS NULL OR "
            "clasificacion_informacion IN "
            "('PUBLICA', 'PUBLICA_CLASIFICADA', 'PUBLICA_RESERVADA')",
            name="ck_planeacion_documento_config_clasificacion",
        ),
    )

    proyecto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("proyectos_formativos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fecha_elaboracion: Mapped[date | None] = mapped_column(Date, nullable=True)
    clasificacion_informacion: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )
    equipo_gestion_curricular: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    regional: Mapped[str | None] = mapped_column(Text, nullable=True)
    centro_formacion: Mapped[str | None] = mapped_column(Text, nullable=True)

    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fecha_generacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Official Approved Consolidated Snapshot (preserved during reopening)
    official_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    official_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    official_checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    official_version: Mapped[int | None] = mapped_column(Integer, nullable=True)

    proyecto: Mapped[ProyectoFormativo] = relationship(
        back_populates="planeacion_documento_config",
    )

