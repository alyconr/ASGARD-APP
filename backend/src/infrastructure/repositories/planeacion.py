"""SQLAlchemy repository for persisted Pedagogical Planning entities."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.db.models.planeacion import PlaneacionPedagogica


class PlaneacionPedagogicaRepository:
    """Read and write operations for PlaneacionPedagogica ORM models."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with shared async session."""
        self._session = session

    async def get_by_id(self, planeacion_id: uuid.UUID) -> PlaneacionPedagogica | None:
        """Retrieve a pedagogical planning by its primary key with children loaded."""
        statement = (
            select(PlaneacionPedagogica)
            .where(PlaneacionPedagogica.id == planeacion_id)
            .options(
                selectinload(PlaneacionPedagogica.resultados),
                selectinload(PlaneacionPedagogica.conocimientos),
                selectinload(PlaneacionPedagogica.criterios),
                selectinload(PlaneacionPedagogica.competencia),
                selectinload(PlaneacionPedagogica.proyecto),
                selectinload(PlaneacionPedagogica.fase),
                selectinload(PlaneacionPedagogica.actividad),
            )
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_proyecto_and_competencia(
        self,
        proyecto_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> PlaneacionPedagogica | None:
        """Retrieve a pedagogical planning by project and competence logical key."""
        statement = (
            select(PlaneacionPedagogica)
            .where(PlaneacionPedagogica.proyecto_id == proyecto_id)
            .where(PlaneacionPedagogica.competencia_id == competencia_id)
            .options(
                selectinload(PlaneacionPedagogica.resultados),
                selectinload(PlaneacionPedagogica.conocimientos),
                selectinload(PlaneacionPedagogica.criterios),
                selectinload(PlaneacionPedagogica.competencia),
                selectinload(PlaneacionPedagogica.fase),
                selectinload(PlaneacionPedagogica.actividad),
            )
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_proyecto(
        self,
        proyecto_id: uuid.UUID,
    ) -> list[PlaneacionPedagogica]:
        """List all pedagogical planning summaries for a project."""
        statement = (
            select(PlaneacionPedagogica)
            .where(PlaneacionPedagogica.proyecto_id == proyecto_id)
            .options(
                selectinload(PlaneacionPedagogica.competencia),
            )
            .order_by(PlaneacionPedagogica.fecha_actualizacion.desc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def save(self, planeacion: PlaneacionPedagogica) -> PlaneacionPedagogica:
        """Add or flush a pedagogical planning entity to session."""
        self._session.add(planeacion)
        await self._session.flush()
        return planeacion

    async def delete(self, planeacion: PlaneacionPedagogica) -> None:
        """Delete a pedagogical planning entity from database."""
        await self._session.delete(planeacion)
        await self._session.flush()
