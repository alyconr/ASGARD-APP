import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProyectoWizardShell } from "./proyecto-wizard-shell";
import * as useProyectoWizardModule from "@/features/proyecto/use-proyecto-wizard";
import type { ProyectoDisponibilidadResponse } from "@/features/proyecto/types";

vi.mock("@/features/proyecto/use-proyecto-wizard", () => ({
  useProyectoWizard: vi.fn(),
}));

const availability: ProyectoDisponibilidadResponse = {
  referencia_id: "22222222-2222-4222-9222-222222222222",
  programa_id: "33333333-3333-4333-9333-333333333333",
  estado_programa: "COMPLETO",
  programa_completo: true,
  proyecto_bloqueado: false,
  estado_proyecto: "BORRADOR",
  motivo: null,
  mensaje: "El proyecto formativo esta habilitado porque el programa esta COMPLETO.",
  accion_sugerida: "iniciar_proyecto",
};

const projectReferenceId = "11111111-1111-4111-9111-111111111111";

function mockInactiveController(overrides = {}) {
  vi.spyOn(useProyectoWizardModule, "useProyectoWizard").mockReturnValue({
    activeReferenceId: null,
    autosave: { state: "idle", message: "Listo" },
    canMoveNext: false,
    canMovePrevious: false,
    clearKnownDrafts: vi.fn(),
    continueReferenceInput: "",
    currentStepId: "fuente-proyecto",
    currentStepIndex: 0,
    draftStatus: "BORRADOR",
    errorMessage: null,
    forgetKnownDraft: vi.fn(),
    goToNextStep: vi.fn(),
    goToPreviousStep: vi.fn(),
    goToStep: vi.fn(),
    isBootstrapping: false,
    isRecovering: false,
    isWizardActive: false,
    knownDrafts: [],
    lastSavedAt: null,
    payload: null,
    recoverDraftByReference: vi.fn(),
    resetFlow: vi.fn(),
    startNewFlow: vi.fn(),
    updateContinueReferenceInput: vi.fn(),
    updateStepNote: vi.fn(),
    ...overrides,
  } as unknown as ReturnType<typeof useProyectoWizardModule.useProyectoWizard>);
}

describe("ProyectoWizardShell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the base project wizard when enabled", () => {
    mockInactiveController();

    render(<ProyectoWizardShell availability={availability} />);

    expect(
      screen.getByLabelText("Wizard base del proyecto"),
    ).toBeInTheDocument();
    expect(screen.getByText("Iniciar proyecto")).toBeInTheDocument();
  });

  it("starts a new project flow from the shell", () => {
    const startNewFlow = vi.fn();
    mockInactiveController({ startNewFlow });

    render(<ProyectoWizardShell availability={availability} />);

    fireEvent.click(
      screen.getByRole("button", { name: /iniciar wizard del proyecto/i }),
    );

    expect(startNewFlow).toHaveBeenCalledOnce();
  });

  it("continues an existing project draft by reference", () => {
    const recoverDraftByReference = vi.fn();
    const updateContinueReferenceInput = vi.fn();
    mockInactiveController({
      continueReferenceInput: projectReferenceId,
      recoverDraftByReference,
      updateContinueReferenceInput,
    });

    render(<ProyectoWizardShell availability={availability} />);

    const nextInputValue = "44444444-4444-4444-9444-444444444444";
    fireEvent.change(screen.getByPlaceholderText("UUID del borrador"), {
      target: { value: nextInputValue },
    });
    fireEvent.click(screen.getByRole("button", { name: /recuperar/i }));

    expect(recoverDraftByReference).toHaveBeenCalledWith(projectReferenceId);
    expect(updateContinueReferenceInput).toHaveBeenCalledWith(nextInputValue);
  });

  it("starts the enabled project wizard in the document source step", () => {
    const goToNextStep = vi.fn();
    const goToPreviousStep = vi.fn();
    mockInactiveController({
      activeReferenceId: projectReferenceId,
      canMoveNext: true,
      canMovePrevious: false,
      goToNextStep,
      goToPreviousStep,
      isWizardActive: true,
      lastSavedAt: "2026-05-16T10:00:00.000Z",
      payload: {
        meta: {
          referenciaId: projectReferenceId,
          programaReferenciaId: availability.referencia_id,
          programaId: availability.programa_id,
          touchedSteps: ["fuente-proyecto"],
          startedAt: "2026-05-16T09:00:00.000Z",
          lastInteractionAt: "2026-05-16T09:00:00.000Z",
        },
        wizard: { notesByStep: {} },
        proyecto: {
          proyecto_formativo_id: null,
          codigo_proyecto: "",
          nombre_proyecto: "",
          version_proyecto: "",
        },
        documental: { proyecto_pdf: null, fuente_estructurada: null },
        estructura: { fases: [], actividades: [] },
      },
    });

    render(<ProyectoWizardShell availability={availability} />);

    expect(screen.getByText("PDF del proyecto")).toBeInTheDocument();
    expect(screen.getByText("Matriz Excel del proyecto")).toBeInTheDocument();
    expect(screen.queryByText("Slot reservado")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /siguiente/i }));

    expect(goToNextStep).toHaveBeenCalledOnce();
    expect(goToPreviousStep).not.toHaveBeenCalled();
  });
});
