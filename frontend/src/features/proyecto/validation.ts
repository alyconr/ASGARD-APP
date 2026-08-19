import type { ProyectoWizardPayload } from "@/features/proyecto/types";

export type ProyectoBaseField = Exclude<
  keyof ProyectoWizardPayload["proyecto"],
  "proyecto_formativo_id"
>;

export interface ProyectoFieldValidation {
  isValid: boolean;
  message: string | null;
}

export const PROYECTO_REQUIRED_FIELDS: ProyectoBaseField[] = [
  "codigo_proyecto",
  "nombre_proyecto",
  "version_proyecto",
];

export function sanitizeProyectoFieldValue(value: string): string {
  return value.trim().length > 0 ? value.trim() : "";
}

export function validateProyectoBaseField(
  field: ProyectoBaseField,
  value: string,
): ProyectoFieldValidation {
  const normalizedValue = value.trim();

  if (
    PROYECTO_REQUIRED_FIELDS.includes(field) &&
    normalizedValue.length === 0
  ) {
    return {
      isValid: false,
      message: "Este campo es obligatorio para completar el proyecto mas adelante.",
    };
  }

  return {
    isValid: true,
    message: null,
  };
}
