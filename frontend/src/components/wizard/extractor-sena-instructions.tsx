"use client";

import { useEffect, useMemo, useState } from "react";
import { ExternalLink, HelpCircle, X } from "lucide-react";

import { cn } from "@/lib/utils";

const EXTRACTOR_GPT_URL =
  "https://chatgpt.com/g/g-69babd0cd3408191aea277054eb1071d-extractor-sena-de-competencias-y-rap";

type ExtractorScope = "programa" | "proyecto";

const SCOPE_COPY: Record<
  ExtractorScope,
  {
    title: string;
    documentName: string;
    matrixName: string;
    resultName: string;
  }
> = {
  programa: {
    title: "Instrucciones para cargar el programa de formacion",
    documentName: "programa de formacion",
    matrixName: "Matriz de Programa de formacion",
    resultName: "competencias, RAP, conocimientos y criterios",
  },
  proyecto: {
    title: "Instrucciones para cargar el proyecto formativo",
    documentName: "proyecto formativo",
    matrixName: "Matriz Excel del proyecto formativo",
    resultName: "datos del proyecto, fases y actividades",
  },
};

export function ExtractorSenaInstructions({
  className,
  referenceId,
  scope,
}: Readonly<{
  className?: string;
  referenceId: string;
  scope: ExtractorScope;
}>): React.JSX.Element {
  const [isOpen, setIsOpen] = useState(false);
  const copy = SCOPE_COPY[scope];
  const titleId = `sena-extractor-instructions-title-${scope}`;
  const storageKey = useMemo(
    () => `sena-extractor-instructions:${scope}:${referenceId}`,
    [referenceId, scope],
  );

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.localStorage.getItem(storageKey) === "seen") return;
    setIsOpen(true);
  }, [storageKey]);

  const closeAndRemember = (): void => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(storageKey, "seen");
    }
    setIsOpen(false);
  };

  return (
    <section
      className={cn(
        "rounded-lg border border-[var(--accent)] bg-[var(--accent-soft)] px-4 py-3",
        className,
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white text-[var(--accent-strong)]">
            <HelpCircle className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-[var(--foreground)]">
              Antes de cargar la documentacion
            </p>
            <p className="mt-1 text-sm leading-6 text-[var(--muted)]">
              Usa el GPT extractor SENA para preparar la informacion y luego
              carga aqui la matriz validada.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[var(--accent)] bg-white px-3 py-2 text-sm font-semibold text-[var(--accent-strong)] transition hover:bg-white/80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
        >
          <HelpCircle className="h-4 w-4" />
          Instrucciones
        </button>
      </div>

      {isOpen ? (
        <div
          aria-modal="true"
          aria-labelledby={titleId}
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4 py-6"
          role="dialog"
        >
          <section className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-lg border border-[color:var(--card-border)] bg-white shadow-[0_24px_70px_rgba(15,23,42,0.24)]">
            <header className="flex items-start justify-between gap-4 border-b border-[var(--line)] px-5 py-4">
              <div>
                <p className="text-xs font-semibold tracking-[0.16em] text-[var(--accent-strong)] uppercase">
                  Lectura obligatoria
                </p>
                <h2 className="mt-1 text-xl font-semibold text-[var(--foreground)]">
                  <span id={titleId}>
                    {copy.title}
                  </span>
                </h2>
              </div>
              <button
                type="button"
                aria-label="Cerrar instrucciones"
                onClick={closeAndRemember}
                className="inline-flex min-h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[color:var(--card-border)] bg-white text-[var(--foreground)] transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
              >
                <X className="h-4 w-4" />
              </button>
            </header>

            <div className="min-h-0 overflow-y-auto px-5 py-4">
              <p className="text-sm leading-6 text-[var(--muted)]">
                Para cargar correctamente el {copy.documentName}, primero abre
                el GPT especializado. Ese GPT fue disenado para extraer y
                organizar todos los datos y campos requeridos por esta
                plataforma.
              </p>

              <ol className="mt-4 grid gap-3 text-sm leading-6 text-[var(--foreground)]">
                <li className="rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] px-3 py-3">
                  1. Abre el GPT extractor SENA desde el enlace de esta modal.
                </li>
                <li className="rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] px-3 py-3">
                  2. Carga alli el documento del {copy.documentName} y sigue
                  sus instrucciones hasta obtener la informacion estructurada.
                </li>
                <li className="rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] px-3 py-3">
                  3. Descarga o prepara la {copy.matrixName} con {copy.resultName}.
                </li>
                <li className="rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] px-3 py-3">
                  4. Regresa a este wizard, selecciona el Excel, valida el
                  preview y confirma la importacion.
                </li>
              </ol>

              <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-950">
                El PDF se conserva solo como evidencia documental. La matriz
                Excel es la fuente estructurada que se valida e importa para
                poder continuar con la planeacion pedagogica.
              </div>
            </div>

            <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--line)] bg-[var(--paper-strong)] px-5 py-4">
              <a
                href={EXTRACTOR_GPT_URL}
                target="_blank"
                rel="noreferrer"
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[var(--accent)] bg-white px-3 py-2 text-sm font-semibold text-[var(--accent-strong)] transition hover:bg-[var(--accent-soft)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
              >
                Abrir GPT extractor SENA
                <ExternalLink className="h-4 w-4" />
              </a>
              <button
                type="button"
                onClick={closeAndRemember}
                className="inline-flex min-h-10 items-center justify-center rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
              >
                Entendido
              </button>
            </footer>
          </section>
        </div>
      ) : null}
    </section>
  );
}
