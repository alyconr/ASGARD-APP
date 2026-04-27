"""HTTP schemas for program PDF uploads."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from src.domain.programa.documentos import EstadoLegibilidadPdf
from src.domain.shared.enums import MotivoFalloExtraccion


class StoredDocumentResponse(BaseModel):
    """Metadata of the stored PDF object."""

    model_config = ConfigDict(from_attributes=True)

    original_filename: str
    storage_key: str
    size_bytes: int
    content_type: str
    checksum_sha256: str
    etag: str | None = None


class PdfLegibilityDiagnosticResponse(BaseModel):
    """Structured PDF legibility result."""

    model_config = ConfigDict(from_attributes=True)

    estado_legibilidad: EstadoLegibilidadPdf
    motivo: MotivoFalloExtraccion | None
    resumen: str
    has_text_layer: bool
    analyzed_pages: int
    pages_with_text: int
    text_character_count: int
    can_attempt_extraction: bool
    requires_manual_entry: bool


class ProgramaPdfUploadResponse(BaseModel):
    """Response returned after upload, storage and diagnosis."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    documento: StoredDocumentResponse
    diagnostico: PdfLegibilityDiagnosticResponse
