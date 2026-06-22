import type { DraftStatus } from "@/features/drafts/types";

export type ProyectoWizardStepId =
  | "fuente-proyecto"
  | "revision-proyecto";

export interface ProyectoWizardStepDefinition {
  id: ProyectoWizardStepId;
  index: number;
  label: string;
  shortLabel: string;
  description: string;
  taskRef: string;
}

export interface ProyectoStoredDocument {
  original_filename: string;
  storage_key: string;
  size_bytes: number;
  content_type: string;
  checksum_sha256: string;
  etag: string | null;
}

export interface ProyectoPdfUploadResult {
  documento: ProyectoStoredDocument;
  uso: "EVIDENCIA_DOCUMENTAL";
  updated_at?: string;
}

export interface ExcelPendingSummary {
  total: number;
}

export interface ExcelValidationIssue {
  hoja: string;
  fila: number | null;
  campo: string | null;
  mensaje: string;
}

export interface ExcelPreviewSummary {
  proyecto: number;
  fases: number;
  actividades: number;
  resultados_especificos: number;
}

export interface ExcelProjectPreview {
  codigo_proyecto: string;
  nombre_proyecto: string;
  version_proyecto: string;
}

export interface ExcelResultPreview {
  rap_id: string;
  rap_numero: string;
  resultado_aprendizaje: string;
  tipo_resultado: string;
  orden_resultado: number | null;
  pagina_origen: string | null;
  observaciones: string | null;
}

export interface ExcelCompetenciaPreview {
  competencia_id: string;
  codigo_competencia: string;
  nombre_competencia: string;
  resultados: ExcelResultPreview[];
}

export interface ExcelActividadPreview {
  actividad_id: string;
  descripcion: string;
  orden: number | null;
  competencias: ExcelCompetenciaPreview[];
}

export interface ExcelFasePreview {
  fase_id: string;
  nombre_fase: string;
  orden: number | null;
  actividades: ExcelActividadPreview[];
  numero_competencias: number;
  numero_resultados: number;
}

export interface ProyectoExcelPreviewState {
  documento: ProyectoStoredDocument | null;
  preview: {
    valid: boolean;
    estado_validacion: "VALIDO" | "INVALIDO";
    resumen: ExcelPreviewSummary;
    proyecto: ExcelProjectPreview | null;
    fases: ExcelFasePreview[];
    pendientes_resumen: ExcelPendingSummary;
    errores: ExcelValidationIssue[];
  } | null;
  confirmacion: {
    estado: "PENDIENTE" | "IMPORTADO";
    confirmed_at?: string;
    proyecto_id?: string;
    fase_ids?: string[];
    actividad_ids?: string[];
    pendientes_resumen?: ExcelPendingSummary;
  };
  updated_at?: string;
}

export interface ProyectoWizardPayload {
  meta: {
    referenciaId: string;
    programaReferenciaId: string;
    programaId: string | null;
    touchedSteps: ProyectoWizardStepId[];
    startedAt: string;
    lastInteractionAt: string;
  };
  wizard: {
    notesByStep: Partial<Record<ProyectoWizardStepId, string>>;
  };
  proyecto: {
    proyecto_formativo_id: string | null;
    codigo_proyecto: string;
    nombre_proyecto: string;
    version_proyecto: string;
  };
  documental: {
    proyecto_pdf: ProyectoPdfUploadResult | null;
    fuente_estructurada: ProyectoExcelPreviewState | null;
  };
  estructura: {
    fases: Array<{ fase_id: string; estado: string }>;
    actividades: Array<{ actividad_id: string; estado: string }>;
  };
}

export interface ProyectoDraftSnapshot {
  referenciaId: string;
  pasoActual: ProyectoWizardStepId;
  payload: ProyectoWizardPayload;
  estado: DraftStatus;
}

export interface ProyectoDisponibilidadResponse {
  referencia_id: string;
  programa_id: string | null;
  estado_programa: DraftStatus | null;
  programa_completo: boolean;
  proyecto_bloqueado: boolean;
  estado_proyecto: DraftStatus;
  motivo: string | null;
  mensaje: string;
  accion_sugerida: "completar_y_cerrar_programa" | "iniciar_proyecto" | string;
  programa_referencia_id?: string | null;
}

export interface ProyectoCompletitudFaltanteResponse {
  codigo: string;
  campo: string;
  mensaje: string;
  fase_id: string | null;
  fase_nombre: string | null;
}

export interface ProyectoCompletitudResumenResponse {
  fases: number;
  actividades: number;
}

export interface ProyectoCompletitudResponse {
  referencia_id: string;
  proyecto_id: string | null;
  estado_actual: DraftStatus | null;
  cerrable: boolean;
  resumen: ProyectoCompletitudResumenResponse;
  faltantes: ProyectoCompletitudFaltanteResponse[];
}

export interface ProyectoCierreResponse {
  referencia_id: string;
  proyecto_id: string;
  estado: DraftStatus;
  mensaje: string;
  completitud: ProyectoCompletitudResponse;
}
