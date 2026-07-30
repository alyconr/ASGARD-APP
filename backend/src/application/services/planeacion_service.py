"""Application service for Pedagogical Planning management."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal, Protocol, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.dto.planeacion import (
    ContextoActividadDTO,
    ContextoAsignacionProyectoDTO,
    ContextoCompetenciaDTO,
    ContextoConocimientoDTO,
    ContextoCriterioDTO,
    ContextoFaseDTO,
    ContextoResultadoDTO,
    FormatoOficialEstadoDTO,
    FormatoOficialFaltanteDTO,
    FormatoOficialGeneradoDTO,
    PlaneacionContextoDTO,
    PlaneacionDocumentoConfigDTO,
    PlaneacionDocumentoConfigUpdateDTO,
    PlaneacionListDTO,
    PlaneacionResponseDTO,
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
from src.domain.shared.enums import EstadoBloque, TipoConocimiento
from src.infrastructure.db.models.curriculum import (
    Competencia,
    Conocimiento,
    CriterioEvaluacion,
    ProgramaFormacion,
    ResultadoAprendizaje,
)
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.planeacion import (
    PlaneacionDocumentoConfig,
    PlaneacionPedagogica,
)
from src.infrastructure.db.models.proyecto import (
    ActividadProyecto,
    FaseProyecto,
    ProyectoFormativo,
)
from src.infrastructure.repositories.planeacion import PlaneacionPedagogicaRepository
from src.infrastructure.storage.document_storage import sanitize_directory_name


class PlaneacionAccessError(Exception):
    """Raised when planning is requested before project completion."""


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


class PlaneacionPedagogicaService:
    """Orchestrate CRUD, state transitions, and file generations
    for Pedagogical Planning.
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
        """Verify program/project status and construct the active curriculum tree."""
        # Retrieve program draft
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

        # Extract programa_id
        programa_id = None
        curr = draft_prog.payload_json.get("curricular")
        if isinstance(curr, dict):
            raw_id = curr.get("programa_formacion_id")
            if raw_id:
                programa_id = uuid.UUID(str(raw_id))

        if programa_id is None:
            raise ValueError(
                "El programa de formación no ha sido importado/materializado "
                "en la sesión"
            )

        # Load program & project
        programa = await self._session.get(
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
        if programa is None:
            raise ValueError(
                f"No se encontró el ProgramaFormacion {programa_id} en base de datos"
            )
        if programa.estado != EstadoBloque.COMPLETO:
            raise PlaneacionAccessError(
                "La planeacion pedagogica requiere el programa en estado COMPLETO"
            )

        # Check if project exists and is not blocked
        proj_stmt = (
            select(ProyectoFormativo)
            .where(ProyectoFormativo.programa_id == programa_id)
            .options(
                selectinload(ProyectoFormativo.fases).selectinload(
                    FaseProyecto.actividades
                )
            )
        )
        proj_res = await self._session.execute(proj_stmt)
        proyecto = proj_res.scalar_one_or_none()
        if proyecto is None:
            raise ValueError(
                "No se ha importado el proyecto formativo para este programa"
            )

        if proyecto.estado != EstadoBloque.COMPLETO:
            raise PlaneacionAccessError(
                "La planeacion pedagogica requiere el proyecto formativo "
                "en estado COMPLETO"
            )

        project_draft_stmt = select(BorradorSesion).where(
            BorradorSesion.tipo_bloque == TipoBloqueBorrador.PROYECTO,
        )
        project_draft_res = await self._session.execute(project_draft_stmt)
        project_draft = None
        for draft in project_draft_res.scalars().all():
            project_payload = draft.payload_json.get("proyecto")
            if not isinstance(project_payload, dict):
                continue
            if (
                project_payload.get("codigo_proyecto")
                == proyecto.codigo_proyecto
                and project_payload.get("nombre_proyecto")
                == proyecto.nombre_proyecto
            ):
                project_draft = draft
                break

        phase_by_name = {fase.nombre_fase: fase for fase in proyecto.fases}
        project_rap_links: dict[str, list[tuple[uuid.UUID, uuid.UUID]]] = {}
        if project_draft is not None:
            documental = project_draft.payload_json.get("documental", {})
            fuente = (
                documental.get("fuente_estructurada", {})
                if isinstance(documental, dict)
                else {}
            )
            preview = fuente.get("preview", {}) if isinstance(fuente, dict) else {}
            preview_fases = (
                preview.get("fases", []) if isinstance(preview, dict) else []
            )
            for preview_fase in preview_fases:
                if not isinstance(preview_fase, dict):
                    continue
                preview_phase_name = preview_fase.get("nombre_fase")
                if not isinstance(preview_phase_name, str):
                    continue
                fase = phase_by_name.get(preview_phase_name)
                if fase is None:
                    continue
                activity_by_description = {
                    actividad.descripcion: actividad for actividad in fase.actividades
                }
                for preview_actividad in preview_fase.get("actividades", []):
                    if not isinstance(preview_actividad, dict):
                        continue
                    preview_activity_description = preview_actividad.get(
                        "descripcion"
                    )
                    if not isinstance(preview_activity_description, str):
                        continue
                    actividad = activity_by_description.get(
                        preview_activity_description
                    )
                    if actividad is None:
                        continue
                    for competencia in preview_actividad.get("competencias", []):
                        if not isinstance(competencia, dict):
                            continue
                        for resultado in competencia.get("resultados", []):
                            if isinstance(resultado, dict) and resultado.get("rap_id"):
                                link = (
                                    fase.id,
                                    actividad.id,
                                )
                                links = project_rap_links.setdefault(
                                    str(resultado["rap_id"]), []
                                )
                                if link not in links:
                                    links.append(link)

        # Format Fases & Actividades
        fase_dtos: list[ContextoFaseDTO] = []
        for f in proyecto.fases:
            act_dtos = [
                ContextoActividadDTO(id=a.id, descripcion=a.descripcion)
                for a in f.actividades
            ]
            fase_dtos.append(
                ContextoFaseDTO(
                    id=f.id, nombre_fase=f.nombre_fase, actividades=act_dtos
                )
            )

        # Format Competencias, outcomes, knowledge
        # (separated by saber/proceso), and criteria
        comp_dtos: list[ContextoCompetenciaDTO] = []
        for c in programa.competencias:
            res_dtos = []
            for r in c.resultados:
                links = project_rap_links.get(r.codigo_resultado or "", [])
                res_dtos.append(
                    ContextoResultadoDTO(
                        id=r.id,
                        descripcion=r.descripcion,
                        fase_id=links[0][0] if links else None,
                        actividad_id=links[0][1] if links else None,
                        asignaciones_proyecto=[
                            ContextoAsignacionProyectoDTO(
                                fase_id=fase_id,
                                actividad_id=actividad_id,
                            )
                            for fase_id, actividad_id in links
                        ],
                    )
                )
            saberes_conceptos = [
                ContextoConocimientoDTO(id=k.id, descripcion=k.descripcion)
                for k in c.conocimientos
                if k.tipo == TipoConocimiento.SABER
            ]
            saberes_proceso = [
                ContextoConocimientoDTO(id=k.id, descripcion=k.descripcion)
                for k in c.conocimientos
                if k.tipo == TipoConocimiento.PROCESO
            ]
            crit_dtos = [
                ContextoCriterioDTO(id=cr.id, descripcion=cr.descripcion)
                for cr in c.criterios
            ]

            comp_dtos.append(
                ContextoCompetenciaDTO(
                    id=c.id,
                    codigo_competencia=c.codigo_competencia,
                    nombre_competencia=c.nombre_competencia,
                    resultados=res_dtos,
                    conocimientos_saber=saberes_conceptos,
                    conocimientos_proceso=saberes_proceso,
                    criterios=crit_dtos,
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
            competencias=comp_dtos,
            fases=fase_dtos,
        )

    async def listar_planeaciones(
        self, proyecto_id: uuid.UUID
    ) -> list[PlaneacionListDTO]:
        """List all pedagogical planning summaries for a project."""
        entities = await self._repository.list_by_proyecto(proyecto_id)
        return [
            PlaneacionListDTO(
                id=e.id,
                proyecto_id=e.proyecto_id,
                competencia_id=e.competencia_id,
                resultado_id=e.resultado_id,
                resultado_descripcion=e.resultado.descripcion,
                codigo_competencia=e.competencia.codigo_competencia,
                nombre_competencia=e.competencia.nombre_competencia,
                estado=e.estado.value,
                fecha_actualizacion=e.fecha_actualizacion,
            )
            for e in entities
        ]

    async def obtener_detalle(
        self, planeacion_id: uuid.UUID
    ) -> PlaneacionResponseDTO | None:
        """Get the full details of a single pedagogical planning record."""
        entity = await self._repository.get_by_id(planeacion_id)
        if entity is None:
            return None
        return self._map_to_response_dto(entity)

    async def guardar_borrador(self, dto: PlaneacionSaveDTO) -> PlaneacionResponseDTO:
        """Create or update a pedagogical planning draft in the database."""
        await self._ensure_project_complete(dto.proyecto_id)
        resultado = await self._session.get(ResultadoAprendizaje, dto.resultado_id)
        if resultado is None:
            raise ValueError(
                f"No existe el resultado de aprendizaje {dto.resultado_id}"
            )
        if resultado.competencia_id != dto.competencia_id:
            raise ValueError(
                "El resultado seleccionado no pertenece a la competencia indicada"
            )

        entity = await self._repository.get_by_proyecto_and_resultado(
            dto.proyecto_id,
            dto.resultado_id,
        )
        if entity is None:
            entity = PlaneacionPedagogica(
                proyecto_id=dto.proyecto_id,
                competencia_id=dto.competencia_id,
                resultado_id=dto.resultado_id,
            )
        else:
            entity.competencia_id = dto.competencia_id
            entity.resultado_id = dto.resultado_id

        entity.fase_id = dto.fase_id
        entity.actividad_id = dto.actividad_id
        entity.estado = EstadoBloque.BORRADOR
        entity.datos_complementarios = dto.datos_complementarios

        entity.resultados = [resultado]

        if dto.conocimientos_ids:
            k_stmt = select(Conocimiento).where(
                Conocimiento.id.in_(dto.conocimientos_ids)
            )
            k_query = await self._session.execute(k_stmt)
            entity.conocimientos = list(k_query.scalars().all())
        else:
            entity.conocimientos = []

        if dto.criterios_ids:
            cr_stmt = select(CriterioEvaluacion).where(
                CriterioEvaluacion.id.in_(dto.criterios_ids)
            )
            cr_query = await self._session.execute(cr_stmt)
            entity.criterios = list(cr_query.scalars().all())
        else:
            entity.criterios = []

        await self._repository.save(entity)

        # Re-fetch to ensure all properties (competencia details, fase, etc)
        # are loaded for response
        refetched = await self._repository.get_by_id(entity.id)
        if refetched is None:
            raise ValueError("Error al guardar y recuperar el borrador")
        return self._map_to_response_dto(refetched)

    async def confirmar_y_generar(
        self, planeacion_id: uuid.UUID
    ) -> PlaneacionResponseDTO:
        """Complete one planning row and generate its official workbook."""
        entity = await self._repository.get_by_id(planeacion_id)
        if entity is None:
            raise ValueError(
                f"No existe la planeación pedagógica con id {planeacion_id}"
            )
        await self._ensure_project_complete(entity.proyecto_id)
        gaps = await self._collect_gaps(entity, require_complete=False)
        if gaps:
            raise PlaneacionFormatoValidationError(
                [gap.mensaje for gap in gaps]
            )
        entity.estado = EstadoBloque.COMPLETO
        await self._generate_individual(entity)
        await self._repository.save(entity)
        return self._map_to_response_dto(entity)

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
        proyecto.programa.modalidad_formacion = dto.modalidad_formacion.strip()
        config.fecha_elaboracion = dto.fecha_elaboracion
        config.clasificacion_informacion = dto.clasificacion_informacion
        config.equipo_gestion_curricular = equipo
        config.regional = dto.regional.strip()
        config.centro_formacion = dto.centro_formacion.strip()
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
        return FormatoOficialEstadoDTO(
            listo=not gaps,
            faltantes=gaps,
            planeaciones_completas=int(entity.estado == EstadoBloque.COMPLETO),
            borradores_excluidos=int(entity.estado != EstadoBloque.COMPLETO),
            storage_key=entity.storage_key,
            file_name=entity.file_name,
            checksum_sha256=entity.checksum_sha256,
            fecha_generacion=entity.fecha_generacion,
        )

    async def obtener_estado_formato_consolidado(
        self,
        proyecto_id: uuid.UUID,
    ) -> FormatoOficialEstadoDTO:
        """Return project counts, gaps, and last consolidated artifact."""
        entities = await self._repository.list_full_by_proyecto(proyecto_id)
        complete = [e for e in entities if e.estado == EstadoBloque.COMPLETO]
        drafts = len(entities) - len(complete)
        config = await self._repository.get_document_config(proyecto_id)
        gaps: list[FormatoOficialFaltanteDTO] = []
        if not complete:
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
        gaps = self._unique_gaps(gaps)
        return FormatoOficialEstadoDTO(
            listo=not gaps,
            faltantes=gaps,
            planeaciones_completas=len(complete),
            borradores_excluidos=drafts,
            storage_key=config.storage_key if config else None,
            file_name=config.file_name if config else None,
            checksum_sha256=config.checksum_sha256 if config else None,
            fecha_generacion=config.fecha_generacion if config else None,
        )

    async def generar_formato_individual(
        self,
        planeacion_id: uuid.UUID,
    ) -> FormatoOficialGeneradoDTO:
        """Regenerate the official workbook for a completed planning."""
        entity = await self._repository.get_by_id(planeacion_id)
        if entity is None:
            raise ValueError(f"No existe la planeacion pedagogica {planeacion_id}")
        gaps = await self._collect_gaps(entity, require_complete=True)
        if gaps:
            raise PlaneacionFormatoValidationError(
                [gap.mensaje for gap in gaps]
            )
        generated = await self._generate_individual(entity)
        await self._repository.save(entity)
        return generated

    async def generar_formato_consolidado(
        self,
        proyecto_id: uuid.UUID,
    ) -> FormatoOficialGeneradoDTO:
        """Generate and store all completed project planning rows."""
        await self._ensure_project_complete(proyecto_id)
        entities = await self._repository.list_full_by_proyecto(proyecto_id)
        complete = [e for e in entities if e.estado == EstadoBloque.COMPLETO]
        drafts = len(entities) - len(complete)
        if not complete:
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
        metadata = self._build_metadata(proyecto, config)
        rows = await self._build_rows(complete)
        result = self._formato_excel_service.generar(metadata=metadata, rows=rows)
        programa_dir = sanitize_directory_name(proyecto.programa.nombre_programa)
        proyecto_dir = sanitize_directory_name(proyecto.nombre_proyecto)
        storage_key = (
            f"planeaciones-pedagogicas/{programa_dir}/{proyecto_dir}/"
            f"formato-oficial/{OFFICIAL_FILE_NAME}"
        )
        await self._storage_service.save_excel(
            key=storage_key,
            content=result.content,
            content_type=EXCEL_CONTENT_TYPE,
            original_filename=OFFICIAL_FILE_NAME,
        )
        now = datetime.now(UTC)
        config.version = config.version + 1 if config.storage_key else config.version
        config.storage_key = storage_key
        config.file_name = OFFICIAL_FILE_NAME
        config.content_type = EXCEL_CONTENT_TYPE
        config.checksum_sha256 = result.checksum_sha256
        config.fecha_generacion = now
        await self._repository.save_document_config(config)
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
        )

    async def descargar_formato_individual(
        self,
        planeacion_id: uuid.UUID,
    ) -> tuple[bytes, str]:
        """Read a previously generated individual workbook from MinIO."""
        entity = await self._repository.get_by_id(planeacion_id)
        if entity is None:
            raise ValueError(f"No existe la planeacion pedagogica {planeacion_id}")
        if (
            entity.estado != EstadoBloque.COMPLETO
            or not entity.storage_key
            or entity.content_type != EXCEL_CONTENT_TYPE
        ):
            raise FileNotFoundError("La planeacion no tiene un Excel oficial generado")
        content = await self._storage_service.read_excel(key=entity.storage_key)
        return content, entity.file_name or OFFICIAL_FILE_NAME

    async def descargar_formato_consolidado(
        self,
        proyecto_id: uuid.UUID,
    ) -> tuple[bytes, str]:
        """Read the latest consolidated project workbook from MinIO."""
        config = await self._repository.get_document_config(proyecto_id)
        if (
            config is None
            or not config.storage_key
            or config.content_type != EXCEL_CONTENT_TYPE
        ):
            raise FileNotFoundError(
                "El proyecto no tiene un Excel oficial consolidado generado"
            )
        content = await self._storage_service.read_excel(key=config.storage_key)
        return content, config.file_name or OFFICIAL_FILE_NAME

    async def _generate_individual(
        self,
        entity: PlaneacionPedagogica,
    ) -> FormatoOficialGeneradoDTO:
        config = await self._require_config(entity.proyecto_id)
        metadata = self._build_metadata(entity.proyecto, config)
        rows = await self._build_rows([entity])
        result = self._formato_excel_service.generar(metadata=metadata, rows=rows)
        programa_dir = sanitize_directory_name(
            entity.proyecto.programa.nombre_programa
        )
        proyecto_dir = sanitize_directory_name(entity.proyecto.nombre_proyecto)
        resultado_dir = sanitize_directory_name(
            entity.resultado.codigo_resultado or "resultado-sin-codigo"
        )
        file_name = "GPFI-F-134V05-planeacion.xlsx"
        storage_key = (
            f"planeaciones-pedagogicas/{programa_dir}/{proyecto_dir}/"
            f"resultados/{resultado_dir}/{file_name}"
        )
        await self._storage_service.save_excel(
            key=storage_key,
            content=result.content,
            content_type=EXCEL_CONTENT_TYPE,
            original_filename=file_name,
        )
        now = datetime.now(UTC)
        entity.version = entity.version + 1 if entity.storage_key else entity.version
        entity.storage_key = storage_key
        entity.file_name = file_name
        entity.content_type = EXCEL_CONTENT_TYPE
        entity.checksum_sha256 = result.checksum_sha256
        entity.fecha_generacion = now
        return FormatoOficialGeneradoDTO(
            storage_key=storage_key,
            file_name=file_name,
            content_type=EXCEL_CONTENT_TYPE,
            checksum_sha256=result.checksum_sha256,
            fecha_generacion=now,
            version=entity.version,
            filas_generadas=result.filas_generadas,
            planeaciones_incluidas=1,
        )

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
        if (
            entity.resultado is None
            or entity.resultado.competencia_id != entity.competencia_id
        ):
            gaps.append(
                self._gap(
                    "RESULTADO_INVALIDO",
                    "El resultado no pertenece a la competencia seleccionada.",
                    "curricular",
                )
            )
        if not entity.conocimientos:
            gaps.append(
                self._gap(
                    "SABERES_FALTANTES",
                    "Selecciona al menos un saber de concepto o proceso.",
                    "curricular",
                )
            )
        elif any(
            knowledge.competencia_id != entity.competencia_id
            for knowledge in entity.conocimientos
        ):
            gaps.append(
                self._gap(
                    "SABERES_INCONSISTENTES",
                    "Hay saberes que no pertenecen a la competencia.",
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
            criterion.competencia_id != entity.competencia_id
            for criterion in entity.criterios
        ):
            gaps.append(
                self._gap(
                    "CRITERIOS_INCONSISTENTES",
                    "Hay criterios que no pertenecen a la competencia.",
                    "curricular",
                )
            )

        phase_map, activity_map = await self._project_structure(proyecto.id)
        assignments = self._assignment_pairs(entity)
        if not assignments:
            gaps.append(
                self._gap(
                    "ASIGNACION_FALTANTE",
                    "Selecciona una fase y actividad del proyecto.",
                    "curricular",
                )
            )
        for phase_id, activity_id in assignments:
            phase = phase_map.get(phase_id)
            activity = activity_map.get(activity_id)
            if (
                phase is None
                or activity is None
                or activity.fase_id != phase.id
            ):
                gaps.append(
                    self._gap(
                        "ASIGNACION_INCONSISTENTE",
                        "La actividad seleccionada no pertenece a la fase indicada.",
                        "curricular",
                    )
                )
                break

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
        return self._unique_gaps(gaps)

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
        if not entities:
            return []
        phase_map, activity_map = await self._project_structure(
            entities[0].proyecto_id
        )
        sortable: list[
            tuple[tuple[int, int, int, int, str], FormatoPlaneacionRow]
        ] = []
        for entity in entities:
            data = entity.datos_complementarios
            selected = sorted(
                entity.conocimientos,
                key=lambda item: (
                    item.orden is None,
                    item.orden or 0,
                    item.descripcion,
                ),
            )
            saberes = self._stable_unique(
                [
                    item.descripcion
                    for item in selected
                    if item.tipo == TipoConocimiento.SABER
                ]
                + self._string_list(data.get("tematicas_saber"))
            )
            procesos = self._stable_unique(
                [
                    item.descripcion
                    for item in selected
                    if item.tipo == TipoConocimiento.PROCESO
                ]
                + self._string_list(data.get("tematicas_proceso"))
            )
            criterios = self._stable_unique(
                [
                    item.descripcion
                    for item in sorted(
                        entity.criterios,
                        key=lambda item: (
                            item.orden is None,
                            item.orden or 0,
                            item.descripcion,
                        ),
                    )
                ]
            )
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
            for phase_id, activity_id in self._assignment_pairs(entity):
                phase = phase_map[phase_id]
                activity = activity_map[activity_id]
                row = FormatoPlaneacionRow(
                    fase=phase.nombre_fase,
                    actividad_proyecto=activity.descripcion,
                    competencia=(
                        f"{entity.competencia.codigo_competencia}\n"
                        f"{entity.competencia.nombre_competencia}"
                    ),
                    resultado="\n".join(
                        value
                        for value in (
                            entity.resultado.codigo_resultado,
                            entity.resultado.descripcion,
                        )
                        if value
                    ),
                    saberes=tuple(saberes),
                    procesos=tuple(procesos),
                    criterios=tuple(criterios),
                    actividades_aprendizaje=str(
                        data.get("actividades_aprendizaje") or ""
                    ).strip(),
                    horas_trabajo_directo=direct,
                    horas_trabajo_independiente=independent,
                    descripcion_evidencia=str(
                        data.get("descripcion_evidencia_aprendizaje") or ""
                    ).strip(),
                    estrategias_didacticas=str(
                        data.get("estrategias_didacticas") or ""
                    ).strip(),
                    ambiente=tuple(ambientes),
                    materiales_formacion=str(
                        data.get("materiales_formacion")
                        or data.get("recursos_didacticos")
                        or ""
                    ).strip(),
                    instructores=str(
                        data.get("instructores")
                        or data.get("instructor_responsable")
                        or ""
                    ).strip(),
                    observaciones=str(data.get("observaciones") or "").strip(),
                )
                sortable.append(
                    (
                        (
                            phase.orden if phase.orden is not None else 10**9,
                            activity.orden
                            if activity.orden is not None
                            else 10**9,
                            entity.competencia.orden
                            if entity.competencia.orden is not None
                            else 10**9,
                            entity.resultado.orden
                            if entity.resultado.orden is not None
                            else 10**9,
                            str(entity.id),
                        ),
                        row,
                    )
                )
        return [row for _, row in sorted(sortable, key=lambda item: item[0])]

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

    @staticmethod
    def _assignment_pairs(
        entity: PlaneacionPedagogica,
    ) -> list[tuple[uuid.UUID, uuid.UUID]]:
        pairs: list[tuple[uuid.UUID, uuid.UUID]] = []
        raw_assignments = entity.datos_complementarios.get("asignaciones_proyecto")
        if isinstance(raw_assignments, list):
            for raw in raw_assignments:
                if not isinstance(raw, dict):
                    continue
                try:
                    pair = (
                        uuid.UUID(str(raw.get("fase_id"))),
                        uuid.UUID(str(raw.get("actividad_id"))),
                    )
                except (TypeError, ValueError):
                    continue
                if pair not in pairs:
                    pairs.append(pair)
        if not pairs and entity.fase_id and entity.actividad_id:
            pairs.append((entity.fase_id, entity.actividad_id))
        return pairs

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

    @staticmethod
    def _map_config(
        proyecto: ProyectoFormativo,
        config: PlaneacionDocumentoConfig | None,
    ) -> PlaneacionDocumentoConfigDTO:
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

    async def eliminar_planeacion(self, planeacion_id: uuid.UUID) -> None:
        """Remove planning record from DB and its file from MinIO."""
        entity = await self._repository.get_by_id(planeacion_id)
        if entity is None:
            return

        # Delete database record
        await self._repository.delete(entity)

    async def _ensure_project_complete(self, proyecto_id: uuid.UUID) -> None:
        proyecto = await self._session.get(ProyectoFormativo, proyecto_id)
        if proyecto is None:
            raise ValueError(f"No existe el proyecto formativo {proyecto_id}")
        if proyecto.estado != EstadoBloque.COMPLETO:
            raise PlaneacionAccessError(
                "La planeacion pedagogica solo puede iniciarse cuando "
                "el proyecto esta COMPLETO"
            )

    def _map_to_response_dto(
        self, entity: PlaneacionPedagogica
    ) -> PlaneacionResponseDTO:
        """Map PlaneacionPedagogica ORM model to PlaneacionResponseDTO."""
        return PlaneacionResponseDTO(
            id=entity.id,
            proyecto_id=entity.proyecto_id,
            competencia_id=entity.competencia_id,
            resultado_id=entity.resultado_id,
            resultado_descripcion=entity.resultado.descripcion
            if entity.resultado
            else None,
            fase_id=entity.fase_id,
            actividad_id=entity.actividad_id,
            estado=entity.estado.value,
            datos_complementarios=entity.datos_complementarios,
            resultados_ids=[r.id for r in entity.resultados],
            conocimientos_ids=[k.id for k in entity.conocimientos],
            criterios_ids=[cr.id for cr in entity.criterios],
            storage_key=entity.storage_key,
            file_name=entity.file_name,
            content_type=entity.content_type,
            checksum_sha256=entity.checksum_sha256,
            fecha_generacion=entity.fecha_generacion,
            version=entity.version,
        )
