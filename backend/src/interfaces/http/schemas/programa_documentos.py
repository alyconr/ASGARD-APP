"""HTTP schemas for program PDF uploads."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from src.domain.programa.documentos import EstadoLegibilidadPdf
from src.domain.shared.enums import EstadoCampo, MotivoFalloExtraccion


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


class ExtractedFieldResponse(BaseModel):
    """Traceable extraction response for a single field."""

    model_config = ConfigDict(from_attributes=True)

    campo: str
    valor: str | None
    estado: EstadoCampo
    motivo: MotivoFalloExtraccion | None
    requiere_revision: bool
    aplicado_al_borrador: bool
    valor_actual_borrador: str | None = None


class ExtractedTextItemResponse(BaseModel):
    """Traceable extraction response for a preliminary curricular item."""

    model_config = ConfigDict(from_attributes=True)

    valor: str
    estado: EstadoCampo
    motivo: MotivoFalloExtraccion | None
    requiere_revision: bool


class ExtractedListBlockResponse(BaseModel):
    """Traceable extraction response for a preliminary curricular collection."""

    model_config = ConfigDict(from_attributes=True)

    items: list[ExtractedTextItemResponse]
    estado: EstadoCampo
    motivo: MotivoFalloExtraccion | None
    requiere_revision: bool


class ProgramaBaseExtractionResponse(BaseModel):
    """Program base fields extracted from the PDF."""

    model_config = ConfigDict(from_attributes=True)

    codigo_programa: ExtractedFieldResponse
    nombre_programa: ExtractedFieldResponse


class ProgramaCurricularExtractionResponse(BaseModel):
    """Preliminary curricular structure extracted before CRUD tasks."""

    model_config = ConfigDict(from_attributes=True)

    competencias: ExtractedListBlockResponse
    resultados_aprendizaje: ExtractedListBlockResponse
    conocimientos_saber: ExtractedListBlockResponse
    conocimientos_proceso: ExtractedListBlockResponse
    criterios_evaluacion: ExtractedListBlockResponse


class ProgramaDraftFieldsResponse(BaseModel):
    """Program draft fields after applying the safe extraction merge."""

    model_config = ConfigDict(from_attributes=True)

    codigo_programa: str
    nombre_programa: str
    version_programa: str


class ProgramaExtractionResponse(BaseModel):
    """Response returned after TASK-07 extraction."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    estado_legibilidad: EstadoLegibilidadPdf
    resumen: str
    requiere_revision_humana: bool
    programa: ProgramaBaseExtractionResponse
    estructura_curricular: ProgramaCurricularExtractionResponse
    programa_actualizado: ProgramaDraftFieldsResponse
