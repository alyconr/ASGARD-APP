import type {
  FieldTraceStatus,
  ProgramaCompetencia,
  ProgramaExcelImportState,
  ProgramaPdfDiagnostic,
  ProgramaStoredDocument,
  ProgramaWizardPayload,
  ProgramaWizardStepDefinition,
  ProgramaWizardStepId,
  ResultadoAprendizaje,
} from "@/features/programa/types";

export const PROGRAMA_WIZARD_STEPS: ProgramaWizardStepDefinition[] = [
  {
    id: "revision-programa",
    index: 0,
    label: "Revision del programa de formación",
    shortLabel: "01",
    description:
      "Carga el PDF de evidencia y el Excel canonico, y revisa el consolidado antes de cerrar el programa de formación.",
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
      programa_excel: null,
    },
    curricular: {
      programa_formacion_id: null,
      competencias: [],
    },
  };
}

function normalizeSummary(value: unknown) {
  const summary = asRecord(value);
  return {
    programa: asNumber(summary?.programa),
    competencias: asNumber(summary?.competencias),
    resultados: asNumber(summary?.resultados),
    conocimientos: asNumber(summary?.conocimientos),
    criterios: asNumber(summary?.criterios),
  };
}

function normalizePendingSummary(value: unknown) {
  const summary = asRecord(value);
  return {
    total: asNumber(summary?.total),
    conocimientos: asNumber(summary?.conocimientos),
    criterios: asNumber(summary?.criterios),
  };
}

function normalizeProgramaExcel(
  value: unknown,
  referenciaId: string,
): ProgramaExcelImportState | null {
  const excel = asRecord(value);
  if (excel === null) {
    return null;
  }

  const document = normalizeStoredDocument(excel.documento);
  const preview = asRecord(excel.preview);
  const confirmation = asRecord(excel.confirmacion);
  const rawCompetencias = Array.isArray(preview?.competencias)
    ? preview.competencias
    : [];
  const rawErrores = Array.isArray(preview?.errores) ? preview.errores : [];
  const rawPendientes = Array.isArray(preview?.pendientes)
    ? preview.pendientes
    : [];
  const programa = asRecord(preview?.programa);
  const valid = asBoolean(preview?.valid);

  return {
    documento: document,
    preview:
      preview === null
        ? null
        : {
            referencia_id: referenciaId,
            documento: document,
            valid,
            estado_validacion: asString(
              preview.estado_validacion,
              valid ? "VALIDO" : "INVALIDO",
            ),
            resumen: normalizeSummary(preview.resumen),
            programa:
              programa === null
                ? null
                : {
                    codigo_programa: asString(programa.codigo_programa),
                    nombre_programa: asString(programa.nombre_programa),
                    version_programa:
                      typeof programa.version_programa === "string"
                        ? programa.version_programa
                        : null,
                  },
            competencias: rawCompetencias.flatMap((item) => {
              const competencia = asRecord(item);
              if (competencia === null) return [];
              return [
                {
                  competencia_id: asString(competencia.competencia_id),
                  codigo_competencia: asString(
                    competencia.codigo_competencia,
                  ),
                  nombre_competencia: asString(
                    competencia.nombre_competencia,
                  ),
                  resultados: asNumber(competencia.resultados),
                  conocimientos: asNumber(competencia.conocimientos),
                  criterios: asNumber(competencia.criterios),
                  resultados_detalle: Array.isArray(
                    competencia.resultados_detalle,
                  )
                    ? competencia.resultados_detalle.flatMap((raw) => {
                        const resultado = asRecord(raw);
                        if (resultado === null) return [];
                        return [
                          {
                            rap_id: asString(resultado.rap_id),
                            rap_numero:
                              typeof resultado.rap_numero === "string"
                                ? resultado.rap_numero
                                : null,
                            descripcion: asString(resultado.descripcion),
                          },
                        ];
                      })
                    : [],
                  conocimientos_detalle: Array.isArray(
                    competencia.conocimientos_detalle,
                  )
                    ? competencia.conocimientos_detalle.flatMap((raw) => {
                        const conocimiento = asRecord(raw);
                        if (conocimiento === null) return [];
                        return [
                          {
                            tipo_conocimiento:
                              conocimiento.tipo_conocimiento === "PROCESO"
                                ? "PROCESO"
                                : "SABER",
                            descripcion: asString(conocimiento.descripcion),
                            rap_id:
                              typeof conocimiento.rap_id === "string"
                                ? conocimiento.rap_id
                                : null,
                          },
                        ];
                      })
                    : [],
                  criterios_detalle: Array.isArray(
                    competencia.criterios_detalle,
                  )
                    ? competencia.criterios_detalle.flatMap((raw) => {
                        const criterio = asRecord(raw);
                        if (criterio === null) return [];
                        return [
                          {
                            descripcion: asString(criterio.descripcion),
                            rap_id:
                              typeof criterio.rap_id === "string"
                                ? criterio.rap_id
                                : null,
                          },
                        ];
                      })
                    : [],
                },
              ];
            }),
            pendientes_resumen: normalizePendingSummary(
              preview.pendientes_resumen,
            ),
            pendientes: rawPendientes.flatMap((item) => {
              const pending = asRecord(item);
              if (pending === null) return [];
              return [
                {
                  tipo_elemento:
                    pending.tipo_elemento === "CRITERIO"
                      ? "CRITERIO"
                      : "CONOCIMIENTO",
                  tipo_conocimiento:
                    pending.tipo_conocimiento === "SABER" ||
                    pending.tipo_conocimiento === "PROCESO"
                      ? pending.tipo_conocimiento
                      : null,
                  descripcion: asString(pending.descripcion),
                  competencia_id_origen_excel:
                    typeof pending.competencia_id_origen_excel === "string"
                      ? pending.competencia_id_origen_excel
                      : null,
                  rap_id_origen_excel:
                    typeof pending.rap_id_origen_excel === "string"
                      ? pending.rap_id_origen_excel
                      : null,
                  motivo:
                    pending.motivo === "RESULTADO_NO_IDENTIFICADO" ||
                    pending.motivo === "ASOCIACION_AMBIGUA"
                      ? pending.motivo
                      : "COMPETENCIA_NO_IDENTIFICADA",
                  hoja: asString(pending.hoja),
                  fila:
                    typeof pending.fila === "number" &&
                    Number.isFinite(pending.fila)
                      ? pending.fila
                      : null,
                },
              ];
            }),
            errores: rawErrores.flatMap((item) => {
              const issue = asRecord(item);
              if (issue === null) return [];
              return [
                {
                  hoja: asString(issue.hoja),
                  fila:
                    typeof issue.fila === "number" &&
                    Number.isFinite(issue.fila)
                      ? issue.fila
                      : null,
                  campo:
                    typeof issue.campo === "string" ? issue.campo : null,
                  mensaje: asString(issue.mensaje),
                },
              ];
            }),
          },
    confirmacion: {
      estado:
        confirmation?.estado === "IMPORTADO" ? "IMPORTADO" : "PENDIENTE",
      confirmed_at:
        typeof confirmation?.confirmed_at === "string"
          ? confirmation.confirmed_at
          : undefined,
      programa_id:
        typeof confirmation?.programa_id === "string"
          ? confirmation.programa_id
          : undefined,
      competencia_ids: Array.isArray(confirmation?.competencia_ids)
        ? confirmation.competencia_ids.filter(
            (item): item is string => typeof item === "string",
          )
        : undefined,
      resultado_ids: Array.isArray(confirmation?.resultado_ids)
        ? confirmation.resultado_ids.filter(
            (item): item is string => typeof item === "string",
          )
        : undefined,
      conocimiento_ids: Array.isArray(confirmation?.conocimiento_ids)
        ? confirmation.conocimiento_ids.filter(
            (item): item is string => typeof item === "string",
          )
        : undefined,
      criterio_ids: Array.isArray(confirmation?.criterio_ids)
        ? confirmation.criterio_ids.filter(
            (item): item is string => typeof item === "string",
          )
        : undefined,
      pendiente_ids: Array.isArray(confirmation?.pendiente_ids)
        ? confirmation.pendiente_ids.filter(
            (item): item is string => typeof item === "string",
          )
        : undefined,
      pendientes_resumen: normalizePendingSummary(
        confirmation?.pendientes_resumen,
      ),
    },
    updated_at: typeof excel.updated_at === "string" ? excel.updated_at : undefined,
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

  return {
    resumen: asString(diagnostic.resumen),
    has_text_layer: asBoolean(diagnostic.has_text_layer),
    analyzed_pages: asNumber(diagnostic.analyzed_pages),
    pages_with_text: asNumber(diagnostic.pages_with_text),
    text_character_count: asNumber(diagnostic.text_character_count),
    almacenamiento_exitoso: asBoolean(diagnostic.almacenamiento_exitoso),
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

function normalizeResultado(value: unknown): ResultadoAprendizaje | null {
  const resultado = asRecord(value);
  if (resultado === null) {
    return null;
  }

  const id = asString(resultado.id);
  const competenciaId = asString(resultado.competencia_id);
  const descripcion = asString(resultado.descripcion).trim();

  if (!id || !competenciaId || !descripcion) {
    return null;
  }

  return {
    id,
    competencia_id: competenciaId,
    codigo_resultado:
      typeof resultado.codigo_resultado === "string"
        ? resultado.codigo_resultado
        : null,
    descripcion,
    orden:
      typeof resultado.orden === "number" && Number.isFinite(resultado.orden)
        ? resultado.orden
        : null,
    estado: asString(resultado.estado, "MANUAL"),
    motivo_fallo_extraccion:
      typeof resultado.motivo_fallo_extraccion === "string"
        ? resultado.motivo_fallo_extraccion
        : null,
    fecha_creacion: asString(resultado.fecha_creacion),
    fecha_actualizacion: asString(resultado.fecha_actualizacion),
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
  const resultados = Array.isArray(competencia.resultados)
    ? competencia.resultados.flatMap((item) => {
        const normalized = normalizeResultado(item);
        return normalized === null ? [] : [normalized];
      })
    : [];

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
    resultados,
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
  const programaExcel = asRecord(documental?.programa_excel);
  const storedDocument = normalizeStoredDocument(programaPdf?.documento);
  const diagnostic = normalizeDiagnostic(programaPdf?.diagnostico);
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
        meta?.entryMode === "EXCEL" ? meta.entryMode : base.meta.entryMode,
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
              uso: "EVIDENCIA_DOCUMENTAL",
              updated_at:
                typeof uploadedAt === "string" ? uploadedAt : undefined,
            }
          : null,
      programa_excel: normalizeProgramaExcel(programaExcel, referenciaId),
    },
    curricular: {
      programa_formacion_id: asNullableString(curricular?.programa_formacion_id),
      competencias,
    },
  };
}
