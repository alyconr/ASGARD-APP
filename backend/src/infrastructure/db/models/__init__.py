"""Import all ORM models so SQLAlchemy metadata is fully registered."""

from src.infrastructure.db.models.audit import EventoAuditoria
from src.infrastructure.db.models.curriculum import (
    Competencia,
    Conocimiento,
    CriterioEvaluacion,
    ProgramaFormacion,
    ResultadoAprendizaje,
)
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.proyecto import (
    ActividadProyecto,
    FaseProyecto,
    ProyectoFormativo,
)

__all__ = [
    "ActividadProyecto",
    "BorradorSesion",
    "Competencia",
    "Conocimiento",
    "CriterioEvaluacion",
    "EventoAuditoria",
    "FaseProyecto",
    "ProgramaFormacion",
    "ProyectoFormativo",
    "ResultadoAprendizaje",
]
