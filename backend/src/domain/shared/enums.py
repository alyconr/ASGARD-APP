"""Domain enums shared by the Phase 1 data model."""

from __future__ import annotations

from enum import Enum


class EstadoBloque(str, Enum):
    """Lifecycle states for top-level blocks and persisted drafts."""

    BORRADOR = "BORRADOR"
    EN_REVISION = "EN_REVISION"
    COMPLETO = "COMPLETO"
    BLOQUEADO = "BLOQUEADO"


class TipoFuenteCargue(str, Enum):
    """Supported sources for the initial capture of a root entity."""

    PDF_EXTRACCION = "PDF_EXTRACCION"
    PDF_EVIDENCIA = "PDF_EVIDENCIA"
    EXCEL_CANONICO = "EXCEL_CANONICO"
    MANUAL = "MANUAL"
    MIXTO = "MIXTO"


class TipoConocimiento(str, Enum):
    """Knowledge categories required by the curriculum structure."""

    SABER = "SABER"
    PROCESO = "PROCESO"


class TipoElementoCurricularPendiente(str, Enum):
    """Curricular element types that can wait for manual assignment."""

    CONOCIMIENTO = "CONOCIMIENTO"
    CRITERIO = "CRITERIO"


class MotivoPendienteAsignacion(str, Enum):
    """Reasons why an Excel row needs human reconciliation."""

    COMPETENCIA_NO_IDENTIFICADA = "COMPETENCIA_NO_IDENTIFICADA"
    RESULTADO_NO_IDENTIFICADO = "RESULTADO_NO_IDENTIFICADO"
    ASOCIACION_AMBIGUA = "ASOCIACION_AMBIGUA"


class EstadoConciliacionPendiente(str, Enum):
    """Lifecycle for unresolved curricular rows imported from Excel."""

    PENDIENTE = "PENDIENTE"
    ASIGNADO = "ASIGNADO"


class EstadoCampo(str, Enum):
    """Traceability state for extracted or manually edited content."""

    EXTRAIDO = "EXTRAIDO"
    MANUAL = "MANUAL"
    CORREGIDO = "CORREGIDO"
    PENDIENTE = "PENDIENTE"
    VALIDADO = "VALIDADO"


class MotivoFalloExtraccion(str, Enum):
    """Minimum extraction failure reasons required by the documents."""

    PDF_ESCANEADO = "PDF_ESCANEADO"
    DOCUMENTO_ILEGIBLE = "DOCUMENTO_ILEGIBLE"
    BAJA_RESOLUCION = "BAJA_RESOLUCION"
    ESTRUCTURA_NO_RECONOCIDA = "ESTRUCTURA_NO_RECONOCIDA"
    CAMPO_NO_ENCONTRADO = "CAMPO_NO_ENCONTRADO"
    CONTENIDO_AMBIGUO = "CONTENIDO_AMBIGUO"
    ARCHIVO_PROTEGIDO = "ARCHIVO_PROTEGIDO"


class TipoResultadoProyecto(str, Enum):
    """Authoritative Learning Result classification for project activities."""

    ESPECIFICO = "ESPECIFICO"
    TRANSVERSAL = "TRANSVERSAL"
    BASICO = "BASICO"


class RolUsuario(str, Enum):
    """System roles for ASGARD RBAC."""

    SUPERADMIN = "SUPERADMIN"
    ADMIN = "ADMIN"
    LIDER_EQUIPO_EJECUTOR = "LIDER_EQUIPO_EJECUTOR"
    USUARIO_ADICIONAL = "USUARIO_ADICIONAL"


class TipoNecesidadProceso(str, Enum):
    """Operational curricular requirement category."""

    CREAR_PLANEACION = "CREAR_PLANEACION"
    ACTUALIZAR_PLANEACION = "ACTUALIZAR_PLANEACION"
    CREAR_GUIA = "CREAR_GUIA"
    AJUSTAR_GUIA = "AJUSTAR_GUIA"


class EstadoScopeProceso(str, Enum):
    """Assignment lifecycle for curricular processes."""

    ASIGNADO = "ASIGNADO"
    SIN_ASIGNAR = "SIN_ASIGNAR"


class EstadoEquipo(str, Enum):
    """Operating status of an executing team."""

    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"


class EstadoUsuario(str, Enum):
    """Account status for users."""

    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"
    BLOQUEADO = "BLOQUEADO"


class EstadoEntregaRevision(str, Enum):
    """Lifecycle states for a curricular submission and review cycle."""

    BORRADOR = "BORRADOR"
    ENVIADO_REVISION = "ENVIADO_REVISION"
    EN_REVISION = "EN_REVISION"
    AJUSTES_SOLICITADOS = "AJUSTES_SOLICITADOS"
    AJUSTES_EN_PROGRESO = "AJUSTES_EN_PROGRESO"
    REENVIADO = "REENVIADO"
    APROBADO = "APROBADO"


class TipoElementoObservacion(str, Enum):
    """Target entity or level of a pedagogical review feedback observation."""

    PROCESO_GENERAL = "PROCESO_GENERAL"
    PROGRAMA = "PROGRAMA"
    PROYECTO = "PROYECTO"
    PLANEACION = "PLANEACION"
    CONFIGURACION_DOCUMENTAL = "CONFIGURACION_DOCUMENTAL"
    SECCION = "SECCION"


class EstadoObservacionRevision(str, Enum):
    """Lifecycle states for individual feedback observations."""

    PENDIENTE = "PENDIENTE"
    AJUSTE_REPORTADO = "AJUSTE_REPORTADO"
    RESUELTO = "RESUELTO"


class SeccionObservacionPlaneacion(str, Enum):
    """Catalog of valid planning sections for targeted pedagogical observations."""

    GENERAL = "GENERAL"
    FASE = "FASE"
    ACTIVIDAD_PROYECTO = "ACTIVIDAD_PROYECTO"
    COMPETENCIA = "COMPETENCIA"
    RAPS = "RAPS"
    ACTIVIDADES_APRENDIZAJE = "ACTIVIDADES_APRENDIZAJE"
    DESCRIPCION_EVIDENCIA_APRENDIZAJE = "DESCRIPCION_EVIDENCIA_APRENDIZAJE"
    SABERES = "SABERES"
    CRITERIOS_EVALUACION = "CRITERIOS_EVALUACION"
    ESTRATEGIAS_DIDACTICAS = "ESTRATEGIAS_DIDACTICAS"
    AMBIENTES = "AMBIENTES"
    MATERIALES = "MATERIALES"
    INSTRUCTORES = "INSTRUCTORES"
    HORAS = "HORAS"


class EstadoRevisionPlaneacion(str, Enum):
    """Explicit review lifecycle state (review_status) for plannings."""

    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    OBSERVED = "OBSERVED"
    APPROVED = "APPROVED"
    CHANGES_ALLOWED = "CHANGES_ALLOWED"


class EstadoAprobacionPlaneacion(str, Enum):
    """Explicit pedagogical approval state (approval_status) for plannings."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    PREVIOUS_VERSION_APPROVED = "PREVIOUS_VERSION_APPROVED"
    REJECTED = "REJECTED"


class EstadoEdicionRA(str, Enum):
    """Explicit editability lock state (edit_status) for Learning Results and plannings."""

    EDITABLE = "EDITABLE"
    LOCKED = "LOCKED"


class EstadoSolicitudReapertura(str, Enum):
    """Lifecycle states for a formal planning edit reopening request (PlanningEditRequest)."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    PARTIALLY_APPROVED = "PARTIALLY_APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"



