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
          entryMode: "MANUAL",
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
      expect(normalized.meta.entryMode).toBe("MANUAL");
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
              estado_legibilidad: "PARCIALMENTE_LEGIBLE",
              motivo: "ESTRUCTURA_NO_RECONOCIDA",
              resumen: "Texto parcial",
              has_text_layer: true,
              analyzed_pages: 3,
              pages_with_text: 1,
              text_character_count: 120,
              can_attempt_extraction: true,
              requires_manual_entry: true,
            },
            updated_at: "2026-04-27T00:00:00Z",
          },
        },
      };

      const normalized = normalizeProgramaPayload(input, "ref-123");

      expect(normalized.documental.programa_pdf?.documento.storage_key).toBe(
        "programas/ref/documentos/programa.pdf",
      );
      expect(
        normalized.documental.programa_pdf?.diagnostico.estado_legibilidad,
      ).toBe("PARCIALMENTE_LEGIBLE");
    });

    it("preserves a valid extraction result in the draft payload", () => {
      const input = {
        programa: {
          codigo_programa: "228118",
          nombre_programa: "Analisis y Desarrollo de Software",
          version_programa: "",
        },
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
              estado_legibilidad: "LEGIBLE",
              motivo: null,
              resumen: "Texto legible",
              has_text_layer: true,
              analyzed_pages: 3,
              pages_with_text: 3,
              text_character_count: 1200,
              can_attempt_extraction: true,
              requires_manual_entry: false,
            },
            extraccion: {
              referencia_id: "ref-123",
              estado_legibilidad: "LEGIBLE",
              resumen: "Extraccion aplicada",
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
                      valor: "Construir software",
                      estado: "EXTRAIDO",
                      motivo: null,
                      requiere_revision: true,
                    },
                  ],
                  estado: "EXTRAIDO",
                  motivo: null,
                  requiere_revision: true,
                },
                resultados_aprendizaje: {
                  items: [],
                  estado: "PENDIENTE",
                  motivo: "CAMPO_NO_ENCONTRADO",
                  requiere_revision: true,
                },
                conocimientos_saber: {
                  items: [],
                  estado: "PENDIENTE",
                  motivo: "CAMPO_NO_ENCONTRADO",
                  requiere_revision: true,
                },
                conocimientos_proceso: {
                  items: [],
                  estado: "PENDIENTE",
                  motivo: "CAMPO_NO_ENCONTRADO",
                  requiere_revision: true,
                },
                criterios_evaluacion: {
                  items: [],
                  estado: "PENDIENTE",
                  motivo: "CAMPO_NO_ENCONTRADO",
                  requiere_revision: true,
                },
              },
              programa_actualizado: {
                codigo_programa: "228118",
                nombre_programa: "Analisis y Desarrollo de Software",
                version_programa: "",
              },
              updated_at: "2026-04-28T00:00:00Z",
            },
            updated_at: "2026-04-28T00:00:00Z",
          },
        },
      };

      const normalized = normalizeProgramaPayload(input, "ref-123");

      expect(
        normalized.documental.programa_pdf?.extraccion?.programa.codigo_programa
          .valor,
      ).toBe("228118");
      expect(
        normalized.documental.programa_pdf?.extraccion?.estructura_curricular
          .competencias.items[0]?.valor,
      ).toBe("Construir software");
    });
  });
});
