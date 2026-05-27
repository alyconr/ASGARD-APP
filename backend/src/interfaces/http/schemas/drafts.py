"""Schemas for draft autosave and recovery endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.domain.drafts.types import TipoBloqueBorrador, validate_draft_state
from src.domain.shared.enums import EstadoBloque


class DraftSaveRequest(BaseModel):
    """Payload accepted by the draft autosave endpoint."""

    paso_actual: str = Field(min_length=1, max_length=100)
    payload_json: dict[str, Any]
    estado_borrador: EstadoBloque

    @field_validator("paso_actual")
    @classmethod
    def validate_step(cls, value: str) -> str:
        """Reject blank step values after trimming whitespace."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("paso_actual es obligatorio")
        return normalized


class DraftResponse(BaseModel):
    """Draft representation returned by save and recovery endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo_bloque: TipoBloqueBorrador
    referencia_id: uuid.UUID
    paso_actual: str
    payload_json: dict[str, Any]
    estado_borrador: EstadoBloque
    ultima_edicion: datetime


class DraftPathParams(BaseModel):
    """Validated path data shared by draft endpoints."""

    tipo_bloque: TipoBloqueBorrador
    referencia_id: uuid.UUID


class SaveDraftInput(BaseModel):
    """Validated request assembled from path and body data."""

    tipo_bloque: TipoBloqueBorrador
    referencia_id: uuid.UUID
    paso_actual: str = Field(min_length=1, max_length=100)
    payload_json: dict[str, Any]
    estado_borrador: EstadoBloque

    @field_validator("paso_actual")
    @classmethod
    def validate_step(cls, value: str) -> str:
        """Reject blank step values after trimming whitespace."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("paso_actual es obligatorio")
        return normalized

    @model_validator(mode="after")
    def validate_state_for_block(self) -> "SaveDraftInput":
        """Ensure draft state is valid for the requested block type."""
        validate_draft_state(self.tipo_bloque, self.estado_borrador)
        return self


class DocumentoMetadataDTO(BaseModel):
    """Metadata representing a stored file."""

    original_filename: str
    storage_key: str
    size_bytes: int
    content_type: str
    checksum_sha256: str
    updated_at: str | None = None


class EstadoDocumentalResponse(BaseModel):
    """Response representing the overall document upload state for a wizard session."""

    programa_excel: DocumentoMetadataDTO | None = None
    proyecto_excel: DocumentoMetadataDTO | None = None
    programa_pdf: DocumentoMetadataDTO | None = None
    proyecto_pdf: DocumentoMetadataDTO | None = None
    programa_importado: bool = False
    proyecto_importado: bool = False
    documentos_habilitados: bool = False
    cargue_pdf_habilitado: bool = False
