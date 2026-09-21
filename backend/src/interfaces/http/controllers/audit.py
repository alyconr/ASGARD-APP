"""Institutional Audit Viewer controller (strictly read-only)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.audit_admin import AuditFilterDTO
from src.application.services.audit_admin import AuditQueryService
from src.domain.shared.enums import RolUsuario
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.session import get_async_session
from src.interfaces.http.deps import require_roles
from src.interfaces.http.schemas.audit import (
    AuditItemSchema,
    AuditPaginatedResponseSchema,
)

router = APIRouter(prefix="/api/v1/admin/audit", tags=["admin-audit"])


@router.get(
    "",
    response_model=AuditPaginatedResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def list_audit_events(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[
        Usuario,
        Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value)),
    ],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    fecha_desde: datetime | None = Query(None),
    fecha_hasta: datetime | None = Query(None),
    actor_usuario_id: uuid.UUID | None = Query(None),
    accion: str | None = Query(None),
    entidad: str | None = Query(None),
    referencia_id: uuid.UUID | None = Query(None),
    search: str | None = Query(None),
) -> AuditPaginatedResponseSchema:
    """Return paginated, sanitized institutional audit records in descending date order."""
    filters = AuditFilterDTO(
        page=page,
        page_size=page_size,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        actor_usuario_id=actor_usuario_id,
        accion=accion,
        entidad=entidad,
        referencia_id=referencia_id,
        search=search,
    )
    service = AuditQueryService(session)
    result_dto = await service.list_events_paginated(filters=filters)
    return AuditPaginatedResponseSchema.model_validate(result_dto)


@router.get(
    "/{event_id}",
    response_model=AuditItemSchema,
    status_code=status.HTTP_200_OK,
)
async def get_audit_event_detail(
    event_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[
        Usuario,
        Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value)),
    ],
) -> AuditItemSchema:
    """Fetch single audit event by ID with redacted sensitive payload."""
    service = AuditQueryService(session)
    event_dto = await service.get_event_by_id(event_id)
    if not event_dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evento de auditoría con ID '{event_id}' no encontrado",
        )
    return AuditItemSchema.model_validate(event_dto)
