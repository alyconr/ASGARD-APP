"use client";

import React, { useState } from "react";
import {
  ArrowLeft,
  AlertTriangle,
  Plus,
  RefreshCcw,
  AlertCircle,
  Check,
  BookOpen,
} from "lucide-react";
import {
  type PlaneacionRevisionDetalle,
  type ObservacionRevision,
  type SeccionObservacionPlaneacion,
} from "@/features/planeacion/planeacion-api";
import { LockStatusBadge } from "@/features/planeacion/components/edit-requests-components";
import { cn } from "@/lib/utils";

interface RevisionPlanningViewerProps {
  detail: PlaneacionRevisionDetalle | null;
  loading: boolean;
  error: string | null;
  onBack: () => void;
  onRetry: () => void;
  onAddObservation: (section: SeccionObservacionPlaneacion) => void;
  onResolverObservacion?: (observacionId: string) => Promise<void>;
}

export function RevisionPlanningViewer({
  detail,
  loading,
  error,
  onBack,
  onRetry,
  onAddObservation,
  onResolverObservacion,
}: RevisionPlanningViewerProps): React.JSX.Element {
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const handleResolve = async (obsId: string) => {
    if (!onResolverObservacion) return;
    setResolvingId(obsId);
    try {
      await onResolverObservacion(obsId);
    } finally {
      setResolvingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-80 items-center justify-center rounded-2xl border border-slate-200 bg-white p-8 dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center gap-2 text-emerald-600">
          <RefreshCcw className="h-5 w-5 animate-spin" />
          <span className="text-xs font-semibold">Cargando desglose curricular de la planeación...</span>
        </div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="flex min-h-80 flex-col items-center justify-center gap-3 rounded-2xl border border-slate-200 bg-white p-8 text-center dark:border-slate-800 dark:bg-slate-900">
        <AlertCircle className="h-6 w-6 text-rose-600" />
        <p className="text-xs text-slate-600 dark:text-slate-400 max-w-md">
          {error || "No fue posible cargar la planeación pedagógica solicitada."}
        </p>
        <div className="flex items-center gap-2 mt-2">
          <button
            type="button"
            onClick={onBack}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300"
          >
            Volver
          </button>
          <button
            type="button"
            onClick={onRetry}
            className="rounded-lg bg-emerald-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-800"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  // Group observations by normalized section_key
  const observationsBySection: Record<string, ObservacionRevision[]> = {};
  for (const obs of detail.observaciones || []) {
    const key = (obs.section_key || "GENERAL").toUpperCase().trim();
    if (!observationsBySection[key]) {
      observationsBySection[key] = [];
    }
    observationsBySection[key].push(obs);
  }

  const renderSectionHeader = (
    title: string,
    sectionKey: SeccionObservacionPlaneacion,
    badgeText?: string,
  ) => {
    const obsList = observationsBySection[sectionKey] || [];
    const pendingCount = obsList.filter((o) => o.estado === "PENDIENTE").length;

    return (
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
            {title}
          </h3>
          {badgeText && (
            <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              {badgeText}
            </span>
          )}
          {pendingCount > 0 && (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-800 dark:bg-amber-950 dark:text-amber-300">
              <AlertTriangle className="h-2.5 w-2.5" />
              {pendingCount} obs. pendiente{pendingCount !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={() => onAddObservation(sectionKey)}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 transition"
          title={`Agregar observación sobre ${title}`}
        >
          <Plus className="h-3 w-3" />
          Observar sección
        </button>
      </div>
    );
  };

  const renderSectionObservations = (sectionKey: string) => {
    const obsList = observationsBySection[sectionKey] || [];
    if (obsList.length === 0) return null;

    return (
      <div className="mt-3 space-y-2 border-t border-slate-100 pt-3 dark:border-slate-800">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
          Observaciones en esta sección:
        </span>
        <div className="grid gap-2">
          {obsList.map((obs) => (
            <div
              key={obs.id}
              className={cn(
                "rounded-lg border p-3 text-xs transition",
                obs.estado === "RESUELTO"
                  ? "border-emerald-200 bg-emerald-50/50 dark:border-emerald-900/40 dark:bg-emerald-950/20"
                  : obs.estado === "AJUSTE_REPORTADO"
                  ? "border-sky-200 bg-sky-50/50 dark:border-sky-900/40 dark:bg-sky-950/20"
                  : "border-amber-200 bg-amber-50/60 dark:border-amber-900/40 dark:bg-amber-950/20",
              )}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "rounded-full px-2 py-0.5 text-[10px] font-bold uppercase",
                      obs.estado === "RESUELTO"
                        ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300"
                        : obs.estado === "AJUSTE_REPORTADO"
                        ? "bg-sky-100 text-sky-800 dark:bg-sky-900/60 dark:text-sky-300"
                        : "bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-300",
                    )}
                  >
                    {obs.estado}
                  </span>
                  <span className="text-[11px] text-slate-500">
                    {new Date(obs.fecha_creacion).toLocaleString("es-CO")} por {obs.creado_por_nombre}
                  </span>
                </div>

                {obs.estado !== "RESUELTO" && onResolverObservacion && (
                  <button
                    type="button"
                    disabled={resolvingId === obs.id}
                    onClick={() => void handleResolve(obs.id)}
                    className="inline-flex items-center gap-1 rounded bg-emerald-600 px-2.5 py-0.5 text-[11px] font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                  >
                    <Check className="h-3 w-3" />
                    {resolvingId === obs.id ? "Resolviendo..." : "Marcar Resuelto"}
                  </button>
                )}
              </div>

              <p className="mt-2 text-slate-800 dark:text-slate-200 whitespace-pre-wrap font-medium">
                {obs.comentario}
              </p>

              {obs.comentario_ajuste && (
                <div className="mt-2 rounded bg-white p-2.5 text-slate-700 border border-slate-200 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300">
                  <span className="font-semibold text-sky-800 dark:text-sky-300">
                    Ajuste reportado por el líder:
                  </span>
                  <p className="mt-0.5 whitespace-pre-line text-xs">{obs.comentario_ajuste}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  const allRaps = detail.competencias.flatMap((c) => c.resultados);

  return (
    <div className="space-y-6">
      {/* Top Bar with Navigation */}
      <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-xs sm:flex-row sm:items-center sm:justify-between dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
            title="Volver al árbol de planeaciones"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
                Fase {detail.fase.orden ?? 1} · {detail.fase.nombre}
              </span>
              <span className="text-slate-300">/</span>
              <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                {detail.actividad_proyecto.orden !== null && detail.actividad_proyecto.orden !== undefined
                  ? `AP${detail.actividad_proyecto.orden}: `
                  : "AP: "}
                {detail.actividad_proyecto.descripcion}
              </span>
            </div>
            <h2 className="mt-0.5 text-base font-bold text-slate-900 dark:text-white">
              {detail.actividades_aprendizaje || "Planeación Pedagógica"}
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onAddObservation("GENERAL")}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
          >
            <Plus className="h-3.5 w-3.5 text-emerald-600" />
            Observación General
          </button>
        </div>
      </div>

      {/* 1. FASE */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        {renderSectionHeader("Fase", "FASE")}
        <div className="mt-3 text-xs text-slate-800 dark:text-slate-200">
          <p className="font-semibold text-slate-900 dark:text-white">
            {detail.fase.orden !== null && detail.fase.orden !== undefined ? `Fase ${detail.fase.orden}: ` : ""}
            {detail.fase.nombre}
          </p>
        </div>
        {renderSectionObservations("FASE")}
      </section>

      {/* 2. ACTIVIDAD DE PROYECTO */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        {renderSectionHeader("Actividad de proyecto", "ACTIVIDAD_PROYECTO")}
        <div className="mt-3 text-xs text-slate-800 dark:text-slate-200">
          <p className="font-semibold text-slate-900 dark:text-white">
            {detail.actividad_proyecto.orden !== null && detail.actividad_proyecto.orden !== undefined
              ? `AP${detail.actividad_proyecto.orden}: `
              : ""}
            {detail.actividad_proyecto.descripcion}
          </p>
        </div>
        {renderSectionObservations("ACTIVIDAD_PROYECTO")}
      </section>

      {/* 3. COMPETENCIAS */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        {renderSectionHeader(
          "Competencias",
          "COMPETENCIA",
          `${detail.competencias.length} vinculada(s)`,
        )}
        <div className="mt-3 space-y-2">
          {detail.competencias.map((comp) => (
            <div
              key={comp.id}
              className="flex items-center gap-2 rounded-lg border border-slate-100 bg-slate-50/50 p-2.5 dark:border-slate-800 dark:bg-slate-800/40"
            >
              <BookOpen className="h-4 w-4 text-emerald-600 shrink-0" />
              <div className="text-xs">
                <span className="font-mono font-bold text-emerald-700 dark:text-emerald-400 mr-2">
                  {comp.codigo}
                </span>
                <span className="text-slate-800 dark:text-slate-200">{comp.nombre}</span>
              </div>
            </div>
          ))}
        </div>
        {renderSectionObservations("COMPETENCIA")}
      </section>

      {/* 4. RESULTADOS DE APRENDIZAJE */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        {renderSectionHeader(
          "Resultados de aprendizaje",
          "RAPS",
          `${allRaps.length} vinculados`,
        )}
        <div className="mt-3 space-y-2">
          {allRaps.length === 0 ? (
            <p className="text-xs text-slate-400 italic">No hay resultados de aprendizaje vinculados.</p>
          ) : (
            allRaps.map((rap) => (
              <div
                key={rap.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-100 bg-slate-50/50 p-2.5 text-xs text-slate-700 dark:border-slate-800 dark:bg-slate-800/40 dark:text-slate-300"
              >
                <div className="flex items-start gap-2">
                  <span className="font-mono text-[11px] font-bold text-slate-500 shrink-0">
                    {rap.codigo ? `${rap.codigo}:` : "RAP:"}
                  </span>
                  <span className="leading-snug">{rap.descripcion}</span>
                </div>
                <LockStatusBadge
                  editStatus={rap.edit_status}
                  unlockRequestId={rap.unlock_request_id}
                  approvedVersion={rap.approved_version}
                  compact
                />
              </div>
            ))
          )}
        </div>
        {renderSectionObservations("RAPS")}
      </section>

      {/* 5. ACTIVIDADES DE APRENDIZAJE */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        {renderSectionHeader("Actividades de aprendizaje", "ACTIVIDADES_APRENDIZAJE")}
        <div className="mt-3">
          <p className="text-xs leading-relaxed text-slate-800 dark:text-slate-200 whitespace-pre-line">
            {detail.actividades_aprendizaje || "Sin formulación de actividad registrada."}
          </p>
        </div>
        {renderSectionObservations("ACTIVIDADES_APRENDIZAJE")}
      </section>

      {/* 6. DESCRIPCION DE LA EVIDENCIA DE APRENDIZAJE */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        {renderSectionHeader(
          "Descripción de la evidencia de aprendizaje",
          "DESCRIPCION_EVIDENCIA_APRENDIZAJE",
        )}
        <div className="mt-3">
          <p className="text-xs leading-relaxed text-slate-800 dark:text-slate-200 whitespace-pre-line">
            {detail.descripcion_evidencia || "Sin descripción de evidencia registrada."}
          </p>
        </div>
        {renderSectionObservations("DESCRIPCION_EVIDENCIA_APRENDIZAJE")}
      </section>

      {/* 7. SABERES */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        {renderSectionHeader(
          "Saberes",
          "SABERES",
          `${(detail.conocimientos_saber?.length || 0) + (detail.conocimientos_proceso?.length || 0)} seleccionados`,
        )}
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          {/* Concepto y Principios (Saber) */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300">
              Conocimientos de Conceptos y Principios (Saber):
            </h4>
            {(detail.conocimientos_saber || []).length === 0 ? (
              <p className="text-xs text-slate-400 italic">No se asociaron saberes teóricos.</p>
            ) : (
              <ul className="list-disc pl-4 space-y-1 text-xs text-slate-600 dark:text-slate-400">
                {detail.conocimientos_saber.map((c) => (
                  <li key={c.id}>{c.descripcion}</li>
                ))}
              </ul>
            )}
          </div>

          {/* Proceso */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300">
              Conocimientos de Proceso:
            </h4>
            {(detail.conocimientos_proceso || []).length === 0 ? (
              <p className="text-xs text-slate-400 italic">No se asociaron saberes de proceso.</p>
            ) : (
              <ul className="list-disc pl-4 space-y-1 text-xs text-slate-600 dark:text-slate-400">
                {detail.conocimientos_proceso.map((c) => (
                  <li key={c.id}>{c.descripcion}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
        {renderSectionObservations("SABERES")}
      </section>

      {/* 8. CRITERIOS DE EVALUACION */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        {renderSectionHeader(
          "Criterios de evaluación",
          "CRITERIOS_EVALUACION",
          `${detail.criterios_evaluacion?.length || 0} vinculados`,
        )}
        <div className="mt-3">
          {(detail.criterios_evaluacion || []).length === 0 ? (
            <p className="text-xs text-slate-400 italic">No se vincularon criterios de evaluación.</p>
          ) : (
            <ul className="list-disc pl-4 space-y-1.5 text-xs text-slate-700 dark:text-slate-300">
              {detail.criterios_evaluacion.map((cr) => (
                <li key={cr.id} className="leading-snug">
                  {cr.descripcion}
                </li>
              ))}
            </ul>
          )}
        </div>
        {renderSectionObservations("CRITERIOS_EVALUACION")}
      </section>

      {/* 9. ESTRATEGIAS DIDACTICAS */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        {renderSectionHeader("Estrategias didácticas", "ESTRATEGIAS_DIDACTICAS")}
        <div className="mt-3">
          <p className="text-xs leading-relaxed text-slate-800 dark:text-slate-200 whitespace-pre-line">
            {detail.estrategias_didacticas || "Sin estrategias didácticas registradas."}
          </p>
        </div>
        {renderSectionObservations("ESTRATEGIAS_DIDACTICAS")}
      </section>

      {/* 10. AMBIENTES */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        {renderSectionHeader("Ambientes", "AMBIENTES")}
        <div className="mt-3">
          <p className="text-xs leading-relaxed text-slate-800 dark:text-slate-200 whitespace-pre-line">
            {detail.ambientes || "Sin ambientes de aprendizaje especificados."}
          </p>
        </div>
        {renderSectionObservations("AMBIENTES")}
      </section>

      {/* 11. MATERIALES */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        {renderSectionHeader("Materiales", "MATERIALES")}
        <div className="mt-3">
          <p className="text-xs leading-relaxed text-slate-800 dark:text-slate-200 whitespace-pre-line">
            {detail.materiales || "Sin materiales de formación especificados."}
          </p>
        </div>
        {renderSectionObservations("MATERIALES")}
      </section>

      {/* 12. INSTRUCTORES */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        {renderSectionHeader("Instructores", "INSTRUCTORES")}
        <div className="mt-3">
          <p className="text-xs leading-relaxed text-slate-800 dark:text-slate-200 whitespace-pre-line">
            {detail.instructores || "Sin instructores responsables registrados."}
          </p>
        </div>
        {renderSectionObservations("INSTRUCTORES")}
      </section>

      {/* 13. HORAS */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        {renderSectionHeader("Horas", "HORAS")}
        <div className="mt-3 flex flex-wrap items-center gap-6 text-xs text-slate-700 dark:text-slate-300">
          <div>
            Directas: <strong className="text-slate-900 dark:text-white font-mono">{detail.horas?.directas ?? 0}h</strong>
          </div>
          <div>
            Independientes: <strong className="text-slate-900 dark:text-white font-mono">{detail.horas?.independientes ?? 0}h</strong>
          </div>
          <div className="rounded-md bg-emerald-50 px-2.5 py-1 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300">
            Total: <strong className="font-mono">{detail.horas?.total ?? 0}h</strong>
          </div>
        </div>
        {renderSectionObservations("HORAS")}
      </section>

      {/* OBSERVACIONES DIDACTICAS ADICIONALES (SI APLICAN) */}
      {detail.observaciones_didacticas && (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
          {renderSectionHeader("Observaciones didácticas", "GENERAL")}
          <p className="mt-3 text-xs leading-relaxed text-slate-700 dark:text-slate-300 whitespace-pre-line">
            {detail.observaciones_didacticas}
          </p>
          {renderSectionObservations("GENERAL")}
        </section>
      )}

      {/* Volver / Finalizar navegación */}
      <div className="flex justify-end pt-4">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-2.5 text-xs font-semibold text-white shadow-xs hover:bg-slate-800 transition dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
        >
          <ArrowLeft className="h-4 w-4" />
          Finalizar revisión y volver al árbol
        </button>
      </div>
    </div>
  );
}
