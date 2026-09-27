"""ORM models for Curricular Submissions, Pedagogical Reviews, and Feedback."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.shared.enums import (
    EstadoEntregaRevision,
    EstadoObservacionRevision,
    TipoElementoObservacion,
)
from src.infrastructure.db.base import Base
from src.infrastructure.db.models.mixins import (
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    build_postgres_enum,
)

if TYPE_CHECKING:
    from src.infrastructure.db.models.auth import Usuario
    from src.infrastructure.db.models.curriculum import ProgramaFormacion
    from src.infrastructure.db.models.organizacion import (
        EquipoEjecutor,
        ProcesoCurricular,
    )
    from src.infrastructure.db.models.proyecto import ProyectoFormativo

estado_entrega_enum = build_postgres_enum(EstadoEntregaRevision, "estado_entrega_revision")
tipo_elemento_obs_enum = build_postgres_enum(TipoElementoObservacion, "tipo_elemento_observacion")
estado_observacion_enum = build_postgres_enum(EstadoObservacionRevision, "estado_observacion_revision")


class EntregaRevisionCurricular(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Snapshot version of a curricular process submitted for pedagogical review."""

    __tablename__ = "entregas_revision_curricular"
    __table_args__ = (
        UniqueConstraint(
            "proceso_curricular_id",
            "version",
            name="uq_entrega_proceso_version",
        ),
        Index("ix_entregas_revision_proceso_id", "proceso_curricular_id"),
        Index("ix_entregas_revision_referencia_id", "referencia_id"),
        Index("ix_entregas_revision_equipo_id", "equipo_ejecutor_id"),
        Index("ix_entregas_revision_programa_id", "programa_id"),
        Index("ix_entregas_revision_proyecto_id", "proyecto_id"),
        Index("ix_entregas_revision_estado", "estado"),
        Index("ix_entregas_revision_version", "version"),
    )

    proceso_curricular_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("procesos_curriculares.id", ondelete="CASCADE"),
        nullable=False,
    )
    referencia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    equipo_ejecutor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("equipos_ejecutores.id", ondelete="RESTRICT"),
        nullable=False,
    )
    programa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("programas_formacion.id", ondelete="RESTRICT"),
        nullable=False,
    )
    proyecto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("proyectos_formativos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    estado: Mapped[EstadoEntregaRevision] = mapped_column(
        estado_entrega_enum,
        default=EstadoEntregaRevision.BORRADOR,
        nullable=False,
    )

    enviado_por_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    fecha_envio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    revisado_por_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    fecha_inicio_revision: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ajustes_solicitados_por_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    fecha_ajustes_solicitados: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    aprobado_por_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    fecha_aprobacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    descarga_habilitada: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    descarga_habilitada_por_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    fecha_descarga_habilitada: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    snapshot_metadatos: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    notas_entrega: Mapped[str | None] = mapped_column(Text, nullable=True)
    notas_aprobacion: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    proceso_curricular: Mapped[ProcesoCurricular] = relationship(
        "ProcesoCurricular",
        back_populates="entregas_revision",
        lazy="selectin",
    )
    equipo_ejecutor: Mapped[EquipoEjecutor] = relationship(
        "EquipoEjecutor",
        lazy="selectin",
    )
    programa: Mapped[ProgramaFormacion] = relationship(
        "ProgramaFormacion",
        lazy="selectin",
    )
    proyecto: Mapped[ProyectoFormativo] = relationship(
        "ProyectoFormativo",
        lazy="selectin",
    )
    enviado_por: Mapped[Usuario] = relationship(
        "Usuario",
        foreign_keys=[enviado_por_id],
        lazy="selectin",
    )
    revisado_por: Mapped[Usuario | None] = relationship(
        "Usuario",
        foreign_keys=[revisado_por_id],
        lazy="selectin",
    )
    aprobado_por: Mapped[Usuario | None] = relationship(
        "Usuario",
        foreign_keys=[aprobado_por_id],
        lazy="selectin",
    )
    observaciones: Mapped[list[ObservacionRevision]] = relationship(
        "ObservacionRevision",
        back_populates="entrega",
        cascade="all, delete-orphan",
        order_by="ObservacionRevision.fecha_creacion",
        lazy="selectin",
    )


class ObservacionRevision(UUIDPrimaryKeyMixin, Base):
    """Contextual pedagogical observation/comment attached to an element or section."""

    __tablename__ = "observaciones_revision_curricular"
    __table_args__ = (
        Index("ix_observaciones_entrega_id", "entrega_id"),
        Index("ix_observaciones_target_type", "target_type"),
        Index("ix_observaciones_target_id", "target_id"),
        Index("ix_observaciones_estado", "estado"),
    )

    entrega_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entregas_revision_curricular.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_type: Mapped[TipoElementoObservacion] = mapped_column(
        tipo_elemento_obs_enum,
        nullable=False,
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    section_key: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    comentario: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    estado: Mapped[EstadoObservacionRevision] = mapped_column(
        estado_observacion_enum,
        default=EstadoObservacionRevision.PENDIENTE,
        nullable=False,
    )

    creado_por_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    ajuste_reportado_por_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    fecha_ajuste_reportado: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    comentario_ajuste: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    resuelto_por_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    fecha_resolucion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    entrega: Mapped[EntregaRevisionCurricular] = relationship(
        "EntregaRevisionCurricular",
        back_populates="observaciones",
        lazy="selectin",
    )
    creado_por: Mapped[Usuario] = relationship(
        "Usuario",
        foreign_keys=[creado_por_id],
        lazy="selectin",
    )
    ajuste_reportado_por: Mapped[Usuario | None] = relationship(
        "Usuario",
        foreign_keys=[ajuste_reportado_por_id],
        lazy="selectin",
    )
    resuelto_por: Mapped[Usuario | None] = relationship(
        "Usuario",
        foreign_keys=[resuelto_por_id],
        lazy="selectin",
    )
