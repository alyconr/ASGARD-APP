import type { ProgramaPdfUploadResponse } from "@/features/programa/types";
import { getApiBaseUrl } from "@/lib/api";

export class ProgramaPdfUploadError extends Error {
  readonly status: number;

  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ProgramaPdfUploadError";
    this.status = status;
    this.detail = detail;
  }
}

async function parseUploadError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
    return "No fue posible cargar y diagnosticar el PDF.";
  }

  return "No fue posible cargar y diagnosticar el PDF.";
}

export async function uploadProgramaPdf(
  referenciaId: string,
  file: File,
): Promise<ProgramaPdfUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    `${getApiBaseUrl()}/programas/${referenciaId}/documentos/programa-pdf`,
    {
      method: "POST",
      body: formData,
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new ProgramaPdfUploadError(
      response.status,
      await parseUploadError(response),
    );
  }

  return (await response.json()) as ProgramaPdfUploadResponse;
}
