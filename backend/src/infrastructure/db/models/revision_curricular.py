"""ORM models for Curricular Submissions, Pedagogical Reviews, and Feedback."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

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
    EstadoSolicitudReapertura,
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
    from src.infrastructure.db.models.curriculum import (
        ProgramaFormacion,
        ResultadoAprendizaje,
    )
    from src.infrastructure.db.models.organizacion import (
        EquipoEjecutor,
        ProcesoCurricular,
    )
    from src.infrastructure.db.models.planeacion import PlaneacionPedagogica
    from src.infrastructure.db.models.proyecto import ProyectoFormativo

estado_entrega_enum = build_postgres_enum(EstadoEntregaRevision, "estado_entrega_revision")
tipo_elemento_obs_enum = build_postgres_enum(TipoElementoObservacion, "tipo_elemento_observacion")
estado_observacion_enum = build_postgres_enum(EstadoObservacionRevision, "estado_observacion_revision")
estado_solicitud_reapertura_enum = build_postgres_enum(
    EstadoSolicitudReapertura, "estado_solicitud_reapertura"
)



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


class PlanningEditRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Formal request by a Team Leader to reopen approved Learning Results in a planning."""

    __tablename__ = "planning_edit_requests"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_planning_edit_requests_codigo"),
        Index("ix_planning_edit_requests_planning_id", "planning_id"),
        Index("ix_planning_edit_requests_proceso_id", "proceso_curricular_id"),
        Index("ix_planning_edit_requests_team_id", "team_id"),
        Index("ix_planning_edit_requests_status", "status"),
    )

    codigo: Mapped[str] = mapped_column(String(40), nullable=False)
    planning_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("planeaciones_pedagogicas.id", ondelete="CASCADE"),
        nullable=False,
    )
    proceso_curricular_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("procesos_curriculares.id", ondelete="CASCADE"),
        nullable=True,
    )
    entrega_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entregas_revision_curricular.id", ondelete="SET NULL"),
        nullable=True,
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("equipos_ejecutores.id", ondelete="SET NULL"),
        nullable=True,
    )
    referencia_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    requested_changes: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[EstadoSolicitudReapertura] = mapped_column(
        estado_solicitud_reapertura_enum,
        nullable=False,
        default=EstadoSolicitudReapertura.PENDING,
        server_default=EstadoSolicitudReapertura.PENDING.value,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    admin_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    def __init__(self, **kwargs: Any) -> None:
        if "status" not in kwargs or kwargs["status"] is None:
            kwargs["status"] = EstadoSolicitudReapertura.PENDING
        if "version" not in kwargs or kwargs["version"] is None:
            kwargs["version"] = 1
        created = kwargs.pop("created_at", None) or kwargs.get("fecha_creacion")
        updated = kwargs.pop("updated_at", None) or kwargs.get("fecha_actualizacion")
        if created is not None:
            kwargs["fecha_creacion"] = created
        if updated is not None:
            kwargs["fecha_actualizacion"] = updated
        if "codigo" not in kwargs or not kwargs["codigo"]:
            req_id = kwargs.get("id") or uuid.uuid4()
            kwargs["id"] = req_id
            yr = created.year if isinstance(created, datetime) else datetime.now(UTC).year
            kwargs["codigo"] = f"REQ-{yr}-{str(req_id)[:4].upper()}"
        super().__init__(**kwargs)
        self.created_at = getattr(self, "fecha_creacion", None) or created
        self.updated_at = getattr(self, "fecha_actualizacion", None) or updated

    # Relationships
    planning: Mapped[PlaneacionPedagogica] = relationship(
        "PlaneacionPedagogica",
        lazy="selectin",
    )
    proceso_curricular: Mapped[ProcesoCurricular | None] = relationship(
        "ProcesoCurricular",
        lazy="selectin",
    )
    team: Mapped[EquipoEjecutor | None] = relationship(
        "EquipoEjecutor",
        lazy="selectin",
    )
    requester: Mapped[Usuario] = relationship(
        "Usuario",
        foreign_keys=[requested_by],
        lazy="selectin",
    )
    reviewer: Mapped[Usuario | None] = relationship(
        "Usuario",
        foreign_keys=[reviewed_by],
        lazy="selectin",
    )
    items: Mapped[list[PlanningEditRequestItem]] = relationship(
        "PlanningEditRequestItem",
        back_populates="request",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PlanningEditRequestItem(UUIDPrimaryKeyMixin, Base):
    """Per-Learning-Result item inside a PlanningEditRequest."""

    __tablename__ = "planning_edit_request_items"
    __table_args__ = (
        UniqueConstraint(
            "request_id",
            "learning_result_id",
            name="uq_planning_edit_request_item_req_ra",
        ),
        Index("ix_planning_edit_request_items_request_id", "request_id"),
        Index("ix_planning_edit_request_items_learning_result_id", "learning_result_id"),
    )

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("planning_edit_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    learning_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resultados_aprendizaje.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    approved: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    def __init__(self, **kwargs: Any) -> None:
        if "requested" not in kwargs or kwargs["requested"] is None:
            kwargs["requested"] = True
        super().__init__(**kwargs)

    request: Mapped[PlanningEditRequest] = relationship(
        "PlanningEditRequest",
        back_populates="items",
    )
    learning_result: Mapped[ResultadoAprendizaje] = relationship(
        "ResultadoAprendizaje",
        lazy="selectin",
    )


class LearningResultVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Immutable snapshot of a Learning Result's approved state within a planning."""

    __tablename__ = "learning_result_versions"
    __table_args__ = (
        UniqueConstraint(
            "planning_id",
            "learning_result_id",
            "version_number",
            name="uq_learning_result_versions_plan_ra_ver",
        ),
        Index("ix_learning_result_versions_planning_id", "planning_id"),
        Index("ix_learning_result_versions_learning_result_id", "learning_result_id"),
    )

    learning_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resultados_aprendizaje.id", ondelete="CASCADE"),
        nullable=False,
    )
    planning_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("planeaciones_pedagogicas.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    snapshot_data: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    edit_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("planning_edit_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_official: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    def __init__(self, **kwargs: Any) -> None:
        if "version_number" not in kwargs or kwargs["version_number"] is None:
            kwargs["version_number"] = 1
        if "is_official" not in kwargs or kwargs["is_official"] is None:
            kwargs["is_official"] = True
        if "snapshot_data" not in kwargs or kwargs["snapshot_data"] is None:
            kwargs["snapshot_data"] = {}
        super().__init__(**kwargs)

    learning_result: Mapped[ResultadoAprendizaje] = relationship(
        "ResultadoAprendizaje",
        lazy="selectin",
    )
    approver: Mapped[Usuario | None] = relationship(
        "Usuario",
        foreign_keys=[approved_by],
        lazy="selectin",
    )

