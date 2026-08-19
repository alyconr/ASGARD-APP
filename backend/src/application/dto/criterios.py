"""DTOs for TASK-12 criteria CRUD operations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from src.domain.shared.enums import EstadoCampo


@dataclass(frozen=True)
class CriterioDTO:
    """Criteria item returned by the application service."""

    id: uuid.UUID
    competencia_id: uuid.UUID
    resultado_id: uuid.UUID | None
    descripcion: str
    orden: int | None
    estado: EstadoCampo
    fecha_creacion: datetime
    fecha_actualizacion: datetime


@dataclass(frozen=True)
class CriterioPayloadDTO:
    """Payload accepted for creating or updating a criteria item."""

    descripcion: str


@dataclass(frozen=True)
class CriterioListDTO:
    """Criteria collection tied to a stable draft reference."""

    referencia_id: uuid.UUID
    competencia_id: uuid.UUID
    criterios: list[CriterioDTO]


@dataclass(frozen=True)
class CriterioDeleteDTO:
    """Result returned after deleting a criteria item."""

    referencia_id: uuid.UUID
    competencia_id: uuid.UUID
    criterio_id: uuid.UUID
    eliminado: bool
