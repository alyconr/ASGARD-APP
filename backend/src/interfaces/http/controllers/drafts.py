"""HTTP endpoints for draft autosave and recovery."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.drafts import SaveDraftCommand
from src.application.services.drafts import DraftNotFoundError, DraftService
from src.domain.drafts.types import TipoBloqueBorrador
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.drafts import DraftRepository
from src.interfaces.http.schemas.drafts import (
    DraftResponse,
    DraftSaveRequest,
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
