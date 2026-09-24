"use client";

import React, { useEffect, useState } from "react";
import { authFetch, getApiBaseUrl } from "@/lib/api";
import { SpecialtyFormDialog } from "./specialty-form-dialog";

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

export interface ProcesoCurricularSummary {
  id: string;
  referencia_id: string;
  coordinacion_id?: string | null;
  especialidad_id?: string | null;
  equipo_ejecutor_id?: string | null;
  lider_id?: string | null;
  tipo_necesidad: string;
  estado_scope: string;
  programa_id?: string | null;
  proyecto_id?: string | null;
  programa_nombre?: string | null;
  programa_codigo?: string | null;
  proyecto_nombre?: string | null;
  proyecto_codigo?: string | null;
}

export interface ProgramaAutorizadoSummary {
  id?: string;
  equipo_id?: string;
  programa_id?: string | null;
  codigo_programa: string;
  nombre_programa: string;
  activo?: boolean;
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
  procesos?: ProcesoCurricularSummary[];
  programas_autorizados?: ProgramaAutorizadoSummary[];
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

  const [programasAutorizados, setProgramasAutorizados] = useState<ProgramaAutorizadoSummary[]>([]);
  const [catalogoProgramas, setCatalogoProgramas] = useState<Array<{ id: string; codigo_programa: string; nombre_programa: string }>>([]);
  const [selectedCatalogoId, setSelectedCatalogoId] = useState("");
  const [nuevoCodigo, setNuevoCodigo] = useState("");
  const [nuevoNombre, setNuevoNombre] = useState("");

  const [especialidades, setEspecialidades] = useState<Especialidad[]>([]);
  const [showNewEspModal, setShowNewEspModal] = useState(false);
  const [lideres, setLideres] = useState<UserSummary[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [loadingEspecialidades, setLoadingEspecialidades] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadEspecialidades = async (cId: string) => {
    setLoadingEspecialidades(true);
    try {
      const res = await authFetch(`${getApiBaseUrl()}/coordinaciones/${cId}/especialidades?solo_activas=true`);
      if (res.ok) {
        const data: Especialidad[] = await res.json();
        setEspecialidades(data);
        return data;
      }
    } catch (err) {
      console.error("Error loading specialties:", err);
    } finally {
      setLoadingEspecialidades(false);
    }
    return [];
  };

  // Fetch all potential leaders and catalog of programs
  useEffect(() => {
    if (!open) return;
    setLoadingUsers(true);
    authFetch(`${getApiBaseUrl()}/auth/users?role=LIDER_EQUIPO_EJECUTOR&page_size=100`)
      .then(async (res) => {
        if (res.ok) {
          const data = await res.json();
          const users: UserSummary[] = Array.isArray(data) ? data : data.items || [];
          setLideres(users.filter((u) => !u.estado || u.estado === "ACTIVO"));
        }
      })
      .catch((err) => console.error("Error loading leaders:", err))
      .finally(() => setLoadingUsers(false));

    authFetch(`${getApiBaseUrl()}/programas-formacion/catalogo`)
      .then(async (res) => {
        if (res.ok) {
          const data = await res.json();
          setCatalogoProgramas(Array.isArray(data) ? data : []);
        }
      })
      .catch((err) => console.error("Error loading programs catalog:", err));
  }, [open]);

  // Sync state with selected team
  useEffect(() => {
    if (team) {
      setNombre(team.nombre);
      setCoordinacionId(team.coordinacion_id);
      setEspecialidadId(team.especialidad_id);
      setLiderId(team.lider_id);
      setEstado(team.estado || "ACTIVO");
      setProgramasAutorizados(team.programas_autorizados || []);
    } else {
      setNombre("");
      setCoordinacionId("");
      setEspecialidadId("");
      setLiderId("");
      setEstado("ACTIVO");
      setEspecialidades([]);
      setProgramasAutorizados([]);
    }
    setError(null);
  }, [team, open]);

  const handleAddFromCatalog = () => {
    if (!selectedCatalogoId) return;
    const prog = catalogoProgramas.find((p) => p.id === selectedCatalogoId);
    if (!prog) return;
    const exists = programasAutorizados.some(
      (p) => p.codigo_programa.trim().toUpperCase() === prog.codigo_programa.trim().toUpperCase()
    );
    if (exists) return;
    setProgramasAutorizados((prev) => [
      ...prev,
      {
        programa_id: prog.id,
        codigo_programa: prog.codigo_programa,
        nombre_programa: prog.nombre_programa,
        activo: true,
      },
    ]);
    setSelectedCatalogoId("");
  };

  const handleAddManual = () => {
    const c = nuevoCodigo.trim().toUpperCase();
    const n = nuevoNombre.trim();
    if (!c || !n) return;
    const exists = programasAutorizados.some(
      (p) => p.codigo_programa.trim().toUpperCase() === c
    );
    if (exists) return;
    setProgramasAutorizados((prev) => [
      ...prev,
      {
        codigo_programa: c,
        nombre_programa: n,
        activo: true,
      },
    ]);
    setNuevoCodigo("");
    setNuevoNombre("");
  };

  const handleRemovePrograma = (codigo: string) => {
    setProgramasAutorizados((prev) =>
      prev.filter((p) => p.codigo_programa.trim().toUpperCase() !== codigo.trim().toUpperCase())
    );
  };

  // Load specialties when coordination changes
  useEffect(() => {
    if (!coordinacionId) {
      setEspecialidades([]);
      if (!isEditing) setEspecialidadId("");
      return;
    }

    loadEspecialidades(coordinacionId);
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
      const mappedProgramas = programasAutorizados.map((p) => ({
        codigo_programa: p.codigo_programa.trim(),
        nombre_programa: p.nombre_programa.trim(),
        programa_id: p.programa_id || undefined,
        activo: true,
      }));

      if (isEditing && team) {
        const payload: Record<string, unknown> = {
          nombre: nombre.trim(),
          lider_id: liderId,
          estado,
          programas: mappedProgramas,
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
          programas: mappedProgramas,
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
              <div className="flex items-center justify-between">
                <label className="block font-semibold text-slate-700 dark:text-slate-300">
                  Especialidad <span className="text-rose-500">*</span>
                </label>
                {!isEditing && coordinacionId && (
                  <button
                    type="button"
                    onClick={() => setShowNewEspModal(true)}
                    className="text-[11px] font-semibold text-emerald-600 hover:text-emerald-700 dark:text-emerald-400 hover:underline"
                  >
                    + Nueva especialidad
                  </button>
                )}
              </div>
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
          {/* Programas Autorizados para el Equipo */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3.5 dark:border-slate-700/60 dark:bg-slate-800/40">
            <div className="flex items-center justify-between">
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300">
                  Programas de Formación Habilitados
                </label>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  Solo los programas aquí autorizados podrán ser iniciados por los miembros de este equipo.
                </p>
              </div>
              <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                {programasAutorizados.length} {programasAutorizados.length === 1 ? "programa" : "programas"}
              </span>
            </div>

            {/* List of current authorized programs */}
            {programasAutorizados.length > 0 ? (
              <div className="mt-2.5 flex flex-wrap gap-2">
                {programasAutorizados.map((p) => (
                  <span
                    key={p.codigo_programa}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-800 shadow-sm dark:border-emerald-800/60 dark:bg-slate-900 dark:text-slate-200"
                  >
                    <span className="font-bold text-emerald-700 dark:text-emerald-400">
                      {p.codigo_programa}
                    </span>
                    <span className="max-w-[180px] truncate">{p.nombre_programa}</span>
                    <button
                      type="button"
                      onClick={() => handleRemovePrograma(p.codigo_programa)}
                      className="ml-1 rounded text-slate-400 hover:text-rose-600 dark:hover:text-rose-400"
                      title="Quitar programa"
                    >
                      ✕
                    </button>
                  </span>
                ))}
              </div>
            ) : (
              <p className="mt-2 text-[11px] italic text-amber-700 dark:text-amber-400">
                Sin programas autorizados específicos (equipo sin restricción curricular o pendiente de asignar).
              </p>
            )}

            {/* Selector from catalog */}
            {catalogoProgramas.length > 0 && (
              <div className="mt-3 flex items-center gap-2">
                <select
                  value={selectedCatalogoId}
                  onChange={(e) => setSelectedCatalogoId(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                >
                  <option value="">Seleccionar del catálogo existente...</option>
                  {catalogoProgramas.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.codigo_programa} - {cat.nombre_programa}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={handleAddFromCatalog}
                  disabled={!selectedCatalogoId}
                  className="shrink-0 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-50"
                >
                  + Agregar
                </button>
              </div>
            )}

            {/* Manual input */}
            <div className="mt-2.5 grid grid-cols-[1fr_2fr_auto] gap-2">
              <input
                type="text"
                value={nuevoCodigo}
                onChange={(e) => setNuevoCodigo(e.target.value)}
                placeholder="Código (ej. 228118)"
                className="rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />
              <input
                type="text"
                value={nuevoNombre}
                onChange={(e) => setNuevoNombre(e.target.value)}
                placeholder="Nombre del programa"
                className="rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />
              <button
                type="button"
                onClick={handleAddManual}
                disabled={!nuevoCodigo.trim() || !nuevoNombre.trim()}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              >
                Añadir
              </button>
            </div>
          </div>

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

      {showNewEspModal && coordinacionId && (
        <SpecialtyFormDialog
          isOpen={showNewEspModal}
          onClose={() => setShowNewEspModal(false)}
          onSuccess={async (newEsp) => {
            await loadEspecialidades(coordinacionId);
            if (newEsp?.id) {
              setEspecialidadId(newEsp.id);
            }
          }}
          coordinacionId={coordinacionId}
          coordinacionNombre={coordinaciones.find((c) => c.id === coordinacionId)?.nombre}
        />
      )}
    </div>
  );
}
