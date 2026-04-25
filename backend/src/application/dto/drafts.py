"""DTOs for the draft autosave application service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque


@dataclass(frozen=True)
class SaveDraftCommand:
    """Input command used to create or update a logical draft."""

    tipo_bloque: TipoBloqueBorrador
    referencia_id: uuid.UUID
    paso_actual: str
    payload_json: dict[str, Any]
    estado_borrador: EstadoBloque


@dataclass(frozen=True)
class DraftDTO:
    """Serialized draft returned by the application service."""

    id: uuid.UUID
    tipo_bloque: TipoBloqueBorrador
    referencia_id: uuid.UUID
    paso_actual: str
    payload_json: dict[str, Any]
    estado_borrador: EstadoBloque
    ultima_edicion: datetime
