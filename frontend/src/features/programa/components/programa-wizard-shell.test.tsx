import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProgramaWizardShell } from "./programa-wizard-shell";
import * as useProgramaWizardModule from "@/features/programa/use-programa-wizard";

vi.mock("@/features/programa/use-programa-wizard", () => ({
  useProgramaWizard: vi.fn(),
}));

vi.mock("@/features/programa/components/programa-competencias-manager", () => ({
  ProgramaCompetenciasManager: () => (
    <section data-testid="competencias-zone">Estructura por competencias</section>
  ),
}));

vi.mock(
  "@/features/programa/components/programa-pendientes-conciliacion",
  () => ({
    ProgramaPendientesConciliacion: () => (
      <section data-testid="pendientes-zone">Pendientes reales</section>
    ),
  }),
);

describe("ProgramaWizardShell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should show loading screen when bootstrapping", () => {
    vi.spyOn(useProgramaWizardModule, "useProgramaWizard").mockReturnValue({
      isBootstrapping: true,
      isWizardActive: false,
    } as unknown as ReturnType<
      typeof useProgramaWizardModule.useProgramaWizard
    >);

    render(<ProgramaWizardShell />);

    expect(
      screen.getByText("Revisando borrador activo del programa"),
    ).toBeInTheDocument();
  });

  it("should show the start screen when wizard is not active", () => {
    vi.spyOn(useProgramaWizardModule, "useProgramaWizard").mockReturnValue({
      isBootstrapping: false,
      isWizardActive: false,
      errorMessage: null,
      activeReferenceId: null,
      continueReferenceInput: "",
      isRecovering: false,
      knownDrafts: [],
      autosave: { state: "idle", message: "" },
      lastSavedAt: null,
      startNewFlow: vi.fn(),
      recoverDraftByReference: vi.fn(),
      updateContinueReferenceInput: vi.fn(),
    } as unknown as ReturnType<
      typeof useProgramaWizardModule.useProgramaWizard
    >);

    render(<ProgramaWizardShell />);

    expect(screen.getByText("Wizard base del programa")).toBeInTheDocument();
    expect(screen.getByText("Iniciar proceso")).toBeInTheDocument();
    expect(screen.getByText("Continuar borrador")).toBeInTheDocument();
    expect(screen.getByText("Manual")).toBeInTheDocument(); // entry modes
  });

  it("should allow removing local draft references without recovering them", () => {
    const forgetKnownDraft = vi.fn();
    const recoverDraftByReference = vi.fn();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(useProgramaWizardModule, "useProgramaWizard").mockReturnValue({
      isBootstrapping: false,
      isWizardActive: false,
      errorMessage: null,
      activeReferenceId: null,
      continueReferenceInput: "",
      isRecovering: false,
      knownDrafts: [
        {
          referenciaId: "12345678-1234-4234-9234-123456789abc",
          pasoActual: "datos-programa",
          updatedAt: "2026-04-27T00:00:00Z",
          estado: "BORRADOR",
          label: "Borrador de programa manual",
        },
      ],
      autosave: { state: "idle", message: "" },
      lastSavedAt: null,
      startNewFlow: vi.fn(),
      recoverDraftByReference,
      updateContinueReferenceInput: vi.fn(),
      forgetKnownDraft,
      clearKnownDrafts: vi.fn(),
    } as unknown as ReturnType<
      typeof useProgramaWizardModule.useProgramaWizard
    >);

    render(<ProgramaWizardShell />);

    fireEvent.click(screen.getByRole("button", { name: /quitar borrador/i }));

    expect(forgetKnownDraft).toHaveBeenCalledWith(
      "12345678-1234-4234-9234-123456789abc",
    );
    expect(recoverDraftByReference).not.toHaveBeenCalled();
  });

  it("should allow clearing the full local draft list", () => {
    const clearKnownDrafts = vi.fn();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(useProgramaWizardModule, "useProgramaWizard").mockReturnValue({
      isBootstrapping: false,
      isWizardActive: false,
      errorMessage: null,
      activeReferenceId: null,
      continueReferenceInput: "",
      isRecovering: false,
      knownDrafts: [
        {
          referenciaId: "12345678-1234-4234-9234-123456789abc",
          pasoActual: "datos-programa",
          updatedAt: "2026-04-27T00:00:00Z",
          estado: "BORRADOR",
          label: "Borrador de programa manual",
        },
      ],
      autosave: { state: "idle", message: "" },
      lastSavedAt: null,
      startNewFlow: vi.fn(),
      recoverDraftByReference: vi.fn(),
      updateContinueReferenceInput: vi.fn(),
      forgetKnownDraft: vi.fn(),
      clearKnownDrafts,
    } as unknown as ReturnType<
      typeof useProgramaWizardModule.useProgramaWizard
    >);

    render(<ProgramaWizardShell />);

    fireEvent.click(screen.getByRole("button", { name: /limpiar lista/i }));

    expect(clearKnownDrafts).toHaveBeenCalledOnce();
  });

  it("should render competencias before the secondary pending reconciliation zone in step 3", () => {
    const referenciaId = "12345678-1234-4234-9234-123456789abc";
    vi.spyOn(useProgramaWizardModule, "useProgramaWizard").mockReturnValue({
      activeReferenceId: referenciaId,
      autosave: { state: "saved", message: "Borrador sincronizado." },
      canMoveNext: true,
      canMovePrevious: true,
      continueReferenceInput: referenciaId,
      currentStepId: "estructura-curricular",
      currentStepIndex: 2,
      errorMessage: null,
      isBootstrapping: false,
      isRecovering: false,
      isWizardActive: true,
      knownDrafts: [],
      lastSavedAt: "2026-05-13T00:00:00Z",
      payload: {
        meta: {
          referenciaId,
          entryMode: "EXCEL",
          touchedSteps: [
            "datos-programa",
            "origen-documental",
            "estructura-curricular",
          ],
          startedAt: "2026-05-13T00:00:00Z",
          lastInteractionAt: "2026-05-13T00:00:00Z",
        },
        programa: {
          codigo_programa: "228118",
          nombre_programa: "Analisis y desarrollo de software",
          version_programa: "",
        },
        wizard: { notesByStep: {} },
        documental: {
          programa_pdf: null,
          programa_excel: null,
        },
        curricular: {
          programa_formacion_id: null,
          competencias: [],
        },
      },
      startNewFlow: vi.fn(),
      recoverDraftByReference: vi.fn(),
      goToNextStep: vi.fn(),
      goToPreviousStep: vi.fn(),
      goToStep: vi.fn(),
      updateProgramaBaseField: vi.fn(),
      updateStepNote: vi.fn(),
      updateProgramaPdfResult: vi.fn(),
      persistActiveDraftNow: vi.fn(),
      updateProgramaExcelPreview: vi.fn(),
      updateProgramaExcelImport: vi.fn(),
      updateProgramaCompetencias: vi.fn(),
      updateContinueReferenceInput: vi.fn(),
      forgetKnownDraft: vi.fn(),
      clearKnownDrafts: vi.fn(),
      setEntryMode: vi.fn(),
      resetFlow: vi.fn(),
    } as unknown as ReturnType<
      typeof useProgramaWizardModule.useProgramaWizard
    >);

    render(<ProgramaWizardShell />);

    const competenciasZone = screen.getByTestId("competencias-zone");
    const pendingZone = screen.getByTestId("pendientes-zone");
    const secondaryRegion = screen.getByLabelText(
      "Zona secundaria de pendientes curriculares",
    );

    expect(secondaryRegion).toContainElement(pendingZone);
    expect(
      competenciasZone.compareDocumentPosition(pendingZone) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });
});
