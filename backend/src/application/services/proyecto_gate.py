"""TASK-15 service that gates project access behind a completed program."""

from __future__ import annotations

import uuid
from typing import Protocol

from src.application.dto.proyecto_gate import ProyectoDisponibilidadDTO
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque
from src.infrastructure.db.models.curriculum import ProgramaFormacion
from src.infrastructure.db.models.drafts import BorradorSesion


class ProyectoGateError(Exception):
    """Base exception for project availability errors."""


class ProyectoGateDraftNotFoundError(ProyectoGateError):
    """Raised when the requested program draft does not exist."""


class ProyectoBloqueadoError(ProyectoGateError):
    """Raised when a caller attempts to access a blocked project module."""

    def __init__(self, disponibilidad: ProyectoDisponibilidadDTO) -> None:
        """Expose the structured availability result to HTTP callers."""
        super().__init__(disponibilidad.mensaje)
        self.disponibilidad = disponibilidad


class DraftRepositoryProtocol(Protocol):
    """Draft lookup behavior required by the project gate."""

    async def get_by_block_reference(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
    ) -> BorradorSesion | None:
        """Return a draft by logical identity."""


class ProyectoGateRepositoryProtocol(Protocol):
    """Program state lookup required to decide project availability."""

    async def get_programa(
        self,
        programa_id: uuid.UUID,
    ) -> ProgramaFormacion | None:
        """Return a program by id."""


class ProyectoGateService:
    """Centralize project blocking/unblocking based on program completion."""

    def __init__(
        self,
        draft_repository: DraftRepositoryProtocol,
        proyecto_repository: ProyectoGateRepositoryProtocol,
    ) -> None:
        """Initialize the gate with explicit infrastructure ports."""
        self._draft_repository = draft_repository
        self._proyecto_repository = proyecto_repository

    async def consultar_disponibilidad(
        self,
        referencia_id: uuid.UUID,
    ) -> ProyectoDisponibilidadDTO:
        """Return whether the project module is available for a program draft."""
        project_draft = None
        draft = await self._draft_repository.get_by_block_reference(
            TipoBloqueBorrador.PROGRAMA,
            referencia_id,
        )
        if draft is None:
            # Try to resolve via project draft
            project_draft = await self._draft_repository.get_by_block_reference(
                TipoBloqueBorrador.PROYECTO,
                referencia_id,
            )
            if project_draft is not None:
                meta = project_draft.payload_json.get("meta", {})
                if isinstance(meta, dict):
                    prog_ref_str = meta.get("programaReferenciaId")
                    if prog_ref_str:
                        try:
                            prog_ref_id = uuid.UUID(str(prog_ref_str))
                            draft = await self._draft_repository.get_by_block_reference(
                                TipoBloqueBorrador.PROGRAMA,
                                prog_ref_id,
                            )
                        except ValueError:
                            pass

        if draft is None and project_draft is None:
            raise ProyectoGateDraftNotFoundError(
                "No existe un borrador de programa para la referencia dada",
            )

        programa_id = None
        if draft is not None:
            programa_id = _extract_programa_id(draft.payload_json)
        if programa_id is None and project_draft is not None:
            programa_id = _extract_programa_id(project_draft.payload_json)

        programa = (
            await self._proyecto_repository.get_programa(programa_id)
            if programa_id is not None
            else None
        )
        programa_completo = (
            programa is not None and programa.estado == EstadoBloque.COMPLETO
        ) or (draft is not None and draft.estado_borrador == EstadoBloque.COMPLETO)
        pdf_cargado = False
        if draft is not None:
            doc_payload = draft.payload_json.get("documental")
            if isinstance(doc_payload, dict):
                programa_pdf = doc_payload.get("programa_pdf")
                if isinstance(programa_pdf, dict):
                    if programa_pdf.get("documento") is not None:
                        pdf_cargado = True

        proyecto_bloqueado = not (programa_completo or pdf_cargado)
        estado_programa = (
            EstadoBloque.COMPLETO
            if programa_completo
            else (
                programa.estado
                if programa is not None
                else (
                    draft.estado_borrador
                    if draft is not None
                    else EstadoBloque.BLOQUEADO
                )
            )
        )
        return ProyectoDisponibilidadDTO(
            referencia_id=referencia_id,
            programa_id=programa.id if programa is not None else programa_id,
            estado_programa=estado_programa,
            programa_completo=programa_completo or pdf_cargado,
            proyecto_bloqueado=proyecto_bloqueado,
            estado_proyecto=(
                EstadoBloque.BORRADOR
                if not proyecto_bloqueado
                else EstadoBloque.BLOQUEADO
            ),
            motivo=(None if not proyecto_bloqueado else "PROGRAMA_NO_COMPLETO"),
            mensaje=(
                (
                    "El proyecto formativo esta habilitado porque el programa "
                    "esta COMPLETO o cuenta con el PDF de evidencia cargado."
                )
                if not proyecto_bloqueado
                else (
                    "El modulo proyecto esta bloqueado hasta que el programa "
                    "quede cerrado como COMPLETO o se cargue su PDF de soporte."
                )
            ),
            accion_sugerida=(
                "iniciar_proyecto"
                if not proyecto_bloqueado
                else "completar_y_cerrar_programa"
            ),
            programa_referencia_id=draft.referencia_id if draft is not None else None,
        )

    async def validar_acceso(
        self,
        referencia_id: uuid.UUID,
    ) -> ProyectoDisponibilidadDTO:
        """Reject project access when the associated program is not complete."""
        disponibilidad = await self.consultar_disponibilidad(referencia_id)
        if disponibilidad.proyecto_bloqueado:
            raise ProyectoBloqueadoError(disponibilidad)
        return disponibilidad

    async def _get_program_draft(self, referencia_id: uuid.UUID) -> BorradorSesion:
        draft = await self._draft_repository.get_by_block_reference(
            TipoBloqueBorrador.PROGRAMA,
            referencia_id,
        )
        if draft is None:
            raise ProyectoGateDraftNotFoundError(
                "No existe un borrador de programa para la referencia dada",
            )
        return draft


def _extract_programa_id(payload: dict[str, object]) -> uuid.UUID | None:
    meta = payload.get("meta")
    if isinstance(meta, dict):
        parsed_programa_id = _parse_uuid(meta.get("programaId"))
        if parsed_programa_id is not None:
            return parsed_programa_id

    curricular = payload.get("curricular")
    if isinstance(curricular, dict):
        parsed_programa_id = _parse_uuid(curricular.get("programa_formacion_id"))
        if parsed_programa_id is not None:
            return parsed_programa_id

    documental = payload.get("documental")
    if not isinstance(documental, dict):
        return None
    programa_excel = documental.get("programa_excel")
    if not isinstance(programa_excel, dict):
        return None
    confirmacion = programa_excel.get("confirmacion")
    if not isinstance(confirmacion, dict):
        return None
    return _parse_uuid(confirmacion.get("programa_id"))


def _parse_uuid(value: object) -> uuid.UUID | None:
    raw_programa_id = value
    if not isinstance(raw_programa_id, str) or not raw_programa_id:
        return None
    try:
        return uuid.UUID(raw_programa_id)
    except ValueError:
        return None
