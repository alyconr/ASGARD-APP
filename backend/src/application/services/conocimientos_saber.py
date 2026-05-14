"""Application service for TASK-10 SABER knowledge CRUD."""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Protocol

from src.application.dto.conocimientos_saber import (
    ConocimientoSaberDeleteDTO,
    ConocimientoSaberDTO,
    ConocimientoSaberListDTO,
    ConocimientoSaberPayloadDTO,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import TipoConocimiento
from src.infrastructure.db.models.curriculum import Competencia, Conocimiento
from src.infrastructure.db.models.drafts import BorradorSesion


class ConocimientoSaberError(Exception):
    """Base exception for SABER knowledge use-case errors."""


class ConocimientoSaberDraftNotFoundError(ConocimientoSaberError):
    """Raised when no program draft exists for a reference."""


class ConocimientoSaberCompetenciaNotFoundError(ConocimientoSaberError):
    """Raised when the competence is missing or not tied to the program."""


class ConocimientoSaberValidationError(ConocimientoSaberError):
    """Raised when user input is not valid."""


class ConocimientoSaberDuplicateError(ConocimientoSaberError):
    """Raised when a SABER description already exists in the competence."""


class ConocimientoSaberNotFoundError(ConocimientoSaberError):
    """Raised when a SABER knowledge item is missing."""


class ConocimientoSaberRepositoryProtocol(Protocol):
    """Repository behavior required by the SABER knowledge service."""

    async def get_competencia(
        self,
        competencia_id: uuid.UUID,
        programa_id: uuid.UUID | None = None,
    ) -> Competencia | None:
        """Return a competence by id."""

    async def list_by_competencia(
        self,
        competencia_id: uuid.UUID,
    ) -> list[Conocimiento]:
        """List competence SABER knowledge items."""

    async def get_by_id_for_competencia(
        self,
        conocimiento_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> Conocimiento | None:
        """Return a SABER knowledge item for a competence."""

    async def descripcion_exists(
        self,
        competencia_id: uuid.UUID,
        descripcion: str,
        exclude_conocimiento_id: uuid.UUID | None = None,
    ) -> bool:
        """Return whether a SABER description exists in a competence."""

    async def add_conocimiento(
        self,
        competencia_id: uuid.UUID,
        descripcion: str,
        orden: int,
    ) -> Conocimiento:
        """Create a SABER knowledge item."""

    async def save_conocimiento(self, conocimiento: Conocimiento) -> Conocimiento:
        """Persist SABER knowledge changes."""

    async def delete_conocimiento(self, conocimiento: Conocimiento) -> None:
        """Delete a SABER knowledge item."""


class DraftRepositoryProtocol(Protocol):
    """Draft repository behavior required by this service."""

    async def get_by_block_reference(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
    ) -> BorradorSesion | None:
        """Return a draft by logical identity."""

    async def save(self, draft: BorradorSesion) -> BorradorSesion:
        """Persist draft changes."""


class AuditRepositoryProtocol(Protocol):
    """Audit behavior required by this service."""

    async def add_event(
        self,
        entidad: str,
        entidad_id: uuid.UUID,
        accion: str,
        detalle: dict[str, object] | None = None,
    ) -> object:
        """Persist a basic audit event."""


class AsyncSessionProtocol(Protocol):
    """Subset of async session behavior required by this service."""

    async def commit(self) -> None:
        """Commit pending changes."""

    async def refresh(self, instance: object) -> None:
        """Refresh an ORM instance."""


class ProgramaConocimientoSaberService:
    """Coordinate SABER knowledge CRUD within the active program draft."""

    def __init__(
        self,
        session: AsyncSessionProtocol,
        conocimiento_repository: ConocimientoSaberRepositoryProtocol,
        draft_repository: DraftRepositoryProtocol,
        audit_repository: AuditRepositoryProtocol,
    ) -> None:
        """Initialize the service with shared dependencies."""
        self._session = session
        self._conocimiento_repository = conocimiento_repository
        self._draft_repository = draft_repository
        self._audit_repository = audit_repository

    async def list_conocimientos(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> ConocimientoSaberListDTO:
        """List SABER knowledge items tied to the current competence."""
        draft = await self._get_program_draft(referencia_id)
        competencia = await self._require_competencia(draft, competencia_id)
        conocimientos = await self._conocimiento_repository.list_by_competencia(
            competencia.id
        )
        await self._sync_draft_curricular_payload(draft, competencia.id, conocimientos)
        await self._session.commit()

        return ConocimientoSaberListDTO(
            referencia_id=referencia_id,
            competencia_id=competencia.id,
            conocimientos=[_build_conocimiento_dto(item) for item in conocimientos],
        )

    async def create_conocimiento(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        payload: ConocimientoSaberPayloadDTO,
    ) -> ConocimientoSaberListDTO:
        """Create a SABER knowledge item for the current competence."""
        command = _normalize_payload(payload)
        draft = await self._get_program_draft(referencia_id)
        competencia = await self._require_competencia(draft, competencia_id)

        if await self._conocimiento_repository.descripcion_exists(
            competencia.id, command.descripcion
        ):
            raise ConocimientoSaberDuplicateError(
                "Ya existe un conocimiento SABER con esta descripcion exacta "
                "en la competencia"
            )

        conocimientos = await self._conocimiento_repository.list_by_competencia(
            competencia.id
        )
        conocimiento = await self._conocimiento_repository.add_conocimiento(
            competencia_id=competencia.id,
            descripcion=command.descripcion,
            orden=len(conocimientos) + 1,
        )
        await self._session.refresh(conocimiento)

        conocimientos = await self._conocimiento_repository.list_by_competencia(
            competencia.id
        )
        await self._sync_draft_curricular_payload(draft, competencia.id, conocimientos)
        await self._audit_repository.add_event(
            entidad="Conocimiento",
            entidad_id=conocimiento.id,
            accion="CONOCIMIENTO_SABER_CREADO",
            detalle={
                "referencia_id": str(referencia_id),
                "competencia_id": str(competencia.id),
                "tipo": TipoConocimiento.SABER.value,
            },
        )
        await self._session.commit()

        return ConocimientoSaberListDTO(
            referencia_id=referencia_id,
            competencia_id=competencia.id,
            conocimientos=[_build_conocimiento_dto(item) for item in conocimientos],
        )

    async def update_conocimiento(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        conocimiento_id: uuid.UUID,
        payload: ConocimientoSaberPayloadDTO,
    ) -> ConocimientoSaberListDTO:
        """Update a SABER knowledge item without changing its competence."""
        command = _normalize_payload(payload)
        draft = await self._get_program_draft(referencia_id)
        competencia = await self._require_competencia(draft, competencia_id)

        conocimiento = await self._conocimiento_repository.get_by_id_for_competencia(
            conocimiento_id, competencia.id
        )
        if conocimiento is None:
            raise ConocimientoSaberNotFoundError(
                "No existe el conocimiento SABER solicitado para esta competencia"
            )

        if await self._conocimiento_repository.descripcion_exists(
            competencia.id,
            command.descripcion,
            exclude_conocimiento_id=conocimiento_id,
        ):
            raise ConocimientoSaberDuplicateError(
                "Ya existe un conocimiento SABER con esta descripcion exacta "
                "en la competencia"
            )

        conocimiento.descripcion = command.descripcion
        conocimiento.resultado_id = None
        conocimiento.tipo = TipoConocimiento.SABER
        conocimiento = await self._conocimiento_repository.save_conocimiento(
            conocimiento
        )
        await self._session.refresh(conocimiento)

        conocimientos = await self._conocimiento_repository.list_by_competencia(
            competencia.id
        )
        await self._sync_draft_curricular_payload(draft, competencia.id, conocimientos)
        await self._audit_repository.add_event(
            entidad="Conocimiento",
            entidad_id=conocimiento.id,
            accion="CONOCIMIENTO_SABER_ACTUALIZADO",
            detalle={
                "referencia_id": str(referencia_id),
                "competencia_id": str(competencia.id),
                "tipo": TipoConocimiento.SABER.value,
            },
        )
        await self._session.commit()

        return ConocimientoSaberListDTO(
            referencia_id=referencia_id,
            competencia_id=competencia.id,
            conocimientos=[_build_conocimiento_dto(item) for item in conocimientos],
        )

    async def delete_conocimiento(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        conocimiento_id: uuid.UUID,
    ) -> ConocimientoSaberDeleteDTO:
        """Delete a SABER knowledge item."""
        draft = await self._get_program_draft(referencia_id)
        competencia = await self._require_competencia(draft, competencia_id)

        conocimiento = await self._conocimiento_repository.get_by_id_for_competencia(
            conocimiento_id, competencia.id
        )
        if conocimiento is None:
            raise ConocimientoSaberNotFoundError(
                "No existe el conocimiento SABER solicitado para esta competencia"
            )

        await self._conocimiento_repository.delete_conocimiento(conocimiento)
        conocimientos = await self._conocimiento_repository.list_by_competencia(
            competencia.id
        )
        await self._sync_draft_curricular_payload(draft, competencia.id, conocimientos)
        await self._audit_repository.add_event(
            entidad="Conocimiento",
            entidad_id=conocimiento_id,
            accion="CONOCIMIENTO_SABER_ELIMINADO",
            detalle={
                "referencia_id": str(referencia_id),
                "competencia_id": str(competencia.id),
                "tipo": TipoConocimiento.SABER.value,
            },
        )
        await self._session.commit()

        return ConocimientoSaberDeleteDTO(
            referencia_id=referencia_id,
            competencia_id=competencia.id,
            conocimiento_id=conocimiento_id,
            eliminado=True,
        )

    async def _get_program_draft(self, referencia_id: uuid.UUID) -> BorradorSesion:
        draft = await self._draft_repository.get_by_block_reference(
            TipoBloqueBorrador.PROGRAMA,
            referencia_id,
        )
        if draft is None:
            raise ConocimientoSaberDraftNotFoundError(
                "No existe un borrador de programa para la referencia dada"
            )
        return draft

    async def _require_competencia(
        self,
        draft: BorradorSesion,
        competencia_id: uuid.UUID,
    ) -> Competencia:
        programa_id = _extract_programa_id(draft.payload_json)
        if programa_id is None:
            raise ConocimientoSaberCompetenciaNotFoundError(
                "No hay un programa asociado al borrador actual"
            )

        competencia = await self._conocimiento_repository.get_competencia(
            competencia_id, programa_id
        )
        if competencia is None:
            raise ConocimientoSaberCompetenciaNotFoundError(
                "La competencia no existe o no pertenece al programa actual"
            )
        return competencia

    async def _sync_draft_curricular_payload(
        self,
        draft: BorradorSesion,
        competencia_id: uuid.UUID,
        conocimientos_saber: list[Conocimiento],
    ) -> None:
        payload = deepcopy(draft.payload_json)
        curricular = payload.get("curricular")
        if not isinstance(curricular, dict):
            curricular = {}

        competencias = curricular.get("competencias", [])
        if not isinstance(competencias, list):
            competencias = []

        comp_idx = next(
            (
                i
                for i, c in enumerate(competencias)
                if isinstance(c, dict) and c.get("id") == str(competencia_id)
            ),
            -1,
        )
        if comp_idx >= 0:
            competencia_data = competencias[comp_idx]
            if isinstance(competencia_data, dict):
                current = competencia_data.get("conocimientos", [])
                if not isinstance(current, list):
                    current = []
                preserved = [
                    item
                    for item in current
                    if isinstance(item, dict)
                    and item.get("tipo") != TipoConocimiento.SABER.value
                ]
                competencia_data["conocimientos"] = preserved + [
                    _conocimiento_payload_item(item) for item in conocimientos_saber
                ]
                competencias[comp_idx] = competencia_data

        curricular["competencias"] = competencias
        payload["curricular"] = curricular
        draft.payload_json = payload
        await self._draft_repository.save(draft)


def _normalize_payload(
    payload: ConocimientoSaberPayloadDTO,
) -> ConocimientoSaberPayloadDTO:
    descripcion = payload.descripcion.strip()
    if not descripcion:
        raise ConocimientoSaberValidationError("La descripcion es obligatoria")
    return ConocimientoSaberPayloadDTO(descripcion=descripcion)


def _extract_programa_id(payload: dict[str, object]) -> uuid.UUID | None:
    curricular = payload.get("curricular")
    if not isinstance(curricular, dict):
        return None
    raw_programa_id = curricular.get("programa_formacion_id")
    if not isinstance(raw_programa_id, str):
        return None
    try:
        return uuid.UUID(raw_programa_id)
    except ValueError:
        return None


def _conocimiento_payload_item(conocimiento: Conocimiento) -> dict[str, object]:
    return {
        "id": str(conocimiento.id),
        "competencia_id": str(conocimiento.competencia_id),
        "resultado_id": str(conocimiento.resultado_id)
        if conocimiento.resultado_id
        else None,
        "tipo": conocimiento.tipo.value,
        "descripcion": conocimiento.descripcion,
        "orden": conocimiento.orden,
        "estado": conocimiento.estado.value,
        "fecha_creacion": conocimiento.fecha_creacion.isoformat(),
        "fecha_actualizacion": conocimiento.fecha_actualizacion.isoformat(),
    }


def _build_conocimiento_dto(conocimiento: Conocimiento) -> ConocimientoSaberDTO:
    return ConocimientoSaberDTO(
        id=conocimiento.id,
        competencia_id=conocimiento.competencia_id,
        resultado_id=conocimiento.resultado_id,
        tipo=conocimiento.tipo,
        descripcion=conocimiento.descripcion,
        orden=conocimiento.orden,
        estado=conocimiento.estado,
        fecha_creacion=conocimiento.fecha_creacion,
        fecha_actualizacion=conocimiento.fecha_actualizacion,
    )
