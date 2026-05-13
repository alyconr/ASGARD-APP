"""HTTP schemas for program competence CRUD endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.shared.enums import EstadoBloque, EstadoCampo, TipoConocimiento


class CompetenciaRequest(BaseModel):
    """Input accepted when creating or updating a competence."""

    codigo_competencia: str = Field(min_length=1, max_length=100)
    nombre_competencia: str = Field(min_length=1)

    @field_validator("codigo_competencia", "nombre_competencia")
    @classmethod
    def trim_and_reject_blank(cls, value: str) -> str:
        """Normalize text fields before the application service runs."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("El campo no puede estar vacio")
        return normalized


class ResultadoAprendizajeResumenResponse(BaseModel):
    """Learning result nested inside a competence response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    competencia_id: uuid.UUID
    codigo_resultado: str | None
    descripcion: str
    orden: int | None
    estado: EstadoCampo
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class ConocimientoResumenResponse(BaseModel):
    """Knowledge item nested inside a competence response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    competencia_id: uuid.UUID
    resultado_id: uuid.UUID | None
    tipo: TipoConocimiento
    descripcion: str
    orden: int | None
    estado: EstadoCampo
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class CriterioEvaluacionResumenResponse(BaseModel):
    """Evaluation criterion nested inside a competence response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    competencia_id: uuid.UUID
    resultado_id: uuid.UUID | None
    descripcion: str
    orden: int | None
    estado: EstadoCampo
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class CompetenciaResponse(BaseModel):
    """Competence representation returned to the frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    programa_id: uuid.UUID
    codigo_competencia: str
    nombre_competencia: str
    orden: int | None
    estado: EstadoBloque
    origen_campo: EstadoCampo
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    resultados: list[ResultadoAprendizajeResumenResponse] = []
    conocimientos: list[ConocimientoResumenResponse] = []
    criterios: list[CriterioEvaluacionResumenResponse] = []


class CompetenciaListResponse(BaseModel):
    """List response tied to a stable program draft reference."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    programa_id: uuid.UUID | None
    competencias: list[CompetenciaResponse]


class CompetenciaDeleteResponse(BaseModel):
    """Delete response for explicit UI confirmation flows."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    programa_id: uuid.UUID
    competencia_id: uuid.UUID
    eliminado: bool
