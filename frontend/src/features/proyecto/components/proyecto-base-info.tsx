import { FileSpreadsheet, Info } from "lucide-react";

import type { ProyectoWizardPayload } from "@/features/proyecto/types";
import { cn } from "@/lib/utils";

type ProyectoBaseInfoValues = ProyectoWizardPayload["proyecto"];

interface ProyectoBaseInfoProps {
  value: ProyectoBaseInfoValues;
}

export function ProyectoBaseInfo({
  value,
}: ProyectoBaseInfoProps): React.JSX.Element {
  const hasData =
    value.codigo_proyecto.trim().length > 0 ||
    value.nombre_proyecto.trim().length > 0 ||
    value.version_proyecto.trim().length > 0;

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[var(--accent-strong)]">
            <FileSpreadsheet className="h-5 w-5" />
            <p className="text-xs font-semibold uppercase tracking-[0.16em]">
              TASK-19
            </p>
          </div>
          <h3 className="mt-2 font-[family:var(--font-display)] text-2xl font-semibold text-[var(--foreground)]">
            Origen de los datos del proyecto
          </h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            Los datos base del proyecto se cargaran desde una fuente estructurada
            tipo Excel/matriz (TASK-19). Este paso muestra el resultado de la
            importacion cuando se ejecute. No existe captura manual de los datos
            base del proyecto.
          </p>
        </div>
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">
        <div className="flex items-start gap-2">
          <Info className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-semibold">No existe captura manual del proyecto</p>
            <p className="mt-1">
              Los campos de codigo, nombre y version del proyecto se cargan
              unicamente desde la importacion de fuente estructurada. No hay
              formulario manual de entrada. Cuando TASK-19 este implementado, el
              usuario cargara la matriz Excel del proyecto en el paso siguiente.
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
              <dt className="text-[var(--muted)]">Codigo del proyecto</dt>
              <dd className="mt-1 font-semibold">
                {value.codigo_proyecto || "—"}
              </dd>
            </div>
            <div>
              <dt className="text-[var(--muted)]">Version</dt>
              <dd className="mt-1 font-semibold">
                {value.version_proyecto || "—"}
              </dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-[var(--muted)]">Nombre del proyecto</dt>
              <dd className="mt-1 font-semibold">
                {value.nombre_proyecto || "—"}
              </dd>
            </div>
          </dl>
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-[color:var(--card-border)] bg-[var(--paper-strong)] p-6 text-center">
          <p className="text-sm text-[var(--muted)]">
            No se detectaron datos de proyecto en este borrador. Cuando TASK-19
            este implementado, podras cargar la matriz Excel del proyecto en el
            paso de fuente del proyecto.
          </p>
        </div>
      )}
    </div>
  );
}
