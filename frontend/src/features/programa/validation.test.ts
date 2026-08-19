import { describe, expect, it } from "vitest";

import {
  PROGRAMA_REQUIRED_FIELDS,
  sanitizeProgramaFieldValue,
  validateProgramaBaseField,
} from "./validation";

describe("programa validation", () => {
  describe("sanitizeProgramaFieldValue", () => {
    it("returns empty string for whitespace only", () => {
      expect(sanitizeProgramaFieldValue("   ")).toBe("");
      expect(sanitizeProgramaFieldValue("")).toBe("");
    });

    it("preserves valid strings but trims them (if needed in sanitize, though currently only checks length > 0)", () => {
      // The current implementation is: value.trim().length > 0 ? value : ""
      // It doesn't actually trim the returned value if it has length.
      expect(sanitizeProgramaFieldValue(" value ")).toBe(" value ");
      expect(sanitizeProgramaFieldValue("value")).toBe("value");
    });
  });

  describe("validateProgramaBaseField", () => {
    it("returns invalid for required fields that are empty", () => {
      PROGRAMA_REQUIRED_FIELDS.forEach((field) => {
        const result = validateProgramaBaseField(field, "   ");
        expect(result.isValid).toBe(false);
        expect(result.message).toBe(
          "Este campo es obligatorio para cerrar el programa mas adelante."
        );
      });
    });

    it("returns valid for required fields that have content", () => {
      PROGRAMA_REQUIRED_FIELDS.forEach((field) => {
        const result = validateProgramaBaseField(field, " content ");
        expect(result.isValid).toBe(true);
        expect(result.message).toBeNull();
      });
    });

    it("returns valid for optional fields even if empty", () => {
      const result = validateProgramaBaseField("version_programa", "   ");
      expect(result.isValid).toBe(true);
      expect(result.message).toBeNull();
    });

    it("returns valid for optional fields with content", () => {
      const result = validateProgramaBaseField("version_programa", " 1.0 ");
      expect(result.isValid).toBe(true);
      expect(result.message).toBeNull();
    });
  });
});
