import type {
  ProgramaCompetenciaDeleteResponse,
  ProgramaCompetenciaListResponse,
  ProgramaCompetenciaPayload,
} from "@/features/programa/types";
import { getApiBaseUrl } from "@/lib/api";

export class ProgramaCompetenciaError extends Error {
  readonly status: number;

  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ProgramaCompetenciaError";
    this.status = status;
    this.detail = detail;
  }
}

function buildCompetenciasUrl(referenciaId: string): string {
  return `${getApiBaseUrl()}/programas/${referenciaId}/competencias`;
}

async function parseCompetenciaError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
    return "No fue posible completar la operacion de competencias.";
  }

  return "No fue posible completar la operacion de competencias.";
}

async function requestCompetencias(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<ProgramaCompetenciaListResponse> {
  const response = await fetch(input, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new ProgramaCompetenciaError(
      response.status,
      await parseCompetenciaError(response),
    );
  }

  return (await response.json()) as ProgramaCompetenciaListResponse;
}

export async function listProgramaCompetencias(
  referenciaId: string,
): Promise<ProgramaCompetenciaListResponse> {
  return requestCompetencias(buildCompetenciasUrl(referenciaId), {
    method: "GET",
  });
}

export async function createProgramaCompetencia(
  referenciaId: string,
  payload: ProgramaCompetenciaPayload,
): Promise<ProgramaCompetenciaListResponse> {
  return requestCompetencias(buildCompetenciasUrl(referenciaId), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateProgramaCompetencia(
  referenciaId: string,
  competenciaId: string,
  payload: ProgramaCompetenciaPayload,
): Promise<ProgramaCompetenciaListResponse> {
  return requestCompetencias(
    `${buildCompetenciasUrl(referenciaId)}/${competenciaId}`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
  );
}

export async function deleteProgramaCompetencia(
  referenciaId: string,
  competenciaId: string,
): Promise<ProgramaCompetenciaDeleteResponse> {
  const response = await fetch(
    `${buildCompetenciasUrl(referenciaId)}/${competenciaId}`,
    {
      method: "DELETE",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new ProgramaCompetenciaError(
      response.status,
      await parseCompetenciaError(response),
    );
  }

  return (await response.json()) as ProgramaCompetenciaDeleteResponse;
}
