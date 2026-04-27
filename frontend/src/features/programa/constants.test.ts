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
  });
});
