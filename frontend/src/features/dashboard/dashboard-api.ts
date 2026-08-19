import { getApiBaseUrl } from "@/lib/api";

export interface DashboardModule {
  id: "programa" | "proyecto" | "planeacion" | string;
  titulo: string;
  estado: string;
  disponible: boolean;
  href: string;
  motivo_bloqueo: string | null;
  accion_requerida: string;
  descripcion: string;
  avance_porcentaje: number;
}

export interface DashboardMetrics {
  programa: {
    estado: string;
    competencias: number;
    resultados: number;
    conocimientos: number;
    criterios: number;
  };
  proyecto: {
    estado: string;
    fases: number;
    actividades: number;
    fuente_estructurada_cargada: boolean;
  };
  planeacion: {
    estado: string;
    total: number;
    borrador: number;
    completas: number;
    competencias_con_planeacion: number;
    competencias_sin_planear: number;
  };
}

export interface DashboardGraphNode {
  id: string;
  label: string;
  tipo: string;
  estado: string;
  href: string;
  disponible: boolean;
  detalle: string;
}

export interface DashboardGraphEdge {
  origen: string;
  destino: string;
  estado: string;
  label: string;
}

export interface DashboardResponse {
  referencia_id: string;
  estado_global: string;
  resumen: string;
  modules: DashboardModule[];
  metricas: DashboardMetrics;
  graph_nodes: DashboardGraphNode[];
  graph_edges: DashboardGraphEdge[];
}

export interface DashboardProgramFlow {
  referencia_id: string;
  estado: string;
  paso_actual: string;
  ultima_edicion: string;
  titulo: string;
  codigo_programa: string | null;
  nombre_programa: string | null;
  href: string;
}

async function parseDashboardError(response: Response): Promise<string> {
  let detail = "No fue posible cargar el dashboard maestro.";
  try {
    const payload = (await response.json()) as { detail?: string };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      detail = payload.detail;
    }
  } catch {}
  return detail;
}

export async function fetchDashboard(
  referenciaId: string,
): Promise<DashboardResponse> {
  const response = await fetch(`${getApiBaseUrl()}/dashboard/${referenciaId}`, {
    method: "GET",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseDashboardError(response));
  }

  return response.json() as Promise<DashboardResponse>;
}

export async function fetchProgramFlows(): Promise<DashboardProgramFlow[]> {
  const response = await fetch(`${getApiBaseUrl()}/dashboard/programas`, {
    method: "GET",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseDashboardError(response));
  }

  return response.json() as Promise<DashboardProgramFlow[]>;
}

export async function deleteProgramFlow(referenciaId: string): Promise<void> {
  const response = await fetch(
    `${getApiBaseUrl()}/dashboard/programas/${referenciaId}`,
    {
      method: "DELETE",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(await parseDashboardError(response));
  }
}
