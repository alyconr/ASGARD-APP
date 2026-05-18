import type { DraftStatus } from "@/features/drafts/types";

export type ProyectoWizardStepId =
  | "datos-proyecto"
  | "fuente-proyecto"
  | "estructura-proyecto"
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
}

export interface ExcelProjectPreview {
  codigo_proyecto: string;
  nombre_proyecto: string;
  version_proyecto: string;
}

export interface ExcelFasePreview {
  fase_id: string;
  nombre_fase: string;
  orden: number | null;
  actividades: number;
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
    fases: [];
    actividades: [];
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
}
