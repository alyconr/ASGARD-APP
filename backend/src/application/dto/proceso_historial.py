"""DTOs for tracking and reporting changes on a single ProcesoCurricular instance."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class CambioActorDTO:
    """Actor identity associated with a change on the curricular process."""

    id: UUID | None
    nombre: str
    apellido: str
    email: str
    rol: str


@dataclass(frozen=True)
class CambioProcesoItemDTO:
    """Single event or modification performed on this curricular process."""

    id: UUID
    fecha_evento: datetime
    accion: str
    tipo_evento: str
    descripcion: str
    actor: CambioActorDTO | None
    entidad: str
    entidad_id: UUID | None
    detalle: dict[str, Any] | None


@dataclass(frozen=True)
class HistorialProcesoDTO:
    """Consolidated change history and current lifecycle state of a unique curricular process."""

    proceso_id: UUID
    referencia_id: UUID
    estado_scope: str
    tipo_necesidad: str
    equipo: dict[str, Any] | None
    programa: dict[str, Any] | None
    proyecto: dict[str, Any] | None
    planeaciones: dict[str, Any]
    fecha_creacion: datetime
    fecha_ultima_modificacion: datetime
    total_cambios: int
    cambios: list[CambioProcesoItemDTO] = field(default_factory=list)
    garantia_unicidad: bool = True
    mensaje_unicidad: str = "Este proceso opera bajo una instancia curricular única y consolidada sin duplicidad."
