"use client";

import React, { useState } from "react";
import { AlertTriangle, Trash2, Ban } from "lucide-react";
import { User } from "@/features/auth/types";
import { authFetch, getApiBaseUrl } from "@/lib/api";

interface UserDeleteDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  onSelectBlock?: (user: User) => void;
  user: User | null;
}

export function UserDeleteDialog({
  isOpen,
  onClose,
  onSuccess,
  onSelectBlock,
  user,
}: UserDeleteDialogProps): React.JSX.Element | null {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  React.useEffect(() => {
    setError(null);
  }, [user, isOpen]);

  if (!isOpen || !user) return null;

  const handleDelete = async () => {
    setError(null);
    setLoading(true);

    try {
      const res = await authFetch(`${getApiBaseUrl()}/auth/users/${user.id}`, {
        method: "DELETE",
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Error al eliminar usuario" }));
        throw new Error(data.detail || "Error al procesar la eliminación");
      }

      onSuccess();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al procesar eliminación del usuario");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
    >
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
          <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400">
            <Trash2 className="h-5 w-5" />
            <h2 id="delete-dialog-title" className="text-base font-bold text-slate-900 dark:text-white">
              Eliminar Usuario
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
          <div className="mt-4 space-y-3 rounded-lg border border-rose-200 bg-rose-50 p-3.5 text-xs text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-300">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0 text-rose-600 mt-0.5" />
              <div>
                <p className="font-semibold">{error}</p>
              </div>
            </div>
            {onSelectBlock && (
              <div className="border-t border-rose-200/60 pt-2 text-right dark:border-rose-900/40">
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    onSelectBlock(user);
                  }}
                  className="inline-flex items-center gap-1.5 rounded-md bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-rose-700 transition"
                >
                  <Ban className="h-3.5 w-3.5" />
                  Bloquear usuario en su lugar
                </button>
              </div>
            )}
          </div>
        )}

        <div className="mt-4 space-y-3">
          <p className="text-xs text-slate-600 dark:text-slate-300">
            ¿Está seguro de que desea eliminar definitivamente la cuenta del usuario?
          </p>

          <div className="rounded-xl border border-slate-200 bg-slate-50/75 p-3.5 dark:border-slate-800 dark:bg-slate-800/40">
            <div className="text-xs font-bold text-slate-900 dark:text-white">
              {user.nombre} {user.apellido}
            </div>
            <div className="text-[11px] text-slate-500">{user.email}</div>
            <div className="mt-1 flex flex-wrap gap-1">
              {user.roles?.map((r) => (
                <span
                  key={r}
                  className="inline-flex rounded bg-slate-200/70 px-1.5 py-0.5 text-[10px] font-medium text-slate-700 dark:bg-slate-700 dark:text-slate-300"
                >
                  {r}
                </span>
              ))}
            </div>
          </div>

          <div className="flex items-start gap-2.5 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-300">
            <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
            <div>
              <p className="font-semibold">Esta acción es irreversible</p>
              <p className="mt-0.5 text-[11px] text-amber-700 dark:text-amber-400">
                Se revocará inmediatamente el acceso del usuario, se eliminarán sus sesiones activas y se desvinculará de los equipos donde participe como miembro de apoyo.
              </p>
            </div>
          </div>
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
            onClick={handleDelete}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-rose-700 transition disabled:opacity-50"
          >
            <Trash2 className="h-3.5 w-3.5" />
            {loading ? "Eliminando..." : "Eliminar Definitivamente"}
          </button>
        </div>
      </div>
    </div>
  );
}
