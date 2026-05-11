"""ORM models for program and curriculum entities."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
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
    EstadoConciliacionPendiente,
    MotivoFalloExtraccion,
    MotivoPendienteAsignacion,
    TipoConocimiento,
    TipoElementoCurricularPendiente,
    TipoFuenteCargue,
)
from src.infrastructure.db.base import Base
from src.infrastructure.db.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    build_postgres_enum,
)

if TYPE_CHECKING:
    from src.infrastructure.db.models.proyecto import ProyectoFormativo


estado_bloque_enum = build_postgres_enum(EstadoBloque, "estado_bloque")
estado_campo_enum = build_postgres_enum(EstadoCampo, "estado_campo")
fuente_cargue_enum = build_postgres_enum(TipoFuenteCargue, "tipo_fuente_cargue")
tipo_conocimiento_enum = build_postgres_enum(TipoConocimiento, "tipo_conocimiento")
tipo_elemento_pendiente_enum = build_postgres_enum(
    TipoElementoCurricularPendiente,
    "tipo_elemento_curricular_pendiente",
)
motivo_pendiente_asignacion_enum = build_postgres_enum(
    MotivoPendienteAsignacion,
    "motivo_pendiente_asignacion",
)
estado_conciliacion_pendiente_enum = build_postgres_enum(
    EstadoConciliacionPendiente,
    "estado_conciliacion_pendiente",
)
motivo_fallo_enum = build_postgres_enum(
    MotivoFalloExtraccion,
    "motivo_fallo_extraccion",
)


class ProgramaFormacion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Root aggregate for the training program captured in Phase 1."""

    __tablename__ = "programas_formacion"
    __table_args__ = (
        UniqueConstraint(
            "codigo_programa",
            "version_programa",
            name="uq_programas_formacion_codigo_version_programa",
        ),
        CheckConstraint(
            "btrim(codigo_programa) <> ''",
            name="codigo_programa_not_blank",
        ),
        CheckConstraint(
            "btrim(nombre_programa) <> ''",
            name="nombre_programa_not_blank",
        ),
    )

    codigo_programa: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    nombre_programa: Mapped[str] = mapped_column(Text, nullable=False)
    version_programa: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estado: Mapped[EstadoBloque] = mapped_column(
        estado_bloque_enum,
        nullable=False,
        default=EstadoBloque.BORRADOR,
    )
    fuente_cargue: Mapped[TipoFuenteCargue] = mapped_column(
        fuente_cargue_enum,
        nullable=False,
        default=TipoFuenteCargue.MANUAL,
    )
    observaciones_revision: Mapped[str | None] = mapped_column(Text, nullable=True)

    competencias: Mapped[list["Competencia"]] = relationship(
        back_populates="programa",
        cascade="all, delete-orphan",
    )
    proyectos: Mapped[list["ProyectoFormativo"]] = relationship(
        back_populates="programa",
        cascade="all, delete-orphan",
    )


class Competencia(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Curriculum competence linked to a single training program."""

    __tablename__ = "competencias"
    __table_args__ = (
        UniqueConstraint(
            "programa_id",
            "codigo_competencia",
            name="uq_competencias_programa_codigo_competencia",
        ),
        CheckConstraint(
            "btrim(codigo_competencia) <> ''",
            name="codigo_competencia_not_blank",
        ),
        CheckConstraint(
            "btrim(nombre_competencia) <> ''",
            name="nombre_competencia_not_blank",
        ),
    )

    programa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("programas_formacion.id", ondelete="CASCADE"),
        nullable=False,
    )
    codigo_competencia: Mapped[str] = mapped_column(String(100), nullable=False)
    nombre_competencia: Mapped[str] = mapped_column(Text, nullable=False)
    orden: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estado: Mapped[EstadoBloque] = mapped_column(
        estado_bloque_enum,
        nullable=False,
        default=EstadoBloque.BORRADOR,
    )
    origen_campo: Mapped[EstadoCampo] = mapped_column(
        estado_campo_enum,
        nullable=False,
        default=EstadoCampo.PENDIENTE,
    )

    programa: Mapped[ProgramaFormacion] = relationship(back_populates="competencias")
    resultados: Mapped[list["ResultadoAprendizaje"]] = relationship(
        back_populates="competencia",
        cascade="all, delete-orphan",
    )
    conocimientos: Mapped[list["Conocimiento"]] = relationship(
        back_populates="competencia",
        cascade="all, delete-orphan",
    )
    criterios: Mapped[list["CriterioEvaluacion"]] = relationship(
        back_populates="competencia",
        cascade="all, delete-orphan",
    )


class ResultadoAprendizaje(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Learning result associated with a single competence."""

    __tablename__ = "resultados_aprendizaje"
    __table_args__ = (
        UniqueConstraint(
            "competencia_id",
            "descripcion",
            name="uq_resultados_aprendizaje_competencia_descripcion",
        ),
        CheckConstraint(
            "btrim(descripcion) <> ''",
            name="descripcion_not_blank",
        ),
        Index("ix_resultados_aprendizaje_competencia_id", "competencia_id"),
    )

    competencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competencias.id", ondelete="CASCADE"),
        nullable=False,
    )
    codigo_resultado: Mapped[str | None] = mapped_column(String(100), nullable=True)
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

    competencia: Mapped[Competencia] = relationship(back_populates="resultados")
    conocimientos: Mapped[list["Conocimiento"]] = relationship(
        back_populates="resultado",
        cascade="all, delete-orphan",
    )
    criterios: Mapped[list["CriterioEvaluacion"]] = relationship(
        back_populates="resultado",
        cascade="all, delete-orphan",
    )


class Conocimiento(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Knowledge item of type saber or proceso for a competence."""

    __tablename__ = "conocimientos"
    __table_args__ = (
        Index(
            "uq_conocimientos_comp_tipo_desc_rap",
            "competencia_id",
            "tipo",
            "descripcion",
            "resultado_id",
            unique=True,
            postgresql_where=text("resultado_id IS NOT NULL"),
        ),
        Index(
            "uq_conocimientos_comp_tipo_desc_norap",
            "competencia_id",
            "tipo",
            "descripcion",
            unique=True,
            postgresql_where=text("resultado_id IS NULL"),
        ),
        CheckConstraint(
            "btrim(descripcion) <> ''",
            name="descripcion_not_blank",
        ),
        Index("ix_conocimientos_competencia_id_tipo", "competencia_id", "tipo"),
    )

    competencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competencias.id", ondelete="CASCADE"),
        nullable=False,
    )
    resultado_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resultados_aprendizaje.id", ondelete="CASCADE"),
        nullable=True,
    )
    tipo: Mapped[TipoConocimiento] = mapped_column(
        tipo_conocimiento_enum,
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

    competencia: Mapped[Competencia] = relationship(back_populates="conocimientos")
    resultado: Mapped[ResultadoAprendizaje | None] = relationship(
        back_populates="conocimientos"
    )


class CriterioEvaluacion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Evaluation criterion associated with a competence."""

    __tablename__ = "criterios_evaluacion"
    __table_args__ = (
        Index(
            "uq_criterios_eval_comp_desc_rap",
            "competencia_id",
            "descripcion",
            "resultado_id",
            unique=True,
            postgresql_where=text("resultado_id IS NOT NULL"),
        ),
        Index(
            "uq_criterios_eval_comp_desc_norap",
            "competencia_id",
            "descripcion",
            unique=True,
            postgresql_where=text("resultado_id IS NULL"),
        ),
        CheckConstraint(
            "btrim(descripcion) <> ''",
            name="descripcion_not_blank",
        ),
        Index("ix_criterios_evaluacion_competencia_id", "competencia_id"),
    )

    competencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competencias.id", ondelete="CASCADE"),
        nullable=False,
    )
    resultado_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resultados_aprendizaje.id", ondelete="CASCADE"),
        nullable=True,
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

    competencia: Mapped[Competencia] = relationship(back_populates="criterios")
    resultado: Mapped[ResultadoAprendizaje | None] = relationship(
        back_populates="criterios"
    )


class ElementoCurricularPendiente(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Excel curricular row waiting for manual assignment."""

    __tablename__ = "elementos_curriculares_pendientes"
    __table_args__ = (
        CheckConstraint(
            "btrim(descripcion) <> ''",
            name="elemento_curricular_pendiente_descripcion_not_blank",
        ),
        Index(
            "ix_elementos_curriculares_pendientes_referencia_estado",
            "referencia_id",
            "estado",
        ),
        Index(
            "ix_elementos_curriculares_pendientes_programa_id",
            "programa_id",
        ),
    )

    referencia_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    programa_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("programas_formacion.id", ondelete="CASCADE"),
        nullable=True,
    )
    tipo_elemento: Mapped[TipoElementoCurricularPendiente] = mapped_column(
        tipo_elemento_pendiente_enum,
        nullable=False,
    )
    tipo_conocimiento: Mapped[TipoConocimiento | None] = mapped_column(
        tipo_conocimiento_enum,
        nullable=True,
    )
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    competencia_id_origen_excel: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    rap_id_origen_excel: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    motivo: Mapped[MotivoPendienteAsignacion] = mapped_column(
        motivo_pendiente_asignacion_enum,
        nullable=False,
    )
    estado: Mapped[EstadoConciliacionPendiente] = mapped_column(
        estado_conciliacion_pendiente_enum,
        nullable=False,
        default=EstadoConciliacionPendiente.PENDIENTE,
    )
    competencia_destino_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("competencias.id", ondelete="SET NULL"),
        nullable=True,
    )
    resultado_destino_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resultados_aprendizaje.id", ondelete="SET NULL"),
        nullable=True,
    )
    elemento_creado_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    orden: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_excel: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
