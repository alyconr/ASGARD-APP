"use client";

import {
  CheckCircle2,
  ChevronUp,
  Circle,
  Info,
  LockKeyhole,
  Minus,
  TriangleAlert,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { cn } from "@/lib/utils";
import type {
  WizardGuideAction,
  WizardGuideChecklistItem,
  WizardGuideSeverity,
  WizardGuideState,
} from "@/features/guide/wizard-guide-engine";

const STORAGE_PREFIX = "asgard.wizard-guide";

const severityStyles: Record<
  WizardGuideSeverity,
  {
    shell: string;
    avatar: string;
    badge: string;
    rail: string;
    icon: typeof Info;
  }
> = {
  info: {
    shell: "border-emerald-200/80 bg-white text-[var(--foreground)]",
    avatar: "bg-emerald-700 text-white",
    badge: "bg-emerald-50 text-emerald-800",
    rail: "bg-emerald-600",
    icon: Info,
  },
  warning: {
    shell: "border-amber-200/90 bg-white text-[var(--foreground)]",
    avatar: "bg-amber-600 text-white",
    badge: "bg-amber-50 text-amber-900",
    rail: "bg-amber-500",
    icon: TriangleAlert,
  },
  blocked: {
    shell: "border-rose-200/90 bg-white text-[var(--foreground)]",
    avatar: "bg-rose-700 text-white",
    badge: "bg-rose-50 text-rose-900",
    rail: "bg-rose-600",
    icon: LockKeyhole,
  },
  success: {
    shell: "border-green-200/90 bg-white text-[var(--foreground)]",
    avatar: "bg-green-700 text-white",
    badge: "bg-green-50 text-green-900",
    rail: "bg-green-600",
    icon: CheckCircle2,
  },
};

function checklistIcon(item: WizardGuideChecklistItem): React.JSX.Element {
  if (item.status === "done") {
    return <CheckCircle2 className="h-3.5 w-3.5 text-green-700" />;
  }
  if (item.status === "current") {
    return <ChevronUp className="h-3.5 w-3.5 text-amber-700" />;
  }
  return <Circle className="h-3.5 w-3.5 text-slate-400" />;
}

function runTargetAction(action: WizardGuideAction): void {
  if (!action.targetId || typeof document === "undefined") {
    return;
  }

  document.getElementById(action.targetId)?.scrollIntoView({
    behavior: "smooth",
    block: "center",
  });
}

function ActionControl({
  action,
  tone,
}: Readonly<{
  action: WizardGuideAction;
  tone: "primary" | "secondary";
}>): React.JSX.Element {
  const className =
    tone === "primary"
      ? "inline-flex min-h-10 items-center justify-center rounded-lg bg-[var(--accent)] px-3 py-2 text-xs font-semibold text-white transition hover:bg-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
      : "inline-flex min-h-10 items-center justify-center rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-xs font-semibold text-[var(--foreground)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]";

  if (action.href) {
    return (
      <Link href={action.href} className={className}>
        {action.label}
      </Link>
    );
  }

  return (
    <button
      type="button"
      onClick={() => runTargetAction(action)}
      className={className}
    >
      {action.label}
    </button>
  );
}

function AnimatedGuideAvatar({
  className,
}: Readonly<{
  className?: string;
}>): React.JSX.Element {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 44 44"
      className={cn(
        "asgard-guide-avatar h-full w-full select-none fill-none stroke-current",
        className,
      )}
    >
      <defs>
        <clipPath id="glasses-clip">
          <circle cx="17.5" cy="22.5" r="2.8" />
          <circle cx="26.5" cy="22.5" r="2.8" />
        </clipPath>
      </defs>

      {/* Partículas de Conocimiento */}
      <path
        d="M6 14 Q8 14 8 12 Q8 14 10 14 Q8 14 8 16 Q8 14 6 14 Z"
        fill="currentColor"
        stroke="none"
        className="asgard-teacher-sparkle asgard-teacher-sparkle--one text-white/90"
      />
      <path
        d="M34 18 Q36 18 36 16 Q36 18 38 18 Q36 18 36 20 Q36 18 34 18 Z"
        fill="currentColor"
        stroke="none"
        className="asgard-teacher-sparkle asgard-teacher-sparkle--two text-white/90"
      />

      {/* Cuerpo */}
      <path
        d="M12 36 C12 33 16 32 22 32 C28 32 32 33 32 36 V42 H12 V36 Z"
        fill="currentColor"
        fillOpacity="0.15"
        strokeWidth="1.2"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M18 32 L22 37 L26 32"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M22 37 V42"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />

      {/* Cabeza */}
      <circle
        cx="22"
        cy="22"
        r="7.5"
        fill="currentColor"
        fillOpacity="0.1"
        stroke="currentColor"
        strokeWidth="1.2"
      />

      {/* Cabello */}
      <path
        d="M14.5 22 C14.5 16 17 14.5 22 14.5 C27 14.5 29.5 16 29.5 22 C29.5 19 28 16 22 16 C16 16 14.5 19 14.5 22 Z"
        fill="currentColor"
        stroke="currentColor"
        strokeWidth="0.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Cristales de Anteojos */}
      <circle cx="17.5" cy="22.5" r="2.8" fill="currentColor" fillOpacity="0.2" stroke="none" />
      <circle cx="26.5" cy="22.5" r="2.8" fill="currentColor" fillOpacity="0.2" stroke="none" />

      {/* Brillo de Anteojos */}
      <g clipPath="url(#glasses-clip)">
        <path
          d="M 5 28 L 15 14 M 10 28 L 20 14 M 15 28 L 25 14 M 20 28 L 30 14 M 25 28 L 35 14"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeOpacity="0.65"
          className="asgard-teacher-glasses-glare"
        />
      </g>

      {/* Montura de Anteojos */}
      <circle
        cx="17.5"
        cy="22.5"
        r="2.8"
        stroke="currentColor"
        strokeWidth="1.2"
      />
      <circle
        cx="26.5"
        cy="22.5"
        r="2.8"
        stroke="currentColor"
        strokeWidth="1.2"
      />
      <path
        d="M20.3 22.5 H23.7"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
      />

      {/* Birrete */}
      <g className="asgard-teacher-cap">
        <path
          d="M17 10 V13 C17 14 27 14 27 13 V10"
          fill="currentColor"
          fillOpacity="0.3"
          stroke="currentColor"
          strokeWidth="1.2"
          strokeLinejoin="round"
        />
        <polygon
          points="22,5 33,9.5 22,14 11,9.5"
          fill="currentColor"
          fillOpacity="0.9"
          stroke="currentColor"
          strokeWidth="1.2"
          strokeLinejoin="round"
        />
        <circle cx="22" cy="9.5" r="0.8" fill="currentColor" stroke="none" />
        <path
          d="M22 9.5 C19 10 14 11 13 13.5 V16.5"
          stroke="currentColor"
          strokeWidth="0.8"
          strokeLinecap="round"
          fill="none"
        />
        <polygon
          points="12,16.5 14,16.5 13,19"
          fill="currentColor"
          stroke="none"
        />
      </g>
    </svg>
  );
}

export function WizardGuideAssistant({
  guide,
  storageKey,
}: Readonly<{
  guide: WizardGuideState;
  storageKey: string;
}>): React.JSX.Element {
  const storageId = `${STORAGE_PREFIX}.${storageKey}`;
  const styles = severityStyles[guide.severity];
  const SeverityIcon = styles.icon;
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [hasSeenIntro, setHasSeenIntro] = useState(false);

  useEffect(() => {
    try {
      const rawValue = window.localStorage.getItem(storageId);
      if (rawValue === null) {
        return;
      }
      const saved = JSON.parse(rawValue) as {
        collapsed?: boolean;
        introSeen?: boolean;
      };
      setIsCollapsed(saved.collapsed === true);
      setHasSeenIntro(saved.introSeen === true);
    } catch {
      setIsCollapsed(false);
      setHasSeenIntro(false);
    }
  }, [storageId]);

  useEffect(() => {
    try {
      window.localStorage.setItem(
        storageId,
        JSON.stringify({
          collapsed: isCollapsed,
          introSeen: hasSeenIntro,
        }),
      );
    } catch {}
  }, [hasSeenIntro, isCollapsed, storageId]);

  const checklistSummary = useMemo(() => {
    const total = guide.checklist.length;
    const done = guide.checklist.filter((item) => item.status === "done").length;
    return `${done}/${total}`;
  }, [guide.checklist]);

  if (isCollapsed) {
    return (
      <aside
        aria-label="Asistente guiado ASGARD colapsado"
        className="fixed right-4 bottom-4 z-50 sm:right-6 sm:bottom-6"
      >
        <button
          type="button"
          onClick={() => {
            setIsCollapsed(false);
            setHasSeenIntro(true);
          }}
          className={cn(
            "group grid h-14 w-14 place-items-center rounded-lg border border-white/70 shadow-[0_18px_40px_rgba(23,53,47,0.18)] transition hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]",
            styles.avatar,
          )}
        >
          <AnimatedGuideAvatar />
          <span className="sr-only">Abrir guia ASGARD</span>
        </button>
      </aside>
    );
  }

  return (
    <aside
      aria-label="Asistente guiado ASGARD"
      className="fixed inset-x-3 bottom-3 z-50 mx-auto max-w-[25rem] sm:right-6 sm:bottom-6 sm:left-auto sm:mx-0"
    >
      <section
        className={cn(
          "relative overflow-hidden rounded-lg border p-4 shadow-[0_24px_60px_rgba(23,53,47,0.16)] backdrop-blur",
          styles.shell,
        )}
      >
        <span
          aria-hidden="true"
          className={cn("absolute inset-y-0 left-0 w-1", styles.rail)}
        />
        <div className="flex items-start gap-3">
          <div
            className={cn(
              "relative grid h-11 w-11 shrink-0 place-items-center rounded-lg shadow-[inset_0_-10px_18px_rgba(0,0,0,0.18)]",
              styles.avatar,
            )}
          >
            <AnimatedGuideAvatar />
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[0.68rem] font-bold tracking-[0.18em] text-[var(--muted)] uppercase">
                  {guide.eyebrow}
                </p>
                <h2 className="mt-1 text-sm font-semibold text-[var(--foreground)]">
                  {guide.title}
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setIsCollapsed(true)}
                className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[color:var(--card-border)] bg-white text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
              >
                <Minus className="h-4 w-4" />
                <span className="sr-only">Colapsar guia</span>
              </button>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[0.68rem] font-bold uppercase",
                  styles.badge,
                )}
              >
                <SeverityIcon className="h-3.5 w-3.5" />
                {guide.severity}
              </span>
              <span className="rounded-full bg-[var(--paper-strong)] px-2.5 py-1 text-[0.68rem] font-bold text-[var(--muted)]">
                Checklist {checklistSummary}
              </span>
            </div>

            <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
              {guide.message}
            </p>

            <ul className="mt-3 grid gap-2">
              {guide.checklist.map((item) => (
                <li
                  key={item.id}
                  className="flex items-start gap-2 rounded-lg bg-[var(--paper-strong)] px-2.5 py-2 text-xs leading-5 text-[var(--foreground)]"
                >
                  <span className="mt-0.5">{checklistIcon(item)}</span>
                  <span>{item.label}</span>
                </li>
              ))}
            </ul>

            {guide.primaryAction || guide.secondaryAction ? (
              <div className="mt-4 flex flex-wrap gap-2">
                {guide.primaryAction ? (
                  <ActionControl action={guide.primaryAction} tone="primary" />
                ) : null}
                {guide.secondaryAction ? (
                  <ActionControl
                    action={guide.secondaryAction}
                    tone="secondary"
                  />
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      </section>
    </aside>
  );
}
