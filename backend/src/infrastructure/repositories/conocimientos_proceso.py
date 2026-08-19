"""SQLAlchemy repository for PROCESO knowledge persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.shared.enums import EstadoCampo, TipoConocimiento
from src.infrastructure.db.models.curriculum import Competencia, Conocimiento


class ConocimientoProcesoRepository:
    """Read and write knowledge items constrained to type PROCESO."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with a shared async session."""
        self._session = session

    async def get_competencia(
        self,
        competencia_id: uuid.UUID,
        programa_id: uuid.UUID | None = None,
    ) -> Competencia | None:
        """Return a competence by primary key, optionally verifying its program."""
        statement = select(Competencia).where(Competencia.id == competencia_id)
        if programa_id is not None:
            statement = statement.where(Competencia.programa_id == programa_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_competencia(
        self,
        competencia_id: uuid.UUID,
    ) -> list[Conocimiento]:
        """Return PROCESO knowledge items linked to the given competence."""
        statement = (
            select(Conocimiento)
            .where(Conocimiento.competencia_id == competencia_id)
            .where(Conocimiento.tipo == TipoConocimiento.PROCESO)
            .order_by(Conocimiento.orden.asc(), Conocimiento.fecha_creacion.asc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id_for_competencia(
        self,
        conocimiento_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> Conocimiento | None:
        """Return a PROCESO knowledge item only when it belongs to the competence."""
        statement = (
            select(Conocimiento)
            .where(Conocimiento.id == conocimiento_id)
            .where(Conocimiento.competencia_id == competencia_id)
            .where(Conocimiento.tipo == TipoConocimiento.PROCESO)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def descripcion_exists(
        self,
        competencia_id: uuid.UUID,
        descripcion: str,
        exclude_conocimiento_id: uuid.UUID | None = None,
    ) -> bool:
        """Check duplicate PROCESO description inside a competence."""
        statement = (
            select(Conocimiento.id)
            .where(Conocimiento.competencia_id == competencia_id)
            .where(Conocimiento.tipo == TipoConocimiento.PROCESO)
            .where(func.lower(Conocimiento.descripcion) == descripcion.lower())
        )
        if exclude_conocimiento_id is not None:
            statement = statement.where(Conocimiento.id != exclude_conocimiento_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def add_conocimiento(
        self,
        competencia_id: uuid.UUID,
        descripcion: str,
        orden: int,
    ) -> Conocimiento:
        """Create a PROCESO knowledge item for one competence."""
        conocimiento = Conocimiento(
            competencia_id=competencia_id,
            resultado_id=None,
            tipo=TipoConocimiento.PROCESO,
            descripcion=descripcion,
            orden=orden,
            estado=EstadoCampo.MANUAL,
        )
        self._session.add(conocimiento)
        await self._session.flush()
        return conocimiento

    async def save_conocimiento(self, conocimiento: Conocimiento) -> Conocimiento:
        """Flush pending changes to a PROCESO knowledge item."""
        self._session.add(conocimiento)
        await self._session.flush()
        return conocimiento

    async def delete_conocimiento(self, conocimiento: Conocimiento) -> None:
        """Delete a PROCESO knowledge row."""
        await self._session.delete(conocimiento)
        await self._session.flush()
