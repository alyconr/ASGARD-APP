"""Repository helpers for TASK-14 program completion and closing."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.db.models.curriculum import (
    Competencia,
    ProgramaFormacion,
)


class ProgramaCierreRepository:
    """Load and persist the program aggregate needed by the completion service."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with a shared async session."""
        self._session = session

    async def get_programa_with_curriculum(
        self,
        programa_id: uuid.UUID,
    ) -> ProgramaFormacion | None:
        """Return a program with its competence-centered curriculum loaded."""
        statement = (
            select(ProgramaFormacion)
            .options(
                selectinload(ProgramaFormacion.competencias).selectinload(
                    Competencia.resultados,
                ),
                selectinload(ProgramaFormacion.competencias).selectinload(
                    Competencia.conocimientos,
                ),
                selectinload(ProgramaFormacion.competencias).selectinload(
                    Competencia.criterios,
                ),
            )
            .where(ProgramaFormacion.id == programa_id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def save_programa(self, programa: ProgramaFormacion) -> ProgramaFormacion:
        """Flush pending changes on a program row."""
        self._session.add(programa)
        await self._session.flush()
        return programa
