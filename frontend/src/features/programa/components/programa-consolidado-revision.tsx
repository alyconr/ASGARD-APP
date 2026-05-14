"use client";

import { useMemo } from "react";
import {
  BookOpenCheck,
  CheckCircle2,
  ClipboardCheck,
  Edit3,
  FileSpreadsheet,
  FileText,
  Layers3,
  ListChecks,
  NotebookText,
} from "lucide-react";

import type {
  CriterioEvaluacionCurricular,
  ConocimientoCurricular,
  ProgramaCompetencia,
  ProgramaEntryMode,
  ProgramaExcelImportState,
  ProgramaPdfUploadResult,
  ProgramaWizardStepId,
  ResultadoAprendizaje,
} from "@/features/programa/types";

type FieldOrigin = "MANUAL" | "EXTRAIDO" | "CORREGIDO" | "PENDIENTE" | "VALIDADO";

const ORIGIN_COPY: Record<FieldOrigin, string> = {
  MANUAL: "Manual",
  EXTRAIDO: "Extraido",
  CORREGIDO: "Corregido",
  PENDIENTE: "Pendiente",
  VALIDADO: "Validado",
};

const ORIGIN_SOFT: Record<FieldOrigin, string> = {
  MANUAL: "bg-white",
  EXTRAIDO: "bg-blue-50 text-blue-800",
  CORREGIDO: "bg-amber-50 text-amber-800",
  PENDIENTE: "bg-rose-50 text-rose-800",
  VALIDADO: "bg-emerald-50 text-emerald-800",
};

function ProgramaOriginBadge({
  origin,
}: Readonly<{ origin: FieldOrigin }>): React.JSX.Element {
  return (
    <span
      className={`inline-flex min-h-6 items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${ORIGIN_SOFT[origin] ?? "bg-white text-[var(--muted)]"}`}
    >
      {ORIGIN_COPY[origin] ?? origin}
    </span>
  );
}

type EntrySource = Exclude<ProgramaEntryMode, null>;

const ENTRY_SOURCE_COPY: Record<EntrySource, string> = {
  MANUAL: "Captura manual",
  PDF: "PDF (evidencia)",
  EXCEL: "Excel canonico",
};

const ENTRY_SOURCE_ICON: Record<EntrySource, React.ComponentType<{ className?: string }>> = {
  MANUAL: NotebookText,
  PDF: FileText,
  EXCEL: FileSpreadsheet,
};

function sortByOrder<T extends { orden: number | null }>(items: T[]): T[] {
  return [...items].sort((left, right) => {
    const leftOrder = left.orden ?? Number.MAX_SAFE_INTEGER;
    const rightOrder = right.orden ?? Number.MAX_SAFE_INTEGER;
    return leftOrder - rightOrder;
  });
}

export function ProgramaConsolidadoRevision({
  codigoPrograma,
  nombrePrograma,
  versionPrograma,
  entryMode,
  competencias,
  pdfResult,
  excelResult,
  onNavigateToStep,
}: Readonly<{
  codigoPrograma: string;
  nombrePrograma: string;
  versionPrograma: string;
  entryMode: ProgramaEntryMode;
  competencias: ProgramaCompetencia[];
  pdfResult: ProgramaPdfUploadResult | null;
  excelResult: ProgramaExcelImportState | null;
  onNavigateToStep: (stepId: ProgramaWizardStepId) => void;
}>): React.JSX.Element {
  const source = (entryMode ?? null) as EntrySource | null;

  const totalResultados = useMemo(
    () => competencias.reduce((sum, c) => sum + (c.resultados?.length ?? 0), 0),
    [competencias],
  );
  const totalSaber = useMemo(
    () =>
      competencias.reduce(
        (sum, c) =>
          sum +
          (c.conocimientos?.filter((k) => k.tipo === "SABER").length ?? 0),
        0,
      ),
    [competencias],
  );
  const totalProceso = useMemo(
    () =>
      competencias.reduce(
        (sum, c) =>
          sum +
          (c.conocimientos?.filter((k) => k.tipo === "PROCESO").length ?? 0),
        0,
      ),
    [competencias],
  );
  const totalCriterios = useMemo(
    () => competencias.reduce((sum, c) => sum + (c.criterios?.length ?? 0), 0),
    [competencias],
  );

  const hasPdf = pdfResult?.documento !== null && pdfResult?.documento !== undefined;
  const hasExcel =
    excelResult?.documento !== null && excelResult?.documento !== undefined;
  const hasCurricular = competencias.length > 0;
  const hasPrograma = codigoPrograma.trim().length > 0 || nombrePrograma.trim().length > 0;

  return (
    <div className="grid gap-6">
      <SummaryBanner
        totalResultados={totalResultados}
        totalSaber={totalSaber}
        totalProceso={totalProceso}
        totalCriterios={totalCriterios}
        totalCompetencias={competencias.length}
        hasPrograma={hasPrograma}
        hasPdf={hasPdf}
        hasExcel={hasExcel}
        hasCurricular={hasCurricular}
      />

      {/* Programa data section */}
      <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h3 className="text-base font-semibold text-[var(--foreground)]">
              Datos del programa
            </h3>
            <p className="mt-1 text-sm leading-6 text-[var(--muted)]">
              {source !== null
                ? `Fuente: ${ENTRY_SOURCE_COPY[source]}`
                : "Sin fuente documental definida"}
            </p>
          </div>
          <button
            type="button"
            onClick={() => onNavigateToStep("datos-programa")}
            className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-1.5 text-xs font-semibold text-[var(--foreground)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            <Edit3 className="h-4 w-4" />
            Editar datos
          </button>
        </div>

        <dl className="mt-4 grid gap-3 sm:grid-cols-3">
          <ProgramaField label="Codigo" value={codigoPrograma} />
          <ProgramaField label="Nombre" value={nombrePrograma} />
          <ProgramaField label="Version" value={versionPrograma || "Sin version"} />
        </dl>

        <div className="mt-4 flex flex-wrap gap-2">
          {source !== null ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--accent-strong)]">
              {(() => {
                const Icon = ENTRY_SOURCE_ICON[source];
                return <Icon className="h-3.5 w-3.5" />;
              })()}
              {ENTRY_SOURCE_COPY[source]}
            </span>
          ) : null}
          {hasPdf ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800">
              <FileText className="h-3.5 w-3.5" />
              PDF en MinIO
            </span>
          ) : null}
          {hasExcel ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800">
              <FileSpreadsheet className="h-3.5 w-3.5" />
              Excel importado
            </span>
          ) : null}
        </div>
      </section>

      {/* Curricular section */}
      <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h3 className="text-base font-semibold text-[var(--foreground)]">
              Estructura curricular
            </h3>
            <p className="mt-1 text-sm leading-6 text-[var(--muted)]">
              {competencias.length} competencia(s)
            </p>
          </div>
          <button
            type="button"
            onClick={() => onNavigateToStep("estructura-curricular")}
            className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-1.5 text-xs font-semibold text-[var(--foreground)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            <Edit3 className="h-4 w-4" />
            Editar estructura
          </button>
        </div>

        {competencias.length === 0 ? (
          <div className="mt-4 rounded-lg border border-dashed border-[color:var(--card-border)] bg-[var(--paper-strong)] px-4 py-6 text-center">
            <p className="text-sm font-semibold text-[var(--foreground)]">
              Sin estructura curricular
            </p>
            <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-[var(--muted)]">
              La estructura curricular debe tener al menos una competencia con
              resultados, conocimientos y criterios para poder cerrar el
              programa.
            </p>
          </div>
        ) : (
          <div className="mt-4 grid gap-3">
            {competencias.map((competencia) => (
              <CompetenciaReviewCard
                key={competencia.id}
                competencia={competencia}
              />
            ))}
          </div>
        )}
      </section>

      {/* Document evidence summary */}
      <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-5">
        <h3 className="text-base font-semibold text-[var(--foreground)]">
          Evidencia documental
        </h3>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div
            className={`rounded-lg border px-4 py-3 ${
              hasPdf
                ? "border-[color:var(--card-border)] bg-[var(--paper-strong)]"
                : "border-dashed border-[color:var(--card-border)] bg-white/50"
            }`}
          >
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-[var(--muted)]" />
              <p className="text-sm font-semibold text-[var(--foreground)]">
                PDF del programa
              </p>
            </div>
            {hasPdf ? (
              <div className="mt-2 grid gap-1 text-xs text-[var(--muted)]">
                <p>
                  Archivo:{" "}
                  <span className="font-semibold text-[var(--foreground)]">
                    {pdfResult!.documento.original_filename}
                  </span>
                </p>
                <p>
                  Estado:{" "}
                  <span className="font-semibold text-[var(--foreground)]">
                    {pdfResult!.diagnostico.estado_legibilidad}
                  </span>
                </p>
              </div>
            ) : (
              <p className="mt-2 text-xs text-[var(--muted)]">
                Sin PDF cargado como evidencia.
              </p>
            )}
          </div>

          <div
            className={`rounded-lg border px-4 py-3 ${
              hasExcel
                ? "border-[color:var(--card-border)] bg-[var(--paper-strong)]"
                : "border-dashed border-[color:var(--card-border)] bg-white/50"
            }`}
          >
            <div className="flex items-center gap-2">
              <FileSpreadsheet className="h-4 w-4 text-[var(--muted)]" />
              <p className="text-sm font-semibold text-[var(--foreground)]">
                Excel canonico
              </p>
            </div>
            {hasExcel ? (
              <div className="mt-2 grid gap-1 text-xs text-[var(--muted)]">
                <p>
                  Archivo:{" "}
                  <span className="font-semibold text-[var(--foreground)]">
                    {excelResult!.documento!.original_filename}
                  </span>
                </p>
                <p>
                  Importacion:{" "}
                  <span className="font-semibold text-[var(--foreground)]">
                    {excelResult!.confirmacion.estado}
                  </span>
                </p>
              </div>
            ) : (
              <p className="mt-2 text-xs text-[var(--muted)]">
                Sin Excel canonico cargado.
              </p>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

function SummaryBanner({
  totalResultados,
  totalSaber,
  totalProceso,
  totalCriterios,
  totalCompetencias,
  hasPrograma,
  hasPdf,
  hasExcel,
  hasCurricular,
}: Readonly<{
  totalResultados: number;
  totalSaber: number;
  totalProceso: number;
  totalCriterios: number;
  totalCompetencias: number;
  hasPrograma: boolean;
  hasPdf: boolean;
  hasExcel: boolean;
  hasCurricular: boolean;
}>): React.JSX.Element {
  const items: { label: string; value: string | number; ready: boolean }[] = [
    { label: "Datos base", value: hasPrograma ? "Ok" : "Pendiente", ready: hasPrograma },
    { label: "PDF evidencia", value: hasPdf ? "Ok" : "Sin carga", ready: hasPdf },
    { label: "Excel canonico", value: hasExcel ? "Ok" : "Sin carga", ready: hasExcel },
    { label: "Competencias", value: totalCompetencias, ready: hasCurricular },
    { label: "Resultados", value: totalResultados, ready: totalResultados > 0 },
    { label: "Saber", value: totalSaber, ready: totalSaber > 0 },
    { label: "Proceso", value: totalProceso, ready: totalProceso > 0 },
    { label: "Criterios", value: totalCriterios, ready: totalCriterios > 0 },
  ];

  return (
    <section className="rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] p-4">
      <div className="flex items-center gap-2">
        <BookOpenCheck className="h-5 w-5 text-[var(--accent-strong)]" />
        <h3 className="text-sm font-semibold text-[var(--foreground)]">
          Resumen del programa
        </h3>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {items.map((item) => (
          <div
            key={item.label}
            className={`rounded-lg border px-3 py-2 ${
              item.ready
                ? "border-[color:var(--card-border)] bg-white"
                : "border-dashed border-amber-200 bg-amber-50/50"
            }`}
          >
            <p className="text-xs leading-5 text-[var(--muted)]">{item.label}</p>
            <div className="mt-1 flex items-center gap-1.5">
              <span
                className={`text-sm font-semibold ${
                  item.ready ? "text-[var(--foreground)]" : "text-amber-700"
                }`}
              >
                {item.value}
              </span>
              {item.ready ? (
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function ProgramaField({
  label,
  value,
}: Readonly<{ label: string; value: string }>): React.JSX.Element {
  const isEmpty = value.trim().length === 0;

  return (
    <div className="rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] px-3 py-2">
      <dt className="text-xs text-[var(--muted)]">{label}</dt>
      <dd
        className={`mt-0.5 text-sm font-semibold ${
          isEmpty ? "italic text-[var(--muted)]" : "text-[var(--foreground)]"
        }`}
      >
        {isEmpty ? "Pendiente" : value}
      </dd>
    </div>
  );
}

function CompetenciaReviewCard({
  competencia,
}: Readonly<{ competencia: ProgramaCompetencia }>): React.JSX.Element {
  const resultados = sortByOrder(competencia.resultados ?? []);
  const saberes = sortByOrder(
    (competencia.conocimientos ?? []).filter((k) => k.tipo === "SABER"),
  );
  const procesos = sortByOrder(
    (competencia.conocimientos ?? []).filter((k) => k.tipo === "PROCESO"),
  );
  const criterios = sortByOrder(competencia.criterios ?? []);

  const origin = (competencia.origen_campo as FieldOrigin) ?? "MANUAL";

  return (
    <article className="rounded-lg border border-[color:var(--card-border)] bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent-strong)]">
              <Layers3 className="h-4 w-4" />
            </span>
            <span className="rounded-lg bg-[var(--accent-soft)] px-2.5 py-1 text-xs font-semibold text-[var(--accent-strong)]">
              {competencia.codigo_competencia}
            </span>
            <ProgramaOriginBadge origin={origin} />
          </div>
          <p className="mt-2 text-sm leading-6 break-words text-[var(--foreground)]">
            {competencia.nombre_competencia}
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {/* Resultados */}
        <ReviewBlock
          icon={<ListChecks className="h-4 w-4" />}
          label="Resultados"
          count={resultados.length}
          emptyLabel="Sin resultados"
        >
          {resultados.map((item) => (
            <ReviewItem
              key={item.id}
              text={item.descripcion}
              origin={item.estado as FieldOrigin}
            />
          ))}
        </ReviewBlock>

        {/* Criterios */}
        <ReviewBlock
          icon={<ClipboardCheck className="h-4 w-4" />}
          label="Criterios"
          count={criterios.length}
          emptyLabel="Sin criterios"
        >
          {criterios.map((item) => (
            <ReviewItem
              key={item.id}
              text={item.descripcion}
              origin={item.estado as FieldOrigin}
            />
          ))}
        </ReviewBlock>

        {/* Saber */}
        <ReviewBlock
          icon={<BookOpenCheck className="h-4 w-4" />}
          label="Saber"
          count={saberes.length}
          emptyLabel="Sin conocimientos SABER"
        >
          {saberes.map((item) => (
            <ReviewItem
              key={item.id}
              text={item.descripcion}
              origin={item.estado as FieldOrigin}
            />
          ))}
        </ReviewBlock>

        {/* Proceso */}
        <ReviewBlock
          icon={<BookOpenCheck className="h-4 w-4" />}
          label="Proceso"
          count={procesos.length}
          emptyLabel="Sin conocimientos PROCESO"
        >
          {procesos.map((item) => (
            <ReviewItem
              key={item.id}
              text={item.descripcion}
              origin={item.estado as FieldOrigin}
            />
          ))}
        </ReviewBlock>
      </div>
    </article>
  );
}

function ReviewBlock({
  icon,
  label,
  count,
  emptyLabel,
  children,
}: Readonly<{
  icon: React.ReactNode;
  label: string;
  count: number;
  emptyLabel: string;
  children: React.ReactNode;
}>): React.JSX.Element {
  return (
    <div className="rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-[var(--foreground)]">
          {icon}
          {label}
        </div>
        <span className="text-xs font-semibold text-[var(--muted)]">{count}</span>
      </div>
      {count === 0 ? (
        <p className="mt-2 text-xs leading-5 italic text-[var(--muted)]">{emptyLabel}</p>
      ) : (
        <div className="mt-2 grid gap-1.5">{children}</div>
      )}
    </div>
  );
}

function ReviewItem({
  text,
  origin,
}: Readonly<{ text: string; origin: FieldOrigin }>): React.JSX.Element {
  return (
    <div className="flex items-start justify-between gap-2 rounded-md bg-white px-2.5 py-1.5">
      <p className="min-w-0 text-xs leading-5 break-words text-[var(--foreground)]">
        {text}
      </p>
      <ProgramaOriginBadge origin={origin} />
    </div>
  );
}
