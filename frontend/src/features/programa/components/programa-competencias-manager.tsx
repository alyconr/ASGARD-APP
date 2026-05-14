"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  ClipboardCheck,
  Edit3,
  Layers3,
  ListChecks,
  Loader2,
  Plus,
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
import {
  createProgramaConocimientoSaber,
  deleteProgramaConocimientoSaber,
  listProgramaConocimientosSaber,
  ProgramaConocimientoSaberError,
  updateProgramaConocimientoSaber,
} from "@/features/programa/conocimientos-saber-api";
import {
  createProgramaConocimientoProceso,
  deleteProgramaConocimientoProceso,
  listProgramaConocimientosProceso,
  ProgramaConocimientoProcesoError,
  updateProgramaConocimientoProceso,
} from "@/features/programa/conocimientos-proceso-api";
import {
  createProgramaCriterio,
  deleteProgramaCriterio,
  listProgramaCriterios,
  ProgramaCriterioError,
  updateProgramaCriterio,
} from "@/features/programa/criterios-api";
import {
  createProgramaResultado,
  deleteProgramaResultado,
  listProgramaResultados,
  ProgramaResultadoError,
  updateProgramaResultado,
} from "@/features/programa/resultados-api";
import { cn } from "@/lib/utils";
import type {
  ProgramaCompetencia,
  ProgramaCompetenciaListResponse,
  ConocimientoCurricular,
  ConocimientoProcesoListResponse,
  ConocimientoSaberListResponse,
  CriterioEvaluacionCurricular,
  CriterioListResponse,
  ResultadoAprendizaje,
  ResultadoAprendizajeListResponse,
} from "@/features/programa/types";

type OperationState = "idle" | "loading" | "saving" | "deleting";

interface CompetenciaFormState {
  codigo_competencia: string;
  nombre_competencia: string;
}

interface ResultadoFormState {
  codigo_resultado: string;
  descripcion: string;
}

interface ConocimientoFormState {
  descripcion: string;
}

const EMPTY_FORM: CompetenciaFormState = {
  codigo_competencia: "",
  nombre_competencia: "",
};

const EMPTY_RESULTADO_FORM: ResultadoFormState = {
  codigo_resultado: "",
  descripcion: "",
};

const EMPTY_CONOCIMIENTO_FORM: ConocimientoFormState = {
  descripcion: "",
};

function getErrorMessage(error: unknown): string {
  if (
    error instanceof ProgramaCompetenciaError ||
    error instanceof ProgramaCriterioError ||
    error instanceof ProgramaResultadoError ||
    error instanceof ProgramaConocimientoSaberError ||
    error instanceof ProgramaConocimientoProcesoError
  ) {
    return error.detail;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "No fue posible completar la operacion de competencias.";
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

function validateResultadoForm(form: ResultadoFormState): string | null {
  if (form.descripcion.trim().length === 0) {
    return "descripcion es obligatoria.";
  }

  return null;
}

function validateConocimientoForm(
  form: ConocimientoFormState,
): string | null {
  if (form.descripcion.trim().length === 0) {
    return "descripcion es obligatoria.";
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
        curricular. El Excel canonico puede importarlas de forma estructurada.
      </p>
    </div>
  );
}

function sortByOrder<T extends { orden: number | null }>(items: T[]): T[] {
  return [...items].sort((left, right) => {
    const leftOrder = left.orden ?? Number.MAX_SAFE_INTEGER;
    const rightOrder = right.orden ?? Number.MAX_SAFE_INTEGER;
    return leftOrder - rightOrder;
  });
}

function CurriculumEmptyNote({
  children,
}: Readonly<{ children: React.ReactNode }>): React.JSX.Element {
  return (
    <p className="rounded-lg border border-dashed border-[color:var(--card-border)] bg-white/70 px-3 py-3 text-sm leading-6 text-[var(--muted)]">
      {children}
    </p>
  );
}

function ProgramaConocimientosPanel({
  competencia,
  conocimientos,
  onConocimientosSaberSynced,
  onConocimientosProcesoSynced,
  referenciaId,
}: Readonly<{
  competencia: ProgramaCompetencia;
  conocimientos: ConocimientoCurricular[];
  onConocimientosSaberSynced: (result: ConocimientoSaberListResponse) => void;
  onConocimientosProcesoSynced: (
    result: ConocimientoProcesoListResponse,
  ) => void;
  referenciaId: string;
}>): React.JSX.Element {
  const [saberes, setSaberes] = useState<ConocimientoCurricular[]>(
    conocimientos.filter((item) => item.tipo === "SABER"),
  );
  const [procesos, setProcesos] = useState<ConocimientoCurricular[]>(
    conocimientos.filter((item) => item.tipo === "PROCESO"),
  );
  const [form, setForm] = useState<ConocimientoFormState>(
    EMPTY_CONOCIMIENTO_FORM,
  );
  const [procesoForm, setProcesoForm] = useState<ConocimientoFormState>(
    EMPTY_CONOCIMIENTO_FORM,
  );
  const [editingId, setEditingId] = useState<string | null>(null);
  const [procesoEditingId, setProcesoEditingId] = useState<string | null>(null);
  const [state, setState] = useState<OperationState>("idle");
  const [procesoState, setProcesoState] = useState<OperationState>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [procesoMessage, setProcesoMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [procesoErrorMessage, setProcesoErrorMessage] = useState<string | null>(
    null,
  );

  const saber = useMemo(() => sortByOrder(saberes), [saberes]);
  const proceso = useMemo(() => sortByOrder(procesos), [procesos]);

  useEffect(() => {
    setSaberes(conocimientos.filter((item) => item.tipo === "SABER"));
    setProcesos(conocimientos.filter((item) => item.tipo === "PROCESO"));
  }, [conocimientos]);

  useEffect(() => {
    let isCurrent = true;

    const loadSaberes = async (): Promise<void> => {
      setState("loading");
      setErrorMessage(null);

      try {
        const result = await listProgramaConocimientosSaber(
          referenciaId,
          competencia.id,
        );
        if (isCurrent) {
          setSaberes(result.conocimientos);
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

    void loadSaberes();

    return () => {
      isCurrent = false;
    };
  }, [competencia.id, referenciaId]);

  useEffect(() => {
    let isCurrent = true;

    const loadProcesos = async (): Promise<void> => {
      setProcesoState("loading");
      setProcesoErrorMessage(null);

      try {
        const result = await listProgramaConocimientosProceso(
          referenciaId,
          competencia.id,
        );
        if (isCurrent) {
          setProcesos(result.conocimientos);
        }
      } catch (error) {
        if (isCurrent) {
          setProcesoErrorMessage(getErrorMessage(error));
        }
      } finally {
        if (isCurrent) {
          setProcesoState("idle");
        }
      }
    };

    void loadProcesos();

    return () => {
      isCurrent = false;
    };
  }, [competencia.id, referenciaId]);

  const resetForm = (): void => {
    setForm(EMPTY_CONOCIMIENTO_FORM);
    setEditingId(null);
  };

  const resetProcesoForm = (): void => {
    setProcesoForm(EMPTY_CONOCIMIENTO_FORM);
    setProcesoEditingId(null);
  };

  const syncSaberes = (result: ConocimientoSaberListResponse): void => {
    setSaberes(result.conocimientos);
    onConocimientosSaberSynced(result);
  };

  const syncProcesos = (result: ConocimientoProcesoListResponse): void => {
    setProcesos(result.conocimientos);
    onConocimientosProcesoSynced(result);
  };

  const handleSubmit = async (
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> => {
    event.preventDefault();
    const validationMessage = validateConocimientoForm(form);
    if (validationMessage !== null) {
      setErrorMessage(validationMessage);
      notify.warning("Revisa el conocimiento SABER", {
        description: validationMessage,
      });
      return;
    }

    setState("saving");
    setErrorMessage(null);
    setMessage(null);

    try {
      const payload = { descripcion: form.descripcion.trim() };
      const result =
        editingId === null
          ? await createProgramaConocimientoSaber(
              referenciaId,
              competencia.id,
              payload,
            )
          : await updateProgramaConocimientoSaber(
              referenciaId,
              competencia.id,
              editingId,
              payload,
            );

      syncSaberes(result);
      resetForm();
      setMessage(
        editingId === null
          ? "Conocimiento SABER registrado."
          : "Conocimiento SABER actualizado.",
      );
      notify.success("Conocimientos SABER sincronizados", {
        description: "El borrador conserva la estructura curricular actual.",
      });
    } catch (error) {
      const detail = getErrorMessage(error);
      setErrorMessage(detail);
      notify.error("No fue posible guardar el conocimiento SABER", {
        description: detail,
      });
    } finally {
      setState("idle");
    }
  };

  const handleEdit = (conocimiento: ConocimientoCurricular): void => {
    setEditingId(conocimiento.id);
    setForm({ descripcion: conocimiento.descripcion });
    setMessage(null);
    setErrorMessage(null);
  };

  const handleDelete = async (
    conocimiento: ConocimientoCurricular,
  ): Promise<void> => {
    const confirmed = window.confirm(
      "Eliminar este conocimiento SABER? Esta accion requiere confirmacion.",
    );
    if (!confirmed) {
      return;
    }

    setState("deleting");
    setErrorMessage(null);
    setMessage(null);

    try {
      await deleteProgramaConocimientoSaber(
        referenciaId,
        competencia.id,
        conocimiento.id,
      );
      const result = await listProgramaConocimientosSaber(
        referenciaId,
        competencia.id,
      );
      syncSaberes(result);
      if (editingId === conocimiento.id) {
        resetForm();
      }
      setMessage("Conocimiento SABER eliminado.");
      notify.success("Conocimiento SABER eliminado", {
        description: "El borrador fue actualizado con la lista vigente.",
      });
    } catch (error) {
      const detail = getErrorMessage(error);
      setErrorMessage(detail);
      notify.error("No fue posible eliminar el conocimiento SABER", {
        description: detail,
      });
    } finally {
      setState("idle");
    }
  };

  const handleProcesoSubmit = async (
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> => {
    event.preventDefault();
    const validationMessage = validateConocimientoForm(procesoForm);
    if (validationMessage !== null) {
      setProcesoErrorMessage(validationMessage);
      notify.warning("Revisa el conocimiento PROCESO", {
        description: validationMessage,
      });
      return;
    }

    setProcesoState("saving");
    setProcesoErrorMessage(null);
    setProcesoMessage(null);

    try {
      const payload = { descripcion: procesoForm.descripcion.trim() };
      const result =
        procesoEditingId === null
          ? await createProgramaConocimientoProceso(
              referenciaId,
              competencia.id,
              payload,
            )
          : await updateProgramaConocimientoProceso(
              referenciaId,
              competencia.id,
              procesoEditingId,
              payload,
            );

      syncProcesos(result);
      resetProcesoForm();
      setProcesoMessage(
        procesoEditingId === null
          ? "Conocimiento PROCESO registrado."
          : "Conocimiento PROCESO actualizado.",
      );
      notify.success("Conocimientos PROCESO sincronizados", {
        description: "El borrador conserva la estructura curricular actual.",
      });
    } catch (error) {
      const detail = getErrorMessage(error);
      setProcesoErrorMessage(detail);
      notify.error("No fue posible guardar el conocimiento PROCESO", {
        description: detail,
      });
    } finally {
      setProcesoState("idle");
    }
  };

  const handleProcesoEdit = (conocimiento: ConocimientoCurricular): void => {
    setProcesoEditingId(conocimiento.id);
    setProcesoForm({ descripcion: conocimiento.descripcion });
    setProcesoMessage(null);
    setProcesoErrorMessage(null);
  };

  const handleProcesoDelete = async (
    conocimiento: ConocimientoCurricular,
  ): Promise<void> => {
    const confirmed = window.confirm(
      "Eliminar este conocimiento PROCESO? Esta accion requiere confirmacion.",
    );
    if (!confirmed) {
      return;
    }

    setProcesoState("deleting");
    setProcesoErrorMessage(null);
    setProcesoMessage(null);

    try {
      await deleteProgramaConocimientoProceso(
        referenciaId,
        competencia.id,
        conocimiento.id,
      );
      const result = await listProgramaConocimientosProceso(
        referenciaId,
        competencia.id,
      );
      syncProcesos(result);
      if (procesoEditingId === conocimiento.id) {
        resetProcesoForm();
      }
      setProcesoMessage("Conocimiento PROCESO eliminado.");
      notify.success("Conocimiento PROCESO eliminado", {
        description: "El borrador fue actualizado con la lista vigente.",
      });
    } catch (error) {
      const detail = getErrorMessage(error);
      setProcesoErrorMessage(detail);
      notify.error("No fue posible eliminar el conocimiento PROCESO", {
        description: detail,
      });
    } finally {
      setProcesoState("idle");
    }
  };

  const isBusy = state === "loading" || state === "saving" || state === "deleting";
  const isProcesoBusy =
    procesoState === "loading" ||
    procesoState === "saving" ||
    procesoState === "deleting";

  return (
    <section className="rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-white text-[var(--accent-strong)]">
            <BookOpen className="h-4 w-4" />
          </span>
          <h4 className="text-sm font-semibold text-[var(--foreground)]">
            Conocimientos
          </h4>
        </div>
        <span className="text-xs font-semibold text-[var(--muted)]">
          {saber.length + proceso.length}
        </span>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <div className="grid gap-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs font-semibold tracking-[0.14em] text-[var(--muted)] uppercase">
              Saber
            </p>
            <span className="inline-flex min-h-7 items-center rounded-full border border-[color:var(--card-border)] bg-white px-2.5 py-1 text-xs font-semibold text-[var(--foreground)]">
              {saber.length} registrado(s)
            </span>
          </div>

          {state === "loading" ? (
            <div className="flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-xs text-[var(--muted)]">
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando conocimientos SABER...
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

          {message !== null ? (
            <div
              role="status"
              className="flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm leading-6 text-emerald-900"
            >
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
              <p>{message}</p>
            </div>
          ) : null}

          <form
            onSubmit={(event) => void handleSubmit(event)}
            className="grid gap-3 rounded-lg bg-white p-3"
          >
            <label className="grid gap-2">
              <span className="text-xs font-semibold tracking-[0.14em] text-[var(--muted)] uppercase">
                descripcion
              </span>
              <textarea
                value={form.descripcion}
                onChange={(event) =>
                  setForm({ descripcion: event.target.value })
                }
                rows={3}
                placeholder="Describe el conocimiento de saber."
                className="min-h-24 resize-none rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm leading-6 text-[var(--foreground)] outline-none transition placeholder:text-[var(--muted)]/70 focus:border-[var(--accent)]"
              />
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                type="submit"
                disabled={isBusy}
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
              >
                {state === "saving" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : editingId === null ? (
                  <Plus className="h-4 w-4" />
                ) : (
                  <CheckCircle2 className="h-4 w-4" />
                )}
                {editingId === null ? "Crear SABER" : "Guardar SABER"}
              </button>
              {editingId !== null ? (
                <button
                  type="button"
                  onClick={resetForm}
                  className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm font-semibold text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                >
                  <X className="h-4 w-4" />
                  Cancelar
                </button>
              ) : null}
            </div>
          </form>

          {saber.length === 0 ? (
            <CurriculumEmptyNote>
              Sin conocimientos SABER registrados para esta competencia.
            </CurriculumEmptyNote>
          ) : (
            <div className="grid gap-2">
              {saber.map((item) => (
                <div
                  key={item.id}
                  className={cn(
                    "grid gap-3 rounded-lg border bg-white px-3 py-2 sm:grid-cols-[1fr_auto]",
                    editingId === item.id
                      ? "border-[var(--accent)]"
                      : "border-[color:var(--card-border)]",
                  )}
                >
                  <div className="min-w-0">
                    <p className="text-sm leading-6 break-words text-[var(--foreground)]">
                      {item.descripcion}
                    </p>
                    {item.resultado_id !== null ? (
                      <p className="mt-1 text-xs text-[var(--muted)]">
                        Asignacion secundaria a RAP disponible
                      </p>
                    ) : null}
                  </div>
                  <div className="flex items-start gap-2">
                    <button
                      type="button"
                      onClick={() => handleEdit(item)}
                      className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-1.5 text-xs font-semibold text-[var(--foreground)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                    >
                      <Edit3 className="h-4 w-4" />
                      Editar
                    </button>
                    <button
                      type="button"
                      disabled={state === "deleting"}
                      onClick={() => void handleDelete(item)}
                      className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-800 transition hover:bg-rose-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
                    >
                      <Trash2 className="h-4 w-4" />
                      Eliminar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="grid gap-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs font-semibold tracking-[0.14em] text-[var(--muted)] uppercase">
              Proceso
            </p>
            <span className="inline-flex min-h-7 items-center rounded-full border border-[color:var(--card-border)] bg-white px-2.5 py-1 text-xs font-semibold text-[var(--foreground)]">
              {proceso.length} registrado(s)
            </span>
          </div>

          {procesoState === "loading" ? (
            <div className="flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-xs text-[var(--muted)]">
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando conocimientos PROCESO...
            </div>
          ) : null}

          {procesoErrorMessage !== null ? (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm leading-6 text-rose-900"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <p>{procesoErrorMessage}</p>
            </div>
          ) : null}

          {procesoMessage !== null ? (
            <div
              role="status"
              className="flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm leading-6 text-emerald-900"
            >
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
              <p>{procesoMessage}</p>
            </div>
          ) : null}

          <form
            onSubmit={(event) => void handleProcesoSubmit(event)}
            className="grid gap-3 rounded-lg bg-white p-3"
          >
            <label className="grid gap-2">
              <span className="text-xs font-semibold tracking-[0.14em] text-[var(--muted)] uppercase">
                descripcion
              </span>
              <textarea
                value={procesoForm.descripcion}
                onChange={(event) =>
                  setProcesoForm({ descripcion: event.target.value })
                }
                rows={3}
                placeholder="Describe el conocimiento de proceso."
                className="min-h-24 resize-none rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm leading-6 text-[var(--foreground)] outline-none transition placeholder:text-[var(--muted)]/70 focus:border-[var(--accent)]"
              />
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                type="submit"
                disabled={isProcesoBusy}
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
              >
                {procesoState === "saving" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : procesoEditingId === null ? (
                  <Plus className="h-4 w-4" />
                ) : (
                  <CheckCircle2 className="h-4 w-4" />
                )}
                {procesoEditingId === null ? "Crear PROCESO" : "Guardar PROCESO"}
              </button>
              {procesoEditingId !== null ? (
                <button
                  type="button"
                  onClick={resetProcesoForm}
                  className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm font-semibold text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                >
                  <X className="h-4 w-4" />
                  Cancelar
                </button>
              ) : null}
            </div>
          </form>

          {proceso.length === 0 ? (
            <CurriculumEmptyNote>
              Sin conocimientos PROCESO registrados para esta competencia.
            </CurriculumEmptyNote>
          ) : (
            <div className="grid gap-2">
              {proceso.map((item) => (
                <div
                  key={item.id}
                  className={cn(
                    "grid gap-3 rounded-lg border bg-white px-3 py-2 sm:grid-cols-[1fr_auto]",
                    procesoEditingId === item.id
                      ? "border-[var(--accent)]"
                      : "border-[color:var(--card-border)]",
                  )}
                >
                  <div className="min-w-0">
                    <p className="text-sm leading-6 break-words text-[var(--foreground)]">
                      {item.descripcion}
                    </p>
                    {item.resultado_id !== null ? (
                      <p className="mt-1 text-xs text-[var(--muted)]">
                        Asignacion secundaria a RAP disponible
                      </p>
                    ) : null}
                  </div>
                  <div className="flex items-start gap-2">
                    <button
                      type="button"
                      onClick={() => handleProcesoEdit(item)}
                      className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-1.5 text-xs font-semibold text-[var(--foreground)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                    >
                      <Edit3 className="h-4 w-4" />
                      Editar
                    </button>
                    <button
                      type="button"
                      disabled={procesoState === "deleting"}
                      onClick={() => void handleProcesoDelete(item)}
                      className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-800 transition hover:bg-rose-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
                    >
                      <Trash2 className="h-4 w-4" />
                      Eliminar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function ProgramaCriteriosPanel({
  competencia,
  criterios,
  onCriteriosSynced,
  referenciaId,
}: Readonly<{
  competencia: ProgramaCompetencia;
  criterios: CriterioEvaluacionCurricular[];
  onCriteriosSynced: (result: CriterioListResponse) => void;
  referenciaId: string;
}>): React.JSX.Element {
  const [items, setItems] = useState<CriterioEvaluacionCurricular[]>(criterios);
  const [form, setForm] = useState<ConocimientoFormState>(
    EMPTY_CONOCIMIENTO_FORM,
  );
  const [editingId, setEditingId] = useState<string | null>(null);
  const [state, setState] = useState<OperationState>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const sorted = useMemo(() => sortByOrder(items), [items]);

  useEffect(() => {
    setItems(criterios);
  }, [criterios]);

  useEffect(() => {
    let isCurrent = true;

    const loadCriterios = async (): Promise<void> => {
      setState("loading");
      setErrorMessage(null);

      try {
        const result = await listProgramaCriterios(
          referenciaId,
          competencia.id,
        );
        if (isCurrent) {
          setItems(result.criterios);
          onCriteriosSynced(result);
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

    void loadCriterios();

    return () => {
      isCurrent = false;
    };
  }, [competencia.id, onCriteriosSynced, referenciaId]);

  const resetForm = (): void => {
    setForm(EMPTY_CONOCIMIENTO_FORM);
    setEditingId(null);
  };

  const syncItems = (result: CriterioListResponse): void => {
    setItems(result.criterios);
    onCriteriosSynced(result);
  };

  const handleSubmit = async (
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> => {
    event.preventDefault();
    const validationMessage = validateConocimientoForm(form);
    if (validationMessage !== null) {
      setErrorMessage(validationMessage);
      notify.warning("Revisa el criterio de evaluacion", {
        description: validationMessage,
      });
      return;
    }

    setState("saving");
    setErrorMessage(null);
    setMessage(null);

    try {
      const payload = { descripcion: form.descripcion.trim() };
      const result =
        editingId === null
          ? await createProgramaCriterio(
              referenciaId,
              competencia.id,
              payload,
            )
          : await updateProgramaCriterio(
              referenciaId,
              competencia.id,
              editingId,
              payload,
            );

      syncItems(result);
      resetForm();
      setMessage(
        editingId === null
          ? "Criterio de evaluacion registrado."
          : "Criterio de evaluacion actualizado.",
      );
      notify.success("Criterios de evaluacion sincronizados", {
        description: "El borrador conserva la estructura curricular actual.",
      });
    } catch (error) {
      const detail = getErrorMessage(error);
      setErrorMessage(detail);
      notify.error("No fue posible guardar el criterio de evaluacion", {
        description: detail,
      });
    } finally {
      setState("idle");
    }
  };

  const handleEdit = (criterio: CriterioEvaluacionCurricular): void => {
    setEditingId(criterio.id);
    setForm({ descripcion: criterio.descripcion });
    setMessage(null);
    setErrorMessage(null);
  };

  const handleDelete = async (
    criterio: CriterioEvaluacionCurricular,
  ): Promise<void> => {
    const confirmed = window.confirm(
      "Eliminar este criterio de evaluacion? Esta accion requiere confirmacion.",
    );
    if (!confirmed) {
      return;
    }

    setState("deleting");
    setErrorMessage(null);
    setMessage(null);

    try {
      await deleteProgramaCriterio(
        referenciaId,
        competencia.id,
        criterio.id,
      );
      const result = await listProgramaCriterios(
        referenciaId,
        competencia.id,
      );
      syncItems(result);
      if (editingId === criterio.id) {
        resetForm();
      }
      setMessage("Criterio de evaluacion eliminado.");
      notify.success("Criterio de evaluacion eliminado", {
        description: "El borrador fue actualizado con la lista vigente.",
      });
    } catch (error) {
      const detail = getErrorMessage(error);
      setErrorMessage(detail);
      notify.error("No fue posible eliminar el criterio de evaluacion", {
        description: detail,
      });
    } finally {
      setState("idle");
    }
  };

  const isBusy = state === "loading" || state === "saving" || state === "deleting";

  return (
    <section className="rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-white text-[var(--accent-strong)]">
            <ClipboardCheck className="h-4 w-4" />
          </span>
          <h4 className="text-sm font-semibold text-[var(--foreground)]">
            Criterios de evaluacion
          </h4>
        </div>
        <span className="text-xs font-semibold text-[var(--muted)]">
          {sorted.length}
        </span>
      </div>

      <div className="mt-3 grid gap-2">
        {state === "loading" ? (
          <div className="flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-xs text-[var(--muted)]">
            <Loader2 className="h-4 w-4 animate-spin" />
            Cargando criterios de evaluacion...
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

        {message !== null ? (
          <div
            role="status"
            className="flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm leading-6 text-emerald-900"
          >
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            <p>{message}</p>
          </div>
        ) : null}

        <form
          onSubmit={(event) => void handleSubmit(event)}
          className="grid gap-3 rounded-lg bg-white p-3"
        >
          <label className="grid gap-2">
            <span className="text-xs font-semibold tracking-[0.14em] text-[var(--muted)] uppercase">
              descripcion
            </span>
            <textarea
              value={form.descripcion}
              onChange={(event) =>
                setForm({ descripcion: event.target.value })
              }
              rows={3}
              placeholder="Describe el criterio de evaluacion."
              className="min-h-24 resize-none rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm leading-6 text-[var(--foreground)] outline-none transition placeholder:text-[var(--muted)]/70 focus:border-[var(--accent)]"
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              type="submit"
              disabled={isBusy}
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
            >
              {state === "saving" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : editingId === null ? (
                <Plus className="h-4 w-4" />
              ) : (
                <CheckCircle2 className="h-4 w-4" />
              )}
              {editingId === null ? "Crear criterio" : "Guardar criterio"}
            </button>
            {editingId !== null ? (
              <button
                type="button"
                onClick={resetForm}
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm font-semibold text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
              >
                <X className="h-4 w-4" />
                Cancelar
              </button>
            ) : null}
          </div>
        </form>

        {sorted.length === 0 ? (
          <CurriculumEmptyNote>
            Sin criterios de evaluacion registrados para esta competencia.
          </CurriculumEmptyNote>
        ) : (
          <div className="grid gap-2">
            {sorted.map((item) => (
              <div
                key={item.id}
                className={cn(
                  "grid gap-3 rounded-lg border bg-white px-3 py-2 sm:grid-cols-[1fr_auto]",
                  editingId === item.id
                    ? "border-[var(--accent)]"
                    : "border-[color:var(--card-border)]",
                )}
              >
                <div className="min-w-0">
                  <p className="text-sm leading-6 break-words text-[var(--foreground)]">
                    {item.descripcion}
                  </p>
                  {item.resultado_id !== null ? (
                    <p className="mt-1 text-xs text-[var(--muted)]">
                      Asignacion secundaria a RAP disponible
                    </p>
                  ) : null}
                </div>
                <div className="flex items-start gap-2">
                  <button
                    type="button"
                    onClick={() => handleEdit(item)}
                    className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-1.5 text-xs font-semibold text-[var(--foreground)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                  >
                    <Edit3 className="h-4 w-4" />
                    Editar
                  </button>
                  <button
                    type="button"
                    disabled={state === "deleting"}
                    onClick={() => void handleDelete(item)}
                    className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-800 transition hover:bg-rose-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
                  >
                    <Trash2 className="h-4 w-4" />
                    Eliminar
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function ProgramaResultadosManager({
  competencia,
  onResultadosSynced,
  referenciaId,
}: Readonly<{
  competencia: ProgramaCompetencia;
  onResultadosSynced: (result: ResultadoAprendizajeListResponse) => void;
  referenciaId: string;
}>): React.JSX.Element {
  const [resultados, setResultados] = useState<ResultadoAprendizaje[]>(
    competencia.resultados ?? [],
  );
  const [form, setForm] = useState<ResultadoFormState>(EMPTY_RESULTADO_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [state, setState] = useState<OperationState>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const sortedResultados = useMemo(() => {
    return [...resultados].sort((left, right) => {
      const leftOrder = left.orden ?? Number.MAX_SAFE_INTEGER;
      const rightOrder = right.orden ?? Number.MAX_SAFE_INTEGER;
      return leftOrder - rightOrder;
    });
  }, [resultados]);

  useEffect(() => {
    setResultados(competencia.resultados ?? []);
  }, [competencia.resultados]);

  useEffect(() => {
    let isCurrent = true;

    const loadResultados = async (): Promise<void> => {
      setState("loading");
      setErrorMessage(null);

      try {
        const result = await listProgramaResultados(referenciaId, competencia.id);
        if (isCurrent) {
          setResultados(result.resultados);
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

    void loadResultados();

    return () => {
      isCurrent = false;
    };
  }, [competencia.id, referenciaId]);

  const resetForm = (): void => {
    setForm(EMPTY_RESULTADO_FORM);
    setEditingId(null);
  };

  const syncResultados = (result: ResultadoAprendizajeListResponse): void => {
    setResultados(result.resultados);
    onResultadosSynced(result);
  };

  const handleSubmit = async (
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> => {
    event.preventDefault();
    const validationMessage = validateResultadoForm(form);
    if (validationMessage !== null) {
      setErrorMessage(validationMessage);
      notify.warning("Revisa el resultado de aprendizaje", {
        description: validationMessage,
      });
      return;
    }

    setState("saving");
    setErrorMessage(null);
    setMessage(null);

    try {
      const payload = {
        descripcion: form.descripcion.trim(),
        codigo_resultado: form.codigo_resultado.trim() || null,
      };
      const result =
        editingId === null
          ? await createProgramaResultado(referenciaId, competencia.id, payload)
          : await updateProgramaResultado(
              referenciaId,
              competencia.id,
              editingId,
              payload,
            );

      syncResultados(result);
      resetForm();
      setMessage(
        editingId === null
          ? "Resultado de aprendizaje registrado."
          : "Resultado de aprendizaje actualizado.",
      );
      notify.success("Resultados sincronizados", {
        description: "El borrador conserva la estructura curricular actual.",
      });
    } catch (error) {
      const detail = getErrorMessage(error);
      setErrorMessage(detail);
      notify.error("No fue posible guardar el resultado", {
        description: detail,
      });
    } finally {
      setState("idle");
    }
  };

  const handleEdit = (resultado: ResultadoAprendizaje): void => {
    setEditingId(resultado.id);
    setForm({
      codigo_resultado: resultado.codigo_resultado ?? "",
      descripcion: resultado.descripcion,
    });
    setMessage(null);
    setErrorMessage(null);
  };

  const handleDelete = async (
    resultado: ResultadoAprendizaje,
  ): Promise<void> => {
    const confirmed = window.confirm(
      "Eliminar este resultado de aprendizaje? Esta accion requiere confirmacion.",
    );
    if (!confirmed) {
      return;
    }

    setState("deleting");
    setErrorMessage(null);
    setMessage(null);

    try {
      await deleteProgramaResultado(referenciaId, competencia.id, resultado.id);
      const result = await listProgramaResultados(referenciaId, competencia.id);
      syncResultados(result);
      if (editingId === resultado.id) {
        resetForm();
      }
      setMessage("Resultado de aprendizaje eliminado.");
      notify.success("Resultado eliminado", {
        description: "El borrador fue actualizado con la lista vigente.",
      });
    } catch (error) {
      const detail = getErrorMessage(error);
      setErrorMessage(detail);
      notify.error("No fue posible eliminar el resultado", {
        description: detail,
      });
    } finally {
      setState("idle");
    }
  };

  const isBusy = state === "loading" || state === "saving" || state === "deleting";

  return (
    <section className="rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] p-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-white text-[var(--accent-strong)]">
            <ListChecks className="h-4 w-4" />
          </span>
          <div>
            <h4 className="text-sm font-semibold text-[var(--foreground)]">
              Resultados de aprendizaje
            </h4>
            <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
              Asociados a esta competencia y guardados en el mismo borrador.
            </p>
          </div>
        </div>
        <span className="text-xs font-semibold text-[var(--muted)]">
          {sortedResultados.length}
        </span>
      </div>

      <div className="mt-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h4 className="text-sm font-semibold text-[var(--foreground)]">
            Registro manual de resultados
          </h4>
          <span className="inline-flex min-h-7 items-center rounded-full border border-[color:var(--card-border)] bg-white px-2.5 py-1 text-xs font-semibold text-[var(--foreground)]">
            {sortedResultados.length} registrado(s)
          </span>
        </div>
      </div>

      {state === "loading" ? (
        <div className="mt-3 flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-xs text-[var(--muted)]">
          <Loader2 className="h-4 w-4 animate-spin" />
          Cargando resultados...
        </div>
      ) : null}

      {errorMessage !== null ? (
        <div
          role="alert"
          className="mt-3 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm leading-6 text-rose-900"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{errorMessage}</p>
        </div>
      ) : null}

      {message !== null ? (
        <div
          role="status"
          className="mt-3 flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm leading-6 text-emerald-900"
        >
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{message}</p>
        </div>
      ) : null}

      <form
        onSubmit={(event) => void handleSubmit(event)}
        className="mt-3 grid gap-3 rounded-lg bg-white p-3"
      >
        <div className="grid gap-3 sm:grid-cols-[minmax(10rem,14rem)_1fr]">
          <label className="grid gap-2">
            <span className="text-xs font-semibold tracking-[0.14em] text-[var(--muted)] uppercase">
              codigo_resultado
            </span>
            <input
              value={form.codigo_resultado}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  codigo_resultado: event.target.value,
                }))
              }
              placeholder="Ej. RAP-01"
              className="min-h-10 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm text-[var(--foreground)] outline-none transition placeholder:text-[var(--muted)]/70 focus:border-[var(--accent)]"
            />
          </label>
          <label className="grid gap-2">
            <span className="text-xs font-semibold tracking-[0.14em] text-[var(--muted)] uppercase">
              descripcion
            </span>
            <textarea
              value={form.descripcion}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  descripcion: event.target.value,
                }))
              }
              rows={3}
              placeholder="Describe el resultado de aprendizaje."
              className="min-h-24 resize-none rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm leading-6 text-[var(--foreground)] outline-none transition placeholder:text-[var(--muted)]/70 focus:border-[var(--accent)]"
            />
          </label>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="submit"
            disabled={isBusy}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
          >
            {state === "saving" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : editingId === null ? (
              <Plus className="h-4 w-4" />
            ) : (
              <CheckCircle2 className="h-4 w-4" />
            )}
            {editingId === null ? "Crear resultado" : "Guardar resultado"}
          </button>
          {editingId !== null ? (
            <button
              type="button"
              onClick={resetForm}
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm font-semibold text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
            >
              <X className="h-4 w-4" />
              Cancelar
            </button>
          ) : null}
        </div>
      </form>

      {sortedResultados.length === 0 ? (
        <p className="mt-3 rounded-lg border border-dashed border-[color:var(--card-border)] bg-white/70 px-3 py-3 text-sm text-[var(--muted)]">
          Sin resultados de aprendizaje registrados para esta competencia.
        </p>
      ) : (
        <div className="mt-3 grid gap-2">
          {sortedResultados.map((resultado) => (
            <div
              key={resultado.id}
              className={cn(
                "grid gap-3 rounded-lg border bg-white p-3 sm:grid-cols-[1fr_auto]",
                editingId === resultado.id
                  ? "border-[var(--accent)]"
                  : "border-[color:var(--card-border)]",
              )}
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  {resultado.codigo_resultado !== null ? (
                    <span className="rounded-lg bg-[var(--accent-soft)] px-2 py-1 text-xs font-semibold text-[var(--accent-strong)]">
                      {resultado.codigo_resultado}
                    </span>
                  ) : null}
                  <span className="text-xs font-semibold text-[var(--muted)]">
                    {resultado.estado}
                  </span>
                </div>
                <p className="mt-2 text-sm leading-6 break-words text-[var(--foreground)]">
                  {resultado.descripcion}
                </p>
              </div>
              <div className="flex items-start gap-2">
                <button
                  type="button"
                  onClick={() => handleEdit(resultado)}
                  className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-1.5 text-xs font-semibold text-[var(--foreground)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                >
                  <Edit3 className="h-4 w-4" />
                  Editar
                </button>
                <button
                  type="button"
                  disabled={state === "deleting"}
                  onClick={() => void handleDelete(resultado)}
                  className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-800 transition hover:bg-rose-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
                >
                  <Trash2 className="h-4 w-4" />
                  Eliminar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export function ProgramaCompetenciasManager({
  competencias,
  onCompetenciasSynced,
  referenciaId,
}: Readonly<{
  competencias: ProgramaCompetencia[];
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

  const handleResultadosSynced = useCallback(
    (result: ResultadoAprendizajeListResponse): void => {
      onCompetenciasSynced({
        referencia_id: result.referencia_id,
        programa_id:
          competencias.find((item) => item.id === result.competencia_id)
            ?.programa_id ?? null,
        competencias: competencias.map((item) =>
          item.id === result.competencia_id
            ? { ...item, resultados: result.resultados }
            : item,
        ),
      });
    },
    [competencias, onCompetenciasSynced],
  );

  const handleConocimientosSaberSynced = useCallback(
    (result: ConocimientoSaberListResponse): void => {
      onCompetenciasSynced({
        referencia_id: result.referencia_id,
        programa_id:
          competencias.find((item) => item.id === result.competencia_id)
            ?.programa_id ?? null,
        competencias: competencias.map((item) => {
          if (item.id !== result.competencia_id) {
            return item;
          }

          const procesos = (item.conocimientos ?? []).filter(
            (conocimiento) => conocimiento.tipo === "PROCESO",
          );
          return {
            ...item,
            conocimientos: [...result.conocimientos, ...procesos],
          };
        }),
      });
    },
    [competencias, onCompetenciasSynced],
  );

  const handleConocimientosProcesoSynced = useCallback(
    (result: ConocimientoProcesoListResponse): void => {
      onCompetenciasSynced({
        referencia_id: result.referencia_id,
        programa_id:
          competencias.find((item) => item.id === result.competencia_id)
            ?.programa_id ?? null,
        competencias: competencias.map((item) => {
          if (item.id !== result.competencia_id) {
            return item;
          }

          const saberes = (item.conocimientos ?? []).filter(
            (conocimiento) => conocimiento.tipo === "SABER",
          );
          return {
            ...item,
            conocimientos: [...saberes, ...result.conocimientos],
          };
        }),
      });
    },
    [competencias, onCompetenciasSynced],
  );

  const handleCriteriosSynced = useCallback(
    (result: CriterioListResponse): void => {
      onCompetenciasSynced({
        referencia_id: result.referencia_id,
        programa_id:
          competencias.find((item) => item.id === result.competencia_id)
            ?.programa_id ?? null,
        competencias: competencias.map((item) =>
          item.id === result.competencia_id
            ? { ...item, criterios: result.criterios }
            : item,
        ),
      });
    },
    [competencias, onCompetenciasSynced],
  );

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
      </div>

      {sortedCompetencias.length === 0 ? (
        <CompetenciaEmptyState />
      ) : (
        <section className="grid gap-3">
          {sortedCompetencias.map((competencia) => (
            <article
              key={competencia.id}
              className={cn(
                "grid gap-4 rounded-lg border bg-white p-4 transition",
                editingId === competencia.id
                  ? "border-[var(--accent)]"
                  : "border-[color:var(--card-border)]",
              )}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent-strong)]">
                      <Layers3 className="h-4 w-4" />
                    </span>
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
              </div>

              <div className="grid gap-3">
                <ProgramaResultadosManager
                  competencia={competencia}
                  referenciaId={referenciaId}
                  onResultadosSynced={handleResultadosSynced}
                />
                <div className="grid gap-3 xl:grid-cols-2">
                  <ProgramaConocimientosPanel
                    competencia={competencia}
                    conocimientos={competencia.conocimientos ?? []}
                    referenciaId={referenciaId}
                    onConocimientosSaberSynced={handleConocimientosSaberSynced}
                    onConocimientosProcesoSynced={
                      handleConocimientosProcesoSynced
                    }
                  />
                  <ProgramaCriteriosPanel
                    competencia={competencia}
                    criterios={competencia.criterios ?? []}
                    referenciaId={referenciaId}
                    onCriteriosSynced={handleCriteriosSynced}
                  />
                </div>
              </div>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}
