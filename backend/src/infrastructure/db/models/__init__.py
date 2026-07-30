"""Import all ORM models so SQLAlchemy metadata is fully registered."""

from src.infrastructure.db.models.audit import EventoAuditoria
from src.infrastructure.db.models.curriculum import (
    Competencia,
    Conocimiento,
    CriterioEvaluacion,
    ElementoCurricularPendiente,
    ProgramaFormacion,
    ResultadoAprendizaje,
)
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.planeacion import (
    PlaneacionDocumentoConfig,
    PlaneacionPedagogica,
)
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
    "ElementoCurricularPendiente",
    "EventoAuditoria",
    "FaseProyecto",
    "PlaneacionDocumentoConfig",
    "PlaneacionPedagogica",
    "ProgramaFormacion",
    "ProyectoFormativo",
    "ResultadoAprendizaje",
]
