"""HTTP endpoint for the master dashboard."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.dashboard import (
    DashboardDraftNotFoundError,
    DashboardService,
)
from src.infrastructure.db.session import get_async_session
from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.storage.document_storage import MinioDocumentStorageService
from src.application.services.proyecto_cargue import ProyectoCargueService
from src.interfaces.http.schemas.dashboard import (
    DashboardProgramFlowResponse,
    DashboardResponse,
)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def get_dashboard_service(
    session: AsyncSession = Depends(get_async_session),
    settings: Settings = Depends(get_settings),
) -> DashboardService:
    """Build request-scoped dashboard service."""
    storage_service = MinioDocumentStorageService(settings)
    return DashboardService(
        session,
        cleanup_service=ProyectoCargueService(
            session=session,
            storage_service=storage_service,
        ),
    )


@router.get(
    "/programas",
    response_model=list[DashboardProgramFlowResponse],
    status_code=status.HTTP_200_OK,
)
async def listar_flujos_programa(
    service: DashboardService = Depends(get_dashboard_service),
) -> list[DashboardProgramFlowResponse]:
    """Return program flows available from the master dashboard."""
    flows = await service.listar_flujos_programa()
    return [DashboardProgramFlowResponse.model_validate(flow) for flow in flows]


@router.delete(
    "/programas/{referencia_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def eliminar_flujo_programa(
    referencia_id: uuid.UUID,
    service: DashboardService = Depends(get_dashboard_service),
) -> None:
    """Permanently delete the selected program and all dependent data."""
    try:
        await service.eliminar_flujo_programa(referencia_id)
    except DashboardDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


@router.get(
    "/{referencia_id}",
    response_model=DashboardResponse,
    status_code=status.HTTP_200_OK,
)
async def consultar_dashboard(
    referencia_id: uuid.UUID,
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardResponse:
    """Return master dashboard metrics, gates and visual map."""
    try:
        result = await service.consultar(referencia_id)
    except DashboardDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return DashboardResponse.model_validate(result)
