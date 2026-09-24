"""HTTP endpoints for draft autosave and recovery."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.dto.drafts import SaveDraftCommand
from src.application.services.access_scope import AccessScopeService
from src.application.services.drafts import DraftNotFoundError, DraftService
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoEquipo, RolUsuario
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.organizacion import EquipoEjecutor, ProcesoCurricular
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.drafts import DraftRepository
from src.interfaces.http.deps import get_access_scope_service, get_current_user
from src.interfaces.http.schemas.drafts import (
    DocumentoMetadataDTO,
    DraftResponse,
    DraftSaveRequest,
    EstadoDocumentalResponse,
    SaveDraftInput,
)

router = APIRouter(prefix="/api/v1/drafts", tags=["drafts"])


def get_draft_service(
    session: AsyncSession = Depends(get_async_session),
) -> DraftService:
    """Build the draft service using request-scoped dependencies."""
    draft_repository = DraftRepository(session)
    audit_repository = AuditRepository(session)
    return DraftService(session, draft_repository, audit_repository)


@router.put(
    "/{tipo_bloque}/{referencia_id}",
    response_model=DraftResponse,
    status_code=status.HTTP_200_OK,
)
async def save_draft(
    tipo_bloque: TipoBloqueBorrador,
    referencia_id: uuid.UUID,
    request: DraftSaveRequest,
    service: DraftService = Depends(get_draft_service),
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> DraftResponse:
    """Create or update the draft for a program or project reference."""
    if hasattr(scope_service, "_session") and scope_service._session is not None:
        stmt = (
            select(ProcesoCurricular)
            .where(ProcesoCurricular.referencia_id == referencia_id)
            .options(
                selectinload(ProcesoCurricular.equipo_ejecutor).selectinload(
                    EquipoEjecutor.miembros
                )
            )
        )
        proc_res = await scope_service._session.execute(stmt)
        existing_proc = proc_res.scalar_one_or_none()

        if existing_proc is not None:
            can_access = await scope_service.can_access_process(current_user, referencia_id)
            if not can_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "EXECUTOR_TEAM_MEMBERSHIP_REQUIRED",
                        "message": "Debes pertenecer al Equipo Ejecutor para modificar este proceso curricular.",
                    },
                )
        else:
            if not request.equipo_ejecutor_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "EXECUTOR_TEAM_MEMBERSHIP_REQUIRED",
                        "message": "Debes especificar un Equipo Ejecutor válido para iniciar este proceso curricular.",
                    },
                )

            team = await scope_service.require_start_curricular_process(
                current_user,
                request.equipo_ejecutor_id,
            )

            await scope_service.ensure_proceso_for_referencia(
                referencia_id=referencia_id,
                creado_por=current_user.id,
                coordinacion_id=team.coordinacion_id,
                especialidad_id=team.especialidad_id,
                equipo_ejecutor_id=team.id,
                lider_id=team.lider_id,
            )

    try:
        payload = SaveDraftInput(
            tipo_bloque=tipo_bloque,
            referencia_id=referencia_id,
            paso_actual=request.paso_actual,
            payload_json=request.payload_json,
            estado_borrador=request.estado_borrador,
        )
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from error

    draft = await service.save_draft(
        SaveDraftCommand(
            tipo_bloque=payload.tipo_bloque,
            referencia_id=payload.referencia_id,
            paso_actual=payload.paso_actual,
            payload_json=payload.payload_json,
            estado_borrador=payload.estado_borrador,
        ),
    )
    return DraftResponse.model_validate(draft)


@router.get(
    "/{referencia_id}/estado-documental",
    response_model=EstadoDocumentalResponse,
    status_code=status.HTTP_200_OK,
)
async def get_estado_documental(
    referencia_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> EstadoDocumentalResponse:
    """Return the structured document state for program and project drafts."""
    can_access = await scope_service.can_access_process(current_user, referencia_id)
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes autorización para acceder a los documentos de este proceso",
        )

    # Query program draft

    prog_statement = select(BorradorSesion).where(
        BorradorSesion.referencia_id == referencia_id,
        BorradorSesion.tipo_bloque == "PROGRAMA",
    )
    prog_result = await session.execute(prog_statement)
    prog_draft = prog_result.scalar_one_or_none()

    # Query project draft
    proj_statement = select(BorradorSesion).where(
        BorradorSesion.referencia_id == referencia_id,
        BorradorSesion.tipo_bloque == "PROYECTO",
    )
    proj_result = await session.execute(proj_statement)
    proj_draft = proj_result.scalar_one_or_none()

    prog_excel_dto = None
    prog_pdf_dto = None
    prog_imported = False

    proj_excel_dto = None
    proj_pdf_dto = None
    proj_imported = False
    cargue_pdf_habilitado = False

    from typing import Any, cast

    if prog_draft is not None:
        payload_dict = cast(dict[str, Any], prog_draft.payload_json)
        doc_payload = payload_dict.get("documental") or {}
        # Program Excel
        excel_data = doc_payload.get("programa_excel") or {}
        doc_info = excel_data.get("documento")
        if doc_info:
            prog_excel_dto = DocumentoMetadataDTO(
                original_filename=doc_info.get("original_filename") or "",
                storage_key=doc_info.get("storage_key") or "",
                size_bytes=int(doc_info.get("size_bytes") or 0),
                content_type=doc_info.get("content_type") or "",
                checksum_sha256=doc_info.get("checksum_sha256") or "",
                updated_at=excel_data.get("updated_at"),
            )
        prog_imported = excel_data.get("confirmacion", {}).get("estado") == "IMPORTADO"

        # Program PDF
        pdf_data = doc_payload.get("programa_pdf") or {}
        doc_info = pdf_data.get("documento")
        if doc_info:
            prog_pdf_dto = DocumentoMetadataDTO(
                original_filename=doc_info.get("original_filename") or "",
                storage_key=doc_info.get("storage_key") or "",
                size_bytes=int(doc_info.get("size_bytes") or 0),
                content_type=doc_info.get("content_type") or "",
                checksum_sha256=doc_info.get("checksum_sha256") or "",
                updated_at=pdf_data.get("updated_at"),
            )

    if proj_draft is not None:
        payload_dict = cast(dict[str, Any], proj_draft.payload_json)
        doc_payload = payload_dict.get("documental") or {}
        # Project Excel
        excel_data = doc_payload.get("fuente_estructurada") or {}
        doc_info = excel_data.get("documento")
        if doc_info:
            proj_excel_dto = DocumentoMetadataDTO(
                original_filename=doc_info.get("original_filename") or "",
                storage_key=doc_info.get("storage_key") or "",
                size_bytes=int(doc_info.get("size_bytes") or 0),
                content_type=doc_info.get("content_type") or "",
                checksum_sha256=doc_info.get("checksum_sha256") or "",
                updated_at=excel_data.get("updated_at"),
            )
        proj_imported = excel_data.get("confirmacion", {}).get("estado") == "IMPORTADO"

        # Project PDF
        pdf_data = doc_payload.get("proyecto_pdf") or {}
        doc_info = pdf_data.get("documento")
        if doc_info:
            proj_pdf_dto = DocumentoMetadataDTO(
                original_filename=doc_info.get("original_filename") or "",
                storage_key=doc_info.get("storage_key") or "",
                size_bytes=int(doc_info.get("size_bytes") or 0),
                content_type=doc_info.get("content_type") or "",
                checksum_sha256=doc_info.get("checksum_sha256") or "",
                updated_at=pdf_data.get("updated_at"),
            )

        cargue_pdf_habilitado = bool(doc_payload.get("cargue_pdf_habilitado", False))

    documentos_habilitados = prog_imported and proj_imported

    return EstadoDocumentalResponse(
        programa_excel=prog_excel_dto,
        proyecto_excel=proj_excel_dto,
        programa_pdf=prog_pdf_dto,
        proyecto_pdf=proj_pdf_dto,
        programa_importado=prog_imported,
        proyecto_importado=proj_imported,
        documentos_habilitados=documentos_habilitados,
        cargue_pdf_habilitado=cargue_pdf_habilitado,
    )


@router.get(
    "/{tipo_bloque}/{referencia_id}",
    response_model=DraftResponse,
    status_code=status.HTTP_200_OK,
)
async def get_draft(
    tipo_bloque: TipoBloqueBorrador,
    referencia_id: uuid.UUID,
    service: DraftService = Depends(get_draft_service),
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> DraftResponse:
    """Return the draft persisted for the requested block and reference."""
    can_access = await scope_service.can_access_process(current_user, referencia_id)
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes autorización para acceder a este borrador",
        )

    try:

        draft = await service.get_draft(tipo_bloque, referencia_id)
    except DraftNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return DraftResponse.model_validate(draft)

