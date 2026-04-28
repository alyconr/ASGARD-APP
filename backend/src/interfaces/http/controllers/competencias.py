"""HTTP endpoints for TASK-08 program competence CRUD."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.competencias import CompetenciaPayloadDTO
from src.application.services.competencias import (
    CompetenciaDraftNotFoundError,
    CompetenciaDuplicateCodeError,
    CompetenciaNotFoundError,
    CompetenciaProgramaIncompleteError,
    CompetenciaValidationError,
    ProgramaCompetenciaService,
)
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.competencias import CompetenciaRepository
from src.infrastructure.repositories.drafts import DraftRepository
from src.interfaces.http.schemas.competencias import (
    CompetenciaDeleteResponse,
    CompetenciaListResponse,
    CompetenciaRequest,
)

router = APIRouter(prefix="/api/v1/programas", tags=["programa-competencias"])


def get_programa_competencia_service(
    session: AsyncSession = Depends(get_async_session),
) -> ProgramaCompetenciaService:
    """Build the competence service using request-scoped dependencies."""
    return ProgramaCompetenciaService(
        session=session,
        competencia_repository=CompetenciaRepository(session),
        draft_repository=DraftRepository(session),
        audit_repository=AuditRepository(session),
    )


@router.get(
    "/{referencia_id}/competencias",
    response_model=CompetenciaListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_competencias(
    referencia_id: uuid.UUID,
    service: ProgramaCompetenciaService = Depends(get_programa_competencia_service),
) -> CompetenciaListResponse:
    """List competences for the current program draft."""
    try:
        result = await service.list_competencias(referencia_id)
    except CompetenciaDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return CompetenciaListResponse.model_validate(result)


@router.post(
    "/{referencia_id}/competencias",
    response_model=CompetenciaListResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_competencia(
    referencia_id: uuid.UUID,
    request: CompetenciaRequest,
    service: ProgramaCompetenciaService = Depends(get_programa_competencia_service),
) -> CompetenciaListResponse:
    """Create a competence linked to the current program draft."""
    try:
        result = await service.create_competencia(
            referencia_id,
            CompetenciaPayloadDTO(
                codigo_competencia=request.codigo_competencia,
                nombre_competencia=request.nombre_competencia,
            ),
        )
    except CompetenciaDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except (
        CompetenciaProgramaIncompleteError,
        CompetenciaValidationError,
    ) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except CompetenciaDuplicateCodeError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return CompetenciaListResponse.model_validate(result)


@router.put(
    "/{referencia_id}/competencias/{competencia_id}",
    response_model=CompetenciaListResponse,
    status_code=status.HTTP_200_OK,
)
async def update_competencia(
    referencia_id: uuid.UUID,
    competencia_id: uuid.UUID,
    request: CompetenciaRequest,
    service: ProgramaCompetenciaService = Depends(get_programa_competencia_service),
) -> CompetenciaListResponse:
    """Update a competence without moving it to another program."""
    try:
        result = await service.update_competencia(
            referencia_id,
            competencia_id,
            CompetenciaPayloadDTO(
                codigo_competencia=request.codigo_competencia,
                nombre_competencia=request.nombre_competencia,
            ),
        )
    except CompetenciaDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except (
        CompetenciaProgramaIncompleteError,
        CompetenciaValidationError,
    ) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except CompetenciaDuplicateCodeError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    except CompetenciaNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return CompetenciaListResponse.model_validate(result)


@router.delete(
    "/{referencia_id}/competencias/{competencia_id}",
    response_model=CompetenciaDeleteResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_competencia(
    referencia_id: uuid.UUID,
    competencia_id: uuid.UUID,
    service: ProgramaCompetenciaService = Depends(get_programa_competencia_service),
) -> CompetenciaDeleteResponse:
    """Delete a competence selected from the current program draft."""
    try:
        result = await service.delete_competencia(referencia_id, competencia_id)
    except CompetenciaDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except CompetenciaProgramaIncompleteError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except CompetenciaNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return CompetenciaDeleteResponse.model_validate(result)
