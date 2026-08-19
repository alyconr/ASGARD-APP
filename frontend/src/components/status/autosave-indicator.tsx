import { AlertTriangle, CheckCircle2, LoaderCircle, NotebookPen } from "lucide-react";

import { cn } from "@/lib/utils";
import type { AutosaveState } from "@/features/programa/types";

interface AutosaveIndicatorProps {
  state: AutosaveState;
  message: string;
  lastSavedAt: string | null;
}

function formatTimestamp(value: string | null): string | null {
  if (value === null) {
    return null;
  }

  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "America/Bogota",
  }).format(new Date(value));
}

export function AutosaveIndicator({
  state,
  message,
  lastSavedAt,
}: AutosaveIndicatorProps): React.JSX.Element {
  const formattedTimestamp = formatTimestamp(lastSavedAt);

  return (
    <div
      aria-live="polite"
      className={cn(
        "inline-flex max-w-full items-center gap-3 rounded-lg border px-3 py-2 text-sm transition-colors",
        state === "saved" &&
          "border-emerald-200 bg-emerald-50 text-emerald-900",
        state === "saving" &&
          "border-amber-200 bg-amber-50 text-amber-950",
        state === "error" &&
          "border-rose-200 bg-rose-50 text-rose-900",
        state === "idle" &&
          "border-[color:var(--card-border)] bg-white/80 text-[color:var(--foreground)]",
      )}
    >
      {state === "saved" ? (
        <CheckCircle2 className="h-4 w-4" />
      ) : null}
      {state === "saving" ? (
        <LoaderCircle className="h-4 w-4 animate-spin" />
      ) : null}
      {state === "error" ? (
        <AlertTriangle className="h-4 w-4" />
      ) : null}
      {state === "idle" ? <NotebookPen className="h-4 w-4" /> : null}

      <span className="min-w-0 font-medium">{message}</span>

      {formattedTimestamp !== null ? (
        <span className="shrink-0 text-xs text-current/70">
          {formattedTimestamp}
        </span>
      ) : null}
    </div>
  );
}
