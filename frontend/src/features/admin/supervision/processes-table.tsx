"use client";

import React from "react";
import { ChevronLeft, ChevronRight, Eye, ExternalLink, Inbox } from "lucide-react";
import { AdminProcesoItem } from "../types";

interface ProcessesTableProps {
  procesos: AdminProcesoItem[];
  loading: boolean;
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  onPageChange: (newPage: number) => void;
  onSelectProceso: (proceso: AdminProcesoItem) => void;
  onActivateProcess: (referenciaId: string) => void;
}

export function ProcessesTable({
  procesos,
  loading,
  page,
  pageSize,
  total,
  totalPages,
  onPageChange,
  onSelectProceso,
  onActivateProcess,
}: ProcessesTableProps): React.JSX.Element {
  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="h-12 w-full animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800"
            />
          ))}
        </div>
      </div>
    );
  }

  if (procesos.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
          <Inbox className="h-6 w-6" />
        </div>
        <h3 className="mt-4 text-sm font-bold text-slate-900 dark:text-white">
          No se encontraron procesos curriculares
        </h3>
        <p className="mt-1 text-xs text-slate-500 max-w-sm mx-auto">
          Intente ajustando o limpiando los filtros seleccionados para ampliar la búsqueda.
        </p>
      </div>
    );
  }

  const startRecord = (page - 1) * pageSize + 1;
  const endRecord = Math.min(page * pageSize, total);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:border-slate-800 dark:bg-slate-950/60 dark:text-slate-400">
              <th className="py-3 px-4">Coordinación & Especialidad</th>
              <th className="py-3 px-4">Programa Formación</th>
              <th className="py-3 px-4">Proyecto Formativo</th>
              <th className="py-3 px-4">Equipo & Líder</th>
              <th className="py-3 px-4">Planeaciones</th>
              <th className="py-3 px-4">Estado Scope</th>
              <th className="py-3 px-4 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
            {procesos.map((p) => {
              const planTotal = p.planeaciones.total;
              const planComp = p.planeaciones.completas;

              return (
                <tr
                  key={p.referencia_id}
                  className="hover:bg-slate-50/80 transition dark:hover:bg-slate-800/40"
                >
                  {/* Coordinacion & Especialidad */}
                  <td className="py-3.5 px-4 font-medium text-slate-900 dark:text-white">
                    <div>
                      <p className="font-semibold text-slate-800 dark:text-slate-200">
                        {p.coordinacion ? p.coordinacion.codigo : "—"}
                      </p>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate max-w-[160px]">
                        {p.especialidad ? p.especialidad.nombre : "Sin especialidad"}
                      </p>
                    </div>
                  </td>

                  {/* Programa */}
                  <td className="py-3.5 px-4">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-xs font-bold text-slate-800 dark:text-slate-200">
                          {p.programa ? p.programa.codigo : "—"}
                        </span>
                        {p.programa && (
                          <span
                            className={`rounded px-1.5 py-0.2 text-[9px] font-bold ${
                              p.programa.estado === "COMPLETO"
                                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300"
                                : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                            }`}
                          >
                            {p.programa.estado}
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate max-w-[180px]">
                        {p.programa ? p.programa.nombre : "Sin programa"}
                      </p>
                    </div>
                  </td>

                  {/* Proyecto */}
                  <td className="py-3.5 px-4">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-xs font-semibold text-slate-800 dark:text-slate-200">
                          {p.proyecto?.codigo || "S/C"}
                        </span>
                        {p.proyecto && (
                          <span
                            className={`rounded px-1.5 py-0.2 text-[9px] font-bold ${
                              p.proyecto.estado === "COMPLETO"
                                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300"
                                : p.proyecto.estado === "BLOQUEADO"
                                ? "bg-rose-100 text-rose-800 dark:bg-rose-950/80 dark:text-rose-300"
                                : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                            }`}
                          >
                            {p.proyecto.estado}
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate max-w-[180px]">
                        {p.proyecto ? p.proyecto.nombre : "Sin proyecto"}
                      </p>
                    </div>
                  </td>

                  {/* Equipo & Lider */}
                  <td className="py-3.5 px-4">
                    <div>
                      <p className="font-semibold text-slate-800 dark:text-slate-200 truncate max-w-[160px]">
                        {p.equipo ? p.equipo.nombre : "Sin equipo asignado"}
                      </p>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate max-w-[160px]">
                        {p.lider ? `${p.lider.nombre} ${p.lider.apellido}` : "Sin líder"}
                      </p>
                    </div>
                  </td>

                  {/* Planeaciones */}
                  <td className="py-3.5 px-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300">
                        <span className="text-emerald-600 dark:text-emerald-400">{planComp}</span>
                        <span>/</span>
                        <span>{planTotal}</span>
                        <span className="text-[10px] text-slate-400 font-normal">completas</span>
                      </div>
                      <div className="h-1.5 w-20 rounded-full bg-slate-100 overflow-hidden dark:bg-slate-800">
                        <div
                          className="h-full rounded-full bg-emerald-500"
                          style={{
                            width: `${planTotal > 0 ? (planComp / planTotal) * 100 : 0}%`,
                          }}
                        />
                      </div>
                    </div>
                  </td>

                  {/* Estado Scope */}
                  <td className="py-3.5 px-4">
                    <span
                      className={`inline-flex items-center rounded-lg px-2 py-0.5 text-[11px] font-bold ${
                        p.estado_scope === "ASIGNADO"
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200 dark:border-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                          : p.estado_scope === "SIN_ASIGNAR"
                          ? "bg-amber-50 text-amber-700 border border-amber-200 dark:border-amber-800 dark:bg-amber-950/60 dark:text-amber-300"
                          : "bg-slate-50 text-slate-700 border border-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                      }`}
                    >
                      {p.estado_scope}
                    </span>
                  </td>

                  {/* Acciones */}
                  <td className="py-3.5 px-4 text-right">
                    <div className="inline-flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => onSelectProceso(p)}
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                        title="Ver ficha técnica del proceso"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        Detalle
                      </button>
                      <button
                        type="button"
                        onClick={() => onActivateProcess(p.referencia_id)}
                        className="inline-flex items-center gap-1 rounded-lg bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-950/60 dark:text-emerald-300 dark:hover:bg-emerald-900/60"
                        title="Abrir en Dashboard Operativo"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                        Ir
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-slate-200 bg-slate-50 px-4 py-3 text-xs dark:border-slate-800 dark:bg-slate-950/60">
        <p className="text-slate-500 dark:text-slate-400">
          Mostrando <strong className="font-semibold text-slate-800 dark:text-slate-200">{startRecord}</strong> a{" "}
          <strong className="font-semibold text-slate-800 dark:text-slate-200">{endRecord}</strong> de{" "}
          <strong className="font-semibold text-slate-800 dark:text-slate-200">{total}</strong> procesos
        </p>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 disabled:opacity-40 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            Anterior
          </button>
          <span className="text-slate-600 dark:text-slate-400 font-medium">
            Página {page} de {totalPages}
          </span>
          <button
            type="button"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 disabled:opacity-40 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
          >
            Siguiente
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
