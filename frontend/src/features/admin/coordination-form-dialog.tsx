"use client";

import React, { useEffect, useState } from "react";
import { authFetch, getApiBaseUrl } from "@/lib/api";

interface Coordinacion {
  id: string;
  codigo: string;
  nombre: string;
  descripcion?: string | null;
  activo: boolean;
}

interface CoordinationFormDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  coordinationToEdit?: Coordinacion | null;
}

export function CoordinationFormDialog({
  isOpen,
  onClose,
  onSuccess,
  coordinationToEdit,
}: CoordinationFormDialogProps): React.JSX.Element | null {
  const isEditing = !!coordinationToEdit;

  const [codigo, setCodigo] = useState("");
  const [nombre, setNombre] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (coordinationToEdit) {
      setCodigo(coordinationToEdit.codigo || "");
      setNombre(coordinationToEdit.nombre || "");
      setDescripcion(coordinationToEdit.descripcion || "");
    } else {
      setCodigo("");
      setNombre("");
      setDescripcion("");
    }
    setError(null);
  }, [coordinationToEdit, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isEditing && coordinationToEdit) {
        const res = await authFetch(`${getApiBaseUrl()}/coordinaciones/${coordinationToEdit.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            nombre: nombre.trim(),
            descripcion: descripcion.trim() || null,
          }),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({ detail: "Error al actualizar coordinación" }));
          throw new Error(data.detail || "Error al actualizar coordinación");
        }
      } else {
        const res = await authFetch(`${getApiBaseUrl()}/coordinaciones`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            codigo: codigo.trim().toUpperCase(),
            nombre: nombre.trim(),
            descripcion: descripcion.trim() || null,
          }),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({ detail: "Error al crear coordinación" }));
          throw new Error(data.detail || "Error al crear coordinación");
        }
      }

      onSuccess();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al procesar solicitud");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="coord-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
    >
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
          <div>
            <h2 id="coord-dialog-title" className="text-base font-bold text-slate-900 dark:text-white">
              {isEditing ? "Editar Coordinación" : "Nueva Coordinación Académica"}
            </h2>
            <p className="text-xs text-slate-500">Estructura curricular de nivel superior</p>
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
          <div className="mt-3 rounded-lg bg-rose-50 p-3 text-xs font-semibold text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-3.5">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
              Código Único *
            </label>
            <input
              type="text"
              required
              disabled={isEditing}
              value={codigo}
              onChange={(e) => setCodigo(e.target.value.toUpperCase())}
              placeholder="TEL"
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 disabled:bg-slate-100 disabled:text-slate-500 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-800/50"
            />
            {isEditing && (
              <p className="mt-1 text-[11px] text-slate-400">
                El código institucional es inmutable para preservar trazabilidad.
              </p>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
              Nombre de la Coordinación *
            </label>
            <input
              type="text"
              required
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="TELEINFORMATICA"
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
              Descripción / Alcance (Opcional)
            </label>
            <textarea
              rows={2}
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
              placeholder="Área encargada de redes, desarrollo de software..."
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
              className="rounded-lg bg-emerald-600 px-5 py-2 text-xs font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-50"
            >
              {loading ? "Guardando..." : isEditing ? "Actualizar" : "Crear Coordinación"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
