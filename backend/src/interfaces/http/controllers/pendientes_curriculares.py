"""HTTP endpoints for Excel curricular pending reconciliation."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.pendientes_curriculares import (
    PendienteCurricularAsignacionDTO,
)
from src.application.services.access_scope import AccessScopeService
from src.application.services.pendientes_curriculares import (
    PendienteCurricularDraftNotFoundError,
    PendienteCurricularDuplicateError,
    PendienteCurricularNotFoundError,
    PendienteCurricularValidationError,
    PendientesCurricularesService,
)
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.drafts import DraftRepository
from src.infrastructure.repositories.pendientes_curriculares import (
    PendientesCurricularesRepository,
)
from src.interfaces.http.deps import get_access_scope_service, get_current_user
from src.interfaces.http.schemas.pendientes_curriculares import (
    PendienteCurricularAsignacionRequest,
    PendienteCurricularAsignacionResponse,
    PendienteCurricularListResponse,
)

router = APIRouter(prefix="/api/v1/programas", tags=["programa-pendientes"])


def get_pendientes_curriculares_service(
    session: AsyncSession = Depends(get_async_session),
) -> PendientesCurricularesService:
    """Build the pending curriculum service using request-scoped dependencies."""
    return PendientesCurricularesService(
        session=session,
        draft_repository=DraftRepository(session),
        pending_repository=PendientesCurricularesRepository(session),
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
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> PendienteCurricularListResponse:
    """List unresolved Excel rows for manual assignment."""
    await scope_service.require_process_access(current_user, referencia_id)

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
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> PendienteCurricularAsignacionResponse:
    """Assign one unresolved Excel row to a competence/result."""
    await scope_service.require_process_access(current_user, referencia_id)

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
