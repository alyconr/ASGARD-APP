"use client";

import { useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ClipboardCheck,
  Loader2,
  ScanSearch,
} from "lucide-react";

import { notify } from "@/components/feedback/notifications";
import {
  extractProgramaPdf,
  ProgramaExtractionError,
} from "@/features/programa/extraction-api";
import { cn } from "@/lib/utils";
import type {
  FieldTraceStatus,
  PdfLegibilityStatus,
  ProgramaCompetenciaExtraccion,
  ProgramaExtractedField,
  ProgramaExtractedListBlock,
  ProgramaExtractionResult,
} from "@/features/programa/types";

type ExtractionState = "idle" | "extracting" | "success" | "error";

const STATUS_COPY: Record<
  FieldTraceStatus,
  {
    label: string;
    tone: string;
  }
> = {
  EXTRAIDO: {
    label: "Extraido",
    tone: "border-emerald-200 bg-emerald-50 text-emerald-900",
  },
  MANUAL: {
    label: "Manual",
    tone: "border-sky-200 bg-sky-50 text-sky-900",
  },
  CORREGIDO: {
    label: "Corregido",
    tone: "border-blue-200 bg-blue-50 text-blue-900",
  },
  PENDIENTE: {
    label: "Pendiente",
    tone: "border-amber-200 bg-amber-50 text-amber-950",
  },
  VALIDADO: {
    label: "Validado",
    tone: "border-emerald-200 bg-emerald-50 text-emerald-900",
  },
};

const REASON_COPY: Record<string, string> = {
  PDF_ESCANEADO: "PDF escaneado",
  DOCUMENTO_ILEGIBLE: "Documento ilegible",
  BAJA_RESOLUCION: "Baja resolucion",
  ESTRUCTURA_NO_RECONOCIDA: "Estructura no reconocida",
  CAMPO_NO_ENCONTRADO: "Campo no encontrado",
  CONTENIDO_AMBIGUO: "Contenido ambiguo",
  ARCHIVO_PROTEGIDO: "Archivo protegido",
};

const CURRICULAR_BLOCKS: Array<{
  id:
    | "resultados_aprendizaje"
    | "conocimientos_saber"
    | "conocimientos_proceso"
    | "criterios_evaluacion";
  label: string;
}> = [
  { id: "resultados_aprendizaje", label: "Resultados de aprendizaje" },
  { id: "conocimientos_saber", label: "Conocimientos de saber" },
  { id: "conocimientos_proceso", label: "Conocimientos de proceso" },
  { id: "criterios_evaluacion", label: "Criterios de evaluacion" },
];

function getErrorMessage(error: unknown): string {
  if (error instanceof ProgramaExtractionError) {
    return error.detail;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "No fue posible ejecutar la extraccion del PDF.";
}

function getActionLabel(legibility: PdfLegibilityStatus | null): string {
  if (legibility === "NO_LEGIBLE") {
    return "Generar fallback manual";
  }

  return "Extraer campos del programa";
}

function StatusPill({
  status,
}: Readonly<{ status: FieldTraceStatus }>): React.JSX.Element {
  const copy = STATUS_COPY[status];

  return (
    <span
      className={cn(
        "inline-flex min-h-7 items-center rounded-full border px-2.5 py-1 text-xs font-semibold",
        copy.tone,
      )}
    >
      {copy.label}
    </span>
  );
}

function FieldCard({
  field,
  label,
}: Readonly<{
  field: ProgramaExtractedField;
  label: string;
}>): React.JSX.Element {
  return (
    <article className="rounded-lg border border-[color:var(--card-border)] bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-sm font-semibold text-[var(--foreground)]">
          {label}
        </h4>
        <StatusPill status={field.estado} />
      </div>

      <p className="mt-3 min-h-6 text-sm leading-6 break-words text-[var(--foreground)]">
        {field.valor ?? "Sin valor extraido"}
      </p>

      <dl className="mt-3 grid gap-2 text-xs leading-5 text-[var(--muted)]">
        <div>
          <dt className="font-semibold text-[var(--foreground)]">Revision</dt>
          <dd>
            {field.requiere_revision
              ? "Requiere confirmacion humana"
              : "Sin revision pendiente"}
          </dd>
        </div>
        <div>
          <dt className="font-semibold text-[var(--foreground)]">Borrador</dt>
          <dd>
            {field.aplicado_al_borrador
              ? "Prefill aplicado"
              : "Valor manual preservado"}
          </dd>
        </div>
        {field.motivo !== null ? (
          <div>
            <dt className="font-semibold text-[var(--foreground)]">Motivo</dt>
            <dd>{REASON_COPY[field.motivo] ?? field.motivo}</dd>
          </div>
        ) : null}
      </dl>
    </article>
  );
}

function BlockPreview({
  block,
  label,
}: Readonly<{
  block: ProgramaExtractedListBlock;
  label: string;
}>): React.JSX.Element {
  const visibleItems = block.items.slice(0, 3);

  return (
    <article className="rounded-lg border border-[color:var(--card-border)] bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-sm font-semibold text-[var(--foreground)]">
          {label}
        </h4>
        <StatusPill status={block.estado} />
      </div>

      {visibleItems.length > 0 ? (
        <ul className="mt-3 grid gap-2 text-sm leading-6 text-[var(--foreground)]">
          {visibleItems.map((item) => (
            <li
              key={`${label}-${item.valor.substring(0, 20)}`}
              className="rounded-lg bg-[var(--paper-strong)] px-3 py-2"
            >
              {item.valor}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
          Sin elementos identificados.
        </p>
      )}

      <p className="mt-3 text-xs leading-5 text-[var(--muted)]">
        {block.total_items} elemento(s) identificado(s).{" "}
        {block.requiere_revision
          ? "Requiere revision humana."
          : "Sin revision pendiente."}
      </p>
      {block.items.length > visibleItems.length ? (
        <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
          Preview reducido: {visibleItems.length} visibles,{" "}
          {block.items.length - visibleItems.length} omitidos.
        </p>
      ) : null}
      {block.bloque_parcial ? (
        <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
          Bloque parcial o pendiente de contraste con el documento fuente.
        </p>
      ) : null}
      {block.motivo !== null ? (
        <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
          Motivo: {REASON_COPY[block.motivo] ?? block.motivo}
        </p>
      ) : null}
    </article>
  );
}

export function ProgramaCurricularExtractionPreview({
  extraction,
}: Readonly<{
  extraction: ProgramaExtractionResult | null;
}>): React.JSX.Element {
  if (extraction === null) {
    return (
      <div className="rounded-lg bg-[var(--paper-strong)] px-4 py-4 text-sm leading-6 text-[var(--muted)]">
        Sin extraccion curricular preliminar asociada al borrador.
      </div>
    );
  }

  const { estructura_curricular } = extraction;

  return (
    <div className="grid gap-4">
      <div className="flex items-start gap-3 rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] p-4">
        <ClipboardCheck className="mt-0.5 h-5 w-5 shrink-0 text-[var(--accent-strong)]" />
        <div>
          <p className="text-sm font-semibold text-[var(--foreground)]">
            Base curricular preliminar ({estructura_curricular.total_competencias} competencias)
          </p>
          <p className="mt-1 text-sm leading-6 text-[var(--muted)]">
            Vista de lectura para TASK-07. La gestion completa queda reservada
            para las tareas curriculares posteriores.
          </p>
        </div>
      </div>

      <div className="grid gap-6">
        {estructura_curricular.competencias.map((comp, idx) => (
          <div key={`${comp.codigo.valor}-${idx}`} className="rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] p-4">
            <div className="mb-4">
              <h3 className="text-base font-bold text-[var(--foreground)]">
                {comp.codigo.valor} - {comp.denominacion.valor}
              </h3>
            </div>
            <div className="grid gap-3 xl:grid-cols-2">
              {CURRICULAR_BLOCKS.map((block) => (
                <BlockPreview
                  key={block.id}
                  block={comp[block.id]}
                  label={block.label}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ProgramaExtractionPanel({
  currentResult,
  hasPdf,
  legibility,
  onExtracted,
  referenciaId,
}: Readonly<{
  currentResult: ProgramaExtractionResult | null;
  hasPdf: boolean;
  legibility: PdfLegibilityStatus | null;
  onExtracted: (result: ProgramaExtractionResult) => void;
  referenciaId: string;
}>): React.JSX.Element {
  const [state, setState] = useState<ExtractionState>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const actionLabel = getActionLabel(legibility);
  const canExtract = hasPdf && state !== "extracting";

  const summary = useMemo(() => {
    if (currentResult === null) {
      return null;
    }

    const extractedCompetencias = currentResult.estructura_curricular.total_competencias;

    return {
      extractedCompetencias
    };
  }, [currentResult]);

  const handleExtract = async (): Promise<void> => {
    if (!hasPdf) {
      const validationMessage =
        "Carga y diagnostica el PDF del programa antes de extraer campos.";
      setState("error");
      setMessage(validationMessage);
      notify.warning("PDF requerido", {
        description: validationMessage,
      });
      return;
    }

    setState("extracting");
    setMessage(null);

    try {
      const result = await extractProgramaPdf(referenciaId);
      onExtracted(result);
      setState("success");
      setMessage("Resultado de extraccion asociado al borrador actual.");
      notify.success("Extraccion registrada", {
        description:
          "Los campos identificados quedaron listos para revision humana.",
      });
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      setState("error");
      setMessage(errorMessage);
      notify.error("No fue posible extraer el programa", {
        description: errorMessage,
      });
    }
  };

  return (
    <section className="grid gap-4 rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className="inline-flex h-11 w-11 items-center justify-center rounded-lg bg-white text-[var(--accent-strong)]">
            <ScanSearch className="h-5 w-5" />
          </span>
          <div>
            <p className="text-sm font-semibold text-[var(--foreground)]">
              Extraccion hibrida del programa
            </p>
            <p className="mt-1 text-sm leading-6 text-[var(--muted)]">
              Intenta prellenar campos, conserva faltantes y exige revision
              humana antes de validar el programa.
            </p>
          </div>
        </div>

        <button
          type="button"
          disabled={!canExtract}
          onClick={() => void handleExtract()}
          className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
        >
          {state === "extracting" ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <ScanSearch className="h-4 w-4" />
          )}
          {actionLabel}
        </button>
      </div>

      {!hasPdf ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-950">
          No hay PDF asociado a este borrador. La extraccion se habilita despues
          del cargue documental.
        </div>
      ) : null}

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
        <div className="grid gap-4">
          <div className="rounded-lg border border-[color:var(--card-border)] bg-white p-4">
            <p className="text-xs font-semibold tracking-[0.16em] text-[var(--muted)] uppercase">
              Resultado persistido
            </p>
            <p className="mt-2 text-sm leading-6 text-[var(--foreground)]">
              {currentResult.resumen}
            </p>
            {summary !== null ? (
              <p className="mt-2 text-xs leading-5 text-[var(--muted)]">
                {summary.extractedCompetencias} competencias con
                datos preliminares. Revision humana:{" "}
                {currentResult.requiere_revision_humana ? "requerida" : "no"}.
              </p>
            ) : null}
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <FieldCard
              field={currentResult.programa.codigo_programa}
              label="Codigo del programa"
            />
            <FieldCard
              field={currentResult.programa.nombre_programa}
              label="Nombre del programa"
            />
          </div>

          <ProgramaCurricularExtractionPreview extraction={currentResult} />
        </div>
      ) : null}
    </section>
  );
}
