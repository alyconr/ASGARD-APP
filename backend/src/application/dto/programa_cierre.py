"""DTOs for TASK-14 program completion validation and closing."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from src.domain.shared.enums import EstadoBloque


@dataclass(frozen=True)
class ProgramaCompletitudFaltanteDTO:
    """Structured missing requirement returned to the UI."""

    codigo: str
    campo: str
    mensaje: str
    competencia_id: uuid.UUID | None = None
    competencia_codigo: str | None = None
    competencia_nombre: str | None = None


@dataclass(frozen=True)
class ProgramaCompletitudResumenDTO:
    """Counts used by the review UI to explain closure readiness."""

    competencias: int
    resultados: int
    conocimientos_saber: int
    conocimientos_proceso: int
    criterios: int


@dataclass(frozen=True)
class ProgramaCompletitudDTO:
    """Result of evaluating whether a program can be closed."""

    referencia_id: uuid.UUID
    programa_id: uuid.UUID | None
    estado_actual: EstadoBloque | None
    cerrable: bool
    resumen: ProgramaCompletitudResumenDTO
    faltantes: list[ProgramaCompletitudFaltanteDTO] = field(default_factory=list)


@dataclass(frozen=True)
class ProgramaCierreDTO:
    """Result returned after an explicit program closing action."""

    referencia_id: uuid.UUID
    programa_id: uuid.UUID
    estado: EstadoBloque
    mensaje: str
    completitud: ProgramaCompletitudDTO
