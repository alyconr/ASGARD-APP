"""HTTP endpoints for TASK-14 program completion validation and closing."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.programa_cierre import (
    ProgramaCierreDraftNotFoundError,
    ProgramaCierreService,
    ProgramaCierreValidationError,
)
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.drafts import DraftRepository
from src.infrastructure.repositories.programa_cierre import ProgramaCierreRepository
from src.interfaces.http.schemas.programa_cierre import (
    ProgramaCierreResponse,
    ProgramaCompletitudResponse,
)

router = APIRouter(prefix="/api/v1/programas", tags=["programa-cierre"])


def get_programa_cierre_service(
    session: AsyncSession = Depends(get_async_session),
) -> ProgramaCierreService:
    """Build the program close service using request-scoped dependencies."""
    return ProgramaCierreService(
        session=session,
        draft_repository=DraftRepository(session),
        programa_repository=ProgramaCierreRepository(session),
        audit_repository=AuditRepository(session),
    )


@router.get(
    "/{referencia_id}/completitud",
    response_model=ProgramaCompletitudResponse,
    status_code=status.HTTP_200_OK,
)
async def validar_completitud_programa(
    referencia_id: uuid.UUID,
    service: ProgramaCierreService = Depends(get_programa_cierre_service),
) -> ProgramaCompletitudResponse:
    """Return structured readiness details for closing a program."""
    try:
        result = await service.validar_completitud(referencia_id)
    except ProgramaCierreDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return ProgramaCompletitudResponse.model_validate(result)


@router.post(
    "/{referencia_id}/cierre",
    response_model=ProgramaCierreResponse,
    status_code=status.HTTP_200_OK,
)
async def cerrar_programa(
    referencia_id: uuid.UUID,
    service: ProgramaCierreService = Depends(get_programa_cierre_service),
) -> ProgramaCierreResponse:
    """Close a program after explicit UI confirmation."""
    try:
        result = await service.cerrar_programa(referencia_id)
    except ProgramaCierreDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except ProgramaCierreValidationError as error:
        detail = ProgramaCompletitudResponse.model_validate(
            error.completitud,
        ).model_dump(mode="json")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    return ProgramaCierreResponse.model_validate(result)
