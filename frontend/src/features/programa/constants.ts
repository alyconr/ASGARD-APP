import type {
  ProgramaWizardPayload,
  ProgramaWizardStepDefinition,
  ProgramaWizardStepId,
} from "@/features/programa/types";

export const PROGRAMA_WIZARD_STEPS: ProgramaWizardStepDefinition[] = [
  {
    id: "datos-programa",
    index: 0,
    label: "Datos del programa",
    shortLabel: "01",
    description:
      "Entrada inicial para los datos minimos del programa y su borrador.",
  },
  {
    id: "origen-documental",
    index: 1,
    label: "Origen documental",
    shortLabel: "02",
    description:
      "Seleccion del origen de informacion y punto preparado para el carril PDF/manual.",
  },
  {
    id: "estructura-curricular",
    index: 2,
    label: "Estructura curricular",
    shortLabel: "03",
    description:
      "Espacio de trabajo para competencias, resultados, saberes, procesos y criterios.",
  },
  {
    id: "revision-programa",
    index: 3,
    label: "Revision del programa",
    shortLabel: "04",
    description:
      "Revision consolidada del programa antes de cualquier cierre funcional.",
  },
];

export const DEFAULT_PROGRAMA_STEP_ID: ProgramaWizardStepId =
  PROGRAMA_WIZARD_STEPS[0].id;

export function isProgramaWizardStepId(
  value: string,
): value is ProgramaWizardStepId {
  return PROGRAMA_WIZARD_STEPS.some((step) => step.id === value);
}

function normalizeStepList(
  touchedSteps: ProgramaWizardPayload["meta"]["touchedSteps"],
): ProgramaWizardStepId[] {
  return touchedSteps.filter((stepId, index, items) => {
    return isProgramaWizardStepId(stepId) && items.indexOf(stepId) === index;
  });
}

export function createEmptyProgramaPayload(
  referenciaId: string,
): ProgramaWizardPayload {
  const now = new Date().toISOString();

  return {
    meta: {
      referenciaId,
      entryMode: null,
      touchedSteps: [DEFAULT_PROGRAMA_STEP_ID],
      startedAt: now,
      lastInteractionAt: now,
    },
    programa: {
      codigo_programa: "",
      nombre_programa: "",
      version_programa: "",
    },
    wizard: {
      notesByStep: {},
    },
  };
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

export function normalizeProgramaPayload(
  value: Record<string, unknown>,
  referenciaId: string,
): ProgramaWizardPayload {
  const base = createEmptyProgramaPayload(referenciaId);
  const meta = asRecord(value.meta);
  const programa = asRecord(value.programa);
  const wizard = asRecord(value.wizard);
  const notesByStepRecord = asRecord(wizard?.notesByStep);

  const touchedStepsCandidate = Array.isArray(meta?.touchedSteps)
    ? meta.touchedSteps.filter(
        (stepId): stepId is ProgramaWizardStepId =>
          typeof stepId === "string" && isProgramaWizardStepId(stepId),
      )
    : base.meta.touchedSteps;

  const notesByStep = PROGRAMA_WIZARD_STEPS.reduce<
    Partial<Record<ProgramaWizardStepId, string>>
  >((accumulator, step) => {
    const note = notesByStepRecord?.[step.id];
    if (typeof note === "string" && note.length > 0) {
      accumulator[step.id] = note;
    }

    return accumulator;
  }, {});

  return {
    meta: {
      referenciaId,
      entryMode:
        meta?.entryMode === "MANUAL" || meta?.entryMode === "PDF"
          ? meta.entryMode
          : base.meta.entryMode,
      touchedSteps: normalizeStepList(
        touchedStepsCandidate.length > 0
          ? touchedStepsCandidate
          : base.meta.touchedSteps,
      ),
      startedAt: asString(meta?.startedAt, base.meta.startedAt),
      lastInteractionAt: asString(
        meta?.lastInteractionAt,
        base.meta.lastInteractionAt,
      ),
    },
    programa: {
      codigo_programa: asString(
        programa?.codigo_programa,
        base.programa.codigo_programa,
      ),
      nombre_programa: asString(
        programa?.nombre_programa,
        base.programa.nombre_programa,
      ),
      version_programa: asString(
        programa?.version_programa,
        base.programa.version_programa,
      ),
    },
    wizard: {
      notesByStep,
    },
  };
}
