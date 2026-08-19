"""Master dashboard aggregation service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.dto.dashboard import (
    DashboardDTO,
    DashboardGraphEdgeDTO,
    DashboardGraphNodeDTO,
    DashboardMetricsDTO,
    DashboardModuleDTO,
    DashboardProgramFlowDTO,
    PlaneacionDashboardMetricsDTO,
    ProgramaDashboardMetricsDTO,
    ProyectoDashboardMetricsDTO,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import (
    EstadoBloque,
    TipoConocimiento,
    TipoResultadoProyecto,
)
from src.infrastructure.db.models.curriculum import (
    Competencia,
    ProgramaFormacion,
    ResultadoAprendizaje,
)
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.planeacion import (
    PlaneacionPedagogica,
    planeacion_resultados,
)
from src.infrastructure.db.models.proyecto import (
    AsignacionCurricularProyecto,
    FaseProyecto,
    ProyectoFormativo,
)


class DashboardDraftNotFoundError(Exception):
    """Raised when the dashboard cannot resolve the program reference."""


class ProgramaCleanupProtocol(Protocol):
    """Port for deleting the complete persisted program aggregate."""

    async def eliminar_cargue_completo(self, referencia_id: uuid.UUID) -> None:
        """Delete relational data and stored documents for a program."""


@dataclass(frozen=True)
class DashboardPlaneacionRow:
    """Minimal planning/result row required for dashboard metrics."""

    planeacion_id: uuid.UUID
    estado: EstadoBloque | str | None
    actividad_id: uuid.UUID | None
    resultado_id: uuid.UUID | None
    competencia_id: uuid.UUID | None
    tipo_resultado: str | None


class DashboardService:
    """Build the master panel from persisted program, project and planning data."""

    def __init__(
        self,
        session: AsyncSession,
        cleanup_service: ProgramaCleanupProtocol | None = None,
    ) -> None:
        """Initialize the service with the active database session."""
        self._session = session
        self._cleanup_service = cleanup_service

    async def consultar(self, referencia_id: uuid.UUID) -> DashboardDTO:
        """Return the full dashboard state for a program draft reference."""
        draft = await self._get_program_draft(referencia_id)
        programa_id = _extract_programa_id(draft.payload_json)

        programa = await self._get_programa(programa_id)
        proyecto = await self._get_proyecto(programa_id) if programa_id else None
        planeaciones = (
            await self._get_planeaciones(proyecto.id) if proyecto is not None else []
        )

        estado_programa = _estado_value(
            programa.estado if programa is not None else draft.estado_borrador
        )
        programa_completo = estado_programa == EstadoBloque.COMPLETO.value

        estado_proyecto = _estado_value(
            proyecto.estado
            if proyecto is not None
            else (
                EstadoBloque.BORRADOR if programa_completo else EstadoBloque.BLOQUEADO
            )
        )
        proyecto_completo = (
            proyecto is not None and proyecto.estado == EstadoBloque.COMPLETO
        )
        planeacion_disponible = programa_completo and proyecto_completo

        metricas = _build_metrics(
            programa=programa,
            proyecto=proyecto,
            planeaciones=planeaciones,
            estado_programa=estado_programa,
            estado_proyecto=estado_proyecto,
            planeacion_disponible=planeacion_disponible,
        )
        modules = _build_modules(
            referencia_id=referencia_id,
            estado_programa=estado_programa,
            estado_proyecto=estado_proyecto,
            programa_completo=programa_completo,
            proyecto_completo=proyecto_completo,
            metricas=metricas,
        )
        nodes, edges = _build_graph(
            referencia_id=referencia_id,
            modules=modules,
            metricas=metricas,
            planeacion_disponible=planeacion_disponible,
        )

        return DashboardDTO(
            referencia_id=referencia_id,
            estado_global=_estado_global(
                programa_completo=programa_completo,
                proyecto_completo=proyecto_completo,
                planeaciones_completas=metricas.planeacion.completas,
            ),
            resumen=_resumen_global(
                programa_completo=programa_completo,
                proyecto_completo=proyecto_completo,
                planeaciones_completas=metricas.planeacion.completas,
            ),
            modules=modules,
            metricas=metricas,
            graph_nodes=nodes,
            graph_edges=edges,
        )

    async def listar_flujos_programa(self) -> list[DashboardProgramFlowDTO]:
        """Return open program drafts available from the master panel."""
        statement = (
            select(BorradorSesion)
            .where(BorradorSesion.tipo_bloque == TipoBloqueBorrador.PROGRAMA.value)
            .order_by(BorradorSesion.ultima_edicion.desc())
        )
        result = await self._session.execute(statement)
        drafts = result.scalars().all()
        flows: list[DashboardProgramFlowDTO] = []

        for draft in drafts:
            programa_id = _extract_programa_id(draft.payload_json)
            programa = await self._get_programa(programa_id)
            nombre_programa = programa.nombre_programa if programa is not None else None
            codigo_programa = programa.codigo_programa if programa is not None else None
            titulo = _flow_title(
                nombre_programa=nombre_programa,
                codigo_programa=codigo_programa,
                referencia_id=draft.referencia_id,
            )
            flows.append(
                DashboardProgramFlowDTO(
                    referencia_id=draft.referencia_id,
                    estado=_estado_value(draft.estado_borrador),
                    paso_actual=draft.paso_actual,
                    ultima_edicion=draft.ultima_edicion,
                    titulo=titulo,
                    codigo_programa=codigo_programa,
                    nombre_programa=nombre_programa,
                    href=f"/programa?referencia_id={draft.referencia_id}",
                )
            )

        return flows

    async def eliminar_flujo_programa(self, referencia_id: uuid.UUID) -> None:
        """Permanently delete a program aggregate, drafts, and stored documents."""
        program_statement = select(BorradorSesion).where(
            BorradorSesion.tipo_bloque == TipoBloqueBorrador.PROGRAMA.value,
            BorradorSesion.referencia_id == referencia_id,
        )
        program_result = await self._session.execute(program_statement)
        program_draft = program_result.scalar_one_or_none()
        if program_draft is None:
            raise DashboardDraftNotFoundError(
                "No existe un programa para eliminar"
            )

        if self._cleanup_service is None:
            raise RuntimeError("El servicio de eliminación no está configurado")
        await self._cleanup_service.eliminar_cargue_completo(referencia_id)

        drafts_statement = select(BorradorSesion).where(
            BorradorSesion.referencia_id == referencia_id,
            BorradorSesion.tipo_bloque.in_(
                [
                    TipoBloqueBorrador.PROGRAMA.value,
                    TipoBloqueBorrador.PROYECTO.value,
                ]
            ),
        )
        drafts_result = await self._session.execute(drafts_statement)
        drafts = drafts_result.scalars().all()
        for draft in drafts:
            await self._session.delete(draft)
        await self._session.commit()

    async def _get_program_draft(self, referencia_id: uuid.UUID) -> BorradorSesion:
        statement = select(BorradorSesion).where(
            BorradorSesion.tipo_bloque == TipoBloqueBorrador.PROGRAMA.value,
            BorradorSesion.referencia_id == referencia_id,
        )
        result = await self._session.execute(statement)
        draft = result.scalar_one_or_none()
        if draft is None:
            raise DashboardDraftNotFoundError(
                "No existe un borrador de programa para la referencia dada"
            )
        return draft

    async def _get_programa(
        self, programa_id: uuid.UUID | None
    ) -> ProgramaFormacion | None:
        if programa_id is None:
            return None
        return await self._session.get(
            ProgramaFormacion,
            programa_id,
            options=[
                selectinload(ProgramaFormacion.competencias).selectinload(
                    Competencia.resultados
                ),
                selectinload(ProgramaFormacion.competencias).selectinload(
                    Competencia.conocimientos
                ),
                selectinload(ProgramaFormacion.competencias).selectinload(
                    Competencia.criterios
                ),
            ],
        )

    async def _get_proyecto(
        self, programa_id: uuid.UUID | None
    ) -> ProyectoFormativo | None:
        if programa_id is None:
            return None
        statement = (
            select(ProyectoFormativo)
            .where(ProyectoFormativo.programa_id == programa_id)
            .order_by(
                ProyectoFormativo.fecha_actualizacion.desc(),
                ProyectoFormativo.fecha_creacion.desc(),
            )
            .limit(1)
            .options(
                selectinload(ProyectoFormativo.fases).selectinload(
                    FaseProyecto.actividades
                )
            )
        )
        result = await self._session.execute(statement)
        return result.scalars().first()

    async def _get_planeaciones(
        self, proyecto_id: uuid.UUID
    ) -> list[DashboardPlaneacionRow]:
        """Return one row per planning/result with derived competency data."""
        statement = (
            select(
                PlaneacionPedagogica.id.label("planeacion_id"),
                PlaneacionPedagogica.estado.label("estado"),
                PlaneacionPedagogica.actividad_id.label("actividad_id"),
                ResultadoAprendizaje.id.label("resultado_id"),
                ResultadoAprendizaje.competencia_id.label("competencia_id"),
                AsignacionCurricularProyecto.tipo_resultado.label(
                    "tipo_resultado"
                ),
            )
            .outerjoin(
                planeacion_resultados,
                planeacion_resultados.c.planeacion_id == PlaneacionPedagogica.id,
            )
            .outerjoin(
                ResultadoAprendizaje,
                ResultadoAprendizaje.id
                == planeacion_resultados.c.resultado_id,
            )
            .outerjoin(
                AsignacionCurricularProyecto,
                (
                    AsignacionCurricularProyecto.actividad_proyecto_id
                    == PlaneacionPedagogica.actividad_id
                )
                & (
                    AsignacionCurricularProyecto.resultado_id
                    == ResultadoAprendizaje.id
                ),
            )
            .where(
                PlaneacionPedagogica.proyecto_id == proyecto_id,
            )
        )
        result = await self._session.execute(statement)
        return [
            DashboardPlaneacionRow(
                planeacion_id=row["planeacion_id"],
                estado=row["estado"],
                actividad_id=row["actividad_id"],
                resultado_id=row["resultado_id"],
                competencia_id=row["competencia_id"],
                tipo_resultado=row["tipo_resultado"],
            )
            for row in result.mappings().all()
        ]


def _build_metrics(
    *,
    programa: ProgramaFormacion | None,
    proyecto: ProyectoFormativo | None,
    planeaciones: list[DashboardPlaneacionRow],
    estado_programa: str,
    estado_proyecto: str,
    planeacion_disponible: bool,
) -> DashboardMetricsDTO:
    competencias = programa.competencias if programa is not None else []
    conocimientos = [
        conocimiento
        for competencia in competencias
        for conocimiento in competencia.conocimientos
    ]
    planeacion_ids = {item.planeacion_id for item in planeaciones}
    planeaciones_completas = {
        item.planeacion_id
        for item in planeaciones
        if item.estado == EstadoBloque.COMPLETO
    }
    planeaciones_borrador = {
        item.planeacion_id
        for item in planeaciones
        if item.estado == EstadoBloque.BORRADOR
    }
    actividades_con_planeacion = {
        item.actividad_id for item in planeaciones if item.actividad_id is not None
    }
    competencias_planeadas = {
        item.competencia_id for item in planeaciones if item.competencia_id is not None
    }
    resultados_planeados = {
        item.resultado_id for item in planeaciones if item.resultado_id is not None
    }
    resultados_especificos = {
        item.resultado_id
        for item in planeaciones
        if item.resultado_id is not None
        and item.tipo_resultado == TipoResultadoProyecto.ESPECIFICO.value
    }
    resultados_transversales = {
        item.resultado_id
        for item in planeaciones
        if item.resultado_id is not None
        and item.tipo_resultado == TipoResultadoProyecto.TRANSVERSAL.value
    }
    fases = proyecto.fases if proyecto is not None else []
    actividades = [actividad for fase in fases for actividad in fase.actividades]

    return DashboardMetricsDTO(
        programa=ProgramaDashboardMetricsDTO(
            estado=estado_programa,
            competencias=len(competencias),
            resultados=sum(len(competencia.resultados) for competencia in competencias),
            conocimientos=sum(
                1
                for conocimiento in conocimientos
                if conocimiento.tipo
                in {TipoConocimiento.SABER, TipoConocimiento.PROCESO}
            ),
            criterios=sum(len(competencia.criterios) for competencia in competencias),
        ),
        proyecto=ProyectoDashboardMetricsDTO(
            estado=estado_proyecto,
            fases=len(fases),
            actividades=len(actividades),
            fuente_estructurada_cargada=proyecto is not None,
        ),
        planeacion=PlaneacionDashboardMetricsDTO(
            estado="DISPONIBLE" if planeacion_disponible else "BLOQUEADO",
            total=len(planeacion_ids),
            borrador=len(planeaciones_borrador),
            completas=len(planeaciones_completas),
            actividades_con_planeacion=len(actividades_con_planeacion),
            competencias_con_planeacion=len(competencias_planeadas),
            competencias_sin_planear=max(
                len(competencias) - len(competencias_planeadas),
                0,
            ),
            resultados_con_planeacion=len(resultados_planeados),
            resultados_especificos_con_planeacion=len(resultados_especificos),
            resultados_transversales_con_planeacion=len(resultados_transversales),
        ),
    )


def _build_modules(
    *,
    referencia_id: uuid.UUID,
    estado_programa: str,
    estado_proyecto: str,
    programa_completo: bool,
    proyecto_completo: bool,
    metricas: DashboardMetricsDTO,
) -> list[DashboardModuleDTO]:
    proyecto_disponible = programa_completo
    planeacion_disponible = programa_completo and proyecto_completo
    return [
        DashboardModuleDTO(
            id="programa",
            titulo="Programa de formacion",
            estado=estado_programa,
            disponible=True,
            href="/programa",
            motivo_bloqueo=None,
            accion_requerida="Cargar Excel, revisar estructura y cerrar programa.",
            descripcion="Fuente estructurada del programa y revision curricular.",
            avance_porcentaje=_percentage(
                estado_programa,
                metricas.programa.competencias,
            ),
        ),
        DashboardModuleDTO(
            id="proyecto",
            titulo="Proyecto formativo",
            estado=estado_proyecto,
            disponible=proyecto_disponible,
            href=f"/proyecto/{referencia_id}",
            motivo_bloqueo=None if proyecto_disponible else "PROGRAMA_NO_COMPLETO",
            accion_requerida=(
                "Iniciar o continuar el proyecto formativo."
                if proyecto_disponible
                else "Cerrar el programa como COMPLETO."
            ),
            descripcion="PDF evidencia y matriz estructurada del proyecto.",
            avance_porcentaje=_percentage(estado_proyecto, metricas.proyecto.fases),
        ),
        DashboardModuleDTO(
            id="planeacion",
            titulo="Planeacion pedagogica",
            estado="DISPONIBLE" if planeacion_disponible else "BLOQUEADO",
            disponible=planeacion_disponible,
            href=f"/planeacion/{referencia_id}",
            motivo_bloqueo=None
            if planeacion_disponible
            else (
                "PROYECTO_NO_COMPLETO" if programa_completo else "PROGRAMA_NO_COMPLETO"
            ),
            accion_requerida=(
                "Crear planeaciones integradas por actividad de aprendizaje."
                if planeacion_disponible
                else "Cerrar el proyecto como COMPLETO."
            ),
            descripcion=(
                "Planeaciones integradas por fase, actividad, competencias y RAP."
            ),
            avance_porcentaje=(
                100
                if metricas.planeacion.total > 0
                and metricas.planeacion.total == metricas.planeacion.completas
                else 50
                if metricas.planeacion.total > 0
                else 0
            ),
        ),
    ]


def _build_graph(
    *,
    referencia_id: uuid.UUID,
    modules: list[DashboardModuleDTO],
    metricas: DashboardMetricsDTO,
    planeacion_disponible: bool,
) -> tuple[list[DashboardGraphNodeDTO], list[DashboardGraphEdgeDTO]]:
    module_by_id = {module.id: module for module in modules}
    programa = module_by_id["programa"]
    proyecto = module_by_id["proyecto"]
    planeacion = module_by_id["planeacion"]
    nodes = [
        DashboardGraphNodeDTO(
            id="programa",
            label="Programa",
            tipo="wizard",
            estado=programa.estado,
            href="/programa",
            disponible=True,
            detalle=(
                f"{metricas.programa.competencias} competencias, "
                f"{metricas.programa.resultados} resultados"
            ),
        ),
        DashboardGraphNodeDTO(
            id="estructura-curricular",
            label="Estructura curricular",
            tipo="contenido",
            estado=programa.estado,
            href="/programa",
            disponible=True,
            detalle=(
                f"{metricas.programa.conocimientos} conocimientos y "
                f"{metricas.programa.criterios} criterios"
            ),
        ),
        DashboardGraphNodeDTO(
            id="proyecto",
            label="Proyecto",
            tipo="wizard",
            estado=proyecto.estado,
            href=f"/proyecto/{referencia_id}",
            disponible=proyecto.disponible,
            detalle=(
                f"{metricas.proyecto.fases} fases, "
                f"{metricas.proyecto.actividades} actividades"
            ),
        ),
        DashboardGraphNodeDTO(
            id="planeacion",
            label="Planeacion",
            tipo="wizard",
            estado=planeacion.estado,
            href=f"/planeacion/{referencia_id}",
            disponible=planeacion_disponible,
            detalle=(
                f"{metricas.planeacion.completas} completas, "
                f"{metricas.planeacion.borrador} borradores"
            ),
        ),
    ]
    edges = [
        DashboardGraphEdgeDTO(
            origen="programa",
            destino="estructura-curricular",
            estado="ACTIVA",
            label="importa y organiza",
        ),
        DashboardGraphEdgeDTO(
            origen="estructura-curricular",
            destino="proyecto",
            estado="ACTIVA" if proyecto.disponible else "BLOQUEADA",
            label="habilita si programa esta COMPLETO",
        ),
        DashboardGraphEdgeDTO(
            origen="proyecto",
            destino="planeacion",
            estado="ACTIVA" if planeacion_disponible else "BLOQUEADA",
            label="habilita si proyecto esta COMPLETO",
        ),
    ]
    return nodes, edges


def _percentage(estado: str, count: int) -> int:
    if estado == EstadoBloque.COMPLETO.value:
        return 100
    if count > 0:
        return 60
    if estado == EstadoBloque.EN_REVISION.value:
        return 75
    return 20 if estado == EstadoBloque.BORRADOR.value else 0


def _estado_value(value: EstadoBloque | str | None) -> str:
    if isinstance(value, EstadoBloque):
        return value.value
    if isinstance(value, str) and value:
        return value
    return EstadoBloque.BORRADOR.value


def _estado_global(
    *,
    programa_completo: bool,
    proyecto_completo: bool,
    planeaciones_completas: int,
) -> str:
    if programa_completo and proyecto_completo and planeaciones_completas > 0:
        return "PLANEACION_EN_CURSO"
    if programa_completo and proyecto_completo:
        return "LISTO_PARA_PLANEACION"
    if programa_completo:
        return "PROYECTO_EN_CURSO"
    return "PROGRAMA_EN_CURSO"


def _resumen_global(
    *,
    programa_completo: bool,
    proyecto_completo: bool,
    planeaciones_completas: int,
) -> str:
    if programa_completo and proyecto_completo and planeaciones_completas > 0:
        return "El flujo base esta completo y ya existen planeaciones aprobadas."
    if programa_completo and proyecto_completo:
        return (
            "Programa y proyecto completos; "
            "la planeacion pedagogica esta habilitada."
        )
    if programa_completo:
        return "Programa completo; falta cerrar el proyecto para habilitar planeacion."
    return "Completa y cierra el programa para desbloquear los modulos siguientes."


def _extract_programa_id(payload: object) -> uuid.UUID | None:
    if not isinstance(payload, dict):
        return None

    for section_name, key in (
        ("curricular", "programa_formacion_id"),
        ("meta", "programaId"),
    ):
        section = payload.get(section_name)
        if isinstance(section, dict):
            parsed = _parse_uuid(section.get(key))
            if parsed is not None:
                return parsed

    documental = payload.get("documental")
    if isinstance(documental, dict):
        programa_excel = documental.get("programa_excel")
        if isinstance(programa_excel, dict):
            confirmacion = programa_excel.get("confirmacion")
            if isinstance(confirmacion, dict):
                return _parse_uuid(confirmacion.get("programa_id"))
    return None


def _parse_uuid(value: object) -> uuid.UUID | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def _flow_title(
    *,
    nombre_programa: str | None,
    codigo_programa: str | None,
    referencia_id: uuid.UUID,
) -> str:
    if nombre_programa and codigo_programa:
        return f"{nombre_programa} / {codigo_programa}"
    if nombre_programa:
        return nombre_programa
    return f"Programa sin importar / {str(referencia_id)[:8]}"
