"""DTOs for Excel curricular pending assignment reconciliation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from src.domain.shared.enums import (
    EstadoConciliacionPendiente,
    MotivoPendienteAsignacion,
    TipoConocimiento,
    TipoElementoCurricularPendiente,
)


@dataclass(frozen=True)
class PendienteCurricularDTO:
    """Curricular element waiting for or already assigned by the user."""

    id: uuid.UUID
    referencia_id: uuid.UUID
    programa_id: uuid.UUID | None
    tipo_elemento: TipoElementoCurricularPendiente
    tipo_conocimiento: TipoConocimiento | None
    descripcion: str
    competencia_id_origen_excel: str | None
    rap_id_origen_excel: str | None
    motivo: MotivoPendienteAsignacion
    estado: EstadoConciliacionPendiente
    competencia_destino_id: uuid.UUID | None
    resultado_destino_id: uuid.UUID | None
    elemento_creado_id: uuid.UUID | None
    fecha_creacion: datetime
    fecha_actualizacion: datetime


@dataclass(frozen=True)
class PendienteCurricularListDTO:
    """List of pending assignment rows for a wizard reference."""

    referencia_id: uuid.UUID
    pendientes: list[PendienteCurricularDTO]


@dataclass(frozen=True)
class PendienteCurricularAsignacionDTO:
    """Manual assignment command selected by the user."""

    competencia_id: uuid.UUID
    resultado_id: uuid.UUID | None = None


@dataclass(frozen=True)
class PendienteCurricularAsignacionResultDTO:
    """Result after materializing a pending row into the final model."""

    referencia_id: uuid.UUID
    pendiente: PendienteCurricularDTO
