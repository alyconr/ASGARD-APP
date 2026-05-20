"""DTOs for project canonical Excel import."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.application.dto.programa_documentos import StoredDocumentDTO


@dataclass(frozen=True)
class ExcelProjectPreviewDTO:
    """Preview data for the Proyecto sheet."""

    codigo_proyecto: str
    nombre_proyecto: str
    version_proyecto: str


@dataclass(frozen=True)
class ExcelFasePreviewDTO:
    """Preview data for a Fase sheet row."""

    fase_id: str
    nombre_fase: str
    orden: int | None
    actividades: int


@dataclass(frozen=True)
class ExcelActividadPreviewDTO:
    """Preview data for an Actividad sheet row."""

    descripcion: str
    orden: int | None


@dataclass(frozen=True)
class ExcelPreviewSummaryDTO:
    """Summary counts for project preview."""

    proyecto: int
    fases: int
    actividades: int


@dataclass(frozen=True)
class ExcelValidationIssueDTO:
    """A single validation issue found in the workbook."""

    hoja: str
    fila: int | None
    campo: str | None
    mensaje: str


@dataclass(frozen=True)
class ExcelPendingSummaryDTO:
    """Summary of post-import correction items."""

    total: int


@dataclass(frozen=True)
class ProyectoExcelPreviewDTO:
    """Full preview response for a project workbook."""

    referencia_id: uuid.UUID
    documento: StoredDocumentDTO | None
    valid: bool
    estado_validacion: str
    resumen: ExcelPreviewSummaryDTO
    proyecto: ExcelProjectPreviewDTO | None
    fases: list[ExcelFasePreviewDTO]
    pendientes_resumen: ExcelPendingSummaryDTO
    errores: list[ExcelValidationIssueDTO]


@dataclass(frozen=True)
class ProyectoExcelImportDTO:
    """Result after confirming a project Excel import."""

    referencia_id: uuid.UUID
    proyecto_id: uuid.UUID
    fase_ids: list[uuid.UUID]
    actividad_ids: list[uuid.UUID]
    resumen: ExcelPreviewSummaryDTO
    pendientes_resumen: ExcelPendingSummaryDTO
