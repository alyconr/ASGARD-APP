import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProyectoExcelImport } from "./proyecto-excel-import";

const mockOnPreview = vi.fn();
const mockOnImported = vi.fn();

vi.mock("@/features/proyecto/excel-import-api", () => ({
  uploadProjectExcelPreview: vi.fn(),
  confirmProjectExcelImport: vi.fn(),
  ProyectoExcelUploadError: class ProyectoExcelUploadError extends Error {
    status: number;
    constructor(status: number, detail: string) {
      super(detail);
      this.status = status;
    }
  },
}));

vi.mock("@/components/feedback/notifications", () => ({
  notify: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

beforeEach(() => {
  vi.clearAllMocks();
});

function createFile(name = "proyecto.xlsx", size = 204800) {
  return new File([new ArrayBuffer(size)], name, {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

describe("ProyectoExcelImport", () => {
  it("renders the uploader with structured source message", () => {
    render(
      <ProyectoExcelImport
        currentResult={null}
        onPreview={mockOnPreview}
        onImported={mockOnImported}
        referenciaId="test-ref"
      />,
    );

    expect(
      screen.getByText(/matriz excel del proyecto formativo/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/fuente estructurada/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/evidencia documental/i),
    ).toBeInTheDocument();
  });

  it("shows file selector button", () => {
    render(
      <ProyectoExcelImport
        currentResult={null}
        onPreview={mockOnPreview}
        onImported={mockOnImported}
        referenciaId="test-ref"
      />,
    );

    expect(
      screen.getByRole("button", { name: /seleccionar excel/i }),
    ).toBeInTheDocument();
  });

  it("shows upload button", () => {
    render(
      <ProyectoExcelImport
        currentResult={null}
        onPreview={mockOnPreview}
        onImported={mockOnImported}
        referenciaId="test-ref"
      />,
    );

    expect(
      screen.getByRole("button", { name: /previsualizar/i }),
    ).toBeInTheDocument();
  });

  it("shows loading state when uploading", async () => {
    const { uploadProjectExcelPreview } = await import(
      "@/features/proyecto/excel-import-api"
    );
    vi.mocked(uploadProjectExcelPreview).mockImplementation(() => {
      return Promise.resolve({
        referencia_id: "test-ref",
        documento: {
          original_filename: "proyecto.xlsx",
          storage_key: "proyectos-formativos/test-id/excel/test.xlsx",
          size_bytes: 204800,
          content_type:
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          checksum_sha256: "abc123",
          etag: "etag-123",
        },
        valid: true,
        estado_validacion: "VALIDO",
        resumen: { proyecto: 1, fases: 2, actividades: 3, resultados_especificos: 4 },
        proyecto: {
          codigo_proyecto: "PR-001",
          nombre_proyecto: "Proyecto de prueba",
          version_proyecto: "1.0",
        },
        fases: [
          {
            fase_id: "F1",
            nombre_fase: "Fase 1",
            orden: 1,
            actividades: [
              {
                actividad_id: "A1",
                descripcion: "Actividad 1",
                orden: 1,
                competencias: [],
              },
            ],
            numero_competencias: 1,
            numero_resultados: 2,
          },
        ],
        pendientes_resumen: { total: 0 },
        errores: [],
      });
    });

    render(
      <ProyectoExcelImport
        currentResult={null}
        onPreview={mockOnPreview}
        onImported={mockOnImported}
        referenciaId="test-ref"
      />,
    );

    const file = createFile();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: /previsualizar/i }));

    expect(screen.getByText(/procesando.../i)).toBeInTheDocument();
  });

  it("shows preview with project data after upload", async () => {
    const { uploadProjectExcelPreview } = await import(
      "@/features/proyecto/excel-import-api"
    );
    vi.mocked(uploadProjectExcelPreview).mockImplementation(() => {
      return Promise.resolve({
        referencia_id: "test-ref",
        documento: {
          original_filename: "proyecto.xlsx",
          storage_key: "proyectos-formativos/test-id/excel/test.xlsx",
          size_bytes: 204800,
          content_type:
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          checksum_sha256: "abc123",
          etag: "etag-123",
        },
        valid: true,
        estado_validacion: "VALIDO",
        resumen: { proyecto: 1, fases: 2, actividades: 3, resultados_especificos: 4 },
        proyecto: {
          codigo_proyecto: "PR-001",
          nombre_proyecto: "Proyecto de prueba",
          version_proyecto: "1.0",
        },
        fases: [
          {
            fase_id: "F1",
            nombre_fase: "Fase 1",
            orden: 1,
            actividades: [
              {
                actividad_id: "A1",
                descripcion: "Actividad 1",
                orden: 1,
                competencias: [],
              },
            ],
            numero_competencias: 1,
            numero_resultados: 2,
          },
        ],
        pendientes_resumen: { total: 0 },
        errores: [],
      });
    });

    render(
      <ProyectoExcelImport
        currentResult={null}
        onPreview={mockOnPreview}
        onImported={mockOnImported}
        referenciaId="test-ref"
      />,
    );

    const file = createFile();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: /previsualizar/i }));

    await screen.findByText(/excel valido/i);
    await screen.findByText(/PR-001/i);
    await screen.findByText(/Proyecto de prueba/i);
    const viewButton = await screen.findByRole("button", { name: /ver fases de proyecto/i });
    act(() => {
      fireEvent.click(viewButton);
    });
    expect((await screen.findAllByText(/Fase 1/i)).length).toBeGreaterThan(0);
  });

  it("shows validation errors when workbook is invalid", async () => {
    const { uploadProjectExcelPreview } = await import(
      "@/features/proyecto/excel-import-api"
    );
    vi.mocked(uploadProjectExcelPreview).mockImplementation(() => {
      return Promise.resolve({
        referencia_id: "test-ref",
        documento: null,
        valid: false,
        estado_validacion: "INVALIDO",
        resumen: { proyecto: 0, fases: 0, actividades: 0, resultados_especificos: 0 },
        proyecto: null,
        fases: [],
        pendientes_resumen: { total: 0 },
        errores: [
          {
            hoja: "Fases",
            fila: 1,
            campo: null,
            mensaje: "Hoja obligatoria faltante",
          },
        ],
      });
    });

    render(
      <ProyectoExcelImport
        currentResult={null}
        onPreview={mockOnPreview}
        onImported={mockOnImported}
        referenciaId="test-ref"
      />,
    );

    const file = createFile();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: /previsualizar/i }));

    await waitFor(() => {
      expect(
        screen.getAllByText(/errores de validacion/i).length,
      ).toBeGreaterThan(0);
    });
  });

  it("shows confirm import button when preview is valid", async () => {
    const { uploadProjectExcelPreview } = await import(
      "@/features/proyecto/excel-import-api"
    );
    vi.mocked(uploadProjectExcelPreview).mockImplementation(() => {
      return Promise.resolve({
        referencia_id: "test-ref",
        documento: {
          original_filename: "proyecto.xlsx",
          storage_key: "proyectos-formativos/test-id/excel/test.xlsx",
          size_bytes: 204800,
          content_type:
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          checksum_sha256: "abc123",
          etag: "etag-123",
        },
        valid: true,
        estado_validacion: "VALIDO",
        resumen: { proyecto: 1, fases: 2, actividades: 3, resultados_especificos: 4 },
        proyecto: {
          codigo_proyecto: "PR-001",
          nombre_proyecto: "Proyecto de prueba",
          version_proyecto: "1.0",
        },
        fases: [
          {
            fase_id: "F1",
            nombre_fase: "Fase 1",
            orden: 1,
            actividades: [
              {
                actividad_id: "A1",
                descripcion: "Actividad 1",
                orden: 1,
                competencias: [],
              },
            ],
            numero_competencias: 1,
            numero_resultados: 2,
          },
        ],
        pendientes_resumen: { total: 0 },
        errores: [],
      });
    });

    render(
      <ProyectoExcelImport
        currentResult={null}
        onPreview={mockOnPreview}
        onImported={mockOnImported}
        referenciaId="test-ref"
      />,
    );

    const file = createFile();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: /previsualizar/i }));

    await screen.findByRole("button", { name: /^confirmar importacion$/i });
  });

  it("shows imported state after confirmation", async () => {
    const { uploadProjectExcelPreview } = await import(
      "@/features/proyecto/excel-import-api"
    );
    vi.mocked(uploadProjectExcelPreview).mockImplementation(() => {
      return Promise.resolve({
        referencia_id: "test-ref",
        documento: {
          original_filename: "proyecto.xlsx",
          storage_key: "proyectos-formativos/test-id/excel/test.xlsx",
          size_bytes: 204800,
          content_type:
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          checksum_sha256: "abc123",
          etag: "etag-123",
        },
        valid: true,
        estado_validacion: "VALIDO",
        resumen: { proyecto: 1, fases: 2, actividades: 3, resultados_especificos: 4 },
        proyecto: {
          codigo_proyecto: "PR-001",
          nombre_proyecto: "Proyecto de prueba",
          version_proyecto: "1.0",
        },
        fases: [
          {
            fase_id: "F1",
            nombre_fase: "Fase 1",
            orden: 1,
            actividades: [
              {
                actividad_id: "A1",
                descripcion: "Actividad 1",
                orden: 1,
                competencias: [],
              },
            ],
            numero_competencias: 1,
            numero_resultados: 2,
          },
        ],
        pendientes_resumen: { total: 0 },
        errores: [],
      });
    });

    const { confirmProjectExcelImport } = await import(
      "@/features/proyecto/excel-import-api"
    );
    vi.mocked(confirmProjectExcelImport).mockImplementation(() => {
      return Promise.resolve({
        referencia_id: "test-ref",
        proyecto_id: "new-proyecto-id",
        fase_ids: ["f1-id", "f2-id"],
        actividad_ids: ["a1-id", "a2-id", "a3-id"],
        resumen: { proyecto: 1, fases: 2, actividades: 3, resultados_especificos: 4 },
        pendientes_resumen: { total: 0 },
      });
    });

    render(
      <ProyectoExcelImport
        currentResult={null}
        onPreview={mockOnPreview}
        onImported={mockOnImported}
        referenciaId="test-ref"
      />,
    );

    const file = createFile();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: /previsualizar/i }));

    await screen.findByRole("button", { name: /^confirmar importacion$/i });

    fireEvent.click(screen.getByRole("button", { name: /confirmar importacion/i }));

    await waitFor(() => {
      expect(
        screen.getAllByText(/importacion completada/i).length,
      ).toBeGreaterThan(0);
    });
    await screen.findByText(/2 fases/i);
    await screen.findByText(/3 actividades/i);
  });

  it("disables selector when already imported", () => {
    render(
      <ProyectoExcelImport
        currentResult={{
          documento: {
            original_filename: "proyecto.xlsx",
            storage_key: "proyectos-formativos/old-id/excel/test.xlsx",
            size_bytes: 1024,
            content_type:
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            checksum_sha256: "xyz",
            etag: null,
          },
          preview: null,
          confirmacion: {
            estado: "IMPORTADO",
            confirmed_at: "2026-05-18T00:00:00Z",
            proyecto_id: "new-proyecto-id",
            fase_ids: ["f1-id"],
            actividad_ids: ["a1-id"],
            pendientes_resumen: { total: 0 },
          },
        }}
        onPreview={mockOnPreview}
        onImported={mockOnImported}
        referenciaId="test-ref"
      />,
    );

    expect(
      screen.getByRole("button", { name: /seleccionar excel/i }),
    ).toBeDisabled();
  });

  it("does not show extraction-related language", () => {
    render(
      <ProyectoExcelImport
        currentResult={null}
        onPreview={mockOnPreview}
        onImported={mockOnImported}
        referenciaId="test-ref"
      />,
    );

    const content = screen.getByRole("region").textContent ?? "";
    expect(content).not.toContain("extraccion");
    expect(content).not.toContain("legible");
    expect(content).not.toContain("prellenar");
    expect(content).not.toContain("fallback");
    expect(content).not.toContain("carril manual");
  });
});
