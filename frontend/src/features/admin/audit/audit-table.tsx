"use client";

import React, { useState } from "react";
import { ChevronLeft, ChevronRight, Eye, Copy, Check, Inbox } from "lucide-react";
import { AuditItem } from "../types";

interface AuditTableProps {
  events: AuditItem[];
  loading: boolean;
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  onPageChange: (newPage: number) => void;
  onSelectEvent: (event: AuditItem) => void;
}

export function AuditTable({
  events,
  loading,
  page,
  pageSize,
  total,
  totalPages,
  onPageChange,
  onSelectEvent,
}: AuditTableProps): React.JSX.Element {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(text);
    setTimeout(() => setCopiedId(null), 1500);
  };

  const getActionBadgeClass = (action: string) => {
    if (action.startsWith("CREAR")) {
      return "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800";
    }
    if (action.startsWith("EDITAR") || action.startsWith("ACTUALIZAR")) {
      return "bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-950/60 dark:text-sky-300 dark:border-sky-800";
    }
    if (action.startsWith("ELIMINAR") || action.includes("INACTIVAR") || action.includes("BLOQUEAR")) {
      return "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800";
    }
    if (action.includes("ASIGNAR") || action.includes("LIDER")) {
      return "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800";
    }
    return "bg-slate-50 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700";
  };

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="space-y-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="h-12 w-full animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800"
            />
          ))}
        </div>
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
          <Inbox className="h-6 w-6" />
        </div>
        <h3 className="mt-4 text-sm font-bold text-slate-900 dark:text-white">
          No se encontraron eventos de auditoría
        </h3>
        <p className="mt-1 text-xs text-slate-500 max-w-sm mx-auto">
          No existen registros para los filtros seleccionados. Intente ajustar el rango de fechas o los criterios de búsqueda.
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
              <th className="py-3 px-4">Fecha & Hora</th>
              <th className="py-3 px-4">Actor Responsable</th>
              <th className="py-3 px-4">Operación / Acción</th>
              <th className="py-3 px-4">Entidad Afectada</th>
              <th className="py-3 px-4">Proceso / Referencia</th>
              <th className="py-3 px-4 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
            {events.map((e) => (
              <tr
                key={e.id}
                className="hover:bg-slate-50/80 transition dark:hover:bg-slate-800/40"
              >
                {/* Fecha */}
                <td className="py-3.5 px-4 font-medium text-slate-900 dark:text-white whitespace-nowrap">
                  <div>
                    <p className="font-semibold text-slate-800 dark:text-slate-200">
                      {new Date(e.fecha_evento).toLocaleDateString()}
                    </p>
                    <p className="text-[11px] text-slate-400 font-mono">
                      {new Date(e.fecha_evento).toLocaleTimeString()}
                    </p>
                  </div>
                </td>

                {/* Actor */}
                <td className="py-3.5 px-4">
                  <div>
                    <p className="font-semibold text-slate-800 dark:text-slate-200">
                      {e.actor ? `${e.actor.nombre} ${e.actor.apellido}` : "Sistema"}
                    </p>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate max-w-[160px]">
                      {e.actor ? `${e.actor.email} (${e.actor.rol})` : "N/A"}
                    </p>
                  </div>
                </td>

                {/* Accion */}
                <td className="py-3.5 px-4 whitespace-nowrap">
                  <span
                    className={`inline-flex items-center rounded-lg border px-2 py-0.5 text-[11px] font-bold ${getActionBadgeClass(
                      e.accion
                    )}`}
                  >
                    {e.accion}
                  </span>
                </td>

                {/* Entidad */}
                <td className="py-3.5 px-4">
                  <div>
                    <p className="font-semibold text-slate-800 dark:text-slate-200">
                      {e.entidad}
                    </p>
                    <div className="flex items-center gap-1 text-[11px] text-slate-400 font-mono">
                      <span>{e.entidad_id.slice(0, 8)}...</span>
                      <button
                        type="button"
                        onClick={() => handleCopy(e.entidad_id)}
                        className="hover:text-slate-600 dark:hover:text-slate-300"
                        title="Copiar UUID"
                      >
                        {copiedId === e.entidad_id ? (
                          <Check className="h-3 w-3 text-emerald-600" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                      </button>
                    </div>
                  </div>
                </td>

                {/* Referencia ID */}
                <td className="py-3.5 px-4">
                  {e.referencia_id ? (
                    <div className="flex items-center gap-1 font-mono text-[11px] text-slate-600 dark:text-slate-300">
                      <span>{e.referencia_id.slice(0, 8)}...</span>
                      <button
                        type="button"
                        onClick={() => handleCopy(e.referencia_id!)}
                        className="hover:text-slate-800 dark:hover:text-slate-100"
                        title="Copiar Referencia ID"
                      >
                        {copiedId === e.referencia_id ? (
                          <Check className="h-3 w-3 text-emerald-600" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                      </button>
                    </div>
                  ) : (
                    <span className="text-slate-400 text-xs">—</span>
                  )}
                </td>

                {/* Acciones */}
                <td className="py-3.5 px-4 text-right">
                  <button
                    type="button"
                    onClick={() => onSelectEvent(e)}
                    className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700 transition"
                  >
                    <Eye className="h-3.5 w-3.5" />
                    Carga Útil
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-slate-200 bg-slate-50 px-4 py-3 text-xs dark:border-slate-800 dark:bg-slate-950/60">
        <p className="text-slate-500 dark:text-slate-400">
          Mostrando <strong className="font-semibold text-slate-800 dark:text-slate-200">{startRecord}</strong> a{" "}
          <strong className="font-semibold text-slate-800 dark:text-slate-200">{endRecord}</strong> de{" "}
          <strong className="font-semibold text-slate-800 dark:text-slate-200">{total}</strong> eventos
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
