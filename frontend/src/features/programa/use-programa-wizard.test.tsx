import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useProgramaWizard } from "./use-programa-wizard";
import { saveDraft } from "@/features/drafts/api";
import type { DraftResponse, DraftSaveRequest } from "@/features/drafts/types";
import type {
  ProgramaExcelImportResponse,
  ProgramaExcelPreviewResponse,
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
      can_attempt_extraction: false,
      requires_manual_entry: false,
      almacenamiento_exitoso: true,
    },
  };
}

function buildExcelPreview(): ProgramaExcelPreviewResponse {
  return {
    referencia_id: referenceId,
    documento: {
      original_filename: "programa.xlsx",
      storage_key: "programas/ref/documentos/programa.xlsx",
      size_bytes: 2048,
      content_type:
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      checksum_sha256: "def456",
      etag: "etag-xlsx",
    },
    valid: true,
    estado_validacion: "VALIDO",
    resumen: {
      programa: 1,
      competencias: 1,
      resultados: 1,
      conocimientos: 2,
      criterios: 1,
    },
    programa: {
      codigo_programa: "228118",
      nombre_programa: "Analisis y Desarrollo de Software",
      version_programa: "1",
    },
    competencias: [
      {
        competencia_id: "COMP-1",
        codigo_competencia: "220501046",
        nombre_competencia: "Desarrollar software",
        resultados: 1,
        conocimientos: 2,
        criterios: 1,
        resultados_detalle: [
          {
            rap_id: "RAP-1",
            rap_numero: "1",
            descripcion: "Construye componentes",
          },
        ],
        conocimientos_detalle: [
          {
            tipo_conocimiento: "SABER",
            descripcion: "Arquitectura",
            rap_id: null,
          },
        ],
        criterios_detalle: [
          {
            descripcion: "Verifica componentes",
            rap_id: null,
          },
        ],
      },
    ],
    pendientes_resumen: {
      total: 0,
      conocimientos: 0,
      criterios: 0,
    },
    pendientes: [],
    errores: [],
  };
}

function buildExcelImport(): ProgramaExcelImportResponse {
  return {
    referencia_id: referenceId,
    programa_id: "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
    competencia_ids: ["bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"],
    resultado_ids: ["cccccccc-cccc-4ccc-cccc-cccccccccccc"],
    conocimiento_ids: [
      "dddddddd-dddd-4ddd-dddd-dddddddddddd",
      "eeeeeeee-eeee-4eee-eeee-eeeeeeeeeeee",
    ],
    criterio_ids: ["ffffffff-ffff-4fff-ffff-ffffffffffff"],
    pendiente_ids: [],
    resumen: {
      programa: 1,
      competencias: 1,
      resultados: 1,
      conocimientos: 2,
      criterios: 1,
    },
    pendientes_resumen: {
      total: 0,
      conocimientos: 0,
      criterios: 0,
    },
  };
}

describe("useProgramaWizard TASK-08.5 Excel integration", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    vi.spyOn(crypto, "randomUUID").mockReturnValue(referenceId);
    mockSaveDraft.mockImplementation(async (_blockType, _draftId, payload) =>
      buildDraftResponse(payload),
    );
  });

  it("keeps PDF as evidence and stores Excel preview/import on the same reference", async () => {
    const { result } = renderHook(() => useProgramaWizard());

    await waitFor(() => {
      expect(result.current.isBootstrapping).toBe(false);
    });

    await act(async () => {
      await result.current.startNewFlow("EXCEL");
    });

    act(() => {
      result.current.updateProgramaPdfResult(buildPdfUploadResponse());
    });

    act(() => {
      result.current.updateProgramaExcelPreview(buildExcelPreview());
    });

    act(() => {
      result.current.updateProgramaExcelImport(buildExcelImport());
    });

    expect(result.current.activeReferenceId).toBe(referenceId);
    expect(result.current.payload?.documental.programa_pdf?.uso).toBe(
      "EVIDENCIA_DOCUMENTAL",
    );
    expect(
      result.current.payload?.documental.programa_excel?.preview?.valid,
    ).toBe(true);
    expect(result.current.payload?.documental.programa_excel?.confirmacion.estado).toBe(
      "IMPORTADO",
    );
    expect(result.current.payload?.curricular.programa_formacion_id).toBe(
      "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
    );

    expect(result.current.activeReferenceId).toBe(referenceId);
    expect(result.current.payload?.meta.entryMode).toBe("EXCEL");
  });
});
