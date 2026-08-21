"""Schema for project Excel import responses."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from src.application.dto.programa_documentos import StoredDocumentDTO
from src.domain.shared.enums import TipoResultadoProyecto


class ExcelValidationIssueResponse(BaseModel):
    """A single validation issue found in the workbook."""

    model_config = ConfigDict(from_attributes=True)

    hoja: str
    fila: int | None
    campo: str | None
    mensaje: str


class ExcelPreviewSummaryResponse(BaseModel):
    """Summary counts for project preview."""

    model_config = ConfigDict(from_attributes=True)

    proyecto: int
    fases: int
    actividades: int
    resultados_especificos: int


class ExcelProjectPreviewResponse(BaseModel):
    """Preview data for the Proyecto sheet."""

    model_config = ConfigDict(from_attributes=True)

    codigo_proyecto: str
    nombre_proyecto: str
    version_proyecto: str


class ExcelResultPreviewResponse(BaseModel):
    """Preview data for a RAP from Planeacion_Proyecto."""

    model_config = ConfigDict(from_attributes=True)

    rap_id: str
    rap_numero: str
    resultado_aprendizaje: str
    tipo_resultado: TipoResultadoProyecto | None
    orden_resultado: int | None
    pagina_origen: str | None
    observaciones: str | None


class ExcelCompetenciaPreviewResponse(BaseModel):
    """Preview data for a Competence from Planeacion_Proyecto."""

    model_config = ConfigDict(from_attributes=True)

    competencia_id: str
    codigo_competencia: str
    nombre_competencia: str
    resultados: list[ExcelResultPreviewResponse]


class ExcelActividadPreviewResponse(BaseModel):
    """Preview data for an Activity from Planeacion_Proyecto."""

    model_config = ConfigDict(from_attributes=True)

    actividad_id: str
    descripcion: str
    orden: int | None
    competencias: list[ExcelCompetenciaPreviewResponse]


class ExcelFasePreviewResponse(BaseModel):
    """Preview data for a Phase from Planeacion_Proyecto."""

    model_config = ConfigDict(from_attributes=True)

    fase_id: str
    nombre_fase: str
    orden: int | None
    actividades: list[ExcelActividadPreviewResponse]
    numero_competencias: int
    numero_resultados: int


class ExcelPendingSummaryResponse(BaseModel):
    """Summary of post-import correction items."""

    model_config = ConfigDict(from_attributes=True)

    total: int


class ProyectoExcelPreviewResponse(BaseModel):
    """Response returned after previewing a project workbook."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    documento: StoredDocumentDTO | None
    valid: bool
    estado_validacion: str
    resumen: ExcelPreviewSummaryResponse
    proyecto: ExcelProjectPreviewResponse | None
    fases: list[ExcelFasePreviewResponse]
    pendientes_resumen: ExcelPendingSummaryResponse
    errores: list[ExcelValidationIssueResponse]


class ProyectoExcelImportResponse(BaseModel):
    """Response returned after confirming a project Excel import."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    proyecto_id: uuid.UUID
    fase_ids: list[uuid.UUID]
    actividad_ids: list[uuid.UUID]
    resumen: ExcelPreviewSummaryResponse
    pendientes_resumen: ExcelPendingSummaryResponse
