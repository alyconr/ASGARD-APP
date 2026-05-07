"""HTTP endpoints for program PDF evidence upload and diagnosis."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.pdf_diagnostics import (
    InvalidPdfError,
    PdfLegibilityDiagnosticService,
)
from src.application.services.programa_documentos import (
    InvalidProgramPdfUploadError,
    ProgramaDocumentService,
    ProgramaDraftMissingError,
)
from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.drafts import DraftRepository
from src.infrastructure.storage.document_storage import MinioDocumentStorageService
from src.interfaces.http.schemas.programa_documentos import (
    ProgramaPdfUploadResponse,
)

router = APIRouter(prefix="/api/v1/programas", tags=["programas"])


def get_programa_document_service(
    session: AsyncSession = Depends(get_async_session),
    settings: Settings = Depends(get_settings),
) -> ProgramaDocumentService:
    """Build the program document service using request-scoped dependencies."""
    return ProgramaDocumentService(
        session=session,
        draft_repository=DraftRepository(session),
        audit_repository=AuditRepository(session),
        storage_service=MinioDocumentStorageService(settings),
        diagnostic_service=PdfLegibilityDiagnosticService(),
    )


@router.post(
    "/{referencia_id}/documentos/programa-pdf",
    response_model=ProgramaPdfUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_program_pdf(
    referencia_id: uuid.UUID,
    file: UploadFile = File(...),
    service: ProgramaDocumentService = Depends(get_programa_document_service),
) -> ProgramaPdfUploadResponse:
    """Upload a program PDF, store it and return a legibility diagnosis."""
    filename = file.filename or ""
    content_type = file.content_type or "application/octet-stream"
    content = await file.read()

    try:
        result = await service.upload_and_diagnose_program_pdf(
            referencia_id=referencia_id,
            filename=filename,
            content_type=content_type,
            content=content,
        )
    except ProgramaDraftMissingError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (InvalidProgramPdfUploadError, InvalidPdfError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    return ProgramaPdfUploadResponse.model_validate(result)
