"""HTTP endpoints for project Excel import."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.proyecto_excel import (
    InvalidProjectExcelUploadError,
    ProjectExcelDraftMissingError,
    ProjectExcelMissingPreviewError,
    ProjectExcelStorageMissingError,
    ProjectExcelValidationError,
    ProyectoExcelImportService,
)
from src.domain.shared.enums import EstadoBloque
from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.db.models.proyecto import (
    ActividadProyecto,
    AsignacionCurricularProyecto,
    FaseProyecto,
    ProyectoFormativo,
)
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.drafts import DraftRepository
from src.infrastructure.storage.document_storage import MinioDocumentStorageService
from src.interfaces.http.schemas.proyecto_excel import (
    ProyectoExcelImportResponse,
    ProyectoExcelPreviewResponse,
)

router = APIRouter(prefix="/api/v1/proyectos", tags=["proyectos"])


class ProjectRepository:
    """Adapts the SQLAlchemy session to the ProjectRepositoryProtocol."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_proyecto(
        self,
        *,
        programa_id: uuid.UUID,
        codigo_proyecto: str,
        nombre_proyecto: str,
        version_proyecto: str,
    ) -> ProyectoFormativo:
        proyecto = ProyectoFormativo(
            programa_id=programa_id,
            codigo_proyecto=codigo_proyecto,
            nombre_proyecto=nombre_proyecto,
            version_proyecto=version_proyecto,
            estado=EstadoBloque.BORRADOR,
        )
        self._session.add(proyecto)
        await self._session.flush()
        return proyecto

    async def create_fase(
        self,
        *,
        proyecto_id: uuid.UUID,
        nombre_fase: str,
        orden: int | None,
    ) -> FaseProyecto:
        fase = FaseProyecto(
            proyecto_id=proyecto_id,
            nombre_fase=nombre_fase,
            orden=orden,
        )
        self._session.add(fase)
        await self._session.flush()
        return fase

    async def create_actividad(
        self,
        *,
        fase_id: uuid.UUID,
        descripcion: str,
        orden: int | None,
    ) -> ActividadProyecto:
        actividad = ActividadProyecto(
            fase_id=fase_id,
            descripcion=descripcion,
            orden=orden,
        )
        self._session.add(actividad)
        await self._session.flush()
        return actividad

    async def proyecto_exists_by_code_name(
        self,
        *,
        programa_id: uuid.UUID,
        codigo_proyecto: str,
        nombre_proyecto: str,
    ) -> bool:
        from sqlalchemy import func, select

        statement = select(ProyectoFormativo.id).where(
            ProyectoFormativo.programa_id == programa_id
        ).where(
            func.lower(ProyectoFormativo.codigo_proyecto)
            == codigo_proyecto.lower()
        ).where(
            func.lower(ProyectoFormativo.nombre_proyecto)
            == nombre_proyecto.lower()
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def create_asignacion_curricular(
        self,
        *,
        proyecto_id: uuid.UUID,
        actividad_proyecto_id: uuid.UUID,
        competencia_id: uuid.UUID,
        resultado_id: uuid.UUID | None,
        tipo_resultado: str,
        orden_resultado: int | None,
        pagina_origen: str | None,
        observaciones: str | None,
    ) -> AsignacionCurricularProyecto:
        asignacion = AsignacionCurricularProyecto(
            proyecto_id=proyecto_id,
            actividad_proyecto_id=actividad_proyecto_id,
            competencia_id=competencia_id,
            resultado_id=resultado_id,
            tipo_resultado=tipo_resultado,
            orden_resultado=orden_resultado,
            pagina_origen=pagina_origen,
            observaciones=observaciones,
        )
        self._session.add(asignacion)
        await self._session.flush()
        return asignacion


def get_proyecto_excel_service(
    session: AsyncSession = Depends(get_async_session),
    settings: Settings = Depends(get_settings),
) -> ProyectoExcelImportService:
    """Build the project Excel import service using request-scoped dependencies."""
    return ProyectoExcelImportService(
        session=session,
        draft_repository=DraftRepository(session),
        audit_repository=AuditRepository(session),
        project_repository=ProjectRepository(session),
        storage_service=MinioDocumentStorageService(settings),
    )


@router.post(
    "/{referencia_id}/excel/preview",
    response_model=ProyectoExcelPreviewResponse,
    status_code=status.HTTP_200_OK,
)
async def preview_project_excel(
    referencia_id: uuid.UUID,
    file: UploadFile = File(...),
    service: ProyectoExcelImportService = Depends(get_proyecto_excel_service),
) -> ProyectoExcelPreviewResponse:
    """Preview a project Excel workbook without relational writes."""
    filename = file.filename or ""
    content_type = file.content_type or "application/octet-stream"
    content = await file.read()

    try:
        result = await service.preview_project_excel(
            referencia_id=referencia_id,
            filename=filename,
            content_type=content_type,
            content=content,
        )
    except ProjectExcelDraftMissingError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (InvalidProjectExcelUploadError, ProjectExcelValidationError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    return ProyectoExcelPreviewResponse.model_validate(result)


@router.post(
    "/{referencia_id}/excel/confirm",
    response_model=ProyectoExcelImportResponse,
    status_code=status.HTTP_200_OK,
)
async def confirm_project_excel_import(
    referencia_id: uuid.UUID,
    service: ProyectoExcelImportService = Depends(get_proyecto_excel_service),
) -> ProyectoExcelImportResponse:
    """Confirm and materialize a previously validated project Excel import."""
    try:
        result = await service.confirm_project_excel_import(
            referencia_id=referencia_id,
        )
    except ProjectExcelDraftMissingError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (
        ProjectExcelMissingPreviewError,
        ProjectExcelStorageMissingError,
        ProjectExcelValidationError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    return ProyectoExcelImportResponse.model_validate(result)
