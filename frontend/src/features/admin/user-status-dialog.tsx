"use client";

import React, { useState } from "react";
import { AlertTriangle, ShieldCheck, Ban, UserX } from "lucide-react";
import { User } from "@/features/auth/types";
import { authFetch, getApiBaseUrl } from "@/lib/api";

interface UserStatusDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  user: User | null;
}

export function UserStatusDialog({
  isOpen,
  onClose,
  onSuccess,
  user,
}: UserStatusDialogProps): React.JSX.Element | null {
  const [selectedEstado, setSelectedEstado] = useState<string>(user?.estado || "ACTIVO");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  React.useEffect(() => {
    if (user) {
      setSelectedEstado(user.estado || "ACTIVO");
      setError(null);
    }
  }, [user, isOpen]);

  if (!isOpen || !user) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await authFetch(`${getApiBaseUrl()}/auth/users/${user.id}/estado`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ estado: selectedEstado }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Error al cambiar estado" }));
        throw new Error(data.detail || "Error al actualizar estado");
      }

      onSuccess();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al procesar cambio de estado");
    } finally {
      setLoading(false);
    }
  };

  const isSensitive = selectedEstado === "INACTIVO" || selectedEstado === "BLOQUEADO";

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="status-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
    >
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
          <div>
            <h2 id="status-dialog-title" className="text-base font-bold text-slate-900 dark:text-white">
              Estado de Cuenta de Usuario
            </h2>
            <p className="text-xs text-slate-500">
              {user.nombre} {user.apellido} ({user.email})
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
          >
            ✕
          </button>
        </div>

        {error && (
          <div className="mt-4 rounded-lg bg-rose-50 p-3 text-xs font-semibold text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div className="space-y-2">
            <label
              className={`flex items-center gap-3 rounded-xl border p-3.5 cursor-pointer transition ${
                selectedEstado === "ACTIVO"
                  ? "border-emerald-500 bg-emerald-50/50 dark:bg-emerald-950/20"
                  : "border-slate-200 dark:border-slate-800"
              }`}
            >
              <input
                type="radio"
                name="estado"
                value="ACTIVO"
                checked={selectedEstado === "ACTIVO"}
                onChange={(e) => setSelectedEstado(e.target.value)}
                className="text-emerald-600 focus:ring-emerald-500"
              />
              <div className="flex items-center gap-2.5">
                <ShieldCheck className="h-5 w-5 text-emerald-600" />
                <div>
                  <div className="text-xs font-bold text-slate-800 dark:text-slate-200">ACTIVO</div>
                  <div className="text-[11px] text-slate-500">Acceso operativo habilitado</div>
                </div>
              </div>
            </label>

            <label
              className={`flex items-center gap-3 rounded-xl border p-3.5 cursor-pointer transition ${
                selectedEstado === "INACTIVO"
                  ? "border-amber-500 bg-amber-50/50 dark:bg-amber-950/20"
                  : "border-slate-200 dark:border-slate-800"
              }`}
            >
              <input
                type="radio"
                name="estado"
                value="INACTIVO"
                checked={selectedEstado === "INACTIVO"}
                onChange={(e) => setSelectedEstado(e.target.value)}
                className="text-amber-600 focus:ring-amber-500"
              />
              <div className="flex items-center gap-2.5">
                <UserX className="h-5 w-5 text-amber-600" />
                <div>
                  <div className="text-xs font-bold text-slate-800 dark:text-slate-200">INACTIVO</div>
                  <div className="text-[11px] text-slate-500">Cese temporal de operaciones</div>
                </div>
              </div>
            </label>

            <label
              className={`flex items-center gap-3 rounded-xl border p-3.5 cursor-pointer transition ${
                selectedEstado === "BLOQUEADO"
                  ? "border-rose-500 bg-rose-50/50 dark:bg-rose-950/20"
                  : "border-slate-200 dark:border-slate-800"
              }`}
            >
              <input
                type="radio"
                name="estado"
                value="BLOQUEADO"
                checked={selectedEstado === "BLOQUEADO"}
                onChange={(e) => setSelectedEstado(e.target.value)}
                className="text-rose-600 focus:ring-rose-500"
              />
              <div className="flex items-center gap-2.5">
                <Ban className="h-5 w-5 text-rose-600" />
                <div>
                  <div className="text-xs font-bold text-slate-800 dark:text-slate-200">BLOQUEADO</div>
                  <div className="text-[11px] text-slate-500">Bloqueo administrativo inmediato</div>
                </div>
              </div>
            </label>
          </div>

          {isSensitive && (
            <div className="flex items-start gap-2.5 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-300">
              <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
              <span>
                Atención: Cambiar el estado a <strong>{selectedEstado}</strong> revoca de inmediato todas las sesiones activas del usuario, impidiendo accesos concurrentes.
              </span>
            </div>
          )}

          <div className="flex items-center justify-end gap-3 border-t border-slate-100 pt-3 dark:border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className={`rounded-lg px-5 py-2 text-xs font-semibold text-white transition disabled:opacity-50 ${
                selectedEstado === "BLOQUEADO"
                  ? "bg-rose-600 hover:bg-rose-700"
                  : selectedEstado === "INACTIVO"
                  ? "bg-amber-600 hover:bg-amber-700"
                  : "bg-emerald-600 hover:bg-emerald-700"
              }`}
            >
              {loading ? "Actualizando..." : "Confirmar Estado"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
