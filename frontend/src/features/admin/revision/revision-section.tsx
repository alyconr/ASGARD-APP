import { Plus } from "lucide-react";
import type {
  ObservacionRevision,
  SeccionObservacionPlaneacion,
} from "@/features/planeacion/planeacion-api";
import { RevisionObservationCard } from "./revision-observation-card";

interface RevisionSectionProps {
  title: string;
  sectionKey: SeccionObservacionPlaneacion;
  observations: ObservacionRevision[];
  onAddObservation: (section: SeccionObservacionPlaneacion) => void;
  children: React.ReactNode;
}

export function RevisionSection({
  title,
  sectionKey,
  observations,
  onAddObservation,
  children,
}: Readonly<RevisionSectionProps>): React.JSX.Element {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 bg-slate-50/70 px-5 py-3 dark:border-slate-800 dark:bg-slate-800/40">
        <h3 className="text-xs font-black uppercase tracking-[0.16em] text-slate-700 dark:text-slate-200">
          {title}
        </h3>
        <button
          type="button"
          onClick={() => onAddObservation(sectionKey)}
          className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800 hover:bg-emerald-100 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-300"
        >
          <Plus className="h-3.5 w-3.5" />
          Agregar observación
        </button>
      </header>
      <div className="space-y-4 p-5">
        <div className="text-sm leading-relaxed text-slate-700 dark:text-slate-200">{children}</div>
        {observations.length > 0 && (
          <div className="grid gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
            {observations.map((observation) => (
              <RevisionObservationCard key={observation.id} observation={observation} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
