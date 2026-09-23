"""Pydantic schemas for authentication and user management."""

from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class CoordinacionSimpleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    codigo: str
    nombre: str


class EspecialidadSimpleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    codigo: str
    nombre: str


class ProgramaSimpleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    codigo_programa: str
    nombre_programa: str
    version_programa: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    nombre: str
    apellido: str
    telefono: str | None = None
    area: str | None = None
    estado: str = "ACTIVO"
    activo: bool = True
    debe_cambiar_password: bool = False
    ultimo_acceso: datetime | None = None
    roles: list[str] = []
    coordinacion: CoordinacionSimpleResponse | None = None
    especialidad: EspecialidadSimpleResponse | None = None
    programas_autorizados: list[ProgramaSimpleResponse] = []


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_new_password: str


class UserCreateRequest(BaseModel):
    email: str
    password: str
    password_confirmation: str
    nombre: str
    apellido: str
    telefono: str | None = None
    area: str | None = None
    coordinacion_id: uuid.UUID | None = None
    especialidad_id: uuid.UUID | None = None
    roles: list[str] = []
    programas_ids: list[uuid.UUID] = []


class UserUpdateRequest(BaseModel):
    nombre: str | None = None
    apellido: str | None = None
    telefono: str | None = None
    area: str | None = None
    coordinacion_id: uuid.UUID | None = None
    especialidad_id: uuid.UUID | None = None
    roles: list[str] | None = None
    programas_ids: list[uuid.UUID] | None = None


class UserStatusUpdateRequest(BaseModel):
    estado: str


class UserResetPasswordRequest(BaseModel):
    temporary_password: str
    confirm_temporary_password: str


class PaginatedUsersResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[UserResponse]
    page: int
    page_size: int
    total: int
    pages: int
