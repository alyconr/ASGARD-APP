"use client";

import React, { useState } from "react";
import { Users, Building2, Shield, Network } from "lucide-react";
import { UsersAdmin } from "./users-admin";
import { OrganizationAdmin } from "./organization-admin";
import { EquiposAdmin } from "./equipos-admin";
import { cn } from "@/lib/utils";

type AdminTab = "usuarios" | "organizacion" | "equipos";

interface AdminWorkspaceProps {
  initialTab?: AdminTab;
}

export function AdminWorkspace({ initialTab = "usuarios" }: AdminWorkspaceProps): React.JSX.Element {
  const [activeTab, setActiveTab] = useState<AdminTab>(initialTab);

  return (
    <div className="space-y-6">
      {/* Workspace Banner */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400">
              <Shield className="h-5 w-5" />
              <span className="text-xs font-bold uppercase tracking-wider">
                Módulo de Administración Organizacional
              </span>
            </div>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              Administración Central ASGARD
            </h1>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 max-w-2xl">
              Gestión multiusuario, catálogo de coordinaciones y especialidades, y control de equipos ejecutores bajo el modelo de alcance curricular.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              Control RBAC Estricto
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
              <span className="h-2 w-2 rounded-full bg-sky-500" />
              Ámbito Multiusuario
            </span>
          </div>
        </div>

        {/* Workspace Navigation Tabs */}
        <div className="mt-6 flex border-b border-slate-200 gap-2 sm:gap-6 overflow-x-auto dark:border-slate-800">
          <button
            type="button"
            onClick={() => setActiveTab("usuarios")}
            className={cn(
              "inline-flex items-center gap-2 pb-3 text-xs sm:text-sm font-semibold border-b-2 -mb-px transition whitespace-nowrap",
              activeTab === "usuarios"
                ? "border-emerald-600 text-emerald-700 dark:border-emerald-400 dark:text-emerald-400"
                : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            )}
          >
            <Users className="h-4 w-4" />
            Usuarios y Credenciales
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("organizacion")}
            className={cn(
              "inline-flex items-center gap-2 pb-3 text-xs sm:text-sm font-semibold border-b-2 -mb-px transition whitespace-nowrap",
              activeTab === "organizacion"
                ? "border-emerald-600 text-emerald-700 dark:border-emerald-400 dark:text-emerald-400"
                : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            )}
          >
            <Building2 className="h-4 w-4" />
            Coordinaciones & Especialidades
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("equipos")}
            className={cn(
              "inline-flex items-center gap-2 pb-3 text-xs sm:text-sm font-semibold border-b-2 -mb-px transition whitespace-nowrap",
              activeTab === "equipos"
                ? "border-emerald-600 text-emerald-700 dark:border-emerald-400 dark:text-emerald-400"
                : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            )}
          >
            <Network className="h-4 w-4" />
            Equipos Ejecutores & Procesos
          </button>
        </div>
      </div>

      {/* Tab Panels */}
      <div>
        {activeTab === "usuarios" && <UsersAdmin />}
        {activeTab === "organizacion" && <OrganizationAdmin />}
        {activeTab === "equipos" && <EquiposAdmin />}
      </div>
    </div>
  );
}
