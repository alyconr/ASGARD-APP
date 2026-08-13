"""DTOs for project canonical Excel import."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.application.dto.programa_documentos import StoredDocumentDTO
from src.domain.shared.enums import TipoResultadoProyecto


@dataclass(frozen=True)
class ExcelProjectPreviewDTO:
    """Preview data for the Proyecto sheet."""

    codigo_proyecto: str
    nombre_proyecto: str
    version_proyecto: str


@dataclass(frozen=True)
class ExcelResultPreviewDTO:
    """Preview data for a RAP from Planeacion_Proyecto."""

    rap_id: str
    rap_numero: str
    resultado_aprendizaje: str
    tipo_resultado: TipoResultadoProyecto | str
    orden_resultado: int | None
    pagina_origen: str | None
    observaciones: str | None


@dataclass(frozen=True)
class ExcelCompetenciaPreviewDTO:
    """Preview data for a Competence from Planeacion_Proyecto."""

    competencia_id: str
    codigo_competencia: str
    nombre_competencia: str
    resultados: list[ExcelResultPreviewDTO]


@dataclass(frozen=True)
class ExcelActividadPreviewDTO:
    """Preview data for an Activity from Planeacion_Proyecto."""

    actividad_id: str
    descripcion: str
    orden: int | None
    competencias: list[ExcelCompetenciaPreviewDTO]


@dataclass(frozen=True)
class ExcelFasePreviewDTO:
    """Preview data for a Phase from Planeacion_Proyecto."""

    fase_id: str
    nombre_fase: str
    orden: int | None
    actividades: list[ExcelActividadPreviewDTO]
    numero_competencias: int
    numero_resultados: int


@dataclass(frozen=True)
class ExcelPreviewSummaryDTO:
    """Summary counts for project preview."""

    proyecto: int
    fases: int
    actividades: int
    resultados_especificos: int


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
    asignaciones_materializadas: int = 0
    asignaciones_sin_competencia: int = 0
    asignaciones_sin_resultado: int = 0


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
