import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useProgramaWizard } from "./use-programa-wizard";
import { saveDraft } from "@/features/drafts/api";
import type { DraftResponse, DraftSaveRequest } from "@/features/drafts/types";
import type {
  ProgramaExtractionResult,
  ProgramaPdfUploadResponse,
} from "@/features/programa/types";

vi.mock("@/components/feedback/notifications", () => ({
  notify: {
    error: vi.fn(),
    info: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
  },
}));

vi.mock("@/features/drafts/api", () => ({
  getDraft: vi.fn(),
  saveDraft: vi.fn(),
}));

const mockSaveDraft = vi.mocked(saveDraft);
const referenceId = "12345678-1234-4234-9234-123456789abc";

function buildDraftResponse(payload: DraftSaveRequest): DraftResponse {
  return {
    id: "draft-1",
    tipo_bloque: "PROGRAMA",
    referencia_id: referenceId,
    paso_actual: payload.paso_actual,
    payload_json: payload.payload_json,
    estado_borrador: payload.estado_borrador,
    ultima_edicion: "2026-04-28T10:00:00.000Z",
  };
}

function buildPdfUploadResponse(): ProgramaPdfUploadResponse {
  return {
    referencia_id: referenceId,
    documento: {
      original_filename: "programa.pdf",
      storage_key: "programas/ref/documentos/programa.pdf",
      size_bytes: 1024,
      content_type: "application/pdf",
      checksum_sha256: "abc123",
      etag: "etag",
    },
    diagnostico: {
      estado_legibilidad: "LEGIBLE",
      motivo: null,
      resumen: "PDF legible",
      has_text_layer: true,
      analyzed_pages: 1,
      pages_with_text: 1,
      text_character_count: 120,
      can_attempt_extraction: true,
      requires_manual_entry: false,
    },
  };
}

function buildExtractionResult(): ProgramaExtractionResult {
  const pendingBlock = {
    items: [],
    estado: "PENDIENTE" as const,
    motivo: "CAMPO_NO_ENCONTRADO" as const,
    requiere_revision: true,
  };

  return {
    referencia_id: referenceId,
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
      competencias: pendingBlock,
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

describe("useProgramaWizard TASK-07 extraction integration", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    vi.spyOn(crypto, "randomUUID").mockReturnValue(referenceId);
    mockSaveDraft.mockImplementation(async (_blockType, _draftId, payload) =>
      buildDraftResponse(payload),
    );
  });

  it("prefills base fields from extraction and keeps later manual edits", async () => {
    const { result } = renderHook(() => useProgramaWizard());

    await waitFor(() => {
      expect(result.current.isBootstrapping).toBe(false);
    });

    await act(async () => {
      await result.current.startNewFlow("PDF");
    });

    act(() => {
      result.current.updateProgramaPdfResult(buildPdfUploadResponse());
    });

    act(() => {
      result.current.updateProgramaExtractionResult(buildExtractionResult());
    });

    expect(result.current.activeReferenceId).toBe(referenceId);
    expect(result.current.payload?.programa.codigo_programa).toBe("228118");
    expect(result.current.payload?.programa.nombre_programa).toBe(
      "Analisis y Desarrollo de Software",
    );
    expect(
      result.current.payload?.documental.programa_pdf?.extraccion
        ?.requiere_revision_humana,
    ).toBe(true);

    act(() => {
      result.current.updateProgramaBaseField("codigo_programa", "MANUAL-01");
    });

    expect(result.current.activeReferenceId).toBe(referenceId);
    expect(result.current.payload?.programa.codigo_programa).toBe("MANUAL-01");
    expect(result.current.payload?.programa.nombre_programa).toBe(
      "Analisis y Desarrollo de Software",
    );
  });
});
