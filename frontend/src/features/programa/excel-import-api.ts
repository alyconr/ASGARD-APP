import { authFetch, getApiBaseUrl } from "@/lib/api";
import type {
  ProgramaExcelImportResponse,
  ProgramaExcelPreviewResponse,
} from "@/features/programa/types";

export class ProgramaExcelImportError extends Error {
  readonly status: number;

  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ProgramaExcelImportError";
    this.status = status;
    this.detail = detail;
  }
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string"
      ? body.detail
      : "No fue posible procesar el Excel canonico.";
  } catch {
    return "No fue posible procesar el Excel canonico.";
  }
}

export async function previewProgramaExcel(
  referenciaId: string,
  file: File,
): Promise<ProgramaExcelPreviewResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await authFetch(
    `${getApiBaseUrl()}/programas/${referenciaId}/documentos/programa-excel/preview`,
    {
      method: "POST",
      body: formData,
    },
  );

  if (!response.ok) {
    throw new ProgramaExcelImportError(
      response.status,
      await parseErrorDetail(response),
    );
  }

  return (await response.json()) as ProgramaExcelPreviewResponse;
}

export async function confirmProgramaExcelImport(
  referenciaId: string,
): Promise<ProgramaExcelImportResponse> {
  const response = await authFetch(
    `${getApiBaseUrl()}/programas/${referenciaId}/documentos/programa-excel/importacion`,
    {
      method: "POST",
    },
  );

  if (!response.ok) {
    throw new ProgramaExcelImportError(
      response.status,
      await parseErrorDetail(response),
    );
  }

  return (await response.json()) as ProgramaExcelImportResponse;
}

export interface ProgramaExcelPrevalidationResponse {
  authorized: boolean;
  codigo_programa: string;
  nombre_programa: string;
  version_programa: string;
  mensaje: string;
  equipo_id?: string | null;
  programa_id?: string | null;
}

export async function prevalidateProgramaExcel(
  referenciaId: string,
  file: File,
): Promise<ProgramaExcelPrevalidationResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await authFetch(
    `${getApiBaseUrl()}/programas/${referenciaId}/documentos/programa-excel/prevalidate`,
    {
      method: "POST",
      body: formData,
    },
  );

  if (!response.ok) {
    throw new ProgramaExcelImportError(
      response.status,
      await parseErrorDetail(response),
    );
  }

  return (await response.json()) as ProgramaExcelPrevalidationResponse;
}
