"""Application service for integrated Pedagogical Planning management.

A pedagogical planning is an integrated learning activity built on top of
one project phase/activity pair. Its learning results (RAP) are the source
of truth; competencies are always derived from those results through the
project curricular structure materialized in PostgreSQL.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal, Protocol, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.dto.planeacion import (
    ContextoActividadDTO,
    ContextoCompetenciaDTO,
    ContextoConocimientoDTO,
    ContextoCriterioDTO,
    ContextoFaseDTO,
    ContextoResultadoDTO,
    FormatoOficialEstadoDTO,
    FormatoOficialFaltanteDTO,
    FormatoOficialGeneradoDTO,
    PlaneacionCompetenciaResumenDTO,
    PlaneacionContextoDTO,
    PlaneacionDocumentoConfigDTO,
    PlaneacionDocumentoConfigUpdateDTO,
    PlaneacionListCompetenciaDTO,
    PlaneacionListDTO,
    PlaneacionResponseDTO,
    PlaneacionResultadoResumenDTO,
    PlaneacionSaveDTO,
)
from src.application.services.planeacion_formato_excel import (
    EXCEL_CONTENT_TYPE,
    OFFICIAL_FILE_NAME,
    FormatoPlaneacionMetadata,
    FormatoPlaneacionRow,
    PlaneacionFormatoExcelService,
    PlaneacionFormatoValidationError,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import (
    EstadoAprobacionPlaneacion,
    EstadoBloque,
    EstadoDocumentoOficial,
    EstadoEdicionRA,
    EstadoRevisionPlaneacion,
    TipoConocimiento,
    TipoResultadoProyecto,
)
from src.infrastructure.db.models.audit import EventoAuditoria
from src.infrastructure.db.models.curriculum import (
    Competencia,
    Conocimiento,
    CriterioEvaluacion,
    ProgramaFormacion,
    ResultadoAprendizaje,
)
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.organizacion import ProcesoCurricular
from src.infrastructure.db.models.planeacion import (
    PlaneacionDocumentoConfig,
    PlaneacionPedagogica,
)
from src.infrastructure.db.models.proyecto import (
    ActividadProyecto,
    AsignacionCurricularProyecto,
    FaseProyecto,
    ProyectoFormativo,
)
from src.infrastructure.repositories.planeacion import PlaneacionPedagogicaRepository
from src.infrastructure.storage.document_storage import sanitize_directory_name

_SEGMENT_MAX_LENGTH = 80


class PlaneacionAccessError(Exception):
    """Raised when planning is requested before project completion."""


class OfficialDocumentGenerationError(Exception):
    """Raised when building the official Excel workbook fails."""

    code: str = "OFFICIAL_DOCUMENT_GENERATION_ERROR"
    default_message: str = (
        "No fue posible generar el formato oficial de la planeación. "
        "Verifica la información e inténtalo nuevamente."
    )

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
    ) -> None:
        self.code = code or self.code
        self.message = message or self.default_message
        super().__init__(self.message)


class OfficialDocumentStorageError(Exception):
    """Raised when storing the official Excel workbook in MinIO fails."""

    code: str = "OFFICIAL_DOCUMENT_STORAGE_ERROR"
    default_message: str = (
        "No fue posible almacenar el formato oficial en el repositorio documental. "
        "Intenta nuevamente."
    )

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
    ) -> None:
        self.code = code or self.code
        self.message = message or self.default_message
        super().__init__(self.message)


class LearningResultLockedError(Exception):
    """Raised when attempting to modify or delete an approved and locked Learning Result."""

    code: str = "LEARNING_RESULT_LOCKED"
    default_message: str = (
        "Este resultado de aprendizaje se encuentra aprobado y bloqueado para edición."
    )

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        learning_result_id: uuid.UUID | None = None,
    ) -> None:
        self.code = code or self.code
        self.message = message or self.default_message
        self.learning_result_id = learning_result_id
        super().__init__(self.message)



class DocumentStorageProtocol(Protocol):
    """Storage protocol for saving pedagogical planning documents."""

    async def save_excel(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        original_filename: str,
    ) -> object:
        """Upload an official Excel workbook to the store."""

    async def read_excel(self, *, key: str) -> bytes:
        """Read an official Excel workbook from the store."""

    async def delete_by_prefix(self, *, prefix: str) -> None:
        """Remove stored artifacts under the given prefix."""


class PlaneacionPedagogicaService:
    """Orchestrate CRUD, state transitions, and file generations
    for integrated Pedagogical Planning.
    """

    def __init__(
        self,
        session: AsyncSession,
        repository: PlaneacionPedagogicaRepository,
        storage_service: DocumentStorageProtocol,
        formato_excel_service: PlaneacionFormatoExcelService | None = None,
    ) -> None:
        """Initialize the service with database session, repo, and storage client."""
        self._session = session
        self._repository = repository
        self._storage_service = storage_service
        self._formato_excel_service = (
            formato_excel_service or PlaneacionFormatoExcelService()
        )

    async def obtener_contexto(self, referencia_id: uuid.UUID) -> PlaneacionContextoDTO:
        """Verify program/project status and build the navigable curricular tree.

        The tree is derived entirely from PostgreSQL:
        fase -> actividad -> competencias -> resultados, using the
        AsignacionCurricularProyecto rows materialized from the project
        matrix. No draft JSON is used as source of truth.
        """
        programa_id = await self._resolve_programa_id(referencia_id)

        programa_stmt = (
            select(ProgramaFormacion)
            .where(ProgramaFormacion.id == programa_id)
            .options(
                selectinload(ProgramaFormacion.competencias).selectinload(
                    Competencia.conocimientos
                ),
                selectinload(ProgramaFormacion.competencias).selectinload(
                    Competencia.criterios
                ),
            )
            .execution_options(populate_existing=True)
        )
        programa_res = await self._session.execute(programa_stmt)
        programa = programa_res.scalar_one_or_none()
        if programa is None:
            raise ValueError(
                f"No se encontró el ProgramaFormacion {programa_id} en base de datos"
            )
        if programa.estado != EstadoBloque.COMPLETO:
            raise PlaneacionAccessError(
                "La planeacion pedagogica requiere el programa en estado COMPLETO"
            )

        proyecto = await self._get_project_for_program(programa_id)
        if proyecto.estado != EstadoBloque.COMPLETO:
            raise PlaneacionAccessError(
                "La planeacion pedagogica requiere el proyecto formativo "
                "en estado COMPLETO"
            )

        competencias_by_id = {c.id: c for c in programa.competencias}
        asignaciones_by_actividad = await self._load_asignaciones(proyecto.id)

        fase_dtos: list[ContextoFaseDTO] = []
        ordered_fases = sorted(
            proyecto.fases,
            key=lambda f: (f.orden is None, f.orden or 0, f.nombre_fase),
        )
        for fase in ordered_fases:
            ordered_actividades = sorted(
                fase.actividades,
                key=lambda a: (a.orden is None, a.orden or 0, a.descripcion),
            )
            actividad_dtos = [
                self._actividad_contexto(
                    actividad,
                    asignaciones_by_actividad.get(actividad.id, []),
                    competencias_by_id,
                )
                for actividad in ordered_actividades
            ]
            fase_dtos.append(
                ContextoFaseDTO(
                    id=fase.id,
                    nombre_fase=fase.nombre_fase,
                    orden=fase.orden,
                    actividades=actividad_dtos,
                )
            )

        return PlaneacionContextoDTO(
            programa_id=programa.id,
            codigo_programa=programa.codigo_programa,
            nombre_programa=programa.nombre_programa,
            version_programa=programa.version_programa,
            proyecto_id=proyecto.id,
            codigo_proyecto=proyecto.codigo_proyecto,
            nombre_proyecto=proyecto.nombre_proyecto,
            version_proyecto=proyecto.version_proyecto,
            fases=fase_dtos,
        )

    def _actividad_contexto(
        self,
        actividad: ActividadProyecto,
        asignaciones: list[AsignacionCurricularProyecto],
        competencias_by_id: dict[uuid.UUID, Competencia],
    ) -> ContextoActividadDTO:
        """Build the competency/RAP context of one project activity."""
        grupos: dict[uuid.UUID, list[ContextoResultadoDTO]] = {}
        seen_resultados: set[tuple[uuid.UUID, uuid.UUID]] = set()
        for asignacion in sorted(
            asignaciones,
            key=lambda item: (item.orden_resultado is None, item.orden_resultado or 0),
        ):
            competencia = competencias_by_id.get(asignacion.competencia_id)
            if competencia is None:
                continue
            if asignacion.resultado is None:
                grupos.setdefault(competencia.id, [])
                continue
            pair = (competencia.id, asignacion.resultado.id)
            if pair in seen_resultados:
                continue
            seen_resultados.add(pair)
            res_obj = asignacion.resultado
            grupos.setdefault(competencia.id, []).append(
                ContextoResultadoDTO(
                    id=res_obj.id,
                    codigo_resultado=res_obj.codigo_resultado,
                    descripcion=res_obj.descripcion,
                    tipo_resultado=(
                        TipoResultadoProyecto(asignacion.tipo_resultado)
                        if asignacion.tipo_resultado is not None
                        else None
                    ),
                    orden_resultado=asignacion.orden_resultado,
                    edit_status=(
                        res_obj.edit_status.value
                        if hasattr(getattr(res_obj, "edit_status", None), "value")
                        else str(getattr(res_obj, "edit_status", None) or "EDITABLE")
                    ),
                    locked_at=getattr(res_obj, "locked_at", None),
                    locked_by=getattr(res_obj, "locked_by", None),
                    unlocked_at=getattr(res_obj, "unlocked_at", None),
                    unlocked_by=getattr(res_obj, "unlocked_by", None),
                    unlock_request_id=getattr(res_obj, "unlock_request_id", None),
                    approved_version=int(getattr(res_obj, "approved_version", 0) or 0),
                    approved_at=getattr(res_obj, "approved_at", None),
                )
            )

        def _competencia_order(item: tuple[uuid.UUID, list[ContextoResultadoDTO]]) -> (
            tuple[bool, int, str]
        ):
            competencia = competencias_by_id.get(item[0])
            return (
                competencia.orden is None if competencia else True,
                (competencia.orden or 0) if competencia else 0,
                competencia.codigo_competencia if competencia else "",
            )

        competencia_dtos: list[ContextoCompetenciaDTO] = []
        for competencia_id, resultados in sorted(
            grupos.items(), key=_competencia_order
        ):
            competencia = competencias_by_id.get(competencia_id)
            if competencia is None:
                continue
            competencia_dtos.append(
                ContextoCompetenciaDTO(
                    id=competencia.id,
                    codigo_competencia=competencia.codigo_competencia,
                    nombre_competencia=competencia.nombre_competencia,
                    resultados=resultados,
                    conocimientos_saber=[
                        ContextoConocimientoDTO(id=k.id, descripcion=k.descripcion)
                        for k in competencia.conocimientos
                        if k.tipo == TipoConocimiento.SABER
                    ],
                    conocimientos_proceso=[
                        ContextoConocimientoDTO(id=k.id, descripcion=k.descripcion)
                        for k in competencia.conocimientos
                        if k.tipo == TipoConocimiento.PROCESO
                    ],
                    criterios=[
                        ContextoCriterioDTO(id=cr.id, descripcion=cr.descripcion)
                        for cr in competencia.criterios
                    ],
                )
            )
        return ContextoActividadDTO(
            id=actividad.id,
            descripcion=actividad.descripcion,
            orden=actividad.orden,
            competencias=competencia_dtos,
        )

    async def listar_planeaciones(
        self, proyecto_id: uuid.UUID
    ) -> list[PlaneacionListDTO]:
        """List integrated planning summaries for a project."""
        entities = await self._repository.list_by_proyecto(proyecto_id)
        tipo_by_pair = await self._load_tipos_resultado(proyecto_id)
        dtos: list[PlaneacionListDTO] = []
        for entity in entities:
            tipos: list[str] = []
            comp_map: dict[uuid.UUID, tuple[str, int]] = {}
            for resultado in entity.resultados:
                c_id = resultado.competencia_id
                competencia_obj = getattr(resultado, "competencia", None)
                c_code = (
                    competencia_obj.codigo_competencia
                    if competencia_obj is not None
                    else ""
                )
                existing_comp = comp_map.get(c_id, (c_code, 0))
                comp_map[c_id] = (c_code, existing_comp[1] + 1)

                tipo = tipo_by_pair.get((entity.actividad_id, resultado.id))
                if tipo:
                    tipos.append(tipo.strip().upper())
            datos = entity.datos_complementarios
            actividades_aprendizaje = datos.get("actividades_aprendizaje")
            competencias_list = [
                PlaneacionListCompetenciaDTO(
                    competencia_id=c_id,
                    codigo_competencia=c_code,
                    resultados_count=count,
                )
                for c_id, (c_code, count) in comp_map.items()
            ]
            rev_status = getattr(entity, "review_status", None)
            app_status = getattr(entity, "approval_status", None)
            ed_status = getattr(entity, "edit_status", None)
            dtos.append(
                PlaneacionListDTO(
                    id=entity.id,
                    proyecto_id=entity.proyecto_id,
                    fase_id=entity.fase_id,
                    actividad_id=entity.actividad_id,
                    nombre_fase=entity.fase.nombre_fase if entity.fase else None,
                    descripcion_actividad=(
                        entity.actividad.descripcion if entity.actividad else None
                    ),
                    actividades_aprendizaje=(
                        actividades_aprendizaje
                        if isinstance(actividades_aprendizaje, str)
                        else None
                    ),
                    estado=entity.estado.value,
                    review_status=(
                        rev_status.value if hasattr(rev_status, "value") else str(rev_status or "DRAFT")
                    ),
                    approval_status=(
                        app_status.value if hasattr(app_status, "value") else str(app_status or "PENDING")
                    ),
                    edit_status=(
                        ed_status.value if hasattr(ed_status, "value") else str(ed_status or "EDITABLE")
                    ),
                    official_document_status=self._resolve_official_document_status(entity),
                    competencias=competencias_list,
                    competencias_count=len(comp_map),
                    resultados_count=len(entity.resultados),
                    resultados_especificos=sum(
                        1 for tipo in tipos if tipo == "ESPECIFICO"
                    ),
                    resultados_transversales=sum(
                        1 for tipo in tipos if tipo == "TRANSVERSAL"
                    ),
                    fecha_actualizacion=entity.fecha_actualizacion,
                )
            )
        return dtos

    async def obtener_detalle(
        self, planeacion_id: uuid.UUID
    ) -> PlaneacionResponseDTO | None:
        """Get the full details of a single pedagogical planning record."""
        entity = await self._repository.get_by_id(planeacion_id)
        if entity is None:
            return None
        return await self._map_to_response_dto(entity)

    async def guardar_borrador(
        self,
        dto: PlaneacionSaveDTO,
        actor_id: uuid.UUID | None = None,
    ) -> PlaneacionResponseDTO:
        """Create or update an integrated pedagogical planning draft.

        The backend never trusts the frontend: every curricular membership
        (fase -> actividad -> competencia -> resultado) is re-verified here.
        Locked learning results cannot be modified or removed without an approved
        PlanningEditRequest.
        """
        existing_entity: PlaneacionPedagogica | None = None
        if dto.planeacion_id is not None:
            existing_entity = await self._repository.get_by_id(dto.planeacion_id)
            if existing_entity is None:
                raise ValueError(
                    f"No existe la planeación pedagógica con id {dto.planeacion_id}"
                )
            if existing_entity.proyecto_id != dto.proyecto_id:
                raise ValueError(
                    "La planeación no pertenece al proyecto formativo indicado"
                )
            self._assert_planning_has_editable_ra(existing_entity)

        await self._ensure_project_complete(dto.proyecto_id)

        proyecto = await self._session.get(ProyectoFormativo, dto.proyecto_id)
        assert proyecto is not None

        fase = await self._session.get(FaseProyecto, dto.fase_id)
        if fase is None or fase.proyecto_id != dto.proyecto_id:
            raise ValueError(
                "La fase seleccionada no pertenece al proyecto formativo"
            )
        actividad = await self._session.get(ActividadProyecto, dto.actividad_id)
        if actividad is None or actividad.fase_id != dto.fase_id:
            raise ValueError(
                "La actividad seleccionada no pertenece a la fase indicada"
            )

        asignaciones = await self._load_asignaciones_for_actividad(dto.actividad_id)
        resultado_ids_validos = {
            asignacion.resultado_id
            for asignacion in asignaciones
            if asignacion.resultado_id is not None
        }
        programas_por_resultado = {
            asignacion.resultado_id: asignacion.competencia.programa_id
            for asignacion in asignaciones
            if asignacion.resultado_id is not None
        }

        selected_resultado_ids = list(dict.fromkeys(dto.resultados_ids))
        if not selected_resultado_ids:
            raise ValueError(
                "Selecciona al menos un resultado de aprendizaje para la "
                "actividad de aprendizaje"
            )
        for resultado_id in selected_resultado_ids:
            if resultado_id not in resultado_ids_validos:
                raise ValueError(
                    "Uno de los resultados seleccionados no esta asociado a "
                    "la actividad de proyecto indicada"
                )
            if programas_por_resultado.get(resultado_id) != proyecto.programa_id:
                raise ValueError(
                    "Uno de los resultados seleccionados pertenece a otro "
                    "programa de formacion"
                )

        statement = select(ResultadoAprendizaje).where(
            ResultadoAprendizaje.id.in_(selected_resultado_ids)
        )
        result = await self._session.execute(statement)
        resultados = list(result.scalars().all())
        if len(resultados) != len(selected_resultado_ids):
            raise ValueError(
                "Uno de los resultados seleccionados no existe en el programa"
            )

        competencias_involucradas = {r.competencia_id for r in resultados}

        conocimientos: list[Conocimiento] = []
        if dto.conocimientos_ids:
            k_stmt = select(Conocimiento).where(
                Conocimiento.id.in_(dto.conocimientos_ids)
            )
            k_query = await self._session.execute(k_stmt)
            conocimientos = list(k_query.scalars().all())
        if len(conocimientos) != len(set(dto.conocimientos_ids)):
            raise ValueError(
                "Uno de los saberes seleccionados no existe en el programa"
            )
        for conocimiento in conocimientos:
            if conocimiento.competencia_id not in competencias_involucradas:
                raise ValueError(
                    "Hay saberes que no pertenecen a ninguna de las "
                    "competencias involucradas en la planeacion"
                )

        criterios: list[CriterioEvaluacion] = []
        if dto.criterios_ids:
            cr_stmt = select(CriterioEvaluacion).where(
                CriterioEvaluacion.id.in_(dto.criterios_ids)
            )
            cr_query = await self._session.execute(cr_stmt)
            criterios = list(cr_query.scalars().all())
        if len(criterios) != len(set(dto.criterios_ids)):
            raise ValueError(
                "Uno de los criterios seleccionados no existe en el programa"
            )
        for criterio in criterios:
            if criterio.competencia_id not in competencias_involucradas:
                raise ValueError(
                    "Hay criterios que no pertenecen a ninguna de las "
                    "competencias involucradas en la planeacion"
                )

        datos = dict(dto.datos_complementarios)
        datos.pop("asignaciones_proyecto", None)

        if existing_entity is not None:
            entity = existing_entity
            datos = await self._enforce_ra_locks_on_mutation(
                entity=entity,
                incoming_datos=datos,
                selected_resultados=resultados,
                actor_id=actor_id,
            )
            had_generated = bool(
                entity.storage_key
                or entity.fecha_generacion is not None
                or getattr(entity, "official_storage_key", None)
                or (getattr(entity, "version", 1) or 1) > 1
                or (
                    isinstance(entity.datos_complementarios, dict)
                    and entity.datos_complementarios.get("official_document_status")
                    in (EstadoDocumentoOficial.CURRENT.value, EstadoDocumentoOficial.OUTDATED.value)
                )
            )
            datos["official_document_status"] = (
                EstadoDocumentoOficial.OUTDATED.value
                if had_generated
                else EstadoDocumentoOficial.NOT_GENERATED.value
            )
        else:
            for r in resultados:
                r_status = getattr(r, "edit_status", None)
                r_status_str = r_status.value if hasattr(r_status, "value") else str(r_status or "EDITABLE")
                if r_status_str == EstadoEdicionRA.LOCKED.value:
                    raise LearningResultLockedError(learning_result_id=r.id)
            datos["official_document_status"] = EstadoDocumentoOficial.NOT_GENERATED.value
            entity = PlaneacionPedagogica(
                id=uuid.uuid4(),
                proyecto_id=dto.proyecto_id,
                fase_id=dto.fase_id,
                actividad_id=dto.actividad_id,
            )

        now = datetime.now(UTC)
        entity.fase_id = dto.fase_id
        entity.actividad_id = dto.actividad_id
        entity.estado = EstadoBloque.BORRADOR
        entity.datos_complementarios = datos
        entity.resultados = resultados
        entity.conocimientos = conocimientos
        entity.criterios = criterios
        entity.fecha_actualizacion = now

        await self._repository.save(entity)

        refetched = await self._repository.get_by_id(entity.id)
        if refetched is None:
            raise ValueError("Error al guardar y recuperar el borrador")
        return await self._map_to_response_dto(refetched)

    async def confirmar_y_generar(
        self,
        planeacion_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
    ) -> PlaneacionResponseDTO:
        """Complete one integrated planning and generate its official workbook."""
        entity = await self._repository.get_by_id(planeacion_id)
        if entity is None:
            raise ValueError(
                f"No existe la planeación pedagógica con id {planeacion_id}"
            )
        self._assert_planning_has_editable_ra(entity)
        await self._ensure_project_complete(entity.proyecto_id)
        gaps = await self._collect_gaps(entity, require_complete=False)
        if gaps:
            raise PlaneacionFormatoValidationError(
                [gap.mensaje for gap in gaps]
            )
        entity.estado = EstadoBloque.COMPLETO
        await self._generate_individual(entity, actor_id=actor_id)
        await self._repository.save(entity)
        return await self._map_to_response_dto(entity)

    async def obtener_configuracion_documento(
        self,
        proyecto_id: uuid.UUID,
    ) -> PlaneacionDocumentoConfigDTO:
        """Return shared official-format metadata for a project."""
        proyecto = await self._get_project_with_program(proyecto_id)
        config = await self._repository.get_document_config(proyecto_id)
        return self._map_config(proyecto, config)

    async def guardar_configuracion_documento(
        self,
        proyecto_id: uuid.UUID,
        dto: PlaneacionDocumentoConfigUpdateDTO,
    ) -> PlaneacionDocumentoConfigDTO:
        """Persist shared official-format metadata once per project."""
        proyecto = await self._get_project_with_program(proyecto_id)
        await self._ensure_project_complete(proyecto_id)
        config = await self._repository.get_document_config(proyecto_id)
        if config is None:
            config = PlaneacionDocumentoConfig(proyecto_id=proyecto_id)

        equipo = list(
            dict.fromkeys(
                member.strip()
                for member in dto.equipo_gestion_curricular
                if member.strip()
            )
        )
        if not equipo:
            raise ValueError("El equipo de gestion curricular es obligatorio")
        had_previous_config_doc = bool(
            config.storage_key
            or config.fecha_generacion is not None
            or getattr(config, "official_storage_key", None)
            or (getattr(config, "version", 1) or 1) > 1
        )
        proyecto.programa.modalidad_formacion = dto.modalidad_formacion.strip()
        config.fecha_elaboracion = dto.fecha_elaboracion
        config.clasificacion_informacion = dto.clasificacion_informacion
        config.equipo_gestion_curricular = equipo
        config.regional = dto.regional.strip()
        config.centro_formacion = dto.centro_formacion.strip()
        if had_previous_config_doc and (getattr(config, "version", 1) or 1) <= 1:
            config.version = 2
        config.storage_key = None
        config.file_name = None
        config.content_type = None
        config.checksum_sha256 = None
        config.fecha_generacion = None
        await self._repository.save_document_config(config)
        return self._map_config(proyecto, config)

    async def obtener_estado_formato_individual(
        self,
        planeacion_id: uuid.UUID,
    ) -> FormatoOficialEstadoDTO:
        """Return authoritative official-format gaps for one planning."""
        entity = await self._repository.get_by_id(planeacion_id)
        if entity is None:
            raise ValueError(f"No existe la planeacion pedagogica {planeacion_id}")
        gaps = await self._collect_gaps(entity, require_complete=False)
        doc_status = self._resolve_official_document_status(entity)
        return FormatoOficialEstadoDTO(
            listo=not gaps,
            official_document_status=doc_status,
            faltantes=gaps,
            planeaciones_completas=int(entity.estado == EstadoBloque.COMPLETO),
            borradores_excluidos=int(entity.estado != EstadoBloque.COMPLETO),
            storage_key=entity.storage_key,
            file_name=entity.file_name,
            checksum_sha256=entity.checksum_sha256,
            fecha_generacion=entity.fecha_generacion,
            version=entity.version or 1,
        )

    async def obtener_estado_formato_consolidado(
        self,
        proyecto_id: uuid.UUID,
    ) -> FormatoOficialEstadoDTO:
        """Return project counts, gaps, and last consolidated artifact."""
        entities = await self._repository.list_full_by_proyecto(proyecto_id)
        complete = [e for e in entities if e.estado == EstadoBloque.COMPLETO]
        draft_entities = [e for e in entities if e.estado != EstadoBloque.COMPLETO]
        drafts = len(draft_entities)
        config = await self._repository.get_document_config(proyecto_id)
        gaps: list[FormatoOficialFaltanteDTO] = []
        if not complete:
            ready_drafts = 0
            draft_gaps: list[FormatoOficialFaltanteDTO] = []
            for d_ent in draft_entities:
                d_g = await self._collect_gaps(d_ent, require_complete=False)
                if not d_g:
                    ready_drafts += 1
                else:
                    draft_gaps.extend(d_g)
            if ready_drafts == 0:
                if draft_gaps:
                    gaps.extend(draft_gaps)
                else:
                    gaps.append(
                        self._gap(
                            "SIN_PLANEACIONES_COMPLETAS",
                            "No existen planeaciones completas para exportar.",
                            "confirmacion",
                        )
                    )
        else:
            for entity in complete:
                gaps.extend(await self._collect_gaps(entity, require_complete=True))
            for d_ent in draft_entities:
                gaps.extend(await self._collect_gaps(d_ent, require_complete=False))
        gaps = self._unique_gaps(gaps)
        doc_status = self._resolve_consolidated_document_status(config, entities)
        has_valid_consolidated = bool((complete or draft_entities) and config and config.storage_key)
        return FormatoOficialEstadoDTO(
            listo=not gaps,
            official_document_status=doc_status,
            faltantes=gaps,
            planeaciones_completas=len(complete),
            borradores_excluidos=drafts,
            storage_key=config.storage_key if (config and has_valid_consolidated) else None,
            file_name=config.file_name if (config and has_valid_consolidated) else None,
            checksum_sha256=config.checksum_sha256 if (config and has_valid_consolidated) else None,
            fecha_generacion=config.fecha_generacion if (config and has_valid_consolidated) else None,
            version=(config.version or 1) if config else 1,
        )

    async def generar_formato_individual(
        self,
        planeacion_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
    ) -> FormatoOficialGeneradoDTO:
        """Regenerate the official workbook for a completed planning."""
        entity = await self._repository.get_by_id(planeacion_id)
        if entity is None:
            raise ValueError(f"No existe la planeacion pedagogica {planeacion_id}")
        self._assert_planning_has_editable_ra(entity)
        gaps = await self._collect_gaps(entity, require_complete=False)
        if gaps:
            raise PlaneacionFormatoValidationError(
                [gap.mensaje for gap in gaps]
            )
        entity.estado = EstadoBloque.COMPLETO
        generated = await self._generate_individual(entity, actor_id=actor_id)
        await self._repository.save(entity)
        return generated

    async def generar_formato_consolidado(
        self,
        proyecto_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
    ) -> FormatoOficialGeneradoDTO:
        """Generate and store all completed project planning rows."""
        await self._ensure_project_complete(proyecto_id)
        entities = await self._repository.list_full_by_proyecto(proyecto_id)

        # Automatically confirm any draft planning that has all required fields complete
        for entity in entities:
            if entity.estado != EstadoBloque.COMPLETO:
                draft_gaps = await self._collect_gaps(entity, require_complete=False)
                if not draft_gaps:
                    entity.estado = EstadoBloque.COMPLETO
                    await self._generate_individual(entity, actor_id=actor_id)
                    await self._repository.save(entity)

        complete = [e for e in entities if e.estado == EstadoBloque.COMPLETO]
        drafts = len(entities) - len(complete)
        if not complete:
            if entities:
                all_draft_gaps: list[FormatoOficialFaltanteDTO] = []
                for e in entities:
                    all_draft_gaps.extend(await self._collect_gaps(e, require_complete=False))
                if all_draft_gaps:
                    raise PlaneacionFormatoValidationError(
                        [gap.mensaje for gap in self._unique_gaps(all_draft_gaps)]
                    )
            raise PlaneacionFormatoValidationError(
                ["No existen planeaciones completas para exportar"]
            )
        gaps: list[FormatoOficialFaltanteDTO] = []
        for entity in complete:
            gaps.extend(await self._collect_gaps(entity, require_complete=True))
        if gaps:
            raise PlaneacionFormatoValidationError(
                [gap.mensaje for gap in self._unique_gaps(gaps)]
            )

        proyecto = complete[0].proyecto
        config = await self._require_config(proyecto.id)
        previous_version = (config.version or 1) if config else 1
        had_previous = bool(
            config.storage_key
            or config.fecha_generacion is not None
            or getattr(config, "official_storage_key", None)
            or previous_version > 1
        )
        programa_dir = sanitize_directory_name(proyecto.programa.nombre_programa)
        proyecto_dir = sanitize_directory_name(proyecto.nombre_proyecto)
        storage_key = (
            f"planeaciones-pedagogicas/{programa_dir}/{proyecto_dir}/"
            f"formato-oficial/{OFFICIAL_FILE_NAME}"
        )

        try:
            metadata = self._build_metadata(proyecto, config)
            rows = await self._build_rows(complete)
            result = self._formato_excel_service.generar(metadata=metadata, rows=rows)
        except PlaneacionFormatoValidationError as exc:
            await self._record_official_document_audit(
                accion="OFFICIAL_DOCUMENT_GENERATION_FAILED",
                entidad="ProyectoFormativo",
                entidad_id=proyecto.id,
                planning_id=complete[0].id if complete else None,
                proyecto_id=proyecto.id,
                programa_id=proyecto.programa_id,
                actor_id=actor_id,
                previous_version=previous_version,
                new_version=previous_version,
                document_path=storage_key,
                extra={"error_stage": "GENERATION", "reason": "; ".join(exc.messages)},
            )
            raise
        except Exception as exc:
            await self._record_official_document_audit(
                accion="OFFICIAL_DOCUMENT_GENERATION_FAILED",
                entidad="ProyectoFormativo",
                entidad_id=proyecto.id,
                planning_id=complete[0].id if complete else None,
                proyecto_id=proyecto.id,
                programa_id=proyecto.programa_id,
                actor_id=actor_id,
                previous_version=previous_version,
                new_version=previous_version,
                document_path=storage_key,
                extra={"error_stage": "GENERATION", "reason": str(exc)},
            )
            raise OfficialDocumentGenerationError() from exc

        try:
            await self._storage_service.save_excel(
                key=storage_key,
                content=result.content,
                content_type=EXCEL_CONTENT_TYPE,
                original_filename=OFFICIAL_FILE_NAME,
            )
        except Exception as exc:
            await self._record_official_document_audit(
                accion="OFFICIAL_DOCUMENT_GENERATION_FAILED",
                entidad="ProyectoFormativo",
                entidad_id=proyecto.id,
                planning_id=complete[0].id if complete else None,
                proyecto_id=proyecto.id,
                programa_id=proyecto.programa_id,
                actor_id=actor_id,
                previous_version=previous_version,
                new_version=previous_version,
                document_path=storage_key,
                extra={"error_stage": "STORAGE", "reason": str(exc)},
            )
            raise OfficialDocumentStorageError() from exc

        now = datetime.now(UTC)
        new_version = previous_version + 1 if had_previous else previous_version
        config.version = new_version
        config.storage_key = storage_key
        config.file_name = OFFICIAL_FILE_NAME
        config.content_type = EXCEL_CONTENT_TYPE
        config.checksum_sha256 = result.checksum_sha256
        config.fecha_generacion = now
        await self._repository.save_document_config(config)

        for entity in complete:
            datos = dict(entity.datos_complementarios) if isinstance(entity.datos_complementarios, dict) else {}
            datos["official_document_status"] = EstadoDocumentoOficial.CURRENT.value
            datos["official_document_generated_at"] = now.isoformat()
            entity.datos_complementarios = datos
            if not entity.storage_key:
                entity.storage_key = storage_key
            entity.fecha_generacion = now
            entity.fecha_actualizacion = now
            await self._repository.save(entity)

        await self._record_official_document_audit(
            accion="OFFICIAL_DOCUMENT_UPDATED" if had_previous else "OFFICIAL_DOCUMENT_GENERATED",
            entidad="ProyectoFormativo",
            entidad_id=proyecto.id,
            planning_id=complete[0].id if complete else None,
            proyecto_id=proyecto.id,
            programa_id=proyecto.programa_id,
            actor_id=actor_id,
            previous_version=previous_version,
            new_version=new_version,
            document_path=storage_key,
            extra={
                "planeaciones_incluidas": len(complete),
                "filas_generadas": result.filas_generadas,
            },
        )

        return FormatoOficialGeneradoDTO(
            storage_key=storage_key,
            file_name=OFFICIAL_FILE_NAME,
            content_type=EXCEL_CONTENT_TYPE,
            checksum_sha256=result.checksum_sha256,
            fecha_generacion=now,
            version=config.version,
            filas_generadas=result.filas_generadas,
            planeaciones_incluidas=len(complete),
            borradores_excluidos=drafts,
            official_document_status=EstadoDocumentoOficial.CURRENT.value,
        )

    async def descargar_formato_individual(
        self,
        planeacion_id: uuid.UUID,
    ) -> tuple[bytes, str]:
        """Read a previously generated individual workbook from MinIO.

        If the planning is currently in controlled reopening (PREVIOUS_VERSION_APPROVED),
        serve the preserved official_storage_key until the new version is approved.
        """
        entity = await self._repository.get_by_id(planeacion_id)
        if entity is None:
            raise ValueError(f"No existe la planeacion pedagogica {planeacion_id}")

        app_status = getattr(entity, "approval_status", None)
        app_status_str = (
            app_status.value if hasattr(app_status, "value") else str(app_status or "")
        )
        official_key = getattr(entity, "official_storage_key", None)
        if (
            app_status_str == EstadoAprobacionPlaneacion.PREVIOUS_VERSION_APPROVED.value
            and official_key
        ):
            content = await self._storage_service.read_excel(key=official_key)
            return content, getattr(entity, "official_file_name", None) or entity.file_name or OFFICIAL_FILE_NAME

        if (
            entity.estado != EstadoBloque.COMPLETO
            or not entity.storage_key
            or entity.content_type != EXCEL_CONTENT_TYPE
        ):
            if official_key:
                content = await self._storage_service.read_excel(key=official_key)
                return content, getattr(entity, "official_file_name", None) or entity.file_name or OFFICIAL_FILE_NAME
            raise FileNotFoundError("La planeacion no tiene un Excel oficial generado")
        content = await self._storage_service.read_excel(key=entity.storage_key)
        return content, entity.file_name or OFFICIAL_FILE_NAME

    async def descargar_formato_consolidado(
        self,
        proyecto_id: uuid.UUID,
    ) -> tuple[bytes, str]:
        """Read the latest consolidated project workbook from MinIO.

        If any planning in the project is in controlled reopening and an official
        consolidated workbook was previously approved, serve the preserved official key.
        """
        entities = await self._repository.list_full_by_proyecto(proyecto_id)
        complete = [e for e in entities if e.estado == EstadoBloque.COMPLETO]
        config = await self._repository.get_document_config(proyecto_id)
        official_key = getattr(config, "official_storage_key", None) if config else None
        has_reopened = any(
            (
                getattr(e, "approval_status", None) == EstadoAprobacionPlaneacion.PREVIOUS_VERSION_APPROVED
                or str(getattr(e, "approval_status", "")) == EstadoAprobacionPlaneacion.PREVIOUS_VERSION_APPROVED.value
            )
            for e in entities
        )
        if has_reopened and official_key and config is not None:
            content = await self._storage_service.read_excel(key=official_key)
            return content, getattr(config, "official_file_name", None) or config.file_name or OFFICIAL_FILE_NAME

        if (
            not complete
            or config is None
            or not config.storage_key
            or config.content_type != EXCEL_CONTENT_TYPE
        ):
            if official_key and config is not None:
                content = await self._storage_service.read_excel(key=official_key)
                return content, getattr(config, "official_file_name", None) or config.file_name or OFFICIAL_FILE_NAME
            if complete and config and config.fecha_elaboracion and config.regional and config.centro_formacion:
                await self.generar_formato_consolidado(proyecto_id)
                config = await self._repository.get_document_config(proyecto_id)
                if config and config.storage_key:
                    content = await self._storage_service.read_excel(key=config.storage_key)
                    return content, config.file_name or OFFICIAL_FILE_NAME
            raise FileNotFoundError(
                "No hay un archivo consolidado disponible para descargar porque la planeación fue eliminada o modificada. Debes volver a generar el formato consolidado."
            )
        content = await self._storage_service.read_excel(key=config.storage_key)
        return content, config.file_name or OFFICIAL_FILE_NAME

    async def eliminar_planeacion(
        self,
        planeacion_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
    ) -> None:
        """Remove the planning record from DB and its workbook from MinIO."""
        entity = await self._repository.get_by_id(planeacion_id)
        if entity is None:
            return

        self._assert_planning_can_be_deleted(entity)

        # Invalidate existing consolidated project workbook in MinIO and DB
        if entity.proyecto_id:
            config = await self._repository.get_document_config(entity.proyecto_id)
            if config and config.storage_key:
                try:
                    await self._storage_service.delete_by_prefix(prefix=config.storage_key)
                except Exception:
                    pass
                config.storage_key = None
                config.file_name = None
                config.checksum_sha256 = None
                config.fecha_generacion = None
                await self._repository.save_document_config(config)

        if entity.storage_key:
            await self._storage_service.delete_by_prefix(prefix=entity.storage_key)
            if "/" in entity.storage_key:
                folder_prefix = entity.storage_key.rsplit("/", 1)[0] + "/"
                await self._storage_service.delete_by_prefix(prefix=folder_prefix)

        if entity.proyecto and entity.fase and entity.actividad:
            try:
                calc_key = self._build_individual_storage_key(entity)
                await self._storage_service.delete_by_prefix(prefix=calc_key)
                if "/" in calc_key:
                    calc_folder = calc_key.rsplit("/", 1)[0] + "/"
                    await self._storage_service.delete_by_prefix(prefix=calc_folder)
            except Exception:
                pass

        await self._repository.delete(entity)

    # ------------------------------------------------------------------
    # Learning Result Locking & Controlled Reopening Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_ra_lock_metadata(
        entity: PlaneacionPedagogica | None,
        resultado: ResultadoAprendizaje,
    ) -> dict[str, object]:
        """Resolve authoritative lock metadata for a Learning Result inside a planning."""
        ra_locks: dict[str, object] = {}
        if entity is not None and isinstance(entity.datos_complementarios, dict):
            raw_locks = entity.datos_complementarios.get("ra_locks")
            if isinstance(raw_locks, dict):
                entry = raw_locks.get(str(resultado.id))
                if isinstance(entry, dict):
                    ra_locks = dict(entry)

        res_status_attr = getattr(resultado, "edit_status", None)
        res_status_str = (
            res_status_attr.value
            if hasattr(res_status_attr, "value")
            else str(res_status_attr or "")
        )
        lock_dict_status = str(ra_locks.get("edit_status") or "")
        entity_status_attr = getattr(entity, "edit_status", None) if entity else None
        entity_status_str = (
            entity_status_attr.value
            if hasattr(entity_status_attr, "value")
            else str(entity_status_attr or "")
        )

        unlock_req = getattr(resultado, "unlock_request_id", None) or ra_locks.get("unlock_request_id")

        if res_status_str == EstadoEdicionRA.LOCKED.value:
            effective_status = EstadoEdicionRA.LOCKED.value
        elif res_status_str == EstadoEdicionRA.EDITABLE.value and unlock_req is not None:
            effective_status = EstadoEdicionRA.EDITABLE.value
        elif lock_dict_status in (EstadoEdicionRA.LOCKED.value, EstadoEdicionRA.EDITABLE.value):
            effective_status = lock_dict_status
        elif entity_status_str == EstadoEdicionRA.LOCKED.value:
            effective_status = EstadoEdicionRA.LOCKED.value
        else:
            effective_status = EstadoEdicionRA.EDITABLE.value

        def _parse_uuid(val: object) -> uuid.UUID | None:
            if isinstance(val, uuid.UUID):
                return val
            if isinstance(val, str) and val.strip():
                try:
                    return uuid.UUID(val.strip())
                except ValueError:
                    return None
            return None

        def _parse_dt(val: object) -> datetime | None:
            if isinstance(val, datetime):
                return val
            if isinstance(val, str) and val.strip():
                try:
                    return datetime.fromisoformat(val.strip())
                except ValueError:
                    return None
            return None

        return {
            "edit_status": effective_status,
            "locked_at": getattr(resultado, "locked_at", None) or _parse_dt(ra_locks.get("locked_at")),
            "locked_by": getattr(resultado, "locked_by", None) or _parse_uuid(ra_locks.get("locked_by")),
            "unlocked_at": getattr(resultado, "unlocked_at", None) or _parse_dt(ra_locks.get("unlocked_at")),
            "unlocked_by": getattr(resultado, "unlocked_by", None) or _parse_uuid(ra_locks.get("unlocked_by")),
            "unlock_request_id": _parse_uuid(unlock_req),
            "approved_version": int(
                getattr(resultado, "approved_version", 0)
                or ra_locks.get("approved_version")  # type: ignore[arg-type]
                or 0
            ),
            "approved_at": getattr(resultado, "approved_at", None) or _parse_dt(ra_locks.get("approved_at")),
        }

    def _assert_planning_has_editable_ra(self, entity: PlaneacionPedagogica) -> None:
        """Raise LearningResultLockedError if all RAs in the planning are LOCKED."""
        entity_ed = getattr(entity, "edit_status", None)
        entity_ed_str = entity_ed.value if hasattr(entity_ed, "value") else str(entity_ed or "EDITABLE")
        if not entity.resultados:
            if entity_ed_str == EstadoEdicionRA.LOCKED.value:
                raise LearningResultLockedError()
            return

        statuses = [
            self._resolve_ra_lock_metadata(entity, r)["edit_status"]
            for r in entity.resultados
        ]
        if all(s == EstadoEdicionRA.LOCKED.value for s in statuses):
            raise LearningResultLockedError(learning_result_id=entity.resultados[0].id)

    def _assert_planning_can_be_deleted(self, entity: PlaneacionPedagogica) -> None:
        """Raise LearningResultLockedError if the planning or any of its RAs is LOCKED."""
        entity_ed = getattr(entity, "edit_status", None)
        entity_ed_str = entity_ed.value if hasattr(entity_ed, "value") else str(entity_ed or "EDITABLE")
        if entity_ed_str == EstadoEdicionRA.LOCKED.value:
            raise LearningResultLockedError()
        for r in entity.resultados:
            meta = self._resolve_ra_lock_metadata(entity, r)
            if meta["edit_status"] == EstadoEdicionRA.LOCKED.value:
                raise LearningResultLockedError(learning_result_id=r.id)

    async def _enforce_ra_locks_on_mutation(
        self,
        *,
        entity: PlaneacionPedagogica,
        incoming_datos: dict[str, object],
        selected_resultados: list[ResultadoAprendizaje],
        actor_id: uuid.UUID | None = None,
    ) -> dict[str, object]:
        """Validate that locked RAs are not removed or modified during draft save."""
        existing_resultados = list(entity.resultados or [])
        locked_ras: list[ResultadoAprendizaje] = []
        editable_ras: list[ResultadoAprendizaje] = []

        for r in existing_resultados:
            meta = self._resolve_ra_lock_metadata(entity, r)
            if meta["edit_status"] == EstadoEdicionRA.LOCKED.value:
                locked_ras.append(r)
            else:
                editable_ras.append(r)

        entity_ed = getattr(entity, "edit_status", None)
        entity_ed_str = entity_ed.value if hasattr(entity_ed, "value") else str(entity_ed or "EDITABLE")

        # If all existing RAs are locked (or entity itself is locked with no unlocked RA)
        if (locked_ras and not editable_ras) or (
            entity_ed_str == EstadoEdicionRA.LOCKED.value and not editable_ras
        ):
            first_locked_id = locked_ras[0].id if locked_ras else None
            raise LearningResultLockedError(learning_result_id=first_locked_id)

        selected_ids = {r.id for r in selected_resultados}
        existing_ids = {r.id for r in existing_resultados}

        # Check newly added RAs are not locked
        for r in selected_resultados:
            if r.id not in existing_ids:
                meta = self._resolve_ra_lock_metadata(entity, r)
                if meta["edit_status"] == EstadoEdicionRA.LOCKED.value:
                    raise LearningResultLockedError(learning_result_id=r.id)

        # In partial reopening (some RAs locked, some editable):
        if locked_ras:
            # 1. Locked RAs cannot be removed from the planning
            for locked_ra in locked_ras:
                if locked_ra.id not in selected_ids:
                    raise LearningResultLockedError(learning_result_id=locked_ra.id)

            # 2. Didactic data of locked RAs cannot be modified
            old_datos = entity.datos_complementarios if isinstance(entity.datos_complementarios, dict) else {}

            didactic_keys = (
                "actividades_aprendizaje",
                "estrategias_didacticas",
                "descripcion_evidencia_aprendizaje",
                "horas_trabajo_directo",
                "horas_trabajo_independiente",
                "duracion_actividad_horas",
                "ambiente",
                "ambientes",
                "materiales",
                "materiales_formacion",
                "instructores",
                "instructor_responsable",
                "observaciones",
            )

            for map_key in ("raps", "rap_complementary_map"):
                old_raps = old_datos.get(map_key) if isinstance(old_datos.get(map_key), dict) else {}
                new_raps = incoming_datos.get(map_key) if isinstance(incoming_datos.get(map_key), dict) else {}
                if not old_raps and not new_raps:
                    continue

                merged_raps: dict[str, object] = dict(new_raps) if isinstance(new_raps, dict) else {}
                for locked_ra in locked_ras:
                    ra_key = str(locked_ra.id)
                    old_rap_data = old_raps.get(ra_key) if isinstance(old_raps, dict) else None
                    new_rap_data = new_raps.get(ra_key) if isinstance(new_raps, dict) else None

                    if isinstance(old_rap_data, dict) and isinstance(new_rap_data, dict):
                        for k in didactic_keys:
                            if k in new_rap_data and k in old_rap_data:
                                old_val = str(old_rap_data.get(k) or "").strip()
                                new_val = str(new_rap_data.get(k) or "").strip()
                                if old_val != new_val:
                                    raise LearningResultLockedError(learning_result_id=locked_ra.id)
                        merged_raps[ra_key] = dict(old_rap_data)
                    elif isinstance(old_rap_data, dict) and new_rap_data is None:
                        merged_raps[ra_key] = dict(old_rap_data)

                if merged_raps:
                    incoming_datos[map_key] = merged_raps

        # Preserve ra_locks in datos_complementarios
        if isinstance(entity.datos_complementarios, dict) and "ra_locks" in entity.datos_complementarios:
            incoming_datos["ra_locks"] = entity.datos_complementarios["ra_locks"]

        # Record audit event LEARNING_RESULT_MODIFIED when editing reopened RAs
        reopened_ras = [
            r for r in editable_ras
            if self._resolve_ra_lock_metadata(entity, r).get("unlock_request_id") is not None
            or str(getattr(entity, "review_status", "")) in (
                EstadoRevisionPlaneacion.CHANGES_ALLOWED.value,
                "EstadoRevisionPlaneacion.CHANGES_ALLOWED",
            )
        ]
        if reopened_ras and hasattr(self._session, "add"):
            for r in reopened_ras:
                meta = self._resolve_ra_lock_metadata(entity, r)
                self._session.add(
                    EventoAuditoria(
                        entidad="ResultadoAprendizaje",
                        entidad_id=r.id,
                        accion="LEARNING_RESULT_MODIFIED",
                        actor_usuario_id=actor_id,
                        detalle={
                            "planning_id": str(entity.id),
                            "learning_result_id": str(r.id),
                            "codigo_resultado": r.codigo_resultado,
                            "unlock_request_id": str(meta["unlock_request_id"]) if meta.get("unlock_request_id") else None,
                            "actor_id": str(actor_id) if actor_id else None,
                        },
                    )
                )

        return incoming_datos

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _resolve_programa_id(self, referencia_id: uuid.UUID) -> uuid.UUID:
        proc_stmt = select(ProcesoCurricular).where(
            ProcesoCurricular.referencia_id == referencia_id
        )
        proc_res = await self._session.execute(proc_stmt)
        proc = proc_res.scalar_one_or_none()
        if proc and proc.programa_id:
            return proc.programa_id

        draft_stmt = select(BorradorSesion).where(
            BorradorSesion.referencia_id == referencia_id,
            BorradorSesion.tipo_bloque == TipoBloqueBorrador.PROGRAMA,
        )
        draft_res = await self._session.execute(draft_stmt)
        draft_prog = draft_res.scalar_one_or_none()
        if draft_prog is None:
            raise ValueError(
                f"No existe sesión de borrador para la referencia {referencia_id}"
            )
        curr = draft_prog.payload_json.get("curricular")
        programa_id: uuid.UUID | None = None
        if isinstance(curr, dict):
            raw_id = curr.get("programa_formacion_id")
            if raw_id:
                programa_id = uuid.UUID(str(raw_id))
        if programa_id is None:
            raise ValueError(
                "El programa de formación no ha sido importado/materializado "
                "en la sesión"
            )
        return programa_id

    async def _get_project_for_program(
        self, programa_id: uuid.UUID
    ) -> ProyectoFormativo:
        proj_stmt = (
            select(ProyectoFormativo)
            .where(ProyectoFormativo.programa_id == programa_id)
            .options(
                selectinload(ProyectoFormativo.fases).selectinload(
                    FaseProyecto.actividades
                )
            )
            .execution_options(populate_existing=True)
        )
        proj_res = await self._session.execute(proj_stmt)
        proyecto = proj_res.scalar_one_or_none()
        if proyecto is None:
            raise ValueError(
                "No se ha importado el proyecto formativo para este programa"
            )
        return proyecto

    async def _load_asignaciones(
        self, proyecto_id: uuid.UUID
    ) -> dict[uuid.UUID, list[AsignacionCurricularProyecto]]:
        statement = (
            select(AsignacionCurricularProyecto)
            .where(AsignacionCurricularProyecto.proyecto_id == proyecto_id)
            .options(
                selectinload(AsignacionCurricularProyecto.competencia),
                selectinload(AsignacionCurricularProyecto.resultado),
            )
        )
        result = await self._session.execute(statement)
        asignaciones = list(result.scalars().unique().all())
        grouped: dict[uuid.UUID, list[AsignacionCurricularProyecto]] = {}
        for asignacion in asignaciones:
            grouped.setdefault(asignacion.actividad_proyecto_id, []).append(
                asignacion
            )
        return grouped

    async def _load_asignaciones_for_actividad(
        self, actividad_id: uuid.UUID
    ) -> list[AsignacionCurricularProyecto]:
        statement = (
            select(AsignacionCurricularProyecto)
            .where(AsignacionCurricularProyecto.actividad_proyecto_id == actividad_id)
            .options(
                selectinload(AsignacionCurricularProyecto.competencia),
                selectinload(AsignacionCurricularProyecto.resultado),
            )
        )
        result = await self._session.execute(statement)
        return list(result.scalars().unique().all())

    async def _load_tipos_resultado(
        self, proyecto_id: uuid.UUID
    ) -> dict[tuple[uuid.UUID | None, uuid.UUID | None], str | None]:
        statement = select(AsignacionCurricularProyecto).where(
            AsignacionCurricularProyecto.proyecto_id == proyecto_id
        )
        result = await self._session.execute(statement)
        return {
            (asignacion.actividad_proyecto_id, asignacion.resultado_id): (
                asignacion.tipo_resultado
            )
            for asignacion in result.scalars().all()
            if asignacion.resultado_id is not None
        }

    async def _generate_individual(
        self,
        entity: PlaneacionPedagogica,
        actor_id: uuid.UUID | None = None,
    ) -> FormatoOficialGeneradoDTO:
        had_previous = bool(entity.storage_key)
        previous_version = entity.version if had_previous else None
        config = await self._require_config(entity.proyecto_id)
        metadata = self._build_metadata(entity.proyecto, config)
        try:
            rows = await self._build_rows([entity])
            result = self._formato_excel_service.generar(metadata=metadata, rows=rows)
        except Exception as exc:
            await self._record_official_document_audit(
                event_type="OFFICIAL_DOCUMENT_GENERATION_FAILED",
                proyecto=entity.proyecto,
                planning_id=entity.id,
                actor_id=actor_id,
                previous_version=previous_version,
                new_version=None,
                document_path=None,
                error_detail="Error durante la construcción del formato oficial individual.",
            )
            raise OfficialDocumentGenerationError() from exc

        storage_key = self._build_individual_storage_key(entity)
        file_name = "GPFI-F-134V05-planeacion.xlsx"
        try:
            await self._storage_service.save_excel(
                key=storage_key,
                content=result.content,
                content_type=EXCEL_CONTENT_TYPE,
                original_filename=file_name,
            )
        except Exception as exc:
            await self._record_official_document_audit(
                event_type="OFFICIAL_DOCUMENT_GENERATION_FAILED",
                proyecto=entity.proyecto,
                planning_id=entity.id,
                actor_id=actor_id,
                previous_version=previous_version,
                new_version=None,
                document_path=storage_key,
                error_detail="Error almacenando el formato oficial individual en el repositorio documental.",
            )
            raise OfficialDocumentStorageError() from exc

        now = datetime.now(UTC)
        entity.version = entity.version + 1 if had_previous else (entity.version or 1)
        entity.storage_key = storage_key
        entity.file_name = file_name
        entity.content_type = EXCEL_CONTENT_TYPE
        entity.checksum_sha256 = result.checksum_sha256
        entity.fecha_generacion = now
        entity.fecha_actualizacion = now
        datos = dict(entity.datos_complementarios or {})
        datos["official_document_status"] = EstadoDocumentoOficial.CURRENT.value
        datos["official_document_generated_at"] = now.isoformat()
        entity.datos_complementarios = datos

        await self._record_official_document_audit(
            event_type=(
                "OFFICIAL_DOCUMENT_UPDATED"
                if had_previous
                else "OFFICIAL_DOCUMENT_GENERATED"
            ),
            proyecto=entity.proyecto,
            planning_id=entity.id,
            actor_id=actor_id,
            previous_version=previous_version,
            new_version=entity.version,
            document_path=storage_key,
        )
        return FormatoOficialGeneradoDTO(
            storage_key=storage_key,
            file_name=file_name,
            content_type=EXCEL_CONTENT_TYPE,
            checksum_sha256=result.checksum_sha256,
            fecha_generacion=now,
            version=entity.version,
            filas_generadas=result.filas_generadas,
            planeaciones_incluidas=1,
            official_document_status=EstadoDocumentoOficial.CURRENT.value,
        )

    @staticmethod
    def _resolve_official_document_status(entity: PlaneacionPedagogica) -> str:
        """Determine whether an individual planning's official document is CURRENT, OUTDATED, or NOT_GENERATED."""
        datos = entity.datos_complementarios or {}
        explicit_status = datos.get("official_document_status")
        if explicit_status == EstadoDocumentoOficial.OUTDATED.value:
            return EstadoDocumentoOficial.OUTDATED.value
        if not entity.storage_key:
            if (
                getattr(entity, "fecha_generacion", None) is not None
                or getattr(entity, "official_storage_key", None)
                or (getattr(entity, "version", 1) or 1) > 1
            ):
                return EstadoDocumentoOficial.OUTDATED.value
            return EstadoDocumentoOficial.NOT_GENERATED.value
        if entity.estado == EstadoBloque.BORRADOR:
            return EstadoDocumentoOficial.OUTDATED.value
        updated_at = getattr(entity, "fecha_actualizacion", None)
        generated_at = getattr(entity, "fecha_generacion", None)
        if (
            updated_at is not None
            and generated_at is not None
            and updated_at > generated_at
        ):
            return EstadoDocumentoOficial.OUTDATED.value
        return EstadoDocumentoOficial.CURRENT.value

    @classmethod
    def _resolve_consolidated_document_status(
        cls,
        config: PlaneacionDocumentoConfig | None,
        entities: Sequence[PlaneacionPedagogica],
    ) -> str:
        """Determine whether the project's consolidated official document is CURRENT, OUTDATED, or NOT_GENERATED."""
        if not entities:
            return EstadoDocumentoOficial.NOT_GENERATED.value
        if config is None:
            return EstadoDocumentoOficial.NOT_GENERATED.value
        if not config.storage_key:
            if (
                getattr(config, "fecha_generacion", None) is not None
                or getattr(config, "official_storage_key", None)
                or (getattr(config, "version", 1) or 1) > 1
                or any(
                    cls._resolve_official_document_status(e)
                    == EstadoDocumentoOficial.OUTDATED.value
                    for e in entities
                )
            ):
                return EstadoDocumentoOficial.OUTDATED.value
            return EstadoDocumentoOficial.NOT_GENERATED.value
        config_generated_at = getattr(config, "fecha_generacion", None)
        config_updated_at = getattr(config, "fecha_actualizacion", None)
        if (
            config_updated_at is not None
            and config_generated_at is not None
            and config_updated_at > config_generated_at
        ):
            return EstadoDocumentoOficial.OUTDATED.value
        for entity in entities:
            if entity.estado == EstadoBloque.BORRADOR:
                return EstadoDocumentoOficial.OUTDATED.value
            datos = entity.datos_complementarios or {}
            if datos.get("official_document_status") == EstadoDocumentoOficial.OUTDATED.value:
                return EstadoDocumentoOficial.OUTDATED.value
            entity_updated = getattr(entity, "fecha_actualizacion", None)
            entity_generated = getattr(entity, "fecha_generacion", None)
            if (
                entity_updated is not None
                and entity_generated is not None
                and entity_updated > entity_generated
            ):
                return EstadoDocumentoOficial.OUTDATED.value
            if (
                entity_updated is not None
                and config_generated_at is not None
                and entity_updated > config_generated_at
            ):
                return EstadoDocumentoOficial.OUTDATED.value
        return EstadoDocumentoOficial.CURRENT.value

    async def _record_official_document_audit(
        self,
        *,
        event_type: str | None = None,
        accion: str | None = None,
        entidad: str = "planeacion_pedagogica",
        entidad_id: uuid.UUID | None = None,
        proyecto: ProyectoFormativo | None = None,
        proyecto_id: uuid.UUID | None = None,
        programa_id: uuid.UUID | None = None,
        planning_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        previous_version: int | None = None,
        new_version: int | None = None,
        document_path: str | None = None,
        error_detail: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        resolved_event = accion or event_type or "OFFICIAL_DOCUMENT_GENERATED"
        programa = getattr(proyecto, "programa", None) if proyecto else None
        proceso = getattr(programa, "proceso_curricular", None) if programa else None
        referencia_id = getattr(programa, "referencia_id", None) if programa else None
        team_id = getattr(proceso, "equipo_ejecutor_id", None) if proceso else None
        resolved_program_id = programa_id or (getattr(programa, "id", None) if programa else None)
        resolved_project_id = proyecto_id or (getattr(proyecto, "id", None) if proyecto else None)
        target_id = entidad_id or planning_id or resolved_project_id or uuid.uuid4()
        now_iso = datetime.now(UTC).isoformat()
        payload: dict[str, Any] = {
            "planning_id": str(planning_id or target_id),
            "project_id": str(resolved_project_id) if resolved_project_id else None,
            "team_id": str(team_id) if team_id else None,
            "program_id": str(resolved_program_id) if resolved_program_id else None,
            "user_id": str(actor_id) if actor_id else None,
            "timestamp": now_iso,
            "previous_version": previous_version,
            "new_version": new_version,
            "document_path": document_path,
        }
        if error_detail:
            payload["error_detail"] = error_detail
        if extra:
            payload.update(extra)
        self._session.add(
            EventoAuditoria(
                entidad=entidad,
                entidad_id=target_id,
                referencia_id=referencia_id,
                accion=resolved_event,
                actor_usuario_id=actor_id,
                detalle=payload,
            )
        )

    def _build_individual_storage_key(self, entity: PlaneacionPedagogica) -> str:
        """Build a business-legible deterministic MinIO key for the workbook."""
        programa_dir = self._segment(entity.proyecto.programa.nombre_programa)
        proyecto_dir = self._segment(entity.proyecto.nombre_proyecto)
        fase_dir = self._segment(
            entity.fase.nombre_fase if entity.fase else "fase-sin-datos"
        )
        actividad_dir = self._segment(
            entity.actividad.descripcion
            if entity.actividad
            else "actividad-sin-datos"
        )
        collision_suffix = str(entity.id).replace("-", "")[:8]
        return (
            f"planeaciones-pedagogicas/{programa_dir}/{proyecto_dir}/"
            f"{fase_dir}/{actividad_dir}-{collision_suffix}/"
            "GPFI-F-134V05-planeacion.xlsx"
        )

    @staticmethod
    def _segment(value: str) -> str:
        segment = sanitize_directory_name(value)
        if len(segment) > _SEGMENT_MAX_LENGTH:
            segment = segment[:_SEGMENT_MAX_LENGTH].rstrip("-")
        return segment or "sin-datos"

    async def _collect_gaps(
        self,
        entity: PlaneacionPedagogica,
        *,
        require_complete: bool,
    ) -> list[FormatoOficialFaltanteDTO]:
        gaps: list[FormatoOficialFaltanteDTO] = []
        proyecto = entity.proyecto
        programa = proyecto.programa
        if programa.estado != EstadoBloque.COMPLETO:
            gaps.append(
                self._gap(
                    "PROGRAMA_INCOMPLETO",
                    "El programa debe estar COMPLETO.",
                    "configuracion",
                )
            )
        if proyecto.estado != EstadoBloque.COMPLETO:
            gaps.append(
                self._gap(
                    "PROYECTO_INCOMPLETO",
                    "El proyecto debe estar COMPLETO.",
                    "configuracion",
                )
            )
        config = await self._repository.get_document_config(proyecto.id)
        gaps.extend(self._metadata_gaps(programa.modalidad_formacion, config))
        if require_complete and entity.estado != EstadoBloque.COMPLETO:
            gaps.append(
                self._gap(
                    "PLANEACION_BORRADOR",
                    "La planeacion todavia esta en borrador.",
                    "confirmacion",
                )
            )

        if not entity.resultados:
            gaps.append(
                self._gap(
                    "RESULTADOS_FALTANTES",
                    "Selecciona al menos un resultado de aprendizaje.",
                    "curricular",
                )
            )

        competencias_involucradas = {
            resultado.competencia_id for resultado in entity.resultados
        }

        if entity.actividad_id is None or entity.fase_id is None:
            gaps.append(
                self._gap(
                    "ASIGNACION_FALTANTE",
                    "Selecciona una fase y actividad del proyecto.",
                    "curricular",
                )
            )
        else:
            phase_map, activity_map = await self._project_structure(proyecto.id)
            phase = phase_map.get(entity.fase_id)
            activity = activity_map.get(entity.actividad_id)
            if phase is None or activity is None or activity.fase_id != phase.id:
                gaps.append(
                    self._gap(
                        "ASIGNACION_INCONSISTENTE",
                        "La actividad seleccionada no pertenece a la fase indicada.",
                        "curricular",
                    )
                )
            else:
                asignaciones = await self._load_asignaciones_for_actividad(
                    entity.actividad_id
                )
                resultado_ids_asignados = {
                    asignacion.resultado_id
                    for asignacion in asignaciones
                    if asignacion.resultado_id is not None
                }
                for resultado in entity.resultados:
                    if resultado.id not in resultado_ids_asignados:
                        gaps.append(
                            self._gap(
                                "RESULTADO_NO_ASIGNADO",
                                "Hay resultados que no estan asociados a la "
                                "actividad de proyecto seleccionada.",
                                "curricular",
                            )
                        )
                        break

        if not entity.conocimientos:
            gaps.append(
                self._gap(
                    "SABERES_FALTANTES",
                    "Selecciona al menos un saber de concepto o proceso.",
                    "curricular",
                )
            )
        elif any(
            knowledge.competencia_id not in competencias_involucradas
            for knowledge in entity.conocimientos
        ):
            gaps.append(
                self._gap(
                    "SABERES_INCONSISTENTES",
                    "Hay saberes que no pertenecen a las competencias "
                    "involucradas.",
                    "curricular",
                )
            )
        if not entity.criterios:
            gaps.append(
                self._gap(
                    "CRITERIOS_FALTANTES",
                    "Selecciona al menos un criterio de evaluacion.",
                    "curricular",
                )
            )
        elif any(
            criterion.competencia_id not in competencias_involucradas
            for criterion in entity.criterios
        ):
            gaps.append(
                self._gap(
                    "CRITERIOS_INCONSISTENTES",
                    "Hay criterios que no pertenecen a las competencias "
                    "involucradas.",
                    "curricular",
                )
            )

        data = entity.datos_complementarios
        required_text = (
            (
                "ACTIVIDADES_APRENDIZAJE_FALTANTES",
                "actividades_aprendizaje",
                "Faltan las actividades de aprendizaje.",
            ),
            (
                "EVIDENCIA_FALTANTE",
                "descripcion_evidencia_aprendizaje",
                "Falta la descripcion de la evidencia.",
            ),
            (
                "ESTRATEGIAS_FALTANTES",
                "estrategias_didacticas",
                "Faltan las estrategias didacticas.",
            ),
            (
                "MATERIALES_FALTANTES",
                "materiales_formacion",
                "Faltan los materiales de formacion.",
            ),
            (
                "INSTRUCTORES_FALTANTES",
                "instructores",
                "Faltan los instructores responsables.",
            ),
        )
        aliases = {
            "materiales_formacion": "recursos_didacticos",
            "instructores": "instructor_responsable",
        }
        for code, key, message in required_text:
            value = data.get(key) or data.get(aliases.get(key, ""))
            if not self._has_text(value):
                gaps.append(self._gap(code, message, "complementario"))
        if not (
            self._has_text(data.get("ambiente"))
            or self._has_text(data.get("ambientes_aprendizaje"))
            or self._has_text(data.get("ambientes_tipificados"))
        ):
            gaps.append(
                self._gap(
                    "AMBIENTES_FALTANTES",
                    "Falta el ambiente de aprendizaje.",
                    "complementario",
                )
            )

        total = self._number(
            data.get("duracion_actividad_horas", data.get("duracion_horas"))
        )
        direct = self._number(data.get("horas_trabajo_directo"))
        independent = self._number(data.get("horas_trabajo_independiente"))
        if total is None or direct is None or independent is None:
            gaps.append(
                self._gap(
                    "HORAS_FALTANTES",
                    "Completa la duracion y las horas directas e independientes.",
                    "complementario",
                )
            )
        elif total <= 0 or direct < 0 or independent < 0:
            gaps.append(
                self._gap(
                    "HORAS_NEGATIVAS",
                    "Las horas no pueden ser negativas.",
                    "complementario",
                )
            )
        elif abs(total - (direct + independent)) > 0.001:
            gaps.append(
                self._gap(
                    "DURACION_INCONSISTENTE",
                    "La duracion total debe ser igual a trabajo directo mas "
                    "trabajo independiente.",
                    "complementario",
                )
            )

        gaps.extend(
            self._per_rap_gaps(entity, data, required_text, aliases)
        )
        return self._unique_gaps(gaps)

    def _per_rap_gaps(
        self,
        entity: PlaneacionPedagogica,
        data: dict[str, object],
        required_text: tuple[tuple[str, str, str], ...],
        aliases: dict[str, str],
    ) -> list[FormatoOficialFaltanteDTO]:
        """Verify that every selected RAP has its own didactic data filled.

        Saving a planning only mirrors the first RAP into the top-level
        fields, so relying solely on those fields lets a planning with
        several RAPs look "complete" while the rest were never planned.
        Legacy plannings saved before the per-RAP breakdown existed have no
        "raps" map at all: for those, fall back to the top-level mirror so
        already-complete plannings are not retroactively broken.
        """
        raps_data_raw = data.get("raps")
        raps_data = raps_data_raw if isinstance(raps_data_raw, dict) else {}
        uses_per_rap_data = bool(raps_data)

        gaps: list[FormatoOficialFaltanteDTO] = []
        for resultado in entity.resultados:
            rap_id = str(resultado.id)
            raw_rap_data = raps_data.get(rap_id)
            if isinstance(raw_rap_data, dict) and raw_rap_data:
                rap_data: dict[str, object] = raw_rap_data
            elif not uses_per_rap_data:
                rap_data = data
            else:
                rap_data = {}

            is_incomplete = False
            for _, key, _ in required_text:
                value = rap_data.get(key) or rap_data.get(aliases.get(key, ""))
                if not self._has_text(value):
                    is_incomplete = True
                    break

            if not is_incomplete and not (
                self._has_text(rap_data.get("ambiente"))
                or self._has_text(rap_data.get("ambientes_aprendizaje"))
                or self._has_text(rap_data.get("ambientes_tipificados"))
            ):
                is_incomplete = True

            if not is_incomplete:
                rap_total = self._number(
                    rap_data.get(
                        "duracion_actividad_horas", rap_data.get("duracion_horas")
                    )
                )
                rap_direct = self._number(rap_data.get("horas_trabajo_directo"))
                rap_independent = self._number(
                    rap_data.get("horas_trabajo_independiente")
                )
                if (
                    rap_total is None
                    or rap_direct is None
                    or rap_independent is None
                    or rap_total <= 0
                ):
                    is_incomplete = True

            if is_incomplete:
                codigo_rap = resultado.codigo_resultado or str(resultado.id)[:8]
                gaps.append(
                    self._gap(
                        f"RAP_PENDIENTE_{resultado.id}",
                        f"Falta completar la orientacion didactica del "
                        f"resultado de aprendizaje {codigo_rap}.",
                        "complementario",
                    )
                )
        return gaps

    @staticmethod
    def _metadata_gaps(
        modalidad_formacion: str | None,
        config: PlaneacionDocumentoConfig | None,
    ) -> list[FormatoOficialFaltanteDTO]:
        gaps: list[FormatoOficialFaltanteDTO] = []
        values = {
            "MODALIDAD_FALTANTE": (
                modalidad_formacion,
                "Falta la modalidad de formacion.",
            ),
            "FECHA_ELABORACION_FALTANTE": (
                config.fecha_elaboracion if config else None,
                "Falta la fecha de elaboracion.",
            ),
            "CLASIFICACION_FALTANTE": (
                config.clasificacion_informacion if config else None,
                "Falta la clasificacion de la informacion.",
            ),
            "EQUIPO_GESTION_FALTANTE": (
                config.equipo_gestion_curricular if config else None,
                "Falta el equipo de gestion curricular.",
            ),
            "REGIONAL_FALTANTE": (
                config.regional if config else None,
                "Falta la regional.",
            ),
            "CENTRO_FALTANTE": (
                config.centro_formacion if config else None,
                "Falta el centro de formacion.",
            ),
        }
        for code, (value, message) in values.items():
            if not value:
                gaps.append(
                    FormatoOficialFaltanteDTO(
                        codigo=code,
                        mensaje=message,
                        paso="configuracion",
                    )
                )
        return gaps

    async def _build_rows(
        self,
        entities: list[PlaneacionPedagogica],
    ) -> list[FormatoPlaneacionRow]:
        """Build official rows: one per RAP, grouped by competency.

        Hours belong to the integrated learning activity, so they are only
        written on the first row of each planning block to avoid summing
        them once per RAP.
        """
        if not entities:
            return []
        phase_map, activity_map = await self._project_structure(
            entities[0].proyecto_id
        )

        sortable: list[
            tuple[tuple[int, int, str, str, int], FormatoPlaneacionRow]
        ] = []
        for entity in entities:
            data = entity.datos_complementarios
            ambientes = self._stable_unique(
                self._text_items(data.get("ambientes_tipificados"))
                + self._text_items(
                    data.get("ambiente") or data.get("ambientes_aprendizaje")
                )
            )
            direct = self._number(data.get("horas_trabajo_directo")) or 0.0
            independent = (
                self._number(data.get("horas_trabajo_independiente")) or 0.0
            )
            actividad_aprendizaje = str(
                data.get("actividades_aprendizaje") or ""
            ).strip()
            descripcion_evidencia = str(
                data.get("descripcion_evidencia_aprendizaje") or ""
            ).strip()
            estrategias = str(data.get("estrategias_didacticas") or "").strip()
            materiales = str(
                data.get("materiales_formacion")
                or data.get("recursos_didacticos")
                or ""
            ).strip()
            instructores_text = str(
                data.get("instructores")
                or data.get("instructor_responsable")
                or ""
            ).strip()
            observaciones = str(data.get("observaciones") or "").strip()
            tematicas_saber = self._stable_unique(
                self._string_list(data.get("tematicas_saber"))
            )
            tematicas_proceso = self._stable_unique(
                self._string_list(data.get("tematicas_proceso"))
            )

            grupos = self._group_results_by_competencia(entity)
            fase = (
                phase_map.get(entity.fase_id) if entity.fase_id is not None else None
            )
            activity = (
                activity_map.get(entity.actividad_id)
                if entity.actividad_id is not None
                else None
            )
            fase_nombre = fase.nombre_fase if fase else "Fase sin asignar"
            actividad_nombre = (
                activity.descripcion if activity else "Actividad sin asignar"
            )
            phase_orden = fase.orden if fase and fase.orden is not None else 10**9
            activity_orden = (
                activity.orden
                if activity and activity.orden is not None
                else 10**9
            )

            first_row_of_block = True
            local_index = 0
            raps_data_dict = data.get("raps") if isinstance(data.get("raps"), dict) else {}
            has_per_rap_data = bool(raps_data_dict)

            for competencia, resultados in grupos:
                saberes_competencia = self._competencia_knowledge(
                    entity, competencia.id, TipoConocimiento.SABER
                )
                procesos_competencia = self._competencia_knowledge(
                    entity, competencia.id, TipoConocimiento.PROCESO
                )
                criterios_competencia = self._competencia_criteria(
                    entity, competencia.id
                )
                for resultado in resultados:
                    r_id_str = str(resultado.id)
                    rap_data = (
                        raps_data_dict.get(r_id_str)
                        if isinstance(raps_data_dict.get(r_id_str), dict)
                        else data
                    )

                    ambientes = self._stable_unique(
                        self._text_items(rap_data.get("ambientes_tipificados"))
                        + self._text_items(
                            rap_data.get("ambiente")
                            or rap_data.get("ambientes_aprendizaje")
                        )
                        or (
                            self._text_items(data.get("ambientes_tipificados"))
                            + self._text_items(
                                data.get("ambiente")
                                or data.get("ambientes_aprendizaje")
                            )
                        )
                    )
                    direct_val = self._number(rap_data.get("horas_trabajo_directo"))
                    independent_val = self._number(
                        rap_data.get("horas_trabajo_independiente")
                    )

                    if has_per_rap_data and direct_val is not None:
                        row_direct = direct_val
                    elif first_row_of_block:
                        row_direct = self._number(data.get("horas_trabajo_directo"))
                    else:
                        row_direct = None

                    if has_per_rap_data and independent_val is not None:
                        row_independent = independent_val
                    elif first_row_of_block:
                        row_independent = self._number(
                            data.get("horas_trabajo_independiente")
                        )
                    else:
                        row_independent = None

                    actividad_aprendizaje = str(
                        rap_data.get("actividades_aprendizaje")
                        or data.get("actividades_aprendizaje")
                        or ""
                    ).strip()
                    descripcion_evidencia = str(
                        rap_data.get("descripcion_evidencia_aprendizaje")
                        or data.get("descripcion_evidencia_aprendizaje")
                        or ""
                    ).strip()
                    estrategias = str(
                        rap_data.get("estrategias_didacticas")
                        or data.get("estrategias_didacticas")
                        or ""
                    ).strip()
                    materiales = str(
                        rap_data.get("materiales_formacion")
                        or rap_data.get("recursos_didacticos")
                        or data.get("materiales_formacion")
                        or data.get("recursos_didacticos")
                        or ""
                    ).strip()
                    instructores_text = str(
                        rap_data.get("instructores")
                        or rap_data.get("instructor_responsable")
                        or data.get("instructores")
                        or data.get("instructor_responsable")
                        or ""
                    ).strip()
                    observaciones = str(
                        rap_data.get("observaciones")
                        or data.get("observaciones")
                        or ""
                    ).strip()

                    rap_t_saber = self._string_list(rap_data.get("tematicas_saber"))
                    rap_t_proceso = self._string_list(rap_data.get("tematicas_proceso"))
                    t_saber_use = (
                        rap_t_saber
                        if rap_t_saber
                        else (
                            self._string_list(data.get("tematicas_saber"))
                            if first_row_of_block
                            else []
                        )
                    )
                    t_proceso_use = (
                        rap_t_proceso
                        if rap_t_proceso
                        else (
                            self._string_list(data.get("tematicas_proceso"))
                            if first_row_of_block
                            else []
                        )
                    )

                    saberes = self._stable_unique(
                        saberes_competencia + t_saber_use
                    )
                    procesos = self._stable_unique(
                        procesos_competencia + t_proceso_use
                    )

                    row = FormatoPlaneacionRow(
                        fase=fase_nombre,
                        actividad_proyecto=actividad_nombre,
                        competencia=(
                            f"{competencia.codigo_competencia}\n"
                            f"{competencia.nombre_competencia}"
                        ),
                        resultado="\n".join(
                            value
                            for value in (
                                resultado.codigo_resultado,
                                resultado.descripcion,
                            )
                            if value
                        ),
                        saberes=tuple(saberes),
                        procesos=tuple(procesos),
                        criterios=tuple(criterios_competencia),
                        actividades_aprendizaje=actividad_aprendizaje,
                        horas_trabajo_directo=row_direct,
                        horas_trabajo_independiente=row_independent,
                        descripcion_evidencia=descripcion_evidencia,
                        estrategias_didacticas=estrategias,
                        ambiente=tuple(ambientes),
                        materiales_formacion=materiales,
                        instructores=instructores_text,
                        observaciones=observaciones,
                    )
                    sortable.append(
                        (
                            (
                                phase_orden,
                                activity_orden,
                                str(entity.actividad_id or ""),
                                str(entity.id),
                                local_index,
                            ),
                            row,
                        )
                    )
                    first_row_of_block = False
                    local_index += 1
        return [row for _, row in sorted(sortable, key=lambda item: item[0])]

    @staticmethod
    def _group_results_by_competencia(
        entity: PlaneacionPedagogica,
    ) -> list[tuple[Competencia, list[ResultadoAprendizaje]]]:
        grupos: dict[uuid.UUID, tuple[Competencia, list[ResultadoAprendizaje]]] = {}
        for resultado in entity.resultados:
            competencia = resultado.competencia
            entry = grupos.setdefault(competencia.id, (competencia, []))
            entry[1].append(resultado)
        ordered = sorted(
            grupos.values(),
            key=lambda item: (
                item[0].orden is None,
                item[0].orden or 0,
                item[0].codigo_competencia,
            ),
        )
        return [
            (
                competencia,
                sorted(
                    resultados,
                    key=lambda resultado: (
                        resultado.orden is None,
                        resultado.orden or 0,
                        resultado.codigo_resultado or "",
                    ),
                ),
            )
            for competencia, resultados in ordered
        ]

    @staticmethod
    def _competencia_knowledge(
        entity: PlaneacionPedagogica,
        competencia_id: uuid.UUID,
        tipo: TipoConocimiento,
    ) -> list[str]:
        selected = sorted(
            (
                item
                for item in entity.conocimientos
                if item.competencia_id == competencia_id and item.tipo == tipo
            ),
            key=lambda item: (
                item.orden is None,
                item.orden or 0,
                item.descripcion,
            ),
        )
        return [item.descripcion for item in selected]

    @staticmethod
    def _competencia_criteria(
        entity: PlaneacionPedagogica,
        competencia_id: uuid.UUID,
    ) -> list[str]:
        selected = sorted(
            (
                item
                for item in entity.criterios
                if item.competencia_id == competencia_id
            ),
            key=lambda item: (
                item.orden is None,
                item.orden or 0,
                item.descripcion,
            ),
        )
        return [item.descripcion for item in selected]

    async def _project_structure(
        self,
        proyecto_id: uuid.UUID,
    ) -> tuple[
        dict[uuid.UUID, FaseProyecto],
        dict[uuid.UUID, ActividadProyecto],
    ]:
        statement = (
            select(FaseProyecto)
            .where(FaseProyecto.proyecto_id == proyecto_id)
            .options(selectinload(FaseProyecto.actividades))
        )
        result = await self._session.execute(statement)
        phases = list(result.scalars().unique().all())
        return (
            {phase.id: phase for phase in phases},
            {
                activity.id: activity
                for phase in phases
                for activity in phase.actividades
            },
        )

    async def _get_project_with_program(
        self,
        proyecto_id: uuid.UUID,
    ) -> ProyectoFormativo:
        proyecto = await self._session.get(
            ProyectoFormativo,
            proyecto_id,
            options=[selectinload(ProyectoFormativo.programa)],
        )
        if proyecto is None:
            raise ValueError(f"No existe el proyecto formativo {proyecto_id}")
        return proyecto

    async def _require_config(
        self,
        proyecto_id: uuid.UUID,
    ) -> PlaneacionDocumentoConfig:
        config = await self._repository.get_document_config(proyecto_id)
        if config is None:
            raise PlaneacionFormatoValidationError(
                ["Falta la configuracion documental del formato oficial"]
            )
        return config

    @staticmethod
    def _build_metadata(
        proyecto: ProyectoFormativo,
        config: PlaneacionDocumentoConfig,
    ) -> FormatoPlaneacionMetadata:
        if config.fecha_elaboracion is None:
            raise PlaneacionFormatoValidationError(
                ["Falta la fecha de elaboracion"]
            )
        return FormatoPlaneacionMetadata(
            fecha_elaboracion=config.fecha_elaboracion,
            nombre_programa=proyecto.programa.nombre_programa,
            modalidad_formacion=proyecto.programa.modalidad_formacion or "",
            codigo_programa=proyecto.programa.codigo_programa,
            version_programa=proyecto.programa.version_programa,
            nombre_proyecto=proyecto.nombre_proyecto,
            codigo_proyecto=proyecto.codigo_proyecto,
            equipo_gestion_curricular=tuple(config.equipo_gestion_curricular),
            regional=config.regional or "",
            centro_formacion=config.centro_formacion or "",
            clasificacion_informacion=config.clasificacion_informacion or "",
        )

    @classmethod
    def _map_config(
        cls,
        proyecto: ProyectoFormativo,
        config: PlaneacionDocumentoConfig | None,
        entities: Sequence[PlaneacionPedagogica] | None = None,
    ) -> PlaneacionDocumentoConfigDTO:
        if entities is not None:
            doc_status = cls._resolve_consolidated_document_status(config, entities)
        elif config and config.storage_key:
            config_gen = getattr(config, "fecha_generacion", None)
            config_upd = getattr(config, "fecha_actualizacion", None)
            if config_upd is not None and config_gen is not None and config_upd > config_gen:
                doc_status = EstadoDocumentoOficial.OUTDATED.value
            else:
                doc_status = EstadoDocumentoOficial.CURRENT.value
        else:
            doc_status = EstadoDocumentoOficial.NOT_GENERATED.value
        return PlaneacionDocumentoConfigDTO(
            proyecto_id=proyecto.id,
            fecha_elaboracion=config.fecha_elaboracion if config else None,
            modalidad_formacion=proyecto.programa.modalidad_formacion,
            clasificacion_informacion=cast(
                Literal[
                    "PUBLICA",
                    "PUBLICA_CLASIFICADA",
                    "PUBLICA_RESERVADA",
                ]
                | None,
                config.clasificacion_informacion if config else None,
            ),
            equipo_gestion_curricular=(
                config.equipo_gestion_curricular if config else []
            ),
            regional=config.regional if config else None,
            centro_formacion=config.centro_formacion if config else None,
            storage_key=config.storage_key if config else None,
            file_name=config.file_name if config else None,
            content_type=config.content_type if config else None,
            checksum_sha256=config.checksum_sha256 if config else None,
            fecha_generacion=config.fecha_generacion if config else None,
            version=config.version if config else 1,
            official_document_status=doc_status,
            official_storage_key=getattr(config, "official_storage_key", None) if config else None,
            official_file_name=getattr(config, "official_file_name", None) if config else None,
            official_version=getattr(config, "official_version", None) if config else None,
        )

    async def _map_to_response_dto(
        self, entity: PlaneacionPedagogica
    ) -> PlaneacionResponseDTO:
        """Map PlaneacionPedagogica ORM model to PlaneacionResponseDTO."""
        tipos: dict[uuid.UUID, str | None] = {}
        if entity.actividad_id is not None:
            asignaciones = await self._load_asignaciones_for_actividad(
                entity.actividad_id
            )
            tipos = {
                asignacion.resultado_id: asignacion.tipo_resultado
                for asignacion in asignaciones
                if asignacion.resultado_id is not None
            }
        grupos: dict[uuid.UUID, PlaneacionCompetenciaResumenDTO] = {}
        for resultado in entity.resultados:
            competencia = resultado.competencia
            tipo_value = tipos.get(resultado.id)
            tipo_resultado = (
                TipoResultadoProyecto(tipo_value) if tipo_value is not None else None
            )
            resumen = grupos.setdefault(
                competencia.id,
                PlaneacionCompetenciaResumenDTO(
                    competencia_id=competencia.id,
                    codigo_competencia=competencia.codigo_competencia,
                    nombre_competencia=competencia.nombre_competencia,
                    tipo_resultado=tipo_resultado,
                ),
            )
            ra_meta = self._resolve_ra_lock_metadata(entity, resultado)
            resumen.resultados.append(
                PlaneacionResultadoResumenDTO(
                    id=resultado.id,
                    codigo_resultado=resultado.codigo_resultado,
                    descripcion=resultado.descripcion,
                    tipo_resultado=tipo_resultado,
                    edit_status=str(ra_meta["edit_status"]),
                    locked_at=cast(datetime | None, ra_meta["locked_at"]),
                    locked_by=cast(uuid.UUID | None, ra_meta["locked_by"]),
                    unlocked_at=cast(datetime | None, ra_meta["unlocked_at"]),
                    unlocked_by=cast(uuid.UUID | None, ra_meta["unlocked_by"]),
                    unlock_request_id=cast(uuid.UUID | None, ra_meta["unlock_request_id"]),
                    approved_version=int(ra_meta["approved_version"]),  # type: ignore[arg-type]
                    approved_at=cast(datetime | None, ra_meta["approved_at"]),
                )
            )
        rev_status = getattr(entity, "review_status", None)
        app_status = getattr(entity, "approval_status", None)
        ed_status = getattr(entity, "edit_status", None)
        return PlaneacionResponseDTO(
            id=entity.id,
            proyecto_id=entity.proyecto_id,
            fase_id=entity.fase_id,
            actividad_id=entity.actividad_id,
            estado=entity.estado.value,
            review_status=(
                rev_status.value if hasattr(rev_status, "value") else str(rev_status or "DRAFT")
            ),
            approval_status=(
                app_status.value if hasattr(app_status, "value") else str(app_status or "PENDING")
            ),
            edit_status=(
                ed_status.value if hasattr(ed_status, "value") else str(ed_status or "EDITABLE")
            ),
            locked_at=getattr(entity, "locked_at", None),
            locked_by=getattr(entity, "locked_by", None),
            unlocked_at=getattr(entity, "unlocked_at", None),
            unlocked_by=getattr(entity, "unlocked_by", None),
            unlock_request_id=getattr(entity, "unlock_request_id", None),
            datos_complementarios=entity.datos_complementarios,
            resultados_ids=[r.id for r in entity.resultados],
            conocimientos_ids=[k.id for k in entity.conocimientos],
            criterios_ids=[cr.id for cr in entity.criterios],
            competencias=list(grupos.values()),
            storage_key=entity.storage_key,
            file_name=entity.file_name,
            content_type=entity.content_type,
            checksum_sha256=entity.checksum_sha256,
            fecha_generacion=entity.fecha_generacion,
            version=entity.version or 1,
            official_document_status=self._resolve_official_document_status(entity),
            official_storage_key=getattr(entity, "official_storage_key", None),
            official_file_name=getattr(entity, "official_file_name", None),
            official_version=getattr(entity, "official_version", None),
            official_approved_at=getattr(entity, "official_approved_at", None),
        )

    @staticmethod
    def _gap(
        code: str,
        message: str,
        step: Literal[
            "configuracion",
            "curricular",
            "complementario",
            "confirmacion",
        ],
    ) -> FormatoOficialFaltanteDTO:
        return FormatoOficialFaltanteDTO(
            codigo=code,
            mensaje=message,
            paso=step,
        )

    @staticmethod
    def _unique_gaps(
        gaps: list[FormatoOficialFaltanteDTO],
    ) -> list[FormatoOficialFaltanteDTO]:
        return list({gap.codigo: gap for gap in gaps}.values())

    @staticmethod
    def _has_text(value: object) -> bool:
        return isinstance(value, str) and bool(value.strip())

    @staticmethod
    def _number(value: object) -> float | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @staticmethod
    def _string_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @staticmethod
    def _text_items(value: object) -> list[str]:
        if not isinstance(value, str):
            return []
        return [
            line.strip().removeprefix("-").strip()
            for line in value.splitlines()
            if line.strip().removeprefix("-").strip()
        ]

    @staticmethod
    def _stable_unique(values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))

    async def _ensure_project_complete(self, proyecto_id: uuid.UUID) -> None:
        proyecto = await self._session.get(ProyectoFormativo, proyecto_id)
        if proyecto is None:
            raise ValueError(f"No existe el proyecto formativo {proyecto_id}")
        if proyecto.estado != EstadoBloque.COMPLETO:
            raise PlaneacionAccessError(
                "La planeacion pedagogica solo puede iniciarse cuando "
                "el proyecto esta COMPLETO"
            )
