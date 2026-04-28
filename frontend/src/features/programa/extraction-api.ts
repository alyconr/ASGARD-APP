import type { ProgramaExtractionResult } from "@/features/programa/types";
import { getApiBaseUrl } from "@/lib/api";

export class ProgramaExtractionError extends Error {
  readonly status: number;

  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ProgramaExtractionError";
    this.status = status;
    this.detail = detail;
  }
}

async function parseExtractionError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
    return "No fue posible extraer informacion del PDF.";
  }

  return "No fue posible extraer informacion del PDF.";
}

export async function extractProgramaPdf(
  referenciaId: string,
): Promise<ProgramaExtractionResult> {
  const response = await fetch(
    `${getApiBaseUrl()}/programas/${referenciaId}/documentos/programa-pdf/extraccion`,
    {
      method: "POST",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new ProgramaExtractionError(
      response.status,
      await parseExtractionError(response),
    );
  }

  return (await response.json()) as ProgramaExtractionResult;
}
