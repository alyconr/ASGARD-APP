"""DTOs for the master dashboard module."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class DashboardModuleDTO:
    """Access state for a main wizard module."""

    id: str
    titulo: str
    estado: str
    disponible: bool
    href: str
    motivo_bloqueo: str | None
    accion_requerida: str
    descripcion: str
    avance_porcentaje: int


@dataclass(frozen=True)
class ProgramaDashboardMetricsDTO:
    """Program progress counters."""

    estado: str
    competencias: int
    resultados: int
    conocimientos: int
    criterios: int


@dataclass(frozen=True)
class ProyectoDashboardMetricsDTO:
    """Project progress counters."""

    estado: str
    fases: int
    actividades: int
    fuente_estructurada_cargada: bool


@dataclass(frozen=True)
class PlaneacionDashboardMetricsDTO:
    """Pedagogical planning progress counters."""

    estado: str
    total: int
    borrador: int
    completas: int
    competencias_con_planeacion: int
    competencias_sin_planear: int


@dataclass(frozen=True)
class DashboardGraphNodeDTO:
    """Navigable node used by the dashboard visual map."""

    id: str
    label: str
    tipo: str
    estado: str
    href: str
    disponible: bool
    detalle: str


@dataclass(frozen=True)
class DashboardGraphEdgeDTO:
    """Relationship between two dashboard map nodes."""

    origen: str
    destino: str
    estado: str
    label: str


@dataclass(frozen=True)
class DashboardMetricsDTO:
    """Dashboard metric bundle."""

    programa: ProgramaDashboardMetricsDTO
    proyecto: ProyectoDashboardMetricsDTO
    planeacion: PlaneacionDashboardMetricsDTO


@dataclass(frozen=True)
class DashboardProgramFlowDTO:
    """Open program flow visible from the master dashboard."""

    referencia_id: uuid.UUID
    estado: str
    paso_actual: str
    ultima_edicion: datetime
    titulo: str
    codigo_programa: str | None
    nombre_programa: str | None
    href: str


@dataclass(frozen=True)
class DashboardDTO:
    """Aggregated master dashboard payload."""

    referencia_id: uuid.UUID
    estado_global: str
    resumen: str
    modules: list[DashboardModuleDTO]
    metricas: DashboardMetricsDTO
    graph_nodes: list[DashboardGraphNodeDTO] = field(default_factory=list)
    graph_edges: list[DashboardGraphEdgeDTO] = field(default_factory=list)
