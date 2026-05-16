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
    proyecto_pdf: null;
    fuente_estructurada: null;
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
