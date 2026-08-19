"""HTTP schemas for criteria CRUD endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.shared.enums import EstadoCampo


class CriterioRequest(BaseModel):
    """Input accepted when creating or updating a criteria item."""

    model_config = ConfigDict(extra="forbid")

    descripcion: str = Field(min_length=1)

    @field_validator("descripcion")
    @classmethod
    def trim_and_reject_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("La descripcion no puede estar vacia")
        return normalized


class CriterioResponse(BaseModel):
    """Criteria representation returned to the frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    competencia_id: uuid.UUID
    resultado_id: uuid.UUID | None = None
    descripcion: str
    orden: int | None = None
    estado: EstadoCampo
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class CriterioListResponse(BaseModel):
    """List response tied to a stable draft reference and competence."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    competencia_id: uuid.UUID
    criterios: list[CriterioResponse]


class CriterioDeleteResponse(BaseModel):
    """Delete response for explicit UI confirmation flows."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    competencia_id: uuid.UUID
    criterio_id: uuid.UUID
    eliminado: bool
