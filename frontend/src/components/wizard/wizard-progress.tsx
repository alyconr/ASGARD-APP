import { Check, CircleDot, Clock3 } from "lucide-react";

import { cn } from "@/lib/utils";
import type {
  ProgramaWizardStepDefinition,
  ProgramaWizardStepId,
} from "@/features/programa/types";

interface WizardProgressProps {
  currentStepId: ProgramaWizardStepId;
  steps: ProgramaWizardStepDefinition[];
  touchedSteps: ProgramaWizardStepId[];
  onSelectStep: (stepId: ProgramaWizardStepId) => void;
  disabledSteps?: ProgramaWizardStepId[];
}

export function WizardProgress({
  currentStepId,
  steps,
  touchedSteps,
  onSelectStep,
  disabledSteps = [],
}: WizardProgressProps): React.JSX.Element {
  const currentIndex = steps.findIndex((step) => step.id === currentStepId);

  return (
    <ol className="grid gap-2">
      {steps.map((step) => {
        const isCurrent = step.id === currentStepId;
        const isCompleted = currentIndex > step.index;
        const isTouched = touchedSteps.includes(step.id);
        const isDisabled = disabledSteps.includes(step.id);
        const statusLabel = isCurrent
          ? "Actual"
          : isCompleted
            ? "Completado"
            : isTouched
              ? "Visitado"
              : "Pendiente";

        return (
          <li key={step.id}>
            <button
              type="button"
              onClick={() => onSelectStep(step.id)}
              disabled={isDisabled}
              aria-current={isCurrent ? "step" : undefined}
              className={cn(
                "group w-full rounded-lg border px-4 py-3 text-left transition duration-200",
                isCurrent &&
                  "border-[var(--accent)] bg-[var(--accent-soft)] shadow-[0_10px_24px_rgba(0,132,61,0.12)]",
                !isCurrent &&
                  "border-[color:var(--card-border)] bg-white hover:border-[var(--accent)]/45",
                isDisabled &&
                  "opacity-50 cursor-not-allowed hover:border-[color:var(--card-border)] bg-slate-50/50",
              )}
            >
              <div className="flex items-start gap-4">
                <span
                  className={cn(
                    "mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border text-sm font-semibold transition",
                    isCurrent &&
                      "border-[var(--accent)] bg-[var(--accent)] text-white",
                    isCompleted &&
                      "border-emerald-600 bg-emerald-600 text-white",
                    !isCurrent &&
                      !isCompleted &&
                      "border-[color:var(--card-border)] bg-[var(--paper-strong)] text-[var(--foreground)]",
                  )}
                >
                  {isCompleted ? <Check className="h-4 w-4" /> : step.shortLabel}
                </span>

                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-[var(--foreground)]">
                      {step.label}
                    </p>
                    <span
                      className={cn(
                        "inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-[11px] font-semibold uppercase",
                        isCurrent &&
                          "bg-[var(--foreground)] text-[var(--paper-strong)]",
                        isCompleted &&
                          "bg-emerald-100 text-emerald-800",
                        !isCurrent &&
                          !isCompleted &&
                          isTouched &&
                          "bg-[var(--accent-soft)] text-[var(--accent)]",
                        !isCurrent &&
                          !isCompleted &&
                          !isTouched &&
                          "bg-[var(--paper)] text-[var(--muted)]",
                      )}
                    >
                      {isCurrent ? <CircleDot className="h-3 w-3" /> : null}
                      {!isCurrent && !isCompleted ? (
                        <Clock3 className="h-3 w-3" />
                      ) : null}
                      {statusLabel}
                    </span>
                  </div>

                  <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
                    {step.description}
                  </p>
                </div>
              </div>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
