import type { ProyectoStoredDocument } from "@/features/proyecto/types";
import { getApiBaseUrl } from "@/lib/api";

export class ProyectoPdfUploadError extends Error {
  readonly status: number;

  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ProyectoPdfUploadError";
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
    return "No fue posible cargar el PDF del proyecto.";
  }

  return "No fue posible cargar el PDF del proyecto.";
}

export interface ProyectoPdfUploadResponse {
  referencia_id: string;
  documento: ProyectoStoredDocument;
}

export async function uploadProyectoPdf(
  referenciaId: string,
  file: File,
): Promise<ProyectoPdfUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    `${getApiBaseUrl()}/proyectos/${referenciaId}/documentos/proyecto-pdf`,
    {
      method: "POST",
      body: formData,
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new ProyectoPdfUploadError(
      response.status,
      await parseUploadError(response),
    );
  }

  return (await response.json()) as ProyectoPdfUploadResponse;
}
