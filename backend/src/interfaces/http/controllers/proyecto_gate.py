"""HTTP endpoints for TASK-15 project blocking and unblocking."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.proyecto_gate import (
    ProyectoBloqueadoError,
    ProyectoGateDraftNotFoundError,
    ProyectoGateService,
)
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.drafts import DraftRepository
from src.infrastructure.repositories.proyecto_gate import ProyectoGateRepository
from src.interfaces.http.schemas.proyecto_gate import (
    ProyectoDisponibilidadResponse,
)

router = APIRouter(prefix="/api/v1/programas", tags=["proyecto-gate"])


def get_proyecto_gate_service(
    session: AsyncSession = Depends(get_async_session),
) -> ProyectoGateService:
    """Build the project availability service for the current request."""
    return ProyectoGateService(
        draft_repository=DraftRepository(session),
        proyecto_repository=ProyectoGateRepository(session),
    )


@router.get(
    "/{referencia_id}/proyecto/disponibilidad",
    response_model=ProyectoDisponibilidadResponse,
)
async def consultar_disponibilidad_proyecto(
    referencia_id: uuid.UUID,
    service: ProyectoGateService = Depends(get_proyecto_gate_service),
) -> ProyectoDisponibilidadResponse:
    """Return whether the project module is currently blocked."""
    try:
        result = await service.consultar_disponibilidad(referencia_id)
    except ProyectoGateDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return ProyectoDisponibilidadResponse.model_validate(result)


@router.post(
    "/{referencia_id}/proyecto/acceso",
    response_model=ProyectoDisponibilidadResponse,
)
async def validar_acceso_proyecto(
    referencia_id: uuid.UUID,
    service: ProyectoGateService = Depends(get_proyecto_gate_service),
) -> ProyectoDisponibilidadResponse:
    """Reject access attempts when the program is not complete."""
    try:
        result = await service.validar_acceso(referencia_id)
    except ProyectoGateDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except ProyectoBloqueadoError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ProyectoDisponibilidadResponse.model_validate(
                error.disponibilidad,
            ).model_dump(mode="json"),
        )
    return ProyectoDisponibilidadResponse.model_validate(result)
