"""Hybrid extraction service for program PDFs in TASK-07."""

from __future__ import annotations

import io
import re
import unicodedata
import uuid
from datetime import UTC, datetime
from typing import Protocol

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from src.application.dto.programa_documentos import (
    ExtractedFieldDTO,
    ExtractedListBlockDTO,
    ExtractedTextItemDTO,
    ProgramaBaseExtractionDTO,
    ProgramaCurricularExtractionDTO,
    ProgramaDraftFieldsDTO,
    ProgramaExtractionResultDTO,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.programa.documentos import EstadoLegibilidadPdf
from src.domain.shared.enums import EstadoBloque, EstadoCampo, MotivoFalloExtraccion
from src.infrastructure.db.models.drafts import BorradorSesion

CURRICULAR_SECTION_LABELS: dict[str, tuple[str, ...]] = {
    "competencias": (
        "competencias",
        "competencia",
    ),
    "resultados_aprendizaje": (
        "resultados de aprendizaje",
        "resultado de aprendizaje",
        "resultados aprendizaje",
        "resultado aprendizaje",
    ),
    "conocimientos_saber": (
        "conocimientos de saber",
        "conocimiento de saber",
        "saberes",
        "saber",
    ),
    "conocimientos_proceso": (
        "conocimientos de proceso",
        "conocimiento de proceso",
        "procesos",
        "proceso",
    ),
    "criterios_evaluacion": (
        "criterios de evaluacion",
        "criterio de evaluacion",
        "criterios evaluacion",
        "criterio evaluacion",
    ),
}


class ProgramaExtractionDraftMissingError(Exception):
    """Raised when extraction is requested for a missing program draft."""


class ProgramaPdfMissingForExtractionError(Exception):
    """Raised when the draft has no TASK-06 PDF result attached."""


class ProgramaPdfReadError(Exception):
    """Raised when the stored PDF cannot be read for extraction."""


class DraftRepositoryProtocol(Protocol):
    """Draft repository dependency used to associate extraction to the wizard."""

    async def get_by_block_reference(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
    ) -> BorradorSesion | None:
        """Return the current logical draft for a reference."""

    async def save(self, draft: BorradorSesion) -> BorradorSesion:
        """Persist modifications on an existing draft row."""


class AuditRepositoryProtocol(Protocol):
    """Audit dependency for relevant extraction events."""

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


class DocumentReaderProtocol(Protocol):
    """Storage dependency required to read already uploaded PDFs."""

    async def read_pdf(self, *, key: str) -> bytes:
        """Read a PDF object by storage key."""


class PdfTextExtractorProtocol(Protocol):
    """Text extraction dependency used by the program extraction service."""

    def extract_text(self, content: bytes) -> str:
        """Return best-effort text from PDF bytes."""


class PdfTextExtractionService:
    """Extract text from a PDF text layer without OCR."""

    def extract_text(self, content: bytes) -> str:
        """Return normalized text from all readable PDF pages."""
        try:
            reader = PdfReader(io.BytesIO(content))
        except (PdfReadError, ValueError) as error:
            raise ProgramaPdfReadError(
                "No fue posible leer el PDF almacenado",
            ) from error

        if reader.is_encrypted:
            try:
                decrypt_result = reader.decrypt("")
            except Exception as error:
                raise ProgramaPdfReadError(
                    "No fue posible abrir el PDF protegido",
                ) from error
            if decrypt_result == 0:
                raise ProgramaPdfReadError("El PDF protegido no permite extraccion")

        page_texts: list[str] = []
        for page in reader.pages:
            try:
                page_texts.append(page.extract_text() or "")
            except Exception:
                page_texts.append("")

        return "\n".join(page_texts)


class ProgramaExtractionService:
    """Coordinate PDF text extraction and draft persistence for TASK-07."""

    def __init__(
        self,
        session: AsyncSessionProtocol,
        draft_repository: DraftRepositoryProtocol,
        audit_repository: AuditRepositoryProtocol,
        document_reader: DocumentReaderProtocol,
        text_extractor: PdfTextExtractorProtocol,
    ) -> None:
        """Initialize the service with explicit infrastructure ports."""
        self._session = session
        self._draft_repository = draft_repository
        self._audit_repository = audit_repository
        self._document_reader = document_reader
        self._text_extractor = text_extractor

    async def extract_program_from_pdf(
        self,
        *,
        referencia_id: uuid.UUID,
    ) -> ProgramaExtractionResultDTO:
        """Extract program data from the current draft PDF without closing it."""
        draft = await self._draft_repository.get_by_block_reference(
            TipoBloqueBorrador.PROGRAMA,
            referencia_id,
        )
        if draft is None:
            raise ProgramaExtractionDraftMissingError(
                "No existe un borrador de programa para extraer informacion",
            )

        pdf_payload = _get_programa_pdf_payload(draft.payload_json)
        diagnostic_payload = _as_record(pdf_payload.get("diagnostico"))
        document_payload = _as_record(pdf_payload.get("documento"))
        if diagnostic_payload is None or document_payload is None:
            raise ProgramaPdfMissingForExtractionError(
                "El borrador actual no tiene un PDF diagnosticado",
            )

        legibility = _read_legibility(diagnostic_payload)
        diagnostic_summary = _read_string(diagnostic_payload, "resumen")
        if legibility is EstadoLegibilidadPdf.NO_LEGIBLE:
            result = _build_manual_fallback_result(
                referencia_id=referencia_id,
                payload=draft.payload_json,
                legibility=legibility,
                summary=diagnostic_summary,
                reason=_read_reason(diagnostic_payload)
                or MotivoFalloExtraccion.DOCUMENTO_ILEGIBLE,
            )
        else:
            storage_key = _read_string(document_payload, "storage_key")
            if not storage_key:
                raise ProgramaPdfMissingForExtractionError(
                    "El PDF diagnosticado no tiene referencia de almacenamiento",
                )
            try:
                pdf_content = await self._document_reader.read_pdf(key=storage_key)
            except FileNotFoundError as error:
                raise ProgramaPdfMissingForExtractionError(
                    "El borrador conserva la referencia del PDF, pero el archivo "
                    "ya no existe en el almacenamiento documental. Vuelve a cargar "
                    "el PDF en este mismo borrador antes de extraer.",
                ) from error
            text = self._text_extractor.extract_text(pdf_content)
            result = _extract_program_fields(
                referencia_id=referencia_id,
                payload=draft.payload_json,
                text=text,
                legibility=legibility,
                summary=diagnostic_summary,
            )

        draft.payload_json = _merge_extraction_result_into_payload(
            payload=draft.payload_json,
            result=result,
        )
        draft.paso_actual = "origen-documental"
        draft.estado_borrador = EstadoBloque.BORRADOR
        await self._draft_repository.save(draft)
        await self._audit_repository.add_event(
            entidad="BorradorSesion",
            entidad_id=draft.id,
            accion="DOCUMENTO_PROGRAMA_EXTRAIDO",
            detalle={
                "referencia_id": str(referencia_id),
                "estado_legibilidad": result.estado_legibilidad.value,
                "codigo_estado": result.programa.codigo_programa.estado.value,
                "nombre_estado": result.programa.nombre_programa.estado.value,
            },
        )
        await self._session.commit()
        await self._session.refresh(draft)
        return result


def _extract_program_fields(
    *,
    referencia_id: uuid.UUID,
    payload: dict[str, object],
    text: str,
    legibility: EstadoLegibilidadPdf,
    summary: str,
) -> ProgramaExtractionResultDTO:
    """Extract program base fields and preliminary curricular blocks from text."""
    current_program = _read_program_draft_fields(payload)
    lines = _normalize_lines(text)
    reason = (
        MotivoFalloExtraccion.ESTRUCTURA_NO_RECONOCIDA
        if legibility is EstadoLegibilidadPdf.PARCIALMENTE_LEGIBLE
        else MotivoFalloExtraccion.CAMPO_NO_ENCONTRADO
    )
    source_is_partial = legibility is EstadoLegibilidadPdf.PARCIALMENTE_LEGIBLE
    codigo = _build_field_result(
        campo="codigo_programa",
        extracted_value=_extract_code(lines),
        current_value=current_program.codigo_programa,
        missing_reason=reason,
    )
    nombre = _build_field_result(
        campo="nombre_programa",
        extracted_value=_extract_name(lines),
        current_value=current_program.nombre_programa,
        missing_reason=reason,
    )
    updated_program = ProgramaDraftFieldsDTO(
        codigo_programa=codigo.valor
        if codigo.aplicado_al_borrador and codigo.valor is not None
        else current_program.codigo_programa,
        nombre_programa=nombre.valor
        if nombre.aplicado_al_borrador and nombre.valor is not None
        else current_program.nombre_programa,
        version_programa=current_program.version_programa,
    )

    return ProgramaExtractionResultDTO(
        referencia_id=referencia_id,
        estado_legibilidad=legibility,
        resumen=summary
        or "Extraccion automatica aplicada con revision humana obligatoria.",
        requiere_revision_humana=True,
        programa=ProgramaBaseExtractionDTO(
            codigo_programa=codigo,
            nombre_programa=nombre,
        ),
        estructura_curricular=ProgramaCurricularExtractionDTO(
            competencias=_extract_list_block(
                lines,
                section_key="competencias",
                missing_reason=reason,
                source_is_partial=source_is_partial,
            ),
            resultados_aprendizaje=_extract_list_block(
                lines,
                section_key="resultados_aprendizaje",
                missing_reason=reason,
                source_is_partial=source_is_partial,
            ),
            conocimientos_saber=_extract_list_block(
                lines,
                section_key="conocimientos_saber",
                missing_reason=reason,
                source_is_partial=source_is_partial,
            ),
            conocimientos_proceso=_extract_list_block(
                lines,
                section_key="conocimientos_proceso",
                missing_reason=reason,
                source_is_partial=source_is_partial,
            ),
            criterios_evaluacion=_extract_list_block(
                lines,
                section_key="criterios_evaluacion",
                missing_reason=reason,
                source_is_partial=source_is_partial,
            ),
        ),
        programa_actualizado=updated_program,
    )


def _build_manual_fallback_result(
    *,
    referencia_id: uuid.UUID,
    payload: dict[str, object],
    legibility: EstadoLegibilidadPdf,
    summary: str,
    reason: MotivoFalloExtraccion,
) -> ProgramaExtractionResultDTO:
    """Build a structured result when extraction must not be attempted."""
    current_program = _read_program_draft_fields(payload)
    codigo = _pending_field(
        campo="codigo_programa",
        current_value=current_program.codigo_programa,
        reason=reason,
    )
    nombre = _pending_field(
        campo="nombre_programa",
        current_value=current_program.nombre_programa,
        reason=reason,
    )
    pending_block = _empty_list_block(reason)
    return ProgramaExtractionResultDTO(
        referencia_id=referencia_id,
        estado_legibilidad=legibility,
        resumen=summary or "El documento no permite extraccion automatica.",
        requiere_revision_humana=True,
        programa=ProgramaBaseExtractionDTO(
            codigo_programa=codigo,
            nombre_programa=nombre,
        ),
        estructura_curricular=ProgramaCurricularExtractionDTO(
            competencias=pending_block,
            resultados_aprendizaje=pending_block,
            conocimientos_saber=pending_block,
            conocimientos_proceso=pending_block,
            criterios_evaluacion=pending_block,
        ),
        programa_actualizado=current_program,
    )


def _build_field_result(
    *,
    campo: str,
    extracted_value: str | None,
    current_value: str,
    missing_reason: MotivoFalloExtraccion,
) -> ExtractedFieldDTO:
    """Return a field result that never overwrites manual content blindly."""
    clean_current = current_value.strip()
    clean_extracted = extracted_value.strip() if extracted_value is not None else None
    if not clean_extracted:
        return _pending_field(
            campo=campo,
            current_value=current_value,
            reason=missing_reason,
        )

    if clean_current and clean_current != clean_extracted:
        return ExtractedFieldDTO(
            campo=campo,
            valor=clean_extracted,
            estado=EstadoCampo.EXTRAIDO,
            motivo=MotivoFalloExtraccion.CONTENIDO_AMBIGUO,
            requiere_revision=True,
            aplicado_al_borrador=False,
            valor_actual_borrador=current_value,
        )

    return ExtractedFieldDTO(
        campo=campo,
        valor=clean_extracted,
        estado=EstadoCampo.EXTRAIDO,
        motivo=None,
        requiere_revision=True,
        aplicado_al_borrador=not clean_current,
        valor_actual_borrador=current_value or None,
    )


def _pending_field(
    *,
    campo: str,
    current_value: str,
    reason: MotivoFalloExtraccion,
) -> ExtractedFieldDTO:
    """Build a pending field result requiring manual completion."""
    return ExtractedFieldDTO(
        campo=campo,
        valor=None,
        estado=EstadoCampo.PENDIENTE,
        motivo=reason,
        requiere_revision=True,
        aplicado_al_borrador=False,
        valor_actual_borrador=current_value or None,
    )


def _extract_code(lines: list[str]) -> str | None:
    """Extract a likely program code from labeled PDF text lines."""
    label_tokens = ("codigo programa", "codigo del programa", "codigo")
    for index, line in enumerate(lines):
        normalized = _plain(line)
        if not any(token in normalized for token in label_tokens):
            continue
        match = re.search(r"\b\d{3,12}\b", line)
        if match is not None:
            return match.group(0)
        for next_line in lines[index + 1 : index + 3]:
            match = re.search(r"\b\d{3,12}\b", next_line)
            if match is not None:
                return match.group(0)
    return None


def _extract_name(lines: list[str]) -> str | None:
    """Extract a likely program name from labeled PDF text lines."""
    labels = (
        "denominacion del programa",
        "nombre del programa",
        "programa de formacion",
    )
    for index, line in enumerate(lines):
        normalized = _plain(line)
        matched_label = next((label for label in labels if label in normalized), None)
        if matched_label is None:
            continue
        inline_value = _value_after_label(line)
        if _looks_like_program_name(inline_value):
            return inline_value
        for next_line in lines[index + 1 : index + 4]:
            if _looks_like_program_name(next_line):
                return next_line.strip(" :-")
    return None


def _extract_list_block(
    lines: list[str],
    *,
    section_key: str,
    missing_reason: MotivoFalloExtraccion,
    source_is_partial: bool,
) -> ExtractedListBlockDTO:
    """Extract all identifiable items from one curricular document section."""
    items = [
        ExtractedTextItemDTO(
            valor=item,
            estado=EstadoCampo.EXTRAIDO,
            motivo=None,
            requiere_revision=True,
        )
        for item in _extract_section_items(lines, section_key=section_key)
    ]

    if not items:
        return _empty_list_block(missing_reason)

    return ExtractedListBlockDTO(
        items=items,
        estado=EstadoCampo.EXTRAIDO,
        motivo=None,
        requiere_revision=True,
        total_items=len(items),
        bloque_vacio=False,
        bloque_parcial=source_is_partial,
    )


def _extract_section_items(lines: list[str], *, section_key: str) -> list[str]:
    """Extract ordered, de-duplicated items from a named section."""
    active = False
    current_parts: list[str] = []
    raw_items: list[str] = []

    def flush_current() -> None:
        nonlocal current_parts
        if current_parts:
            raw_items.append(" ".join(current_parts))
            current_parts = []

    for line in lines:
        heading_key = _find_curricular_heading_key(line)
        if heading_key is not None:
            if active and heading_key != section_key:
                flush_current()
                active = False

            if heading_key == section_key:
                active = True
                inline_value = _value_after_section_label(line, section_key)
                if inline_value:
                    flush_current()
                    current_parts = [inline_value]
                continue

        if not active or _is_section_noise(line):
            continue

        clean_line = _clean_item_line(line)
        if not clean_line:
            continue

        if _starts_new_item(line):
            flush_current()
            current_parts = [_strip_item_marker(clean_line)]
            continue

        if not current_parts:
            current_parts = [clean_line]
        elif _looks_like_new_unmarked_item(clean_line, current_parts):
            flush_current()
            current_parts = [clean_line]
        else:
            current_parts.append(clean_line)

    flush_current()
    return _dedupe_items(raw_items)


def _empty_list_block(reason: MotivoFalloExtraccion) -> ExtractedListBlockDTO:
    """Return a pending list block."""
    return ExtractedListBlockDTO(
        items=[],
        estado=EstadoCampo.PENDIENTE,
        motivo=reason,
        requiere_revision=True,
        total_items=0,
        bloque_vacio=True,
        bloque_parcial=True,
    )


def _merge_extraction_result_into_payload(
    *,
    payload: dict[str, object],
    result: ProgramaExtractionResultDTO,
) -> dict[str, object]:
    """Persist extraction metadata while preserving manual draft fields."""
    next_payload = dict(payload)
    now = datetime.now(UTC).isoformat()
    meta = _as_record(next_payload.get("meta"))
    if meta is not None:
        next_meta = dict(meta)
        next_meta["entryMode"] = "PDF"
        next_meta["lastInteractionAt"] = now
        next_meta["touchedSteps"] = _append_touched_step(
            next_meta.get("touchedSteps"),
            "origen-documental",
        )
        next_payload["meta"] = next_meta

    next_payload["programa"] = {
        **(_as_record(next_payload.get("programa")) or {}),
        "codigo_programa": result.programa_actualizado.codigo_programa,
        "nombre_programa": result.programa_actualizado.nombre_programa,
        "version_programa": result.programa_actualizado.version_programa,
    }

    documental = _as_record(next_payload.get("documental")) or {}
    programa_pdf = _as_record(documental.get("programa_pdf")) or {}
    programa_pdf["extraccion"] = _extraction_to_payload(result, updated_at=now)
    documental["programa_pdf"] = programa_pdf
    next_payload["documental"] = documental
    return next_payload


def _extraction_to_payload(
    result: ProgramaExtractionResultDTO,
    *,
    updated_at: str,
) -> dict[str, object]:
    """Convert the extraction result into JSON-compatible draft payload."""
    return {
        "referencia_id": str(result.referencia_id),
        "estado_legibilidad": result.estado_legibilidad.value,
        "resumen": result.resumen,
        "requiere_revision_humana": result.requiere_revision_humana,
        "programa": {
            "codigo_programa": _field_to_payload(result.programa.codigo_programa),
            "nombre_programa": _field_to_payload(result.programa.nombre_programa),
        },
        "estructura_curricular": {
            "competencias": _block_to_payload(
                result.estructura_curricular.competencias,
            ),
            "resultados_aprendizaje": _block_to_payload(
                result.estructura_curricular.resultados_aprendizaje,
            ),
            "conocimientos_saber": _block_to_payload(
                result.estructura_curricular.conocimientos_saber,
            ),
            "conocimientos_proceso": _block_to_payload(
                result.estructura_curricular.conocimientos_proceso,
            ),
            "criterios_evaluacion": _block_to_payload(
                result.estructura_curricular.criterios_evaluacion,
            ),
        },
        "programa_actualizado": {
            "codigo_programa": result.programa_actualizado.codigo_programa,
            "nombre_programa": result.programa_actualizado.nombre_programa,
            "version_programa": result.programa_actualizado.version_programa,
        },
        "updated_at": updated_at,
    }


def _field_to_payload(field: ExtractedFieldDTO) -> dict[str, object]:
    """Convert a field result to JSON-compatible payload."""
    return {
        "campo": field.campo,
        "valor": field.valor,
        "estado": field.estado.value,
        "motivo": field.motivo.value if field.motivo is not None else None,
        "requiere_revision": field.requiere_revision,
        "aplicado_al_borrador": field.aplicado_al_borrador,
        "valor_actual_borrador": field.valor_actual_borrador,
    }


def _block_to_payload(block: ExtractedListBlockDTO) -> dict[str, object]:
    """Convert a list block result to JSON-compatible payload."""
    return {
        "items": [
            {
                "valor": item.valor,
                "estado": item.estado.value,
                "motivo": item.motivo.value if item.motivo is not None else None,
                "requiere_revision": item.requiere_revision,
            }
            for item in block.items
        ],
        "estado": block.estado.value,
        "motivo": block.motivo.value if block.motivo is not None else None,
        "requiere_revision": block.requiere_revision,
        "total_items": block.total_items,
        "bloque_vacio": block.bloque_vacio,
        "bloque_parcial": block.bloque_parcial,
    }


def _read_program_draft_fields(payload: dict[str, object]) -> ProgramaDraftFieldsDTO:
    """Read current program fields from the draft payload."""
    programa = _as_record(payload.get("programa")) or {}
    return ProgramaDraftFieldsDTO(
        codigo_programa=_read_string(programa, "codigo_programa"),
        nombre_programa=_read_string(programa, "nombre_programa"),
        version_programa=_read_string(programa, "version_programa"),
    )


def _get_programa_pdf_payload(payload: dict[str, object]) -> dict[str, object]:
    """Return the current program PDF payload or raise a domain error."""
    documental = _as_record(payload.get("documental"))
    programa_pdf = _as_record(documental.get("programa_pdf") if documental else None)
    if programa_pdf is None:
        raise ProgramaPdfMissingForExtractionError(
            "El borrador actual no tiene un PDF asociado",
        )
    return programa_pdf


def _read_legibility(payload: dict[str, object]) -> EstadoLegibilidadPdf:
    """Read the stored legibility enum from payload."""
    value = _read_string(payload, "estado_legibilidad")
    try:
        return EstadoLegibilidadPdf(value)
    except ValueError as error:
        raise ProgramaPdfMissingForExtractionError(
            "El diagnostico del PDF no tiene estado de legibilidad valido",
        ) from error


def _read_reason(payload: dict[str, object]) -> MotivoFalloExtraccion | None:
    """Read an optional extraction failure reason from payload."""
    value = payload.get("motivo")
    if not isinstance(value, str):
        return None
    try:
        return MotivoFalloExtraccion(value)
    except ValueError:
        return None


def _append_touched_step(value: object, step: str) -> list[str]:
    """Append a wizard step id without duplicates."""
    if isinstance(value, list):
        steps = [item for item in value if isinstance(item, str)]
        if step not in steps:
            steps.append(step)
        return steps
    return [step]


def _normalize_lines(text: str) -> list[str]:
    """Normalize text into non-empty human-readable lines."""
    return [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()
        if re.sub(r"\s+", " ", line).strip()
    ]


def _plain(value: str) -> str:
    """Return lowercase accent-free text for matching."""
    normalized = unicodedata.normalize("NFD", value)
    without_accents = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return without_accents.lower()


def _value_after_label(line: str) -> str:
    """Return the value-looking part of a labeled line."""
    parts = re.split(r"[:\-]", line, maxsplit=1)
    if len(parts) == 2:
        return parts[1].strip()
    return ""


def _looks_like_program_name(value: str) -> bool:
    """Return whether a candidate looks like a program name."""
    clean = value.strip(" :-")
    if len(clean) < 8:
        return False
    if re.fullmatch(r"\d+", clean):
        return False
    return "codigo" not in _plain(clean)


def _clean_item(value: str) -> str:
    """Clean one extracted preliminary curricular item."""
    clean = value.strip(" :-*\t")
    if len(clean) < 4:
        return ""
    if clean.lower() in {
        "competencia",
        "competencias",
        "resultado de aprendizaje",
        "resultados de aprendizaje",
        "conocimiento de saber",
        "conocimientos de saber",
        "conocimiento de proceso",
        "conocimientos de proceso",
        "criterio de evaluacion",
        "criterios de evaluacion",
    }:
        return ""
    return clean[:500]


def _find_curricular_heading_key(line: str) -> str | None:
    """Return the curricular section key represented by a heading line."""
    for section_key, labels in CURRICULAR_SECTION_LABELS.items():
        if any(_matches_section_heading(line, label) for label in labels):
            return section_key
    return None


def _matches_section_heading(line: str, label: str) -> bool:
    """Return whether a line starts a known curricular section."""
    normalized = _plain(line)
    normalized = re.sub(r"^\s*\d+(?:\.\d+)*[\.)]?\s+", "", normalized)
    normalized = normalized.strip(" :-\t")
    return (
        normalized == label
        or normalized.startswith(f"{label}:")
        or normalized.startswith(f"{label} -")
    )


def _value_after_section_label(line: str, section_key: str) -> str:
    """Return inline content after a section label, preserving original text."""
    labels = CURRICULAR_SECTION_LABELS[section_key]
    normalized = _plain(line)
    normalized = re.sub(r"^\s*\d+(?:\.\d+)*[\.)]?\s+", "", normalized)
    normalized = normalized.strip()
    if not any(
        normalized.startswith(f"{label}:") or normalized.startswith(f"{label} -")
        for label in labels
    ):
        return ""

    value = _value_after_label(line)
    return _clean_item_line(value)


def _is_section_noise(line: str) -> bool:
    """Return whether a line is document chrome rather than curricular content."""
    normalized = _plain(line).strip()
    if not normalized:
        return True
    if re.fullmatch(r"(pagina|page)?\s*\d+\s*(de|/)?\s*\d*", normalized):
        return True
    return normalized in {"sena", "servicio nacional de aprendizaje"}


def _clean_item_line(value: str) -> str:
    """Clean one physical line before assembling section items."""
    return re.sub(r"\s+", " ", value).strip(" :-*\t")


def _starts_new_item(line: str) -> bool:
    """Detect numbered, bulleted, coded or prefixed item starts."""
    return re.match(
        r"^\s*(?:[-*•–—]+|\d+(?:\.\d+)*[\.)-]|[A-Za-z][\.)-]|"
        r"(?:RA|RAP|CE|C)\s*[-\d])\s+",
        line,
        flags=re.IGNORECASE,
    ) is not None


def _strip_item_marker(line: str) -> str:
    """Remove a leading list marker from an extracted item line."""
    return re.sub(
        r"^\s*(?:[-*•–—]+|\d+(?:\.\d+)*[\.)-]|[A-Za-z][\.)-]|"
        r"(?:RA|RAP|CE|C)\s*[-\d])\s+",
        "",
        line,
        flags=re.IGNORECASE,
    ).strip()


def _looks_like_new_unmarked_item(line: str, current_parts: list[str]) -> bool:
    """Detect conservative unmarked item boundaries inside a section."""
    current = " ".join(current_parts).strip()
    if not current:
        return False
    if not current.endswith("."):
        return False
    if len(current) > 180 or len(line) > 180:
        return False
    return line[:1].isupper()


def _dedupe_items(items: list[str]) -> list[str]:
    """Clean and de-duplicate extracted items while preserving order."""
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        clean = _clean_item(item)
        key = _plain(clean)
        if clean and key not in seen:
            seen.add(key)
            deduped.append(clean)
    return deduped


def _as_record(value: object) -> dict[str, object] | None:
    """Return a dictionary only for plain object-like payload values."""
    if not isinstance(value, dict):
        return None
    return value


def _read_string(payload: dict[str, object], key: str) -> str:
    """Read a string from a payload dictionary."""
    value = payload.get(key)
    return value if isinstance(value, str) else ""
