"""HTTP endpoints for TASK-09 learning outcomes CRUD."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.resultados_aprendizaje import ResultadoAprendizajePayloadDTO
from src.application.services.resultados_aprendizaje import (
    ProgramaResultadoAprendizajeService,
    ResultadoAprendizajeCompetenciaNotFoundError,
    ResultadoAprendizajeDraftNotFoundError,
    ResultadoAprendizajeDuplicateError,
    ResultadoAprendizajeNotFoundError,
    ResultadoAprendizajeValidationError,
)
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.drafts import DraftRepository
from src.infrastructure.repositories.resultados_aprendizaje import (
    ResultadoAprendizajeRepository,
)
from src.interfaces.http.schemas.resultados_aprendizaje import (
    ResultadoAprendizajeDeleteResponse,
    ResultadoAprendizajeListResponse,
    ResultadoAprendizajeRequest,
)

router = APIRouter(prefix="/api/v1/programas", tags=["programa-resultados"])


def get_programa_resultado_service(
    session: AsyncSession = Depends(get_async_session),
) -> ProgramaResultadoAprendizajeService:
    """Build the learning outcomes service using request-scoped dependencies."""
    return ProgramaResultadoAprendizajeService(
        session=session,
        resultado_repository=ResultadoAprendizajeRepository(session),
        draft_repository=DraftRepository(session),
        audit_repository=AuditRepository(session),
    )


@router.get(
    "/{referencia_id}/competencias/{competencia_id}/resultados",
    response_model=ResultadoAprendizajeListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_resultados(
    referencia_id: uuid.UUID,
    competencia_id: uuid.UUID,
    service: ProgramaResultadoAprendizajeService = Depends(
        get_programa_resultado_service
    ),
) -> ResultadoAprendizajeListResponse:
    """List learning outcomes for a competence in the current program draft."""
    try:
        result = await service.list_resultados(referencia_id, competencia_id)
    except ResultadoAprendizajeDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except ResultadoAprendizajeCompetenciaNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return ResultadoAprendizajeListResponse.model_validate(result)


@router.post(
    "/{referencia_id}/competencias/{competencia_id}/resultados",
    response_model=ResultadoAprendizajeListResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_resultado(
    referencia_id: uuid.UUID,
    competencia_id: uuid.UUID,
    request: ResultadoAprendizajeRequest,
    service: ProgramaResultadoAprendizajeService = Depends(
        get_programa_resultado_service
    ),
) -> ResultadoAprendizajeListResponse:
    """Create a learning outcome linked to the given competence."""
    try:
        result = await service.create_resultado(
            referencia_id,
            competencia_id,
            ResultadoAprendizajePayloadDTO(
                descripcion=request.descripcion,
                codigo_resultado=request.codigo_resultado,
            ),
        )
    except ResultadoAprendizajeDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except (
        ResultadoAprendizajeCompetenciaNotFoundError,
        ResultadoAprendizajeValidationError,
    ) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except ResultadoAprendizajeDuplicateError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return ResultadoAprendizajeListResponse.model_validate(result)


@router.put(
    "/{referencia_id}/competencias/{competencia_id}/resultados/{resultado_id}",
    response_model=ResultadoAprendizajeListResponse,
    status_code=status.HTTP_200_OK,
)
async def update_resultado(
    referencia_id: uuid.UUID,
    competencia_id: uuid.UUID,
    resultado_id: uuid.UUID,
    request: ResultadoAprendizajeRequest,
    service: ProgramaResultadoAprendizajeService = Depends(
        get_programa_resultado_service
    ),
) -> ResultadoAprendizajeListResponse:
    """Update a learning outcome without moving it to another competence."""
    try:
        result = await service.update_resultado(
            referencia_id,
            competencia_id,
            resultado_id,
            ResultadoAprendizajePayloadDTO(
                descripcion=request.descripcion,
                codigo_resultado=request.codigo_resultado,
            ),
        )
    except ResultadoAprendizajeDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except (
        ResultadoAprendizajeCompetenciaNotFoundError,
        ResultadoAprendizajeValidationError,
    ) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except ResultadoAprendizajeDuplicateError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    except ResultadoAprendizajeNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return ResultadoAprendizajeListResponse.model_validate(result)


@router.delete(
    "/{referencia_id}/competencias/{competencia_id}/resultados/{resultado_id}",
    response_model=ResultadoAprendizajeDeleteResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_resultado(
    referencia_id: uuid.UUID,
    competencia_id: uuid.UUID,
    resultado_id: uuid.UUID,
    service: ProgramaResultadoAprendizajeService = Depends(
        get_programa_resultado_service
    ),
) -> ResultadoAprendizajeDeleteResponse:
    """Delete a learning outcome from a competence."""
    try:
        result = await service.delete_resultado(
            referencia_id, competencia_id, resultado_id
        )
    except ResultadoAprendizajeDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except ResultadoAprendizajeCompetenciaNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except ResultadoAprendizajeNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return ResultadoAprendizajeDeleteResponse.model_validate(result)
