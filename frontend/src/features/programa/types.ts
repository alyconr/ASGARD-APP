import type { DraftStatus } from "@/features/drafts/types";

export type ProgramaEntryMode = "MANUAL" | "PDF" | null;

export type ProgramaWizardStepId =
  | "datos-programa"
  | "origen-documental"
  | "estructura-curricular"
  | "revision-programa";

export type AutosaveState = "idle" | "saving" | "saved" | "error";

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
}

export interface ProgramaDraftSnapshot {
  referenciaId: string;
  pasoActual: ProgramaWizardStepId;
  payload: ProgramaWizardPayload;
  estado: DraftStatus;
}
