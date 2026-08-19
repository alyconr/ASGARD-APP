"""Application service for TASK-12 criteria CRUD."""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Protocol

from src.application.dto.criterios import (
    CriterioDeleteDTO,
    CriterioDTO,
    CriterioListDTO,
    CriterioPayloadDTO,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.infrastructure.db.models.curriculum import Competencia, CriterioEvaluacion
from src.infrastructure.db.models.drafts import BorradorSesion


class CriterioError(Exception):
    """Base exception for criteria use-case errors."""


class CriterioDraftNotFoundError(CriterioError):
    """Raised when no program draft exists for a reference."""


class CriterioCompetenciaNotFoundError(CriterioError):
    """Raised when the competence is missing or not tied to the program."""


class CriterioValidationError(CriterioError):
    """Raised when user input is not valid."""


class CriterioDuplicateError(CriterioError):
    """Raised when a criteria description already exists in the competence."""


class CriterioNotFoundError(CriterioError):
    """Raised when a criteria item is missing."""


class CriterioRepositoryProtocol(Protocol):
    """Repository behavior required by the criteria service."""

    async def get_competencia(
        self,
        competencia_id: uuid.UUID,
        programa_id: uuid.UUID | None = None,
    ) -> Competencia | None:
        """Return a competence by id."""

    async def list_by_competencia(
        self,
        competencia_id: uuid.UUID,
    ) -> list[CriterioEvaluacion]:
        """List competence criteria items."""

    async def get_by_id_for_competencia(
        self,
        criterio_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> CriterioEvaluacion | None:
        """Return a criteria item for a competence."""

    async def descripcion_exists(
        self,
        competencia_id: uuid.UUID,
        descripcion: str,
        exclude_criterio_id: uuid.UUID | None = None,
    ) -> bool:
        """Return whether a criteria description exists in a competence."""

    async def add_criterio(
        self,
        competencia_id: uuid.UUID,
        descripcion: str,
        orden: int,
    ) -> CriterioEvaluacion:
        """Create a criteria item."""

    async def save_criterio(
        self,
        criterio: CriterioEvaluacion,
    ) -> CriterioEvaluacion:
        """Persist criteria changes."""

    async def delete_criterio(self, criterio: CriterioEvaluacion) -> None:
        """Delete a criteria item."""


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


class ProgramaCriteriosService:
    """Coordinate criteria CRUD within the active program draft."""

    def __init__(
        self,
        session: AsyncSessionProtocol,
        criterio_repository: CriterioRepositoryProtocol,
        draft_repository: DraftRepositoryProtocol,
        audit_repository: AuditRepositoryProtocol,
    ) -> None:
        self._session = session
        self._criterio_repository = criterio_repository
        self._draft_repository = draft_repository
        self._audit_repository = audit_repository

    async def list_criterios(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> CriterioListDTO:
        draft = await self._get_program_draft(referencia_id)
        competencia = await self._require_competencia(draft, competencia_id)
        criterios = await self._criterio_repository.list_by_competencia(
            competencia.id,
        )
        await self._sync_draft_curricular_payload(draft, competencia.id, criterios)
        await self._session.commit()

        return CriterioListDTO(
            referencia_id=referencia_id,
            competencia_id=competencia.id,
            criterios=[_build_criterio_dto(item) for item in criterios],
        )

    async def create_criterio(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        payload: CriterioPayloadDTO,
    ) -> CriterioListDTO:
        command = _normalize_payload(payload)
        draft = await self._get_program_draft(referencia_id)
        competencia = await self._require_competencia(draft, competencia_id)

        if await self._criterio_repository.descripcion_exists(
            competencia.id,
            command.descripcion,
        ):
            raise CriterioDuplicateError(
                "Ya existe un criterio de evaluacion con esta descripcion exacta "
                "en la competencia",
            )

        criterios = await self._criterio_repository.list_by_competencia(
            competencia.id,
        )
        criterio = await self._criterio_repository.add_criterio(
            competencia_id=competencia.id,
            descripcion=command.descripcion,
            orden=len(criterios) + 1,
        )
        await self._session.refresh(criterio)

        criterios = await self._criterio_repository.list_by_competencia(
            competencia.id,
        )
        await self._sync_draft_curricular_payload(draft, competencia.id, criterios)
        await self._audit_repository.add_event(
            entidad="CriterioEvaluacion",
            entidad_id=criterio.id,
            accion="CRITERIO_CREADO",
            detalle={
                "referencia_id": str(referencia_id),
                "competencia_id": str(competencia.id),
            },
        )
        await self._session.commit()

        return CriterioListDTO(
            referencia_id=referencia_id,
            competencia_id=competencia.id,
            criterios=[_build_criterio_dto(item) for item in criterios],
        )

    async def update_criterio(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        criterio_id: uuid.UUID,
        payload: CriterioPayloadDTO,
    ) -> CriterioListDTO:
        command = _normalize_payload(payload)
        draft = await self._get_program_draft(referencia_id)
        competencia = await self._require_competencia(draft, competencia_id)

        criterio = await self._criterio_repository.get_by_id_for_competencia(
            criterio_id,
            competencia.id,
        )
        if criterio is None:
            raise CriterioNotFoundError(
                "No existe el criterio de evaluacion solicitado para esta competencia",
            )

        if await self._criterio_repository.descripcion_exists(
            competencia.id,
            command.descripcion,
            exclude_criterio_id=criterio_id,
        ):
            raise CriterioDuplicateError(
                "Ya existe un criterio de evaluacion con esta descripcion exacta "
                "en la competencia",
            )

        criterio.descripcion = command.descripcion
        criterio = await self._criterio_repository.save_criterio(criterio)
        await self._session.refresh(criterio)

        criterios = await self._criterio_repository.list_by_competencia(
            competencia.id,
        )
        await self._sync_draft_curricular_payload(draft, competencia.id, criterios)
        await self._audit_repository.add_event(
            entidad="CriterioEvaluacion",
            entidad_id=criterio.id,
            accion="CRITERIO_ACTUALIZADO",
            detalle={
                "referencia_id": str(referencia_id),
                "competencia_id": str(competencia.id),
            },
        )
        await self._session.commit()

        return CriterioListDTO(
            referencia_id=referencia_id,
            competencia_id=competencia.id,
            criterios=[_build_criterio_dto(item) for item in criterios],
        )

    async def delete_criterio(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        criterio_id: uuid.UUID,
    ) -> CriterioDeleteDTO:
        draft = await self._get_program_draft(referencia_id)
        competencia = await self._require_competencia(draft, competencia_id)

        criterio = await self._criterio_repository.get_by_id_for_competencia(
            criterio_id,
            competencia.id,
        )
        if criterio is None:
            raise CriterioNotFoundError(
                "No existe el criterio de evaluacion solicitado para esta competencia",
            )

        await self._criterio_repository.delete_criterio(criterio)
        criterios = await self._criterio_repository.list_by_competencia(
            competencia.id,
        )
        await self._sync_draft_curricular_payload(draft, competencia.id, criterios)
        await self._audit_repository.add_event(
            entidad="CriterioEvaluacion",
            entidad_id=criterio_id,
            accion="CRITERIO_ELIMINADO",
            detalle={
                "referencia_id": str(referencia_id),
                "competencia_id": str(competencia.id),
            },
        )
        await self._session.commit()

        return CriterioDeleteDTO(
            referencia_id=referencia_id,
            competencia_id=competencia.id,
            criterio_id=criterio_id,
            eliminado=True,
        )

    async def _get_program_draft(self, referencia_id: uuid.UUID) -> BorradorSesion:
        draft = await self._draft_repository.get_by_block_reference(
            TipoBloqueBorrador.PROGRAMA,
            referencia_id,
        )
        if draft is None:
            raise CriterioDraftNotFoundError(
                "No existe un borrador de programa para la referencia dada",
            )
        return draft

    async def _require_competencia(
        self,
        draft: BorradorSesion,
        competencia_id: uuid.UUID,
    ) -> Competencia:
        programa_id = _extract_programa_id(draft.payload_json)
        if programa_id is None:
            raise CriterioCompetenciaNotFoundError(
                "No hay un programa asociado al borrador actual",
            )

        competencia = await self._criterio_repository.get_competencia(
            competencia_id,
            programa_id,
        )
        if competencia is None:
            raise CriterioCompetenciaNotFoundError(
                "La competencia no existe o no pertenece al programa actual",
            )
        return competencia

    async def _sync_draft_curricular_payload(
        self,
        draft: BorradorSesion,
        competencia_id: uuid.UUID,
        criterios: list[CriterioEvaluacion],
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
                competencia_data["criterios"] = [
                    _criterio_payload_item(item) for item in criterios
                ]
                competencias[comp_idx] = competencia_data

        curricular["competencias"] = competencias
        payload["curricular"] = curricular
        draft.payload_json = payload
        await self._draft_repository.save(draft)


def _normalize_payload(payload: CriterioPayloadDTO) -> CriterioPayloadDTO:
    descripcion = payload.descripcion.strip()
    if not descripcion:
        raise CriterioValidationError("La descripcion es obligatoria")
    return CriterioPayloadDTO(descripcion=descripcion)


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


def _criterio_payload_item(criterio: CriterioEvaluacion) -> dict[str, object]:
    return {
        "id": str(criterio.id),
        "competencia_id": str(criterio.competencia_id),
        "resultado_id": str(criterio.resultado_id) if criterio.resultado_id else None,
        "descripcion": criterio.descripcion,
        "orden": criterio.orden,
        "estado": criterio.estado.value,
        "fecha_creacion": criterio.fecha_creacion.isoformat(),
        "fecha_actualizacion": criterio.fecha_actualizacion.isoformat(),
    }


def _build_criterio_dto(criterio: CriterioEvaluacion) -> CriterioDTO:
    return CriterioDTO(
        id=criterio.id,
        competencia_id=criterio.competencia_id,
        resultado_id=criterio.resultado_id,
        descripcion=criterio.descripcion,
        orden=criterio.orden,
        estado=criterio.estado,
        fecha_creacion=criterio.fecha_creacion,
        fecha_actualizacion=criterio.fecha_actualizacion,
    )
