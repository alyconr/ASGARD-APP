"""ORM models for organization, teams, memberships, and curricular processes."""

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
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.shared.enums import (
    EstadoEquipo,
    EstadoScopeProceso,
    RolEquipo,
    TipoNecesidadProceso,
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
    from src.infrastructure.db.models.proyecto import ProyectoFormativo

estado_equipo_enum = build_postgres_enum(EstadoEquipo, "estado_equipo")
tipo_necesidad_enum = build_postgres_enum(TipoNecesidadProceso, "tipo_necesidad_proceso")
estado_scope_enum = build_postgres_enum(EstadoScopeProceso, "estado_scope_proceso")
rol_equipo_enum = build_postgres_enum(RolEquipo, "rol_equipo")


class Coordinacion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Academic coordination grouping specialties and teams."""

    __tablename__ = "coordinaciones"
    __table_args__ = (
        Index("ix_coordinaciones_codigo", "codigo", unique=True),
    )

    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    especialidades: Mapped[list[Especialidad]] = relationship(
        "Especialidad",
        back_populates="coordinacion",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    equipos: Mapped[list[EquipoEjecutor]] = relationship(
        "EquipoEjecutor",
        back_populates="coordinacion",
        lazy="selectin",
    )


class Especialidad(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Academic specialty under a coordination."""

    __tablename__ = "especialidades"
    __table_args__ = (
        Index("ix_especialidades_codigo", "codigo", unique=True),
        Index("ix_especialidades_coordinacion_id", "coordinacion_id"),
        Index("ix_especialidades_creado_por_id", "creado_por_id"),
    )

    coordinacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coordinaciones.id", ondelete="CASCADE"),
        nullable=False,
    )
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    creado_por_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )

    coordinacion: Mapped[Coordinacion] = relationship(
        "Coordinacion",
        back_populates="especialidades",
        lazy="selectin",
    )
    equipos: Mapped[list[EquipoEjecutor]] = relationship(
        "EquipoEjecutor",
        back_populates="especialidad",
        lazy="selectin",
    )


class EquipoEjecutor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Executing pedagogical team assigned to specific curricular duties."""

    __tablename__ = "equipos_ejecutores"
    __table_args__ = (
        Index("ix_equipos_ejecutores_coordinacion_id", "coordinacion_id"),
        Index("ix_equipos_ejecutores_especialidad_id", "especialidad_id"),
        Index("ix_equipos_ejecutores_programa_id", "programa_id"),
        Index("ix_equipos_ejecutores_lider_id", "lider_id"),
        Index("ix_equipos_ejecutores_estado", "estado"),
    )

    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    coordinacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coordinaciones.id", ondelete="RESTRICT"),
        nullable=False,
    )
    especialidad_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("especialidades.id", ondelete="RESTRICT"),
        nullable=False,
    )
    programa_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("programas_formacion.id", ondelete="RESTRICT"),
        nullable=True,
    )
    lider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    max_members: Mapped[int] = mapped_column(
        Integer,
        default=5,
        server_default="5",
        nullable=False,
    )
    leaders_can_manage_members: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[EstadoEquipo] = mapped_column(
        estado_equipo_enum,
        default=EstadoEquipo.ACTIVO,
        nullable=False,
    )

    coordinacion: Mapped[Coordinacion] = relationship(
        "Coordinacion",
        back_populates="equipos",
        lazy="selectin",
    )
    especialidad: Mapped[Especialidad] = relationship(
        "Especialidad",
        back_populates="equipos",
        lazy="selectin",
    )
    programa: Mapped[ProgramaFormacion | None] = relationship(
        "ProgramaFormacion",
        foreign_keys=[programa_id],
        lazy="selectin",
    )
    lider: Mapped[Usuario] = relationship(
        "Usuario",
        foreign_keys=[lider_id],
        back_populates="equipos_liderados",
        lazy="selectin",
    )
    miembros: Mapped[list[EquipoEjecutorMiembro]] = relationship(
        "EquipoEjecutorMiembro",
        back_populates="equipo",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    procesos: Mapped[list[ProcesoCurricular]] = relationship(
        "ProcesoCurricular",
        back_populates="equipo_ejecutor",
        lazy="selectin",
    )


class EquipoEjecutorMiembro(UUIDPrimaryKeyMixin, Base):
    """Membership of additional users inside an executing team."""

    __tablename__ = "equipos_ejecutores_miembros"
    __table_args__ = (
        UniqueConstraint("equipo_id", "usuario_id", name="uq_equipo_usuario_miembro"),
        Index("ix_equipos_ejecutores_miembros_equipo_id", "equipo_id"),
        Index("ix_equipos_ejecutores_miembros_usuario_id", "usuario_id"),
        Index("ix_equipos_ejecutores_miembros_rol_equipo", "rol_equipo"),
    )

    equipo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("equipos_ejecutores.id", ondelete="CASCADE"),
        nullable=False,
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    rol_equipo: Mapped[RolEquipo] = mapped_column(
        rol_equipo_enum,
        default=RolEquipo.INSTRUCTOR,
        server_default=RolEquipo.INSTRUCTOR.value,
        nullable=False,
    )
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    asignado_por: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    fecha_asignacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    equipo: Mapped[EquipoEjecutor] = relationship(
        "EquipoEjecutor",
        back_populates="miembros",
        lazy="selectin",
    )
    usuario: Mapped[Usuario] = relationship(
        "Usuario",
        foreign_keys=[usuario_id],
        back_populates="membresias",
        lazy="selectin",
    )


class ProcesoCurricular(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Unit of curricular process tracking and scoping linked by referencia_id."""

    __tablename__ = "procesos_curriculares"
    __table_args__ = (
        Index("ix_procesos_curriculares_referencia_id", "referencia_id", unique=True),
        Index("ix_procesos_curriculares_equipo_id", "equipo_ejecutor_id"),
        Index("ix_procesos_curriculares_lider_id", "lider_id"),
        Index("ix_procesos_curriculares_estado_scope", "estado_scope"),
        Index("ix_procesos_curriculares_coordinacion_id", "coordinacion_id"),
        Index("ix_procesos_curriculares_especialidad_id", "especialidad_id"),
        Index("ix_procesos_curriculares_programa_id", "programa_id"),
        Index("ix_procesos_curriculares_proyecto_id", "proyecto_id"),
    )

    referencia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
    )
    coordinacion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coordinaciones.id", ondelete="SET NULL"),
        nullable=True,
    )
    especialidad_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("especialidades.id", ondelete="SET NULL"),
        nullable=True,
    )
    equipo_ejecutor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("equipos_ejecutores.id", ondelete="SET NULL"),
        nullable=True,
    )
    lider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    tipo_necesidad: Mapped[TipoNecesidadProceso] = mapped_column(
        tipo_necesidad_enum,
        default=TipoNecesidadProceso.CREAR_PLANEACION,
        nullable=False,
    )
    estado_scope: Mapped[EstadoScopeProceso] = mapped_column(
        estado_scope_enum,
        default=EstadoScopeProceso.SIN_ASIGNAR,
        nullable=False,
    )
    programa_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("programas_formacion.id", ondelete="SET NULL"),
        nullable=True,
    )
    proyecto_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("proyectos_formativos.id", ondelete="SET NULL"),
        nullable=True,
    )
    creado_por: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )

    coordinacion: Mapped[Coordinacion | None] = relationship(
        "Coordinacion",
        foreign_keys=[coordinacion_id],
        lazy="selectin",
    )
    especialidad: Mapped[Especialidad | None] = relationship(
        "Especialidad",
        foreign_keys=[especialidad_id],
        lazy="selectin",
    )
    equipo_ejecutor: Mapped[EquipoEjecutor | None] = relationship(
        "EquipoEjecutor",
        back_populates="procesos",
        lazy="selectin",
    )
    lider: Mapped[Usuario | None] = relationship(
        "Usuario",
        foreign_keys=[lider_id],
        lazy="selectin",
    )
    programa: Mapped[ProgramaFormacion | None] = relationship(
        "ProgramaFormacion",
        foreign_keys=[programa_id],
        lazy="selectin",
    )
    proyecto: Mapped[ProyectoFormativo | None] = relationship(
        "ProyectoFormativo",
        foreign_keys=[proyecto_id],
        lazy="selectin",
    )
