"""HTTP schemas for TASK-14 program completion validation and closing."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from src.domain.shared.enums import EstadoBloque


class ProgramaCompletitudFaltanteResponse(BaseModel):
    """Structured missing requirement returned to the frontend."""

    model_config = ConfigDict(from_attributes=True)

    codigo: str
    campo: str
    mensaje: str
    competencia_id: uuid.UUID | None = None
    competencia_codigo: str | None = None
    competencia_nombre: str | None = None


class ProgramaCompletitudResumenResponse(BaseModel):
    """Counts used to explain program closing readiness."""

    model_config = ConfigDict(from_attributes=True)

    competencias: int
    resultados: int
    conocimientos_saber: int
    conocimientos_proceso: int
    criterios: int


class ProgramaCompletitudResponse(BaseModel):
    """Readiness response for the program close action."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    programa_id: uuid.UUID | None
    estado_actual: EstadoBloque | None
    cerrable: bool
    resumen: ProgramaCompletitudResumenResponse
    faltantes: list[ProgramaCompletitudFaltanteResponse]


class ProgramaCierreResponse(BaseModel):
    """Successful explicit program close response."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    programa_id: uuid.UUID
    estado: EstadoBloque
    mensaje: str
    completitud: ProgramaCompletitudResponse
