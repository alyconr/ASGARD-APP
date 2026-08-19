import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  mensaje: "El proyecto formativo esta habilitado porque el programa de formación esta COMPLETO.",
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
    closeProject: vi.fn(),
    forgetKnownDraft: vi.fn(),
    goToNextStep: vi.fn(),
    goToPreviousStep: vi.fn(),
    goToStep: vi.fn(),
    isBootstrapping: false,
    isClosing: false,
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
      screen.getByLabelText("Wizard base del proyecto formativo"),
    ).toBeInTheDocument();
    expect(screen.getByText("Iniciar proyecto")).toBeInTheDocument();
  });

  it("starts a new project flow from the shell", () => {
    const startNewFlow = vi.fn();
    mockInactiveController({ startNewFlow });

    render(<ProyectoWizardShell availability={availability} />);

    fireEvent.click(
      screen.getByRole("button", { name: /iniciar wizard del proyecto formativo/i }),
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

  it("deletes an existing project cargue after confirmation", async () => {
    const forgetKnownDraft = vi.fn();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mockInactiveController({
      forgetKnownDraft,
      knownDrafts: [
        {
          referenciaId: projectReferenceId,
          pasoActual: "fuente-proyecto",
          updatedAt: "2026-05-16T10:00:00.000Z",
          estado: "BORRADOR",
          label: "Borrador de proyecto",
        },
      ],
    });

    render(<ProyectoWizardShell availability={availability} />);

    fireEvent.click(
      screen.getByRole("button", { name: /eliminar cargue borrador/i }),
    );

    await waitFor(() => {
      expect(forgetKnownDraft).toHaveBeenCalledWith(projectReferenceId);
    });
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

    expect(screen.queryByText("PDF del proyecto formativo")).not.toBeInTheDocument();
    expect(screen.getByText("Matriz Excel del proyecto formativo")).toBeInTheDocument();
    expect(screen.queryByText("Slot reservado")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /siguiente/i }));

    expect(goToNextStep).toHaveBeenCalledOnce();
    expect(goToPreviousStep).not.toHaveBeenCalled();
  });

  it("renders the PDF upload component once the project matrix is imported", () => {
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
        documental: {
          proyecto_pdf: null,
          fuente_estructurada: {
            documento: null,
            preview: null,
            confirmacion: {
              estado: "IMPORTADO",
              confirmed_at: "2026-05-16T09:30:00.000Z",
              proyecto_id: "some-project-id",
            },
          },
        },
        estructura: { fases: [], actividades: [] },
      },
    });

    render(<ProyectoWizardShell availability={availability} />);

    const excelHeading = screen.getByText("Matriz Excel del proyecto formativo");
    const pdfHeading = screen.getByText("PDF del proyecto formativo");

    expect(
      excelHeading.compareDocumentPosition(pdfHeading) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.getByText("PDF del proyecto formativo")).toBeInTheDocument();
    expect(screen.getByText("Matriz Excel del proyecto formativo")).toBeInTheDocument();
  });

  it("renders the project close action when the project matrix is confirmed", () => {
    const closeProject = vi.fn();
    mockInactiveController({
      activeReferenceId: projectReferenceId,
      closeProject,
      canMoveNext: false,
      canMovePrevious: true,
      currentStepId: "revision-proyecto",
      currentStepIndex: 1,
      isWizardActive: true,
      payload: {
        meta: {
          referenciaId: projectReferenceId,
          programaReferenciaId: availability.referencia_id,
          programaId: availability.programa_id,
          touchedSteps: ["fuente-proyecto", "revision-proyecto"],
          startedAt: "2026-05-16T09:00:00.000Z",
          lastInteractionAt: "2026-05-16T09:00:00.000Z",
        },
        wizard: { notesByStep: {} },
        proyecto: {
          proyecto_formativo_id: "some-project-id",
          codigo_proyecto: "PR-1234",
          nombre_proyecto: "Proyecto Test",
          version_proyecto: "1",
        },
        documental: {
          proyecto_pdf: null,
          fuente_estructurada: {
            documento: null,
            preview: {
              valid: true,
              estado_validacion: "VALIDO",
              resumen: { proyecto: 1, fases: 2, actividades: 4, resultados_especificos: 8 },
              proyecto: { codigo_proyecto: "PR-1234", nombre_proyecto: "Proyecto Test", version_proyecto: "1" },
              fases: [],
              pendientes_resumen: { total: 0 },
              errores: [],
            },
            confirmacion: {
              estado: "IMPORTADO",
              confirmed_at: "2026-05-16T09:30:00.000Z",
              proyecto_id: "some-project-id",
            },
          },
        },
        estructura: { fases: [], actividades: [] },
      },
    });

    render(<ProyectoWizardShell availability={availability} />);

    expect(screen.getByText("Proyecto listo para cierre")).toBeInTheDocument();
    const closeButton = screen.getByRole("button", {
      name: /confirmar y cerrar proyecto/i,
    });

    fireEvent.click(closeButton);

    expect(closeProject).toHaveBeenCalledOnce();
    expect(
      screen.queryByRole("link", { name: /^Configurar Planeación$/i }),
    ).not.toBeInTheDocument();
  });

  it("renders a link to the pedagogical planning wizard when the project is complete", () => {
    mockInactiveController({
      activeReferenceId: projectReferenceId,
      canMoveNext: false,
      canMovePrevious: true,
      currentStepId: "revision-proyecto",
      currentStepIndex: 1,
      draftStatus: "COMPLETO",
      isWizardActive: true,
      payload: {
        meta: {
          referenciaId: projectReferenceId,
          programaReferenciaId: availability.referencia_id,
          programaId: availability.programa_id,
          touchedSteps: ["fuente-proyecto", "revision-proyecto"],
          startedAt: "2026-05-16T09:00:00.000Z",
          lastInteractionAt: "2026-05-16T09:00:00.000Z",
        },
        wizard: { notesByStep: {} },
        proyecto: {
          proyecto_formativo_id: "some-project-id",
          codigo_proyecto: "PR-1234",
          nombre_proyecto: "Proyecto Test",
          version_proyecto: "1",
        },
        documental: {
          proyecto_pdf: null,
          fuente_estructurada: {
            documento: null,
            preview: {
              valid: true,
              estado_validacion: "VALIDO",
              resumen: { proyecto: 1, fases: 2, actividades: 4, resultados_especificos: 8 },
              proyecto: { codigo_proyecto: "PR-1234", nombre_proyecto: "Proyecto Test", version_proyecto: "1" },
              fases: [],
              pendientes_resumen: { total: 0 },
              errores: [],
            },
            confirmacion: {
              estado: "IMPORTADO",
              confirmed_at: "2026-05-16T09:30:00.000Z",
              proyecto_id: "some-project-id",
            },
          },
        },
        estructura: { fases: [], actividades: [] },
      },
    });

    render(<ProyectoWizardShell availability={availability} />);

    const bottomLink = screen.getByRole("link", { name: /^Configurar Planeación$/i });
    expect(bottomLink).toHaveAttribute("href", `/planeacion/${availability.referencia_id}`);
  });
});
