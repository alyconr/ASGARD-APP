"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Edit3,
  Loader2,
  Plus,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";

import { notify } from "@/components/feedback/notifications";
import {
  createProgramaCompetencia,
  deleteProgramaCompetencia,
  listProgramaCompetencias,
  ProgramaCompetenciaError,
  updateProgramaCompetencia,
} from "@/features/programa/competencias-api";
import { cn } from "@/lib/utils";
import type {
  ProgramaCompetencia,
  ProgramaCompetenciaExtraccion,
  ProgramaCompetenciaListResponse,
} from "@/features/programa/types";

type OperationState = "idle" | "loading" | "saving" | "deleting";

interface CompetenciaFormState {
  codigo_competencia: string;
  nombre_competencia: string;
}

const EMPTY_FORM: CompetenciaFormState = {
  codigo_competencia: "",
  nombre_competencia: "",
};

function getErrorMessage(error: unknown): string {
  if (error instanceof ProgramaCompetenciaError) {
    return error.detail;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "No fue posible completar la operacion de competencias.";
}

function splitExtractedCompetencia(value: string): CompetenciaFormState {
  const normalized = value.replace(/\s+/g, " ").trim();
  const match = normalized.match(/^([A-Za-z0-9.-]{3,})\s+(.+)$/);
  if (match === null) {
    return {
      codigo_competencia: "",
      nombre_competencia: normalized,
    };
  }

  return {
    codigo_competencia: match[1],
    nombre_competencia: match[2],
  };
}

function validateForm(form: CompetenciaFormState): string | null {
  if (form.codigo_competencia.trim().length === 0) {
    return "codigo_competencia es obligatorio.";
  }

  if (form.nombre_competencia.trim().length === 0) {
    return "nombre_competencia es obligatorio.";
  }

  return null;
}

function CompetenciaEmptyState(): React.JSX.Element {
  return (
    <div className="rounded-lg border border-dashed border-[color:var(--card-border)] bg-[var(--paper-strong)] px-4 py-6 text-center">
      <p className="text-sm font-semibold text-[var(--foreground)]">
        Sin competencias registradas
      </p>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-[var(--muted)]">
        Agrega la primera competencia del programa para construir la estructura
        curricular sin validar automaticamente lo extraido del PDF.
      </p>
    </div>
  );
}

function ExtractedCompetenciaSuggestions({
  competencias,
  onUseSuggestion,
}: Readonly<{
  competencias: ProgramaCompetenciaExtraccion[] | null;
  onUseSuggestion: (value: string) => void;
}>): React.JSX.Element | null {
  const suggestions = competencias ?? [];
  if (suggestions.length === 0) {
    return null;
  }

  return (
    <section className="min-w-0 rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] p-4">
      <div className="flex items-start gap-3">
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-white text-[var(--accent-strong)]">
          <Sparkles className="h-4 w-4" />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-[var(--foreground)]">
            Competencias extraidas como base
          </p>
          <p className="mt-1 text-sm leading-6 text-[var(--muted)]">
            Puedes precargar el formulario y confirmar manualmente cada
            competencia.
          </p>
        </div>
      </div>

      <div className="mt-3 grid max-h-72 min-w-0 gap-2 overflow-auto pr-1">
        {suggestions.map((item, idx) => {
          const textValue = `${item.codigo.valor} ${item.denominacion.valor}`;
          return (
            <button
              key={`${item.codigo.valor}-${idx}`}
              type="button"
              onClick={() => onUseSuggestion(textValue)}
              className="min-w-0 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-left text-sm leading-6 break-words text-[var(--foreground)] transition hover:border-[var(--accent)] hover:bg-[var(--accent-soft)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
            >
              {textValue}
            </button>
          );
        })}
      </div>
    </section>
  );
}

export function ProgramaCompetenciasManager({
  competencias,
  extractedCompetencias,
  onCompetenciasSynced,
  referenciaId,
}: Readonly<{
  competencias: ProgramaCompetencia[];
  extractedCompetencias: ProgramaCompetenciaExtraccion[] | null;
  onCompetenciasSynced: (result: ProgramaCompetenciaListResponse) => void;
  referenciaId: string;
}>): React.JSX.Element {
  const [form, setForm] = useState<CompetenciaFormState>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [state, setState] = useState<OperationState>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const sortedCompetencias = useMemo(() => {
    return [...competencias].sort((left, right) => {
      const leftOrder = left.orden ?? Number.MAX_SAFE_INTEGER;
      const rightOrder = right.orden ?? Number.MAX_SAFE_INTEGER;
      return leftOrder - rightOrder;
    });
  }, [competencias]);

  useEffect(() => {
    let isCurrent = true;

    const loadCompetencias = async (): Promise<void> => {
      setState("loading");
      setErrorMessage(null);

      try {
        const result = await listProgramaCompetencias(referenciaId);
        if (isCurrent) {
          onCompetenciasSynced(result);
        }
      } catch (error) {
        if (isCurrent) {
          const detail = getErrorMessage(error);
          setErrorMessage(detail);
        }
      } finally {
        if (isCurrent) {
          setState("idle");
        }
      }
    };

    void loadCompetencias();

    return () => {
      isCurrent = false;
    };
  }, [onCompetenciasSynced, referenciaId]);

  const resetForm = (): void => {
    setForm(EMPTY_FORM);
    setEditingId(null);
  };

  const handleSubmit = async (
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> => {
    event.preventDefault();
    const validationMessage = validateForm(form);
    if (validationMessage !== null) {
      setErrorMessage(validationMessage);
      notify.warning("Revisa los datos de la competencia", {
        description: validationMessage,
      });
      return;
    }

    setState("saving");
    setErrorMessage(null);
    setMessage(null);

    try {
      const payload = {
        codigo_competencia: form.codigo_competencia.trim(),
        nombre_competencia: form.nombre_competencia.trim(),
      };
      const result =
        editingId === null
          ? await createProgramaCompetencia(referenciaId, payload)
          : await updateProgramaCompetencia(referenciaId, editingId, payload);

      onCompetenciasSynced(result);
      resetForm();
      setMessage(
        editingId === null
          ? "Competencia registrada."
          : "Competencia actualizada.",
      );
      notify.success("Competencias sincronizadas", {
        description: "El borrador conserva la estructura curricular actual.",
      });
    } catch (error) {
      const detail = getErrorMessage(error);
      setErrorMessage(detail);
      notify.error("No fue posible guardar la competencia", {
        description: detail,
      });
    } finally {
      setState("idle");
    }
  };

  const handleEdit = (competencia: ProgramaCompetencia): void => {
    setEditingId(competencia.id);
    setForm({
      codigo_competencia: competencia.codigo_competencia,
      nombre_competencia: competencia.nombre_competencia,
    });
    setMessage(null);
    setErrorMessage(null);
  };

  const handleDelete = async (competencia: ProgramaCompetencia): Promise<void> => {
    const confirmed = window.confirm(
      `Eliminar la competencia ${competencia.codigo_competencia}? Esta accion requiere confirmacion.`,
    );
    if (!confirmed) {
      return;
    }

    setState("deleting");
    setErrorMessage(null);
    setMessage(null);

    try {
      await deleteProgramaCompetencia(referenciaId, competencia.id);
      const result = await listProgramaCompetencias(referenciaId);
      onCompetenciasSynced(result);
      if (editingId === competencia.id) {
        resetForm();
      }
      setMessage("Competencia eliminada.");
      notify.success("Competencia eliminada", {
        description: "El borrador fue actualizado con la lista vigente.",
      });
    } catch (error) {
      const detail = getErrorMessage(error);
      setErrorMessage(detail);
      notify.error("No fue posible eliminar la competencia", {
        description: detail,
      });
    } finally {
      setState("idle");
    }
  };

  const handleUseSuggestion = (value: string): void => {
    setForm(splitExtractedCompetencia(value));
    setEditingId(null);
    setMessage("Sugerencia cargada en el formulario.");
    setErrorMessage(null);
  };

  const isBusy = state === "loading" || state === "saving" || state === "deleting";

  return (
    <div className="grid gap-4">
      <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold tracking-[0.16em] text-[var(--muted)] uppercase">
              Competencias
            </p>
            <h3 className="mt-1 text-xl font-[family:var(--font-display)] font-semibold text-[var(--foreground)]">
              Gestion del programa
            </h3>
          </div>
          <span className="inline-flex min-h-8 items-center rounded-full border border-[color:var(--card-border)] bg-[var(--paper-strong)] px-3 py-1 text-xs font-semibold text-[var(--foreground)]">
            {sortedCompetencias.length} registrada(s)
          </span>
        </div>

        {state === "loading" ? (
          <div className="mt-4 flex items-center gap-2 rounded-lg bg-[var(--paper-strong)] px-4 py-3 text-sm text-[var(--muted)]">
            <Loader2 className="h-4 w-4 animate-spin" />
            Cargando competencias del borrador...
          </div>
        ) : null}

        {errorMessage !== null ? (
          <div
            role="alert"
            className="mt-4 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-900"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <p>{errorMessage}</p>
          </div>
        ) : null}

        {message !== null ? (
          <div
            role="status"
            className="mt-4 flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm leading-6 text-emerald-900"
          >
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            <p>{message}</p>
          </div>
        ) : null}
      </section>

      <div className="grid min-w-0 gap-4">
        <section className="min-w-0 rounded-lg border border-[color:var(--card-border)] bg-white p-4">
          <form onSubmit={(event) => void handleSubmit(event)} className="grid gap-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h4 className="text-base font-semibold text-[var(--foreground)]">
                {editingId === null ? "Agregar competencia" : "Editar competencia"}
              </h4>
              {editingId !== null ? (
                <button
                  type="button"
                  onClick={resetForm}
                  className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-1.5 text-xs font-semibold text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                >
                  <X className="h-4 w-4" />
                  Cancelar
                </button>
              ) : null}
            </div>

            <label className="grid gap-2">
              <span className="text-xs font-semibold tracking-[0.14em] text-[var(--muted)] uppercase">
                codigo_competencia
              </span>
              <input
                value={form.codigo_competencia}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    codigo_competencia: event.target.value,
                  }))
                }
                placeholder="Ej. 220501046"
                className="min-h-11 rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] px-3 py-2 text-sm text-[var(--foreground)] outline-none transition placeholder:text-[var(--muted)]/70 focus:border-[var(--accent)]"
              />
            </label>

            <label className="grid gap-2">
              <span className="text-xs font-semibold tracking-[0.14em] text-[var(--muted)] uppercase">
                nombre_competencia
              </span>
              <textarea
                value={form.nombre_competencia}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    nombre_competencia: event.target.value,
                  }))
                }
                rows={4}
                placeholder="Describe la competencia del programa."
                className="min-h-28 resize-none rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] px-3 py-2 text-sm leading-6 text-[var(--foreground)] outline-none transition placeholder:text-[var(--muted)]/70 focus:border-[var(--accent)]"
              />
            </label>

            <button
              type="submit"
              disabled={isBusy}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
            >
              {state === "saving" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : editingId === null ? (
                <Plus className="h-4 w-4" />
              ) : (
                <CheckCircle2 className="h-4 w-4" />
              )}
              {editingId === null ? "Crear competencia" : "Guardar cambios"}
            </button>
          </form>
        </section>

        <ExtractedCompetenciaSuggestions
          competencias={extractedCompetencias}
          onUseSuggestion={handleUseSuggestion}
        />
      </div>

      {sortedCompetencias.length === 0 ? (
        <CompetenciaEmptyState />
      ) : (
        <section className="grid gap-3">
          {sortedCompetencias.map((competencia) => (
            <article
              key={competencia.id}
              className={cn(
                "grid gap-3 rounded-lg border bg-white p-4 transition sm:grid-cols-[1fr_auto]",
                editingId === competencia.id
                  ? "border-[var(--accent)]"
                  : "border-[color:var(--card-border)]",
              )}
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-lg bg-[var(--accent-soft)] px-2.5 py-1 text-xs font-semibold text-[var(--accent-strong)]">
                    {competencia.codigo_competencia}
                  </span>
                  <span className="text-xs font-semibold text-[var(--muted)]">
                    {competencia.origen_campo}
                  </span>
                </div>
                <p className="mt-2 text-sm leading-6 break-words text-[var(--foreground)]">
                  {competencia.nombre_competencia}
                </p>
              </div>

              <div className="flex items-start gap-2">
                <button
                  type="button"
                  onClick={() => handleEdit(competencia)}
                  className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm font-semibold text-[var(--foreground)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                >
                  <Edit3 className="h-4 w-4" />
                  Editar
                </button>
                <button
                  type="button"
                  disabled={state === "deleting"}
                  onClick={() => void handleDelete(competencia)}
                  className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-800 transition hover:bg-rose-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
                >
                  <Trash2 className="h-4 w-4" />
                  Eliminar
                </button>
              </div>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}
