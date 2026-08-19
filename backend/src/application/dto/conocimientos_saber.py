"""DTOs for TASK-10 SABER knowledge CRUD operations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from src.domain.shared.enums import EstadoCampo, TipoConocimiento


@dataclass(frozen=True)
class ConocimientoSaberDTO:
    """SABER knowledge item returned by the application service."""

    id: uuid.UUID
    competencia_id: uuid.UUID
    resultado_id: uuid.UUID | None
    tipo: TipoConocimiento
    descripcion: str
    orden: int | None
    estado: EstadoCampo
    fecha_creacion: datetime
    fecha_actualizacion: datetime


@dataclass(frozen=True)
class ConocimientoSaberPayloadDTO:
    """Payload accepted for creating or updating a SABER knowledge item."""

    descripcion: str


@dataclass(frozen=True)
class ConocimientoSaberListDTO:
    """SABER knowledge collection tied to a stable draft reference."""

    referencia_id: uuid.UUID
    competencia_id: uuid.UUID
    conocimientos: list[ConocimientoSaberDTO]


@dataclass(frozen=True)
class ConocimientoSaberDeleteDTO:
    """Result returned after deleting a SABER knowledge item."""

    referencia_id: uuid.UUID
    competencia_id: uuid.UUID
    conocimiento_id: uuid.UUID
    eliminado: bool
