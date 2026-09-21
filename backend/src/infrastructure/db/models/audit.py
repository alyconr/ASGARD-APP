"""ORM model for basic audit events."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base
from src.infrastructure.db.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.infrastructure.db.models.auth import Usuario


class EventoAuditoria(UUIDPrimaryKeyMixin, Base):
    """Audit trail entry with optional structured actor and process references."""

    __tablename__ = "eventos_auditoria"
    __table_args__ = (
        CheckConstraint(
            "btrim(entidad) <> ''",
            name="entidad_not_blank",
        ),
        CheckConstraint(
            "btrim(accion) <> ''",
            name="accion_not_blank",
        ),
        Index("ix_eventos_auditoria_fecha_evento", "fecha_evento"),
        Index("ix_eventos_auditoria_accion", "accion"),
        Index("ix_eventos_auditoria_entidad", "entidad"),
        Index("ix_eventos_auditoria_actor_usuario_id", "actor_usuario_id"),
        Index("ix_eventos_auditoria_referencia_id", "referencia_id"),
    )

    entidad: Mapped[str] = mapped_column(String(100), nullable=False)
    entidad_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    accion: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    referencia_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    detalle: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    fecha_evento: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    actor: Mapped[Usuario | None] = relationship(
        "Usuario",
        foreign_keys=[actor_usuario_id],
        lazy="selectin",
    )
