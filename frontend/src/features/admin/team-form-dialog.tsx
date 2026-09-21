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
  coordinacion_id?: string | null;
  especialidad_id?: string | null;
  estado?: string;
}

export interface MiembroSummary {
  id: string;
  equipo_id: string;
  usuario_id: string;
  activo: boolean;
  usuario?: UserSummary;
}

export interface EquipoEjecutor {
  id: string;
  nombre: string;
  coordinacion_id: string;
  especialidad_id: string;
  lider_id: string;
  estado: string;
  coordinacion?: Coordinacion;
  especialidad?: Especialidad;
  lider?: UserSummary;
  miembros?: MiembroSummary[];
}

interface TeamFormDialogProps {
  open: boolean;
  team: EquipoEjecutor | null;
  coordinaciones: Coordinacion[];
  onClose: () => void;
  onSuccess: () => void;
}

export function TeamFormDialog({
  open,
  team,
  coordinaciones,
  onClose,
  onSuccess,
}: TeamFormDialogProps): React.JSX.Element | null {
  const isEditing = Boolean(team);
  const [nombre, setNombre] = useState("");
  const [coordinacionId, setCoordinacionId] = useState("");
  const [especialidadId, setEspecialidadId] = useState("");
  const [liderId, setLiderId] = useState("");
  const [estado, setEstado] = useState("ACTIVO");

  const [especialidades, setEspecialidades] = useState<Especialidad[]>([]);
  const [lideres, setLideres] = useState<UserSummary[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [loadingEspecialidades, setLoadingEspecialidades] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch all potential leaders
  useEffect(() => {
    if (!open) return;
    setLoadingUsers(true);
    authFetch(`${getApiBaseUrl()}/auth/users?role=LIDER_EQUIPO_EJECUTOR&page_size=100`)
      .then(async (res) => {
        if (res.ok) {
          const data = await res.json();
          // Endpoint might return PaginatedUsersResponse or list
          const users: UserSummary[] = Array.isArray(data) ? data : data.items || [];
          setLideres(users.filter((u) => !u.estado || u.estado === "ACTIVO"));
        }
      })
      .catch((err) => console.error("Error loading leaders:", err))
      .finally(() => setLoadingUsers(false));
  }, [open]);

  // Sync state with selected team
  useEffect(() => {
    if (team) {
      setNombre(team.nombre);
      setCoordinacionId(team.coordinacion_id);
      setEspecialidadId(team.especialidad_id);
      setLiderId(team.lider_id);
      setEstado(team.estado || "ACTIVO");
    } else {
      setNombre("");
      setCoordinacionId("");
      setEspecialidadId("");
      setLiderId("");
      setEstado("ACTIVO");
      setEspecialidades([]);
    }
    setError(null);
  }, [team, open]);

  // Load specialties when coordination changes
  useEffect(() => {
    if (!coordinacionId) {
      setEspecialidades([]);
      if (!isEditing) setEspecialidadId("");
      return;
    }

    setLoadingEspecialidades(true);
    authFetch(`${getApiBaseUrl()}/coordinaciones/${coordinacionId}/especialidades?solo_activas=true`)
      .then(async (res) => {
        if (res.ok) {
          const data: Especialidad[] = await res.json();
          setEspecialidades(data);
        }
      })
      .catch((err) => console.error("Error loading specialties:", err))
      .finally(() => setLoadingEspecialidades(false));
  }, [coordinacionId, isEditing]);

  if (!open) return null;

  // Filter leaders compatible with the coordination/specialty if configured
  const filteredLideres = lideres.filter((l) => {
    if (l.id === team?.lider_id) return true; // keep current leader
    if (coordinacionId && l.coordinacion_id && l.coordinacion_id !== coordinacionId) {
      return false;
    }
    if (especialidadId && l.especialidad_id && l.especialidad_id !== especialidadId) {
      return false;
    }
    return true;
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (isEditing && team) {
        const payload: Record<string, unknown> = {
          nombre: nombre.trim(),
          lider_id: liderId,
          estado,
        };

        const res = await authFetch(`${getApiBaseUrl()}/equipos/${team.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "Error al actualizar el equipo ejecutor");
        }
      } else {
        const payload = {
          nombre: nombre.trim(),
          coordinacion_id: coordinacionId,
          especialidad_id: especialidadId,
          lider_id: liderId,
        };

        const res = await authFetch(`${getApiBaseUrl()}/equipos`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "Error al crear el equipo ejecutor");
        }
      }

      onSuccess();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error inesperado al guardar equipo");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
          <div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
              {isEditing ? "Editar Equipo Ejecutor" : "Nuevo Equipo Ejecutor"}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {isEditing
                ? "Actualiza nombre, líder asignado o estado operativo del equipo."
                : "Registra un nuevo equipo ejecutor vinculado a coordinación y especialidad."}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          >
            ✕
          </button>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-300">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300">
              Nombre del Equipo <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              minLength={3}
              maxLength={150}
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="ej. Equipo ADSO 2026 - Mañana"
              className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-900 transition focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300">
                Coordinación <span className="text-rose-500">*</span>
              </label>
              <select
                required
                disabled={isEditing}
                value={coordinacionId}
                onChange={(e) => {
                  setCoordinacionId(e.target.value);
                  setEspecialidadId("");
                }}
                className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-900 transition focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              >
                <option value="" disabled>
                  Seleccione coordinación...
                </option>
                {coordinaciones.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.codigo} - {c.nombre}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300">
                Especialidad <span className="text-rose-500">*</span>
              </label>
              <select
                required
                disabled={isEditing || !coordinacionId || loadingEspecialidades}
                value={especialidadId}
                onChange={(e) => setEspecialidadId(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-900 transition focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              >
                <option value="" disabled>
                  {loadingEspecialidades
                    ? "Cargando especialidades..."
                    : !coordinacionId
                    ? "Seleccione coordinación primero"
                    : "Seleccione especialidad..."}
                </option>
                {especialidades.map((esp) => (
                  <option key={esp.id} value={esp.id}>
                    {esp.codigo} - {esp.nombre}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <label className="block font-semibold text-slate-700 dark:text-slate-300">
                Líder de Equipo Ejecutor <span className="text-rose-500">*</span>
              </label>
              {isEditing && (
                <span className="text-[11px] text-amber-600 dark:text-amber-400">
                  Nota: Al cambiar líder se reasignan los procesos del equipo
                </span>
              )}
            </div>
            <select
              required
              disabled={loadingUsers}
              value={liderId}
              onChange={(e) => setLiderId(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-900 transition focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            >
              <option value="" disabled>
                {loadingUsers ? "Cargando líderes disponibles..." : "Seleccione líder..."}
              </option>
              {filteredLideres.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.nombre} {l.apellido} ({l.email})
                </option>
              ))}
            </select>
          </div>

          {isEditing && (
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300">
                Estado Operativo
              </label>
              <select
                value={estado}
                onChange={(e) => setEstado(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-900 transition focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              >
                <option value="ACTIVO">ACTIVO - Puede recibir procesos y operar</option>
                <option value="INACTIVO">INACTIVO - Bloqueado para nuevos procesos</option>
              </select>
            </div>
          )}

          <div className="flex justify-end gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="rounded-xl px-4 py-2.5 font-semibold text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  Guardando...
                </>
              ) : isEditing ? (
                "Actualizar Equipo"
              ) : (
                "Crear Equipo"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
