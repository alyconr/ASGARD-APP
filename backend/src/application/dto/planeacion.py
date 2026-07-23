"""Pydantic schemas for Pedagogical Planning data transfer objects."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# Context retrieval DTOs
class ContextoResultadoDTO(BaseModel):
    """Learning result context metadata."""

    id: uuid.UUID
    descripcion: str
    fase_id: uuid.UUID | None = None
    actividad_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class ContextoConocimientoDTO(BaseModel):
    """Knowledge item context metadata."""

    id: uuid.UUID
    descripcion: str

    model_config = {"from_attributes": True}


class ContextoCriterioDTO(BaseModel):
    """Evaluation criteria context metadata."""

    id: uuid.UUID
    descripcion: str

    model_config = {"from_attributes": True}


class ContextoCompetenciaDTO(BaseModel):
    """Competence context tree."""

    id: uuid.UUID
    codigo_competencia: str
    nombre_competencia: str
    resultados: list[ContextoResultadoDTO]
    conocimientos_saber: list[ContextoConocimientoDTO]
    conocimientos_proceso: list[ContextoConocimientoDTO]
    criterios: list[ContextoCriterioDTO]

    model_config = {"from_attributes": True}


class ContextoActividadDTO(BaseModel):
    """Project activity context metadata."""

    id: uuid.UUID
    descripcion: str

    model_config = {"from_attributes": True}


class ContextoFaseDTO(BaseModel):
    """Project phase context tree."""

    id: uuid.UUID
    nombre_fase: str
    actividades: list[ContextoActividadDTO]

    model_config = {"from_attributes": True}


class PlaneacionContextoDTO(BaseModel):
    """Global context containing curriculum program and project structure."""

    programa_id: uuid.UUID
    codigo_programa: str
    nombre_programa: str
    proyecto_id: uuid.UUID
    codigo_proyecto: str
    nombre_proyecto: str
    competencias: list[ContextoCompetenciaDTO]
    fases: list[ContextoFaseDTO]

    model_config = {"from_attributes": True}


# Create / Update requests
class PlaneacionSaveDTO(BaseModel):
    """Save payload for pedagogical planning draft or completion."""

    proyecto_id: uuid.UUID
    competencia_id: uuid.UUID
    resultado_id: uuid.UUID
    fase_id: uuid.UUID | None = None
    actividad_id: uuid.UUID | None = None
    resultados_ids: list[uuid.UUID] = Field(default_factory=list)
    conocimientos_ids: list[uuid.UUID] = Field(default_factory=list)
    criterios_ids: list[uuid.UUID] = Field(default_factory=list)
    datos_complementarios: dict[str, object] = Field(default_factory=dict)


# Responses
class PlaneacionResponseDTO(BaseModel):
    """Pedagogical planning representation."""

    id: uuid.UUID
    proyecto_id: uuid.UUID
    competencia_id: uuid.UUID
    resultado_id: uuid.UUID
    resultado_descripcion: str | None = None
    fase_id: uuid.UUID | None = None
    actividad_id: uuid.UUID | None = None
    estado: str
    datos_complementarios: dict[str, object]
    resultados_ids: list[uuid.UUID]
    conocimientos_ids: list[uuid.UUID]
    criterios_ids: list[uuid.UUID]
    storage_key: str | None = None
    file_name: str | None = None
    content_type: str | None = None
    checksum_sha256: str | None = None
    fecha_generacion: datetime | None = None
    version: int

    model_config = {"from_attributes": True}


class PlaneacionListDTO(BaseModel):
    """Summary item of a planning for dashboard views."""

    id: uuid.UUID
    proyecto_id: uuid.UUID
    competencia_id: uuid.UUID
    resultado_id: uuid.UUID
    resultado_descripcion: str
    codigo_competencia: str
    nombre_competencia: str
    estado: str
    fecha_actualizacion: datetime

    model_config = {"from_attributes": True}
