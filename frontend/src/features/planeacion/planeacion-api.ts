import { authFetch, getApiBaseUrl } from "@/lib/api";

export interface ContextoResultado {
  id: string;
  codigo_resultado?: string | null;
  descripcion: string;
  tipo_resultado: string | null;
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
  tipo_resultado: string | null;
}

export interface PlaneacionCompetenciaResumen {
  competencia_id: string;
  codigo_competencia: string;
  nombre_competencia: string;
  tipo_resultado: string | null;
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
  const response = await authFetch(
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
  const response = await authFetch(
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
  const response = await authFetch(
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
  const response = await authFetch(`${getApiBaseUrl()}/planeaciones`, {
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
  const response = await authFetch(
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
  const response = await authFetch(
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
  const response = await authFetch(`${getApiBaseUrl()}${path}`, {
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
  const response = await authFetch(`${getApiBaseUrl()}${path}`, {
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
        | { message?: string; code?: string }
        | Array<string | { msg?: string; loc?: Array<string | number> }>;
    };
    if (typeof payload.detail === "object" && !Array.isArray(payload.detail) && payload.detail?.message) {
      return payload.detail.message;
    }
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
    return typeof payload.detail === "string"
      ? payload.detail
      : "No fue posible completar la operación.";
  } catch {
    return "No fue posible completar la operación.";
  }
}

// ----------------------------------------------------------------------------
// Revisión Pedagógica y Aprobación de Planeaciones
// ----------------------------------------------------------------------------

export type EstadoEntregaRevision =
  | "BORRADOR"
  | "ENVIADO_REVISION"
  | "EN_REVISION"
  | "AJUSTES_SOLICITADOS"
  | "AJUSTES_EN_PROGRESO"
  | "REENVIADO"
  | "APROBADO";

export type TipoElementoObservacion =
  | "PROCESO_GENERAL"
  | "PROGRAMA"
  | "PROYECTO"
  | "PLANEACION"
  | "CONFIGURACION_DOCUMENTAL"
  | "SECCION";

export type EstadoObservacionRevision =
  | "PENDIENTE"
  | "AJUSTE_REPORTADO"
  | "RESUELTO";

export interface ObservacionRevision {
  id: string;
  entrega_id: string;
  target_type: TipoElementoObservacion;
  target_id?: string | null;
  section_key?: string | null;
  comentario: string;
  estado: EstadoObservacionRevision;
  creado_por_id: string;
  creado_por_nombre: string;
  fecha_creacion: string;
  ajuste_reportado_por_id?: string | null;
  ajuste_reportado_por_nombre?: string | null;
  fecha_ajuste_reportado?: string | null;
  comentario_ajuste?: string | null;
  resuelto_por_id?: string | null;
  resuelto_por_nombre?: string | null;
  fecha_resolucion?: string | null;
}

export interface PreflightEnvioRevision {
  listo: boolean;
  pendientes: string[];
  advertencias?: string[];
  resumen: {
    total_actividades_proyecto?: number;
    planeaciones_completas?: number;
    planeaciones_borrador?: number;
    actividades_sin_planeacion?: string[];
    es_entrega_parcial?: boolean;
    faltantes_count?: number;
    version_actual?: number;
    estado_actual?: string;
    [key: string]: unknown;
  };
}

export interface EntregaRevisionResumen {
  id: string;
  proceso_curricular_id: string;
  referencia_id: string;
  equipo_ejecutor_id?: string | null;
  equipo_ejecutor_nombre: string;
  programa_id?: string | null;
  codigo_programa: string;
  nombre_programa: string;
  proyecto_id?: string | null;
  codigo_proyecto: string;
  nombre_proyecto: string;
  lider_nombre: string;
  lider_email: string;
  version: number;
  estado: EstadoEntregaRevision;
  fecha_envio: string;
  observaciones_pendientes_count: number;
  observaciones_ajustadas_count: number;
  observaciones_resueltas_count: number;
  descarga_habilitada: boolean;
  fecha_actualizacion?: string | null;
}

export interface EntregaRevisionDetalle extends EntregaRevisionResumen {
  notas_entrega?: string | null;
  notas_aprobacion?: string | null;
  snapshot_metadatos: Record<string, unknown>;
  observaciones: ObservacionRevision[];
  historial_versiones: EntregaRevisionResumen[];
}

export interface BandejaRevisionPaginada {
  items: EntregaRevisionResumen[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
  metricas: Record<string, number>;
}

export interface BandejaRevisionFiltros {
  estado?: EstadoEntregaRevision | null;
  programa_id?: string | null;
  equipo_ejecutor_id?: string | null;
  lider_id?: string | null;
  page?: number;
  limit?: number;
}

export type SeccionObservacionPlaneacion =
  | "GENERAL"
  | "FASE"
  | "ACTIVIDAD_PROYECTO"
  | "COMPETENCIA"
  | "RAPS"
  | "ACTIVIDADES_APRENDIZAJE"
  | "DESCRIPCION_EVIDENCIA_APRENDIZAJE"
  | "SABERES"
  | "CRITERIOS_EVALUACION"
  | "ESTRATEGIAS_DIDACTICAS"
  | "AMBIENTES"
  | "MATERIALES"
  | "INSTRUCTORES"
  | "HORAS";

export interface FaseResumen {
  id: string | null;
  nombre: string;
  orden?: number | null;
}

export interface ActividadProyectoResumen {
  id: string | null;
  descripcion: string;
  orden?: number | null;
}

export interface RAPResumen {
  id: string;
  codigo?: string | null;
  descripcion: string;
  tipo_resultado?: string | null;
}

export interface CompetenciaResumen {
  id: string;
  codigo: string;
  nombre: string;
  resultados_count: number;
  resultados: RAPResumen[];
}

export interface ConocimientoResumen {
  id: string;
  tipo: string;
  descripcion: string;
}

export interface CriterioResumen {
  id: string;
  codigo?: string | null;
  descripcion: string;
}

export interface HorasPlaneacion {
  directas: number;
  independientes: number;
  total: number;
  horas_directas?: number;
  horas_independientes?: number;
  horas_totales?: number;
}

export interface PlaneacionRevisionItem {
  id: string;
  estado: string;
  fase: FaseResumen;
  actividad_proyecto: ActividadProyectoResumen;
  competencias: CompetenciaResumen[];
  raps: RAPResumen[];
  actividades_aprendizaje: string;
  actividad_aprendizaje?: string;
  horas: HorasPlaneacion;
  ambiente?: string | null;
  ambientes?: string | string[] | null;
  instructores?: string | string[] | null;
  observaciones_count: number;
  observaciones_pendientes_count: number;
  total_observaciones?: number;
  observaciones_pendientes?: number;
}

export interface PlaneacionesEntregaList {
  entrega_id: string;
  version: number;
  total: number;
  total_planeaciones?: number;
  horas_directas_total: number;
  horas_independientes_total: number;
  planeaciones: PlaneacionRevisionItem[];
  items?: PlaneacionRevisionItem[];
}

export interface PlaneacionRevisionDetalle {
  id: string;
  entrega_id: string;
  version_entrega: number;
  estado: string;
  fase: FaseResumen;
  actividad_proyecto: ActividadProyectoResumen;
  competencias: CompetenciaResumen[];
  conocimientos_saber: ConocimientoResumen[];
  conocimientos_proceso: ConocimientoResumen[];
  criterios_evaluacion: CriterioResumen[];
  actividades_aprendizaje: string;
  descripcion_evidencia: string;
  estrategias_didacticas: string;
  ambientes: string;
  materiales: string;
  instructores: string;
  horas: HorasPlaneacion;
  observaciones_didacticas?: string | null;
  observaciones: ObservacionRevision[];
}

export interface ObservacionCreatePayload {
  target_type: TipoElementoObservacion;
  target_id?: string | null;
  section_key?: string | null;
  comentario: string;
}

export interface AjusteReportarPayload {
  comentario_ajuste: string;
}

export async function fetchPreflightRevision(
  referencia_id: string,
): Promise<PreflightEnvioRevision> {
  return requestJson<PreflightEnvioRevision>(
    `/revision-curricular/proceso/${referencia_id}/preflight-envio`,
  );
}

export async function enviarProcesoARevision(
  referencia_id: string,
  notas_entrega?: string,
): Promise<EntregaRevisionDetalle> {
  return requestJson<EntregaRevisionDetalle>(
    `/revision-curricular/proceso/${referencia_id}/enviar`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ notas_entrega: notas_entrega || null }),
    },
  );
}

export async function fetchEstadoActualRevision(
  referencia_id: string,
): Promise<EntregaRevisionDetalle | null> {
  return requestJson<EntregaRevisionDetalle | null>(
    `/revision-curricular/proceso/${referencia_id}/estado-actual`,
  );
}

export async function fetchDetalleEntrega(
  entrega_id: string,
): Promise<EntregaRevisionDetalle> {
  return requestJson<EntregaRevisionDetalle>(
    `/revision-curricular/entregas/${entrega_id}`,
  );
}

export async function reportarAjusteObservacion(
  observacion_id: string,
  comentario_ajuste: string,
): Promise<ObservacionRevision> {
  return requestJson<ObservacionRevision>(
    `/revision-curricular/observaciones/${observacion_id}/reportar-ajuste`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ comentario_ajuste }),
    },
  );
}

export async function fetchBandejaRevision(
  filtros?: BandejaRevisionFiltros,
): Promise<BandejaRevisionPaginada> {
  const query = new URLSearchParams();
  if (filtros?.estado) query.set("estado", filtros.estado);
  if (filtros?.programa_id) query.set("programa_id", filtros.programa_id);
  if (filtros?.equipo_ejecutor_id) query.set("equipo_ejecutor_id", filtros.equipo_ejecutor_id);
  if (filtros?.lider_id) query.set("lider_id", filtros.lider_id);
  if (filtros?.page) query.set("page", String(filtros.page));
  if (filtros?.limit) query.set("limit", String(filtros.limit));

  const qs = query.toString();
  return requestJson<BandejaRevisionPaginada>(
    `/revision-curricular/bandeja${qs ? `?${qs}` : ""}`,
  );
}

export async function iniciarRevisionEntrega(
  entrega_id: string,
): Promise<EntregaRevisionDetalle> {
  return requestJson<EntregaRevisionDetalle>(
    `/revision-curricular/entregas/${entrega_id}/iniciar-revision`,
    { method: "POST" },
  );
}

export async function crearObservacionEntrega(
  entrega_id: string,
  dto: ObservacionCreatePayload,
): Promise<ObservacionRevision> {
  return requestJson<ObservacionRevision>(
    `/revision-curricular/entregas/${entrega_id}/observaciones`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(dto),
    },
  );
}

export async function solicitarAjustesEntrega(
  entrega_id: string,
): Promise<EntregaRevisionDetalle> {
  return requestJson<EntregaRevisionDetalle>(
    `/revision-curricular/entregas/${entrega_id}/solicitar-ajustes`,
    { method: "POST" },
  );
}

export async function resolverObservacion(
  observacion_id: string,
): Promise<ObservacionRevision> {
  return requestJson<ObservacionRevision>(
    `/revision-curricular/observaciones/${observacion_id}/resolver`,
    { method: "POST" },
  );
}

export async function aprobarEntregaRevision(
  entrega_id: string,
  notas_aprobacion?: string,
): Promise<EntregaRevisionDetalle> {
  return requestJson<EntregaRevisionDetalle>(
    `/revision-curricular/entregas/${entrega_id}/aprobar`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ notas_aprobacion: notas_aprobacion || null }),
    },
  );
}

export async function fetchPlaneacionesEntrega(
  entrega_id: string,
): Promise<PlaneacionesEntregaList> {
  return requestJson<PlaneacionesEntregaList>(
    `/revision-curricular/entregas/${entrega_id}/planeaciones`,
  );
}

export async function fetchPlaneacionRevisionDetalle(
  entrega_id: string,
  planeacion_id: string,
): Promise<PlaneacionRevisionDetalle> {
  return requestJson<PlaneacionRevisionDetalle>(
    `/revision-curricular/entregas/${entrega_id}/planeaciones/${planeacion_id}`,
  );
}

