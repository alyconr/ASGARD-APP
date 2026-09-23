"""HTTP endpoints for canonical Excel preview and import."""

from __future__ import annotations

import io
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.access_scope import AccessScopeService
from src.application.services.planeacion_formato_excel import EXCEL_CONTENT_TYPE
from src.application.services.programa_excel import (
    InvalidProgramaExcelUploadError,
    ProgramaExcelDraftMissingError,
    ProgramaExcelImportService,
    ProgramaExcelMissingPreviewError,
    ProgramaExcelStorageMissingError,
    ProgramaExcelValidationError,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.drafts import DraftRepository
from src.infrastructure.repositories.programa_excel import (
    ProgramaExcelImportRepository,
)
from src.infrastructure.storage.document_storage import MinioDocumentStorageService
from src.interfaces.http.deps import get_access_scope_service, get_current_user
from src.interfaces.http.schemas.programa_excel import (
    ProgramaExcelImportResponse,
    ProgramaExcelPrevalidationResponse,
    ProgramaExcelPreviewResponse,
)

router = APIRouter(prefix="/api/v1/programas", tags=["programas"])


def get_programa_excel_service(
    session: AsyncSession = Depends(get_async_session),
    settings: Settings = Depends(get_settings),
) -> ProgramaExcelImportService:
    """Build the program Excel import service using request-scoped dependencies."""
    return ProgramaExcelImportService(
        session=session,
        draft_repository=DraftRepository(session),
        audit_repository=AuditRepository(session),
        curriculum_repository=ProgramaExcelImportRepository(session),
        storage_service=MinioDocumentStorageService(settings),
    )


@router.post(
    "/{referencia_id}/documentos/programa-excel/prevalidate",
    response_model=ProgramaExcelPrevalidationResponse,
    status_code=status.HTTP_200_OK,
)
async def prevalidate_program_excel(
    referencia_id: uuid.UUID,
    file: UploadFile = File(...),
    service: ProgramaExcelImportService = Depends(get_programa_excel_service),
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> ProgramaExcelPrevalidationResponse:
    """Fast prevalidation of the canonical Excel workbook against authorized programs."""
    await scope_service.require_process_access(current_user, referencia_id)

    filename = file.filename or ""
    content = await file.read()

    try:
        result = await service.prevalidate_program_excel(
            referencia_id=referencia_id,
            filename=filename,
            content=content,
            user=current_user,
        )
    except InvalidProgramaExcelUploadError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    return ProgramaExcelPrevalidationResponse.model_validate(result)


@router.post(
    "/{referencia_id}/documentos/programa-excel/preview",
    response_model=ProgramaExcelPreviewResponse,
    status_code=status.HTTP_200_OK,
)
async def preview_program_excel(
    referencia_id: uuid.UUID,
    file: UploadFile = File(...),
    service: ProgramaExcelImportService = Depends(get_programa_excel_service),
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> ProgramaExcelPreviewResponse:
    """Validate and store a canonical Excel workbook for preview."""
    await scope_service.require_process_access(current_user, referencia_id)

    filename = file.filename or ""
    content_type = file.content_type or "application/octet-stream"
    content = await file.read()

    try:
        result = await service.preview_program_excel(
            referencia_id=referencia_id,
            filename=filename,
            content_type=content_type,
            content=content,
            user=current_user,
        )
    except ProgramaExcelDraftMissingError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (InvalidProgramaExcelUploadError, ProgramaExcelValidationError) as error:
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
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> ProgramaExcelImportResponse:
    """Confirm and materialize the previously previewed canonical Excel."""
    await scope_service.require_process_access(current_user, referencia_id)

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


@router.get(
    "/{referencia_id}/documentos/programa-excel",
    status_code=status.HTTP_200_OK,
)
async def download_program_excel(
    referencia_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    settings: Settings = Depends(get_settings),
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> StreamingResponse:
    """Download stored program Excel workbook, enforcing strict process scope."""
    await scope_service.require_process_access(current_user, referencia_id)

    draft_repo = DraftRepository(session)
    draft = await draft_repo.get_by_block_reference(
        TipoBloqueBorrador.PROGRAMA,
        referencia_id,
    )
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un borrador de programa para esta referencia",
        )

    from typing import Any, cast
    payload = cast(dict[str, Any], draft.payload_json or {})
    doc_info = payload.get("documental", {}).get("programa_excel", {}).get("documento", {})
    storage_key = doc_info.get("storage_key")
    filename = doc_info.get("original_filename") or "programa-matriz.xlsx"

    if not storage_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El programa no tiene una matriz Excel cargada",
        )

    storage = MinioDocumentStorageService(settings)
    try:
        content = await storage.read_excel(key=storage_key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se pudo recuperar el archivo Excel: {exc}",
        ) from exc

    safe_filename = filename.replace('"', "")
    encoded_filename = quote(filename, safe="")
    return StreamingResponse(
        io.BytesIO(content),
        media_type=EXCEL_CONTENT_TYPE,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{safe_filename}"; '
                f"filename*=UTF-8''{encoded_filename}"
            )
        },
    )

