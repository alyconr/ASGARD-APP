"""Organization, Executing Teams, and Process Assignment controller."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.shared.enums import EstadoEquipo, EstadoScopeProceso, RolUsuario
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.models.organizacion import (
    Coordinacion,
    EquipoEjecutor,
    EquipoEjecutorMiembro,
    Especialidad,
    ProcesoCurricular,
)
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.interfaces.http.controllers.auth import _map_user_response
from src.interfaces.http.deps import get_current_user, require_roles
from src.interfaces.http.schemas.organizacion import (
    CoordinacionResponse,
    EquipoEjecutorCreate,
    EquipoEjecutorResponse,
    EspecialidadResponse,
    MiembroCreate,
    MiembroResponse,
    MiembroUpdate,
    ProcesoAsignarRequest,
    ProcesoCurricularResponse,
)

router = APIRouter(prefix="/api/v1", tags=["organizacion"])


@router.get("/coordinaciones", response_model=list[CoordinacionResponse])
async def list_coordinaciones(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> list[CoordinacionResponse]:
    """Return all active academic coordinations."""
    stmt = select(Coordinacion).where(Coordinacion.activo.is_(True)).order_by(Coordinacion.nombre)
    res = await session.execute(stmt)
    return [CoordinacionResponse.model_validate(c) for c in res.scalars().all()]


@router.get("/coordinaciones/{coordinacion_id}/especialidades", response_model=list[EspecialidadResponse])
async def list_especialidades_by_coordinacion(
    coordinacion_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> list[EspecialidadResponse]:
    """Return all active specialties under a coordination."""
    stmt = (
        select(Especialidad)
        .where(
            Especialidad.coordinacion_id == coordinacion_id,
            Especialidad.activo.is_(True),
        )
        .order_by(Especialidad.nombre)
    )
    res = await session.execute(stmt)
    return [EspecialidadResponse.model_validate(e) for e in res.scalars().all()]


def _map_equipo_response(equipo: EquipoEjecutor) -> EquipoEjecutorResponse:
    miembros_dtos = [
        MiembroResponse(
            id=m.id,
            equipo_id=m.equipo_id,
            usuario_id=m.usuario_id,
            activo=m.activo,
            fecha_asignacion=m.fecha_asignacion,
            usuario=_map_user_response(m.usuario) if m.usuario else None,
        )
        for m in equipo.miembros
    ]
    return EquipoEjecutorResponse(
        id=equipo.id,
        nombre=equipo.nombre,
        coordinacion_id=equipo.coordinacion_id,
        especialidad_id=equipo.especialidad_id,
        lider_id=equipo.lider_id,
        estado=equipo.estado.value,
        lider=_map_user_response(equipo.lider) if equipo.lider else None,
        miembros=miembros_dtos,
    )


@router.get("/equipos", response_model=list[EquipoEjecutorResponse])
async def list_equipos(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    coordinacion_id: uuid.UUID | None = Query(None),
    especialidad_id: uuid.UUID | None = Query(None),
) -> list[EquipoEjecutorResponse]:
    """List executing teams according to user role and filters."""
    stmt = (
        select(EquipoEjecutor)
        .options(
            selectinload(EquipoEjecutor.lider).selectinload(Usuario.roles),
            selectinload(EquipoEjecutor.miembros).selectinload(EquipoEjecutorMiembro.usuario).selectinload(Usuario.roles),
        )
        .order_by(EquipoEjecutor.nombre)
    )

    if current_user.has_role(RolUsuario.LIDER_EQUIPO_EJECUTOR.value):
        stmt = stmt.where(EquipoEjecutor.lider_id == current_user.id)
    elif current_user.has_role(RolUsuario.USUARIO_ADICIONAL.value):
        stmt = stmt.join(EquipoEjecutorMiembro).where(
            EquipoEjecutorMiembro.usuario_id == current_user.id,
            EquipoEjecutorMiembro.activo.is_(True),
        )
    else:
        if coordinacion_id:
            stmt = stmt.where(EquipoEjecutor.coordinacion_id == coordinacion_id)
        if especialidad_id:
            stmt = stmt.where(EquipoEjecutor.especialidad_id == especialidad_id)

    res = await session.execute(stmt)
    return [_map_equipo_response(e) for e in res.scalars().unique().all()]


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
    """Create a new executing team enforcing leader and specialty integrity."""
    lider = await session.get(
        Usuario,
        payload.lider_id,
        options=[selectinload(Usuario.roles)],
    )
    if lider is None or not lider.activo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El líder especificado no existe o está inactivo",
        )

    # Invariant: Líder debe pertenecer a la misma coordinación y especialidad
    if lider.coordinacion_id != payload.coordinacion_id or lider.especialidad_id != payload.especialidad_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La coordinación y especialidad del equipo deben coincidir exactamente con las del líder",
        )

    # Verify specialty belongs to coordination
    esp = await session.get(Especialidad, payload.especialidad_id)
    if esp is None or esp.coordinacion_id != payload.coordinacion_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La especialidad no pertenece a la coordinación especificada",
        )

    equipo = EquipoEjecutor(
        nombre=payload.nombre.strip(),
        coordinacion_id=payload.coordinacion_id,
        especialidad_id=payload.especialidad_id,
        lider_id=payload.lider_id,
        estado=EstadoEquipo.ACTIVO,
    )
    session.add(equipo)
    await session.flush()

    audit_repo = AuditRepository(session)
    await audit_repo.add_event(
        entidad="EquipoEjecutor",
        entidad_id=equipo.id,
        accion="TEAM_CREATED",
        detalle={"creado_por": str(current_user.id), "nombre": equipo.nombre, "lider_id": str(equipo.lider_id)},
    )
    await session.commit()

    reloaded = await session.get(
        EquipoEjecutor,
        equipo.id,
        options=[
            selectinload(EquipoEjecutor.lider).selectinload(Usuario.roles),
            selectinload(EquipoEjecutor.miembros).selectinload(EquipoEjecutorMiembro.usuario).selectinload(Usuario.roles),
        ],
    )
    return _map_equipo_response(reloaded)  # type: ignore


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
    equipo = await session.get(EquipoEjecutor, equipo_id)
    if equipo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipo no encontrado")

    usuario = await session.get(Usuario, payload.usuario_id, options=[selectinload(Usuario.roles)])
    if usuario is None or not usuario.activo:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Usuario no válido o inactivo")

    # Invariant: Usuario de apoyo debe pertenecer a la misma coordinación y especialidad
    if usuario.coordinacion_id != equipo.coordinacion_id or usuario.especialidad_id != equipo.especialidad_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El usuario de apoyo debe pertenecer a la misma coordinación y especialidad del equipo ejecutor",
        )

    audit_repo = AuditRepository(session)
    stmt = select(EquipoEjecutorMiembro).where(
        EquipoEjecutorMiembro.equipo_id == equipo_id,
        EquipoEjecutorMiembro.usuario_id == payload.usuario_id,
    )
    res = await session.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing:
        existing.activo = True
        await audit_repo.add_event(
            entidad="EquipoEjecutorMiembro",
            entidad_id=existing.id,
            accion="TEAM_MEMBER_ADDED",
            detalle={"equipo_id": str(equipo_id), "usuario_id": str(payload.usuario_id), "reactivado": True},
        )
        await session.commit()
        await session.refresh(existing)
        return MiembroResponse(
            id=existing.id,
            equipo_id=existing.equipo_id,
            usuario_id=existing.usuario_id,
            activo=existing.activo,
            fecha_asignacion=existing.fecha_asignacion,
            usuario=_map_user_response(usuario),
        )

    miembro = EquipoEjecutorMiembro(
        equipo_id=equipo_id,
        usuario_id=payload.usuario_id,
        activo=True,
        asignado_por=current_user.id,
    )
    session.add(miembro)
    await session.flush()

    await audit_repo.add_event(
        entidad="EquipoEjecutorMiembro",
        entidad_id=miembro.id,
        accion="TEAM_MEMBER_ADDED",
        detalle={"equipo_id": str(equipo_id), "usuario_id": str(payload.usuario_id)},
    )
    await session.commit()
    await session.refresh(miembro)

    return MiembroResponse(
        id=miembro.id,
        equipo_id=miembro.equipo_id,
        usuario_id=miembro.usuario_id,
        activo=miembro.activo,
        fecha_asignacion=miembro.fecha_asignacion,
        usuario=_map_user_response(usuario),
    )


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
) -> MiembroResponse:
    """Activate or deactivate an additional user's team membership."""
    stmt = (
        select(EquipoEjecutorMiembro)
        .where(
            EquipoEjecutorMiembro.equipo_id == equipo_id,
            EquipoEjecutorMiembro.usuario_id == usuario_id,
        )
        .options(selectinload(EquipoEjecutorMiembro.usuario).selectinload(Usuario.roles))
    )
    res = await session.execute(stmt)
    miembro = res.scalar_one_or_none()
    if miembro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membresía no encontrada")

    miembro.activo = payload.activo
    audit_repo = AuditRepository(session)
    await audit_repo.add_event(
        entidad="EquipoEjecutorMiembro",
        entidad_id=miembro.id,
        accion="TEAM_MEMBER_DISABLED" if not payload.activo else "TEAM_MEMBER_ENABLED",
        detalle={"equipo_id": str(equipo_id), "usuario_id": str(usuario_id), "activo": payload.activo},
    )
    await session.commit()
    await session.refresh(miembro)
    return MiembroResponse(
        id=miembro.id,
        equipo_id=miembro.equipo_id,
        usuario_id=miembro.usuario_id,
        activo=miembro.activo,
        fecha_asignacion=miembro.fecha_asignacion,
        usuario=_map_user_response(miembro.usuario) if miembro.usuario else None,
    )


@router.post(
    "/procesos/{referencia_id}/asignar",
    response_model=ProcesoCurricularResponse,
    dependencies=[Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value))],
)
async def asignar_proceso(
    referencia_id: uuid.UUID,
    payload: ProcesoAsignarRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ProcesoCurricularResponse:
    """Assign or reassign a curricular process to an executing team and leader."""
    equipo = await session.get(EquipoEjecutor, payload.equipo_ejecutor_id)
    if equipo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipo no encontrado")

    lider_id = payload.lider_id or equipo.lider_id

    stmt = select(ProcesoCurricular).where(ProcesoCurricular.referencia_id == referencia_id)
    res = await session.execute(stmt)
    proceso = res.scalar_one_or_none()

    audit_repo = AuditRepository(session)
    accion = "PROCESS_REASSIGNED" if proceso and proceso.equipo_ejecutor_id else "PROCESS_ASSIGNED"

    if proceso is None:
        proceso = ProcesoCurricular(
            referencia_id=referencia_id,
            coordinacion_id=equipo.coordinacion_id,
            especialidad_id=equipo.especialidad_id,
            equipo_ejecutor_id=equipo.id,
            lider_id=lider_id,
            estado_scope=EstadoScopeProceso.ASIGNADO,
        )
        session.add(proceso)
    else:
        proceso.coordinacion_id = equipo.coordinacion_id
        proceso.especialidad_id = equipo.especialidad_id
        proceso.equipo_ejecutor_id = equipo.id
        proceso.lider_id = lider_id
        proceso.estado_scope = EstadoScopeProceso.ASIGNADO

    await session.flush()
    await audit_repo.add_event(
        entidad="ProcesoCurricular",
        entidad_id=proceso.id,
        accion=accion,
        detalle={"referencia_id": str(referencia_id), "equipo_id": str(equipo.id), "lider_id": str(lider_id)},
    )
    await session.commit()
    await session.refresh(proceso)
    return ProcesoCurricularResponse.model_validate(proceso)


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
        .order_by(ProcesoCurricular.fecha_creacion.desc())
    )
    res = await session.execute(stmt)
    return [ProcesoCurricularResponse.model_validate(p) for p in res.scalars().all()]
