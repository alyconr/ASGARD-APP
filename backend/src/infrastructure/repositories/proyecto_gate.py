"""Repository helpers for TASK-15 project availability gate."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.curriculum import ProgramaFormacion


class ProyectoGateRepository:
    """Read the program state needed to gate project access."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with a shared async session."""
        self._session = session

    async def get_programa(self, programa_id: uuid.UUID) -> ProgramaFormacion | None:
        """Return a program by id."""
        statement = select(ProgramaFormacion).where(ProgramaFormacion.id == programa_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()
