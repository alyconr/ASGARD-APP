import { AlertCircle, BookOpenCheck, RefreshCcw } from "lucide-react";
import type {
  PlaneacionRevisionItem,
  PlaneacionesEntregaList,
} from "@/features/planeacion/planeacion-api";

interface RevisionPlanningTreeProps {
  data: PlaneacionesEntregaList | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  onSelect: (planeacionId: string) => void;
}

interface ActivityGroup {
  key: string;
  label: string;
  order: number;
  items: PlaneacionRevisionItem[];
}

interface PhaseGroup {
  key: string;
  label: string;
  order: number;
  activities: ActivityGroup[];
}

function groupPlannings(items: PlaneacionRevisionItem[]): PhaseGroup[] {
  const phases = new Map<string, PhaseGroup>();
  for (const item of items) {
    const phaseKey = item.fase.id ?? `fase:${item.fase.nombre}`;
    const phase = phases.get(phaseKey) ?? {
      key: phaseKey,
      label: item.fase.nombre,
      order: item.fase.orden ?? Number.MAX_SAFE_INTEGER,
      activities: [],
    };
    const activityKey = item.actividad_proyecto.id ?? `actividad:${item.actividad_proyecto.descripcion}`;
    let activity = phase.activities.find((entry) => entry.key === activityKey);
    if (!activity) {
      activity = {
        key: activityKey,
        label: item.actividad_proyecto.descripcion,
        order: item.actividad_proyecto.orden ?? Number.MAX_SAFE_INTEGER,
        items: [],
      };
      phase.activities.push(activity);
    }
    activity.items.push(item);
    phases.set(phaseKey, phase);
  }
  return [...phases.values()]
    .sort((a, b) => a.order - b.order || a.label.localeCompare(b.label))
    .map((phase) => ({
      ...phase,
      activities: phase.activities.sort(
        (a, b) => a.order - b.order || a.label.localeCompare(b.label),
      ),
    }));
}

export function RevisionPlanningTree({
  data,
  loading,
  error,
  onRetry,
  onSelect,
}: Readonly<RevisionPlanningTreeProps>): React.JSX.Element {
  if (loading) {
    return (
      <div className="flex min-h-52 items-center justify-center rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <RefreshCcw className="mr-2 h-4 w-4 animate-spin text-emerald-600" />
        <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">Cargando planeaciones de la entrega…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-52 flex-col items-center justify-center gap-3 rounded-2xl border border-rose-200 bg-rose-50/40 p-6 text-center dark:border-rose-900 dark:bg-rose-950/20">
        <AlertCircle className="h-6 w-6 text-rose-600" />
        <p className="max-w-lg text-xs text-rose-800 dark:text-rose-300">{error}</p>
        <button type="button" onClick={onRetry} className="rounded-lg bg-rose-700 px-3 py-1.5 text-xs font-semibold text-white">
          Reintentar
        </button>
      </div>
    );
  }

  if (!data || data.total === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900">
        Esta entrega no contiene planeaciones pedagógicas.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
        <span>{data.total} {data.total === 1 ? "planeación congelada" : "planeaciones congeladas"} en la versión {data.version}</span>
        <span>
          <strong>{data.horas_directas_total}h</strong> directas ·{" "}
          <strong>{data.horas_independientes_total}h</strong> independientes
        </span>
      </div>
      {groupPlannings(data.planeaciones).map((phase) => (
        <details key={phase.key} open className="group rounded-2xl border border-slate-200 bg-slate-50/60 p-3 dark:border-slate-800 dark:bg-slate-900/60">
          <summary className="cursor-pointer list-none px-2 py-1 text-sm font-black uppercase tracking-[0.12em] text-slate-800 dark:text-slate-100">
            {phase.label}
          </summary>
          <div className="mt-3 space-y-3">
            {phase.activities.map((activity) => (
              <details key={activity.key} open className="rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900">
                <summary className="cursor-pointer list-none text-xs font-bold text-slate-700 dark:text-slate-200">
                  {activity.label}
                </summary>
                <div className="mt-3 grid gap-3 lg:grid-cols-2">
                  {activity.items.map((planning) => (
                    <article key={planning.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-[11px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">Planeación pedagógica</p>
                          <h4 className="mt-1 line-clamp-2 text-sm font-bold text-slate-900 dark:text-white">
                            {planning.actividades_aprendizaje || "Actividad de aprendizaje sin título"}
                          </h4>
                        </div>
                        <BookOpenCheck className="h-5 w-5 shrink-0 text-emerald-600" />
                      </div>
                      <div className="mt-3 space-y-1 text-xs text-slate-600 dark:text-slate-300">
                        <p><strong>Competencias:</strong> {planning.competencias.map((item) => item.codigo).join(", ") || "Sin datos"}</p>
                        <p><strong>RAP:</strong> {planning.raps.map((item) => item.codigo || item.descripcion).join(", ") || "Sin datos"}</p>
                        <p><strong>Horas:</strong> {planning.horas.directas} directas · {planning.horas.independientes} independientes</p>
                        <p><strong>Observaciones:</strong> {planning.observaciones_count}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => onSelect(planning.id)}
                        className="mt-4 w-full rounded-lg bg-emerald-700 px-3 py-2 text-xs font-bold text-white hover:bg-emerald-800"
                      >
                        Revisar planeación
                      </button>
                    </article>
                  ))}
                </div>
              </details>
            ))}
          </div>
        </details>
      ))}
    </div>
  );
}
