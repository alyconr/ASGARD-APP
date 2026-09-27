"""HTTP endpoints for Pedagogical Planning wizard operations."""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, update
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
from src.domain.shared.enums import RolUsuario
from src.application.services.planeacion_service import (
    PlaneacionAccessError,
    PlaneacionPedagogicaService,
)
from src.application.services.access_scope import AccessScopeService
from src.application.services.revision_curricular_service import (
    RevisionCurricularService,
)
from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.models.organizacion import ProcesoCurricular
from src.infrastructure.db.models.planeacion import PlaneacionPedagogica
from src.infrastructure.db.models.proyecto import ActividadProyecto, ProyectoFormativo
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.planeacion import PlaneacionPedagogicaRepository
from src.infrastructure.storage.document_storage import MinioDocumentStorageService
from src.interfaces.http.deps import get_access_scope_service, get_current_user

router = APIRouter(prefix="/api/v1/planeaciones", tags=["planeacion-pedagogica"])


async def _safe_actor_id(session: AsyncSession, user: Usuario | None) -> uuid.UUID | None:
    """Verify actor exists in the database to prevent foreign key errors in mock environments."""
    if not user or not getattr(user, "id", None):
        return None
    try:
        existing = await session.get(Usuario, user.id)
        return user.id if existing else None
    except Exception:
        return None


async def _resolve_referencia_id(session: AsyncSession, proyecto_id: uuid.UUID | None) -> uuid.UUID | None:
    """Resolve process referencia_id from the project identifier."""
    if not proyecto_id:
        return None
    try:
        stmt = select(ProcesoCurricular.referencia_id).where(ProcesoCurricular.proyecto_id == proyecto_id)
        res = await session.execute(stmt)
        ref = res.scalar_one_or_none()
        if ref:
            return ref
        proy = await session.get(ProyectoFormativo, proyecto_id)
        if proy and proy.programa_id:
            stmt2 = select(ProcesoCurricular.referencia_id).where(ProcesoCurricular.programa_id == proy.programa_id)
            res2 = await session.execute(stmt2)
            ref2 = res2.scalar_one_or_none()
            if ref2:
                return ref2
    except Exception:
        pass
    return None


async def _touch_proceso(session: AsyncSession, referencia_id: uuid.UUID | None) -> None:
    """Update process modification timestamp to reflect new planning changes."""
    if not referencia_id:
        return
    try:
        stmt = (
            update(ProcesoCurricular)
            .where(ProcesoCurricular.referencia_id == referencia_id)
            .values(fecha_actualizacion=datetime.now(UTC))
        )
        await session.execute(stmt)
    except Exception:
        pass


def _extract_actividad_descripcion(datos: dict[str, Any] | None) -> str:
    """Extract learning activity name from complementary dictionary."""
    if not datos or not isinstance(datos, dict):
        return ""
    if datos.get("actividades_aprendizaje"):
        return str(datos["actividades_aprendizaje"]).strip()
    if datos.get("actividad_aprendizaje"):
        return str(datos["actividad_aprendizaje"]).strip()
    rap_map = datos.get("rap_complementary_map")
    if isinstance(rap_map, dict):
        for val in rap_map.values():
            if isinstance(val, dict) and val.get("actividades_aprendizaje"):
                return str(val["actividades_aprendizaje"]).strip()
    return ""



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
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> PlaneacionContextoDTO:
    """Fetch active program and project tree structure for planning context."""
    if not await scope_service.can_access_process(current_user, referencia_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado al proceso curricular",
        )
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
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> list[PlaneacionListDTO]:
    """List all created planning items for a specific project formativo."""
    if not await scope_service.can_access_project(current_user, proyecto_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado al proyecto formativo",
        )
    return await service.listar_planeaciones(proyecto_id)


@router.get(
    "/proyecto/{proyecto_id}/configuracion-formato-oficial",
    response_model=PlaneacionDocumentoConfigDTO,
)
async def obtener_configuracion_formato_oficial(
    proyecto_id: uuid.UUID,
    service: PlaneacionPedagogicaService = Depends(get_planeacion_service),
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> PlaneacionDocumentoConfigDTO:
    """Return shared institutional workbook metadata."""
    if not current_user.has_role(RolUsuario.ADMIN.value, RolUsuario.SUPERADMIN.value):
        if not await scope_service.can_access_project(current_user, proyecto_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado al proyecto")
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
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> PlaneacionDocumentoConfigDTO:
    """Persist shared institutional workbook metadata."""
    if not await scope_service.can_access_project(current_user, proyecto_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado al proyecto")
    try:
        result = await service.guardar_configuracion_documento(proyecto_id, dto)
        referencia_id = await _resolve_referencia_id(session, proyecto_id)
        actor_id = await _safe_actor_id(session, current_user)
        audit_repo = AuditRepository(session)
        await audit_repo.add_event(
            entidad="PlaneacionDocumentoConfig",
            entidad_id=proyecto_id,
            accion="CONFIGURACION_FORMATO_ACTUALIZADA",
            detalle={
                "clasificacion_informacion": dto.clasificacion_informacion,
                "equipo_gestion_curricular": dto.equipo_gestion_curricular,
                "regional": dto.regional,
                "centro_formacion": dto.centro_formacion,
            },
            actor_usuario_id=actor_id,
            referencia_id=referencia_id,
        )
        rev_service = RevisionCurricularService(session=session, scope_service=scope_service)
        await rev_service.invalidate_approval_on_mutation(proyecto_id, actor_id)
        await _touch_proceso(session, referencia_id)
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
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> FormatoOficialEstadoDTO:
    """Return consolidated generation readiness and counts."""
    if not current_user.has_role(RolUsuario.ADMIN.value, RolUsuario.SUPERADMIN.value):
        if not await scope_service.can_access_project(current_user, proyecto_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado al proyecto")
    return await service.obtener_estado_formato_consolidado(proyecto_id)


@router.post(
    "/proyecto/{proyecto_id}/generar-formato-oficial",
    response_model=FormatoOficialGeneradoDTO,
)
async def generar_formato_consolidado(
    proyecto_id: uuid.UUID,
    service: PlaneacionPedagogicaService = Depends(get_planeacion_service),
    session: AsyncSession = Depends(get_async_session),
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> FormatoOficialGeneradoDTO:
    """Generate and store the consolidated official project workbook."""
    if not await scope_service.can_access_project(current_user, proyecto_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado al proyecto")
    try:
        result = await service.generar_formato_consolidado(proyecto_id)
        referencia_id = await _resolve_referencia_id(session, proyecto_id)
        actor_id = await _safe_actor_id(session, current_user)
        audit_repo = AuditRepository(session)
        await audit_repo.add_event(
            entidad="ProyectoFormativo",
            entidad_id=proyecto_id,
            accion="GPFI_F_134_CONSOLIDADO_GENERADO",
            detalle={
                "file_name": result.file_name,
                "planeaciones_incluidas": result.planeaciones_incluidas,
                "filas_generadas": result.filas_generadas,
                "storage_key": result.storage_key,
            },
            actor_usuario_id=actor_id,
            referencia_id=referencia_id,
        )
        await _touch_proceso(session, referencia_id)
        await session.commit()
        return result
    except (PlaneacionAccessError, ValueError) as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/proyecto/{proyecto_id}/descargar-formato-oficial")
async def descargar_formato_consolidado(
    proyecto_id: uuid.UUID,
    service: PlaneacionPedagogicaService = Depends(get_planeacion_service),
    session: AsyncSession = Depends(get_async_session),
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> StreamingResponse:
    """Stream the latest consolidated workbook stored in MinIO."""
    # Pedagogical reviewers (ADMIN, SUPERADMIN) have inspection/preview rights during review
    is_pedagogical_reviewer = current_user.has_role(
        RolUsuario.ADMIN.value,
        RolUsuario.SUPERADMIN.value,
    )

    if not is_pedagogical_reviewer:
        if not await scope_service.can_access_project(current_user, proyecto_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado al proyecto")

        rev_service = RevisionCurricularService(session=session, scope_service=scope_service)
        autorizado, motivo = await rev_service.verify_download_authorization(proyecto_id)
        if not autorizado:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "DOWNLOAD_NOT_AUTHORIZED", "message": motivo},
            )

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
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> PlaneacionResponseDTO:
    """Retrieve detailed properties of a single pedagogical planning record."""
    if not current_user.has_role(RolUsuario.ADMIN.value, RolUsuario.SUPERADMIN.value):
        if not await scope_service.can_access_planning(current_user, planeacion_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a la planeación")
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
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> FormatoOficialEstadoDTO:
    """Return individual generation readiness from backend rules."""
    if not current_user.has_role(RolUsuario.ADMIN.value, RolUsuario.SUPERADMIN.value):
        if not await scope_service.can_access_planning(current_user, planeacion_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a la planeación")
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
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> FormatoOficialGeneradoDTO:
    """Regenerate one completed planning workbook."""
    if not await scope_service.can_access_planning(current_user, planeacion_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a la planeación")
    try:
        result = await service.generar_formato_individual(planeacion_id)
        planeacion = None
        try:
            planeacion = await session.get(PlaneacionPedagogica, planeacion_id)
        except Exception:
            pass
        proyecto_id = planeacion.proyecto_id if planeacion else None
        referencia_id = await _resolve_referencia_id(session, proyecto_id)
        actor_id = await _safe_actor_id(session, current_user)
        audit_repo = AuditRepository(session)
        await audit_repo.add_event(
            entidad="PlaneacionPedagogica",
            entidad_id=planeacion_id,
            accion="GPFI_F_134_INDIVIDUAL_GENERADO",
            detalle={
                "planeacion_id": str(planeacion_id),
                "file_name": result.file_name,
                "filas_generadas": result.filas_generadas,
                "storage_key": result.storage_key,
            },
            actor_usuario_id=actor_id,
            referencia_id=referencia_id,
        )
        await _touch_proceso(session, referencia_id)
        await session.commit()
        return result
    except (PlaneacionAccessError, ValueError) as error:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/{planeacion_id}/descargar-formato-oficial")
async def descargar_formato_individual(
    planeacion_id: uuid.UUID,
    service: PlaneacionPedagogicaService = Depends(get_planeacion_service),
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> StreamingResponse:
    """Stream one official workbook stored in MinIO."""
    if not current_user.has_role(RolUsuario.ADMIN.value, RolUsuario.SUPERADMIN.value):
        if not await scope_service.can_access_planning(current_user, planeacion_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a la planeación")
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
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> PlaneacionResponseDTO:
    """Create or update a pedagogical planning draft."""
    if not await scope_service.can_access_project(current_user, dto.proyecto_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado al proyecto")
    try:
        is_creation = dto.planeacion_id is None
        res = await service.guardar_borrador(dto)
        referencia_id = await _resolve_referencia_id(session, dto.proyecto_id)
        actor_id = await _safe_actor_id(session, current_user)

        actividad_nombre = _extract_actividad_descripcion(dto.datos_complementarios)
        if not actividad_nombre and dto.actividad_id:
            try:
                act = await session.get(ActividadProyecto, dto.actividad_id)
                if act and act.descripcion:
                    actividad_nombre = act.descripcion
            except Exception:
                pass

        accion = "PLANEACION_CREADA" if is_creation else "PLANEACION_ACTUALIZADA"
        audit_repo = AuditRepository(session)
        await audit_repo.add_event(
            entidad="PlaneacionPedagogica",
            entidad_id=res.id,
            accion=accion,
            detalle={
                "planeacion_id": str(res.id),
                "proyecto_id": str(dto.proyecto_id),
                "actividad_id": str(dto.actividad_id),
                "descripcion_actividad": actividad_nombre,
                "resultados_count": len(dto.resultados_ids),
                "conocimientos_count": len(dto.conocimientos_ids),
                "criterios_count": len(dto.criterios_ids),
            },
            actor_usuario_id=actor_id,
            referencia_id=referencia_id,
        )
        rev_service = RevisionCurricularService(session=session, scope_service=scope_service)
        await rev_service.invalidate_approval_on_mutation(dto.proyecto_id, actor_id)
        await _touch_proceso(session, referencia_id)
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
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> PlaneacionResponseDTO:
    """Transition state to COMPLETE, build output and store it in MinIO."""
    if not await scope_service.can_access_planning(current_user, planeacion_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a la planeación")
    try:
        res = await service.confirmar_y_generar(planeacion_id)
        referencia_id = await _resolve_referencia_id(session, res.proyecto_id)
        actor_id = await _safe_actor_id(session, current_user)

        actividad_nombre = _extract_actividad_descripcion(res.datos_complementarios)
        if not actividad_nombre and res.actividad_id:
            try:
                act = await session.get(ActividadProyecto, res.actividad_id)
                if act and act.descripcion:
                    actividad_nombre = act.descripcion
            except Exception:
                pass

        audit_repo = AuditRepository(session)
        await audit_repo.add_event(
            entidad="PlaneacionPedagogica",
            entidad_id=res.id,
            accion="PLANEACION_COMPLETADA",
            detalle={
                "planeacion_id": str(res.id),
                "proyecto_id": str(res.proyecto_id),
                "actividad_id": str(res.actividad_id) if res.actividad_id else None,
                "descripcion_actividad": actividad_nombre,
                "file_name": res.file_name,
                "storage_key": res.storage_key,
            },
            actor_usuario_id=actor_id,
            referencia_id=referencia_id,
        )
        rev_service = RevisionCurricularService(session=session, scope_service=scope_service)
        await rev_service.invalidate_approval_on_mutation(res.proyecto_id, actor_id)
        await _touch_proceso(session, referencia_id)
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
    current_user: Usuario = Depends(get_current_user),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> dict[str, str]:
    """Delete a pedagogical planning from database and cancel related artifacts."""
    if not await scope_service.can_access_planning(current_user, planeacion_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a la planeación")
    try:
        planeacion = None
        try:
            planeacion = await session.get(PlaneacionPedagogica, planeacion_id)
        except Exception:
            pass

        proyecto_id = planeacion.proyecto_id if planeacion else None
        referencia_id = await _resolve_referencia_id(session, proyecto_id)
        actor_id = await _safe_actor_id(session, current_user)

        actividad_nombre = ""
        if planeacion:
            actividad_nombre = _extract_actividad_descripcion(planeacion.datos_complementarios)
            if not actividad_nombre and planeacion.actividad_id:
                try:
                    act = await session.get(ActividadProyecto, planeacion.actividad_id)
                    if act and act.descripcion:
                        actividad_nombre = act.descripcion
                except Exception:
                    pass

        await service.eliminar_planeacion(planeacion_id)

        audit_repo = AuditRepository(session)
        await audit_repo.add_event(
            entidad="PlaneacionPedagogica",
            entidad_id=planeacion_id,
            accion="PLANEACION_ELIMINADA",
            detalle={
                "planeacion_id": str(planeacion_id),
                "proyecto_id": str(proyecto_id) if proyecto_id else None,
                "descripcion_actividad": actividad_nombre,
            },
            actor_usuario_id=actor_id,
            referencia_id=referencia_id,
        )
        if proyecto_id:
            rev_service = RevisionCurricularService(session=session, scope_service=scope_service)
            await rev_service.invalidate_approval_on_mutation(proyecto_id, actor_id)
        await _touch_proceso(session, referencia_id)
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
