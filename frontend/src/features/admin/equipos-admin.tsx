"use client";

import React, { useEffect, useState } from "react";
import { authFetch, getApiBaseUrl } from "@/lib/api";

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

interface EquipoEjecutor {
  id: string;
  nombre: string;
  coordinacion_id: string;
  especialidad_id: string;
  lider_id: string;
  estado: string;
  lider?: UserSummary;
  miembros: Miembro[];
}

interface ProcesoCurricular {
  id: string;
  referencia_id: string;
  tipo_necesidad: string;
  estado_scope: string;
}

export function EquiposAdmin(): React.JSX.Element {
  const [equipos, setEquipos] = useState<EquipoEjecutor[]>([]);
  const [coordinaciones, setCoordinaciones] = useState<Coordinacion[]>([]);
  const [especialidades, setEspecialidades] = useState<Especialidad[]>([]);
  const [lideres, setLideres] = useState<UserSummary[]>([]);
  const [usuariosApoyo, setUsuariosApoyo] = useState<UserSummary[]>([]);
  const [procesosSinAsignar, setProcesosSinAsignar] = useState<ProcesoCurricular[]>([]);
  const [loading, setLoading] = useState(true);

  // New team form state
  const [showNewTeamModal, setShowNewTeamModal] = useState(false);
  const [nombreEquipo, setNombreEquipo] = useState("");
  const [selectedCoordId, setSelectedCoordId] = useState("");
  const [selectedEspId, setSelectedEspId] = useState("");
  const [selectedLiderId, setSelectedLiderId] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  // Add member modal state
  const [selectedEquipoForMember, setSelectedEquipoForMember] = useState<EquipoEjecutor | null>(null);
  const [selectedMemberUserId, setSelectedMemberUserId] = useState("");

  const loadData = async () => {
    setLoading(true);
    try {
      const [eqRes, coordRes, sinAsignarRes, usersRes] = await Promise.all([
        authFetch(`${getApiBaseUrl()}/equipos`),
        authFetch(`${getApiBaseUrl()}/coordinaciones`),
        authFetch(`${getApiBaseUrl()}/procesos/sin-asignar`),
        authFetch(`${getApiBaseUrl()}/auth/users`),
      ]);

      if (eqRes.ok) setEquipos(await eqRes.json());
      if (coordRes.ok) setCoordinaciones(await coordRes.json());
      if (sinAsignarRes.ok) setProcesosSinAsignar(await sinAsignarRes.json());

      if (usersRes.ok) {
        const allUsers: UserSummary[] = await usersRes.json();
        setLideres(allUsers.filter((u) => u.roles.includes("LIDER_EQUIPO_EJECUTOR")));
        setUsuariosApoyo(allUsers.filter((u) => u.roles.includes("USUARIO_ADICIONAL")));
      }
    } catch (err) {
      console.error("Error loading equipos data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (!selectedCoordId) {
      setEspecialidades([]);
      setSelectedEspId("");
      return;
    }
    authFetch(`${getApiBaseUrl()}/coordinaciones/${selectedCoordId}/especialidades`)
      .then(async (res) => {
        if (res.ok) setEspecialidades(await res.json());
      })
      .catch(console.error);
  }, [selectedCoordId]);

  const handleCreateTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    try {
      const res = await authFetch(`${getApiBaseUrl()}/equipos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nombre: nombreEquipo,
          coordinacion_id: selectedCoordId,
          especialidad_id: selectedEspId,
          lider_id: selectedLiderId,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Error al crear el equipo");
      }

      setShowNewTeamModal(false);
      setNombreEquipo("");
      setSelectedCoordId("");
      setSelectedEspId("");
      setSelectedLiderId("");
      await loadData();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Error al crear equipo");
    }
  };

  const handleAddMember = async () => {
    if (!selectedEquipoForMember || !selectedMemberUserId) return;
    try {
      const res = await authFetch(`${getApiBaseUrl()}/equipos/${selectedEquipoForMember.id}/miembros`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ usuario_id: selectedMemberUserId }),
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Error al asociar miembro");
        return;
      }
      setSelectedEquipoForMember(null);
      setSelectedMemberUserId("");
      await loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Error al asociar miembro");
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
        await loadData();
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
        await loadData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header and Actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Gestión de Equipos Ejecutores
          </h2>
          <p className="text-sm text-slate-500">
            Administración de equipos, asignación de líderes y miembros adicionales para control estricto de acceso.
          </p>
        </div>
        <button
          onClick={() => setShowNewTeamModal(true)}
          className="inline-flex items-center justify-center rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700"
        >
          + Crear Equipo Ejecutor
        </button>
      </div>

      {loading && equipos.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-center text-sm font-semibold text-slate-500">
          Cargando estructura de equipos ejecutores...
        </div>
      ) : null}

      {/* Procesos Sin Asignar Banner */}
      {procesosSinAsignar.length > 0 && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/70 p-5 dark:border-amber-900/50 dark:bg-amber-950/20">
          <div className="flex items-center gap-2 mb-3">
            <span className="flex h-3 w-3 rounded-full bg-amber-500 animate-pulse" />
            <h3 className="font-semibold text-amber-900 dark:text-amber-200 text-sm">
              Procesos Curriculares Pendientes de Asignación ({procesosSinAsignar.length})
            </h3>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {procesosSinAsignar.map((proc) => (
              <div
                key={proc.id}
                className="flex flex-col justify-between rounded-xl border border-amber-200 bg-white p-4 shadow-sm dark:border-amber-900 dark:bg-slate-900"
              >
                <div>
                  <div className="text-xs font-mono text-slate-500">Ref: {proc.referencia_id.slice(0, 8)}...</div>
                  <div className="text-sm font-semibold text-slate-800 dark:text-slate-200 mt-1">
                    {proc.tipo_necesidad}
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
                  <label className="block text-[11px] font-medium text-slate-500 mb-1">
                    Asignar a Equipo:
                  </label>
                  <select
                    onChange={(e) => {
                      if (e.target.value) handleAssignProcess(proc.referencia_id, e.target.value);
                    }}
                    defaultValue=""
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                  >
                    <option value="" disabled>Seleccionar equipo...</option>
                    {equipos.map((eq) => (
                      <option key={eq.id} value={eq.id}>
                        {eq.nombre} ({eq.lider?.nombre} {eq.lider?.apellido})
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Equipos List */}
      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
        {equipos.map((equipo) => (
          <div
            key={equipo.id}
            className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
          >
            <div>
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-slate-900 dark:text-white text-base">{equipo.nombre}</h3>
                <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                  {equipo.estado}
                </span>
              </div>

              {/* Lider info */}
              <div className="mt-4 rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Líder Asignado</div>
                <div className="text-sm font-semibold text-slate-800 dark:text-slate-100 mt-0.5">
                  {equipo.lider ? `${equipo.lider.nombre} ${equipo.lider.apellido}` : "Sin líder"}
                </div>
                <div className="text-xs text-slate-500">{equipo.lider?.email}</div>
              </div>

              {/* Members */}
              <div className="mt-4">
                <div className="flex items-center justify-between text-xs font-bold text-slate-600 dark:text-slate-400">
                  <span>Miembros de Apoyo ({equipo.miembros.length})</span>
                  <button
                    onClick={() => setSelectedEquipoForMember(equipo)}
                    className="text-emerald-600 hover:text-emerald-700 font-semibold"
                  >
                    + Agregar
                  </button>
                </div>
                <div className="mt-2 space-y-1.5 max-h-36 overflow-y-auto pr-1">
                  {equipo.miembros.length === 0 ? (
                    <div className="text-xs text-slate-400 italic">No hay miembros adicionales</div>
                  ) : (
                    equipo.miembros.map((m) => (
                      <div
                        key={m.id}
                        className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 px-2.5 py-1.5 text-xs dark:border-slate-800 dark:bg-slate-800/40"
                      >
                        <div>
                          <div className="font-medium text-slate-700 dark:text-slate-300">
                            {m.usuario?.nombre} {m.usuario?.apellido}
                          </div>
                          <div className="text-[10px] text-slate-400">{m.usuario?.email}</div>
                        </div>
                        <button
                          onClick={() => handleToggleMember(equipo.id, m.usuario_id, m.activo)}
                          className={`rounded px-1.5 py-0.5 text-[10px] font-semibold transition ${
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
          </div>
        ))}
      </div>

      {/* Modal: New Team */}
      {showNewTeamModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Crear Nuevo Equipo Ejecutor</h3>
            <p className="text-xs text-slate-500 mb-4">
              Configura el equipo ejecutor y selecciona su líder curricular.
            </p>

            {formError && (
              <div className="mb-4 rounded-lg bg-rose-50 p-3 text-xs text-rose-700 dark:bg-rose-950/50">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateTeam} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Nombre del Equipo
                </label>
                <input
                  type="text"
                  required
                  value={nombreEquipo}
                  onChange={(e) => setNombreEquipo(e.target.value)}
                  placeholder="ej. Equipo Redes 01 Mañana"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Coordinación Académica
                </label>
                <select
                  required
                  value={selectedCoordId}
                  onChange={(e) => setSelectedCoordId(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                >
                  <option value="" disabled>Seleccione coordinación...</option>
                  {coordinaciones.map((c) => (
                    <option key={c.id} value={c.id}>{c.nombre}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Especialidad
                </label>
                <select
                  required
                  disabled={!selectedCoordId || especialidades.length === 0}
                  value={selectedEspId}
                  onChange={(e) => setSelectedEspId(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                >
                  <option value="" disabled>Seleccione especialidad...</option>
                  {especialidades.map((esp) => (
                    <option key={esp.id} value={esp.id}>{esp.nombre}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Líder de Equipo Ejecutor
                </label>
                <select
                  required
                  value={selectedLiderId}
                  onChange={(e) => setSelectedLiderId(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                >
                  <option value="" disabled>Seleccione líder...</option>
                  {lideres.map((l) => (
                    <option key={l.id} value={l.id}>{l.nombre} {l.apellido} ({l.email})</option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setShowNewTeamModal(false)}
                  className="rounded-lg px-4 py-2 font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-700"
                >
                  Guardar Equipo
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Add Member */}
      {selectedEquipoForMember && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              Agregar Miembro de Apoyo
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Equipo: <span className="font-semibold text-emerald-600">{selectedEquipoForMember.nombre}</span>
            </p>

            <div className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Usuario Adicional
                </label>
                <select
                  value={selectedMemberUserId}
                  onChange={(e) => setSelectedMemberUserId(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                >
                  <option value="" disabled>Seleccionar usuario...</option>
                  {usuariosApoyo.map((u) => (
                    <option key={u.id} value={u.id}>{u.nombre} {u.apellido} ({u.email})</option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedEquipoForMember(null)}
                  className="rounded-lg px-4 py-2 font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  disabled={!selectedMemberUserId}
                  onClick={handleAddMember}
                  className="rounded-lg bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                >
                  Vincular al Equipo
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
