"""Service to recursively clean training program and project cargues."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque
from src.infrastructure.db.models.curriculum import ProgramaFormacion
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.proyecto import ProyectoFormativo
from src.infrastructure.storage.document_storage import (
    build_programa_storage_prefix,
    build_proyecto_storage_prefix,
    sanitize_directory_name,
)


class DocumentStorageProtocol(Protocol):
    """Storage port for deleting files."""

    async def delete_by_prefix(self, *, prefix: str) -> None:
        """Remove all objects matching the prefix from the bucket."""


def _planeaciones_storage_prefix(
    *, nombre_programa: str, nombre_proyecto: str
) -> str:
    """Build the legible prefix that stores integrated planning workbooks."""
    programa_dir = sanitize_directory_name(nombre_programa)
    proyecto_dir = sanitize_directory_name(nombre_proyecto)
    return f"planeaciones-pedagogicas/{programa_dir}/{proyecto_dir}/"


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

        nombre_prog = None
        codigo_prog = None
        version_prog = None
        nombre_proj = None
        codigo_proj = None

        if draft_programa is not None and isinstance(draft_programa.payload_json, dict):
            prog_payload = draft_programa.payload_json.get("programa")
            if isinstance(prog_payload, dict):
                nombre_prog = prog_payload.get("nombre_programa")
                codigo_prog = prog_payload.get("codigo_programa")
                version_prog = prog_payload.get("version_programa")

        if draft_proyecto is not None and isinstance(draft_proyecto.payload_json, dict):
            proj_payload = draft_proyecto.payload_json.get("proyecto")
            if isinstance(proj_payload, dict):
                nombre_proj = proj_payload.get("nombre_proyecto")
                codigo_proj = proj_payload.get("codigo_proyecto")

        # 2. If we have programa_id, find the other draft and delete DB records
        if programa_id is not None:
            programa_db = await self._session.get(ProgramaFormacion, programa_id)
            # Delete relational project formativo first (due to foreign key constraint)
            proj_db_statement = select(ProyectoFormativo).where(
                ProyectoFormativo.programa_id == programa_id
            )
            proj_db_result = await self._session.execute(proj_db_statement)
            proyectos_db = proj_db_result.scalars().all()
            for proyecto_db in proyectos_db:
                nombre_proj = proyecto_db.nombre_proyecto
                codigo_proj = proyecto_db.codigo_proyecto
                await self._storage_service.delete_by_prefix(
                    prefix=f"planeaciones-pedagogicas/{programa_id}/{proyecto_db.id}/"
                )
                if programa_db is not None:
                    await self._storage_service.delete_by_prefix(
                        prefix=_planeaciones_storage_prefix(
                            nombre_programa=programa_db.nombre_programa,
                            nombre_proyecto=proyecto_db.nombre_proyecto,
                        )
                    )
                await self._session.delete(proyecto_db)

            # Delete relational program
            if programa_db is not None:
                nombre_prog = programa_db.nombre_programa
                codigo_prog = programa_db.codigo_programa
                version_prog = programa_db.version_programa
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
        for storage_key in _collect_storage_keys_from_drafts(
            draft_programa,
            draft_proyecto,
        ):
            await self._storage_service.delete_by_prefix(prefix=storage_key)

        if nombre_prog and codigo_prog:
            prefix_prog = build_programa_storage_prefix(
                nombre=str(nombre_prog),
                codigo=str(codigo_prog),
                version=str(version_prog) if version_prog else "1",
            )
            await self._storage_service.delete_by_prefix(prefix=f"{prefix_prog}/")

        if programa_ref_id is not None:
            await self._storage_service.delete_by_prefix(
                prefix=f"programas/{programa_ref_id}/"
            )

        if nombre_proj and codigo_proj:
            prefix_proj = build_proyecto_storage_prefix(
                nombre=str(nombre_proj), codigo=str(codigo_proj)
            )
            await self._storage_service.delete_by_prefix(prefix=f"{prefix_proj}/")

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

    async def eliminar_cargue_proyecto(self, referencia_id: uuid.UUID) -> None:
        """Delete project formativo records and files, then reset project draft."""
        # 1. Identify the source drafts
        draft_proj = await self._session.execute(
            select(BorradorSesion).where(
                BorradorSesion.referencia_id == referencia_id,
                BorradorSesion.tipo_bloque == TipoBloqueBorrador.PROYECTO,
            )
        )
        draft_proyecto = draft_proj.scalar_one_or_none()

        programa_id = None
        if draft_proyecto is not None:
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

        nombre_proj = None
        codigo_proj = None
        if draft_proyecto is not None and isinstance(draft_proyecto.payload_json, dict):
            proj_payload = draft_proyecto.payload_json.get("proyecto")
            if isinstance(proj_payload, dict):
                nombre_proj = proj_payload.get("nombre_proyecto")
                codigo_proj = proj_payload.get("codigo_proyecto")

        # 2. If we have programa_id, find the project in DB and delete it
        if programa_id is not None:
            programa_db = await self._session.get(ProgramaFormacion, programa_id)
            proj_db_statement = select(ProyectoFormativo).where(
                ProyectoFormativo.programa_id == programa_id
            )
            proj_db_result = await self._session.execute(proj_db_statement)
            proyecto_db = proj_db_result.scalar_one_or_none()
            if proyecto_db is not None:
                nombre_proj = proyecto_db.nombre_proyecto
                codigo_proj = proyecto_db.codigo_proyecto
                # Delete pedagogical plannings from MinIO first
                await self._storage_service.delete_by_prefix(
                    prefix=f"planeaciones-pedagogicas/{programa_id}/{proyecto_db.id}/"
                )
                if programa_db is not None:
                    await self._storage_service.delete_by_prefix(
                        prefix=_planeaciones_storage_prefix(
                            nombre_programa=programa_db.nombre_programa,
                            nombre_proyecto=proyecto_db.nombre_proyecto,
                        )
                    )
                await self._session.delete(proyecto_db)
            await self._session.flush()

        # 3. Clean project files from MinIO
        for storage_key in _collect_storage_keys_from_drafts(draft_proyecto):
            await self._storage_service.delete_by_prefix(prefix=storage_key)

        if nombre_proj and codigo_proj:
            prefix_proj = build_proyecto_storage_prefix(
                nombre=str(nombre_proj), codigo=str(codigo_proj)
            )
            await self._storage_service.delete_by_prefix(prefix=f"{prefix_proj}/")

        if referencia_id is not None:
            await self._storage_service.delete_by_prefix(
                prefix=f"proyectos-formativos/{referencia_id}/"
            )

        # 4. Reset project draft to initial state
        now = datetime.now(UTC).isoformat()
        if draft_proyecto is not None:
            from typing import Any, cast

            proj_payload = cast(dict[str, Any], draft_proyecto.payload_json)
            draft_proyecto.paso_actual = "fuente-proyecto"
            draft_proyecto.estado_borrador = EstadoBloque.BORRADOR
            draft_proyecto.payload_json = {
                "meta": {
                    "referenciaId": str(referencia_id),
                    "programaReferenciaId": proj_payload.get("meta", {}).get(
                        "programaReferenciaId"
                    ),
                    "programaId": str(programa_id) if programa_id else None,
                    "touchedSteps": ["fuente-proyecto"],
                    "lastInteractionAt": now,
                },
                "wizard": {
                    "notesByStep": {},
                },
                "proyecto": {
                    "proyecto_formativo_id": None,
                    "codigo_proyecto": "",
                    "nombre_proyecto": "",
                    "version_proyecto": "",
                },
                "documental": {
                    "proyecto_pdf": None,
                    "fuente_estructurada": None,
                },
                "estructura": {
                    "fases": [],
                    "actividades": [],
                },
            }
            self._session.add(draft_proyecto)
            await self._session.flush()


def _collect_storage_keys_from_drafts(
    *drafts: BorradorSesion | None,
) -> list[str]:
    """Collect exact MinIO object keys stored in draft payload metadata."""
    storage_keys: set[str] = set()
    for draft in drafts:
        if draft is not None:
            _collect_storage_keys(draft.payload_json, storage_keys)
    return sorted(storage_keys)


def _collect_storage_keys(value: object, storage_keys: set[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == "storage_key" and isinstance(child, str) and child.strip():
                storage_keys.add(child.strip())
                continue
            _collect_storage_keys(child, storage_keys)
        return

    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for child in value:
            _collect_storage_keys(child, storage_keys)
