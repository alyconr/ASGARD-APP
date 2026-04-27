import { CheckCircle2, CircleAlert, ClipboardList } from "lucide-react";

import type { ProgramaWizardPayload } from "@/features/programa/types";
import {
  PROGRAMA_REQUIRED_FIELDS,
  validateProgramaBaseField,
  type ProgramaBaseField,
} from "@/features/programa/validation";
import { cn } from "@/lib/utils";

type ProgramaBaseFormValues = ProgramaWizardPayload["programa"];

interface ProgramaBaseFormProps {
  value: ProgramaBaseFormValues;
  onFieldChange: (field: ProgramaBaseField, value: string) => void;
}

const FIELD_COPY: Record<
  ProgramaBaseField,
  {
    label: string;
    description: string;
    placeholder: string;
  }
> = {
  codigo_programa: {
    label: "Codigo del programa",
    description: "Identificador institucional del programa de formacion.",
    placeholder: "Ej. 228118",
  },
  nombre_programa: {
    label: "Nombre del programa",
    description: "Nombre oficial del programa segun la fuente institucional.",
    placeholder: "Ej. Analisis y desarrollo de software",
  },
  version_programa: {
    label: "Version del programa",
    description: "Dato opcional previsto por el modelo para diferenciar versiones.",
    placeholder: "Ej. 102",
  },
};

function ProgramaBaseInput({
  field,
  value,
  onFieldChange,
}: Readonly<{
  field: ProgramaBaseField;
  value: string;
  onFieldChange: (field: ProgramaBaseField, value: string) => void;
}>): React.JSX.Element {
  const copy = FIELD_COPY[field];
  const validation = validateProgramaBaseField(field, value);
  const isRequired = PROGRAMA_REQUIRED_FIELDS.includes(field);
  const isEmpty = value.trim().length === 0;
  const showRequiredHint = isRequired && isEmpty;

  return (
    <label className="block rounded-lg border border-[color:var(--card-border)] bg-white p-4">
      <span className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-semibold text-[var(--foreground)]">
          {copy.label}
        </span>
        {isRequired ? (
          <span className="rounded-md bg-[var(--accent-soft)] px-2 py-1 text-[11px] font-semibold uppercase text-[var(--accent-strong)]">
            Obligatorio
          </span>
        ) : (
          <span className="rounded-md bg-[var(--paper-strong)] px-2 py-1 text-[11px] font-semibold uppercase text-[var(--muted)]">
            Opcional
          </span>
        )}
      </span>
      <span className="mt-1 block text-sm leading-6 text-[var(--muted)]">
        {copy.description}
      </span>
      <input
        value={value}
        onChange={(event) => onFieldChange(field, event.target.value)}
        placeholder={copy.placeholder}
        aria-invalid={!validation.isValid && !isEmpty}
        aria-describedby={`${field}-feedback`}
        className={cn(
          "mt-3 w-full rounded-lg border bg-[var(--paper-strong)] px-3 py-2.5 text-sm font-semibold text-[var(--foreground)] outline-none transition placeholder:font-normal placeholder:text-[var(--muted)]/70 focus:border-[var(--accent)]",
          !validation.isValid && !isEmpty
            ? "border-rose-300"
            : "border-[color:var(--card-border)]",
        )}
      />
      <span
        id={`${field}-feedback`}
        className={cn(
          "mt-2 flex items-center gap-2 text-xs leading-5",
          validation.isValid || isEmpty ? "text-[var(--muted)]" : "text-rose-700",
        )}
      >
        {validation.isValid && !showRequiredHint ? (
          <CheckCircle2 className="h-3.5 w-3.5 text-[var(--accent-strong)]" />
        ) : (
          <CircleAlert className="h-3.5 w-3.5" />
        )}
        {showRequiredHint
          ? "Puedes guardar el borrador incompleto; este dato sera necesario para avanzar en tareas posteriores."
          : validation.message ?? "El valor se guarda automaticamente dentro del borrador activo."}
      </span>
    </label>
  );
}

export function ProgramaBaseForm({
  value,
  onFieldChange,
}: ProgramaBaseFormProps): React.JSX.Element {
  const completedRequiredFields = PROGRAMA_REQUIRED_FIELDS.filter((field) => {
    return value[field].trim().length > 0;
  }).length;

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[var(--accent-strong)]">
            <ClipboardList className="h-5 w-5" />
            <p className="text-xs font-semibold uppercase tracking-[0.16em]">
              TASK-05
            </p>
          </div>
          <h3 className="mt-2 font-[family:var(--font-display)] text-2xl font-semibold text-[var(--foreground)]">
            Datos minimos del programa
          </h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            Captura inicial editable. El formulario admite avance parcial y se
            sincroniza con el borrador existente del wizard.
          </p>
        </div>

        <div className="rounded-lg bg-[var(--paper-strong)] px-4 py-3 text-sm">
          <p className="text-[var(--muted)]">Obligatorios diligenciados</p>
          <p className="mt-1 text-xl font-semibold text-[var(--foreground)]">
            {completedRequiredFields}/{PROGRAMA_REQUIRED_FIELDS.length}
          </p>
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <ProgramaBaseInput
          field="codigo_programa"
          value={value.codigo_programa}
          onFieldChange={onFieldChange}
        />
        <ProgramaBaseInput
          field="version_programa"
          value={value.version_programa}
          onFieldChange={onFieldChange}
        />
      </div>

      <ProgramaBaseInput
        field="nombre_programa"
        value={value.nombre_programa}
        onFieldChange={onFieldChange}
      />
    </div>
  );
}
