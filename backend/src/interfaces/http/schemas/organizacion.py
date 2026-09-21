"""Pydantic schemas for organizations, executing teams, and process assignments."""

from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from src.interfaces.http.schemas.auth import UserResponse


class CoordinacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    codigo: str
    nombre: str
    descripcion: str | None = None
    activo: bool


class EspecialidadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    coordinacion_id: uuid.UUID
    codigo: str
    nombre: str
    activo: bool


class MiembroResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    equipo_id: uuid.UUID
    usuario_id: uuid.UUID
    activo: bool
    fecha_asignacion: datetime
    usuario: UserResponse | None = None


class MiembroCreate(BaseModel):
    usuario_id: uuid.UUID


class MiembroUpdate(BaseModel):
    activo: bool


class EquipoEjecutorCreate(BaseModel):
    nombre: str
    coordinacion_id: uuid.UUID
    especialidad_id: uuid.UUID
    lider_id: uuid.UUID


class EquipoEjecutorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    coordinacion_id: uuid.UUID
    especialidad_id: uuid.UUID
    lider_id: uuid.UUID
    estado: str
    lider: UserResponse | None = None
    miembros: list[MiembroResponse] = []


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
