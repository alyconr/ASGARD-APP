"""Import all ORM models so SQLAlchemy metadata is fully registered."""

from src.infrastructure.db.models.audit import EventoAuditoria
from src.infrastructure.db.models.auth import Rol, Usuario, UsuarioRol
from src.infrastructure.db.models.curriculum import (
    Competencia,
    Conocimiento,
    CriterioEvaluacion,
    ElementoCurricularPendiente,
    ProgramaFormacion,
    ResultadoAprendizaje,
)
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.organizacion import (
    Coordinacion,
    EquipoEjecutor,
    EquipoEjecutorMiembro,
    Especialidad,
    ProcesoCurricular,
)
from src.infrastructure.db.models.planeacion import (
    PlaneacionDocumentoConfig,
    PlaneacionPedagogica,
)
from src.infrastructure.db.models.proyecto import (
    ActividadProyecto,
    AsignacionCurricularProyecto,
    FaseProyecto,
    ProyectoFormativo,
)

__all__ = [
    "ActividadProyecto",
    "AsignacionCurricularProyecto",
    "BorradorSesion",
    "Competencia",
    "Conocimiento",
    "Coordinacion",
    "CriterioEvaluacion",
    "ElementoCurricularPendiente",
    "EquipoEjecutor",
    "EquipoEjecutorMiembro",
    "Especialidad",
    "EventoAuditoria",
    "FaseProyecto",
    "PlaneacionDocumentoConfig",
    "PlaneacionPedagogica",
    "ProcesoCurricular",
    "ProgramaFormacion",
    "ProyectoFormativo",
    "ResultadoAprendizaje",
    "Rol",
    "Usuario",
    "UsuarioRol",
]

