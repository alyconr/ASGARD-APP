"use client";

import {
  startTransition,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { DraftApiError, type DraftResponse } from "@/features/drafts/types";
import { getDraft, saveDraft } from "@/features/drafts/api";
import {
  clearActiveProgramaDraftReference,
  getActiveProgramaDraftReference,
  listKnownProgramaDrafts,
  rememberProgramaDraft,
  setActiveProgramaDraftReference,
  type KnownDraftSummary,
} from "@/features/drafts/storage";
import {
  createEmptyProgramaPayload,
  DEFAULT_PROGRAMA_STEP_ID,
  isProgramaWizardStepId,
  normalizeProgramaPayload,
  PROGRAMA_WIZARD_STEPS,
} from "@/features/programa/constants";
import type {
  AutosaveState,
  ProgramaDraftSnapshot,
  ProgramaEntryMode,
  ProgramaPdfUploadResponse,
  ProgramaWizardPayload,
  ProgramaWizardStepId,
} from "@/features/programa/types";
import {
  sanitizeProgramaFieldValue,
  type ProgramaBaseField,
} from "@/features/programa/validation";

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
): ProgramaDraftSnapshot {
  return {
    referenciaId,
    pasoActual,
    payload,
    estado: "BORRADOR",
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

  if (payload.meta.entryMode === "PDF") {
    return "Borrador de programa desde PDF";
  }

  if (payload.meta.entryMode === "MANUAL") {
    return "Borrador de programa manual";
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
  startNewFlow: (entryMode: Exclude<ProgramaEntryMode, null>) => Promise<void>;
  recoverDraftByReference: (
    referenceId: string,
    silent?: boolean,
  ) => Promise<void>;
  goToNextStep: () => void;
  goToPreviousStep: () => void;
  goToStep: (stepId: ProgramaWizardStepId) => void;
  updateProgramaBaseField: (field: ProgramaBaseField, value: string) => void;
  updateStepNote: (stepId: ProgramaWizardStepId, note: string) => void;
  updateProgramaPdfResult: (result: ProgramaPdfUploadResponse) => void;
  updateContinueReferenceInput: (value: string) => void;
  setEntryMode: (entryMode: Exclude<ProgramaEntryMode, null>) => void;
  resetFlow: () => void;
}

export function useProgramaWizard(): ProgramaWizardController {
  const [activeReferenceId, setActiveReferenceId] = useState<string | null>(
    null,
  );
  const [currentStepId, setCurrentStepId] = useState<ProgramaWizardStepId>(
    DEFAULT_PROGRAMA_STEP_ID,
  );
  const [payload, setPayload] = useState<ProgramaWizardPayload | null>(null);
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

  const lastPersistedSnapshotRef = useRef<string | null>(null);

  const snapshot = useMemo(() => {
    if (activeReferenceId === null || payload === null) {
      return null;
    }

    return buildSnapshot(activeReferenceId, currentStepId, payload);
  }, [activeReferenceId, currentStepId, payload]);

  const persistSnapshot = useCallback(
    async (nextSnapshot: ProgramaDraftSnapshot): Promise<void> => {
      const serialized = serializeSnapshot(nextSnapshot);
      if (serialized === lastPersistedSnapshotRef.current) {
        return;
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
      } catch (error) {
        setAutosave({
          state: "error",
          message:
            "No fue posible guardar automaticamente. El flujo sigue abierto.",
        });
        setErrorMessage(getDraftErrorMessage(error));
      }
    },
    [],
  );

  const recoverDraftByReference = useCallback(
    async (referenceId: string, silent = false): Promise<void> => {
      if (!isUuid(referenceId)) {
        if (!silent) {
          setErrorMessage(
            "Ingresa un referencia_id UUID valido para continuar.",
          );
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
          setContinueReferenceInput(draft.referencia_id);
          setLastSavedAt(draft.ultima_edicion);
          setAutosave({
            state: "saved",
            message: "Borrador recuperado y listo para continuar.",
          });
        });

        setActiveProgramaDraftReference(draft.referencia_id);
        lastPersistedSnapshotRef.current = serializeSnapshot(
          buildSnapshot(draft.referencia_id, nextStepId, nextPayload),
        );
        setKnownDrafts(
          rememberProgramaDraft(
            buildSummaryFromDraftResponse(draft, nextPayload),
          ),
        );
      } catch (error) {
        if (silent) {
          clearActiveProgramaDraftReference();
        } else {
          setAutosave({
            state: "error",
            message:
              "No fue posible recuperar el borrador solicitado. Puedes iniciar un nuevo flujo.",
          });
          setErrorMessage(getDraftErrorMessage(error));
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
    async (entryMode: Exclude<ProgramaEntryMode, null>): Promise<void> => {
      const nextReferenceId = crypto.randomUUID();
      const nextPayload = createEmptyProgramaPayload(nextReferenceId);
      const targetStepId = DEFAULT_PROGRAMA_STEP_ID;
      const now = new Date().toISOString();

      nextPayload.meta.entryMode = entryMode;
      nextPayload.meta.touchedSteps = addTouchedStep(
        nextPayload.meta.touchedSteps,
        targetStepId,
      );
      nextPayload.meta.lastInteractionAt = now;

      setActiveReferenceId(nextReferenceId);
      setPayload(nextPayload);
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
        buildSnapshot(nextReferenceId, targetStepId, nextPayload),
      );
    },
    [persistSnapshot],
  );

  const updateContinueReferenceInput = useCallback((value: string): void => {
    setContinueReferenceInput(value.trim());
  }, []);

  const goToStep = useCallback((stepId: ProgramaWizardStepId): void => {
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
  }, []);

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

  const updateProgramaBaseField = useCallback(
    (field: ProgramaBaseField, value: string): void => {
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
              "datos-programa",
            ),
            lastInteractionAt: new Date().toISOString(),
          },
          programa: {
            ...currentPayload.programa,
            [field]: sanitizeProgramaFieldValue(value),
          },
        };
      });
    },
    [],
  );

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
            entryMode: "PDF",
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
              updated_at: new Date().toISOString(),
            },
          },
        };
      });
    },
    [],
  );

  const setEntryMode = useCallback(
    (entryMode: Exclude<ProgramaEntryMode, null>): void => {
      setPayload((currentPayload) => {
        if (currentPayload === null) {
          return currentPayload;
        }

        return {
          ...currentPayload,
          meta: {
            ...currentPayload.meta,
            entryMode,
            touchedSteps: addTouchedStep(
              currentPayload.meta.touchedSteps,
              currentStepId,
            ),
            lastInteractionAt: new Date().toISOString(),
          },
        };
      });
    },
    [currentStepId],
  );

  const resetFlow = useCallback((): void => {
    clearActiveProgramaDraftReference();
    lastPersistedSnapshotRef.current = null;
    setActiveReferenceId(null);
    setPayload(null);
    setCurrentStepId(DEFAULT_PROGRAMA_STEP_ID);
    setLastSavedAt(null);
    setErrorMessage(null);
    setAutosave({
      state: "idle",
      message: "Listo para iniciar un nuevo borrador.",
    });
    setKnownDrafts(listKnownProgramaDrafts());
  }, []);

  const currentStepIndex = Math.max(0, getStepIndex(currentStepId));

  return {
    activeReferenceId,
    autosave,
    canMoveNext: currentStepIndex < PROGRAMA_WIZARD_STEPS.length - 1,
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
    startNewFlow,
    recoverDraftByReference,
    goToNextStep,
    goToPreviousStep,
    goToStep,
    updateProgramaBaseField,
    updateStepNote,
    updateProgramaPdfResult,
    updateContinueReferenceInput,
    setEntryMode,
    resetFlow,
  };
}
