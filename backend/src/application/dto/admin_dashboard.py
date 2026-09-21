"""DTOs for institutional administrative dashboard."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class CoordinacionSummaryDTO:
    id: str
    codigo: str
    nombre: str


@dataclass(frozen=True)
class EspecialidadSummaryDTO:
    id: str
    codigo: str
    nombre: str


@dataclass(frozen=True)
class ProgramaSummaryDTO:
    id: str
    codigo: str
    nombre: str
    estado: str


@dataclass(frozen=True)
class ProyectoSummaryDTO:
    id: str
    codigo: str | None
    nombre: str
    estado: str


@dataclass(frozen=True)
class EquipoSummaryDTO:
    id: str
    nombre: str
    estado: str


@dataclass(frozen=True)
class LiderSummaryDTO:
    id: str
    nombre: str
    apellido: str
    email: str


@dataclass(frozen=True)
class PlaneacionesCountDTO:
    total: int
    borrador: int
    completas: int


@dataclass(frozen=True)
class AdminProcesoItemDTO:
    referencia_id: str
    tipo_necesidad: str
    estado_scope: str
    coordinacion: CoordinacionSummaryDTO | None
    especialidad: EspecialidadSummaryDTO | None
    programa: ProgramaSummaryDTO | None
    proyecto: ProyectoSummaryDTO | None
    equipo: EquipoSummaryDTO | None
    lider: LiderSummaryDTO | None
    planeaciones: PlaneacionesCountDTO
    fecha_actualizacion: str


@dataclass(frozen=True)
class AdminDashboardResumenDTO:
    procesos_totales: int
    procesos_asignados: int
    procesos_sin_asignar: int
    programas_borrador: int
    programas_en_revision: int
    programas_completo: int
    proyectos_bloqueado: int
    proyectos_borrador: int
    proyectos_en_revision: int
    proyectos_completo: int
    planeaciones_totales: int
    planeaciones_borrador: int
    planeaciones_completo: int
    equipos_activos: int
    equipos_inactivos: int
    lideres_activos: int
    usuarios_apoyo_activos: int


@dataclass(frozen=True)
class PaginatedAdminProcesosDTO:
    items: list[AdminProcesoItemDTO]
    total: int
    page: int
    page_size: int
    total_pages: int


@dataclass(frozen=True)
class AdminDashboardFilterDTO:
    coordinacion_id: uuid.UUID | None = None
    especialidad_id: uuid.UUID | None = None
    programa_id: uuid.UUID | None = None
    proyecto_id: uuid.UUID | None = None
    equipo_ejecutor_id: uuid.UUID | None = None
    lider_id: uuid.UUID | None = None
    referencia_id: uuid.UUID | None = None
    estado_scope: str | None = None
    estado_programa: str | None = None
    estado_proyecto: str | None = None
    estado_planeacion: str | None = None
    search: str | None = None
    solo_sin_asignar: bool = False
