"""HTTP endpoints for project PDF evidence upload."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.access_scope import AccessScopeService
from src.application.services.proyecto_documentos import (
    InvalidProjectPdfUploadError,
    ProjectDocumentService,
    ProjectDraftMissingError,
)
from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.drafts import DraftRepository
from src.infrastructure.storage.document_storage import MinioDocumentStorageService
from src.interfaces.http.deps import get_access_scope_service, get_optional_current_user
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
    current_user: Usuario | None = Depends(get_optional_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> ProyectoPdfUploadResponse:
    """Upload a project PDF, store it as evidence and return metadata."""
    if current_user is not None:
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
