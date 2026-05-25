"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BookOpenCheck,
  CheckCircle2,
  ClipboardCheck,
  Edit3,
  FileSpreadsheet,
  FileText,
  Layers3,
  ListChecks,
  NotebookText,
  RefreshCcw,
  ShieldCheck,
} from "lucide-react";

import {
  cerrarPrograma,
  ProgramaCierreError,
  validarCompletitudPrograma,
} from "@/features/programa/programa-cierre-api";
import { ProgramaPendientesConciliacion } from "@/features/programa/components/programa-pendientes-conciliacion";
import type {
  ProgramaCierreResponse,
  ProgramaCompetencia,
  ProgramaCompletitudFaltante,
  ProgramaCompletitudResponse,
  ProgramaExcelImportState,
  ProgramaPdfUploadResult,
  ProgramaWizardStepId,
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

function sortByOrder<T extends { orden: number | null }>(items: T[]): T[] {
  return [...items].sort((left, right) => {
    const leftOrder = left.orden ?? Number.MAX_SAFE_INTEGER;
    const rightOrder = right.orden ?? Number.MAX_SAFE_INTEGER;
    return leftOrder - rightOrder;
  });
}

export function ProgramaConsolidadoRevision(
  props: Readonly<{
    codigoPrograma: string;
    nombrePrograma: string;
    versionPrograma: string;
    referenciaId?: string;
    estadoBorrador?: "BORRADOR" | "EN_REVISION" | "COMPLETO" | "BLOQUEADO";
    competencias: ProgramaCompetencia[];
    pdfResult: ProgramaPdfUploadResult | null;
    excelResult: ProgramaExcelImportState | null;
    onNavigateToStep: (stepId: ProgramaWizardStepId) => void;
    onProgramaCerrado?: (result: ProgramaCierreResponse) => void;
    onSyncNeeded?: () => void;
  }>,
): React.JSX.Element {
  const {
    codigoPrograma,
    nombrePrograma,
    versionPrograma,
    referenciaId = "",
    estadoBorrador = "BORRADOR",
    competencias,
    pdfResult,
    excelResult,
    onNavigateToStep,
    onProgramaCerrado = () => {},
    onSyncNeeded,
  } = props;
  const [validation, setValidation] =
    useState<ProgramaCompletitudResponse | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const [closeMessage, setCloseMessage] = useState<string | null>(null);
  const [isRevisionModalOpen, setIsRevisionModalOpen] = useState(false);

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
  const isCompleted =
    estadoBorrador === "COMPLETO" || validation?.estado_actual === "COMPLETO";

  const runValidation = useCallback(async (): Promise<ProgramaCompletitudResponse | null> => {
    setIsValidating(true);
    setValidationError(null);
    setCloseMessage(null);
    try {
      const result = await validarCompletitudPrograma(referenciaId);
      setValidation(result);
      return result;
    } catch (error) {
      const message =
        error instanceof ProgramaCierreError
          ? error.detail
          : "No fue posible validar la completitud del programa de formación.";
      setValidationError(message);
      return null;
    } finally {
      setIsValidating(false);
    }
  }, [referenciaId]);

  useEffect(() => {
    if (referenciaId) {
      void runValidation();
    }
  }, [referenciaId, competencias, runValidation]);


  const handleCloseProgram = useCallback(async (): Promise<void> => {
    const currentValidation = validation?.cerrable
      ? validation
      : await runValidation();
    if (currentValidation === null || !currentValidation.cerrable) {
      return;
    }
    const confirmed = window.confirm(
      "Confirma que revisaste el consolidado y quieres cerrar el programa de formación como COMPLETO.",
    );
    if (!confirmed) {
      return;
    }

    setIsClosing(true);
    setValidationError(null);
    setCloseMessage(null);
    try {
      const result = await cerrarPrograma(referenciaId);
      setValidation(result.completitud);
      setCloseMessage(result.mensaje);
      onProgramaCerrado(result);
    } catch (error) {
      if (error instanceof ProgramaCierreError) {
        setValidationError(error.detail);
        if (error.completitud !== null) {
          setValidation(error.completitud);
        }
      } else {
        setValidationError("No fue posible cerrar el programa de formación.");
      }
    } finally {
      setIsClosing(false);
    }
  }, [onProgramaCerrado, referenciaId, runValidation, validation]);

  return (
    <div className="grid gap-6">
      <CompletionPanel
        closeMessage={closeMessage}
        estadoBorrador={estadoBorrador}
        isClosing={isClosing}
        isCompleted={isCompleted}
        isValidating={isValidating}
        onCloseProgram={() => void handleCloseProgram()}
        onNavigateToStep={onNavigateToStep}
        onValidate={() => void runValidation()}
        validation={validation}
        validationError={validationError}
      />

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

      {referenciaId ? (
        <ProgramaPendientesConciliacion
          competencias={competencias}
          referenciaId={referenciaId}
          onAssignedCompleted={onSyncNeeded}
        />
      ) : null}

      {/* Programa data section */}
      <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h3 className="text-base font-semibold text-[var(--foreground)]">
              Datos del programa de formación
            </h3>
            <p className="mt-1 text-sm leading-6 text-[var(--muted)]">
              Fuente del programa de formación: Excel canonico. El PDF se conserva como
              evidencia documental en MinIO.
            </p>
          </div>
          <button
            type="button"
            onClick={() => onNavigateToStep("origen-documental")}
            className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-1.5 text-xs font-semibold text-[var(--foreground)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            <Edit3 className="h-4 w-4" />
            Revisar origen
          </button>
        </div>

        <dl className="mt-4 grid gap-3 sm:grid-cols-3">
          <ProgramaField label="Codigo" value={codigoPrograma} />
          <ProgramaField label="Nombre" value={nombrePrograma} />
          <ProgramaField label="Version" value={versionPrograma || "Sin version"} />
        </dl>

        <div className="mt-4 flex flex-wrap gap-2">
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
        </div>

        {competencias.length === 0 ? (
          <div className="mt-4 rounded-lg border border-dashed border-[color:var(--card-border)] bg-[var(--paper-strong)] px-4 py-6 text-center">
            <p className="text-sm font-semibold text-[var(--foreground)]">
              Sin estructura curricular
            </p>
            <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-[var(--muted)]">
              La estructura curricular debe tener al menos una competencia con
              resultados, conocimientos y criterios para poder cerrar el
              programa de formación.
            </p>
          </div>
        ) : (
          <div className="mt-4 rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] px-4 py-6 text-center">
            <p className="text-sm font-semibold text-[var(--foreground)]">
              Estructura curricular cargada
            </p>
            <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-[var(--muted)]">
              Hay {competencias.length} competencia(s) importada(s) con resultados de aprendizaje, criterios de evaluación y conocimientos.
            </p>
            <div className="mt-4 flex justify-center">
              <button
                type="button"
                id="btn-revisar-estructura"
                onClick={() => setIsRevisionModalOpen(true)}
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
              >
                <Layers3 className="h-4 w-4" />
                Revisar estructura
              </button>
            </div>
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
                PDF del programa de formación
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
                  Estado del almacenamiento:{" "}
                  <span className="font-semibold text-[var(--foreground)]">
                    {pdfResult!.diagnostico.almacenamiento_exitoso
                      ? "Exitoso"
                      : "Fallido"}
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

      {isRevisionModalOpen && (
        <CurriculumRevisionModal
          competencias={competencias}
          onClose={() => setIsRevisionModalOpen(false)}
        />
      )}
    </div>
  );
}

function CompletionPanel({
  closeMessage,
  estadoBorrador,
  isClosing,
  isCompleted,
  isValidating,
  onCloseProgram,
  onNavigateToStep,
  onValidate,
  validation,
  validationError,
}: Readonly<{
  closeMessage: string | null;
  estadoBorrador: "BORRADOR" | "EN_REVISION" | "COMPLETO" | "BLOQUEADO";
  isClosing: boolean;
  isCompleted: boolean;
  isValidating: boolean;
  onCloseProgram: () => void;
  onNavigateToStep: (stepId: ProgramaWizardStepId) => void;
  onValidate: () => void;
  validation: ProgramaCompletitudResponse | null;
  validationError: string | null;
}>): React.JSX.Element {
  const canClose = validation?.cerrable === true && !isCompleted;
  const pendingCount = validation?.faltantes?.length ?? 0;

  return (
    <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-2xl">
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex h-9 w-9 items-center justify-center rounded-lg ${
                isCompleted
                  ? "bg-emerald-50 text-emerald-700"
                  : validation?.cerrable
                    ? "bg-[var(--accent-soft)] text-[var(--accent-strong)]"
                    : "bg-amber-50 text-amber-700"
              }`}
            >
              {isCompleted ? (
                <ShieldCheck className="h-5 w-5" />
              ) : validation?.cerrable ? (
                <CheckCircle2 className="h-5 w-5" />
              ) : (
                <AlertTriangle className="h-5 w-5" />
              )}
            </span>
            <div>
              <h3 className="text-base font-semibold text-[var(--foreground)]">
                Validacion y cierre del programa de formación
              </h3>
              <p className="mt-1 text-sm leading-6 text-[var(--muted)]">
                Estado actual:{" "}
                <span className="font-semibold text-[var(--foreground)]">
                  {isCompleted ? "COMPLETO" : estadoBorrador}
                </span>
              </p>
            </div>
          </div>

          {validation === null && !isCompleted ? (
            <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
              Ejecuta la validacion para confirmar si el programa cumple codigo,
              nombre y estructura curricular minima del programa de formación.
            </p>
          ) : null}
          {validation?.cerrable === true && !isCompleted ? (
            <p className="mt-3 text-sm leading-6 text-emerald-800">
              El programa de formación esta listo para cierre. La accion requiere confirmacion
              explicita.
            </p>
          ) : null}
          {isCompleted ? (
            <p className="mt-3 text-sm leading-6 text-emerald-800">
              {closeMessage ?? "El programa de formación quedo cerrado como COMPLETO."}
            </p>
          ) : null}
          {validationError !== null ? (
            <p role="alert" className="mt-3 text-sm leading-6 text-rose-800">
              {validationError}
            </p>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onValidate}
            disabled={isValidating || isClosing || isCompleted}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm font-semibold text-[var(--foreground)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCcw className={`h-4 w-4 ${isValidating ? "animate-spin" : ""}`} />
            Validar completitud
          </button>
          <button
            type="button"
            onClick={onCloseProgram}
            disabled={!canClose || isClosing}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <ShieldCheck className="h-4 w-4" />
            Confirmar y cerrar programa
          </button>
        </div>
      </div>

      {validation !== null ? (
        <div className="mt-4 grid gap-3">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
            <CompletionMetric label="Competencias" value={validation.resumen.competencias} />
            <CompletionMetric label="Resultados" value={validation.resumen.resultados} />
            <CompletionMetric label="Saber" value={validation.resumen.conocimientos_saber} />
            <CompletionMetric label="Proceso" value={validation.resumen.conocimientos_proceso} />
            <CompletionMetric label="Criterios" value={validation.resumen.criterios} />
          </div>

          {!validation.cerrable ? (
            <MissingList
              faltantes={validation.faltantes ?? []}
              pendingCount={pendingCount}
              onNavigateToStep={onNavigateToStep}
            />
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function CompletionMetric({
  label,
  value,
}: Readonly<{ label: string; value: number }>): React.JSX.Element {
  return (
    <div className="rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] px-3 py-2">
      <p className="text-xs leading-5 text-[var(--muted)]">{label}</p>
      <p className="mt-1 text-sm font-semibold text-[var(--foreground)]">{value}</p>
    </div>
  );
}

function MissingList({
  faltantes,
  pendingCount,
  onNavigateToStep,
}: Readonly<{
  faltantes: ProgramaCompletitudFaltante[];
  pendingCount: number;
  onNavigateToStep: (stepId: ProgramaWizardStepId) => void;
}>): React.JSX.Element {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50/60 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm font-semibold text-amber-900">
          Faltantes para cierre: {pendingCount}
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onNavigateToStep("origen-documental")}
            className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-amber-900 transition hover:text-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            <Edit3 className="h-4 w-4" />
            Revisar origen
          </button>
        </div>
      </div>
      <ul className="mt-3 grid gap-2">
        {faltantes.map((item) => (
          <li
            key={`${item.codigo}-${item.competencia_id ?? "programa"}`}
            className="rounded-lg bg-white px-3 py-2 text-sm leading-6 text-amber-950"
          >
            <span className="font-semibold">
              {item.competencia_codigo ?? "Programa"}
            </span>
            : {item.mensaje}
          </li>
        ))}
      </ul>
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
          Resumen del programa de formación
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

function CurriculumRevisionModal({
  competencias,
  onClose,
}: Readonly<{
  competencias: ProgramaCompetencia[];
  onClose: () => void;
}>): React.JSX.Element | null {
  const [selectedId, setSelectedId] = useState<string>(competencias[0]?.id ?? "");

  const competencia = useMemo(() => {
    return competencias.find((c) => c.id === selectedId) ?? competencias[0] ?? null;
  }, [competencias, selectedId]);

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
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--line)] px-5 py-4">
          <div className="flex-1 min-w-[240px]">
            <label
              htmlFor="modal-competencia-select"
              className="block text-xs font-semibold tracking-[0.16em] text-[var(--accent-strong)] uppercase mb-1"
            >
              Seleccione la competencia a revisar
            </label>
            <select
              id="modal-competencia-select"
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm text-[var(--foreground)] shadow-sm focus:border-[var(--accent)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
            >
              {competencias.map((comp) => (
                <option key={comp.id} value={comp.id}>
                  {comp.codigo_competencia} - {comp.nombre_competencia.substring(0, 80)}
                  {comp.nombre_competencia.length > 80 ? "..." : ""}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            aria-label="Cerrar modal de revisión curricular"
            onClick={onClose}
            className="inline-flex min-h-10 w-10 items-center justify-center rounded-lg border border-[color:var(--card-border)] bg-white text-[var(--foreground)] transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            <span className="text-xl font-medium">&times;</span>
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-5 bg-[var(--paper-strong)]">
          <CompetenciaReviewCard competencia={competencia} />
        </div>
      </section>
    </div>
  );
}
