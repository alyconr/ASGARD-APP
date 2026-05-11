import type {
  PendienteCurricularAsignacionResponse,
  PendienteCurricularListResponse,
} from "@/features/programa/types";
import { getApiBaseUrl } from "@/lib/api";

export class ProgramaPendienteError extends Error {
  readonly status: number;

  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ProgramaPendienteError";
    this.status = status;
    this.detail = detail;
  }
}

function buildPendientesUrl(referenciaId: string): string {
  return `${getApiBaseUrl()}/programas/${referenciaId}/pendientes-curriculares`;
}

async function parsePendienteError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
    return "No fue posible completar la conciliacion curricular.";
  }

  return "No fue posible completar la conciliacion curricular.";
}

export async function listPendientesCurriculares(
  referenciaId: string,
): Promise<PendienteCurricularListResponse> {
  const response = await fetch(buildPendientesUrl(referenciaId), {
    method: "GET",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ProgramaPendienteError(
      response.status,
      await parsePendienteError(response),
    );
  }

  return (await response.json()) as PendienteCurricularListResponse;
}

export async function assignPendienteCurricular(
  referenciaId: string,
  pendienteId: string,
  payload: {
    competencia_id: string;
    resultado_id?: string | null;
  },
): Promise<PendienteCurricularAsignacionResponse> {
  const response = await fetch(
    `${buildPendientesUrl(referenciaId)}/${pendienteId}/asignacion`,
    {
      method: "POST",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );

  if (!response.ok) {
    throw new ProgramaPendienteError(
      response.status,
      await parsePendienteError(response),
    );
  }

  return (await response.json()) as PendienteCurricularAsignacionResponse;
}
