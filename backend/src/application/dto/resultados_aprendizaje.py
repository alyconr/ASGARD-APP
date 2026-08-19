"""Data transfer objects for learning outcomes (resultados de aprendizaje) use cases."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from src.domain.shared.enums import EstadoCampo, MotivoFalloExtraccion


@dataclass(frozen=True)
class ResultadoAprendizajePayloadDTO:
    """Input representation for creating or updating a learning outcome."""

    descripcion: str
    codigo_resultado: str | None = None


@dataclass(frozen=True)
class ResultadoAprendizajeDTO:
    """Output representation of a learning outcome."""

    id: uuid.UUID
    competencia_id: uuid.UUID
    descripcion: str
    estado: EstadoCampo
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    codigo_resultado: str | None = None
    orden: int | None = None
    motivo_fallo_extraccion: MotivoFalloExtraccion | None = None


@dataclass(frozen=True)
class ResultadoAprendizajeListDTO:
    """Response containing a list of learning outcomes for a draft reference."""

    referencia_id: uuid.UUID
    competencia_id: uuid.UUID | None
    resultados: list[ResultadoAprendizajeDTO]


@dataclass(frozen=True)
class ResultadoAprendizajeDeleteDTO:
    """Response returned when a learning outcome is deleted."""

    referencia_id: uuid.UUID
    competencia_id: uuid.UUID
    resultado_id: uuid.UUID
    eliminado: bool
