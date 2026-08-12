"""HTTP schemas for the master dashboard."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class DashboardModuleResponse(BaseModel):
    """Access state for a main module."""

    id: str
    titulo: str
    estado: str
    disponible: bool
    href: str
    motivo_bloqueo: str | None
    accion_requerida: str
    descripcion: str
    avance_porcentaje: int

    model_config = {"from_attributes": True}


class ProgramaDashboardMetricsResponse(BaseModel):
    """Program metrics."""

    estado: str
    competencias: int
    resultados: int
    conocimientos: int
    criterios: int

    model_config = {"from_attributes": True}


class ProyectoDashboardMetricsResponse(BaseModel):
    """Project metrics."""

    estado: str
    fases: int
    actividades: int
    fuente_estructurada_cargada: bool

    model_config = {"from_attributes": True}


class PlaneacionDashboardMetricsResponse(BaseModel):
    """Planning metrics."""

    estado: str
    total: int
    borrador: int
    completas: int
    actividades_con_planeacion: int
    competencias_con_planeacion: int
    competencias_sin_planear: int
    resultados_con_planeacion: int
    resultados_especificos_con_planeacion: int
    resultados_transversales_con_planeacion: int

    model_config = {"from_attributes": True}


class DashboardMetricsResponse(BaseModel):
    """Metric bundle."""

    programa: ProgramaDashboardMetricsResponse
    proyecto: ProyectoDashboardMetricsResponse
    planeacion: PlaneacionDashboardMetricsResponse

    model_config = {"from_attributes": True}


class DashboardGraphNodeResponse(BaseModel):
    """Navigable visual map node."""

    id: str
    label: str
    tipo: str
    estado: str
    href: str
    disponible: bool
    detalle: str

    model_config = {"from_attributes": True}


class DashboardGraphEdgeResponse(BaseModel):
    """Visual map edge."""

    origen: str
    destino: str
    estado: str
    label: str

    model_config = {"from_attributes": True}


class DashboardResponse(BaseModel):
    """Aggregated dashboard response."""

    referencia_id: uuid.UUID
    estado_global: str
    resumen: str
    modules: list[DashboardModuleResponse]
    metricas: DashboardMetricsResponse
    graph_nodes: list[DashboardGraphNodeResponse]
    graph_edges: list[DashboardGraphEdgeResponse]

    model_config = {"from_attributes": True}


class DashboardProgramFlowResponse(BaseModel):
    """Open program flow listed in the master dashboard."""

    referencia_id: uuid.UUID
    estado: str
    paso_actual: str
    ultima_edicion: datetime
    titulo: str
    codigo_programa: str | None
    nombre_programa: str | None
    href: str

    model_config = {"from_attributes": True}
