import type {
  CriterioDeleteResponse,
  CriterioListResponse,
  CriterioPayload,
} from "@/features/programa/types";
import { getApiBaseUrl } from "@/lib/api";

export class ProgramaCriterioError extends Error {
  readonly status: number;

  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ProgramaCriterioError";
    this.status = status;
    this.detail = detail;
  }
}

function buildCriteriosUrl(
  referenciaId: string,
  competenciaId: string,
): string {
  return `${getApiBaseUrl()}/programas/${referenciaId}/competencias/${competenciaId}/criterios`;
}

async function parseCriterioError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
    return "No fue posible completar la operacion de criterios.";
  }

  return "No fue posible completar la operacion de criterios.";
}

async function requestCriterios(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<CriterioListResponse> {
  const response = await fetch(input, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new ProgramaCriterioError(
      response.status,
      await parseCriterioError(response),
    );
  }

  return (await response.json()) as CriterioListResponse;
}

export async function listProgramaCriterios(
  referenciaId: string,
  competenciaId: string,
): Promise<CriterioListResponse> {
  return requestCriterios(
    buildCriteriosUrl(referenciaId, competenciaId),
    {
      method: "GET",
    },
  );
}

export async function createProgramaCriterio(
  referenciaId: string,
  competenciaId: string,
  payload: CriterioPayload,
): Promise<CriterioListResponse> {
  return requestCriterios(
    buildCriteriosUrl(referenciaId, competenciaId),
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function updateProgramaCriterio(
  referenciaId: string,
  competenciaId: string,
  criterioId: string,
  payload: CriterioPayload,
): Promise<CriterioListResponse> {
  return requestCriterios(
    `${buildCriteriosUrl(referenciaId, competenciaId)}/${criterioId}`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
  );
}

export async function deleteProgramaCriterio(
  referenciaId: string,
  competenciaId: string,
  criterioId: string,
): Promise<CriterioDeleteResponse> {
  const response = await fetch(
    `${buildCriteriosUrl(referenciaId, competenciaId)}/${criterioId}`,
    {
      method: "DELETE",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new ProgramaCriterioError(
      response.status,
      await parseCriterioError(response),
    );
  }

  return (await response.json()) as CriterioDeleteResponse;
}
