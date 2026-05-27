"""TASK-14 service for program completion validation and explicit closing."""

from __future__ import annotations

import re
import unicodedata
import uuid
from copy import deepcopy
from datetime import UTC, datetime
from typing import Protocol

from src.application.dto.programa_cierre import (
    ProgramaCierreDTO,
    ProgramaCompletitudDTO,
    ProgramaCompletitudFaltanteDTO,
    ProgramaCompletitudResumenDTO,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque, TipoConocimiento
from src.infrastructure.db.models.curriculum import Competencia, ProgramaFormacion
from src.infrastructure.db.models.drafts import BorradorSesion


class ProgramaCierreError(Exception):
    """Base exception for program closing errors."""


class ProgramaCierreDraftNotFoundError(ProgramaCierreError):
    """Raised when there is no program draft for the requested reference."""


class ProgramaCierreValidationError(ProgramaCierreError):
    """Raised when an explicit close is attempted on an incomplete program."""

    def __init__(self, completitud: ProgramaCompletitudDTO) -> None:
        """Store the structured validation result for HTTP and UI callers."""
        super().__init__("El programa no cumple la estructura minima de cierre")
        self.completitud = completitud


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


class ProgramaCierreRepositoryProtocol(Protocol):
    """Program aggregate persistence required by TASK-14."""

    async def get_programa_with_curriculum(
        self,
        programa_id: uuid.UUID,
    ) -> ProgramaFormacion | None:
        """Return a program with curriculum children loaded."""

    async def save_programa(self, programa: ProgramaFormacion) -> ProgramaFormacion:
        """Persist program changes."""


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


class ProgramaCierreService:
    """Validate program completeness and close the program on explicit request."""

    def __init__(
        self,
        session: AsyncSessionProtocol,
        draft_repository: DraftRepositoryProtocol,
        programa_repository: ProgramaCierreRepositoryProtocol,
        audit_repository: AuditRepositoryProtocol,
    ) -> None:
        """Initialize the service with explicit infrastructure ports."""
        self._session = session
        self._draft_repository = draft_repository
        self._programa_repository = programa_repository
        self._audit_repository = audit_repository

    async def validar_completitud(
        self,
        referencia_id: uuid.UUID,
    ) -> ProgramaCompletitudDTO:
        """Return a structured explanation of whether the program can close."""
        draft = await self._get_program_draft(referencia_id)
        programa = await self._get_programa_from_draft(draft)
        codigo, nombre = _extract_program_base(draft.payload_json, programa)
        competencias = sorted(
            programa.competencias if programa is not None else [],
            key=lambda item: (item.orden is None, item.orden or 0),
        )

        faltantes: list[ProgramaCompletitudFaltanteDTO] = []
        if not codigo:
            faltantes.append(
                _missing(
                    codigo="programa.codigo_programa",
                    campo="codigo_programa",
                    mensaje="El codigo del programa es obligatorio para cerrar.",
                )
            )
        if not nombre:
            faltantes.append(
                _missing(
                    codigo="programa.nombre_programa",
                    campo="nombre_programa",
                    mensaje="El nombre del programa es obligatorio para cerrar.",
                )
            )

        if programa is None or not competencias:
            faltantes.append(
                _missing(
                    codigo="programa.competencias",
                    campo="competencias",
                    mensaje=("Registra al menos una competencia asociada al programa."),
                )
            )

        total_resultados = 0
        total_saber = 0
        total_proceso = 0
        total_criterios = 0

        for competencia in competencias:
            resultados = [
                item for item in competencia.resultados if item.descripcion.strip()
            ]
            saberes = [
                item
                for item in competencia.conocimientos
                if item.tipo == TipoConocimiento.SABER and item.descripcion.strip()
            ]
            procesos = [
                item
                for item in competencia.conocimientos
                if item.tipo == TipoConocimiento.PROCESO and item.descripcion.strip()
            ]
            criterios = [
                item for item in competencia.criterios if item.descripcion.strip()
            ]
            total_resultados += len(resultados)
            total_saber += len(saberes)
            total_proceso += len(procesos)
            total_criterios += len(criterios)

            if _is_practical_stage_competence(competencia):
                continue

            if not competencia.codigo_competencia.strip():
                faltantes.append(
                    _missing_for_competencia(
                        competencia,
                        "competencia.codigo_competencia",
                        "codigo_competencia",
                        "La competencia debe tener codigo.",
                    )
                )
            if not competencia.nombre_competencia.strip():
                faltantes.append(
                    _missing_for_competencia(
                        competencia,
                        "competencia.nombre_competencia",
                        "nombre_competencia",
                        "La competencia debe tener nombre.",
                    )
                )
            if not resultados:
                faltantes.append(
                    _missing_for_competencia(
                        competencia,
                        "competencia.resultados",
                        "resultados",
                        "Agrega al menos un resultado de aprendizaje.",
                    )
                )
            if not saberes:
                faltantes.append(
                    _missing_for_competencia(
                        competencia,
                        "competencia.conocimientos_saber",
                        "conocimientos_saber",
                        "Agrega al menos un conocimiento SABER.",
                    )
                )
            if not procesos:
                faltantes.append(
                    _missing_for_competencia(
                        competencia,
                        "competencia.conocimientos_proceso",
                        "conocimientos_proceso",
                        "Agrega al menos un conocimiento PROCESO.",
                    )
                )
            if not criterios:
                faltantes.append(
                    _missing_for_competencia(
                        competencia,
                        "competencia.criterios",
                        "criterios",
                        "Agrega al menos un criterio de evaluacion.",
                    )
                )

        faltantes.extend(
            _global_curricular_missing(
                total_resultados=total_resultados,
                total_saber=total_saber,
                total_proceso=total_proceso,
                total_criterios=total_criterios,
            )
        )
        resumen = ProgramaCompletitudResumenDTO(
            competencias=len(competencias),
            resultados=total_resultados,
            conocimientos_saber=total_saber,
            conocimientos_proceso=total_proceso,
            criterios=total_criterios,
        )
        return ProgramaCompletitudDTO(
            referencia_id=referencia_id,
            programa_id=programa.id if programa is not None else None,
            estado_actual=(
                programa.estado if programa is not None else draft.estado_borrador
            ),
            cerrable=len(faltantes) == 0,
            resumen=resumen,
            faltantes=faltantes,
        )

    async def cerrar_programa(self, referencia_id: uuid.UUID) -> ProgramaCierreDTO:
        """Close a program only after successful structured validation."""
        draft = await self._get_program_draft(referencia_id)
        completitud = await self.validar_completitud(referencia_id)
        if not completitud.cerrable or completitud.programa_id is None:
            raise ProgramaCierreValidationError(completitud)

        programa = await self._programa_repository.get_programa_with_curriculum(
            completitud.programa_id,
        )
        if programa is None:
            raise ProgramaCierreValidationError(completitud)

        programa.estado = EstadoBloque.COMPLETO
        draft.estado_borrador = EstadoBloque.COMPLETO
        draft.paso_actual = "revision-programa"
        draft.payload_json = _touch_review_step(draft.payload_json)
        await self._programa_repository.save_programa(programa)
        await self._draft_repository.save(draft)
        await self._audit_repository.add_event(
            entidad="ProgramaFormacion",
            entidad_id=programa.id,
            accion="PROGRAMA_CERRADO",
            detalle={
                "referencia_id": str(referencia_id),
                "estado": EstadoBloque.COMPLETO.value,
            },
        )
        await self._session.commit()
        await self._session.refresh(programa)
        await self._session.refresh(draft)

        closed_completitud = ProgramaCompletitudDTO(
            referencia_id=completitud.referencia_id,
            programa_id=completitud.programa_id,
            estado_actual=EstadoBloque.COMPLETO,
            cerrable=True,
            resumen=completitud.resumen,
            faltantes=[],
        )
        return ProgramaCierreDTO(
            referencia_id=referencia_id,
            programa_id=programa.id,
            estado=EstadoBloque.COMPLETO,
            mensaje="Programa cerrado correctamente.",
            completitud=closed_completitud,
        )

    async def _get_program_draft(self, referencia_id: uuid.UUID) -> BorradorSesion:
        draft = await self._draft_repository.get_by_block_reference(
            TipoBloqueBorrador.PROGRAMA,
            referencia_id,
        )
        if draft is None:
            raise ProgramaCierreDraftNotFoundError(
                "No existe un borrador de programa para la referencia dada",
            )
        return draft

    async def _get_programa_from_draft(
        self,
        draft: BorradorSesion,
    ) -> ProgramaFormacion | None:
        programa_id = _extract_programa_id(draft.payload_json)
        if programa_id is None:
            return None
        return await self._programa_repository.get_programa_with_curriculum(programa_id)


def _extract_programa_id(payload: dict[str, object]) -> uuid.UUID | None:
    curricular = payload.get("curricular")
    if not isinstance(curricular, dict):
        return None
    raw_programa_id = curricular.get("programa_formacion_id")
    if not isinstance(raw_programa_id, str) or not raw_programa_id:
        return None
    try:
        return uuid.UUID(raw_programa_id)
    except ValueError:
        return None


def _extract_program_base(
    payload: dict[str, object],
    programa: ProgramaFormacion | None,
) -> tuple[str, str]:
    if programa is not None:
        return programa.codigo_programa.strip(), programa.nombre_programa.strip()

    draft_programa = payload.get("programa")
    if not isinstance(draft_programa, dict):
        return "", ""
    raw_codigo = draft_programa.get("codigo_programa")
    raw_nombre = draft_programa.get("nombre_programa")
    return (
        raw_codigo.strip() if isinstance(raw_codigo, str) else "",
        raw_nombre.strip() if isinstance(raw_nombre, str) else "",
    )


def _global_curricular_missing(
    *,
    total_resultados: int,
    total_saber: int,
    total_proceso: int,
    total_criterios: int,
) -> list[ProgramaCompletitudFaltanteDTO]:
    faltantes: list[ProgramaCompletitudFaltanteDTO] = []
    if total_resultados == 0:
        faltantes.append(
            _missing(
                codigo="programa.resultados",
                campo="resultados",
                mensaje="El programa debe tener al menos un resultado de aprendizaje.",
            )
        )
    if total_saber == 0:
        faltantes.append(
            _missing(
                codigo="programa.conocimientos_saber",
                campo="conocimientos_saber",
                mensaje="El programa debe tener al menos un conocimiento SABER.",
            )
        )
    if total_proceso == 0:
        faltantes.append(
            _missing(
                codigo="programa.conocimientos_proceso",
                campo="conocimientos_proceso",
                mensaje="El programa debe tener al menos un conocimiento PROCESO.",
            )
        )
    if total_criterios == 0:
        faltantes.append(
            _missing(
                codigo="programa.criterios",
                campo="criterios",
                mensaje="El programa debe tener al menos un criterio de evaluacion.",
            )
        )
    return faltantes


def _missing(
    *,
    codigo: str,
    campo: str,
    mensaje: str,
) -> ProgramaCompletitudFaltanteDTO:
    return ProgramaCompletitudFaltanteDTO(
        codigo=codigo,
        campo=campo,
        mensaje=mensaje,
    )


def _missing_for_competencia(
    competencia: Competencia,
    codigo: str,
    campo: str,
    mensaje: str,
) -> ProgramaCompletitudFaltanteDTO:
    return ProgramaCompletitudFaltanteDTO(
        codigo=codigo,
        campo=campo,
        mensaje=mensaje,
        competencia_id=competencia.id,
        competencia_codigo=competencia.codigo_competencia,
        competencia_nombre=competencia.nombre_competencia,
    )


def _is_practical_stage_competence(competencia: Competencia) -> bool:
    normalized_name = _normalize_text(competencia.nombre_competencia)
    normalized_code = competencia.codigo_competencia.strip()
    return (
        normalized_code == "999999999"
        or "etapa practica" in normalized_name
        or "etapa productiva" in normalized_name
    )


def _normalize_text(value: str) -> str:
    without_accents = "".join(
        char
        for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", without_accents).strip().lower()


def _touch_review_step(payload: dict[str, object]) -> dict[str, object]:
    next_payload = deepcopy(payload)
    meta = next_payload.get("meta")
    if not isinstance(meta, dict):
        meta = {}
    touched_steps = meta.get("touchedSteps")
    if isinstance(touched_steps, list):
        next_steps = [item for item in touched_steps if isinstance(item, str)]
    else:
        next_steps = []
    if "revision-programa" not in next_steps:
        next_steps.append("revision-programa")
    meta["touchedSteps"] = next_steps
    meta["lastInteractionAt"] = datetime.now(UTC).isoformat()
    next_payload["meta"] = meta
    return next_payload
