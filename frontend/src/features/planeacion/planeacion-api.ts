import { getApiBaseUrl } from "@/lib/api";

export interface ContextoResultado {
  id: string;
  descripcion: string;
  fase_id?: string | null;
  actividad_id?: string | null;
  asignaciones_proyecto?: ContextoAsignacionProyecto[];
}

export interface ContextoAsignacionProyecto {
  fase_id: string;
  actividad_id: string;
}

export interface ContextoConocimiento {
  id: string;
  descripcion: string;
}

export interface ContextoCriterio {
  id: string;
  descripcion: string;
}

export interface ContextoCompetencia {
  id: string;
  codigo_competencia: string;
  nombre_competencia: string;
  resultados: ContextoResultado[];
  conocimientos_saber: ContextoConocimiento[];
  conocimientos_proceso: ContextoConocimiento[];
  criterios: ContextoCriterio[];
}

export interface ContextoActividad {
  id: string;
  descripcion: string;
}

export interface ContextoFase {
  id: string;
  nombre_fase: string;
  actividades: ContextoActividad[];
}

export interface PlaneacionContextoResponse {
  programa_id: string;
  codigo_programa: string;
  nombre_programa: string;
  proyecto_id: string;
  codigo_proyecto: string;
  nombre_proyecto: string;
  competencias: ContextoCompetencia[];
  fases: ContextoFase[];
}

export interface PlaneacionSaveRequest {
  proyecto_id: string;
  competencia_id: string;
  resultado_id: string;
  fase_id?: string | null;
  actividad_id?: string | null;
  resultados_ids: string[];
  conocimientos_ids: string[];
  criterios_ids: string[];
  datos_complementarios: Record<string, unknown>;
}

export interface PlaneacionResponse {
  id: string;
  proyecto_id: string;
  competencia_id: string;
  resultado_id: string;
  resultado_descripcion: string | null;
  fase_id: string | null;
  actividad_id: string | null;
  estado: string;
  datos_complementarios: Record<string, unknown>;
  resultados_ids: string[];
  conocimientos_ids: string[];
  criterios_ids: string[];
  storage_key: string | null;
  file_name: string | null;
  content_type: string | null;
  checksum_sha256: string | null;
  fecha_generacion: string | null;
  version: number;
}

export interface PlaneacionListResponse {
  id: string;
  proyecto_id: string;
  competencia_id: string;
  resultado_id: string;
  resultado_descripcion: string;
  codigo_competencia: string;
  nombre_competencia: string;
  estado: string;
  fecha_actualizacion: string;
}

export async function fetchPlaneacionContexto(
  referenciaId: string,
): Promise<PlaneacionContextoResponse> {
  const response = await fetch(
    `${getApiBaseUrl()}/planeaciones/contexto/${referenciaId}`,
    {
      method: "GET",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    let errorDetail = "No fue posible cargar el contexto de planeación.";
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        errorDetail = payload.detail;
      }
    } catch {}
    throw new Error(errorDetail);
  }

  return response.json() as Promise<PlaneacionContextoResponse>;
}

export async function listPlaneacionesProyecto(
  proyectoId: string,
): Promise<PlaneacionListResponse[]> {
  const response = await fetch(
    `${getApiBaseUrl()}/planeaciones/proyecto/${proyectoId}`,
    {
      method: "GET",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error("No fue posible listar las planeaciones del proyecto.");
  }

  return response.json() as Promise<PlaneacionListResponse[]>;
}

export async function fetchPlaneacionDetalle(
  planeacionId: string,
): Promise<PlaneacionResponse> {
  const response = await fetch(
    `${getApiBaseUrl()}/planeaciones/${planeacionId}`,
    {
      method: "GET",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error("No fue posible cargar el detalle de la planeación.");
  }

  return response.json() as Promise<PlaneacionResponse>;
}

export async function savePlaneacionBorrador(
  payload: PlaneacionSaveRequest,
): Promise<PlaneacionResponse> {
  const response = await fetch(`${getApiBaseUrl()}/planeaciones`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let errorDetail = "Error al guardar el borrador.";
    try {
      const p = (await response.json()) as { detail?: string };
      if (p.detail) {
        errorDetail = p.detail;
      }
    } catch {}
    throw new Error(errorDetail);
  }

  return response.json() as Promise<PlaneacionResponse>;
}

export async function confirmarPlaneacion(
  planeacionId: string,
): Promise<PlaneacionResponse> {
  const response = await fetch(
    `${getApiBaseUrl()}/planeaciones/${planeacionId}/confirmar`,
    {
      method: "POST",
    },
  );

  if (!response.ok) {
    let errorDetail = "Error al confirmar la planeación.";
    try {
      const p = (await response.json()) as { detail?: string };
      if (p.detail) {
        errorDetail = p.detail;
      }
    } catch {}
    throw new Error(errorDetail);
  }

  return response.json() as Promise<PlaneacionResponse>;
}

export async function deletePlaneacion(planeacionId: string): Promise<void> {
  const response = await fetch(
    `${getApiBaseUrl()}/planeaciones/${planeacionId}`,
    {
      method: "DELETE",
    },
  );

  if (!response.ok) {
    throw new Error("No fue posible eliminar la planeación.");
  }
}
