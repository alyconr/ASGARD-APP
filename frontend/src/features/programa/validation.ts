import type { ProgramaWizardPayload } from "@/features/programa/types";

export type ProgramaBaseField = keyof ProgramaWizardPayload["programa"];

export interface ProgramaFieldValidation {
  isValid: boolean;
  message: string | null;
}

export const PROGRAMA_REQUIRED_FIELDS: ProgramaBaseField[] = [
  "codigo_programa",
  "nombre_programa",
];

export function sanitizeProgramaFieldValue(value: string): string {
  return value.trim().length > 0 ? value : "";
}

export function validateProgramaBaseField(
  field: ProgramaBaseField,
  value: string,
): ProgramaFieldValidation {
  const normalizedValue = value.trim();

  if (
    PROGRAMA_REQUIRED_FIELDS.includes(field) &&
    normalizedValue.length === 0
  ) {
    return {
      isValid: false,
      message: "Este campo es obligatorio para cerrar el programa mas adelante.",
    };
  }

  return {
    isValid: true,
    message: null,
  };
}
