import type {
  ConocimientoSaberDeleteResponse,
  ConocimientoSaberListResponse,
  ConocimientoSaberPayload,
} from "@/features/programa/types";
import { getApiBaseUrl } from "@/lib/api";

export class ProgramaConocimientoSaberError extends Error {
  readonly status: number;

  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ProgramaConocimientoSaberError";
    this.status = status;
    this.detail = detail;
  }
}

function buildConocimientosSaberUrl(
  referenciaId: string,
  competenciaId: string,
): string {
  return `${getApiBaseUrl()}/programas/${referenciaId}/competencias/${competenciaId}/conocimientos/saber`;
}

async function parseConocimientoSaberError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
    return "No fue posible completar la operacion de conocimientos SABER.";
  }

  return "No fue posible completar la operacion de conocimientos SABER.";
}

async function requestConocimientosSaber(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<ConocimientoSaberListResponse> {
  const response = await fetch(input, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new ProgramaConocimientoSaberError(
      response.status,
      await parseConocimientoSaberError(response),
    );
  }

  return (await response.json()) as ConocimientoSaberListResponse;
}

export async function listProgramaConocimientosSaber(
  referenciaId: string,
  competenciaId: string,
): Promise<ConocimientoSaberListResponse> {
  return requestConocimientosSaber(
    buildConocimientosSaberUrl(referenciaId, competenciaId),
    {
      method: "GET",
    },
  );
}

export async function createProgramaConocimientoSaber(
  referenciaId: string,
  competenciaId: string,
  payload: ConocimientoSaberPayload,
): Promise<ConocimientoSaberListResponse> {
  return requestConocimientosSaber(
    buildConocimientosSaberUrl(referenciaId, competenciaId),
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function updateProgramaConocimientoSaber(
  referenciaId: string,
  competenciaId: string,
  conocimientoId: string,
  payload: ConocimientoSaberPayload,
): Promise<ConocimientoSaberListResponse> {
  return requestConocimientosSaber(
    `${buildConocimientosSaberUrl(referenciaId, competenciaId)}/${conocimientoId}`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
  );
}

export async function deleteProgramaConocimientoSaber(
  referenciaId: string,
  competenciaId: string,
  conocimientoId: string,
): Promise<ConocimientoSaberDeleteResponse> {
  const response = await fetch(
    `${buildConocimientosSaberUrl(referenciaId, competenciaId)}/${conocimientoId}`,
    {
      method: "DELETE",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new ProgramaConocimientoSaberError(
      response.status,
      await parseConocimientoSaberError(response),
    );
  }

  return (await response.json()) as ConocimientoSaberDeleteResponse;
}
