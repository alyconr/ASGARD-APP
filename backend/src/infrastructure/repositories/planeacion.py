"""SQLAlchemy repository for persisted Pedagogical Planning entities."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.db.models.curriculum import ResultadoAprendizaje
from src.infrastructure.db.models.planeacion import (
    PlaneacionDocumentoConfig,
    PlaneacionPedagogica,
)
from src.infrastructure.db.models.proyecto import (
    ActividadProyecto,
    FaseProyecto,
    ProyectoFormativo,
)

_LIST_OPTIONS: tuple[Any, ...] = (
    selectinload(PlaneacionPedagogica.resultados).selectinload(
        ResultadoAprendizaje.competencia
    ),
    selectinload(PlaneacionPedagogica.conocimientos),
    selectinload(PlaneacionPedagogica.criterios),
    selectinload(PlaneacionPedagogica.proyecto).selectinload(
        ProyectoFormativo.programa
    ),
    selectinload(PlaneacionPedagogica.fase),
    selectinload(PlaneacionPedagogica.actividad),
)


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
            .options(*_LIST_OPTIONS)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_proyecto_and_actividad(
        self,
        proyecto_id: uuid.UUID,
        actividad_id: uuid.UUID,
    ) -> list[PlaneacionPedagogica]:
        """List all integrated plannings for a single project activity."""
        statement = (
            select(PlaneacionPedagogica)
            .where(PlaneacionPedagogica.proyecto_id == proyecto_id)
            .where(PlaneacionPedagogica.actividad_id == actividad_id)
            .options(*_LIST_OPTIONS)
            .order_by(PlaneacionPedagogica.fecha_actualizacion.desc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().unique().all())

    async def list_by_proyecto(
        self,
        proyecto_id: uuid.UUID,
    ) -> list[PlaneacionPedagogica]:
        """List all integrated planning summaries for a project."""
        statement = (
            select(PlaneacionPedagogica)
            .where(PlaneacionPedagogica.proyecto_id == proyecto_id)
            .options(
                selectinload(PlaneacionPedagogica.resultados).selectinload(
                    ResultadoAprendizaje.competencia
                ),
                selectinload(PlaneacionPedagogica.fase),
                selectinload(PlaneacionPedagogica.actividad),
            )
            .order_by(
                FaseProyecto.orden.asc().nulls_last(),
                ActividadProyecto.orden.asc().nulls_last(),
                PlaneacionPedagogica.fecha_actualizacion.desc(),
            )
            .outerjoin(
                FaseProyecto,
                FaseProyecto.id == PlaneacionPedagogica.fase_id,
            )
            .outerjoin(
                ActividadProyecto,
                ActividadProyecto.id == PlaneacionPedagogica.actividad_id,
            )
        )
        result = await self._session.execute(statement)
        return list(result.scalars().unique().all())

    async def list_full_by_proyecto(
        self,
        proyecto_id: uuid.UUID,
    ) -> list[PlaneacionPedagogica]:
        """List project planning rows with workbook relationships loaded."""
        statement = (
            select(PlaneacionPedagogica)
            .where(PlaneacionPedagogica.proyecto_id == proyecto_id)
            .options(*_LIST_OPTIONS)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().unique().all())

    async def get_document_config(
        self,
        proyecto_id: uuid.UUID,
    ) -> PlaneacionDocumentoConfig | None:
        """Return the shared official-document configuration."""
        statement = select(PlaneacionDocumentoConfig).where(
            PlaneacionDocumentoConfig.proyecto_id == proyecto_id
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def save_document_config(
        self,
        config: PlaneacionDocumentoConfig,
    ) -> PlaneacionDocumentoConfig:
        """Persist shared official-document configuration."""
        self._session.add(config)
        await self._session.flush()
        return config

    async def save(self, planeacion: PlaneacionPedagogica) -> PlaneacionPedagogica:
        """Add or flush a pedagogical planning entity to session."""
        self._session.add(planeacion)
        await self._session.flush()
        return planeacion

    async def delete(self, planeacion: PlaneacionPedagogica) -> None:
        """Delete a pedagogical planning entity from database."""
        await self._session.delete(planeacion)
        await self._session.flush()
