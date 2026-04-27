import type {
  ProgramaPdfDiagnostic,
  ProgramaStoredDocument,
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
    documental: {
      programa_pdf: null,
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

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function asBoolean(value: unknown, fallback = false): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function normalizeStoredDocument(
  value: unknown,
): ProgramaStoredDocument | null {
  const document = asRecord(value);
  if (document === null) {
    return null;
  }

  const originalFilename = asString(document.original_filename);
  const storageKey = asString(document.storage_key);
  const checksum = asString(document.checksum_sha256);
  if (!originalFilename || !storageKey || !checksum) {
    return null;
  }

  return {
    original_filename: originalFilename,
    storage_key: storageKey,
    size_bytes: asNumber(document.size_bytes),
    content_type: asString(document.content_type, "application/pdf"),
    checksum_sha256: checksum,
    etag: typeof document.etag === "string" ? document.etag : null,
  };
}

function normalizeDiagnostic(value: unknown): ProgramaPdfDiagnostic | null {
  const diagnostic = asRecord(value);
  if (diagnostic === null) {
    return null;
  }

  const status = diagnostic.estado_legibilidad;
  if (
    status !== "LEGIBLE" &&
    status !== "PARCIALMENTE_LEGIBLE" &&
    status !== "NO_LEGIBLE"
  ) {
    return null;
  }

  return {
    estado_legibilidad: status,
    motivo: typeof diagnostic.motivo === "string" ? diagnostic.motivo : null,
    resumen: asString(diagnostic.resumen),
    has_text_layer: asBoolean(diagnostic.has_text_layer),
    analyzed_pages: asNumber(diagnostic.analyzed_pages),
    pages_with_text: asNumber(diagnostic.pages_with_text),
    text_character_count: asNumber(diagnostic.text_character_count),
    can_attempt_extraction: asBoolean(diagnostic.can_attempt_extraction),
    requires_manual_entry: asBoolean(diagnostic.requires_manual_entry),
  };
}

export function normalizeProgramaPayload(
  value: Record<string, unknown>,
  referenciaId: string,
): ProgramaWizardPayload {
  const base = createEmptyProgramaPayload(referenciaId);
  const meta = asRecord(value.meta);
  const programa = asRecord(value.programa);
  const wizard = asRecord(value.wizard);
  const documental = asRecord(value.documental);
  const programaPdf = asRecord(documental?.programa_pdf);
  const storedDocument = normalizeStoredDocument(programaPdf?.documento);
  const diagnostic = normalizeDiagnostic(programaPdf?.diagnostico);
  const uploadedAt = programaPdf?.updated_at;
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
    documental: {
      programa_pdf:
        storedDocument !== null && diagnostic !== null
          ? {
              documento: storedDocument,
              diagnostico: diagnostic,
              updated_at:
                typeof uploadedAt === "string" ? uploadedAt : undefined,
            }
          : null,
    },
  };
}
