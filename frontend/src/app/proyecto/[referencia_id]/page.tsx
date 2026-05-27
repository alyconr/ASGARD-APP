"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, RefreshCcw } from "lucide-react";

import { ProyectoWizardShell } from "@/features/proyecto/components/proyecto-wizard-shell";
import { consultarDisponibilidadProyecto, ProyectoGateError } from "@/features/proyecto/proyecto-gate-api";
import type { ProyectoDisponibilidadResponse } from "@/features/proyecto/types";

export default function ProyectoPage({
  params,
}: {
  params: Promise<{ referencia_id: string }>;
}): React.JSX.Element {
  const { referencia_id } = use(params);
  const [availability, setAvailability] = useState<ProyectoDisponibilidadResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;
    setIsLoading(true);
    setErrorMessage(null);

    void consultarDisponibilidadProyecto(referencia_id)
      .then((result) => {
        if (isActive) {
          setAvailability(result);
        }
      })
      .catch((error: unknown) => {
        if (!isActive) return;
        if (error instanceof ProyectoGateError && error.disponibilidad !== null) {
          setAvailability(error.disponibilidad);
          setErrorMessage(error.detail);
        } else {
          setErrorMessage("No fue posible validar la disponibilidad del proyecto.");
        }
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
              Validando disponibilidad del proyecto formativo...
            </p>
          </div>
        </section>
      </main>
    );
  }

  if (errorMessage !== null || availability === null || availability.proyecto_bloqueado) {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-5 py-8">
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-6 text-sm leading-6 text-amber-900 shadow-[0_18px_42px_rgba(23,53,47,0.04)]">
          <h2 className="text-lg font-semibold text-amber-950 mb-2">Acceso al Proyecto Formativo Restringido</h2>
          <p>{errorMessage ?? availability?.mensaje ?? "El módulo del proyecto formativo se encuentra bloqueado."}</p>
          <div className="mt-5">
            <Link
              href="/"
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-amber-300 bg-white px-4 py-2 text-sm font-semibold text-amber-950 hover:bg-amber-100 transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
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
          href="/"
          className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-1.5 text-xs font-semibold text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Volver al Programa de Formación
        </Link>
      </div>
      <ProyectoWizardShell availability={availability} />
    </main>
  );
}
