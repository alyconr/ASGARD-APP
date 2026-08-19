import type {
  ConocimientoProcesoDeleteResponse,
  ConocimientoProcesoListResponse,
  ConocimientoProcesoPayload,
} from "@/features/programa/types";
import { getApiBaseUrl } from "@/lib/api";

export class ProgramaConocimientoProcesoError extends Error {
  readonly status: number;

  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ProgramaConocimientoProcesoError";
    this.status = status;
    this.detail = detail;
  }
}

function buildConocimientosProcesoUrl(
  referenciaId: string,
  competenciaId: string,
): string {
  return `${getApiBaseUrl()}/programas/${referenciaId}/competencias/${competenciaId}/conocimientos/proceso`;
}

async function parseConocimientoProcesoError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
    return "No fue posible completar la operacion de conocimientos PROCESO.";
  }

  return "No fue posible completar la operacion de conocimientos PROCESO.";
}

async function requestConocimientosProceso(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<ConocimientoProcesoListResponse> {
  const response = await fetch(input, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new ProgramaConocimientoProcesoError(
      response.status,
      await parseConocimientoProcesoError(response),
    );
  }

  return (await response.json()) as ConocimientoProcesoListResponse;
}

export async function listProgramaConocimientosProceso(
  referenciaId: string,
  competenciaId: string,
): Promise<ConocimientoProcesoListResponse> {
  return requestConocimientosProceso(
    buildConocimientosProcesoUrl(referenciaId, competenciaId),
    {
      method: "GET",
    },
  );
}

export async function createProgramaConocimientoProceso(
  referenciaId: string,
  competenciaId: string,
  payload: ConocimientoProcesoPayload,
): Promise<ConocimientoProcesoListResponse> {
  return requestConocimientosProceso(
    buildConocimientosProcesoUrl(referenciaId, competenciaId),
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function updateProgramaConocimientoProceso(
  referenciaId: string,
  competenciaId: string,
  conocimientoId: string,
  payload: ConocimientoProcesoPayload,
): Promise<ConocimientoProcesoListResponse> {
  return requestConocimientosProceso(
    `${buildConocimientosProcesoUrl(referenciaId, competenciaId)}/${conocimientoId}`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
  );
}

export async function deleteProgramaConocimientoProceso(
  referenciaId: string,
  competenciaId: string,
  conocimientoId: string,
): Promise<ConocimientoProcesoDeleteResponse> {
  const response = await fetch(
    `${buildConocimientosProcesoUrl(referenciaId, competenciaId)}/${conocimientoId}`,
    {
      method: "DELETE",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new ProgramaConocimientoProcesoError(
      response.status,
      await parseConocimientoProcesoError(response),
    );
  }

  return (await response.json()) as ConocimientoProcesoDeleteResponse;
}
