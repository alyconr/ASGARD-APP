"""Application service for TASK-09 learning outcomes CRUD."""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Protocol

from src.application.dto.resultados_aprendizaje import (
    ResultadoAprendizajeDeleteDTO,
    ResultadoAprendizajeDTO,
    ResultadoAprendizajeListDTO,
    ResultadoAprendizajePayloadDTO,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.infrastructure.db.models.curriculum import Competencia, ResultadoAprendizaje
from src.infrastructure.db.models.drafts import BorradorSesion


class ResultadoAprendizajeError(Exception):
    """Base exception for learning outcome use-case errors."""


class ResultadoAprendizajeDraftNotFoundError(ResultadoAprendizajeError):
    """Raised when no program draft exists for a reference."""


class ResultadoAprendizajeCompetenciaNotFoundError(ResultadoAprendizajeError):
    """Raised when the competence is missing or not tied to the program."""


class ResultadoAprendizajeValidationError(ResultadoAprendizajeError):
    """Raised when user input is not valid."""


class ResultadoAprendizajeDuplicateError(ResultadoAprendizajeError):
    """Raised when a description already exists in the competence."""


class ResultadoAprendizajeNotFoundError(ResultadoAprendizajeError):
    """Raised when a learning outcome is missing."""


class ResultadoAprendizajeRepositoryProtocol(Protocol):
    """Repository behavior required by the learning outcomes service."""

    async def get_competencia(
        self,
        competencia_id: uuid.UUID,
        programa_id: uuid.UUID | None = None,
    ) -> Competencia | None:
        """Return a competence by id."""

    async def list_by_competencia(
        self,
        competencia_id: uuid.UUID,
    ) -> list[ResultadoAprendizaje]:
        """List competence learning outcomes."""

    async def get_by_id_for_competencia(
        self,
        resultado_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> ResultadoAprendizaje | None:
        """Return a learning outcome for a competence."""

    async def descripcion_exists(
        self,
        competencia_id: uuid.UUID,
        descripcion: str,
        exclude_resultado_id: uuid.UUID | None = None,
    ) -> bool:
        """Return whether a description exists in a competence."""

    async def add_resultado(
        self,
        competencia_id: uuid.UUID,
        descripcion: str,
        orden: int,
        codigo_resultado: str | None = None,
    ) -> ResultadoAprendizaje:
        """Create a learning outcome."""

    async def save_resultado(
        self,
        resultado: ResultadoAprendizaje,
    ) -> ResultadoAprendizaje:
        """Persist learning outcome changes."""

    async def delete_resultado(self, resultado: ResultadoAprendizaje) -> None:
        """Delete a learning outcome."""


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


class ProgramaResultadoAprendizajeService:
    """Coordinate learning outcomes CRUD within the active program draft."""

    def __init__(
        self,
        session: AsyncSessionProtocol,
        resultado_repository: ResultadoAprendizajeRepositoryProtocol,
        draft_repository: DraftRepositoryProtocol,
        audit_repository: AuditRepositoryProtocol,
    ) -> None:
        """Initialize the service with shared dependencies."""
        self._session = session
        self._resultado_repository = resultado_repository
        self._draft_repository = draft_repository
        self._audit_repository = audit_repository

    async def list_resultados(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> ResultadoAprendizajeListDTO:
        """List learning outcomes tied to the current competence."""
        draft = await self._get_program_draft(referencia_id)
        programa_id = _extract_programa_id(draft.payload_json)

        if programa_id is None:
            return ResultadoAprendizajeListDTO(
                referencia_id=referencia_id,
                competencia_id=competencia_id,
                resultados=[],
            )

        competencia = await self._resultado_repository.get_competencia(
            competencia_id, programa_id
        )
        if competencia is None:
            return ResultadoAprendizajeListDTO(
                referencia_id=referencia_id,
                competencia_id=competencia_id,
                resultados=[],
            )

        resultados = await self._resultado_repository.list_by_competencia(
            competencia.id
        )
        await self._sync_draft_curricular_payload(draft, competencia.id, resultados)
        await self._session.commit()

        return ResultadoAprendizajeListDTO(
            referencia_id=referencia_id,
            competencia_id=competencia.id,
            resultados=[_build_resultado_dto(item) for item in resultados],
        )

    async def create_resultado(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        payload: ResultadoAprendizajePayloadDTO,
    ) -> ResultadoAprendizajeListDTO:
        """Create a learning outcome for the current competence."""
        command = _normalize_payload(payload)
        draft = await self._get_program_draft(referencia_id)
        programa_id = _extract_programa_id(draft.payload_json)

        if programa_id is None:
            raise ResultadoAprendizajeCompetenciaNotFoundError(
                "No hay un programa asociado al borrador actual"
            )

        competencia = await self._resultado_repository.get_competencia(
            competencia_id, programa_id
        )
        if competencia is None:
            raise ResultadoAprendizajeCompetenciaNotFoundError(
                "La competencia no existe o no pertenece al programa actual"
            )

        if await self._resultado_repository.descripcion_exists(
            competencia.id, command.descripcion
        ):
            raise ResultadoAprendizajeDuplicateError(
                "Ya existe un resultado de aprendizaje con esta descripcion exacta "
                "en la competencia"
            )

        resultados = await self._resultado_repository.list_by_competencia(
            competencia.id
        )
        resultado = await self._resultado_repository.add_resultado(
            competencia_id=competencia.id,
            descripcion=command.descripcion,
            codigo_resultado=command.codigo_resultado,
            orden=len(resultados) + 1,
        )
        await self._session.refresh(resultado)

        resultados = await self._resultado_repository.list_by_competencia(
            competencia.id
        )
        await self._sync_draft_curricular_payload(draft, competencia.id, resultados)
        await self._audit_repository.add_event(
            entidad="ResultadoAprendizaje",
            entidad_id=resultado.id,
            accion="RESULTADO_CREADO",
            detalle={
                "referencia_id": str(referencia_id),
                "competencia_id": str(competencia.id),
            },
        )
        await self._session.commit()

        return ResultadoAprendizajeListDTO(
            referencia_id=referencia_id,
            competencia_id=competencia.id,
            resultados=[_build_resultado_dto(item) for item in resultados],
        )

    async def update_resultado(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        resultado_id: uuid.UUID,
        payload: ResultadoAprendizajePayloadDTO,
    ) -> ResultadoAprendizajeListDTO:
        """Update a learning outcome."""
        command = _normalize_payload(payload)
        draft = await self._get_program_draft(referencia_id)
        programa_id = _extract_programa_id(draft.payload_json)

        if programa_id is None:
            raise ResultadoAprendizajeCompetenciaNotFoundError(
                "No hay un programa asociado al borrador actual"
            )

        competencia = await self._resultado_repository.get_competencia(
            competencia_id, programa_id
        )
        if competencia is None:
            raise ResultadoAprendizajeCompetenciaNotFoundError(
                "La competencia no existe o no pertenece al programa actual"
            )

        resultado = await self._resultado_repository.get_by_id_for_competencia(
            resultado_id, competencia.id
        )
        if resultado is None:
            raise ResultadoAprendizajeNotFoundError(
                "No existe el resultado solicitado para esta competencia"
            )

        if await self._resultado_repository.descripcion_exists(
            competencia.id, command.descripcion, exclude_resultado_id=resultado_id
        ):
            raise ResultadoAprendizajeDuplicateError(
                "Ya existe un resultado con esta descripcion exacta en la competencia"
            )

        resultado.descripcion = command.descripcion
        resultado.codigo_resultado = command.codigo_resultado
        resultado = await self._resultado_repository.save_resultado(resultado)
        await self._session.refresh(resultado)

        resultados = await self._resultado_repository.list_by_competencia(
            competencia.id
        )
        await self._sync_draft_curricular_payload(draft, competencia.id, resultados)
        await self._audit_repository.add_event(
            entidad="ResultadoAprendizaje",
            entidad_id=resultado.id,
            accion="RESULTADO_ACTUALIZADO",
            detalle={
                "referencia_id": str(referencia_id),
                "competencia_id": str(competencia.id),
            },
        )
        await self._session.commit()

        return ResultadoAprendizajeListDTO(
            referencia_id=referencia_id,
            competencia_id=competencia.id,
            resultados=[_build_resultado_dto(item) for item in resultados],
        )

    async def delete_resultado(
        self,
        referencia_id: uuid.UUID,
        competencia_id: uuid.UUID,
        resultado_id: uuid.UUID,
    ) -> ResultadoAprendizajeDeleteDTO:
        """Delete a learning outcome."""
        draft = await self._get_program_draft(referencia_id)
        programa_id = _extract_programa_id(draft.payload_json)

        if programa_id is None:
            raise ResultadoAprendizajeCompetenciaNotFoundError(
                "No hay un programa asociado al borrador actual"
            )

        competencia = await self._resultado_repository.get_competencia(
            competencia_id, programa_id
        )
        if competencia is None:
            raise ResultadoAprendizajeCompetenciaNotFoundError(
                "La competencia no existe o no pertenece al programa actual"
            )

        resultado = await self._resultado_repository.get_by_id_for_competencia(
            resultado_id, competencia.id
        )
        if resultado is None:
            raise ResultadoAprendizajeNotFoundError(
                "No existe el resultado solicitado para esta competencia"
            )

        await self._resultado_repository.delete_resultado(resultado)
        resultados = await self._resultado_repository.list_by_competencia(
            competencia.id
        )
        await self._sync_draft_curricular_payload(draft, competencia.id, resultados)
        await self._audit_repository.add_event(
            entidad="ResultadoAprendizaje",
            entidad_id=resultado_id,
            accion="RESULTADO_ELIMINADO",
            detalle={
                "referencia_id": str(referencia_id),
                "competencia_id": str(competencia.id),
            },
        )
        await self._session.commit()

        return ResultadoAprendizajeDeleteDTO(
            referencia_id=referencia_id,
            competencia_id=competencia.id,
            resultado_id=resultado_id,
            eliminado=True,
        )

    async def _get_program_draft(self, referencia_id: uuid.UUID) -> BorradorSesion:
        draft = await self._draft_repository.get_by_block_reference(
            TipoBloqueBorrador.PROGRAMA,
            referencia_id,
        )
        if draft is None:
            raise ResultadoAprendizajeDraftNotFoundError(
                "No existe un borrador de programa para la referencia dada"
            )
        return draft

    async def _sync_draft_curricular_payload(
        self,
        draft: BorradorSesion,
        competencia_id: uuid.UUID,
        resultados: list[ResultadoAprendizaje],
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
                if c.get("id") == str(competencia_id)
            ),
            -1,
        )
        if comp_idx >= 0:
            competencia_data = competencias[comp_idx]
            if isinstance(competencia_data, dict):
                competencia_data["resultados"] = [
                    _resultado_payload_item(item) for item in resultados
                ]
                competencias[comp_idx] = competencia_data

        curricular["competencias"] = competencias
        payload["curricular"] = curricular
        draft.payload_json = payload
        await self._draft_repository.save(draft)


def _normalize_payload(
    payload: ResultadoAprendizajePayloadDTO,
) -> ResultadoAprendizajePayloadDTO:
    descripcion = payload.descripcion.strip()
    codigo = payload.codigo_resultado.strip() if payload.codigo_resultado else None
    if not descripcion:
        raise ResultadoAprendizajeValidationError("La descripcion es obligatoria")
    return ResultadoAprendizajePayloadDTO(
        descripcion=descripcion,
        codigo_resultado=codigo,
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


def _resultado_payload_item(resultado: ResultadoAprendizaje) -> dict[str, object]:
    return {
        "id": str(resultado.id),
        "competencia_id": str(resultado.competencia_id),
        "codigo_resultado": resultado.codigo_resultado,
        "descripcion": resultado.descripcion,
        "orden": resultado.orden,
        "estado": resultado.estado.value,
        "motivo_fallo_extraccion": resultado.motivo_fallo_extraccion.value
        if resultado.motivo_fallo_extraccion
        else None,
        "fecha_creacion": resultado.fecha_creacion.isoformat(),
        "fecha_actualizacion": resultado.fecha_actualizacion.isoformat(),
    }


def _build_resultado_dto(resultado: ResultadoAprendizaje) -> ResultadoAprendizajeDTO:
    return ResultadoAprendizajeDTO(
        id=resultado.id,
        competencia_id=resultado.competencia_id,
        codigo_resultado=resultado.codigo_resultado,
        descripcion=resultado.descripcion,
        orden=resultado.orden,
        estado=resultado.estado,
        motivo_fallo_extraccion=resultado.motivo_fallo_extraccion,
        fecha_creacion=resultado.fecha_creacion,
        fecha_actualizacion=resultado.fecha_actualizacion,
    )
