"use client";

import {
  startTransition,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  DraftApiError,
  type DraftResponse,
  type DraftStatus,
  type EstadoDocumentalResponse,
} from "@/features/drafts/types";
import { notify } from "@/components/feedback/notifications";
import { getDraft, saveDraft } from "@/features/drafts/api";
import { listProgramaCompetencias } from "@/features/programa/competencias-api";
import {
  eliminarCargueCompleto,
  getEstadoDocumental,
} from "@/features/proyecto/cargue-api";
import type {
  AutosaveState,
  ProgramaCierreResponse,
  ProgramaCompetenciaListResponse,
  ProgramaDraftSnapshot,
  ProgramaEntryMode,
  ProgramaExcelImportResponse,
  ProgramaExcelPreviewResponse,
  ProgramaPdfUploadResponse,
  ProgramaWizardPayload,
  ProgramaWizardStepId,
} from "@/features/programa/types";
import {
  DEFAULT_PROGRAMA_STEP_ID,
  PROGRAMA_WIZARD_STEPS,
  isProgramaWizardStepId,
  createEmptyProgramaPayload,
  normalizeProgramaPayload,
} from "@/features/programa/constants";
import {
  clearActiveProgramaDraftReference,
  getActiveProgramaDraftReference,
  setActiveProgramaDraftReference,
  listKnownProgramaDrafts,
  rememberProgramaDraft,
  forgetProgramaDraft,
  clearKnownProgramaDrafts,
  type KnownDraftSummary,
} from "@/features/drafts/storage";
interface ProgramaWizardAutosave {
  state: AutosaveState;
  message: string;
}

function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
    value,
  );
}

function buildSnapshot(
  referenciaId: string,
  pasoActual: ProgramaWizardStepId,
  payload: ProgramaWizardPayload,
  estado: DraftStatus,
): ProgramaDraftSnapshot {
  return {
    referenciaId,
    pasoActual,
    payload,
    estado,
  };
}

function serializeSnapshot(snapshot: ProgramaDraftSnapshot): string {
  return JSON.stringify(snapshot);
}

function toDraftPayloadRecord(
  payload: ProgramaWizardPayload,
): Record<string, unknown> {
  return payload as unknown as Record<string, unknown>;
}

function addTouchedStep(
  touchedSteps: ProgramaWizardStepId[],
  stepId: ProgramaWizardStepId,
): ProgramaWizardStepId[] {
  if (touchedSteps.includes(stepId)) {
    return touchedSteps;
  }

  return [...touchedSteps, stepId];
}

function buildDraftLabel(payload: ProgramaWizardPayload): string {
  const parts = [
    payload.programa.codigo_programa.trim(),
    payload.programa.nombre_programa.trim(),
  ].filter((value) => value.length > 0);

  if (parts.length > 0) {
    return parts.join(" - ");
  }

  return "Borrador de programa";
}

function buildSummaryFromDraftResponse(
  draft: DraftResponse,
  payload: ProgramaWizardPayload,
): KnownDraftSummary {
  return {
    referenciaId: draft.referencia_id,
    pasoActual: draft.paso_actual,
    updatedAt: draft.ultima_edicion,
    estado: draft.estado_borrador,
    label: buildDraftLabel(payload),
  };
}

function getStepIndex(stepId: ProgramaWizardStepId): number {
  return PROGRAMA_WIZARD_STEPS.findIndex((step) => step.id === stepId);
}

function getDraftErrorMessage(error: unknown): string {
  if (error instanceof DraftApiError) {
    if (error.status === 404) {
      return "No se encontro un borrador con ese identificador.";
    }

    return error.detail;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "No fue posible sincronizar el borrador del programa.";
}

export interface ProgramaWizardController {
  activeReferenceId: string | null;
  autosave: ProgramaWizardAutosave;
  canMoveNext: boolean;
  canMovePrevious: boolean;
  continueReferenceInput: string;
  currentStepId: ProgramaWizardStepId;
  currentStepIndex: number;
  errorMessage: string | null;
  isBootstrapping: boolean;
  isRecovering: boolean;
  isWizardActive: boolean;
  knownDrafts: KnownDraftSummary[];
  lastSavedAt: string | null;
  payload: ProgramaWizardPayload | null;
  draftStatus: DraftStatus;
  startNewFlow: (entryMode: ProgramaEntryMode) => Promise<void>;
  recoverDraftByReference: (
    referenceId: string,
    silent?: boolean,
  ) => Promise<void>;
  goToNextStep: () => void;
  goToPreviousStep: () => void;
  goToStep: (stepId: ProgramaWizardStepId) => void;
  updateStepNote: (stepId: ProgramaWizardStepId, note: string) => void;
  updateProgramaPdfResult: (result: ProgramaPdfUploadResponse) => void;
  persistActiveDraftNow: () => Promise<boolean>;
  updateProgramaExcelPreview: (result: ProgramaExcelPreviewResponse) => void;
  updateProgramaExcelImport: (result: ProgramaExcelImportResponse) => void;
  updateProgramaCompetencias: (result: ProgramaCompetenciaListResponse) => void;
  markProgramaClosed: (result: ProgramaCierreResponse) => void;
  updateContinueReferenceInput: (value: string) => void;
  forgetKnownDraft: (referenceId: string) => Promise<void>;
  clearKnownDrafts: () => void;
  resetFlow: () => void;
  refreshCurriculum: () => Promise<void>;
  disabledSteps: ProgramaWizardStepId[];
  docState: EstadoDocumentalResponse | null;
  fetchDocState: () => Promise<void>;
}

export function useProgramaWizard(): ProgramaWizardController {
  const [activeReferenceId, setActiveReferenceId] = useState<string | null>(
    null,
  );
  const [currentStepId, setCurrentStepId] = useState<ProgramaWizardStepId>(
    DEFAULT_PROGRAMA_STEP_ID,
  );
  const [payload, setPayload] = useState<ProgramaWizardPayload | null>(null);
  const [draftStatus, setDraftStatus] = useState<DraftStatus>("BORRADOR");
  const [knownDrafts, setKnownDrafts] = useState<KnownDraftSummary[]>([]);
  const [continueReferenceInput, setContinueReferenceInput] = useState("");
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);
  const [autosave, setAutosave] = useState<ProgramaWizardAutosave>({
    state: "idle",
    message: "Listo para iniciar un nuevo borrador.",
  });
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isRecovering, setIsRecovering] = useState(false);

  const [docState, setDocState] = useState<EstadoDocumentalResponse | null>(
    null,
  );
  const autoStartedFromDashboardRef = useRef(false);

  const fetchDocState = useCallback(async (): Promise<void> => {
    if (activeReferenceId === null) {
      return;
    }
    try {
      const state = await getEstadoDocumental(activeReferenceId);
      setDocState(state);
    } catch (error) {
      console.error("Error fetching document state:", error);
    }
  }, [activeReferenceId]);

  useEffect(() => {
    if (activeReferenceId !== null) {
      void fetchDocState();
    } else {
      setDocState(null);
    }
  }, [activeReferenceId, fetchDocState]);

  const lastPersistedSnapshotRef = useRef<string | null>(null);

  const snapshot = useMemo(() => {
    if (activeReferenceId === null || payload === null) {
      return null;
    }

    return buildSnapshot(
      activeReferenceId,
      currentStepId,
      payload,
      draftStatus,
    );
  }, [activeReferenceId, currentStepId, draftStatus, payload]);

  const persistSnapshot = useCallback(
    async (
      nextSnapshot: ProgramaDraftSnapshot,
      options: { force?: boolean } = {},
    ): Promise<boolean> => {
      const serialized = serializeSnapshot(nextSnapshot);
      if (!options.force && serialized === lastPersistedSnapshotRef.current) {
        return true;
      }

      setAutosave({
        state: "saving",
        message: "Guardando avance del programa...",
      });
      setErrorMessage(null);

      try {
        const draft = await saveDraft("PROGRAMA", nextSnapshot.referenciaId, {
          paso_actual: nextSnapshot.pasoActual,
          payload_json: toDraftPayloadRecord(nextSnapshot.payload),
          estado_borrador: nextSnapshot.estado,
        });

        lastPersistedSnapshotRef.current = serialized;
        setLastSavedAt(draft.ultima_edicion);
        setAutosave({
          state: "saved",
          message: "Borrador sincronizado.",
        });
        setKnownDrafts((currentDrafts) => {
          const summary = buildSummaryFromDraftResponse(
            draft,
            nextSnapshot.payload,
          );
          const nextDrafts = rememberProgramaDraft(summary);
          return nextDrafts.length > 0 ? nextDrafts : currentDrafts;
        });
        return true;
      } catch (error) {
        const errorMessage = getDraftErrorMessage(error);
        setAutosave({
          state: "error",
          message:
            "No fue posible guardar automaticamente. El flujo sigue abierto.",
        });
        setErrorMessage(errorMessage);
        notify.error("No fue posible guardar el borrador", {
          description: errorMessage,
        });
        return false;
      }
    },
    [],
  );

  const recoverDraftByReference = useCallback(
    async (referenceId: string, silent = false): Promise<void> => {
      if (!isUuid(referenceId)) {
        if (!silent) {
          const validationMessage =
            "Ingresa un referencia_id UUID valido para continuar.";

          setErrorMessage(validationMessage);
          notify.warning("Referencia de borrador invalida", {
            description: validationMessage,
          });
        }

        return;
      }

      setIsRecovering(true);
      setAutosave({
        state: "saving",
        message: "Recuperando borrador del programa...",
      });
      setErrorMessage(null);

      try {
        const draft = await getDraft("PROGRAMA", referenceId);
        const nextStepId = isProgramaWizardStepId(draft.paso_actual)
          ? draft.paso_actual
          : DEFAULT_PROGRAMA_STEP_ID;
        const nextPayload = normalizeProgramaPayload(
          draft.payload_json,
          draft.referencia_id,
        );

        startTransition(() => {
          setActiveReferenceId(draft.referencia_id);
          setCurrentStepId(nextStepId);
          setPayload(nextPayload);
          setDraftStatus(draft.estado_borrador);
          setContinueReferenceInput(draft.referencia_id);
          setLastSavedAt(draft.ultima_edicion);
          setAutosave({
            state: "saved",
            message: "Borrador recuperado y listo para continuar.",
          });
        });

        setActiveProgramaDraftReference(draft.referencia_id);
        lastPersistedSnapshotRef.current = serializeSnapshot(
          buildSnapshot(
            draft.referencia_id,
            nextStepId,
            nextPayload,
            draft.estado_borrador,
          ),
        );
        setKnownDrafts(
          rememberProgramaDraft(
            buildSummaryFromDraftResponse(draft, nextPayload),
          ),
        );
        if (!silent) {
          notify.success("Borrador recuperado", {
            description: "Puedes continuar desde el ultimo paso guardado.",
          });
        }
      } catch (error) {
        if (silent) {
          clearActiveProgramaDraftReference();
        } else {
          const errorMessage = getDraftErrorMessage(error);

          setAutosave({
            state: "error",
            message:
              "No fue posible recuperar el borrador solicitado. Puedes iniciar un nuevo flujo.",
          });
          setErrorMessage(errorMessage);
          notify.error("No fue posible recuperar el borrador", {
            description: errorMessage,
          });
        }
      } finally {
        setIsRecovering(false);
        setIsBootstrapping(false);
      }
    },
    [],
  );

  useEffect(() => {
    setKnownDrafts(listKnownProgramaDrafts());
    const activeReference = getActiveProgramaDraftReference();

    if (activeReference !== null) {
      void recoverDraftByReference(activeReference, true);
      return;
    }

    setIsBootstrapping(false);
  }, [recoverDraftByReference]);

  useEffect(() => {
    if (snapshot === null || isRecovering || isBootstrapping) {
      return;
    }

    const serialized = serializeSnapshot(snapshot);
    if (serialized === lastPersistedSnapshotRef.current) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      void persistSnapshot(snapshot);
    }, 500);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [isBootstrapping, isRecovering, persistSnapshot, snapshot]);

  const startNewFlow = useCallback(
    async (entryMode: ProgramaEntryMode): Promise<void> => {
      const nextReferenceId = crypto.randomUUID();
      const nextPayload = createEmptyProgramaPayload(nextReferenceId);
      const targetStepId = DEFAULT_PROGRAMA_STEP_ID;
      const now = new Date().toISOString();

      nextPayload.meta.entryMode = entryMode ?? "EXCEL";
      nextPayload.meta.touchedSteps = addTouchedStep(
        nextPayload.meta.touchedSteps,
        targetStepId,
      );
      nextPayload.meta.lastInteractionAt = now;

      setActiveReferenceId(nextReferenceId);
      setPayload(nextPayload);
      setDraftStatus("BORRADOR");
      setCurrentStepId(targetStepId);
      setContinueReferenceInput(nextReferenceId);
      setLastSavedAt(null);
      setErrorMessage(null);
      setActiveProgramaDraftReference(nextReferenceId);
      setKnownDrafts(
        rememberProgramaDraft({
          referenciaId: nextReferenceId,
          pasoActual: targetStepId,
          updatedAt: now,
          estado: "BORRADOR",
          label: buildDraftLabel(nextPayload),
        }),
      );

      await persistSnapshot(
        buildSnapshot(nextReferenceId, targetStepId, nextPayload, "BORRADOR"),
      );
      notify.success("Borrador iniciado", {
        description: "Se creo una referencia estable para este flujo.",
      });
    },
    [persistSnapshot],
  );

  useEffect(() => {
    if (
      autoStartedFromDashboardRef.current ||
      isBootstrapping ||
      activeReferenceId !== null ||
      typeof window === "undefined"
    ) {
      return;
    }

    const params = new URLSearchParams(window.location.search);
    if (params.get("nuevo") !== "programa") {
      return;
    }

    autoStartedFromDashboardRef.current = true;
    void startNewFlow("EXCEL");
    window.history.replaceState(null, "", window.location.pathname);
  }, [activeReferenceId, isBootstrapping, startNewFlow]);

  const updateContinueReferenceInput = useCallback((value: string): void => {
    setContinueReferenceInput(value.trim());
  }, []);

  const isRevisionStepEnabled = useMemo(() => {
    if (payload === null) {
      return false;
    }
    const hasExcelValid =
      payload.documental.programa_excel?.preview?.valid === true;
    const hasExcelImported =
      payload.documental.programa_excel?.confirmacion.estado === "IMPORTADO";
    return hasExcelValid && hasExcelImported;
  }, [payload]);

  const disabledSteps = useMemo<ProgramaWizardStepId[]>(() => {
    return isRevisionStepEnabled ? [] : ["revision-programa"];
  }, [isRevisionStepEnabled]);

  const goToStep = useCallback(
    (stepId: ProgramaWizardStepId): void => {
      if (stepId === "revision-programa" && !isRevisionStepEnabled) {
        return;
      }
      setCurrentStepId(stepId);
      setPayload((currentPayload) => {
        if (currentPayload === null) {
          return currentPayload;
        }

        return {
          ...currentPayload,
          meta: {
            ...currentPayload.meta,
            touchedSteps: addTouchedStep(
              currentPayload.meta.touchedSteps,
              stepId,
            ),
            lastInteractionAt: new Date().toISOString(),
          },
        };
      });
    },
    [isRevisionStepEnabled],
  );

  const goToNextStep = useCallback((): void => {
    const currentIndex = getStepIndex(currentStepId);
    const nextStep = PROGRAMA_WIZARD_STEPS[currentIndex + 1];
    if (nextStep !== undefined) {
      goToStep(nextStep.id);
    }
  }, [currentStepId, goToStep]);

  const goToPreviousStep = useCallback((): void => {
    const currentIndex = getStepIndex(currentStepId);
    const previousStep = PROGRAMA_WIZARD_STEPS[currentIndex - 1];
    if (previousStep !== undefined) {
      goToStep(previousStep.id);
    }
  }, [currentStepId, goToStep]);

  const updateStepNote = useCallback(
    (stepId: ProgramaWizardStepId, note: string): void => {
      setPayload((currentPayload) => {
        if (currentPayload === null) {
          return currentPayload;
        }

        return {
          ...currentPayload,
          meta: {
            ...currentPayload.meta,
            touchedSteps: addTouchedStep(
              currentPayload.meta.touchedSteps,
              stepId,
            ),
            lastInteractionAt: new Date().toISOString(),
          },
          wizard: {
            ...currentPayload.wizard,
            notesByStep: {
              ...currentPayload.wizard.notesByStep,
              [stepId]: note,
            },
          },
        };
      });
    },
    [],
  );

  const persistActiveDraftNow = useCallback(async (): Promise<boolean> => {
    if (snapshot === null) {
      return false;
    }

    return await persistSnapshot(snapshot, { force: true });
  }, [persistSnapshot, snapshot]);

  const updateProgramaPdfResult = useCallback(
    (result: ProgramaPdfUploadResponse): void => {
      setPayload((currentPayload) => {
        if (currentPayload === null) {
          return currentPayload;
        }

        return {
          ...currentPayload,
          meta: {
            ...currentPayload.meta,
            touchedSteps: addTouchedStep(
              currentPayload.meta.touchedSteps,
              "origen-documental",
            ),
            lastInteractionAt: new Date().toISOString(),
          },
          documental: {
            ...currentPayload.documental,
            programa_pdf: {
              documento: result.documento,
              diagnostico: result.diagnostico,
              uso: "EVIDENCIA_DOCUMENTAL",
              updated_at: new Date().toISOString(),
            },
          },
        };
      });
      void fetchDocState();
    },
    [fetchDocState],
  );

  const updateProgramaExcelPreview = useCallback(
    (result: ProgramaExcelPreviewResponse): void => {
      setPayload((currentPayload) => {
        if (currentPayload === null) {
          return currentPayload;
        }

        const now = new Date().toISOString();

        return {
          ...currentPayload,
          meta: {
            ...currentPayload.meta,
            touchedSteps: addTouchedStep(
              currentPayload.meta.touchedSteps,
              "origen-documental",
            ),
            lastInteractionAt: now,
          },
          documental: {
            ...currentPayload.documental,
            programa_excel: {
              documento: result.documento,
              preview: result,
              confirmacion: { estado: "PENDIENTE" },
              updated_at: now,
            },
          },
        };
      });
    },
    [],
  );

  const updateProgramaExcelImport = useCallback(
    (result: ProgramaExcelImportResponse): void => {
      setPayload((currentPayload) => {
        if (currentPayload === null) {
          return currentPayload;
        }

        const now = new Date().toISOString();
        const preview = currentPayload.documental.programa_excel?.preview;
        const programa = preview?.programa;

        return {
          ...currentPayload,
          meta: {
            ...currentPayload.meta,
            touchedSteps: addTouchedStep(
              currentPayload.meta.touchedSteps,
              "revision-programa",
            ),
            lastInteractionAt: now,
          },
          programa: {
            ...currentPayload.programa,
            codigo_programa:
              programa?.codigo_programa ??
              currentPayload.programa.codigo_programa,
            nombre_programa:
              programa?.nombre_programa ??
              currentPayload.programa.nombre_programa,
            version_programa:
              programa?.version_programa ??
              currentPayload.programa.version_programa,
          },
          curricular: {
            ...currentPayload.curricular,
            programa_formacion_id: result.programa_id,
          },
          documental: {
            ...currentPayload.documental,
            programa_excel:
              currentPayload.documental.programa_excel === null
                ? null
                : {
                    ...currentPayload.documental.programa_excel,
                    confirmacion: {
                      estado: "IMPORTADO",
                      confirmed_at: now,
                      programa_id: result.programa_id,
                      competencia_ids: result.competencia_ids,
                      resultado_ids: result.resultado_ids,
                      conocimiento_ids: result.conocimiento_ids,
                      criterio_ids: result.criterio_ids,
                      pendiente_ids: result.pendiente_ids,
                      pendientes_resumen: result.pendientes_resumen,
                    },
                    updated_at: now,
                  },
          },
        };
      });
      // Do not redirect automatically to revision-programa step so the user can upload the program PDF in step 1 immediately.
      // setCurrentStepId("revision-programa");
      void fetchDocState();
    },
    [fetchDocState],
  );

  const refreshCurriculum = useCallback(async (): Promise<void> => {
    if (activeReferenceId === null) {
      return;
    }
    try {
      const response = await listProgramaCompetencias(activeReferenceId);
      setPayload((current) => {
        if (current === null) {
          return null;
        }
        return {
          ...current,
          curricular: {
            ...current.curricular,
            competencias: response.competencias,
          },
        };
      });
    } catch (error) {
      console.error("Failed to refresh curriculum:", error);
    }
  }, [activeReferenceId]);

  useEffect(() => {
    if (activeReferenceId === null || currentStepId !== "revision-programa") {
      return;
    }

    let isCurrent = true;
    const fetchLatest = async () => {
      try {
        const response = await listProgramaCompetencias(activeReferenceId);
        if (isCurrent) {
          setPayload((current) => {
            if (current === null) {
              return null;
            }
            return {
              ...current,
              programa: {
                codigo_programa: current.programa.codigo_programa || "",
                nombre_programa: current.programa.nombre_programa || "",
                version_programa: current.programa.version_programa || "",
              },
              curricular: {
                ...current.curricular,
                programa_formacion_id:
                  response.programa_id ||
                  current.curricular.programa_formacion_id,
                competencias: response.competencias,
              },
            };
          });
        }
      } catch (error) {
        console.error("Failed to sync competencies on revision step:", error);
      }
    };

    void fetchLatest();
    return () => {
      isCurrent = false;
    };
  }, [activeReferenceId, currentStepId]);

  const updateProgramaCompetencias = useCallback(
    (result: ProgramaCompetenciaListResponse): void => {
      setPayload((currentPayload) => {
        if (currentPayload === null) {
          return currentPayload;
        }

        return {
          ...currentPayload,
          meta: {
            ...currentPayload.meta,
            touchedSteps: addTouchedStep(
              currentPayload.meta.touchedSteps,
              "revision-programa",
            ),
            lastInteractionAt: new Date().toISOString(),
          },
          curricular: {
            programa_formacion_id: result.programa_id,
            competencias: result.competencias,
          },
        };
      });
    },
    [],
  );

  const forgetKnownDraft = useCallback(async (referenceId: string): Promise<void> => {
    setErrorMessage(null);
    try {
      await eliminarCargueCompleto(referenceId);
      setKnownDrafts(forgetProgramaDraft(referenceId));
      if (activeReferenceId === referenceId) {
        clearActiveProgramaDraftReference();
      }
      notify.success("Cargue eliminado", {
        description:
          "Se borraron los datos del programa, proyecto y archivos asociados en MinIO.",
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible eliminar el cargue del programa.";
      setErrorMessage(message);
      notify.error("No fue posible eliminar el cargue", {
        description: message,
      });
    }
  }, [activeReferenceId]);

  const clearKnownDrafts = useCallback((): void => {
    setKnownDrafts(clearKnownProgramaDrafts());
    notify.info("Lista local limpiada", {
      description: "Los borradores del servidor se conservan.",
    });
  }, []);

  const resetFlow = useCallback((): void => {
    clearActiveProgramaDraftReference();
    lastPersistedSnapshotRef.current = null;
    setActiveReferenceId(null);
    setPayload(null);
    setDraftStatus("BORRADOR");
    setCurrentStepId(DEFAULT_PROGRAMA_STEP_ID);
    setLastSavedAt(null);
    setErrorMessage(null);
    setAutosave({
      state: "idle",
      message: "Listo para iniciar un nuevo borrador.",
    });
    setKnownDrafts(listKnownProgramaDrafts());
  }, []);

  const markProgramaClosed = useCallback(
    (result: ProgramaCierreResponse): void => {
      const now = new Date().toISOString();
      setDraftStatus("COMPLETO");
      setCurrentStepId("revision-programa");
      setPayload((currentPayload) => {
        if (currentPayload === null) {
          return currentPayload;
        }

        return {
          ...currentPayload,
          meta: {
            ...currentPayload.meta,
            touchedSteps: addTouchedStep(
              currentPayload.meta.touchedSteps,
              "revision-programa",
            ),
            lastInteractionAt: now,
          },
          curricular: {
            ...currentPayload.curricular,
            programa_formacion_id: result.programa_id,
          },
          documental: {
            ...currentPayload.documental,
            programa_excel:
              currentPayload.documental.programa_excel === null
                ? null
                : {
                    ...currentPayload.documental.programa_excel,
                    confirmacion: {
                      ...currentPayload.documental.programa_excel.confirmacion,
                      estado: "IMPORTADO",
                      programa_id: result.programa_id,
                    },
                  },
          },
        };
      });
      setKnownDrafts((currentDrafts) => {
        if (activeReferenceId === null || payload === null) {
          return currentDrafts;
        }
        return rememberProgramaDraft({
          referenciaId: activeReferenceId,
          pasoActual: "revision-programa",
          updatedAt: now,
          estado: "COMPLETO",
          label: buildDraftLabel(payload),
        });
      });
    },
    [activeReferenceId, payload],
  );

  const currentStepIndex = Math.max(0, getStepIndex(currentStepId));

  return {
    activeReferenceId,
    autosave,
    canMoveNext:
      currentStepIndex < PROGRAMA_WIZARD_STEPS.length - 1 &&
      (currentStepId !== "origen-documental" || isRevisionStepEnabled),
    canMovePrevious: currentStepIndex > 0,
    continueReferenceInput,
    currentStepId,
    currentStepIndex,
    errorMessage,
    isBootstrapping,
    isRecovering,
    isWizardActive: activeReferenceId !== null && payload !== null,
    knownDrafts,
    lastSavedAt,
    payload,
    draftStatus,
    startNewFlow,
    recoverDraftByReference,
    goToNextStep,
    goToPreviousStep,
    goToStep,
    updateStepNote,
    persistActiveDraftNow,
    updateProgramaPdfResult,
    updateProgramaExcelPreview,
    updateProgramaExcelImport,
    updateProgramaCompetencias,
    markProgramaClosed,
    updateContinueReferenceInput,
    forgetKnownDraft,
    clearKnownDrafts,
    resetFlow,
    refreshCurriculum,
    disabledSteps,
    docState,
    fetchDocState,
  };
}
