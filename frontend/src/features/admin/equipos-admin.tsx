"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Trash2, AlertTriangle, Unlink, Layers } from "lucide-react";
import { authFetch, getApiBaseUrl } from "@/lib/api";
import { TeamFormDialog, EquipoEjecutor } from "./team-form-dialog";

interface Coordinacion {
  id: string;
  codigo: string;
  nombre: string;
}

interface Especialidad {
  id: string;
  coordinacion_id: string;
  codigo: string;
  nombre: string;
}

interface UserSummary {
  id: string;
  nombre: string;
  apellido: string;
  email: string;
  roles: string[];
}

interface Miembro {
  id: string;
  equipo_id: string;
  usuario_id: string;
  activo: boolean;
  usuario?: UserSummary;
}

interface ProcesoCurricular {
  id: string;
  referencia_id: string;
  tipo_necesidad: string;
  estado_scope: string;
  programa_nombre?: string | null;
  programa_codigo?: string | null;
  proyecto_nombre?: string | null;
  proyecto_codigo?: string | null;
}

export interface FullEquipoEjecutor extends Omit<EquipoEjecutor, "miembros"> {
  miembros?: Miembro[];
  procesos?: ProcesoCurricular[];
}

interface PaginatedEquiposResponse {
  items: FullEquipoEjecutor[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export function EquiposAdmin(): React.JSX.Element {
  const [equipos, setEquipos] = useState<FullEquipoEjecutor[]>([]);
  const [coordinaciones, setCoordinaciones] = useState<Coordinacion[]>([]);
  const [especialidades, setEspecialidades] = useState<Especialidad[]>([]);
  const [usuariosApoyo, setUsuariosApoyo] = useState<UserSummary[]>([]);
  const [procesosSinAsignar, setProcesosSinAsignar] = useState<ProcesoCurricular[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters & Pagination
  const [search, setSearch] = useState("");
  const [filterCoord, setFilterCoord] = useState("");
  const [filterEsp, setFilterEsp] = useState("");
  const [filterEstado, setFilterEstado] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // Modal states
  const [showTeamModal, setShowTeamModal] = useState(false);
  const [editingTeam, setEditingTeam] = useState<EquipoEjecutor | null>(null);

  // Delete team confirmation state
  const [teamToDelete, setTeamToDelete] = useState<FullEquipoEjecutor | null>(null);
  const [deletingTeamLoading, setDeletingTeamLoading] = useState(false);
  const [teamDeleteError, setTeamDeleteError] = useState<string | null>(null);

  // Process action confirmation state (unassign or delete)
  const [processAction, setProcessAction] = useState<{
    type: "unassign" | "delete";
    referenciaId: string;
    label?: string;
  } | null>(null);
  const [processActionLoading, setProcessActionLoading] = useState(false);
  const [processActionError, setProcessActionError] = useState<string | null>(null);

  // Add member modal state
  const [selectedEquipoForMember, setSelectedEquipoForMember] = useState<EquipoEjecutor | null>(null);
  const [selectedMemberUserId, setSelectedMemberUserId] = useState("");
  const [memberError, setMemberError] = useState<string | null>(null);

  // Load catalogs (coordinaciones, unassigned processes, support users)
  const loadCatalogs = useCallback(async () => {
    try {
      const [coordRes, sinAsignarRes, usersRes] = await Promise.all([
        authFetch(`${getApiBaseUrl()}/coordinaciones`),
        authFetch(`${getApiBaseUrl()}/procesos/sin-asignar`),
        authFetch(`${getApiBaseUrl()}/auth/users?role=USUARIO_ADICIONAL&page_size=100`),
      ]);

      if (coordRes.ok) setCoordinaciones(await coordRes.json());
      if (sinAsignarRes.ok) setProcesosSinAsignar(await sinAsignarRes.json());
      if (usersRes.ok) {
        const usersData = await usersRes.json();
        const usersList: UserSummary[] = Array.isArray(usersData) ? usersData : usersData.items || [];
        setUsuariosApoyo(usersList.filter((u) => u.roles.includes("USUARIO_ADICIONAL")));
      }
    } catch (err) {
      console.error("Error loading catalogs:", err);
    }
  }, []);

  // Load specialties for filter
  useEffect(() => {
    if (!filterCoord) {
      setEspecialidades([]);
      setFilterEsp("");
      return;
    }
    authFetch(`${getApiBaseUrl()}/coordinaciones/${filterCoord}/especialidades?solo_activas=true`)
      .then(async (res) => {
        if (res.ok) setEspecialidades(await res.json());
      })
      .catch(console.error);
  }, [filterCoord]);

  // Load teams with pagination and filters
  const loadTeams = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("page_size", "9"); // 3x3 grid
      if (search.trim()) params.set("search", search.trim());
      if (filterCoord) params.set("coordinacion_id", filterCoord);
      if (filterEsp) params.set("especialidad_id", filterEsp);
      if (filterEstado) params.set("estado", filterEstado);

      const res = await authFetch(`${getApiBaseUrl()}/equipos?${params.toString()}`);
      if (res.ok) {
        const data: PaginatedEquiposResponse = await res.json();
        setEquipos(data.items || []);
        setTotalPages(data.total_pages || 1);
        setTotalCount(data.total || 0);
      }
    } catch (err) {
      console.error("Error loading teams:", err);
    } finally {
      setLoading(false);
    }
  }, [page, search, filterCoord, filterEsp, filterEstado]);

  useEffect(() => {
    loadCatalogs();
  }, [loadCatalogs]);

  useEffect(() => {
    loadTeams();
  }, [loadTeams]);

  const handleOpenCreate = () => {
    setEditingTeam(null);
    setShowTeamModal(true);
  };

  const handleOpenEdit = (team: EquipoEjecutor) => {
    setEditingTeam(team);
    setShowTeamModal(true);
  };

  const handleAddMember = async () => {
    if (!selectedEquipoForMember || !selectedMemberUserId) return;
    setMemberError(null);
    try {
      const res = await authFetch(`${getApiBaseUrl()}/equipos/${selectedEquipoForMember.id}/miembros`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ usuario_id: selectedMemberUserId }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setMemberError(err.detail || "Error al asociar miembro");
        return;
      }
      setSelectedEquipoForMember(null);
      setSelectedMemberUserId("");
      await loadTeams();
    } catch (err: unknown) {
      setMemberError(err instanceof Error ? err.message : "Error al asociar miembro");
    }
  };

  const handleToggleMember = async (equipoId: string, usuarioId: string, currentActive: boolean) => {
    try {
      const res = await authFetch(`${getApiBaseUrl()}/equipos/${equipoId}/miembros/${usuarioId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ activo: !currentActive }),
      });
      if (res.ok) {
        await loadTeams();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleAssignProcess = async (referenciaId: string, equipoId: string) => {
    try {
      const res = await authFetch(`${getApiBaseUrl()}/procesos/${referenciaId}/asignar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ equipo_ejecutor_id: equipoId }),
      });
      if (res.ok) {
        await Promise.all([loadCatalogs(), loadTeams()]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleConfirmDeleteTeam = async (forceUnassign: boolean) => {
    if (!teamToDelete) return;
    setDeletingTeamLoading(true);
    setTeamDeleteError(null);
    try {
      const url = `${getApiBaseUrl()}/equipos/${teamToDelete.id}${forceUnassign ? "?desasignar_procesos=true" : ""}`;
      const res = await authFetch(url, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setTeamDeleteError(err.detail || "Error al eliminar el equipo ejecutor");
        return;
      }
      setTeamToDelete(null);
      await Promise.all([loadCatalogs(), loadTeams()]);
    } catch (err: unknown) {
      setTeamDeleteError(err instanceof Error ? err.message : "Error al eliminar el equipo ejecutor");
    } finally {
      setDeletingTeamLoading(false);
    }
  };

  const handleConfirmProcessAction = async () => {
    if (!processAction) return;
    setProcessActionLoading(true);
    setProcessActionError(null);
    try {
      if (processAction.type === "unassign") {
        const res = await authFetch(`${getApiBaseUrl()}/procesos/${processAction.referenciaId}/desasignar`, {
          method: "POST",
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          setProcessActionError(err.detail || "Error al desasignar el proceso curricular");
          return;
        }
      } else {
        const res = await authFetch(`${getApiBaseUrl()}/procesos/${processAction.referenciaId}`, {
          method: "DELETE",
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          setProcessActionError(err.detail || "Error al eliminar el proceso curricular");
          return;
        }
      }
      setProcessAction(null);
      await Promise.all([loadCatalogs(), loadTeams()]);
    } catch (err: unknown) {
      setProcessActionError(err instanceof Error ? err.message : "Error al procesar la acción");
    } finally {
      setProcessActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
            Gestión de Equipos Ejecutores
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Administración de equipos ejecutores, sincronización atómica de líderes y miembros de apoyo con alcance multiusuario.
          </p>
        </div>
        <button
          onClick={handleOpenCreate}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-emerald-700"
        >
          <span>+</span> Crear Equipo Ejecutor
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="grid grid-cols-1 gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-5 dark:border-slate-800 dark:bg-slate-900">
        <div className="lg:col-span-2">
          <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400">Buscar</label>
          <input
            type="text"
            placeholder="Buscar por nombre de equipo..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-1.5 text-xs text-slate-800 transition focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          />
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400">Coordinación</label>
          <select
            value={filterCoord}
            onChange={(e) => {
              setFilterCoord(e.target.value);
              setPage(1);
            }}
            className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-1.5 text-xs text-slate-800 transition focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          >
            <option value="">Todas</option>
            {coordinaciones.map((c) => (
              <option key={c.id} value={c.id}>
                {c.codigo} - {c.nombre}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400">Especialidad</label>
          <select
            value={filterEsp}
            disabled={!filterCoord}
            onChange={(e) => {
              setFilterEsp(e.target.value);
              setPage(1);
            }}
            className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-1.5 text-xs text-slate-800 transition focus:border-emerald-600 focus:outline-none disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          >
            <option value="">Todas</option>
            {especialidades.map((esp) => (
              <option key={esp.id} value={esp.id}>
                {esp.codigo} - {esp.nombre}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400">Estado</label>
          <select
            value={filterEstado}
            onChange={(e) => {
              setFilterEstado(e.target.value);
              setPage(1);
            }}
            className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-1.5 text-xs text-slate-800 transition focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          >
            <option value="">Todos</option>
            <option value="ACTIVO">ACTIVO</option>
            <option value="INACTIVO">INACTIVO</option>
          </select>
        </div>
      </div>

      {/* Unassigned Processes Banner */}
      {procesosSinAsignar.length > 0 && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/70 p-4 dark:border-amber-900/50 dark:bg-amber-950/20">
          <div className="flex items-center gap-2 mb-3">
            <span className="flex h-2.5 w-2.5 rounded-full bg-amber-500 animate-pulse" />
            <h3 className="font-semibold text-amber-900 dark:text-amber-200 text-xs">
              Procesos Curriculares Pendientes de Asignación ({procesosSinAsignar.length})
            </h3>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {procesosSinAsignar.map((proc) => {
              const label = proc.programa_codigo
                ? `${proc.programa_codigo} - ${proc.programa_nombre || ""}`
                : `Ref: ${proc.referencia_id.slice(0, 8)}...`;
              return (
                <div
                  key={proc.id}
                  className="flex flex-col justify-between rounded-xl border border-amber-200 bg-white p-3.5 shadow-sm dark:border-amber-900 dark:bg-slate-900"
                >
                  <div>
                    <div className="flex items-start justify-between gap-1">
                      <div className="text-[10px] font-mono text-slate-500 truncate" title={label}>
                        {proc.programa_codigo ? `Prog: ${proc.programa_codigo}` : `Ref: ${proc.referencia_id.slice(0, 8)}...`}
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setProcessActionError(null);
                          setProcessAction({
                            type: "delete",
                            referenciaId: proc.referencia_id,
                            label,
                          });
                        }}
                        className="rounded p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition shrink-0"
                        title="Eliminar proceso curricular definitivamente"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                    <div className="text-xs font-semibold text-slate-800 dark:text-slate-200 mt-1 truncate" title={proc.programa_nombre || proc.tipo_necesidad}>
                      {proc.programa_nombre || proc.tipo_necesidad}
                    </div>
                    {proc.proyecto_nombre && (
                      <div className="text-[10px] text-slate-500 truncate mt-0.5" title={proc.proyecto_nombre}>
                        Proj: {proc.proyecto_codigo ? `[${proc.proyecto_codigo}] ` : ""}{proc.proyecto_nombre}
                      </div>
                    )}
                  </div>
                  <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800">
                    <label className="block text-[10px] font-medium text-slate-500 mb-1">
                      Asignar a Equipo Activo:
                    </label>
                    <select
                      onChange={(e) => {
                        if (e.target.value) handleAssignProcess(proc.referencia_id, e.target.value);
                      }}
                      defaultValue=""
                      className="w-full rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                    >
                      <option value="" disabled>Seleccionar equipo...</option>
                      {equipos
                        .filter((eq) => eq.estado === "ACTIVO")
                        .map((eq) => (
                          <option key={eq.id} value={eq.id}>
                            {eq.nombre} ({eq.lider ? `${eq.lider.nombre} ${eq.lider.apellido}` : "Sin líder"})
                          </option>
                        ))}
                    </select>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Loading indicator */}
      {loading && equipos.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center text-xs font-semibold text-slate-500 dark:border-slate-800 dark:bg-slate-900">
          <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent mb-2" />
          <p>Cargando estructura de equipos ejecutores...</p>
        </div>
      ) : null}

      {/* Empty State */}
      {!loading && equipos.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900">
          No se encontraron equipos ejecutores con los criterios seleccionados.
        </div>
      ) : null}

      {/* Equipos Grid */}
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {equipos.map((equipo) => {
          const isActivo = equipo.estado === "ACTIVO";
          const miembros = equipo.miembros || [];
          return (
            <div
              key={equipo.id}
              className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md dark:border-slate-800 dark:bg-slate-900"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-bold text-slate-900 dark:text-white text-sm">{equipo.nombre}</h3>
                    <div className="mt-1 flex flex-wrap gap-1 text-[10px]">
                      {equipo.coordinacion && (
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                          {equipo.coordinacion.codigo}
                        </span>
                      )}
                      {equipo.especialidad && (
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                          {equipo.especialidad.codigo}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold ${
                        isActivo
                          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                          : "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                      }`}
                    >
                      {equipo.estado}
                    </span>
                    <button
                      onClick={() => handleOpenEdit(equipo)}
                      className="rounded-lg p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                      title="Editar equipo o cambiar líder"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={() => {
                        setTeamDeleteError(null);
                        setTeamToDelete(equipo);
                      }}
                      className="rounded-lg p-1 text-slate-400 transition hover:bg-rose-100 hover:text-rose-700 dark:hover:bg-rose-950/60 dark:hover:text-rose-300"
                      title="Eliminar equipo ejecutor"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>

                {/* Leader block */}
                <div className="mt-3.5 rounded-xl border border-slate-100 bg-slate-50/70 p-3 dark:border-slate-800 dark:bg-slate-800/40">
                  <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    <span>Líder Responsable</span>
                    {equipo.lider && (
                      <span className="rounded bg-emerald-100 px-1 text-[9px] font-bold text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                        LÍDER
                      </span>
                    )}
                  </div>
                  <div className="text-xs font-semibold text-slate-800 dark:text-slate-100 mt-1">
                    {equipo.lider ? `${equipo.lider.nombre} ${equipo.lider.apellido}` : "Sin líder asignado"}
                  </div>
                  <div className="text-[11px] text-slate-500">{equipo.lider?.email}</div>
                </div>

                {/* Support Members */}
                <div className="mt-4">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-600 dark:text-slate-400">
                    <span>Miembros de Apoyo ({miembros.length})</span>
                    <button
                      onClick={() => setSelectedEquipoForMember(equipo)}
                      className="text-xs font-semibold text-emerald-600 hover:text-emerald-700 dark:text-emerald-400"
                    >
                      + Agregar
                    </button>
                  </div>
                  <div className="mt-2 space-y-1.5 max-h-36 overflow-y-auto pr-1">
                    {miembros.length === 0 ? (
                      <div className="text-[11px] text-slate-400 italic">No hay miembros de apoyo vinculados</div>
                    ) : (
                      miembros.map((m) => (
                        <div
                          key={m.id}
                          className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 px-2.5 py-1.5 text-xs dark:border-slate-800 dark:bg-slate-800/40"
                        >
                          <div>
                            <div className="text-xs font-medium text-slate-700 dark:text-slate-300">
                              {m.usuario?.nombre} {m.usuario?.apellido}
                            </div>
                            <div className="text-[10px] text-slate-400">{m.usuario?.email}</div>
                          </div>
                          <button
                            onClick={() => handleToggleMember(equipo.id, m.usuario_id, m.activo)}
                            className={`rounded px-1.5 py-0.5 text-[10px] font-bold transition ${
                              m.activo
                                ? "bg-emerald-100 text-emerald-700 hover:bg-rose-100 hover:text-rose-700"
                                : "bg-slate-200 text-slate-600 hover:bg-emerald-100 hover:text-emerald-700"
                            }`}
                          >
                            {m.activo ? "Activo" : "Inactivo"}
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Assigned Curricular Processes */}
                <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-600 dark:text-slate-400">
                    <span className="flex items-center gap-1.5">
                      <Layers className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                      Procesos Curriculares Asignados ({(equipo.procesos || []).length})
                    </span>
                  </div>
                  <div className="mt-2 space-y-2 max-h-48 overflow-y-auto pr-1">
                    {(equipo.procesos || []).length === 0 ? (
                      <div className="text-[11px] text-slate-400 italic">
                        No hay procesos curriculares asignados a este equipo
                      </div>
                    ) : (
                      (equipo.procesos || []).map((proc) => {
                        const progTitle = proc.programa_codigo
                          ? `${proc.programa_codigo} - ${proc.programa_nombre || ""}`
                          : `Ref: ${proc.referencia_id.slice(0, 8)}...`;
                        return (
                          <div
                            key={proc.id}
                            className="rounded-lg border border-slate-100 bg-slate-50/80 p-2.5 text-xs transition dark:border-slate-800 dark:bg-slate-800/40"
                          >
                            <div className="flex items-start justify-between gap-1.5">
                              <div className="min-w-0 flex-1">
                                <div className="font-semibold text-slate-800 dark:text-slate-200 truncate" title={progTitle}>
                                  {progTitle}
                                </div>
                                {proc.proyecto_nombre && (
                                  <div className="text-[10px] text-slate-500 truncate mt-0.5" title={proc.proyecto_nombre}>
                                    Proj: {proc.proyecto_codigo ? `[${proc.proyecto_codigo}] ` : ""}{proc.proyecto_nombre}
                                  </div>
                                )}
                                <div className="mt-1 flex items-center gap-1 text-[9px] text-slate-400 font-mono">
                                  <span>{proc.tipo_necesidad}</span>
                                  <span>•</span>
                                  <span className="text-emerald-600 font-semibold dark:text-emerald-400">{proc.estado_scope}</span>
                                </div>
                              </div>
                              <div className="flex items-center gap-1 shrink-0 pt-0.5">
                                <button
                                  type="button"
                                  onClick={() => {
                                    setProcessActionError(null);
                                    setProcessAction({
                                      type: "unassign",
                                      referenciaId: proc.referencia_id,
                                      label: progTitle,
                                    });
                                  }}
                                  className="rounded px-2 py-1 text-[10px] font-semibold text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-900/60 transition"
                                  title="Desasignar proceso del equipo (volver a pendientes)"
                                >
                                  Desasignar
                                </button>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setProcessActionError(null);
                                    setProcessAction({
                                      type: "delete",
                                      referenciaId: proc.referencia_id,
                                      label: progTitle,
                                    });
                                  }}
                                  className="rounded p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 dark:hover:text-rose-300 transition"
                                  title="Eliminar proceso curricular definitivamente"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
                              </div>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 text-[10px] text-slate-400 dark:border-slate-800">
                ID: {equipo.id}
              </div>
            </div>
          );
        })}
      </div>

      {/* Pagination Footer */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-slate-200 bg-white px-4 py-3 rounded-2xl shadow-sm sm:px-6 dark:border-slate-800 dark:bg-slate-900">
          <div className="text-xs text-slate-600 dark:text-slate-400">
            Total <span className="font-semibold">{totalCount}</span> equipos (Página {page} de {totalPages})
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Anterior
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}

      {/* Create / Edit Team Modal */}
      <TeamFormDialog
        open={showTeamModal}
        team={editingTeam}
        coordinaciones={coordinaciones}
        onClose={() => setShowTeamModal(false)}
        onSuccess={() => {
          loadTeams();
        }}
      />

      {/* Modal: Add Member */}
      {selectedEquipoForMember && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                Vincular Miembro de Apoyo
              </h3>
              <button
                type="button"
                onClick={() => setSelectedEquipoForMember(null)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
              >
                ✕
              </button>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Asigna un <span className="font-semibold text-slate-700 dark:text-slate-300">USUARIO_ADICIONAL</span> al equipo{" "}
              <span className="font-bold text-emerald-600">{selectedEquipoForMember.nombre}</span>.
            </p>

            {memberError && (
              <div className="mt-3 rounded-lg bg-rose-50 p-2.5 text-xs text-rose-700 dark:bg-rose-950/50">
                {memberError}
              </div>
            )}

            <div className="mt-4 space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Usuario de Apoyo Disponible
                </label>
                <select
                  value={selectedMemberUserId}
                  onChange={(e) => setSelectedMemberUserId(e.target.value)}
                  className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                >
                  <option value="" disabled>Seleccione usuario adicional...</option>
                  {usuariosApoyo.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.nombre} {u.apellido} ({u.email})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setSelectedEquipoForMember(null)}
                  className="rounded-xl px-4 py-2 font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  disabled={!selectedMemberUserId}
                  onClick={handleAddMember}
                  className="rounded-xl bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                >
                  Vincular al Equipo
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Delete Team Confirmation */}
      {teamToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center gap-3 text-rose-600 dark:text-rose-400">
              <div className="rounded-xl bg-rose-100 p-2.5 dark:bg-rose-950/60">
                <AlertTriangle className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Eliminar Equipo Ejecutor
                </h3>
                <p className="text-xs text-slate-500">
                  Equipo: <span className="font-semibold text-slate-800 dark:text-slate-200">{teamToDelete.nombre}</span>
                </p>
              </div>
            </div>

            {teamDeleteError && (
              <div className="mt-4 rounded-xl bg-rose-50 p-3 text-xs text-rose-700 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-900">
                {teamDeleteError}
              </div>
            )}

            <div className="mt-4 text-xs text-slate-600 dark:text-slate-300 space-y-2">
              {(teamToDelete.procesos || []).length > 0 ? (
                <div className="rounded-xl bg-amber-50 p-3 border border-amber-200 text-amber-900 dark:bg-amber-950/30 dark:border-amber-900 dark:text-amber-200">
                  <p className="font-semibold">
                    Advertencia: Este equipo tiene {(teamToDelete.procesos || []).length} proceso(s) curricular(es) asignado(s).
                  </p>
                  <p className="mt-1 text-[11px] text-amber-800 dark:text-amber-300">
                    Al confirmar, todos los procesos asignados quedarán liberados en estado &quot;SIN ASIGNAR&quot; para poder ser asignados a otros equipos.
                  </p>
                </div>
              ) : (
                <p>
                  ¿Está seguro de que desea eliminar este equipo ejecutor? Esta acción eliminará el equipo y sus vinculaciones de miembros de apoyo. No se puede deshacer.
                </p>
              )}
            </div>

            <div className="mt-6 flex justify-end gap-2 border-t border-slate-100 pt-3 dark:border-slate-800">
              <button
                type="button"
                disabled={deletingTeamLoading}
                onClick={() => setTeamToDelete(null)}
                className="rounded-xl px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={deletingTeamLoading}
                onClick={() => handleConfirmDeleteTeam((teamToDelete.procesos || []).length > 0)}
                className="rounded-xl bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-50 transition"
              >
                {deletingTeamLoading
                  ? "Eliminando..."
                  : (teamToDelete.procesos || []).length > 0
                  ? "Desasignar procesos y Eliminar Equipo"
                  : "Eliminar Equipo"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Process Action Confirmation (Unassign or Delete) */}
      {processAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center gap-3">
              <div
                className={`rounded-xl p-2.5 ${
                  processAction.type === "unassign"
                    ? "bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300"
                    : "bg-rose-100 text-rose-600 dark:bg-rose-950/60 dark:text-rose-400"
                }`}
              >
                {processAction.type === "unassign" ? (
                  <Unlink className="h-6 w-6" />
                ) : (
                  <Trash2 className="h-6 w-6" />
                )}
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  {processAction.type === "unassign"
                    ? "Desasignar Proceso Curricular"
                    : "Eliminar Proceso Curricular"}
                </h3>
                <p className="text-xs text-slate-500 font-mono truncate max-w-xs">
                  {processAction.label || `Ref: ${processAction.referenciaId.slice(0, 8)}...`}
                </p>
              </div>
            </div>

            {processActionError && (
              <div className="mt-4 rounded-xl bg-rose-50 p-3 text-xs text-rose-700 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-900">
                {processActionError}
              </div>
            )}

            <div className="mt-4 text-xs text-slate-600 dark:text-slate-300">
              {processAction.type === "unassign" ? (
                <p>
                  ¿Desea desvincular este proceso curricular del equipo ejecutor? El proceso volverá al estado{" "}
                  <strong className="text-amber-700 dark:text-amber-300">SIN ASIGNAR</strong> y quedará disponible para ser asignado a otro equipo.
                </p>
              ) : (
                <p>
                  ¿Está seguro de que desea <strong className="text-rose-600">eliminar permanentemente</strong> este proceso curricular? Se eliminarán los registros del programa, proyecto, planeaciones y archivos asociados. Esta acción no se puede deshacer.
                </p>
              )}
            </div>

            <div className="mt-6 flex justify-end gap-2 border-t border-slate-100 pt-3 dark:border-slate-800">
              <button
                type="button"
                disabled={processActionLoading}
                onClick={() => setProcessAction(null)}
                className="rounded-xl px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={processActionLoading}
                onClick={handleConfirmProcessAction}
                className={`rounded-xl px-4 py-2 text-xs font-semibold text-white transition disabled:opacity-50 ${
                  processAction.type === "unassign"
                    ? "bg-amber-600 hover:bg-amber-700"
                    : "bg-rose-600 hover:bg-rose-700"
                }`}
              >
                {processActionLoading
                  ? "Procesando..."
                  : processAction.type === "unassign"
                  ? "Desasignar de Equipo"
                  : "Eliminar Proceso"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
