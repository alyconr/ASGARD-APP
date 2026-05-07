"""HTTP endpoints for canonical Excel preview and import."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.programa_excel import (
    InvalidProgramaExcelUploadError,
    ProgramaExcelDraftMissingError,
    ProgramaExcelImportService,
    ProgramaExcelMissingPreviewError,
    ProgramaExcelStorageMissingError,
    ProgramaExcelValidationError,
)
from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.drafts import DraftRepository
from src.infrastructure.repositories.programa_excel import (
    ProgramaExcelImportRepository,
)
from src.infrastructure.storage.document_storage import MinioDocumentStorageService
from src.interfaces.http.schemas.programa_excel import (
    ProgramaExcelImportResponse,
    ProgramaExcelPreviewResponse,
)

router = APIRouter(prefix="/api/v1/programas", tags=["programas"])


def get_programa_excel_service(
    session: AsyncSession = Depends(get_async_session),
    settings: Settings = Depends(get_settings),
) -> ProgramaExcelImportService:
    """Build the Excel import service with request-scoped dependencies."""
    return ProgramaExcelImportService(
        session=session,
        draft_repository=DraftRepository(session),
        audit_repository=AuditRepository(session),
        curriculum_repository=ProgramaExcelImportRepository(session),
        storage_service=MinioDocumentStorageService(settings),
    )


@router.post(
    "/{referencia_id}/documentos/programa-excel/preview",
    response_model=ProgramaExcelPreviewResponse,
    status_code=status.HTTP_200_OK,
)
async def preview_program_excel(
    referencia_id: uuid.UUID,
    file: UploadFile = File(...),
    service: ProgramaExcelImportService = Depends(get_programa_excel_service),
) -> ProgramaExcelPreviewResponse:
    """Validate and store a canonical Excel workbook for preview."""
    filename = file.filename or ""
    content_type = file.content_type or "application/octet-stream"
    content = await file.read()

    try:
        result = await service.preview_program_excel(
            referencia_id=referencia_id,
            filename=filename,
            content_type=content_type,
            content=content,
        )
    except ProgramaExcelDraftMissingError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except InvalidProgramaExcelUploadError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    return ProgramaExcelPreviewResponse.model_validate(result)


@router.post(
    "/{referencia_id}/documentos/programa-excel/importacion",
    response_model=ProgramaExcelImportResponse,
)
async def confirm_program_excel_import(
    referencia_id: uuid.UUID,
    service: ProgramaExcelImportService = Depends(get_programa_excel_service),
) -> ProgramaExcelImportResponse:
    """Confirm and materialize the previously previewed canonical Excel."""
    try:
        result = await service.confirm_program_excel_import(
            referencia_id=referencia_id,
        )
    except ProgramaExcelDraftMissingError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ProgramaExcelMissingPreviewError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except ProgramaExcelStorageMissingError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except ProgramaExcelValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    return ProgramaExcelImportResponse.model_validate(result)
