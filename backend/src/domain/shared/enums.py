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


class RolEquipo(str, Enum):
    """Team membership roles inside an executing team."""

    LIDER = "LIDER"
    CO_LIDER = "CO_LIDER"
    INSTRUCTOR = "INSTRUCTOR"
    TRANSVERSAL = "TRANSVERSAL"
    COLABORADOR = "COLABORADOR"


