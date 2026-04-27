"use client";

import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  BookOpenCheck,
  ClipboardList,
  FileText,
  FolderOpen,
  Landmark,
  NotebookText,
  RefreshCcw,
  Route,
  Save,
  ScanLine,
} from "lucide-react";

import { AutosaveIndicator } from "@/components/status/autosave-indicator";
import { WizardProgress } from "@/components/wizard/wizard-progress";
import { ProgramaBaseForm } from "@/features/programa/components/programa-base-form";
import { ProgramaDocumentUpload } from "@/features/programa/components/programa-document-upload";
import { PROGRAMA_WIZARD_STEPS } from "@/features/programa/constants";
import { useProgramaWizard } from "@/features/programa/use-programa-wizard";
import { cn } from "@/lib/utils";
import type {
  ProgramaEntryMode,
  ProgramaPdfUploadResponse,
  ProgramaPdfUploadResult,
  ProgramaWizardStepDefinition,
  ProgramaWizardStepId,
} from "@/features/programa/types";
import type { ProgramaBaseField } from "@/features/programa/validation";

const ENTRY_MODE_COPY: Record<
  Exclude<ProgramaEntryMode, null>,
  {
    label: string;
    description: string;
    icon: React.ComponentType<{ className?: string }>;
  }
> = {
  MANUAL: {
    label: "Manual",
    description:
      "Captura directa para iniciar el programa desde datos propios.",
    icon: NotebookText,
  },
  PDF: {
    label: "PDF",
    description: "Carril reservado para cargue documental con revision humana.",
    icon: FileText,
  },
};

const STEP_CONTENT: Record<
  ProgramaWizardStepId,
  {
    label: string;
    description: string;
    slotLabel: string;
    checks: string[];
    icon: React.ComponentType<{ className?: string }>;
  }
> = {
  "datos-programa": {
    label: "Datos base del programa",
    description:
      "Captura los campos minimos del programa y conserva avances parciales.",
    slotLabel: "Formulario base",
    checks: [
      "Misma referencia del flujo",
      "Paso actual persistido",
      "Borrador editable",
    ],
    icon: ClipboardList,
  },
  "origen-documental": {
    label: "Origen de informacion",
    description:
      "El PDF se almacena y se diagnostica sin activar extraccion de campos.",
    slotLabel: "Cargue documental",
    checks: ["PDF valido", "Diagnostico estructurado", "Fallback manual"],
    icon: ScanLine,
  },
  "estructura-curricular": {
    label: "Estructura curricular",
    description:
      "El contenedor ya separa el trabajo curricular de la captura inicial.",
    slotLabel: "Slot curricular",
    checks: ["Competencias", "Resultados", "Saberes, procesos y criterios"],
    icon: FolderOpen,
  },
  "revision-programa": {
    label: "Revision del programa",
    description:
      "La revision se mantiene como paso independiente antes de cualquier cierre.",
    slotLabel: "Slot de revision consolidada",
    checks: [
      "Vista consolidada",
      "Correccion antes de cierre",
      "Sin cierre implementado",
    ],
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

function EntryModeButton({
  mode,
  onSelect,
}: Readonly<{
  mode: Exclude<ProgramaEntryMode, null>;
  onSelect: () => void;
}>): React.JSX.Element {
  const copy = ENTRY_MODE_COPY[mode];
  const Icon = copy.icon;

  return (
    <button
      type="button"
      onClick={onSelect}
      className="grid gap-3 rounded-lg border border-[color:var(--card-border)] bg-white p-4 text-left transition hover:border-[var(--accent)] hover:shadow-[0_12px_28px_rgba(23,53,47,0.08)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
    >
      <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent-strong)]">
        <Icon className="h-5 w-5" />
      </span>
      <span className="text-base font-semibold text-[var(--foreground)]">
        {copy.label}
      </span>
      <span className="text-sm leading-6 text-[var(--muted)]">
        {copy.description}
      </span>
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

function StepWorkspace({
  currentStep,
  currentStepNote,
  entryMode,
  programaValue,
  onEntryModeChange,
  onProgramaPdfUploaded,
  onProgramaFieldChange,
  onNoteChange,
  programaPdfResult,
  referenceId,
}: Readonly<{
  currentStep: ProgramaWizardStepDefinition;
  currentStepNote: string;
  entryMode: ProgramaEntryMode;
  programaPdfResult: ProgramaPdfUploadResult | null;
  referenceId: string;
  programaValue: {
    codigo_programa: string;
    nombre_programa: string;
    version_programa: string;
  };
  onEntryModeChange: (entryMode: Exclude<ProgramaEntryMode, null>) => void;
  onProgramaPdfUploaded: (result: ProgramaPdfUploadResponse) => void;
  onProgramaFieldChange: (field: ProgramaBaseField, value: string) => void;
  onNoteChange: (value: string) => void;
}>): React.JSX.Element {
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

      {currentStep.id === "origen-documental" ? (
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {(["MANUAL", "PDF"] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => onEntryModeChange(mode)}
              className={cn(
                "rounded-lg border px-4 py-3 text-left transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]",
                entryMode === mode
                  ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                  : "border-[color:var(--card-border)] bg-white hover:border-[var(--accent)]/50",
              )}
            >
              <p className="text-sm font-semibold text-[var(--foreground)]">
                {ENTRY_MODE_COPY[mode].label}
              </p>
              <p className="mt-1 text-sm leading-6 text-[var(--muted)]">
                {ENTRY_MODE_COPY[mode].description}
              </p>
            </button>
          ))}
        </div>
      ) : null}

      <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_18rem]">
        <div className="rounded-lg border border-dashed border-[color:var(--card-border)] bg-white p-5">
          {currentStep.id === "datos-programa" ? (
            <ProgramaBaseForm
              value={programaValue}
              onFieldChange={onProgramaFieldChange}
            />
          ) : currentStep.id === "origen-documental" ? (
            <ProgramaDocumentUpload
              currentResult={programaPdfResult}
              referenciaId={referenceId}
              onUploaded={onProgramaPdfUploaded}
            />
          ) : (
            <>
              <p className="text-xs font-semibold tracking-[0.16em] text-[var(--muted)] uppercase">
                {content.slotLabel}
              </p>
              <div className="mt-4 grid gap-2 sm:grid-cols-3">
                {content.checks.map((check) => (
                  <div
                    key={check}
                    className="rounded-lg bg-[var(--paper-strong)] px-3 py-3 text-sm leading-5 text-[var(--foreground)]"
                  >
                    {check}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        <label className="rounded-lg border border-[color:var(--card-border)] bg-white p-4">
          <span className="text-xs font-semibold tracking-[0.16em] text-[var(--muted)] uppercase">
            Notas del paso
          </span>
          <textarea
            value={currentStepNote}
            onChange={(event) => onNoteChange(event.target.value)}
            rows={7}
            placeholder="Pendientes o decisiones de este paso."
            className="mt-3 min-h-36 w-full resize-none rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] px-3 py-2 text-sm leading-6 text-[var(--foreground)] transition outline-none placeholder:text-[var(--muted)]/70 focus:border-[var(--accent)]"
          />
        </label>
      </div>
    </section>
  );
}

function DraftSummary({
  entryMode,
  referenceId,
  stepLabel,
}: Readonly<{
  entryMode: ProgramaEntryMode;
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
        <dt className="text-[var(--muted)]">Modalidad</dt>
        <dd className="mt-1 font-semibold text-[var(--foreground)]">
          {entryMode === null ? "Pendiente" : ENTRY_MODE_COPY[entryMode].label}
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
              Revisando borrador activo del programa
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
              <Landmark className="h-5 w-5" />
              <p className="text-xs font-semibold tracking-[0.18em] uppercase">
                SENA / Fase 1
              </p>
            </div>
            <h1 className="mt-2 text-3xl font-[family:var(--font-display)] font-semibold text-[var(--foreground)] lg:text-4xl">
              Wizard base del programa
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
              Flujo de captura con borrador persistente, navegacion por pasos y
              recuperacion por referencia estable.
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
              <EntryModeButton
                mode="MANUAL"
                onSelect={() => void controller.startNewFlow("MANUAL")}
              />
              <EntryModeButton
                mode="PDF"
                onSelect={() => void controller.startNewFlow("PDF")}
              />
            </div>

            <div className="mt-5 rounded-lg border border-[color:var(--card-border)] bg-white px-4 py-3 text-sm leading-6 text-[var(--muted)]">
              El proceso inicia en estado BORRADOR y conserva el mismo
              referencia_id durante todo el wizard.
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
              <p className="text-xs font-semibold tracking-[0.16em] text-[var(--muted)] uppercase">
                Borradores locales
              </p>
              {controller.knownDrafts.length > 0 ? (
                <div className="mt-3 grid gap-2">
                  {controller.knownDrafts.map((draft) => (
                    <button
                      key={draft.referenciaId}
                      type="button"
                      onClick={() =>
                        void controller.recoverDraftByReference(
                          draft.referenciaId,
                        )
                      }
                      className="rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-3 text-left transition hover:border-[var(--accent)]"
                    >
                      <span className="block truncate text-sm font-semibold text-[var(--foreground)]">
                        {draft.label}
                      </span>
                      <span className="mt-1 block text-xs text-[var(--muted)]">
                        {formatReferenceId(draft.referenciaId)} / {draft.estado}
                      </span>
                    </button>
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
        <section className="grid gap-5 lg:grid-cols-[22rem_1fr]">
          <aside className="grid gap-4">
            <section className="rounded-lg border border-[color:var(--card-border)] bg-[var(--card)] p-4 shadow-[0_18px_42px_rgba(23,53,47,0.08)]">
              <WizardProgress
                currentStepId={controller.currentStepId}
                steps={PROGRAMA_WIZARD_STEPS}
                touchedSteps={controller.payload.meta.touchedSteps}
                onSelectStep={controller.goToStep}
              />
            </section>

            <DraftSummary
              entryMode={controller.payload.meta.entryMode}
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

          <div className="grid gap-4">
            <StepWorkspace
              currentStep={currentStep}
              currentStepNote={
                controller.payload.wizard.notesByStep[
                  controller.currentStepId
                ] ?? ""
              }
              entryMode={controller.payload.meta.entryMode}
              programaPdfResult={controller.payload.documental.programa_pdf}
              referenceId={
                controller.activeReferenceId ??
                controller.payload.meta.referenciaId
              }
              programaValue={controller.payload.programa}
              onEntryModeChange={controller.setEntryMode}
              onProgramaPdfUploaded={controller.updateProgramaPdfResult}
              onProgramaFieldChange={controller.updateProgramaBaseField}
              onNoteChange={(value) =>
                controller.updateStepNote(controller.currentStepId, value)
              }
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
