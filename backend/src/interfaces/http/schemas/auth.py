"""Pydantic schemas for authentication and user management."""

from __future__ import annotations

import uuid
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


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    nombre: str
    apellido: str
    telefono: str | None = None
    activo: bool
    roles: list[str] = []
    coordinacion: CoordinacionSimpleResponse | None = None
    especialidad: EspecialidadSimpleResponse | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_new_password: str


class UserCreateRequest(BaseModel):
    email: str
    password: str
    nombre: str
    apellido: str
    telefono: str | None = None
    coordinacion_id: uuid.UUID | None = None
    especialidad_id: uuid.UUID | None = None
    roles: list[str] = []
