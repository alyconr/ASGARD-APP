"use client";

import React from "react";
import { FolderGit2, BookOpen, Layers, GraduationCap } from "lucide-react";
import { AdminDashboardResumen } from "../types";

interface SummaryCardsProps {
  resumen: AdminDashboardResumen | null;
  loading: boolean;
}

export function SummaryCards({ resumen, loading }: SummaryCardsProps): React.JSX.Element {
  if (loading || !resumen) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-32 animate-pulse rounded-2xl border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900/50"
          />
        ))}
      </div>
    );
  }

  const planeacionesPct =
    resumen.planeaciones_totales > 0
      ? Math.round((resumen.planeaciones_completo / resumen.planeaciones_totales) * 100)
      : 0;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {/* 1. Procesos Curriculares */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Procesos Curriculares
          </span>
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400">
            <FolderGit2 className="h-5 w-5" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            {resumen.procesos_totales}
          </span>
          <span className="text-xs text-slate-500">en total</span>
        </div>
        <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3 text-xs dark:border-slate-800">
          <div className="flex items-center gap-1.5 text-emerald-700 dark:text-emerald-400">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            <span>Asignados: <strong>{resumen.procesos_asignados}</strong></span>
          </div>
          <div className="flex items-center gap-1.5 text-amber-700 dark:text-amber-400">
            <span className="h-2 w-2 rounded-full bg-amber-500" />
            <span>Sin asignar: <strong>{resumen.procesos_sin_asignar}</strong></span>
          </div>
        </div>
      </div>

      {/* 2. Programas de Formación */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Programas Formación
          </span>
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-50 text-sky-600 dark:bg-sky-950/60 dark:text-sky-400">
            <GraduationCap className="h-5 w-5" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            {resumen.programas_completo + resumen.programas_en_revision + resumen.programas_borrador}
          </span>
          <span className="text-xs text-slate-500">en curso</span>
        </div>
        <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3 text-xs dark:border-slate-800">
          <span className="text-emerald-700 dark:text-emerald-400 font-medium">
            Completo: {resumen.programas_completo}
          </span>
          <span className="text-sky-700 dark:text-sky-400 font-medium">
            Revisión: {resumen.programas_en_revision}
          </span>
          <span className="text-slate-500 font-medium">
            Borrador: {resumen.programas_borrador}
          </span>
        </div>
      </div>

      {/* 3. Proyectos Formativos */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Proyectos Formativos
          </span>
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400">
            <BookOpen className="h-5 w-5" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            {resumen.proyectos_completo + resumen.proyectos_en_revision + resumen.proyectos_borrador + resumen.proyectos_bloqueado}
          </span>
          <span className="text-xs text-slate-500">vinculados</span>
        </div>
        <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3 text-xs dark:border-slate-800">
          <span className="text-emerald-700 dark:text-emerald-400 font-medium">
            Completo: {resumen.proyectos_completo}
          </span>
          <span className="text-slate-500 font-medium">
            Borrador: {resumen.proyectos_borrador}
          </span>
          <span className="text-rose-600 dark:text-rose-400 font-medium">
            Bloqueado: {resumen.proyectos_bloqueado}
          </span>
        </div>
      </div>

      {/* 4. Planeaciones Pedagógicas */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Planeaciones Pedagógicas
          </span>
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-50 text-violet-600 dark:bg-violet-950/60 dark:text-violet-400">
            <Layers className="h-5 w-5" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            {resumen.planeaciones_totales}
          </span>
          <span className="text-xs text-emerald-600 dark:text-emerald-400 font-semibold">
            {planeacionesPct}% completas
          </span>
        </div>
        <div className="mt-3 space-y-1.5 border-t border-slate-100 pt-3 text-xs dark:border-slate-800">
          <div className="flex justify-between text-slate-600 dark:text-slate-400">
            <span>Completas: <strong>{resumen.planeaciones_completo}</strong></span>
            <span>Borrador: <strong>{resumen.planeaciones_borrador}</strong></span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden dark:bg-slate-800">
            <div
              className="h-full rounded-full bg-emerald-500 transition-all duration-300"
              style={{ width: `${planeacionesPct}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
