"use client";

import { useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  FileCheck2,
  FileText,
  Loader2,
  Upload,
} from "lucide-react";

import {
  ProgramaPdfUploadError,
  uploadProgramaPdf,
} from "@/features/programa/document-upload-api";
import { notify } from "@/components/feedback/notifications";
import type {
  ProgramaPdfUploadResponse,
  ProgramaPdfUploadResult,
} from "@/features/programa/types";
import { cn } from "@/lib/utils";

type UploadState = "idle" | "uploading" | "success" | "error";

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
  if (error instanceof ProgramaPdfUploadError) {
    return error.detail;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "No fue posible cargar el PDF como evidencia.";
}

function validatePdfFile(file: File | null): string | null {
  if (file === null) {
    return "Selecciona un archivo PDF antes de cargar.";
  }

  if (
    file.type !== "application/pdf" ||
    !file.name.toLowerCase().endsWith(".pdf")
  ) {
    return "Solo se aceptan archivos PDF.";
  }

  if (file.size === 0) {
    return "El PDF seleccionado esta vacio.";
  }

  return null;
}

function DiagnosticResult({
  value,
}: Readonly<{ value: ProgramaPdfUploadResult }>): React.JSX.Element {
  const hasText = value.diagnostico.pages_with_text > 0;

  return (
    <section className={cn("rounded-lg border p-4", hasText ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-amber-200 bg-amber-50 text-amber-950")}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-5 w-5" />
          <p className="text-sm font-semibold">
            {hasText ? "PDF cargado como evidencia documental" : "PDF cargado como evidencia documental (sin texto detectado)"}
          </p>
        </div>
        <span className="text-xs font-semibold">
          {value.diagnostico.pages_with_text}/{value.diagnostico.analyzed_pages}{" "}
          paginas analizadas
        </span>
      </div>

      {value.diagnostico.resumen ? (
        <p className="mt-3 text-sm leading-6">{value.diagnostico.resumen}</p>
      ) : null}

      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="font-semibold">Archivo</dt>
          <dd className="mt-1 break-words">
            {value.documento.original_filename}
          </dd>
        </div>
        <div>
          <dt className="font-semibold">Tamano</dt>
          <dd className="mt-1">{formatFileSize(value.documento.size_bytes)}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="font-semibold">Referencia documental</dt>
          <dd className="mt-1 text-xs break-all">
            {value.documento.storage_key}
          </dd>
        </div>
      </dl>
    </section>
  );
}

export function ProgramaDocumentUpload({
  currentResult,
  onUploaded,
  referenciaId,
}: Readonly<{
  currentResult: ProgramaPdfUploadResult | null;
  onUploaded: (result: ProgramaPdfUploadResponse) => void;
  referenciaId: string;
}>): React.JSX.Element {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [state, setState] = useState<UploadState>("idle");
  const [message, setMessage] = useState<string | null>(null);

  const handleUpload = async (): Promise<void> => {
    const validationError = validatePdfFile(selectedFile);
    if (validationError !== null) {
      setState("error");
      setMessage(validationError);
      notify.warning("No se pudo cargar el PDF", {
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
      const result = await uploadProgramaPdf(referenciaId, file);
      onUploaded(result);
      setState("success");
      setMessage("PDF cargado como evidencia documental.");
      notify.success("PDF cargado como evidencia documental", {
        description: result.diagnostico.resumen || "Archivo almacenado en MinIO.",
      });
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      setState("error");
      setMessage(errorMessage);
      notify.error("No fue posible cargar el PDF", {
        description: errorMessage,
      });
    }
  };

  return (
    <section className="grid gap-4">
      <div className="rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="inline-flex h-11 w-11 items-center justify-center rounded-lg bg-white text-[var(--accent-strong)]">
              <FileText className="h-5 w-5" />
            </span>
            <div>
              <p className="text-sm font-semibold text-[var(--foreground)]">
                PDF del programa de formación
              </p>
              <p className="mt-1 text-sm leading-6 text-[var(--muted)]">
                Se conserva como evidencia documental en MinIO; no se usa para
                extraer informacion curricular.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[var(--accent)] bg-white px-3 py-2 text-sm font-semibold text-[var(--accent-strong)] transition hover:bg-[var(--accent-soft)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            <Upload className="h-4 w-4" />
            Seleccionar PDF
          </button>
        </div>

        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          className="sr-only"
          onChange={(event) => {
            const file = event.target.files?.[0] ?? null;
            setSelectedFile(file);
            setState("idle");
            setMessage(file === null ? null : "Archivo listo para cargar.");
          }}
        />

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-[var(--foreground)]">
              {selectedFile?.name ?? "Sin archivo seleccionado"}
            </p>
            <p className="mt-1 text-xs text-[var(--muted)]">
              {selectedFile === null
                ? "PDF requerido"
                : formatFileSize(selectedFile.size)}
            </p>
          </div>

          <button
            type="button"
            disabled={state === "uploading"}
            onClick={() => void handleUpload()}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
          >
            {state === "uploading" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FileCheck2 className="h-4 w-4" />
            )}
            Cargar como evidencia
          </button>
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

      {currentResult !== null ? (
        <DiagnosticResult value={currentResult} />
      ) : null}
    </section>
  );
}
