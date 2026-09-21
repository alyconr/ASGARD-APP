"use client";

import React, { useEffect, useState } from "react";
import { Search, RotateCcw } from "lucide-react";
import { authFetch, getApiBaseUrl } from "@/lib/api";
import { SupervisionFilters } from "../types";

interface CoordinacionItem {
  id: string;
  codigo: string;
  nombre: string;
}

interface EspecialidadItem {
  id: string;
  coordinacion_id: string;
  codigo: string;
  nombre: string;
}

interface EquipoItem {
  id: string;
  nombre: string;
  especialidad_id: string;
}

interface ProcessFiltersProps {
  filters: SupervisionFilters;
  onFilterChange: (newFilters: SupervisionFilters) => void;
  onReset: () => void;
}

export function ProcessFilters({
  filters,
  onFilterChange,
  onReset,
}: ProcessFiltersProps): React.JSX.Element {
  const [coordinaciones, setCoordinaciones] = useState<CoordinacionItem[]>([]);
  const [especialidades, setEspecialidades] = useState<EspecialidadItem[]>([]);
  const [equipos, setEquipos] = useState<EquipoItem[]>([]);

  // Load coordinaciones
  useEffect(() => {
    authFetch(`${getApiBaseUrl()}/coordinaciones?solo_activas=true`)
      .then(async (res) => {
        if (res.ok) setCoordinaciones(await res.json());
      })
      .catch(console.error);
  }, []);

  // Load especialidades when coordinacion changes
  useEffect(() => {
    if (!filters.coordinacion_id) {
      setEspecialidades([]);
      return;
    }
    authFetch(`${getApiBaseUrl()}/coordinaciones/${filters.coordinacion_id}/especialidades?solo_activas=true`)
      .then(async (res) => {
        if (res.ok) setEspecialidades(await res.json());
      })
      .catch(console.error);
  }, [filters.coordinacion_id]);

  // Load equipos when especialidad changes
  useEffect(() => {
    if (!filters.especialidad_id) {
      setEquipos([]);
      return;
    }
    authFetch(`${getApiBaseUrl()}/equipos?especialidad_id=${filters.especialidad_id}&solo_activos=true`)
      .then(async (res) => {
        if (res.ok) {
          const data = await res.json();
          setEquipos(data.items || []);
        }
      })
      .catch(console.error);
  }, [filters.especialidad_id]);

  const hasActiveFilters = Boolean(
    filters.search ||
      filters.coordinacion_id ||
      filters.especialidad_id ||
      filters.equipo_ejecutor_id ||
      filters.estado_scope ||
      filters.solo_sin_asignar
  );

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-4">
      <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        {/* Search bar */}
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Buscar por código Sofía, programa, proyecto, equipo o líder..."
            value={filters.search || ""}
            onChange={(e) => onFilterChange({ ...filters, search: e.target.value })}
            className="w-full rounded-xl border border-slate-200 bg-slate-50 pl-10 pr-4 py-2 text-xs md:text-sm text-slate-900 placeholder:text-slate-400 focus:border-emerald-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-emerald-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:focus:bg-slate-900"
          />
        </div>

        {/* Solo sin asignar toggle */}
        <label className="flex items-center gap-2 cursor-pointer select-none text-xs font-semibold text-slate-700 dark:text-slate-300">
          <input
            type="checkbox"
            checked={Boolean(filters.solo_sin_asignar)}
            onChange={(e) =>
              onFilterChange({
                ...filters,
                solo_sin_asignar: e.target.checked,
                estado_scope: e.target.checked ? undefined : filters.estado_scope,
              })
            }
            className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 dark:border-slate-700 dark:bg-slate-800"
          />
          <span>Solo sin asignar</span>
        </label>

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

      {/* Cascading dropdown selectors */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2 border-t border-slate-100 dark:border-slate-800">
        {/* Coordinación */}
        <div>
          <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
            Coordinación
          </label>
          <select
            value={filters.coordinacion_id || ""}
            onChange={(e) =>
              onFilterChange({
                ...filters,
                coordinacion_id: e.target.value || undefined,
                especialidad_id: undefined,
                equipo_ejecutor_id: undefined,
              })
            }
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-800 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          >
            <option value="">Todas las coordinaciones</option>
            {coordinaciones.map((c) => (
              <option key={c.id} value={c.id}>
                {c.codigo} - {c.nombre}
              </option>
            ))}
          </select>
        </div>

        {/* Especialidad */}
        <div>
          <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
            Especialidad
          </label>
          <select
            value={filters.especialidad_id || ""}
            onChange={(e) =>
              onFilterChange({
                ...filters,
                especialidad_id: e.target.value || undefined,
                equipo_ejecutor_id: undefined,
              })
            }
            disabled={!filters.coordinacion_id}
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-800 disabled:opacity-50 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          >
            <option value="">
              {filters.coordinacion_id ? "Todas las especialidades" : "Selecciona coordinación"}
            </option>
            {especialidades.map((esp) => (
              <option key={esp.id} value={esp.id}>
                {esp.codigo} - {esp.nombre}
              </option>
            ))}
          </select>
        </div>

        {/* Equipo Ejecutor */}
        <div>
          <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
            Equipo Ejecutor
          </label>
          <select
            value={filters.equipo_ejecutor_id || ""}
            onChange={(e) =>
              onFilterChange({
                ...filters,
                equipo_ejecutor_id: e.target.value || undefined,
              })
            }
            disabled={!filters.especialidad_id}
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-800 disabled:opacity-50 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          >
            <option value="">
              {filters.especialidad_id ? "Todos los equipos" : "Selecciona especialidad"}
            </option>
            {equipos.map((eq) => (
              <option key={eq.id} value={eq.id}>
                {eq.nombre}
              </option>
            ))}
          </select>
        </div>

        {/* Estado Scope */}
        <div>
          <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
            Estado de Asignación
          </label>
          <select
            value={filters.estado_scope || ""}
            onChange={(e) =>
              onFilterChange({
                ...filters,
                estado_scope: e.target.value || undefined,
                solo_sin_asignar: false,
              })
            }
            disabled={Boolean(filters.solo_sin_asignar)}
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-800 disabled:opacity-50 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          >
            <option value="">Todos los estados</option>
            <option value="ASIGNADO">ASIGNADO</option>
            <option value="SIN_ASIGNAR">SIN ASIGNAR</option>
            <option value="CERRADO">CERRADO</option>
          </select>
        </div>
      </div>
    </div>
  );
}
