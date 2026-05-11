"""Repository for Excel curricular pending assignment reconciliation."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.shared.enums import (
    EstadoCampo,
    TipoConocimiento,
)
from src.infrastructure.db.models.curriculum import (
    Competencia,
    Conocimiento,
    CriterioEvaluacion,
    ElementoCurricularPendiente,
    ResultadoAprendizaje,
)


class PendientesCurricularesRepository:
    """Read and write pending curricular assignment rows."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with a shared async session."""
        self._session = session

    async def list_by_reference(
        self,
        referencia_id: uuid.UUID,
    ) -> list[ElementoCurricularPendiente]:
        """Return all pending rows for the wizard reference."""
        statement = (
            select(ElementoCurricularPendiente)
            .where(ElementoCurricularPendiente.referencia_id == referencia_id)
            .order_by(
                ElementoCurricularPendiente.estado.asc(),
                ElementoCurricularPendiente.orden.asc(),
                ElementoCurricularPendiente.fecha_creacion.asc(),
            )
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(
        self,
        referencia_id: uuid.UUID,
        pendiente_id: uuid.UUID,
    ) -> ElementoCurricularPendiente | None:
        """Return one pending row scoped to a wizard reference."""
        statement = (
            select(ElementoCurricularPendiente)
            .where(ElementoCurricularPendiente.referencia_id == referencia_id)
            .where(ElementoCurricularPendiente.id == pendiente_id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_competencia(
        self,
        competencia_id: uuid.UUID,
        programa_id: uuid.UUID,
    ) -> Competencia | None:
        """Return a competence only if it belongs to the current program."""
        statement = (
            select(Competencia)
            .where(Competencia.id == competencia_id)
            .where(Competencia.programa_id == programa_id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_resultado(
        self,
        resultado_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> ResultadoAprendizaje | None:
        """Return a learning outcome scoped to a competence."""
        statement = (
            select(ResultadoAprendizaje)
            .where(ResultadoAprendizaje.id == resultado_id)
            .where(ResultadoAprendizaje.competencia_id == competencia_id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def conocimiento_exists(
        self,
        *,
        competencia_id: uuid.UUID,
        tipo: TipoConocimiento,
        descripcion: str,
        resultado_id: uuid.UUID | None,
    ) -> bool:
        """Return whether a final knowledge item already exists."""
        statement = (
            select(Conocimiento.id)
            .where(Conocimiento.competencia_id == competencia_id)
            .where(Conocimiento.tipo == tipo)
            .where(func.lower(Conocimiento.descripcion) == descripcion.lower())
        )
        if resultado_id is None:
            statement = statement.where(Conocimiento.resultado_id.is_(None))
        else:
            statement = statement.where(Conocimiento.resultado_id == resultado_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def criterio_exists(
        self,
        *,
        competencia_id: uuid.UUID,
        descripcion: str,
        resultado_id: uuid.UUID | None,
    ) -> bool:
        """Return whether a final criterion already exists."""
        statement = (
            select(CriterioEvaluacion.id)
            .where(CriterioEvaluacion.competencia_id == competencia_id)
            .where(func.lower(CriterioEvaluacion.descripcion) == descripcion.lower())
        )
        if resultado_id is None:
            statement = statement.where(CriterioEvaluacion.resultado_id.is_(None))
        else:
            statement = statement.where(CriterioEvaluacion.resultado_id == resultado_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def add_conocimiento(
        self,
        *,
        competencia_id: uuid.UUID,
        resultado_id: uuid.UUID | None,
        tipo: TipoConocimiento,
        descripcion: str,
        orden: int | None,
    ) -> Conocimiento:
        """Create a final knowledge item from a pending row."""
        conocimiento = Conocimiento(
            competencia_id=competencia_id,
            resultado_id=resultado_id,
            tipo=tipo,
            descripcion=descripcion,
            orden=orden,
            estado=EstadoCampo.VALIDADO,
        )
        self._session.add(conocimiento)
        await self._session.flush()
        return conocimiento

    async def add_criterio(
        self,
        *,
        competencia_id: uuid.UUID,
        resultado_id: uuid.UUID | None,
        descripcion: str,
        orden: int | None,
    ) -> CriterioEvaluacion:
        """Create a final criterion from a pending row."""
        criterio = CriterioEvaluacion(
            competencia_id=competencia_id,
            resultado_id=resultado_id,
            descripcion=descripcion,
            orden=orden,
            estado=EstadoCampo.VALIDADO,
        )
        self._session.add(criterio)
        await self._session.flush()
        return criterio

    async def save(
        self,
        pendiente: ElementoCurricularPendiente,
    ) -> ElementoCurricularPendiente:
        """Persist changes to a pending row."""
        self._session.add(pendiente)
        await self._session.flush()
        return pendiente
