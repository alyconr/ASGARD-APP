import type {
  ProyectoWizardPayload,
  ProyectoWizardStepDefinition,
  ProyectoWizardStepId,
} from "@/features/proyecto/types";

export const PROYECTO_WIZARD_STEPS: ProyectoWizardStepDefinition[] = [
  {
    id: "datos-proyecto",
    index: 0,
    label: "Datos del proyecto",
    shortLabel: "01",
    description:
      "Base reservada para el formulario del proyecto de TASK-17.",
    taskRef: "TASK-17",
  },
  {
    id: "fuente-proyecto",
    index: 1,
    label: "Fuente del proyecto",
    shortLabel: "02",
    description:
      "Espacio preparado para evidencia PDF y fuente estructurada del proyecto.",
    taskRef: "TASK-18 / TASK-19",
  },
  {
    id: "estructura-proyecto",
    index: 2,
    label: "Fases y actividades",
    shortLabel: "03",
    description:
      "Base navegable para la gestion futura de fases y actividades.",
    taskRef: "TASK-20 / TASK-21",
  },
  {
    id: "revision-proyecto",
    index: 3,
    label: "Revision del proyecto",
    shortLabel: "04",
    description:
      "Lugar del consolidado editable antes del cierre del proyecto.",
    taskRef: "TASK-22",
  },
];

export const DEFAULT_PROYECTO_STEP_ID: ProyectoWizardStepId =
  PROYECTO_WIZARD_STEPS[0].id;

export function isProyectoWizardStepId(
  value: string,
): value is ProyectoWizardStepId {
  return PROYECTO_WIZARD_STEPS.some((step) => step.id === value);
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function asCleanString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value.trim() : fallback;
}

function asNullableString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function normalizeTouchedSteps(value: unknown): ProyectoWizardStepId[] {
  if (!Array.isArray(value)) {
    return [DEFAULT_PROYECTO_STEP_ID];
  }

  const steps = value.filter(
    (stepId): stepId is ProyectoWizardStepId =>
      typeof stepId === "string" && isProyectoWizardStepId(stepId),
  );

  return steps.length > 0
    ? steps.filter((stepId, index, items) => items.indexOf(stepId) === index)
    : [DEFAULT_PROYECTO_STEP_ID];
}

export function createEmptyProyectoPayload(
  referenciaId: string,
  programaReferenciaId: string,
  programaId: string | null,
): ProyectoWizardPayload {
  const now = new Date().toISOString();

  return {
    meta: {
      referenciaId,
      programaReferenciaId,
      programaId,
      touchedSteps: [DEFAULT_PROYECTO_STEP_ID],
      startedAt: now,
      lastInteractionAt: now,
    },
    wizard: {
      notesByStep: {},
    },
    proyecto: {
      proyecto_formativo_id: null,
      codigo_proyecto: "",
      nombre_proyecto: "",
      version_proyecto: "",
    },
    documental: {
      proyecto_pdf: null,
      fuente_estructurada: null,
    },
    estructura: {
      fases: [],
      actividades: [],
    },
  };
}

export function normalizeProyectoPayload(
  value: Record<string, unknown>,
  referenciaId: string,
  programaReferenciaId: string,
  programaId: string | null,
): ProyectoWizardPayload {
  const base = createEmptyProyectoPayload(
    referenciaId,
    programaReferenciaId,
    programaId,
  );
  const meta = asRecord(value.meta);
  const wizard = asRecord(value.wizard);
  const proyecto = asRecord(value.proyecto);
  const notesByStepRecord = asRecord(wizard?.notesByStep);

  const notesByStep = PROYECTO_WIZARD_STEPS.reduce<
    Partial<Record<ProyectoWizardStepId, string>>
  >((accumulator, step) => {
    const note = notesByStepRecord?.[step.id];
    if (typeof note === "string" && note.length > 0) {
      accumulator[step.id] = note;
    }
    return accumulator;
  }, {});

  return {
    ...base,
    meta: {
      referenciaId,
      programaReferenciaId: asString(
        meta?.programaReferenciaId,
        programaReferenciaId,
      ),
      programaId: asNullableString(meta?.programaId) ?? programaId,
      touchedSteps: normalizeTouchedSteps(meta?.touchedSteps),
      startedAt: asString(meta?.startedAt, base.meta.startedAt),
      lastInteractionAt: asString(
        meta?.lastInteractionAt,
        base.meta.lastInteractionAt,
      ),
    },
    wizard: {
      notesByStep,
    },
    proyecto: {
      proyecto_formativo_id: asNullableString(
        proyecto?.proyecto_formativo_id,
      ),
      codigo_proyecto: asCleanString(proyecto?.codigo_proyecto),
      nombre_proyecto: asCleanString(proyecto?.nombre_proyecto),
      version_proyecto: asCleanString(proyecto?.version_proyecto),
    },
  };
}
