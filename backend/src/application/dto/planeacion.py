"""Pydantic schemas for Pedagogical Planning data transfer objects."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.domain.shared.enums import TipoResultadoProyecto


# Context retrieval DTOs (project curricular structure tree)
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


class ContextoResultadoDTO(BaseModel):
    """Learning result assigned to a project activity."""

    id: uuid.UUID
    codigo_resultado: str | None = None
    descripcion: str
    tipo_resultado: TipoResultadoProyecto | None
    orden_resultado: int | None = None

    model_config = {"from_attributes": True}


class ContextoCompetenciaDTO(BaseModel):
    """Competence context scoped to one project activity."""

    id: uuid.UUID
    codigo_competencia: str
    nombre_competencia: str
    resultados: list[ContextoResultadoDTO]
    conocimientos_saber: list[ContextoConocimientoDTO]
    conocimientos_proceso: list[ContextoConocimientoDTO]
    criterios: list[ContextoCriterioDTO]

    model_config = {"from_attributes": True}


class ContextoActividadDTO(BaseModel):
    """Project activity with its assigned competencies."""

    id: uuid.UUID
    descripcion: str
    orden: int | None = None
    competencias: list[ContextoCompetenciaDTO] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ContextoFaseDTO(BaseModel):
    """Project phase context tree."""

    id: uuid.UUID
    nombre_fase: str
    orden: int | None = None
    actividades: list[ContextoActividadDTO]

    model_config = {"from_attributes": True}


class PlaneacionContextoDTO(BaseModel):
    """Navigable project curricular structure used to build planning."""

    programa_id: uuid.UUID
    codigo_programa: str
    nombre_programa: str
    version_programa: str | None = None
    proyecto_id: uuid.UUID
    codigo_proyecto: str
    nombre_proyecto: str
    version_proyecto: str | None = None
    fases: list[ContextoFaseDTO]

    model_config = {"from_attributes": True}


# Create / Update requests
class PlaneacionSaveDTO(BaseModel):
    """Save payload for an integrated pedagogical planning draft."""

    planeacion_id: uuid.UUID | None = None
    proyecto_id: uuid.UUID
    fase_id: uuid.UUID
    actividad_id: uuid.UUID
    resultados_ids: list[uuid.UUID] = Field(min_length=1)
    conocimientos_ids: list[uuid.UUID] = Field(default_factory=list)
    criterios_ids: list[uuid.UUID] = Field(default_factory=list)
    datos_complementarios: dict[str, object] = Field(default_factory=dict)


# Responses
class PlaneacionResultadoResumenDTO(BaseModel):
    """One learning result inside an integrated planning."""

    id: uuid.UUID
    codigo_resultado: str | None = None
    descripcion: str
    tipo_resultado: TipoResultadoProyecto | None

    model_config = {"from_attributes": True}


class PlaneacionCompetenciaResumenDTO(BaseModel):
    """One competency grouped with its selected learning results."""

    competencia_id: uuid.UUID
    codigo_competencia: str
    nombre_competencia: str
    tipo_resultado: TipoResultadoProyecto | None
    resultados: list[PlaneacionResultadoResumenDTO] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PlaneacionListCompetenciaDTO(BaseModel):
    """Competence item summary inside a planning list response."""

    competencia_id: uuid.UUID
    codigo_competencia: str
    resultados_count: int = 0

    model_config = {"from_attributes": True}


class PlaneacionResponseDTO(BaseModel):
    """Integrated pedagogical planning representation."""

    id: uuid.UUID
    proyecto_id: uuid.UUID
    fase_id: uuid.UUID | None = None
    actividad_id: uuid.UUID | None = None
    estado: str
    datos_complementarios: dict[str, object]
    resultados_ids: list[uuid.UUID]
    conocimientos_ids: list[uuid.UUID]
    criterios_ids: list[uuid.UUID]
    competencias: list[PlaneacionCompetenciaResumenDTO] = Field(default_factory=list)
    storage_key: str | None = None
    file_name: str | None = None
    content_type: str | None = None
    checksum_sha256: str | None = None
    fecha_generacion: datetime | None = None
    version: int

    model_config = {"from_attributes": True}


class PlaneacionListDTO(BaseModel):
    """Summary item of an integrated planning for dashboard views."""

    id: uuid.UUID
    proyecto_id: uuid.UUID
    fase_id: uuid.UUID | None = None
    actividad_id: uuid.UUID | None = None
    nombre_fase: str | None = None
    descripcion_actividad: str | None = None
    actividades_aprendizaje: str | None = None
    estado: str
    competencias: list[PlaneacionListCompetenciaDTO] = Field(default_factory=list)
    competencias_count: int = 0
    resultados_count: int = 0
    resultados_especificos: int = 0
    resultados_transversales: int = 0
    fecha_actualizacion: datetime

    model_config = {"from_attributes": True}


ClasificacionInformacion = Literal[
    "PUBLICA",
    "PUBLICA_CLASIFICADA",
    "PUBLICA_RESERVADA",
]


class PlaneacionDocumentoConfigUpdateDTO(BaseModel):
    """Institutional metadata shared by all planning rows in a project."""

    fecha_elaboracion: date
    modalidad_formacion: str = Field(min_length=1, max_length=150)
    clasificacion_informacion: ClasificacionInformacion
    equipo_gestion_curricular: list[str] = Field(min_length=1)
    regional: str = Field(min_length=1)
    centro_formacion: str = Field(min_length=1)


class PlaneacionDocumentoConfigDTO(BaseModel):
    """Persisted official workbook configuration and consolidated artifact."""

    proyecto_id: uuid.UUID
    fecha_elaboracion: date | None = None
    modalidad_formacion: str | None = None
    clasificacion_informacion: ClasificacionInformacion | None = None
    equipo_gestion_curricular: list[str] = Field(default_factory=list)
    regional: str | None = None
    centro_formacion: str | None = None
    storage_key: str | None = None
    file_name: str | None = None
    content_type: str | None = None
    checksum_sha256: str | None = None
    fecha_generacion: datetime | None = None
    version: int = 1


class FormatoOficialFaltanteDTO(BaseModel):
    """One actionable gap that blocks the official workbook."""

    codigo: str
    mensaje: str
    paso: Literal["configuracion", "curricular", "complementario", "confirmacion"]


class FormatoOficialEstadoDTO(BaseModel):
    """Backend-derived generation readiness for one planning or one project."""

    listo: bool
    faltantes: list[FormatoOficialFaltanteDTO] = Field(default_factory=list)
    planeaciones_completas: int = 0
    borradores_excluidos: int = 0
    storage_key: str | None = None
    file_name: str | None = None
    checksum_sha256: str | None = None
    fecha_generacion: datetime | None = None


class FormatoOficialGeneradoDTO(BaseModel):
    """Metadata returned after storing an official workbook."""

    storage_key: str
    file_name: str
    content_type: str
    checksum_sha256: str
    fecha_generacion: datetime
    version: int
    filas_generadas: int
    planeaciones_incluidas: int
    borradores_excluidos: int = 0
