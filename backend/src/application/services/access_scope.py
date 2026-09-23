"""Central access scope and data isolation service."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.shared.enums import EstadoEquipo, EstadoScopeProceso, RolUsuario
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.models.curriculum import ProgramaFormacion
from src.infrastructure.db.models.organizacion import (
    EquipoEjecutor,
    EquipoEjecutorMiembro,
    ProcesoCurricular,
)
from src.infrastructure.db.models.planeacion import PlaneacionPedagogica
from src.infrastructure.db.models.proyecto import ProyectoFormativo


class AccessScopeService:
    """Evaluate data-level authorization and enforce strict process isolation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _try_auto_heal_proceso(
        self, user: Usuario, referencia_id: uuid.UUID
    ) -> ProcesoCurricular | None:
        """Auto-heal legacy drafts created without a ProcesoCurricular anchor."""
        from src.infrastructure.db.models.drafts import BorradorSesion

        draft_stmt = select(BorradorSesion).where(BorradorSesion.referencia_id == referencia_id)
        draft_res = await self._session.execute(draft_stmt)
        draft = draft_res.scalar_one_or_none()
        if draft is None:
            return None

        coordinacion_id = user.coordinacion_id
        especialidad_id = user.especialidad_id
        equipo_id = None
        lider_id = None
        programa_id = None
        proyecto_id = None

        if isinstance(draft.payload_json, dict):
            curr = draft.payload_json.get("curricular")
            if isinstance(curr, dict) and curr.get("programa_formacion_id"):
                try:
                    programa_id = uuid.UUID(str(curr.get("programa_formacion_id")))
                except (ValueError, TypeError):
                    pass
            meta = draft.payload_json.get("meta")
            if isinstance(meta, dict) and meta.get("programaId"):
                try:
                    programa_id = uuid.UUID(str(meta.get("programaId")))
                except (ValueError, TypeError):
                    pass

        if user.has_role(RolUsuario.LIDER_EQUIPO_EJECUTOR.value):
            teams_stmt = select(EquipoEjecutor).where(
                EquipoEjecutor.lider_id == user.id,
                EquipoEjecutor.estado == EstadoEquipo.ACTIVO,
            )
            teams_res = await self._session.execute(teams_stmt)
            active_teams = teams_res.scalars().all()
            if active_teams:
                target_team = active_teams[0]
                equipo_id = target_team.id
                coordinacion_id = target_team.coordinacion_id
                especialidad_id = target_team.especialidad_id
                lider_id = user.id
        elif user.has_role(RolUsuario.USUARIO_ADICIONAL.value):
            members_stmt = (
                select(EquipoEjecutor)
                .join(EquipoEjecutorMiembro, EquipoEjecutor.id == EquipoEjecutorMiembro.equipo_id)
                .where(
                    EquipoEjecutorMiembro.usuario_id == user.id,
                    EquipoEjecutorMiembro.activo.is_(True),
                    EquipoEjecutor.estado == EstadoEquipo.ACTIVO,
                )
            )
            members_res = await self._session.execute(members_stmt)
            member_team = members_res.scalar_one_or_none()
            if member_team:
                equipo_id = member_team.id
                coordinacion_id = member_team.coordinacion_id
                especialidad_id = member_team.especialidad_id
                lider_id = member_team.lider_id

        proceso = await self.ensure_proceso_for_referencia(
            referencia_id=referencia_id,
            creado_por=user.id,
            coordinacion_id=coordinacion_id,
            especialidad_id=especialidad_id,
            equipo_ejecutor_id=equipo_id,
            lider_id=lider_id,
            programa_id=programa_id,
            proyecto_id=proyecto_id,
        )
        stmt = (
            select(ProcesoCurricular)
            .where(ProcesoCurricular.id == proceso.id)
            .options(
                selectinload(ProcesoCurricular.equipo_ejecutor).selectinload(
                    EquipoEjecutor.miembros
                )
            )
        )
        reloaded_res = await self._session.execute(stmt)
        return reloaded_res.scalar_one_or_none() or proceso

    async def can_access_process(self, user: Usuario, referencia_id: uuid.UUID) -> bool:
        """Determine whether the user is authorized to access the given process."""
        stmt = (
            select(ProcesoCurricular)
            .where(ProcesoCurricular.referencia_id == referencia_id)
            .options(
                selectinload(ProcesoCurricular.equipo_ejecutor).selectinload(
                    EquipoEjecutor.miembros
                )
            )
        )
        res = await self._session.execute(stmt)
        proceso = res.scalar_one_or_none()

        if proceso is None:
            proceso = await self._try_auto_heal_proceso(user, referencia_id)
            if proceso is None:
                return False

        if user.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value):
            return True

        if proceso.estado_scope != EstadoScopeProceso.ASIGNADO:
            return False

        # Inactive executing teams block operational access for leaders and members
        if proceso.equipo_ejecutor and proceso.equipo_ejecutor.estado != EstadoEquipo.ACTIVO:
            return False

        if user.has_role(RolUsuario.LIDER_EQUIPO_EJECUTOR.value):
            if proceso.lider_id == user.id:
                return True
            if proceso.equipo_ejecutor and proceso.equipo_ejecutor.lider_id == user.id:
                return True
            if not proceso.equipo_ejecutor_id:
                return False
            member_stmt = select(EquipoEjecutorMiembro).where(
                EquipoEjecutorMiembro.equipo_id == proceso.equipo_ejecutor_id,
                EquipoEjecutorMiembro.usuario_id == user.id,
                EquipoEjecutorMiembro.activo.is_(True),
            )
            member_res = await self._session.execute(member_stmt)
            member = member_res.scalar_one_or_none()
            return isinstance(member, EquipoEjecutorMiembro) and member.activo

        if user.has_role(RolUsuario.USUARIO_ADICIONAL.value):
            if not proceso.equipo_ejecutor_id:
                return False
            member_stmt = select(EquipoEjecutorMiembro).where(
                EquipoEjecutorMiembro.equipo_id == proceso.equipo_ejecutor_id,
                EquipoEjecutorMiembro.usuario_id == user.id,
                EquipoEjecutorMiembro.activo.is_(True),
            )
            member_res = await self._session.execute(member_stmt)
            member = member_res.scalar_one_or_none()
            return isinstance(member, EquipoEjecutorMiembro) and member.activo

        return False

    async def require_process_access(
        self,
        user: Usuario | None,
        referencia_id: uuid.UUID,
    ) -> ProcesoCurricular:
        """Enforce access to a curricular process; raise HTTP 401/403/404 if denied."""
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Autenticación requerida para acceder al proceso",
                headers={"WWW-Authenticate": "Bearer"},
            )

        stmt = (
            select(ProcesoCurricular)
            .where(ProcesoCurricular.referencia_id == referencia_id)
            .options(
                selectinload(ProcesoCurricular.equipo_ejecutor).selectinload(
                    EquipoEjecutor.miembros
                )
            )
        )
        res = await self._session.execute(stmt)
        proceso = res.scalar_one_or_none()

        if proceso is None:
            proceso = await self._try_auto_heal_proceso(user, referencia_id)

        if proceso is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proceso curricular no encontrado",
            )

        if user.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value):
            return proceso

        if proceso.estado_scope != EstadoScopeProceso.ASIGNADO:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El proceso no está asignado a ningún equipo ejecutor",
            )

        if proceso.equipo_ejecutor and proceso.equipo_ejecutor.estado != EstadoEquipo.ACTIVO:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El equipo ejecutor asignado se encuentra inactivo",
            )

        if user.has_role(RolUsuario.LIDER_EQUIPO_EJECUTOR.value):
            if proceso.lider_id == user.id:
                return proceso
            if proceso.equipo_ejecutor and proceso.equipo_ejecutor.lider_id == user.id:
                return proceso
            if proceso.equipo_ejecutor_id:
                member_stmt = select(EquipoEjecutorMiembro).where(
                    EquipoEjecutorMiembro.equipo_id == proceso.equipo_ejecutor_id,
                    EquipoEjecutorMiembro.usuario_id == user.id,
                    EquipoEjecutorMiembro.activo.is_(True),
                )
                member_res = await self._session.execute(member_stmt)
                member = member_res.scalar_one_or_none()
                if isinstance(member, EquipoEjecutorMiembro) and member.activo:
                    return proceso
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes autorización sobre el equipo ejecutor de este proceso",
            )

        if user.has_role(RolUsuario.USUARIO_ADICIONAL.value):
            if not proceso.equipo_ejecutor_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Proceso sin equipo ejecutor asignado",
                )
            member_stmt = select(EquipoEjecutorMiembro).where(
                EquipoEjecutorMiembro.equipo_id == proceso.equipo_ejecutor_id,
                EquipoEjecutorMiembro.usuario_id == user.id,
                EquipoEjecutorMiembro.activo.is_(True),
            )
            member_res = await self._session.execute(member_stmt)
            member = member_res.scalar_one_or_none()
            if isinstance(member, EquipoEjecutorMiembro) and member.activo:
                return proceso
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No eres miembro activo del equipo ejecutor asignado",
            )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado al proceso curricular",
        )

    async def require_program_access(
        self,
        user: Usuario | None,
        programa_id: uuid.UUID,
    ) -> ProcesoCurricular | None:
        """Enforce access to a program via its process; raise HTTP 401/403/404 if denied."""
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Autenticación requerida para acceder al programa",
                headers={"WWW-Authenticate": "Bearer"},
            )

        stmt = select(ProcesoCurricular).where(ProcesoCurricular.programa_id == programa_id)
        res = await self._session.execute(stmt)
        proceso = res.scalar_one_or_none()
        if proceso is not None:
            return await self.require_process_access(user, proceso.referencia_id)

        if user.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value):
            prog = await self._session.get(ProgramaFormacion, programa_id)
            if prog is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Programa de formación no encontrado",
                )
            return None

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso no autorizado al programa de formación",
        )

    async def require_project_access(
        self,
        user: Usuario | None,
        proyecto_id: uuid.UUID,
    ) -> ProcesoCurricular | None:
        """Enforce access to a project via its process; raise HTTP 401/403/404 if denied."""
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Autenticación requerida para acceder al proyecto",
                headers={"WWW-Authenticate": "Bearer"},
            )

        stmt = select(ProcesoCurricular).where(ProcesoCurricular.proyecto_id == proyecto_id)
        res = await self._session.execute(stmt)
        proceso = res.scalar_one_or_none()
        if proceso is not None:
            return await self.require_process_access(user, proceso.referencia_id)

        proyecto = await self._session.get(ProyectoFormativo, proyecto_id)
        if proyecto is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proyecto formativo no encontrado",
            )
        return await self.require_program_access(user, proyecto.programa_id)

    async def require_planning_access(
        self,
        user: Usuario | None,
        planeacion_id: uuid.UUID,
    ) -> ProcesoCurricular | None:
        """Enforce access to a planning record; raise HTTP 401/403/404 if denied."""
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Autenticación requerida para acceder a la planeación",
                headers={"WWW-Authenticate": "Bearer"},
            )

        plan = await self._session.get(PlaneacionPedagogica, planeacion_id)
        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Planeación pedagógica no encontrada",
            )
        return await self.require_project_access(user, plan.proyecto_id)

    async def can_access_planning(self, user: Usuario, planeacion_id: uuid.UUID) -> bool:
        """Determine access to a planning record via its project and program process."""
        if user.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value):
            return True

        plan = await self._session.get(PlaneacionPedagogica, planeacion_id)
        if plan is None:
            return False
        return await self.can_access_project(user, plan.proyecto_id)

    async def can_access_project(self, user: Usuario, proyecto_id: uuid.UUID) -> bool:
        """Determine access to a project by matching its registered process."""
        if user.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value):
            return True

        stmt = select(ProcesoCurricular).where(ProcesoCurricular.proyecto_id == proyecto_id)
        res = await self._session.execute(stmt)
        proceso = res.scalar_one_or_none()
        if proceso is not None:
            return await self.can_access_process(user, proceso.referencia_id)

        proyecto = await self._session.get(ProyectoFormativo, proyecto_id)
        if proyecto is not None:
            return await self.can_access_program(user, proyecto.programa_id)
        return False

    async def can_access_program(self, user: Usuario, programa_id: uuid.UUID) -> bool:
        """Determine access to a program by matching its registered process."""
        if user.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value):
            return True

        stmt = select(ProcesoCurricular).where(ProcesoCurricular.programa_id == programa_id)
        res = await self._session.execute(stmt)
        proceso = res.scalar_one_or_none()
        if proceso is not None:
            return await self.can_access_process(user, proceso.referencia_id)
        return False

    async def get_allowed_referencias(
        self,
        user: Usuario,
        candidate_referencias: Sequence[uuid.UUID],
    ) -> set[uuid.UUID]:
        """Filter a collection of referencias returning only those permitted for the user."""
        if not candidate_referencias:
            return set()

        if user.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value):
            return set(candidate_referencias)

        if user.has_role(RolUsuario.LIDER_EQUIPO_EJECUTOR.value):
            stmt = (
                select(ProcesoCurricular.referencia_id)
                .join(EquipoEjecutor, ProcesoCurricular.equipo_ejecutor_id == EquipoEjecutor.id, isouter=True)
                .where(
                    ProcesoCurricular.referencia_id.in_(candidate_referencias),
                    ProcesoCurricular.estado_scope == EstadoScopeProceso.ASIGNADO,
                    EquipoEjecutor.estado == EstadoEquipo.ACTIVO,
                    (ProcesoCurricular.lider_id == user.id) | (EquipoEjecutor.lider_id == user.id),
                )
            )
            res = await self._session.execute(stmt)
            return set(res.scalars().all())

        if user.has_role(RolUsuario.USUARIO_ADICIONAL.value):
            stmt = (
                select(ProcesoCurricular.referencia_id)
                .join(
                    EquipoEjecutor,
                    ProcesoCurricular.equipo_ejecutor_id == EquipoEjecutor.id,
                )
                .join(
                    EquipoEjecutorMiembro,
                    ProcesoCurricular.equipo_ejecutor_id == EquipoEjecutorMiembro.equipo_id,
                )
                .where(
                    ProcesoCurricular.referencia_id.in_(candidate_referencias),
                    ProcesoCurricular.estado_scope == EstadoScopeProceso.ASIGNADO,
                    EquipoEjecutor.estado == EstadoEquipo.ACTIVO,
                    EquipoEjecutorMiembro.usuario_id == user.id,
                    EquipoEjecutorMiembro.activo.is_(True),
                )
            )
            res = await self._session.execute(stmt)
            return set(res.scalars().all())

        return set()

    async def ensure_proceso_for_referencia(
        self,
        referencia_id: uuid.UUID,
        creado_por: uuid.UUID | None = None,
        coordinacion_id: uuid.UUID | None = None,
        especialidad_id: uuid.UUID | None = None,
        equipo_ejecutor_id: uuid.UUID | None = None,
        lider_id: uuid.UUID | None = None,
        programa_id: uuid.UUID | None = None,
        proyecto_id: uuid.UUID | None = None,
    ) -> ProcesoCurricular:
        """Get or create the ProcesoCurricular anchor for a referencia_id."""
        stmt = select(ProcesoCurricular).where(ProcesoCurricular.referencia_id == referencia_id)
        res = await self._session.execute(stmt)
        proceso = res.scalar_one_or_none()
        if proceso is None:
            estado_scope = (
                EstadoScopeProceso.ASIGNADO
                if equipo_ejecutor_id and lider_id
                else EstadoScopeProceso.SIN_ASIGNAR
            )
            proceso = ProcesoCurricular(
                referencia_id=referencia_id,
                coordinacion_id=coordinacion_id,
                especialidad_id=especialidad_id,
                equipo_ejecutor_id=equipo_ejecutor_id,
                lider_id=lider_id,
                estado_scope=estado_scope,
                programa_id=programa_id,
                proyecto_id=proyecto_id,
                creado_por=creado_por,
            )
            self._session.add(proceso)
            await self._session.flush()
        else:
            if programa_id and not proceso.programa_id:
                proceso.programa_id = programa_id
            if proyecto_id and not proceso.proyecto_id:
                proceso.proyecto_id = proyecto_id
            if equipo_ejecutor_id and not proceso.equipo_ejecutor_id:
                proceso.equipo_ejecutor_id = equipo_ejecutor_id
                proceso.estado_scope = EstadoScopeProceso.ASIGNADO
            if lider_id and not proceso.lider_id:
                proceso.lider_id = lider_id
            await self._session.flush()
        return proceso
