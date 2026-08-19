"""HTTP schemas for project completion validation and closing."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from src.domain.shared.enums import EstadoBloque


class ProyectoCompletitudFaltanteResponse(BaseModel):
    """Structured missing requirement returned to the frontend."""

    model_config = ConfigDict(from_attributes=True)

    codigo: str
    campo: str
    mensaje: str
    fase_id: uuid.UUID | None = None
    fase_nombre: str | None = None


class ProyectoCompletitudResumenResponse(BaseModel):
    """Counts used to explain project closing readiness."""

    model_config = ConfigDict(from_attributes=True)

    fases: int
    actividades: int


class ProyectoCompletitudResponse(BaseModel):
    """Readiness response for the project close action."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    proyecto_id: uuid.UUID | None
    estado_actual: EstadoBloque | None
    cerrable: bool
    resumen: ProyectoCompletitudResumenResponse
    faltantes: list[ProyectoCompletitudFaltanteResponse]


class ProyectoCierreResponse(BaseModel):
    """Successful explicit project close response."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    proyecto_id: uuid.UUID
    estado: EstadoBloque
    mensaje: str
    completitud: ProyectoCompletitudResponse
