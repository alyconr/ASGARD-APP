"""HTTP endpoints for project and program cargue deletion."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.access_scope import AccessScopeService
from src.application.services.proyecto_cargue import ProyectoCargueService
from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.session import get_async_session
from src.infrastructure.storage.document_storage import MinioDocumentStorageService
from src.interfaces.http.deps import get_access_scope_service, get_current_user

router = APIRouter(prefix="/api/v1/proyectos", tags=["cargue"])


def get_proyecto_cargue_service(
    session: AsyncSession = Depends(get_async_session),
    settings: Settings = Depends(get_settings),
) -> ProyectoCargueService:
    """Build the project cargue service using request-scoped dependencies."""
    storage_service = MinioDocumentStorageService(settings)
    return ProyectoCargueService(session=session, storage_service=storage_service)


@router.delete(
    "/cargue/{referencia_id}",
    status_code=status.HTTP_200_OK,
)
async def eliminar_cargue_completo(
    referencia_id: uuid.UUID,
    service: ProyectoCargueService = Depends(get_proyecto_cargue_service),
    session: AsyncSession = Depends(get_async_session),
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> dict[str, str]:
    """Delete training program and project formativo DB records and MinIO files."""
    await scope_service.require_process_access(current_user, referencia_id)
    try:
        await service.eliminar_cargue_completo(referencia_id)
        await session.commit()
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el cargue completo: {error}",
        ) from error

    return {"message": "El cargue del programa y proyecto ha sido eliminado con exito."}


@router.delete(
    "/cargue-proyecto/{referencia_id}",
    status_code=status.HTTP_200_OK,
)
async def eliminar_cargue_proyecto(
    referencia_id: uuid.UUID,
    service: ProyectoCargueService = Depends(get_proyecto_cargue_service),
    session: AsyncSession = Depends(get_async_session),
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> dict[str, str]:
    """Delete project formativo DB records and MinIO files, preserving program."""
    await scope_service.require_process_access(current_user, referencia_id)


    try:
        await service.eliminar_cargue_proyecto(referencia_id)
        await session.commit()
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el cargue del proyecto: {error}",
        ) from error

    return {"message": "El cargue del proyecto formativo ha sido eliminado con exito."}
