"use client";

import { ArrowRight, CheckCircle2, X } from "lucide-react";

export function AlreadyLoadedModal({
  message,
  onClose,
  planeacionHref,
  title = "Cargue ya registrado",
}: Readonly<{
  message: string;
  onClose: () => void;
  planeacionHref: string;
  title?: string;
}>): React.JSX.Element {
  return (
    <div
      aria-labelledby="already-loaded-title"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4 py-6"
      role="dialog"
    >
      <section className="w-full max-w-xl overflow-hidden rounded-lg border border-[color:var(--card-border)] bg-white shadow-[0_24px_70px_rgba(15,23,42,0.24)]">
        <header className="flex items-start justify-between gap-4 border-b border-[var(--line)] px-5 py-4">
          <div className="flex items-start gap-3">
            <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
              <CheckCircle2 className="h-5 w-5" />
            </span>
            <div>
              <p className="text-xs font-semibold tracking-[0.16em] text-[var(--accent-strong)] uppercase">
                Sin duplicar cargues
              </p>
              <h2
                id="already-loaded-title"
                className="mt-1 text-xl font-semibold text-[var(--foreground)]"
              >
                {title}
              </h2>
            </div>
          </div>
          <button
            type="button"
            aria-label="Cerrar aviso de cargue existente"
            onClick={onClose}
            className="inline-flex min-h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[color:var(--card-border)] bg-white text-[var(--foreground)] transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="px-5 py-4">
          <p className="text-sm leading-6 text-[var(--muted)]">{message}</p>
          <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm leading-6 text-emerald-950">
            No se creara otro wizard para el mismo nombre y codigo. Usa el
            proceso que ya esta cargado y continua con la planeacion pedagogica.
          </div>
        </div>

        <footer className="flex flex-wrap justify-end gap-3 border-t border-[var(--line)] bg-[var(--paper-strong)] px-5 py-4">
          <button
            type="button"
            onClick={onClose}
            className="inline-flex min-h-10 items-center justify-center rounded-lg border border-[color:var(--card-border)] bg-white px-4 py-2 text-sm font-semibold text-[var(--foreground)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            Entendido
          </button>
          <a
            href={planeacionHref}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            Ir a planeacion pedagogica
            <ArrowRight className="h-4 w-4" />
          </a>
        </footer>
      </section>
    </div>
  );
}
