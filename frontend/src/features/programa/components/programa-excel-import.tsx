"use client";

import { useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Eye,
  FileSpreadsheet,
  Loader2,
  Upload,
  X,
} from "lucide-react";

import { notify } from "@/components/feedback/notifications";
import {
  confirmProgramaExcelImport,
  previewProgramaExcel,
  ProgramaExcelImportError,
} from "@/features/programa/excel-import-api";
import { cn } from "@/lib/utils";
import type {
  ProgramaExcelImportResponse,
  ProgramaExcelImportState,
  ProgramaExcelPreviewResponse,
} from "@/features/programa/types";

type ExcelState = "idle" | "previewing" | "ready" | "importing" | "done" | "error";

function formatFileSize(sizeBytes: number): string {
  if (sizeBytes < 1024) return `${sizeBytes} B`;
  const sizeKb = sizeBytes / 1024;
  if (sizeKb < 1024) return `${sizeKb.toFixed(1)} KB`;
  return `${(sizeKb / 1024).toFixed(1)} MB`;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ProgramaExcelImportError) {
    return error.detail;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "No fue posible procesar el Excel canonico.";
}

function validateExcelFile(file: File | null): string | null {
  if (file === null) {
    return "Selecciona un archivo Excel .xlsx antes de validar.";
  }
  if (!file.name.toLowerCase().endsWith(".xlsx")) {
    return "Solo se aceptan archivos .xlsx.";
  }
  if (file.size === 0) {
    return "El Excel seleccionado esta vacio.";
  }
  return null;
}

function PreviewPanel({
  imported,
  onOpenCompetencias,
  preview,
}: Readonly<{
  imported: boolean;
  onOpenCompetencias: () => void;
  preview: ProgramaExcelPreviewResponse;
}>): React.JSX.Element {
  return (
    <section
      className={cn(
        "rounded-lg border p-4",
        preview.valid
          ? "border-emerald-200 bg-emerald-50 text-emerald-950"
          : "border-rose-200 bg-rose-50 text-rose-950",
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {preview.valid ? (
            <CheckCircle2 className="h-5 w-5" />
          ) : (
            <AlertCircle className="h-5 w-5" />
          )}
          <p className="text-sm font-semibold">
            {preview.valid ? "Workbook valido" : "Workbook con errores"}
          </p>
        </div>
        <span className="rounded-full bg-white/70 px-2.5 py-1 text-xs font-semibold">
          {imported ? "Importacion confirmada" : preview.estado_validacion}
        </span>
      </div>

      {preview.programa !== null ? (
        <p className="mt-3 text-sm leading-6">
          {preview.programa.codigo_programa} /{" "}
          {preview.programa.nombre_programa}
        </p>
      ) : null}

      <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-4">
        <div>
          <dt className="font-semibold">Resultados</dt>
          <dd>{preview.resumen.resultados}</dd>
        </div>
        <div>
          <dt className="font-semibold">Conocimientos</dt>
          <dd>{preview.resumen.conocimientos}</dd>
        </div>
        <div>
          <dt className="font-semibold">Criterios</dt>
          <dd>{preview.resumen.criterios}</dd>
        </div>
        <div>
          <dt className="font-semibold">Estado</dt>
          <dd>{preview.estado_validacion}</dd>
        </div>
      </dl>

      {preview.pendientes_resumen.total > 0 ? (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-3 text-sm leading-6 text-amber-950">
          <p className="font-semibold">
            {preview.pendientes_resumen.total} excepcion(es) de competencia
          </p>
          <p className="mt-1">
            {preview.pendientes_resumen.conocimientos} conocimiento(s) y{" "}
            {preview.pendientes_resumen.criterios} criterio(s) requieren
            conciliacion porque no tienen competencia confiable.
          </p>
        </div>
      ) : null}

      {preview.competencias.length > 0 ? (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-emerald-200 bg-white/80 px-3 py-3">
          <div className="min-w-0">
            <p className="text-sm font-semibold">
              Vista curricular compacta
            </p>
            <p className="mt-1 text-xs leading-5">
              {preview.resumen.competencias} competencia(s) disponibles para
              revision paginada sin desplegarlas en linea.
            </p>
          </div>
          <button
            type="button"
            onClick={onOpenCompetencias}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-emerald-700 px-3 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
          >
            <Eye className="h-4 w-4" />
            Ver competencias
          </button>
        </div>
      ) : null}

      {preview.errores.length > 0 ? (
        <div className="mt-4 grid gap-2">
          {preview.errores.slice(0, 5).map((issue, index) => (
            <p key={`${issue.hoja}-${issue.fila ?? index}`} className="text-sm">
              {issue.hoja}
              {issue.fila !== null ? ` fila ${issue.fila}` : ""}:{" "}
              {issue.mensaje}
            </p>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function PreviewList({
  emptyLabel,
  items,
}: Readonly<{
  emptyLabel: string;
  items: { id: string; label: string; meta?: string | null }[];
}>): React.JSX.Element {
  if (items.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-[color:var(--card-border)] bg-white px-3 py-2 text-sm text-[var(--muted)]">
        {emptyLabel}
      </p>
    );
  }

  return (
    <div className="grid gap-2">
      {items.map((item) => (
        <article
          key={item.id}
          className="rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2"
        >
          <p className="text-sm leading-6 break-words text-[var(--foreground)]">
            {item.label}
          </p>
          {item.meta !== null && item.meta !== undefined ? (
            <p className="mt-1 text-xs font-semibold text-[var(--muted)]">
              {item.meta}
            </p>
          ) : null}
        </article>
      ))}
    </div>
  );
}

function CompetenciasModal({
  currentIndex,
  onClose,
  onIndexChange,
  preview,
}: Readonly<{
  currentIndex: number;
  onClose: () => void;
  onIndexChange: (index: number) => void;
  preview: ProgramaExcelPreviewResponse;
}>): React.JSX.Element | null {
  const total = preview.competencias.length;
  const safeIndex = total === 0 ? 0 : Math.min(currentIndex, total - 1);
  const competencia = preview.competencias[safeIndex] ?? null;

  if (competencia === null) {
    return null;
  }

  return (
    <div
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4 py-6"
      role="dialog"
    >
      <section className="flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-lg border border-[color:var(--card-border)] bg-white shadow-[0_24px_70px_rgba(15,23,42,0.24)]">
        <header className="flex flex-col gap-4 border-b border-[var(--line)] px-5 py-4">
          <div className="flex items-center justify-between gap-4">
            <h3 className="text-lg font-semibold text-[var(--foreground)]">
              Revisión de Estructura Curricular por Competencia
            </h3>
            <button
              type="button"
              aria-label="Cerrar modal de competencias"
              onClick={onClose}
              className="inline-flex min-h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[color:var(--card-border)] bg-white text-[var(--foreground)] transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="grid gap-1.5 min-w-0 max-w-full">
            <label htmlFor="competencia-select" className="text-xs font-semibold tracking-wider text-[var(--muted)] uppercase">
              Seleccionar competencia
            </label>
            <select
              id="competencia-select"
              value={safeIndex}
              onChange={(e) => onIndexChange(Number(e.target.value))}
              className="w-full max-w-full rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] px-3 py-2 text-sm text-[var(--foreground)] transition outline-none focus:border-[var(--accent)] cursor-pointer truncate"
            >
              {preview.competencias.map((comp, idx) => (
                <option key={comp.competencia_id} value={idx}>
                  [{comp.codigo_competencia}] {comp.nombre_competencia.substring(0, 80)}
                  {comp.nombre_competencia.length > 80 ? "..." : ""}
                </option>
              ))}
            </select>
          </div>
        </header>

        <div className="min-h-0 overflow-y-auto px-5 py-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg bg-[var(--paper-strong)] px-3 py-2">
              <p className="text-xs font-semibold text-[var(--muted)]">
                Resultados
              </p>
              <p className="mt-1 text-sm font-semibold text-[var(--foreground)]">
                {competencia.resultados_detalle.length}
              </p>
            </div>
            <div className="rounded-lg bg-[var(--paper-strong)] px-3 py-2">
              <p className="text-xs font-semibold text-[var(--muted)]">
                Conocimientos
              </p>
              <p className="mt-1 text-sm font-semibold text-[var(--foreground)]">
                {competencia.conocimientos_detalle.length}
              </p>
            </div>
            <div className="rounded-lg bg-[var(--paper-strong)] px-3 py-2">
              <p className="text-xs font-semibold text-[var(--muted)]">
                Criterios
              </p>
              <p className="mt-1 text-sm font-semibold text-[var(--foreground)]">
                {competencia.criterios_detalle.length}
              </p>
            </div>
          </div>

          <div className="mt-4 grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <section className="min-w-0 rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] p-3">
              <h4 className="text-sm font-semibold text-[var(--foreground)]">
                Resultados de aprendizaje
              </h4>
              <div className="mt-3">
                <PreviewList
                  emptyLabel="Sin resultados en el preview."
                  items={competencia.resultados_detalle.map((item) => ({
                    id: item.rap_id,
                    label: item.descripcion,
                    meta: item.rap_numero ?? item.rap_id,
                  }))}
                />
              </div>
            </section>

            <section className="min-w-0 rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] p-3">
              <h4 className="text-sm font-semibold text-[var(--foreground)]">
                Conocimientos
              </h4>
              <div className="mt-3">
                <PreviewList
                  emptyLabel="Sin conocimientos en el preview."
                  items={competencia.conocimientos_detalle.map(
                    (item, index) => ({
                      id: `${item.tipo_conocimiento}-${index}`,
                      label: item.descripcion,
                      meta:
                        item.rap_id === null
                          ? item.tipo_conocimiento
                          : `${item.tipo_conocimiento} / ${item.rap_id}`,
                    }),
                  )}
                />
              </div>
            </section>

            <section className="min-w-0 rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] p-3 lg:col-span-2">
              <h4 className="text-sm font-semibold text-[var(--foreground)]">
                Criterios
              </h4>
              <div className="mt-3">
                <PreviewList
                  emptyLabel="Sin criterios en el preview."
                  items={competencia.criterios_detalle.map((item, index) => ({
                    id: `${competencia.competencia_id}-criterio-${index}`,
                    label: item.descripcion,
                    meta: item.rap_id,
                  }))}
                />
              </div>
            </section>
          </div>
        </div>
      </section>
    </div>
  );
}

export function ProgramaExcelImport({
  currentResult,
  onImported,
  onBeforePreview,
  onPreviewed,
  referenciaId,
}: Readonly<{
  currentResult: ProgramaExcelImportState | null;
  onImported: (result: ProgramaExcelImportResponse) => void;
  onBeforePreview?: () => Promise<boolean>;
  onPreviewed: (result: ProgramaExcelPreviewResponse) => void;
  referenciaId: string;
}>): React.JSX.Element {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [state, setState] = useState<ExcelState>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [isCompetenciasModalOpen, setIsCompetenciasModalOpen] =
    useState(false);
  const [competenciaModalIndex, setCompetenciaModalIndex] = useState(0);

  const preview = currentResult?.preview ?? null;
  const imported = currentResult?.confirmacion.estado === "IMPORTADO";

  const handlePreview = async (): Promise<void> => {
    const validationError = validateExcelFile(selectedFile);
    if (validationError !== null) {
      setState("error");
      setMessage(validationError);
      notify.warning("No se pudo validar el Excel", {
        description: validationError,
      });
      return;
    }

    const file = selectedFile;
    if (file === null) return;

    setState("previewing");
    setMessage(null);

    try {
      const draftReady = onBeforePreview === undefined || (await onBeforePreview());
      if (!draftReady) {
        setState("error");
        setMessage(
          "No fue posible sincronizar el borrador antes de validar el Excel.",
        );
        return;
      }

      const result = await previewProgramaExcel(referenciaId, file);
      onPreviewed(result);
      setState(result.valid ? "ready" : "error");
      setMessage(
        result.valid
          ? "Preview valido. Puedes confirmar la importacion."
          : "El Excel no cumple el contrato canonico.",
      );
      notify[result.valid ? "success" : "warning"](
        result.valid ? "Excel validado" : "Excel con errores",
        {
          description: result.valid
            ? "El preview esta listo para confirmar."
            : "Corrige el archivo y vuelve a cargarlo.",
        },
      );
    } catch (error) {
      const detail = getErrorMessage(error);
      setState("error");
      setMessage(detail);
      notify.error("No fue posible validar el Excel", { description: detail });
    }
  };

  const handleImport = async (): Promise<void> => {
    setState("importing");
    setMessage(null);

    try {
      const result = await confirmProgramaExcelImport(referenciaId);
      onImported(result);
      setState("done");
      setMessage("Importacion relacional confirmada.");
      notify.success("Excel importado", {
        description: "La estructura curricular quedo materializada.",
      });
    } catch (error) {
      const detail = getErrorMessage(error);
      setState("error");
      setMessage(detail);
      notify.error("No fue posible importar el Excel", { description: detail });
    }
  };

  return (
    <section className="grid gap-4">
      <div className="rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="inline-flex h-11 w-11 items-center justify-center rounded-lg bg-white text-[var(--accent-strong)]">
              <FileSpreadsheet className="h-5 w-5" />
            </span>
            <div>
              <p className="text-sm font-semibold text-[var(--foreground)]">
                Excel canonico curricular
              </p>
              <p className="mt-1 text-sm leading-6 text-[var(--muted)]">
                Este archivo es la fuente estructurada para poblar programa,
                competencias, resultados, conocimientos y criterios.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[var(--accent)] bg-white px-3 py-2 text-sm font-semibold text-[var(--accent-strong)] transition hover:bg-[var(--accent-soft)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            <Upload className="h-4 w-4" />
            Seleccionar Excel
          </button>
        </div>

        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          className="sr-only"
          onChange={(event) => {
            const file = event.target.files?.[0] ?? null;
            setSelectedFile(file);
            setState("idle");
            setMessage(file === null ? null : "Excel listo para validar.");
          }}
        />

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-[var(--foreground)]">
              {selectedFile?.name ??
                currentResult?.documento?.original_filename ??
                "Sin archivo seleccionado"}
            </p>
            <p className="mt-1 text-xs text-[var(--muted)]">
              {selectedFile === null
                ? "Workbook .xlsx canonico"
                : formatFileSize(selectedFile.size)}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={state === "previewing" || state === "importing"}
              onClick={() => void handlePreview()}
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[var(--accent)] bg-white px-3 py-2 text-sm font-semibold text-[var(--accent-strong)] transition hover:bg-[var(--accent-soft)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
            >
              {state === "previewing" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FileSpreadsheet className="h-4 w-4" />
              )}
              Validar preview
            </button>
            <button
              type="button"
              disabled={!preview?.valid || imported || state === "importing"}
              onClick={() => void handleImport()}
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
            >
              {state === "importing" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle2 className="h-4 w-4" />
              )}
              Confirmar importacion
            </button>
          </div>
        </div>
      </div>

      {message !== null ? (
        <div
          role={state === "error" ? "alert" : "status"}
          className={cn(
            "flex items-start gap-2 rounded-lg border px-4 py-3 text-sm leading-6",
            state === "error"
              ? "border-rose-200 bg-rose-50 text-rose-900"
              : "border-emerald-200 bg-emerald-50 text-emerald-900",
          )}
        >
          {state === "error" ? (
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          ) : (
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          )}
          <p>{message}</p>
        </div>
      ) : null}

      {preview !== null ? (
        <PreviewPanel
          imported={imported}
          preview={preview}
          onOpenCompetencias={() => {
            setCompetenciaModalIndex(0);
            setIsCompetenciasModalOpen(true);
          }}
        />
      ) : null}

      {preview !== null && isCompetenciasModalOpen ? (
        <CompetenciasModal
          currentIndex={competenciaModalIndex}
          preview={preview}
          onClose={() => setIsCompetenciasModalOpen(false)}
          onIndexChange={setCompetenciaModalIndex}
        />
      ) : null}
    </section>
  );
}
