"""DTOs for program competence CRUD operations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from src.domain.shared.enums import EstadoBloque, EstadoCampo


@dataclass(frozen=True)
class CompetenciaDTO:
    """Competence data returned by the application service."""

    id: uuid.UUID
    programa_id: uuid.UUID
    codigo_competencia: str
    nombre_competencia: str
    orden: int | None
    estado: EstadoBloque
    origen_campo: EstadoCampo
    fecha_creacion: datetime
    fecha_actualizacion: datetime


@dataclass(frozen=True)
class CompetenciaPayloadDTO:
    """Payload accepted for creating or updating a competence."""

    codigo_competencia: str
    nombre_competencia: str


@dataclass(frozen=True)
class CompetenciaListDTO:
    """Competence collection tied to the current program draft."""

    referencia_id: uuid.UUID
    programa_id: uuid.UUID | None
    competencias: list[CompetenciaDTO]


@dataclass(frozen=True)
class CompetenciaDeleteDTO:
    """Result returned after deleting a competence."""

    referencia_id: uuid.UUID
    programa_id: uuid.UUID
    competencia_id: uuid.UUID
    eliminado: bool
