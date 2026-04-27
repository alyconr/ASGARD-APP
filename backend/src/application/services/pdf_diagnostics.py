"""PDF legibility diagnosis for TASK-06."""

from __future__ import annotations

import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from src.application.dto.programa_documentos import PdfLegibilityDiagnosticDTO
from src.domain.programa.documentos import EstadoLegibilidadPdf
from src.domain.shared.enums import MotivoFalloExtraccion

MIN_TEXT_CHARS_FOR_LEGIBLE = 80


class InvalidPdfError(Exception):
    """Raised when uploaded bytes are not a readable PDF document."""


class PdfLegibilityDiagnosticService:
    """Classify whether a PDF has an extractable text layer."""

    def diagnose(self, content: bytes) -> PdfLegibilityDiagnosticDTO:
        """Return a structured legibility diagnosis without extracting fields."""
        if not content.startswith(b"%PDF-"):
            raise InvalidPdfError("El archivo no tiene una cabecera PDF valida")

        try:
            reader = PdfReader(io.BytesIO(content))
        except (PdfReadError, ValueError) as error:
            raise InvalidPdfError("El archivo no pudo leerse como PDF") from error

        if reader.is_encrypted:
            try:
                decrypt_result = reader.decrypt("")
            except Exception as error:  # pypdf can raise provider-specific errors.
                raise InvalidPdfError("El PDF protegido no pudo abrirse") from error
            if decrypt_result == 0:
                return PdfLegibilityDiagnosticDTO(
                    estado_legibilidad=EstadoLegibilidadPdf.NO_LEGIBLE,
                    motivo=MotivoFalloExtraccion.ARCHIVO_PROTEGIDO,
                    resumen="El PDF esta protegido y no permite leer texto extraible.",
                    has_text_layer=False,
                    analyzed_pages=0,
                    pages_with_text=0,
                    text_character_count=0,
                    can_attempt_extraction=False,
                    requires_manual_entry=True,
                )

        total_pages = len(reader.pages)
        pages_with_text = 0
        text_character_count = 0

        for page in reader.pages:
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            normalized_text = " ".join(text.split())
            if normalized_text:
                pages_with_text += 1
                text_character_count += len(normalized_text)

        return _classify_text_layer(
            total_pages=total_pages,
            pages_with_text=pages_with_text,
            text_character_count=text_character_count,
        )


def _classify_text_layer(
    *,
    total_pages: int,
    pages_with_text: int,
    text_character_count: int,
) -> PdfLegibilityDiagnosticDTO:
    """Classify a PDF from text-layer counters."""
    if total_pages <= 0:
        return PdfLegibilityDiagnosticDTO(
            estado_legibilidad=EstadoLegibilidadPdf.NO_LEGIBLE,
            motivo=MotivoFalloExtraccion.DOCUMENTO_ILEGIBLE,
            resumen="El PDF no contiene paginas analizables.",
            has_text_layer=False,
            analyzed_pages=0,
            pages_with_text=0,
            text_character_count=0,
            can_attempt_extraction=False,
            requires_manual_entry=True,
        )

    if pages_with_text == 0 or text_character_count == 0:
        return PdfLegibilityDiagnosticDTO(
            estado_legibilidad=EstadoLegibilidadPdf.NO_LEGIBLE,
            motivo=MotivoFalloExtraccion.PDF_ESCANEADO,
            resumen=(
                "No se encontro capa de texto extraible. El flujo debe continuar "
                "con ingreso manual."
            ),
            has_text_layer=False,
            analyzed_pages=total_pages,
            pages_with_text=0,
            text_character_count=0,
            can_attempt_extraction=False,
            requires_manual_entry=True,
        )

    if (
        pages_with_text == total_pages
        and text_character_count >= MIN_TEXT_CHARS_FOR_LEGIBLE
    ):
        return PdfLegibilityDiagnosticDTO(
            estado_legibilidad=EstadoLegibilidadPdf.LEGIBLE,
            motivo=None,
            resumen=(
                "El PDF tiene capa de texto suficiente para intentar una "
                "extraccion posterior con revision humana."
            ),
            has_text_layer=True,
            analyzed_pages=total_pages,
            pages_with_text=pages_with_text,
            text_character_count=text_character_count,
            can_attempt_extraction=True,
            requires_manual_entry=False,
        )

    return PdfLegibilityDiagnosticDTO(
        estado_legibilidad=EstadoLegibilidadPdf.PARCIALMENTE_LEGIBLE,
        motivo=MotivoFalloExtraccion.ESTRUCTURA_NO_RECONOCIDA,
        resumen=(
            "El PDF tiene texto extraible parcial o insuficiente. Se podra "
            "intentar extraccion limitada y completar manualmente."
        ),
        has_text_layer=True,
        analyzed_pages=total_pages,
        pages_with_text=pages_with_text,
        text_character_count=text_character_count,
        can_attempt_extraction=True,
        requires_manual_entry=True,
    )
