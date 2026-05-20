import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProyectoDocumentUpload } from "./proyecto-document-upload";

const mockOnUploaded = vi.fn();

vi.mock("@/features/proyecto/document-upload-api", () => ({
  uploadProyectoPdf: vi.fn(),
  ProyectoPdfUploadError: class ProyectoPdfUploadError extends Error {
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

function createFile(name = "proyecto.pdf", size = 204800) {
  return new File([new ArrayBuffer(size)], name, { type: "application/pdf" });
}

describe("ProyectoDocumentUpload", () => {
  it("renders the uploader with evidence documentation message", () => {
    render(
      <ProyectoDocumentUpload
        currentResult={null}
        onUploaded={mockOnUploaded}
        referenciaId="test-ref"
      />,
    );

    expect(screen.getByText(/PDF del proyecto/i)).toBeInTheDocument();
    expect(screen.getAllByText(/evidencia documental/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/fuente estructurada/i).length).toBeGreaterThan(
      0,
    );
  });

  it("shows file selector button", () => {
    render(
      <ProyectoDocumentUpload
        currentResult={null}
        onUploaded={mockOnUploaded}
        referenciaId="test-ref"
      />,
    );

    expect(
      screen.getByRole("button", { name: /seleccionar pdf/i }),
    ).toBeInTheDocument();
  });

  it("shows loading state when uploading", async () => {
    const { uploadProyectoPdf } = await import("@/features/proyecto/document-upload-api");
    vi.mocked(uploadProyectoPdf).mockImplementation(() => {
      return Promise.resolve({
        referencia_id: "test-ref",
        documento: {
          original_filename: "proyecto.pdf",
          storage_key: "proyectos-formativos/test-id/documentos/obj-1.pdf",
          size_bytes: 204800,
          content_type: "application/pdf",
          checksum_sha256: "abc123",
          etag: "etag-123",
        },
      });
    });

    render(
      <ProyectoDocumentUpload
        currentResult={null}
        onUploaded={mockOnUploaded}
        referenciaId="test-ref"
      />,
    );

    const file = createFile();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: /cargar como evidencia/i }));

    expect(screen.getByText(/cargando.../i)).toBeInTheDocument();
  });

  it("shows success state and metadata after upload", async () => {
    const { uploadProyectoPdf } = await import("@/features/proyecto/document-upload-api");
    vi.mocked(uploadProyectoPdf).mockImplementation(() => {
      return Promise.resolve({
        referencia_id: "test-ref",
        documento: {
          original_filename: "proyecto.pdf",
          storage_key: "proyectos-formativos/test-id/documentos/obj-1.pdf",
          size_bytes: 204800,
          content_type: "application/pdf",
          checksum_sha256: "abc123",
          etag: "etag-123",
        },
      });
    });

    render(
      <ProyectoDocumentUpload
        currentResult={null}
        onUploaded={mockOnUploaded}
        referenciaId="test-ref"
      />,
    );

    const file = createFile();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: /cargar como evidencia/i }));

    await screen.findByText(/pdf almacenado como evidencia documental/i);

    expect(screen.getByText(/proyecto\.pdf/i)).toBeInTheDocument();
  });

  it("shows error message for invalid file type", async () => {
    render(
      <ProyectoDocumentUpload
        currentResult={null}
        onUploaded={mockOnUploaded}
        referenciaId="test-ref"
      />,
    );

    const fakeFile = new File([new ArrayBuffer(100)], "image.png", {
      type: "image/png",
    });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [fakeFile] } });

    fireEvent.click(screen.getByRole("button", { name: /cargar como evidencia/i }));

    expect(
      screen.getByText(/solo se aceptan archivos pdf/i),
    ).toBeInTheDocument();
  });

  it("shows uploaded state when currentResult is provided", () => {
    render(
      <ProyectoDocumentUpload
        currentResult={{
          documento: {
            original_filename: "existing.pdf",
            storage_key: "proyectos-formativos/old-id/documentos/obj.pdf",
            size_bytes: 1024,
            content_type: "application/pdf",
            checksum_sha256: "xyz",
            etag: null,
          },
          uso: "EVIDENCIA_DOCUMENTAL",
        }}
        onUploaded={mockOnUploaded}
        referenciaId="test-ref"
      />,
    );

    expect(screen.getByText(/existing\.pdf/i)).toBeInTheDocument();
    expect(screen.getByText(/cargado/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /seleccionar pdf/i }),
    ).toBeDisabled();
  });

  it("does not show extraction-related language", () => {
    render(
      <ProyectoDocumentUpload
        currentResult={null}
        onUploaded={mockOnUploaded}
        referenciaId="test-ref"
      />,
    );

    const content = screen.getByRole("region").textContent ?? "";
    expect(content).not.toContain("extraccion");
    expect(content).not.toContain("legible");
    expect(content).not.toContain("prellenar");
    expect(content).not.toContain("fallback");
  });
});
