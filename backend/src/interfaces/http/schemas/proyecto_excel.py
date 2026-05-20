"""Schema for project Excel import responses."""

from __future__ import annotations

from pydantic import BaseModel

from src.application.dto.programa_documentos import StoredDocumentDTO


class ProyectoExcelPreviewResponse(BaseModel):
    """Response returned after previewing a project workbook."""

    referencia_id: str
    documento: StoredDocumentDTO | None
    valid: bool
    estado_validacion: str
    resumen: dict[str, int]
    proyecto: dict[str, object] | None
    fases: list[dict[str, object]]
    pendientes_resumen: dict[str, int]
    errores: list[dict[str, object]]


class ProyectoExcelImportResponse(BaseModel):
    """Response returned after confirming a project Excel import."""

    referencia_id: str
    proyecto_id: str
    fase_ids: list[str]
    actividad_ids: list[str]
    resumen: dict[str, int]
    pendientes_resumen: dict[str, int]
