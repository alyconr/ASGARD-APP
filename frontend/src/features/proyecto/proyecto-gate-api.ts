import type { ProyectoDisponibilidadResponse } from "@/features/proyecto/types";
import { getApiBaseUrl } from "@/lib/api";

export class ProyectoGateError extends Error {
  readonly status: number;

  readonly detail: string;

  readonly disponibilidad: ProyectoDisponibilidadResponse | null;

  constructor(
    status: number,
    detail: string,
    disponibilidad: ProyectoDisponibilidadResponse | null = null,
  ) {
    super(detail);
    this.name = "ProyectoGateError";
    this.status = status;
    this.detail = detail;
    this.disponibilidad = disponibilidad;
  }
}

function buildProyectoGateUrl(referenciaId: string, action: string): string {
  return `${getApiBaseUrl()}/programas/${referenciaId}/proyecto/${action}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isProyectoDisponibilidadResponse(
  value: unknown,
): value is ProyectoDisponibilidadResponse {
  return (
    isRecord(value) &&
    typeof value.programa_completo === "boolean" &&
    typeof value.proyecto_bloqueado === "boolean" &&
    typeof value.mensaje === "string"
  );
}

async function parseProyectoGateError(
  response: Response,
): Promise<ProyectoGateError> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (isProyectoDisponibilidadResponse(payload.detail)) {
      return new ProyectoGateError(
        response.status,
        payload.detail.mensaje,
        payload.detail,
      );
    }
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return new ProyectoGateError(response.status, payload.detail);
    }
  } catch {
    return new ProyectoGateError(
      response.status,
      "No fue posible validar la disponibilidad del proyecto.",
    );
  }

  return new ProyectoGateError(
    response.status,
    "No fue posible validar la disponibilidad del proyecto.",
  );
}

async function requestProyectoGate<TResponse>(
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
    throw await parseProyectoGateError(response);
  }

  return (await response.json()) as TResponse;
}

export async function consultarDisponibilidadProyecto(
  referenciaId: string,
): Promise<ProyectoDisponibilidadResponse> {
  return requestProyectoGate<ProyectoDisponibilidadResponse>(
    buildProyectoGateUrl(referenciaId, "disponibilidad"),
    {
      method: "GET",
    },
  );
}

export async function validarAccesoProyecto(
  referenciaId: string,
): Promise<ProyectoDisponibilidadResponse> {
  return requestProyectoGate<ProyectoDisponibilidadResponse>(
    buildProyectoGateUrl(referenciaId, "acceso"),
    {
      method: "POST",
    },
  );
}
