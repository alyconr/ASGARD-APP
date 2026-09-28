import type { ObservacionRevision } from "@/features/planeacion/planeacion-api";
import { cn } from "@/lib/utils";

export function RevisionObservationCard({
  observation,
}: Readonly<{ observation: ObservacionRevision }>): React.JSX.Element {
  return (
    <article className="rounded-xl border border-amber-200 bg-amber-50/70 p-3 text-xs text-slate-700 dark:border-amber-900/60 dark:bg-amber-950/20 dark:text-slate-200">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-bold text-amber-900 dark:text-amber-300">
          Observación pedagógica
        </span>
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-[10px] font-bold uppercase",
            observation.estado === "RESUELTO"
              ? "bg-emerald-100 text-emerald-800"
              : observation.estado === "AJUSTE_REPORTADO"
                ? "bg-sky-100 text-sky-800"
                : "bg-amber-100 text-amber-800",
          )}
        >
          {observation.estado.replaceAll("_", " ")}
        </span>
      </div>
      <p className="mt-2 whitespace-pre-wrap leading-relaxed">{observation.comentario}</p>
      <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">
        {observation.creado_por_nombre} ·{" "}
        {new Date(observation.fecha_creacion).toLocaleString("es-CO")}
      </p>
      {observation.comentario_ajuste && (
        <div className="mt-3 rounded-lg border border-sky-200 bg-sky-50 p-2 text-sky-950 dark:border-sky-900 dark:bg-sky-950/30 dark:text-sky-200">
          <strong>Respuesta del equipo:</strong> {observation.comentario_ajuste}
        </div>
      )}
    </article>
  );
}
