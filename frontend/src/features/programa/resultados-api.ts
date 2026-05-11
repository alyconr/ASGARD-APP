import type {
  ResultadoAprendizajeDeleteResponse,
  ResultadoAprendizajeListResponse,
  ResultadoAprendizajePayload,
} from "@/features/programa/types";
import { getApiBaseUrl } from "@/lib/api";

export class ProgramaResultadoError extends Error {
  readonly status: number;

  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ProgramaResultadoError";
    this.status = status;
    this.detail = detail;
  }
}

function buildResultadosUrl(referenciaId: string, competenciaId: string): string {
  return `${getApiBaseUrl()}/programas/${referenciaId}/competencias/${competenciaId}/resultados`;
}

async function parseResultadoError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
    return "No fue posible completar la operacion de resultados de aprendizaje.";
  }

  return "No fue posible completar la operacion de resultados de aprendizaje.";
}

async function requestResultados(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<ResultadoAprendizajeListResponse> {
  const response = await fetch(input, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new ProgramaResultadoError(
      response.status,
      await parseResultadoError(response),
    );
  }

  return (await response.json()) as ResultadoAprendizajeListResponse;
}

export async function listProgramaResultados(
  referenciaId: string,
  competenciaId: string,
): Promise<ResultadoAprendizajeListResponse> {
  return requestResultados(buildResultadosUrl(referenciaId, competenciaId), {
    method: "GET",
  });
}

export async function createProgramaResultado(
  referenciaId: string,
  competenciaId: string,
  payload: ResultadoAprendizajePayload,
): Promise<ResultadoAprendizajeListResponse> {
  return requestResultados(buildResultadosUrl(referenciaId, competenciaId), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateProgramaResultado(
  referenciaId: string,
  competenciaId: string,
  resultadoId: string,
  payload: ResultadoAprendizajePayload,
): Promise<ResultadoAprendizajeListResponse> {
  return requestResultados(
    `${buildResultadosUrl(referenciaId, competenciaId)}/${resultadoId}`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
  );
}

export async function deleteProgramaResultado(
  referenciaId: string,
  competenciaId: string,
  resultadoId: string,
): Promise<ResultadoAprendizajeDeleteResponse> {
  const response = await fetch(
    `${buildResultadosUrl(referenciaId, competenciaId)}/${resultadoId}`,
    {
      method: "DELETE",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new ProgramaResultadoError(
      response.status,
      await parseResultadoError(response),
    );
  }

  return (await response.json()) as ResultadoAprendizajeDeleteResponse;
}
