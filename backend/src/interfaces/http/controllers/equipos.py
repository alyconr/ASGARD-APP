"""Organization, Executing Teams, and Process Assignment controller."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.services.organization_admin import OrganizationAdminService
from src.application.services.team_admin import TeamAdminService, _map_proceso_dto
from src.domain.shared.enums import EstadoScopeProceso, RolUsuario
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.models.organizacion import ProcesoCurricular
from src.infrastructure.db.session import get_async_session
from src.interfaces.http.deps import get_current_user, require_roles
from src.interfaces.http.schemas.organizacion import (
    CoordinacionCreate,
    CoordinacionResponse,
    CoordinacionUpdate,
    EquipoEjecutorCreate,
    EquipoEjecutorResponse,
    EquipoEjecutorUpdate,
    EspecialidadCreate,
    EspecialidadResponse,
    EspecialidadUpdate,
    MiembroCreate,
    MiembroResponse,
    MiembroUpdate,
    PaginatedEquiposResponse,
    ProcesoAsignarRequest,
    ProcesoCurricularResponse,
)

router = APIRouter(prefix="/api/v1", tags=["organizacion"])


# ==========================================
# COORDINACIONES
# ==========================================


@router.get("/coordinaciones", response_model=list[CoordinacionResponse])
async def list_coordinaciones(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    solo_activas: bool = Query(False),
) -> list[CoordinacionResponse]:
    """Return academic coordinations with optional active-only filter."""
    service = OrganizationAdminService(session)
    return await service.list_coordinaciones(solo_activas=solo_activas)


@router.get("/coordinaciones/{coordinacion_id}", response_model=CoordinacionResponse)
async def get_coordinacion(
    coordinacion_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> CoordinacionResponse:
    """Return single coordination detail."""
    service = OrganizationAdminService(session)
    return await service.get_coordinacion(coordinacion_id)


@router.post(
    "/coordinaciones",
    response_model=CoordinacionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value))],
)
async def create_coordinacion(
    payload: CoordinacionCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> CoordinacionResponse:
    """Create a new coordination with unique code."""
    service = OrganizationAdminService(session)
    return await service.create_coordinacion(current_user, payload)


@router.patch(
    "/coordinaciones/{coordinacion_id}",
    response_model=CoordinacionResponse,
    dependencies=[Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value))],
)
async def update_coordinacion(
    coordinacion_id: uuid.UUID,
    payload: CoordinacionUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> CoordinacionResponse:
    """Update coordination details or status with dependency validation."""
    service = OrganizationAdminService(session)
    return await service.update_coordinacion(current_user, coordinacion_id, payload)


@router.delete(
    "/coordinaciones/{coordinacion_id}",
    dependencies=[Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value))],
)
async def delete_coordinacion(
    coordinacion_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict[str, str]:
    """Permanently delete coordination if it has no dependencies (SUPERADMIN/ADMIN only)."""
    service = OrganizationAdminService(session)
    return await service.delete_coordinacion(current_user, coordinacion_id)


# ==========================================
# ESPECIALIDADES
# ==========================================


@router.get("/coordinaciones/{coordinacion_id}/especialidades", response_model=list[EspecialidadResponse])
async def list_especialidades_by_coordinacion(
    coordinacion_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    solo_activas: bool = Query(False),
) -> list[EspecialidadResponse]:
    """Return specialties under a coordination."""
    service = OrganizationAdminService(session)
    return await service.list_especialidades_by_coordinacion(coordinacion_id, solo_activas=solo_activas)


@router.get("/especialidades/{especialidad_id}", response_model=EspecialidadResponse)
async def get_especialidad(
    especialidad_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> EspecialidadResponse:
    """Return single specialty detail."""
    service = OrganizationAdminService(session)
    return await service.get_especialidad(especialidad_id)


@router.post(
    "/coordinaciones/{coordinacion_id}/especialidades",
    response_model=EspecialidadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            require_roles(
                RolUsuario.SUPERADMIN.value,
                RolUsuario.ADMIN.value,
                RolUsuario.LIDER_EQUIPO_EJECUTOR.value,
            )
        )
    ],
)
async def create_especialidad(
    coordinacion_id: uuid.UUID,
    payload: EspecialidadCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> EspecialidadResponse:
    """Create a new specialty under an active coordination (SUPERADMIN, ADMIN or LIDER)."""
    service = OrganizationAdminService(session)
    return await service.create_especialidad(current_user, coordinacion_id, payload)


@router.patch(
    "/especialidades/{especialidad_id}",
    response_model=EspecialidadResponse,
    dependencies=[Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value))],
)
async def update_especialidad(
    especialidad_id: uuid.UUID,
    payload: EspecialidadUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> EspecialidadResponse:
    """Update specialty details or status enforcing dependency checks."""
    service = OrganizationAdminService(session)
    return await service.update_especialidad(current_user, especialidad_id, payload)


@router.delete(
    "/especialidades/{especialidad_id}",
    dependencies=[
        Depends(
            require_roles(
                RolUsuario.SUPERADMIN.value,
                RolUsuario.ADMIN.value,
                RolUsuario.LIDER_EQUIPO_EJECUTOR.value,
            )
        )
    ],
)
async def delete_especialidad(
    especialidad_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict[str, str]:
    """Permanently delete specialty if it has no dependencies. Leaders can only delete their own specialties."""
    service = OrganizationAdminService(session)
    return await service.delete_especialidad(current_user, especialidad_id)


# ==========================================
# EQUIPOS EJECUTORES
# ==========================================


@router.get("/equipos", response_model=PaginatedEquiposResponse)
async def list_equipos(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    estado: str | None = Query(None),
    coordinacion_id: uuid.UUID | None = Query(None),
    especialidad_id: uuid.UUID | None = Query(None),
    lider_id: uuid.UUID | None = Query(None),
) -> PaginatedEquiposResponse:
    """List executing teams paginated server-side with role scoping."""
    service = TeamAdminService(session)
    return await service.list_teams_paginated(
        actor=current_user,
        page=page,
        page_size=page_size,
        search=search,
        estado=estado,
        coordinacion_id=coordinacion_id,
        especialidad_id=especialidad_id,
        lider_id=lider_id,
    )


@router.get("/equipos/{equipo_id}", response_model=EquipoEjecutorResponse)
async def get_equipo(
    equipo_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> EquipoEjecutorResponse:
    """Return executing team details."""
    service = TeamAdminService(session)
    return await service.get_team(equipo_id)


@router.post(
    "/equipos",
    response_model=EquipoEjecutorResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value))],
)
async def create_equipo(
    payload: EquipoEjecutorCreate,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EquipoEjecutorResponse:
    """Create a new executing team enforcing leader role, status, and coordination/specialty integrity."""
    service = TeamAdminService(session)
    return await service.create_team(current_user, payload)


@router.patch(
    "/equipos/{equipo_id}",
    response_model=EquipoEjecutorResponse,
    dependencies=[Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value))],
)
async def update_equipo(
    equipo_id: uuid.UUID,
    payload: EquipoEjecutorUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> EquipoEjecutorResponse:
    """Update team details, including leader change with transactional propagation to assigned processes."""
    service = TeamAdminService(session)
    return await service.update_team(current_user, equipo_id, payload)


@router.delete(
    "/equipos/{equipo_id}",
    dependencies=[Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value))],
)
async def delete_equipo(
    equipo_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    desasignar_procesos: bool = Query(False),
) -> dict[str, str]:
    """Permanently delete executing team, optionally unassigning linked curricular processes."""
    service = TeamAdminService(session)
    return await service.delete_team(current_user, equipo_id, desasignar_procesos=desasignar_procesos)


@router.post(
    "/equipos/{equipo_id}/miembros",
    response_model=MiembroResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value))],
)
async def add_miembro_equipo(
    equipo_id: uuid.UUID,
    payload: MiembroCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> MiembroResponse:
    """Attach an additional user to an executing team, validating organizational consistency."""
    service = TeamAdminService(session)
    return await service.add_member(current_user, equipo_id, payload)


@router.patch(
    "/equipos/{equipo_id}/miembros/{usuario_id}",
    response_model=MiembroResponse,
    dependencies=[Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value))],
)
async def update_miembro_status(
    equipo_id: uuid.UUID,
    usuario_id: uuid.UUID,
    payload: MiembroUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> MiembroResponse:
    """Activate or deactivate an additional user's team membership."""
    service = TeamAdminService(session)
    return await service.update_member_status(current_user, equipo_id, usuario_id, payload)


# ==========================================
# PROCESOS CURRICULARES
# ==========================================


@router.post(
    "/procesos/{referencia_id}/asignar",
    response_model=ProcesoCurricularResponse,
    dependencies=[Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value))],
)
async def asignar_proceso(
    referencia_id: uuid.UUID,
    payload: ProcesoAsignarRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> ProcesoCurricularResponse:
    """Assign or reassign a curricular process to an executing team and leader."""
    service = TeamAdminService(session)
    return await service.assign_process(current_user, referencia_id, payload)


@router.post(
    "/procesos/{referencia_id}/desasignar",
    response_model=ProcesoCurricularResponse,
    dependencies=[Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value))],
)
async def desasignar_proceso(
    referencia_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> ProcesoCurricularResponse:
    """Unassign a curricular process from its team and leader, returning it to SIN_ASIGNAR."""
    service = TeamAdminService(session)
    return await service.unassign_process(current_user, referencia_id)


@router.delete(
    "/procesos/{referencia_id}",
    dependencies=[Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value))],
)
async def delete_proceso(
    referencia_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict[str, str]:
    """Permanently delete a curricular process and clean up its drafts and artifacts."""
    service = TeamAdminService(session)
    return await service.delete_process(current_user, referencia_id)


@router.get(
    "/procesos/sin-asignar",
    response_model=list[ProcesoCurricularResponse],
    dependencies=[Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value))],
)
async def list_procesos_sin_asignar(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[ProcesoCurricularResponse]:
    """List all curricular processes pending assignment."""
    stmt = (
        select(ProcesoCurricular)
        .where(ProcesoCurricular.estado_scope == EstadoScopeProceso.SIN_ASIGNAR)
        .options(
            selectinload(ProcesoCurricular.programa),
            selectinload(ProcesoCurricular.proyecto),
        )
        .order_by(ProcesoCurricular.fecha_creacion.desc())
    )
    res = await session.execute(stmt)
    dtos = [_map_proceso_dto(p) for p in res.scalars().all()]
    return [d for d in dtos if d is not None]
