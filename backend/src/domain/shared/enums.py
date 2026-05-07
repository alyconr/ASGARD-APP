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
