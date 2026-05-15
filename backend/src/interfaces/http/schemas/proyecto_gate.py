"""HTTP schemas for TASK-15 project availability gate."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from src.domain.shared.enums import EstadoBloque


class ProyectoDisponibilidadResponse(BaseModel):
    """Structured response explaining whether the project module is blocked."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    programa_id: uuid.UUID | None
    estado_programa: EstadoBloque | None
    programa_completo: bool
    proyecto_bloqueado: bool
    estado_proyecto: EstadoBloque
    motivo: str | None
    mensaje: str
    accion_sugerida: str
