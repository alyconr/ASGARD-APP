"use client";

import React from "react";
import { Search, RotateCcw } from "lucide-react";
import { AuditFilters } from "../types";

interface AuditFiltersProps {
  filters: AuditFilters;
  onFilterChange: (newFilters: AuditFilters) => void;
  onReset: () => void;
}

export function AuditFiltersComponent({
  filters,
  onFilterChange,
  onReset,
}: AuditFiltersProps): React.JSX.Element {
  const hasActiveFilters = Boolean(
    filters.search ||
      filters.accion ||
      filters.entidad ||
      filters.fecha_desde ||
      filters.fecha_hasta
  );

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-4">
      <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        {/* Search bar */}
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Buscar por acción o entidad..."
            value={filters.search || ""}
            onChange={(e) => onFilterChange({ ...filters, search: e.target.value })}
            className="w-full rounded-xl border border-slate-200 bg-slate-50 pl-10 pr-4 py-2 text-xs md:text-sm text-slate-900 placeholder:text-slate-400 focus:border-emerald-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-emerald-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:focus:bg-slate-900"
          />
        </div>

        {hasActiveFilters && (
          <button
            type="button"
            onClick={onReset}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50 hover:text-slate-900 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Limpiar filtros
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2 border-t border-slate-100 dark:border-slate-800">
        {/* Fecha Desde */}
        <div>
          <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
            Fecha Desde
          </label>
          <div className="relative">
            <input
              type="date"
              value={filters.fecha_desde || ""}
              onChange={(e) => onFilterChange({ ...filters, fecha_desde: e.target.value || undefined })}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-800 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            />
          </div>
        </div>

        {/* Fecha Hasta */}
        <div>
          <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
            Fecha Hasta
          </label>
          <div className="relative">
            <input
              type="date"
              value={filters.fecha_hasta || ""}
              onChange={(e) => onFilterChange({ ...filters, fecha_hasta: e.target.value || undefined })}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-800 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            />
          </div>
        </div>

        {/* Acción */}
        <div>
          <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
            Acción
          </label>
          <select
            value={filters.accion || ""}
            onChange={(e) => onFilterChange({ ...filters, accion: e.target.value || undefined })}
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-800 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          >
            <option value="">Todas las acciones</option>
            <option value="CREAR_USUARIO">CREAR_USUARIO</option>
            <option value="EDITAR_USUARIO">EDITAR_USUARIO</option>
            <option value="CAMBIAR_ESTADO_USUARIO">CAMBIAR_ESTADO_USUARIO</option>
            <option value="RESET_PASSWORD_ADMIN">RESET_PASSWORD_ADMIN</option>
            <option value="CREAR_COORDINACION">CREAR_COORDINACION</option>
            <option value="EDITAR_COORDINACION">EDITAR_COORDINACION</option>
            <option value="CREAR_ESPECIALIDAD">CREAR_ESPECIALIDAD</option>
            <option value="EDITAR_ESPECIALIDAD">EDITAR_ESPECIALIDAD</option>
            <option value="CREAR_EQUIPO">CREAR_EQUIPO</option>
            <option value="EDITAR_EQUIPO">EDITAR_EQUIPO</option>
            <option value="CAMBIAR_LIDER_EQUIPO">CAMBIAR_LIDER_EQUIPO</option>
            <option value="ASIGNAR_PROCESO">ASIGNAR_PROCESO</option>
          </select>
        </div>

        {/* Entidad */}
        <div>
          <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
            Entidad Afectada
          </label>
          <select
            value={filters.entidad || ""}
            onChange={(e) => onFilterChange({ ...filters, entidad: e.target.value || undefined })}
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-800 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          >
            <option value="">Todas las entidades</option>
            <option value="Usuario">Usuario</option>
            <option value="Coordinacion">Coordinación</option>
            <option value="Especialidad">Especialidad</option>
            <option value="EquipoEjecutor">Equipo Ejecutor</option>
            <option value="EquipoEjecutorMiembro">Miembro de Equipo</option>
            <option value="ProcesoCurricular">Proceso Curricular</option>
          </select>
        </div>
      </div>
    </div>
  );
}
