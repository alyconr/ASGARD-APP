import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProgramaDocumentUpload } from "./programa-document-upload";
import { uploadProgramaPdf } from "@/features/programa/document-upload-api";
import type { ProgramaPdfUploadResponse } from "@/features/programa/types";

vi.mock("@/features/programa/document-upload-api", () => ({
  ProgramaPdfUploadError: class ProgramaPdfUploadError extends Error {
    readonly status: number;

    readonly detail: string;

    constructor(status: number, detail: string) {
      super(detail);
      this.status = status;
      this.detail = detail;
    }
  },
  uploadProgramaPdf: vi.fn(),
}));

const mockUploadProgramaPdf = vi.mocked(uploadProgramaPdf);

function buildUploadResponse(): ProgramaPdfUploadResponse {
  return {
    referencia_id: "ref-123",
    documento: {
      original_filename: "programa.pdf",
      storage_key: "programas/ref-123/documentos/programa.pdf",
      size_bytes: 1024,
      content_type: "application/pdf",
      checksum_sha256: "checksum",
      etag: "etag",
    },
    diagnostico: {
      estado_legibilidad: "LEGIBLE",
      motivo: null,
      resumen: "PDF legible",
      has_text_layer: true,
      analyzed_pages: 1,
      pages_with_text: 1,
      text_character_count: 100,
      can_attempt_extraction: false,
      requires_manual_entry: false,
    },
  };
}

describe("ProgramaDocumentUpload", () => {
  it("validates absence of file before upload", async () => {
    render(
      <ProgramaDocumentUpload
        currentResult={null}
        referenciaId="ref-123"
        onUploaded={vi.fn()}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: /cargar y diagnosticar/i }),
    );

    expect(
      await screen.findByText("Selecciona un archivo PDF antes de cargar."),
    ).toBeInTheDocument();
    expect(mockUploadProgramaPdf).not.toHaveBeenCalled();
  });

  it("uploads a valid PDF and returns the diagnosis to the wizard", async () => {
    const response = buildUploadResponse();
    mockUploadProgramaPdf.mockResolvedValueOnce(response);
    const onUploaded = vi.fn();

    render(
      <ProgramaDocumentUpload
        currentResult={null}
        referenciaId="ref-123"
        onUploaded={onUploaded}
      />,
    );

    const input = document.querySelector("input[type='file']");
    expect(input).not.toBeNull();

    fireEvent.change(input as HTMLInputElement, {
      target: {
        files: [
          new File(["%PDF-1.4"], "programa.pdf", {
            type: "application/pdf",
          }),
        ],
      },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /cargar y diagnosticar/i }),
    );

    await waitFor(() => {
      expect(onUploaded).toHaveBeenCalledWith(response);
    });
    expect(
      screen.getByText("PDF cargado y diagnosticado."),
    ).toBeInTheDocument();
  });
});
