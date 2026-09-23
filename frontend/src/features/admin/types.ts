export interface CoordinacionSummary {
  id: string;
  codigo: string;
  nombre: string;
}

export interface EspecialidadSummary {
  id: string;
  codigo: string;
  nombre: string;
}

export interface ProgramaSummary {
  id: string;
  codigo: string;
  nombre: string;
  estado: string;
}

export interface ProyectoSummary {
  id: string;
  codigo: string | null;
  nombre: string;
  estado: string;
}

export interface EquipoSummary {
  id: string;
  nombre: string;
  estado: string;
}

export interface LiderSummary {
  id: string;
  nombre: string;
  apellido: string;
  email: string;
}

export interface PlaneacionesCount {
  total: number;
  borrador: number;
  completas: number;
}

export interface AdminProcesoItem {
  referencia_id: string;
  tipo_necesidad: string;
  estado_scope: string;
  coordinacion: CoordinacionSummary | null;
  especialidad: EspecialidadSummary | null;
  programa: ProgramaSummary | null;
  proyecto: ProyectoSummary | null;
  equipo: EquipoSummary | null;
  lider: LiderSummary | null;
  planeaciones: PlaneacionesCount;
  fecha_actualizacion: string;
}

export interface PaginatedAdminProcesos {
  items: AdminProcesoItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminDashboardResumen {
  procesos_totales: number;
  procesos_asignados: number;
  procesos_sin_asignar: number;
  programas_borrador: number;
  programas_en_revision: number;
  programas_completo: number;
  proyectos_bloqueado: number;
  proyectos_borrador: number;
  proyectos_en_revision: number;
  proyectos_completo: number;
  planeaciones_totales: number;
  planeaciones_borrador: number;
  planeaciones_completo: number;
  equipos_activos: number;
  equipos_inactivos: number;
  lideres_activos: number;
  usuarios_apoyo_activos: number;
}

export interface SupervisionFilters {
  coordinacion_id?: string;
  especialidad_id?: string;
  programa_id?: string;
  proyecto_id?: string;
  equipo_ejecutor_id?: string;
  lider_id?: string;
  estado_scope?: string;
  estado_programa?: string;
  estado_proyecto?: string;
  estado_planeacion?: string;
  search?: string;
  solo_sin_asignar?: boolean;
}

export interface ActorSummary {
  id: string;
  nombre: string;
  apellido: string;
  email: string;
  rol: string;
}

export interface AuditItem {
  id: string;
  fecha_evento: string;
  accion: string;
  entidad: string;
  entidad_id: string;
  actor: ActorSummary | null;
  referencia_id: string | null;
  detalle: Record<string, unknown> | null;
}

export interface PaginatedAuditResponse {
  items: AuditItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AuditFilters {
  page?: number;
  page_size?: number;
  fecha_desde?: string;
  fecha_hasta?: string;
  actor_usuario_id?: string;
  accion?: string;
  entidad?: string;
  referencia_id?: string;
  search?: string;
}

export type RolEquipo = "LIDER" | "CO_LIDER" | "INSTRUCTOR" | "TRANSVERSAL" | "COLABORADOR";

export interface ProgramaSimple {
  id: string;
  codigo_programa: string;
  nombre_programa: string;
  version_programa?: string | null;
}

