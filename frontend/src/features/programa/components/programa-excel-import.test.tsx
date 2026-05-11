import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProgramaExcelImport } from "./programa-excel-import";
import {
  confirmProgramaExcelImport,
  previewProgramaExcel,
} from "@/features/programa/excel-import-api";
import type {
  ProgramaExcelImportResponse,
  ProgramaExcelPreviewResponse,
} from "@/features/programa/types";

vi.mock("@/features/programa/excel-import-api", () => ({
  ProgramaExcelImportError: class ProgramaExcelImportError extends Error {
    readonly status: number;

    readonly detail: string;

    constructor(status: number, detail: string) {
      super(detail);
      this.status = status;
      this.detail = detail;
    }
  },
  confirmProgramaExcelImport: vi.fn(),
  previewProgramaExcel: vi.fn(),
}));

const mockPreviewProgramaExcel = vi.mocked(previewProgramaExcel);
const mockConfirmProgramaExcelImport = vi.mocked(confirmProgramaExcelImport);

function buildPreview(valid = true): ProgramaExcelPreviewResponse {
  return {
    referencia_id: "ref-123",
    documento: {
      original_filename: "programa.xlsx",
      storage_key: "programas/ref-123/documentos/programa.xlsx",
      size_bytes: 2048,
      content_type:
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      checksum_sha256: "checksum",
      etag: "etag",
    },
    valid,
    estado_validacion: valid ? "VALIDO" : "INVALIDO",
    resumen: {
      programa: valid ? 1 : 0,
      competencias: valid ? 1 : 0,
      resultados: valid ? 1 : 0,
      conocimientos: valid ? 2 : 0,
      criterios: valid ? 1 : 0,
    },
    programa: valid
      ? {
          codigo_programa: "228118",
          nombre_programa: "Analisis y Desarrollo de Software",
          version_programa: "1",
        }
      : null,
    competencias: valid
      ? [
          {
            competencia_id: "COMP-1",
            codigo_competencia: "220501046",
            nombre_competencia: "Desarrollar software",
            resultados: 1,
            conocimientos: 2,
            criterios: 1,
          },
        ]
      : [],
    pendientes_resumen: {
      total: 0,
      conocimientos: 0,
      criterios: 0,
    },
    pendientes: [],
    errores: valid
      ? []
      : [
          {
            hoja: "Competencias",
            fila: 1,
            campo: null,
            mensaje: "Encabezados invalidos",
          },
        ],
  };
}

function buildImport(): ProgramaExcelImportResponse {
  return {
    referencia_id: "ref-123",
    programa_id: "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
    competencia_ids: ["bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"],
    resultado_ids: ["cccccccc-cccc-4ccc-cccc-cccccccccccc"],
    conocimiento_ids: ["dddddddd-dddd-4ddd-dddd-dddddddddddd"],
    criterio_ids: ["eeeeeeee-eeee-4eee-eeee-eeeeeeeeeeee"],
    pendiente_ids: [],
    resumen: {
      programa: 1,
      competencias: 1,
      resultados: 1,
      conocimientos: 1,
      criterios: 1,
    },
    pendientes_resumen: {
      total: 0,
      conocimientos: 0,
      criterios: 0,
    },
  };
}

describe("ProgramaExcelImport", () => {
  it("validates absence of file before preview", async () => {
    render(
      <ProgramaExcelImport
        currentResult={null}
        referenciaId="ref-123"
        onImported={vi.fn()}
        onPreviewed={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /validar preview/i }));

    expect(
      await screen.findByText("Selecciona un archivo Excel .xlsx antes de validar."),
    ).toBeInTheDocument();
    expect(mockPreviewProgramaExcel).not.toHaveBeenCalled();
  });

  it("renders validation errors returned by preview", async () => {
    mockPreviewProgramaExcel.mockResolvedValueOnce(buildPreview(false));
    render(
      <ProgramaExcelImport
        currentResult={null}
        referenciaId="ref-123"
        onImported={vi.fn()}
        onPreviewed={vi.fn()}
      />,
    );

    const input = document.querySelector("input[type='file']");
    fireEvent.change(input as HTMLInputElement, {
      target: {
        files: [new File(["xlsx"], "programa.xlsx")],
      },
    });
    fireEvent.click(screen.getByRole("button", { name: /validar preview/i }));

    expect(
      await screen.findByText("El Excel no cumple el contrato canonico."),
    ).toBeInTheDocument();
  });

  it("previews a valid workbook and confirms import", async () => {
    const preview = buildPreview(true);
    const imported = buildImport();
    mockPreviewProgramaExcel.mockResolvedValueOnce(preview);
    mockConfirmProgramaExcelImport.mockResolvedValueOnce(imported);
    const onPreviewed = vi.fn();
    const onImported = vi.fn();

    const { rerender } = render(
      <ProgramaExcelImport
        currentResult={null}
        referenciaId="ref-123"
        onImported={onImported}
        onPreviewed={onPreviewed}
      />,
    );

    const input = document.querySelector("input[type='file']");
    fireEvent.change(input as HTMLInputElement, {
      target: {
        files: [new File(["xlsx"], "programa.xlsx")],
      },
    });
    fireEvent.click(screen.getByRole("button", { name: /validar preview/i }));

    await waitFor(() => {
      expect(onPreviewed).toHaveBeenCalledWith(preview);
    });

    rerender(
      <ProgramaExcelImport
        currentResult={{
          documento: preview.documento,
          preview,
          confirmacion: { estado: "PENDIENTE" },
        }}
        referenciaId="ref-123"
        onImported={onImported}
        onPreviewed={onPreviewed}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: /confirmar importacion/i }),
    );

    await waitFor(() => {
      expect(onImported).toHaveBeenCalledWith(imported);
    });
  });
});
