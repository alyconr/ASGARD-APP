"use client";

import React, { useEffect, useState, useCallback } from "react";
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
  rol_equipo?: string;
  usuario?: UserSummary;
}

interface ProcesoCurricular {
  id: string;
  referencia_id: string;
  tipo_necesidad: string;
  estado_scope: string;
}

export interface FullEquipoEjecutor extends Omit<EquipoEjecutor, "miembros"> {
  miembros?: Miembro[];
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

  // Add member modal state
  const [selectedEquipoForMember, setSelectedEquipoForMember] = useState<EquipoEjecutor | null>(null);
  const [selectedMemberUserId, setSelectedMemberUserId] = useState("");
  const [selectedMemberRole, setSelectedMemberRole] = useState("COLABORADOR");
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
        body: JSON.stringify({
          usuario_id: selectedMemberUserId,
          rol_equipo: selectedMemberRole,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setMemberError(err.detail || "Error al asociar miembro");
        return;
      }
      setSelectedEquipoForMember(null);
      setSelectedMemberUserId("");
      setSelectedMemberRole("COLABORADOR");
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
            {procesosSinAsignar.map((proc) => (
              <div
                key={proc.id}
                className="flex flex-col justify-between rounded-xl border border-amber-200 bg-white p-3.5 shadow-sm dark:border-amber-900 dark:bg-slate-900"
              >
                <div>
                  <div className="text-[10px] font-mono text-slate-500">Ref: {proc.referencia_id.slice(0, 8)}...</div>
                  <div className="text-xs font-semibold text-slate-800 dark:text-slate-200 mt-1">
                    {proc.tipo_necesidad}
                  </div>
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
            ))}
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
          const activeMembersCount = miembros.filter((m) => m.activo).length + (equipo.lider_id ? 1 : 0);
          const maxCapacity = equipo.max_members || 5;
          const isFull = activeMembersCount >= maxCapacity;

          return (
            <div
              key={equipo.id}
              className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md dark:border-slate-800 dark:bg-slate-900"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-bold text-slate-900 dark:text-white text-sm">{equipo.nombre}</h3>
                    {equipo.descripcion && (
                      <p className="mt-0.5 text-[11px] text-slate-500 line-clamp-2">{equipo.descripcion}</p>
                    )}
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
                    {equipo.programa && (
                      <div className="mt-2 flex items-center gap-1.5 rounded-lg bg-emerald-50 px-2 py-1 text-[11px] font-medium text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300">
                        <span className="font-bold">Programa:</span> {equipo.programa.codigo_programa} - {equipo.programa.nombre_programa} (v{equipo.programa.version_programa || "1"})
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold ${
                        isFull
                          ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                          : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                      }`}
                      title={`Capacidad: ${activeMembersCount} de ${maxCapacity} integrantes`}
                    >
                      {activeMembersCount}/{maxCapacity}
                    </span>
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
                    <span>Miembros ({miembros.length})</span>
                    <button
                      onClick={() => setSelectedEquipoForMember(equipo)}
                      className="text-xs font-semibold text-emerald-600 hover:text-emerald-700 dark:text-emerald-400"
                    >
                      + Agregar
                    </button>
                  </div>
                  <div className="mt-2 space-y-1.5 max-h-36 overflow-y-auto pr-1">
                    {miembros.length === 0 ? (
                      <div className="text-[11px] text-slate-400 italic">No hay miembros vinculados</div>
                    ) : (
                      miembros.map((m) => (
                        <div
                          key={m.id}
                          className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 px-2.5 py-1.5 text-xs dark:border-slate-800 dark:bg-slate-800/40"
                        >
                          <div>
                            <div className="flex items-center gap-1.5">
                              <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                                {m.usuario?.nombre} {m.usuario?.apellido}
                              </span>
                              <span
                                className={`rounded px-1.5 py-0.2 text-[9px] font-bold ${
                                  m.rol_equipo === "CO_LIDER"
                                    ? "bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300"
                                    : m.rol_equipo === "INSTRUCTOR"
                                    ? "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300"
                                    : m.rol_equipo === "TRANSVERSAL"
                                    ? "bg-cyan-100 text-cyan-800 dark:bg-cyan-950 dark:text-cyan-300"
                                    : "bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300"
                                }`}
                              >
                                {m.rol_equipo || "COLABORADOR"}
                              </span>
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
      {selectedEquipoForMember && (() => {
        const currentActive = (selectedEquipoForMember.miembros?.filter((m) => m.activo).length || 0) + (selectedEquipoForMember.lider_id ? 1 : 0);
        const max = selectedEquipoForMember.max_members || 5;
        const isAtCapacity = currentActive >= max;

        return (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Vincular Integrante al Equipo
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
                Asigna un integrante al equipo{" "}
                <span className="font-bold text-emerald-600">{selectedEquipoForMember.nombre}</span>.
              </p>

              {isAtCapacity ? (
                <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-800 dark:border-amber-900/40 dark:bg-amber-950/40 dark:text-amber-300">
                  Capacidad máxima alcanzada ({currentActive}/{max} integrantes activos). Para vincular más usuarios, inactive a otro miembro o incremente el límite del equipo.
                </div>
              ) : (
                <div className="mt-2 text-[11px] text-slate-500">
                  Ocupación del equipo: <span className="font-semibold text-slate-700 dark:text-slate-300">{currentActive} / {max}</span> integrantes.
                </div>
              )}

              {memberError && (
                <div className="mt-3 rounded-lg bg-rose-50 p-2.5 text-xs text-rose-700 dark:bg-rose-950/50">
                  {memberError}
                </div>
              )}

              <div className="mt-4 space-y-4 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Usuario Disponible
                  </label>
                  <select
                    value={selectedMemberUserId}
                    onChange={(e) => setSelectedMemberUserId(e.target.value)}
                    disabled={isAtCapacity}
                    className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                  >
                    <option value="" disabled>Seleccione usuario...</option>
                    {usuariosApoyo.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.nombre} {u.apellido} ({u.email})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Rol en el Equipo
                  </label>
                  <select
                    value={selectedMemberRole}
                    onChange={(e) => setSelectedMemberRole(e.target.value)}
                    disabled={isAtCapacity}
                    className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                  >
                    <option value="COLABORADOR">COLABORADOR - Integrante de apoyo curricular</option>
                    <option value="INSTRUCTOR">INSTRUCTOR - Instructor técnico/específico</option>
                    <option value="TRANSVERSAL">TRANSVERSAL - Instructor transversal / bilingüismo</option>
                    <option value="CO_LIDER">CO_LIDER - Co-líder con permisos de edición y gestión</option>
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
                    disabled={!selectedMemberUserId || isAtCapacity}
                    onClick={handleAddMember}
                    className="rounded-xl bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                  >
                    Vincular al Equipo
                  </button>
                </div>
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
