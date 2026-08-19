import { getApiBaseUrl } from "@/lib/api";
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

  const response = await fetch(
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
  const response = await fetch(
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
