"""ORM models for persisted draft sessions."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.domain.shared.enums import EstadoBloque
from src.infrastructure.db.base import Base
from src.infrastructure.db.models.curriculum import estado_bloque_enum
from src.infrastructure.db.models.mixins import UUIDPrimaryKeyMixin


class BorradorSesion(UUIDPrimaryKeyMixin, Base):
    """Persisted wizard state for a program or project block."""

    __tablename__ = "borradores_sesion"
    __table_args__ = (
        UniqueConstraint(
            "tipo_bloque",
            "referencia_id",
            name="uq_borradores_sesion_tipo_bloque_referencia_id",
        ),
        CheckConstraint(
            "btrim(tipo_bloque) <> ''",
            name="tipo_bloque_not_blank",
        ),
        CheckConstraint(
            "btrim(paso_actual) <> ''",
            name="paso_actual_not_blank",
        ),
        Index(
            "ix_borradores_sesion_tipo_bloque_referencia_id",
            "tipo_bloque",
            "referencia_id",
        ),
    )

    tipo_bloque: Mapped[str] = mapped_column(String(50), nullable=False)
    referencia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    paso_actual: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    estado_borrador: Mapped[EstadoBloque] = mapped_column(
        estado_bloque_enum,
        nullable=False,
        default=EstadoBloque.BORRADOR,
    )
    ultima_edicion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
