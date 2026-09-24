"use client";

import React, { useState } from "react";
import { ChevronLeft, ChevronRight, Eye, ExternalLink, Inbox, Trash2, Unlink } from "lucide-react";
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
  onUnassignProcess?: (referenciaId: string) => void;
  onDeleteProcess?: (referenciaId: string) => void;
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
  onUnassignProcess,
  onDeleteProcess,
}: ProcessesTableProps): React.JSX.Element {
  const [confirmItem, setConfirmItem] = useState<{
    proceso: AdminProcesoItem;
    type: "unassign" | "delete";
  } | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
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
                      {p.estado_scope === "ASIGNADO" && onUnassignProcess && (
                        <button
                          type="button"
                          onClick={() => setConfirmItem({ proceso: p, type: "unassign" })}
                          className="inline-flex items-center gap-1 rounded-lg border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-700 hover:bg-amber-100 dark:border-amber-900/60 dark:bg-amber-950/60 dark:text-amber-300 dark:hover:bg-amber-900/60"
                          title="Desasignar del equipo ejecutor"
                        >
                          <Unlink className="h-3.5 w-3.5" />
                        </button>
                      )}
                      {onDeleteProcess && (
                        <button
                          type="button"
                          onClick={() => setConfirmItem({ proceso: p, type: "delete" })}
                          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-rose-950/40 dark:hover:text-rose-300"
                          title="Eliminar proceso curricular definitivamente"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
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

      {/* Confirmation Modal */}
      {confirmItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center gap-3">
              <div
                className={`rounded-xl p-2.5 ${
                  confirmItem.type === "unassign"
                    ? "bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300"
                    : "bg-rose-100 text-rose-600 dark:bg-rose-950/60 dark:text-rose-400"
                }`}
              >
                {confirmItem.type === "unassign" ? (
                  <Unlink className="h-6 w-6" />
                ) : (
                  <Trash2 className="h-6 w-6" />
                )}
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  {confirmItem.type === "unassign"
                    ? "Desasignar Proceso Curricular"
                    : "Eliminar Proceso Curricular"}
                </h3>
                <p className="text-xs text-slate-500 font-mono truncate max-w-xs">
                  {confirmItem.proceso.programa ? `${confirmItem.proceso.programa.codigo} - ${confirmItem.proceso.programa.nombre}` : `Ref: ${confirmItem.proceso.referencia_id.slice(0, 8)}...`}
                </p>
              </div>
            </div>

            <div className="mt-4 text-xs text-slate-600 dark:text-slate-300">
              {confirmItem.type === "unassign" ? (
                <p>
                  ¿Desea desvincular este proceso curricular de su equipo y líder? El proceso volverá al estado <strong className="text-amber-700 dark:text-amber-300">SIN ASIGNAR</strong>.
                </p>
              ) : (
                <p>
                  ¿Está seguro de que desea <strong className="text-rose-600">eliminar permanentemente</strong> este proceso curricular? Se eliminarán los registros del programa, proyecto, planeaciones y archivos asociados en MinIO. Esta acción no se puede deshacer.
                </p>
              )}
            </div>

            <div className="mt-6 flex justify-end gap-2 border-t border-slate-100 pt-3 dark:border-slate-800">
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => setConfirmItem(null)}
                className="rounded-xl px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={actionLoading}
                onClick={async () => {
                  setActionLoading(true);
                  try {
                    if (confirmItem.type === "unassign") {
                      await onUnassignProcess?.(confirmItem.proceso.referencia_id);
                    } else {
                      await onDeleteProcess?.(confirmItem.proceso.referencia_id);
                    }
                    setConfirmItem(null);
                  } finally {
                    setActionLoading(false);
                  }
                }}
                className={`rounded-xl px-4 py-2 text-xs font-semibold text-white transition disabled:opacity-50 ${
                  confirmItem.type === "unassign"
                    ? "bg-amber-600 hover:bg-amber-700"
                    : "bg-rose-600 hover:bg-rose-700"
                }`}
              >
                {actionLoading
                  ? "Procesando..."
                  : confirmItem.type === "unassign"
                  ? "Desasignar de Equipo"
                  : "Eliminar Proceso"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
