import { FileSpreadsheet, Info } from "lucide-react";

import type { ProgramaWizardPayload } from "@/features/programa/types";
import { cn } from "@/lib/utils";

type ProgramaBaseFormValues = ProgramaWizardPayload["programa"];

interface ProgramaBaseInfoProps {
  value: ProgramaBaseFormValues;
}

export function ProgramaBaseInfo({
  value,
}: ProgramaBaseInfoProps): React.JSX.Element {
  const hasData =
    value.codigo_programa.trim().length > 0 ||
    value.nombre_programa.trim().length > 0 ||
    value.version_programa.trim().length > 0;

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[var(--accent-strong)]">
            <FileSpreadsheet className="h-5 w-5" />
            <p className="text-xs font-semibold uppercase tracking-[0.16em]">
              TASK-08.5
            </p>
          </div>
          <h3 className="mt-2 font-[family:var(--font-display)] text-2xl font-semibold text-[var(--foreground)]">
            Origen de los datos del programa
          </h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            Los datos base del programa provienen exclusivamente de la matriz
            Excel canonica. Este paso muestra el resultado de la importacion
            estructurada. Si los datos ya aparecen aqui, provienen del Excel
            cargado en el paso siguiente.
          </p>
        </div>
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">
        <div className="flex items-start gap-2">
          <Info className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-semibold">No existe captura manual del programa</p>
            <p className="mt-1">
              Los campos de codigo, nombre y version del programa se cargan
              unicamente desde la importacion Excel canonica. No hay formulario
              manual de entrada. Si los datos no aparecen aqui, debes cargar o
              corregir la matriz Excel en el paso de origen documental.
            </p>
          </div>
        </div>
      </div>

      {hasData ? (
        <div className="grid gap-3 rounded-lg border border-[color:var(--card-border)] bg-white p-4">
          <p className="text-xs font-semibold tracking-[0.16em] text-[var(--muted)] uppercase">
            Datos detectados en el borrador
          </p>
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-[var(--muted)]">Codigo del programa</dt>
              <dd className="mt-1 font-semibold">
                {value.codigo_programa || "—"}
              </dd>
            </div>
            <div>
              <dt className="text-[var(--muted)]">Version</dt>
              <dd className="mt-1 font-semibold">
                {value.version_programa || "—"}
              </dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-[var(--muted)]">Nombre del programa</dt>
              <dd className="mt-1 font-semibold">
                {value.nombre_programa || "—"}
              </dd>
            </div>
          </dl>
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-[color:var(--card-border)] bg-[var(--paper-strong)] p-6 text-center">
          <p className="text-sm text-[var(--muted)]">
            No se detectaron datos de programa en este borrador. Carga la
            matriz Excel canonica en el paso siguiente para importar la
            estructura curricular.
          </p>
        </div>
      )}
    </div>
  );
}
