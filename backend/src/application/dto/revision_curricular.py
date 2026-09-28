"""DTOs for curricular submission, pedagogical review, feedback, and approvals."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.domain.shared.enums import (
    EstadoEntregaRevision,
    EstadoObservacionRevision,
    TipoElementoObservacion,
)


class PreflightEnvioRevisionDTO(BaseModel):
    """Result of validating whether a curricular process is ready for submission."""

    listo: bool
    pendientes: list[str]
    advertencias: list[str] = Field(default_factory=list)
    resumen: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class EnvioRevisionRequestDTO(BaseModel):
    """Payload sent by executor team when submitting/resubmitting a process."""

    notas_entrega: str | None = None


class ObservacionCreateDTO(BaseModel):
    """Payload from pedagogical reviewer creating an observation."""

    target_type: TipoElementoObservacion
    target_id: uuid.UUID | None = None
    section_key: str | None = None
    comentario: str = Field(..., min_length=3)


class AjusteReportarDTO(BaseModel):
    """Payload from executor team reporting that an observation was addressed."""

    comentario_ajuste: str = Field(..., min_length=3)


class ObservacionDTO(BaseModel):
    """Full detail of an observation with audit user names and timestamps."""

    id: uuid.UUID
    entrega_id: uuid.UUID
    target_type: TipoElementoObservacion
    target_id: uuid.UUID | None = None
    section_key: str | None = None
    comentario: str
    estado: EstadoObservacionRevision

    creado_por_id: uuid.UUID
    creado_por_nombre: str
    fecha_creacion: datetime

    ajuste_reportado_por_id: uuid.UUID | None = None
    ajuste_reportado_por_nombre: str | None = None
    fecha_ajuste_reportado: datetime | None = None
    comentario_ajuste: str | None = None

    resuelto_por_id: uuid.UUID | None = None
    resuelto_por_nombre: str | None = None
    fecha_resolucion: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class EntregaRevisionResumenDTO(BaseModel):
    """Summary item for the pedagogical reviewer dashboard."""

    id: uuid.UUID
    proceso_curricular_id: uuid.UUID
    referencia_id: uuid.UUID
    equipo_ejecutor_id: uuid.UUID | None = None
    equipo_ejecutor_nombre: str = "Equipo"
    programa_id: uuid.UUID | None = None
    codigo_programa: str = ""
    nombre_programa: str = ""
    proyecto_id: uuid.UUID | None = None
    codigo_proyecto: str = ""
    nombre_proyecto: str = ""
    lider_nombre: str = "Sin líder"
    lider_email: str = ""
    version: int = 1
    estado: EstadoEntregaRevision
    fecha_envio: datetime
    observaciones_pendientes_count: int = 0
    observaciones_ajustadas_count: int = 0
    observaciones_resueltas_count: int = 0
    descarga_habilitada: bool = False
    fecha_actualizacion: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class EntregaRevisionDetalleDTO(EntregaRevisionResumenDTO):
    """Full detail of an individual delivery version, including observations and history."""

    notas_entrega: str | None = None
    notas_aprobacion: str | None = None
    snapshot_metadatos: dict[str, Any] = Field(default_factory=dict)
    observaciones: list[ObservacionDTO] = Field(default_factory=list)
    historial_versiones: list[EntregaRevisionResumenDTO] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class BandejaRevisionFiltrosDTO(BaseModel):
    """Filter parameters for pedagogical review inbox."""

    estado: EstadoEntregaRevision | None = None
    programa_id: uuid.UUID | None = None
    equipo_ejecutor_id: uuid.UUID | None = None
    lider_id: uuid.UUID | None = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class BandejaRevisionPaginadaDTO(BaseModel):
    """Paginated inbox of curricular submissions with real summary statistics."""

    items: list[EntregaRevisionResumenDTO]
    total: int
    page: int
    limit: int
    total_pages: int
    metricas: dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class AprobacionRequestDTO(BaseModel):
    """Payload for final approval and download authorization."""

    notas_aprobacion: str | None = None


# -----------------------------------------------------------------------------
# Read-only Planning Review Inspection DTOs
# -----------------------------------------------------------------------------


class FaseResumenDTO(BaseModel):
    id: uuid.UUID | None = None
    nombre: str
    orden: int | None = None
    model_config = ConfigDict(from_attributes=True)


class ActividadProyectoResumenDTO(BaseModel):
    id: uuid.UUID | None = None
    descripcion: str
    orden: int | None = None
    model_config = ConfigDict(from_attributes=True)


class RAPResumenDTO(BaseModel):
    id: uuid.UUID
    codigo: str | None = None
    descripcion: str
    tipo_resultado: str | None = None
    model_config = ConfigDict(from_attributes=True)


class CompetenciaResumenDTO(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    resultados_count: int = 0
    resultados: list[RAPResumenDTO] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class ConocimientoResumenDTO(BaseModel):
    id: uuid.UUID
    tipo: str
    descripcion: str
    model_config = ConfigDict(from_attributes=True)


class CriterioResumenDTO(BaseModel):
    id: uuid.UUID
    codigo: str | None = None
    descripcion: str
    model_config = ConfigDict(from_attributes=True)


class HorasPlaneacionDTO(BaseModel):
    directas: float = 0.0
    independientes: float = 0.0
    total: float = 0.0


class PlaneacionRevisionItemDTO(BaseModel):
    """Summary item for the planning tree belonging to an official delivery version."""

    id: uuid.UUID
    estado: str
    fase: FaseResumenDTO
    actividad_proyecto: ActividadProyectoResumenDTO
    competencias: list[CompetenciaResumenDTO] = Field(default_factory=list)
    raps: list[RAPResumenDTO] = Field(default_factory=list)
    actividades_aprendizaje: str
    horas: HorasPlaneacionDTO
    ambiente: str | None = None
    instructores: str | None = None
    observaciones_count: int = 0
    observaciones_pendientes_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class PlaneacionesEntregaListDTO(BaseModel):
    """Collection of plannings strictly frozen in this delivery snapshot."""

    entrega_id: uuid.UUID
    version: int
    total: int
    horas_directas_total: float = 0.0
    horas_independientes_total: float = 0.0
    planeaciones: list[PlaneacionRevisionItemDTO] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PlaneacionRevisionDetalleDTO(BaseModel):
    """Comprehensive read-only inspection payload of one planning for pedagogical review."""

    id: uuid.UUID
    entrega_id: uuid.UUID
    version_entrega: int
    estado: str
    fase: FaseResumenDTO
    actividad_proyecto: ActividadProyectoResumenDTO
    competencias: list[CompetenciaResumenDTO] = Field(default_factory=list)
    conocimientos_saber: list[ConocimientoResumenDTO] = Field(default_factory=list)
    conocimientos_proceso: list[ConocimientoResumenDTO] = Field(default_factory=list)
    criterios_evaluacion: list[CriterioResumenDTO] = Field(default_factory=list)
    actividades_aprendizaje: str = ""
    descripcion_evidencia: str = ""
    estrategias_didacticas: str = ""
    ambientes: str = ""
    materiales: str = ""
    instructores: str = ""
    horas: HorasPlaneacionDTO
    observaciones_didacticas: str | None = None
    observaciones: list[ObservacionDTO] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
