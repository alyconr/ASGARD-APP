"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, GitBranch, Loader2 } from "lucide-react";

import { notify } from "@/components/feedback/notifications";
import {
  assignPendienteCurricular,
  listPendientesCurriculares,
  ProgramaPendienteError,
} from "@/features/programa/pendientes-api";
import { cn } from "@/lib/utils";
import type {
  PendienteCurricular,
  ProgramaCompetencia,
} from "@/features/programa/types";

type PendingFilter = "TODOS" | "CONOCIMIENTO" | "CRITERIO";

function getErrorMessage(error: unknown): string {
  if (error instanceof ProgramaPendienteError) {
    return error.detail;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "No fue posible completar la conciliacion curricular.";
}

function motivoLabel(motivo: PendienteCurricular["motivo"]): string {
  if (motivo === "COMPETENCIA_NO_IDENTIFICADA") {
    return "Competencia no identificada";
  }
  if (motivo === "RESULTADO_NO_IDENTIFICADO") {
    return "Resultado no identificado";
  }
  return "Asociacion ambigua";
}

function PendingAssignmentRow({
  competencias,
  item,
  onAssigned,
  referenciaId,
}: Readonly<{
  competencias: ProgramaCompetencia[];
  item: PendienteCurricular;
  onAssigned: (pending: PendienteCurricular) => void;
  referenciaId: string;
}>): React.JSX.Element {
  const [competenciaId, setCompetenciaId] = useState("");
  const [resultadoId, setResultadoId] = useState("");
  const [state, setState] = useState<"idle" | "saving">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const selectedCompetencia = competencias.find(
    (competencia) => competencia.id === competenciaId,
  );
  const resultados = selectedCompetencia?.resultados ?? [];
  const canAssign = item.estado === "PENDIENTE" && competenciaId.length > 0;

  const handleAssign = async (): Promise<void> => {
    if (!canAssign) {
      setErrorMessage("Selecciona una competencia destino.");
      return;
    }

    setState("saving");
    setErrorMessage(null);
    try {
      const result = await assignPendienteCurricular(referenciaId, item.id, {
        competencia_id: competenciaId,
        resultado_id: resultadoId || null,
      });
      onAssigned(result.pendiente);
      notify.success("Pendiente asignado", {
        description: "El elemento quedo materializado en la estructura final.",
      });
    } catch (error) {
      const detail = getErrorMessage(error);
      setErrorMessage(detail);
      notify.error("No fue posible asignar el pendiente", {
        description: detail,
      });
    } finally {
      setState("idle");
    }
  };

  return (
    <article className="grid gap-3 rounded-lg border border-[color:var(--card-border)] bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-lg bg-[var(--accent-soft)] px-2 py-1 text-xs font-semibold text-[var(--accent-strong)]">
              {item.tipo_elemento}
            </span>
            {item.tipo_conocimiento !== null ? (
              <span className="rounded-lg border border-[color:var(--card-border)] px-2 py-1 text-xs font-semibold text-[var(--muted)]">
                {item.tipo_conocimiento}
              </span>
            ) : null}
            <span className="text-xs font-semibold text-[var(--muted)]">
              {motivoLabel(item.motivo)}
            </span>
          </div>
          <p className="mt-2 text-sm leading-6 break-words text-[var(--foreground)]">
            {item.descripcion}
          </p>
          <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
            Origen Excel: competencia{" "}
            {item.competencia_id_origen_excel ?? "sin dato"} / RAP{" "}
            {item.rap_id_origen_excel ?? "sin dato"}
          </p>
        </div>
        <span
          className={cn(
            "rounded-lg px-2 py-1 text-xs font-semibold",
            item.estado === "ASIGNADO"
              ? "bg-emerald-50 text-emerald-800"
              : "bg-amber-50 text-amber-800",
          )}
        >
          {item.estado}
        </span>
      </div>

      {item.estado === "PENDIENTE" ? (
        <div className="grid gap-3 lg:grid-cols-[minmax(12rem,1fr)_minmax(12rem,1fr)_auto]">
          <label className="grid gap-2">
            <span className="text-xs font-semibold tracking-[0.14em] text-[var(--muted)] uppercase">
              Competencia destino
            </span>
            <select
              aria-label={`Competencia destino para ${item.descripcion}`}
              value={competenciaId}
              onChange={(event) => {
                setCompetenciaId(event.target.value);
                setResultadoId("");
              }}
              className="min-h-10 rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] px-3 py-2 text-sm text-[var(--foreground)] outline-none transition focus:border-[var(--accent)]"
            >
              <option value="">Selecciona competencia</option>
              {competencias.map((competencia) => (
                <option key={competencia.id} value={competencia.id}>
                  {competencia.codigo_competencia} -{" "}
                  {competencia.nombre_competencia}
                </option>
              ))}
            </select>
          </label>

          <label className="grid gap-2">
            <span className="text-xs font-semibold tracking-[0.14em] text-[var(--muted)] uppercase">
              Resultado destino
            </span>
            <select
              aria-label={`Resultado destino para ${item.descripcion}`}
              value={resultadoId}
              onChange={(event) => setResultadoId(event.target.value)}
              className="min-h-10 rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] px-3 py-2 text-sm text-[var(--foreground)] outline-none transition focus:border-[var(--accent)]"
            >
              <option value="">Sin resultado especifico</option>
              {resultados.map((resultado) => (
                <option key={resultado.id} value={resultado.id}>
                  {resultado.codigo_resultado ?? "RAP"} -{" "}
                  {resultado.descripcion}
                </option>
              ))}
            </select>
          </label>

          <button
            type="button"
            disabled={!canAssign || state === "saving"}
            onClick={() => void handleAssign()}
            className="inline-flex min-h-10 items-center justify-center gap-2 self-end rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
          >
            {state === "saving" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <CheckCircle2 className="h-4 w-4" />
            )}
            Asignar
          </button>
        </div>
      ) : null}

      {errorMessage !== null ? (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm leading-6 text-rose-900"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{errorMessage}</p>
        </div>
      ) : null}
    </article>
  );
}

export function ProgramaPendientesConciliacion({
  competencias,
  referenciaId,
}: Readonly<{
  competencias: ProgramaCompetencia[];
  referenciaId: string;
}>): React.JSX.Element {
  const [pendientes, setPendientes] = useState<PendienteCurricular[]>([]);
  const [filter, setFilter] = useState<PendingFilter>("TODOS");
  const [state, setState] = useState<"loading" | "idle">("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isCurrent = true;

    const load = async (): Promise<void> => {
      setState("loading");
      setErrorMessage(null);
      try {
        const result = await listPendientesCurriculares(referenciaId);
        if (isCurrent) {
          setPendientes(result.pendientes);
        }
      } catch (error) {
        if (isCurrent) {
          setErrorMessage(getErrorMessage(error));
        }
      } finally {
        if (isCurrent) {
          setState("idle");
        }
      }
    };

    void load();

    return () => {
      isCurrent = false;
    };
  }, [referenciaId]);

  const visiblePendientes = useMemo(() => {
    return pendientes.filter((item) => {
      if (filter === "TODOS") return true;
      return item.tipo_elemento === filter;
    });
  }, [filter, pendientes]);

  const pendingCount = pendientes.filter(
    (item) => item.estado === "PENDIENTE",
  ).length;

  const handleAssigned = (updated: PendienteCurricular): void => {
    setPendientes((current) =>
      current.map((item) => (item.id === updated.id ? updated : item)),
    );
  };

  return (
    <section className="rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-[var(--accent-strong)]" />
            <h3 className="text-base font-semibold text-[var(--foreground)]">
              Conciliacion de pendientes Excel
            </h3>
          </div>
          <p className="mt-1 text-sm leading-6 text-[var(--muted)]">
            Asigna los conocimientos y criterios que el workbook no pudo
            enlazar con seguridad.
          </p>
        </div>
        <span className="inline-flex min-h-8 items-center rounded-full border border-[color:var(--card-border)] bg-white px-3 py-1 text-xs font-semibold text-[var(--foreground)]">
          {pendingCount} pendiente(s)
        </span>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {(["TODOS", "CONOCIMIENTO", "CRITERIO"] as const).map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => setFilter(item)}
            className={cn(
              "inline-flex min-h-9 items-center rounded-lg border px-3 py-1.5 text-xs font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]",
              filter === item
                ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent-strong)]"
                : "border-[color:var(--card-border)] bg-white text-[var(--muted)] hover:border-[var(--accent)]",
            )}
          >
            {item}
          </button>
        ))}
      </div>

      {state === "loading" ? (
        <div className="mt-4 flex items-center gap-2 rounded-lg bg-white px-3 py-3 text-sm text-[var(--muted)]">
          <Loader2 className="h-4 w-4 animate-spin" />
          Cargando pendientes curriculares...
        </div>
      ) : null}

      {errorMessage !== null ? (
        <div
          role="alert"
          className="mt-4 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-3 text-sm leading-6 text-rose-900"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{errorMessage}</p>
        </div>
      ) : null}

      {state === "idle" && visiblePendientes.length === 0 ? (
        <p className="mt-4 rounded-lg border border-dashed border-[color:var(--card-border)] bg-white px-3 py-3 text-sm text-[var(--muted)]">
          No hay pendientes para el filtro seleccionado.
        </p>
      ) : null}

      <div className="mt-4 grid gap-3">
        {visiblePendientes.map((item) => (
          <PendingAssignmentRow
            key={item.id}
            competencias={competencias}
            item={item}
            referenciaId={referenciaId}
            onAssigned={handleAssigned}
          />
        ))}
      </div>
    </section>
  );
}
