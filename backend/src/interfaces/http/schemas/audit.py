"""Pydantic schemas for institutional audit viewer."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class ActorSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    apellido: str
    email: str
    rol: str


class AuditItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fecha_evento: datetime
    accion: str
    entidad: str
    entidad_id: uuid.UUID
    actor: ActorSummarySchema | None = None
    referencia_id: uuid.UUID | None = None
    detalle: dict[str, Any] | None = None


class AuditPaginatedResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[AuditItemSchema]
    total: int
    page: int
    page_size: int
    total_pages: int
