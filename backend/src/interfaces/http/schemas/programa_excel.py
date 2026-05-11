"""HTTP schemas for canonical Excel curriculum import."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from src.interfaces.http.schemas.programa_documentos import StoredDocumentResponse


class ExcelValidationIssueResponse(BaseModel):
    """Validation issue returned by the workbook preview."""

    model_config = ConfigDict(from_attributes=True)

    hoja: str
    fila: int | None
    campo: str | None
    mensaje: str


class ExcelPreviewSummaryResponse(BaseModel):
    """Workbook row counts detected in preview."""

    model_config = ConfigDict(from_attributes=True)

    programa: int
    competencias: int
    resultados: int
    conocimientos: int
    criterios: int


class ExcelPendingSummaryResponse(BaseModel):
    """Pending assignment counts detected in preview or import."""

    model_config = ConfigDict(from_attributes=True)

    total: int
    conocimientos: int
    criterios: int


class ExcelPendingAssignmentResponse(BaseModel):
    """Unresolved workbook row shown for later manual assignment."""

    model_config = ConfigDict(from_attributes=True)

    tipo_elemento: str
    tipo_conocimiento: str | None
    descripcion: str
    competencia_id_origen_excel: str | None
    rap_id_origen_excel: str | None
    motivo: str
    hoja: str
    fila: int | None


class ExcelProgramPreviewResponse(BaseModel):
    """Program fields read from the canonical workbook."""

    model_config = ConfigDict(from_attributes=True)

    codigo_programa: str
    nombre_programa: str
    version_programa: str | None


class ExcelCompetenciaPreviewResponse(BaseModel):
    """Competence row shown in preview."""

    model_config = ConfigDict(from_attributes=True)

    competencia_id: str
    codigo_competencia: str
    nombre_competencia: str
    resultados: int
    conocimientos: int
    criterios: int


class ProgramaExcelPreviewResponse(BaseModel):
    """Response returned after validating a canonical Excel workbook."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    documento: StoredDocumentResponse | None
    valid: bool
    estado_validacion: str
    resumen: ExcelPreviewSummaryResponse
    programa: ExcelProgramPreviewResponse | None
    competencias: list[ExcelCompetenciaPreviewResponse]
    pendientes_resumen: ExcelPendingSummaryResponse
    pendientes: list[ExcelPendingAssignmentResponse]
    errores: list[ExcelValidationIssueResponse]


class ProgramaExcelImportResponse(BaseModel):
    """Response returned after confirming relational import."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    programa_id: uuid.UUID
    competencia_ids: list[uuid.UUID]
    resultado_ids: list[uuid.UUID]
    conocimiento_ids: list[uuid.UUID]
    criterio_ids: list[uuid.UUID]
    pendiente_ids: list[uuid.UUID]
    resumen: ExcelPreviewSummaryResponse
    pendientes_resumen: ExcelPendingSummaryResponse
