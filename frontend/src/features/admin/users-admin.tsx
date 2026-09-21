"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Search,
  Plus,
  Edit2,
  KeyRound,
  ShieldCheck,
  Ban,
  UserX,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { User } from "@/features/auth/types";
import { useAuth } from "@/features/auth/auth-context";
import { authFetch, getApiBaseUrl } from "@/lib/api";
import { UserFormDialog } from "./user-form-dialog";
import { UserStatusDialog } from "./user-status-dialog";
import { UserResetPasswordDialog } from "./user-reset-password-dialog";

interface PaginatedUsersResponse {
  items: User[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

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

interface UsersAdminProps {
  currentUser?: User | null;
}

export function UsersAdmin({ currentUser: propUser }: UsersAdminProps = {}): React.JSX.Element {
  const { user: authUser } = useAuth();
  const currentUser = propUser ?? authUser;
  const isSuperAdmin = currentUser?.roles?.includes("SUPERADMIN") ?? false;

  const [users, setUsers] = useState<User[]>([]);
  const [page, setPage] = useState(1);
  const pageSize = 15;
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);

  // Filters
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [estadoFilter, setEstadoFilter] = useState("");
  const [coordFilter, setCoordFilter] = useState("");
  const [espFilter, setEspFilter] = useState("");

  const [coordinaciones, setCoordinaciones] = useState<Coordinacion[]>([]);
  const [especialidades, setEspecialidades] = useState<Especialidad[]>([]);
  const [loading, setLoading] = useState(true);

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [userToEdit, setUserToEdit] = useState<User | null>(null);
  const [userForStatus, setUserForStatus] = useState<User | null>(null);
  const [userForReset, setUserForReset] = useState<User | null>(null);

  // Load coordinations for filter
  useEffect(() => {
    authFetch(`${getApiBaseUrl()}/coordinaciones`)
      .then(async (res) => {
        if (res.ok) setCoordinaciones(await res.json());
      })
      .catch(console.error);
  }, []);

  // Load specialties when coord filter changes
  useEffect(() => {
    if (!coordFilter) {
      setEspecialidades([]);
      setEspFilter("");
      return;
    }
    authFetch(`${getApiBaseUrl()}/coordinaciones/${coordFilter}/especialidades`)
      .then(async (res) => {
        if (res.ok) setEspecialidades(await res.json());
      })
      .catch(console.error);
  }, [coordFilter]);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("page_size", String(pageSize));
      if (search.trim()) params.set("search", search.trim());
      if (roleFilter) params.set("role", roleFilter);
      if (estadoFilter) params.set("estado", estadoFilter);
      if (coordFilter) params.set("coordinacion_id", coordFilter);
      if (espFilter) params.set("especialidad_id", espFilter);

      const res = await authFetch(`${getApiBaseUrl()}/auth/users?${params.toString()}`);
      if (res.ok) {
        const data: PaginatedUsersResponse = await res.json();
        setUsers(data.items || []);
        setTotal(data.total || 0);
        setPages(data.pages || 1);
      }
    } catch (err) {
      console.error("Error loading users:", err);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, roleFilter, estadoFilter, coordFilter, espFilter]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "Nunca";
    const d = new Date(dateStr);
    return isNaN(d.getTime())
      ? dateStr
      : new Intl.DateTimeFormat("es-CO", { dateStyle: "short", timeStyle: "short" }).format(d);
  };

  const renderBadge = (estado: string) => {
    if (estado === "ACTIVO") {
      return (
        <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-600/20 dark:bg-emerald-950/40 dark:text-emerald-400">
          <ShieldCheck className="h-3 w-3" />
          ACTIVO
        </span>
      );
    }
    if (estado === "INACTIVO") {
      return (
        <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-700 ring-1 ring-inset ring-amber-600/20 dark:bg-amber-950/40 dark:text-amber-400">
          <UserX className="h-3 w-3" />
          INACTIVO
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 rounded-md bg-rose-50 px-2 py-0.5 text-xs font-semibold text-rose-700 ring-1 ring-inset ring-rose-600/20 dark:bg-rose-950/40 dark:text-rose-400">
        <Ban className="h-3 w-3" />
        BLOQUEADO
      </span>
    );
  };

  return (
    <div className="space-y-4">
      {/* Top action and filter bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Administración de Usuarios</h2>
          <p className="text-xs text-slate-500">
            Control de identidades, credenciales temporales y adscripción organizacional
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 transition"
        >
          <Plus className="h-4 w-4" />
          Nuevo Usuario
        </button>
      </div>

      {/* Filter toolbar */}
      <div className="grid grid-cols-1 gap-2.5 rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm dark:border-slate-800 dark:bg-slate-900 md:grid-cols-5">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Buscar por nombre, correo, área..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full rounded-lg border border-slate-300 bg-white py-1.5 pl-8 pr-3 text-xs text-slate-900 placeholder-slate-400 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
          />
        </div>

        <div>
          <select
            value={roleFilter}
            onChange={(e) => {
              setRoleFilter(e.target.value);
              setPage(1);
            }}
            className="w-full rounded-lg border border-slate-300 bg-white py-1.5 px-2.5 text-xs text-slate-900 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
          >
            <option value="">Todos los roles</option>
            <option value="SUPERADMIN">SUPERADMIN</option>
            <option value="ADMIN">ADMIN</option>
            <option value="LIDER_EQUIPO_EJECUTOR">LÍDER EQUIPO</option>
            <option value="USUARIO_ADICIONAL">USUARIO ADICIONAL</option>
          </select>
        </div>

        <div>
          <select
            value={estadoFilter}
            onChange={(e) => {
              setEstadoFilter(e.target.value);
              setPage(1);
            }}
            className="w-full rounded-lg border border-slate-300 bg-white py-1.5 px-2.5 text-xs text-slate-900 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
          >
            <option value="">Todos los estados</option>
            <option value="ACTIVO">ACTIVO</option>
            <option value="INACTIVO">INACTIVO</option>
            <option value="BLOQUEADO">BLOQUEADO</option>
          </select>
        </div>

        <div>
          <select
            value={coordFilter}
            onChange={(e) => {
              setCoordFilter(e.target.value);
              setPage(1);
            }}
            className="w-full rounded-lg border border-slate-300 bg-white py-1.5 px-2.5 text-xs text-slate-900 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
          >
            <option value="">Todas las coordinaciones</option>
            {coordinaciones.map((c) => (
              <option key={c.id} value={c.id}>
                {c.codigo}
              </option>
            ))}
          </select>
        </div>

        <div>
          <select
            value={espFilter}
            onChange={(e) => {
              setEspFilter(e.target.value);
              setPage(1);
            }}
            disabled={!coordFilter}
            className="w-full rounded-lg border border-slate-300 bg-white py-1.5 px-2.5 text-xs text-slate-900 disabled:bg-slate-100 disabled:text-slate-400 focus:border-emerald-600 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-800/50"
          >
            <option value="">Todas las especialidades</option>
            {especialidades.map((esp) => (
              <option key={esp.id} value={esp.id}>
                {esp.codigo}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Users table */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/75 dark:border-slate-800 dark:bg-slate-800/50 text-slate-600 dark:text-slate-400 font-semibold uppercase tracking-wider">
                <th className="py-3 px-4">Usuario / Email</th>
                <th className="py-3 px-4">Teléfono / Área</th>
                <th className="py-3 px-4">Rol</th>
                <th className="py-3 px-4">Coordinación & Especialidad</th>
                <th className="py-3 px-4">Estado</th>
                <th className="py-3 px-4">Último Acceso</th>
                <th className="py-3 px-4 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 font-medium">
                    Cargando usuarios...
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 font-medium">
                    No se encontraron usuarios con los filtros aplicados.
                  </td>
                </tr>
              ) : (
                users.map((u) => {
                  const targetIsSuperAdmin = u.roles?.includes("SUPERADMIN");
                  const canManageTarget = isSuperAdmin || !targetIsSuperAdmin;

                  return (
                    <tr key={u.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900 dark:text-white">
                          {u.nombre} {u.apellido}
                        </div>
                        <div className="text-[11px] text-slate-500">{u.email}</div>
                        {u.debe_cambiar_password && (
                          <span className="mt-1 inline-flex items-center gap-1 rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-950/40 dark:text-amber-400">
                            Clave temporal
                          </span>
                        )}
                      </td>

                      <td className="py-3 px-4 text-slate-600 dark:text-slate-300">
                        <div>{u.telefono || "—"}</div>
                        <div className="text-[11px] text-slate-400">{u.area || "—"}</div>
                      </td>

                      <td className="py-3 px-4">
                        <span className="inline-flex rounded-md bg-slate-100 px-2 py-0.5 font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                          {u.roles?.join(", ") || "SIN ROL"}
                        </span>
                      </td>

                      <td className="py-3 px-4 text-slate-600 dark:text-slate-300">
                        {u.coordinacion ? (
                          <div>
                            <span className="font-semibold text-slate-800 dark:text-slate-200">
                              {u.coordinacion.codigo}
                            </span>
                            {u.especialidad && (
                              <span className="text-slate-500"> / {u.especialidad.codigo}</span>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400">Global / Sin asignar</span>
                        )}
                      </td>

                      <td className="py-3 px-4">{renderBadge(u.estado || (u.activo ? "ACTIVO" : "INACTIVO"))}</td>

                      <td className="py-3 px-4 text-slate-500 text-[11px]">{formatDate(u.ultimo_acceso)}</td>

                      <td className="py-3 px-4 text-right">
                        {canManageTarget ? (
                          <div className="inline-flex items-center gap-1">
                            <button
                              type="button"
                              onClick={() => setUserToEdit(u)}
                              title="Editar usuario"
                              className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800"
                            >
                              <Edit2 className="h-3.5 w-3.5" />
                            </button>

                            <button
                              type="button"
                              onClick={() => setUserForStatus(u)}
                              title="Cambiar estado"
                              className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800"
                            >
                              <ShieldCheck className="h-3.5 w-3.5" />
                            </button>

                            <button
                              type="button"
                              onClick={() => setUserForReset(u)}
                              title="Restablecer contraseña"
                              className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800"
                            >
                              <KeyRound className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        ) : (
                          <span className="text-[11px] italic text-slate-400">Protegido</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination controls */}
        <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 dark:border-slate-800">
          <div className="text-xs text-slate-500">
            Total: <span className="font-semibold text-slate-800 dark:text-slate-200">{total}</span> usuarios
            {pages > 1 && (
              <span>
                {" "}
                (Página {page} de {pages})
              </span>
            )}
          </div>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(p - 1, 1))}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-40 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              Anterior
            </button>
            <button
              type="button"
              disabled={page >= pages}
              onClick={() => setPage((p) => Math.min(p + 1, pages))}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-40 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Siguiente
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Modal dialogs */}
      <UserFormDialog
        isOpen={showCreateModal || !!userToEdit}
        onClose={() => {
          setShowCreateModal(false);
          setUserToEdit(null);
        }}
        onSuccess={loadUsers}
        userToEdit={userToEdit}
        isSuperAdmin={isSuperAdmin}
      />

      <UserStatusDialog
        isOpen={!!userForStatus}
        onClose={() => setUserForStatus(null)}
        onSuccess={loadUsers}
        user={userForStatus}
      />

      <UserResetPasswordDialog
        isOpen={!!userForReset}
        onClose={() => setUserForReset(null)}
        onSuccess={loadUsers}
        user={userForReset}
      />
    </div>
  );
}
