"""Institutional administrative dashboard query service."""

from __future__ import annotations

import math
import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.dto.admin_dashboard import (
    AdminDashboardFilterDTO,
    AdminDashboardResumenDTO,
    AdminProcesoItemDTO,
    CoordinacionSummaryDTO,
    EquipoSummaryDTO,
    EspecialidadSummaryDTO,
    LiderSummaryDTO,
    PaginatedAdminProcesosDTO,
    PlaneacionesCountDTO,
    ProgramaSummaryDTO,
    ProyectoSummaryDTO,
)
from src.domain.shared.enums import (
    EstadoBloque,
    EstadoEquipo,
    EstadoScopeProceso,
    EstadoUsuario,
    RolUsuario,
)
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.models.curriculum import ProgramaFormacion
from src.infrastructure.db.models.organizacion import (
    Coordinacion,
    EquipoEjecutor,
    Especialidad,
    ProcesoCurricular,
)
from src.infrastructure.db.models.planeacion import PlaneacionPedagogica
from src.infrastructure.db.models.proyecto import ProyectoFormativo


class AdminDashboardQueryService:
    """Read-only query service for hierarchical administrative supervision."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_resumen(
        self,
        actor: Usuario,
        filters: AdminDashboardFilterDTO | None = None,
    ) -> AdminDashboardResumenDTO:
        """Calculate real aggregations responding dynamically to applied scope filters."""
        f = filters or AdminDashboardFilterDTO()

        # Base filtered process IDs subquery
        proc_stmt = select(ProcesoCurricular.id, ProcesoCurricular.estado_scope, ProcesoCurricular.programa_id, ProcesoCurricular.proyecto_id)
        if f.coordinacion_id:
            proc_stmt = proc_stmt.where(ProcesoCurricular.coordinacion_id == f.coordinacion_id)
        if f.especialidad_id:
            proc_stmt = proc_stmt.where(ProcesoCurricular.especialidad_id == f.especialidad_id)
        if f.equipo_ejecutor_id:
            proc_stmt = proc_stmt.where(ProcesoCurricular.equipo_ejecutor_id == f.equipo_ejecutor_id)
        if f.lider_id:
            proc_stmt = proc_stmt.where(ProcesoCurricular.lider_id == f.lider_id)
        if f.solo_sin_asignar:
            proc_stmt = proc_stmt.where(ProcesoCurricular.estado_scope == EstadoScopeProceso.SIN_ASIGNAR)
        elif f.estado_scope:
            proc_stmt = proc_stmt.where(ProcesoCurricular.estado_scope == f.estado_scope)

        proc_res = (await self._session.execute(proc_stmt)).all()
        procesos_totales = len(proc_res)

        def get_row_field(row: Any, attr: str, idx: int) -> Any:
            return getattr(row, attr) if hasattr(row, attr) else row[idx]

        procesos_asignados = sum(
            1
            for p in proc_res
            if str(get_row_field(p, "estado_scope", 1)) == str(EstadoScopeProceso.ASIGNADO.value)
            or get_row_field(p, "estado_scope", 1) == EstadoScopeProceso.ASIGNADO
        )
        procesos_sin_asignar = procesos_totales - procesos_asignados

        programa_ids = [get_row_field(p, "programa_id", 2) for p in proc_res if get_row_field(p, "programa_id", 2) is not None]
        proyecto_ids = [get_row_field(p, "proyecto_id", 3) for p in proc_res if get_row_field(p, "proyecto_id", 3) is not None]

        # Program counts
        prog_borrador = 0
        prog_en_revision = 0
        prog_completo = 0
        if programa_ids:
            prog_stmt = select(ProgramaFormacion.estado, func.count(ProgramaFormacion.id)).where(
                ProgramaFormacion.id.in_(programa_ids)
            ).group_by(ProgramaFormacion.estado)
            for est, cnt in (await self._session.execute(prog_stmt)).all():
                st_val = getattr(est, "value", str(est))
                if st_val == EstadoBloque.BORRADOR.value:
                    prog_borrador += cnt
                elif st_val == EstadoBloque.EN_REVISION.value:
                    prog_en_revision += cnt
                elif st_val == EstadoBloque.COMPLETO.value:
                    prog_completo += cnt

        # Project counts
        proy_bloqueado = 0
        proy_borrador = 0
        proy_en_revision = 0
        proy_completo = 0
        if proyecto_ids:
            proy_stmt = select(ProyectoFormativo.estado, func.count(ProyectoFormativo.id)).where(
                ProyectoFormativo.id.in_(proyecto_ids)
            ).group_by(ProyectoFormativo.estado)
            for est, cnt in (await self._session.execute(proy_stmt)).all():
                st_val = getattr(est, "value", str(est))
                if st_val == "BLOQUEADO":
                    proy_bloqueado += cnt
                elif st_val == EstadoBloque.BORRADOR.value:
                    proy_borrador += cnt
                elif st_val == EstadoBloque.EN_REVISION.value:
                    proy_en_revision += cnt
                elif st_val == EstadoBloque.COMPLETO.value:
                    proy_completo += cnt

        # Planning counts
        plan_totales = 0
        plan_borrador = 0
        plan_completo = 0
        if proyecto_ids:
            plan_stmt = select(PlaneacionPedagogica.estado, func.count(PlaneacionPedagogica.id)).where(
                PlaneacionPedagogica.proyecto_id.in_(proyecto_ids)
            ).group_by(PlaneacionPedagogica.estado)
            for est, cnt in (await self._session.execute(plan_stmt)).all():
                plan_totales += cnt
                st_val = getattr(est, "value", str(est))
                if st_val == EstadoBloque.COMPLETO.value:
                    plan_completo += cnt
                else:
                    plan_borrador += cnt

        # Team counts within scope filter
        team_stmt = select(EquipoEjecutor.estado, func.count(EquipoEjecutor.id))
        if f.coordinacion_id:
            team_stmt = team_stmt.where(EquipoEjecutor.coordinacion_id == f.coordinacion_id)
        if f.especialidad_id:
            team_stmt = team_stmt.where(EquipoEjecutor.especialidad_id == f.especialidad_id)
        team_stmt = team_stmt.group_by(EquipoEjecutor.estado)

        eq_activos = 0
        eq_inactivos = 0
        for est, cnt in (await self._session.execute(team_stmt)).all():
            st_val = getattr(est, "value", str(est))
            if st_val == EstadoEquipo.ACTIVO.value:
                eq_activos += cnt
            else:
                eq_inactivos += cnt

        # Operational users (active leaders and active support members)
        user_stmt = select(Usuario).where(Usuario.estado == EstadoUsuario.ACTIVO)
        if f.coordinacion_id:
            user_stmt = user_stmt.where(Usuario.coordinacion_id == f.coordinacion_id)
        if f.especialidad_id:
            user_stmt = user_stmt.where(Usuario.especialidad_id == f.especialidad_id)
        users = (await self._session.execute(user_stmt)).scalars().all()

        lideres_activos = sum(1 for u in users if u.has_role(RolUsuario.LIDER_EQUIPO_EJECUTOR.value))
        apoyo_activos = sum(1 for u in users if u.has_role(RolUsuario.USUARIO_ADICIONAL.value))

        return AdminDashboardResumenDTO(
            procesos_totales=procesos_totales,
            procesos_asignados=procesos_asignados,
            procesos_sin_asignar=procesos_sin_asignar,
            programas_borrador=prog_borrador,
            programas_en_revision=prog_en_revision,
            programas_completo=prog_completo,
            proyectos_bloqueado=proy_bloqueado,
            proyectos_borrador=proy_borrador,
            proyectos_en_revision=proy_en_revision,
            proyectos_completo=proy_completo,
            planeaciones_totales=plan_totales,
            planeaciones_borrador=plan_borrador,
            planeaciones_completo=plan_completo,
            equipos_activos=eq_activos,
            equipos_inactivos=eq_inactivos,
            lideres_activos=lideres_activos,
            usuarios_apoyo_activos=apoyo_activos,
        )

    async def list_procesos_paginated(
        self,
        actor: Usuario,
        filters: AdminDashboardFilterDTO | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedAdminProcesosDTO:
        """List processes paginated server-side with eager joins and aggregated planning metrics."""
        f = filters or AdminDashboardFilterDTO()

        stmt = (
            select(ProcesoCurricular)
            .options(
                selectinload(ProcesoCurricular.coordinacion),
                selectinload(ProcesoCurricular.especialidad),
                selectinload(ProcesoCurricular.equipo_ejecutor),
                selectinload(ProcesoCurricular.lider),
                selectinload(ProcesoCurricular.programa),
                selectinload(ProcesoCurricular.proyecto),
            )
        )

        count_stmt = select(func.count(ProcesoCurricular.id))

        # Apply filters
        conditions = []
        if f.solo_sin_asignar:
            conditions.append(ProcesoCurricular.estado_scope == EstadoScopeProceso.SIN_ASIGNAR)
        elif f.estado_scope:
            conditions.append(ProcesoCurricular.estado_scope == f.estado_scope)

        if f.coordinacion_id:
            conditions.append(ProcesoCurricular.coordinacion_id == f.coordinacion_id)
        if f.especialidad_id:
            conditions.append(ProcesoCurricular.especialidad_id == f.especialidad_id)
        if f.equipo_ejecutor_id:
            conditions.append(ProcesoCurricular.equipo_ejecutor_id == f.equipo_ejecutor_id)
        if f.lider_id:
            conditions.append(ProcesoCurricular.lider_id == f.lider_id)
        if f.programa_id:
            conditions.append(ProcesoCurricular.programa_id == f.programa_id)
        if f.proyecto_id:
            conditions.append(ProcesoCurricular.proyecto_id == f.proyecto_id)
        if f.referencia_id:
            conditions.append(ProcesoCurricular.referencia_id == f.referencia_id)

        # Filters on linked entities
        if f.estado_programa:
            stmt = stmt.join(ProcesoCurricular.programa)
            count_stmt = count_stmt.join(ProcesoCurricular.programa)
            conditions.append(ProgramaFormacion.estado == f.estado_programa)

        if f.estado_proyecto:
            stmt = stmt.join(ProcesoCurricular.proyecto)
            count_stmt = count_stmt.join(ProcesoCurricular.proyecto)
            conditions.append(ProyectoFormativo.estado == f.estado_proyecto)

        if f.search and f.search.strip():
            term = f"%{f.search.strip()}%"
            search_cond = or_(
                ProcesoCurricular.referencia_id.cast(func.text).ilike(term),
                ProcesoCurricular.programa.has(ProgramaFormacion.nombre_programa.ilike(term)),
                ProcesoCurricular.programa.has(ProgramaFormacion.codigo_programa.ilike(term)),
                ProcesoCurricular.proyecto.has(ProyectoFormativo.nombre_proyecto.ilike(term)),
                ProcesoCurricular.equipo_ejecutor.has(EquipoEjecutor.nombre.ilike(term)),
                ProcesoCurricular.lider.has(Usuario.nombre.ilike(term)),
                ProcesoCurricular.lider.has(Usuario.apellido.ilike(term)),
                ProcesoCurricular.lider.has(Usuario.email.ilike(term)),
            )
            conditions.append(search_cond)

        for c in conditions:
            stmt = stmt.where(c)
            count_stmt = count_stmt.where(c)

        count_res = await self._session.execute(count_stmt)
        total = count_res.scalar_one_or_none() or 0
        total_pages = max(1, math.ceil(total / page_size))
        offset = (page - 1) * page_size

        stmt = stmt.order_by(ProcesoCurricular.fecha_actualizacion.desc()).offset(offset).limit(page_size)
        procesos = (await self._session.execute(stmt)).scalars().all()

        # Batch load plannings metrics for fetched processes
        proyecto_ids = [p.proyecto_id for p in procesos if p.proyecto_id is not None]
        planning_stats: dict[uuid.UUID, dict[str, int]] = {}
        if proyecto_ids:
            plan_stmt = (
                select(
                    PlaneacionPedagogica.proyecto_id,
                    PlaneacionPedagogica.estado,
                    func.count(PlaneacionPedagogica.id),
                )
                .where(PlaneacionPedagogica.proyecto_id.in_(proyecto_ids))
                .group_by(PlaneacionPedagogica.proyecto_id, PlaneacionPedagogica.estado)
            )
            for p_id, est, cnt in (await self._session.execute(plan_stmt)).all():
                if p_id not in planning_stats:
                    planning_stats[p_id] = {"total": 0, "borrador": 0, "completas": 0}
                planning_stats[p_id]["total"] += cnt
                st_val = getattr(est, "value", str(est))
                if st_val == EstadoBloque.COMPLETO.value:
                    planning_stats[p_id]["completas"] += cnt
                else:
                    planning_stats[p_id]["borrador"] += cnt

        # Build items
        items: list[AdminProcesoItemDTO] = []
        for p in procesos:
            coord_dto = (
                CoordinacionSummaryDTO(
                    id=str(p.coordinacion.id),
                    codigo=p.coordinacion.codigo,
                    nombre=p.coordinacion.nombre,
                )
                if p.coordinacion
                else None
            )

            esp_dto = (
                EspecialidadSummaryDTO(
                    id=str(p.especialidad.id),
                    codigo=p.especialidad.codigo,
                    nombre=p.especialidad.nombre,
                )
                if p.especialidad
                else None
            )

            prog_dto = (
                ProgramaSummaryDTO(
                    id=str(p.programa.id),
                    codigo=getattr(p.programa, "codigo_programa", ""),
                    nombre=getattr(p.programa, "nombre_programa", ""),
                    estado=getattr(p.programa.estado, "value", str(p.programa.estado)),
                )
                if p.programa
                else None
            )

            proy_dto = (
                ProyectoSummaryDTO(
                    id=str(p.proyecto.id),
                    codigo=getattr(p.proyecto, "codigo_proyecto", None),
                    nombre=getattr(p.proyecto, "nombre_proyecto", ""),
                    estado=getattr(p.proyecto.estado, "value", str(p.proyecto.estado)),
                )
                if p.proyecto
                else None
            )

            eq_dto = (
                EquipoSummaryDTO(
                    id=str(p.equipo_ejecutor.id),
                    nombre=p.equipo_ejecutor.nombre,
                    estado=getattr(p.equipo_ejecutor.estado, "value", str(p.equipo_ejecutor.estado)),
                )
                if p.equipo_ejecutor
                else None
            )

            lider_dto = (
                LiderSummaryDTO(
                    id=str(p.lider.id),
                    nombre=p.lider.nombre,
                    apellido=p.lider.apellido,
                    email=p.lider.email,
                )
                if p.lider
                else None
            )

            p_stats = planning_stats.get(p.proyecto_id or uuid.uuid4(), {"total": 0, "borrador": 0, "completas": 0})
            plan_dto = PlaneacionesCountDTO(
                total=p_stats["total"],
                borrador=p_stats["borrador"],
                completas=p_stats["completas"],
            )

            updated_val = getattr(p, "fecha_actualizacion", None) or getattr(p, "fecha_creacion", None)
            updated_str = updated_val.isoformat() if updated_val else ""

            items.append(
                AdminProcesoItemDTO(
                    referencia_id=str(p.referencia_id),
                    tipo_necesidad=getattr(p.tipo_necesidad, "value", str(p.tipo_necesidad)),
                    estado_scope=getattr(p.estado_scope, "value", str(p.estado_scope)),
                    coordinacion=coord_dto,
                    especialidad=esp_dto,
                    programa=prog_dto,
                    proyecto=proy_dto,
                    equipo=eq_dto,
                    lider=lider_dto,
                    planeaciones=plan_dto,
                    fecha_actualizacion=updated_str,
                )
            )

        return PaginatedAdminProcesosDTO(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_proceso_detail(
        self,
        actor: Usuario,
        referencia_id: uuid.UUID,
    ) -> AdminProcesoItemDTO | None:
        """Fetch single process hierarchical detail."""
        res = await self.list_procesos_paginated(
            actor=actor,
            filters=AdminDashboardFilterDTO(referencia_id=referencia_id),
            page=1,
            page_size=1,
        )
        for item in res.items:
            if item.referencia_id == str(referencia_id):
                return item
        return None
