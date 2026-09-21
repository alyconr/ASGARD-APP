"""Pydantic schemas for the hierarchical administrative dashboard."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CoordinacionSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    codigo: str
    nombre: str


class EspecialidadSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    codigo: str
    nombre: str


class ProgramaSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    codigo: str
    nombre: str
    estado: str


class ProyectoSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    codigo: str | None = None
    nombre: str
    estado: str


class EquipoSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre: str
    estado: str


class LiderSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre: str
    apellido: str
    email: str


class PlaneacionesCountSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int
    borrador: int
    completas: int


class AdminProcesoItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    referencia_id: str
    tipo_necesidad: str
    estado_scope: str
    coordinacion: CoordinacionSummarySchema | None = None
    especialidad: EspecialidadSummarySchema | None = None
    programa: ProgramaSummarySchema | None = None
    proyecto: ProyectoSummarySchema | None = None
    equipo: EquipoSummarySchema | None = None
    lider: LiderSummarySchema | None = None
    planeaciones: PlaneacionesCountSchema
    fecha_actualizacion: str


class PaginatedAdminProcesosSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[AdminProcesoItemSchema]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminDashboardResumenSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
