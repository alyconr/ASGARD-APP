"""Hybrid extraction service for program PDFs in TASK-07."""

from __future__ import annotations

import io
import re
import unicodedata
import uuid
import enum
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
    CompetenciaExtraccionDTO,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.programa.documentos import EstadoLegibilidadPdf
from src.domain.shared.enums import EstadoBloque, EstadoCampo, MotivoFalloExtraccion
from src.infrastructure.db.models.drafts import BorradorSesion


class FSMState(enum.Enum):
    BUSCANDO_NORMA = enum.auto()
    CAPTURA_GENERAL = enum.auto()
    CAPTURA_RA = enum.auto()
    CAPTURA_SABER = enum.auto()
    CAPTURA_HACER = enum.auto()
    CAPTURA_CRITERIOS = enum.auto()

# Exceptions and protocols remain identical
class ProgramaExtractionDraftMissingError(Exception):
    """Raised when extraction is requested for a missing program draft."""

class ProgramaPdfMissingForExtractionError(Exception):
    """Raised when the draft has no TASK-06 PDF result attached."""

class ProgramaPdfReadError(Exception):
    """Raised when the stored PDF cannot be read for extraction."""

class DraftRepositoryProtocol(Protocol):
    async def get_by_block_reference(
        self, tipo_bloque: TipoBloqueBorrador, referencia_id: uuid.UUID
    ) -> BorradorSesion | None: ...
    async def save(self, draft: BorradorSesion) -> BorradorSesion: ...

class AuditRepositoryProtocol(Protocol):
    async def add_event(
        self, entidad: str, entidad_id: uuid.UUID, accion: str, detalle: dict[str, object] | None = None
    ) -> object: ...

class AsyncSessionProtocol(Protocol):
    async def commit(self) -> None: ...
    async def refresh(self, instance: object) -> None: ...

class DocumentReaderProtocol(Protocol):
    async def read_pdf(self, *, key: str) -> bytes: ...

class PdfTextExtractorProtocol(Protocol):
    def extract_text(self, content: bytes) -> str: ...

class PdfTextExtractionService:
    def extract_text(self, content: bytes) -> str:
        try:
            reader = PdfReader(io.BytesIO(content))
        except (PdfReadError, ValueError) as error:
            raise ProgramaPdfReadError("No fue posible leer el PDF almacenado") from error

        if reader.is_encrypted:
            try:
                decrypt_result = reader.decrypt("")
            except Exception as error:
                raise ProgramaPdfReadError("No fue posible abrir el PDF protegido") from error
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
    def __init__(
        self,
        session: AsyncSessionProtocol,
        draft_repository: DraftRepositoryProtocol,
        audit_repository: AuditRepositoryProtocol,
        document_reader: DocumentReaderProtocol,
        text_extractor: PdfTextExtractorProtocol,
    ) -> None:
        self._session = session
        self._draft_repository = draft_repository
        self._audit_repository = audit_repository
        self._document_reader = document_reader
        self._text_extractor = text_extractor

    async def extract_program_from_pdf(
        self, *, referencia_id: uuid.UUID
    ) -> ProgramaExtractionResultDTO:
        draft = await self._draft_repository.get_by_block_reference(
            TipoBloqueBorrador.PROGRAMA, referencia_id
        )
        if draft is None:
            raise ProgramaExtractionDraftMissingError(
                "No existe un borrador de programa para extraer informacion"
            )

        pdf_payload = _get_programa_pdf_payload(draft.payload_json)
        diagnostic_payload = _as_record(pdf_payload.get("diagnostico"))
        document_payload = _as_record(pdf_payload.get("documento"))
        if diagnostic_payload is None or document_payload is None:
            raise ProgramaPdfMissingForExtractionError(
                "El borrador actual no tiene un PDF diagnosticado"
            )

        legibility = _read_legibility(diagnostic_payload)
        diagnostic_summary = _read_string(diagnostic_payload, "resumen")
        if legibility is EstadoLegibilidadPdf.NO_LEGIBLE:
            result = _build_manual_fallback_result(
                referencia_id=referencia_id,
                payload=draft.payload_json,
                legibility=legibility,
                summary=diagnostic_summary,
                reason=_read_reason(diagnostic_payload) or MotivoFalloExtraccion.DOCUMENTO_ILEGIBLE,
            )
        else:
            storage_key = _read_string(document_payload, "storage_key")
            if not storage_key:
                raise ProgramaPdfMissingForExtractionError(
                    "El PDF diagnosticado no tiene referencia de almacenamiento"
                )
            try:
                pdf_content = await self._document_reader.read_pdf(key=storage_key)
            except FileNotFoundError as error:
                raise ProgramaPdfMissingForExtractionError(
                    "El borrador conserva la referencia del PDF, pero el archivo "
                    "ya no existe en el almacenamiento documental. Vuelve a cargar "
                    "el PDF en este mismo borrador antes de extraer."
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
            payload=draft.payload_json, result=result
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
    current_program = _read_program_draft_fields(payload)
    lines = _filter_page_noise(_normalize_lines(text))
    lines = _unify_lines(lines)
    
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

    estructura = _extract_curricular_structure(lines, source_is_partial, reason)

    return ProgramaExtractionResultDTO(
        referencia_id=referencia_id,
        estado_legibilidad=legibility,
        resumen=summary or "Extraccion automatica aplicada con revision humana obligatoria.",
        requiere_revision_humana=True,
        programa=ProgramaBaseExtractionDTO(
            codigo_programa=codigo,
            nombre_programa=nombre,
        ),
        estructura_curricular=estructura,
        programa_actualizado=updated_program,
    )

def _filter_page_noise(lines: list[str]) -> list[str]:
    noise_patterns = [
        re.compile(r"^\s*SENA\s*$", re.IGNORECASE),
        re.compile(r"^\s*L[IÍ]NEA TECNOL[OÓ]GICA.*$", re.IGNORECASE),
        re.compile(r"^\s*RED TECNOL[OÓ]GICA.*$", re.IGNORECASE),
        re.compile(r"^\s*GESTI[OÓ]N DE LA INFORMACI[OÓ]N.*$", re.IGNORECASE),
        re.compile(r"^\s*DIRECCI[OÓ]N DE FORMACI[OÓ]N.*$", re.IGNORECASE),
        re.compile(r"^\s*P[aá]gina \d+ de \d+\s*$", re.IGNORECASE),
        re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}\s+[AP]M$", re.IGNORECASE),
    ]
    filtered = []
    for line in lines:
        if not any(p.match(line) for p in noise_patterns):
            filtered.append(line)
    return filtered

def _unify_lines(lines: list[str]) -> list[str]:
    if not lines:
        return []
    unified = [lines[0]]
    for i in range(1, len(lines)):
        prev = unified[-1]
        curr = lines[i]
        if prev and curr and not prev[-1] in ".!?:;" and curr[0].islower():
            unified[-1] = f"{prev} {curr}"
        else:
            unified.append(curr)
    return unified

def _extract_curricular_structure(
    lines: list[str], source_is_partial: bool, missing_reason: MotivoFalloExtraccion
) -> ProgramaCurricularExtractionDTO:
    state = FSMState.BUSCANDO_NORMA
    competencias: list[CompetenciaExtraccionDTO] = []
    
    current_competencia_codigo = ""
    current_competencia_denom = ""
    
    ra_list: list[str] = []
    saber_list: list[str] = []
    hacer_list: list[str] = []
    criterios_list: list[str] = []

    def flush_competencia():
        nonlocal current_competencia_codigo, current_competencia_denom, ra_list, saber_list, hacer_list, criterios_list
        if current_competencia_codigo or current_competencia_denom:
            comp = CompetenciaExtraccionDTO(
                codigo=ExtractedTextItemDTO(valor=current_competencia_codigo, estado=EstadoCampo.EXTRAIDO if current_competencia_codigo else EstadoCampo.PENDIENTE, motivo=None if current_competencia_codigo else missing_reason, requiere_revision=True),
                denominacion=ExtractedTextItemDTO(valor=current_competencia_denom, estado=EstadoCampo.EXTRAIDO if current_competencia_denom else EstadoCampo.PENDIENTE, motivo=None if current_competencia_denom else missing_reason, requiere_revision=True),
                resultados_aprendizaje=_build_list_block(ra_list, source_is_partial, missing_reason),
                conocimientos_saber=_build_list_block(saber_list, source_is_partial, missing_reason),
                conocimientos_proceso=_build_list_block(hacer_list, source_is_partial, missing_reason),
                criterios_evaluacion=_build_list_block(criterios_list, source_is_partial, missing_reason),
            )
            competencias.append(comp)
        
        current_competencia_codigo = ""
        current_competencia_denom = ""
        ra_list = []
        saber_list = []
        hacer_list = []
        criterios_list = []

    for line in lines:
        plain = _plain(line)
        
        # Transitions
        # We look for "3. CONTENIDOS CURRICULARES DE LA COMPETENCIA" to indicate start of a competence block
        if "contenidos curriculares de la competencia" in plain or re.search(r"^\d+\.\s*contenidos curriculares", plain):
            flush_competencia()
            state = FSMState.CAPTURA_GENERAL
            continue
            
        if state == FSMState.BUSCANDO_NORMA:
            # Fallback looking for "codigo" / "denominacion" outside of "contenidos curriculares" section
            match = re.search(r"\b(2\d{8})\b", line) # Competence codes typically start with 2 and have 9 digits
            if match and "codigo" in plain:
                if current_competencia_codigo: flush_competencia()
                current_competencia_codigo = match.group(1)
                state = FSMState.CAPTURA_GENERAL
                continue
                
        if state != FSMState.BUSCANDO_NORMA:
            if "resultados de aprendizaje" in plain or re.search(r"^4\.5\s", plain):
                state = FSMState.CAPTURA_RA
                continue
            if "conocimientos de saber" in plain or "conocimientos_saber" in plain or re.search(r"^4\.6\.1\s", plain):
                state = FSMState.CAPTURA_SABER
                continue
            if "conocimientos de proceso" in plain or "conocimientos_proceso" in plain or re.search(r"^4\.6\.2\s", plain):
                state = FSMState.CAPTURA_HACER
                continue
            if "criterios de evaluacion" in plain or re.search(r"^4\.7\s", plain):
                state = FSMState.CAPTURA_CRITERIOS
                continue
            
            # Additional fallback to capture new competence without explicit header
            match_code = re.search(r"\bcodigo\s*:\s*(2\d{8})\b", plain)
            if match_code and state in [FSMState.CAPTURA_CRITERIOS, FSMState.CAPTURA_HACER]:
                flush_competencia()
                current_competencia_codigo = match_code.group(1)
                state = FSMState.CAPTURA_GENERAL
                continue

            # Data capture
            clean_item = _clean_item(line)
            if clean_item:
                if state == FSMState.CAPTURA_GENERAL:
                    if not current_competencia_codigo:
                        m = re.search(r"\b(2\d{8})\b", line)
                        if m: current_competencia_codigo = m.group(1)
                    if "denominacion" in plain or "competencia" in plain:
                        parts = re.split(r"[:\-]", line, maxsplit=1)
                        if len(parts) > 1 and parts[1].strip():
                            current_competencia_denom = parts[1].strip()
                        elif "denominacion" not in plain:
                            # It might just be the name itself
                            current_competencia_denom = clean_item
                elif state == FSMState.CAPTURA_RA:
                    ra_list.append(clean_item)
                elif state == FSMState.CAPTURA_SABER:
                    saber_list.append(clean_item)
                elif state == FSMState.CAPTURA_HACER:
                    hacer_list.append(clean_item)
                elif state == FSMState.CAPTURA_CRITERIOS:
                    criterios_list.append(clean_item)

    flush_competencia()

    total_comps = len(competencias)
    return ProgramaCurricularExtractionDTO(
        competencias=competencias,
        estado=EstadoCampo.EXTRAIDO if total_comps > 0 else EstadoCampo.PENDIENTE,
        motivo=None if total_comps > 0 else missing_reason,
        requiere_revision=True,
        total_competencias=total_comps,
        bloque_vacio=total_comps == 0,
        bloque_parcial=source_is_partial
    )

def _build_list_block(items: list[str], source_is_partial: bool, missing_reason: MotivoFalloExtraccion) -> ExtractedListBlockDTO:
    deduped = _dedupe_items(items)
    extracted = [
        ExtractedTextItemDTO(valor=item, estado=EstadoCampo.EXTRAIDO, motivo=None, requiere_revision=True)
        for item in deduped if item
    ]
    return ExtractedListBlockDTO(
        items=extracted,
        estado=EstadoCampo.EXTRAIDO if extracted else EstadoCampo.PENDIENTE,
        motivo=None if extracted else missing_reason,
        requiere_revision=True,
        total_items=len(extracted),
        bloque_vacio=not extracted,
        bloque_parcial=source_is_partial
    )

def _build_manual_fallback_result(
    *,
    referencia_id: uuid.UUID,
    payload: dict[str, object],
    legibility: EstadoLegibilidadPdf,
    summary: str,
    reason: MotivoFalloExtraccion,
) -> ProgramaExtractionResultDTO:
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
            competencias=[],
            estado=EstadoCampo.PENDIENTE,
            motivo=reason,
            requiere_revision=True,
            total_competencias=0,
            bloque_vacio=True,
            bloque_parcial=True,
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

def _dedupe_items(items: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped

def _merge_extraction_result_into_payload(
    *,
    payload: dict[str, object],
    result: ProgramaExtractionResultDTO,
) -> dict[str, object]:
    next_payload = dict(payload)
    now = datetime.now(UTC).isoformat()
    meta = _as_record(next_payload.get("meta"))
    if meta is not None:
        next_meta = dict(meta)
        next_meta["entryMode"] = "PDF"
        next_meta["lastInteractionAt"] = now
        next_meta["touchedSteps"] = _append_touched_step(
            next_meta.get("touchedSteps"), "origen-documental"
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
            "competencias": [
                {
                    "codigo": _field_to_payload(c.codigo),
                    "denominacion": _field_to_payload(c.denominacion),
                    "resultados_aprendizaje": _block_to_payload(c.resultados_aprendizaje),
                    "conocimientos_saber": _block_to_payload(c.conocimientos_saber),
                    "conocimientos_proceso": _block_to_payload(c.conocimientos_proceso),
                    "criterios_evaluacion": _block_to_payload(c.criterios_evaluacion),
                }
                for c in result.estructura_curricular.competencias
            ],
            "estado": result.estructura_curricular.estado.value,
            "motivo": result.estructura_curricular.motivo.value if result.estructura_curricular.motivo else None,
            "requiere_revision": result.estructura_curricular.requiere_revision,
            "total_competencias": result.estructura_curricular.total_competencias,
            "bloque_vacio": result.estructura_curricular.bloque_vacio,
            "bloque_parcial": result.estructura_curricular.bloque_parcial,
        },
        "programa_actualizado": {
            "codigo_programa": result.programa_actualizado.codigo_programa,
            "nombre_programa": result.programa_actualizado.nombre_programa,
            "version_programa": result.programa_actualizado.version_programa,
        },
        "updated_at": updated_at,
    }

def _field_to_payload(field: ExtractedFieldDTO | ExtractedTextItemDTO) -> dict[str, object]:
    base = {
        "valor": field.valor,
        "estado": field.estado.value,
        "motivo": field.motivo.value if field.motivo is not None else None,
        "requiere_revision": field.requiere_revision,
    }
    if hasattr(field, "campo"):
        base["campo"] = getattr(field, "campo")
        base["aplicado_al_borrador"] = getattr(field, "aplicado_al_borrador")
        base["valor_actual_borrador"] = getattr(field, "valor_actual_borrador")
    return base

def _block_to_payload(block: ExtractedListBlockDTO) -> dict[str, object]:
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
    programa = _as_record(payload.get("programa")) or {}
    return ProgramaDraftFieldsDTO(
        codigo_programa=_read_string(programa, "codigo_programa"),
        nombre_programa=_read_string(programa, "nombre_programa"),
        version_programa=_read_string(programa, "version_programa"),
    )

def _get_programa_pdf_payload(payload: dict[str, object]) -> dict[str, object]:
    documental = _as_record(payload.get("documental"))
    programa_pdf = _as_record(documental.get("programa_pdf") if documental else None)
    if programa_pdf is None:
        raise ProgramaPdfMissingForExtractionError(
            "El borrador actual no tiene un PDF asociado"
        )
    return programa_pdf

def _read_legibility(payload: dict[str, object]) -> EstadoLegibilidadPdf:
    value = _read_string(payload, "estado_legibilidad")
    try:
        return EstadoLegibilidadPdf(value)
    except ValueError as error:
        raise ProgramaPdfMissingForExtractionError(
            "El diagnostico del PDF no tiene estado de legibilidad valido"
        ) from error

def _read_reason(payload: dict[str, object]) -> MotivoFalloExtraccion | None:
    value = payload.get("motivo")
    if not isinstance(value, str):
        return None
    try:
        return MotivoFalloExtraccion(value)
    except ValueError:
        return None

def _append_touched_step(value: object, step: str) -> list[str]:
    if isinstance(value, list):
        steps = [item for item in value if isinstance(item, str)]
        if step not in steps:
            steps.append(step)
        return steps
    return [step]

def _normalize_lines(text: str) -> list[str]:
    return [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()
        if re.sub(r"\s+", " ", line).strip()
    ]

def _plain(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    without_accents = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return without_accents.lower()

def _value_after_label(line: str) -> str:
    parts = re.split(r"[:\-]", line, maxsplit=1)
    if len(parts) == 2:
        return parts[1].strip()
    return ""

def _looks_like_program_name(value: str) -> bool:
    clean = value.strip(" :-")
    if len(clean) < 8:
        return False
    if re.fullmatch(r"\d+", clean):
        return False
    return "codigo" not in _plain(clean)

def _clean_item(value: str) -> str:
    clean = value.strip(" :-*\t")
    if len(clean) < 4:
        return ""
    lower = clean.lower()
    if lower in {
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
        "criterios evaluacion",
    }:
        return ""
    return clean[:500]

def _as_record(value: object) -> dict[str, object] | None:
    return value if isinstance(value, dict) else None

def _read_string(record: dict[str, object], key: str) -> str:
    value = record.get(key)
    return str(value) if value is not None else ""
