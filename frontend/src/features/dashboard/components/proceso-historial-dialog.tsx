"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  X,
  Clock,
  History,
  User,
  CheckCircle2,
  Calendar,
  Building2,
  BookOpen,
  Layers,
  Send,
  RefreshCw,
  FileText,
  ShieldCheck,
  Tag,
} from "lucide-react";
import { authFetch, getApiBaseUrl } from "@/lib/api";
import { notify } from "@/components/feedback/notifications";

export interface CambioActor {
  id: string | null;
  nombre: string | null;
  apellido: string | null;
  email: string | null;
  rol: string | null;
}

export interface CambioProcesoItem {
  id: string;
  fecha_evento: string;
  accion: string;
  tipo_evento: string;
  descripcion: string;
  actor: CambioActor | null;
  entidad: string;
  entidad_id: string | null;
  detalle: Record<string, unknown> | null;
}

export interface ProcesoHistorialData {
  proceso_id: string;
  referencia_id: string;
  estado_scope: string;
  tipo_necesidad: string;
  equipo: {
    id: string;
    nombre: string;
    coordinacion_nombre?: string | null;
    especialidad_nombre?: string | null;
    lider?: {
      id: string;
      nombre: string;
      email: string;
    } | null;
  } | null;
  programa: {
    id: string;
    codigo: string;
    nombre: string;
    version: string;
    modalidad: string;
    estado: string;
  } | null;
  proyecto: {
    id: string;
    codigo_sofia: string;
    nombre: string;
    fases_count: number;
    actividades_count: number;
    estado: string;
  } | null;
  planeaciones: {
    total: number;
    completas: number;
    en_borrador: number;
  };
  fecha_creacion: string;
  fecha_ultima_modificacion: string;
  total_cambios: number;
  cambios: CambioProcesoItem[];
  garantia_unicidad: boolean;
  mensaje_unicidad: string;
}

interface ProcesoHistorialDialogProps {
  referenciaId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export function ProcesoHistorialDialog({
  referenciaId,
  isOpen,
  onClose,
}: ProcesoHistorialDialogProps): React.JSX.Element | null {
  const [data, setData] = useState<ProcesoHistorialData | null>(null);
  const [loading, setLoading] = useState(false);
  const [nuevaObservacion, setNuevaObservacion] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState<"cronologia" | "resumen">("cronologia");

  const loadHistorial = useCallback(async () => {
    if (!referenciaId) return;
    setLoading(true);
    try {
      const res = await authFetch(`${getApiBaseUrl()}/procesos/${referenciaId}/historial`);
      if (!res.ok) {
        throw new Error("No se pudo obtener el historial del proceso curricular.");
      }
      const json = await res.json();
      setData(json);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error al cargar historial";
      notify.error("Error al cargar historial", { description: msg });
    } finally {
      setLoading(false);
    }
  }, [referenciaId]);

  useEffect(() => {
    if (isOpen && referenciaId) {
      void loadHistorial();
    } else {
      setData(null);
      setNuevaObservacion("");
    }
  }, [isOpen, referenciaId, loadHistorial]);

  const handleRegistrarCambio = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!referenciaId || !nuevaObservacion.trim()) return;

    setIsSubmitting(true);
    try {
      const res = await authFetch(`${getApiBaseUrl()}/procesos/${referenciaId}/cambios`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          accion: "PROCESO_CAMBIO_REGISTRADO",
          descripcion: nuevaObservacion.trim(),
        }),
      });
      if (!res.ok) {
        throw new Error("No se pudo registrar el cambio en el proceso.");
      }
      notify.success("Cambio registrado", {
        description: "La observación se registró exitosamente sobre este mismo proceso.",
      });
      setNuevaObservacion("");
      await loadHistorial();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error al registrar cambio";
      notify.error("Error al registrar cambio", { description: msg });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen || !referenciaId) return null;

  const formatDate = (isoString?: string | null) => {
    if (!isoString) return "—";
    try {
      const d = new Date(isoString);
      return new Intl.DateTimeFormat("es-CO", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(d);
    } catch {
      return isoString;
    }
  };

  const getBadgeStyle = (tipo: string) => {
    switch (tipo) {
      case "CREACION":
        return "bg-blue-100 text-blue-800 dark:bg-blue-950/80 dark:text-blue-300 border-blue-200 dark:border-blue-800";
      case "PROGRAMA":
        return "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800";
      case "PROYECTO":
        return "bg-purple-100 text-purple-800 dark:bg-purple-950/80 dark:text-purple-300 border-purple-200 dark:border-purple-800";
      case "PLANEACION":
        return "bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300 border-amber-200 dark:border-amber-800";
      case "CAMBIO_REGISTRADO":
        return "bg-indigo-100 text-indigo-800 dark:bg-indigo-950/80 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800";
      case "EQUIPO":
        return "bg-pink-100 text-pink-800 dark:bg-pink-950/80 dark:text-pink-300 border-pink-200 dark:border-pink-800";
      default:
        return "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700";
    }
  };

  const formatRoleName = (role?: string | null) => {
    if (!role) return "Usuario del Proceso";
    const r = role.toUpperCase();
    if (r.includes("LIDER")) return "Líder Equipo Ejecutor";
    if (r.includes("ADICIONAL") || r.includes("APOYO")) return "Usuario Adicional";
    if (r.includes("SUPERADMIN")) return "Superadministrador";
    if (r.includes("ADMIN")) return "Administrador";
    return role;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-900/60 p-4 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative flex max-h-[90vh] w-full max-w-3xl flex-col rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-900">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-200 p-5 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-950/50 rounded-t-2xl">
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                <ShieldCheck className="h-3.5 w-3.5" />
                Instancia Única Consolidada
              </span>
              <span className="text-xs text-slate-500 font-mono">
                {referenciaId.slice(0, 8)}...
              </span>
            </div>
            <h3 className="mt-1.5 text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <History className="h-5 w-5 text-[var(--accent)]" />
              Historial de Cambios del Proceso Curricular
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Registro trazable de cambios y modificaciones sobre este mismo proceso sin duplicación de instancias.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl p-1.5 text-slate-400 hover:bg-slate-200 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tabs & Refresh */}
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-2.5 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setActiveTab("cronologia")}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                activeTab === "cronologia"
                  ? "bg-[var(--accent)] text-white shadow-sm"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              }`}
            >
              Línea de Tiempo ({data?.total_cambios ?? 0})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("resumen")}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                activeTab === "resumen"
                  ? "bg-[var(--accent)] text-white shadow-sm"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              }`}
            >
              Estado Integral del Proceso
            </button>
          </div>
          <button
            type="button"
            onClick={() => void loadHistorial()}
            disabled={loading}
            className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 disabled:opacity-50"
            title="Refrescar historial"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Actualizar
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {loading && !data ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400">
              <RefreshCw className="h-8 w-8 animate-spin text-[var(--accent)]" />
              <p className="mt-2 text-xs font-medium">Cargando trazabilidad del proceso...</p>
            </div>
          ) : data ? (
            activeTab === "cronologia" ? (
              <div className="space-y-6">
                {/* Form to append a change to this same process */}
                <form
                  onSubmit={handleRegistrarCambio}
                  className="rounded-xl border border-indigo-100 bg-indigo-50/40 p-4 dark:border-indigo-950/60 dark:bg-indigo-950/20"
                >
                  <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-900 dark:text-indigo-300">
                    <Tag className="h-3.5 w-3.5" />
                    Registrar Observación / Cambio sobre este Proceso
                  </div>
                  <div className="mt-2">
                    <textarea
                      value={nuevaObservacion}
                      onChange={(e) => setNuevaObservacion(e.target.value)}
                      placeholder="Escribe un cambio curricular, ajuste pedagógico o nota operativa sobre este proceso..."
                      rows={2}
                      className="w-full rounded-lg border border-indigo-200 bg-white p-2.5 text-xs text-slate-800 shadow-sm placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-indigo-900 dark:bg-slate-900 dark:text-slate-200"
                    />
                  </div>
                  <div className="mt-2 flex justify-end">
                    <button
                      type="submit"
                      disabled={isSubmitting || !nuevaObservacion.trim()}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {isSubmitting ? (
                        <>
                          <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                          Guardando...
                        </>
                      ) : (
                        <>
                          <Send className="h-3.5 w-3.5" />
                          Registrar en el Proceso
                        </>
                      )}
                    </button>
                  </div>
                </form>

                {/* Timeline List */}
                <div className="relative pl-6 before:absolute before:bottom-2 before:left-[11px] before:top-2 before:w-[2px] before:bg-slate-200 dark:before:bg-slate-800 space-y-4">
                  {data.cambios.length === 0 ? (
                    <div className="py-6 text-center text-xs text-slate-400">
                      No hay eventos registrados aún para este proceso.
                    </div>
                  ) : (
                    data.cambios.map((c) => (
                      <div key={c.id} className="relative group">
                        {/* Dot */}
                        <div className="absolute -left-[19px] top-1.5 h-3.5 w-3.5 rounded-full border-2 border-white bg-[var(--accent)] shadow-sm dark:border-slate-900" />

                        {/* Card */}
                        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span
                              className={`rounded-md border px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider ${getBadgeStyle(
                                c.tipo_evento,
                              )}`}
                            >
                              {c.tipo_evento.replace("_", " ")}
                            </span>
                            <span className="flex items-center gap-1 text-[11px] font-medium text-slate-400">
                              <Calendar className="h-3 w-3" />
                              {formatDate(c.fecha_evento)}
                            </span>
                          </div>

                          <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-white">
                            {c.descripcion}
                          </p>

                          {/* Detail metadata if present */}
                          {c.detalle && Object.keys(c.detalle).length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-1.5 text-[11px]">
                              {c.detalle.competencias !== undefined && (
                                <span className="rounded bg-emerald-50 px-2 py-0.5 font-medium text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300">
                                  {String(c.detalle.competencias)} competencias
                                </span>
                              )}
                              {c.detalle.resultados !== undefined && (
                                <span className="rounded bg-blue-50 px-2 py-0.5 font-medium text-blue-700 dark:bg-blue-950/60 dark:text-blue-300">
                                  {String(c.detalle.resultados)} RAPs
                                </span>
                              )}
                              {c.detalle.fases !== undefined && (
                                <span className="rounded bg-purple-50 px-2 py-0.5 font-medium text-purple-700 dark:bg-purple-950/60 dark:text-purple-300">
                                  {String(c.detalle.fases)} fases
                                </span>
                              )}
                              {c.detalle.actividades !== undefined && (
                                <span className="rounded bg-indigo-50 px-2 py-0.5 font-medium text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300">
                                  {String(c.detalle.actividades)} actividades
                                </span>
                              )}
                              {c.detalle.resultados_count !== undefined && (
                                <span className="rounded bg-blue-50 px-2 py-0.5 font-medium text-blue-700 dark:bg-blue-950/60 dark:text-blue-300">
                                  {String(c.detalle.resultados_count)} RAPs
                                </span>
                              )}
                              {c.detalle.conocimientos_count !== undefined && Number(c.detalle.conocimientos_count) > 0 && (
                                <span className="rounded bg-emerald-50 px-2 py-0.5 font-medium text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300">
                                  {String(c.detalle.conocimientos_count)} saberes
                                </span>
                              )}
                              {c.detalle.criterios_count !== undefined && Number(c.detalle.criterios_count) > 0 && (
                                <span className="rounded bg-amber-50 px-2 py-0.5 font-medium text-amber-700 dark:bg-amber-950/60 dark:text-amber-300">
                                  {String(c.detalle.criterios_count)} criterios
                                </span>
                              )}
                              {c.detalle.planeaciones_incluidas !== undefined && (
                                <span className="rounded bg-teal-50 px-2 py-0.5 font-medium text-teal-700 dark:bg-teal-950/60 dark:text-teal-300">
                                  {String(c.detalle.planeaciones_incluidas)} planeaciones consolidadas
                                </span>
                              )}
                              {c.detalle.file_name !== undefined && (
                                <span className="rounded bg-slate-100 px-2 py-0.5 font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                                  {String(c.detalle.file_name)}
                                </span>
                              )}
                            </div>
                          )}

                          {/* Actor / Responsable badge */}
                          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-100 bg-slate-50/90 px-3 py-2 text-xs dark:border-slate-800 dark:bg-slate-800/40">
                            <div className="flex items-center gap-2">
                              <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-800 font-bold text-xs shadow-xs dark:bg-emerald-950 dark:text-emerald-300">
                                {c.actor?.nombre ? c.actor.nombre.charAt(0).toUpperCase() : "U"}
                              </span>
                              <div>
                                <div className="font-semibold text-slate-800 dark:text-slate-200">
                                  {c.actor?.nombre || "Usuario del Proceso"}
                                </div>
                                {c.actor?.email && (
                                  <div className="text-[11px] text-slate-500 dark:text-slate-400">
                                    {c.actor.email}
                                  </div>
                                )}
                              </div>
                            </div>
                            <span className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-semibold text-slate-700 shadow-xs dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                              <ShieldCheck className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                              {formatRoleName(c.actor?.rol)}
                            </span>
                          </div>

                          {/* Footer with action metadata */}
                          <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400">
                            <span className="font-mono">Acción: {c.accion}</span>
                            {c.entidad && <span>Entidad: {c.entidad}</span>}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Process Summary Grid */}
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 dark:border-slate-800 dark:bg-slate-800/40">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      Equipo Ejecutor
                    </span>
                    <h5 className="mt-1 font-semibold text-slate-900 dark:text-white">
                      {data.equipo?.nombre || "Sin equipo asignado"}
                    </h5>
                    <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                      {[data.equipo?.coordinacion_nombre, data.equipo?.especialidad_nombre]
                        .filter(Boolean)
                        .join(" • ")}
                    </p>
                    {data.equipo?.lider && (
                      <p className="mt-2 text-xs text-slate-600 dark:text-slate-300 font-medium">
                        Líder: {data.equipo.lider.nombre} ({data.equipo.lider.email})
                      </p>
                    )}
                  </div>

                  <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 dark:border-slate-800 dark:bg-slate-800/40">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      Programa de Formación
                    </span>
                    <h5 className="mt-1 font-semibold text-slate-900 dark:text-white">
                      {data.programa ? `${data.programa.codigo} - ${data.programa.nombre}` : "Sin programa vinculado"}
                    </h5>
                    {data.programa && (
                      <div className="mt-2 flex items-center gap-2 text-xs">
                        <span className="rounded bg-emerald-100 px-2 py-0.5 font-semibold text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                          {data.programa.estado}
                        </span>
                        <span className="text-slate-500">
                          Versión {data.programa.version} • {data.programa.modalidad}
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 dark:border-slate-800 dark:bg-slate-800/40">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      Proyecto Formativo
                    </span>
                    <h5 className="mt-1 font-semibold text-slate-900 dark:text-white">
                      {data.proyecto ? `${data.proyecto.codigo_sofia} - ${data.proyecto.nombre}` : "Sin proyecto cargado"}
                    </h5>
                    {data.proyecto && (
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        {data.proyecto.fases_count} fases • {data.proyecto.actividades_count} actividades
                      </p>
                    )}
                  </div>

                  <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 dark:border-slate-800 dark:bg-slate-800/40">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      Planeaciones Pedagógicas (GPFI-F-134 V05)
                    </span>
                    <h5 className="mt-1 font-semibold text-slate-900 dark:text-white">
                      {data.planeaciones.total} planeaciones registradas
                    </h5>
                    <div className="mt-2 flex items-center gap-2 text-xs">
                      <span className="rounded bg-emerald-100 px-2 py-0.5 font-semibold text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                        {data.planeaciones.completas} completas
                      </span>
                      <span className="rounded bg-amber-100 px-2 py-0.5 font-semibold text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
                        {data.planeaciones.en_borrador} en borrador
                      </span>
                    </div>
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-slate-50/40 p-4 dark:border-slate-800 dark:bg-slate-800/20 text-xs text-slate-500 dark:text-slate-400 space-y-1">
                  <div>
                    <strong className="text-slate-700 dark:text-slate-300">Fecha de creación:</strong>{" "}
                    {formatDate(data.fecha_creacion)}
                  </div>
                  <div>
                    <strong className="text-slate-700 dark:text-slate-300">Última modificación:</strong>{" "}
                    {formatDate(data.fecha_ultima_modificacion)}
                  </div>
                  <div>
                    <strong className="text-slate-700 dark:text-slate-300">Garantía de unicidad:</strong>{" "}
                    {data.mensaje_unicidad}
                  </div>
                </div>
              </div>
            )
          ) : null}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-200 p-4 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/50 rounded-b-2xl">
          <span className="text-[11px] font-mono text-slate-400">
            ID Proceso: {data?.proceso_id || "—"}
          </span>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 bg-white px-4 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
