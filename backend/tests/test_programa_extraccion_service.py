"""Tests for TASK-07 program PDF hybrid extraction."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from src.application.services.programa_extraccion import (
    ProgramaExtractionService,
    ProgramaPdfMissingForExtractionError,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.programa.documentos import EstadoLegibilidadPdf
from src.domain.shared.enums import EstadoBloque, EstadoCampo
from src.infrastructure.db.models.drafts import BorradorSesion


class FakeSession:
    """Minimal async session stub for extraction tests."""

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


class FakeDocumentReader:
    """Fake storage reader returning deterministic PDF bytes."""

    def __init__(self) -> None:
        """Initialize read count."""
        self.reads = 0

    async def read_pdf(self, *, key: str) -> bytes:
        """Return fake bytes and record reads."""
        assert key == "programas/ref/documentos/programa.pdf"
        self.reads += 1
        return b"%PDF fake"


class FakeTextExtractor:
    """Fake PDF text extraction dependency."""

    def __init__(self, text: str) -> None:
        """Store deterministic text."""
        self.text = text

    def extract_text(self, content: bytes) -> str:
        """Return configured text."""
        assert content == b"%PDF fake"
        return self.text


def build_draft(
    referencia_id: uuid.UUID,
    *,
    legibility: EstadoLegibilidadPdf = EstadoLegibilidadPdf.LEGIBLE,
    codigo_programa: str = "",
    nombre_programa: str = "",
    with_document: bool = True,
) -> BorradorSesion:
    """Create a program draft ORM object with optional PDF metadata."""
    payload: dict[str, object] = {
        "meta": {
            "referenciaId": str(referencia_id),
            "entryMode": "PDF",
            "touchedSteps": ["datos-programa", "origen-documental"],
        },
        "programa": {
            "codigo_programa": codigo_programa,
            "nombre_programa": nombre_programa,
            "version_programa": "",
        },
        "documental": {},
    }
    if with_document:
        payload["documental"] = {
            "programa_pdf": {
                "documento": {
                    "original_filename": "programa.pdf",
                    "storage_key": "programas/ref/documentos/programa.pdf",
                    "size_bytes": 1024,
                    "content_type": "application/pdf",
                    "checksum_sha256": "abc123",
                    "etag": "etag",
                },
                "diagnostico": {
                    "estado_legibilidad": legibility.value,
                    "motivo": None,
                    "resumen": "PDF legible",
                    "has_text_layer": legibility is not EstadoLegibilidadPdf.NO_LEGIBLE,
                    "analyzed_pages": 1,
                    "pages_with_text": 1
                    if legibility is not EstadoLegibilidadPdf.NO_LEGIBLE
                    else 0,
                    "text_character_count": 120
                    if legibility is not EstadoLegibilidadPdf.NO_LEGIBLE
                    else 0,
                    "can_attempt_extraction": legibility
                    is not EstadoLegibilidadPdf.NO_LEGIBLE,
                    "requires_manual_entry": legibility
                    is EstadoLegibilidadPdf.NO_LEGIBLE,
                },
            },
        }
    draft = BorradorSesion(
        tipo_bloque=TipoBloqueBorrador.PROGRAMA.value,
        referencia_id=referencia_id,
        paso_actual="origen-documental",
        payload_json=payload,
        estado_borrador=EstadoBloque.BORRADOR,
    )
    draft.id = uuid.uuid4()
    draft.ultima_edicion = datetime.now(UTC)
    return draft


@pytest.mark.anyio
async def test_extract_program_pdf_prefills_empty_base_fields() -> None:
    """Extraction should prefill empty base fields and keep the same reference."""
    referencia_id = uuid.uuid4()
    draft_repository = FakeDraftRepository(build_draft(referencia_id))
    reader = FakeDocumentReader()
    service = ProgramaExtractionService(
        session=FakeSession(),
        draft_repository=draft_repository,
        audit_repository=FakeAuditRepository(),
        document_reader=reader,
        text_extractor=FakeTextExtractor(
            "\n".join(
                [
                    "Codigo del programa: 228118",
                    "Denominacion del programa: Analisis y Desarrollo de Software",
                    "Competencia: Construir software de acuerdo con requisitos",
                    "Resultado de aprendizaje: Validar la solucion de software",
                    "Conocimiento de saber: Arquitectura de software",
                    "Conocimiento de proceso: Elaborar componentes",
                    "Criterio de evaluacion: Verifica cumplimiento de requisitos",
                ],
            ),
        ),
    )

    result = await service.extract_program_from_pdf(referencia_id=referencia_id)

    assert result.referencia_id == referencia_id
    assert result.programa.codigo_programa.valor == "228118"
    assert result.programa.codigo_programa.estado is EstadoCampo.EXTRAIDO
    assert result.programa.codigo_programa.aplicado_al_borrador is True
    assert result.programa_actualizado.codigo_programa == "228118"
    assert result.programa_actualizado.nombre_programa == (
        "Analisis y Desarrollo de Software"
    )
    assert result.estructura_curricular.competencias.items
    assert reader.reads == 1
    assert draft_repository.draft is not None
    assert (
        draft_repository.draft.payload_json["documental"]["programa_pdf"]["extraccion"][
            "programa"
        ]["codigo_programa"]["estado"]
        == "EXTRAIDO"
    )


@pytest.mark.anyio
async def test_extract_program_pdf_preserves_manual_values() -> None:
    """Extraction must not overwrite existing manual draft values."""
    referencia_id = uuid.uuid4()
    draft_repository = FakeDraftRepository(
        build_draft(
            referencia_id,
            codigo_programa="MANUAL-01",
            nombre_programa="Nombre manual",
        ),
    )
    service = ProgramaExtractionService(
        session=FakeSession(),
        draft_repository=draft_repository,
        audit_repository=FakeAuditRepository(),
        document_reader=FakeDocumentReader(),
        text_extractor=FakeTextExtractor(
            "Codigo del programa: 228118\n"
            "Denominacion del programa: Analisis y Desarrollo de Software",
        ),
    )

    result = await service.extract_program_from_pdf(referencia_id=referencia_id)

    assert result.programa.codigo_programa.aplicado_al_borrador is False
    assert result.programa.codigo_programa.motivo is not None
    assert result.programa_actualizado.codigo_programa == "MANUAL-01"
    assert result.programa_actualizado.nombre_programa == "Nombre manual"


@pytest.mark.anyio
async def test_extract_program_pdf_no_legible_skips_storage_read() -> None:
    """A non-legible PDF should produce fallback data without blind extraction."""
    referencia_id = uuid.uuid4()
    reader = FakeDocumentReader()
    service = ProgramaExtractionService(
        session=FakeSession(),
        draft_repository=FakeDraftRepository(
            build_draft(
                referencia_id,
                legibility=EstadoLegibilidadPdf.NO_LEGIBLE,
            ),
        ),
        audit_repository=FakeAuditRepository(),
        document_reader=reader,
        text_extractor=FakeTextExtractor(""),
    )

    result = await service.extract_program_from_pdf(referencia_id=referencia_id)

    assert result.estado_legibilidad is EstadoLegibilidadPdf.NO_LEGIBLE
    assert result.programa.codigo_programa.estado is EstadoCampo.PENDIENTE
    assert result.estructura_curricular.competencias.estado is EstadoCampo.PENDIENTE
    assert reader.reads == 0


@pytest.mark.anyio
async def test_extract_program_pdf_requires_existing_document() -> None:
    """Extraction should fail clearly when TASK-06 has not attached a PDF."""
    referencia_id = uuid.uuid4()
    service = ProgramaExtractionService(
        session=FakeSession(),
        draft_repository=FakeDraftRepository(
            build_draft(referencia_id, with_document=False),
        ),
        audit_repository=FakeAuditRepository(),
        document_reader=FakeDocumentReader(),
        text_extractor=FakeTextExtractor(""),
    )

    with pytest.raises(ProgramaPdfMissingForExtractionError):
        await service.extract_program_from_pdf(referencia_id=referencia_id)
