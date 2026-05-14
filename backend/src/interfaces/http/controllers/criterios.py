"""HTTP endpoints for TASK-12 criteria CRUD."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.criterios import CriterioPayloadDTO
from src.application.services.criterios import (
    CriterioCompetenciaNotFoundError,
    CriterioDraftNotFoundError,
    CriterioDuplicateError,
    CriterioNotFoundError,
    CriterioValidationError,
    ProgramaCriteriosService,
)
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.criterios import CriterioRepository
from src.infrastructure.repositories.drafts import DraftRepository
from src.interfaces.http.schemas.criterios import (
    CriterioDeleteResponse,
    CriterioListResponse,
    CriterioRequest,
)

router = APIRouter(prefix="/api/v1/programas", tags=["programa-criterios"])


def get_programa_criterios_service(
    session: AsyncSession = Depends(get_async_session),
) -> ProgramaCriteriosService:
    return ProgramaCriteriosService(
        session=session,
        criterio_repository=CriterioRepository(session),
        draft_repository=DraftRepository(session),
        audit_repository=AuditRepository(session),
    )


@router.get(
    "/{referencia_id}/competencias/{competencia_id}/criterios",
    response_model=CriterioListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_criterios(
    referencia_id: uuid.UUID,
    competencia_id: uuid.UUID,
    service: ProgramaCriteriosService = Depends(get_programa_criterios_service),
) -> CriterioListResponse:
    try:
        result = await service.list_criterios(referencia_id, competencia_id)
    except CriterioDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except CriterioCompetenciaNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return CriterioListResponse.model_validate(result)


@router.post(
    "/{referencia_id}/competencias/{competencia_id}/criterios",
    response_model=CriterioListResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_criterio(
    referencia_id: uuid.UUID,
    competencia_id: uuid.UUID,
    request: CriterioRequest,
    service: ProgramaCriteriosService = Depends(get_programa_criterios_service),
) -> CriterioListResponse:
    try:
        result = await service.create_criterio(
            referencia_id,
            competencia_id,
            CriterioPayloadDTO(descripcion=request.descripcion),
        )
    except CriterioDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except (
        CriterioCompetenciaNotFoundError,
        CriterioValidationError,
    ) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except CriterioDuplicateError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return CriterioListResponse.model_validate(result)


@router.put(
    "/{referencia_id}/competencias/{competencia_id}/criterios/{criterio_id}",
    response_model=CriterioListResponse,
    status_code=status.HTTP_200_OK,
)
async def update_criterio(
    referencia_id: uuid.UUID,
    competencia_id: uuid.UUID,
    criterio_id: uuid.UUID,
    request: CriterioRequest,
    service: ProgramaCriteriosService = Depends(get_programa_criterios_service),
) -> CriterioListResponse:
    try:
        result = await service.update_criterio(
            referencia_id,
            competencia_id,
            criterio_id,
            CriterioPayloadDTO(descripcion=request.descripcion),
        )
    except CriterioDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except (
        CriterioCompetenciaNotFoundError,
        CriterioValidationError,
    ) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except CriterioDuplicateError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    except CriterioNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return CriterioListResponse.model_validate(result)


@router.delete(
    "/{referencia_id}/competencias/{competencia_id}/criterios/{criterio_id}",
    response_model=CriterioDeleteResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_criterio(
    referencia_id: uuid.UUID,
    competencia_id: uuid.UUID,
    criterio_id: uuid.UUID,
    service: ProgramaCriteriosService = Depends(get_programa_criterios_service),
) -> CriterioDeleteResponse:
    try:
        result = await service.delete_criterio(
            referencia_id,
            competencia_id,
            criterio_id,
        )
    except CriterioDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except CriterioCompetenciaNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    except CriterioNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return CriterioDeleteResponse.model_validate(result)
