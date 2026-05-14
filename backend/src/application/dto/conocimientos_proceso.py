"""DTOs for TASK-11 PROCESO knowledge CRUD operations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from src.domain.shared.enums import EstadoCampo, TipoConocimiento


@dataclass(frozen=True)
class ConocimientoProcesoDTO:
    """PROCESO knowledge item returned by the application service."""

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
class ConocimientoProcesoPayloadDTO:
    """Payload accepted for creating or updating a PROCESO knowledge item."""

    descripcion: str


@dataclass(frozen=True)
class ConocimientoProcesoListDTO:
    """PROCESO knowledge collection tied to a stable draft reference."""

    referencia_id: uuid.UUID
    competencia_id: uuid.UUID
    conocimientos: list[ConocimientoProcesoDTO]


@dataclass(frozen=True)
class ConocimientoProcesoDeleteDTO:
    """Result returned after deleting a PROCESO knowledge item."""

    referencia_id: uuid.UUID
    competencia_id: uuid.UUID
    conocimiento_id: uuid.UUID
    eliminado: bool
