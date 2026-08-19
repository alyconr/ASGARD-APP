import { getApiBaseUrl } from "@/lib/api";

export interface ContextoResultado {
  id: string;
  codigo_resultado?: string | null;
  descripcion: string;
  tipo_resultado: string;
  orden_resultado?: number | null;
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
  orden?: number | null;
  competencias: ContextoCompetencia[];
}

export interface ContextoFase {
  id: string;
  nombre_fase: string;
  orden?: number | null;
  actividades: ContextoActividad[];
}

export interface PlaneacionContextoResponse {
  programa_id: string;
  codigo_programa: string;
  nombre_programa: string;
  version_programa?: string | null;
  proyecto_id: string;
  codigo_proyecto: string;
  nombre_proyecto: string;
  version_proyecto?: string | null;
  fases: ContextoFase[];
}

export interface PlaneacionSaveRequest {
  planeacion_id?: string | null;
  proyecto_id: string;
  fase_id: string;
  actividad_id: string;
  resultados_ids: string[];
  conocimientos_ids: string[];
  criterios_ids: string[];
  datos_complementarios: Record<string, unknown>;
}

export interface PlaneacionResultadoResumen {
  id: string;
  codigo_resultado?: string | null;
  descripcion: string;
  tipo_resultado: string;
}

export interface PlaneacionCompetenciaResumen {
  competencia_id: string;
  codigo_competencia: string;
  nombre_competencia: string;
  tipo_resultado: string;
  resultados: PlaneacionResultadoResumen[];
}

export interface PlaneacionListCompetencia {
  competencia_id: string;
  codigo_competencia: string;
  resultados_count: number;
}

export interface PlaneacionResponse {
  id: string;
  proyecto_id: string;
  fase_id: string | null;
  actividad_id: string | null;
  estado: string;
  datos_complementarios: Record<string, unknown>;
  resultados_ids: string[];
  conocimientos_ids: string[];
  criterios_ids: string[];
  competencias: PlaneacionCompetenciaResumen[];
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
  fase_id?: string | null;
  actividad_id?: string | null;
  nombre_fase?: string | null;
  descripcion_actividad?: string | null;
  actividades_aprendizaje?: string | null;
  estado: string;
  competencias?: PlaneacionListCompetencia[];
  competencias_count: number;
  resultados_count: number;
  resultados_especificos: number;
  resultados_transversales: number;
  fecha_actualizacion: string;
}

export type ClasificacionInformacion =
  | "PUBLICA"
  | "PUBLICA_CLASIFICADA"
  | "PUBLICA_RESERVADA";

export interface PlaneacionDocumentoConfig {
  proyecto_id: string;
  fecha_elaboracion: string | null;
  modalidad_formacion: string | null;
  clasificacion_informacion: ClasificacionInformacion | null;
  equipo_gestion_curricular: string[];
  regional: string | null;
  centro_formacion: string | null;
  storage_key: string | null;
  file_name: string | null;
  content_type: string | null;
  checksum_sha256: string | null;
  fecha_generacion: string | null;
  version: number;
}

export interface PlaneacionDocumentoConfigUpdate {
  fecha_elaboracion: string;
  modalidad_formacion: string;
  clasificacion_informacion: ClasificacionInformacion;
  equipo_gestion_curricular: string[];
  regional: string;
  centro_formacion: string;
}

export interface FormatoOficialFaltante {
  codigo: string;
  mensaje: string;
  paso: "configuracion" | "curricular" | "complementario" | "confirmacion";
}

export interface FormatoOficialEstado {
  listo: boolean;
  faltantes: FormatoOficialFaltante[];
  planeaciones_completas: number;
  borradores_excluidos: number;
  storage_key: string | null;
  file_name: string | null;
  checksum_sha256: string | null;
  fecha_generacion: string | null;
}

export interface FormatoOficialGenerado {
  storage_key: string;
  file_name: string;
  content_type: string;
  checksum_sha256: string;
  fecha_generacion: string;
  version: number;
  filas_generadas: number;
  planeaciones_incluidas: number;
  borradores_excluidos: number;
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

export async function fetchPlaneacionDocumentoConfig(
  proyectoId: string,
): Promise<PlaneacionDocumentoConfig> {
  return requestJson(
    `/planeaciones/proyecto/${proyectoId}/configuracion-formato-oficial`,
  );
}

export async function savePlaneacionDocumentoConfig(
  proyectoId: string,
  payload: PlaneacionDocumentoConfigUpdate,
): Promise<PlaneacionDocumentoConfig> {
  return requestJson(
    `/planeaciones/proyecto/${proyectoId}/configuracion-formato-oficial`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
}

export async function fetchFormatoOficialEstadoIndividual(
  planeacionId: string,
): Promise<FormatoOficialEstado> {
  return requestJson(`/planeaciones/${planeacionId}/estado-formato-oficial`);
}

export async function fetchFormatoOficialEstadoConsolidado(
  proyectoId: string,
): Promise<FormatoOficialEstado> {
  return requestJson(
    `/planeaciones/proyecto/${proyectoId}/estado-formato-oficial`,
  );
}

export async function generarFormatoOficialIndividual(
  planeacionId: string,
): Promise<FormatoOficialGenerado> {
  return requestJson(
    `/planeaciones/${planeacionId}/generar-formato-oficial`,
    { method: "POST" },
  );
}

export async function generarFormatoOficialConsolidado(
  proyectoId: string,
): Promise<FormatoOficialGenerado> {
  return requestJson(
    `/planeaciones/proyecto/${proyectoId}/generar-formato-oficial`,
    { method: "POST" },
  );
}

export async function downloadFormatoOficialIndividual(
  planeacionId: string,
): Promise<void> {
  await downloadWorkbook(
    `/planeaciones/${planeacionId}/descargar-formato-oficial`,
    "GPFI-F-134V05-planeacion.xlsx",
  );
}

export async function downloadFormatoOficialConsolidado(
  proyectoId: string,
): Promise<void> {
  await downloadWorkbook(
    `/planeaciones/proyecto/${proyectoId}/descargar-formato-oficial`,
    "GPFI-F-134V05-planeacion-pedagogica.xlsx",
  );
}

async function requestJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    cache: "no-store",
    ...init,
  });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
  return response.json() as Promise<T>;
}

async function downloadWorkbook(
  path: string,
  fallbackName: string,
): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "GET",
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const utf8Name = /filename\*=UTF-8''([^;]+)/i.exec(disposition)?.[1];
  const filename = utf8Name ? decodeURIComponent(utf8Name) : fallbackName;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as {
      detail?:
        | string
        | Array<string | { msg?: string; loc?: Array<string | number> }>;
    };
    if (Array.isArray(payload.detail)) {
      const messages = payload.detail.map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && item.msg) {
          const field = item.loc ? item.loc[item.loc.length - 1] : "";
          return field ? `${field}: ${item.msg}` : item.msg;
        }
        return String(item);
      });
      return messages.join("; ");
    }
    return payload.detail ?? "No fue posible completar la operación.";
  } catch {
    return "No fue posible completar la operación.";
  }
}
