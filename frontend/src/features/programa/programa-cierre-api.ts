import type {
  ProgramaCierreResponse,
  ProgramaCompletitudResponse,
} from "@/features/programa/types";
import { getApiBaseUrl } from "@/lib/api";

export class ProgramaCierreError extends Error {
  readonly status: number;

  readonly detail: string;

  readonly completitud: ProgramaCompletitudResponse | null;

  constructor(
    status: number,
    detail: string,
    completitud: ProgramaCompletitudResponse | null = null,
  ) {
    super(detail);
    this.name = "ProgramaCierreError";
    this.status = status;
    this.detail = detail;
    this.completitud = completitud;
  }
}

function buildProgramaUrl(referenciaId: string, action: string): string {
  return `${getApiBaseUrl()}/programas/${referenciaId}/${action}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isCompletitudResponse(
  value: unknown,
): value is ProgramaCompletitudResponse {
  return (
    isRecord(value) &&
    typeof value.cerrable === "boolean" &&
    isRecord(value.resumen) &&
    Array.isArray(value.faltantes)
  );
}

async function parseProgramaCierreError(
  response: Response,
): Promise<ProgramaCierreError> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (isCompletitudResponse(payload.detail)) {
      return new ProgramaCierreError(
        response.status,
        "El programa no cumple la estructura minima de cierre.",
        payload.detail,
      );
    }
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return new ProgramaCierreError(response.status, payload.detail);
    }
  } catch {
    return new ProgramaCierreError(
      response.status,
      "No fue posible completar la operacion de cierre del programa.",
    );
  }

  return new ProgramaCierreError(
    response.status,
    "No fue posible completar la operacion de cierre del programa.",
  );
}

async function requestProgramaCierre<TResponse>(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<TResponse> {
  const response = await fetch(input, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw await parseProgramaCierreError(response);
  }

  return (await response.json()) as TResponse;
}

export async function validarCompletitudPrograma(
  referenciaId: string,
): Promise<ProgramaCompletitudResponse> {
  return requestProgramaCierre<ProgramaCompletitudResponse>(
    buildProgramaUrl(referenciaId, "completitud"),
    {
      method: "GET",
    },
  );
}

export async function cerrarPrograma(
  referenciaId: string,
): Promise<ProgramaCierreResponse> {
  return requestProgramaCierre<ProgramaCierreResponse>(
    buildProgramaUrl(referenciaId, "cierre"),
    {
      method: "POST",
    },
  );
}
