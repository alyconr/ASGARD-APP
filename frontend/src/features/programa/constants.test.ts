import { describe, expect, it } from "vitest";

import {
  PROGRAMA_WIZARD_STEPS,
  DEFAULT_PROGRAMA_STEP_ID,
  isProgramaWizardStepId,
  createEmptyProgramaPayload,
  normalizeProgramaPayload,
} from "./constants";

describe("programa constants", () => {
  describe("isProgramaWizardStepId", () => {
    it("returns true for valid step ids", () => {
      PROGRAMA_WIZARD_STEPS.forEach((step) => {
        expect(isProgramaWizardStepId(step.id)).toBe(true);
      });
    });

    it("returns false for invalid step ids", () => {
      expect(isProgramaWizardStepId("invalid-step")).toBe(false);
      expect(isProgramaWizardStepId("")).toBe(false);
    });
  });

  describe("createEmptyProgramaPayload", () => {
    it("creates a well-formed empty payload", () => {
      const payload = createEmptyProgramaPayload("ref-123");
      expect(payload.meta.referenciaId).toBe("ref-123");
      expect(payload.meta.entryMode).toBeNull();
      expect(payload.meta.touchedSteps).toEqual([DEFAULT_PROGRAMA_STEP_ID]);
      expect(payload.programa.codigo_programa).toBe("");
      expect(payload.documental.programa_pdf).toBeNull();
      expect(payload.documental.programa_excel).toBeNull();
      expect(payload.wizard.notesByStep).toEqual({});
      expect(typeof payload.meta.startedAt).toBe("string");
      expect(typeof payload.meta.lastInteractionAt).toBe("string");
    });
  });

  describe("normalizeProgramaPayload", () => {
    it("normalizes a completely empty object into a valid payload", () => {
      const normalized = normalizeProgramaPayload({}, "ref-123");
      expect(normalized.meta.referenciaId).toBe("ref-123");
      expect(normalized.meta.entryMode).toBeNull();
      expect(normalized.meta.touchedSteps).toEqual([DEFAULT_PROGRAMA_STEP_ID]);
      expect(normalized.programa.codigo_programa).toBe("");
      expect(normalized.documental.programa_pdf).toBeNull();
    });

    it("preserves valid properties and step notes", () => {
      const input = {
        meta: {
          entryMode: "EXCEL",
          touchedSteps: ["datos-programa", "origen-documental"],
          startedAt: "2024-01-01T00:00:00Z",
          lastInteractionAt: "2024-01-01T01:00:00Z",
        },
        programa: {
          codigo_programa: "123",
          nombre_programa: "Test",
          version_programa: "v1",
        },
        wizard: {
          notesByStep: {
            "datos-programa": "some note",
            "invalid-step": "should be ignored",
          },
        },
      };

      const normalized = normalizeProgramaPayload(input, "ref-123");
      expect(normalized.meta.entryMode).toBe("EXCEL");
      expect(normalized.meta.touchedSteps).toEqual([
        "datos-programa",
        "origen-documental",
      ]);
      expect(normalized.programa.codigo_programa).toBe("123");
      expect(normalized.programa.nombre_programa).toBe("Test");
      expect(normalized.programa.version_programa).toBe("v1");
      expect(normalized.wizard.notesByStep).toEqual({
        "datos-programa": "some note",
      });
    });

    it("filters out invalid steps and deduplicates touched steps", () => {
      const input = {
        meta: {
          touchedSteps: [
            "datos-programa",
            "invalid-step",
            "datos-programa",
            "origen-documental",
          ],
        },
      };

      const normalized = normalizeProgramaPayload(input, "ref-123");
      expect(normalized.meta.touchedSteps).toEqual([
        "datos-programa",
        "origen-documental",
      ]);
    });

    it("preserves a valid program PDF diagnosis in the draft payload", () => {
      const input = {
        documental: {
          programa_pdf: {
            documento: {
              original_filename: "programa.pdf",
              storage_key: "programas/ref/documentos/programa.pdf",
              size_bytes: 2048,
              content_type: "application/pdf",
              checksum_sha256: "checksum",
              etag: "etag",
            },
            diagnostico: {
              resumen: "Texto parcial",
              has_text_layer: true,
              analyzed_pages: 3,
              pages_with_text: 1,
              text_character_count: 120,
              almacenamiento_exitoso: true,
            },
            uso: "EVIDENCIA_DOCUMENTAL",
            updated_at: "2026-04-27T00:00:00Z",
          },
        },
      };

      const normalized = normalizeProgramaPayload(input, "ref-123");

      expect(normalized.documental.programa_pdf?.documento.storage_key).toBe(
        "programas/ref/documentos/programa.pdf",
      );
      expect(normalized.documental.programa_pdf?.diagnostico.resumen).toBe(
        "Texto parcial",
      );
      expect(normalized.documental.programa_pdf?.uso).toBe(
        "EVIDENCIA_DOCUMENTAL",
      );
    });

    it("preserves canonical Excel preview metadata in the draft payload", () => {
      const input = {
        documental: {
          programa_excel: {
            documento: {
              original_filename: "programa.xlsx",
              storage_key: "programas/ref/documentos/programa.xlsx",
              size_bytes: 2048,
              content_type:
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              checksum_sha256: "checksum",
              etag: "etag",
            },
            preview: {
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
                  codigo_competencia: "220501096",
                  nombre_competencia: "Construir software",
                  resultados: 1,
                  conocimientos: 2,
                  criterios: 1,
                },
              ],
              errores: [],
            },
            confirmacion: { estado: "PENDIENTE" },
            updated_at: "2026-04-28T00:00:00Z",
          },
        },
      };

      const normalized = normalizeProgramaPayload(input, "ref-123");

      expect(normalized.documental.programa_excel?.preview?.valid).toBe(true);
      expect(
        normalized.documental.programa_excel?.preview?.competencias[0]
          ?.codigo_competencia,
      ).toBe("220501096");
    });
  });
});
