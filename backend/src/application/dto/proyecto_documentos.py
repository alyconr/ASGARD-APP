"""DTOs for project PDF evidence upload."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.application.dto.programa_documentos import StoredDocumentDTO


@dataclass(frozen=True)
class ProjectPdfUploadResultDTO:
    """Result returned by the project PDF upload use case."""

    referencia_id: uuid.UUID
    documento: StoredDocumentDTO
