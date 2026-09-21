"""HTTP endpoints for project PDF evidence upload."""

from __future__ import annotations

import io
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.access_scope import AccessScopeService
from src.application.services.proyecto_documentos import (
    InvalidProjectPdfUploadError,
    ProjectDocumentService,
    ProjectDraftMissingError,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.drafts import DraftRepository
from src.infrastructure.storage.document_storage import MinioDocumentStorageService
from src.interfaces.http.deps import get_access_scope_service, get_current_user
from src.interfaces.http.schemas.proyecto_documentos import (
    ProyectoPdfUploadResponse,
)

router = APIRouter(prefix="/api/v1/proyectos", tags=["proyectos"])


def get_proyecto_document_service(
    session: AsyncSession = Depends(get_async_session),
    settings: Settings = Depends(get_settings),
) -> ProjectDocumentService:
    """Build the project document service using request-scoped dependencies."""
    return ProjectDocumentService(
        session=session,
        draft_repository=DraftRepository(session),
        audit_repository=AuditRepository(session),
        storage_service=MinioDocumentStorageService(settings),
    )


@router.post(
    "/{referencia_id}/documentos/proyecto-pdf",
    response_model=ProyectoPdfUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_project_pdf(
    referencia_id: uuid.UUID,
    file: UploadFile = File(...),
    service: ProjectDocumentService = Depends(get_proyecto_document_service),
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> ProyectoPdfUploadResponse:
    """Upload a project PDF, store it as evidence and return metadata."""
    await scope_service.require_process_access(current_user, referencia_id)
    filename = file.filename or ""
    content_type = file.content_type or "application/octet-stream"
    content = await file.read()

    try:
        result = await service.upload_and_store_project_pdf(
            referencia_id=referencia_id,
            filename=filename,
            content_type=content_type,
            content=content,
        )
    except ProjectDraftMissingError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except InvalidProjectPdfUploadError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    return ProyectoPdfUploadResponse.model_validate(result)


@router.get(
    "/{referencia_id}/documentos/proyecto-pdf",
    status_code=status.HTTP_200_OK,
)
async def download_project_pdf(
    referencia_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    settings: Settings = Depends(get_settings),
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> StreamingResponse:
    """Download stored project PDF evidence, enforcing strict process scope."""
    await scope_service.require_process_access(current_user, referencia_id)


    draft_repo = DraftRepository(session)
    draft = await draft_repo.get_by_block_reference(
        TipoBloqueBorrador.PROYECTO,
        referencia_id,
    )
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un borrador de proyecto para esta referencia",
        )

    from typing import Any, cast
    payload = cast(dict[str, Any], draft.payload_json or {})
    doc_info = payload.get("documental", {}).get("proyecto_pdf", {}).get("documento", {})
    storage_key = doc_info.get("storage_key")
    filename = doc_info.get("original_filename") or "proyecto-formativo.pdf"

    if not storage_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El proyecto no tiene un archivo PDF de evidencia cargado",
        )

    storage = MinioDocumentStorageService(settings)
    try:
        content = await storage.read_pdf(key=storage_key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se pudo recuperar el archivo PDF: {exc}",
        ) from exc

    safe_filename = filename.replace('"', "")
    encoded_filename = quote(filename, safe="")
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{safe_filename}"; '
                f"filename*=UTF-8''{encoded_filename}"
            )
        },
    )

