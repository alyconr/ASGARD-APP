"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  BarChart3,
  BookOpenCheck,
  CalendarClock,
  Check,
  Copy,
  GitBranch,
  ListChecks,
  LockKeyhole,
  Network,
  Plus,
  RefreshCcw,
  Route,
  Sparkles,
  Trash2,
  LogOut,
  Shield,
  History,
} from "lucide-react";

import { useAuth } from "@/features/auth/auth-context";
import { ForceChangePasswordDialog } from "@/features/auth/force-change-password-dialog";
import { AdminWorkspace } from "@/features/admin/admin-workspace";
import { ProcesoHistorialDialog } from "@/features/dashboard/components/proceso-historial-dialog";
import { authFetch, getApiBaseUrl } from "@/lib/api";
import { notify } from "@/components/feedback/notifications";

import {
  deleteProgramFlow,
  fetchDashboard,
  fetchProgramFlows,
  type DashboardModule,
  type DashboardProgramFlow,
  type DashboardResponse,
} from "@/features/dashboard/dashboard-api";
import {
  clearActiveProgramaDraftReference,
  clearActiveProyectoDraftReference,
  forgetProgramaDraft,
  forgetProyectoDraft,
  getActiveProgramaDraftReference,
  listKnownProgramaDrafts,
  setActiveProgramaDraftReference,
  type KnownDraftSummary,
} from "@/features/drafts/storage";
import { useConfirm } from "@/components/feedback/confirm-context";
import { cn } from "@/lib/utils";

function formatReferenceId(referenceId: string): string {
  return referenceId.length > 18
    ? `${referenceId.slice(0, 8)}-${referenceId.slice(9, 13)}...`
    : referenceId;
}

function moduleIcon(moduleId: string): React.ComponentType<{ className?: string }> {
  if (moduleId === "proyecto") return Route;
  if (moduleId === "planeacion") return Network;
  return BookOpenCheck;
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function ModuleCard({
  module,
  referenceId,
}: Readonly<{
  module: DashboardModule;
  referenceId: string | null;
}>): React.JSX.Element {
  const Icon = moduleIcon(module.id);
  const canOpen = module.disponible && (module.id === "programa" || referenceId);
  const href =
    module.id === "programa"
      ? referenceId
        ? `/programa?referencia_id=${referenceId}`
        : "/programa"
      : module.href;

  return (
    <article
      className={cn(
        "grid gap-4 rounded-lg border bg-white p-5 shadow-[0_16px_38px_rgba(24,51,45,0.07)]",
        module.disponible ? "border-emerald-200" : "border-slate-200",
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <span
          className={cn(
            "inline-flex h-11 w-11 items-center justify-center rounded-lg",
            module.disponible
              ? "bg-emerald-50 text-emerald-700"
              : "bg-slate-100 text-slate-500",
          )}
        >
          <Icon className="h-5 w-5" />
        </span>
        <span
          className={cn(
            "inline-flex min-h-8 items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold",
            module.disponible
              ? "bg-emerald-50 text-emerald-800"
              : "bg-amber-50 text-amber-800",
          )}
        >
          {!module.disponible ? <LockKeyhole className="h-3.5 w-3.5" /> : null}
          {module.disponible ? module.estado : "BLOQUEADO"}
        </span>
      </div>

      <div>
        <h2 className="text-xl font-[family:var(--font-display)] font-semibold text-[var(--foreground)]">
          {module.titulo}
        </h2>
        <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
          {module.descripcion}
        </p>
      </div>

      <div className="grid gap-2">
        <div className="h-2 overflow-hidden rounded-full bg-slate-100">
          <div
            className={cn(
              "h-full rounded-full",
              module.disponible ? "bg-emerald-500" : "bg-amber-400",
            )}
            style={{ width: `${Math.min(module.avance_porcentaje, 100)}%` }}
          />
        </div>
        <p className="text-xs font-semibold text-[var(--muted)]">
          {module.avance_porcentaje}% de avance estimado
        </p>
      </div>

      <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-sm leading-6 text-slate-700">
        {module.accion_requerida}
      </div>

      {canOpen ? (
        <Link
          href={href}
          onClick={() => {
            if (referenceId) setActiveProgramaDraftReference(referenceId);
          }}
          className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold !text-white transition hover:bg-[var(--accent-strong)]"
        >
          Abrir modulo
          <ArrowRight className="h-4 w-4" />
        </Link>
      ) : (
        <span className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-semibold text-slate-500">
          No disponible
        </span>
      )}
    </article>
  );
}

function MetricsStrip({
  dashboard,
}: Readonly<{ dashboard: DashboardResponse }>): React.JSX.Element {
  const metrics: Array<[string, number]> = [
    ["Competencias", dashboard.metricas.programa.competencias],
    ["Resultados", dashboard.metricas.programa.resultados],
    ["Conocimientos", dashboard.metricas.programa.conocimientos],
    ["Criterios", dashboard.metricas.programa.criterios],
    ["Fases", dashboard.metricas.proyecto.fases],
    ["Actividades", dashboard.metricas.proyecto.actividades],
    ["Planeaciones", dashboard.metricas.planeacion.total],
    ["Completas", dashboard.metricas.planeacion.completas],
  ];

  return (
    <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {metrics.map(([label, value]) => (
        <div
          key={label}
          className="rounded-lg border border-[color:var(--card-border)] bg-white p-4"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
            {label}
          </p>
          <p className="mt-2 text-3xl font-[family:var(--font-display)] font-semibold text-[var(--foreground)]">
            {value}
          </p>
        </div>
      ))}
    </section>
  );
}

function NavigationMap({
  dashboard,
  referenceId,
}: Readonly<{
  dashboard: DashboardResponse;
  referenceId: string;
}>): React.JSX.Element {
  return (
    <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-5 shadow-[0_16px_38px_rgba(24,51,45,0.06)]">
      <div className="flex items-center gap-2 text-[var(--accent-strong)]">
        <GitBranch className="h-5 w-5" />
        <h2 className="text-lg font-semibold text-[var(--foreground)]">
          Mapa navegable del flujo
        </h2>
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-[repeat(4,minmax(0,1fr))]">
        {dashboard.graph_nodes.map((node) => {
          const content = (
            <div
              className={cn(
                "grid min-h-36 gap-3 rounded-lg border p-4 text-left transition",
                node.disponible
                  ? "border-[var(--accent)] bg-[var(--accent-soft)]/50 hover:bg-white"
                  : "border-slate-200 bg-slate-50",
              )}
            >
              <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                {node.tipo}
              </span>
              <span className="text-lg font-[family:var(--font-display)] font-semibold text-[var(--foreground)]">
                {node.label}
              </span>
              <span className="text-sm leading-5 text-[var(--muted)]">
                {node.detalle}
              </span>
              <span
                className={cn(
                  "mt-auto inline-flex w-fit rounded-lg px-2.5 py-1 text-xs font-semibold",
                  node.disponible
                    ? "bg-emerald-50 text-emerald-800"
                    : "bg-amber-50 text-amber-800",
                )}
              >
                {node.estado}
              </span>
            </div>
          );

          return node.disponible ? (
            <Link
              key={node.id}
              href={node.href}
              onClick={() => setActiveProgramaDraftReference(referenceId)}
            >
              {content}
            </Link>
          ) : (
            <div key={node.id}>{content}</div>
          );
        })}
      </div>

      <div className="mt-4 grid gap-2 border-t border-[var(--line)] pt-4 text-sm text-[var(--muted)] md:grid-cols-3">
        {dashboard.graph_edges.map((edge) => (
          <div key={`${edge.origen}-${edge.destino}`} className="flex gap-2">
            <span
              className={cn(
                "mt-1 h-2 w-2 shrink-0 rounded-full",
                edge.estado === "ACTIVA" ? "bg-emerald-500" : "bg-amber-500",
              )}
            />
            <span>{edge.label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function ProgramFlowsPanel({
  flows,
  activeReference,
  isLoading,
  isDeleting,
  errorMessage,
  onSelect,
  onDelete,
}: Readonly<{
  flows: DashboardProgramFlow[];
  activeReference: string | null;
  isLoading: boolean;
  isDeleting: boolean;
  errorMessage: string | null;
  onSelect: (referenceId: string) => void;
  onDelete: (referenceId: string) => void;
}>): React.JSX.Element {
  const selectedFlow =
    flows.find((flow) => flow.referencia_id === activeReference) ?? flows[0];

  return (
    <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-5 shadow-[0_16px_38px_rgba(24,51,45,0.06)]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-[var(--accent-strong)]">
          <ListChecks className="h-5 w-5" />
          <h2 className="text-lg font-semibold text-[var(--foreground)]">
            Flujos abiertos de programa
          </h2>
        </div>
        {isLoading ? (
          <span className="inline-flex items-center gap-2 rounded-lg bg-[var(--paper-strong)] px-3 py-1.5 text-xs font-semibold text-[var(--muted)]">
            <RefreshCcw className="h-3.5 w-3.5 animate-spin" />
            Actualizando
          </span>
        ) : null}
      </div>

      {errorMessage ? (
        <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm leading-6 text-amber-900">
          {errorMessage}
        </p>
      ) : null}

      {flows.length === 0 && !isLoading ? (
        <div className="mt-4 rounded-lg border border-dashed border-[color:var(--card-border)] bg-[var(--paper)] px-4 py-5 text-sm leading-6 text-[var(--muted)]">
          No hay flujos abiertos de programa en servidor. Puedes iniciar un
          nuevo programa de formacion desde el panel.
        </div>
      ) : (
        <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
          <label className="block min-w-0">
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
              Seleccionar flujo abierto
            </span>
            <select
              value={selectedFlow?.referencia_id ?? ""}
              onChange={(event) => onSelect(event.target.value)}
              className="mt-2 w-full rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm font-semibold text-[var(--foreground)] outline-none transition focus:border-[var(--accent)]"
            >
              <option value="" disabled>
                Selecciona un programa
              </option>
              {flows.map((flow) => (
                <option key={flow.referencia_id} value={flow.referencia_id}>
                  {flow.titulo} / {flow.estado} / {flow.paso_actual}
                </option>
              ))}
            </select>
          </label>

          <div className="flex flex-wrap gap-2 lg:justify-end">
            <button
              type="button"
              disabled={!selectedFlow}
              onClick={() => {
                if (selectedFlow) onSelect(selectedFlow.referencia_id);
              }}
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-4 py-2 text-sm font-semibold text-[var(--foreground)] transition hover:border-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              <ArrowRight className="h-4 w-4" />
              Retomar
            </button>
            <button
              type="button"
              disabled={!selectedFlow || isDeleting}
              onClick={() => {
                if (selectedFlow) onDelete(selectedFlow.referencia_id);
              }}
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm font-semibold text-red-800 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isDeleting ? (
                <RefreshCcw className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
              Eliminar
            </button>
          </div>

          {selectedFlow ? (
            <div className="rounded-lg border border-[color:var(--card-border)] bg-[var(--paper)] p-4 lg:col-span-2">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={cn(
                    "inline-flex rounded-lg px-2.5 py-1 text-xs font-semibold",
                    selectedFlow.estado === "EN_REVISION"
                      ? "bg-sky-50 text-sky-800"
                      : "bg-emerald-50 text-emerald-800",
                  )}
                >
                  {selectedFlow.estado}
                </span>
                <span className="text-xs font-semibold text-[var(--muted)]">
                  {formatReferenceId(selectedFlow.referencia_id)}
                </span>
                <span className="text-xs font-semibold text-[var(--muted)]">
                  {selectedFlow.paso_actual}
                </span>
                <span className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--muted)]">
                  <CalendarClock className="h-3.5 w-3.5" />
                  {formatDateTime(selectedFlow.ultima_edicion)}
                </span>
              </div>
              <p className="mt-2 truncate text-base font-semibold text-[var(--foreground)]">
                {selectedFlow.titulo}
              </p>
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}

export interface MiEquipoPrograma {
  id: string;
  codigo_programa: string;
  nombre_programa: string;
  programa_id?: string | null;
  activo: boolean;
}

export interface MiEquipoProceso {
  id: string;
  referencia_id: string;
  tipo_necesidad: string;
  estado_scope: string;
  programa_id?: string | null;
  proyecto_id?: string | null;
  programa_nombre?: string | null;
  programa_codigo?: string | null;
  proyecto_nombre?: string | null;
  proyecto_codigo?: string | null;
}

export interface MiEquipo {
  id: string;
  nombre: string;
  estado: string;
  coordinacion_id?: string;
  coordinacion_nombre?: string;
  especialidad_id?: string;
  especialidad_nombre?: string;
  rol_en_equipo: "LIDER" | "MIEMBRO";
  programas_autorizados: MiEquipoPrograma[];
  procesos: MiEquipoProceso[];
}

function CopyButton({ text, label }: { text: string; label?: string }): React.JSX.Element {
  const [copied, setCopied] = useState(false);
  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      type="button"
      onClick={handleCopy}
      title={label || "Copiar referencia"}
      className="inline-flex items-center gap-1 rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-700 dark:hover:bg-slate-700 dark:hover:text-slate-200 transition"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}

function ExecutorTeamWorkspace({
  misEquipos,
  loadingEquipos,
  selectedTeam,
  onSelectTeam,
  onGoToAdmin,
  isAdmin,
  programFlows,
  onSelectFlow,
  onStartProcess,
  iniciandoCodigo,
  onOpenHistorial,
}: Readonly<{
  misEquipos: MiEquipo[];
  loadingEquipos: boolean;
  selectedTeam: MiEquipo | null;
  onSelectTeam: (teamId: string) => void;
  onGoToAdmin: () => void;
  isAdmin: boolean;
  programFlows: DashboardProgramFlow[];
  onSelectFlow: (referenceId: string) => void;
  onStartProcess: (equipoId: string, prog: MiEquipoPrograma) => void;
  iniciandoCodigo: string | null;
  onOpenHistorial?: (referenceId: string) => void;
}>): React.JSX.Element {
  if (loadingEquipos) {
    return (
      <section className="flex min-h-[140px] items-center justify-center rounded-xl border border-[color:var(--card-border)] bg-white p-6 shadow-sm">
        <div className="flex items-center gap-3 text-sm font-semibold text-[var(--muted)]">
          <RefreshCcw className="h-4 w-4 animate-spin text-[var(--accent)]" />
          Cargando tus equipos ejecutores y programas autorizados...
        </div>
      </section>
    );
  }

  if (misEquipos.length === 0) {
    if (isAdmin) {
      return (
        <section className="rounded-xl border border-blue-200 bg-blue-50/70 p-6 text-slate-800 shadow-sm dark:border-blue-900/50 dark:bg-blue-950/30 dark:text-blue-200">
          <div className="flex items-start gap-4">
            <div className="rounded-xl bg-blue-100 p-3 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300">
              <Shield className="h-6 w-6" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                Sin equipos ejecutores asignados
              </h3>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                Como administrador tienes privilegios de gestión de plataforma, pero los procesos curriculares (wizards, carga de matrices de programa o proyecto, y planeación pedagógica) deben originarse obligatoriamente desde un Equipo Ejecutor ACTIVO donde participes como líder o miembro con programas habilitados.
              </p>
              <div className="mt-4 flex gap-3">
                <button
                  type="button"
                  onClick={onGoToAdmin}
                  className="inline-flex items-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)]"
                >
                  <Shield className="h-4 w-4" />
                  Ir a Administración Organizacional
                </button>
              </div>
            </div>
          </div>
        </section>
      );
    }

    return (
      <section className="rounded-xl border border-amber-200 bg-amber-50/70 p-6 text-slate-800 shadow-sm dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
        <div className="flex items-start gap-4">
          <div className="rounded-xl bg-amber-100 p-3 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300">
            <LockKeyhole className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
              Sin asignación de equipo ejecutor
            </h3>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              No te encuentras registrado en ningún Equipo Ejecutor activo. Para construir o continuar procesos curriculares, comunícate con el Equipo Pedagógico o la Coordinación Académica para que se te asigne a un equipo ejecutor y se habiliten los programas de formación correspondientes.
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-[color:var(--card-border)] bg-white p-6 shadow-[0_16px_38px_rgba(24,51,45,0.06)]">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2 text-[var(--accent-strong)]">
            <Network className="h-5 w-5" />
            <h2 className="text-lg font-semibold text-[var(--foreground)]">
              Espacio de trabajo del Equipo Ejecutor
            </h2>
          </div>
          <p className="mt-1 text-xs text-[var(--muted)]">
            Selecciona tu equipo ejecutor para consultar sus programas autorizados e iniciar o continuar procesos curriculares.
          </p>
        </div>
        {misEquipos.length > 1 && (
          <div className="flex flex-wrap gap-2">
            {misEquipos.map((eq) => (
              <button
                key={eq.id}
                type="button"
                onClick={() => onSelectTeam(eq.id)}
                className={cn(
                  "rounded-lg px-3 py-1.5 text-xs font-semibold transition",
                  eq.id === selectedTeam?.id
                    ? "bg-[var(--accent)] text-white shadow-sm"
                    : "border border-slate-200 bg-white text-slate-700 hover:border-[var(--accent)] hover:text-[var(--accent-strong)] dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200",
                )}
              >
                {eq.nombre}
              </button>
            ))}
          </div>
        )}
      </div>

      {selectedTeam && (
        <div className="mt-5 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-100 bg-slate-50/80 p-4 dark:border-slate-800 dark:bg-slate-800/40">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  {selectedTeam.nombre}
                </h3>
                <span
                  className={cn(
                    "rounded px-2 py-0.5 text-xs font-bold",
                    selectedTeam.rol_en_equipo === "LIDER"
                      ? "bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300"
                      : "bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300",
                  )}
                >
                  {selectedTeam.rol_en_equipo === "LIDER" ? "Líder de Equipo" : "Miembro de Equipo"}
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                {[selectedTeam.coordinacion_nombre, selectedTeam.especialidad_nombre]
                  .filter(Boolean)
                  .join(" • ")}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                {selectedTeam.programas_autorizados.length}{" "}
                {selectedTeam.programas_autorizados.length === 1 ? "programa autorizado" : "programas autorizados"}
              </span>
              <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-800 dark:bg-blue-950/60 dark:text-blue-300">
                {selectedTeam.procesos?.length || 0}{" "}
                {(selectedTeam.procesos?.length || 0) === 1 ? "proceso asignado" : "procesos asignados"}
              </span>
            </div>
          </div>

          {/* Procesos Curriculares Asignados al Equipo */}
          <div>
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Procesos Curriculares Asignados al Equipo
              </h4>
              <span className="text-xs text-slate-400">
                {selectedTeam.procesos?.length || 0} asignados
              </span>
            </div>

            {(!selectedTeam.procesos || selectedTeam.procesos.length === 0) ? (
              <div className="mt-3 rounded-xl border border-dashed border-slate-200 bg-slate-50/50 p-5 text-center text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900/40 dark:text-slate-400">
                No hay procesos curriculares preasignados a este equipo. Puedes iniciar uno nuevo desde los programas autorizados abajo.
              </div>
            ) : (
              <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {selectedTeam.procesos.map((proc) => {
                  const matchingFlow = programFlows.find((f) => f.referencia_id === proc.referencia_id);
                  const isCompleted = matchingFlow?.estado === "COMPLETO";

                  return (
                    <div
                      key={proc.referencia_id}
                      className="flex flex-col justify-between rounded-xl border border-blue-200 bg-blue-50/20 p-4 shadow-sm transition hover:border-blue-400 dark:border-blue-900/50 dark:bg-blue-950/10"
                    >
                      <div>
                        <div className="flex items-center justify-between gap-2">
                          <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-bold text-blue-800 dark:bg-blue-950/60 dark:text-blue-300">
                            {proc.tipo_necesidad.replace("_", " ")}
                          </span>
                          <span
                            className={cn(
                              "rounded px-2 py-0.5 text-[11px] font-semibold",
                              isCompleted
                                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                                : "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300",
                            )}
                          >
                            {isCompleted ? "Completo" : (proc.estado_scope === "ASIGNADO" ? "Asignado" : proc.estado_scope)}
                          </span>
                        </div>

                        <h5 className="mt-2.5 font-semibold text-slate-900 dark:text-white text-sm">
                          {proc.programa_codigo
                            ? `${proc.programa_codigo} - ${proc.programa_nombre || ""}`
                            : matchingFlow?.nombre_programa
                              ? `${matchingFlow.codigo_programa || ""} - ${matchingFlow.nombre_programa}`
                              : "Programa de Formación"}
                        </h5>

                        <div className="mt-2 flex items-center justify-between rounded-lg bg-slate-100/80 px-2 py-1 text-[11px] font-mono text-slate-600 dark:bg-slate-800/80 dark:text-slate-300">
                          <span className="truncate" title={proc.referencia_id}>
                            {proc.referencia_id}
                          </span>
                          <CopyButton text={proc.referencia_id} label="Copiar ID del proceso" />
                        </div>
                      </div>

                      <div className="mt-4 border-t border-blue-100 pt-3 dark:border-blue-900/40 flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => onSelectFlow(proc.referencia_id)}
                          className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-[var(--accent)] px-3 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-[var(--accent-strong)]"
                        >
                          Cargar / Continuar
                          <ArrowRight className="h-3.5 w-3.5" />
                        </button>
                        {onOpenHistorial && (
                          <button
                            type="button"
                            onClick={() => onOpenHistorial(proc.referencia_id)}
                            className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                            title="Ver historial de cambios de este proceso"
                          >
                            <History className="h-3.5 w-3.5 text-slate-500" />
                            Historial
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Programas de Formación Autorizados
            </h4>
            {selectedTeam.programas_autorizados.length === 0 ? (
              <div className="mt-3 rounded-xl border border-dashed border-slate-200 bg-slate-50/50 p-6 text-center text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900/40 dark:text-slate-400">
                Este equipo no tiene programas de formación autorizados. Solicita a un administrador o al Equipo Pedagógico la habilitación de los programas correspondientes.
              </div>
            ) : (
              <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {selectedTeam.programas_autorizados.map((prog) => {
                  const existingProcess = selectedTeam.procesos?.find(
                    (p) =>
                      (p.programa_codigo &&
                        p.programa_codigo.trim().toUpperCase() ===
                          prog.codigo_programa.trim().toUpperCase()) ||
                      (p.programa_id &&
                        prog.programa_id &&
                        p.programa_id === prog.programa_id),
                  );
                  const existingFlow = programFlows.find(
                    (f) =>
                      f.codigo_programa?.trim().toUpperCase() ===
                        prog.codigo_programa.trim().toUpperCase() ||
                      (existingProcess &&
                        f.referencia_id === existingProcess.referencia_id),
                  );
                  const activeRef =
                    existingProcess?.referencia_id || existingFlow?.referencia_id;
                  const isCompleted = existingFlow?.estado === "COMPLETO";
                  const isStarting = iniciandoCodigo === prog.codigo_programa;

                  return (
                    <div
                      key={prog.codigo_programa}
                      className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-emerald-300 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-emerald-700"
                    >
                      <div>
                        <div className="flex items-center justify-between gap-2">
                          <span className="rounded bg-emerald-50 px-2 py-0.5 text-xs font-bold text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                            {prog.codigo_programa}
                          </span>
                          {activeRef ? (
                            <span
                              className={cn(
                                "rounded px-2 py-0.5 text-[11px] font-semibold",
                                isCompleted
                                  ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                                  : "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300",
                              )}
                            >
                              {isCompleted ? "Completo" : "En construcción"}
                            </span>
                          ) : (
                            <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                              Sin iniciar
                            </span>
                          )}
                        </div>
                        <h5 className="mt-2 font-semibold text-slate-900 dark:text-white">
                          {prog.nombre_programa}
                        </h5>
                      </div>

                      <div className="mt-4 border-t border-slate-100 pt-3 dark:border-slate-800">
                        {activeRef ? (
                          <button
                            type="button"
                            onClick={() => onSelectFlow(activeRef)}
                            className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-emerald-600 bg-white px-3 py-2 text-xs font-semibold text-emerald-700 transition hover:bg-emerald-50 dark:border-emerald-500 dark:bg-slate-900 dark:text-emerald-400 dark:hover:bg-slate-800"
                          >
                            Continuar proceso
                            <ArrowRight className="h-3.5 w-3.5" />
                          </button>
                        ) : (
                          <button
                            type="button"
                            disabled={isStarting}
                            onClick={() => onStartProcess(selectedTeam.id, prog)}
                            className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:opacity-50"
                          >
                            {isStarting ? (
                              <>
                                <RefreshCcw className="h-3.5 w-3.5 animate-spin" />
                                Iniciando...
                              </>
                            ) : (
                              <>
                                <Plus className="h-3.5 w-3.5" />
                                Iniciar proceso curricular
                              </>
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

export function MasterDashboard(): React.JSX.Element {
  const router = useRouter();
  const confirm = useConfirm();
  const { user, isAuthenticated, logout, hasRole, refreshUser } = useAuth();
  const isAdmin = hasRole("SUPERADMIN", "ADMIN");
  const [knownDrafts, setKnownDrafts] = useState<KnownDraftSummary[]>([]);
  const [programFlows, setProgramFlows] = useState<DashboardProgramFlow[]>([]);
  const [referenceInput, setReferenceInput] = useState("");
  const [activeReference, setActiveReference] = useState<string | null>(null);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingFlows, setIsLoadingFlows] = useState(false);
  const [isDeletingFlow, setIsDeletingFlow] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [flowsErrorMessage, setFlowsErrorMessage] = useState<string | null>(null);

  // Executing teams state
  const [misEquipos, setMisEquipos] = useState<MiEquipo[]>([]);
  const [loadingEquipos, setLoadingEquipos] = useState(false);
  const [selectedTeamId, setSelectedTeamId] = useState<string | null>(null);
  const [iniciandoProcesoCodigo, setIniciandoProcesoCodigo] = useState<string | null>(null);
  const [selectedHistorialRef, setSelectedHistorialRef] = useState<string | null>(null);

  const selectedTeam = useMemo(
    () => misEquipos.find((e) => e.id === selectedTeamId) ?? misEquipos[0] ?? null,
    [misEquipos, selectedTeamId],
  );

  const loadMisEquipos = useCallback(async (): Promise<void> => {
    if (!isAuthenticated || !user || user.debe_cambiar_password || isAdmin) {
      return;
    }
    setLoadingEquipos(true);
    try {
      const res = await authFetch(`${getApiBaseUrl()}/equipos/mis-equipos`);
      if (res.ok) {
        const rawData = await res.json();
        const mapped: MiEquipo[] = (Array.isArray(rawData) ? rawData : []).map((rawItem: unknown) => {
          const item = (rawItem && typeof rawItem === "object" ? rawItem : {}) as Record<string, unknown>;
          const eq = (item.equipo && typeof item.equipo === "object" ? item.equipo : {}) as Record<string, unknown>;
          const coord = (eq.coordinacion && typeof eq.coordinacion === "object" ? eq.coordinacion : {}) as Record<string, unknown>;
          const esp = (eq.especialidad && typeof eq.especialidad === "object" ? eq.especialidad : {}) as Record<string, unknown>;
          return {
            id: String(eq.id || item.id || ""),
            nombre: String(eq.nombre || item.nombre || "Equipo sin nombre"),
            estado: String(eq.estado || item.estado || "ACTIVO"),
            coordinacion_id: (eq.coordinacion_id || item.coordinacion_id || undefined) as string | undefined,
            coordinacion_nombre: (coord.nombre || eq.coordinacion_nombre || item.coordinacion_nombre || undefined) as string | undefined,
            especialidad_id: (eq.especialidad_id || item.especialidad_id || undefined) as string | undefined,
            especialidad_nombre: (esp.nombre || eq.especialidad_nombre || item.especialidad_nombre || undefined) as string | undefined,
            rol_en_equipo: (item.rol_en_equipo === "LIDER" ? "LIDER" : "MIEMBRO") as "LIDER" | "MIEMBRO",
            programas_autorizados: (item.programas_autorizados || eq.programas_autorizados || []) as MiEquipoPrograma[],
            procesos: (item.procesos || eq.procesos || []) as MiEquipoProceso[],
          };
        });
        setMisEquipos(mapped);
        if (mapped.length > 0) {
          setSelectedTeamId((current) => current ?? mapped[0].id);
        }
      }
    } catch (err) {
      console.error("Error loading my teams:", err);
    } finally {
      setLoadingEquipos(false);
    }
  }, [isAuthenticated, user, isAdmin]);

  useEffect(() => {
    void loadMisEquipos();
  }, [loadMisEquipos]);

  const handleIniciarProceso = async (
    equipoId: string,
    prog: { codigo_programa: string; programa_id?: string | null },
  ) => {
    setIniciandoProcesoCodigo(prog.codigo_programa);
    try {
      const res = await authFetch(
        `${getApiBaseUrl()}/equipos/${equipoId}/procesos/iniciar`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            codigo_programa: prog.codigo_programa,
            programa_id: prog.programa_id || undefined,
          }),
        },
      );
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(
          errData.detail?.message ||
            errData.detail ||
            "Error al iniciar el proceso curricular",
        );
      }
      const proceso = await res.json();
      activateReference(proceso.referencia_id);
      await loadProgramFlows();
      router.push("/programa");
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Error al iniciar el proceso curricular";
      notify.error("No se pudo iniciar el proceso", { description: msg });
    } finally {
      setIniciandoProcesoCodigo(null);
    }
  };

  useEffect(() => {
    const drafts = listKnownProgramaDrafts();
    const active = getActiveProgramaDraftReference();
    setKnownDrafts(drafts);
    setActiveReference(active);
    setReferenceInput(active ?? "");
  }, []);

  const loadProgramFlows = useCallback(async (): Promise<DashboardProgramFlow[]> => {
    if (!isAuthenticated || !user || user.debe_cambiar_password || isAdmin || misEquipos.length === 0) {
      return [];
    }

    setIsLoadingFlows(true);
    setFlowsErrorMessage(null);
    try {
      const flows = await fetchProgramFlows();
      setProgramFlows(flows);
      setActiveReference((current) => {
        if (flows.length === 0) {
          clearActiveProgramaDraftReference();
          setReferenceInput("");
          if (typeof window !== "undefined") {
            window.localStorage.removeItem("sena.known-programa-drafts");
          }
          setKnownDrafts([]);
          return null;
        }
        if (current) return current;
        const nextReference = flows[0].referencia_id;
        setReferenceInput(nextReference);
        setActiveProgramaDraftReference(nextReference);
        return nextReference;
      });
      return flows;
    } catch (error: unknown) {
      setFlowsErrorMessage(
        error instanceof Error
          ? error.message
          : "No fue posible cargar los flujos abiertos.",
      );
      return [];
    } finally {
      setIsLoadingFlows(false);
    }
  }, [isAuthenticated, user, isAdmin, misEquipos.length]);

  useEffect(() => {
    if (!isAuthenticated || !user || user.debe_cambiar_password || isAdmin || misEquipos.length === 0) {
      return;
    }
    void loadProgramFlows();
  }, [loadProgramFlows, isAuthenticated, user, isAdmin, misEquipos.length]);

  useEffect(() => {
    if (!isAuthenticated || !user || user.debe_cambiar_password || isAdmin || misEquipos.length === 0) {
      setDashboard(null);
      return;
    }

    if (!activeReference) {
      setDashboard(null);
      return;
    }

    let isActive = true;
    setIsLoading(true);
    setErrorMessage(null);
    void fetchDashboard(activeReference)
      .then((result) => {
        if (isActive) setDashboard(result);
      })
      .catch((error: unknown) => {
        if (!isActive) return;
        setDashboard(null);
        setErrorMessage(
          error instanceof Error
            ? error.message
            : "No fue posible cargar el dashboard maestro.",
        );
        if (
          error instanceof Error &&
          (error.message.includes("403") ||
            error.message.includes("autorización") ||
            error.message.includes("404") ||
            error.message.includes("No existe"))
        ) {
          clearActiveProgramaDraftReference();
          if (activeReference) {
            setKnownDrafts(forgetProgramaDraft(activeReference));
          }
          setActiveReference(null);
          setReferenceInput("");
          setErrorMessage(null);
        }
      })
      .finally(() => {
        if (isActive) setIsLoading(false);
      });

    return () => {
      isActive = false;
    };
  }, [activeReference, isAuthenticated, user, isAdmin, misEquipos.length]);

  const selectedDraft = useMemo(
    () => knownDrafts.find((draft) => draft.referenciaId === activeReference),
    [activeReference, knownDrafts],
  );

  const activateReference = (referenceId: string): void => {
    const cleanReference = referenceId.trim();
    if (!cleanReference) return;
    setActiveReference(cleanReference);
    setReferenceInput(cleanReference);
    setActiveProgramaDraftReference(cleanReference);
  };

  const deleteSelectedProgramFlow = async (referenceId: string): Promise<void> => {
    const selectedFlow = programFlows.find(
      (flow) => flow.referencia_id === referenceId,
    );
    const flowLabel = selectedFlow?.titulo ?? formatReferenceId(referenceId);
    const confirmationValue = selectedFlow?.codigo_programa ?? undefined;
    const confirmed = await confirm({
      title: "Eliminar programa definitivamente",
      message: `Vas a eliminar "${flowLabel}" junto con su estructura curricular, proyecto, planeaciones, borradores y archivos. Esta acción no se puede deshacer.`,
      isDestructive: true,
      confirmLabel: "Eliminar definitivamente",
      details: [
        {
          label: "Nombre del programa",
          value: selectedFlow?.nombre_programa ?? "Sin nombre importado",
        },
        {
          label: "Código del programa",
          value: selectedFlow?.codigo_programa ?? "Sin código importado",
        },
      ],
      requiredConfirmationText: confirmationValue,
    });
    if (!confirmed) return;

    setIsDeletingFlow(true);
    setFlowsErrorMessage(null);
    void deleteProgramFlow(referenceId)
      .then(async () => {
        setKnownDrafts(forgetProgramaDraft(referenceId));
        forgetProyectoDraft(referenceId);
        setProgramFlows((current) =>
          current.filter((flow) => flow.referencia_id !== referenceId),
        );
        if (activeReference === referenceId) {
          clearActiveProgramaDraftReference();
          clearActiveProyectoDraftReference();
          setActiveReference(null);
          setReferenceInput("");
          setDashboard(null);
        }
        notify.success("El flujo curricular y sus borradores fueron eliminados correctamente.");
        await loadProgramFlows();
      })
      .catch((error: unknown) => {
        setFlowsErrorMessage(
          error instanceof Error
            ? error.message
            : "No fue posible eliminar el flujo seleccionado.",
        );
      })
      .finally(() => setIsDeletingFlow(false));
  };

  if (user?.debe_cambiar_password) {
    return (
      <main className="min-h-screen bg-[var(--paper)] px-5 py-6 lg:px-8">
        <ForceChangePasswordDialog
          isOpen={true}
          onPasswordChanged={() => {
            void refreshUser();
          }}
        />
      </main>
    );
  }

  if (isAdmin) {
    return (
      <main className="min-h-screen bg-[var(--paper)] px-5 py-6 lg:px-8">
        <div className="mx-auto grid w-full max-w-7xl gap-6">
          <header className="rounded-lg border border-[color:var(--card-border)] bg-white p-6 shadow-[0_18px_42px_rgba(24,51,45,0.07)]">
            <div className="flex flex-wrap items-start justify-between gap-5">
              <div className="max-w-3xl">
                <div className="flex items-center gap-2 text-[var(--accent-strong)]">
                  <span className="inline-flex h-14 w-14 items-center justify-center">
                    <Image
                      src="/logo-sena.svg"
                      alt="Logo SENA"
                      width={48}
                      height={48}
                      className="h-12 w-12 object-contain"
                      priority
                    />
                  </span>
                  <Sparkles className="h-5 w-5" />
                  <p className="text-xs font-semibold uppercase tracking-[0.18em]">
                    ASGARD / Módulo Institucional
                  </p>
                </div>
                <h1 className="mt-3 text-3xl font-[family:var(--font-display)] font-semibold text-[var(--foreground)] lg:text-5xl">
                  Administración y Supervisión Central ASGARD
                </h1>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--muted)]">
                  Supervisión institucional de procesos curriculares, gestión de usuarios, catálogo organizacional, control de equipos ejecutores y visor institucional de auditoría.
                </p>
              </div>
              <div className="flex flex-col items-end gap-3">
                {user ? (
                  <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 text-right">
                    <div>
                      <div className="flex items-center justify-end gap-2">
                        <span className="text-xs font-bold text-slate-800">
                          {user.nombre} {user.apellido}
                        </span>
                        <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-bold text-emerald-800">
                          {user.roles.join(", ")}
                        </span>
                      </div>
                      {(user.coordinacion || user.especialidad) && (
                        <p className="text-[10px] text-slate-500">
                          {[user.coordinacion?.nombre, user.especialidad?.nombre].filter(Boolean).join(" • ")}
                        </p>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={logout}
                      title="Cerrar sesión"
                      className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 transition hover:border-rose-300 hover:bg-rose-50 hover:text-rose-700"
                    >
                      <LogOut className="h-4 w-4" />
                    </button>
                  </div>
                ) : null}
              </div>
            </div>
          </header>

          <AdminWorkspace />
        </div>
      </main>
    );
  }

  if (loadingEquipos) {
    return (
      <main className="min-h-screen bg-[var(--paper)] px-5 py-6 lg:px-8">
        <div className="mx-auto flex min-h-[60vh] max-w-7xl items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <RefreshCcw className="h-8 w-8 animate-spin text-[var(--accent)]" />
            <p className="text-sm font-semibold text-slate-600">
              Verificando asignación de Equipo Ejecutor...
            </p>
          </div>
        </div>
      </main>
    );
  }

  if (misEquipos.length === 0) {
    return (
      <main className="min-h-screen bg-[var(--paper)] px-5 py-6 lg:px-8">
        <div className="mx-auto grid w-full max-w-7xl gap-6">
          <header className="rounded-lg border border-[color:var(--card-border)] bg-white p-6 shadow-[0_18px_42px_rgba(24,51,45,0.07)]">
            <div className="flex flex-wrap items-start justify-between gap-5">
              <div className="max-w-3xl">
                <div className="flex items-center gap-2 text-[var(--accent-strong)]">
                  <span className="inline-flex h-14 w-14 items-center justify-center">
                    <Image
                      src="/logo-sena.svg"
                      alt="Logo SENA"
                      width={48}
                      height={48}
                      className="h-12 w-12 object-contain"
                      priority
                    />
                  </span>
                  <Sparkles className="h-5 w-5" />
                  <p className="text-xs font-semibold uppercase tracking-[0.18em]">
                    ASGARD / Panel Operativo
                  </p>
                </div>
                <h1 className="mt-3 text-3xl font-[family:var(--font-display)] font-semibold text-[var(--foreground)] lg:text-5xl">
                  Panel de gestion de programa, proyecto y planeacion
                </h1>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--muted)]">
                  Entrada central para abrir wizards, ver bloqueos reales, medir avance
                  y navegar la estructura construida por el equipo.
                </p>
              </div>
              <div className="flex flex-col items-end gap-3">
                {user ? (
                  <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 text-right">
                    <div>
                      <div className="flex items-center justify-end gap-2">
                        <span className="text-xs font-bold text-slate-800">
                          {user.nombre} {user.apellido}
                        </span>
                        <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-bold text-emerald-800">
                          {user.roles.join(", ")}
                        </span>
                      </div>
                      {(user.coordinacion || user.especialidad) && (
                        <p className="text-[10px] text-slate-500">
                          {[user.coordinacion?.nombre, user.especialidad?.nombre].filter(Boolean).join(" • ")}
                        </p>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={logout}
                      title="Cerrar sesión"
                      className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 transition hover:border-rose-300 hover:bg-rose-50 hover:text-rose-700"
                    >
                      <LogOut className="h-4 w-4" />
                    </button>
                  </div>
                ) : null}
              </div>
            </div>
          </header>

          <div className="rounded-2xl border border-amber-200 bg-white p-8 text-center shadow-sm">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-100 text-amber-800">
              <LockKeyhole className="h-7 w-7" />
            </div>
            <h2 className="mt-4 text-xl font-bold text-slate-900">
              Acceso Restringido: Sin Equipo Ejecutor Asignado
            </h2>
            <p className="mx-auto mt-2 max-w-lg text-sm text-slate-600">
              El panel de gestión y construcción curricular está habilitado exclusivamente para instructores y líderes adheridos a un <strong>Equipo Ejecutor activo</strong>.
            </p>
            <p className="mx-auto mt-1 max-w-lg text-xs text-slate-500">
              Actualmente no estás vinculado a ningún Equipo Ejecutor. Comunícate con un Administrador Pedagógico o con tu Coordinación Académica para que te asigne a tu equipo correspondiente.
            </p>
            <div className="mt-6 flex justify-center gap-3">
              <button
                type="button"
                onClick={() => void loadMisEquipos()}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
              >
                <RefreshCcw className="h-4 w-4" />
                Verificar asignación
              </button>
              <button
                type="button"
                onClick={logout}
                className="inline-flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-4 py-2 text-xs font-semibold text-rose-800 shadow-sm transition hover:bg-rose-100"
              >
                <LogOut className="h-4 w-4" />
                Cerrar sesión
              </button>
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[var(--paper)] px-5 py-6 lg:px-8">
      <div className="mx-auto grid w-full max-w-7xl gap-6">
        <header className="rounded-lg border border-[color:var(--card-border)] bg-white p-6 shadow-[0_18px_42px_rgba(24,51,45,0.07)]">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div className="max-w-3xl">
              <div className="flex items-center gap-2 text-[var(--accent-strong)]">
                <span className="inline-flex h-14 w-14 items-center justify-center">
                  <Image
                    src="/logo-sena.svg"
                    alt="Logo SENA"
                    width={48}
                    height={48}
                    className="h-12 w-12 object-contain"
                    priority
                  />
                </span>
                <Sparkles className="h-5 w-5" />
                <p className="text-xs font-semibold uppercase tracking-[0.18em]">
                  ASGARD / Panel maestro
                </p>
              </div>
              <h1 className="mt-3 text-3xl font-[family:var(--font-display)] font-semibold text-[var(--foreground)] lg:text-5xl">
                Panel de gestion de programa, proyecto y planeacion
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--muted)]">
                Entrada central para abrir wizards, ver bloqueos reales, medir avance
                y navegar la estructura construida por el usuario.
              </p>
            </div>
            <div className="flex flex-col items-end gap-3">
              {/* Widget de Usuario / Autenticación */}
              {user ? (
                <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 text-right">
                  <div>
                    <div className="flex items-center justify-end gap-2">
                      <span className="text-xs font-bold text-slate-800">
                        {user.nombre} {user.apellido}
                      </span>
                      <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-bold text-emerald-800">
                        {user.roles.join(", ")}
                      </span>
                    </div>
                    {(user.coordinacion || user.especialidad) && (
                      <p className="text-[10px] text-slate-500">
                        {[user.coordinacion?.nombre, user.especialidad?.nombre].filter(Boolean).join(" • ")}
                      </p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={logout}
                    title="Cerrar sesión"
                    className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 transition hover:border-rose-300 hover:bg-rose-50 hover:text-rose-700"
                  >
                    <LogOut className="h-4 w-4" />
                  </button>
                </div>
              ) : null}

              <div className="w-full rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] p-4 text-sm">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                  Referencia activa
                </p>
                <p className="mt-2 font-semibold text-[var(--foreground)]">
                  {activeReference ? formatReferenceId(activeReference) : "Sin referencia"}
                </p>
                <p className="mt-1 text-xs text-[var(--muted)]">
                  {selectedDraft?.label ?? dashboard?.estado_global ?? "Inicia o selecciona un borrador"}
                </p>
                {activeReference ? (
                  <Link
                    href="/programa"
                    className="mt-4 inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold !text-white transition hover:bg-[var(--accent-strong)]"
                  >
                    <ArrowRight className="h-4 w-4" />
                    Ir al wizard activo
                  </Link>
                ) : null}
              </div>
            </div>
          </div>
        </header>

        <ExecutorTeamWorkspace
          misEquipos={misEquipos}
          loadingEquipos={loadingEquipos}
          selectedTeam={selectedTeam}
          onSelectTeam={(teamId) => setSelectedTeamId(teamId)}
          onGoToAdmin={() => {}}
          isAdmin={false}
          programFlows={programFlows}
          onSelectFlow={activateReference}
          onStartProcess={handleIniciarProceso}
          iniciandoCodigo={iniciandoProcesoCodigo}
          onOpenHistorial={setSelectedHistorialRef}
        />

            <ProgramFlowsPanel
              flows={programFlows}
              activeReference={activeReference}
              isLoading={isLoadingFlows}
              isDeleting={isDeletingFlow}
              errorMessage={flowsErrorMessage}
              onSelect={activateReference}
              onDelete={deleteSelectedProgramFlow}
            />

        <section className="grid gap-4 rounded-lg border border-[color:var(--card-border)] bg-white p-5 lg:grid-cols-[1fr_auto] lg:items-end">
          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
              Buscar referencia de programa
            </span>
            <input
              value={referenceInput}
              onChange={(event) => setReferenceInput(event.target.value)}
              placeholder="UUID del borrador de programa"
              className="mt-2 w-full rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm outline-none transition focus:border-[var(--accent)]"
            />
          </label>
          <button
            type="button"
            onClick={() => activateReference(referenceInput)}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)]"
          >
            <RefreshCcw className="h-4 w-4" />
            Cargar panel
          </button>
          {knownDrafts.length > 0 ? (
            <div className="flex flex-wrap gap-2 lg:col-span-2">
              {knownDrafts.map((draft) => (
                <button
                  key={draft.referenciaId}
                  type="button"
                  onClick={() => activateReference(draft.referenciaId)}
                  className={cn(
                    "rounded-lg border px-3 py-1.5 text-xs font-semibold transition",
                    draft.referenciaId === activeReference
                      ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent-strong)]"
                      : "border-[color:var(--card-border)] bg-white text-[var(--muted)] hover:border-[var(--accent)]",
                  )}
                >
                  {draft.label} / {draft.estado}
                </button>
              ))}
            </div>
          ) : null}
        </section>

        {isLoading ? (
          <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-6 text-sm font-semibold text-[var(--accent-strong)]">
            Cargando metricas reales del panel...
          </section>
        ) : null}

        {errorMessage ? (
          <section
            role="alert"
            className="rounded-lg border border-amber-200 bg-amber-50 p-5 text-sm leading-6 text-amber-900"
          >
            {errorMessage}
          </section>
        ) : null}

        {!dashboard ? (
          <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-6">
            <h2 className="text-xl font-[family:var(--font-display)] font-semibold text-[var(--foreground)]">
              Sin proceso curricular seleccionado
            </h2>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
              Selecciona o inicia un proceso curricular desde el espacio de tu Equipo Ejecutor más arriba, o busca una referencia existente para consultar bloqueos, métricas y mapa navegable.
            </p>
          </section>
        ) : (
          <>
            <section className="rounded-lg border border-[color:var(--card-border)] bg-[var(--foreground)] p-5 text-white">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/70">
                    Estado global
                  </p>
                  <h2 className="mt-2 text-2xl font-[family:var(--font-display)] font-semibold">
                    {dashboard.estado_global}
                  </h2>
                  <p className="mt-2 text-sm leading-6 text-white/75">
                    {dashboard.resumen}
                  </p>
                </div>
                <BarChart3 className="h-12 w-12 text-white/70" />
              </div>
            </section>

            <section className="grid gap-4 lg:grid-cols-3">
              {dashboard.modules.map((module) => (
                <ModuleCard
                  key={module.id}
                  module={module}
                  referenceId={activeReference}
                />
              ))}
            </section>

            <MetricsStrip dashboard={dashboard} />
            <NavigationMap dashboard={dashboard} referenceId={activeReference ?? ""} />
          </>
        )}
        <ForceChangePasswordDialog
        isOpen={Boolean(isAuthenticated && user?.debe_cambiar_password)}
        onPasswordChanged={() => {
          void refreshUser();
        }}
      />
      <ProcesoHistorialDialog
        referenciaId={selectedHistorialRef}
        isOpen={Boolean(selectedHistorialRef)}
        onClose={() => setSelectedHistorialRef(null)}
      />
    </div>
  </main>
);
}
