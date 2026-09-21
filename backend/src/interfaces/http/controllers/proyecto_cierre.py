"""HTTP endpoints for project completion validation and closing."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.access_scope import AccessScopeService
from src.application.services.proyecto_cierre import (
    ProyectoCierreDraftNotFoundError,
    ProyectoCierreService,
    ProyectoCierreValidationError,
)
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.drafts import DraftRepository
from src.infrastructure.repositories.proyecto_cierre import ProyectoCierreRepository
from src.interfaces.http.deps import get_access_scope_service, get_current_user
from src.interfaces.http.schemas.proyecto_cierre import (
    ProyectoCierreResponse,
    ProyectoCompletitudResponse,
)

router = APIRouter(prefix="/api/v1/proyectos", tags=["proyecto-cierre"])


def get_proyecto_cierre_service(
    session: AsyncSession = Depends(get_async_session),
) -> ProyectoCierreService:
    """Build the project close service using request-scoped dependencies."""
    return ProyectoCierreService(
        session=session,
        draft_repository=DraftRepository(session),
        proyecto_repository=ProyectoCierreRepository(session),
        audit_repository=AuditRepository(session),
    )


@router.get(
    "/{referencia_id}/completitud",
    response_model=ProyectoCompletitudResponse,
    status_code=status.HTTP_200_OK,
)
async def validar_completitud_proyecto(
    referencia_id: uuid.UUID,
    service: ProyectoCierreService = Depends(get_proyecto_cierre_service),
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> ProyectoCompletitudResponse:
    """Return structured readiness details for closing a project."""
    await scope_service.require_process_access(current_user, referencia_id)

    try:
        result = await service.validar_completitud(referencia_id)
    except ProyectoCierreDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return ProyectoCompletitudResponse.model_validate(result)


@router.post(
    "/{referencia_id}/cierre",
    response_model=ProyectoCierreResponse,
    status_code=status.HTTP_200_OK,
)
async def cerrar_proyecto(
    referencia_id: uuid.UUID,
    service: ProyectoCierreService = Depends(get_proyecto_cierre_service),
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> ProyectoCierreResponse:
    """Close a project after explicit UI confirmation."""
    await scope_service.require_process_access(current_user, referencia_id)


    try:
        result = await service.cerrar_proyecto(referencia_id)
    except ProyectoCierreDraftNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except ProyectoCierreValidationError as error:
        detail = ProyectoCompletitudResponse.model_validate(
            error.completitud,
        ).model_dump(mode="json")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    return ProyectoCierreResponse.model_validate(result)
