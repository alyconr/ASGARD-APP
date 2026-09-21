"use client";

import React, { useState } from "react";
import { KeyRound, ShieldAlert } from "lucide-react";
import { User } from "@/features/auth/types";
import { authFetch, getApiBaseUrl } from "@/lib/api";

interface UserResetPasswordDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  user: User | null;
}

export function UserResetPasswordDialog({
  isOpen,
  onClose,
  onSuccess,
  user,
}: UserResetPasswordDialogProps): React.JSX.Element | null {
  const [temporaryPassword, setTemporaryPassword] = useState("");
  const [confirmTemporaryPassword, setConfirmTemporaryPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  React.useEffect(() => {
    setTemporaryPassword("");
    setConfirmTemporaryPassword("");
    setError(null);
  }, [user, isOpen]);

  if (!isOpen || !user) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (temporaryPassword !== confirmTemporaryPassword) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    if (temporaryPassword.length < 8) {
      setError("La contraseña temporal debe tener al menos 8 caracteres.");
      return;
    }

    setLoading(true);
    try {
      const res = await authFetch(`${getApiBaseUrl()}/auth/users/${user.id}/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          temporary_password: temporaryPassword,
          confirm_temporary_password: confirmTemporaryPassword,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Error al resetear contraseña" }));
        throw new Error(data.detail || "Error al restablecer contraseña");
      }

      onSuccess();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al procesar restablecimiento");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="reset-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
    >
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
          <div>
            <h2 id="reset-dialog-title" className="text-base font-bold text-slate-900 dark:text-white">
              Restablecer Contraseña
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

        <div className="mt-3 flex items-start gap-2.5 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-300">
          <ShieldAlert className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
          <span>
            Al asignar una contraseña temporal, todas las sesiones activas del usuario se revocarán de inmediato. En su próximo inicio de sesión, el sistema le exigirá definir una nueva contraseña personalizada.
          </span>
        </div>

        {error && (
          <div className="mt-3 rounded-lg bg-rose-50 p-3 text-xs font-semibold text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-3.5">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
              Nueva Contraseña Temporal *
            </label>
            <input
              type="password"
              required
              value={temporaryPassword}
              onChange={(e) => setTemporaryPassword(e.target.value)}
              placeholder="••••••••"
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
              Confirmar Contraseña Temporal *
            </label>
            <input
              type="password"
              required
              value={confirmTemporaryPassword}
              onChange={(e) => setConfirmTemporaryPassword(e.target.value)}
              placeholder="••••••••"
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            />
          </div>

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
              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-5 py-2 text-xs font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-50"
            >
              <KeyRound className="h-3.5 w-3.5" />
              {loading ? "Asignando..." : "Asignar Clave Temporal"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
