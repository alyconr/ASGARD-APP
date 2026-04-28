import type {
  ExtractionFailureReason,
  FieldTraceStatus,
  ProgramaExtractedField,
  ProgramaExtractedListBlock,
  ProgramaCompetencia,
  ProgramaExtractionResult,
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
    curricular: {
      programa_formacion_id: null,
      competencias: [],
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

function asNullableString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
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

function normalizeTraceStatus(value: unknown): FieldTraceStatus | null {
  if (
    value === "EXTRAIDO" ||
    value === "MANUAL" ||
    value === "CORREGIDO" ||
    value === "PENDIENTE" ||
    value === "VALIDADO"
  ) {
    return value;
  }

  return null;
}

function normalizeFailureReason(
  value: unknown,
): ExtractionFailureReason | null {
  if (
    value === "PDF_ESCANEADO" ||
    value === "DOCUMENTO_ILEGIBLE" ||
    value === "BAJA_RESOLUCION" ||
    value === "ESTRUCTURA_NO_RECONOCIDA" ||
    value === "CAMPO_NO_ENCONTRADO" ||
    value === "CONTENIDO_AMBIGUO" ||
    value === "ARCHIVO_PROTEGIDO"
  ) {
    return value;
  }

  return null;
}

function normalizeExtractedField(
  value: unknown,
): ProgramaExtractedField | null {
  const field = asRecord(value);
  if (field === null) {
    return null;
  }

  const status = normalizeTraceStatus(field.estado);
  if (status === null) {
    return null;
  }

  return {
    campo: asString(field.campo),
    valor: typeof field.valor === "string" ? field.valor : null,
    estado: status,
    motivo: normalizeFailureReason(field.motivo),
    requiere_revision: asBoolean(field.requiere_revision, true),
    aplicado_al_borrador: asBoolean(field.aplicado_al_borrador),
    valor_actual_borrador:
      typeof field.valor_actual_borrador === "string"
        ? field.valor_actual_borrador
        : null,
  };
}

function normalizeExtractedListBlock(
  value: unknown,
): ProgramaExtractedListBlock | null {
  const block = asRecord(value);
  if (block === null) {
    return null;
  }

  const status = normalizeTraceStatus(block.estado);
  if (status === null || !Array.isArray(block.items)) {
    return null;
  }

  const items = block.items.flatMap((item) => {
    const record = asRecord(item);
    if (record === null) {
      return [];
    }
    const itemStatus = normalizeTraceStatus(record.estado);
    const value = asString(record.valor).trim();
    if (itemStatus === null || value.length === 0) {
      return [];
    }
    return [
      {
        valor: value,
        estado: itemStatus,
        motivo: normalizeFailureReason(record.motivo),
        requiere_revision: asBoolean(record.requiere_revision, true),
      },
    ];
  });

  return {
    items,
    estado: status,
    motivo: normalizeFailureReason(block.motivo),
    requiere_revision: asBoolean(block.requiere_revision, true),
    total_items: asNumber(block.total_items, items.length),
    bloque_vacio: asBoolean(block.bloque_vacio, items.length === 0),
    bloque_parcial: asBoolean(block.bloque_parcial),
  };
}

function normalizeExtraction(
  value: unknown,
  referenciaId: string,
): ProgramaExtractionResult | null {
  const extraction = asRecord(value);
  if (extraction === null) {
    return null;
  }

  const legibility = extraction.estado_legibilidad;
  if (
    legibility !== "LEGIBLE" &&
    legibility !== "PARCIALMENTE_LEGIBLE" &&
    legibility !== "NO_LEGIBLE"
  ) {
    return null;
  }

  const programa = asRecord(extraction.programa);
  const estructura = asRecord(extraction.estructura_curricular);
  const updatedProgram = asRecord(extraction.programa_actualizado);
  const codigo = normalizeExtractedField(programa?.codigo_programa);
  const nombre = normalizeExtractedField(programa?.nombre_programa);
  const competencias = normalizeExtractedListBlock(estructura?.competencias);
  const resultados = normalizeExtractedListBlock(
    estructura?.resultados_aprendizaje,
  );
  const saber = normalizeExtractedListBlock(estructura?.conocimientos_saber);
  const proceso = normalizeExtractedListBlock(
    estructura?.conocimientos_proceso,
  );
  const criterios = normalizeExtractedListBlock(
    estructura?.criterios_evaluacion,
  );

  if (
    codigo === null ||
    nombre === null ||
    competencias === null ||
    resultados === null ||
    saber === null ||
    proceso === null ||
    criterios === null
  ) {
    return null;
  }

  return {
    referencia_id: asString(extraction.referencia_id, referenciaId),
    estado_legibilidad: legibility,
    resumen: asString(extraction.resumen),
    requiere_revision_humana: asBoolean(
      extraction.requiere_revision_humana,
      true,
    ),
    programa: {
      codigo_programa: codigo,
      nombre_programa: nombre,
    },
    estructura_curricular: {
      competencias,
      resultados_aprendizaje: resultados,
      conocimientos_saber: saber,
      conocimientos_proceso: proceso,
      criterios_evaluacion: criterios,
    },
    programa_actualizado: {
      codigo_programa: asString(updatedProgram?.codigo_programa),
      nombre_programa: asString(updatedProgram?.nombre_programa),
      version_programa: asString(updatedProgram?.version_programa),
    },
    updated_at:
      typeof extraction.updated_at === "string"
        ? extraction.updated_at
        : undefined,
  };
}

function normalizeCompetencia(value: unknown): ProgramaCompetencia | null {
  const competencia = asRecord(value);
  if (competencia === null) {
    return null;
  }

  const id = asString(competencia.id);
  const programaId = asString(competencia.programa_id);
  const codigo = asString(competencia.codigo_competencia).trim();
  const nombre = asString(competencia.nombre_competencia).trim();
  const estado = competencia.estado;
  const origen = normalizeTraceStatus(competencia.origen_campo);

  if (
    !id ||
    !programaId ||
    !codigo ||
    !nombre ||
    origen === null ||
    (estado !== "BORRADOR" &&
      estado !== "EN_REVISION" &&
      estado !== "COMPLETO" &&
      estado !== "BLOQUEADO")
  ) {
    return null;
  }

  return {
    id,
    programa_id: programaId,
    codigo_competencia: codigo,
    nombre_competencia: nombre,
    orden:
      typeof competencia.orden === "number" &&
      Number.isFinite(competencia.orden)
        ? competencia.orden
        : null,
    estado,
    origen_campo: origen,
    fecha_creacion: asString(competencia.fecha_creacion),
    fecha_actualizacion: asString(competencia.fecha_actualizacion),
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
  const curricular = asRecord(value.curricular);
  const programaPdf = asRecord(documental?.programa_pdf);
  const storedDocument = normalizeStoredDocument(programaPdf?.documento);
  const diagnostic = normalizeDiagnostic(programaPdf?.diagnostico);
  const extraction = normalizeExtraction(programaPdf?.extraccion, referenciaId);
  const uploadedAt = programaPdf?.updated_at;
  const notesByStepRecord = asRecord(wizard?.notesByStep);
  const competencias = Array.isArray(curricular?.competencias)
    ? curricular.competencias.flatMap((item) => {
        const normalized = normalizeCompetencia(item);
        return normalized === null ? [] : [normalized];
      })
    : [];

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
              extraccion: extraction,
              updated_at:
                typeof uploadedAt === "string" ? uploadedAt : undefined,
            }
          : null,
    },
    curricular: {
      programa_formacion_id: asNullableString(curricular?.programa_formacion_id),
      competencias,
    },
  };
}
