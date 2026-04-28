"""Application service for TASK-08 program competence CRUD."""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Protocol

from src.application.dto.competencias import (
    CompetenciaDeleteDTO,
    CompetenciaDTO,
    CompetenciaListDTO,
    CompetenciaPayloadDTO,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.infrastructure.db.models.curriculum import Competencia, ProgramaFormacion
from src.infrastructure.db.models.drafts import BorradorSesion


class CompetenciaError(Exception):
    """Base exception for competence use-case errors."""


class CompetenciaDraftNotFoundError(CompetenciaError):
    """Raised when no program draft exists for a reference."""


class CompetenciaProgramaIncompleteError(CompetenciaError):
    """Raised when the draft has no minimum program data."""


class CompetenciaValidationError(CompetenciaError):
    """Raised when user input is not valid."""


class CompetenciaDuplicateCodeError(CompetenciaError):
    """Raised when a competence code already exists in the program."""


class CompetenciaNotFoundError(CompetenciaError):
    """Raised when a competence is missing or belongs to another program."""


class CompetenciaRepositoryProtocol(Protocol):
    """Repository behavior required by the competence service."""

    async def get_programa(self, programa_id: uuid.UUID) -> ProgramaFormacion | None:
        """Return a program by id."""

    async def get_programa_by_code_version(
        self,
        codigo_programa: str,
        version_programa: str | None,
    ) -> ProgramaFormacion | None:
        """Return the logical program matching code and version."""

    async def add_programa(
        self,
        codigo_programa: str,
        nombre_programa: str,
        version_programa: str | None,
    ) -> ProgramaFormacion:
        """Create a program."""

    async def list_by_programa(self, programa_id: uuid.UUID) -> list[Competencia]:
        """List program competences."""

    async def get_by_id_for_programa(
        self,
        competencia_id: uuid.UUID,
        programa_id: uuid.UUID,
    ) -> Competencia | None:
        """Return a competence for a program."""

    async def code_exists(
        self,
        programa_id: uuid.UUID,
        codigo_competencia: str,
        exclude_competencia_id: uuid.UUID | None = None,
    ) -> bool:
        """Return whether a code exists in a program."""

    async def add_competencia(
        self,
        programa_id: uuid.UUID,
        codigo_competencia: str,
        nombre_competencia: str,
        orden: int,
    ) -> Competencia:
        """Create a competence."""

    async def save_competencia(self, competencia: Competencia) -> Competencia:
        """Persist competence changes."""

    async def delete_competencia(self, competencia: Competencia) -> None:
        """Delete a competence."""


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


class ProgramaCompetenciaService:
    """Coordinate competence CRUD within the active program draft."""

    def __init__(
        self,
        session: AsyncSessionProtocol,
        competencia_repository: CompetenciaRepositoryProtocol,
        draft_repository: DraftRepositoryProtocol,
        audit_repository: AuditRepositoryProtocol,
    ) -> None:
        """Initialize the service with shared dependencies."""
        self._session = session
        self._competencia_repository = competencia_repository
        self._draft_repository = draft_repository
        self._audit_repository = audit_repository

    async def list_competencias(self, referencia_id: uuid.UUID) -> CompetenciaListDTO:
        """List competences tied to the current program draft."""
        draft = await self._get_program_draft(referencia_id)
        programa = await self._get_existing_program_from_draft(draft)
        if programa is None:
            return CompetenciaListDTO(
                referencia_id=referencia_id,
                programa_id=None,
                competencias=[],
            )

        competencias = await self._competencia_repository.list_by_programa(programa.id)
        await self._sync_draft_curricular_payload(draft, programa.id, competencias)
        await self._session.commit()
        return CompetenciaListDTO(
            referencia_id=referencia_id,
            programa_id=programa.id,
            competencias=[_build_competencia_dto(item) for item in competencias],
        )

    async def create_competencia(
        self,
        referencia_id: uuid.UUID,
        payload: CompetenciaPayloadDTO,
    ) -> CompetenciaListDTO:
        """Create a competence for the current program draft."""
        command = _normalize_payload(payload)
        draft = await self._get_program_draft(referencia_id)
        programa = await self._get_or_create_program_for_draft(draft)

        if await self._competencia_repository.code_exists(
            programa.id,
            command.codigo_competencia,
        ):
            raise CompetenciaDuplicateCodeError(
                "Ya existe una competencia con ese codigo en el programa actual"
            )

        competencias = await self._competencia_repository.list_by_programa(programa.id)
        competencia = await self._competencia_repository.add_competencia(
            programa_id=programa.id,
            codigo_competencia=command.codigo_competencia,
            nombre_competencia=command.nombre_competencia,
            orden=len(competencias) + 1,
        )
        await self._session.refresh(competencia)
        competencias = await self._competencia_repository.list_by_programa(programa.id)
        await self._sync_draft_curricular_payload(draft, programa.id, competencias)
        await self._audit_repository.add_event(
            entidad="Competencia",
            entidad_id=competencia.id,
            accion="COMPETENCIA_CREADA",
            detalle={
                "referencia_id": str(referencia_id),
                "programa_id": str(programa.id),
                "codigo_competencia": command.codigo_competencia,
            },
        )
        await self._session.commit()

        return CompetenciaListDTO(
            referencia_id=referencia_id,
            programa_id=programa.id,
            competencias=[_build_competencia_dto(item) for item in competencias],
        )

    async def update_competencia(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        payload: CompetenciaPayloadDTO,
    ) -> CompetenciaListDTO:
        """Update a competence without changing its program ownership."""
        command = _normalize_payload(payload)
        draft = await self._get_program_draft(referencia_id)
        programa = await self._require_program_from_draft(draft)
        competencia = await self._competencia_repository.get_by_id_for_programa(
            competencia_id,
            programa.id,
        )
        if competencia is None:
            raise CompetenciaNotFoundError(
                "No existe la competencia solicitada para el programa actual"
            )

        if await self._competencia_repository.code_exists(
            programa.id,
            command.codigo_competencia,
            exclude_competencia_id=competencia_id,
        ):
            raise CompetenciaDuplicateCodeError(
                "Ya existe una competencia con ese codigo en el programa actual"
            )

        competencia.codigo_competencia = command.codigo_competencia
        competencia.nombre_competencia = command.nombre_competencia
        competencia = await self._competencia_repository.save_competencia(competencia)
        await self._session.refresh(competencia)

        competencias = await self._competencia_repository.list_by_programa(programa.id)
        await self._sync_draft_curricular_payload(draft, programa.id, competencias)
        await self._audit_repository.add_event(
            entidad="Competencia",
            entidad_id=competencia.id,
            accion="COMPETENCIA_ACTUALIZADA",
            detalle={
                "referencia_id": str(referencia_id),
                "programa_id": str(programa.id),
                "codigo_competencia": command.codigo_competencia,
            },
        )
        await self._session.commit()

        return CompetenciaListDTO(
            referencia_id=referencia_id,
            programa_id=programa.id,
            competencias=[_build_competencia_dto(item) for item in competencias],
        )

    async def delete_competencia(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> CompetenciaDeleteDTO:
        """Delete a competence from the current program draft."""
        draft = await self._get_program_draft(referencia_id)
        programa = await self._require_program_from_draft(draft)
        competencia = await self._competencia_repository.get_by_id_for_programa(
            competencia_id,
            programa.id,
        )
        if competencia is None:
            raise CompetenciaNotFoundError(
                "No existe la competencia solicitada para el programa actual"
            )

        await self._competencia_repository.delete_competencia(competencia)
        competencias = await self._competencia_repository.list_by_programa(programa.id)
        await self._sync_draft_curricular_payload(draft, programa.id, competencias)
        await self._audit_repository.add_event(
            entidad="Competencia",
            entidad_id=competencia_id,
            accion="COMPETENCIA_ELIMINADA",
            detalle={
                "referencia_id": str(referencia_id),
                "programa_id": str(programa.id),
            },
        )
        await self._session.commit()

        return CompetenciaDeleteDTO(
            referencia_id=referencia_id,
            programa_id=programa.id,
            competencia_id=competencia_id,
            eliminado=True,
        )

    async def _get_program_draft(self, referencia_id: uuid.UUID) -> BorradorSesion:
        draft = await self._draft_repository.get_by_block_reference(
            TipoBloqueBorrador.PROGRAMA,
            referencia_id,
        )
        if draft is None:
            raise CompetenciaDraftNotFoundError(
                "No existe un borrador de programa para la referencia dada"
            )
        return draft

    async def _get_existing_program_from_draft(
        self,
        draft: BorradorSesion,
    ) -> ProgramaFormacion | None:
        programa_id = _extract_programa_id(draft.payload_json)
        if programa_id is None:
            return None
        return await self._competencia_repository.get_programa(programa_id)

    async def _require_program_from_draft(
        self,
        draft: BorradorSesion,
    ) -> ProgramaFormacion:
        programa = await self._get_existing_program_from_draft(draft)
        if programa is None:
            raise CompetenciaProgramaIncompleteError(
                "Completa y guarda codigo y nombre del programa antes de editar "
                "competencias"
            )
        return programa

    async def _get_or_create_program_for_draft(
        self,
        draft: BorradorSesion,
    ) -> ProgramaFormacion:
        existing_program = await self._get_existing_program_from_draft(draft)
        if existing_program is not None:
            return existing_program

        codigo, nombre, version = _extract_program_base(draft.payload_json)
        if codigo is None or nombre is None:
            raise CompetenciaProgramaIncompleteError(
                "Completa y guarda codigo y nombre del programa antes de crear "
                "competencias"
            )

        programa = await self._competencia_repository.get_programa_by_code_version(
            codigo,
            version,
        )
        if programa is None:
            programa = await self._competencia_repository.add_programa(
                codigo_programa=codigo,
                nombre_programa=nombre,
                version_programa=version,
            )
            await self._session.refresh(programa)

        competencias = await self._competencia_repository.list_by_programa(programa.id)
        await self._sync_draft_curricular_payload(draft, programa.id, competencias)
        return programa

    async def _sync_draft_curricular_payload(
        self,
        draft: BorradorSesion,
        programa_id: uuid.UUID,
        competencias: list[Competencia],
    ) -> None:
        payload = deepcopy(draft.payload_json)
        curricular = payload.get("curricular")
        if not isinstance(curricular, dict):
            curricular = {}

        curricular["programa_formacion_id"] = str(programa_id)
        curricular["competencias"] = [
            _competencia_payload_item(item) for item in competencias
        ]
        payload["curricular"] = curricular
        draft.payload_json = payload
        await self._draft_repository.save(draft)


def _normalize_payload(payload: CompetenciaPayloadDTO) -> CompetenciaPayloadDTO:
    codigo = payload.codigo_competencia.strip()
    nombre = payload.nombre_competencia.strip()
    if not codigo:
        raise CompetenciaValidationError("codigo_competencia es obligatorio")
    if not nombre:
        raise CompetenciaValidationError("nombre_competencia es obligatorio")
    return CompetenciaPayloadDTO(
        codigo_competencia=codigo,
        nombre_competencia=nombre,
    )


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


def _extract_program_base(
    payload: dict[str, object],
) -> tuple[str | None, str | None, str | None]:
    programa = payload.get("programa")
    if not isinstance(programa, dict):
        return None, None, None

    raw_codigo = programa.get("codigo_programa")
    raw_nombre = programa.get("nombre_programa")
    raw_version = programa.get("version_programa")
    codigo = raw_codigo.strip() if isinstance(raw_codigo, str) else ""
    nombre = raw_nombre.strip() if isinstance(raw_nombre, str) else ""
    version = raw_version.strip() if isinstance(raw_version, str) else ""
    return (
        codigo or None,
        nombre or None,
        version or None,
    )


def _competencia_payload_item(competencia: Competencia) -> dict[str, object]:
    return {
        "id": str(competencia.id),
        "programa_id": str(competencia.programa_id),
        "codigo_competencia": competencia.codigo_competencia,
        "nombre_competencia": competencia.nombre_competencia,
        "orden": competencia.orden,
        "estado": competencia.estado.value,
        "origen_campo": competencia.origen_campo.value,
        "fecha_creacion": competencia.fecha_creacion.isoformat(),
        "fecha_actualizacion": competencia.fecha_actualizacion.isoformat(),
    }


def _build_competencia_dto(competencia: Competencia) -> CompetenciaDTO:
    return CompetenciaDTO(
        id=competencia.id,
        programa_id=competencia.programa_id,
        codigo_competencia=competencia.codigo_competencia,
        nombre_competencia=competencia.nombre_competencia,
        orden=competencia.orden,
        estado=competencia.estado,
        origen_campo=competencia.origen_campo,
        fecha_creacion=competencia.fecha_creacion,
        fecha_actualizacion=competencia.fecha_actualizacion,
    )
