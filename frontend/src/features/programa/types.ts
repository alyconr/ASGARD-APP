import type { DraftStatus } from "@/features/drafts/types";

export type ProgramaEntryMode = "MANUAL" | "PDF" | "EXCEL" | null;

export type ProgramaWizardStepId =
  | "datos-programa"
  | "origen-documental"
  | "estructura-curricular"
  | "revision-programa";

export type AutosaveState = "idle" | "saving" | "saved" | "error";

export type PdfLegibilityStatus =
  | "LEGIBLE"
  | "PARCIALMENTE_LEGIBLE"
  | "NO_LEGIBLE";

export type FieldTraceStatus =
  | "EXTRAIDO"
  | "MANUAL"
  | "CORREGIDO"
  | "PENDIENTE"
  | "VALIDADO";

export interface ProgramaWizardStepDefinition {
  id: ProgramaWizardStepId;
  index: number;
  label: string;
  shortLabel: string;
  description: string;
}

export interface ResultadoAprendizaje {
  id: string;
  competencia_id: string;
  codigo_resultado: string | null;
  descripcion: string;
  orden: number | null;
  estado: string;
  motivo_fallo_extraccion?: string | null;
  fecha_creacion: string;
  fecha_actualizacion: string;
}

export interface ConocimientoCurricular {
  id: string;
  competencia_id: string;
  resultado_id: string | null;
  tipo: "SABER" | "PROCESO";
  descripcion: string;
  orden: number | null;
  estado: string;
  fecha_creacion: string;
  fecha_actualizacion: string;
}

export interface CriterioEvaluacionCurricular {
  id: string;
  competencia_id: string;
  resultado_id: string | null;
  descripcion: string;
  orden: number | null;
  estado: string;
  fecha_creacion: string;
  fecha_actualizacion: string;
}

export interface ResultadoAprendizajePayload {
  descripcion: string;
  codigo_resultado?: string | null;
}

export interface ResultadoAprendizajeListResponse {
  referencia_id: string;
  competencia_id: string | null;
  resultados: ResultadoAprendizaje[];
}

export interface ResultadoAprendizajeDeleteResponse {
  referencia_id: string;
  competencia_id: string;
  resultado_id: string;
  eliminado: boolean;
}

export interface ProgramaCompetencia {
  id: string;
  programa_id: string;
  codigo_competencia: string;
  nombre_competencia: string;
  orden: number | null;
  estado: "BORRADOR" | "EN_REVISION" | "COMPLETO" | "BLOQUEADO";
  origen_campo: FieldTraceStatus;
  fecha_creacion: string;
  fecha_actualizacion: string;
  resultados?: ResultadoAprendizaje[];
  conocimientos?: ConocimientoCurricular[];
  criterios?: CriterioEvaluacionCurricular[];
}

export interface ProgramaWizardPayload {
  meta: {
    referenciaId: string;
    entryMode: ProgramaEntryMode;
    touchedSteps: ProgramaWizardStepId[];
    startedAt: string;
    lastInteractionAt: string;
  };
  programa: {
    codigo_programa: string;
    nombre_programa: string;
    version_programa: string;
  };
  wizard: {
    notesByStep: Partial<Record<ProgramaWizardStepId, string>>;
  };
  documental: {
    programa_pdf: ProgramaPdfUploadResult | null;
    programa_excel: ProgramaExcelImportState | null;
  };
  curricular: {
    programa_formacion_id: string | null;
    competencias: ProgramaCompetencia[];
  };
}

export interface ProgramaStoredDocument {
  original_filename: string;
  storage_key: string;
  size_bytes: number;
  content_type: string;
  checksum_sha256: string;
  etag: string | null;
}

export interface ProgramaPdfDiagnostic {
  estado_legibilidad: PdfLegibilityStatus;
  motivo: string | null;
  resumen: string;
  has_text_layer: boolean;
  analyzed_pages: number;
  pages_with_text: number;
  text_character_count: number;
  can_attempt_extraction: boolean;
  requires_manual_entry: boolean;
}

export interface ProgramaPdfUploadResult {
  documento: ProgramaStoredDocument;
  diagnostico: ProgramaPdfDiagnostic;
  uso?: "EVIDENCIA_DOCUMENTAL";
  updated_at?: string;
}

export interface ProgramaPdfUploadResponse {
  referencia_id: string;
  documento: ProgramaStoredDocument;
  diagnostico: ProgramaPdfDiagnostic;
}


export interface ProgramaCompetenciaPayload {
  codigo_competencia: string;
  nombre_competencia: string;
}

export interface ProgramaCompetenciaListResponse {
  referencia_id: string;
  programa_id: string | null;
  competencias: ProgramaCompetencia[];
}

export interface ExcelValidationIssue {
  hoja: string;
  fila: number | null;
  campo: string | null;
  mensaje: string;
}

export interface ExcelPreviewSummary {
  programa: number;
  competencias: number;
  resultados: number;
  conocimientos: number;
  criterios: number;
}

export interface ExcelPendingSummary {
  total: number;
  conocimientos: number;
  criterios: number;
}

export type TipoElementoCurricularPendiente = "CONOCIMIENTO" | "CRITERIO";
export type EstadoConciliacionPendiente = "PENDIENTE" | "ASIGNADO";
export type MotivoPendienteAsignacion =
  | "COMPETENCIA_NO_IDENTIFICADA"
  | "RESULTADO_NO_IDENTIFICADO"
  | "ASOCIACION_AMBIGUA";

export interface ExcelPendingAssignment {
  tipo_elemento: TipoElementoCurricularPendiente;
  tipo_conocimiento: "SABER" | "PROCESO" | null;
  descripcion: string;
  competencia_id_origen_excel: string | null;
  rap_id_origen_excel: string | null;
  motivo: MotivoPendienteAsignacion;
  hoja: string;
  fila: number | null;
}

export interface ExcelProgramPreview {
  codigo_programa: string;
  nombre_programa: string;
  version_programa: string | null;
}

export interface ExcelResultadoPreview {
  rap_id: string;
  rap_numero: string | null;
  descripcion: string;
}

export interface ExcelConocimientoPreview {
  tipo_conocimiento: "SABER" | "PROCESO";
  descripcion: string;
  rap_id: string | null;
}

export interface ExcelCriterioPreview {
  descripcion: string;
  rap_id: string | null;
}

export interface ExcelCompetenciaPreview {
  competencia_id: string;
  codigo_competencia: string;
  nombre_competencia: string;
  resultados: number;
  conocimientos: number;
  criterios: number;
  resultados_detalle: ExcelResultadoPreview[];
  conocimientos_detalle: ExcelConocimientoPreview[];
  criterios_detalle: ExcelCriterioPreview[];
}

export interface ProgramaExcelPreviewResponse {
  referencia_id: string;
  documento: ProgramaStoredDocument | null;
  valid: boolean;
  estado_validacion: "VALIDO" | "INVALIDO" | string;
  resumen: ExcelPreviewSummary;
  programa: ExcelProgramPreview | null;
  competencias: ExcelCompetenciaPreview[];
  pendientes_resumen: ExcelPendingSummary;
  pendientes: ExcelPendingAssignment[];
  errores: ExcelValidationIssue[];
}

export interface ProgramaExcelImportResponse {
  referencia_id: string;
  programa_id: string;
  competencia_ids: string[];
  resultado_ids: string[];
  conocimiento_ids: string[];
  criterio_ids: string[];
  pendiente_ids: string[];
  resumen: ExcelPreviewSummary;
  pendientes_resumen: ExcelPendingSummary;
}

export interface ProgramaExcelImportState {
  documento: ProgramaStoredDocument | null;
  preview: ProgramaExcelPreviewResponse | null;
  confirmacion: {
    estado: "PENDIENTE" | "IMPORTADO";
    confirmed_at?: string;
    programa_id?: string;
    competencia_ids?: string[];
    resultado_ids?: string[];
    conocimiento_ids?: string[];
    criterio_ids?: string[];
    pendiente_ids?: string[];
    pendientes_resumen?: ExcelPendingSummary;
  };
  updated_at?: string;
}

export interface PendienteCurricular {
  id: string;
  referencia_id: string;
  programa_id: string | null;
  tipo_elemento: TipoElementoCurricularPendiente;
  tipo_conocimiento: "SABER" | "PROCESO" | null;
  descripcion: string;
  competencia_id_origen_excel: string | null;
  rap_id_origen_excel: string | null;
  motivo: MotivoPendienteAsignacion;
  estado: EstadoConciliacionPendiente;
  competencia_destino_id: string | null;
  resultado_destino_id: string | null;
  elemento_creado_id: string | null;
  fecha_creacion: string;
  fecha_actualizacion: string;
}

export interface PendienteCurricularListResponse {
  referencia_id: string;
  pendientes: PendienteCurricular[];
}

export interface PendienteCurricularAsignacionResponse {
  referencia_id: string;
  pendiente: PendienteCurricular;
}

export interface ProgramaCompetenciaDeleteResponse {
  referencia_id: string;
  programa_id: string;
  competencia_id: string;
  eliminado: boolean;
}

export interface ProgramaDraftSnapshot {
  referenciaId: string;
  pasoActual: ProgramaWizardStepId;
  payload: ProgramaWizardPayload;
  estado: DraftStatus;
}
