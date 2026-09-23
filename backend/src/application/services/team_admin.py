"""Team and Process Scope Administration Service."""

from __future__ import annotations

from datetime import UTC, datetime
import math
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.shared.enums import (
    EstadoEquipo,
    EstadoScopeProceso,
    EstadoUsuario,
    RolEquipo,
    RolUsuario,
)
from src.infrastructure.db.models.auth import Usuario, UsuarioProgramaAutorizado
from src.infrastructure.db.models.curriculum import ProgramaFormacion
from src.infrastructure.db.models.organizacion import (
    Coordinacion,
    EquipoEjecutor,
    EquipoEjecutorMiembro,
    Especialidad,
    ProcesoCurricular,
)
from src.infrastructure.repositories.audit import AuditRepository
from src.interfaces.http.schemas.auth import ProgramaSimpleResponse, UserResponse
from src.interfaces.http.schemas.organizacion import (
    EquipoEjecutorCreate,
    EquipoEjecutorResponse,
    EquipoEjecutorUpdate,
    MiembroCreate,
    MiembroResponse,
    MiembroUpdate,
    PaginatedEquiposResponse,
    ProcesoAsignarRequest,
    ProcesoCurricularResponse,
)


def _map_user_dto(user: Usuario | None) -> UserResponse | None:
    if user is None:
        return None
    estado_val = user.estado.value if hasattr(getattr(user, "estado", None), "value") else str(getattr(user, "estado", None) or "ACTIVO")
    progs: list[ProgramaSimpleResponse] = []
    for up in getattr(user, "programas_autorizados", []) or []:
        if getattr(up, "activo", True) and getattr(up, "programa", None):
            progs.append(
                ProgramaSimpleResponse(
                    id=up.programa.id,
                    codigo_programa=up.programa.codigo_programa,
                    nombre_programa=up.programa.nombre_programa,
                    version_programa=up.programa.version_programa,
                )
            )
    return UserResponse(
        id=user.id,
        email=user.email,
        nombre=user.nombre,
        apellido=user.apellido,
        telefono=user.telefono,
        area=getattr(user, "area", None),
        estado=estado_val,
        activo=user.activo,
        debe_cambiar_password=bool(getattr(user, "debe_cambiar_password", False) or False),
        ultimo_acceso=getattr(user, "ultimo_acceso", None),
        roles=list(user.role_names),
        coordinacion=user.coordinacion,  # type: ignore
        especialidad=user.especialidad,  # type: ignore
        programas_autorizados=progs,
    )


def _map_equipo_dto(equipo: EquipoEjecutor) -> EquipoEjecutorResponse:
    miembros_dtos = [
        MiembroResponse(
            id=m.id,
            equipo_id=m.equipo_id,
            usuario_id=m.usuario_id,
            rol_equipo=m.rol_equipo.value if hasattr(m.rol_equipo, "value") else str(m.rol_equipo),
            activo=m.activo,
            fecha_asignacion=m.fecha_asignacion or datetime.now(UTC),
            usuario=_map_user_dto(m.usuario),
        )
        for m in equipo.miembros
    ]
    prog_dto = None
    if equipo.programa:
        prog_dto = ProgramaSimpleResponse(
            id=equipo.programa.id,
            codigo_programa=equipo.programa.codigo_programa,
            nombre_programa=equipo.programa.nombre_programa,
            version_programa=equipo.programa.version_programa,
        )
    return EquipoEjecutorResponse(
        id=equipo.id,
        nombre=equipo.nombre,
        coordinacion_id=equipo.coordinacion_id,
        especialidad_id=equipo.especialidad_id,
        programa_id=equipo.programa_id,
        programa=prog_dto,
        max_members=(equipo.max_members if getattr(equipo, "max_members", None) is not None else 5),
        leaders_can_manage_members=(
            equipo.leaders_can_manage_members
            if getattr(equipo, "leaders_can_manage_members", None) is not None
            else True
        ),
        descripcion=getattr(equipo, "descripcion", None),
        lider_id=equipo.lider_id,
        estado=equipo.estado.value if hasattr(equipo.estado, "value") else str(equipo.estado),
        lider=_map_user_dto(equipo.lider),
        miembros=miembros_dtos,
    )


class TeamAdminService:
    """Service governing executing teams, memberships, leader changes, and process assignment."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)

    async def create_team(self, actor: Usuario, payload: EquipoEjecutorCreate) -> EquipoEjecutorResponse:
        """Create a new executing team enforcing leader role, state, and coordination/specialty integrity."""
        lider = await self.session.get(
            Usuario,
            payload.lider_id,
            options=[selectinload(Usuario.roles)],
        )
        if lider is None or lider.estado != EstadoUsuario.ACTIVO:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El líder especificado no existe o no se encuentra activo",
            )

        if not lider.has_role(RolUsuario.LIDER_EQUIPO_EJECUTOR.value):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El usuario asignado como líder debe poseer el rol LIDER_EQUIPO_EJECUTOR",
            )

        if lider.coordinacion_id != payload.coordinacion_id or lider.especialidad_id != payload.especialidad_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La coordinación y especialidad del equipo deben coincidir exactamente con las del líder",
            )

        # Verify specialty belongs to coordination and is active
        esp = await self.session.get(Especialidad, payload.especialidad_id)
        if esp is None or esp.coordinacion_id != payload.coordinacion_id or not esp.activo:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La especialidad no existe, no pertenece a la coordinación o se encuentra inactiva",
            )

        if payload.programa_id:
            prog = await self.session.get(ProgramaFormacion, payload.programa_id)
            if prog is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="El programa de formación especificado no existe",
                )
            # Check leader has authorized program
            leader_auth_stmt = select(UsuarioProgramaAutorizado).where(
                UsuarioProgramaAutorizado.usuario_id == payload.lider_id,
                UsuarioProgramaAutorizado.programa_id == payload.programa_id,
                UsuarioProgramaAutorizado.activo.is_(True),
            )
            leader_auth_res = await self.session.execute(leader_auth_stmt)
            if leader_auth_res.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="USUARIO_SIN_PROGRAMA_AUTORIZADO: El usuario asignado como líder no tiene autorizado el programa de formación",
                )

        equipo = EquipoEjecutor(
            nombre=payload.nombre.strip(),
            coordinacion_id=payload.coordinacion_id,
            especialidad_id=payload.especialidad_id,
            lider_id=payload.lider_id,
            programa_id=payload.programa_id,
            max_members=payload.max_members if payload.max_members is not None else 5,
            leaders_can_manage_members=payload.leaders_can_manage_members if payload.leaders_can_manage_members is not None else True,
            descripcion=payload.descripcion.strip() if payload.descripcion else None,
            estado=EstadoEquipo.ACTIVO,
        )
        self.session.add(equipo)
        await self.session.flush()

        # Register leader as member with RolEquipo.LIDER
        leader_member = EquipoEjecutorMiembro(
            equipo_id=equipo.id,
            usuario_id=payload.lider_id,
            rol_equipo=RolEquipo.LIDER,
            activo=True,
            asignado_por=actor.id,
            fecha_asignacion=datetime.now(UTC),
        )
        self.session.add(leader_member)

        await self.audit_repo.add_event(
            entidad="EquipoEjecutor",
            entidad_id=equipo.id,
            accion="TEAM_CREATED",
            detalle={
                "creado_por": str(actor.id),
                "nombre": equipo.nombre,
                "lider_id": str(equipo.lider_id),
                "programa_id": str(equipo.programa_id) if equipo.programa_id else None,
            },
        )
        await self.session.commit()

        reloaded = await self.session.get(
            EquipoEjecutor,
            equipo.id,
            options=[
                selectinload(EquipoEjecutor.lider).selectinload(Usuario.roles),
                selectinload(EquipoEjecutor.programa),
                selectinload(EquipoEjecutor.miembros).selectinload(EquipoEjecutorMiembro.usuario).selectinload(Usuario.roles),
            ],
        )
        return _map_equipo_dto(reloaded)  # type: ignore

    async def get_team(self, equipo_id: uuid.UUID) -> EquipoEjecutorResponse:
        """Fetch executing team details with leader and members."""
        stmt = (
            select(EquipoEjecutor)
            .where(EquipoEjecutor.id == equipo_id)
            .options(
                selectinload(EquipoEjecutor.lider).selectinload(Usuario.roles),
                selectinload(EquipoEjecutor.programa),
                selectinload(EquipoEjecutor.miembros).selectinload(EquipoEjecutorMiembro.usuario).selectinload(Usuario.roles),
            )
        )
        res = await self.session.execute(stmt)
        equipo = res.scalar_one_or_none()
        if equipo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipo no encontrado")
        return _map_equipo_dto(equipo)

    async def list_teams_paginated(
        self,
        actor: Usuario,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        estado: str | None = None,
        coordinacion_id: uuid.UUID | None = None,
        especialidad_id: uuid.UUID | None = None,
        lider_id: uuid.UUID | None = None,
    ) -> PaginatedEquiposResponse:
        """List executing teams enforcing user role scoping and server-side filtering."""
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        stmt = select(EquipoEjecutor).distinct()

        # Operational scoping for non-admin users
        if actor.has_role(RolUsuario.LIDER_EQUIPO_EJECUTOR.value) and not actor.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value):
            stmt = stmt.where(EquipoEjecutor.lider_id == actor.id)
        elif actor.has_role(RolUsuario.USUARIO_ADICIONAL.value) and not actor.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value):
            stmt = stmt.join(EquipoEjecutorMiembro, EquipoEjecutorMiembro.equipo_id == EquipoEjecutor.id).where(
                EquipoEjecutorMiembro.usuario_id == actor.id,
                EquipoEjecutorMiembro.activo.is_(True),
            )
        else:
            if lider_id:
                stmt = stmt.where(EquipoEjecutor.lider_id == lider_id)

        if estado:
            stmt = stmt.where(EquipoEjecutor.estado == estado)

        if coordinacion_id:
            stmt = stmt.where(EquipoEjecutor.coordinacion_id == coordinacion_id)

        if especialidad_id:
            stmt = stmt.where(EquipoEjecutor.especialidad_id == especialidad_id)

        if search and search.strip():
            stmt = stmt.where(EquipoEjecutor.nombre.ilike(f"%{search.strip()}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one() or 0

        items_stmt = (
            stmt.options(
                selectinload(EquipoEjecutor.lider).selectinload(Usuario.roles),
                selectinload(EquipoEjecutor.programa),
                selectinload(EquipoEjecutor.miembros).selectinload(EquipoEjecutorMiembro.usuario).selectinload(Usuario.roles),
            )
            .order_by(EquipoEjecutor.nombre)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items_res = await self.session.execute(items_stmt)
        equipos = items_res.scalars().unique().all()

        pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedEquiposResponse(
            items=[_map_equipo_dto(e) for e in equipos],
            page=page,
            page_size=page_size,
            total=total,
            pages=pages,
        )

    async def update_team(
        self,
        actor: Usuario,
        equipo_id: uuid.UUID,
        payload: EquipoEjecutorUpdate,
    ) -> EquipoEjecutorResponse:
        """Update executing team details, handling leader change and organizational scope changes transactionally."""
        equipo = await self.session.get(
            EquipoEjecutor,
            equipo_id,
            options=[
                selectinload(EquipoEjecutor.lider).selectinload(Usuario.roles),
                selectinload(EquipoEjecutor.miembros).selectinload(EquipoEjecutorMiembro.usuario),
            ],
        )
        if equipo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipo no encontrado")

        # Invariant 43: Cannot change coordinacion/especialidad if team has ProcesoCurricular assigned
        if payload.coordinacion_id is not None or payload.especialidad_id is not None:
            new_coord = payload.coordinacion_id or equipo.coordinacion_id
            new_esp = payload.especialidad_id or equipo.especialidad_id

            if new_coord != equipo.coordinacion_id or new_esp != equipo.especialidad_id:
                proc_stmt = select(func.count(ProcesoCurricular.id)).where(ProcesoCurricular.equipo_ejecutor_id == equipo_id)
                proc_count = (await self.session.execute(proc_stmt)).scalar_one() or 0
                if proc_count > 0:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="No se puede modificar la coordinación o especialidad de un equipo con procesos curriculares asignados",
                    )

                # Check leader compatibility
                if equipo.lider and (equipo.lider.coordinacion_id != new_coord or equipo.lider.especialidad_id != new_esp):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="El líder actual no pertenece a la nueva coordinación y especialidad seleccionadas",
                    )

                equipo.coordinacion_id = new_coord
                equipo.especialidad_id = new_esp

        # Invariant 44: Leader change with transactional propagation to ProcesoCurricular
        if payload.lider_id is not None and payload.lider_id != equipo.lider_id:
            new_lider = await self.session.get(
                Usuario,
                payload.lider_id,
                options=[selectinload(Usuario.roles)],
            )
            if new_lider is None or new_lider.estado != EstadoUsuario.ACTIVO:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="El nuevo líder especificado no existe o se encuentra inactivo",
                )
            if not new_lider.has_role(RolUsuario.LIDER_EQUIPO_EJECUTOR.value):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="El usuario asignado debe poseer el rol LIDER_EQUIPO_EJECUTOR",
                )
            if new_lider.coordinacion_id != equipo.coordinacion_id or new_lider.especialidad_id != equipo.especialidad_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="El nuevo líder debe pertenecer a la misma coordinación y especialidad del equipo",
                )

            old_lider_id = equipo.lider_id
            equipo.lider_id = new_lider.id

            # Atomic sync to all assigned ProcesoCurricular records
            proc_update_stmt = (
                update(ProcesoCurricular)
                .where(ProcesoCurricular.equipo_ejecutor_id == equipo_id)
                .values(lider_id=new_lider.id)
            )
            await self.session.execute(proc_update_stmt)

            await self.audit_repo.add_event(
                entidad="EquipoEjecutor",
                entidad_id=equipo.id,
                accion="TEAM_LEADER_CHANGED",
                detalle={
                    "actualizado_por": str(actor.id),
                    "antiguo_lider_id": str(old_lider_id),
                    "nuevo_lider_id": str(new_lider.id),
                },
            )

        if payload.nombre is not None:
            equipo.nombre = payload.nombre.strip()

        if payload.programa_id is not None and payload.programa_id != equipo.programa_id:
            prog = await self.session.get(ProgramaFormacion, payload.programa_id)
            if prog is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="El programa de formación especificado no existe",
                )
            # Check leader has authorized program
            leader_auth_stmt = select(UsuarioProgramaAutorizado).where(
                UsuarioProgramaAutorizado.usuario_id == equipo.lider_id,
                UsuarioProgramaAutorizado.programa_id == payload.programa_id,
                UsuarioProgramaAutorizado.activo.is_(True),
            )
            leader_auth_res = await self.session.execute(leader_auth_stmt)
            if leader_auth_res.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="USUARIO_SIN_PROGRAMA_AUTORIZADO: El líder actual no tiene autorizado el nuevo programa de formación",
                )
            equipo.programa_id = payload.programa_id

        if payload.max_members is not None:
            if payload.max_members < 1:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="El cupo máximo de integrantes debe ser al menos 1",
                )
            active_cnt = sum(1 for m in equipo.miembros if m.activo)
            if active_cnt > payload.max_members:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"El cupo máximo ({payload.max_members}) no puede ser menor a los integrantes activos actuales ({active_cnt})",
                )
            equipo.max_members = payload.max_members

        if payload.leaders_can_manage_members is not None:
            equipo.leaders_can_manage_members = payload.leaders_can_manage_members

        if payload.descripcion is not None:
            equipo.descripcion = payload.descripcion.strip() if payload.descripcion else None

        if payload.estado is not None and payload.estado != equipo.estado.value:
            try:
                nuevo_estado = EstadoEquipo(payload.estado)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Estado de equipo inválido: {payload.estado}",
                )
            equipo.estado = nuevo_estado
            await self.audit_repo.add_event(
                entidad="EquipoEjecutor",
                entidad_id=equipo.id,
                accion="TEAM_STATUS_CHANGED",
                detalle={"actualizado_por": str(actor.id), "nuevo_estado": nuevo_estado.value},
            )

        await self.audit_repo.add_event(
            entidad="EquipoEjecutor",
            entidad_id=equipo.id,
            accion="TEAM_UPDATED",
            detalle={"actualizado_por": str(actor.id), "nombre": equipo.nombre},
        )
        await self.session.commit()

        reloaded = await self.session.get(
            EquipoEjecutor,
            equipo.id,
            options=[
                selectinload(EquipoEjecutor.lider).selectinload(Usuario.roles),
                selectinload(EquipoEjecutor.programa),
                selectinload(EquipoEjecutor.miembros).selectinload(EquipoEjecutorMiembro.usuario).selectinload(Usuario.roles),
            ],
        )
        return _map_equipo_dto(reloaded)  # type: ignore

    async def add_member(
        self,
        actor: Usuario,
        equipo_id: uuid.UUID,
        payload: MiembroCreate,
    ) -> MiembroResponse:
        """Attach an additional user to an executing team verifying role, active state, program, and scope."""
        equipo = await self.session.get(
            EquipoEjecutor,
            equipo_id,
            options=[selectinload(EquipoEjecutor.miembros)],
        )
        if equipo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipo no encontrado")

        # Permission check: SUPERADMIN, ADMIN, or team leader if leaders_can_manage_members
        is_admin = actor.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value)
        is_team_leader = actor.id == equipo.lider_id or any(
            m.usuario_id == actor.id and m.activo and m.rol_equipo in [RolEquipo.LIDER, RolEquipo.CO_LIDER]
            for m in equipo.miembros
        )
        if not is_admin:
            if not getattr(equipo, "leaders_can_manage_members", True) or not is_team_leader:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tiene permisos para gestionar integrantes de este equipo ejecutor",
                )

        usuario = await self.session.get(Usuario, payload.usuario_id, options=[selectinload(Usuario.roles)])
        if usuario is None or usuario.estado != EstadoUsuario.ACTIVO:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El usuario especificado no existe o no se encuentra activo",
            )

        # Parse target rol_equipo
        try:
            rol_equipo = RolEquipo(payload.rol_equipo) if getattr(payload, "rol_equipo", None) else RolEquipo.INSTRUCTOR
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Rol de equipo inválido: {payload.rol_equipo}",
            )

        allowed_roles = [RolUsuario.USUARIO_ADICIONAL.value]
        if rol_equipo in [RolEquipo.LIDER, RolEquipo.CO_LIDER]:
            allowed_roles.append(RolUsuario.LIDER_EQUIPO_EJECUTOR.value)
        if not any(usuario.has_role(r) for r in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El miembro debe poseer el rol USUARIO_ADICIONAL",
            )

        if usuario.coordinacion_id != equipo.coordinacion_id or usuario.especialidad_id != equipo.especialidad_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El usuario de apoyo debe pertenecer a la misma coordinación y especialidad del equipo ejecutor",
            )

        # Program Compatibility Rule
        if equipo.programa_id:
            auth_check_stmt = select(UsuarioProgramaAutorizado).where(
                UsuarioProgramaAutorizado.usuario_id == payload.usuario_id,
                UsuarioProgramaAutorizado.programa_id == equipo.programa_id,
                UsuarioProgramaAutorizado.activo.is_(True),
            )
            auth_check_res = await self.session.execute(auth_check_stmt)
            if auth_check_res.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="USUARIO_SIN_PROGRAMA_AUTORIZADO: El usuario no tiene autorizado el programa de formación asignado al equipo",
                )

        # Max Members Check
        active_cnt = sum(1 for m in equipo.miembros if m.activo and m.usuario_id != payload.usuario_id)
        if active_cnt >= getattr(equipo, "max_members", 5):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"El equipo ha alcanzado el límite máximo de integrantes ({equipo.max_members})",
            )

        stmt = select(EquipoEjecutorMiembro).where(
            EquipoEjecutorMiembro.equipo_id == equipo_id,
            EquipoEjecutorMiembro.usuario_id == payload.usuario_id,
        )
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            existing.activo = True
            existing.rol_equipo = rol_equipo
            await self.audit_repo.add_event(
                entidad="EquipoEjecutorMiembro",
                entidad_id=existing.id,
                accion="TEAM_MEMBER_ADDED",
                detalle={"equipo_id": str(equipo_id), "usuario_id": str(payload.usuario_id), "rol_equipo": rol_equipo.value, "reactivado": True},
            )
            await self.session.commit()
            await self.session.refresh(existing)
            return MiembroResponse(
                id=existing.id,
                equipo_id=existing.equipo_id,
                usuario_id=existing.usuario_id,
                rol_equipo=existing.rol_equipo.value,
                activo=existing.activo,
                fecha_asignacion=existing.fecha_asignacion or datetime.now(UTC),
                usuario=_map_user_dto(usuario),
            )

        miembro = EquipoEjecutorMiembro(
            equipo_id=equipo_id,
            usuario_id=payload.usuario_id,
            rol_equipo=rol_equipo,
            activo=True,
            asignado_por=actor.id,
            fecha_asignacion=datetime.now(UTC),
        )
        self.session.add(miembro)
        await self.session.flush()

        await self.audit_repo.add_event(
            entidad="EquipoEjecutorMiembro",
            entidad_id=miembro.id,
            accion="TEAM_MEMBER_ADDED",
            detalle={"equipo_id": str(equipo_id), "usuario_id": str(payload.usuario_id), "rol_equipo": rol_equipo.value},
        )
        await self.session.commit()
        await self.session.refresh(miembro)

        return MiembroResponse(
            id=miembro.id,
            equipo_id=miembro.equipo_id,
            usuario_id=miembro.usuario_id,
            rol_equipo=miembro.rol_equipo.value,
            activo=miembro.activo,
            fecha_asignacion=miembro.fecha_asignacion or datetime.now(UTC),
            usuario=_map_user_dto(usuario),
        )

    async def update_member_status(
        self,
        actor: Usuario,
        equipo_id: uuid.UUID,
        usuario_id: uuid.UUID,
        payload: MiembroUpdate,
    ) -> MiembroResponse:
        """Activate, deactivate or update role of a team member."""
        equipo = await self.session.get(EquipoEjecutor, equipo_id, options=[selectinload(EquipoEjecutor.miembros)])
        if equipo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipo no encontrado")

        is_admin = actor.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value)
        is_team_leader = actor.id == equipo.lider_id or any(
            m.usuario_id == actor.id and m.activo and m.rol_equipo in [RolEquipo.LIDER, RolEquipo.CO_LIDER]
            for m in equipo.miembros
        )
        if not is_admin:
            if not getattr(equipo, "leaders_can_manage_members", True) or not is_team_leader:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tiene permisos para gestionar integrantes de este equipo ejecutor",
                )

        stmt = (
            select(EquipoEjecutorMiembro)
            .where(
                EquipoEjecutorMiembro.equipo_id == equipo_id,
                EquipoEjecutorMiembro.usuario_id == usuario_id,
            )
            .options(selectinload(EquipoEjecutorMiembro.usuario).selectinload(Usuario.roles))
        )
        res = await self.session.execute(stmt)
        miembro = res.scalar_one_or_none()
        if miembro is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membresía no encontrada")

        if payload.activo is not None:
            if payload.activo and not miembro.activo:
                active_cnt = sum(1 for m in equipo.miembros if m.activo and m.id != miembro.id)
                if active_cnt >= getattr(equipo, "max_members", 5):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"El equipo ha alcanzado el límite máximo de integrantes ({equipo.max_members})",
                    )
            miembro.activo = payload.activo
            await self.audit_repo.add_event(
                entidad="EquipoEjecutorMiembro",
                entidad_id=miembro.id,
                accion="TEAM_MEMBER_DISABLED" if not payload.activo else "TEAM_MEMBER_ENABLED",
                detalle={"equipo_id": str(equipo_id), "usuario_id": str(usuario_id), "activo": payload.activo},
            )

        if payload.rol_equipo is not None:
            try:
                nuevo_rol = RolEquipo(payload.rol_equipo)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Rol de equipo inválido: {payload.rol_equipo}",
                )
            miembro.rol_equipo = nuevo_rol
            await self.audit_repo.add_event(
                entidad="EquipoEjecutorMiembro",
                entidad_id=miembro.id,
                accion="TEAM_MEMBER_ROLE_CHANGED",
                detalle={"equipo_id": str(equipo_id), "usuario_id": str(usuario_id), "nuevo_rol": nuevo_rol.value},
            )

        await self.session.commit()
        await self.session.refresh(miembro)
        return MiembroResponse(
            id=miembro.id,
            equipo_id=miembro.equipo_id,
            usuario_id=miembro.usuario_id,
            rol_equipo=miembro.rol_equipo.value if hasattr(miembro.rol_equipo, "value") else str(miembro.rol_equipo),
            activo=miembro.activo,
            fecha_asignacion=miembro.fecha_asignacion or datetime.now(UTC),
            usuario=_map_user_dto(miembro.usuario),
        )

    async def list_user_teams(self, user: Usuario) -> list[EquipoEjecutorResponse]:
        """Return executing teams where the user participates as leader or active member."""
        stmt = (
            select(EquipoEjecutor)
            .distinct()
            .outerjoin(EquipoEjecutorMiembro, EquipoEjecutorMiembro.equipo_id == EquipoEjecutor.id)
            .where(
                or_(
                    EquipoEjecutor.lider_id == user.id,
                    and_(
                        EquipoEjecutorMiembro.usuario_id == user.id,
                        EquipoEjecutorMiembro.activo.is_(True),
                    ),
                ),
                EquipoEjecutor.estado == EstadoEquipo.ACTIVO,
            )
            .options(
                selectinload(EquipoEjecutor.lider).selectinload(Usuario.roles),
                selectinload(EquipoEjecutor.programa),
                selectinload(EquipoEjecutor.miembros).selectinload(EquipoEjecutorMiembro.usuario).selectinload(Usuario.roles),
            )
            .order_by(EquipoEjecutor.nombre)
        )
        res = await self.session.execute(stmt)
        return [_map_equipo_dto(e) for e in res.scalars().unique().all()]

    async def list_programas_catalogo(self) -> list[ProgramaSimpleResponse]:
        """Return all available training programs for assignment in admin or team creation."""
        stmt = select(ProgramaFormacion).order_by(ProgramaFormacion.codigo_programa)
        res = await self.session.execute(stmt)
        return [
            ProgramaSimpleResponse(
                id=p.id,
                codigo_programa=p.codigo_programa,
                nombre_programa=p.nombre_programa,
                version_programa=p.version_programa,
            )
            for p in res.scalars().all()
        ]

    async def assign_process(
        self,
        actor: Usuario,
        referencia_id: uuid.UUID,
        payload: ProcesoAsignarRequest,
    ) -> ProcesoCurricularResponse:
        """Assign or reassign a curricular process to an executing team and leader, maintaining strict consistency."""
        equipo = await self.session.get(EquipoEjecutor, payload.equipo_ejecutor_id)
        if equipo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipo no encontrado")

        if equipo.estado != EstadoEquipo.ACTIVO:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No se puede asignar un proceso a un equipo ejecutor inactivo",
            )

        # Leader validation: must match team leader
        if payload.lider_id and payload.lider_id != equipo.lider_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El líder indicado no coincide con el líder asignado al equipo ejecutor",
            )

        lider_id = equipo.lider_id

        stmt = select(ProcesoCurricular).where(ProcesoCurricular.referencia_id == referencia_id)
        res = await self.session.execute(stmt)
        proceso = res.scalar_one_or_none()

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
            self.session.add(proceso)
        else:
            proceso.coordinacion_id = equipo.coordinacion_id
            proceso.especialidad_id = equipo.especialidad_id
            proceso.equipo_ejecutor_id = equipo.id
            proceso.lider_id = lider_id
            proceso.estado_scope = EstadoScopeProceso.ASIGNADO

        await self.session.flush()
        await self.audit_repo.add_event(
            entidad="ProcesoCurricular",
            entidad_id=proceso.id,
            accion=accion,
            detalle={"referencia_id": str(referencia_id), "equipo_id": str(equipo.id), "lider_id": str(lider_id)},
        )
        await self.session.commit()
        await self.session.refresh(proceso)
        return ProcesoCurricularResponse.model_validate(proceso)
