"""DTOs for canonical Excel curriculum import."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.application.dto.programa_documentos import StoredDocumentDTO
from src.domain.shared.enums import (
    MotivoPendienteAsignacion,
    TipoConocimiento,
    TipoElementoCurricularPendiente,
)


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
class ExcelPendingSummaryDTO:
    """Pending assignment counts detected during preview or import."""

    total: int
    conocimientos: int
    criterios: int


@dataclass(frozen=True)
class ExcelPendingAssignmentDTO:
    """Workbook row that requires manual curricular assignment."""

    tipo_elemento: TipoElementoCurricularPendiente
    tipo_conocimiento: TipoConocimiento | None
    descripcion: str
    competencia_id_origen_excel: str | None
    rap_id_origen_excel: str | None
    motivo: MotivoPendienteAsignacion
    hoja: str
    fila: int | None
    raw_excel: dict[str, object] | None = None


@dataclass(frozen=True)
class ExcelProgramPreviewDTO:
    """Program fields read from the canonical workbook."""

    codigo_programa: str
    nombre_programa: str
    version_programa: str | None


@dataclass(frozen=True)
class ExcelResultadoPreviewDTO:
    """Learning result shown inside its competence preview."""

    rap_id: str
    rap_numero: str | None
    descripcion: str


@dataclass(frozen=True)
class ExcelConocimientoPreviewDTO:
    """Knowledge item shown inside its competence preview."""

    tipo_conocimiento: TipoConocimiento
    descripcion: str
    rap_id: str | None


@dataclass(frozen=True)
class ExcelCriterioPreviewDTO:
    """Evaluation criterion shown inside its competence preview."""

    descripcion: str
    rap_id: str | None


@dataclass(frozen=True)
class ExcelCompetenciaPreviewDTO:
    """Competence row displayed in preview."""

    competencia_id: str
    codigo_competencia: str
    nombre_competencia: str
    resultados: int
    conocimientos: int
    criterios: int
    resultados_detalle: list[ExcelResultadoPreviewDTO]
    conocimientos_detalle: list[ExcelConocimientoPreviewDTO]
    criterios_detalle: list[ExcelCriterioPreviewDTO]


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
    pendientes_resumen: ExcelPendingSummaryDTO
    pendientes: list[ExcelPendingAssignmentDTO]
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
    pendiente_ids: list[uuid.UUID]
    resumen: ExcelPreviewSummaryDTO
    pendientes_resumen: ExcelPendingSummaryDTO
