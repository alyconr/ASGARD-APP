"""Organization Administration Service for academic coordinations and specialties."""

from __future__ import annotations

import uuid
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.shared.enums import EstadoEquipo, EstadoUsuario
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.models.organizacion import (
    Coordinacion,
    EquipoEjecutor,
    Especialidad,
)
from src.infrastructure.repositories.audit import AuditRepository
from src.interfaces.http.schemas.organizacion import (
    CoordinacionCreate,
    CoordinacionResponse,
    CoordinacionUpdate,
    EspecialidadCreate,
    EspecialidadResponse,
    EspecialidadUpdate,
)


class OrganizationAdminService:
    """Service governing institutional academic coordinations and specialties."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)

    async def list_coordinaciones(self, solo_activas: bool = False) -> list[CoordinacionResponse]:
        """Return all coordinations with optional active-only filter."""
        stmt = select(Coordinacion).order_by(Coordinacion.codigo)
        if solo_activas:
            stmt = stmt.where(Coordinacion.activo.is_(True))
        res = await self.session.execute(stmt)
        return [CoordinacionResponse.model_validate(c) for c in res.scalars().all()]

    async def get_coordinacion(self, coordinacion_id: uuid.UUID) -> CoordinacionResponse:
        """Get single coordination detail."""
        coord = await self.session.get(Coordinacion, coordinacion_id)
        if coord is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coordinación no encontrada")
        return CoordinacionResponse.model_validate(coord)

    async def create_coordinacion(self, actor: Usuario, payload: CoordinacionCreate) -> CoordinacionResponse:
        """Create a new coordination ensuring unique functional code."""
        code_clean = payload.codigo.strip().upper()
        existing = await self.session.execute(select(Coordinacion).where(Coordinacion.codigo == code_clean))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una coordinación con el código '{code_clean}'",
            )

        coord = Coordinacion(
            codigo=code_clean,
            nombre=payload.nombre.strip(),
            descripcion=payload.descripcion.strip() if payload.descripcion else None,
            activo=True,
        )
        self.session.add(coord)
        await self.session.flush()

        await self.audit_repo.add_event(
            entidad="Coordinacion",
            entidad_id=coord.id,
            accion="COORDINATION_CREATED",
            detalle={"creado_por": str(actor.id), "codigo": coord.codigo, "nombre": coord.nombre},
        )
        await self.session.commit()
        await self.session.refresh(coord)
        return CoordinacionResponse.model_validate(coord)

    async def update_coordinacion(
        self,
        actor: Usuario,
        coordinacion_id: uuid.UUID,
        payload: CoordinacionUpdate,
    ) -> CoordinacionResponse:
        """Update coordination details or status validating active dependencies before deactivation."""
        coord = await self.session.get(Coordinacion, coordinacion_id)
        if coord is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coordinación no encontrada")

        status_changed = False
        if payload.activo is not None and payload.activo != coord.activo:
            if not payload.activo:
                # Validate active specialties
                active_esp_stmt = select(func.count(Especialidad.id)).where(
                    Especialidad.coordinacion_id == coordinacion_id,
                    Especialidad.activo.is_(True),
                )
                esp_count = (await self.session.execute(active_esp_stmt)).scalar_one() or 0
                if esp_count > 0:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"No se puede desactivar la coordinación porque tiene {esp_count} especialidad(es) activa(s)",
                    )

                # Validate active executing teams
                active_teams_stmt = select(func.count(EquipoEjecutor.id)).where(
                    EquipoEjecutor.coordinacion_id == coordinacion_id,
                    EquipoEjecutor.estado == EstadoEquipo.ACTIVO,
                )
                teams_count = (await self.session.execute(active_teams_stmt)).scalar_one() or 0
                if teams_count > 0:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"No se puede desactivar la coordinación porque tiene {teams_count} equipo(s) ejecutor(es) activo(s)",
                    )

                # Validate active users
                active_users_stmt = select(func.count(Usuario.id)).where(
                    Usuario.coordinacion_id == coordinacion_id,
                    Usuario.estado == EstadoUsuario.ACTIVO,
                )
                users_count = (await self.session.execute(active_users_stmt)).scalar_one() or 0
                if users_count > 0:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"No se puede desactivar la coordinación porque tiene {users_count} usuario(s) activo(s) asociado(s)",
                    )

            coord.activo = payload.activo
            status_changed = True

        if payload.nombre is not None:
            coord.nombre = payload.nombre.strip()
        if payload.descripcion is not None:
            coord.descripcion = payload.descripcion.strip() if payload.descripcion else None

        await self.audit_repo.add_event(
            entidad="Coordinacion",
            entidad_id=coord.id,
            accion="COORDINATION_STATUS_CHANGED" if status_changed else "COORDINATION_UPDATED",
            detalle={"modificado_por": str(actor.id), "activo": coord.activo, "nombre": coord.nombre},
        )
        await self.session.commit()
        await self.session.refresh(coord)
        return CoordinacionResponse.model_validate(coord)

    async def list_especialidades_by_coordinacion(
        self,
        coordinacion_id: uuid.UUID,
        solo_activas: bool = False,
    ) -> list[EspecialidadResponse]:
        """List specialties belonging to a coordination."""
        stmt = (
            select(Especialidad)
            .where(Especialidad.coordinacion_id == coordinacion_id)
            .order_by(Especialidad.codigo)
        )
        if solo_activas:
            stmt = stmt.where(Especialidad.activo.is_(True))
        res = await self.session.execute(stmt)
        return [EspecialidadResponse.model_validate(e) for e in res.scalars().all()]

    async def get_especialidad(self, especialidad_id: uuid.UUID) -> EspecialidadResponse:
        """Get single specialty detail."""
        esp = await self.session.get(Especialidad, especialidad_id)
        if esp is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Especialidad no encontrada")
        return EspecialidadResponse.model_validate(esp)

    async def create_especialidad(
        self,
        actor: Usuario,
        coordinacion_id: uuid.UUID,
        payload: EspecialidadCreate,
    ) -> EspecialidadResponse:
        """Create a new specialty under an active coordination."""
        coord = await self.session.get(Coordinacion, coordinacion_id)
        if coord is None or not coord.activo:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La coordinación indicada no existe o se encuentra inactiva",
            )

        code_clean = payload.codigo.strip().upper()
        existing = await self.session.execute(select(Especialidad).where(Especialidad.codigo == code_clean))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una especialidad con el código '{code_clean}'",
            )

        esp = Especialidad(
            coordinacion_id=coordinacion_id,
            codigo=code_clean,
            nombre=payload.nombre.strip(),
            activo=True,
        )
        self.session.add(esp)
        await self.session.flush()

        await self.audit_repo.add_event(
            entidad="Especialidad",
            entidad_id=esp.id,
            accion="SPECIALTY_CREATED",
            detalle={"creado_por": str(actor.id), "codigo": esp.codigo, "coordinacion_id": str(coordinacion_id)},
        )
        await self.session.commit()
        await self.session.refresh(esp)
        return EspecialidadResponse.model_validate(esp)

    async def update_especialidad(
        self,
        actor: Usuario,
        especialidad_id: uuid.UUID,
        payload: EspecialidadUpdate,
    ) -> EspecialidadResponse:
        """Update specialty details or status enforcing dependency checks before deactivation."""
        esp = await self.session.get(Especialidad, especialidad_id)
        if esp is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Especialidad no encontrada")

        status_changed = False
        if payload.activo is not None and payload.activo != esp.activo:
            if not payload.activo:
                # Validate active executing teams
                active_teams_stmt = select(func.count(EquipoEjecutor.id)).where(
                    EquipoEjecutor.especialidad_id == especialidad_id,
                    EquipoEjecutor.estado == EstadoEquipo.ACTIVO,
                )
                teams_count = (await self.session.execute(active_teams_stmt)).scalar_one() or 0
                if teams_count > 0:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"No se puede desactivar la especialidad porque tiene {teams_count} equipo(s) ejecutor(es) activo(s) asociado(s)",
                    )

                # Validate active users
                active_users_stmt = select(func.count(Usuario.id)).where(
                    Usuario.especialidad_id == especialidad_id,
                    Usuario.estado == EstadoUsuario.ACTIVO,
                )
                users_count = (await self.session.execute(active_users_stmt)).scalar_one() or 0
                if users_count > 0:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"No se puede desactivar la especialidad porque tiene {users_count} usuario(s) activo(s) asociado(s)",
                    )

            esp.activo = payload.activo
            status_changed = True

        if payload.nombre is not None:
            esp.nombre = payload.nombre.strip()

        await self.audit_repo.add_event(
            entidad="Especialidad",
            entidad_id=esp.id,
            accion="SPECIALTY_STATUS_CHANGED" if status_changed else "SPECIALTY_UPDATED",
            detalle={"modificado_por": str(actor.id), "activo": esp.activo, "nombre": esp.nombre},
        )
        await self.session.commit()
        await self.session.refresh(esp)
        return EspecialidadResponse.model_validate(esp)
