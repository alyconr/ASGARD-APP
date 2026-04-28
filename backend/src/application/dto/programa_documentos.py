"""DTOs for program PDF upload and diagnosis."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.domain.programa.documentos import EstadoLegibilidadPdf
from src.domain.shared.enums import EstadoCampo, MotivoFalloExtraccion


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


@dataclass(frozen=True)
class ExtractedFieldDTO:
    """Traceable extraction result for a single field."""

    campo: str
    valor: str | None
    estado: EstadoCampo
    motivo: MotivoFalloExtraccion | None
    requiere_revision: bool
    aplicado_al_borrador: bool
    valor_actual_borrador: str | None = None


@dataclass(frozen=True)
class ExtractedTextItemDTO:
    """Traceable extraction result for one preliminary curricular item."""

    valor: str
    estado: EstadoCampo
    motivo: MotivoFalloExtraccion | None
    requiere_revision: bool


@dataclass(frozen=True)
class ExtractedListBlockDTO:
    """Traceable extraction result for a preliminary curricular collection."""

    items: list[ExtractedTextItemDTO]
    estado: EstadoCampo
    motivo: MotivoFalloExtraccion | None
    requiere_revision: bool


@dataclass(frozen=True)
class ProgramaBaseExtractionDTO:
    """Program base fields extracted from the PDF."""

    codigo_programa: ExtractedFieldDTO
    nombre_programa: ExtractedFieldDTO


@dataclass(frozen=True)
class ProgramaCurricularExtractionDTO:
    """Preliminary curricular structure extracted before CRUD tasks."""

    competencias: ExtractedListBlockDTO
    resultados_aprendizaje: ExtractedListBlockDTO
    conocimientos_saber: ExtractedListBlockDTO
    conocimientos_proceso: ExtractedListBlockDTO
    criterios_evaluacion: ExtractedListBlockDTO


@dataclass(frozen=True)
class ProgramaDraftFieldsDTO:
    """Program draft fields after applying the safe extraction merge."""

    codigo_programa: str
    nombre_programa: str
    version_programa: str


@dataclass(frozen=True)
class ProgramaExtractionResultDTO:
    """Structured result returned by the TASK-07 extraction use case."""

    referencia_id: uuid.UUID
    estado_legibilidad: EstadoLegibilidadPdf
    resumen: str
    requiere_revision_humana: bool
    programa: ProgramaBaseExtractionDTO
    estructura_curricular: ProgramaCurricularExtractionDTO
    programa_actualizado: ProgramaDraftFieldsDTO
