"use client";

import {
  CheckCircle2,
  LockKeyhole,
  RefreshCcw,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import {
  ProyectoGateError,
  consultarDisponibilidadProyecto,
} from "@/features/proyecto/proyecto-gate-api";
import type { ProyectoDisponibilidadResponse } from "@/features/proyecto/types";
import { cn } from "@/lib/utils";
import type { DraftStatus, EstadoDocumentalResponse } from "@/features/drafts/types";

function buildLocalAvailability(
  referenciaId: string,
  programaEstado: DraftStatus,
  programaId: string | null,
): ProyectoDisponibilidadResponse {
  const isComplete = programaEstado === "COMPLETO";
  return {
    referencia_id: referenciaId,
    programa_id: programaId,
    estado_programa: programaEstado,
    programa_completo: isComplete,
    proyecto_bloqueado: !isComplete,
    estado_proyecto: isComplete ? "BORRADOR" : "BLOQUEADO",
    motivo: isComplete ? null : "PROGRAMA_NO_COMPLETO",
    mensaje: isComplete
      ? "El proyecto formativo esta habilitado porque el programa de formación esta COMPLETO. Su cargue usa PDF como evidencia y Excel como fuente estructurada."
      : "El modulo proyecto formativo esta bloqueado hasta que el programa de formación quede cerrado como COMPLETO.",
    accion_sugerida: isComplete
      ? "iniciar_proyecto"
      : "completar_y_cerrar_programa",
  };
}

export function ProyectoDisponibilidadPanel({
  className,
  programaId = null,
  programaEstado,
  referenciaId,
  docState = null,
}: Readonly<{
  className?: string;
  programaId?: string | null;
  programaEstado: DraftStatus;
  referenciaId: string;
  docState?: EstadoDocumentalResponse | null;
}>): React.JSX.Element {
  const fallbackAvailability = useMemo(
    () => buildLocalAvailability(referenciaId, programaEstado, programaId),
    [programaEstado, programaId, referenciaId],
  );
  const [availability, setAvailability] =
    useState<ProyectoDisponibilidadResponse>(fallbackAvailability);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;
    setAvailability(fallbackAvailability);

    if (!referenciaId) {
      return () => {
        isActive = false;
      };
    }

    setIsLoading(true);
    setErrorMessage(null);
    void consultarDisponibilidadProyecto(referenciaId)
      .then((result) => {
        if (isActive) {
          setAvailability(result);
        }
      })
      .catch((error: unknown) => {
        if (!isActive) {
          return;
        }
        if (
          error instanceof ProyectoGateError &&
          error.disponibilidad !== null
        ) {
          setAvailability(error.disponibilidad);
          setErrorMessage(error.detail);
          return;
        }
        setErrorMessage("No fue posible validar el bloqueo del proyecto.");
      })
      .finally(() => {
        if (isActive) {
          setIsLoading(false);
        }
      });

    return () => {
      isActive = false;
    };
  }, [fallbackAvailability, referenciaId, docState]);

  const isBlocked = availability.proyecto_bloqueado;
  const Icon = isBlocked ? LockKeyhole : CheckCircle2;

  return (
    <section
      aria-label="Disponibilidad del modulo proyecto formativo"
      className={cn(
        "rounded-lg border bg-white p-4 shadow-[0_14px_32px_rgba(23,53,47,0.06)]",
        isBlocked ? "border-amber-200" : "border-emerald-200",
        className,
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <span
            className={cn(
              "inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
              isBlocked
                ? "bg-amber-50 text-amber-700"
                : "bg-emerald-50 text-emerald-700",
            )}
          >
            <Icon className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <p className="text-xs font-semibold tracking-[0.16em] text-[var(--muted)] uppercase">
              Modulo proyecto
            </p>
            <h3 className="mt-1 text-lg font-semibold text-[var(--foreground)]">
              {isBlocked
                ? "Modulo proyecto bloqueado"
                : "Modulo proyecto habilitado"}
            </h3>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
              {availability.mensaje}
            </p>
            {errorMessage !== null ? (
              <p className="mt-2 text-sm leading-6 text-amber-800">
                {errorMessage}
              </p>
            ) : null}
          </div>
        </div>

        <span
          className={cn(
            "inline-flex min-h-9 items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold",
            isBlocked
              ? "bg-amber-50 text-amber-800"
              : "bg-emerald-50 text-emerald-800",
          )}
        >
          {isLoading ? (
            <RefreshCcw className="h-4 w-4 animate-spin" />
          ) : (
            <ShieldCheck className="h-4 w-4" />
          )}
          {isBlocked ? "BLOQUEADO" : "LISTO PARA INICIAR"}
        </span>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-[var(--line)] pt-4">
        <p className="text-sm leading-6 text-[var(--muted)]">
          Estado programa:{" "}
          <span className="font-semibold text-[var(--foreground)]">
            {availability.estado_programa ?? "SIN_PROGRAMA"}
          </span>
        </p>
      </div>

      {!isBlocked ? (
        <div className="mt-4 border-t border-[var(--line)] pt-4">
          <Link
            href={`/proyecto/${availability.referencia_id}`}
            aria-label="Wizard base del proyecto formativo"
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-transparent bg-[var(--accent)] px-4 py-2 text-sm font-semibold !text-white transition hover:bg-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            Iniciar wizard del proyecto formativo
          </Link>
        </div>
      ) : null}
    </section>
  );
}
