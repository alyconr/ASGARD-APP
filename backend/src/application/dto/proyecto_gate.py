"""DTOs for TASK-15 project availability gate."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.domain.shared.enums import EstadoBloque


@dataclass(frozen=True)
class ProyectoDisponibilidadDTO:
    """Structured project availability result for backend and frontend callers."""

    referencia_id: uuid.UUID
    programa_id: uuid.UUID | None
    estado_programa: EstadoBloque | None
    programa_completo: bool
    proyecto_bloqueado: bool
    estado_proyecto: EstadoBloque
    motivo: str | None
    mensaje: str
    accion_sugerida: str
    programa_referencia_id: uuid.UUID | None = None
