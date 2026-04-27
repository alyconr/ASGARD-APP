import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { ProgramaWizardShell } from "./programa-wizard-shell";
import * as useProgramaWizardModule from "@/features/programa/use-programa-wizard";

vi.mock("@/features/programa/use-programa-wizard", () => ({
  useProgramaWizard: vi.fn(),
}));

describe("ProgramaWizardShell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should show loading screen when bootstrapping", () => {
    vi.spyOn(useProgramaWizardModule, "useProgramaWizard").mockReturnValue({
      isBootstrapping: true,
      isWizardActive: false,
    } as unknown as ReturnType<typeof useProgramaWizardModule.useProgramaWizard>);

    render(<ProgramaWizardShell />);
    
    expect(screen.getByText("Revisando borrador activo del programa")).toBeInTheDocument();
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
    } as unknown as ReturnType<typeof useProgramaWizardModule.useProgramaWizard>);

    render(<ProgramaWizardShell />);
    
    expect(screen.getByText("Wizard base del programa")).toBeInTheDocument();
    expect(screen.getByText("Iniciar proceso")).toBeInTheDocument();
    expect(screen.getByText("Continuar borrador")).toBeInTheDocument();
    expect(screen.getByText("Manual")).toBeInTheDocument(); // entry modes
  });
});
