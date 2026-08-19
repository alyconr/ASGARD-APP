"""HTTP schemas for PROCESO knowledge CRUD endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.shared.enums import EstadoCampo, TipoConocimiento


class ConocimientoProcesoRequest(BaseModel):
    """Input accepted when creating or updating a PROCESO knowledge item."""

    model_config = ConfigDict(extra="forbid")

    descripcion: str = Field(min_length=1)

    @field_validator("descripcion")
    @classmethod
    def trim_and_reject_blank(cls, value: str) -> str:
        """Normalize text fields before the application service runs."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("La descripcion no puede estar vacia")
        return normalized


class ConocimientoProcesoResponse(BaseModel):
    """PROCESO knowledge representation returned to the frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    competencia_id: uuid.UUID
    resultado_id: uuid.UUID | None = None
    tipo: TipoConocimiento
    descripcion: str
    orden: int | None = None
    estado: EstadoCampo
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class ConocimientoProcesoListResponse(BaseModel):
    """List response tied to a stable draft reference and competence."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    competencia_id: uuid.UUID
    conocimientos: list[ConocimientoProcesoResponse]


class ConocimientoProcesoDeleteResponse(BaseModel):
    """Delete response for explicit UI confirmation flows."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    competencia_id: uuid.UUID
    conocimiento_id: uuid.UUID
    eliminado: bool
