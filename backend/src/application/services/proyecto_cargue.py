"""Service to recursively clean training program and project cargues."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque
from src.infrastructure.db.models.curriculum import ProgramaFormacion
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.proyecto import ProyectoFormativo


class DocumentStorageProtocol(Protocol):
    """Storage port for deleting files."""

    async def delete_by_prefix(self, *, prefix: str) -> None:
        """Remove all objects matching the prefix from the bucket."""


class ProyectoCargueService:
    """Clean relational training program, format projects, and MinIO uploads."""

    def __init__(
        self,
        session: AsyncSession,
        storage_service: DocumentStorageProtocol,
    ) -> None:
        """Initialize service with dependencies."""
        self._session = session
        self._storage_service = storage_service

    async def eliminar_cargue_completo(self, referencia_id: uuid.UUID) -> None:
        """Delete program, project data and MinIO files, resetting drafts."""
        # 1. Identify the source drafts
        draft_prog = await self._session.execute(
            select(BorradorSesion).where(
                BorradorSesion.referencia_id == referencia_id,
                BorradorSesion.tipo_bloque == TipoBloqueBorrador.PROGRAMA,
            )
        )
        draft_programa = draft_prog.scalar_one_or_none()

        draft_proj = await self._session.execute(
            select(BorradorSesion).where(
                BorradorSesion.referencia_id == referencia_id,
                BorradorSesion.tipo_bloque == TipoBloqueBorrador.PROYECTO,
            )
        )
        draft_proyecto = draft_proj.scalar_one_or_none()

        programa_id = None
        programa_ref_id = None
        proyecto_ref_id = None

        if draft_programa is not None:
            programa_ref_id = draft_programa.referencia_id
            payload = draft_programa.payload_json
            if isinstance(payload, dict):
                curricular = payload.get("curricular")
                if isinstance(curricular, dict):
                    raw_id = curricular.get("programa_formacion_id")
                    if raw_id:
                        try:
                            programa_id = uuid.UUID(str(raw_id))
                        except ValueError:
                            pass

        if draft_proyecto is not None:
            proyecto_ref_id = draft_proyecto.referencia_id
            payload = draft_proyecto.payload_json
            if isinstance(payload, dict):
                meta = payload.get("meta")
                if isinstance(meta, dict):
                    raw_id = meta.get("programaId")
                    if raw_id:
                        try:
                            programa_id = uuid.UUID(str(raw_id))
                        except ValueError:
                            pass

        # 2. If we have programa_id, find the other draft and delete DB records
        if programa_id is not None:
            # Delete relational project formativo first (due to foreign key constraint)
            proj_db_statement = select(ProyectoFormativo).where(
                ProyectoFormativo.programa_id == programa_id
            )
            proj_db_result = await self._session.execute(proj_db_statement)
            proyecto_db = proj_db_result.scalar_one_or_none()
            if proyecto_db is not None:
                await self._session.delete(proyecto_db)

            # Delete relational program
            programa_db = await self._session.get(ProgramaFormacion, programa_id)
            if programa_db is not None:
                await self._session.delete(programa_db)

            await self._session.flush()

            # Find program draft if not set yet
            if draft_programa is None:
                all_program_drafts = await self._session.execute(
                    select(BorradorSesion).where(
                        BorradorSesion.tipo_bloque == TipoBloqueBorrador.PROGRAMA
                    )
                )
                for d in all_program_drafts.scalars():
                    payload_d = d.payload_json
                    if isinstance(payload_d, dict):
                        curr = payload_d.get("curricular")
                        if isinstance(curr, dict):
                            if curr.get("programa_formacion_id") == str(programa_id):
                                draft_programa = d
                                programa_ref_id = d.referencia_id
                                break

            # Find project draft if not set yet
            if draft_proyecto is None:
                all_project_drafts = await self._session.execute(
                    select(BorradorSesion).where(
                        BorradorSesion.tipo_bloque == TipoBloqueBorrador.PROYECTO
                    )
                )
                for d in all_project_drafts.scalars():
                    payload_d = d.payload_json
                    if isinstance(payload_d, dict):
                        m = payload_d.get("meta")
                        if isinstance(m, dict):
                            if m.get("programaId") == str(programa_id):
                                draft_proyecto = d
                                proyecto_ref_id = d.referencia_id
                                break

        # 3. Clean files from MinIO
        if programa_ref_id is not None:
            await self._storage_service.delete_by_prefix(
                prefix=f"programas/{programa_ref_id}/"
            )
        if proyecto_ref_id is not None:
            await self._storage_service.delete_by_prefix(
                prefix=f"proyectos-formativos/{proyecto_ref_id}/"
            )

        # 4. Reset drafts to initial states
        now = datetime.now(UTC).isoformat()
        if draft_programa is not None:
            draft_programa.paso_actual = "origen-documental"
            draft_programa.estado_borrador = EstadoBloque.BORRADOR
            draft_programa.payload_json = {
                "meta": {
                    "touchedSteps": ["origen-documental"],
                    "lastInteractionAt": now,
                },
                "documental": {},
                "curricular": {},
            }
            self._session.add(draft_programa)

        if draft_proyecto is not None:
            draft_proyecto.paso_actual = "fuente-proyecto"
            draft_proyecto.estado_borrador = EstadoBloque.BLOQUEADO
            draft_proyecto.payload_json = {
                "meta": {
                    "touchedSteps": ["fuente-proyecto"],
                    "lastInteractionAt": now,
                    "programaId": str(programa_id) if programa_id else None,
                },
                "documental": {},
                "planeacion": {},
            }
            self._session.add(draft_proyecto)

        await self._session.flush()
