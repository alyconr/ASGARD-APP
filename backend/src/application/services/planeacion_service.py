"""Application service for Pedagogical Planning management."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Protocol

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
    PlaneacionContextoDTO,
    PlaneacionListDTO,
    PlaneacionResponseDTO,
    PlaneacionSaveDTO,
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
from src.infrastructure.db.models.planeacion import PlaneacionPedagogica
from src.infrastructure.db.models.proyecto import FaseProyecto, ProyectoFormativo
from src.infrastructure.repositories.planeacion import PlaneacionPedagogicaRepository


class DocumentStorageProtocol(Protocol):
    """Storage protocol for saving pedagogical planning documents."""

    async def save_pdf(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        original_filename: str,
    ) -> object:
        """Upload a PDF or representational document to the store."""


class PlaneacionPedagogicaService:
    """Orchestrate CRUD, state transitions, and file generations
    for Pedagogical Planning.
    """

    def __init__(
        self,
        session: AsyncSession,
        repository: PlaneacionPedagogicaRepository,
        storage_service: DocumentStorageProtocol,
    ) -> None:
        """Initialize the service with database session, repo, and storage client."""
        self._session = session
        self._repository = repository
        self._storage_service = storage_service

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

        if proyecto.estado == EstadoBloque.BLOQUEADO:
            # Auto-heal: If the project was already imported in the database,
            # it should not be blocked anymore. Set it to BORRADOR.
            proyecto.estado = EstadoBloque.BORRADOR
            self._session.add(proyecto)
            await self._session.commit()

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
            res_dtos = [
                ContextoResultadoDTO(id=r.id, descripcion=r.descripcion)
                for r in c.resultados
            ]
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
            proyecto_id=proyecto.id,
            codigo_proyecto=proyecto.codigo_proyecto,
            nombre_proyecto=proyecto.nombre_proyecto,
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
        entity = await self._repository.get_by_proyecto_and_competencia(
            dto.proyecto_id,
            dto.competencia_id,
        )
        if entity is None:
            entity = PlaneacionPedagogica(
                proyecto_id=dto.proyecto_id,
                competencia_id=dto.competencia_id,
            )

        entity.fase_id = dto.fase_id
        entity.actividad_id = dto.actividad_id
        entity.estado = EstadoBloque.BORRADOR
        entity.datos_complementarios = dto.datos_complementarios

        # Fetch and link relations
        if dto.resultados_ids:
            res_stmt = select(ResultadoAprendizaje).where(
                ResultadoAprendizaje.id.in_(dto.resultados_ids)
            )
            res_query = await self._session.execute(res_stmt)
            entity.resultados = list(res_query.scalars().all())
        else:
            entity.resultados = []

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
        """Transition planning state to complete and upload a
        representational file to MinIO.
        """
        entity = await self._repository.get_by_id(planeacion_id)
        if entity is None:
            raise ValueError(
                f"No existe la planeación pedagógica con id {planeacion_id}"
            )

        entity.estado = EstadoBloque.COMPLETO
        entity.fecha_generacion = datetime.now(UTC)

        # Generate JSON content representing the document
        doc_payload = {
            "planeacion_id": str(entity.id),
            "programa_id": str(entity.proyecto.programa_id),
            "proyecto_id": str(entity.proyecto_id),
            "competencia": {
                "id": str(entity.competencia_id),
                "codigo": entity.competencia.codigo_competencia,
                "nombre": entity.competencia.nombre_competencia,
            },
            "fase": {
                "id": str(entity.fase_id) if entity.fase_id else None,
                "nombre": entity.fase.nombre_fase if entity.fase else None,
            },
            "actividad": {
                "id": str(entity.actividad_id) if entity.actividad_id else None,
                "descripcion": entity.actividad.descripcion
                if entity.actividad
                else None,
            },
            "resultados": [
                {"id": str(r.id), "descripcion": r.descripcion}
                for r in entity.resultados
            ],
            "conocimientos": [
                {"id": str(k.id), "tipo": k.tipo.value, "descripcion": k.descripcion}
                for k in entity.conocimientos
            ],
            "criterios": [
                {"id": str(cr.id), "descripcion": cr.descripcion}
                for cr in entity.criterios
            ],
            "datos_complementarios": entity.datos_complementarios,
            "version": entity.version,
            "fecha_aprobacion": entity.fecha_generacion.isoformat(),
        }

        content_bytes = json.dumps(doc_payload, indent=2, ensure_ascii=False).encode(
            "utf-8"
        )
        checksum = hashlib.sha256(content_bytes).hexdigest()

        # Define canonical prefix
        storage_key = (
            f"planeaciones-pedagogicas/"
            f"{entity.proyecto.programa_id}/"
            f"{entity.proyecto_id}/"
            f"{entity.competencia_id}/"
            f"planeacion.json"
        )
        file_name = f"planeacion_{entity.competencia.codigo_competencia}.json"

        # Save to storage (MinIO)
        await self._storage_service.save_pdf(
            key=storage_key,
            content=content_bytes,
            content_type="application/json",
            original_filename=file_name,
        )

        # Update ORM record
        entity.storage_key = storage_key
        entity.file_name = file_name
        entity.content_type = "application/json"
        entity.checksum_sha256 = checksum

        await self._repository.save(entity)
        return self._map_to_response_dto(entity)

    async def eliminar_planeacion(self, planeacion_id: uuid.UUID) -> None:
        """Remove planning record from DB and its file from MinIO."""
        entity = await self._repository.get_by_id(planeacion_id)
        if entity is None:
            return

        # Delete database record
        await self._repository.delete(entity)

    def _map_to_response_dto(
        self, entity: PlaneacionPedagogica
    ) -> PlaneacionResponseDTO:
        """Map PlaneacionPedagogica ORM model to PlaneacionResponseDTO."""
        return PlaneacionResponseDTO(
            id=entity.id,
            proyecto_id=entity.proyecto_id,
            competencia_id=entity.competencia_id,
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
