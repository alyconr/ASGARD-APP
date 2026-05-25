"use client";

import Image from "next/image";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  BookOpenCheck,
  FileSpreadsheet,
  ListX,
  RefreshCcw,
  Route,
  Save,
  Trash2,
} from "lucide-react";

import { AutosaveIndicator } from "@/components/status/autosave-indicator";
import { WizardProgress } from "@/components/wizard/wizard-progress";
import { ProgramaConsolidadoRevision } from "@/features/programa/components/programa-consolidado-revision";
import { ProgramaDocumentUpload } from "@/features/programa/components/programa-document-upload";
import { ProgramaExcelImport } from "@/features/programa/components/programa-excel-import";
import { PROGRAMA_WIZARD_STEPS } from "@/features/programa/constants";
import { useProgramaWizard } from "@/features/programa/use-programa-wizard";
import { ProyectoDisponibilidadPanel } from "@/features/proyecto/components/proyecto-disponibilidad-panel";
import { cn } from "@/lib/utils";
import type {
  ProgramaCierreResponse,
  ProgramaCompetencia,
  ProgramaExcelImportResponse,
  ProgramaExcelImportState,
  ProgramaExcelPreviewResponse,
  ProgramaPdfUploadResponse,
  ProgramaPdfUploadResult,
  ProgramaWizardStepDefinition,
  ProgramaWizardStepId,
} from "@/features/programa/types";

const STEP_CONTENT: Record<
  ProgramaWizardStepId,
  {
    label: string;
    description: string;
    icon: React.ComponentType<{ className?: string }>;
  }
> = {
  "origen-documental": {
    label: "Origen de informacion",
    description:
      "PDF como evidencia documental y Excel canonico como fuente curricular.",
    icon: FileSpreadsheet,
  },
  "revision-programa": {
    label: "Revision del programa de formación",
    description:
      "La revision se mantiene como paso independiente antes de cualquier cierre.",
    icon: BookOpenCheck,
  },
};

function formatReferenceId(referenceId: string): string {
  if (referenceId.length < 18) {
    return referenceId;
  }

  return `${referenceId.slice(0, 8)}-${referenceId.slice(9, 13)}-${referenceId.slice(14, 18)}...`;
}

function ActionButton({
  children,
  className,
  disabled = false,
  onClick,
  tone = "primary",
  type = "button",
}: Readonly<{
  children: React.ReactNode;
  className?: string;
  disabled?: boolean;
  onClick?: () => void;
  tone?: "primary" | "secondary" | "quiet";
  type?: "button" | "submit";
}>): React.JSX.Element {
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50",
        tone === "primary" &&
          "bg-[var(--accent)] text-white hover:bg-[var(--accent-strong)]",
        tone === "secondary" &&
          "border border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent-strong)] hover:bg-white",
        tone === "quiet" &&
          "border border-[color:var(--card-border)] bg-white text-[var(--foreground)] hover:border-[var(--accent)] hover:text-[var(--accent-strong)]",
        className,
      )}
    >
      {children}
    </button>
  );
}

function ErrorBanner({
  message,
}: Readonly<{ message: string }>): React.JSX.Element {
  return (
    <section
      role="alert"
      className="flex items-start gap-3 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-900"
    >
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      <p>{message}</p>
    </section>
  );
}

type StepWorkspaceProps = {
  currentStep: ProgramaWizardStepDefinition;
  programaExcelResult: ProgramaExcelImportState | null;
  programaPdfResult: ProgramaPdfUploadResult | null;
  referenceId: string;
  estadoBorrador: ProgramaCompetencia["estado"];
  programaValue: {
    codigo_programa: string;
    nombre_programa: string;
    version_programa: string;
  };
  onProgramaExcelPreviewed: (result: ProgramaExcelPreviewResponse) => void;
  onProgramaExcelImported: (result: ProgramaExcelImportResponse) => void;
  onProgramaPdfUploaded: (result: ProgramaPdfUploadResponse) => void;
  onPersistDraftBeforeExcelPreview: () => Promise<boolean>;
  onNavigateToStep: (stepId: ProgramaWizardStepId) => void;
  onProgramaCerrado: (result: ProgramaCierreResponse) => void;
  competencias: ProgramaCompetencia[];
  onSyncNeeded?: () => void;
};

function StepWorkspace({
  currentStep,
  programaExcelResult,
  programaPdfResult,
  referenceId,
  estadoBorrador,
  programaValue,
  onProgramaExcelPreviewed,
  onProgramaExcelImported,
  onProgramaPdfUploaded,
  onPersistDraftBeforeExcelPreview,
  onNavigateToStep,
  onProgramaCerrado,
  competencias,
  onSyncNeeded,
}: StepWorkspaceProps): React.JSX.Element {
  const content = STEP_CONTENT[currentStep.id];
  const Icon = content.icon;

  return (
    <section className="rounded-lg border border-[color:var(--card-border)] bg-[var(--card)] p-5 shadow-[0_18px_42px_rgba(23,53,47,0.08)]">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-[var(--line)] pb-5">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold tracking-[0.16em] text-[var(--accent-strong)] uppercase">
            {currentStep.shortLabel} / {currentStep.label}
          </p>
          <h2 className="mt-2 text-2xl font-[family:var(--font-display)] font-semibold text-[var(--foreground)]">
            {content.label}
          </h2>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
            {content.description}
          </p>
        </div>

        <span className="inline-flex h-11 w-11 items-center justify-center rounded-lg bg-[var(--foreground)] text-white">
          <Icon className="h-5 w-5" />
        </span>
      </header>

      <div className="mt-5 min-w-0">
        <div className="min-w-0 rounded-lg border border-dashed border-[color:var(--card-border)] bg-white p-5">
          {currentStep.id === "origen-documental" ? (
            <div className="grid gap-4">
              <ProgramaDocumentUpload
                currentResult={programaPdfResult}
                referenciaId={referenceId}
                onUploaded={onProgramaPdfUploaded}
              />
              <ProgramaExcelImport
                currentResult={programaExcelResult}
                referenciaId={referenceId}
                onBeforePreview={onPersistDraftBeforeExcelPreview}
                onImported={onProgramaExcelImported}
                onPreviewed={onProgramaExcelPreviewed}
              />
            </div>
          ) : (
            <ProgramaConsolidadoRevision
              codigoPrograma={programaValue.codigo_programa}
              nombrePrograma={programaValue.nombre_programa}
              versionPrograma={programaValue.version_programa}
              competencias={competencias}
              pdfResult={programaPdfResult}
              excelResult={programaExcelResult}
              onNavigateToStep={onNavigateToStep}
              referenciaId={referenceId}
              estadoBorrador={estadoBorrador}
              onProgramaCerrado={onProgramaCerrado}
              onSyncNeeded={onSyncNeeded}
            />
          )}
        </div>
      </div>
    </section>
  );
}

function DraftSummary({
  referenceId,
  stepLabel,
}: Readonly<{
  referenceId: string | null;
  stepLabel: string;
}>): React.JSX.Element {
  return (
    <dl className="grid gap-3 rounded-lg border border-[color:var(--card-border)] bg-white p-4 text-sm">
      <div>
        <dt className="text-[var(--muted)]">Referencia</dt>
        <dd className="mt-1 font-semibold text-[var(--foreground)]">
          {referenceId === null
            ? "Sin borrador activo"
            : formatReferenceId(referenceId)}
        </dd>
      </div>
      <div>
        <dt className="text-[var(--muted)]">Fuente</dt>
        <dd className="mt-1 font-semibold text-[var(--foreground)]">
          Excel canonico
        </dd>
      </div>
      <div>
        <dt className="text-[var(--muted)]">Paso</dt>
        <dd className="mt-1 font-semibold text-[var(--foreground)]">
          {stepLabel}
        </dd>
      </div>
    </dl>
  );
}

export function ProgramaWizardShell(): React.JSX.Element {
  const controller = useProgramaWizard();
  const currentStep =
    PROGRAMA_WIZARD_STEPS[controller.currentStepIndex] ??
    PROGRAMA_WIZARD_STEPS[0];

  if (controller.isBootstrapping) {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-7xl items-center px-5 py-8">
        <section className="w-full rounded-lg border border-[color:var(--card-border)] bg-white p-8 shadow-[0_18px_42px_rgba(23,53,47,0.08)]">
          <div className="flex items-center gap-3 text-[var(--accent-strong)]">
            <RefreshCcw className="h-5 w-5 animate-spin" />
            <p className="text-sm font-semibold">
              Revisando borrador activo del programa de formación
            </p>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-5 px-5 py-6 lg:px-8">
      <header className="rounded-lg border border-[color:var(--card-border)] bg-white px-5 py-4 shadow-[0_14px_32px_rgba(23,53,47,0.07)]">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <div className="flex items-center gap-2 text-[var(--accent-strong)]">
              <Image
                src="/logo-sena.svg"
                alt="Logo SENA"
                width={24}
                height={24}
                className="shrink-0 object-contain"
              />
              <p className="text-xs font-semibold tracking-[0.18em] uppercase">
                SENA / Fase 1
              </p>
            </div>
            <h1 className="mt-2 text-3xl font-[family:var(--font-display)] font-semibold text-[var(--foreground)] lg:text-4xl">
              Wizard base del programa de formación
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
              Flujo de importacion con borrador persistente, navegacion por pasos
              y recuperacion por referencia estable. La fuente estructurada del
              programa es la matriz Excel canonica.
            </p>
          </div>

          <div className="flex flex-col items-start gap-3 lg:items-end">
            <AutosaveIndicator
              state={controller.autosave.state}
              message={controller.autosave.message}
              lastSavedAt={controller.lastSavedAt}
            />
            {controller.activeReferenceId !== null ? (
              <span className="inline-flex items-center gap-2 rounded-lg bg-[var(--paper-strong)] px-3 py-2 text-xs font-semibold text-[var(--foreground)]">
                <Save className="h-4 w-4 text-[var(--accent-strong)]" />
                {formatReferenceId(controller.activeReferenceId)}
              </span>
            ) : null}
          </div>
        </div>
      </header>

      {controller.errorMessage !== null ? (
        <ErrorBanner message={controller.errorMessage} />
      ) : null}

      {!controller.isWizardActive ? (
        <section className="grid gap-5 lg:grid-cols-[1fr_26rem]">
          <section className="rounded-lg border border-[color:var(--card-border)] bg-[var(--card)] p-5 shadow-[0_18px_42px_rgba(23,53,47,0.08)]">
            <div className="flex items-center gap-2">
              <Route className="h-5 w-5 text-[var(--accent-strong)]" />
              <h2 className="text-2xl font-[family:var(--font-display)] font-semibold text-[var(--foreground)]">
                Iniciar proceso
              </h2>
            </div>

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <button
                type="button"
                onClick={() => void controller.startNewFlow("EXCEL")}
                className="grid gap-3 rounded-lg border border-[color:var(--card-border)] bg-white p-4 text-left transition hover:border-[var(--accent)] hover:shadow-[0_12px_28px_rgba(23,53,47,0.08)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
              >
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent-strong)]">
                  <FileSpreadsheet className="h-5 w-5" />
                </span>
                <span className="text-base font-semibold text-[var(--foreground)]">
                  Excel canonico
                </span>
                <span className="text-sm leading-6 text-[var(--muted)]">
                  Workbook canonico para preview e importacion curricular
                  estructurada.
                </span>
              </button>
            </div>

            <div className="mt-5 rounded-lg border border-[color:var(--card-border)] bg-white px-4 py-3 text-sm leading-6 text-[var(--muted)]">
              El proceso inicia en estado BORRADOR y conserva el mismo
              referencia_id durante todo el wizard. La fuente estructurada del
              programa es la matriz Excel canonica.
            </div>
          </section>

          <aside className="rounded-lg border border-[color:var(--card-border)] bg-[var(--card)] p-5 shadow-[0_18px_42px_rgba(23,53,47,0.08)]">
            <h2 className="text-2xl font-[family:var(--font-display)] font-semibold text-[var(--foreground)]">
              Continuar borrador
            </h2>

            <label className="mt-4 block">
              <span className="text-xs font-semibold tracking-[0.16em] text-[var(--muted)] uppercase">
                referencia_id
              </span>
              <input
                value={controller.continueReferenceInput}
                onChange={(event) =>
                  controller.updateContinueReferenceInput(event.target.value)
                }
                placeholder="UUID del borrador"
                className="mt-2 w-full rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm text-[var(--foreground)] transition outline-none placeholder:text-[var(--muted)]/70 focus:border-[var(--accent)]"
              />
            </label>

            <ActionButton
              className="mt-3 w-full"
              disabled={controller.isRecovering}
              onClick={() =>
                void controller.recoverDraftByReference(
                  controller.continueReferenceInput,
                )
              }
            >
              <RefreshCcw className="h-4 w-4" />
              Recuperar
            </ActionButton>

            <div className="mt-5 border-t border-[var(--line)] pt-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-xs font-semibold tracking-[0.16em] text-[var(--muted)] uppercase">
                  Borradores locales
                </p>
                {controller.knownDrafts.length > 0 ? (
                  <button
                    type="button"
                    onClick={() => {
                      if (
                        window.confirm(
                          "Esto solo quitara las referencias locales de este navegador. Los borradores del servidor no se eliminan.",
                        )
                      ) {
                        controller.clearKnownDrafts();
                      }
                    }}
                    className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-1.5 text-xs font-semibold text-[var(--muted)] transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                  >
                    <ListX className="h-4 w-4" />
                    Limpiar lista
                  </button>
                ) : null}
              </div>
              {controller.knownDrafts.length > 0 ? (
                <div className="mt-3 grid gap-2">
                  {controller.knownDrafts.map((draft) => (
                    <article
                      key={draft.referenciaId}
                      className="grid gap-3 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-3 transition hover:border-[var(--accent)] sm:grid-cols-[1fr_auto]"
                    >
                      <button
                        type="button"
                        onClick={() =>
                          void controller.recoverDraftByReference(
                            draft.referenciaId,
                          )
                        }
                        className="min-w-0 text-left focus-visible:rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                      >
                        <span className="block truncate text-sm font-semibold text-[var(--foreground)]">
                          {draft.label}
                        </span>
                        <span className="mt-1 block text-xs text-[var(--muted)]">
                          {formatReferenceId(draft.referenciaId)} /{" "}
                          {draft.estado}
                        </span>
                      </button>
                      <button
                        type="button"
                        aria-label={`Quitar ${draft.label} de la lista local`}
                        title="Quitar de esta lista local"
                        onClick={() => {
                          if (
                            window.confirm(
                              "Esto solo quitara esta referencia local. El borrador del servidor no se elimina.",
                            )
                          ) {
                            controller.forgetKnownDraft(draft.referenciaId);
                          }
                        }}
                        className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-transparent px-2 py-1.5 text-xs font-semibold text-[var(--muted)] transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                      >
                        <Trash2 className="h-4 w-4" />
                        Quitar
                      </button>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
                  Sin borradores locales registrados.
                </p>
              )}
            </div>
          </aside>
        </section>
      ) : null}

      {controller.isWizardActive && controller.payload !== null ? (
        <section className="grid min-h-[calc(100vh-12rem)] gap-5 lg:grid-cols-[22rem_minmax(0,1fr)]">
          <aside className="flex flex-col gap-4 self-start lg:sticky lg:top-6 w-full h-fit">
            <section className="rounded-lg border border-[color:var(--card-border)] bg-[var(--card)] p-4 shadow-[0_18px_42px_rgba(23,53,47,0.08)]">
              <WizardProgress
                currentStepId={controller.currentStepId}
                steps={PROGRAMA_WIZARD_STEPS}
                touchedSteps={controller.payload.meta.touchedSteps}
                onSelectStep={controller.goToStep}
                disabledSteps={controller.disabledSteps}
              />
            </section>

            <DraftSummary
              referenceId={
                controller.activeReferenceId ??
                controller.payload.meta.referenciaId
              }
              stepLabel={currentStep.label}
            />

            <ActionButton tone="quiet" onClick={controller.resetFlow}>
              Volver al inicio
            </ActionButton>
          </aside>

          <div className="min-w-0 flex flex-col gap-4">
            <div className="flex-1 overflow-y-auto rounded-lg">
              <StepWorkspace
                currentStep={currentStep}
                programaExcelResult={controller.payload.documental.programa_excel}
                programaPdfResult={controller.payload.documental.programa_pdf}
                competencias={controller.payload.curricular.competencias}
                referenceId={
                  controller.activeReferenceId ??
                  controller.payload.meta.referenciaId
                }
                estadoBorrador={controller.draftStatus}
                programaValue={controller.payload.programa}
                onProgramaExcelPreviewed={controller.updateProgramaExcelPreview}
                onProgramaExcelImported={controller.updateProgramaExcelImport}
                onProgramaPdfUploaded={controller.updateProgramaPdfResult}
                onPersistDraftBeforeExcelPreview={
                  controller.persistActiveDraftNow
                }
                onNavigateToStep={controller.goToStep}
                onProgramaCerrado={controller.markProgramaClosed}
                onSyncNeeded={controller.refreshCurriculum}
              />
            </div>

            <ProyectoDisponibilidadPanel
              referenciaId={
                controller.activeReferenceId ??
                controller.payload.meta.referenciaId
              }
              programaEstado={controller.draftStatus}
              onNavigateToStep={controller.goToStep}
            />

            <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm leading-6 text-[var(--muted)]">
                  Paso {controller.currentStepIndex + 1} de{" "}
                  {PROGRAMA_WIZARD_STEPS.length}
                </p>

                <div className="flex flex-wrap gap-2">
                  <ActionButton
                    disabled={!controller.canMovePrevious}
                    tone="quiet"
                    onClick={controller.goToPreviousStep}
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Anterior
                  </ActionButton>
                  <ActionButton
                    disabled={!controller.canMoveNext}
                    onClick={controller.goToNextStep}
                  >
                    Siguiente
                    <ArrowRight className="h-4 w-4" />
                  </ActionButton>
                </div>
              </div>
            </section>
          </div>
        </section>
      ) : null}
    </main>
  );
}
