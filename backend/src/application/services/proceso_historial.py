"""Service for tracking and reporting modifications and history on a single ProcesoCurricular instance."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.dto.proceso_historial import (
    CambioActorDTO,
    CambioProcesoItemDTO,
    HistorialProcesoDTO,
)
from src.application.services.access_scope import AccessScopeService
from src.application.services.audit_admin import sanitize_audit_payload
from src.domain.shared.enums import EstadoBloque
from src.infrastructure.db.models.audit import EventoAuditoria
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.organizacion import (
    Coordinacion,
    EquipoEjecutor,
    Especialidad,
    ProcesoCurricular,
)
from src.infrastructure.db.models.planeacion import PlaneacionPedagogica
from src.infrastructure.db.models.proyecto import FaseProyecto, ProyectoFormativo


class ProcesoHistorialService:
    """Service to track, audit, and inspect changes strictly on a single ProcesoCurricular."""

    def __init__(
        self,
        session: AsyncSession,
        scope_service: AccessScopeService | None = None,
    ) -> None:
        self.session = session
        self.scope_service = scope_service or AccessScopeService(session)

    async def obtener_historial(
        self,
        actor: Usuario,
        referencia_id: UUID,
    ) -> HistorialProcesoDTO:
        """Fetch the complete change history and current lifecycle state of the curricular process."""
        # Require operational access according to user role and executing team
        await self.scope_service.require_process_access(actor, referencia_id)

        # Load process with rich hierarchical relationships
        stmt = (
            select(ProcesoCurricular)
            .where(ProcesoCurricular.referencia_id == referencia_id)
            .options(
                selectinload(ProcesoCurricular.coordinacion),
                selectinload(ProcesoCurricular.especialidad),
                selectinload(ProcesoCurricular.lider).selectinload(Usuario.roles),
                selectinload(ProcesoCurricular.equipo_ejecutor).selectinload(EquipoEjecutor.lider).selectinload(Usuario.roles),
                selectinload(ProcesoCurricular.programa),
                selectinload(ProcesoCurricular.proyecto).selectinload(ProyectoFormativo.fases).selectinload(FaseProyecto.actividades),
            )
        )
        res = await self.session.execute(stmt)
        proceso = res.scalar_one_or_none()
        if not proceso:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proceso curricular con referencia_id '{referencia_id}' no encontrado",
            )

        # Query BorradorSesion to capture draft states
        draft_stmt = select(BorradorSesion).where(BorradorSesion.referencia_id == referencia_id)
        draft_res = await self.session.execute(draft_stmt)
        drafts = draft_res.scalars().all()
        draft_programa = next((d for d in drafts if d.tipo_bloque == "PROGRAMA"), None)
        draft_proyecto = next((d for d in drafts if d.tipo_bloque == "PROYECTO"), None)

        # Query plannings summary if project is linked
        planeaciones_summary: dict[str, Any] = {
            "total": 0,
            "completas": 0,
            "en_borrador": 0,
            "actividades_planeadas": [],
        }
        if proceso.proyecto_id:
            plan_stmt = select(PlaneacionPedagogica).where(PlaneacionPedagogica.proyecto_id == proceso.proyecto_id)
            plan_res = await self.session.execute(plan_stmt)
            all_plans = plan_res.scalars().all()
            planeaciones_summary["total"] = len(all_plans)
            planeaciones_summary["completas"] = sum(1 for p in all_plans if p.estado == EstadoBloque.COMPLETO)
            planeaciones_summary["en_borrador"] = sum(1 for p in all_plans if p.estado != EstadoBloque.COMPLETO)
            planeaciones_summary["actividades_planeadas"] = [
                {
                    "id": str(p.id),
                    "actividad_id": str(p.actividad_id),
                    "estado": p.estado.value if hasattr(p.estado, "value") else str(p.estado),
                    "fecha_actualizacion": p.fecha_actualizacion.isoformat() if p.fecha_actualizacion else None,
                }
                for p in all_plans
            ]

        # Query all audit events related to this process/reference
        or_conds = [
            EventoAuditoria.referencia_id == referencia_id,
            EventoAuditoria.entidad_id == proceso.id,
        ]
        if proceso.programa_id:
            or_conds.append(EventoAuditoria.entidad_id == proceso.programa_id)
        if proceso.proyecto_id:
            or_conds.append(EventoAuditoria.entidad_id == proceso.proyecto_id)
        if proceso.proyecto_id and all_plans:
            plan_ids = [p.id for p in all_plans]
            or_conds.append(EventoAuditoria.entidad_id.in_(plan_ids))

        events_stmt = (
            select(EventoAuditoria)
            .options(
                selectinload(EventoAuditoria.actor).selectinload(Usuario.roles),
            )
            .where(or_(*or_conds))
            .order_by(EventoAuditoria.fecha_evento.desc())
        )
        events_res = await self.session.execute(events_stmt)
        all_events = events_res.scalars().all()

        cambios_items: list[CambioProcesoItemDTO] = []
        for ev in all_events:
            actor_dto: CambioActorDTO | None = None
            if ev.actor:
                rol_name = ""
                if hasattr(ev.actor, "roles") and ev.actor.roles:
                    rol_name = getattr(ev.actor.roles[0], "nombre", str(ev.actor.roles[0]))
                full_name = f"{ev.actor.nombre} {ev.actor.apellido}".strip() if ev.actor.apellido else ev.actor.nombre
                actor_dto = CambioActorDTO(
                    id=ev.actor.id,
                    nombre=full_name,
                    apellido=ev.actor.apellido,
                    email=ev.actor.email,
                    rol=rol_name,
                )
            elif proceso.lider:
                rol_name = ""
                if hasattr(proceso.lider, "roles") and proceso.lider.roles:
                    rol_name = getattr(proceso.lider.roles[0], "nombre", str(proceso.lider.roles[0]))
                full_name = f"{proceso.lider.nombre} {proceso.lider.apellido}".strip() if proceso.lider.apellido else proceso.lider.nombre
                actor_dto = CambioActorDTO(
                    id=proceso.lider.id,
                    nombre=full_name,
                    apellido=proceso.lider.apellido,
                    email=proceso.lider.email,
                    rol=rol_name or "LIDER_EQUIPO_EJECUTOR",
                )
            elif proceso.equipo_ejecutor and proceso.equipo_ejecutor.lider:
                lider = proceso.equipo_ejecutor.lider
                rol_name = ""
                if hasattr(lider, "roles") and lider.roles:
                    rol_name = getattr(lider.roles[0], "nombre", str(lider.roles[0]))
                full_name = f"{lider.nombre} {lider.apellido}".strip() if lider.apellido else lider.nombre
                actor_dto = CambioActorDTO(
                    id=lider.id,
                    nombre=full_name,
                    apellido=lider.apellido,
                    email=lider.email,
                    rol=rol_name or "LIDER_EQUIPO_EJECUTOR",
                )

            tipo_ev, desc = self._classify_event(ev.accion, ev.entidad, ev.detalle)
            sanitized_det = sanitize_audit_payload(ev.detalle) if ev.detalle is not None else None

            cambios_items.append(
                CambioProcesoItemDTO(
                    id=ev.id,
                    fecha_evento=ev.fecha_evento,
                    accion=ev.accion,
                    tipo_evento=tipo_ev,
                    descripcion=desc,
                    actor=actor_dto,
                    entidad=ev.entidad,
                    entidad_id=ev.entidad_id,
                    detalle=sanitized_det,
                )
            )

        # Team projection
        equipo_data = None
        if proceso.equipo_ejecutor:
            eq = proceso.equipo_ejecutor
            equipo_data = {
                "id": str(eq.id),
                "nombre": eq.nombre,
                "coordinacion_nombre": proceso.coordinacion.nombre if proceso.coordinacion else None,
                "especialidad_nombre": proceso.especialidad.nombre if proceso.especialidad else None,
                "lider": {
                    "id": str(eq.lider.id),
                    "nombre": f"{eq.lider.nombre} {eq.lider.apellido}".strip(),
                    "email": eq.lider.email,
                } if eq.lider else None,
            }

        # Program projection
        programa_data = None
        if proceso.programa:
            prog = proceso.programa
            estado_prog = (
                draft_programa.estado_borrador.value
                if (draft_programa and hasattr(draft_programa.estado_borrador, "value"))
                else ("COMPLETO" if prog else "SIN_INICIAR")
            )
            programa_data = {
                "id": str(prog.id),
                "codigo": prog.codigo_programa,
                "nombre": prog.nombre_programa,
                "version": prog.version_programa,
                "modalidad": prog.modalidad_formacion,
                "estado": estado_prog,
            }
        elif draft_programa:
            meta = draft_programa.payload_json.get("meta", {}) if isinstance(draft_programa.payload_json, dict) else {}
            prog_info = draft_programa.payload_json.get("programa", {}) if isinstance(draft_programa.payload_json, dict) else {}
            programa_data = {
                "id": meta.get("programa_id") or meta.get("programaId"),
                "codigo": prog_info.get("codigo_programa") or meta.get("codigo_programa", "Sin código"),
                "nombre": prog_info.get("nombre_programa") or meta.get("nombre_programa", "Programa en borrador"),
                "version": prog_info.get("version_programa") or meta.get("version_programa", "1"),
                "modalidad": prog_info.get("modalidad_formacion"),
                "estado": draft_programa.estado_borrador.value if hasattr(draft_programa.estado_borrador, "value") else str(draft_programa.estado_borrador),
            }

        # Project projection
        proyecto_data = None
        if proceso.proyecto:
            proy = proceso.proyecto
            total_actividades = sum(len(f.actividades) for f in proy.fases) if proy.fases else 0
            estado_proy = (
                draft_proyecto.estado_borrador.value
                if (draft_proyecto and hasattr(draft_proyecto.estado_borrador, "value"))
                else "ACTIVO"
            )
            proyecto_data = {
                "id": str(proy.id),
                "codigo_sofia": getattr(proy, "codigo_proyecto", None) or getattr(proy, "codigo_proyecto_sofia", None),
                "nombre": proy.nombre_proyecto,
                "fases_count": len(proy.fases) if proy.fases else 0,
                "actividades_count": total_actividades,
                "estado": estado_proy,
            }
        elif draft_proyecto:
            proj_dict = draft_proyecto.payload_json.get("proyecto", {}) if isinstance(draft_proyecto.payload_json, dict) else {}
            estructura = draft_proyecto.payload_json.get("estructura", {}) if isinstance(draft_proyecto.payload_json, dict) else {}
            proyecto_data = {
                "id": proj_dict.get("proyecto_formativo_id"),
                "codigo_sofia": proj_dict.get("codigo_proyecto"),
                "nombre": proj_dict.get("nombre_proyecto", "Proyecto en borrador"),
                "fases_count": len(estructura.get("fases", [])) if isinstance(estructura, dict) else 0,
                "actividades_count": len(estructura.get("actividades", [])) if isinstance(estructura, dict) else 0,
                "estado": draft_proyecto.estado_borrador.value if hasattr(draft_proyecto.estado_borrador, "value") else str(draft_proyecto.estado_borrador),
            }

        # Calculate latest modification date
        raw_candidates = [proceso.fecha_actualizacion, proceso.fecha_creacion]
        for d in drafts:
            if getattr(d, "ultima_edicion", None):
                raw_candidates.append(d.ultima_edicion)
        if all_events:
            raw_candidates.append(all_events[0].fecha_evento)
        valid_dates = [d for d in raw_candidates if d is not None]
        latest_date = max(valid_dates) if valid_dates else datetime.now(UTC)
        created_date = proceso.fecha_creacion or (all_events[-1].fecha_evento if all_events else latest_date)

        return HistorialProcesoDTO(
            proceso_id=proceso.id,
            referencia_id=proceso.referencia_id,
            estado_scope=proceso.estado_scope.value if hasattr(proceso.estado_scope, "value") else str(proceso.estado_scope),
            tipo_necesidad=proceso.tipo_necesidad.value if hasattr(proceso.tipo_necesidad, "value") else str(proceso.tipo_necesidad),
            equipo=equipo_data,
            programa=programa_data,
            proyecto=proyecto_data,
            planeaciones=planeaciones_summary,
            fecha_creacion=created_date,
            fecha_ultima_modificacion=latest_date,
            total_cambios=len(cambios_items),
            cambios=cambios_items,
            garantia_unicidad=True,
            mensaje_unicidad="Este proceso opera bajo una instancia curricular única y consolidada sin duplicidad.",
        )

    async def registrar_cambio(
        self,
        actor: Usuario,
        referencia_id: UUID,
        accion: str,
        descripcion: str,
        detalle: dict[str, Any] | None = None,
    ) -> CambioProcesoItemDTO:
        """Register a new change or operational annotation directly on the existing process."""
        # Require operational access
        proceso = await self.scope_service.require_process_access(actor, referencia_id)

        clean_accion = accion.strip().upper() if accion else "PROCESO_CAMBIO_REGISTRADO"
        clean_desc = descripcion.strip() if descripcion else "Actualización registrada sobre el proceso"

        # Update modification timestamp on the single existing process
        proceso.fecha_actualizacion = datetime.now(UTC)

        event_detail: dict[str, Any] = {
            "descripcion": clean_desc,
            "referencia_id": str(referencia_id),
        }
        if detalle and isinstance(detalle, dict):
            event_detail.update(detalle)

        event = EventoAuditoria(
            id=uuid.uuid4(),
            entidad="ProcesoCurricular",
            entidad_id=proceso.id,
            accion=clean_accion,
            detalle=event_detail,
            actor_usuario_id=actor.id,
            referencia_id=referencia_id,
            fecha_evento=datetime.now(UTC),
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)

        rol_name = ""
        if hasattr(actor, "roles") and actor.roles:
            rol_name = getattr(actor.roles[0], "nombre", str(actor.roles[0]))

        actor_dto = CambioActorDTO(
            id=actor.id,
            nombre=actor.nombre,
            apellido=actor.apellido,
            email=actor.email,
            rol=rol_name,
        )

        return CambioProcesoItemDTO(
            id=event.id,
            fecha_evento=event.fecha_evento,
            accion=clean_accion,
            tipo_evento="CAMBIO_REGISTRADO",
            descripcion=clean_desc,
            actor=actor_dto,
            entidad=event.entidad,
            entidad_id=event.entidad_id,
            detalle=sanitize_audit_payload(event.detalle),
        )

    @staticmethod
    def _classify_event(
        accion: str,
        entidad: str,
        detalle: dict[str, Any] | None,
    ) -> tuple[str, str]:
        """Classify action into category and synthesize a clear user-facing description."""
        accion_upper = accion.upper()

        # If user explicitly supplied a description in detail, respect it
        if isinstance(detalle, dict) and detalle.get("descripcion"):
            return "CAMBIO_REGISTRADO", str(detalle["descripcion"])

        if "CURRICULAR_PROCESS_STARTED" in accion_upper or "PROCESS_STARTED" in accion_upper:
            return "CREACION", "Proceso curricular iniciado para el equipo ejecutor y programa de formación"
        if "PROCESS_ASSIGNED" in accion_upper or "ASIGNAR" in accion_upper:
            return "CREACION", "Proceso curricular asignado al equipo ejecutor"
        if "EXCEL_CANONICO_IMPORTADO" in accion_upper or ("EXCEL" in accion_upper and "PROGRAMA" in entidad.upper()):
            res_txt = ""
            if isinstance(detalle, dict):
                comps = detalle.get("competencias", 0)
                raps = detalle.get("resultados", 0)
                res_txt = f" ({comps} competencias, {raps} resultados de aprendizaje)"
            return "PROGRAMA", f"Matriz Excel canónica del programa importada exitosamente{res_txt}"
        if "PROGRAMA_CERRADO" in accion_upper or "PROGRAMA_CIERRE" in accion_upper:
            return "PROGRAMA", "Programa de formación validado y consolidado en estado COMPLETO"
        if "EXCEL_PROYECTO_IMPORTADO" in accion_upper or ("EXCEL" in accion_upper and "PROYECTO" in entidad.upper()):
            res_txt = ""
            if isinstance(detalle, dict):
                fases = detalle.get("fases", 0)
                acts = detalle.get("actividades", 0)
                res_txt = f" ({fases} fases, {acts} actividades)"
            return "PROYECTO", f"Matriz Excel del proyecto formativo importada exitosamente{res_txt}"
        if "PROYECTO_CERRADO" in accion_upper or "PROYECTO_CIERRE" in accion_upper:
            return "PROYECTO", "Proyecto formativo validado y consolidado en estado COMPLETO"
        if "PLANEACION_COMPLETADA" in accion_upper:
            act_txt = f": {detalle.get('descripcion_actividad')}" if isinstance(detalle, dict) and detalle.get("descripcion_actividad") else ""
            return "PLANEACION", f"Planeación pedagógica validada y cerrada{act_txt}"
        if "PLANEACION_CREADA" in accion_upper:
            act_txt = f": {detalle.get('descripcion_actividad')}" if isinstance(detalle, dict) and detalle.get("descripcion_actividad") else ""
            return "PLANEACION", f"Borrador de planeación pedagógica creado{act_txt}"
        if "PLANEACION_ACTUALIZADA" in accion_upper:
            act_txt = f": {detalle.get('descripcion_actividad')}" if isinstance(detalle, dict) and detalle.get("descripcion_actividad") else ""
            return "PLANEACION", f"Planeación pedagógica actualizada{act_txt}"
        if "PLANEACION_ELIMINADA" in accion_upper:
            act_txt = f": {detalle.get('descripcion_actividad')}" if isinstance(detalle, dict) and detalle.get("descripcion_actividad") else ""
            return "PLANEACION", f"Planeación pedagógica eliminada{act_txt}"
        if "CONFIGURACION_FORMATO_ACTUALIZADA" in accion_upper:
            return "PLANEACION", "Configuración institucional para formato GPFI-F-134 V05 actualizada"
        if "GPFI_F_134_CONSOLIDADO" in accion_upper:
            return "PLANEACION", "Formato consolidado GPFI-F-134 V05 generado y almacenado en MinIO"
        if "GPFI_F_134" in accion_upper or "EXCEL_GENERADO" in accion_upper:
            return "PLANEACION", "Formato institucional GPFI-F-134 V05 generado y almacenado en MinIO"
        if "TEAM_LEADER_CHANGED" in accion_upper:
            return "EQUIPO", "Cambio de líder asignado al equipo ejecutor del proceso"
        if "TEAM_MEMBER" in accion_upper:
            return "EQUIPO", "Actualización en los miembros del equipo ejecutor"

        return "SISTEMA", f"Operación registrada: {accion.replace('_', ' ').capitalize()}"
