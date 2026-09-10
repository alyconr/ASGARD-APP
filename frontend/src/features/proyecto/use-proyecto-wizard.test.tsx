import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useProyectoWizard } from "./use-proyecto-wizard";
import { getDraft, saveDraft } from "@/features/drafts/api";
import type { DraftResponse, DraftSaveRequest } from "@/features/drafts/types";
import type { ProyectoWizardPayload as DraftPayloadProyecto } from "@/features/proyecto/types";

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

const mockGetDraft = vi.mocked(getDraft);
const mockSaveDraft = vi.mocked(saveDraft);
const projectReferenceId = "11111111-1111-4111-9111-111111111111";
const programReferenceId = "22222222-2222-4222-9222-222222222222";
const programId = "33333333-3333-4333-9333-333333333333";

function buildDraftResponse(
  payload: DraftSaveRequest,
  referenceId = projectReferenceId,
): DraftResponse {
  return {
    id: "draft-project",
    tipo_bloque: "PROYECTO",
    referencia_id: referenceId,
    paso_actual: payload.paso_actual,
    payload_json: payload.payload_json,
    estado_borrador: payload.estado_borrador,
    ultima_edicion: "2026-05-16T10:00:00.000Z",
  };
}

function buildProjectPayload(referenceId = projectReferenceId): DraftPayloadProyecto {
  return {
    meta: {
      referenciaId: referenceId,
      programaReferenciaId: programReferenceId,
      programaId: programId,
      touchedSteps: ["revision-proyecto"],
      startedAt: "2026-05-16T09:00:00.000Z",
      lastInteractionAt: "2026-05-16T09:30:00.000Z",
    },
    wizard: {
      notesByStep: {
        "revision-proyecto": "Revisar soporte despues",
      },
    },
    proyecto: {
      proyecto_formativo_id: null,
      codigo_proyecto: "PR-001",
      nombre_proyecto: "Proyecto formativo base",
      version_proyecto: "1",
    },
    documental: {
      proyecto_pdf: null,
      fuente_estructurada: null,
    },
    estructura: {
      fases: [],
      actividades: [],
    },
  };
}

describe("useProyectoWizard", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    vi.spyOn(crypto, "randomUUID").mockReturnValue(projectReferenceId);
    mockSaveDraft.mockImplementation(async (_blockType, _draftId, payload) =>
      buildDraftResponse(payload),
    );
  });

  it("starts a project draft using the PROYECTO block type", async () => {
    const { result } = renderHook(() =>
      useProyectoWizard({
        programaId: programId,
        programaReferenciaId: programReferenceId,
      }),
    );

    await waitFor(() => {
      expect(result.current.isBootstrapping).toBe(false);
    });

    await act(async () => {
      await result.current.startNewFlow();
    });

    expect(result.current.activeReferenceId).toBe(projectReferenceId);
    expect(result.current.currentStepId).toBe("revision-proyecto");
    expect(mockSaveDraft).toHaveBeenCalledWith("PROYECTO", projectReferenceId, {
      paso_actual: "revision-proyecto",
      payload_json: expect.objectContaining({
        meta: expect.objectContaining({
          programaReferenciaId: programReferenceId,
          programaId: programId,
        }),
        proyecto: expect.objectContaining({
          codigo_proyecto: "",
          nombre_proyecto: "",
          version_proyecto: "",
        }),
      }),
      estado_borrador: "BORRADOR",
    });
  });

  it("recovers a project draft and restores the saved step", async () => {
    const payload = buildProjectPayload();
    mockGetDraft.mockResolvedValue(
      buildDraftResponse(
        {
          paso_actual: "revision-proyecto",
          payload_json: payload as unknown as Record<string, unknown>,
          estado_borrador: "BORRADOR",
        },
        projectReferenceId,
      ),
    );
    const { result } = renderHook(() =>
      useProyectoWizard({
        programaId: programId,
        programaReferenciaId: programReferenceId,
      }),
    );

    await waitFor(() => {
      expect(result.current.isBootstrapping).toBe(false);
    });

    await act(async () => {
      await result.current.recoverDraftByReference(projectReferenceId);
    });

    expect(mockGetDraft).toHaveBeenCalledWith("PROYECTO", projectReferenceId);
    expect(result.current.currentStepId).toBe("revision-proyecto");
    expect(result.current.payload?.wizard.notesByStep["revision-proyecto"]).toBe(
      "Revisar soporte despues",
    );
    expect(result.current.payload?.proyecto.codigo_proyecto).toBe("PR-001");
    expect(result.current.payload?.proyecto.nombre_proyecto).toBe(
      "Proyecto formativo base",
    );
    expect(result.current.payload?.proyecto.version_proyecto).toBe("1");
  });

  it("updates and autosaves source-step notes in the PROYECTO draft", async () => {
    const { result } = renderHook(() =>
      useProyectoWizard({
        programaId: programId,
        programaReferenciaId: programReferenceId,
      }),
    );

    await waitFor(() => {
      expect(result.current.isBootstrapping).toBe(false);
    });

    await act(async () => {
      await result.current.startNewFlow();
    });

    act(() => {
      result.current.updateStepNote("revision-proyecto", "PDF evidencia listo");
    });

    expect(result.current.payload?.wizard.notesByStep["revision-proyecto"]).toBe(
      "PDF evidencia listo",
    );

    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 600));
    });

    await waitFor(() => {
      expect(mockSaveDraft).toHaveBeenLastCalledWith(
        "PROYECTO",
        projectReferenceId,
        expect.objectContaining({
          paso_actual: "revision-proyecto",
          payload_json: expect.objectContaining({
            wizard: expect.objectContaining({
              notesByStep: expect.objectContaining({
                "revision-proyecto": "PDF evidencia listo",
              }),
            }),
          }),
        }),
      );
    });
  });

  it("autosaves the single project step after importing the matrix and PDF", async () => {
    const { result } = renderHook(() =>
      useProyectoWizard({
        programaId: programId,
        programaReferenciaId: programReferenceId,
      }),
    );

    await waitFor(() => {
      expect(result.current.isBootstrapping).toBe(false);
    });

    await act(async () => {
      await result.current.startNewFlow();
    });

    expect(result.current.currentStepId).toBe("revision-proyecto");

    await act(async () => {
      result.current.updateProyectoExcelImport({
        preview: {
          valid: true,
          proyecto: {
            codigo_proyecto: "PR-001",
            nombre_proyecto: "Proyecto formativo base",
            version_proyecto: "1",
          },
        },
        confirmacion: {
          estado: "IMPORTADO",
          confirmed_at: "2026-05-16T10:00:00.000Z",
          proyecto_id: "some-id",
        },
      } as unknown as Parameters<typeof result.current.updateProyectoExcelImport>[0]);
      result.current.updateProyectoPdfResult({
        documento: {
          original_filename: "proyecto.pdf",
          storage_key: "proyectos-formativos/some-key.pdf",
          size_bytes: 1024,
          content_type: "application/pdf",
          checksum_sha256: "some-sha",
          etag: "some-etag",
        },
        uso: "EVIDENCIA_DOCUMENTAL",
        updated_at: "2026-05-16T10:00:00.000Z",
      } as unknown as Parameters<typeof result.current.updateProyectoPdfResult>[0]);
    });

    expect(result.current.currentStepId).toBe("revision-proyecto");

    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 600));
    });

    await waitFor(() => {
      expect(mockSaveDraft).toHaveBeenLastCalledWith(
        "PROYECTO",
        projectReferenceId,
        expect.objectContaining({
          paso_actual: "revision-proyecto",
          payload_json: expect.any(Object),
        }),
      );
    });
  });
});
