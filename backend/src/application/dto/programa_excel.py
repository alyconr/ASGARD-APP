"""DTOs for canonical Excel curriculum import."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.application.dto.programa_documentos import StoredDocumentDTO


@dataclass(frozen=True)
class ExcelValidationIssueDTO:
    """Validation issue detected while reading the canonical workbook."""

    hoja: str
    fila: int | None
    campo: str | None
    mensaje: str


@dataclass(frozen=True)
class ExcelPreviewSummaryDTO:
    """Workbook row counts detected in a validated preview."""

    programa: int
    competencias: int
    resultados: int
    conocimientos: int
    criterios: int


@dataclass(frozen=True)
class ExcelProgramPreviewDTO:
    """Program fields read from the canonical workbook."""

    codigo_programa: str
    nombre_programa: str
    version_programa: str | None


@dataclass(frozen=True)
class ExcelCompetenciaPreviewDTO:
    """Competence row displayed in preview."""

    competencia_id: str
    codigo_competencia: str
    nombre_competencia: str
    resultados: int
    conocimientos: int
    criterios: int


@dataclass(frozen=True)
class ProgramaExcelPreviewDTO:
    """Preview result for the canonical Excel workbook."""

    referencia_id: uuid.UUID
    documento: StoredDocumentDTO | None
    valid: bool
    estado_validacion: str
    resumen: ExcelPreviewSummaryDTO
    programa: ExcelProgramPreviewDTO | None
    competencias: list[ExcelCompetenciaPreviewDTO]
    errores: list[ExcelValidationIssueDTO]


@dataclass(frozen=True)
class ProgramaExcelImportDTO:
    """Result returned after confirming the relational import."""

    referencia_id: uuid.UUID
    programa_id: uuid.UUID
    competencia_ids: list[uuid.UUID]
    resultado_ids: list[uuid.UUID]
    conocimiento_ids: list[uuid.UUID]
    criterio_ids: list[uuid.UUID]
    resumen: ExcelPreviewSummaryDTO
