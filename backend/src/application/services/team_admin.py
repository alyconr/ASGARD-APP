"""Team and Process Scope Administration Service."""

from __future__ import annotations

import math
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.shared.enums import EstadoEquipo, EstadoScopeProceso, EstadoUsuario, RolUsuario
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.models.curriculum import ProgramaFormacion
from src.infrastructure.db.models.organizacion import (
    Coordinacion,
    EquipoEjecutor,
    EquipoEjecutorMiembro,
    EquipoEjecutorPrograma,
    Especialidad,
    ProcesoCurricular,
)
from src.infrastructure.repositories.audit import AuditRepository
from src.interfaces.http.schemas.auth import UserResponse
from src.interfaces.http.schemas.organizacion import (
    EquipoEjecutorCreate,
    EquipoEjecutorResponse,
    EquipoEjecutorUpdate,
    IniciarProcesoRequest,
    MiEquipoResponse,
    MiembroCreate,
    MiembroResponse,
    MiembroUpdate,
    PaginatedEquiposResponse,
    ProgramaAutorizadoCreate,
    ProgramaAutorizadoResponse,
    ProcesoAsignarRequest,
    ProcesoCurricularResponse,
)


def _map_user_dto(user: Usuario | None) -> UserResponse | None:
    if user is None:
        return None
    estado_val = user.estado.value if hasattr(getattr(user, "estado", None), "value") else str(getattr(user, "estado", None) or "ACTIVO")
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
    )


def _map_proceso_dto(proceso: ProcesoCurricular | None) -> ProcesoCurricularResponse | None:
    if proceso is None:
        return None
    tipo_val = proceso.tipo_necesidad.value if hasattr(proceso.tipo_necesidad, "value") else str(proceso.tipo_necesidad)
    estado_val = proceso.estado_scope.value if hasattr(proceso.estado_scope, "value") else str(proceso.estado_scope)
    return ProcesoCurricularResponse(
        id=proceso.id,
        referencia_id=proceso.referencia_id,
        coordinacion_id=proceso.coordinacion_id,
        especialidad_id=proceso.especialidad_id,
        equipo_ejecutor_id=proceso.equipo_ejecutor_id,
        lider_id=proceso.lider_id,
        tipo_necesidad=tipo_val,
        estado_scope=estado_val,
        programa_id=proceso.programa_id,
        proyecto_id=proceso.proyecto_id,
        programa_nombre=proceso.programa.nombre_programa if getattr(proceso, "programa", None) else None,
        programa_codigo=proceso.programa.codigo_programa if getattr(proceso, "programa", None) else None,
        proyecto_nombre=proceso.proyecto.nombre_proyecto if getattr(proceso, "proyecto", None) else None,
        proyecto_codigo=proceso.proyecto.codigo_proyecto if getattr(proceso, "proyecto", None) else None,
    )


def _map_programa_autorizado_dto(prog: EquipoEjecutorPrograma | None) -> ProgramaAutorizadoResponse | None:
    if prog is None:
        return None
    return ProgramaAutorizadoResponse(
        id=prog.id,
        equipo_id=prog.equipo_id,
        programa_id=prog.programa_id,
        codigo_programa=prog.codigo_programa,
        nombre_programa=prog.nombre_programa,
        activo=prog.activo,
    )


def _map_equipo_dto(equipo: EquipoEjecutor) -> EquipoEjecutorResponse:
    miembros_dtos = [
        MiembroResponse(
            id=m.id,
            equipo_id=m.equipo_id,
            usuario_id=m.usuario_id,
            activo=m.activo,
            fecha_asignacion=m.fecha_asignacion,
            usuario=_map_user_dto(m.usuario),
        )
        for m in (getattr(equipo, "miembros", None) or [])
    ]
    procesos_dtos = [
        _map_proceso_dto(p)
        for p in (getattr(equipo, "procesos", None) or [])
        if p is not None
    ]
    programas_dtos = [
        _map_programa_autorizado_dto(pr)
        for pr in (getattr(equipo, "programas_autorizados", None) or [])
        if pr is not None
    ]
    return EquipoEjecutorResponse(
        id=equipo.id,
        nombre=equipo.nombre,
        coordinacion_id=equipo.coordinacion_id,
        especialidad_id=equipo.especialidad_id,
        lider_id=equipo.lider_id,
        estado=equipo.estado.value if hasattr(equipo.estado, "value") else str(equipo.estado),
        lider=_map_user_dto(equipo.lider),
        miembros=miembros_dtos,
        procesos=[p for p in procesos_dtos if p is not None],
        programas_autorizados=[pr for pr in programas_dtos if pr is not None],
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

        equipo = EquipoEjecutor(
            nombre=payload.nombre.strip(),
            coordinacion_id=payload.coordinacion_id,
            especialidad_id=payload.especialidad_id,
            lider_id=payload.lider_id,
            estado=EstadoEquipo.ACTIVO,
        )
        self.session.add(equipo)
        await self.session.flush()

        if payload.programas:
            for prog_in in payload.programas:
                p_id = prog_in.programa_id
                if not p_id:
                    p_stmt = select(ProgramaFormacion).where(
                        func.lower(ProgramaFormacion.codigo_programa) == prog_in.codigo_programa.strip().lower()
                    )
                    p_res = await self.session.execute(p_stmt)
                    matched_p = p_res.scalars().first()
                    if matched_p:
                        p_id = matched_p.id

                equipo_prog = EquipoEjecutorPrograma(
                    equipo_id=equipo.id,
                    programa_id=p_id,
                    codigo_programa=prog_in.codigo_programa.strip(),
                    nombre_programa=prog_in.nombre_programa.strip(),
                    activo=True,
                )
                self.session.add(equipo_prog)

        await self.audit_repo.add_event(
            entidad="EquipoEjecutor",
            entidad_id=equipo.id,
            accion="TEAM_CREATED",
            detalle={"creado_por": str(actor.id), "nombre": equipo.nombre, "lider_id": str(equipo.lider_id)},
        )
        await self.session.commit()

        reloaded = await self.session.get(
            EquipoEjecutor,
            equipo.id,
            options=[
                selectinload(EquipoEjecutor.lider).selectinload(Usuario.roles),
                selectinload(EquipoEjecutor.miembros).selectinload(EquipoEjecutorMiembro.usuario).selectinload(Usuario.roles),
                selectinload(EquipoEjecutor.programas_autorizados),
                selectinload(EquipoEjecutor.procesos).selectinload(ProcesoCurricular.programa),
                selectinload(EquipoEjecutor.procesos).selectinload(ProcesoCurricular.proyecto),
            ],
        )
        return _map_equipo_dto(reloaded)  # type: ignore

    async def get_team(self, equipo_id: uuid.UUID) -> EquipoEjecutorResponse:
        """Fetch executing team details with leader, members, and assigned processes."""
        stmt = (
            select(EquipoEjecutor)
            .where(EquipoEjecutor.id == equipo_id)
            .options(
                selectinload(EquipoEjecutor.lider).selectinload(Usuario.roles),
                selectinload(EquipoEjecutor.miembros).selectinload(EquipoEjecutorMiembro.usuario).selectinload(Usuario.roles),
                selectinload(EquipoEjecutor.programas_autorizados),
                selectinload(EquipoEjecutor.procesos).selectinload(ProcesoCurricular.programa),
                selectinload(EquipoEjecutor.procesos).selectinload(ProcesoCurricular.proyecto),
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
                selectinload(EquipoEjecutor.miembros).selectinload(EquipoEjecutorMiembro.usuario).selectinload(Usuario.roles),
                selectinload(EquipoEjecutor.programas_autorizados),
                selectinload(EquipoEjecutor.procesos).selectinload(ProcesoCurricular.programa),
                selectinload(EquipoEjecutor.procesos).selectinload(ProcesoCurricular.proyecto),
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

        if payload.programas is not None:
            del_stmt = select(EquipoEjecutorPrograma).where(EquipoEjecutorPrograma.equipo_id == equipo.id)
            del_res = await self.session.execute(del_stmt)
            for old_p in del_res.scalars().all():
                await self.session.delete(old_p)
            for prog_in in payload.programas:
                p_id = prog_in.programa_id
                if not p_id:
                    p_stmt = select(ProgramaFormacion).where(
                        func.lower(ProgramaFormacion.codigo_programa) == prog_in.codigo_programa.strip().lower()
                    )
                    p_res = await self.session.execute(p_stmt)
                    matched_p = p_res.scalars().first()
                    if matched_p:
                        p_id = matched_p.id

                equipo_prog = EquipoEjecutorPrograma(
                    equipo_id=equipo.id,
                    programa_id=p_id,
                    codigo_programa=prog_in.codigo_programa.strip(),
                    nombre_programa=prog_in.nombre_programa.strip(),
                    activo=True,
                )
                self.session.add(equipo_prog)

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
                selectinload(EquipoEjecutor.miembros).selectinload(EquipoEjecutorMiembro.usuario).selectinload(Usuario.roles),
                selectinload(EquipoEjecutor.programas_autorizados),
                selectinload(EquipoEjecutor.procesos).selectinload(ProcesoCurricular.programa),
                selectinload(EquipoEjecutor.procesos).selectinload(ProcesoCurricular.proyecto),
            ],
        )
        return _map_equipo_dto(reloaded)  # type: ignore

    async def add_member(
        self,
        actor: Usuario,
        equipo_id: uuid.UUID,
        payload: MiembroCreate,
    ) -> MiembroResponse:
        """Attach an additional user to an executing team verifying role, active state, and scope."""
        equipo = await self.session.get(EquipoEjecutor, equipo_id)
        if equipo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipo no encontrado")

        usuario = await self.session.get(Usuario, payload.usuario_id, options=[selectinload(Usuario.roles)])
        if usuario is None or usuario.estado != EstadoUsuario.ACTIVO:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El usuario especificado no existe o no se encuentra activo",
            )

        if not usuario.has_role(RolUsuario.USUARIO_ADICIONAL.value):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El miembro debe poseer el rol USUARIO_ADICIONAL",
            )

        if usuario.coordinacion_id != equipo.coordinacion_id or usuario.especialidad_id != equipo.especialidad_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El usuario de apoyo debe pertenecer a la misma coordinación y especialidad del equipo ejecutor",
            )

        stmt = select(EquipoEjecutorMiembro).where(
            EquipoEjecutorMiembro.equipo_id == equipo_id,
            EquipoEjecutorMiembro.usuario_id == payload.usuario_id,
        )
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            existing.activo = True
            await self.audit_repo.add_event(
                entidad="EquipoEjecutorMiembro",
                entidad_id=existing.id,
                accion="TEAM_MEMBER_ADDED",
                detalle={"equipo_id": str(equipo_id), "usuario_id": str(payload.usuario_id), "reactivado": True},
            )
            await self.session.commit()
            await self.session.refresh(existing)
            return MiembroResponse(
                id=existing.id,
                equipo_id=existing.equipo_id,
                usuario_id=existing.usuario_id,
                activo=existing.activo,
                fecha_asignacion=existing.fecha_asignacion,
                usuario=_map_user_dto(usuario),
            )

        miembro = EquipoEjecutorMiembro(
            equipo_id=equipo_id,
            usuario_id=payload.usuario_id,
            activo=True,
            asignado_por=actor.id,
        )
        self.session.add(miembro)
        await self.session.flush()

        await self.audit_repo.add_event(
            entidad="EquipoEjecutorMiembro",
            entidad_id=miembro.id,
            accion="TEAM_MEMBER_ADDED",
            detalle={"equipo_id": str(equipo_id), "usuario_id": str(payload.usuario_id)},
        )
        await self.session.commit()
        await self.session.refresh(miembro)

        return MiembroResponse(
            id=miembro.id,
            equipo_id=miembro.equipo_id,
            usuario_id=miembro.usuario_id,
            activo=miembro.activo,
            fecha_asignacion=miembro.fecha_asignacion,
            usuario=_map_user_dto(usuario),
        )

    async def update_member_status(
        self,
        actor: Usuario,
        equipo_id: uuid.UUID,
        usuario_id: uuid.UUID,
        payload: MiembroUpdate,
    ) -> MiembroResponse:
        """Activate or deactivate team membership."""
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

        miembro.activo = payload.activo
        await self.audit_repo.add_event(
            entidad="EquipoEjecutorMiembro",
            entidad_id=miembro.id,
            accion="TEAM_MEMBER_DISABLED" if not payload.activo else "TEAM_MEMBER_ENABLED",
            detalle={"equipo_id": str(equipo_id), "usuario_id": str(usuario_id), "activo": payload.activo},
        )
        await self.session.commit()
        await self.session.refresh(miembro)
        return MiembroResponse(
            id=miembro.id,
            equipo_id=miembro.equipo_id,
            usuario_id=miembro.usuario_id,
            activo=miembro.activo,
            fecha_asignacion=miembro.fecha_asignacion,
            usuario=_map_user_dto(miembro.usuario),
        )

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
        
        reloaded_proc = await self.session.get(
            ProcesoCurricular,
            proceso.id,
            options=[
                selectinload(ProcesoCurricular.programa),
                selectinload(ProcesoCurricular.proyecto),
            ],
        )
        dto = _map_proceso_dto(reloaded_proc or proceso)
        assert dto is not None
        return dto

    async def delete_team(
        self,
        actor: Usuario,
        equipo_id: uuid.UUID,
        desasignar_procesos: bool = False,
    ) -> dict[str, Any]:
        """Permanently delete executing team, optionally unassigning linked processes."""
        equipo = await self.session.get(EquipoEjecutor, equipo_id)
        if equipo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipo ejecutor no encontrado")

        proc_stmt = select(ProcesoCurricular).where(ProcesoCurricular.equipo_ejecutor_id == equipo_id)
        proc_res = await self.session.execute(proc_stmt)
        assigned_processes = proc_res.scalars().all()

        if len(assigned_processes) > 0 and not desasignar_procesos:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"No se puede eliminar el equipo '{equipo.nombre}' porque tiene {len(assigned_processes)} proceso(s) curricular(es) asignado(s). Desasigne o elimine los procesos vinculados primero.",
            )

        if len(assigned_processes) > 0 and desasignar_procesos:
            for proc in assigned_processes:
                proc.equipo_ejecutor_id = None
                proc.lider_id = None
                proc.estado_scope = EstadoScopeProceso.SIN_ASIGNAR
            await self.session.flush()

        nombre_equipo = equipo.nombre
        await self.session.delete(equipo)
        await self.audit_repo.add_event(
            entidad="EquipoEjecutor",
            entidad_id=equipo_id,
            accion="TEAM_DELETED",
            detalle={
                "eliminado_por": str(actor.id),
                "nombre": nombre_equipo,
                "procesos_desasignados": len(assigned_processes),
            },
        )
        await self.session.commit()
        return {"status": "ok", "message": f"Equipo ejecutor '{nombre_equipo}' eliminado exitosamente"}

    async def unassign_process(
        self,
        actor: Usuario,
        referencia_id: uuid.UUID,
    ) -> ProcesoCurricularResponse:
        """Unassign a curricular process from its team and leader, reverting it to SIN_ASIGNAR."""
        stmt = (
            select(ProcesoCurricular)
            .where(ProcesoCurricular.referencia_id == referencia_id)
            .options(
                selectinload(ProcesoCurricular.programa),
                selectinload(ProcesoCurricular.proyecto),
            )
        )
        res = await self.session.execute(stmt)
        proceso = res.scalar_one_or_none()
        if proceso is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proceso curricular no encontrado")

        old_team_id = proceso.equipo_ejecutor_id
        old_lider_id = proceso.lider_id

        proceso.equipo_ejecutor_id = None
        proceso.lider_id = None
        proceso.estado_scope = EstadoScopeProceso.SIN_ASIGNAR

        await self.audit_repo.add_event(
            entidad="ProcesoCurricular",
            entidad_id=proceso.id,
            accion="PROCESS_UNASSIGNED",
            detalle={
                "referencia_id": str(referencia_id),
                "antiguo_equipo_id": str(old_team_id) if old_team_id else None,
                "antiguo_lider_id": str(old_lider_id) if old_lider_id else None,
                "desasignado_por": str(actor.id),
            },
        )
        await self.session.commit()
        await self.session.refresh(proceso)
        dto = _map_proceso_dto(proceso)
        assert dto is not None
        return dto

    async def delete_process(
        self,
        actor: Usuario,
        referencia_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Permanently delete a curricular process, cleaning up its drafts and artifacts."""
        stmt = select(ProcesoCurricular).where(ProcesoCurricular.referencia_id == referencia_id)
        res = await self.session.execute(stmt)
        proceso = res.scalar_one_or_none()
        if proceso is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proceso curricular no encontrado")

        # Attempt to clean up via ProyectoCargueService if possible
        try:
            from src.application.services.proyecto_cargue import ProyectoCargueService
            from src.core.config import get_settings
            from src.infrastructure.storage.document_storage import MinioDocumentStorageService

            settings = get_settings()
            storage_service = MinioDocumentStorageService(settings)
            cargue_service = ProyectoCargueService(session=self.session, storage_service=storage_service)
            await cargue_service.eliminar_cargue_completo(referencia_id)
        except Exception:
            pass

        # Cleanup drafts directly
        from src.infrastructure.db.models.drafts import BorradorSesion
        draft_stmt = select(BorradorSesion).where(BorradorSesion.referencia_id == referencia_id)
        draft_res = await self.session.execute(draft_stmt)
        for draft in draft_res.scalars().all():
            await self.session.delete(draft)

        proc_id = proceso.id
        await self.session.delete(proceso)
        await self.audit_repo.add_event(
            entidad="ProcesoCurricular",
            entidad_id=proc_id,
            accion="PROCESS_DELETED",
            detalle={
                "referencia_id": str(referencia_id),
                "eliminado_por": str(actor.id),
            },
        )
        await self.session.commit()
        return {"status": "ok", "message": f"Proceso curricular '{referencia_id}' eliminado exitosamente"}

    async def list_authorized_programs(self, equipo_id: uuid.UUID) -> list[ProgramaAutorizadoResponse]:
        """List programs authorized for the given team."""
        stmt = (
            select(EquipoEjecutorPrograma)
            .where(EquipoEjecutorPrograma.equipo_id == equipo_id)
            .order_by(EquipoEjecutorPrograma.codigo_programa.asc())
        )
        res = await self.session.execute(stmt)
        return [_map_programa_autorizado_dto(p) for p in res.scalars().all() if p is not None]  # type: ignore

    async def add_authorized_program(
        self,
        actor: Usuario,
        equipo_id: uuid.UUID,
        payload: ProgramaAutorizadoCreate,
    ) -> ProgramaAutorizadoResponse:
        """Add an authorized program to an executing team."""
        equipo = await self.session.get(EquipoEjecutor, equipo_id)
        if equipo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipo no encontrado")

        clean_code = payload.codigo_programa.strip()
        clean_name = payload.nombre_programa.strip()

        # Check existing
        existing_stmt = select(EquipoEjecutorPrograma).where(
            EquipoEjecutorPrograma.equipo_id == equipo_id,
            func.lower(EquipoEjecutorPrograma.codigo_programa) == clean_code.lower(),
        )
        existing_res = await self.session.execute(existing_stmt)
        if existing_res.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El programa con código '{clean_code}' ya está asignado a este equipo ejecutor",
            )

        p_id = payload.programa_id
        if not p_id:
            p_stmt = select(ProgramaFormacion).where(
                func.lower(ProgramaFormacion.codigo_programa) == clean_code.lower()
            )
            p_res = await self.session.execute(p_stmt)
            matched_p = p_res.scalars().first()
            if matched_p:
                p_id = matched_p.id

        prog = EquipoEjecutorPrograma(
            equipo_id=equipo_id,
            programa_id=p_id,
            codigo_programa=clean_code,
            nombre_programa=clean_name,
            activo=True,
        )
        self.session.add(prog)
        await self.session.flush()

        await self.audit_repo.add_event(
            entidad="EquipoEjecutorPrograma",
            entidad_id=prog.id,
            accion="PROGRAM_AUTHORIZED_FOR_TEAM",
            detalle={
                "equipo_id": str(equipo_id),
                "codigo_programa": clean_code,
                "nombre_programa": clean_name,
                "autorizado_por": str(actor.id),
            },
        )
        await self.session.commit()
        await self.session.refresh(prog)
        dto = _map_programa_autorizado_dto(prog)
        assert dto is not None
        return dto

    async def remove_authorized_program(
        self,
        actor: Usuario,
        equipo_id: uuid.UUID,
        programa_autorizado_id: uuid.UUID,
    ) -> dict[str, str]:
        """Remove an authorized program from an executing team."""
        prog = await self.session.get(EquipoEjecutorPrograma, programa_autorizado_id)
        if prog is None or prog.equipo_id != equipo_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programa autorizado no encontrado")

        await self.session.delete(prog)
        await self.audit_repo.add_event(
            entidad="EquipoEjecutorPrograma",
            entidad_id=programa_autorizado_id,
            accion="PROGRAM_DEAUTHORIZED_FROM_TEAM",
            detalle={
                "equipo_id": str(equipo_id),
                "codigo_programa": prog.codigo_programa,
                "removido_por": str(actor.id),
            },
        )
        await self.session.commit()
        return {"status": "ok", "message": "Programa desasociado del equipo ejecutor"}

    async def list_my_teams(self, actor: Usuario) -> list[MiEquipoResponse]:
        """List active executing teams that the actor belongs to as leader or active member."""
        # Find team IDs where user is leader
        leader_stmt = select(EquipoEjecutor.id).where(
            EquipoEjecutor.lider_id == actor.id,
            EquipoEjecutor.estado == EstadoEquipo.ACTIVO,
        )
        leader_res = await self.session.execute(leader_stmt)
        leader_team_ids = set(leader_res.scalars().all())

        # Find team IDs where user is active member
        member_stmt = (
            select(EquipoEjecutorMiembro.equipo_id)
            .join(EquipoEjecutor, EquipoEjecutorMiembro.equipo_id == EquipoEjecutor.id)
            .where(
                EquipoEjecutorMiembro.usuario_id == actor.id,
                EquipoEjecutorMiembro.activo.is_(True),
                EquipoEjecutor.estado == EstadoEquipo.ACTIVO,
            )
        )
        member_res = await self.session.execute(member_stmt)
        member_team_ids = set(member_res.scalars().all())

        all_team_ids = leader_team_ids.union(member_team_ids)
        if not all_team_ids:
            return []

        stmt = (
            select(EquipoEjecutor)
            .where(EquipoEjecutor.id.in_(all_team_ids))
            .options(
                selectinload(EquipoEjecutor.coordinacion),
                selectinload(EquipoEjecutor.especialidad),
                selectinload(EquipoEjecutor.lider).selectinload(Usuario.roles),
                selectinload(EquipoEjecutor.miembros).selectinload(EquipoEjecutorMiembro.usuario).selectinload(Usuario.roles),
                selectinload(EquipoEjecutor.programas_autorizados),
                selectinload(EquipoEjecutor.procesos).selectinload(ProcesoCurricular.programa),
                selectinload(EquipoEjecutor.procesos).selectinload(ProcesoCurricular.proyecto),
            )
            .order_by(EquipoEjecutor.nombre.asc())
        )
        res = await self.session.execute(stmt)
        teams = res.scalars().all()

        responses: list[MiEquipoResponse] = []
        for t in teams:
            rol = "LIDER" if t.id in leader_team_ids else "MIEMBRO"
            eq_dto = _map_equipo_dto(t)
            responses.append(
                MiEquipoResponse(
                    equipo=eq_dto,
                    rol_en_equipo=rol,
                    programas_autorizados=eq_dto.programas_autorizados,
                    procesos=eq_dto.procesos,
                )
            )
        return responses

    async def iniciar_proceso_curricular(
        self,
        actor: Usuario,
        payload: IniciarProcesoRequest,
    ) -> ProcesoCurricularResponse:
        """Start a new curricular process scoped strictly to an executor team and authorized program."""
        from src.application.services.access_scope import AccessScopeService
        from src.domain.drafts.types import TipoBloqueBorrador
        from src.domain.shared.enums import EstadoBloque
        from src.infrastructure.db.models.drafts import BorradorSesion

        scope_service = AccessScopeService(self.session)
        team = await scope_service.require_start_curricular_process(
            actor,
            payload.equipo_ejecutor_id,
            payload.programa_id,
            payload.codigo_programa,
        )

        # Check existing process for team and program
        existing_stmt = (
            select(ProcesoCurricular)
            .where(
                ProcesoCurricular.equipo_ejecutor_id == team.id,
            )
            .options(
                selectinload(ProcesoCurricular.programa),
                selectinload(ProcesoCurricular.proyecto),
            )
        )
        if payload.programa_id:
            existing_stmt = existing_stmt.where(ProcesoCurricular.programa_id == payload.programa_id)
        existing_res = await self.session.execute(existing_stmt)
        candidates = existing_res.scalars().all()

        for cand in candidates:
            if payload.codigo_programa and cand.programa:
                if cand.programa.codigo_programa.strip().upper() == payload.codigo_programa.strip().upper():
                    return _map_proceso_dto(cand)  # type: ignore
            elif payload.programa_id and cand.programa_id == payload.programa_id:
                return _map_proceso_dto(cand)  # type: ignore

        # Resolve programa_id if codigo_programa was supplied
        resolved_programa_id = payload.programa_id
        if not resolved_programa_id and payload.codigo_programa:
            prog_stmt = select(ProgramaFormacion).where(
                func.lower(ProgramaFormacion.codigo_programa) == payload.codigo_programa.strip().lower()
            )
            prog_res = await self.session.execute(prog_stmt)
            matched_prog = prog_res.scalars().first()
            if matched_prog:
                resolved_programa_id = matched_prog.id

        new_referencia_id = uuid.uuid4()
        from src.domain.shared.enums import TipoNecesidadProceso
        try:
            tipo_nec = TipoNecesidadProceso(payload.tipo_necesidad)
        except ValueError:
            tipo_nec = TipoNecesidadProceso.CREAR_PLANEACION

        proceso = ProcesoCurricular(
            referencia_id=new_referencia_id,
            coordinacion_id=team.coordinacion_id,
            especialidad_id=team.especialidad_id,
            equipo_ejecutor_id=team.id,
            lider_id=team.lider_id,
            tipo_necesidad=tipo_nec,
            estado_scope=EstadoScopeProceso.ASIGNADO,
            programa_id=resolved_programa_id,
            creado_por=actor.id,
        )
        self.session.add(proceso)

        # Initialize BorradorSesion for PROGRAMA
        initial_payload = {
            "meta": {
                "equipo_ejecutor_id": str(team.id),
                "programa_id": str(resolved_programa_id) if resolved_programa_id else None,
                "codigo_programa": payload.codigo_programa,
                "iniciado_por": str(actor.id),
            },
            "documental": {},
            "curricular": {
                "programa_formacion_id": str(resolved_programa_id) if resolved_programa_id else None,
            },
        }
        draft = BorradorSesion(
            tipo_bloque=TipoBloqueBorrador.PROGRAMA.value,
            referencia_id=new_referencia_id,
            paso_actual="origen-documental",
            payload_json=initial_payload,
            estado_borrador=EstadoBloque.BORRADOR,
        )
        self.session.add(draft)

        await self.audit_repo.add_event(
            entidad="ProcesoCurricular",
            entidad_id=proceso.id,
            accion="CURRICULAR_PROCESS_STARTED",
            detalle={
                "referencia_id": str(new_referencia_id),
                "created_by_user_id": str(actor.id),
                "executor_team_id": str(team.id),
                "training_program_id": str(resolved_programa_id) if resolved_programa_id else None,
                "codigo_programa": payload.codigo_programa,
            },
            actor_usuario_id=actor.id,
            referencia_id=new_referencia_id,
        )
        await self.session.commit()

        reloaded_stmt = (
            select(ProcesoCurricular)
            .where(ProcesoCurricular.id == proceso.id)
            .options(
                selectinload(ProcesoCurricular.programa),
                selectinload(ProcesoCurricular.proyecto),
            )
        )
        reloaded_res = await self.session.execute(reloaded_stmt)
        saved_proc = reloaded_res.scalar_one()
        return _map_proceso_dto(saved_proc)  # type: ignore

