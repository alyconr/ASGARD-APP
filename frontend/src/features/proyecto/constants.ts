import type {
  ExcelPendingSummary,
  ExcelPreviewSummary,
  ProyectoExcelPreviewState,
  ProyectoPdfUploadResult,
  ProyectoStoredDocument,
  ProyectoWizardPayload,
  ProyectoWizardStepDefinition,
  ProyectoWizardStepId,
} from "@/features/proyecto/types";

export const PROYECTO_WIZARD_STEPS: ProyectoWizardStepDefinition[] = [
  {
    id: "fuente-proyecto",
    index: 0,
    label: "Origen documental",
    shortLabel: "01",
    description:
      "PDF como evidencia y matriz Excel como fuente estructurada del proyecto formativo.",
    taskRef: "TASK-18 / TASK-19",
  },
  {
    id: "revision-proyecto",
    index: 1,
    label: "Revisión del proyecto formativo",
    shortLabel: "02",
    description:
      "Lugar del consolidado editable antes del cierre del proyecto formativo.",
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

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && !Number.isNaN(value) ? value : fallback;
}

function asBoolean(value: unknown, fallback = false): boolean {
  return typeof value === "boolean" ? value : fallback;
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
    documental: normalizeProyectoDocumental(value.documental),
    estructura: normalizeProyectoEstructura(value.estructura),
  };
}

function normalizeProyectoEstructura(
  value: unknown,
): ProyectoWizardPayload["estructura"] {
  const estructura = asRecord(value);
  if (estructura === null) {
    return { fases: [], actividades: [] };
  }

  const fases = Array.isArray(estructura.fases)
    ? estructura.fases.flatMap((item) => {
        const record = asRecord(item);
        if (record === null) return [];
        return [
          {
            fase_id: asString(record.fase_id),
            estado: asString(record.estado),
          },
        ];
      })
    : [];

  const actividades = Array.isArray(estructura.actividades)
    ? estructura.actividades.flatMap((item) => {
        const record = asRecord(item);
        if (record === null) return [];
        return [
          {
            actividad_id: asString(record.actividad_id),
            estado: asString(record.estado),
          },
        ];
      })
    : [];

  return {
    fases,
    actividades,
  };
}


function normalizeStoredDocument(
  value: unknown,
): ProyectoStoredDocument | null {
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

function normalizeProyectoDocumental(
  value: unknown,
): ProyectoWizardPayload["documental"] {
  const documental = asRecord(value);
  if (documental === null) {
    return { proyecto_pdf: null, fuente_estructurada: null };
  }

  const proyectoPdf = asRecord(documental.proyecto_pdf);
  let proyectoPdfResult: ProyectoPdfUploadResult | null = null;
  if (proyectoPdf !== null) {
    const storedDocument = normalizeStoredDocument(proyectoPdf.documento);
    if (storedDocument !== null) {
      proyectoPdfResult = {
        documento: storedDocument,
        uso: "EVIDENCIA_DOCUMENTAL",
        updated_at:
          typeof proyectoPdf.updated_at === "string"
            ? proyectoPdf.updated_at
            : undefined,
      };
    }
  }

  const fuenteEstructurada = asRecord(documental.fuente_estructurada);
  let fuenteEstructuradaResult: ProyectoExcelPreviewState | null = null;
  if (fuenteEstructurada !== null) {
    const docPayload = asRecord(fuenteEstructurada.documento);
    const storedDoc =
      docPayload !== null
        ? {
            original_filename: asString(docPayload.original_filename),
            storage_key: asString(docPayload.storage_key),
            size_bytes: asNumber(docPayload.size_bytes),
            content_type: asString(
              docPayload.content_type,
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            checksum_sha256: asString(docPayload.checksum_sha256),
            etag:
              typeof docPayload.etag === "string" ? docPayload.etag : null,
          }
        : null;

    const previewPayload = asRecord(fuenteEstructurada.preview);
    const previewData =
      previewPayload !== null
        ? {
            valid: asBoolean(previewPayload.valid),
            estado_validacion:
              (previewPayload.estado_validacion as "VALIDO" | "INVALIDO") ??
              "INVALIDO",
            resumen: normalizePreviewSummary(previewPayload.resumen),
            proyecto:
              asRecord(previewPayload.proyecto) !== null
                ? {
                    codigo_proyecto: asString(
                      (previewPayload.proyecto as Record<string, unknown>).codigo_proyecto,
                    ),
                    nombre_proyecto: asString(
                      (previewPayload.proyecto as Record<string, unknown>).nombre_proyecto,
                    ),
                    version_proyecto: asString(
                      (previewPayload.proyecto as Record<string, unknown>).version_proyecto,
                    ),
                  }
                : null,
            fases: (Array.isArray(previewPayload.fases)
              ? previewPayload.fases
              : []
            ).flatMap((item) => {
              const f = asRecord(item);
              if (f === null) return [];
              return [
                {
                  fase_id: asString(f.fase_id),
                  nombre_fase: asString(f.nombre_fase),
                  orden:
                    typeof f.orden === "number" && Number.isFinite(f.orden)
                      ? f.orden
                      : null,
                  actividades: (Array.isArray(f.actividades) ? f.actividades : []).flatMap((actItem) => {
                    const act = asRecord(actItem);
                    if (act === null) return [];
                    return [
                      {
                        actividad_id: asString(act.actividad_id),
                        descripcion: asString(act.descripcion),
                        orden:
                          typeof act.orden === "number" && Number.isFinite(act.orden)
                            ? act.orden
                            : null,
                        competencias: (Array.isArray(act.competencias) ? act.competencias : []).flatMap((compItem) => {
                          const comp = asRecord(compItem);
                          if (comp === null) return [];
                          return [
                            {
                              competencia_id: asString(comp.competencia_id),
                              codigo_competencia: asString(comp.codigo_competencia),
                              nombre_competencia: asString(comp.nombre_competencia),
                              resultados: (Array.isArray(comp.resultados) ? comp.resultados : []).flatMap((rapItem) => {
                                const rap = asRecord(rapItem);
                                if (rap === null) return [];
                                return [
                                  {
                                    rap_id: asString(rap.rap_id),
                                    rap_numero: asString(rap.rap_numero),
                                    resultado_aprendizaje: asString(rap.resultado_aprendizaje),
                                    tipo_resultado: asString(rap.tipo_resultado),
                                    orden_resultado:
                                      typeof rap.orden_resultado === "number" && Number.isFinite(rap.orden_resultado)
                                        ? rap.orden_resultado
                                        : null,
                                    pagina_origen:
                                      typeof rap.pagina_origen === "string" ? rap.pagina_origen : null,
                                    observaciones:
                                      typeof rap.observaciones === "string" ? rap.observaciones : null,
                                  }
                                ];
                              }),
                            }
                          ];
                        }),
                      }
                    ];
                  }),
                  numero_competencias: asNumber(f.numero_competencias),
                  numero_resultados: asNumber(f.numero_resultados),
                },
              ];
            }),
            pendientes_resumen: normalizePendingSummary(
              previewPayload.pendientes_resumen,
            ),
            errores: (Array.isArray(previewPayload.errores)
              ? previewPayload.errores
              : []
            ).flatMap((item) => {
              const e = asRecord(item);
              if (e === null) return [];
              return [
                {
                  hoja: asString(e.hoja),
                  fila:
                    typeof e.fila === "number" && Number.isFinite(e.fila)
                      ? e.fila
                      : null,
                  campo:
                    typeof e.campo === "string" ? e.campo : null,
                  mensaje: asString(e.mensaje),
                },
              ];
            }),
          }
        : null;

    const confirmPayload = asRecord(fuenteEstructurada.confirmacion);
    const confirmData: ProyectoExcelPreviewState["confirmacion"] = {
      estado:
        (confirmPayload?.estado as "IMPORTADO" | "PENDIENTE") ?? "PENDIENTE",
      confirmed_at:
        typeof confirmPayload?.confirmed_at === "string"
          ? confirmPayload.confirmed_at
          : undefined,
      proyecto_id:
        typeof confirmPayload?.proyecto_id === "string"
          ? confirmPayload.proyecto_id
          : undefined,
      fase_ids: Array.isArray(confirmPayload?.fase_ids)
        ? confirmPayload.fase_ids.filter(
            (item): item is string => typeof item === "string",
          )
        : undefined,
      actividad_ids: Array.isArray(confirmPayload?.actividad_ids)
        ? confirmPayload.actividad_ids.filter(
            (item): item is string => typeof item === "string",
          )
        : undefined,
      pendientes_resumen: normalizePendingSummary(
        confirmPayload?.pendientes_resumen,
      ),
    };

    fuenteEstructuradaResult = {
      documento: storedDoc,
      preview: previewData,
      confirmacion: confirmData,
      updated_at:
        typeof fuenteEstructurada.updated_at === "string"
          ? fuenteEstructurada.updated_at
          : undefined,
    };
  }

  return {
    proyecto_pdf: proyectoPdfResult,
    fuente_estructurada: fuenteEstructuradaResult,
  };
}

function normalizePreviewSummary(
  value: unknown,
): ExcelPreviewSummary {
  const s = asRecord(value);
  return {
    proyecto: asNumber(s?.proyecto),
    fases: asNumber(s?.fases),
    actividades: asNumber(s?.actividades),
    resultados_especificos: asNumber(s?.resultados_especificos),
  };
}

function normalizePendingSummary(
  value: unknown,
): ExcelPendingSummary {
  const s = asRecord(value);
  return {
    total: asNumber(s?.total),
  };
}
