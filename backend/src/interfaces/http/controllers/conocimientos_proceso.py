"""HTTP endpoints for TASK-11 PROCESO knowledge CRUD."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.conocimientos_proceso import ConocimientoProcesoPayloadDTO
from src.application.services.conocimientos_proceso import (
    ConocimientoProcesoCompetenciaNotFoundError,
    ConocimientoProcesoDraftNotFoundError,
    ConocimientoProcesoDuplicateError,
    ConocimientoProcesoNotFoundError,
    ConocimientoProcesoValidationError,
    ProgramaConocimientoProcesoService,
)
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.conocimientos_proceso import (
    ConocimientoProcesoRepository,
)
from src.infrastructure.repositories.drafts import DraftRepository
from src.interfaces.http.schemas.conocimientos_proceso import (
    ConocimientoProcesoDeleteResponse,
    ConocimientoProcesoListResponse,
    ConocimientoProcesoRequest,
)

router = APIRouter(prefix="/api/v1/programas", tags=["programa-conocimientos-proceso"])


def get_programa_conocimiento_proceso_service(
    session: AsyncSession = Depends(get_async_session),
) -> ProgramaConocimientoProcesoService:
    """Build the PROCESO knowledge service using request-scoped dependencies."""
    return ProgramaConocimientoProcesoService(
        session=session,
        conocimiento_repository=ConocimientoProcesoRepository(session),
        draft_repository=DraftRepository(session),
        audit_repository=AuditRepository(session),
    )


@router.get(
    "/{referencia_id}/competencias/{competencia_id}/conocimientos/proceso",
    response_model=ConocimientoProcesoListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_conocimientos_proceso(
    referencia_id: uuid.UUID,
    competencia_id: uuid.UUID,
    service: ProgramaConocimientoProcesoService = Depends(
        get_programa_conocimiento_proceso_service
    ),
) -> ConocimientoProcesoListResponse:
    """List PROCESO knowledge items for a competence in the current draft."""
    try:
        result = await service.list_conocimientos(referencia_id, competencia_id)
    except ConocimientoProcesoDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except ConocimientoProcesoCompetenciaNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return ConocimientoProcesoListResponse.model_validate(result)


@router.post(
    "/{referencia_id}/competencias/{competencia_id}/conocimientos/proceso",
    response_model=ConocimientoProcesoListResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conocimiento_proceso(
    referencia_id: uuid.UUID,
    competencia_id: uuid.UUID,
    request: ConocimientoProcesoRequest,
    service: ProgramaConocimientoProcesoService = Depends(
        get_programa_conocimiento_proceso_service
    ),
) -> ConocimientoProcesoListResponse:
    """Create a PROCESO knowledge item linked to the given competence."""
    try:
        result = await service.create_conocimiento(
            referencia_id,
            competencia_id,
            ConocimientoProcesoPayloadDTO(descripcion=request.descripcion),
        )
    except ConocimientoProcesoDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except (
        ConocimientoProcesoCompetenciaNotFoundError,
        ConocimientoProcesoValidationError,
    ) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except ConocimientoProcesoDuplicateError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return ConocimientoProcesoListResponse.model_validate(result)


@router.put(
    (
        "/{referencia_id}/competencias/{competencia_id}"
        "/conocimientos/proceso/{conocimiento_id}"
    ),
    response_model=ConocimientoProcesoListResponse,
    status_code=status.HTTP_200_OK,
)
async def update_conocimiento_proceso(
    referencia_id: uuid.UUID,
    competencia_id: uuid.UUID,
    conocimiento_id: uuid.UUID,
    request: ConocimientoProcesoRequest,
    service: ProgramaConocimientoProcesoService = Depends(
        get_programa_conocimiento_proceso_service
    ),
) -> ConocimientoProcesoListResponse:
    """Update a PROCESO knowledge item without moving it to another competence."""
    try:
        result = await service.update_conocimiento(
            referencia_id,
            competencia_id,
            conocimiento_id,
            ConocimientoProcesoPayloadDTO(descripcion=request.descripcion),
        )
    except ConocimientoProcesoDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except (
        ConocimientoProcesoCompetenciaNotFoundError,
        ConocimientoProcesoValidationError,
    ) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except ConocimientoProcesoDuplicateError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    except ConocimientoProcesoNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return ConocimientoProcesoListResponse.model_validate(result)


@router.delete(
    (
        "/{referencia_id}/competencias/{competencia_id}"
        "/conocimientos/proceso/{conocimiento_id}"
    ),
    response_model=ConocimientoProcesoDeleteResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_conocimiento_proceso(
    referencia_id: uuid.UUID,
    competencia_id: uuid.UUID,
    conocimiento_id: uuid.UUID,
    service: ProgramaConocimientoProcesoService = Depends(
        get_programa_conocimiento_proceso_service
    ),
) -> ConocimientoProcesoDeleteResponse:
    """Delete a PROCESO knowledge item from a competence."""
    try:
        result = await service.delete_conocimiento(
            referencia_id, competencia_id, conocimiento_id
        )
    except ConocimientoProcesoDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except ConocimientoProcesoCompetenciaNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except ConocimientoProcesoNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return ConocimientoProcesoDeleteResponse.model_validate(result)
