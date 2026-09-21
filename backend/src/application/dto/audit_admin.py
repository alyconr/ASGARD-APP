"""DTOs for institutional audit query service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class AuditFilterDTO:
    """Filter parameters for querying audit logs."""

    page: int = 1
    page_size: int = 50
    fecha_desde: datetime | None = None
    fecha_hasta: datetime | None = None
    actor_usuario_id: UUID | None = None
    accion: str | None = None
    entidad: str | None = None
    referencia_id: UUID | None = None
    search: str | None = None


@dataclass(frozen=True)
class ActorSummaryDTO:
    """Actor identity projection for audit records."""

    id: UUID
    nombre: str
    apellido: str
    email: str
    rol: str


@dataclass(frozen=True)
class AuditItemDTO:
    """Single sanitized audit event projection."""

    id: UUID
    fecha_evento: datetime
    accion: str
    entidad: str
    entidad_id: UUID
    actor: ActorSummaryDTO | None
    referencia_id: UUID | None
    detalle: dict[str, Any] | None


@dataclass(frozen=True)
class AuditPaginatedResponseDTO:
    """Paginated list of audit events."""

    items: list[AuditItemDTO]
    total: int
    page: int
    page_size: int
    total_pages: int
