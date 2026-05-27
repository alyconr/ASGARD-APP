"""ORM models for Pedagogical Planning entities."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
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
            "competencia_id",
            name="uq_planeacion_proyecto_competencia",
        ),
        Index("ix_planeaciones_pedagogicas_proyecto_id", "proyecto_id"),
        Index("ix_planeaciones_pedagogicas_competencia_id", "competencia_id"),
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
