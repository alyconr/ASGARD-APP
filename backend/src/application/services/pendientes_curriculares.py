"""Application service for manual reconciliation of Excel pending rows."""

from __future__ import annotations

import uuid
from typing import Protocol

from src.application.dto.pendientes_curriculares import (
    PendienteCurricularAsignacionDTO,
    PendienteCurricularAsignacionResultDTO,
    PendienteCurricularDTO,
    PendienteCurricularListDTO,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import (
    EstadoConciliacionPendiente,
    TipoConocimiento,
    TipoElementoCurricularPendiente,
)
from src.infrastructure.db.models.curriculum import (
    Competencia,
    Conocimiento,
    CriterioEvaluacion,
    ElementoCurricularPendiente,
    ResultadoAprendizaje,
)
from src.infrastructure.db.models.drafts import BorradorSesion


class PendienteCurricularError(Exception):
    """Base exception for pending assignment reconciliation errors."""


class PendienteCurricularDraftNotFoundError(PendienteCurricularError):
    """Raised when the program draft does not exist."""


class PendienteCurricularNotFoundError(PendienteCurricularError):
    """Raised when the requested pending row does not exist."""


class PendienteCurricularValidationError(PendienteCurricularError):
    """Raised when the assignment command is invalid."""


class PendienteCurricularDuplicateError(PendienteCurricularError):
    """Raised when the chosen final destination already has the element."""


class PendientesRepositoryProtocol(Protocol):
    """Repository behavior required by the reconciliation service."""

    async def list_by_reference(
        self,
        referencia_id: uuid.UUID,
    ) -> list[ElementoCurricularPendiente]:
        """Return all pending rows for a reference."""

    async def get_by_id(
        self,
        referencia_id: uuid.UUID,
        pendiente_id: uuid.UUID,
    ) -> ElementoCurricularPendiente | None:
        """Return one pending row."""

    async def get_competencia(
        self,
        competencia_id: uuid.UUID,
        programa_id: uuid.UUID,
    ) -> Competencia | None:
        """Return a competence scoped to a program."""

    async def get_resultado(
        self,
        resultado_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> ResultadoAprendizaje | None:
        """Return a result scoped to a competence."""

    async def conocimiento_exists(
        self,
        *,
        competencia_id: uuid.UUID,
        tipo: TipoConocimiento,
        descripcion: str,
        resultado_id: uuid.UUID | None,
    ) -> bool:
        """Return whether the knowledge item already exists."""

    async def criterio_exists(
        self,
        *,
        competencia_id: uuid.UUID,
        descripcion: str,
        resultado_id: uuid.UUID | None,
    ) -> bool:
        """Return whether the criterion already exists."""

    async def add_conocimiento(
        self,
        *,
        competencia_id: uuid.UUID,
        resultado_id: uuid.UUID | None,
        tipo: TipoConocimiento,
        descripcion: str,
        orden: int | None,
    ) -> Conocimiento:
        """Create a final knowledge item."""

    async def add_criterio(
        self,
        *,
        competencia_id: uuid.UUID,
        resultado_id: uuid.UUID | None,
        descripcion: str,
        orden: int | None,
    ) -> CriterioEvaluacion:
        """Create a final criterion."""

    async def save(
        self,
        pendiente: ElementoCurricularPendiente,
    ) -> ElementoCurricularPendiente:
        """Persist a pending row."""


class DraftRepositoryProtocol(Protocol):
    """Draft repository behavior required by this service."""

    async def get_by_block_reference(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
    ) -> BorradorSesion | None:
        """Return a draft by logical identity."""


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


class PendientesCurricularesService:
    """Coordinate pending assignment listing and manual assignment."""

    def __init__(
        self,
        session: AsyncSessionProtocol,
        pending_repository: PendientesRepositoryProtocol,
        draft_repository: DraftRepositoryProtocol,
        audit_repository: AuditRepositoryProtocol,
    ) -> None:
        """Initialize service dependencies."""
        self._session = session
        self._pending_repository = pending_repository
        self._draft_repository = draft_repository
        self._audit_repository = audit_repository

    async def list_pendientes(
        self,
        referencia_id: uuid.UUID,
    ) -> PendienteCurricularListDTO:
        """List pending assignment rows for the current program draft."""
        await self._get_program_draft(referencia_id)
        pendientes = await self._pending_repository.list_by_reference(referencia_id)
        return PendienteCurricularListDTO(
            referencia_id=referencia_id,
            pendientes=[_build_pendiente_dto(item) for item in pendientes],
        )

    async def asignar_pendiente(
        self,
        referencia_id: uuid.UUID,
        pendiente_id: uuid.UUID,
        payload: PendienteCurricularAsignacionDTO,
    ) -> PendienteCurricularAsignacionResultDTO:
        """Assign one pending row into the final relational curriculum model."""
        draft = await self._get_program_draft(referencia_id)
        programa_id = _extract_programa_id(draft.payload_json)
        if programa_id is None:
            raise PendienteCurricularValidationError(
                "No hay un programa asociado al borrador actual"
            )

        pendiente = await self._pending_repository.get_by_id(
            referencia_id,
            pendiente_id,
        )
        if pendiente is None:
            raise PendienteCurricularNotFoundError("El pendiente solicitado no existe")
        if pendiente.estado != EstadoConciliacionPendiente.PENDIENTE:
            raise PendienteCurricularValidationError("El pendiente ya fue asignado")

        competencia = await self._pending_repository.get_competencia(
            payload.competencia_id,
            programa_id,
        )
        if competencia is None:
            raise PendienteCurricularValidationError(
                "La competencia destino no pertenece al programa actual"
            )

        resultado_id = payload.resultado_id
        if resultado_id is not None:
            resultado = await self._pending_repository.get_resultado(
                resultado_id,
                competencia.id,
            )
            if resultado is None:
                raise PendienteCurricularValidationError(
                    "El resultado destino no pertenece a la competencia seleccionada"
                )

        created: Conocimiento | CriterioEvaluacion
        if pendiente.tipo_elemento == TipoElementoCurricularPendiente.CONOCIMIENTO:
            if pendiente.tipo_conocimiento is None:
                raise PendienteCurricularValidationError(
                    "El conocimiento pendiente no tiene tipo_conocimiento"
                )
            if await self._pending_repository.conocimiento_exists(
                competencia_id=competencia.id,
                tipo=pendiente.tipo_conocimiento,
                descripcion=pendiente.descripcion,
                resultado_id=resultado_id,
            ):
                raise PendienteCurricularDuplicateError(
                    "Ya existe un conocimiento igual en el destino seleccionado"
                )
            created = await self._pending_repository.add_conocimiento(
                competencia_id=competencia.id,
                resultado_id=resultado_id,
                tipo=pendiente.tipo_conocimiento,
                descripcion=pendiente.descripcion,
                orden=pendiente.orden,
            )
        else:
            if await self._pending_repository.criterio_exists(
                competencia_id=competencia.id,
                descripcion=pendiente.descripcion,
                resultado_id=resultado_id,
            ):
                raise PendienteCurricularDuplicateError(
                    "Ya existe un criterio igual en el destino seleccionado"
                )
            created = await self._pending_repository.add_criterio(
                competencia_id=competencia.id,
                resultado_id=resultado_id,
                descripcion=pendiente.descripcion,
                orden=pendiente.orden,
            )

        await self._session.refresh(created)
        pendiente.estado = EstadoConciliacionPendiente.ASIGNADO
        pendiente.competencia_destino_id = competencia.id
        pendiente.resultado_destino_id = resultado_id
        pendiente.elemento_creado_id = created.id
        pendiente = await self._pending_repository.save(pendiente)
        await self._session.refresh(pendiente)
        await self._audit_repository.add_event(
            entidad="ElementoCurricularPendiente",
            entidad_id=pendiente.id,
            accion="PENDIENTE_CURRICULAR_ASIGNADO",
            detalle={
                "referencia_id": str(referencia_id),
                "competencia_id": str(competencia.id),
                "resultado_id": str(resultado_id) if resultado_id else None,
                "elemento_creado_id": str(created.id),
            },
        )
        await self._session.commit()
        return PendienteCurricularAsignacionResultDTO(
            referencia_id=referencia_id,
            pendiente=_build_pendiente_dto(pendiente),
        )

    async def _get_program_draft(self, referencia_id: uuid.UUID) -> BorradorSesion:
        draft = await self._draft_repository.get_by_block_reference(
            TipoBloqueBorrador.PROGRAMA,
            referencia_id,
        )
        if draft is None:
            raise PendienteCurricularDraftNotFoundError(
                "No existe un borrador de programa para la referencia dada"
            )
        return draft


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


def _build_pendiente_dto(
    pendiente: ElementoCurricularPendiente,
) -> PendienteCurricularDTO:
    return PendienteCurricularDTO(
        id=pendiente.id,
        referencia_id=pendiente.referencia_id,
        programa_id=pendiente.programa_id,
        tipo_elemento=pendiente.tipo_elemento,
        tipo_conocimiento=pendiente.tipo_conocimiento,
        descripcion=pendiente.descripcion,
        competencia_id_origen_excel=pendiente.competencia_id_origen_excel,
        rap_id_origen_excel=pendiente.rap_id_origen_excel,
        motivo=pendiente.motivo,
        estado=pendiente.estado,
        competencia_destino_id=pendiente.competencia_destino_id,
        resultado_destino_id=pendiente.resultado_destino_id,
        elemento_creado_id=pendiente.elemento_creado_id,
        fecha_creacion=pendiente.fecha_creacion,
        fecha_actualizacion=pendiente.fecha_actualizacion,
    )
