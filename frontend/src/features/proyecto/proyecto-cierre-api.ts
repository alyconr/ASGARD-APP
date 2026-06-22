import type {
  ProyectoCierreResponse,
  ProyectoCompletitudResponse,
} from "@/features/proyecto/types";
import { getApiBaseUrl } from "@/lib/api";

export class ProyectoCierreError extends Error {
  readonly status: number;

  readonly detail: string;

  readonly completitud: ProyectoCompletitudResponse | null;

  constructor(
    status: number,
    detail: string,
    completitud: ProyectoCompletitudResponse | null = null,
  ) {
    super(detail);
    this.name = "ProyectoCierreError";
    this.status = status;
    this.detail = detail;
    this.completitud = completitud;
  }
}

function buildProyectoUrl(referenciaId: string, action: string): string {
  return `${getApiBaseUrl()}/proyectos/${referenciaId}/${action}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isCompletitudResponse(
  value: unknown,
): value is ProyectoCompletitudResponse {
  return (
    isRecord(value) &&
    typeof value.cerrable === "boolean" &&
    isRecord(value.resumen) &&
    Array.isArray(value.faltantes)
  );
}

async function parseProyectoCierreError(
  response: Response,
): Promise<ProyectoCierreError> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (isCompletitudResponse(payload.detail)) {
      return new ProyectoCierreError(
        response.status,
        "El proyecto no cumple la estructura minima de cierre.",
        payload.detail,
      );
    }
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return new ProyectoCierreError(response.status, payload.detail);
    }
  } catch {
    return new ProyectoCierreError(
      response.status,
      "No fue posible completar la operacion de cierre del proyecto.",
    );
  }

  return new ProyectoCierreError(
    response.status,
    "No fue posible completar la operacion de cierre del proyecto.",
  );
}

async function requestProyectoCierre<TResponse>(
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
    throw await parseProyectoCierreError(response);
  }

  return (await response.json()) as TResponse;
}

export async function validarCompletitudProyecto(
  referenciaId: string,
): Promise<ProyectoCompletitudResponse> {
  return requestProyectoCierre<ProyectoCompletitudResponse>(
    buildProyectoUrl(referenciaId, "completitud"),
    {
      method: "GET",
    },
  );
}

export async function cerrarProyecto(
  referenciaId: string,
): Promise<ProyectoCierreResponse> {
  return requestProyectoCierre<ProyectoCierreResponse>(
    buildProyectoUrl(referenciaId, "cierre"),
    {
      method: "POST",
    },
  );
}
