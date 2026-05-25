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
      <section aria-label="Zona secundaria de pendientes curriculares">
        <div data-testid="pendientes-zone">Pendientes reales</div>
      </section>
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
      screen.getByText("Revisando borrador activo del programa de formación"),
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

    expect(screen.getByText("Wizard base del programa de formación")).toBeInTheDocument();
    expect(screen.getByText("Iniciar proceso")).toBeInTheDocument();
    expect(screen.getByText("Continuar borrador")).toBeInTheDocument();
    expect(screen.getByText("Excel canonico")).toBeInTheDocument();
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
          pasoActual: "origen-documental",
          updatedAt: "2026-04-27T00:00:00Z",
          estado: "BORRADOR",
          label: "Borrador de programa Excel",
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
          pasoActual: "origen-documental",
          updatedAt: "2026-04-27T00:00:00Z",
          estado: "BORRADOR",
          label: "Borrador de programa Excel",
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
});
