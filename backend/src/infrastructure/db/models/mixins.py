"""Reusable SQLAlchemy helpers for the Phase 1 schema."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


def build_postgres_enum(enum_class: type[Enum], name: str) -> SqlEnum:
    """Create a reusable PostgreSQL enum definition for a Python enum."""

    return SqlEnum(
        enum_class,
        name=name,
        native_enum=True,
        validate_strings=True,
    )


class UUIDPrimaryKeyMixin:
    """Provide a UUID primary key for persisted entities."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    """Provide creation and update timestamps for persisted entities."""

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
