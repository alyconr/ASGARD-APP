"use client";

import { useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  FileSpreadsheet,
  Loader2,
  Upload,
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
  preview,
}: Readonly<{ preview: ProgramaExcelPreviewResponse }>): React.JSX.Element {
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
        <span className="text-xs font-semibold">
          {preview.resumen.competencias} competencias
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

export function ProgramaExcelImport({
  currentResult,
  onImported,
  onPreviewed,
  referenciaId,
}: Readonly<{
  currentResult: ProgramaExcelImportState | null;
  onImported: (result: ProgramaExcelImportResponse) => void;
  onPreviewed: (result: ProgramaExcelPreviewResponse) => void;
  referenciaId: string;
}>): React.JSX.Element {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [state, setState] = useState<ExcelState>("idle");
  const [message, setMessage] = useState<string | null>(null);

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

      {preview !== null ? <PreviewPanel preview={preview} /> : null}
    </section>
  );
}
