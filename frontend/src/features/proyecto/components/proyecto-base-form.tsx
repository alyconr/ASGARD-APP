import { CheckCircle2, CircleAlert, ClipboardList } from "lucide-react";

import type { ProyectoWizardPayload } from "@/features/proyecto/types";
import {
  PROYECTO_REQUIRED_FIELDS,
  validateProyectoBaseField,
  type ProyectoBaseField,
} from "@/features/proyecto/validation";
import { cn } from "@/lib/utils";

type ProyectoBaseFormValues = ProyectoWizardPayload["proyecto"];

interface ProyectoBaseFormProps {
  value: ProyectoBaseFormValues;
  onFieldChange: (field: ProyectoBaseField, value: string) => void;
}

const FIELD_COPY: Record<
  ProyectoBaseField,
  {
    label: string;
    description: string;
    placeholder: string;
  }
> = {
  codigo_proyecto: {
    label: "Codigo del proyecto",
    description: "Identificador institucional del proyecto formativo.",
    placeholder: "Ej. 2273651",
  },
  nombre_proyecto: {
    label: "Nombre del proyecto",
    description: "Nombre oficial del proyecto que se trabajara en la guia.",
    placeholder: "Ej. Sistema de informacion para gestion academica",
  },
  version_proyecto: {
    label: "Version del proyecto",
    description: "Version vigente del proyecto formativo asociado al programa.",
    placeholder: "Ej. 1",
  },
};

function ProyectoBaseInput({
  field,
  onFieldChange,
  value,
}: Readonly<{
  field: ProyectoBaseField;
  onFieldChange: (field: ProyectoBaseField, value: string) => void;
  value: string;
}>): React.JSX.Element {
  const copy = FIELD_COPY[field];
  const validation = validateProyectoBaseField(field, value);
  const isEmpty = value.trim().length === 0;

  return (
    <label className="block rounded-lg border border-[color:var(--card-border)] bg-white p-4">
      <span className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-semibold text-[var(--foreground)]">
          {copy.label}
        </span>
        <span className="rounded-md bg-[var(--accent-soft)] px-2 py-1 text-[11px] font-semibold text-[var(--accent-strong)] uppercase">
          Obligatorio
        </span>
      </span>
      <span className="mt-1 block text-sm leading-6 text-[var(--muted)]">
        {copy.description}
      </span>
      <input
        value={value}
        onChange={(event) => onFieldChange(field, event.target.value)}
        placeholder={copy.placeholder}
        aria-invalid={!validation.isValid}
        aria-describedby={`${field}-feedback`}
        className={cn(
          "mt-3 w-full rounded-lg border bg-[var(--paper-strong)] px-3 py-2.5 text-sm font-semibold text-[var(--foreground)] outline-none transition placeholder:font-normal placeholder:text-[var(--muted)]/70 focus:border-[var(--accent)]",
          validation.isValid
            ? "border-[color:var(--card-border)]"
            : "border-rose-300",
        )}
      />
      <span
        id={`${field}-feedback`}
        className={cn(
          "mt-2 flex items-center gap-2 text-xs leading-5",
          validation.isValid ? "text-[var(--muted)]" : "text-rose-700",
        )}
      >
        {validation.isValid && !isEmpty ? (
          <CheckCircle2 className="h-3.5 w-3.5 text-[var(--accent-strong)]" />
        ) : (
          <CircleAlert className="h-3.5 w-3.5" />
        )}
        {validation.message ??
          "El valor se guarda automaticamente dentro del borrador PROYECTO."}
      </span>
    </label>
  );
}

export function ProyectoBaseForm({
  onFieldChange,
  value,
}: ProyectoBaseFormProps): React.JSX.Element {
  const completedRequiredFields = PROYECTO_REQUIRED_FIELDS.filter((field) => {
    return value[field].trim().length > 0;
  }).length;

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[var(--accent-strong)]">
            <ClipboardList className="h-5 w-5" />
            <p className="text-xs font-semibold tracking-[0.16em] uppercase">
              TASK-17
            </p>
          </div>
          <h3 className="mt-2 text-2xl font-[family:var(--font-display)] font-semibold text-[var(--foreground)]">
            Datos minimos del proyecto
          </h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            Captura inicial editable del proyecto formativo. El avance se
            sincroniza con el borrador PROYECTO activo.
          </p>
        </div>

        <div className="rounded-lg bg-[var(--paper-strong)] px-4 py-3 text-sm">
          <p className="text-[var(--muted)]">Obligatorios diligenciados</p>
          <p className="mt-1 text-xl font-semibold text-[var(--foreground)]">
            {completedRequiredFields}/{PROYECTO_REQUIRED_FIELDS.length}
          </p>
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <ProyectoBaseInput
          field="codigo_proyecto"
          value={value.codigo_proyecto}
          onFieldChange={onFieldChange}
        />
        <ProyectoBaseInput
          field="version_proyecto"
          value={value.version_proyecto}
          onFieldChange={onFieldChange}
        />
      </div>

      <ProyectoBaseInput
        field="nombre_proyecto"
        value={value.nombre_proyecto}
        onFieldChange={onFieldChange}
      />
    </div>
  );
}
