"""DTOs for program competence CRUD operations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.shared.enums import EstadoBloque, EstadoCampo, TipoConocimiento


@dataclass(frozen=True)
class ResultadoAprendizajeResumenDTO:
    """Learning result nested inside a competence summary."""

    id: uuid.UUID
    competencia_id: uuid.UUID
    codigo_resultado: str | None
    descripcion: str
    orden: int | None
    estado: EstadoCampo
    fecha_creacion: datetime
    fecha_actualizacion: datetime


@dataclass(frozen=True)
class ConocimientoResumenDTO:
    """Knowledge item nested inside a competence summary."""

    id: uuid.UUID
    competencia_id: uuid.UUID
    resultado_id: uuid.UUID | None
    tipo: TipoConocimiento
    descripcion: str
    orden: int | None
    estado: EstadoCampo
    fecha_creacion: datetime
    fecha_actualizacion: datetime


@dataclass(frozen=True)
class CriterioEvaluacionResumenDTO:
    """Evaluation criterion nested inside a competence summary."""

    id: uuid.UUID
    competencia_id: uuid.UUID
    resultado_id: uuid.UUID | None
    descripcion: str
    orden: int | None
    estado: EstadoCampo
    fecha_creacion: datetime
    fecha_actualizacion: datetime


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
    resultados: list[ResultadoAprendizajeResumenDTO] = field(default_factory=list)
    conocimientos: list[ConocimientoResumenDTO] = field(default_factory=list)
    criterios: list[CriterioEvaluacionResumenDTO] = field(default_factory=list)


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
