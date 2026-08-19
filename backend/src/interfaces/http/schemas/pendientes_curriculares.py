"""HTTP schemas for Excel curricular pending reconciliation."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.domain.shared.enums import (
    EstadoConciliacionPendiente,
    MotivoPendienteAsignacion,
    TipoConocimiento,
    TipoElementoCurricularPendiente,
)


class PendienteCurricularAsignacionRequest(BaseModel):
    """Manual assignment request for one pending curricular row."""

    competencia_id: uuid.UUID
    resultado_id: uuid.UUID | None = None


class PendienteCurricularResponse(BaseModel):
    """Pending curricular row returned to the frontend."""

    model_config = ConfigDict(from_attributes=True)

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


class PendienteCurricularListResponse(BaseModel):
    """List response scoped to a stable wizard reference."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    pendientes: list[PendienteCurricularResponse]


class PendienteCurricularAsignacionResponse(BaseModel):
    """Response after assigning a pending row."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    pendiente: PendienteCurricularResponse
