"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  BarChart3,
  BookOpenCheck,
  CalendarClock,
  GitBranch,
  ListChecks,
  LockKeyhole,
  Network,
  Plus,
  RefreshCcw,
  Route,
  Sparkles,
  Trash2,
} from "lucide-react";

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
  forgetProgramaDraft,
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
  const href = module.id === "programa" ? "/programa" : module.href;

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
  const selectedFlow = flows.find((flow) => flow.referencia_id === activeReference);

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

export function MasterDashboard(): React.JSX.Element {
  const confirm = useConfirm();
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

  useEffect(() => {
    const drafts = listKnownProgramaDrafts();
    const active = getActiveProgramaDraftReference() ?? drafts[0]?.referenciaId ?? null;
    setKnownDrafts(drafts);
    setActiveReference(active);
    setReferenceInput(active ?? "");
  }, []);

  const loadProgramFlows = useCallback(async (): Promise<DashboardProgramFlow[]> => {
    setIsLoadingFlows(true);
    setFlowsErrorMessage(null);
    try {
      const flows = await fetchProgramFlows();
      setProgramFlows(flows);
      setActiveReference((current) => {
        if (current || flows.length === 0) return current;
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
  }, []);

  useEffect(() => {
    void loadProgramFlows();
  }, [loadProgramFlows]);

  useEffect(() => {
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
      })
      .finally(() => {
        if (isActive) setIsLoading(false);
      });

    return () => {
      isActive = false;
    };
  }, [activeReference]);

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
    const confirmationValue =
      selectedFlow?.codigo_programa ??
      selectedFlow?.nombre_programa ??
      referenceId;
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
        setProgramFlows((current) =>
          current.filter((flow) => flow.referencia_id !== referenceId),
        );
        if (activeReference === referenceId) {
          clearActiveProgramaDraftReference();
          setActiveReference(null);
          setReferenceInput("");
          setDashboard(null);
        }
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

  const prepareNewProgramFlow = (): void => {
    clearActiveProgramaDraftReference();
    setActiveReference(null);
    setReferenceInput("");
  };

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
            <div className="rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] p-4 text-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                Referencia activa
              </p>
              <p className="mt-2 font-semibold text-[var(--foreground)]">
                {activeReference ? formatReferenceId(activeReference) : "Sin referencia"}
              </p>
              <p className="mt-1 text-xs text-[var(--muted)]">
                {selectedDraft?.label ?? dashboard?.estado_global ?? "Inicia o selecciona un borrador"}
              </p>
              <Link
                href="/programa?nuevo=programa"
                onClick={prepareNewProgramFlow}
                className="mt-4 inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold !text-white transition hover:bg-[var(--accent-strong)]"
              >
                <Plus className="h-4 w-4" />
                Nuevo programa
              </Link>
            </div>
          </div>
        </header>

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
              Sin proceso activo
            </h2>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
              Inicia el wizard del programa o carga una referencia existente para ver
              bloqueos, metricas y mapa navegable.
            </p>
            <Link
              href="/programa"
              className="mt-4 inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold !text-white transition hover:bg-[var(--accent-strong)]"
            >
              Abrir wizard del programa
              <ArrowRight className="h-4 w-4" />
            </Link>
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
      </div>
    </main>
  );
}
