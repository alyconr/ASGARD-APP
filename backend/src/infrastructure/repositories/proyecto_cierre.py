"""Repository helpers for project completion and closing."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.db.models.proyecto import (
    FaseProyecto,
    ProyectoFormativo,
)


class ProyectoCierreRepository:
    """Load and persist the project aggregate needed by the completion service."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with a shared async session."""
        self._session = session

    async def get_project_with_structure(
        self,
        proyecto_id: uuid.UUID,
    ) -> ProyectoFormativo | None:
        """Return a project with its phases and activities loaded."""
        statement = (
            select(ProyectoFormativo)
            .options(
                selectinload(ProyectoFormativo.programa),
                selectinload(ProyectoFormativo.fases).selectinload(
                    FaseProyecto.actividades,
                ),
            )
            .where(ProyectoFormativo.id == proyecto_id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def save_project(self, proyecto: ProyectoFormativo) -> ProyectoFormativo:
        """Flush pending changes on a project row."""
        self._session.add(proyecto)
        await self._session.flush()
        return proyecto
