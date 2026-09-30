"""REST controller for pedagogical review, submissions, feedback, and approvals."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.revision_curricular import (
    AjusteReportarDTO,
    AprobacionRequestDTO,
    BandejaRevisionFiltrosDTO,
    BandejaRevisionPaginadaDTO,
    EntregaRevisionDetalleDTO,
    EnvioRevisionRequestDTO,
    LearningResultVersionDTO,
    ObservacionCreateDTO,
    ObservacionDTO,
    PlaneacionRevisionDetalleDTO,
    PlaneacionesEntregaListDTO,
    PlanningEditRequestApproveDTO,
    PlanningEditRequestCreateDTO,
    PlanningEditRequestDTO,
    PlanningEditRequestRejectDTO,
    PreflightEnvioRevisionDTO,
)
from src.application.services.access_scope import AccessScopeService
from src.application.services.revision_curricular_service import (
    RevisionCurricularService,
)
from src.domain.shared.enums import (
    EstadoEntregaRevision,
    EstadoSolicitudReapertura,
)
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.session import get_async_session
from src.interfaces.http.deps import (
    get_access_scope_service,
    get_current_user,
)

router = APIRouter(prefix="/api/v1/revision-curricular", tags=["revision-curricular"])


def get_revision_service(
    session: AsyncSession = Depends(get_async_session),
    scope_service: AccessScopeService = Depends(get_access_scope_service),
) -> RevisionCurricularService:
    """Build request-scoped revision service instance."""
    return RevisionCurricularService(session=session, scope_service=scope_service)


# -----------------------------------------------------------------------------
# Flujo del Equipo Ejecutor
# -----------------------------------------------------------------------------


@router.get(
    "/proceso/{referencia_id}/preflight-envio",
    response_model=PreflightEnvioRevisionDTO,
    status_code=status.HTTP_200_OK,
)
async def preflight_envio(
    referencia_id: uuid.UUID,
    service: RevisionCurricularService = Depends(get_revision_service),
    current_user: Usuario = Depends(get_current_user),
) -> PreflightEnvioRevisionDTO:
    """Validate server-side if the process is ready to be submitted for pedagogical review."""
    return await service.validate_preflight_envio(current_user, referencia_id)


@router.post(
    "/proceso/{referencia_id}/enviar",
    response_model=EntregaRevisionDetalleDTO,
    status_code=status.HTTP_201_CREATED,
)
async def enviar_proceso(
    referencia_id: uuid.UUID,
    dto: EnvioRevisionRequestDTO,
    service: RevisionCurricularService = Depends(get_revision_service),
    current_user: Usuario = Depends(get_current_user),
) -> EntregaRevisionDetalleDTO:
    """Submit or resubmit a completed curricular process for pedagogical review."""
    return await service.enviar_a_revision(current_user, referencia_id, dto)


@router.get(
    "/proceso/{referencia_id}/estado-actual",
    response_model=EntregaRevisionDetalleDTO | None,
    status_code=status.HTTP_200_OK,
)
async def obtener_estado_actual(
    referencia_id: uuid.UUID,
    service: RevisionCurricularService = Depends(get_revision_service),
    current_user: Usuario = Depends(get_current_user),
) -> EntregaRevisionDetalleDTO | None:
    """Fetch the latest active delivery, observations, and download status for the process."""
    return await service.obtener_estado_actual(current_user, referencia_id)


@router.post(
    "/observaciones/{observacion_id}/reportar-ajuste",
    response_model=ObservacionDTO,
    status_code=status.HTTP_200_OK,
)
async def reportar_ajuste(
    observacion_id: uuid.UUID,
    dto: AjusteReportarDTO,
    service: RevisionCurricularService = Depends(get_revision_service),
    current_user: Usuario = Depends(get_current_user),
) -> ObservacionDTO:
    """Report that an observation was addressed by the executing team."""
    return await service.reportar_ajuste(current_user, observacion_id, dto)


# -----------------------------------------------------------------------------
# Flujo del Equipo Pedagógico (Supervisión / Revisor)
# -----------------------------------------------------------------------------


@router.get(
    "/bandeja",
    response_model=BandejaRevisionPaginadaDTO,
    status_code=status.HTTP_200_OK,
)
async def bandeja_revision(
    estado: EstadoEntregaRevision | None = None,
    programa_id: uuid.UUID | None = None,
    equipo_ejecutor_id: uuid.UUID | None = None,
    lider_id: uuid.UUID | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    service: RevisionCurricularService = Depends(get_revision_service),
    current_user: Usuario = Depends(get_current_user),
) -> BandejaRevisionPaginadaDTO:
    """Return paginated pedagogical review inbox with real summary metrics."""
    filtros = BandejaRevisionFiltrosDTO(
        estado=estado,
        programa_id=programa_id,
        equipo_ejecutor_id=equipo_ejecutor_id,
        lider_id=lider_id,
        page=page,
        limit=limit,
    )
    return await service.obtener_bandeja_pedagogica(current_user, filtros)


@router.get(
    "/entregas/{entrega_id}",
    response_model=EntregaRevisionDetalleDTO,
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/entregas/{entrega_id}/detalle-completo",
    response_model=EntregaRevisionDetalleDTO,
    status_code=status.HTTP_200_OK,
)
async def detalle_completo_entrega(
    entrega_id: uuid.UUID,
    service: RevisionCurricularService = Depends(get_revision_service),
    current_user: Usuario = Depends(get_current_user),
) -> EntregaRevisionDetalleDTO:
    """Fetch complete detail of a delivery version including observations and version history."""
    return await service.obtener_detalle_entrega(current_user, entrega_id)


@router.get(
    "/entregas/{entrega_id}/planeaciones",
    response_model=PlaneacionesEntregaListDTO,
    status_code=status.HTTP_200_OK,
)
async def planeaciones_entrega(
    entrega_id: uuid.UUID,
    service: RevisionCurricularService = Depends(get_revision_service),
    current_user: Usuario = Depends(get_current_user),
) -> PlaneacionesEntregaListDTO:
    """Fetch structured tree of plannings frozen in this delivery snapshot."""
    return await service.obtener_planeaciones_entrega(current_user, entrega_id)


@router.get(
    "/entregas/{entrega_id}/planeaciones/{planeacion_id}",
    response_model=PlaneacionRevisionDetalleDTO,
    status_code=status.HTTP_200_OK,
)
async def planeacion_detalle_entrega(
    entrega_id: uuid.UUID,
    planeacion_id: uuid.UUID,
    service: RevisionCurricularService = Depends(get_revision_service),
    current_user: Usuario = Depends(get_current_user),
) -> PlaneacionRevisionDetalleDTO:
    """Fetch read-only full curricular details and contextual observations of one planning in this delivery."""
    return await service.obtener_planeacion_detalle_entrega(current_user, entrega_id, planeacion_id)


@router.post(
    "/entregas/{entrega_id}/iniciar-revision",
    response_model=EntregaRevisionDetalleDTO,
    status_code=status.HTTP_200_OK,
)
async def iniciar_revision(
    entrega_id: uuid.UUID,
    service: RevisionCurricularService = Depends(get_revision_service),
    current_user: Usuario = Depends(get_current_user),
) -> EntregaRevisionDetalleDTO:
    """Transition delivery to EN_REVISION state."""
    return await service.iniciar_revision(current_user, entrega_id)


@router.post(
    "/entregas/{entrega_id}/observaciones",
    response_model=ObservacionDTO,
    status_code=status.HTTP_201_CREATED,
)
async def crear_observacion(
    entrega_id: uuid.UUID,
    dto: ObservacionCreateDTO,
    service: RevisionCurricularService = Depends(get_revision_service),
    current_user: Usuario = Depends(get_current_user),
) -> ObservacionDTO:
    """Create a contextual observation on a specific element or section."""
    return await service.crear_observacion(current_user, entrega_id, dto)


@router.post(
    "/observaciones/{observacion_id}/resolver",
    response_model=ObservacionDTO,
    status_code=status.HTTP_200_OK,
)
async def resolver_observacion(
    observacion_id: uuid.UUID,
    service: RevisionCurricularService = Depends(get_revision_service),
    current_user: Usuario = Depends(get_current_user),
) -> ObservacionDTO:
    """Confirm and resolve an observation (pedagogical reviewer only)."""
    return await service.resolver_observacion(current_user, observacion_id)


@router.post(
    "/entregas/{entrega_id}/solicitar-ajustes",
    response_model=EntregaRevisionDetalleDTO,
    status_code=status.HTTP_200_OK,
)
async def solicitar_ajustes(
    entrega_id: uuid.UUID,
    service: RevisionCurricularService = Depends(get_revision_service),
    current_user: Usuario = Depends(get_current_user),
) -> EntregaRevisionDetalleDTO:
    """Formally request adjustments from the executor team based on pending observations."""
    return await service.solicitar_ajustes(current_user, entrega_id)


@router.post(
    "/entregas/{entrega_id}/aprobar",
    response_model=EntregaRevisionDetalleDTO,
    status_code=status.HTTP_200_OK,
)
async def aprobar_entrega(
    entrega_id: uuid.UUID,
    dto: AprobacionRequestDTO,
    service: RevisionCurricularService = Depends(get_revision_service),
    current_user: Usuario = Depends(get_current_user),
) -> EntregaRevisionDetalleDTO:
    """Formally approve the delivery, authorize consolidated download, and lock Learning Results."""
    return await service.aprobar_entrega(current_user, entrega_id, dto)


# -----------------------------------------------------------------------------
# Solicitudes de Reapertura y Versiones de Resultados de Aprendizaje
# -----------------------------------------------------------------------------


@router.post(
    "/solicitudes-modificacion",
    response_model=PlanningEditRequestDTO,
    status_code=status.HTTP_201_CREATED,
)
async def crear_solicitud_modificacion(
    dto: PlanningEditRequestCreateDTO,
    service: RevisionCurricularService = Depends(get_revision_service),
    current_user: Usuario = Depends(get_current_user),
) -> PlanningEditRequestDTO:
    """Create a formal request from the Executor Team Leader to reopen approved Learning Results."""
    return await service.crear_solicitud_reapertura(current_user, dto)


@router.get(
    "/solicitudes-modificacion",
    response_model=list[PlanningEditRequestDTO],
    status_code=status.HTTP_200_OK,
)
async def listar_solicitudes_modificacion(
    planning_id: uuid.UUID | None = None,
    referencia_id: uuid.UUID | None = None,
    status: EstadoSolicitudReapertura | None = None,
    service: RevisionCurricularService = Depends(get_revision_service),
    current_user: Usuario = Depends(get_current_user),
) -> list[PlanningEditRequestDTO]:
    """List edit requests filtered by planning, process reference, or status."""
    return await service.listar_solicitudes_reapertura(
        current_user,
        planning_id=planning_id,
        referencia_id=referencia_id,
        status_filter=status,
    )


@router.get(
    "/solicitudes-modificacion/{request_id}",
    response_model=PlanningEditRequestDTO,
    status_code=status.HTTP_200_OK,
)
async def obtener_solicitud_modificacion(
    request_id: uuid.UUID,
    service: RevisionCurricularService = Depends(get_revision_service),
    current_user: Usuario = Depends(get_current_user),
) -> PlanningEditRequestDTO:
    """Fetch complete detail of a specific edit request."""
    return await service.obtener_solicitud_reapertura(current_user, request_id)


@router.post(
    "/solicitudes-modificacion/{request_id}/aprobar",
    response_model=PlanningEditRequestDTO,
    status_code=status.HTTP_200_OK,
)
async def aprobar_solicitud_modificacion(
    request_id: uuid.UUID,
    dto: PlanningEditRequestApproveDTO,
    service: RevisionCurricularService = Depends(get_revision_service),
    current_user: Usuario = Depends(get_current_user),
) -> PlanningEditRequestDTO:
    """Approve all or selected Learning Results in an edit request (Pedagogical Admin only)."""
    return await service.aprobar_solicitud_reapertura(current_user, request_id, dto)


@router.post(
    "/solicitudes-modificacion/{request_id}/rechazar",
    response_model=PlanningEditRequestDTO,
    status_code=status.HTTP_200_OK,
)
async def rechazar_solicitud_modificacion(
    request_id: uuid.UUID,
    dto: PlanningEditRequestRejectDTO,
    service: RevisionCurricularService = Depends(get_revision_service),
    current_user: Usuario = Depends(get_current_user),
) -> PlanningEditRequestDTO:
    """Reject an edit request, keeping all Learning Results locked (Pedagogical Admin only)."""
    return await service.rechazar_solicitud_reapertura(current_user, request_id, dto)


@router.get(
    "/planeaciones/{planning_id}/versiones-resultados",
    response_model=list[LearningResultVersionDTO],
    status_code=status.HTTP_200_OK,
)
async def listar_versiones_resultados(
    planning_id: uuid.UUID,
    learning_result_id: uuid.UUID | None = None,
    service: RevisionCurricularService = Depends(get_revision_service),
    current_user: Usuario = Depends(get_current_user),
) -> list[LearningResultVersionDTO]:
    """Return approved version history snapshots for Learning Results in a planning."""
    return await service.listar_versiones_resultado(
        current_user,
        planning_id=planning_id,
        learning_result_id=learning_result_id,
    )

