"""DTOs for program PDF upload and diagnosis."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.domain.programa.documentos import EstadoLegibilidadPdf
from src.domain.shared.enums import MotivoFalloExtraccion


@dataclass(frozen=True)
class StoredDocumentDTO:
    """Metadata returned after storing a PDF object."""

    original_filename: str
    storage_key: str
    size_bytes: int
    content_type: str
    checksum_sha256: str
    etag: str | None = None


@dataclass(frozen=True)
class PdfLegibilityDiagnosticDTO:
    """Structured result of the PDF text-layer diagnosis."""

    estado_legibilidad: EstadoLegibilidadPdf
    motivo: MotivoFalloExtraccion | None
    resumen: str
    has_text_layer: bool
    analyzed_pages: int
    pages_with_text: int
    text_character_count: int
    can_attempt_extraction: bool
    requires_manual_entry: bool


@dataclass(frozen=True)
class ProgramaPdfUploadResultDTO:
    """Result returned by the program PDF upload use case."""

    referencia_id: uuid.UUID
    documento: StoredDocumentDTO
    diagnostico: PdfLegibilityDiagnosticDTO
