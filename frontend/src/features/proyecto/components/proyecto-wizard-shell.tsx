"use client";

import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  FileSpreadsheet,
  ListChecks,
  RefreshCcw,
  Route,
  Save,
  Trash2,
} from "lucide-react";

import { AutosaveIndicator } from "@/components/status/autosave-indicator";
import { ExtractorSenaInstructions } from "@/components/wizard/extractor-sena-instructions";
import { ProyectoDocumentUpload } from "@/features/proyecto/components/proyecto-document-upload";
import { ProyectoExcelImport } from "@/features/proyecto/components/proyecto-excel-import";
import { PROYECTO_WIZARD_STEPS } from "@/features/proyecto/constants";
import type {
  ProyectoDisponibilidadResponse,
  ProyectoExcelPreviewState,
  ProyectoPdfUploadResult,
  ProyectoWizardPayload,
  ProyectoWizardStepDefinition,
  ProyectoWizardStepId,
} from "@/features/proyecto/types";
import Link from "next/link";
import { useProyectoWizard } from "@/features/proyecto/use-proyecto-wizard";
import { cn } from "@/lib/utils";
import { EstadoDocumentalResponse } from "@/features/drafts/types";
import { useConfirm } from "@/components/feedback/confirm-context";

const STEP_ICONS: Record<
  ProyectoWizardStepId,
  React.ComponentType<{ className?: string }>
> = {
  "fuente-proyecto": FileSpreadsheet,
  "revision-proyecto": ListChecks,
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
}: Readonly<{
  children: React.ReactNode;
  className?: string;
  disabled?: boolean;
  onClick?: () => void;
  tone?: "primary" | "quiet" | "secondary";
}>): React.JSX.Element {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50",
        tone === "primary" &&
          "border border-transparent bg-[var(--accent)] !text-white hover:bg-[var(--accent-strong)]",
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

function WizardProgress({
  currentStepId,
  onSelectStep,
  steps,
  touchedSteps,
  disabledSteps = [],
}: Readonly<{
  currentStepId: ProyectoWizardStepId;
  onSelectStep: (stepId: ProyectoWizardStepId) => void;
  steps: ProyectoWizardStepDefinition[];
  touchedSteps: ProyectoWizardStepId[];
  disabledSteps?: ProyectoWizardStepId[];
}>): React.JSX.Element {
  return (
    <nav aria-label="Progreso del wizard del proyecto" className="grid gap-2">
      {steps.map((step) => {
        const isCurrent = step.id === currentStepId;
        const isTouched = touchedSteps.includes(step.id);
        const isDisabled = disabledSteps.includes(step.id);

        return (
          <button
            key={step.id}
            type="button"
            disabled={isDisabled}
            onClick={() => onSelectStep(step.id)}
            className={cn(
              "grid grid-cols-[2.25rem_1fr] gap-3 rounded-lg border px-3 py-3 text-left transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50",
              isCurrent
                ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                : "border-[color:var(--card-border)] bg-white hover:border-[var(--accent)]/50",
              isDisabled && "bg-slate-50/50 opacity-50",
            )}
          >
            <span
              className={cn(
                "inline-flex h-9 w-9 items-center justify-center rounded-lg text-xs font-semibold",
                isCurrent
                  ? "bg-[var(--accent)] text-white"
                  : "bg-[var(--paper-strong)] text-[var(--muted)]",
              )}
            >
              {isTouched ? <CheckCircle2 className="h-4 w-4" /> : step.shortLabel}
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-semibold text-[var(--foreground)]">
                {step.label}
              </span>
              <span className="mt-1 block text-xs leading-5 text-[var(--muted)]">
                {step.taskRef}
              </span>
            </span>
          </button>
        );
      })}
    </nav>
  );
}

function StepWorkspace({
  currentStep,
  payload,
  onPdfUploaded,
  onExcelPreview,
  onExcelImported,
  docState,
  onHabilitarCarguePdf,
}: Readonly<{
  currentStep: ProyectoWizardStepDefinition;
  payload: ProyectoWizardPayload | null;
  onPdfUploaded: (result: ProyectoPdfUploadResult) => void;
  onExcelPreview: (result: ProyectoExcelPreviewState) => void;
  onExcelImported: (result: ProyectoExcelPreviewState) => void;
  docState: EstadoDocumentalResponse | null;
  onHabilitarCarguePdf: () => void;
}>): React.JSX.Element {
  const Icon = STEP_ICONS[currentStep.id];

  return (
    <section className="rounded-lg border border-[color:var(--card-border)] bg-[var(--card)] p-5 shadow-[0_18px_42px_rgba(23,53,47,0.08)]">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-[var(--line)] pb-5">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold tracking-[0.16em] text-[var(--accent-strong)] uppercase">
            {currentStep.shortLabel} / {currentStep.label}
          </p>
          <h3 className="mt-2 text-2xl font-[family:var(--font-display)] font-semibold text-[var(--foreground)]">
            {currentStep.description}
          </h3>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
            El proyecto formativo usa PDF como evidencia documental y Excel como fuente
            estructurada activa.
          </p>
        </div>

        <span className="inline-flex h-11 w-11 items-center justify-center rounded-lg bg-[var(--foreground)] text-white">
          <Icon className="h-5 w-5" />
        </span>
      </header>

      <div className="mt-5 min-w-0">
        <div className="min-w-0 rounded-lg border border-dashed border-[color:var(--card-border)] bg-white p-5">
          {currentStep.id === "fuente-proyecto" && payload !== null ? (
            <div className="grid gap-4">
              <ExtractorSenaInstructions
                referenceId={payload.meta.referenciaId}
                scope="proyecto"
              />
              <ProyectoExcelImport
                currentResult={payload.documental.fuente_estructurada}
                onPreview={onExcelPreview}
                onImported={onExcelImported}
                planeacionHref={`/planeacion/${payload.meta.programaReferenciaId}`}
                referenciaId={payload.meta.referenciaId}
              />
              {payload.documental.fuente_estructurada?.confirmacion?.estado === "IMPORTADO" ||
              docState?.proyecto_importado === true ? (
                <ProyectoDocumentUpload
                  currentResult={payload.documental.proyecto_pdf}
                  onUploaded={onPdfUploaded}
                  referenciaId={payload.meta.referenciaId}
                  habilitado={true}
                  carguePdfHabilitado={true}
                  onHabilitarCarguePdf={onHabilitarCarguePdf}
                  documentoExistente={docState?.proyecto_pdf}
                />
              ) : null}
            </div>

          ) : payload !== null ? (
            <div className="grid gap-6">
              <div className="rounded-lg bg-[var(--paper-strong)] p-4 border border-[color:var(--card-border)]">
                <h4 className="text-sm font-semibold text-[var(--foreground)] mb-3 uppercase tracking-wider">
                  Resumen General del Proyecto
                </h4>
                <dl className="grid gap-4 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="text-xs font-medium text-[var(--muted)]">Nombre del Proyecto</dt>
                    <dd className="mt-1 font-semibold text-[var(--foreground)]">{payload.proyecto.nombre_proyecto || "No asignado (Cargar Excel)"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium text-[var(--muted)]">Código del Proyecto (SOFIA)</dt>
                    <dd className="mt-1 font-semibold text-[var(--foreground)]">{payload.proyecto.codigo_proyecto || "No asignado (Cargar Excel)"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium text-[var(--muted)]">Referencia de Sesión</dt>
                    <dd className="mt-1 text-xs break-all text-[var(--foreground)]">{payload.meta.referenciaId}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium text-[var(--muted)]">Programa Asociado</dt>
                    <dd className="mt-1 text-[var(--foreground)]">{payload.meta.programaId || "Desconocido"}</dd>
                  </div>
                </dl>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg border border-[color:var(--card-border)] bg-white p-4">
                  <h4 className="text-xs font-semibold text-[var(--muted)] uppercase tracking-wider mb-2">
                    Evidencia Documental (PDF)
                  </h4>
                  {payload.documental.proyecto_pdf ? (
                    <div className="text-sm">
                      <p className="font-semibold text-emerald-700 font-medium">✓ Cargado</p>
                      <p className="mt-1 text-[var(--muted)] truncate">Archivo: {payload.documental.proyecto_pdf.documento.original_filename}</p>
                    </div>
                  ) : (
                    <p className="text-sm text-amber-700 font-medium">⚠️ No se ha cargado el PDF del proyecto formativo</p>
                  )}
                </div>

                <div className="rounded-lg border border-[color:var(--card-border)] bg-white p-4">
                  <h4 className="text-xs font-semibold text-[var(--muted)] uppercase tracking-wider mb-2">
                    Estructura Curricular (Excel)
                  </h4>
                  {payload.documental.fuente_estructurada?.confirmacion.estado === "IMPORTADO" ? (
                    <div className="text-sm">
                      <p className="font-semibold text-emerald-700 font-medium">✓ Importado y Confirmado</p>
                      <p className="mt-1 text-[var(--muted)]">Fases: {payload.documental.fuente_estructurada.preview?.resumen.fases ?? 0}</p>
                      <p className="text-[var(--muted)]">Actividades: {payload.documental.fuente_estructurada.preview?.resumen.actividades ?? 0}</p>
                      <p className="text-[var(--muted)]">Resultados específicos: {payload.documental.fuente_estructurada.preview?.resumen.resultados_especificos ?? 0}</p>
                    </div>
                  ) : (
                    <p className="text-sm text-amber-700 font-medium">⚠️ Estructura pendiente de importación / confirmación</p>
                  )}
                </div>
              </div>

              {payload.documental.fuente_estructurada?.confirmacion.estado === "IMPORTADO" ? (
                <div className="rounded-lg border border-[var(--accent)] bg-[var(--accent-soft)] p-5 shadow-sm">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="max-w-xl">
                      <h4 className="text-base font-semibold text-[var(--accent-strong)]">
                        Proyecto listo para cierre
                      </h4>
                      <p className="mt-1 text-sm text-[var(--muted)] leading-relaxed">
                        La matriz del proyecto formativo fue cargada y validada. Revisa el consolidado y cierra el proyecto como COMPLETO para habilitar la planeacion pedagogica.
                      </p>
                    </div>
                  </div>
                </div>
              ) : null}

              <div className="rounded-lg bg-slate-50 p-4 border border-slate-200">
                <h4 className="text-xs font-semibold text-slate-800 uppercase tracking-wider mb-2">
                  Trazabilidad de la Información
                </h4>
                <p className="text-xs leading-5 text-[var(--muted)]">
                  La estructura de planeación, fases, actividades y resultados de aprendizaje (RAP) específicos ha sido importada de manera exclusiva a partir de la matriz de Excel canónico suministrada por el usuario, sirviendo el archivo PDF cargado como sustento y evidencia documental del cargue en la plataforma MinIO.
                </p>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

export function ProyectoWizardShell({
  availability,
}: Readonly<{
  availability: ProyectoDisponibilidadResponse;
}>): React.JSX.Element {
  const controller = useProyectoWizard({
    programaId: availability.programa_id,
    programaReferenciaId: availability.programa_referencia_id ?? availability.referencia_id,
  });
  const confirm = useConfirm();
  const currentStep =
    PROYECTO_WIZARD_STEPS[controller.currentStepIndex] ??
    PROYECTO_WIZARD_STEPS[0];

  if (availability.proyecto_bloqueado || !availability.programa_completo) {
    return (
      <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900">
        El wizard del proyecto formativo permanece bloqueado hasta cerrar el programa de formación.
      </section>
    );
  }

  if (controller.isBootstrapping) {
    return (
      <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-5">
        <div className="flex items-center gap-3 text-[var(--accent-strong)]">
          <RefreshCcw className="h-5 w-5 animate-spin" />
          <p className="text-sm font-semibold">
            Revisando borrador activo del proyecto formativo
          </p>
        </div>
      </section>
    );
  }

  return (
    <section
      aria-label="Wizard base del proyecto formativo"
      className="grid gap-5 rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] p-4"
    >
      <header className="flex flex-wrap items-start justify-between gap-4 rounded-lg border border-[color:var(--card-border)] bg-white px-5 py-4">
        <div className="max-w-3xl">
          <div className="flex items-center gap-2 text-[var(--accent-strong)]">
            <Route className="h-5 w-5" />
            <p className="text-xs font-semibold tracking-[0.18em] uppercase">
              Proyecto / Fase 1
            </p>
          </div>
          <h2 className="mt-2 text-2xl font-[family:var(--font-display)] font-semibold text-[var(--foreground)] lg:text-3xl">
            Wizard base del proyecto formativo
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            El proyecto formativo ya esta habilitado porque el programa de formación esta COMPLETO.
            Este flujo guarda PDF como evidencia y usa la matriz Excel como
            fuente estructurada del proyecto formativo.
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
      </header>

      {controller.errorMessage !== null ? (
        <p className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-900">
          {controller.errorMessage}
        </p>
      ) : null}

      {!controller.isWizardActive ? (
        <section className="grid gap-4 lg:grid-cols-[1fr_24rem]">
          <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-5">
            <h3 className="text-xl font-semibold text-[var(--foreground)]">
              Iniciar proyecto
            </h3>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
              Crea un borrador independiente de tipo PROYECTO asociado al
              programa de formación completo. El primer paso es fuente documental:
              PDF evidencia y Excel estructurado.
            </p>
            <ActionButton
              className="mt-4"
              onClick={() => void controller.startNewFlow()}
            >
              Iniciar wizard del proyecto formativo
            </ActionButton>
          </section>

          <aside className="rounded-lg border border-[color:var(--card-border)] bg-white p-5">
            <h3 className="text-xl font-semibold text-[var(--foreground)]">
              Continuar borrador
            </h3>
            <label className="mt-4 block">
              <span className="text-xs font-semibold tracking-[0.16em] text-[var(--muted)] uppercase">
                referencia_id proyecto
              </span>
              <input
                value={controller.continueReferenceInput}
                onChange={(event) =>
                  controller.updateContinueReferenceInput(event.target.value)
                }
                placeholder="UUID del borrador"
                className="mt-2 w-full rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm text-[var(--foreground)] outline-none transition placeholder:text-[var(--muted)]/70 focus:border-[var(--accent)]"
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

            {controller.knownDrafts.length > 0 ? (
              <div className="mt-5 grid gap-2 border-t border-[var(--line)] pt-4">
                {controller.knownDrafts.map((draft) => (
                  <article
                    key={draft.referenciaId}
                    className="grid gap-3 rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] px-3 py-3"
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
                        {formatReferenceId(draft.referenciaId)} / {draft.estado}
                      </span>
                    </button>
                    <button
                      type="button"
                      aria-label={`Eliminar cargue ${draft.label}`}
                      title="Eliminar cargue del proyecto y archivos en MinIO"
                      onClick={async () => {
                        const confirmed = await confirm({
                          title: "Eliminar cargue de proyecto",
                          message: "Esto eliminará el cargue del proyecto en el servidor y sus archivos asociados en MinIO. También se quitará de esta lista.",
                          isDestructive: true,
                        });
                        if (confirmed) {
                          void controller.forgetKnownDraft(draft.referenciaId);
                        }
                      }}
                      className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-transparent px-2 py-1.5 text-xs font-semibold text-[var(--muted)] transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                    >
                      <Trash2 className="h-4 w-4" />
                      Quitar
                    </button>
                  </article>
                ))}
                <ActionButton tone="quiet" onClick={controller.clearKnownDrafts}>
                  Limpiar lista
                </ActionButton>
              </div>
            ) : null}
          </aside>
        </section>
      ) : null}

      {controller.isWizardActive && controller.payload !== null ? (
        <section className="grid gap-5 lg:grid-cols-[21rem_minmax(0,1fr)]">
          <aside className="flex flex-col gap-4 self-start lg:sticky lg:top-6 w-full h-fit">
            <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-4">
              <WizardProgress
                currentStepId={controller.currentStepId}
                onSelectStep={controller.goToStep}
                steps={PROYECTO_WIZARD_STEPS}
                touchedSteps={controller.payload.meta.touchedSteps}
                disabledSteps={controller.disabledSteps}
              />
            </section>
            <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-4 text-sm leading-6">
              <p className="text-xs font-semibold tracking-[0.16em] text-[var(--muted)] uppercase">
                Borrador proyecto
              </p>
              <p className="mt-2 font-semibold text-[var(--foreground)]">
                {formatReferenceId(controller.payload.meta.referenciaId)}
              </p>
              <p className="mt-1 text-[var(--muted)]">
                Estado: {controller.draftStatus}
              </p>
            </section>
            <ActionButton tone="quiet" onClick={controller.resetFlow}>
              Volver al inicio del proyecto formativo
            </ActionButton>
          </aside>

          <div className="grid min-w-0 gap-4">
            <StepWorkspace
              currentStep={currentStep}
              payload={controller.payload}
              onPdfUploaded={(result) =>
                controller.updateProyectoPdfResult(result)
              }
              onExcelPreview={(result) =>
                controller.updateProyectoExcelPreview(result)
              }
              onExcelImported={(result) =>
                controller.updateProyectoExcelImport(result)
              }
              docState={controller.docState}
              onHabilitarCarguePdf={controller.habilitarCarguePdf}
            />

            <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm leading-6 text-[var(--muted)]">
                  Paso {controller.currentStepIndex + 1} de{" "}
                  {PROYECTO_WIZARD_STEPS.length}
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
                  {controller.currentStepId === "revision-proyecto" &&
                  controller.draftStatus === "COMPLETO" ? (
                    <Link
                      href={`/planeacion/${controller.payload.meta.programaReferenciaId}`}
                      className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-transparent bg-[var(--accent)] px-4 py-2 text-sm font-semibold !text-white transition hover:bg-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                    >
                      Configurar Planeación
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                  ) : controller.currentStepId === "revision-proyecto" &&
                    controller.payload?.documental.fuente_estructurada?.confirmacion.estado === "IMPORTADO" ? (
                    <ActionButton
                      disabled={controller.isClosing}
                      onClick={() => void controller.closeProject()}
                    >
                      {controller.isClosing ? (
                        <RefreshCcw className="h-4 w-4 animate-spin" />
                      ) : (
                        <CheckCircle2 className="h-4 w-4" />
                      )}
                      Confirmar y cerrar proyecto
                    </ActionButton>
                  ) : (
                    <ActionButton
                      disabled={!controller.canMoveNext}
                      onClick={controller.goToNextStep}
                    >
                      Siguiente
                      <ArrowRight className="h-4 w-4" />
                    </ActionButton>
                  )}
                </div>
              </div>
            </section>
          </div>
        </section>
      ) : null}
    </section>
  );
}
