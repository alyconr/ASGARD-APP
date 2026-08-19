"""HTTP endpoints for Pedagogical Planning wizard operations."""

from __future__ import annotations

import io
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.planeacion import (
    FormatoOficialEstadoDTO,
    FormatoOficialGeneradoDTO,
    PlaneacionContextoDTO,
    PlaneacionDocumentoConfigDTO,
    PlaneacionDocumentoConfigUpdateDTO,
    PlaneacionListDTO,
    PlaneacionResponseDTO,
    PlaneacionSaveDTO,
)
from src.application.services.planeacion_formato_excel import EXCEL_CONTENT_TYPE
from src.application.services.planeacion_service import (
    PlaneacionAccessError,
    PlaneacionPedagogicaService,
)
from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.planeacion import PlaneacionPedagogicaRepository
from src.infrastructure.storage.document_storage import MinioDocumentStorageService

router = APIRouter(prefix="/api/v1/planeaciones", tags=["planeacion-pedagogica"])


def get_planeacion_service(
    session: AsyncSession = Depends(get_async_session),
    settings: Settings = Depends(get_settings),
) -> PlaneacionPedagogicaService:
    """Build request-scoped service instance."""
    repository = PlaneacionPedagogicaRepository(session)
    storage_service = MinioDocumentStorageService(settings)
    return PlaneacionPedagogicaService(
        session=session,
        repository=repository,
        storage_service=storage_service,
    )


@router.get(
    "/contexto/{referencia_id}",
    response_model=PlaneacionContextoDTO,
    status_code=status.HTTP_200_OK,
)
async def obtener_contexto(
    referencia_id: uuid.UUID,
    service: PlaneacionPedagogicaService = Depends(get_planeacion_service),
) -> PlaneacionContextoDTO:
    """Fetch active program and project tree structure for planning context."""
    try:
        return await service.obtener_contexto(referencia_id)
    except PlaneacionAccessError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@router.get(
    "/proyecto/{proyecto_id}",
    response_model=list[PlaneacionListDTO],
    status_code=status.HTTP_200_OK,
)
async def listar_planeaciones(
    proyecto_id: uuid.UUID,
    service: PlaneacionPedagogicaService = Depends(get_planeacion_service),
) -> list[PlaneacionListDTO]:
    """List all created planning items for a specific project formativo."""
    return await service.listar_planeaciones(proyecto_id)


@router.get(
    "/proyecto/{proyecto_id}/configuracion-formato-oficial",
    response_model=PlaneacionDocumentoConfigDTO,
)
async def obtener_configuracion_formato_oficial(
    proyecto_id: uuid.UUID,
    service: PlaneacionPedagogicaService = Depends(get_planeacion_service),
) -> PlaneacionDocumentoConfigDTO:
    """Return shared institutional workbook metadata."""
    try:
        return await service.obtener_configuracion_documento(proyecto_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.put(
    "/proyecto/{proyecto_id}/configuracion-formato-oficial",
    response_model=PlaneacionDocumentoConfigDTO,
)
async def guardar_configuracion_formato_oficial(
    proyecto_id: uuid.UUID,
    dto: PlaneacionDocumentoConfigUpdateDTO,
    service: PlaneacionPedagogicaService = Depends(get_planeacion_service),
    session: AsyncSession = Depends(get_async_session),
) -> PlaneacionDocumentoConfigDTO:
    """Persist shared institutional workbook metadata."""
    try:
        result = await service.guardar_configuracion_documento(proyecto_id, dto)
        await session.commit()
        return result
    except (PlaneacionAccessError, ValueError) as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get(
    "/proyecto/{proyecto_id}/estado-formato-oficial",
    response_model=FormatoOficialEstadoDTO,
)
async def obtener_estado_formato_consolidado(
    proyecto_id: uuid.UUID,
    service: PlaneacionPedagogicaService = Depends(get_planeacion_service),
) -> FormatoOficialEstadoDTO:
    """Return consolidated generation readiness and counts."""
    return await service.obtener_estado_formato_consolidado(proyecto_id)


@router.post(
    "/proyecto/{proyecto_id}/generar-formato-oficial",
    response_model=FormatoOficialGeneradoDTO,
)
async def generar_formato_consolidado(
    proyecto_id: uuid.UUID,
    service: PlaneacionPedagogicaService = Depends(get_planeacion_service),
    session: AsyncSession = Depends(get_async_session),
) -> FormatoOficialGeneradoDTO:
    """Generate and store the consolidated official project workbook."""
    try:
        result = await service.generar_formato_consolidado(proyecto_id)
        await session.commit()
        return result
    except (PlaneacionAccessError, ValueError) as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/proyecto/{proyecto_id}/descargar-formato-oficial")
async def descargar_formato_consolidado(
    proyecto_id: uuid.UUID,
    service: PlaneacionPedagogicaService = Depends(get_planeacion_service),
) -> StreamingResponse:
    """Stream the latest consolidated workbook stored in MinIO."""
    try:
        content, filename = await service.descargar_formato_consolidado(proyecto_id)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return _excel_response(content, filename)


@router.get(
    "/{planeacion_id}",
    response_model=PlaneacionResponseDTO,
    status_code=status.HTTP_200_OK,
)
async def obtener_detalle(
    planeacion_id: uuid.UUID,
    service: PlaneacionPedagogicaService = Depends(get_planeacion_service),
) -> PlaneacionResponseDTO:
    """Retrieve detailed properties of a single pedagogical planning record."""
    detail = await service.obtener_detalle(planeacion_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la planeación pedagógica con id {planeacion_id}",
        )
    return detail


@router.get(
    "/{planeacion_id}/estado-formato-oficial",
    response_model=FormatoOficialEstadoDTO,
)
async def obtener_estado_formato_individual(
    planeacion_id: uuid.UUID,
    service: PlaneacionPedagogicaService = Depends(get_planeacion_service),
) -> FormatoOficialEstadoDTO:
    """Return individual generation readiness from backend rules."""
    try:
        return await service.obtener_estado_formato_individual(planeacion_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/{planeacion_id}/generar-formato-oficial",
    response_model=FormatoOficialGeneradoDTO,
)
async def generar_formato_individual(
    planeacion_id: uuid.UUID,
    service: PlaneacionPedagogicaService = Depends(get_planeacion_service),
    session: AsyncSession = Depends(get_async_session),
) -> FormatoOficialGeneradoDTO:
    """Regenerate one completed planning workbook."""
    try:
        result = await service.generar_formato_individual(planeacion_id)
        await session.commit()
        return result
    except (PlaneacionAccessError, ValueError) as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/{planeacion_id}/descargar-formato-oficial")
async def descargar_formato_individual(
    planeacion_id: uuid.UUID,
    service: PlaneacionPedagogicaService = Depends(get_planeacion_service),
) -> StreamingResponse:
    """Stream one official workbook stored in MinIO."""
    try:
        content, filename = await service.descargar_formato_individual(planeacion_id)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return _excel_response(content, filename)


@router.post(
    "",
    response_model=PlaneacionResponseDTO,
    status_code=status.HTTP_200_OK,
)
async def guardar_borrador(
    dto: PlaneacionSaveDTO,
    service: PlaneacionPedagogicaService = Depends(get_planeacion_service),
    session: AsyncSession = Depends(get_async_session),
) -> PlaneacionResponseDTO:
    """Create or update a pedagogical planning draft."""
    try:
        res = await service.guardar_borrador(dto)
        await session.commit()
        return res
    except PlaneacionAccessError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except ValueError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except Exception as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar el borrador de planeación: {error}",
        ) from error


@router.post(
    "/{planeacion_id}/confirmar",
    response_model=PlaneacionResponseDTO,
    status_code=status.HTTP_200_OK,
)
async def confirmar_y_generar(
    planeacion_id: uuid.UUID,
    service: PlaneacionPedagogicaService = Depends(get_planeacion_service),
    session: AsyncSession = Depends(get_async_session),
) -> PlaneacionResponseDTO:
    """Transition state to COMPLETE, build output and store it in MinIO."""
    try:
        res = await service.confirmar_y_generar(planeacion_id)
        await session.commit()
        return res
    except PlaneacionAccessError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except ValueError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except Exception as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al confirmar la planeación pedagógica: {error}",
        ) from error


@router.delete(
    "/{planeacion_id}",
    status_code=status.HTTP_200_OK,
)
async def eliminar_planeacion(
    planeacion_id: uuid.UUID,
    service: PlaneacionPedagogicaService = Depends(get_planeacion_service),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    """Delete a pedagogical planning from database and cancel related artifacts."""
    try:
        await service.eliminar_planeacion(planeacion_id)
        await session.commit()
    except Exception as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar la planeación pedagógica: {error}",
        ) from error

    return {"message": "Planeación pedagógica eliminada con éxito."}


def _excel_response(content: bytes, filename: str) -> StreamingResponse:
    safe_filename = filename.replace('"', "")
    encoded_filename = quote(filename, safe="")
    return StreamingResponse(
        io.BytesIO(content),
        media_type=EXCEL_CONTENT_TYPE,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{safe_filename}"; '
                f"filename*=UTF-8''{encoded_filename}"
            )
        },
    )
