"""ORM models for Pedagogical Planning entities."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

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
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.shared.enums import EstadoBloque
from src.infrastructure.db.base import Base
from src.infrastructure.db.models.curriculum import (
    Competencia,
    Conocimiento,
    CriterioEvaluacion,
    ResultadoAprendizaje,
)
from src.infrastructure.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

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
    """Pedagogical planning created for a specific competence in a format project."""

    __tablename__ = "planeaciones_pedagogicas"
    __table_args__ = (
        UniqueConstraint(
            "proyecto_id",
            "resultado_id",
            name="uq_planeacion_proyecto_resultado",
        ),
        Index("ix_planeaciones_pedagogicas_proyecto_id", "proyecto_id"),
        Index("ix_planeaciones_pedagogicas_competencia_id", "competencia_id"),
        Index("ix_planeaciones_pedagogicas_resultado_id", "resultado_id"),
    )

    proyecto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("proyectos_formativos.id", ondelete="CASCADE"),
        nullable=False,
    )
    competencia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("competencias.id", ondelete="CASCADE"),
        nullable=False,
    )
    resultado_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resultados_aprendizaje.id", ondelete="CASCADE"),
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

    datos_complementarios: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Storage Info
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fecha_generacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    proyecto: Mapped[ProyectoFormativo] = relationship()
    competencia: Mapped[Competencia] = relationship()
    resultado: Mapped[ResultadoAprendizaje] = relationship(
        foreign_keys=[resultado_id],
    )
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

    proyecto: Mapped[ProyectoFormativo] = relationship(
        back_populates="planeacion_documento_config",
    )
