"use client";

import React, { useState } from "react";
import { Ban, CheckCircle2, ShieldAlert } from "lucide-react";
import { User } from "@/features/auth/types";
import { authFetch, getApiBaseUrl } from "@/lib/api";

interface UserBlockDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  user: User | null;
}

export function UserBlockDialog({
  isOpen,
  onClose,
  onSuccess,
  user,
}: UserBlockDialogProps): React.JSX.Element | null {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  React.useEffect(() => {
    setError(null);
  }, [user, isOpen]);

  if (!isOpen || !user) return null;

  const isBlocked = user.estado === "BLOQUEADO";
  const targetState = isBlocked ? "ACTIVO" : "BLOQUEADO";

  const handleToggleBlock = async () => {
    setError(null);
    setLoading(true);

    try {
      const res = await authFetch(`${getApiBaseUrl()}/auth/users/${user.id}/estado`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ estado: targetState }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Error al cambiar estado" }));
        throw new Error(data.detail || "Error al actualizar estado del usuario");
      }

      onSuccess();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al procesar el cambio de estado");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="block-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
    >
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
          <div className="flex items-center gap-2">
            {isBlocked ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            ) : (
              <Ban className="h-5 w-5 text-rose-600 dark:text-rose-400" />
            )}
            <h2 id="block-dialog-title" className="text-base font-bold text-slate-900 dark:text-white">
              {isBlocked ? "Desbloquear Usuario" : "Bloquear Usuario"}
            </h2>
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

        <div className="mt-4 space-y-3">
          <p className="text-xs text-slate-600 dark:text-slate-300">
            {isBlocked
              ? "¿Desea restablecer el acceso al sistema para este usuario?"
              : "¿Está seguro de que desea bloquear el acceso al sistema para este usuario?"}
          </p>

          <div className="rounded-xl border border-slate-200 bg-slate-50/75 p-3.5 dark:border-slate-800 dark:bg-slate-800/40">
            <div className="text-xs font-bold text-slate-900 dark:text-white">
              {user.nombre} {user.apellido}
            </div>
            <div className="text-[11px] text-slate-500">{user.email}</div>
            <div className="mt-1 flex items-center gap-2">
              <span className="text-[10px] uppercase font-semibold text-slate-400">Estado actual:</span>
              <span
                className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-bold ${
                  isBlocked
                    ? "bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300"
                    : "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300"
                }`}
              >
                {user.estado || "ACTIVO"}
              </span>
            </div>
          </div>

          {isBlocked ? (
            <div className="flex items-start gap-2.5 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/30 dark:text-emerald-300">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600 mt-0.5" />
              <div>
                <p className="font-semibold">Reactivación de credenciales</p>
                <p className="mt-0.5 text-[11px] text-emerald-700 dark:text-emerald-400">
                  La cuenta volverá a estado ACTIVO y el usuario podrá iniciar sesión normalmente con sus credenciales actuales.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-2.5 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-300">
              <ShieldAlert className="h-4 w-4 shrink-0 text-rose-600 mt-0.5" />
              <div>
                <p className="font-semibold">Bloqueo de seguridad inmediato</p>
                <p className="mt-0.5 text-[11px] text-rose-700 dark:text-rose-400">
                  Se revocarán de inmediato todas las sesiones activas en todos los dispositivos y se rechazará cualquier intento de inicio de sesión o actualización de tokens.
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="mt-6 flex items-center justify-end gap-3 border-t border-slate-100 pt-3 dark:border-slate-800">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="rounded-lg px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleToggleBlock}
            disabled={loading}
            className={`inline-flex items-center gap-1.5 rounded-lg px-5 py-2 text-xs font-semibold text-white shadow-sm transition disabled:opacity-50 ${
              isBlocked
                ? "bg-emerald-600 hover:bg-emerald-700"
                : "bg-rose-600 hover:bg-rose-700"
            }`}
          >
            {isBlocked ? (
              <>
                <CheckCircle2 className="h-3.5 w-3.5" />
                {loading ? "Desbloqueando..." : "Desbloquear Usuario"}
              </>
            ) : (
              <>
                <Ban className="h-3.5 w-3.5" />
                {loading ? "Bloqueando..." : "Bloquear Usuario"}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
