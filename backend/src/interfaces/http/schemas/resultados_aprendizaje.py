"""HTTP schemas for learning outcomes (resultados de aprendizaje)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.shared.enums import EstadoCampo, MotivoFalloExtraccion


class ResultadoAprendizajeRequest(BaseModel):
    """Input accepted when creating or updating a learning outcome."""

    descripcion: str = Field(min_length=1)
    codigo_resultado: str | None = Field(None, max_length=100)

    @field_validator("descripcion")
    @classmethod
    def trim_and_reject_blank(cls, value: str) -> str:
        """Normalize text fields before the application service runs."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("La descripcion no puede estar vacia")
        return normalized


class ResultadoAprendizajeResponse(BaseModel):
    """Learning outcome representation returned to the frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    competencia_id: uuid.UUID
    codigo_resultado: str | None = None
    descripcion: str
    orden: int | None = None
    estado: EstadoCampo
    motivo_fallo_extraccion: MotivoFalloExtraccion | None = None
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class ResultadoAprendizajeListResponse(BaseModel):
    """List response tied to a stable draft reference and competence."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    competencia_id: uuid.UUID
    resultados: list[ResultadoAprendizajeResponse]


class ResultadoAprendizajeDeleteResponse(BaseModel):
    """Delete response for explicit UI confirmation flows."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    competencia_id: uuid.UUID
    resultado_id: uuid.UUID
    eliminado: bool
