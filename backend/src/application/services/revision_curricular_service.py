"""Service for Curricular Submission, Pedagogical Review, Feedback, and Approval Workflow."""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from copy import deepcopy
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.dto.revision_curricular import (
    ActividadProyectoResumenDTO,
    AjusteReportarDTO,
    AprobacionRequestDTO,
    BandejaRevisionFiltrosDTO,
    BandejaRevisionPaginadaDTO,
    CompetenciaResumenDTO,
    ConocimientoResumenDTO,
    CriterioResumenDTO,
    EntregaRevisionDetalleDTO,
    EntregaRevisionResumenDTO,
    EnvioRevisionRequestDTO,
    FaseResumenDTO,
    HorasPlaneacionDTO,
    LearningResultVersionDTO,
    ObservacionCreateDTO,
    ObservacionDTO,
    PlaneacionRevisionDetalleDTO,
    PlaneacionRevisionItemDTO,
    PlaneacionesEntregaListDTO,
    PlanningEditRequestApproveDTO,
    PlanningEditRequestCreateDTO,
    PlanningEditRequestDTO,
    PlanningEditRequestItemDTO,
    PlanningEditRequestRejectDTO,
    PreflightEnvioRevisionDTO,
    RAPResumenDTO,
)
from src.application.services.access_scope import AccessScopeService
from src.application.services.notification_events import notification_dispatcher
from src.domain.shared.enums import (
    EstadoAprobacionPlaneacion,
    EstadoBloque,
    EstadoEdicionRA,
    EstadoEntregaRevision,
    EstadoEquipo,
    EstadoObservacionRevision,
    EstadoRevisionPlaneacion,
    EstadoSolicitudReapertura,
    RolUsuario,
    SeccionObservacionPlaneacion,
    TipoElementoObservacion,
)
from src.infrastructure.db.models.audit import EventoAuditoria
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.models.curriculum import ResultadoAprendizaje
from src.infrastructure.db.models.organizacion import (
    EquipoEjecutor,
    ProcesoCurricular,
)
from src.infrastructure.db.models.planeacion import (
    PlaneacionDocumentoConfig,
    PlaneacionPedagogica,
    planeacion_resultados,
)
from src.infrastructure.db.models.proyecto import (
    ActividadProyecto,
    FaseProyecto,
)
from src.infrastructure.db.models.revision_curricular import (
    EntregaRevisionCurricular,
    LearningResultVersion,
    ObservacionRevision,
    PlanningEditRequest,
    PlanningEditRequestItem,
)


class RevisionCurricularService:
    """Orchestrates the pedagogical review, feedback, and approval lifecycle."""

    def __init__(
        self,
        session: AsyncSession,
        scope_service: AccessScopeService | None = None,
    ) -> None:
        self.session = session
        self.scope_service = scope_service or AccessScopeService(session)

    # -------------------------------------------------------------------------
    # Preflight Validation
    # -------------------------------------------------------------------------

    async def validate_preflight_envio(
        self,
        actor: Usuario,
        referencia_id: UUID,
    ) -> PreflightEnvioRevisionDTO:
        """Evaluate if the curricular process satisfies all criteria to be submitted."""
        # 1. Require operational membership or leadership in the executor team
        await self.scope_service.require_process_access(actor, referencia_id)

        proceso = await self._get_proceso_by_ref(referencia_id)
        if not proceso:
            return PreflightEnvioRevisionDTO(
                listo=False,
                pendientes=["Proceso curricular no encontrado."],
            )

        pendientes: list[str] = []
        advertencias: list[str] = []

        # Team checks
        if not proceso.equipo_ejecutor_id or not proceso.equipo_ejecutor:
            pendientes.append("El proceso curricular no tiene un Equipo Ejecutor asignado.")
        elif proceso.equipo_ejecutor.estado != EstadoEquipo.ACTIVO:
            pendientes.append("El Equipo Ejecutor asignado se encuentra inactivo.")

        # Program checks
        if not proceso.programa_id or not proceso.programa:
            pendientes.append("El programa de formación no está cargado o asociado.")
        elif proceso.programa.estado != EstadoBloque.COMPLETO:
            prog_est = getattr(proceso.programa.estado, "value", str(proceso.programa.estado)) if proceso.programa.estado else "INCOMPLETO"
            pendientes.append(f"El programa de formación está en estado '{prog_est}', debe estar 'COMPLETO'.")

        # Project checks
        if not proceso.proyecto_id or not proceso.proyecto:
            pendientes.append("El proyecto formativo no está cargado o asociado.")
        elif proceso.proyecto.estado != EstadoBloque.COMPLETO:
            proy_est = getattr(proceso.proyecto.estado, "value", str(proceso.proyecto.estado)) if proceso.proyecto.estado else "INCOMPLETO"
            pendientes.append(f"El proyecto formativo está en estado '{proy_est}', debe estar 'COMPLETO'.")

        # Plannings check: Requires at least 1 completed planning; partial submissions are allowed
        total_actividades = 0
        planeaciones_completas = 0
        planeaciones_borrador = 0
        actividades_sin_planeacion: list[str] = []

        if proceso.proyecto_id:
            # Query all activities of the project formativo
            act_stmt = (
                select(ActividadProyecto)
                .join(FaseProyecto, ActividadProyecto.fase_id == FaseProyecto.id)
                .where(FaseProyecto.proyecto_id == proceso.proyecto_id)
            )
            act_res = await self.session.execute(act_stmt)
            actividades = act_res.scalars().all()
            total_actividades = len(actividades)

            plan_stmt = select(PlaneacionPedagogica).where(
                PlaneacionPedagogica.proyecto_id == proceso.proyecto_id
            )
            plan_res = await self.session.execute(plan_stmt)
            planeaciones = plan_res.scalars().all()

            actividades_con_completa = {
                p.actividad_id
                for p in planeaciones
                if p.actividad_id and p.estado == EstadoBloque.COMPLETO
            }
            planeaciones_completas = len([p for p in planeaciones if p.estado == EstadoBloque.COMPLETO])
            planeaciones_borrador = len([p for p in planeaciones if p.estado != EstadoBloque.COMPLETO])

            if planeaciones_completas == 0:
                pendientes.append("Debe existir al menos 1 planeación pedagógica en estado COMPLETO para enviar a revisión.")

            if planeaciones_borrador > 0:
                pendientes.append(f"Existen {planeaciones_borrador} planeación(es) en estado BORRADOR que deben completarse o eliminarse.")

            for act in actividades:
                if act.id not in actividades_con_completa:
                    desc_corta = (act.descripcion[:60] + "...") if len(act.descripcion) > 60 else act.descripcion
                    actividades_sin_planeacion.append(f"Actividad '{desc_corta}'")

            if actividades_sin_planeacion and planeaciones_completas > 0:
                advertencias.append(
                    f"Entrega parcial: {planeaciones_completas} de {total_actividades} actividades de proyecto cuentan con planeación completa. "
                    f"Quedan {len(actividades_sin_planeacion)} actividad(es) sin planeación que podrán ser enviadas en entregas posteriores."
                )

            # Document config check
            config_stmt = select(PlaneacionDocumentoConfig).where(
                PlaneacionDocumentoConfig.proyecto_id == proceso.proyecto_id
            )
            config_res = await self.session.execute(config_stmt)
            doc_config = config_res.scalar_one_or_none()

            if not doc_config:
                pendientes.append("No se ha registrado la Configuración Documental institucional.")
            else:
                if not doc_config.fecha_elaboracion:
                    pendientes.append("Falta la fecha de elaboración en la Configuración Documental.")
                if not doc_config.regional or not doc_config.regional.strip():
                    pendientes.append("Falta la Regional en la Configuración Documental.")
                if not doc_config.centro_formacion or not doc_config.centro_formacion.strip():
                    pendientes.append("Falta el Centro de Formación en la Configuración Documental.")
                if not doc_config.equipo_gestion_curricular or len(doc_config.equipo_gestion_curricular) == 0:
                    pendientes.append("Falta registrar el Equipo de Gestión Curricular en la Configuración Documental.")
                if not doc_config.storage_key:
                    pendientes.append("Debe generar previamente el consolidado oficial GPFI-F-134 V05 en MinIO.")

        # Check existing active delivery
        active_delivery = await self._get_latest_delivery_by_ref(referencia_id)
        if active_delivery and active_delivery.estado in (
            EstadoEntregaRevision.ENVIADO_REVISION,
            EstadoEntregaRevision.EN_REVISION,
            EstadoEntregaRevision.REENVIADO,
        ):
            pendientes.append(f"Ya existe una entrega en curso ({active_delivery.estado.value}, Versión {active_delivery.version}) pendiente de evaluación pedagógica.")

        resumen: dict[str, Any] = {
            "total_actividades_proyecto": total_actividades,
            "planeaciones_completas": planeaciones_completas,
            "planeaciones_borrador": planeaciones_borrador,
            "actividades_sin_planeacion": actividades_sin_planeacion,
            "es_entrega_parcial": len(actividades_sin_planeacion) > 0 and planeaciones_completas > 0,
            "faltantes_count": len(pendientes),
            "version_actual": active_delivery.version if active_delivery else 0,
            "estado_actual": active_delivery.estado.value if active_delivery else "BORRADOR",
        }

        return PreflightEnvioRevisionDTO(
            listo=len(pendientes) == 0,
            pendientes=pendientes,
            advertencias=advertencias,
            resumen=resumen,
        )

    # -------------------------------------------------------------------------
    # Submission & Resubmission (Equipo Ejecutor)
    # -------------------------------------------------------------------------

    async def enviar_a_revision(
        self,
        actor: Usuario,
        referencia_id: UUID,
        dto: EnvioRevisionRequestDTO,
    ) -> EntregaRevisionDetalleDTO:
        """Submit or resubmit a curricular process to pedagogical review."""
        preflight = await self.validate_preflight_envio(actor, referencia_id)
        if not preflight.listo:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "PREFLIGHT_VALIDATION_FAILED",
                    "message": "No es posible enviar el proceso a revisión pedagógica.",
                    "pendientes": preflight.pendientes,
                },
            )

        proceso = await self._get_proceso_by_ref(referencia_id, for_update=True)
        if not proceso or not proceso.equipo_ejecutor_id or not proceso.programa_id or not proceso.proyecto_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Proceso curricular incompleto para envío.",
            )

        # Get latest delivery if any
        latest = await self._get_latest_delivery_by_ref(referencia_id, for_update=True)

        new_version = 1
        new_state = EstadoEntregaRevision.ENVIADO_REVISION

        if latest:
            if latest.estado in (
                EstadoEntregaRevision.ENVIADO_REVISION,
                EstadoEntregaRevision.EN_REVISION,
                EstadoEntregaRevision.REENVIADO,
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ya existe una versión ({latest.version}) en proceso de revisión pedagógica.",
                )
            new_version = latest.version + 1
            new_state = EstadoEntregaRevision.REENVIADO

        # Build snapshot metadata for tampering detection
        snapshot = await self._build_snapshot_metadatos(proceso.proyecto_id)
        now = datetime.now(UTC)

        nueva_entrega = EntregaRevisionCurricular(
            id=uuid.uuid4(),
            proceso_curricular_id=proceso.id,
            referencia_id=referencia_id,
            equipo_ejecutor_id=proceso.equipo_ejecutor_id,
            programa_id=proceso.programa_id,
            proyecto_id=proceso.proyecto_id,
            version=new_version,
            estado=new_state,
            enviado_por_id=actor.id,
            fecha_envio=now,
            descarga_habilitada=False,
            snapshot_metadatos=snapshot,
            notas_entrega=dto.notas_entrega,
        )
        self.session.add(nueva_entrega)

        # Re-lock RAs and transition plannings to IN_REVIEW / LOCKED
        plan_stmt = (
            select(PlaneacionPedagogica)
            .where(PlaneacionPedagogica.proyecto_id == proceso.proyecto_id)
            .options(selectinload(PlaneacionPedagogica.resultados))
        )
        plan_res = await self.session.execute(plan_stmt)
        plans = list(plan_res.scalars().all())

        relocked_ra_ids: list[str] = []
        for p in plans:
            was_reopened = (
                p.review_status == EstadoRevisionPlaneacion.CHANGES_ALLOWED
                or p.approval_status == EstadoAprobacionPlaneacion.PREVIOUS_VERSION_APPROVED
                or p.unlock_request_id is not None
            )
            p.review_status = EstadoRevisionPlaneacion.IN_REVIEW
            p.edit_status = EstadoEdicionRA.LOCKED
            p.locked_at = now
            p.locked_by = actor.id

            datos = deepcopy(p.datos_complementarios or {})
            ra_locks = datos.get("ra_locks") if isinstance(datos.get("ra_locks"), dict) else {}

            for r in p.resultados:
                was_ra_unlocked = (
                    getattr(r, "edit_status", EstadoEdicionRA.EDITABLE) == EstadoEdicionRA.EDITABLE
                    and (getattr(r, "unlock_request_id", None) is not None or (getattr(r, "approved_version", 0) or 0) >= 1 or was_reopened)
                )
                r.edit_status = EstadoEdicionRA.LOCKED
                r.locked_at = now
                r.locked_by = actor.id

                ra_key = str(r.id)
                prev_lock = ra_locks.get(ra_key, {}) if isinstance(ra_locks.get(ra_key), dict) else {}
                ra_locks[ra_key] = {
                    **prev_lock,
                    "edit_status": EstadoEdicionRA.LOCKED.value,
                    "locked_at": now.isoformat(),
                    "locked_by": str(actor.id),
                }
                await self.session.execute(
                    update(planeacion_resultados)
                    .where(
                        planeacion_resultados.c.planeacion_id == p.id,
                        planeacion_resultados.c.resultado_id == r.id,
                    )
                    .values(
                        edit_status=EstadoEdicionRA.LOCKED,
                        locked_at=now,
                        locked_by=actor.id,
                    )
                )
                if was_ra_unlocked:
                    relocked_ra_ids.append(ra_key)
                    await self._audit(
                        actor_id=actor.id,
                        referencia_id=referencia_id,
                        entidad="ResultadoAprendizaje",
                        entidad_id=r.id,
                        accion="LEARNING_RESULT_RELOCKED",
                        detalle={
                            "planeacion_id": str(p.id),
                            "learning_result_id": ra_key,
                            "version": new_version,
                            "motivo": "Reenvío de planeación a revisión pedagógica",
                        },
                    )

            datos["ra_locks"] = ra_locks
            p.datos_complementarios = datos

        # Complete any active APPROVED / PARTIALLY_APPROVED edit requests for these plannings
        if plans:
            plan_ids = [p.id for p in plans]
            req_stmt = (
                select(PlanningEditRequest)
                .where(
                    PlanningEditRequest.planning_id.in_(plan_ids),
                    PlanningEditRequest.status.in_([
                        EstadoSolicitudReapertura.APPROVED,
                        EstadoSolicitudReapertura.PARTIALLY_APPROVED,
                    ]),
                )
                .with_for_update()
            )
            req_res = await self.session.execute(req_stmt)
            active_requests = list(req_res.scalars().all())
            for req in active_requests:
                req.status = EstadoSolicitudReapertura.COMPLETED
                req.version = (req.version or 1) + 1
                req.updated_at = now

        # Audit
        action = "ENTREGA_CURRICULAR_REENVIADA" if new_version > 1 else "ENTREGA_CURRICULAR_ENVIADA"
        await self._audit(
            actor_id=actor.id,
            referencia_id=referencia_id,
            entidad="EntregaRevisionCurricular",
            entidad_id=nueva_entrega.id,
            accion=action,
            detalle={
                "version": new_version,
                "estado": new_state.value,
                "notas_entrega": dto.notas_entrega,
                "snapshot_checksum": snapshot.get("checksum_consolidado"),
                "relocked_ra_ids": relocked_ra_ids,
            },
        )
        if new_version > 1:
            await self._audit(
                actor_id=actor.id,
                referencia_id=referencia_id,
                entidad="EntregaRevisionCurricular",
                entidad_id=nueva_entrega.id,
                accion="PLANNING_RESUBMITTED",
                detalle={
                    "version": new_version,
                    "relocked_ra_ids": relocked_ra_ids,
                    "notas_entrega": dto.notas_entrega,
                },
            )
            notification_dispatcher.emit(
                event_type="planning.resubmitted",
                actor_id=actor.id,
                referencia_id=referencia_id,
                team_id=proceso.equipo_ejecutor_id,
                payload={
                    "entrega_id": str(nueva_entrega.id),
                    "version": new_version,
                    "relocked_ra_ids": relocked_ra_ids,
                },
            )

        await self.session.commit()
        return await self.obtener_detalle_entrega(actor, nueva_entrega.id)

    # -------------------------------------------------------------------------
    # Pedagogical Review Management (Admin / Superadmin)
    # -------------------------------------------------------------------------

    async def obtener_bandeja_pedagogica(
        self,
        actor: Usuario,
        filtros: BandejaRevisionFiltrosDTO,
    ) -> BandejaRevisionPaginadaDTO:
        """Return paginated inbox of all curricular deliveries for pedagogical reviewers."""
        self._require_pedagogical_reviewer(actor)

        # Base subquery to get latest version ID per process
        latest_version_subq = (
            select(
                EntregaRevisionCurricular.proceso_curricular_id,
                func.max(EntregaRevisionCurricular.version).label("max_version"),
            )
            .group_by(EntregaRevisionCurricular.proceso_curricular_id)
            .subquery()
        )

        # Main query joining latest versions
        stmt = (
            select(EntregaRevisionCurricular)
            .join(
                latest_version_subq,
                (EntregaRevisionCurricular.proceso_curricular_id == latest_version_subq.c.proceso_curricular_id)
                & (EntregaRevisionCurricular.version == latest_version_subq.c.max_version),
            )
            .options(
                selectinload(EntregaRevisionCurricular.equipo_ejecutor),
                selectinload(EntregaRevisionCurricular.programa),
                selectinload(EntregaRevisionCurricular.proyecto),
                selectinload(EntregaRevisionCurricular.enviado_por),
                selectinload(EntregaRevisionCurricular.observaciones),
            )
            .order_by(EntregaRevisionCurricular.fecha_envio.desc())
        )

        if filtros.estado:
            stmt = stmt.where(EntregaRevisionCurricular.estado == filtros.estado)
        if filtros.programa_id:
            stmt = stmt.where(EntregaRevisionCurricular.programa_id == filtros.programa_id)
        if filtros.equipo_ejecutor_id:
            stmt = stmt.where(EntregaRevisionCurricular.equipo_ejecutor_id == filtros.equipo_ejecutor_id)

        # Total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_items = (await self.session.execute(count_stmt)).scalar() or 0

        # Pagination
        offset = (filtros.page - 1) * filtros.limit
        paginated_stmt = stmt.offset(offset).limit(filtros.limit)
        items_res = (await self.session.execute(paginated_stmt)).scalars().all()

        # Calculate high level metrics across all latest submissions
        metricas = await self._calculate_inbox_metrics()

        items_dto = [self._to_resumen_dto(e) for e in items_res]
        total_pages = math.ceil(total_items / filtros.limit) if filtros.limit > 0 else 1

        return BandejaRevisionPaginadaDTO(
            items=items_dto,
            total=total_items,
            page=filtros.page,
            limit=filtros.limit,
            total_pages=total_pages,
            metricas=metricas,
        )

    async def obtener_detalle_entrega(
        self,
        actor: Usuario,
        entrega_id: UUID,
    ) -> EntregaRevisionDetalleDTO:
        """Fetch complete detail of a delivery version, observations, and version history."""
        stmt = (
            select(EntregaRevisionCurricular)
            .where(EntregaRevisionCurricular.id == entrega_id)
            .options(
                selectinload(EntregaRevisionCurricular.equipo_ejecutor).selectinload(EquipoEjecutor.lider),
                selectinload(EntregaRevisionCurricular.programa),
                selectinload(EntregaRevisionCurricular.proyecto),
                selectinload(EntregaRevisionCurricular.enviado_por),
                selectinload(EntregaRevisionCurricular.observaciones).selectinload(ObservacionRevision.creado_por),
                selectinload(EntregaRevisionCurricular.observaciones).selectinload(ObservacionRevision.ajuste_reportado_por),
                selectinload(EntregaRevisionCurricular.observaciones).selectinload(ObservacionRevision.resuelto_por),
            )
        )
        res = await self.session.execute(stmt)
        entrega = res.scalar_one_or_none()
        if not entrega:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entrega de revisión no encontrada.",
            )

        # Scope check: Must be pedagogical reviewer or member of the executor team
        if not actor.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value):
            await self.scope_service.require_process_access(actor, entrega.referencia_id)

        # Version history for the same process
        history_stmt = (
            select(EntregaRevisionCurricular)
            .where(EntregaRevisionCurricular.proceso_curricular_id == entrega.proceso_curricular_id)
            .options(
                selectinload(EntregaRevisionCurricular.equipo_ejecutor),
                selectinload(EntregaRevisionCurricular.programa),
                selectinload(EntregaRevisionCurricular.proyecto),
                selectinload(EntregaRevisionCurricular.enviado_por),
                selectinload(EntregaRevisionCurricular.observaciones),
            )
            .order_by(EntregaRevisionCurricular.version.desc())
        )
        history_res = (await self.session.execute(history_stmt)).scalars().all()
        historial_dto = [self._to_resumen_dto(h) for h in history_res]

        return self._to_detalle_dto(entrega, historial_dto)

    async def obtener_estado_actual(
        self,
        actor: Usuario,
        referencia_id: UUID,
    ) -> EntregaRevisionDetalleDTO | None:
        """Fetch the latest active delivery of the process for the current user."""
        await self.scope_service.require_process_access(actor, referencia_id)
        latest = await self._get_latest_delivery_by_ref(referencia_id)
        if not latest:
            return None
        return await self.obtener_detalle_entrega(actor, latest.id)

    async def iniciar_revision(
        self,
        actor: Usuario,
        entrega_id: UUID,
    ) -> EntregaRevisionDetalleDTO:
        """Transition delivery from ENVIADO_REVISION / REENVIADO to EN_REVISION."""
        self._require_pedagogical_reviewer(actor)

        stmt = select(EntregaRevisionCurricular).where(EntregaRevisionCurricular.id == entrega_id).with_for_update()
        res = await self.session.execute(stmt)
        entrega = res.scalar_one_or_none()
        if not entrega:
            raise HTTPException(status_code=404, detail="Entrega no encontrada.")

        if entrega.estado in (EstadoEntregaRevision.ENVIADO_REVISION, EstadoEntregaRevision.REENVIADO):
            entrega.estado = EstadoEntregaRevision.EN_REVISION
            entrega.revisado_por_id = actor.id
            entrega.fecha_inicio_revision = datetime.now(UTC)

            await self._audit(
                actor_id=actor.id,
                referencia_id=entrega.referencia_id,
                entidad="EntregaRevisionCurricular",
                entidad_id=entrega.id,
                accion="REVISION_CURRICULAR_INICIADA",
                detalle={"version": entrega.version},
            )
            await self.session.commit()

        return await self.obtener_detalle_entrega(actor, entrega.id)

    @staticmethod
    def _normalize_section_key(key: str | None) -> str | None:
        if not key:
            return None
        cleaned = (
            key.strip()
            .upper()
            .replace("Á", "A")
            .replace("É", "E")
            .replace("Í", "I")
            .replace("Ó", "O")
            .replace("Ú", "U")
            .replace(" ", "_")
            .replace("-", "_")
        )
        aliases = {
            "ACTIVIDADES_DE_APRENDIZAJE": "ACTIVIDADES_APRENDIZAJE",
            "DESCRIPCION_DE_LA_EVIDENCIA_DE_APRENDIZAJE": (
                "DESCRIPCION_EVIDENCIA_APRENDIZAJE"
            ),
            "EVIDENCIA_DE_APRENDIZAJE": (
                "DESCRIPCION_EVIDENCIA_APRENDIZAJE"
            ),
            "CRITERIOS_DE_EVALUACION": "CRITERIOS_EVALUACION",
            "ACTIVIDAD": "ACTIVIDAD_PROYECTO",
            "RESULTADOS": "RAPS",
            "RESULTADOS_APRENDIZAJE": "RAPS",
            "RESULTADOS_DE_APRENDIZAJE": "RAPS",
            "CONOCIMIENTOS": "SABERES",
            "CONOCIMIENTOS_SABER": "SABERES",
            "CONOCIMIENTOS_PROCESO": "SABERES",
            "CRITERIOS": "CRITERIOS_EVALUACION",
            "ESTRATEGIAS": "ESTRATEGIAS_DIDACTICAS",
            "AMBIENTE": "AMBIENTES",
            "MATERIAL": "MATERIALES",
            "INSTRUCTOR": "INSTRUCTORES",
            "HORA": "HORAS",
            "DURACION": "HORAS",
        }
        cleaned = aliases.get(cleaned, cleaned)
        if cleaned in {s.value for s in SeccionObservacionPlaneacion}:
            return cleaned
        return None

    @staticmethod
    def _parse_float(val: Any) -> float:
        if val is None or val == "":
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    async def obtener_planeaciones_entrega(
        self,
        actor: Usuario,
        entrega_id: UUID,
    ) -> PlaneacionesEntregaListDTO:
        """Fetch read-only list of plannings that belong exclusively to this delivery snapshot."""
        self._require_pedagogical_reviewer(actor)

        stmt = (
            select(EntregaRevisionCurricular)
            .where(EntregaRevisionCurricular.id == entrega_id)
            .options(selectinload(EntregaRevisionCurricular.observaciones))
        )
        res = await self.session.execute(stmt)
        entrega = res.scalar_one_or_none()
        if not entrega:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrega no encontrada.")

        snapshot = entrega.snapshot_metadatos or {}
        raw_ids = snapshot.get("planeaciones_ids", [])
        if not raw_ids:
            if int(snapshot.get("planeaciones_count") or 0) > 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El snapshot declara planeaciones, pero no contiene sus identificadores.",
                )
            return PlaneacionesEntregaListDTO(
                entrega_id=entrega.id,
                version=entrega.version,
                total=0,
                horas_directas_total=0.0,
                horas_independientes_total=0.0,
                planeaciones=[],
            )

        valid_ids: list[UUID] = []
        for item in raw_ids:
            try:
                valid_ids.append(UUID(str(item)))
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El snapshot contiene un identificador de planeación inválido.",
                ) from None

        # Query only the frozen planning IDs belonging to this project
        plan_stmt = (
            select(PlaneacionPedagogica)
            .where(
                PlaneacionPedagogica.id.in_(valid_ids),
                PlaneacionPedagogica.proyecto_id == entrega.proyecto_id,
            )
            .options(
                selectinload(PlaneacionPedagogica.fase),
                selectinload(PlaneacionPedagogica.actividad),
                selectinload(PlaneacionPedagogica.resultados).selectinload(ResultadoAprendizaje.competencia),
            )
        )
        plan_res = await self.session.execute(plan_stmt)
        plans = list(plan_res.scalars().all())
        if len(plans) != len(set(valid_ids)):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No fue posible resolver todas las planeaciones congeladas en la entrega.",
            )

        obs_total_map: dict[UUID, int] = {}
        obs_pending_map: dict[UUID, int] = {}
        for o in (entrega.observaciones or []):
            if o.target_type == TipoElementoObservacion.PLANEACION and o.target_id:
                obs_total_map[o.target_id] = obs_total_map.get(o.target_id, 0) + 1
                if o.estado == EstadoObservacionRevision.PENDIENTE:
                    obs_pending_map[o.target_id] = obs_pending_map.get(o.target_id, 0) + 1

        items: list[PlaneacionRevisionItemDTO] = []
        total_directas = 0.0
        total_independientes = 0.0

        for p in plans:
            data = p.datos_complementarios or {}
            h_direct = self._parse_float(data.get("horas_trabajo_directo"))
            h_indep = self._parse_float(data.get("horas_trabajo_independiente"))
            h_total = self._parse_float(data.get("duracion_actividad_horas") or data.get("duracion_horas")) or (h_direct + h_indep)

            total_directas += h_direct
            total_independientes += h_indep

            comp_map: dict[UUID, CompetenciaResumenDTO] = {}
            all_raps: list[RAPResumenDTO] = []
            ra_locks_meta = data.get("ra_locks") if isinstance(data.get("ra_locks"), dict) else {}
            for r in p.resultados:
                comp = getattr(r, "competencia", None)
                if comp is None:
                    continue
                comp_id = comp.id
                comp_cod = comp.codigo_competencia if comp else "N/A"
                comp_nom = comp.nombre_competencia if comp else "Competencia"

                ra_meta = ra_locks_meta.get(str(r.id), {}) if isinstance(ra_locks_meta.get(str(r.id)), dict) else {}
                raw_edit_st = ra_meta.get("edit_status") or getattr(r, "edit_status", EstadoEdicionRA.EDITABLE)
                edit_st_str = raw_edit_st.value if hasattr(raw_edit_st, "value") else str(raw_edit_st)

                rap_dto = RAPResumenDTO(
                    id=r.id,
                    codigo=r.codigo_resultado,
                    descripcion=r.descripcion,
                    tipo_resultado=None,
                    edit_status=edit_st_str,
                    locked_at=getattr(r, "locked_at", None),
                    locked_by=getattr(r, "locked_by", None),
                    unlocked_at=getattr(r, "unlocked_at", None),
                    unlocked_by=getattr(r, "unlocked_by", None),
                    unlock_request_id=getattr(r, "unlock_request_id", None),
                    approved_version=getattr(r, "approved_version", 0) or 0,
                    approved_at=getattr(r, "approved_at", None),
                )
                all_raps.append(rap_dto)

                if comp_id not in comp_map:
                    comp_map[comp_id] = CompetenciaResumenDTO(
                        id=comp_id,
                        codigo=comp_cod,
                        nombre=comp_nom,
                        resultados_count=0,
                        resultados=[],
                    )
                comp_map[comp_id].resultados.append(rap_dto)
                comp_map[comp_id].resultados_count += 1

            actividades_text = str(data.get("actividades_aprendizaje") or "").strip()
            if not actividades_text and p.actividad:
                actividades_text = p.actividad.descripcion

            ambiente_text = str(
                data.get("ambiente")
                or data.get("ambientes_aprendizaje")
                or (", ".join(data.get("ambientes_tipificados", [])) if isinstance(data.get("ambientes_tipificados"), list) else data.get("ambientes_tipificados"))
                or ""
            ).strip() or None

            instructores_text = str(
                data.get("instructores")
                or data.get("instructor_responsable")
                or ""
            ).strip() or None

            rev_st = getattr(p, "review_status", EstadoRevisionPlaneacion.DRAFT)
            app_st = getattr(p, "approval_status", EstadoAprobacionPlaneacion.PENDING)
            ed_st = getattr(p, "edit_status", EstadoEdicionRA.EDITABLE)

            item_dto = PlaneacionRevisionItemDTO(
                id=p.id,
                estado=p.estado.value if hasattr(p.estado, "value") else str(p.estado),
                review_status=rev_st.value if hasattr(rev_st, "value") else str(rev_st),
                approval_status=app_st.value if hasattr(app_st, "value") else str(app_st),
                edit_status=ed_st.value if hasattr(ed_st, "value") else str(ed_st),
                official_version=getattr(p, "official_version", 0) or 0,
                fase=FaseResumenDTO(
                    id=p.fase.id if p.fase else None,
                    nombre=p.fase.nombre_fase if p.fase else "Fase",
                    orden=p.fase.orden if p.fase else None,
                ),
                actividad_proyecto=ActividadProyectoResumenDTO(
                    id=p.actividad.id if p.actividad else None,
                    descripcion=p.actividad.descripcion if p.actividad else "Actividad de Proyecto",
                    orden=p.actividad.orden if p.actividad else None,
                ),
                competencias=list(comp_map.values()),
                raps=all_raps,
                actividades_aprendizaje=actividades_text,
                horas=HorasPlaneacionDTO(
                    directas=h_direct,
                    independientes=h_indep,
                    total=h_total,
                ),
                ambiente=ambiente_text,
                instructores=instructores_text,
                observaciones_count=obs_total_map.get(p.id, 0),
                observaciones_pendientes_count=obs_pending_map.get(p.id, 0),
            )
            items.append(item_dto)

        # Deterministic sort
        items.sort(
            key=lambda x: (
                x.fase.orden if x.fase.orden is not None else 9999,
                x.fase.nombre,
                x.actividad_proyecto.orden if x.actividad_proyecto.orden is not None else 9999,
                x.actividad_proyecto.descripcion,
                str(x.id),
            )
        )

        return PlaneacionesEntregaListDTO(
            entrega_id=entrega.id,
            version=entrega.version,
            total=len(items),
            horas_directas_total=round(total_directas, 2),
            horas_independientes_total=round(total_independientes, 2),
            planeaciones=items,
        )

    async def obtener_planeacion_detalle_entrega(
        self,
        actor: Usuario,
        entrega_id: UUID,
        planeacion_id: UUID,
    ) -> PlaneacionRevisionDetalleDTO:
        """Fetch comprehensive read-only detail of one planning frozen in this delivery."""
        self._require_pedagogical_reviewer(actor)

        stmt = select(EntregaRevisionCurricular).where(EntregaRevisionCurricular.id == entrega_id)
        res = await self.session.execute(stmt)
        entrega = res.scalar_one_or_none()
        if not entrega:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrega no encontrada.")

        # Whitelist anti-IDOR check
        snapshot = entrega.snapshot_metadatos or {}
        raw_ids = snapshot.get("planeaciones_ids", [])
        allowed_ids = {str(item) for item in raw_ids}
        if str(planeacion_id) not in allowed_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La planeación pedagógica no pertenece a esta entrega de revisión.",
            )

        plan_stmt = (
            select(PlaneacionPedagogica)
            .where(
                PlaneacionPedagogica.id == planeacion_id,
                PlaneacionPedagogica.proyecto_id == entrega.proyecto_id,
            )
            .options(
                selectinload(PlaneacionPedagogica.fase),
                selectinload(PlaneacionPedagogica.actividad),
                selectinload(PlaneacionPedagogica.resultados).selectinload(ResultadoAprendizaje.competencia),
                selectinload(PlaneacionPedagogica.conocimientos),
                selectinload(PlaneacionPedagogica.criterios),
            )
        )
        plan_res = await self.session.execute(plan_stmt)
        p = plan_res.scalar_one_or_none()
        if not p:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Planeación pedagógica no encontrada.",
            )

        # Query all observations on this planning for this delivery
        obs_stmt = (
            select(ObservacionRevision)
            .where(
                ObservacionRevision.entrega_id == entrega.id,
                ObservacionRevision.target_type == TipoElementoObservacion.PLANEACION,
                ObservacionRevision.target_id == p.id,
            )
            .options(
                selectinload(ObservacionRevision.creado_por),
                selectinload(ObservacionRevision.ajuste_reportado_por),
                selectinload(ObservacionRevision.resuelto_por),
            )
            .order_by(ObservacionRevision.fecha_creacion.asc())
        )
        obs_res = await self.session.execute(obs_stmt)
        obs_entities = obs_res.scalars().all()
        obs_dtos = [
            ObservacionDTO(
                id=o.id,
                entrega_id=o.entrega_id,
                target_type=o.target_type,
                target_id=o.target_id,
                section_key=o.section_key,
                comentario=o.comentario,
                estado=o.estado,
                creado_por_id=o.creado_por_id,
                creado_por_nombre=f"{o.creado_por.nombre} {o.creado_por.apellido}" if o.creado_por else "Usuario",
                fecha_creacion=o.fecha_creacion,
                ajuste_reportado_por_id=o.ajuste_reportado_por_id,
                ajuste_reportado_por_nombre=f"{o.ajuste_reportado_por.nombre} {o.ajuste_reportado_por.apellido}" if o.ajuste_reportado_por else None,
                fecha_ajuste_reportado=o.fecha_ajuste_reportado,
                comentario_ajuste=o.comentario_ajuste,
                resuelto_por_id=o.resuelto_por_id,
                resuelto_por_nombre=f"{o.resuelto_por.nombre} {o.resuelto_por.apellido}" if o.resuelto_por else None,
                fecha_resolucion=o.fecha_resolucion,
            )
            for o in obs_entities
        ]

        data = p.datos_complementarios or {}
        h_direct = self._parse_float(data.get("horas_trabajo_directo"))
        h_indep = self._parse_float(data.get("horas_trabajo_independiente"))
        h_total = self._parse_float(data.get("duracion_actividad_horas") or data.get("duracion_horas")) or (h_direct + h_indep)

        comp_map: dict[UUID, CompetenciaResumenDTO] = {}
        ra_locks_meta = data.get("ra_locks") if isinstance(data.get("ra_locks"), dict) else {}
        for r in p.resultados:
            comp = getattr(r, "competencia", None)
            if comp is None:
                continue
            comp_id = comp.id
            comp_cod = comp.codigo_competencia if comp else "N/A"
            comp_nom = comp.nombre_competencia if comp else "Competencia"

            ra_meta = ra_locks_meta.get(str(r.id), {}) if isinstance(ra_locks_meta.get(str(r.id)), dict) else {}
            raw_edit_st = ra_meta.get("edit_status") or getattr(r, "edit_status", EstadoEdicionRA.EDITABLE)
            edit_st_str = raw_edit_st.value if hasattr(raw_edit_st, "value") else str(raw_edit_st)

            rap_dto = RAPResumenDTO(
                id=r.id,
                codigo=r.codigo_resultado,
                descripcion=r.descripcion,
                tipo_resultado=None,
                edit_status=edit_st_str,
                locked_at=getattr(r, "locked_at", None),
                locked_by=getattr(r, "locked_by", None),
                unlocked_at=getattr(r, "unlocked_at", None),
                unlocked_by=getattr(r, "unlocked_by", None),
                unlock_request_id=getattr(r, "unlock_request_id", None),
                approved_version=getattr(r, "approved_version", 0) or 0,
                approved_at=getattr(r, "approved_at", None),
            )
            if comp_id not in comp_map:
                comp_map[comp_id] = CompetenciaResumenDTO(
                    id=comp_id,
                    codigo=comp_cod,
                    nombre=comp_nom,
                    resultados_count=0,
                    resultados=[],
                )
            comp_map[comp_id].resultados.append(rap_dto)
            comp_map[comp_id].resultados_count += 1

        conocimientos_saber: list[ConocimientoResumenDTO] = []
        conocimientos_proceso: list[ConocimientoResumenDTO] = []
        for k in p.conocimientos:
            tipo_str = str(getattr(k.tipo, "value", k.tipo) if hasattr(k, "tipo") else "SABER").upper()
            dto_k = ConocimientoResumenDTO(id=k.id, tipo=tipo_str, descripcion=k.descripcion)
            if "SABER" in tipo_str:
                conocimientos_saber.append(dto_k)
            else:
                conocimientos_proceso.append(dto_k)

        criterios_eval: list[CriterioResumenDTO] = [
            CriterioResumenDTO(
                id=cr.id,
                codigo=getattr(cr, "codigo", None),
                descripcion=cr.descripcion,
            )
            for cr in p.criterios
        ]

        actividades_text = str(data.get("actividades_aprendizaje") or "").strip()
        if not actividades_text and p.actividad:
            actividades_text = p.actividad.descripcion

        ambientes_text = str(
            data.get("ambiente")
            or data.get("ambientes_aprendizaje")
            or (", ".join(data.get("ambientes_tipificados", [])) if isinstance(data.get("ambientes_tipificados"), list) else data.get("ambientes_tipificados"))
            or ""
        ).strip()

        materiales_text = str(
            data.get("materiales_formacion")
            or data.get("recursos_didacticos")
            or ""
        ).strip()

        instructores_text = str(
            data.get("instructores")
            or data.get("instructor_responsable")
            or ""
        ).strip()

        estrategias_text = str(data.get("estrategias_didacticas") or "").strip()
        evidencia_text = str(data.get("descripcion_evidencia_aprendizaje") or "").strip()
        observaciones_didacticas = str(data.get("observaciones") or "").strip() or None

        rev_st = getattr(p, "review_status", EstadoRevisionPlaneacion.DRAFT)
        app_st = getattr(p, "approval_status", EstadoAprobacionPlaneacion.PENDING)
        ed_st = getattr(p, "edit_status", EstadoEdicionRA.EDITABLE)

        return PlaneacionRevisionDetalleDTO(
            id=p.id,
            entrega_id=entrega.id,
            version_entrega=entrega.version,
            estado=p.estado.value if hasattr(p.estado, "value") else str(p.estado),
            review_status=rev_st.value if hasattr(rev_st, "value") else str(rev_st),
            approval_status=app_st.value if hasattr(app_st, "value") else str(app_st),
            edit_status=ed_st.value if hasattr(ed_st, "value") else str(ed_st),
            official_version=getattr(p, "official_version", 0) or 0,
            fase=FaseResumenDTO(
                id=p.fase.id if p.fase else None,
                nombre=p.fase.nombre_fase if p.fase else "Fase",
                orden=p.fase.orden if p.fase else None,
            ),
            actividad_proyecto=ActividadProyectoResumenDTO(
                id=p.actividad.id if p.actividad else None,
                descripcion=p.actividad.descripcion if p.actividad else "Actividad de Proyecto",
                orden=p.actividad.orden if p.actividad else None,
            ),
            competencias=list(comp_map.values()),
            conocimientos_saber=conocimientos_saber,
            conocimientos_proceso=conocimientos_proceso,
            criterios_evaluacion=criterios_eval,
            actividades_aprendizaje=actividades_text,
            descripcion_evidencia=evidencia_text,
            estrategias_didacticas=estrategias_text,
            ambientes=ambientes_text,
            materiales=materiales_text,
            instructores=instructores_text,
            horas=HorasPlaneacionDTO(
                directas=h_direct,
                independientes=h_indep,
                total=h_total,
            ),
            observaciones_didacticas=observaciones_didacticas,
            observaciones=obs_dtos,
        )

    # -------------------------------------------------------------------------
    # Observations & Feedback
    # -------------------------------------------------------------------------

    async def crear_observacion(
        self,
        actor: Usuario,
        entrega_id: UUID,
        dto: ObservacionCreateDTO,
    ) -> ObservacionDTO:
        """Create a targeted pedagogical observation on a specific element or section."""
        self._require_pedagogical_reviewer(actor)

        stmt = select(EntregaRevisionCurricular).where(EntregaRevisionCurricular.id == entrega_id).with_for_update()
        res = await self.session.execute(stmt)
        entrega = res.scalar_one_or_none()
        if not entrega:
            raise HTTPException(status_code=404, detail="Entrega no encontrada.")

        if entrega.estado == EstadoEntregaRevision.APROBADO:
            raise HTTPException(status_code=400, detail="No se pueden agregar observaciones a una entrega ya aprobada.")

        # Validate planning targets against delivery whitelist and known section catalog
        if dto.target_type == TipoElementoObservacion.PLANEACION:
            if dto.target_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="La observación de planeación requiere target_id.",
                )

            allowed_ids = {
                str(item)
                for item in (entrega.snapshot_metadatos or {}).get("planeaciones_ids", [])
            }
            if str(dto.target_id) not in allowed_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="La planeación indicada no pertenece a esta entrega de revisión.",
                )

            normalized = self._normalize_section_key(dto.section_key or "GENERAL")
            if not normalized:
                valid_sections = {s.value for s in SeccionObservacionPlaneacion}
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Sección de planeación inválida '{dto.section_key}'. Secciones válidas: {', '.join(sorted(valid_sections))}",
                )
            dto.section_key = normalized

            planning_exists_stmt = select(PlaneacionPedagogica.id).where(
                PlaneacionPedagogica.id == dto.target_id,
                PlaneacionPedagogica.proyecto_id == entrega.proyecto_id,
            )
            if (await self.session.execute(planning_exists_stmt)).scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="La planeación indicada no pertenece al proyecto de esta entrega.",
                )

        # Ensure delivery is in review
        if entrega.estado in (EstadoEntregaRevision.ENVIADO_REVISION, EstadoEntregaRevision.REENVIADO):
            entrega.estado = EstadoEntregaRevision.EN_REVISION
            entrega.revisado_por_id = actor.id
            entrega.fecha_inicio_revision = datetime.now(UTC)

        obs = ObservacionRevision(
            id=uuid.uuid4(),
            entrega_id=entrega.id,
            target_type=dto.target_type,
            target_id=dto.target_id,
            section_key=dto.section_key,
            comentario=dto.comentario.strip(),
            estado=EstadoObservacionRevision.PENDIENTE,
            creado_por_id=actor.id,
            fecha_creacion=datetime.now(UTC),
        )
        self.session.add(obs)

        await self._audit(
            actor_id=actor.id,
            referencia_id=entrega.referencia_id,
            entidad="ObservacionRevision",
            entidad_id=obs.id,
            accion="OBSERVACION_REVISION_CREADA",
            detalle={
                "target_type": dto.target_type.value,
                "target_id": str(dto.target_id) if dto.target_id else None,
                "section_key": dto.section_key,
                "comentario": dto.comentario,
            },
        )

        await self.session.commit()
        return await self._get_observacion_dto(obs.id)

    async def reportar_ajuste(
        self,
        actor: Usuario,
        observacion_id: UUID,
        dto: AjusteReportarDTO,
    ) -> ObservacionDTO:
        """Report that an observation was addressed by the executor team."""
        stmt = (
            select(ObservacionRevision)
            .where(ObservacionRevision.id == observacion_id)
            .options(selectinload(ObservacionRevision.entrega))
            .with_for_update()
        )
        res = await self.session.execute(stmt)
        obs = res.scalar_one_or_none()
        if not obs:
            raise HTTPException(status_code=404, detail="Observación no encontrada.")

        # Check access: must belong to the executor team
        await self.scope_service.require_process_access(actor, obs.entrega.referencia_id)

        obs.estado = EstadoObservacionRevision.AJUSTE_REPORTADO
        obs.ajuste_reportado_por_id = actor.id
        obs.fecha_ajuste_reportado = datetime.now(UTC)
        obs.comentario_ajuste = dto.comentario_ajuste.strip()

        # Update delivery state to AJUSTES_EN_PROGRESO if it was AJUSTES_SOLICITADOS
        if obs.entrega.estado == EstadoEntregaRevision.AJUSTES_SOLICITADOS:
            obs.entrega.estado = EstadoEntregaRevision.AJUSTES_EN_PROGRESO

        await self._audit(
            actor_id=actor.id,
            referencia_id=obs.entrega.referencia_id,
            entidad="ObservacionRevision",
            entidad_id=obs.id,
            accion="AJUSTE_OBSERVACION_REPORTADO",
            detalle={"comentario_ajuste": dto.comentario_ajuste},
        )

        await self.session.commit()
        return await self._get_observacion_dto(obs.id)

    async def resolver_observacion(
        self,
        actor: Usuario,
        observacion_id: UUID,
    ) -> ObservacionDTO:
        """Confirm and close an observation (pedagogical reviewer only)."""
        self._require_pedagogical_reviewer(actor)

        stmt = (
            select(ObservacionRevision)
            .where(ObservacionRevision.id == observacion_id)
            .options(selectinload(ObservacionRevision.entrega))
            .with_for_update()
        )
        res = await self.session.execute(stmt)
        obs = res.scalar_one_or_none()
        if not obs:
            raise HTTPException(status_code=404, detail="Observación no encontrada.")

        obs.estado = EstadoObservacionRevision.RESUELTO
        obs.resuelto_por_id = actor.id
        obs.fecha_resolucion = datetime.now(UTC)

        await self._audit(
            actor_id=actor.id,
            referencia_id=obs.entrega.referencia_id,
            entidad="ObservacionRevision",
            entidad_id=obs.id,
            accion="OBSERVACION_REVISION_RESUELTA",
            detalle={"observacion_id": str(obs.id)},
        )

        await self.session.commit()
        return await self._get_observacion_dto(obs.id)

    # -------------------------------------------------------------------------
    # Formal Decisions: Request Changes & Approve
    # -------------------------------------------------------------------------

    async def solicitar_ajustes(
        self,
        actor: Usuario,
        entrega_id: UUID,
    ) -> EntregaRevisionDetalleDTO:
        """Formally request changes and notify the executing team."""
        self._require_pedagogical_reviewer(actor)

        stmt = (
            select(EntregaRevisionCurricular)
            .where(EntregaRevisionCurricular.id == entrega_id)
            .options(selectinload(EntregaRevisionCurricular.observaciones))
            .with_for_update()
        )
        res = await self.session.execute(stmt)
        entrega = res.scalar_one_or_none()
        if not entrega:
            raise HTTPException(status_code=404, detail="Entrega no encontrada.")

        pendientes = [o for o in entrega.observaciones if o.estado != EstadoObservacionRevision.RESUELTO]
        if not pendientes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debes crear al menos una observación antes de solicitar ajustes.",
            )

        now = datetime.now(UTC)
        entrega.estado = EstadoEntregaRevision.AJUSTES_SOLICITADOS
        entrega.ajustes_solicitados_por_id = actor.id
        entrega.fecha_ajustes_solicitados = now
        entrega.descarga_habilitada = False

        plan_stmt = (
            select(PlaneacionPedagogica)
            .where(PlaneacionPedagogica.proyecto_id == entrega.proyecto_id)
            .options(selectinload(PlaneacionPedagogica.resultados))
        )
        plan_res = await self.session.execute(plan_stmt)
        for p in plan_res.scalars().all():
            p.review_status = EstadoRevisionPlaneacion.OBSERVED
            if p.approval_status == EstadoAprobacionPlaneacion.PENDING:
                p.edit_status = EstadoEdicionRA.EDITABLE
                for r in p.resultados:
                    if (getattr(r, "approved_version", 0) or 0) == 0:
                        r.edit_status = EstadoEdicionRA.EDITABLE

        await self._audit(
            actor_id=actor.id,
            referencia_id=entrega.referencia_id,
            entidad="EntregaRevisionCurricular",
            entidad_id=entrega.id,
            accion="AJUSTES_CURRICULARES_SOLICITADOS",
            detalle={
                "version": entrega.version,
                "observaciones_pendientes_count": len(pendientes),
            },
        )

        await self.session.commit()
        return await self.obtener_detalle_entrega(actor, entrega.id)

    async def aprobar_entrega(
        self,
        actor: Usuario,
        entrega_id: UUID,
        dto: AprobacionRequestDTO,
    ) -> EntregaRevisionDetalleDTO:
        """Formally approve the delivery, authorize download, and transactionally lock all associated Learning Results."""
        self._require_pedagogical_reviewer(actor)

        stmt = (
            select(EntregaRevisionCurricular)
            .where(EntregaRevisionCurricular.id == entrega_id)
            .options(selectinload(EntregaRevisionCurricular.observaciones))
            .with_for_update()
        )
        res = await self.session.execute(stmt)
        entrega = res.scalar_one_or_none()
        if not entrega:
            raise HTTPException(status_code=404, detail="Entrega no encontrada.")

        # Invariant 1: Must be latest version of the process
        latest = await self._get_latest_delivery_by_ref(entrega.referencia_id)
        if latest and latest.id != entrega.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"No se puede aprobar la versión {entrega.version} porque existe una versión más reciente ({latest.version}).",
            )

        # Invariant 2: Cannot approve with unresolved observations
        unresolved = [o for o in entrega.observaciones if o.estado != EstadoObservacionRevision.RESUELTO]
        if unresolved:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "UNRESOLVED_OBSERVATIONS_REMAIN",
                    "message": f"No se puede aprobar. Quedan {len(unresolved)} observación(es) pendientes o sin confirmar.",
                },
            )

        now = datetime.now(UTC)
        entrega.estado = EstadoEntregaRevision.APROBADO
        entrega.aprobado_por_id = actor.id
        entrega.fecha_aprobacion = now
        entrega.descarga_habilitada = True
        entrega.descarga_habilitada_por_id = actor.id
        entrega.fecha_descarga_habilitada = now
        entrega.notas_aprobacion = dto.notas_aprobacion

        # Preserve official consolidated document metadata on PlaneacionDocumentoConfig
        config_stmt = (
            select(PlaneacionDocumentoConfig)
            .where(PlaneacionDocumentoConfig.proyecto_id == entrega.proyecto_id)
            .with_for_update()
        )
        config_res = await self.session.execute(config_stmt)
        doc_config = config_res.scalar_one_or_none()
        if doc_config:
            doc_config.official_storage_key = doc_config.storage_key
            doc_config.official_file_name = doc_config.file_name
            doc_config.official_checksum_sha256 = doc_config.checksum_sha256
            doc_config.official_version = entrega.version

        # Transactionally lock all plannings and Learning Results (RAs)
        plan_stmt = (
            select(PlaneacionPedagogica)
            .where(
                PlaneacionPedagogica.proyecto_id == entrega.proyecto_id,
                PlaneacionPedagogica.estado == EstadoBloque.COMPLETO,
            )
            .options(
                selectinload(PlaneacionPedagogica.resultados),
                selectinload(PlaneacionPedagogica.conocimientos),
                selectinload(PlaneacionPedagogica.criterios),
            )
            .with_for_update()
        )
        plan_res = await self.session.execute(plan_stmt)
        plans = list(plan_res.scalars().all())

        is_reapproval = entrega.version > 1
        locked_ra_ids: list[str] = []

        for p in plans:
            was_reopened = (
                p.approval_status == EstadoAprobacionPlaneacion.PREVIOUS_VERSION_APPROVED
                or (getattr(p, "official_version", 0) or 0) >= 1
                or is_reapproval
            )
            p.review_status = EstadoRevisionPlaneacion.APPROVED
            p.approval_status = EstadoAprobacionPlaneacion.APPROVED
            p.edit_status = EstadoEdicionRA.LOCKED
            p.locked_at = now
            p.locked_by = actor.id
            p.unlock_request_id = None
            p.official_storage_key = p.storage_key
            p.official_file_name = p.file_name
            p.official_checksum_sha256 = p.checksum_sha256
            p.official_version = entrega.version
            p.official_approved_at = now
            p.official_approved_by = actor.id

            # Mark older versions of RAs in this planning as non-official
            await self.session.execute(
                update(LearningResultVersion)
                .where(LearningResultVersion.planning_id == p.id)
                .values(is_official=False)
            )

            datos = deepcopy(p.datos_complementarios or {})
            ra_locks = datos.get("ra_locks") if isinstance(datos.get("ra_locks"), dict) else {}

            for r in p.resultados:
                r.edit_status = EstadoEdicionRA.LOCKED
                r.locked_at = now
                r.locked_by = actor.id
                r.unlock_request_id = None
                r.approved_version = entrega.version
                r.approved_at = now

                ra_key = str(r.id)
                locked_ra_ids.append(ra_key)
                ra_locks[ra_key] = {
                    "edit_status": EstadoEdicionRA.LOCKED.value,
                    "locked_at": now.isoformat(),
                    "locked_by": str(actor.id),
                    "unlocked_at": r.unlocked_at.isoformat() if r.unlocked_at else None,
                    "unlocked_by": str(r.unlocked_by) if r.unlocked_by else None,
                    "unlock_request_id": None,
                    "approved_version": entrega.version,
                    "approved_at": now.isoformat(),
                }

                await self.session.execute(
                    update(planeacion_resultados)
                    .where(
                        planeacion_resultados.c.planeacion_id == p.id,
                        planeacion_resultados.c.resultado_id == r.id,
                    )
                    .values(
                        edit_status=EstadoEdicionRA.LOCKED,
                        locked_at=now,
                        locked_by=actor.id,
                        unlock_request_id=None,
                        approved_version=entrega.version,
                        approved_at=now,
                    )
                )

                version_record = LearningResultVersion(
                    id=uuid.uuid4(),
                    planning_id=p.id,
                    learning_result_id=r.id,
                    version_number=entrega.version,
                    snapshot_data=self._extract_ra_snapshot(p, r),
                    approved_by=actor.id,
                    approved_at=now,
                    is_official=True,
                )
                self.session.add(version_record)

                await self._audit(
                    actor_id=actor.id,
                    referencia_id=entrega.referencia_id,
                    entidad="ResultadoAprendizaje",
                    entidad_id=r.id,
                    accion="LEARNING_RESULT_LOCKED",
                    detalle={
                        "planeacion_id": str(p.id),
                        "learning_result_id": ra_key,
                        "codigo_resultado": r.codigo_resultado,
                        "version": entrega.version,
                    },
                )
                if was_reopened:
                    await self._audit(
                        actor_id=actor.id,
                        referencia_id=entrega.referencia_id,
                        entidad="ResultadoAprendizaje",
                        entidad_id=r.id,
                        accion="LEARNING_RESULT_REAPPROVED",
                        detalle={
                            "planeacion_id": str(p.id),
                            "learning_result_id": ra_key,
                            "version": entrega.version,
                        },
                    )
                    await self._audit(
                        actor_id=actor.id,
                        referencia_id=entrega.referencia_id,
                        entidad="ResultadoAprendizaje",
                        entidad_id=r.id,
                        accion="LEARNING_RESULT_RELOCKED",
                        detalle={
                            "planeacion_id": str(p.id),
                            "learning_result_id": ra_key,
                            "version": entrega.version,
                        },
                    )

            datos["ra_locks"] = ra_locks
            p.datos_complementarios = datos

            await self._audit(
                actor_id=actor.id,
                referencia_id=entrega.referencia_id,
                entidad="PlaneacionPedagogica",
                entidad_id=p.id,
                accion="PLANNING_APPROVED",
                detalle={
                    "planeacion_id": str(p.id),
                    "version": entrega.version,
                    "review_status": EstadoRevisionPlaneacion.APPROVED.value,
                    "approval_status": EstadoAprobacionPlaneacion.APPROVED.value,
                    "edit_status": EstadoEdicionRA.LOCKED.value,
                },
            )

        # Complete any remaining open APPROVED/PARTIALLY_APPROVED edit requests
        if plans:
            plan_ids = [p.id for p in plans]
            req_stmt = (
                select(PlanningEditRequest)
                .where(
                    PlanningEditRequest.planning_id.in_(plan_ids),
                    PlanningEditRequest.status.in_([
                        EstadoSolicitudReapertura.APPROVED,
                        EstadoSolicitudReapertura.PARTIALLY_APPROVED,
                    ]),
                )
                .with_for_update()
            )
            req_res = await self.session.execute(req_stmt)
            for req in req_res.scalars().all():
                req.status = EstadoSolicitudReapertura.COMPLETED
                req.version = (req.version or 1) + 1
                req.updated_at = now

        # Refresh snapshot with finalized checksums
        entrega.snapshot_metadatos = await self._build_snapshot_metadatos(entrega.proyecto_id)

        await self._audit(
            actor_id=actor.id,
            referencia_id=entrega.referencia_id,
            entidad="EntregaRevisionCurricular",
            entidad_id=entrega.id,
            accion="ENTREGA_CURRICULAR_APROBADA",
            detalle={
                "version": entrega.version,
                "notas_aprobacion": dto.notas_aprobacion,
                "checksum_aprobado": entrega.snapshot_metadatos.get("checksum_consolidado"),
                "locked_ra_ids": locked_ra_ids,
            },
        )
        await self._audit(
            actor_id=actor.id,
            referencia_id=entrega.referencia_id,
            entidad="EntregaRevisionCurricular",
            entidad_id=entrega.id,
            accion="DESCARGA_CONSOLIDADO_HABILITADA",
            detalle={"version": entrega.version},
        )

        if is_reapproval:
            notification_dispatcher.emit(
                event_type="planning.reapproved",
                actor_id=actor.id,
                referencia_id=entrega.referencia_id,
                team_id=entrega.equipo_ejecutor_id,
                payload={
                    "entrega_id": str(entrega.id),
                    "version": entrega.version,
                    "locked_ra_ids": locked_ra_ids,
                },
            )

        await self.session.commit()
        return await self.obtener_detalle_entrega(actor, entrega.id)

    # -------------------------------------------------------------------------
    # Download Gatekeeping & Anti-Tampering Protection
    # -------------------------------------------------------------------------

    async def verify_download_authorization(self, proyecto_id: UUID) -> tuple[bool, str | None]:
        """Verify server-side that the project planning has active pedagogical approval."""
        stmt = (
            select(EntregaRevisionCurricular)
            .where(
                EntregaRevisionCurricular.proyecto_id == proyecto_id,
                EntregaRevisionCurricular.estado == EstadoEntregaRevision.APROBADO,
                EntregaRevisionCurricular.descarga_habilitada.is_(True),
            )
            .order_by(EntregaRevisionCurricular.version.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        approved = res.scalar_one_or_none()
        if not approved:
            return False, "La planeación todavía no ha sido aprobada por el Equipo Pedagógico."

        # Anti-tampering check: verify that current planning count and checksum match the approved snapshot
        current_snapshot = await self._build_snapshot_metadatos(proyecto_id)
        if current_snapshot.get("has_authorized_reopening"):
            return True, None

        approved_snapshot = approved.snapshot_metadatos or {}

        if (
            current_snapshot.get("planeaciones_count") != approved_snapshot.get("planeaciones_count")
            or current_snapshot.get("checksum_consolidado") != approved_snapshot.get("checksum_consolidado")
        ):
            # Invalidate approval because contents changed after approval without authorized reopening
            approved.descarga_habilitada = False
            approved.estado = EstadoEntregaRevision.BORRADOR
            await self._audit(
                actor_id=None,
                referencia_id=approved.referencia_id,
                entidad="EntregaRevisionCurricular",
                entidad_id=approved.id,
                accion="APROBACION_INVALIDADA_POR_MODIFICACION",
                detalle={
                    "motivo": "Contenido o archivo consolidado modificado con posterioridad a la aprobación pedagógica."
                },
            )
            await self.session.commit()
            return False, "Se detectaron modificaciones curriculares posteriores a la aprobación. La descarga fue bloqueada y se requiere una nueva revisión pedagógica."

        return True, None

    async def invalidate_approval_on_mutation(self, proyecto_id: UUID, actor_id: UUID | None) -> None:
        """Invalidate active approval if an approved project's plannings are modified."""
        stmt = (
            select(EntregaRevisionCurricular)
            .where(
                EntregaRevisionCurricular.proyecto_id == proyecto_id,
                EntregaRevisionCurricular.estado == EstadoEntregaRevision.APROBADO,
            )
            .with_for_update()
        )
        res = await self.session.execute(stmt)
        approved = res.scalars().all()
        for app in approved:
            app.descarga_habilitada = False
            app.estado = EstadoEntregaRevision.BORRADOR
            await self._audit(
                actor_id=actor_id,
                referencia_id=app.referencia_id,
                entidad="EntregaRevisionCurricular",
                entidad_id=app.id,
                accion="APROBACION_INVALIDADA_POR_MODIFICACION",
                detalle={"version": app.version},
            )

    # -------------------------------------------------------------------------
    # Controlled Reopening & Edit Requests (PlanningEditRequest)
    # -------------------------------------------------------------------------

    async def crear_solicitud_reapertura(
        self,
        actor: Usuario,
        dto: PlanningEditRequestCreateDTO,
    ) -> PlanningEditRequestDTO:
        """Create a formal request from the Executor Team Leader to unlock specific approved Learning Results."""
        plan_stmt = (
            select(PlaneacionPedagogica)
            .where(PlaneacionPedagogica.id == dto.planning_id)
            .options(
                selectinload(PlaneacionPedagogica.resultados),
                selectinload(PlaneacionPedagogica.fase),
                selectinload(PlaneacionPedagogica.actividad),
            )
            .with_for_update()
        )
        plan_res = await self.session.execute(plan_stmt)
        planeacion = plan_res.scalar_one_or_none()
        if not planeacion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planeación pedagógica no encontrada.")

        # Resolve ProcesoCurricular and EquipoEjecutor
        proc_stmt = (
            select(ProcesoCurricular)
            .where(ProcesoCurricular.proyecto_id == planeacion.proyecto_id)
            .options(
                selectinload(ProcesoCurricular.equipo_ejecutor).selectinload(EquipoEjecutor.lider),
                selectinload(ProcesoCurricular.programa),
                selectinload(ProcesoCurricular.proyecto),
            )
        )
        proc_res = await self.session.execute(proc_stmt)
        proceso = proc_res.scalar_one_or_none()
        if not proceso or not proceso.equipo_ejecutor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La planeación no está vinculada a un proceso curricular con Equipo Ejecutor activo.",
            )

        # Only the Team Leader of the owning Executor Team can create an edit request
        is_team_leader = (
            actor.has_role(RolUsuario.LIDER_EQUIPO_EJECUTOR.value)
            and (
                getattr(proceso, "lider_id", None) == actor.id
                or getattr(proceso, "usuario_lider_id", None) == actor.id
                or proceso.equipo_ejecutor.lider_id == actor.id
            )
        )
        if not is_team_leader:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el Líder del Equipo Ejecutor titular puede solicitar la reapertura de Resultados de Aprendizaje aprobados.",
            )

        # Verify planning is approved and download is enabled
        latest_approved_stmt = (
            select(EntregaRevisionCurricular)
            .where(
                EntregaRevisionCurricular.proyecto_id == planeacion.proyecto_id,
                EntregaRevisionCurricular.estado == EstadoEntregaRevision.APROBADO,
                EntregaRevisionCurricular.descarga_habilitada.is_(True),
            )
            .order_by(EntregaRevisionCurricular.version.desc())
        )
        approved_delivery = (await self.session.execute(latest_approved_stmt)).scalars().first()
        is_planning_approved = (
            planeacion.approval_status in (
                EstadoAprobacionPlaneacion.APPROVED,
                EstadoAprobacionPlaneacion.PREVIOUS_VERSION_APPROVED,
            )
            or approved_delivery is not None
        )
        if not is_planning_approved:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Solo se puede solicitar modificación sobre una planeación aprobada con descarga habilitada.",
            )

        # Validate requested learning results belong to this planning and are currently LOCKED
        plan_ra_map = {r.id: r for r in planeacion.resultados}
        requested_ids: list[UUID] = []
        seen: set[UUID] = set()
        for ra_id in dto.learning_result_ids:
            if ra_id in seen:
                continue
            seen.add(ra_id)
            if ra_id not in plan_ra_map:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El Resultado de Aprendizaje {ra_id} no pertenece a esta planeación pedagógica.",
                )
            ra_obj = plan_ra_map[ra_id]
            if getattr(ra_obj, "edit_status", EstadoEdicionRA.EDITABLE) != EstadoEdicionRA.LOCKED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"El Resultado de Aprendizaje '{ra_obj.codigo_resultado or ra_obj.id}' ya se encuentra habilitado para edición.",
                )
            requested_ids.append(ra_id)

        if not requested_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debe seleccionar al menos un Resultado de Aprendizaje para solicitar modificación.",
            )

        # Prevent duplicate PENDING requests for any of the requested RAs
        dup_stmt = (
            select(PlanningEditRequest)
            .join(PlanningEditRequestItem, PlanningEditRequestItem.request_id == PlanningEditRequest.id)
            .where(
                PlanningEditRequest.planning_id == planeacion.id,
                PlanningEditRequest.status == EstadoSolicitudReapertura.PENDING,
                PlanningEditRequestItem.learning_result_id.in_(requested_ids),
            )
        )
        dup_existing = (await self.session.execute(dup_stmt)).scalars().first()
        if dup_existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "DUPLICATE_PENDING_EDIT_REQUEST",
                    "message": "Ya existe una solicitud de modificación pendiente de revisión para uno o más de los Resultados de Aprendizaje seleccionados.",
                },
            )

        now = datetime.now(UTC)
        edit_req = PlanningEditRequest(
            id=uuid.uuid4(),
            planning_id=planeacion.id,
            team_id=proceso.equipo_ejecutor.id,
            referencia_id=proceso.referencia_id,
            requested_by=actor.id,
            reason=dto.reason.strip(),
            requested_changes=dto.requested_changes.strip(),
            status=EstadoSolicitudReapertura.PENDING,
            version=1,
            created_at=now,
            updated_at=now,
        )
        self.session.add(edit_req)

        for ra_id in requested_ids:
            item = PlanningEditRequestItem(
                id=uuid.uuid4(),
                request_id=edit_req.id,
                learning_result_id=ra_id,
                requested=True,
                approved=False,
            )
            self.session.add(item)

        await self._audit(
            actor_id=actor.id,
            referencia_id=proceso.referencia_id,
            entidad="PlanningEditRequest",
            entidad_id=edit_req.id,
            accion="EDIT_REQUEST_CREATED",
            detalle={
                "request_id": str(edit_req.id),
                "planning_id": str(planeacion.id),
                "learning_result_ids": [str(rid) for rid in requested_ids],
                "reason": edit_req.reason,
                "requested_changes": edit_req.requested_changes,
            },
        )

        notification_dispatcher.emit(
            event_type="edit_request.created",
            actor_id=actor.id,
            referencia_id=proceso.referencia_id,
            planning_id=planeacion.id,
            request_id=edit_req.id,
            team_id=proceso.equipo_ejecutor.id,
            payload={
                "learning_result_ids": [str(rid) for rid in requested_ids],
                "reason": edit_req.reason,
            },
        )

        await self.session.commit()
        return await self.obtener_solicitud_reapertura(actor, edit_req.id)

    async def listar_solicitudes_reapertura(
        self,
        actor: Usuario,
        planning_id: UUID | None = None,
        referencia_id: UUID | None = None,
        status_filter: EstadoSolicitudReapertura | None = None,
    ) -> list[PlanningEditRequestDTO]:
        """List edit requests visible to the actor (Pedagogical Admin or Executor Team member)."""
        is_reviewer = actor.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value)
        if not is_reviewer:
            if planning_id:
                if not await self.scope_service.can_access_planning(actor, planning_id):
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a la planeación.")
            elif referencia_id:
                await self.scope_service.require_process_access(actor, referencia_id)
            else:
                team_ids = await self.scope_service.get_user_team_ids(actor.id)
                if not team_ids:
                    return []

        stmt = (
            select(PlanningEditRequest)
            .options(
                selectinload(PlanningEditRequest.items).selectinload(PlanningEditRequestItem.learning_result),
                selectinload(PlanningEditRequest.planning).selectinload(PlaneacionPedagogica.fase),
                selectinload(PlanningEditRequest.planning).selectinload(PlaneacionPedagogica.actividad),
                selectinload(PlanningEditRequest.team),
                selectinload(PlanningEditRequest.requester),
                selectinload(PlanningEditRequest.reviewer),
            )
            .order_by(PlanningEditRequest.fecha_creacion.desc())
        )

        if planning_id:
            stmt = stmt.where(PlanningEditRequest.planning_id == planning_id)
        if referencia_id:
            stmt = stmt.where(PlanningEditRequest.referencia_id == referencia_id)
        if status_filter:
            stmt = stmt.where(PlanningEditRequest.status == status_filter)
        if not is_reviewer and not planning_id and not referencia_id:
            team_ids = await self.scope_service.get_user_team_ids(actor.id)
            stmt = stmt.where(PlanningEditRequest.team_id.in_(team_ids))

        res = await self.session.execute(stmt)
        requests = list(res.scalars().all())
        return [await self._to_edit_request_dto(r) for r in requests]

    async def obtener_solicitud_reapertura(
        self,
        actor: Usuario,
        request_id: UUID,
    ) -> PlanningEditRequestDTO:
        """Fetch one edit request with its learning result items and context."""
        stmt = (
            select(PlanningEditRequest)
            .where(PlanningEditRequest.id == request_id)
            .options(
                selectinload(PlanningEditRequest.items).selectinload(PlanningEditRequestItem.learning_result),
                selectinload(PlanningEditRequest.planning).selectinload(PlaneacionPedagogica.fase),
                selectinload(PlanningEditRequest.planning).selectinload(PlaneacionPedagogica.actividad),
                selectinload(PlanningEditRequest.team),
                selectinload(PlanningEditRequest.requester),
                selectinload(PlanningEditRequest.reviewer),
            )
        )
        res = await self.session.execute(stmt)
        req = res.scalar_one_or_none()
        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud de modificación no encontrada.")

        if not actor.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value):
            if not await self.scope_service.can_access_planning(actor, req.planning_id):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a la solicitud.")

        return await self._to_edit_request_dto(req)

    async def aprobar_solicitud_reapertura(
        self,
        actor: Usuario,
        request_id: UUID,
        dto: PlanningEditRequestApproveDTO,
    ) -> PlanningEditRequestDTO:
        """Approve all or a subset of requested Learning Results, unlocking only the authorized ones."""
        self._require_pedagogical_reviewer(actor)

        stmt = (
            select(PlanningEditRequest)
            .where(PlanningEditRequest.id == request_id)
            .options(selectinload(PlanningEditRequest.items))
            .with_for_update()
        )
        res = await self.session.execute(stmt)
        req = res.scalar_one_or_none()
        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud de modificación no encontrada.")

        if req.status != EstadoSolicitudReapertura.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "EDIT_REQUEST_ALREADY_PROCESSED",
                    "message": f"La solicitud ya fue procesada (estado actual: {req.status.value}).",
                },
            )

        requested_map = {item.learning_result_id: item for item in req.items if item.requested}
        approved_set = set(dto.approved_learning_result_ids)
        if not approved_set:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debe seleccionar al menos un Resultado de Aprendizaje para autorizar.",
            )
        invalid_ids = approved_set - set(requested_map.keys())
        if invalid_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uno o más Resultados de Aprendizaje seleccionados no forman parte de la solicitud original.",
            )

        is_partial = len(approved_set) < len(requested_map)
        new_status = (
            EstadoSolicitudReapertura.PARTIALLY_APPROVED
            if is_partial
            else EstadoSolicitudReapertura.APPROVED
        )

        now = datetime.now(UTC)
        for item in req.items:
            item.approved = item.learning_result_id in approved_set

        req.status = new_status
        req.reviewed_by = actor.id
        req.admin_response = dto.admin_response.strip() if dto.admin_response else None
        req.reviewed_at = now
        req.version = (req.version or 1) + 1
        req.updated_at = now

        # Load planning and its RAs with row lock
        plan_stmt = (
            select(PlaneacionPedagogica)
            .where(PlaneacionPedagogica.id == req.planning_id)
            .options(
                selectinload(PlaneacionPedagogica.resultados),
                selectinload(PlaneacionPedagogica.conocimientos),
                selectinload(PlaneacionPedagogica.criterios),
            )
            .with_for_update()
        )
        plan_res = await self.session.execute(plan_stmt)
        planeacion = plan_res.scalar_one_or_none()
        if not planeacion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planeación pedagógica no encontrada.")

        # Preserve official storage key on planning and document config before allowing changes
        if not planeacion.official_storage_key and planeacion.storage_key:
            planeacion.official_storage_key = planeacion.storage_key
            planeacion.official_file_name = planeacion.file_name
            planeacion.official_checksum_sha256 = planeacion.checksum_sha256
            if not planeacion.official_version:
                planeacion.official_version = 1

        config_stmt = (
            select(PlaneacionDocumentoConfig)
            .where(PlaneacionDocumentoConfig.proyecto_id == planeacion.proyecto_id)
            .with_for_update()
        )
        doc_config = (await self.session.execute(config_stmt)).scalar_one_or_none()
        if doc_config and not doc_config.official_storage_key and doc_config.storage_key:
            doc_config.official_storage_key = doc_config.storage_key
            doc_config.official_file_name = doc_config.file_name
            doc_config.official_checksum_sha256 = doc_config.checksum_sha256
            if not doc_config.official_version:
                doc_config.official_version = doc_config.version or 1

        planeacion.review_status = EstadoRevisionPlaneacion.CHANGES_ALLOWED
        planeacion.approval_status = EstadoAprobacionPlaneacion.PREVIOUS_VERSION_APPROVED
        planeacion.edit_status = EstadoEdicionRA.EDITABLE
        planeacion.unlocked_at = now
        planeacion.unlocked_by = actor.id
        planeacion.unlock_request_id = req.id

        datos = deepcopy(planeacion.datos_complementarios or {})
        ra_locks = datos.get("ra_locks") if isinstance(datos.get("ra_locks"), dict) else {}

        for r in planeacion.resultados:
            ra_key = str(r.id)
            if r.id in approved_set:
                # Ensure a snapshot of the approved RA state exists in LearningResultVersion before unlocking
                ver_exists_stmt = select(LearningResultVersion.id).where(
                    LearningResultVersion.planning_id == planeacion.id,
                    LearningResultVersion.learning_result_id == r.id,
                )
                if (await self.session.execute(ver_exists_stmt)).scalars().first() is None:
                    self.session.add(
                        LearningResultVersion(
                            id=uuid.uuid4(),
                            planning_id=planeacion.id,
                            learning_result_id=r.id,
                            version_number=max(getattr(r, "approved_version", 1) or 1, 1),
                            snapshot_data=self._extract_ra_snapshot(planeacion, r),
                            approved_by=getattr(r, "locked_by", None) or actor.id,
                            approved_at=getattr(r, "approved_at", None) or now,
                            is_official=True,
                        )
                    )

                r.edit_status = EstadoEdicionRA.EDITABLE
                r.unlocked_at = now
                r.unlocked_by = actor.id
                r.unlock_request_id = req.id

                prev_meta = ra_locks.get(ra_key, {}) if isinstance(ra_locks.get(ra_key), dict) else {}
                ra_locks[ra_key] = {
                    **prev_meta,
                    "edit_status": EstadoEdicionRA.EDITABLE.value,
                    "unlocked_at": now.isoformat(),
                    "unlocked_by": str(actor.id),
                    "unlock_request_id": str(req.id),
                }
                await self.session.execute(
                    update(planeacion_resultados)
                    .where(
                        planeacion_resultados.c.planeacion_id == planeacion.id,
                        planeacion_resultados.c.resultado_id == r.id,
                    )
                    .values(
                        edit_status=EstadoEdicionRA.EDITABLE,
                        unlocked_at=now,
                        unlocked_by=actor.id,
                        unlock_request_id=req.id,
                    )
                )
                await self._audit(
                    actor_id=actor.id,
                    referencia_id=req.referencia_id,
                    entidad="ResultadoAprendizaje",
                    entidad_id=r.id,
                    accion="LEARNING_RESULT_UNLOCKED",
                    detalle={
                        "request_id": str(req.id),
                        "planning_id": str(planeacion.id),
                        "learning_result_id": ra_key,
                        "codigo_resultado": r.codigo_resultado,
                    },
                )
            else:
                # Ensure non-authorized RAs remain strictly LOCKED
                if getattr(r, "edit_status", EstadoEdicionRA.LOCKED) != EstadoEdicionRA.EDITABLE:
                    r.edit_status = EstadoEdicionRA.LOCKED
                    prev_meta = ra_locks.get(ra_key, {}) if isinstance(ra_locks.get(ra_key), dict) else {}
                    ra_locks[ra_key] = {
                        **prev_meta,
                        "edit_status": EstadoEdicionRA.LOCKED.value,
                    }

        datos["ra_locks"] = ra_locks
        planeacion.datos_complementarios = datos

        audit_action = (
            "EDIT_REQUEST_PARTIALLY_APPROVED"
            if is_partial
            else "EDIT_REQUEST_APPROVED"
        )
        await self._audit(
            actor_id=actor.id,
            referencia_id=req.referencia_id,
            entidad="PlanningEditRequest",
            entidad_id=req.id,
            accion=audit_action,
            detalle={
                "request_id": str(req.id),
                "planning_id": str(planeacion.id),
                "status": new_status.value,
                "approved_learning_result_ids": [str(rid) for rid in approved_set],
                "admin_response": req.admin_response,
            },
        )

        event_type = (
            "edit_request.partially_approved"
            if is_partial
            else "edit_request.approved"
        )
        notification_dispatcher.emit(
            event_type=event_type,
            actor_id=actor.id,
            recipient_ids=[req.requested_by],
            referencia_id=req.referencia_id,
            planning_id=planeacion.id,
            request_id=req.id,
            team_id=req.team_id,
            payload={
                "status": new_status.value,
                "approved_learning_result_ids": [str(rid) for rid in approved_set],
                "admin_response": req.admin_response,
            },
        )

        await self.session.commit()
        return await self.obtener_solicitud_reapertura(actor, req.id)

    async def rechazar_solicitud_reapertura(
        self,
        actor: Usuario,
        request_id: UUID,
        dto: PlanningEditRequestRejectDTO,
    ) -> PlanningEditRequestDTO:
        """Reject an edit request, keeping all Learning Results LOCKED."""
        self._require_pedagogical_reviewer(actor)

        stmt = (
            select(PlanningEditRequest)
            .where(PlanningEditRequest.id == request_id)
            .options(selectinload(PlanningEditRequest.items))
            .with_for_update()
        )
        res = await self.session.execute(stmt)
        req = res.scalar_one_or_none()
        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud de modificación no encontrada.")

        if req.status != EstadoSolicitudReapertura.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "EDIT_REQUEST_ALREADY_PROCESSED",
                    "message": f"La solicitud ya fue procesada (estado actual: {req.status.value}).",
                },
            )

        now = datetime.now(UTC)
        for item in req.items:
            item.approved = False

        req.status = EstadoSolicitudReapertura.REJECTED
        req.reviewed_by = actor.id
        req.admin_response = dto.admin_response.strip() if dto.admin_response else None
        req.reviewed_at = now
        req.version = (req.version or 1) + 1
        req.updated_at = now

        await self._audit(
            actor_id=actor.id,
            referencia_id=req.referencia_id,
            entidad="PlanningEditRequest",
            entidad_id=req.id,
            accion="EDIT_REQUEST_REJECTED",
            detalle={
                "request_id": str(req.id),
                "planning_id": str(req.planning_id),
                "admin_response": req.admin_response,
            },
        )

        notification_dispatcher.emit(
            event_type="edit_request.rejected",
            actor_id=actor.id,
            recipient_ids=[req.requested_by],
            referencia_id=req.referencia_id,
            planning_id=req.planning_id,
            request_id=req.id,
            team_id=req.team_id,
            payload={
                "status": EstadoSolicitudReapertura.REJECTED.value,
                "admin_response": req.admin_response,
            },
        )

        await self.session.commit()
        return await self.obtener_solicitud_reapertura(actor, req.id)

    async def listar_versiones_resultado(
        self,
        actor: Usuario,
        planning_id: UUID,
        learning_result_id: UUID | None = None,
    ) -> list[LearningResultVersionDTO]:
        """Return approved version history snapshots for Learning Results in a planning."""
        if not actor.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value):
            if not await self.scope_service.can_access_planning(actor, planning_id):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a la planeación.")

        stmt = (
            select(LearningResultVersion)
            .where(LearningResultVersion.planning_id == planning_id)
            .options(selectinload(LearningResultVersion.approver))
            .order_by(LearningResultVersion.version_number.desc(), LearningResultVersion.approved_at.desc())
        )
        if learning_result_id:
            stmt = stmt.where(LearningResultVersion.learning_result_id == learning_result_id)

        res = await self.session.execute(stmt)
        versions = list(res.scalars().all())
        return [
            LearningResultVersionDTO(
                id=v.id,
                planning_id=v.planning_id,
                learning_result_id=v.learning_result_id,
                version_number=v.version_number,
                snapshot_data=v.snapshot_data or {},
                approved_by=v.approved_by,
                approved_by_name=f"{v.approver.nombre} {v.approver.apellido}" if v.approver else None,
                approved_by_nombre=f"{v.approver.nombre} {v.approver.apellido}" if v.approver else None,
                approved_at=v.approved_at,
                edit_request_id=getattr(v, "edit_request_id", None),
                is_official=v.is_official,
                created_at=getattr(v, "created_at", None),
            )
            for v in versions
        ]

    # -------------------------------------------------------------------------
    # Private Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _extract_ra_snapshot(planeacion: PlaneacionPedagogica, resultado: ResultadoAprendizaje) -> dict[str, Any]:
        """Build a self-contained snapshot of a Learning Result and its didactic configuration within a planning."""
        datos = planeacion.datos_complementarios or {}
        rap_map = datos.get("rap_complementary_map") if isinstance(datos.get("rap_complementary_map"), dict) else {}
        if not rap_map and isinstance(datos.get("raps"), dict):
            rap_map = datos.get("raps")  # type: ignore[assignment]
        ra_specific = rap_map.get(str(resultado.id), {}) if isinstance(rap_map.get(str(resultado.id)), dict) else {}
        return {
            "learning_result_id": str(resultado.id),
            "codigo_resultado": resultado.codigo_resultado,
            "descripcion": resultado.descripcion,
            "actividades_aprendizaje": ra_specific.get("actividades_aprendizaje") or datos.get("actividades_aprendizaje"),
            "horas_trabajo_directo": ra_specific.get("horas_trabajo_directo") if "horas_trabajo_directo" in ra_specific else datos.get("horas_trabajo_directo"),
            "horas_trabajo_independiente": ra_specific.get("horas_trabajo_independiente") if "horas_trabajo_independiente" in ra_specific else datos.get("horas_trabajo_independiente"),
            "duracion_actividad_horas": ra_specific.get("duracion_actividad_horas") if "duracion_actividad_horas" in ra_specific else datos.get("duracion_actividad_horas"),
            "estrategias_didacticas": ra_specific.get("estrategias_didacticas") or datos.get("estrategias_didacticas"),
            "descripcion_evidencia_aprendizaje": ra_specific.get("descripcion_evidencia_aprendizaje") or datos.get("descripcion_evidencia_aprendizaje"),
            "ambiente": ra_specific.get("ambiente") or datos.get("ambiente") or datos.get("ambientes_aprendizaje"),
            "materiales_formacion": ra_specific.get("materiales_formacion") or datos.get("materiales_formacion") or datos.get("recursos_didacticos"),
            "instructores": ra_specific.get("instructores") or datos.get("instructores") or datos.get("instructor_responsable"),
            "observaciones": ra_specific.get("observaciones") or datos.get("observaciones"),
            "conocimientos_ids": [str(k.id) for k in (planeacion.conocimientos or [])],
            "criterios_ids": [str(c.id) for c in (planeacion.criterios or [])],
            "storage_key": planeacion.storage_key,
            "file_name": planeacion.file_name,
        }

    async def _to_edit_request_dto(self, req: PlanningEditRequest) -> PlanningEditRequestDTO:
        programa_nombre = ""
        codigo_programa = ""
        proyecto_codigo = ""
        proyecto_nombre = ""
        planning_label = None
        fase_nom = ""
        act_desc = ""

        if req.planning:
            act_desc = req.planning.actividad.descripcion if req.planning.actividad else "Actividad"
            fase_nom = req.planning.fase.nombre_fase if req.planning.fase else "Fase"
            planning_label = f"{fase_nom} — {act_desc}"

        if req.referencia_id:
            proc = await self._get_proceso_by_ref(req.referencia_id)
            if proc:
                if proc.programa:
                    programa_nombre = proc.programa.nombre_programa or ""
                    codigo_programa = proc.programa.codigo_programa or ""
                if proc.proyecto:
                    proyecto_nombre = proc.proyecto.nombre_proyecto or ""
                    proyecto_codigo = getattr(proc.proyecto, "codigo_proyecto", "") or ""

        items_dto = []
        for item in (req.items or []):
            lr = item.learning_result
            ed_st = getattr(lr, "edit_status", EstadoEdicionRA.LOCKED) if lr else EstadoEdicionRA.LOCKED
            comp = getattr(lr, "competencia", None) if lr else None
            items_dto.append(
                PlanningEditRequestItemDTO(
                    id=item.id,
                    request_id=item.request_id,
                    learning_result_id=item.learning_result_id,
                    codigo_resultado=lr.codigo_resultado if lr else None,
                    descripcion=lr.descripcion if lr else "",
                    descripcion_resultado=lr.descripcion if lr else "",
                    competencia_codigo=getattr(comp, "codigo_competencia", None) if comp else None,
                    competencia_nombre=getattr(comp, "nombre_competencia", None) if comp else None,
                    requested=item.requested,
                    approved=item.approved,
                    edit_status=ed_st.value if hasattr(ed_st, "value") else str(ed_st),
                )
            )

        created_dt = getattr(req, "created_at", None) or getattr(req, "fecha_creacion", None)
        short_code = (
            getattr(req, "codigo", None)
            or (f"REQ-{created_dt.year}-{str(req.id)[:4].upper()}" if created_dt else f"REQ-{str(req.id)[:8].upper()}")
        )
        team_label = req.team.nombre if req.team else ""
        requester_label = f"{req.requester.nombre} {req.requester.apellido}" if req.requester else ""
        reviewer_label = f"{req.reviewer.nombre} {req.reviewer.apellido}" if req.reviewer else None
        status_str = req.status.value if hasattr(req.status, "value") else str(req.status)

        return PlanningEditRequestDTO(
            id=req.id,
            codigo=short_code,
            code=short_code,
            planning_id=req.planning_id,
            planning_actividad=planning_label,
            team_id=req.team_id,
            team_name=team_label,
            team_nombre=team_label or None,
            referencia_id=req.referencia_id,
            programa_codigo=codigo_programa,
            codigo_programa=codigo_programa or None,
            programa_nombre=programa_nombre,
            proyecto_codigo=proyecto_codigo,
            proyecto_nombre=proyecto_nombre,
            fase_nombre=fase_nom,
            actividad_descripcion=act_desc,
            requested_by=req.requested_by,
            requested_by_name=requester_label,
            requested_by_nombre=requester_label or None,
            requested_by_email=req.requester.email if req.requester else "",
            reason=req.reason,
            requested_changes=req.requested_changes,
            status=status_str,
            reviewed_by=req.reviewed_by,
            reviewed_by_name=reviewer_label,
            reviewed_by_nombre=reviewer_label,
            admin_response=req.admin_response,
            version=req.version or 1,
            created_at=created_dt or datetime.now(UTC),
            reviewed_at=req.reviewed_at,
            items=items_dto,
        )


    def _require_pedagogical_reviewer(self, actor: Usuario) -> None:
        if not actor.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operación exclusiva del Equipo Pedagógico (Administrador / Superadministrador).",
            )

    async def _get_proceso_by_ref(self, referencia_id: UUID, for_update: bool = False) -> ProcesoCurricular | None:
        stmt = (
            select(ProcesoCurricular)
            .where(ProcesoCurricular.referencia_id == referencia_id)
            .options(
                selectinload(ProcesoCurricular.equipo_ejecutor),
                selectinload(ProcesoCurricular.programa),
                selectinload(ProcesoCurricular.proyecto),
            )
        )
        if for_update:
            stmt = stmt.with_for_update()
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def _get_latest_delivery_by_ref(
        self, referencia_id: UUID, for_update: bool = False
    ) -> EntregaRevisionCurricular | None:
        stmt = (
            select(EntregaRevisionCurricular)
            .where(EntregaRevisionCurricular.referencia_id == referencia_id)
            .order_by(EntregaRevisionCurricular.version.desc())
        )
        if for_update:
            stmt = stmt.with_for_update()
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def _build_snapshot_metadatos(self, proyecto_id: UUID) -> dict[str, Any]:
        """Compile deterministic checksums and counts to freeze delivery state."""
        plan_stmt = select(PlaneacionPedagogica).where(
            PlaneacionPedagogica.proyecto_id == proyecto_id,
            PlaneacionPedagogica.estado == EstadoBloque.COMPLETO,
        )
        plan_res = await self.session.execute(plan_stmt)
        plans = plan_res.scalars().all()

        config_stmt = select(PlaneacionDocumentoConfig).where(
            PlaneacionDocumentoConfig.proyecto_id == proyecto_id
        )
        config_res = await self.session.execute(config_stmt)
        doc_config = config_res.scalar_one_or_none()
        config_dict = None
        if doc_config:
            config_dict = {
                "fecha_elaboracion": doc_config.fecha_elaboracion.isoformat() if doc_config.fecha_elaboracion else None,
                "clasificacion_informacion": doc_config.clasificacion_informacion,
                "regional": doc_config.regional,
                "centro_formacion": doc_config.centro_formacion,
                "equipo_gestion_curricular": list(doc_config.equipo_gestion_curricular or []),
                "storage_key": doc_config.storage_key,
                "checksum_sha256": doc_config.checksum_sha256,
                "version": doc_config.version,
            }

        has_authorized_reopening = any(
            getattr(p, "approval_status", None) == EstadoAprobacionPlaneacion.PREVIOUS_VERSION_APPROVED
            or getattr(p, "review_status", None) == EstadoRevisionPlaneacion.CHANGES_ALLOWED
            for p in plans
        )

        return {
            "planeaciones_count": len(plans),
            "planeaciones_ids": [str(p.id) for p in plans],
            "checksum_consolidado": doc_config.checksum_sha256 if doc_config else None,
            "storage_key_consolidado": doc_config.storage_key if doc_config else None,
            "version_documento_config": doc_config.version if doc_config else 1,
            "configuracion_documental": config_dict,
            "has_authorized_reopening": has_authorized_reopening,
            "snapshot_timestamp": datetime.now(UTC).isoformat(),
        }

    async def _calculate_inbox_metrics(self) -> dict[str, int]:
        """Aggregate counts across all latest process submissions."""
        latest_subq = (
            select(
                EntregaRevisionCurricular.proceso_curricular_id,
                func.max(EntregaRevisionCurricular.version).label("max_v"),
            )
            .group_by(EntregaRevisionCurricular.proceso_curricular_id)
            .subquery()
        )
        stmt = (
            select(EntregaRevisionCurricular.estado, func.count())
            .join(
                latest_subq,
                (EntregaRevisionCurricular.proceso_curricular_id == latest_subq.c.proceso_curricular_id)
                & (EntregaRevisionCurricular.version == latest_subq.c.max_v),
            )
            .group_by(EntregaRevisionCurricular.estado)
        )
        rows = (await self.session.execute(stmt)).all()
        counts = {str(getattr(r[0], "value", r[0])): r[1] for r in rows}

        enviadas = counts.get(EstadoEntregaRevision.ENVIADO_REVISION.value, 0)
        reenviadas = counts.get(EstadoEntregaRevision.REENVIADO.value, 0)
        con_ajustes = (
            counts.get(EstadoEntregaRevision.AJUSTES_SOLICITADOS.value, 0)
            + counts.get(EstadoEntregaRevision.AJUSTES_EN_PROGRESO.value, 0)
        )

        # Count pending edit requests
        edit_req_stmt = select(func.count()).where(
            PlanningEditRequest.status == EstadoSolicitudReapertura.PENDING
        )
        solicitudes_pendientes = (await self.session.execute(edit_req_stmt)).scalar() or 0

        return {
            "pendientes": enviadas + reenviadas,
            "pendientes_revision": enviadas,
            "reenviadas": reenviadas,
            "ajustes_solicitados": con_ajustes,
            "con_ajustes_solicitados": con_ajustes,
            "aprobadas": counts.get(EstadoEntregaRevision.APROBADO.value, 0),
            "en_revision": counts.get(EstadoEntregaRevision.EN_REVISION.value, 0),
            "solicitudes_modificacion_pendientes": solicitudes_pendientes,
        }

    async def _get_observacion_dto(self, observacion_id: UUID) -> ObservacionDTO:
        stmt = (
            select(ObservacionRevision)
            .where(ObservacionRevision.id == observacion_id)
            .options(
                selectinload(ObservacionRevision.creado_por),
                selectinload(ObservacionRevision.ajuste_reportado_por),
                selectinload(ObservacionRevision.resuelto_por),
            )
        )
        res = await self.session.execute(stmt)
        obs = res.scalar_one_or_none()
        if not obs:
            raise HTTPException(status_code=404, detail="Observación no encontrada.")

        return ObservacionDTO(
            id=obs.id,
            entrega_id=obs.entrega_id,
            target_type=obs.target_type,
            target_id=obs.target_id,
            section_key=obs.section_key,
            comentario=obs.comentario,
            estado=obs.estado,
            creado_por_id=obs.creado_por_id,
            creado_por_nombre=f"{obs.creado_por.nombre} {obs.creado_por.apellido}" if obs.creado_por else "Usuario",
            fecha_creacion=obs.fecha_creacion,
            ajuste_reportado_por_id=obs.ajuste_reportado_por_id,
            ajuste_reportado_por_nombre=(
                f"{obs.ajuste_reportado_por.nombre} {obs.ajuste_reportado_por.apellido}"
                if obs.ajuste_reportado_por
                else None
            ),
            fecha_ajuste_reportado=obs.fecha_ajuste_reportado,
            comentario_ajuste=obs.comentario_ajuste,
            resuelto_por_id=obs.resuelto_por_id,
            resuelto_por_nombre=(
                f"{obs.resuelto_por.nombre} {obs.resuelto_por.apellido}"
                if obs.resuelto_por
                else None
            ),
            fecha_resolucion=obs.fecha_resolucion,
        )

    def _to_resumen_dto(self, e: EntregaRevisionCurricular) -> EntregaRevisionResumenDTO:
        obs = e.observaciones or []
        lider = e.equipo_ejecutor.lider if e.equipo_ejecutor else None
        return EntregaRevisionResumenDTO(
            id=e.id,
            proceso_curricular_id=e.proceso_curricular_id,
            referencia_id=e.referencia_id,
            equipo_ejecutor_id=e.equipo_ejecutor_id,
            equipo_ejecutor_nombre=e.equipo_ejecutor.nombre if e.equipo_ejecutor else "Equipo",
            programa_id=e.programa_id,
            codigo_programa=e.programa.codigo_programa if e.programa else "",
            nombre_programa=e.programa.nombre_programa if e.programa else "",
            proyecto_id=e.proyecto_id,
            codigo_proyecto=getattr(e.proyecto, "codigo_proyecto", "") if e.proyecto else "",
            nombre_proyecto=e.proyecto.nombre_proyecto if e.proyecto else "",
            lider_nombre=f"{lider.nombre} {lider.apellido}" if lider else "Sin líder",
            lider_email=lider.email if lider else "",
            version=e.version,
            estado=e.estado,
            fecha_envio=e.fecha_envio,
            observaciones_pendientes_count=sum(1 for o in obs if o.estado == EstadoObservacionRevision.PENDIENTE),
            observaciones_ajustadas_count=sum(1 for o in obs if o.estado == EstadoObservacionRevision.AJUSTE_REPORTADO),
            observaciones_resueltas_count=sum(1 for o in obs if o.estado == EstadoObservacionRevision.RESUELTO),
            descarga_habilitada=e.descarga_habilitada,
            fecha_actualizacion=getattr(e, "updated_at", None) or getattr(e, "fecha_actualizacion", None) or e.fecha_envio or datetime.now(UTC),
        )

    def _to_detalle_dto(
        self,
        e: EntregaRevisionCurricular,
        history: list[EntregaRevisionResumenDTO],
    ) -> EntregaRevisionDetalleDTO:
        resumen = self._to_resumen_dto(e)
        obs_dtos = [
            ObservacionDTO(
                id=o.id,
                entrega_id=o.entrega_id,
                target_type=o.target_type,
                target_id=o.target_id,
                section_key=o.section_key,
                comentario=o.comentario,
                estado=o.estado,
                creado_por_id=o.creado_por_id,
                creado_por_nombre=f"{o.creado_por.nombre} {o.creado_por.apellido}" if o.creado_por else "Usuario",
                fecha_creacion=o.fecha_creacion,
                ajuste_reportado_por_id=o.ajuste_reportado_por_id,
                ajuste_reportado_por_nombre=(
                    f"{o.ajuste_reportado_por.nombre} {o.ajuste_reportado_por.apellido}"
                    if o.ajuste_reportado_por
                    else None
                ),
                fecha_ajuste_reportado=o.fecha_ajuste_reportado,
                comentario_ajuste=o.comentario_ajuste,
                resuelto_por_id=o.resuelto_por_id,
                resuelto_por_nombre=(
                    f"{o.resuelto_por.nombre} {o.resuelto_por.apellido}"
                    if o.resuelto_por
                    else None
                ),
                fecha_resolucion=o.fecha_resolucion,
            )
            for o in (e.observaciones or [])
        ]

        return EntregaRevisionDetalleDTO(
            **resumen.model_dump(),
            notas_entrega=e.notas_entrega,
            notas_aprobacion=e.notas_aprobacion,
            snapshot_metadatos=e.snapshot_metadatos,
            observaciones=obs_dtos,
            historial_versiones=history,
        )

    async def _audit(
        self,
        actor_id: UUID | None,
        referencia_id: UUID | None,
        entidad: str,
        entidad_id: UUID,
        accion: str,
        detalle: dict[str, Any] | None = None,
    ) -> None:
        evento = EventoAuditoria(
            id=uuid.uuid4(),
            entidad=entidad,
            entidad_id=entidad_id,
            accion=accion,
            actor_usuario_id=actor_id,
            referencia_id=referencia_id,
            detalle=detalle,
        )
        self.session.add(evento)
