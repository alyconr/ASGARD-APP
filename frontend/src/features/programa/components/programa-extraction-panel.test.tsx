import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProgramaExtractionPanel } from "./programa-extraction-panel";
import { extractProgramaPdf } from "@/features/programa/extraction-api";
import type { ProgramaExtractionResult } from "@/features/programa/types";

vi.mock("@/components/feedback/notifications", () => ({
  notify: {
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
  },
}));

vi.mock("@/features/programa/extraction-api", () => ({
  ProgramaExtractionError: class ProgramaExtractionError extends Error {
    readonly status: number;

    readonly detail: string;

    constructor(status: number, detail: string) {
      super(detail);
      this.status = status;
      this.detail = detail;
    }
  },
  extractProgramaPdf: vi.fn(),
}));

const mockExtractProgramaPdf = vi.mocked(extractProgramaPdf);

function buildExtractionResult(): ProgramaExtractionResult {
  const pendingBlock = {
    items: [],
    estado: "PENDIENTE" as const,
    motivo: "CAMPO_NO_ENCONTRADO" as const,
    requiere_revision: true,
  };

  return {
    referencia_id: "12345678-1234-4234-9234-123456789abc",
    estado_legibilidad: "LEGIBLE",
    resumen: "Extraccion aplicada con revision humana.",
    requiere_revision_humana: true,
    programa: {
      codigo_programa: {
        campo: "codigo_programa",
        valor: "228118",
        estado: "EXTRAIDO",
        motivo: null,
        requiere_revision: true,
        aplicado_al_borrador: true,
        valor_actual_borrador: null,
      },
      nombre_programa: {
        campo: "nombre_programa",
        valor: "Analisis y Desarrollo de Software",
        estado: "EXTRAIDO",
        motivo: null,
        requiere_revision: true,
        aplicado_al_borrador: true,
        valor_actual_borrador: null,
      },
    },
    estructura_curricular: {
      competencias: {
        items: [
          {
            valor: "Construir software de acuerdo con requisitos",
            estado: "EXTRAIDO",
            motivo: null,
            requiere_revision: true,
          },
        ],
        estado: "EXTRAIDO",
        motivo: null,
        requiere_revision: true,
      },
      resultados_aprendizaje: pendingBlock,
      conocimientos_saber: pendingBlock,
      conocimientos_proceso: pendingBlock,
      criterios_evaluacion: pendingBlock,
    },
    programa_actualizado: {
      codigo_programa: "228118",
      nombre_programa: "Analisis y Desarrollo de Software",
      version_programa: "",
    },
  };
}

describe("ProgramaExtractionPanel", () => {
  it("requires an uploaded PDF before starting extraction", async () => {
    render(
      <ProgramaExtractionPanel
        currentResult={null}
        hasPdf={false}
        legibility={null}
        referenciaId="ref-123"
        onExtracted={vi.fn()}
      />,
    );

    expect(
      await screen.findByText(/no hay pdf asociado a este borrador/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /extraer campos del programa/i }),
    ).toBeDisabled();
    expect(mockExtractProgramaPdf).not.toHaveBeenCalled();
  });

  it("returns the extraction result to the wizard", async () => {
    const result = buildExtractionResult();
    const onExtracted = vi.fn();
    mockExtractProgramaPdf.mockResolvedValueOnce(result);

    render(
      <ProgramaExtractionPanel
        currentResult={null}
        hasPdf
        legibility="LEGIBLE"
        referenciaId="12345678-1234-4234-9234-123456789abc"
        onExtracted={onExtracted}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: /extraer campos del programa/i }),
    );

    await waitFor(() => {
      expect(onExtracted).toHaveBeenCalledWith(result);
    });
    expect(mockExtractProgramaPdf).toHaveBeenCalledWith(
      "12345678-1234-4234-9234-123456789abc",
    );
  });

  it("shows the persisted extracted fields and preliminary structure", () => {
    render(
      <ProgramaExtractionPanel
        currentResult={buildExtractionResult()}
        hasPdf
        legibility="LEGIBLE"
        referenciaId="12345678-1234-4234-9234-123456789abc"
        onExtracted={vi.fn()}
      />,
    );

    expect(screen.getByText("228118")).toBeInTheDocument();
    expect(
      screen.getByText("Analisis y Desarrollo de Software"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Construir software de acuerdo con requisitos"),
    ).toBeInTheDocument();
  });
});
