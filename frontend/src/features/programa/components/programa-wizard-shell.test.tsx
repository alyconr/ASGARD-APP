import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProgramaWizardShell } from "./programa-wizard-shell";
import * as useProgramaWizardModule from "@/features/programa/use-programa-wizard";

vi.mock("@/features/programa/use-programa-wizard", () => ({
  useProgramaWizard: vi.fn(),
}));

vi.mock("@/features/programa/components/programa-excel-import", () => ({
  ProgramaExcelImport: () => (
    <section data-testid="programa-excel-import">Excel canonico</section>
  ),
}));

vi.mock("@/features/programa/components/programa-competencias-manager", () => ({
  ProgramaCompetenciasManager: () => (
    <section data-testid="competencias-zone">
      Estructura por competencias
    </section>
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

vi.mock("@/features/proyecto/components/proyecto-disponibilidad-panel", () => ({
  ProyectoDisponibilidadPanel: () => (
    <section data-testid="proyecto-disponibilidad-panel">Proyecto</section>
  ),
}));

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

    expect(
      screen.getByText("Wizard base del programa de formación"),
    ).toBeInTheDocument();
    expect(screen.getByText("Iniciar proceso")).toBeInTheDocument();
    expect(screen.getByText("Continuar borrador")).toBeInTheDocument();
    expect(
      screen.getByText("Matriz de Programa de formacion"),
    ).toBeInTheDocument();
  });

  it("should allow deleting draft cargues without recovering them", async () => {
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

    fireEvent.click(
      screen.getByRole("button", { name: /eliminar cargue borrador/i }),
    );

    await waitFor(() => {
      expect(forgetKnownDraft).toHaveBeenCalledWith(
        "12345678-1234-4234-9234-123456789abc",
      );
    });
    expect(recoverDraftByReference).not.toHaveBeenCalled();
  });

  it("should allow clearing the full local draft list", async () => {
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

    await waitFor(() => {
      expect(clearKnownDrafts).toHaveBeenCalledOnce();
    });
  });

  it("shows enabled program PDF upload after program import even when global document flag is false", () => {
    vi.spyOn(useProgramaWizardModule, "useProgramaWizard").mockReturnValue({
      isBootstrapping: false,
      isWizardActive: true,
      errorMessage: null,
      activeReferenceId: "12345678-1234-4234-9234-123456789abc",
      currentStepIndex: 0,
      currentStepId: "origen-documental",
      payload: {
        meta: {
          referenciaId: "12345678-1234-4234-9234-123456789abc",
          entryMode: "EXCEL",
          touchedSteps: ["origen-documental"],
        },
        programa: {
          codigo_programa: "228118",
          nombre_programa: "Analisis y Desarrollo de Software",
          version_programa: "1",
        },
        documental: {
          programa_pdf: null,
          programa_excel: {
            confirmacion: { estado: "IMPORTADO" },
            documento: {
              original_filename: "matriz.xlsx",
              storage_key: "programas/ads/excel/matriz.xlsx",
              size_bytes: 1024,
              content_type:
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              checksum_sha256: "checksum",
              etag: "etag",
            },
          },
        },
        curricular: { competencias: [] },
      },
      docState: {
        programa_excel: null,
        proyecto_excel: null,
        programa_pdf: null,
        proyecto_pdf: null,
        programa_importado: true,
        proyecto_importado: false,
        documentos_habilitados: false,
        cargue_pdf_habilitado: false,
      },
      draftStatus: "COMPLETO",
      autosave: { state: "idle", message: "" },
      lastSavedAt: null,
      disabledSteps: [],
      canMovePrevious: false,
      canMoveNext: true,
      goToStep: vi.fn(),
      resetFlow: vi.fn(),
      goToPreviousStep: vi.fn(),
      goToNextStep: vi.fn(),
      updateProgramaExcelPreview: vi.fn(),
      updateProgramaExcelImport: vi.fn(),
      updateProgramaPdfResult: vi.fn(),
      persistActiveDraftNow: vi.fn(),
      markProgramaClosed: vi.fn(),
      refreshCurriculum: vi.fn(),
    } as unknown as ReturnType<
      typeof useProgramaWizardModule.useProgramaWizard
    >);

    render(<ProgramaWizardShell />);

    const excelRegion = screen.getByTestId("programa-excel-import");
    const [pdfHeading] = screen.getAllByText(/PDF del programa/i);

    expect(
      excelRegion.compareDocumentPosition(pdfHeading) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.getAllByText(/PDF del programa/i).length).toBeGreaterThanOrEqual(1);
    expect(
      screen.getByRole("button", { name: /cargar como evidencia/i }),
    ).toBeEnabled();
  });
});
