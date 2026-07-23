"""Service for project completion validation and explicit closing."""

from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import UTC, datetime
from typing import Protocol

from src.application.dto.proyecto_cierre import (
    ProyectoCierreDTO,
    ProyectoCompletitudDTO,
    ProyectoCompletitudFaltanteDTO,
    ProyectoCompletitudResumenDTO,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.proyecto import FaseProyecto, ProyectoFormativo


class ProyectoCierreError(Exception):
    """Base exception for project closing errors."""


class ProyectoCierreDraftNotFoundError(ProyectoCierreError):
    """Raised when there is no project draft for the requested reference."""


class ProyectoCierreValidationError(ProyectoCierreError):
    """Raised when an explicit close is attempted on an incomplete project."""

    def __init__(self, completitud: ProyectoCompletitudDTO) -> None:
        """Store the structured validation result for HTTP and UI callers."""
        super().__init__("El proyecto no cumple la estructura minima de cierre")
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


class ProyectoCierreRepositoryProtocol(Protocol):
    """Project aggregate persistence required by the closing service."""

    async def get_project_with_structure(
        self,
        proyecto_id: uuid.UUID,
    ) -> ProyectoFormativo | None:
        """Return a project with phases and activities loaded."""

    async def save_project(self, proyecto: ProyectoFormativo) -> ProyectoFormativo:
        """Persist project changes."""


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


class ProyectoCierreService:
    """Validate project completeness and close the project on explicit request."""

    def __init__(
        self,
        session: AsyncSessionProtocol,
        draft_repository: DraftRepositoryProtocol,
        proyecto_repository: ProyectoCierreRepositoryProtocol,
        audit_repository: AuditRepositoryProtocol,
    ) -> None:
        """Initialize the service with explicit infrastructure ports."""
        self._session = session
        self._draft_repository = draft_repository
        self._proyecto_repository = proyecto_repository
        self._audit_repository = audit_repository

    async def validar_completitud(
        self,
        referencia_id: uuid.UUID,
    ) -> ProyectoCompletitudDTO:
        """Return a structured explanation of whether the project can close."""
        draft = await self._get_project_draft(referencia_id)
        proyecto_id = _extract_project_id(draft.payload_json)
        proyecto = (
            await self._proyecto_repository.get_project_with_structure(proyecto_id)
            if proyecto_id is not None
            else None
        )

        fases = sorted(
            proyecto.fases if proyecto is not None else [],
            key=lambda item: (item.orden is None, item.orden or 0),
        )
        faltantes: list[ProyectoCompletitudFaltanteDTO] = []

        if proyecto is None:
            faltantes.append(
                _missing(
                    codigo="proyecto.importacion",
                    campo="proyecto_formativo_id",
                    mensaje="Importa y confirma la matriz Excel del proyecto.",
                )
            )
        else:
            documental = draft.payload_json.get("documental") or {}
            proyecto_pdf = documental.get("proyecto_pdf")
            has_pdf = (
                isinstance(proyecto_pdf, dict)
                and proyecto_pdf.get("documento") is not None
            )
            if not has_pdf:
                faltantes.append(
                    _missing(
                        codigo="proyecto.documental.proyecto_pdf",
                        campo="proyecto_pdf",
                        mensaje="El PDF de evidencia del proyecto es obligatorio.",
                    )
                )

            if proyecto.programa.estado != EstadoBloque.COMPLETO:
                faltantes.append(
                    _missing(
                        codigo="proyecto.programa",
                        campo="programa_id",
                        mensaje="El programa asociado debe estar en estado COMPLETO.",
                    )
                )
            if not proyecto.codigo_proyecto.strip():
                faltantes.append(
                    _missing(
                        codigo="proyecto.codigo_proyecto",
                        campo="codigo_proyecto",
                        mensaje="El codigo del proyecto es obligatorio para cerrar.",
                    )
                )
            if not proyecto.nombre_proyecto.strip():
                faltantes.append(
                    _missing(
                        codigo="proyecto.nombre_proyecto",
                        campo="nombre_proyecto",
                        mensaje="El nombre del proyecto es obligatorio para cerrar.",
                    )
                )
            if not proyecto.version_proyecto.strip():
                faltantes.append(
                    _missing(
                        codigo="proyecto.version_proyecto",
                        campo="version_proyecto",
                        mensaje="La version del proyecto es obligatoria para cerrar.",
                    )
                )

        total_actividades = 0
        if not fases:
            faltantes.append(
                _missing(
                    codigo="proyecto.fases",
                    campo="fases",
                    mensaje="Registra al menos una fase del proyecto.",
                )
            )

        for fase in fases:
            actividades = [
                actividad
                for actividad in fase.actividades
                if actividad.descripcion.strip()
            ]
            total_actividades += len(actividades)
            if not fase.nombre_fase.strip():
                faltantes.append(
                    _missing_for_fase(
                        fase,
                        "proyecto.fase.nombre_fase",
                        "nombre_fase",
                        "La fase debe tener nombre.",
                    )
                )
            if not actividades:
                faltantes.append(
                    _missing_for_fase(
                        fase,
                        "proyecto.fase.actividades",
                        "actividades",
                        "Cada fase debe tener al menos una actividad.",
                    )
                )

        resumen = ProyectoCompletitudResumenDTO(
            fases=len(fases),
            actividades=total_actividades,
        )
        return ProyectoCompletitudDTO(
            referencia_id=referencia_id,
            proyecto_id=proyecto.id if proyecto is not None else None,
            estado_actual=proyecto.estado if proyecto is not None else None,
            cerrable=len(faltantes) == 0,
            resumen=resumen,
            faltantes=faltantes,
        )

    async def cerrar_proyecto(self, referencia_id: uuid.UUID) -> ProyectoCierreDTO:
        """Close a project only after successful structured validation."""
        draft = await self._get_project_draft(referencia_id)
        completitud = await self.validar_completitud(referencia_id)
        if not completitud.cerrable or completitud.proyecto_id is None:
            raise ProyectoCierreValidationError(completitud)

        proyecto = await self._proyecto_repository.get_project_with_structure(
            completitud.proyecto_id,
        )
        if proyecto is None:
            raise ProyectoCierreValidationError(completitud)

        proyecto.estado = EstadoBloque.COMPLETO
        draft.estado_borrador = EstadoBloque.COMPLETO
        draft.paso_actual = "revision-proyecto"
        draft.payload_json = _touch_review_step(draft.payload_json)
        await self._proyecto_repository.save_project(proyecto)
        await self._draft_repository.save(draft)
        await self._audit_repository.add_event(
            entidad="ProyectoFormativo",
            entidad_id=proyecto.id,
            accion="PROYECTO_CERRADO",
            detalle={
                "referencia_id": str(referencia_id),
                "estado": EstadoBloque.COMPLETO.value,
            },
        )
        await self._session.commit()
        await self._session.refresh(proyecto)
        await self._session.refresh(draft)

        closed_completitud = ProyectoCompletitudDTO(
            referencia_id=completitud.referencia_id,
            proyecto_id=completitud.proyecto_id,
            estado_actual=EstadoBloque.COMPLETO,
            cerrable=True,
            resumen=completitud.resumen,
            faltantes=[],
        )
        return ProyectoCierreDTO(
            referencia_id=referencia_id,
            proyecto_id=proyecto.id,
            estado=EstadoBloque.COMPLETO,
            mensaje="Proyecto cerrado correctamente.",
            completitud=closed_completitud,
        )

    async def _get_project_draft(self, referencia_id: uuid.UUID) -> BorradorSesion:
        draft = await self._draft_repository.get_by_block_reference(
            TipoBloqueBorrador.PROYECTO,
            referencia_id,
        )
        if draft is None:
            raise ProyectoCierreDraftNotFoundError(
                "No existe un borrador de proyecto para la referencia dada",
            )
        return draft


def _extract_project_id(payload: dict[str, object]) -> uuid.UUID | None:
    proyecto = _as_record(payload.get("proyecto")) or {}
    raw_project_id = proyecto.get("proyecto_formativo_id")
    if raw_project_id:
        return uuid.UUID(str(raw_project_id))

    documental = _as_record(payload.get("documental")) or {}
    fuente = _as_record(documental.get("fuente_estructurada")) or {}
    confirmacion = _as_record(fuente.get("confirmacion")) or {}
    raw_project_id = confirmacion.get("proyecto_id")
    if raw_project_id:
        return uuid.UUID(str(raw_project_id))
    return None


def _as_record(value: object) -> dict[str, object] | None:
    return value if isinstance(value, dict) else None


def _missing(
    *,
    codigo: str,
    campo: str,
    mensaje: str,
) -> ProyectoCompletitudFaltanteDTO:
    return ProyectoCompletitudFaltanteDTO(
        codigo=codigo,
        campo=campo,
        mensaje=mensaje,
    )


def _missing_for_fase(
    fase: FaseProyecto,
    codigo: str,
    campo: str,
    mensaje: str,
) -> ProyectoCompletitudFaltanteDTO:
    return ProyectoCompletitudFaltanteDTO(
        codigo=codigo,
        campo=campo,
        mensaje=mensaje,
        fase_id=fase.id,
        fase_nombre=fase.nombre_fase,
    )


def _touch_review_step(payload: dict[str, object]) -> dict[str, object]:
    next_payload = deepcopy(payload)
    now = datetime.now(UTC).isoformat()
    meta = _as_record(next_payload.get("meta")) or {}
    touched_steps = list(meta.get("touchedSteps") or [])
    if "revision-proyecto" not in touched_steps:
        touched_steps.append("revision-proyecto")
    next_payload["meta"] = {
        **meta,
        "lastInteractionAt": now,
        "touchedSteps": touched_steps,
    }
    proyecto = _as_record(next_payload.get("proyecto")) or {}
    next_payload["proyecto"] = {
        **proyecto,
        "estado": EstadoBloque.COMPLETO.value,
    }
    return next_payload
