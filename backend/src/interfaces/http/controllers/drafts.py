"""HTTP endpoints for draft autosave and recovery."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.drafts import SaveDraftCommand
from src.application.services.drafts import DraftNotFoundError, DraftService
from src.domain.drafts.types import TipoBloqueBorrador
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.drafts import DraftRepository
from src.interfaces.http.schemas.drafts import (
    DraftResponse,
    DraftSaveRequest,
    SaveDraftInput,
    EstadoDocumentalResponse,
    DocumentoMetadataDTO,
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
) -> DraftResponse:
    """Create or update the draft for a program or project reference."""
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
) -> EstadoDocumentalResponse:
    """Return the structured document state for program and project drafts."""
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

    if prog_draft is not None:
        doc_payload = prog_draft.payload_json.get("documental") or {}
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
        doc_payload = proj_draft.payload_json.get("documental") or {}
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
) -> DraftResponse:
    """Return the draft persisted for the requested block and reference."""
    try:
        draft = await service.get_draft(tipo_bloque, referencia_id)
    except DraftNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return DraftResponse.model_validate(draft)
