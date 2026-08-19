"""HTTP endpoints for Excel curricular pending reconciliation."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.pendientes_curriculares import (
    PendienteCurricularAsignacionDTO,
)
from src.application.services.pendientes_curriculares import (
    PendienteCurricularDraftNotFoundError,
    PendienteCurricularDuplicateError,
    PendienteCurricularNotFoundError,
    PendienteCurricularValidationError,
    PendientesCurricularesService,
)
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.drafts import DraftRepository
from src.infrastructure.repositories.pendientes_curriculares import (
    PendientesCurricularesRepository,
)
from src.interfaces.http.schemas.pendientes_curriculares import (
    PendienteCurricularAsignacionRequest,
    PendienteCurricularAsignacionResponse,
    PendienteCurricularListResponse,
)

router = APIRouter(prefix="/api/v1/programas", tags=["programa-pendientes"])


def get_pendientes_curriculares_service(
    session: AsyncSession = Depends(get_async_session),
) -> PendientesCurricularesService:
    """Build the pending reconciliation service with request-scoped dependencies."""
    return PendientesCurricularesService(
        session=session,
        pending_repository=PendientesCurricularesRepository(session),
        draft_repository=DraftRepository(session),
        audit_repository=AuditRepository(session),
    )


@router.get(
    "/{referencia_id}/pendientes-curriculares",
    response_model=PendienteCurricularListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_pendientes_curriculares(
    referencia_id: uuid.UUID,
    service: PendientesCurricularesService = Depends(
        get_pendientes_curriculares_service
    ),
) -> PendienteCurricularListResponse:
    """List unresolved Excel rows for manual assignment."""
    try:
        result = await service.list_pendientes(referencia_id)
    except PendienteCurricularDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return PendienteCurricularListResponse.model_validate(result)


@router.post(
    "/{referencia_id}/pendientes-curriculares/{pendiente_id}/asignacion",
    response_model=PendienteCurricularAsignacionResponse,
    status_code=status.HTTP_200_OK,
)
async def asignar_pendiente_curricular(
    referencia_id: uuid.UUID,
    pendiente_id: uuid.UUID,
    request: PendienteCurricularAsignacionRequest,
    service: PendientesCurricularesService = Depends(
        get_pendientes_curriculares_service
    ),
) -> PendienteCurricularAsignacionResponse:
    """Assign one unresolved Excel row to a competence/result."""
    try:
        result = await service.asignar_pendiente(
            referencia_id,
            pendiente_id,
            PendienteCurricularAsignacionDTO(
                competencia_id=request.competencia_id,
                resultado_id=request.resultado_id,
            ),
        )
    except PendienteCurricularDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except PendienteCurricularNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except PendienteCurricularValidationError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except PendienteCurricularDuplicateError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return PendienteCurricularAsignacionResponse.model_validate(result)
