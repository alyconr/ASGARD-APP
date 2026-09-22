"use client";

import React, { useEffect, useState } from "react";
import { Plus, Edit2, Power, Trash2, AlertCircle, ChevronRight } from "lucide-react";
import { authFetch, getApiBaseUrl } from "@/lib/api";
import { useAuth } from "@/features/auth/auth-context";
import { CoordinationFormDialog } from "./coordination-form-dialog";
import { SpecialtyFormDialog } from "./specialty-form-dialog";

interface Coordinacion {
  id: string;
  codigo: string;
  nombre: string;
  descripcion?: string | null;
  activo: boolean;
}

interface Especialidad {
  id: string;
  coordinacion_id: string;
  codigo: string;
  nombre: string;
  activo: boolean;
}

export function OrganizationAdmin(): React.JSX.Element {
  const { hasRole } = useAuth();
  const canDelete = hasRole("SUPERADMIN", "ADMIN");

  const [coordinaciones, setCoordinaciones] = useState<Coordinacion[]>([]);
  const [selectedCoord, setSelectedCoord] = useState<Coordinacion | null>(null);
  const [especialidades, setEspecialidades] = useState<Especialidad[]>([]);
  const [loadingCoords, setLoadingCoords] = useState(true);
  const [loadingEsps, setLoadingEsps] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Modals
  const [showCoordModal, setShowCoordModal] = useState(false);
  const [coordToEdit, setCoordToEdit] = useState<Coordinacion | null>(null);
  const [showEspModal, setShowEspModal] = useState(false);
  const [espToEdit, setEspToEdit] = useState<Especialidad | null>(null);

  const loadCoordinaciones = async () => {
    setLoadingCoords(true);
    setActionError(null);
    try {
      const res = await authFetch(`${getApiBaseUrl()}/coordinaciones`);
      if (res.ok) {
        const data: Coordinacion[] = await res.json();
        setCoordinaciones(data);
        if (data.length > 0) {
          if (!selectedCoord || !data.some((c) => c.id === selectedCoord.id)) {
            setSelectedCoord(data[0]);
          } else {
            const updated = data.find((c) => c.id === selectedCoord.id);
            if (updated) setSelectedCoord(updated);
          }
        } else {
          setSelectedCoord(null);
        }
      }
    } catch (err) {
      console.error("Error loading coordinaciones:", err);
    } finally {
      setLoadingCoords(false);
    }
  };

  const loadEspecialidades = async (coordId: string) => {
    setLoadingEsps(true);
    setActionError(null);
    try {
      const res = await authFetch(`${getApiBaseUrl()}/coordinaciones/${coordId}/especialidades`);
      if (res.ok) {
        const data: Especialidad[] = await res.json();
        setEspecialidades(data);
      }
    } catch (err) {
      console.error("Error loading especialidades:", err);
    } finally {
      setLoadingEsps(false);
    }
  };

  useEffect(() => {
    loadCoordinaciones();
  }, []);

  useEffect(() => {
    if (selectedCoord) {
      loadEspecialidades(selectedCoord.id);
    } else {
      setEspecialidades([]);
    }
  }, [selectedCoord?.id]);

  const handleToggleCoordStatus = async (coord: Coordinacion) => {
    setActionError(null);
    try {
      const res = await authFetch(`${getApiBaseUrl()}/coordinaciones/${coord.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ activo: !coord.activo }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Error al cambiar estado" }));
        throw new Error(err.detail || "Error al actualizar estado");
      }

      await loadCoordinaciones();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Error al procesar solicitud");
    }
  };

  const handleToggleEspStatus = async (esp: Especialidad) => {
    setActionError(null);
    try {
      const res = await authFetch(`${getApiBaseUrl()}/especialidades/${esp.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ activo: !esp.activo }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Error al cambiar estado" }));
        throw new Error(err.detail || "Error al actualizar estado");
      }

      if (selectedCoord) {
        await loadEspecialidades(selectedCoord.id);
      }
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Error al procesar solicitud");
    }
  };

  const handleDeleteCoord = async (coord: Coordinacion) => {
    setActionError(null);
    const confirmed = window.confirm(
      `¿Está seguro de eliminar permanentemente la coordinación "${coord.nombre}" (${coord.codigo})?\n\nEsta acción no se puede deshacer.`
    );
    if (!confirmed) return;

    try {
      const res = await authFetch(`${getApiBaseUrl()}/coordinaciones/${coord.id}`, {
        method: "DELETE",
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Error al eliminar coordinación" }));
        throw new Error(err.detail || "Error al eliminar coordinación");
      }

      if (selectedCoord?.id === coord.id) {
        setSelectedCoord(null);
        setEspecialidades([]);
      }
      await loadCoordinaciones();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Error al procesar eliminación");
    }
  };

  const handleDeleteEsp = async (esp: Especialidad) => {
    setActionError(null);
    const confirmed = window.confirm(
      `¿Está seguro de eliminar permanentemente la especialidad "${esp.nombre}" (${esp.codigo})?\n\nEsta acción no se puede deshacer.`
    );
    if (!confirmed) return;

    try {
      const res = await authFetch(`${getApiBaseUrl()}/especialidades/${esp.id}`, {
        method: "DELETE",
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Error al eliminar especialidad" }));
        throw new Error(err.detail || "Error al eliminar especialidad");
      }

      if (selectedCoord) {
        await loadEspecialidades(selectedCoord.id);
      }
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Error al procesar eliminación");
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Estructura Organizacional SENA</h2>
          <p className="text-xs text-slate-500">
            Catálogo canónico de Coordinaciones y Especialidades para asignación curricular y equipos
          </p>
        </div>

        <button
          type="button"
          onClick={() => {
            setCoordToEdit(null);
            setShowCoordModal(true);
          }}
          className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 transition"
        >
          <Plus className="h-4 w-4" />
          Nueva Coordinación
        </button>
      </div>

      {actionError && (
        <div className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs font-semibold text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-300">
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
          <span>{actionError}</span>
        </div>
      )}

      {/* Dual pane */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        {/* Coordinaciones list */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 lg:col-span-5">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
            <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">
              Coordinaciones ({coordinaciones.length})
            </h3>
          </div>

          <div className="mt-3 space-y-2">
            {loadingCoords ? (
              <div className="py-8 text-center text-xs text-slate-500">Cargando catálogo...</div>
            ) : coordinaciones.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500">No hay coordinaciones registradas.</div>
            ) : (
              coordinaciones.map((coord) => {
                const isSelected = selectedCoord?.id === coord.id;
                return (
                  <div
                    key={coord.id}
                    onClick={() => setSelectedCoord(coord)}
                    className={`flex items-center justify-between rounded-xl border p-3 cursor-pointer transition ${
                      isSelected
                        ? "border-emerald-600 bg-emerald-50/60 shadow-sm dark:border-emerald-500 dark:bg-emerald-950/30"
                        : "border-slate-200 hover:border-slate-300 hover:bg-slate-50/50 dark:border-slate-800 dark:hover:bg-slate-800/40"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-xs font-bold ${
                          coord.activo
                            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300"
                            : "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
                        }`}
                      >
                        {coord.codigo}
                      </span>
                      <div>
                        <div className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                          {coord.nombre}
                          {!coord.activo && (
                            <span className="rounded bg-slate-100 px-1.5 py-0.2 text-[10px] font-semibold text-slate-500 dark:bg-slate-800">
                              Inactiva
                            </span>
                          )}
                        </div>
                        {coord.descripcion && (
                          <div className="text-[11px] text-slate-500 line-clamp-1">{coord.descripcion}</div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        onClick={() => {
                          setCoordToEdit(coord);
                          setShowCoordModal(true);
                        }}
                        title="Editar coordinación"
                        className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800"
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                      </button>

                      <button
                        type="button"
                        onClick={() => handleToggleCoordStatus(coord)}
                        title={coord.activo ? "Desactivar coordinación" : "Activar coordinación"}
                        className={`rounded-lg p-1.5 transition ${
                          coord.activo
                            ? "text-emerald-600 hover:bg-emerald-100/50 dark:hover:bg-emerald-950/40"
                            : "text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                        }`}
                      >
                        <Power className="h-3.5 w-3.5" />
                      </button>

                      {canDelete && (
                        <button
                          type="button"
                          onClick={() => handleDeleteCoord(coord)}
                          title="Eliminar coordinación"
                          className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/40 dark:hover:text-rose-400 transition"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}

                      <ChevronRight
                        className={`h-4 w-4 ml-1 transition ${
                          isSelected ? "text-emerald-600 font-bold" : "text-slate-300 dark:text-slate-600"
                        }`}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Especialidades list for selected coordination */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 lg:col-span-7">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
            <div>
              <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">
                Especialidades de {selectedCoord ? selectedCoord.nombre : "Coordinación"}
              </h3>
              <p className="text-xs text-slate-500">
                {selectedCoord ? `Código institucional: ${selectedCoord.codigo}` : "Seleccione una coordinación"}
              </p>
            </div>

            {selectedCoord && (
              <button
                type="button"
                onClick={() => {
                  setEspToEdit(null);
                  setShowEspModal(true);
                }}
                className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-600 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-50 dark:border-emerald-500 dark:text-emerald-400 dark:hover:bg-emerald-950/30 transition"
              >
                <Plus className="h-3.5 w-3.5" />
                Nueva Especialidad
              </button>
            )}
          </div>

          <div className="mt-3 space-y-2">
            {!selectedCoord ? (
              <div className="py-12 text-center text-xs text-slate-400">
                Seleccione una coordinación a la izquierda para administrar sus especialidades académicas.
              </div>
            ) : loadingEsps ? (
              <div className="py-8 text-center text-xs text-slate-500">Cargando especialidades...</div>
            ) : especialidades.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500">
                No hay especialidades configuradas en esta coordinación.
              </div>
            ) : (
              especialidades.map((esp) => (
                <div
                  key={esp.id}
                  className="flex items-center justify-between rounded-xl border border-slate-200 p-3 hover:bg-slate-50/50 dark:border-slate-800 dark:hover:bg-slate-800/40 transition"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`inline-flex px-2 py-1 rounded-md text-xs font-mono font-bold ${
                        esp.activo
                          ? "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200"
                          : "bg-slate-100 text-slate-400 dark:bg-slate-800/50 dark:text-slate-500"
                      }`}
                    >
                      {esp.codigo}
                    </span>
                    <div>
                      <div className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                        {esp.nombre}
                        {!esp.activo && (
                          <span className="rounded bg-rose-50 px-1.5 py-0.2 text-[10px] font-semibold text-rose-600 dark:bg-rose-950/40 dark:text-rose-400">
                            Inactiva
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => {
                        setEspToEdit(esp);
                        setShowEspModal(true);
                      }}
                      title="Editar especialidad"
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800"
                    >
                      <Edit2 className="h-3.5 w-3.5" />
                    </button>

                    <button
                      type="button"
                      onClick={() => handleToggleEspStatus(esp)}
                      title={esp.activo ? "Desactivar especialidad" : "Activar especialidad"}
                      className={`rounded-lg p-1.5 transition ${
                        esp.activo
                          ? "text-emerald-600 hover:bg-emerald-100/50 dark:hover:bg-emerald-950/40"
                          : "text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                      }`}
                    >
                      <Power className="h-3.5 w-3.5" />
                    </button>

                    {canDelete && (
                      <button
                        type="button"
                        onClick={() => handleDeleteEsp(esp)}
                        title="Eliminar especialidad"
                        className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/40 dark:hover:text-rose-400 transition"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Coordination Dialog */}
      <CoordinationFormDialog
        isOpen={showCoordModal}
        onClose={() => setShowCoordModal(false)}
        onSuccess={loadCoordinaciones}
        coordinationToEdit={coordToEdit}
      />

      {/* Specialty Dialog */}
      {selectedCoord && (
        <SpecialtyFormDialog
          isOpen={showEspModal}
          onClose={() => setShowEspModal(false)}
          onSuccess={() => loadEspecialidades(selectedCoord.id)}
          coordinacionId={selectedCoord.id}
          coordinacionNombre={selectedCoord.nombre}
          specialtyToEdit={espToEdit}
        />
      )}
    </div>
  );
}
