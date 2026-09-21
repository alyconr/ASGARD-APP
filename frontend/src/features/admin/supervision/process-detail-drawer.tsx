"use client";

import React, { useState } from "react";
import { X, ExternalLink, Copy, Check, Building2, BookOpen, Layers, Clock } from "lucide-react";
import { AdminProcesoItem } from "../types";

interface ProcessDetailDrawerProps {
  proceso: AdminProcesoItem | null;
  onClose: () => void;
  onActivateProcess: (referenciaId: string) => void;
}

export function ProcessDetailDrawer({
  proceso,
  onClose,
  onActivateProcess,
}: ProcessDetailDrawerProps): React.JSX.Element | null {
  const [copied, setCopied] = useState(false);

  if (!proceso) return null;

  const handleCopyId = () => {
    navigator.clipboard.writeText(proceso.referencia_id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const planeacionesTotal = proceso.planeaciones.total;
  const planeacionesPct =
    planeacionesTotal > 0
      ? Math.round((proceso.planeaciones.completas / planeacionesTotal) * 100)
      : 0;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-white shadow-2xl dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 flex flex-col">
          {/* Header */}
          <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex items-start justify-between bg-slate-50 dark:bg-slate-950/50">
            <div>
              <div className="flex items-center gap-2">
                <span
                  className={`inline-flex items-center rounded-lg px-2.5 py-1 text-xs font-bold uppercase tracking-wider ${
                    proceso.estado_scope === "ASIGNADO"
                      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300"
                      : proceso.estado_scope === "SIN_ASIGNAR"
                      ? "bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300"
                      : "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300"
                  }`}
                >
                  {proceso.estado_scope}
                </span>
                <span className="text-xs text-slate-500 font-medium">
                  {proceso.tipo_necesidad}
                </span>
              </div>
              <h2 className="mt-2 text-lg font-bold text-slate-900 dark:text-white">
                Supervisión de Proceso
              </h2>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl p-1.5 text-slate-400 hover:bg-slate-200 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200 transition"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Body Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Referencia ID Card */}
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 dark:border-slate-800 dark:bg-slate-800/50">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Referencia Operativa
              </span>
              <div className="mt-1 flex items-center justify-between gap-2">
                <span className="font-mono text-xs text-slate-700 dark:text-slate-300 break-all select-all">
                  {proceso.referencia_id}
                </span>
                <button
                  type="button"
                  onClick={handleCopyId}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                  title="Copiar Referencia ID"
                >
                  {copied ? (
                    <Check className="h-3.5 w-3.5 text-emerald-600" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                </button>
              </div>
            </div>

            {/* Hierarchical Chain */}
            <div className="space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <Building2 className="h-4 w-4 text-emerald-600" />
                Jerarquía Organizacional
              </h3>

              <div className="rounded-xl border border-slate-200 p-4 space-y-3 dark:border-slate-800">
                <div>
                  <span className="text-[10px] font-bold uppercase text-slate-400">Coordinación</span>
                  <p className="text-xs font-semibold text-slate-900 dark:text-white">
                    {proceso.coordinacion
                      ? `${proceso.coordinacion.codigo} - ${proceso.coordinacion.nombre}`
                      : "Sin coordinación"}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase text-slate-400">Especialidad</span>
                  <p className="text-xs font-semibold text-slate-900 dark:text-white">
                    {proceso.especialidad
                      ? `${proceso.especialidad.codigo} - ${proceso.especialidad.nombre}`
                      : "Sin especialidad"}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase text-slate-400">Equipo Ejecutor</span>
                  <p className="text-xs font-semibold text-slate-900 dark:text-white">
                    {proceso.equipo ? proceso.equipo.nombre : "Sin equipo asignado"}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase text-slate-400">Líder Responsable</span>
                  <p className="text-xs font-semibold text-slate-900 dark:text-white">
                    {proceso.lider
                      ? `${proceso.lider.nombre} ${proceso.lider.apellido} (${proceso.lider.email})`
                      : "Sin líder asignado"}
                  </p>
                </div>
              </div>
            </div>

            {/* Curricular Scope */}
            <div className="space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <BookOpen className="h-4 w-4 text-sky-600" />
                Cadena Curricular
              </h3>

              <div className="rounded-xl border border-slate-200 p-4 space-y-3 dark:border-slate-800">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase text-slate-400">Programa</span>
                    <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">
                      {proceso.programa?.estado || "NO INICIADO"}
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-slate-900 dark:text-white">
                    {proceso.programa
                      ? `${proceso.programa.codigo} - ${proceso.programa.nombre}`
                      : "Sin programa vinculado"}
                  </p>
                </div>

                <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase text-slate-400">Proyecto Formativo</span>
                    <span className="text-[10px] font-semibold text-indigo-600 dark:text-indigo-400">
                      {proceso.proyecto?.estado || "BLOQUEADO"}
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-slate-900 dark:text-white">
                    {proceso.proyecto
                      ? `${proceso.proyecto.codigo || "S/C"} - ${proceso.proyecto.nombre}`
                      : "Sin proyecto vinculado"}
                  </p>
                </div>
              </div>
            </div>

            {/* Planning Status */}
            <div className="space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <Layers className="h-4 w-4 text-violet-600" />
                Avance de Planeaciones
              </h3>

              <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800 space-y-2">
                <div className="flex justify-between items-baseline">
                  <span className="text-xs font-semibold text-slate-900 dark:text-white">
                    {proceso.planeaciones.completas} de {proceso.planeaciones.total} completas
                  </span>
                  <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400">
                    {planeacionesPct}%
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden dark:bg-slate-800">
                  <div
                    className="h-full rounded-full bg-emerald-500 transition-all duration-300"
                    style={{ width: `${planeacionesPct}%` }}
                  />
                </div>
                <div className="flex justify-between text-[11px] text-slate-500 pt-1">
                  <span>Borrador: {proceso.planeaciones.borrador}</span>
                  <span>Formato GPFI: {proceso.planeaciones.completas > 0 ? "Disponible" : "Sin generar"}</span>
                </div>
              </div>
            </div>

            {/* Timestamps */}
            {proceso.fecha_actualizacion && (
              <div className="flex items-center gap-1.5 text-xs text-slate-400 pt-2">
                <Clock className="h-3.5 w-3.5" />
                <span>Última actualización: {new Date(proceso.fecha_actualizacion).toLocaleString()}</span>
              </div>
            )}
          </div>

          {/* Action Footer */}
          <div className="p-6 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/50">
            <button
              type="button"
              onClick={() => onActivateProcess(proceso.referencia_id)}
              className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-600 transition"
            >
              <ExternalLink className="h-4 w-4" />
              Abrir en Dashboard Operativo
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
