"""Application service for draft autosave and recovery."""

from __future__ import annotations

import uuid
from typing import Protocol

from src.application.dto.drafts import DraftDTO, SaveDraftCommand
from src.domain.drafts.types import TipoBloqueBorrador, validate_draft_state
from src.domain.shared.enums import EstadoBloque
from src.infrastructure.db.models.drafts import BorradorSesion


class DraftNotFoundError(Exception):
    """Raised when no logical draft exists for the requested reference."""


class DraftRepositoryProtocol(Protocol):
    """Protocol used by the draft service to persist draft rows."""

    async def get_by_block_reference(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
    ) -> BorradorSesion | None:
        """Return the draft identified by block and reference id."""

    async def add(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
        paso_actual: str,
        payload_json: dict[str, object],
        estado_borrador: EstadoBloque,
    ) -> BorradorSesion:
        """Create a new draft row."""

    async def save(self, draft: BorradorSesion) -> BorradorSesion:
        """Persist modifications on an existing draft row."""


class AuditRepositoryProtocol(Protocol):
    """Protocol used by the draft service for minimal traceability."""

    async def add_event(
        self,
        entidad: str,
        entidad_id: uuid.UUID,
        accion: str,
        detalle: dict[str, object] | None = None,
    ) -> object:
        """Persist a basic audit event."""


class AsyncSessionProtocol(Protocol):
    """Subset of async session behavior required by the draft service."""

    async def commit(self) -> None:
        """Commit the current transaction."""

    async def refresh(self, instance: object) -> None:
        """Refresh the provided ORM instance."""


class DraftService:
    """Coordinate autosave and recovery of drafts for program and project."""

    def __init__(
        self,
        session: AsyncSessionProtocol,
        draft_repository: DraftRepositoryProtocol,
        audit_repository: AuditRepositoryProtocol,
    ) -> None:
        """Initialize the service with shared repositories and session."""
        self._session = session
        self._draft_repository = draft_repository
        self._audit_repository = audit_repository

    async def save_draft(self, command: SaveDraftCommand) -> DraftDTO:
        """Create or update a logical draft and record minimal audit data."""
        validate_draft_state(command.tipo_bloque, command.estado_borrador)
        existing_draft = await self._draft_repository.get_by_block_reference(
            command.tipo_bloque,
            command.referencia_id,
        )

        if existing_draft is None:
            draft = await self._draft_repository.add(
                tipo_bloque=command.tipo_bloque,
                referencia_id=command.referencia_id,
                paso_actual=command.paso_actual,
                payload_json=command.payload_json,
                estado_borrador=command.estado_borrador,
            )
            audit_action = "BORRADOR_CREADO"
        else:
            draft = existing_draft
            draft.paso_actual = command.paso_actual
            draft.payload_json = command.payload_json
            draft.estado_borrador = command.estado_borrador
            draft = await self._draft_repository.save(draft)
            audit_action = "BORRADOR_ACTUALIZADO"

        await self._audit_repository.add_event(
            entidad="BorradorSesion",
            entidad_id=draft.id,
            accion=audit_action,
            detalle={
                "tipo_bloque": command.tipo_bloque.value,
                "referencia_id": str(command.referencia_id),
                "paso_actual": command.paso_actual,
                "estado_borrador": command.estado_borrador.value,
            },
        )
        await self._session.commit()
        await self._session.refresh(draft)
        return _build_draft_dto(draft)

    async def get_draft(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
    ) -> DraftDTO:
        """Recover the draft identified by block type and reference id."""
        draft = await self._draft_repository.get_by_block_reference(
            tipo_bloque,
            referencia_id,
        )
        if draft is None:
            raise DraftNotFoundError("No existe un borrador para la referencia dada")
        return _build_draft_dto(draft)


def _build_draft_dto(draft: BorradorSesion) -> DraftDTO:
    """Convert a persisted draft row into an application DTO."""
    return DraftDTO(
        id=draft.id,
        tipo_bloque=TipoBloqueBorrador(draft.tipo_bloque),
        referencia_id=draft.referencia_id,
        paso_actual=draft.paso_actual,
        payload_json=draft.payload_json,
        estado_borrador=draft.estado_borrador,
        ultima_edicion=draft.ultima_edicion,
    )
