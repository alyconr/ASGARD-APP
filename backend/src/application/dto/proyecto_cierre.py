"""DTOs for project completion validation and explicit closing."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from src.domain.shared.enums import EstadoBloque


@dataclass(frozen=True)
class ProyectoCompletitudFaltanteDTO:
    """Structured missing requirement returned to the UI."""

    codigo: str
    campo: str
    mensaje: str
    fase_id: uuid.UUID | None = None
    fase_nombre: str | None = None


@dataclass(frozen=True)
class ProyectoCompletitudResumenDTO:
    """Counts used to explain project closing readiness."""

    fases: int
    actividades: int


@dataclass(frozen=True)
class ProyectoCompletitudDTO:
    """Result of evaluating whether a project can be closed."""

    referencia_id: uuid.UUID
    proyecto_id: uuid.UUID | None
    estado_actual: EstadoBloque | None
    cerrable: bool
    resumen: ProyectoCompletitudResumenDTO
    faltantes: list[ProyectoCompletitudFaltanteDTO] = field(default_factory=list)


@dataclass(frozen=True)
class ProyectoCierreDTO:
    """Result returned after an explicit project closing action."""

    referencia_id: uuid.UUID
    proyecto_id: uuid.UUID
    estado: EstadoBloque
    mensaje: str
    completitud: ProyectoCompletitudDTO
