"""Application service for project PDF evidence upload."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Protocol

from src.application.dto.programa_documentos import StoredDocumentDTO
from src.application.dto.proyecto_documentos import ProjectPdfUploadResultDTO
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque
from src.infrastructure.db.models.drafts import BorradorSesion


class ProjectDraftMissingError(Exception):
    """Raised when a project PDF upload has no current wizard draft."""


class InvalidProjectPdfUploadError(Exception):
    """Raised when the provided upload cannot be accepted."""


class DocumentStorageProtocol(Protocol):
    """Storage dependency required by the project document service."""

    async def save_pdf(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        original_filename: str,
    ) -> StoredDocumentDTO:
        """Persist a PDF and return object metadata."""


class DraftRepositoryProtocol(Protocol):
    """Draft repository dependency used to associate uploads to the wizard."""

    async def get_by_block_reference(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
    ) -> BorradorSesion | None:
        """Return the current logical draft for a reference."""

    async def save(self, draft: BorradorSesion) -> BorradorSesion:
        """Persist modifications on an existing draft row."""


class AuditRepositoryProtocol(Protocol):
    """Audit dependency for relevant document events."""

    async def add_event(
        self,
        entidad: str,
        entidad_id: uuid.UUID,
        accion: str,
        detalle: dict[str, object] | None = None,
    ) -> object:
        """Persist a basic audit event."""


class AsyncSessionProtocol(Protocol):
    """Subset of async session behavior required by this service."""

    async def commit(self) -> None:
        """Commit the current transaction."""

    async def refresh(self, instance: object) -> None:
        """Refresh the provided ORM instance."""


class ProjectDocumentService:
    """Coordinate project PDF evidence storage and draft persistence."""

    def __init__(
        self,
        session: AsyncSessionProtocol,
        draft_repository: DraftRepositoryProtocol,
        audit_repository: AuditRepositoryProtocol,
        storage_service: DocumentStorageProtocol,
    ) -> None:
        """Initialize the service with explicit infrastructure ports."""
        self._session = session
        self._draft_repository = draft_repository
        self._audit_repository = audit_repository
        self._storage_service = storage_service

    async def upload_and_store_project_pdf(
        self,
        *,
        referencia_id: uuid.UUID,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> ProjectPdfUploadResultDTO:
        """Store a project PDF as evidence and update the draft."""
        _validate_pdf_upload(
            filename=filename, content_type=content_type, content=content
        )

        draft = await self._draft_repository.get_by_block_reference(
            TipoBloqueBorrador.PROYECTO,
            referencia_id,
        )
        if draft is None:
            raise ProjectDraftMissingError(
                "No existe un borrador de proyecto para asociar el PDF",
            )

        storage_key = _build_storage_key(referencia_id, filename)
        stored_document = await self._storage_service.save_pdf(
            key=storage_key,
            content=content,
            content_type="application/pdf",
            original_filename=filename,
        )

        draft.payload_json = _merge_document_result_into_payload(
            payload=draft.payload_json,
            document=stored_document,
        )
        draft.paso_actual = "fuente-proyecto"
        draft.estado_borrador = EstadoBloque.BORRADOR
        await self._draft_repository.save(draft)
        await self._audit_repository.add_event(
            entidad="BorradorSesion",
            entidad_id=draft.id,
            accion="DOCUMENTO_PROYECTO_ALMACENADO",
            detalle={
                "referencia_id": str(referencia_id),
                "storage_key": stored_document.storage_key,
            },
        )
        await self._session.commit()
        await self._session.refresh(draft)

        return ProjectPdfUploadResultDTO(
            referencia_id=referencia_id,
            documento=stored_document,
        )


def _validate_pdf_upload(
    *,
    filename: str,
    content_type: str,
    content: bytes,
) -> None:
    """Reject missing, empty or non-PDF uploads."""
    if not filename.strip():
        raise InvalidProjectPdfUploadError("El archivo PDF es obligatorio")

    if not content:
        raise InvalidProjectPdfUploadError("El archivo PDF no puede estar vacio")

    normalized_content_type = content_type.lower().split(";")[0].strip()
    if normalized_content_type not in {"application/pdf", "application/x-pdf"}:
        raise InvalidProjectPdfUploadError("Solo se aceptan archivos PDF")

    if not filename.lower().endswith(".pdf"):
        raise InvalidProjectPdfUploadError("El archivo debe tener extension .pdf")


def _build_storage_key(referencia_id: uuid.UUID, filename: str) -> str:
    """Build the canonical project evidence prefix for MinIO objects."""
    safe_filename = re.sub(r"[^a-zA-Z0-9._-]+", "-", filename).strip("-")
    if not safe_filename:
        safe_filename = "proyecto.pdf"
    object_id = uuid.uuid4()
    return (
        f"proyectos-formativos/{referencia_id}/documentos/{object_id}-{safe_filename}"
    )


def _merge_document_result_into_payload(
    *,
    payload: dict[str, object],
    document: StoredDocumentDTO,
) -> dict[str, object]:
    """Persist only metadata in the draft payload."""
    next_payload = dict(payload)
    now = datetime.now(UTC).isoformat()

    meta = next_payload.get("meta")
    if isinstance(meta, dict):
        next_meta = dict(meta)
        next_meta["lastInteractionAt"] = now
        touched_steps = next_meta.get("touchedSteps")
        if isinstance(touched_steps, list):
            next_meta["touchedSteps"] = [
                *[step for step in touched_steps if isinstance(step, str)],
                *([] if "fuente-proyecto" in touched_steps else ["fuente-proyecto"]),
            ]
        else:
            next_meta["touchedSteps"] = ["fuente-proyecto"]
        next_payload["meta"] = next_meta

    documental = next_payload.get("documental")
    next_documental = dict(documental) if isinstance(documental, dict) else {}
    next_documental["proyecto_pdf"] = {
        "documento": {
            "original_filename": document.original_filename,
            "storage_key": document.storage_key,
            "size_bytes": document.size_bytes,
            "content_type": document.content_type,
            "checksum_sha256": document.checksum_sha256,
            "etag": document.etag,
        },
        "uso": "EVIDENCIA_DOCUMENTAL",
        "updated_at": now,
    }
    next_payload["documental"] = next_documental
    return next_payload
