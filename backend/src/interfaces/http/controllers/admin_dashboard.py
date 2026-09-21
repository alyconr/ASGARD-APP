"""Hierarchical Administrative Dashboard controller for institutional supervision."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.admin_dashboard import AdminDashboardFilterDTO
from src.application.services.admin_dashboard import AdminDashboardQueryService
from src.domain.shared.enums import RolUsuario
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.session import get_async_session
from src.interfaces.http.deps import require_roles
from src.interfaces.http.schemas.admin_dashboard import (
    AdminDashboardResumenSchema,
    AdminProcesoItemSchema,
    PaginatedAdminProcesosSchema,
)

router = APIRouter(prefix="/api/v1/admin/dashboard", tags=["admin-dashboard"])


@router.get(
    "/resumen",
    response_model=AdminDashboardResumenSchema,
    status_code=status.HTTP_200_OK,
)
async def get_dashboard_resumen(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[
        Usuario,
        Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value)),
    ],
    coordinacion_id: uuid.UUID | None = Query(None),
    especialidad_id: uuid.UUID | None = Query(None),
    programa_id: uuid.UUID | None = Query(None),
    proyecto_id: uuid.UUID | None = Query(None),
    equipo_ejecutor_id: uuid.UUID | None = Query(None),
    lider_id: uuid.UUID | None = Query(None),
    estado_scope: str | None = Query(None),
    estado_programa: str | None = Query(None),
    estado_proyecto: str | None = Query(None),
    estado_planeacion: str | None = Query(None),
    search: str | None = Query(None),
    solo_sin_asignar: bool = Query(False),
) -> AdminDashboardResumenSchema:
    """Return reactive macro-aggregations for the administrative supervision dashboard."""
    filters = AdminDashboardFilterDTO(
        coordinacion_id=coordinacion_id,
        especialidad_id=especialidad_id,
        programa_id=programa_id,
        proyecto_id=proyecto_id,
        equipo_ejecutor_id=equipo_ejecutor_id,
        lider_id=lider_id,
        estado_scope=estado_scope,
        estado_programa=estado_programa,
        estado_proyecto=estado_proyecto,
        estado_planeacion=estado_planeacion,
        search=search,
        solo_sin_asignar=solo_sin_asignar,
    )
    service = AdminDashboardQueryService(session)
    resumen_dto = await service.get_resumen(actor=current_user, filters=filters)
    return AdminDashboardResumenSchema.model_validate(resumen_dto)


@router.get(
    "/procesos",
    response_model=PaginatedAdminProcesosSchema,
    status_code=status.HTTP_200_OK,
)
async def list_dashboard_procesos(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[
        Usuario,
        Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value)),
    ],
    coordinacion_id: uuid.UUID | None = Query(None),
    especialidad_id: uuid.UUID | None = Query(None),
    programa_id: uuid.UUID | None = Query(None),
    proyecto_id: uuid.UUID | None = Query(None),
    equipo_ejecutor_id: uuid.UUID | None = Query(None),
    lider_id: uuid.UUID | None = Query(None),
    estado_scope: str | None = Query(None),
    estado_programa: str | None = Query(None),
    estado_proyecto: str | None = Query(None),
    estado_planeacion: str | None = Query(None),
    search: str | None = Query(None),
    solo_sin_asignar: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedAdminProcesosSchema:
    """List curricular processes with institutional hierarchy, metrics, and pagination."""
    filters = AdminDashboardFilterDTO(
        coordinacion_id=coordinacion_id,
        especialidad_id=especialidad_id,
        programa_id=programa_id,
        proyecto_id=proyecto_id,
        equipo_ejecutor_id=equipo_ejecutor_id,
        lider_id=lider_id,
        estado_scope=estado_scope,
        estado_programa=estado_programa,
        estado_proyecto=estado_proyecto,
        estado_planeacion=estado_planeacion,
        search=search,
        solo_sin_asignar=solo_sin_asignar,
    )
    service = AdminDashboardQueryService(session)
    paginated_dto = await service.list_procesos_paginated(
        actor=current_user,
        filters=filters,
        page=page,
        page_size=page_size,
    )
    return PaginatedAdminProcesosSchema.model_validate(paginated_dto)


@router.get(
    "/procesos/{referencia_id}",
    response_model=AdminProcesoItemSchema,
    status_code=status.HTTP_200_OK,
)
async def get_dashboard_proceso_detail(
    referencia_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[
        Usuario,
        Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value)),
    ],
) -> AdminProcesoItemSchema:
    """Return single process detail with hierarchical context and aggregated plannings."""
    service = AdminDashboardQueryService(session)
    item_dto = await service.get_proceso_detail(actor=current_user, referencia_id=referencia_id)
    if not item_dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proceso con referencia_id '{referencia_id}' no encontrado",
        )
    return AdminProcesoItemSchema.model_validate(item_dto)
