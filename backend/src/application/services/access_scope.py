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

        # Find active team where user is leader or active member
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
        else:
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

    async def can_start_curricular_process(
        self,
        user: Usuario,
        equipo_ejecutor_id: uuid.UUID,
        programa_id: uuid.UUID | None = None,
        codigo_programa: str | None = None,
    ) -> tuple[bool, str | None]:
        """Determine if user can start a curricular process inside the given team and program."""
        stmt = (
            select(EquipoEjecutor)
            .where(EquipoEjecutor.id == equipo_ejecutor_id)
            .options(
                selectinload(EquipoEjecutor.miembros),
                selectinload(EquipoEjecutor.programas_autorizados),
                selectinload(EquipoEjecutor.procesos),
            )
        )
        res = await self._session.execute(stmt)
        team = res.scalar_one_or_none()

        if team is None:
            return False, "Equipo ejecutor no encontrado"

        if team.estado != EstadoEquipo.ACTIVO:
            return False, "El equipo ejecutor se encuentra inactivo"

        is_leader = team.lider_id == user.id
        is_member = any(
            m.usuario_id == user.id and m.activo for m in team.miembros
        )
        if not (is_leader or is_member):
            return False, "Debes pertenecer al Equipo Ejecutor para iniciar este proceso curricular."

        if codigo_programa or programa_id:
            authorized_codes = {p.codigo_programa.strip().upper() for p in team.programas_autorizados if p.activo}
            authorized_pids = {p.programa_id for p in team.programas_autorizados if p.programa_id and p.activo}
            for proc in team.procesos:
                if proc.programa_id:
                    authorized_pids.add(proc.programa_id)

            code_match = codigo_programa and codigo_programa.strip().upper() in authorized_codes
            pid_match = programa_id and programa_id in authorized_pids
            if team.programas_autorizados and not (code_match or pid_match):
                return False, "El programa seleccionado no se encuentra habilitado para este Equipo Ejecutor."

        return True, None

    async def require_start_curricular_process(
        self,
        user: Usuario | None,
        equipo_ejecutor_id: uuid.UUID,
        programa_id: uuid.UUID | None = None,
        codigo_programa: str | None = None,
    ) -> EquipoEjecutor:
        """Enforce requirements to start a curricular process; raise HTTP 401/403/404."""
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Autenticación requerida para iniciar el proceso curricular",
                headers={"WWW-Authenticate": "Bearer"},
            )

        stmt = (
            select(EquipoEjecutor)
            .where(EquipoEjecutor.id == equipo_ejecutor_id)
            .options(
                selectinload(EquipoEjecutor.miembros),
                selectinload(EquipoEjecutor.programas_autorizados),
                selectinload(EquipoEjecutor.procesos),
            )
        )
        res = await self._session.execute(stmt)
        team = res.scalar_one_or_none()

        if team is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipo ejecutor no encontrado",
            )

        if team.estado != EstadoEquipo.ACTIVO:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "EXECUTOR_TEAM_INACTIVE",
                    "message": "El equipo ejecutor se encuentra inactivo",
                },
            )

        is_leader = team.lider_id == user.id
        is_member = any(
            m.usuario_id == user.id and m.activo for m in team.miembros
        )
        if not (is_leader or is_member):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "EXECUTOR_TEAM_MEMBERSHIP_REQUIRED",
                    "message": "Debes pertenecer al Equipo Ejecutor para iniciar este proceso curricular.",
                },
            )

        if codigo_programa or programa_id:
            authorized_codes = {p.codigo_programa.strip().upper() for p in team.programas_autorizados if p.activo}
            authorized_pids = {p.programa_id for p in team.programas_autorizados if p.programa_id and p.activo}
            for proc in team.procesos:
                if proc.programa_id:
                    authorized_pids.add(proc.programa_id)

            code_match = codigo_programa and codigo_programa.strip().upper() in authorized_codes
            pid_match = programa_id and programa_id in authorized_pids
            if team.programas_autorizados and not (code_match or pid_match):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "PROGRAM_NOT_AUTHORIZED_FOR_TEAM",
                        "message": "El programa seleccionado no se encuentra habilitado para este Equipo Ejecutor.",
                    },
                )

        return team

    async def validate_program_authorized_for_process(
        self,
        referencia_id: uuid.UUID,
        codigo_programa: str,
    ) -> bool:
        """Validate whether the program code is authorized for the process's executor team."""
        stmt = (
            select(ProcesoCurricular)
            .where(ProcesoCurricular.referencia_id == referencia_id)
            .options(
                selectinload(ProcesoCurricular.programa),
                selectinload(ProcesoCurricular.equipo_ejecutor).selectinload(
                    EquipoEjecutor.programas_autorizados
                ),
            )
        )
        res = await self._session.execute(stmt)
        proc = res.scalar_one_or_none()
        if proc is None:
            return True

        clean_code = codigo_programa.strip().upper()

        if proc.programa is not None and proc.programa.codigo_programa:
            if proc.programa.codigo_programa.strip().upper() != clean_code:
                return False

        if proc.equipo_ejecutor is not None and proc.equipo_ejecutor.programas_autorizados:
            authorized_codes = {
                p.codigo_programa.strip().upper()
                for p in proc.equipo_ejecutor.programas_autorizados
                if p.activo
            }
            if authorized_codes and clean_code not in authorized_codes:
                return False

        return True

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

        if proceso.estado_scope != EstadoScopeProceso.ASIGNADO:
            return False

        if proceso.equipo_ejecutor and proceso.equipo_ejecutor.estado != EstadoEquipo.ACTIVO:
            return False

        # Check if user is the team leader
        if proceso.lider_id == user.id:
            return True
        if proceso.equipo_ejecutor and proceso.equipo_ejecutor.lider_id == user.id:
            return True

        # Check if user is an active team member
        if (
            proceso.equipo_ejecutor
            and hasattr(proceso.equipo_ejecutor, "miembros")
            and isinstance(proceso.equipo_ejecutor.miembros, list)
            and proceso.equipo_ejecutor.miembros
        ):
            if any(
                m.usuario_id == user.id and getattr(m, "activo", False)
                for m in proceso.equipo_ejecutor.miembros
            ):
                return True

        if proceso.equipo_ejecutor_id:
            member_stmt = select(EquipoEjecutorMiembro).where(
                EquipoEjecutorMiembro.equipo_id == proceso.equipo_ejecutor_id,
                EquipoEjecutorMiembro.usuario_id == user.id,
                EquipoEjecutorMiembro.activo.is_(True),
            )
            member_res = await self._session.execute(member_stmt)
            res_obj = member_res.scalar_one_or_none()
            return isinstance(res_obj, EquipoEjecutorMiembro) and res_obj.activo

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

        if proceso.estado_scope != EstadoScopeProceso.ASIGNADO:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "PROCESS_NOT_ASSIGNED",
                    "message": "El proceso no está asignado a ningún equipo ejecutor",
                },
            )

        if proceso.equipo_ejecutor and proceso.equipo_ejecutor.estado != EstadoEquipo.ACTIVO:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "EXECUTOR_TEAM_INACTIVE",
                    "message": "El equipo ejecutor asignado se encuentra inactivo",
                },
            )

        # Leader has operational access
        if proceso.lider_id == user.id or (
            proceso.equipo_ejecutor and proceso.equipo_ejecutor.lider_id == user.id
        ):
            return proceso

        # Active member has operational access
        if (
            proceso.equipo_ejecutor
            and hasattr(proceso.equipo_ejecutor, "miembros")
            and isinstance(proceso.equipo_ejecutor.miembros, list)
            and proceso.equipo_ejecutor.miembros
        ):
            if any(m.usuario_id == user.id and getattr(m, "activo", False) for m in proceso.equipo_ejecutor.miembros):
                return proceso

        if proceso.equipo_ejecutor_id:
            member_stmt = select(EquipoEjecutorMiembro).where(
                EquipoEjecutorMiembro.equipo_id == proceso.equipo_ejecutor_id,
                EquipoEjecutorMiembro.usuario_id == user.id,
                EquipoEjecutorMiembro.activo.is_(True),
            )
            member_res = await self._session.execute(member_stmt)
            res_obj = member_res.scalar_one_or_none()
            if isinstance(res_obj, EquipoEjecutorMiembro) and res_obj.activo:
                return proceso

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "EXECUTOR_TEAM_MEMBERSHIP_REQUIRED",
                "message": "Debes pertenecer al Equipo Ejecutor para operar en este proceso curricular.",
            },
        )

    # Aliases for explicit domain semantics
    can_access_curricular_process = can_access_process
    require_access_curricular_process = require_process_access

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
        plan = await self._session.get(PlaneacionPedagogica, planeacion_id)
        if plan is None:
            return False
        return await self.can_access_project(user, plan.proyecto_id)

    async def can_access_project(self, user: Usuario, proyecto_id: uuid.UUID) -> bool:
        """Determine access to a project by matching its registered process."""
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
        """Filter a collection of referencias returning only those permitted for the user's teams."""
        if not candidate_referencias:
            return set()

        allowed: set[uuid.UUID] = set()

        query = (
            select(ProcesoCurricular.referencia_id)
            .join(EquipoEjecutor, ProcesoCurricular.equipo_ejecutor_id == EquipoEjecutor.id)
            .outerjoin(
                EquipoEjecutorMiembro,
                (ProcesoCurricular.equipo_ejecutor_id == EquipoEjecutorMiembro.equipo_id)
                & (EquipoEjecutorMiembro.usuario_id == user.id)
                & (EquipoEjecutorMiembro.activo.is_(True)),
            )
            .where(
                ProcesoCurricular.referencia_id.in_(candidate_referencias),
                ProcesoCurricular.estado_scope == EstadoScopeProceso.ASIGNADO,
                EquipoEjecutor.estado == EstadoEquipo.ACTIVO,
                (ProcesoCurricular.lider_id == user.id)
                | (EquipoEjecutor.lider_id == user.id)
                | (EquipoEjecutorMiembro.id.is_not(None)),
            )
        )
        res = await self._session.execute(query)
        allowed.update(res.scalars().all())

        return allowed

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


ExecutorTeamAuthorizationService = AccessScopeService

