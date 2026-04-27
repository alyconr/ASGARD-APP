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
  updated_at?: string;
}

export interface ProgramaPdfUploadResponse {
  referencia_id: string;
  documento: ProgramaStoredDocument;
  diagnostico: ProgramaPdfDiagnostic;
}

export interface ProgramaDraftSnapshot {
  referenciaId: string;
  pasoActual: ProgramaWizardStepId;
  payload: ProgramaWizardPayload;
  estado: DraftStatus;
}
