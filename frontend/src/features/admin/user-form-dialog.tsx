"use client";

import React, { useEffect, useState } from "react";
import { ProgramaSimple, User } from "@/features/auth/types";
import { authFetch, getApiBaseUrl } from "@/lib/api";
import { SpecialtyFormDialog } from "./specialty-form-dialog";

interface Coordinacion {
  id: string;
  codigo: string;
  nombre: string;
}

interface Especialidad {
  id: string;
  coordinacion_id: string;
  codigo: string;
  nombre: string;
}

interface UserFormDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  userToEdit?: User | null;
  isSuperAdmin: boolean;
}

export function UserFormDialog({
  isOpen,
  onClose,
  onSuccess,
  userToEdit,
  isSuperAdmin,
}: UserFormDialogProps): React.JSX.Element | null {
  const isEditing = !!userToEdit;

  const [nombre, setNombre] = useState("");
  const [apellido, setApellido] = useState("");
  const [email, setEmail] = useState("");
  const [telefono, setTelefono] = useState("");
  const [area, setArea] = useState("");
  const [selectedRole, setSelectedRole] = useState("LIDER_EQUIPO_EJECUTOR");
  const [selectedCoordId, setSelectedCoordId] = useState("");
  const [selectedEspId, setSelectedEspId] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [programasCatalogo, setProgramasCatalogo] = useState<ProgramaSimple[]>([]);
  const [selectedProgramasIds, setSelectedProgramasIds] = useState<string[]>([]);
  const [programSearch, setProgramSearch] = useState("");

  const [coordinaciones, setCoordinaciones] = useState<Coordinacion[]>([]);
  const [especialidades, setEspecialidades] = useState<Especialidad[]>([]);
  const [showNewEspModal, setShowNewEspModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadEspecialidades = async (coordId: string) => {
    try {
      const res = await authFetch(`${getApiBaseUrl()}/coordinaciones/${coordId}/especialidades?solo_activas=true`);
      if (res.ok) {
        const data = await res.json();
        setEspecialidades(data);
        return data;
      }
    } catch (err) {
      console.error(err);
    }
    return [];
  };

  // Load coordinations and programs catalog on mount
  useEffect(() => {
    if (!isOpen) return;
    authFetch(`${getApiBaseUrl()}/coordinaciones?solo_activas=true`)
      .then(async (res) => {
        if (res.ok) setCoordinaciones(await res.json());
      })
      .catch(console.error);

    authFetch(`${getApiBaseUrl()}/programas/catalogo`)
      .then(async (res) => {
        if (res.ok) setProgramasCatalogo(await res.json());
      })
      .catch(console.error);
  }, [isOpen]);

  // Load specialties when coordination changes
  useEffect(() => {
    if (!selectedCoordId) {
      setEspecialidades([]);
      setSelectedEspId("");
      return;
    }
    loadEspecialidades(selectedCoordId);
  }, [selectedCoordId]);

  // Pre-fill form when editing
  useEffect(() => {
    if (userToEdit) {
      setNombre(userToEdit.nombre || "");
      setApellido(userToEdit.apellido || "");
      setEmail(userToEdit.email || "");
      setTelefono(userToEdit.telefono || "");
      setArea(userToEdit.area || "");
      setSelectedRole(userToEdit.roles[0] || "LIDER_EQUIPO_EJECUTOR");
      setSelectedCoordId(userToEdit.coordinacion?.id || "");
      setSelectedEspId(userToEdit.especialidad?.id || "");
      setSelectedProgramasIds(userToEdit.programas_autorizados?.map((p) => p.id) || []);
      setPassword("");
      setPasswordConfirmation("");
    } else {
      setNombre("");
      setApellido("");
      setEmail("");
      setTelefono("");
      setArea("");
      setSelectedRole("LIDER_EQUIPO_EJECUTOR");
      setSelectedCoordId("");
      setSelectedEspId("");
      setSelectedProgramasIds([]);
      setPassword("");
      setPasswordConfirmation("");
    }
    setProgramSearch("");
    setError(null);
  }, [userToEdit, isOpen]);

  if (!isOpen) return null;

  const requiresOrg = ["LIDER_EQUIPO_EJECUTOR", "USUARIO_ADICIONAL"].includes(selectedRole);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!isEditing) {
      if (password !== passwordConfirmation) {
        setError("Las contraseñas no coinciden.");
        return;
      }
      if (password.length < 8) {
        setError("La contraseña debe tener al menos 8 caracteres.");
        return;
      }
    }

    if (requiresOrg && (!selectedCoordId || !selectedEspId)) {
      setError("Líder y Usuario de Apoyo requieren Coordinación y Especialidad obligatorias.");
      return;
    }

    setLoading(true);
    try {
      if (isEditing && userToEdit) {
        const payload: Record<string, unknown> = {
          nombre: nombre.trim(),
          apellido: apellido.trim(),
          telefono: telefono.trim() || null,
          area: area.trim() || null,
          roles: [selectedRole],
          coordinacion_id: selectedCoordId || null,
          especialidad_id: selectedEspId || null,
          programas_ids: selectedProgramasIds,
        };

        const res = await authFetch(`${getApiBaseUrl()}/auth/users/${userToEdit.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({ detail: "Error al actualizar usuario" }));
          throw new Error(data.detail || "Error al actualizar");
        }
      } else {
        const payload = {
          email: email.trim().toLowerCase(),
          password,
          password_confirmation: passwordConfirmation,
          nombre: nombre.trim(),
          apellido: apellido.trim(),
          telefono: telefono.trim() || null,
          area: area.trim() || null,
          roles: [selectedRole],
          coordinacion_id: selectedCoordId || null,
          especialidad_id: selectedEspId || null,
          programas_ids: selectedProgramasIds,
        };

        const res = await authFetch(`${getApiBaseUrl()}/auth/users`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({ detail: "Error al crear usuario" }));
          throw new Error(data.detail || "Error al crear usuario");
        }
      }

      onSuccess();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al guardar usuario");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="user-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
    >
      <div className="w-full max-w-xl max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
          <div>
            <h2 id="user-dialog-title" className="text-lg font-bold text-slate-900 dark:text-white">
              {isEditing ? "Editar Usuario" : "Nuevo Usuario Institucional"}
            </h2>
            <p className="text-xs text-slate-500">Gestión de identidad, roles y ámbito académico</p>
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
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                Nombres *
              </label>
              <input
                type="text"
                required
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder="Carlos"
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                Apellidos *
              </label>
              <input
                type="text"
                required
                value={apellido}
                onChange={(e) => setApellido(e.target.value)}
                placeholder="Pérez"
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                Correo Institucional *
              </label>
              <input
                type="email"
                required
                disabled={isEditing}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="cperez@sena.edu.co"
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 disabled:bg-slate-100 disabled:text-slate-500 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-800/50"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                Teléfono {requiresOrg ? "*" : ""}
              </label>
              <input
                type="text"
                required={requiresOrg}
                value={telefono}
                onChange={(e) => setTelefono(e.target.value)}
                placeholder="310 123 4567"
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                Área / Dependencia {requiresOrg ? "*" : ""}
              </label>
              <input
                type="text"
                required={requiresOrg}
                value={area}
                onChange={(e) => setArea(e.target.value)}
                placeholder="Teleinformática / Redes"
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                Rol de Sistema *
              </label>
              <select
                value={selectedRole}
                onChange={(e) => setSelectedRole(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              >
                <option value="LIDER_EQUIPO_EJECUTOR">LÍDER EQUIPO EJECUTOR</option>
                <option value="USUARIO_ADICIONAL">USUARIO ADICIONAL</option>
                {isSuperAdmin && <option value="ADMIN">ADMINISTRADOR</option>}
                {isSuperAdmin && <option value="SUPERADMIN">SUPERADMINISTRADOR</option>}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                Coordinación Académica {requiresOrg ? "*" : ""}
              </label>
              <select
                value={selectedCoordId}
                onChange={(e) => setSelectedCoordId(e.target.value)}
                required={requiresOrg}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              >
                <option value="">Seleccione coordinación...</option>
                {coordinaciones.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.codigo} — {c.nombre}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <div className="flex items-center justify-between">
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                  Especialidad Académica {requiresOrg ? "*" : ""}
                </label>
                {selectedCoordId && (
                  <button
                    type="button"
                    onClick={() => setShowNewEspModal(true)}
                    className="text-[11px] font-semibold text-emerald-600 hover:text-emerald-700 dark:text-emerald-400 hover:underline"
                  >
                    + Nueva especialidad
                  </button>
                )}
              </div>
              <select
                value={selectedEspId}
                onChange={(e) => setSelectedEspId(e.target.value)}
                disabled={!selectedCoordId}
                required={requiresOrg}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 disabled:bg-slate-100 disabled:text-slate-400 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-800/50"
              >
                <option value="">
                  {selectedCoordId ? "Seleccione especialidad..." : "Seleccione primero coordinación"}
                </option>
                {especialidades.map((esp) => (
                  <option key={esp.id} value={esp.id}>
                    {esp.codigo} — {esp.nombre}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {!isEditing && (
            <div className="grid grid-cols-1 gap-3 border-t border-slate-100 pt-3 dark:border-slate-800 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                  Contraseña Inicial *
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Mínimo 8 caracteres"
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                  Confirmar Contraseña *
                </label>
                <input
                  type="password"
                  required
                  value={passwordConfirmation}
                  onChange={(e) => setPasswordConfirmation(e.target.value)}
                  placeholder="Repetir contraseña"
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                />
              </div>
            </div>
          )}

          {/* Programas de Formación Autorizados */}
          <div className="border-t border-slate-100 pt-3 dark:border-slate-800">
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                Programas de Formación Autorizados ({selectedProgramasIds.length})
              </label>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setSelectedProgramasIds(programasCatalogo.map((p) => p.id))}
                  className="text-[11px] font-semibold text-emerald-600 hover:text-emerald-700 dark:text-emerald-400 hover:underline"
                >
                  Seleccionar todos
                </button>
                <span className="text-slate-300 dark:text-slate-700">|</span>
                <button
                  type="button"
                  onClick={() => setSelectedProgramasIds([])}
                  className="text-[11px] font-semibold text-slate-500 hover:text-slate-700 dark:text-slate-400 hover:underline"
                >
                  Limpiar
                </button>
              </div>
            </div>
            <p className="text-[11px] text-slate-500 mb-2">
              Define los programas curriculares sobre los cuales el usuario tiene permiso para liderar equipos o cargar matrices.
            </p>
            <input
              type="text"
              placeholder="Filtrar por código o nombre..."
              value={programSearch}
              onChange={(e) => setProgramSearch(e.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-800 transition focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 mb-2"
            />
            <div className="max-h-36 overflow-y-auto space-y-1.5 rounded-lg border border-slate-200 bg-slate-50/50 p-2 dark:border-slate-700 dark:bg-slate-800/30">
              {programasCatalogo.length === 0 ? (
                <div className="text-center py-2 text-xs text-slate-400">No hay programas registrados en el catálogo</div>
              ) : (
                programasCatalogo
                  .filter((p) => {
                    const term = programSearch.toLowerCase();
                    return (
                      p.codigo_programa.toLowerCase().includes(term) ||
                      p.nombre_programa.toLowerCase().includes(term)
                    );
                  })
                  .map((p) => {
                    const isSelected = selectedProgramasIds.includes(p.id);
                    return (
                      <label
                        key={p.id}
                        className={`flex items-start gap-2.5 p-2 rounded-lg cursor-pointer border text-xs transition ${
                          isSelected
                            ? "border-emerald-300 bg-emerald-50/70 text-emerald-950 dark:border-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-100"
                            : "border-transparent bg-white hover:bg-slate-100/70 text-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700/50 dark:text-slate-300"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedProgramasIds((prev) => [...prev, p.id]);
                            } else {
                              setSelectedProgramasIds((prev) => prev.filter((id) => id !== p.id));
                            }
                          }}
                          className="mt-0.5 h-3.5 w-3.5 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5">
                            <span className="font-mono font-semibold text-[11px] text-slate-900 dark:text-white">
                              {p.codigo_programa}
                            </span>
                            <span className="text-[10px] rounded bg-slate-100 px-1 py-0.2 font-medium text-slate-500 dark:bg-slate-700 dark:text-slate-300">
                              v{p.version_programa || "1"}
                            </span>
                          </div>
                          <div className="text-[11px] truncate text-slate-600 dark:text-slate-300 mt-0.5">
                            {p.nombre_programa}
                          </div>
                        </div>
                      </label>
                    );
                  })
              )}
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 border-t border-slate-100 pt-4 dark:border-slate-800">
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
              {loading ? "Guardando..." : isEditing ? "Actualizar Usuario" : "Crear Usuario"}
            </button>
          </div>
        </form>
      </div>

      {showNewEspModal && selectedCoordId && (
        <SpecialtyFormDialog
          isOpen={showNewEspModal}
          onClose={() => setShowNewEspModal(false)}
          onSuccess={async (newEsp) => {
            await loadEspecialidades(selectedCoordId);
            if (newEsp?.id) {
              setSelectedEspId(newEsp.id);
            }
          }}
          coordinacionId={selectedCoordId}
          coordinacionNombre={coordinaciones.find((c) => c.id === selectedCoordId)?.nombre}
        />
      )}
    </div>
  );
}
