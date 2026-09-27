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
