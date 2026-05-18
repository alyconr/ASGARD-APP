"use client";

import { useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  FileSpreadsheet,
  Loader2,
  Upload,
} from "lucide-react";

import {
  confirmProjectExcelImport,
  uploadProjectExcelPreview,
} from "@/features/proyecto/excel-import-api";
import { notify } from "@/components/feedback/notifications";
import type {
  ExcelFasePreview,
  ExcelPreviewSummary,
  ExcelValidationIssue,
  ProyectoExcelPreviewState,
  ProyectoStoredDocument,
} from "@/features/proyecto/types";
import { cn } from "@/lib/utils";

type UploadState = "idle" | "uploading" | "preview" | "confirming" | "success" | "error";

function formatFileSize(sizeBytes: number): string {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }

  const sizeKb = sizeBytes / 1024;
  if (sizeKb < 1024) {
    return `${sizeKb.toFixed(1)} KB`;
  }

  return `${(sizeKb / 1024).toFixed(1)} MB`;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && "detail" in error) {
    return (error as { detail: string }).detail;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "No fue posible procesar el Excel del proyecto.";
}

function validateExcelFile(file: File | null): string | null {
  if (file === null) {
    return "Selecciona un archivo Excel antes de cargar.";
  }

  if (
    file.type !==
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" &&
    !file.name.toLowerCase().endsWith(".xlsx")
  ) {
    return "Solo se aceptan archivos .xlsx.";
  }

  if (file.size === 0) {
    return "El Excel seleccionado esta vacio.";
  }

  return null;
}

function PreviewSection({
  preview,
}: Readonly<{
  preview: ProyectoExcelPreviewState["preview"];
}>): React.JSX.Element | null {
  if (preview === null) {
    return null;
  }

  return (
    <section className="grid gap-4">
      <div
        className={cn(
          "rounded-lg border p-4",
          preview.valid
            ? "border-emerald-200 bg-emerald-50 text-emerald-900"
            : "border-amber-200 bg-amber-50 text-amber-950",
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
              {preview.valid
                ? "Excel valido - listo para confirmar importacion"
                : "Excel con errores de validacion"}
            </p>
          </div>
          <span className="text-xs font-semibold">{preview.estado_validacion}</span>
        </div>

        {preview.proyecto !== null ? (
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="font-semibold">Codigo del proyecto</dt>
              <dd className="mt-1">{preview.proyecto.codigo_proyecto}</dd>
            </div>
            <div>
              <dt className="font-semibold">Version</dt>
              <dd className="mt-1">{preview.proyecto.version_proyecto}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="font-semibold">Nombre del proyecto</dt>
              <dd className="mt-1">{preview.proyecto.nombre_proyecto}</dd>
            </div>
          </dl>
        ) : null}

        <div className="mt-4 grid grid-cols-3 gap-3 text-center">
          <div className="rounded-lg bg-white/60 p-3">
            <p className="text-2xl font-bold">{preview.resumen.proyecto}</p>
            <p className="text-xs text-[var(--muted)]">Proyecto</p>
          </div>
          <div className="rounded-lg bg-white/60 p-3">
            <p className="text-2xl font-bold">{preview.resumen.fases}</p>
            <p className="text-xs text-[var(--muted)]">Fases</p>
          </div>
          <div className="rounded-lg bg-white/60 p-3">
            <p className="text-2xl font-bold">{preview.resumen.actividades}</p>
            <p className="text-xs text-[var(--muted)]">Actividades</p>
          </div>
        </div>
      </div>

      {preview.fases.length > 0 ? (
        <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-4">
          <p className="text-xs font-semibold tracking-[0.16em] text-[var(--muted)] uppercase">
            Fases detectadas
          </p>
          <ul className="mt-3 grid gap-2">
            {preview.fases.map((fase) => (
              <li
                key={fase.fase_id}
                className="flex items-center justify-between rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] px-3 py-2 text-sm"
              >
                <span className="font-semibold">{fase.nombre_fase}</span>
                <span className="text-xs text-[var(--muted)]">
                  {fase.actividades} actividad{fase.actividades !== 1 ? "es" : ""}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {preview.errores.length > 0 ? (
        <section className="rounded-lg border border-rose-200 bg-rose-50 p-4">
          <p className="text-sm font-semibold text-rose-900">
            Errores de validacion ({preview.errores.length})
          </p>
          <ul className="mt-2 grid gap-1">
            {preview.errores.map((error, index) => (
              <li
                key={index}
                className="flex items-start gap-2 text-xs text-rose-800"
              >
                <AlertCircle className="mt-0.5 h-3 w-3 shrink-0" />
                <span>
                  [{error.hoja}] {error.mensaje}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}

export function ProyectoExcelImport({
  currentResult,
  onPreview,
  onImported,
  referenciaId,
}: Readonly<{
  currentResult: ProyectoExcelPreviewState | null;
  onPreview: (result: ProyectoExcelPreviewState) => void;
  onImported: (result: ProyectoExcelPreviewState) => void;
  referenciaId: string;
}>): React.JSX.Element {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [state, setState] = useState<UploadState>("idle");
  const [message, setMessage] = useState<string | null>(null);

  const handlePreview = async (): Promise<void> => {
    const validationError = validateExcelFile(selectedFile);
    if (validationError !== null) {
      setState("error");
      setMessage(validationError);
      notify.warning("No se pudo cargar el Excel", {
        description: validationError,
      });
      return;
    }

    const file = selectedFile;
    if (file === null) {
      return;
    }

    setState("uploading");
    setMessage(null);

    try {
      const result = await uploadProjectExcelPreview(referenciaId, file);
      const previewState: ProyectoExcelPreviewState = {
        documento: result.documento ?? null,
        preview: {
          valid: result.valid,
          estado_validacion: result.estado_validacion,
          resumen: result.resumen,
          proyecto: result.proyecto,
          fases: result.fases,
          pendientes_resumen: result.pendientes_resumen,
          errores: result.errores,
        },
        confirmacion: { estado: "PENDIENTE" },
        updated_at: new Date().toISOString(),
      };
      onPreview(previewState);
      setState("preview");
      setMessage(
        result.valid
          ? "Excel validado correctamente. Revisa el preview y confirma la importacion."
          : "El Excel tiene errores. Corrigelos antes de confirmar.",
      );
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      setState("error");
      setMessage(errorMessage);
      notify.error("No fue posible procesar el Excel", {
        description: errorMessage,
      });
    }
  };

  const handleConfirm = async (): Promise<void> => {
    setState("confirming");
    setMessage(null);

    try {
      const result = await confirmProjectExcelImport(referenciaId);
      const importedState: ProyectoExcelPreviewState = {
        documento: currentResult?.documento ?? null,
        preview: currentResult?.preview ?? null,
        confirmacion: {
          estado: "IMPORTADO",
          confirmed_at: new Date().toISOString(),
          proyecto_id: result.proyecto_id,
          fase_ids: result.fase_ids,
          actividad_ids: result.actividad_ids,
          pendientes_resumen: result.pendientes_resumen,
        },
        updated_at: new Date().toISOString(),
      };
      onImported(importedState);
      setState("success");
      setMessage(
        `Importacion completada: ${result.resumen.fases} fases y ${result.resumen.actividades} actividades materializadas.`,
      );
      notify.success("Importacion completada", {
        description: importedState.confirmacion.confirmed_at
          ? `Proyecto creado con ${result.fase_ids.length} fases y ${result.actividad_ids.length} actividades.`
          : "Datos del proyecto actualizados.",
      });
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      setState("error");
      setMessage(errorMessage);
      notify.error("No fue posible confirmar la importacion", {
        description: errorMessage,
      });
    }
  };

  const isImported = currentResult?.confirmacion.estado === "IMPORTADO";
  const hasPreview = currentResult?.preview !== null;
  const hasErrors = currentResult?.preview?.errores.length ?? 0 > 0;
  const canConfirm = hasPreview && !hasErrors && !isImported;

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
                Matriz Excel del proyecto
              </p>
              <p className="mt-1 text-sm leading-6 text-[var(--muted)]">
                Fuente estructurada del proyecto. Define Proyecto, Fases y
                Actividades. El PDF cargado anteriormente es solo evidencia
                documental.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[var(--accent)] bg-white px-3 py-2 text-sm font-semibold text-[var(--accent-strong)] transition hover:bg-[var(--accent-soft)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
            disabled={isImported}
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
            setMessage(file === null ? null : "Archivo listo para previsualizar.");
          }}
        />

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-[var(--foreground)]">
              {selectedFile?.name ?? "Sin archivo seleccionado"}
            </p>
            <p className="mt-1 text-xs text-[var(--muted)]">
              {selectedFile === null
                ? "Excel requerido"
                : formatFileSize(selectedFile.size)}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={state === "uploading" || isImported}
              onClick={() => void handlePreview()}
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
            >
              {state === "uploading" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : isImported ? (
                <CheckCircle2 className="h-4 w-4" />
              ) : (
                <FileSpreadsheet className="h-4 w-4" />
              )}
              {state === "uploading"
                ? "Procesando..."
                : isImported
                  ? "Importado"
                  : "Previsualizar"}
            </button>

            {canConfirm && (
              <button
                type="button"
                disabled={state === "confirming"}
                onClick={() => void handleConfirm()}
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-emerald-600 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
              >
                {state === "confirming" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-4 w-4" />
                )}
                {state === "confirming" ? "Importando..." : "Confirmar importacion"}
              </button>
            )}
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
              : state === "success"
                ? "border-emerald-200 bg-emerald-50 text-emerald-900"
                : "border-blue-200 bg-blue-50 text-blue-900",
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

      {currentResult?.preview !== null ? (
        <PreviewSection preview={currentResult.preview} />
      ) : null}

      {isImported && currentResult.confirmacion.proyecto_id ? (
        <section className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-emerald-700" />
            <p className="text-sm font-semibold text-emerald-900">
              Importacion confirmada
            </p>
          </div>
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="font-semibold">Proyecto ID</dt>
              <dd className="mt-1 text-xs break-all">
                {currentResult.confirmacion.proyecto_id}
              </dd>
            </div>
            <div>
              <dt className="font-semibold">Fases creadas</dt>
              <dd className="mt-1">
                {currentResult.confirmacion.fase_ids?.length ?? 0}
              </dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="font-semibold">Actividades creadas</dt>
              <dd className="mt-1">
                {currentResult.confirmacion.actividad_ids?.length ?? 0}
              </dd>
            </div>
          </dl>
        </section>
      ) : null}
    </section>
  );
}
