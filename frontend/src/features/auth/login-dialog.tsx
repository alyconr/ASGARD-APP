"use client";

import React, { useState } from "react";
import { useAuth } from "./auth-context";

interface LoginDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export function LoginDialog({ isOpen, onClose }: LoginDialogProps): React.JSX.Element | null {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al iniciar sesión");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = (quickEmail: string) => {
    setEmail(quickEmail);
    setPassword("password123");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">Iniciar Sesión en ASGARD</h2>
            <p className="text-xs text-slate-500">Gestión Curricular y Planeación Pedagógica</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
          >
            ✕
          </button>
        </div>

        {error && (
          <div className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/50 dark:text-rose-300">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
              Correo Institucional
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="nombre@sena.edu.co"
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
              Contraseña
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-emerald-600 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:ring-offset-2 disabled:opacity-50"
          >
            {loading ? "Accediendo..." : "Ingresar"}
          </button>
        </form>

        {process.env.NODE_ENV !== "production" && (
          <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
              Accesos de prueba rápidos:
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => handleQuickLogin("admin.pedagogico@sena.edu.co")}
                className="rounded-md border border-slate-200 bg-slate-50 p-2 text-left hover:bg-emerald-50 hover:border-emerald-300 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700"
              >
                <div className="font-semibold text-slate-800 dark:text-slate-200">Admin Pedagógico</div>
                <div className="text-[10px] text-slate-500">Visibilidad global</div>
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin("lider.redes1@sena.edu.co")}
                className="rounded-md border border-slate-200 bg-slate-50 p-2 text-left hover:bg-emerald-50 hover:border-emerald-300 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700"
              >
                <div className="font-semibold text-slate-800 dark:text-slate-200">Líder Redes 01</div>
                <div className="text-[10px] text-slate-500">Aislamiento Equipo 1</div>
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin("lider.redes2@sena.edu.co")}
                className="rounded-md border border-slate-200 bg-slate-50 p-2 text-left hover:bg-emerald-50 hover:border-emerald-300 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700"
              >
                <div className="font-semibold text-slate-800 dark:text-slate-200">Líder Redes 02</div>
                <div className="text-[10px] text-slate-500">Aislamiento Equipo 2</div>
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin("apoyo.redes1@sena.edu.co")}
                className="rounded-md border border-slate-200 bg-slate-50 p-2 text-left hover:bg-emerald-50 hover:border-emerald-300 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700"
              >
                <div className="font-semibold text-slate-800 dark:text-slate-200">Usuario Adicional</div>
                <div className="text-[10px] text-slate-500">Miembro Equipo 1</div>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
