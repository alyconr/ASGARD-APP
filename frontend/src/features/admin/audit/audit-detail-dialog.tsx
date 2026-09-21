"use client";

import React, { useState } from "react";
import { X, Copy, Check, Shield, Clock, Database, User } from "lucide-react";
import { AuditItem } from "../types";

interface AuditDetailDialogProps {
  event: AuditItem | null;
  onClose: () => void;
}

export function AuditDetailDialog({ event, onClose }: AuditDetailDialogProps): React.JSX.Element | null {
  const [copied, setCopied] = useState(false);

  if (!event) return null;

  const handleCopyJson = () => {
    const jsonStr = JSON.stringify(event.detalle, null, 2);
    navigator.clipboard.writeText(jsonStr);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-2xl rounded-2xl bg-white shadow-2xl dark:bg-slate-900 border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-950/50">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400">
              <Shield className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Registro de Auditoría Institucional
              </h3>
              <p className="text-xs text-slate-500 font-mono">
                {event.id}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl p-1.5 text-slate-400 hover:bg-slate-200 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 text-xs">
          {/* Metadata Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Actor */}
            <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-800 space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                <User className="h-3.5 w-3.5 text-emerald-600" />
                Actor Responsable
              </span>
              <p className="font-semibold text-slate-900 dark:text-white">
                {event.actor ? `${event.actor.nombre} ${event.actor.apellido}` : "Sistema / Desconocido"}
              </p>
              <p className="text-slate-500 dark:text-slate-400">
                {event.actor ? `${event.actor.email} (${event.actor.rol})` : "N/A"}
              </p>
            </div>

            {/* Event Timestamp */}
            <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-800 space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                <Clock className="h-3.5 w-3.5 text-sky-600" />
                Fecha y Hora (UTC)
              </span>
              <p className="font-semibold text-slate-900 dark:text-white">
                {new Date(event.fecha_evento).toLocaleString()}
              </p>
              <p className="font-mono text-slate-500 text-[11px]">
                {event.fecha_evento}
              </p>
            </div>

            {/* Action & Entity */}
            <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-800 space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                <Database className="h-3.5 w-3.5 text-indigo-600" />
                Operación
              </span>
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900 dark:text-white">
                  {event.accion}
                </span>
                <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                  {event.entidad}
                </span>
              </div>
              <p className="font-mono text-[10px] text-slate-400 truncate">
                ID Entidad: {event.entidad_id}
              </p>
            </div>

            {/* Referencia ID */}
            <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-800 space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Proceso Vinculado
              </span>
              <p className="font-mono text-xs text-slate-700 dark:text-slate-300 truncate">
                {event.referencia_id || "Sin proceso curricular"}
              </p>
            </div>
          </div>

          {/* Payload JSON */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Carga Útil Sanitizada (Detalle)
              </span>
              <button
                type="button"
                onClick={handleCopyJson}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-600" />
                    Copiado
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    Copiar JSON
                  </>
                )}
              </button>
            </div>

            <pre className="rounded-xl border border-slate-200 bg-slate-900 p-4 font-mono text-xs text-emerald-400 overflow-x-auto max-h-72 dark:border-slate-800">
              {JSON.stringify(event.detalle, null, 2)}
            </pre>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/50 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
