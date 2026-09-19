"""Central access scope and data isolation service."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.shared.enums import EstadoScopeProceso, RolUsuario
from src.infrastructure.db.models.auth import Usuario
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

    async def can_access_process(self, user: Usuario, referencia_id: uuid.UUID) -> bool:
        """Determine whether the user is authorized to access the given process."""
        if user.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value):
            return True

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
            # Unregistered process in scope tracking; only admins can access
            return False

        if proceso.estado_scope != EstadoScopeProceso.ASIGNADO:
            # Unassigned processes are only accessible to admins
            return False

        if user.has_role(RolUsuario.LIDER_EQUIPO_EJECUTOR.value):
            # Strict isolation: only if the leader matches the process or team leader
            if proceso.lider_id == user.id:
                return True
            if proceso.equipo_ejecutor and proceso.equipo_ejecutor.lider_id == user.id:
                return True
            return False

        if user.has_role(RolUsuario.USUARIO_ADICIONAL.value):
            # Only if the user has an active membership in the assigned executing team
            if not proceso.equipo_ejecutor_id:
                return False
            member_stmt = select(EquipoEjecutorMiembro).where(
                EquipoEjecutorMiembro.equipo_id == proceso.equipo_ejecutor_id,
                EquipoEjecutorMiembro.usuario_id == user.id,
                EquipoEjecutorMiembro.activo.is_(True),
            )
            member_res = await self._session.execute(member_stmt)
            return member_res.scalar_one_or_none() is not None

        return False

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

        # Fallback: check via program
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
                    (ProcesoCurricular.lider_id == user.id) | (EquipoEjecutor.lider_id == user.id),
                )
            )
            res = await self._session.execute(stmt)
            return set(res.scalars().all())

        if user.has_role(RolUsuario.USUARIO_ADICIONAL.value):
            stmt = (
                select(ProcesoCurricular.referencia_id)
                .join(
                    EquipoEjecutorMiembro,
                    ProcesoCurricular.equipo_ejecutor_id == EquipoEjecutorMiembro.equipo_id,
                )
                .where(
                    ProcesoCurricular.referencia_id.in_(candidate_referencias),
                    ProcesoCurricular.estado_scope == EstadoScopeProceso.ASIGNADO,
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
        return proceso
