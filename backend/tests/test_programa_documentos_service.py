"""Tests for program PDF upload, storage and draft association."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from src.application.dto.programa_documentos import (
    PdfLegibilityDiagnosticDTO,
    StoredDocumentDTO,
)
from src.application.services.programa_documentos import (
    InvalidProgramPdfUploadError,
    ProgramaDocumentService,
    ProgramaDraftMissingError,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.programa.documentos import EstadoLegibilidadPdf
from src.domain.shared.enums import EstadoBloque
from src.infrastructure.db.models.drafts import BorradorSesion


class FakeSession:
    """Minimal async session stub for the document service."""

    def __init__(self) -> None:
        """Track commits."""
        self.commits = 0

    async def commit(self) -> None:
        """Record a commit invocation."""
        self.commits += 1

    async def refresh(self, instance: object) -> None:
        """Populate update timestamp when refreshing a draft."""
        assert isinstance(instance, BorradorSesion)
        instance.ultima_edicion = datetime.now(UTC)


class FakeDraftRepository:
    """In-memory draft repository keyed by logical block identity."""

    def __init__(self, draft: BorradorSesion | None) -> None:
        """Store one optional draft."""
        self.draft = draft

    async def get_by_block_reference(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
    ) -> BorradorSesion | None:
        """Return the draft when the logical key matches."""
        if (
            self.draft is not None
            and self.draft.tipo_bloque == tipo_bloque.value
            and self.draft.referencia_id == referencia_id
        ):
            return self.draft
        return None

    async def save(self, draft: BorradorSesion) -> BorradorSesion:
        """Persist the draft in memory."""
        self.draft = draft
        return draft


class FakeAuditRepository:
    """Collect emitted audit events."""

    def __init__(self) -> None:
        """Initialize empty audit storage."""
        self.events: list[dict[str, Any]] = []

    async def add_event(
        self,
        entidad: str,
        entidad_id: uuid.UUID,
        accion: str,
        detalle: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        """Append an audit event."""
        event = {
            "entidad": entidad,
            "entidad_id": entidad_id,
            "accion": accion,
            "detalle": detalle,
        }
        self.events.append(event)
        return event


class FakeStorageService:
    """Fake document storage that returns deterministic metadata."""

    async def save_pdf(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        original_filename: str,
    ) -> StoredDocumentDTO:
        """Return metadata without contacting MinIO."""
        return StoredDocumentDTO(
            original_filename=original_filename,
            storage_key=key,
            size_bytes=len(content),
            content_type=content_type,
            checksum_sha256="abc123",
            etag="etag-1",
        )


class FakeDiagnosticService:
    """Fake PDF diagnostic returning a legible result."""

    def diagnose(self, content: bytes) -> PdfLegibilityDiagnosticDTO:
        """Return a structured diagnosis."""
        return PdfLegibilityDiagnosticDTO(
            estado_legibilidad=EstadoLegibilidadPdf.LEGIBLE,
            motivo=None,
            resumen="PDF legible",
            has_text_layer=True,
            analyzed_pages=1,
            pages_with_text=1,
            text_character_count=120,
            can_attempt_extraction=True,
            requires_manual_entry=False,
        )


def build_draft(referencia_id: uuid.UUID) -> BorradorSesion:
    """Create a program draft ORM object for tests."""
    draft = BorradorSesion(
        tipo_bloque=TipoBloqueBorrador.PROGRAMA.value,
        referencia_id=referencia_id,
        paso_actual="datos-programa",
        payload_json={
            "meta": {
                "referenciaId": str(referencia_id),
                "entryMode": "MANUAL",
                "touchedSteps": ["datos-programa"],
            },
        },
        estado_borrador=EstadoBloque.BORRADOR,
    )
    draft.id = uuid.uuid4()
    draft.ultima_edicion = datetime.now(UTC)
    return draft


@pytest.mark.anyio
async def test_upload_program_pdf_updates_existing_draft_payload() -> None:
    """A valid PDF should be stored and associated to the same draft reference."""
    referencia_id = uuid.uuid4()
    draft_repository = FakeDraftRepository(build_draft(referencia_id))
    audit_repository = FakeAuditRepository()
    session = FakeSession()
    service = ProgramaDocumentService(
        session=session,
        draft_repository=draft_repository,
        audit_repository=audit_repository,
        storage_service=FakeStorageService(),
        diagnostic_service=FakeDiagnosticService(),
    )

    result = await service.upload_and_diagnose_program_pdf(
        referencia_id=referencia_id,
        filename="programa.pdf",
        content_type="application/pdf",
        content=b"%PDF-1.4 fake test content",
    )

    assert result.referencia_id == referencia_id
    assert result.diagnostico.estado_legibilidad is EstadoLegibilidadPdf.LEGIBLE
    assert draft_repository.draft is not None
    assert draft_repository.draft.paso_actual == "origen-documental"
    assert draft_repository.draft.payload_json["meta"]["entryMode"] == "PDF"
    assert "programa_pdf" in draft_repository.draft.payload_json["documental"]
    assert session.commits == 1
    assert audit_repository.events[0]["accion"] == "DOCUMENTO_PROGRAMA_DIAGNOSTICADO"


@pytest.mark.anyio
async def test_upload_program_pdf_rejects_missing_draft() -> None:
    """The service must not generate a new referencia_id or implicit draft."""
    service = ProgramaDocumentService(
        session=FakeSession(),
        draft_repository=FakeDraftRepository(None),
        audit_repository=FakeAuditRepository(),
        storage_service=FakeStorageService(),
        diagnostic_service=FakeDiagnosticService(),
    )

    with pytest.raises(ProgramaDraftMissingError):
        await service.upload_and_diagnose_program_pdf(
            referencia_id=uuid.uuid4(),
            filename="programa.pdf",
            content_type="application/pdf",
            content=b"%PDF-1.4 fake test content",
        )


@pytest.mark.anyio
async def test_upload_program_pdf_rejects_non_pdf() -> None:
    """Non-PDF uploads should fail before storage or diagnosis."""
    service = ProgramaDocumentService(
        session=FakeSession(),
        draft_repository=FakeDraftRepository(build_draft(uuid.uuid4())),
        audit_repository=FakeAuditRepository(),
        storage_service=FakeStorageService(),
        diagnostic_service=FakeDiagnosticService(),
    )

    with pytest.raises(InvalidProgramPdfUploadError):
        await service.upload_and_diagnose_program_pdf(
            referencia_id=uuid.uuid4(),
            filename="programa.txt",
            content_type="text/plain",
            content=b"not a pdf",
        )
