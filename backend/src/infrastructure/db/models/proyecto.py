"""ORM models for project, phases and activities."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.shared.enums import (
    EstadoBloque,
    EstadoCampo,
    MotivoFalloExtraccion,
    TipoFuenteCargue,
)
from src.infrastructure.db.base import Base
from src.infrastructure.db.models.curriculum import (
    ProgramaFormacion,
    estado_bloque_enum,
    estado_campo_enum,
    fuente_cargue_enum,
    motivo_fallo_enum,
)
from src.infrastructure.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.infrastructure.db.models.curriculum import (
        Competencia,
        ResultadoAprendizaje,
    )
    from src.infrastructure.db.models.planeacion import PlaneacionDocumentoConfig


class ProyectoFormativo(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Project aggregate that depends on a training program."""

    __tablename__ = "proyectos_formativos"
    __table_args__ = (
        CheckConstraint(
            "btrim(codigo_proyecto) <> ''",
            name="codigo_proyecto_not_blank",
        ),
        CheckConstraint(
            "btrim(nombre_proyecto) <> ''",
            name="nombre_proyecto_not_blank",
        ),
        CheckConstraint(
            "btrim(version_proyecto) <> ''",
            name="version_proyecto_not_blank",
        ),
        Index("ix_proyectos_formativos_programa_id", "programa_id"),
    )

    programa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("programas_formacion.id", ondelete="CASCADE"),
        nullable=False,
    )
    codigo_proyecto: Mapped[str] = mapped_column(String(100), nullable=False)
    nombre_proyecto: Mapped[str] = mapped_column(Text, nullable=False)
    version_proyecto: Mapped[str] = mapped_column(String(100), nullable=False)
    estado: Mapped[EstadoBloque] = mapped_column(
        estado_bloque_enum,
        nullable=False,
        default=EstadoBloque.BLOQUEADO,
    )
    fuente_cargue: Mapped[TipoFuenteCargue] = mapped_column(
        fuente_cargue_enum,
        nullable=False,
        default=TipoFuenteCargue.EXCEL_CANONICO,
    )
    observaciones_revision: Mapped[str | None] = mapped_column(Text, nullable=True)

    programa: Mapped[ProgramaFormacion] = relationship(back_populates="proyectos")
    fases: Mapped[list["FaseProyecto"]] = relationship(
        back_populates="proyecto",
        cascade="all, delete-orphan",
    )
    planeacion_documento_config: Mapped["PlaneacionDocumentoConfig | None"] = (
        relationship(
            back_populates="proyecto",
            cascade="all, delete-orphan",
            uselist=False,
        )
    )


class FaseProyecto(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Project phase linked to one project."""

    __tablename__ = "fases_proyecto"
    __table_args__ = (
        CheckConstraint(
            "btrim(nombre_fase) <> ''",
            name="nombre_fase_not_blank",
        ),
        Index("ix_fases_proyecto_proyecto_id", "proyecto_id"),
    )

    proyecto_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("proyectos_formativos.id", ondelete="CASCADE"),
        nullable=False,
    )
    nombre_fase: Mapped[str] = mapped_column(String(255), nullable=False)
    orden: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estado: Mapped[EstadoCampo] = mapped_column(
        estado_campo_enum,
        nullable=False,
        default=EstadoCampo.PENDIENTE,
    )

    proyecto: Mapped[ProyectoFormativo] = relationship(back_populates="fases")
    actividades: Mapped[list["ActividadProyecto"]] = relationship(
        back_populates="fase",
        cascade="all, delete-orphan",
    )


class ActividadProyecto(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Project activity belonging to a single phase."""

    __tablename__ = "actividades_proyecto"
    __table_args__ = (
        UniqueConstraint(
            "fase_id",
            "descripcion",
            name="uq_actividades_proyecto_fase_descripcion",
        ),
        CheckConstraint(
            "btrim(descripcion) <> ''",
            name="descripcion_not_blank",
        ),
        Index("ix_actividades_proyecto_fase_id", "fase_id"),
    )

    fase_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fases_proyecto.id", ondelete="CASCADE"),
        nullable=False,
    )
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    orden: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estado: Mapped[EstadoCampo] = mapped_column(
        estado_campo_enum,
        nullable=False,
        default=EstadoCampo.PENDIENTE,
    )
    motivo_fallo_extraccion: Mapped[MotivoFalloExtraccion | None] = mapped_column(
        motivo_fallo_enum,
        nullable=True,
    )

    fase: Mapped[FaseProyecto] = relationship(back_populates="actividades")
    asignaciones_curriculares: Mapped[list["AsignacionCurricularProyecto"]] = (
        relationship(
            back_populates="actividad",
            cascade="all, delete-orphan",
        )
    )


class AsignacionCurricularProyecto(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Relational materialization of one Planeacion_Proyecto matrix row.

    Links a project activity with the competencies and learning results
    assigned to it by the canonical project matrix, preserving the
    authoritative ``tipo_resultado`` value from the source.
    """

    __tablename__ = "asignaciones_curriculares_proyecto"
    __table_args__ = (
        CheckConstraint(
            "tipo_resultado IN ('ESPECIFICO', 'TRANSVERSAL', 'BASICO')",
            name="asignacion_curricular_tipo_resultado_enum",
        ),
        Index(
            "uq_asignacion_curricular_act_comp_rap",
            "actividad_proyecto_id",
            "competencia_id",
            "resultado_id",
            unique=True,
            postgresql_where=text("resultado_id IS NOT NULL"),
        ),
        Index(
            "uq_asignacion_curricular_act_comp_norap",
            "actividad_proyecto_id",
            "competencia_id",
            unique=True,
            postgresql_where=text("resultado_id IS NULL"),
        ),
        Index(
            "ix_asignaciones_curriculares_proyecto_id",
            "proyecto_id",
        ),
        Index(
            "ix_asignaciones_curriculares_actividad_id",
            "actividad_proyecto_id",
        ),
        Index(
            "ix_asignaciones_curriculares_competencia_id",
            "competencia_id",
        ),
        Index(
            "ix_asignaciones_curriculares_resultado_id",
            "resultado_id",
        ),
    )

    proyecto_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("proyectos_formativos.id", ondelete="CASCADE"),
        nullable=False,
    )
    actividad_proyecto_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("actividades_proyecto.id", ondelete="CASCADE"),
        nullable=False,
    )
    competencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competencias.id", ondelete="CASCADE"),
        nullable=False,
    )
    resultado_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resultados_aprendizaje.id", ondelete="CASCADE"),
        nullable=True,
    )
    tipo_resultado: Mapped[str] = mapped_column(String(50), nullable=False)
    orden_resultado: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pagina_origen: Mapped[str | None] = mapped_column(String(100), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    proyecto: Mapped[ProyectoFormativo] = relationship()
    actividad: Mapped[ActividadProyecto] = relationship(
        back_populates="asignaciones_curriculares",
    )
    competencia: Mapped["Competencia"] = relationship()
    resultado: Mapped["ResultadoAprendizaje | None"] = relationship()
