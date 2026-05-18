"use client";

import {
  startTransition,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { notify } from "@/components/feedback/notifications";
import { getDraft, saveDraft } from "@/features/drafts/api";
import type { DraftResponse, DraftStatus } from "@/features/drafts/types";
import {
  clearActiveProyectoDraftReference,
  clearKnownProyectoDrafts,
  forgetProyectoDraft,
  getActiveProyectoDraftReference,
  type KnownDraftSummary,
  listKnownProyectoDrafts,
  rememberProyectoDraft,
  setActiveProyectoDraftReference,
} from "@/features/drafts/storage";
import {
  createEmptyProyectoPayload,
  DEFAULT_PROYECTO_STEP_ID,
  isProyectoWizardStepId,
  normalizeProyectoPayload,
  PROYECTO_WIZARD_STEPS,
} from "@/features/proyecto/constants";
import type {
  ProyectoDraftSnapshot,
  ProyectoExcelPreviewState,
  ProyectoPdfUploadResult,
  ProyectoWizardPayload,
  ProyectoWizardStepId,
} from "@/features/proyecto/types";
import type { AutosaveState } from "@/features/programa/types";

interface ProyectoWizardAutosave {
  state: AutosaveState;
  message: string;
}

function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
    value,
  );
}

function addTouchedStep(
  touchedSteps: ProyectoWizardStepId[],
  stepId: ProyectoWizardStepId,
): ProyectoWizardStepId[] {
  if (touchedSteps.includes(stepId)) {
    return touchedSteps;
  }

  return [...touchedSteps, stepId];
}

function buildSnapshot(
  referenciaId: string,
  pasoActual: ProyectoWizardStepId,
  payload: ProyectoWizardPayload,
  estado: DraftStatus,
): ProyectoDraftSnapshot {
  return {
    referenciaId,
    pasoActual,
    payload,
    estado,
  };
}

function serializeSnapshot(snapshot: ProyectoDraftSnapshot): string {
  return JSON.stringify(snapshot);
}

function toDraftPayloadRecord(
  payload: ProyectoWizardPayload,
): Record<string, unknown> {
  return payload as unknown as Record<string, unknown>;
}

function getStepIndex(stepId: ProyectoWizardStepId): number {
  return PROYECTO_WIZARD_STEPS.findIndex((step) => step.id === stepId);
}

function buildDraftLabel(payload: ProyectoWizardPayload): string {
  const suffix = payload.meta.programaId?.slice(0, 8) ?? "sin-programa";
  return `Borrador de proyecto / programa ${suffix}`;
}

function buildSummaryFromDraftResponse(
  draft: DraftResponse,
  payload: ProyectoWizardPayload,
): KnownDraftSummary {
  return {
    referenciaId: draft.referencia_id,
    pasoActual: draft.paso_actual,
    updatedAt: draft.ultima_edicion,
    estado: draft.estado_borrador,
    label: buildDraftLabel(payload),
  };
}

function getDraftErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "No fue posible sincronizar el borrador del proyecto.";
}

export interface ProyectoWizardController {
  activeReferenceId: string | null;
  autosave: ProyectoWizardAutosave;
  canMoveNext: boolean;
  canMovePrevious: boolean;
  continueReferenceInput: string;
  currentStepId: ProyectoWizardStepId;
  currentStepIndex: number;
  draftStatus: DraftStatus;
  errorMessage: string | null;
  isBootstrapping: boolean;
  isRecovering: boolean;
  isWizardActive: boolean;
  knownDrafts: KnownDraftSummary[];
  lastSavedAt: string | null;
  payload: ProyectoWizardPayload | null;
  clearKnownDrafts: () => void;
  forgetKnownDraft: (referenceId: string) => void;
  goToNextStep: () => void;
  goToPreviousStep: () => void;
  goToStep: (stepId: ProyectoWizardStepId) => void;
  recoverDraftByReference: (referenceId: string, silent?: boolean) => Promise<void>;
  resetFlow: () => void;
  startNewFlow: () => Promise<void>;
  updateContinueReferenceInput: (value: string) => void;
  updateStepNote: (stepId: ProyectoWizardStepId, note: string) => void;
  updateProyectoPdfResult: (result: ProyectoPdfUploadResult) => void;
  updateProyectoExcelPreview: (result: ProyectoExcelPreviewState) => void;
  updateProyectoExcelImport: (result: ProyectoExcelPreviewState) => void;
}

export function useProyectoWizard({
  programaId,
  programaReferenciaId,
}: Readonly<{
  programaId: string | null;
  programaReferenciaId: string;
}>): ProyectoWizardController {
  const [activeReferenceId, setActiveReferenceId] = useState<string | null>(
    null,
  );
  const [currentStepId, setCurrentStepId] = useState<ProyectoWizardStepId>(
    DEFAULT_PROYECTO_STEP_ID,
  );
  const [payload, setPayload] = useState<ProyectoWizardPayload | null>(null);
  const [draftStatus, setDraftStatus] = useState<DraftStatus>("BORRADOR");
  const [knownDrafts, setKnownDrafts] = useState<KnownDraftSummary[]>([]);
  const [continueReferenceInput, setContinueReferenceInput] = useState("");
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);
  const [autosave, setAutosave] = useState<ProyectoWizardAutosave>({
    state: "idle",
    message: "Listo para iniciar el borrador del proyecto.",
  });
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isRecovering, setIsRecovering] = useState(false);

  const lastPersistedSnapshotRef = useRef<string | null>(null);

  const snapshot = useMemo(() => {
    if (activeReferenceId === null || payload === null) {
      return null;
    }

    return buildSnapshot(activeReferenceId, currentStepId, payload, draftStatus);
  }, [activeReferenceId, currentStepId, draftStatus, payload]);

  const persistSnapshot = useCallback(
    async (
      nextSnapshot: ProyectoDraftSnapshot,
      options: { force?: boolean } = {},
    ): Promise<boolean> => {
      const serialized = serializeSnapshot(nextSnapshot);
      if (!options.force && serialized === lastPersistedSnapshotRef.current) {
        return true;
      }

      setAutosave({
        state: "saving",
        message: "Guardando avance del proyecto...",
      });
      setErrorMessage(null);

      try {
        const draft = await saveDraft("PROYECTO", nextSnapshot.referenciaId, {
          paso_actual: nextSnapshot.pasoActual,
          payload_json: toDraftPayloadRecord(nextSnapshot.payload),
          estado_borrador: nextSnapshot.estado,
        });

        lastPersistedSnapshotRef.current = serialized;
        setLastSavedAt(draft.ultima_edicion);
        setAutosave({
          state: "saved",
          message: "Borrador del proyecto sincronizado.",
        });
        setKnownDrafts((currentDrafts) => {
          const summary = buildSummaryFromDraftResponse(
            draft,
            nextSnapshot.payload,
          );
          const nextDrafts = rememberProyectoDraft(summary);
          return nextDrafts.length > 0 ? nextDrafts : currentDrafts;
        });
        return true;
      } catch (error) {
        const message = getDraftErrorMessage(error);
        setAutosave({
          state: "error",
          message: "No fue posible guardar automaticamente el proyecto.",
        });
        setErrorMessage(message);
        notify.error("No fue posible guardar el borrador del proyecto", {
          description: message,
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
          notify.warning("Referencia de proyecto invalida", {
            description: validationMessage,
          });
        }
        return;
      }

      setIsRecovering(true);
      setAutosave({
        state: "saving",
        message: "Recuperando borrador del proyecto...",
      });
      setErrorMessage(null);

      try {
        const draft = await getDraft("PROYECTO", referenceId);
        const nextStepId = isProyectoWizardStepId(draft.paso_actual)
          ? draft.paso_actual
          : DEFAULT_PROYECTO_STEP_ID;
        const nextPayload = normalizeProyectoPayload(
          draft.payload_json,
          draft.referencia_id,
          programaReferenciaId,
          programaId,
        );

        if (nextPayload.meta.programaReferenciaId !== programaReferenciaId) {
          throw new Error(
            "El borrador del proyecto pertenece a otro programa.",
          );
        }

        startTransition(() => {
          setActiveReferenceId(draft.referencia_id);
          setCurrentStepId(nextStepId);
          setPayload(nextPayload);
          setDraftStatus(draft.estado_borrador);
          setContinueReferenceInput(draft.referencia_id);
          setLastSavedAt(draft.ultima_edicion);
          setAutosave({
            state: "saved",
            message: "Borrador del proyecto recuperado.",
          });
        });

        setActiveProyectoDraftReference(draft.referencia_id);
        lastPersistedSnapshotRef.current = serializeSnapshot(
          buildSnapshot(
            draft.referencia_id,
            nextStepId,
            nextPayload,
            draft.estado_borrador,
          ),
        );
        setKnownDrafts(
          rememberProyectoDraft(
            buildSummaryFromDraftResponse(draft, nextPayload),
          ),
        );
        if (!silent) {
          notify.success("Borrador del proyecto recuperado", {
            description: "Puedes continuar desde el ultimo paso guardado.",
          });
        }
      } catch (error) {
        if (silent) {
          clearActiveProyectoDraftReference();
        } else {
          const message = getDraftErrorMessage(error);
          setAutosave({
            state: "error",
            message: "No fue posible recuperar el borrador del proyecto.",
          });
          setErrorMessage(message);
          notify.error("No fue posible recuperar el borrador del proyecto", {
            description: message,
          });
        }
      } finally {
        setIsRecovering(false);
        setIsBootstrapping(false);
      }
    },
    [programaId, programaReferenciaId],
  );

  useEffect(() => {
    setKnownDrafts(listKnownProyectoDrafts());
    const activeReference = getActiveProyectoDraftReference();

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

  const startNewFlow = useCallback(async (): Promise<void> => {
    const nextReferenceId = crypto.randomUUID();
    const nextPayload = createEmptyProyectoPayload(
      nextReferenceId,
      programaReferenciaId,
      programaId,
    );
    const now = new Date().toISOString();

    setActiveReferenceId(nextReferenceId);
    setPayload(nextPayload);
    setDraftStatus("BORRADOR");
    setCurrentStepId(DEFAULT_PROYECTO_STEP_ID);
    setContinueReferenceInput(nextReferenceId);
    setLastSavedAt(null);
    setErrorMessage(null);
    setActiveProyectoDraftReference(nextReferenceId);
    setKnownDrafts(
      rememberProyectoDraft({
        referenciaId: nextReferenceId,
        pasoActual: DEFAULT_PROYECTO_STEP_ID,
        updatedAt: now,
        estado: "BORRADOR",
        label: buildDraftLabel(nextPayload),
      }),
    );

    await persistSnapshot(
      buildSnapshot(
        nextReferenceId,
        DEFAULT_PROYECTO_STEP_ID,
        nextPayload,
        "BORRADOR",
      ),
    );
    notify.success("Wizard del proyecto iniciado", {
      description: "Se creo un borrador independiente para el proyecto.",
    });
  }, [persistSnapshot, programaId, programaReferenciaId]);

  const updateContinueReferenceInput = useCallback((value: string): void => {
    setContinueReferenceInput(value.trim());
  }, []);

  const goToStep = useCallback((stepId: ProyectoWizardStepId): void => {
    setCurrentStepId(stepId);
    setPayload((currentPayload) => {
      if (currentPayload === null) {
        return currentPayload;
      }

      return {
        ...currentPayload,
        meta: {
          ...currentPayload.meta,
          touchedSteps: addTouchedStep(currentPayload.meta.touchedSteps, stepId),
          lastInteractionAt: new Date().toISOString(),
        },
      };
    });
  }, []);

  const goToNextStep = useCallback((): void => {
    const currentIndex = getStepIndex(currentStepId);
    const nextStep = PROYECTO_WIZARD_STEPS[currentIndex + 1];
    if (nextStep !== undefined) {
      goToStep(nextStep.id);
    }
  }, [currentStepId, goToStep]);

  const goToPreviousStep = useCallback((): void => {
    const currentIndex = getStepIndex(currentStepId);
    const previousStep = PROYECTO_WIZARD_STEPS[currentIndex - 1];
    if (previousStep !== undefined) {
      goToStep(previousStep.id);
    }
  }, [currentStepId, goToStep]);

  const updateStepNote = useCallback(
    (stepId: ProyectoWizardStepId, note: string): void => {
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

  const updateProyectoPdfResult = useCallback(
    (result: ProyectoPdfUploadResult): void => {
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
              "fuente-proyecto",
            ),
            lastInteractionAt: new Date().toISOString(),
          },
          documental: {
            ...currentPayload.documental,
            proyecto_pdf: result,
          },
        };
      });
    },
    [],
  );

  const updateProyectoExcelPreview = useCallback(
    (result: ProyectoExcelPreviewState): void => {
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
              "fuente-proyecto",
            ),
            lastInteractionAt: new Date().toISOString(),
          },
          documental: {
            ...currentPayload.documental,
            fuente_estructurada: result,
          },
        };
      });
    },
    [],
  );

  const updateProyectoExcelImport = useCallback(
    (result: ProyectoExcelPreviewState): void => {
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
              "fuente-proyecto",
            ),
            lastInteractionAt: new Date().toISOString(),
          },
          documental: {
            ...currentPayload.documental,
            fuente_estructurada: result,
          },
          estructura: {
            ...currentPayload.estructura,
            fases: result.confirmacion.fase_ids?.map((id) => ({
              fase_id: id,
              estado: "IMPORTADO",
            })) ?? [],
            actividades: result.confirmacion.actividad_ids?.map((id) => ({
              actividad_id: id,
              estado: "IMPORTADO",
            })) ?? [],
          },
        };
      });
    },
    [],
  );

  const forgetKnownDraft = useCallback((referenceId: string): void => {
    setKnownDrafts(forgetProyectoDraft(referenceId));
    notify.info("Referencia local retirada", {
      description: "El borrador del servidor no fue eliminado.",
    });
  }, []);

  const clearKnownDrafts = useCallback((): void => {
    setKnownDrafts(clearKnownProyectoDrafts());
    notify.info("Lista local del proyecto limpiada", {
      description: "Los borradores del servidor se conservan.",
    });
  }, []);

  const resetFlow = useCallback((): void => {
    clearActiveProyectoDraftReference();
    lastPersistedSnapshotRef.current = null;
    setActiveReferenceId(null);
    setPayload(null);
    setDraftStatus("BORRADOR");
    setCurrentStepId(DEFAULT_PROYECTO_STEP_ID);
    setLastSavedAt(null);
    setErrorMessage(null);
    setAutosave({
      state: "idle",
      message: "Listo para iniciar el borrador del proyecto.",
    });
    setKnownDrafts(listKnownProyectoDrafts());
  }, []);

  const currentStepIndex = Math.max(0, getStepIndex(currentStepId));

  return {
    activeReferenceId,
    autosave,
    canMoveNext: currentStepIndex < PROYECTO_WIZARD_STEPS.length - 1,
    canMovePrevious: currentStepIndex > 0,
    clearKnownDrafts,
    continueReferenceInput,
    currentStepId,
    currentStepIndex,
    draftStatus,
    errorMessage,
    forgetKnownDraft,
    goToNextStep,
    goToPreviousStep,
    goToStep,
    isBootstrapping,
    isRecovering,
    isWizardActive: activeReferenceId !== null && payload !== null,
    knownDrafts,
    lastSavedAt,
    payload,
    recoverDraftByReference,
    resetFlow,
    startNewFlow,
    updateContinueReferenceInput,
    updateStepNote,
    updateProyectoPdfResult,
    updateProyectoExcelPreview,
    updateProyectoExcelImport,
  };
}
