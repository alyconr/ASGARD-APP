import type { ProyectoStoredDocument } from "@/features/proyecto/types";
import { getApiBaseUrl } from "@/lib/api";

export class ProyectoExcelUploadError extends Error {
  readonly status: number;

  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ProyectoExcelUploadError";
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
    return "No fue posible procesar el Excel del proyecto.";
  }

  return "No fue posible procesar el Excel del proyecto.";
}

export interface ProyectoExcelPreviewResponse {
  referencia_id: string;
  documento: ProyectoStoredDocument | null;
  valid: boolean;
  estado_validacion: "VALIDO" | "INVALIDO";
  resumen: {
    proyecto: number;
    fases: number;
    actividades: number;
  };
  proyecto: {
    codigo_proyecto: string;
    nombre_proyecto: string;
    version_proyecto: string;
  } | null;
  fases: {
    fase_id: string;
    nombre_fase: string;
    orden: number | null;
    actividades: number;
  }[];
  pendientes_resumen: {
    total: number;
  };
  errores: {
    hoja: string;
    fila: number | null;
    campo: string | null;
    mensaje: string;
  }[];
}

export async function uploadProjectExcelPreview(
  referenciaId: string,
  file: File,
): Promise<ProyectoExcelPreviewResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    `${getApiBaseUrl()}/proyectos/${referenciaId}/excel/preview`,
    {
      method: "POST",
      body: formData,
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new ProyectoExcelUploadError(
      response.status,
      await parseUploadError(response),
    );
  }

  return (await response.json()) as ProyectoExcelPreviewResponse;
}

export async function confirmProjectExcelImport(
  referenciaId: string,
): Promise<{
  referencia_id: string;
  proyecto_id: string;
  fase_ids: string[];
  actividad_ids: string[];
  resumen: {
    proyecto: number;
    fases: number;
    actividades: number;
  };
  pendientes_resumen: {
    total: number;
  };
}> {
  const response = await fetch(
    `${getApiBaseUrl()}/proyectos/${referenciaId}/excel/confirm`,
    {
      method: "POST",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new ProyectoExcelUploadError(
      response.status,
      await parseUploadError(response),
    );
  }

  return (await response.json()) as {
    referencia_id: string;
    proyecto_id: string;
    fase_ids: string[];
    actividad_ids: string[];
    resumen: {
      proyecto: number;
      fases: number;
      actividades: number;
    };
    pendientes_resumen: {
      total: number;
    };
  };
}
