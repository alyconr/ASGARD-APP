"""Persistence helpers for basic audit events."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.audit import EventoAuditoria


class AuditRepository:
    """Store minimal audit events using the current SQLAlchemy session."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with a shared async session."""
        self._session = session

    async def add_event(
        self,
        entidad: str,
        entidad_id: uuid.UUID,
        accion: str,
        detalle: dict[str, Any] | None = None,
        actor_usuario_id: uuid.UUID | None = None,
        referencia_id: uuid.UUID | None = None,
    ) -> EventoAuditoria:
        """Persist an audit event with optional actor and process references."""
        event = EventoAuditoria(
            entidad=entidad,
            entidad_id=entidad_id,
            accion=accion,
            detalle=detalle,
            actor_usuario_id=actor_usuario_id,
            referencia_id=referencia_id,
        )
        self._session.add(event)
        await self._session.flush()
        return event
