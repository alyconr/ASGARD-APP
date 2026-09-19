"""ORM models for users, roles, and user assignments."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base
from src.infrastructure.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.infrastructure.db.models.organizacion import (
        Coordinacion,
        EquipoEjecutor,
        EquipoEjecutorMiembro,
        Especialidad,
    )


class UsuarioRol(Base):
    """Association table linking users and their roles."""

    __tablename__ = "usuario_roles"
    __table_args__ = (
        Index("ix_usuario_roles_usuario_id", "usuario_id"),
        Index("ix_usuario_roles_rol_id", "rol_id"),
    )

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    rol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )


class Rol(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """System role entity."""

    __tablename__ = "roles"

    nombre: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)

    usuarios: Mapped[list[Usuario]] = relationship(
        "Usuario",
        secondary="usuario_roles",
        back_populates="roles",
        lazy="selectin",
    )


class Usuario(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """User account entity with organizational scoping."""

    __tablename__ = "usuarios"
    __table_args__ = (
        Index("ix_usuarios_email", "email"),
        Index("ix_usuarios_coordinacion_id", "coordinacion_id"),
        Index("ix_usuarios_especialidad_id", "especialidad_id"),
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)

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
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    roles: Mapped[list[Rol]] = relationship(
        "Rol",
        secondary="usuario_roles",
        back_populates="usuarios",
        lazy="selectin",
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
    equipos_liderados: Mapped[list[EquipoEjecutor]] = relationship(
        "EquipoEjecutor",
        back_populates="lider",
        foreign_keys="EquipoEjecutor.lider_id",
        lazy="selectin",
    )
    membresias: Mapped[list[EquipoEjecutorMiembro]] = relationship(
        "EquipoEjecutorMiembro",
        back_populates="usuario",
        foreign_keys="EquipoEjecutorMiembro.usuario_id",
        lazy="selectin",
    )

    @property
    def role_names(self) -> set[str]:
        """Return the set of role names assigned to the user."""
        return {r.nombre for r in self.roles}

    def has_role(self, *role_names: str) -> bool:
        """Check if user holds any of the specified roles."""
        return bool(self.role_names.intersection(role_names))
