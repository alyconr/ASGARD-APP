"""Schema for project PDF upload response."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from src.application.dto.programa_documentos import StoredDocumentDTO


class ProyectoPdfUploadResponse(BaseModel):
    """Response returned after storing a project PDF evidence."""

    model_config = ConfigDict(from_attributes=True)

    referencia_id: uuid.UUID
    documento: StoredDocumentDTO
