import type { DraftStatus } from "@/features/drafts/types";

export type ProgramaEntryMode = "MANUAL" | "PDF" | null;

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

export type ExtractionFailureReason =
  | "PDF_ESCANEADO"
  | "DOCUMENTO_ILEGIBLE"
  | "BAJA_RESOLUCION"
  | "ESTRUCTURA_NO_RECONOCIDA"
  | "CAMPO_NO_ENCONTRADO"
  | "CONTENIDO_AMBIGUO"
  | "ARCHIVO_PROTEGIDO";

export interface ProgramaWizardStepDefinition {
  id: ProgramaWizardStepId;
  index: number;
  label: string;
  shortLabel: string;
  description: string;
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
  extraccion: ProgramaExtractionResult | null;
  updated_at?: string;
}

export interface ProgramaPdfUploadResponse {
  referencia_id: string;
  documento: ProgramaStoredDocument;
  diagnostico: ProgramaPdfDiagnostic;
}

export interface ProgramaExtractedField {
  campo: string;
  valor: string | null;
  estado: FieldTraceStatus;
  motivo: ExtractionFailureReason | null;
  requiere_revision: boolean;
  aplicado_al_borrador: boolean;
  valor_actual_borrador: string | null;
}

export interface ProgramaExtractedTextItem {
  valor: string;
  estado: FieldTraceStatus;
  motivo: ExtractionFailureReason | null;
  requiere_revision: boolean;
}

export interface ProgramaExtractedListBlock {
  items: ProgramaExtractedTextItem[];
  estado: FieldTraceStatus;
  motivo: ExtractionFailureReason | null;
  requiere_revision: boolean;
}

export interface ProgramaExtractionResult {
  referencia_id: string;
  estado_legibilidad: PdfLegibilityStatus;
  resumen: string;
  requiere_revision_humana: boolean;
  programa: {
    codigo_programa: ProgramaExtractedField;
    nombre_programa: ProgramaExtractedField;
  };
  estructura_curricular: {
    competencias: ProgramaExtractedListBlock;
    resultados_aprendizaje: ProgramaExtractedListBlock;
    conocimientos_saber: ProgramaExtractedListBlock;
    conocimientos_proceso: ProgramaExtractedListBlock;
    criterios_evaluacion: ProgramaExtractedListBlock;
  };
  programa_actualizado: {
    codigo_programa: string;
    nombre_programa: string;
    version_programa: string;
  };
  updated_at?: string;
}

export interface ProgramaDraftSnapshot {
  referenciaId: string;
  pasoActual: ProgramaWizardStepId;
  payload: ProgramaWizardPayload;
  estado: DraftStatus;
}
