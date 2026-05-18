"""Schema for project PDF upload response."""

from __future__ import annotations

from pydantic import BaseModel

from src.application.dto.programa_documentos import StoredDocumentDTO


class ProyectoPdfUploadResponse(BaseModel):
    """Response returned after storing a project PDF evidence."""

    referencia_id: str
    documento: StoredDocumentDTO
