"""Pydantic schemas for organizations, executing teams, and process assignments."""

from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from src.interfaces.http.schemas.auth import ProgramaSimpleResponse, UserResponse


class CoordinacionCreate(BaseModel):
    codigo: str
    nombre: str
    descripcion: str | None = None


class CoordinacionUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    activo: bool | None = None


class CoordinacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    codigo: str
    nombre: str
    descripcion: str | None = None
    activo: bool


class EspecialidadCreate(BaseModel):
    codigo: str
    nombre: str


class EspecialidadUpdate(BaseModel):
    nombre: str | None = None
    activo: bool | None = None


class EspecialidadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    coordinacion_id: uuid.UUID
    codigo: str
    nombre: str
    activo: bool
    creado_por_id: uuid.UUID | None = None


class MiembroResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    equipo_id: uuid.UUID
    usuario_id: uuid.UUID
    rol_equipo: str = "INSTRUCTOR"
    activo: bool
    fecha_asignacion: datetime
    usuario: UserResponse | None = None


class MiembroCreate(BaseModel):
    usuario_id: uuid.UUID
    rol_equipo: str = "INSTRUCTOR"


class MiembroUpdate(BaseModel):
    activo: bool | None = None
    rol_equipo: str | None = None


class EquipoEjecutorCreate(BaseModel):
    nombre: str
    coordinacion_id: uuid.UUID
    especialidad_id: uuid.UUID
    lider_id: uuid.UUID
    programa_id: uuid.UUID | None = None
    max_members: int = 5
    leaders_can_manage_members: bool = True
    descripcion: str | None = None


class EquipoEjecutorUpdate(BaseModel):
    nombre: str | None = None
    coordinacion_id: uuid.UUID | None = None
    especialidad_id: uuid.UUID | None = None
    lider_id: uuid.UUID | None = None
    programa_id: uuid.UUID | None = None
    max_members: int | None = None
    leaders_can_manage_members: bool | None = None
    descripcion: str | None = None
    estado: str | None = None


class EquipoEjecutorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    coordinacion_id: uuid.UUID
    especialidad_id: uuid.UUID
    lider_id: uuid.UUID
    programa_id: uuid.UUID | None = None
    programa: ProgramaSimpleResponse | None = None
    max_members: int = 5
    leaders_can_manage_members: bool = True
    descripcion: str | None = None
    estado: str
    lider: UserResponse | None = None
    miembros: list[MiembroResponse] = []


class PaginatedEquiposResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[EquipoEjecutorResponse]
    page: int
    page_size: int
    total: int
    pages: int


class ProcesoAsignarRequest(BaseModel):
    equipo_ejecutor_id: uuid.UUID
    lider_id: uuid.UUID | None = None


class ProcesoCurricularResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    referencia_id: uuid.UUID
    coordinacion_id: uuid.UUID | None = None
    especialidad_id: uuid.UUID | None = None
    equipo_ejecutor_id: uuid.UUID | None = None
    lider_id: uuid.UUID | None = None
    tipo_necesidad: str
    estado_scope: str
    programa_id: uuid.UUID | None = None
    proyecto_id: uuid.UUID | None = None
