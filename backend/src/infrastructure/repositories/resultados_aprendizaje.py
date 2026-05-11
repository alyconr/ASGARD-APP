"""SQLAlchemy repository for learning outcome persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.shared.enums import EstadoCampo
from src.infrastructure.db.models.curriculum import Competencia, ResultadoAprendizaje


class ResultadoAprendizajeRepository:
    """Read and write learning outcomes (resultados de aprendizaje)."""

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
    ) -> list[ResultadoAprendizaje]:
        """Return all learning outcomes linked to the given competence."""
        statement = (
            select(ResultadoAprendizaje)
            .where(ResultadoAprendizaje.competencia_id == competencia_id)
            .order_by(
                ResultadoAprendizaje.orden.asc(),
                ResultadoAprendizaje.fecha_creacion.asc(),
            )
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id_for_competencia(
        self,
        resultado_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> ResultadoAprendizaje | None:
        """Return a learning outcome only when it belongs to the given competence."""
        statement = (
            select(ResultadoAprendizaje)
            .where(ResultadoAprendizaje.id == resultado_id)
            .where(ResultadoAprendizaje.competencia_id == competencia_id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def descripcion_exists(
        self,
        competencia_id: uuid.UUID,
        descripcion: str,
        exclude_resultado_id: uuid.UUID | None = None,
    ) -> bool:
        """Check duplicate learning outcome description inside a competence."""
        statement = (
            select(ResultadoAprendizaje.id)
            .where(ResultadoAprendizaje.competencia_id == competencia_id)
            .where(
                func.lower(ResultadoAprendizaje.descripcion) == descripcion.lower(),
            )
        )
        if exclude_resultado_id is not None:
            statement = statement.where(ResultadoAprendizaje.id != exclude_resultado_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def add_resultado(
        self,
        competencia_id: uuid.UUID,
        descripcion: str,
        orden: int,
        codigo_resultado: str | None = None,
    ) -> ResultadoAprendizaje:
        """Create a learning outcome for one competence."""
        resultado = ResultadoAprendizaje(
            competencia_id=competencia_id,
            descripcion=descripcion,
            codigo_resultado=codigo_resultado,
            orden=orden,
            estado=EstadoCampo.MANUAL,
        )
        self._session.add(resultado)
        await self._session.flush()
        return resultado

    async def save_resultado(
        self,
        resultado: ResultadoAprendizaje,
    ) -> ResultadoAprendizaje:
        """Flush pending changes to a learning outcome."""
        self._session.add(resultado)
        await self._session.flush()
        return resultado

    async def delete_resultado(self, resultado: ResultadoAprendizaje) -> None:
        """Delete a learning outcome row."""
        await self._session.delete(resultado)
        await self._session.flush()
