"use client";

import React, { useState } from "react";
import {
  Layers,
  Clock,
  BookOpen,
  MapPin,
  Users,
  Eye,
  Plus,
  RefreshCcw,
  AlertCircle,
  MessageSquare,
  AlertTriangle,
  FolderTree,
} from "lucide-react";
import {
  type PlaneacionesEntregaList,
  type PlaneacionRevisionItem,
} from "@/features/planeacion/planeacion-api";

interface RevisionPlanningTreeProps {
  data: PlaneacionesEntregaList | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  onSelect: (planeacionId: string) => void;
  onAddObservation?: (planeacionId: string, sectionKey?: string) => void;
}

export function RevisionPlanningTree({
  data,
  loading,
  error,
  onRetry,
  onSelect,
  onAddObservation,
}: RevisionPlanningTreeProps): React.JSX.Element {
  const [filterPendingObsOnly, setFilterPendingObsOnly] = useState(false);

  if (loading) {
    return (
      <div className="flex min-h-64 items-center justify-center rounded-2xl border border-slate-200 bg-white p-8 dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center gap-2 text-emerald-600">
          <RefreshCcw className="h-5 w-5 animate-spin" />
          <span className="text-xs font-semibold">Cargando planeaciones pedagógicas de la entrega...</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex min-h-64 flex-col items-center justify-center gap-3 rounded-2xl border border-slate-200 bg-white p-8 text-center dark:border-slate-800 dark:bg-slate-900">
        <AlertCircle className="h-6 w-6 text-rose-600" />
        <p className="text-xs text-slate-600 dark:text-slate-400 max-w-md">
          {error || "No fue posible cargar las planeaciones de la entrega."}
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="rounded-lg bg-emerald-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-800"
        >
          Reintentar
        </button>
      </div>
    );
  }

  const items = data.planeaciones || data.items || [];

  if (items.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center dark:border-slate-800 dark:bg-slate-900">
        <FolderTree className="mx-auto h-8 w-8 text-slate-300 dark:text-slate-600" />
        <h4 className="mt-2 text-sm font-bold text-slate-800 dark:text-slate-200">
          No hay planeaciones incluidas en esta entrega
        </h4>
        <p className="mt-1 text-xs text-slate-500 max-w-sm mx-auto">
          El snapshot de la entrega no contiene planeaciones registradas o validadas.
        </p>
      </div>
    );
  }

  // Calculate totals
  const totalHorasDirectas = items.reduce(
    (acc, it) => acc + (it.horas.directas ?? it.horas.horas_directas ?? 0),
    0,
  );
  const totalHorasIndependientes = items.reduce(
    (acc, it) => acc + (it.horas.independientes ?? it.horas.horas_independientes ?? 0),
    0,
  );
  const totalHoras = totalHorasDirectas + totalHorasIndependientes;

  // Filter items if requested
  const displayedItems = filterPendingObsOnly
    ? items.filter((it) => (it.observaciones_pendientes_count ?? it.observaciones_pendientes ?? 0) > 0)
    : items;

  // Group by Phase and Activity
  const groupedByPhase: Record<
    string,
    {
      fase: PlaneacionRevisionItem["fase"];
      actividades: Record<
        string,
        {
          actividad: PlaneacionRevisionItem["actividad_proyecto"];
          planeaciones: PlaneacionRevisionItem[];
        }
      >;
    }
  > = {};

  for (const item of displayedItems) {
    const faseKey = item.fase.id || item.fase.nombre;
    if (!groupedByPhase[faseKey]) {
      groupedByPhase[faseKey] = {
        fase: item.fase,
        actividades: {},
      };
    }
    const actKey = item.actividad_proyecto.id || item.actividad_proyecto.descripcion;
    if (!groupedByPhase[faseKey].actividades[actKey]) {
      groupedByPhase[faseKey].actividades[actKey] = {
        actividad: item.actividad_proyecto,
        planeaciones: [],
      };
    }
    groupedByPhase[faseKey].actividades[actKey].planeaciones.push(item);
  }

  return (
    <div className="space-y-4">
      {/* Header and Summary stats */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-xs sm:flex-row sm:items-center sm:justify-between dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400">
            <Layers className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
              Estructura Jerárquica de la Entrega
            </h3>
            <p className="text-xs text-slate-500">
              {data.total_planeaciones ?? data.total ?? items.length} planeaciones congeladas en la versión {data.version ?? 1}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600 dark:text-slate-400">
          <div className="rounded-lg bg-slate-50 px-3 py-1.5 dark:bg-slate-800/60">
            Directas: <strong className="text-slate-900 dark:text-white">{totalHorasDirectas}h</strong>
          </div>
          <div className="rounded-lg bg-slate-50 px-3 py-1.5 dark:bg-slate-800/60">
            Independientes: <strong className="text-slate-900 dark:text-white">{totalHorasIndependientes}h</strong>
          </div>
          <div className="rounded-lg bg-emerald-50 px-3 py-1.5 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300">
            Total: <strong>{totalHoras}h</strong>
          </div>

          <label className="flex items-center gap-1.5 cursor-pointer ml-2">
            <input
              type="checkbox"
              checked={filterPendingObsOnly}
              onChange={(e) => setFilterPendingObsOnly(e.target.checked)}
              className="rounded text-emerald-600 focus:ring-emerald-500"
            />
            <span className="text-[11px] font-medium text-slate-700 dark:text-slate-300">
              Solo con observaciones pendientes
            </span>
          </label>
        </div>
      </div>

      {/* Tree Groups */}
      <div className="space-y-4">
        {Object.entries(groupedByPhase).map(([faseKey, { fase, actividades }]) => (
          <div
            key={faseKey}
            className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900"
          >
            {/* Phase Header */}
            <div className="border-b border-slate-200 bg-slate-50/80 px-4 py-3 dark:border-slate-800 dark:bg-slate-800/40">
              <div className="flex items-center gap-2">
                <span className="rounded bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-900 dark:bg-emerald-900/60 dark:text-emerald-200 uppercase">
                  Fase {fase.orden ?? 1}
                </span>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
                  {fase.nombre}
                </h4>
              </div>
            </div>

            {/* Activities in Phase */}
            <div className="p-4 space-y-4">
              {Object.entries(actividades).map(([actKey, { actividad, planeaciones }]) => (
                <div key={actKey} className="space-y-2">
                  <div className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                    <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                      {actividad.orden !== null && actividad.orden !== undefined ? `AP${actividad.orden}:` : "AP:"}
                    </span>
                    <span className="font-medium text-slate-700 dark:text-slate-300">
                      {actividad.descripcion}
                    </span>
                    <span className="text-[11px] text-slate-400">
                      ({planeaciones.length} planeación{planeaciones.length !== 1 ? "es" : ""})
                    </span>
                  </div>

                  {/* Planning Cards */}
                  <div className="grid gap-3 pl-2 sm:pl-4 border-l-2 border-slate-100 dark:border-slate-800">
                    {planeaciones.map((plan) => {
                      const pendingObs = plan.observaciones_pendientes_count ?? plan.observaciones_pendientes ?? 0;
                      const totalObs = plan.observaciones_count ?? plan.total_observaciones ?? 0;
                      const hDirectas = plan.horas.directas ?? plan.horas.horas_directas ?? 0;
                      const hIndep = plan.horas.independientes ?? plan.horas.horas_independientes ?? 0;
                      const hTotal = plan.horas.total ?? plan.horas.horas_totales ?? (hDirectas + hIndep);
                      const ambienteStr = typeof plan.ambiente === "string" ? plan.ambiente : (Array.isArray(plan.ambientes) ? plan.ambientes.join(", ") : (plan.ambientes || null));
                      const instructorStr = typeof plan.instructores === "string" ? plan.instructores : (Array.isArray(plan.instructores) ? plan.instructores.join(", ") : null);

                      return (
                        <article
                          key={plan.id}
                          className="group rounded-xl border border-slate-200 bg-white p-4 shadow-xs transition hover:border-emerald-300 hover:shadow-sm dark:border-slate-800 dark:bg-slate-900/80"
                        >
                          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                            <div className="space-y-1.5 flex-1 min-w-0">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-700 dark:bg-slate-800 dark:text-slate-300 uppercase">
                                  Actividad de Aprendizaje
                                </span>
                                {pendingObs > 0 && (
                                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                                    <AlertTriangle className="h-3 w-3" />
                                    {pendingObs} pendiente{pendingObs !== 1 ? "s" : ""}
                                  </span>
                                )}
                                {totalObs > 0 && pendingObs === 0 && (
                                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
                                    <MessageSquare className="h-3 w-3" />
                                    {totalObs} observacion(es) resuelta(s)
                                  </span>
                                )}
                              </div>

                              <h5 className="text-sm font-bold text-slate-900 dark:text-white line-clamp-2">
                                {plan.actividades_aprendizaje || plan.actividad_aprendizaje || "Sin descripción de actividad"}
                              </h5>

                              {/* Competencies and RAPs summary */}
                              <div className="flex flex-wrap items-center gap-2 pt-1">
                                {plan.competencias.map((comp) => (
                                  <span
                                    key={comp.id}
                                    className="inline-flex items-center gap-1 rounded-md bg-slate-50 border border-slate-200 px-2 py-0.5 text-[11px] text-slate-700 dark:bg-slate-800/80 dark:border-slate-700 dark:text-slate-300"
                                    title={`${comp.codigo} - ${comp.nombre} (${comp.resultados.length} RAPs)`}
                                  >
                                    <BookOpen className="h-3 w-3 text-emerald-600 shrink-0" />
                                    <strong className="font-mono">{comp.codigo}</strong>
                                    <span className="text-[10px] text-slate-400">
                                      ({comp.resultados.length} RAP)
                                    </span>
                                  </span>
                                ))}
                              </div>
                            </div>

                            {/* Action Buttons */}
                            <div className="flex items-center gap-2 shrink-0 sm:self-start">
                              {onAddObservation && (
                                <button
                                  type="button"
                                  onClick={() => onAddObservation(plan.id, "GENERAL")}
                                  className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                                  title="Agregar observación pedagógica sobre esta planeación"
                                >
                                  <Plus className="h-3 w-3" />
                                  Observar
                                </button>
                              )}

                              <button
                                type="button"
                                onClick={() => onSelect(plan.id)}
                                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-700 px-3 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-emerald-800 transition"
                              >
                                <Eye className="h-3.5 w-3.5" />
                                Revisar planeación
                              </button>
                            </div>
                          </div>

                          {/* Card Footer: Hours, Environments, Instructors */}
                          <div className="mt-3 flex flex-wrap items-center gap-4 border-t border-slate-100 pt-3 text-[11px] text-slate-500 dark:border-slate-800 dark:text-slate-400">
                            <div className="flex items-center gap-1">
                              <Clock className="h-3.5 w-3.5 text-slate-400" />
                              <span>
                                Horas: Directas <strong>{hDirectas}h</strong> ·
                                Independientes <strong>{hIndep}h</strong> (Total <strong>{hTotal}h</strong>)
                              </span>
                            </div>

                            {ambienteStr && (
                              <div className="flex items-center gap-1">
                                <MapPin className="h-3.5 w-3.5 text-slate-400" />
                                <span className="truncate max-w-xs">{ambienteStr}</span>
                              </div>
                            )}

                            {instructorStr && (
                              <div className="flex items-center gap-1">
                                <Users className="h-3.5 w-3.5 text-slate-400" />
                                <span className="truncate max-w-xs">{instructorStr}</span>
                              </div>
                            )}
                          </div>
                        </article>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
