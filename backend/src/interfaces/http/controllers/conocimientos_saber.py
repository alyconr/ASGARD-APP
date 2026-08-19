"""HTTP endpoints for TASK-10 SABER knowledge CRUD."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.conocimientos_saber import ConocimientoSaberPayloadDTO
from src.application.services.conocimientos_saber import (
    ConocimientoSaberCompetenciaNotFoundError,
    ConocimientoSaberDraftNotFoundError,
    ConocimientoSaberDuplicateError,
    ConocimientoSaberNotFoundError,
    ConocimientoSaberValidationError,
    ProgramaConocimientoSaberService,
)
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.conocimientos_saber import (
    ConocimientoSaberRepository,
)
from src.infrastructure.repositories.drafts import DraftRepository
from src.interfaces.http.schemas.conocimientos_saber import (
    ConocimientoSaberDeleteResponse,
    ConocimientoSaberListResponse,
    ConocimientoSaberRequest,
)

router = APIRouter(prefix="/api/v1/programas", tags=["programa-conocimientos-saber"])


def get_programa_conocimiento_saber_service(
    session: AsyncSession = Depends(get_async_session),
) -> ProgramaConocimientoSaberService:
    """Build the SABER knowledge service using request-scoped dependencies."""
    return ProgramaConocimientoSaberService(
        session=session,
        conocimiento_repository=ConocimientoSaberRepository(session),
        draft_repository=DraftRepository(session),
        audit_repository=AuditRepository(session),
    )


@router.get(
    "/{referencia_id}/competencias/{competencia_id}/conocimientos/saber",
    response_model=ConocimientoSaberListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_conocimientos_saber(
    referencia_id: uuid.UUID,
    competencia_id: uuid.UUID,
    service: ProgramaConocimientoSaberService = Depends(
        get_programa_conocimiento_saber_service
    ),
) -> ConocimientoSaberListResponse:
    """List SABER knowledge items for a competence in the current draft."""
    try:
        result = await service.list_conocimientos(referencia_id, competencia_id)
    except ConocimientoSaberDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except ConocimientoSaberCompetenciaNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return ConocimientoSaberListResponse.model_validate(result)


@router.post(
    "/{referencia_id}/competencias/{competencia_id}/conocimientos/saber",
    response_model=ConocimientoSaberListResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conocimiento_saber(
    referencia_id: uuid.UUID,
    competencia_id: uuid.UUID,
    request: ConocimientoSaberRequest,
    service: ProgramaConocimientoSaberService = Depends(
        get_programa_conocimiento_saber_service
    ),
) -> ConocimientoSaberListResponse:
    """Create a SABER knowledge item linked to the given competence."""
    try:
        result = await service.create_conocimiento(
            referencia_id,
            competencia_id,
            ConocimientoSaberPayloadDTO(descripcion=request.descripcion),
        )
    except ConocimientoSaberDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except (
        ConocimientoSaberCompetenciaNotFoundError,
        ConocimientoSaberValidationError,
    ) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except ConocimientoSaberDuplicateError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return ConocimientoSaberListResponse.model_validate(result)


@router.put(
    (
        "/{referencia_id}/competencias/{competencia_id}"
        "/conocimientos/saber/{conocimiento_id}"
    ),
    response_model=ConocimientoSaberListResponse,
    status_code=status.HTTP_200_OK,
)
async def update_conocimiento_saber(
    referencia_id: uuid.UUID,
    competencia_id: uuid.UUID,
    conocimiento_id: uuid.UUID,
    request: ConocimientoSaberRequest,
    service: ProgramaConocimientoSaberService = Depends(
        get_programa_conocimiento_saber_service
    ),
) -> ConocimientoSaberListResponse:
    """Update a SABER knowledge item without moving it to another competence."""
    try:
        result = await service.update_conocimiento(
            referencia_id,
            competencia_id,
            conocimiento_id,
            ConocimientoSaberPayloadDTO(descripcion=request.descripcion),
        )
    except ConocimientoSaberDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except (
        ConocimientoSaberCompetenciaNotFoundError,
        ConocimientoSaberValidationError,
    ) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except ConocimientoSaberDuplicateError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    except ConocimientoSaberNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return ConocimientoSaberListResponse.model_validate(result)


@router.delete(
    (
        "/{referencia_id}/competencias/{competencia_id}"
        "/conocimientos/saber/{conocimiento_id}"
    ),
    response_model=ConocimientoSaberDeleteResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_conocimiento_saber(
    referencia_id: uuid.UUID,
    competencia_id: uuid.UUID,
    conocimiento_id: uuid.UUID,
    service: ProgramaConocimientoSaberService = Depends(
        get_programa_conocimiento_saber_service
    ),
) -> ConocimientoSaberDeleteResponse:
    """Delete a SABER knowledge item from a competence."""
    try:
        result = await service.delete_conocimiento(
            referencia_id, competencia_id, conocimiento_id
        )
    except ConocimientoSaberDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except ConocimientoSaberCompetenciaNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except ConocimientoSaberNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return ConocimientoSaberDeleteResponse.model_validate(result)
