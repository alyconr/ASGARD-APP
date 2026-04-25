"""ORM model for basic audit events."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base
from src.infrastructure.db.models.mixins import UUIDPrimaryKeyMixin


class EventoAuditoria(UUIDPrimaryKeyMixin, Base):
    """Basic audit trail entry required by Phase 1."""

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
    )

    entidad: Mapped[str] = mapped_column(String(100), nullable=False)
    entidad_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    accion: Mapped[str] = mapped_column(String(100), nullable=False)
    detalle: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    fecha_evento: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
