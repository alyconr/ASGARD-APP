"""SQLAlchemy repository for persisted draft sessions."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque
from src.infrastructure.db.models.drafts import BorradorSesion


class DraftRepository:
    """Read and write logical drafts backed by ``borradores_sesion``."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with a shared async session."""
        self._session = session

    async def get_by_block_reference(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
    ) -> BorradorSesion | None:
        """Return the draft identified by block type and reference id."""
        statement = (
            select(BorradorSesion)
            .where(BorradorSesion.tipo_bloque == tipo_bloque.value)
            .where(BorradorSesion.referencia_id == referencia_id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def add(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
        paso_actual: str,
        payload_json: dict[str, object],
        estado_borrador: EstadoBloque,
    ) -> BorradorSesion:
        """Create a new draft row without committing the transaction."""
        draft = BorradorSesion(
            tipo_bloque=tipo_bloque.value,
            referencia_id=referencia_id,
            paso_actual=paso_actual,
            payload_json=payload_json,
            estado_borrador=estado_borrador,
        )
        self._session.add(draft)
        await self._session.flush()
        return draft

    async def save(self, draft: BorradorSesion) -> BorradorSesion:
        """Flush pending changes for an existing draft row."""
        self._session.add(draft)
        await self._session.flush()
        return draft
