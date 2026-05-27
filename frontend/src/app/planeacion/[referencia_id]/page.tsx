"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, RefreshCcw } from "lucide-react";

import { fetchPlaneacionContexto, type PlaneacionContextoResponse } from "@/features/planeacion/planeacion-api";
import { PlaneacionWizardShell } from "@/features/planeacion/components/planeacion-wizard-shell";

export default function PlaneacionPage({
  params,
}: {
  params: Promise<{ referencia_id: string }>;
}): React.JSX.Element {
  const { referencia_id } = use(params);
  const [contexto, setContexto] = useState<PlaneacionContextoResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;
    setIsLoading(true);
    setErrorMessage(null);

    void fetchPlaneacionContexto(referencia_id)
      .then((result) => {
        if (isActive) {
          setContexto(result);
        }
      })
      .catch((error: unknown) => {
        if (!isActive) return;
        const msg = error instanceof Error ? error.message : "No fue posible cargar el contexto del programa/proyecto.";
        setErrorMessage(msg);
      })
      .finally(() => {
        if (isActive) {
          setIsLoading(false);
        }
      });

    return () => {
      isActive = false;
    };
  }, [referencia_id]);

  if (isLoading) {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-7xl items-center px-5 py-8">
        <section className="w-full rounded-lg border border-[color:var(--card-border)] bg-white p-8 shadow-[0_18px_42px_rgba(23,53,47,0.08)]">
          <div className="flex items-center gap-3 text-[var(--accent-strong)]">
            <RefreshCcw className="h-5 w-5 animate-spin" />
            <p className="text-sm font-semibold animate-pulse">
              Cargando estructura curricular para planeación pedagógica...
            </p>
          </div>
        </section>
      </main>
    );
  }

  if (errorMessage !== null || contexto === null) {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-5 py-8">
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-6 text-sm leading-6 text-amber-900 shadow-[0_18px_42px_rgba(23,53,47,0.04)]">
          <h2 className="text-lg font-semibold text-amber-950 mb-2">Planificación Pedagógica No Disponible</h2>
          <p>{errorMessage ?? "El módulo se encuentra inaccesible en este momento."}</p>
          <div className="mt-5">
            <Link
              href="/"
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-amber-300 bg-white px-4 py-2 text-sm font-semibold text-amber-950 hover:bg-amber-100 transition"
            >
              <ArrowLeft className="h-4 w-4" />
              Volver al Programa de Formación
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-5 py-6 lg:px-8">
      <div className="self-start">
        <Link
          href={`/proyecto/${referencia_id}`}
          className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-1.5 text-xs font-semibold text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)]"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Volver al Proyecto Formativo
        </Link>
      </div>
      <PlaneacionWizardShell contexto={contexto} referenciaId={referencia_id} />
    </main>
  );
}
