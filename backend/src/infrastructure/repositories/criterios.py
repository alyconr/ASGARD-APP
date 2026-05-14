"""SQLAlchemy repository for criteria persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.shared.enums import EstadoCampo
from src.infrastructure.db.models.curriculum import Competencia, CriterioEvaluacion


class CriterioRepository:
    """Read and write criteria items bound to a competence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_competencia(
        self,
        competencia_id: uuid.UUID,
        programa_id: uuid.UUID | None = None,
    ) -> Competencia | None:
        statement = select(Competencia).where(Competencia.id == competencia_id)
        if programa_id is not None:
            statement = statement.where(Competencia.programa_id == programa_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_competencia(
        self,
        competencia_id: uuid.UUID,
    ) -> list[CriterioEvaluacion]:
        statement = (
            select(CriterioEvaluacion)
            .where(CriterioEvaluacion.competencia_id == competencia_id)
            .order_by(
                CriterioEvaluacion.orden.asc(),
                CriterioEvaluacion.fecha_creacion.asc(),
            )
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id_for_competencia(
        self,
        criterio_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> CriterioEvaluacion | None:
        statement = (
            select(CriterioEvaluacion)
            .where(CriterioEvaluacion.id == criterio_id)
            .where(CriterioEvaluacion.competencia_id == competencia_id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def descripcion_exists(
        self,
        competencia_id: uuid.UUID,
        descripcion: str,
        exclude_criterio_id: uuid.UUID | None = None,
    ) -> bool:
        statement = (
            select(CriterioEvaluacion.id)
            .where(CriterioEvaluacion.competencia_id == competencia_id)
            .where(
                func.lower(CriterioEvaluacion.descripcion) == descripcion.lower(),
            )
        )
        if exclude_criterio_id is not None:
            statement = statement.where(
                CriterioEvaluacion.id != exclude_criterio_id,
            )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def add_criterio(
        self,
        competencia_id: uuid.UUID,
        descripcion: str,
        orden: int,
    ) -> CriterioEvaluacion:
        criterio = CriterioEvaluacion(
            competencia_id=competencia_id,
            resultado_id=None,
            descripcion=descripcion,
            orden=orden,
            estado=EstadoCampo.MANUAL,
        )
        self._session.add(criterio)
        await self._session.flush()
        return criterio

    async def save_criterio(
        self,
        criterio: CriterioEvaluacion,
    ) -> CriterioEvaluacion:
        self._session.add(criterio)
        await self._session.flush()
        return criterio

    async def delete_criterio(self, criterio: CriterioEvaluacion) -> None:
        await self._session.delete(criterio)
        await self._session.flush()
