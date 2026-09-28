import { ArrowLeft, MessageSquarePlus, RefreshCcw } from "lucide-react";
import type {
  PlaneacionRevisionDetalle,
  SeccionObservacionPlaneacion,
} from "@/features/planeacion/planeacion-api";
import { RevisionSection } from "./revision-section";

interface RevisionPlanningViewerProps {
  detail: PlaneacionRevisionDetalle | null;
  loading: boolean;
  error: string | null;
  onBack: () => void;
  onRetry: () => void;
  onAddObservation: (section: SeccionObservacionPlaneacion) => void;
}

function EmptyValue(): React.JSX.Element {
  return <span className="italic text-slate-400">No registrado</span>;
}

export function RevisionPlanningViewer({
  detail,
  loading,
  error,
  onBack,
  onRetry,
  onAddObservation,
}: Readonly<RevisionPlanningViewerProps>): React.JSX.Element {
  if (loading) {
    return (
      <div className="flex min-h-72 items-center justify-center rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <RefreshCcw className="mr-2 h-4 w-4 animate-spin text-emerald-600" />
        <span className="text-xs font-semibold">Cargando planeación…</span>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50/40 p-8 text-center dark:border-rose-900 dark:bg-rose-950/20">
        <p className="text-xs text-rose-800 dark:text-rose-300">{error || "No fue posible cargar la planeación."}</p>
        <div className="mt-4 flex justify-center gap-2">
          <button type="button" onClick={onBack} className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold">Volver al árbol</button>
          <button type="button" onClick={onRetry} className="rounded-lg bg-rose-700 px-3 py-1.5 text-xs font-semibold text-white">Reintentar</button>
        </div>
      </div>
    );
  }

  const observationsFor = (section: SeccionObservacionPlaneacion) =>
    detail.observaciones.filter((observation) => observation.section_key === section);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-950 px-5 py-4 text-white shadow-sm dark:border-slate-700">
        <div>
          <button type="button" onClick={onBack} className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-300 hover:text-emerald-200">
            <ArrowLeft className="h-3.5 w-3.5" /> Volver al árbol
          </button>
          <h2 className="mt-2 text-lg font-black">Planeación Pedagógica</h2>
          <p className="text-xs text-slate-300">Vista de revisión pedagógica · Solo lectura · Entrega v{detail.version_entrega}</p>
        </div>
        <button
          type="button"
          onClick={() => onAddObservation("GENERAL")}
          className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white hover:bg-emerald-500"
        >
          <MessageSquarePlus className="h-4 w-4" />
          Observación general
        </button>
      </div>

      <RevisionSection title="Fase" sectionKey="FASE" observations={observationsFor("FASE")} onAddObservation={onAddObservation}>
        <strong>{detail.fase.nombre}</strong>
      </RevisionSection>

      <RevisionSection title="Actividad de proyecto" sectionKey="ACTIVIDAD_PROYECTO" observations={observationsFor("ACTIVIDAD_PROYECTO")} onAddObservation={onAddObservation}>
        {detail.actividad_proyecto.descripcion || <EmptyValue />}
      </RevisionSection>

      <RevisionSection title="Competencias" sectionKey="COMPETENCIA" observations={observationsFor("COMPETENCIA")} onAddObservation={onAddObservation}>
        {detail.competencias.length > 0 ? (
          <div className="grid gap-2">
            {detail.competencias.map((competence) => (
              <div key={competence.id} className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60">
                <strong>{competence.codigo}</strong> — {competence.nombre}
              </div>
            ))}
          </div>
        ) : <EmptyValue />}
      </RevisionSection>

      <RevisionSection title="Resultados de aprendizaje" sectionKey="RAPS" observations={observationsFor("RAPS")} onAddObservation={onAddObservation}>
        {detail.competencias.some((item) => item.resultados.length > 0) ? (
          <ul className="grid gap-2">
            {detail.competencias.flatMap((competence) =>
              competence.resultados.map((rap) => (
                <li key={rap.id} className="rounded-lg border border-slate-100 p-3 dark:border-slate-800">
                  <strong>{rap.codigo || "RAP"}</strong> — {rap.descripcion}
                </li>
              )),
            )}
          </ul>
        ) : <EmptyValue />}
      </RevisionSection>

      <RevisionSection title="Actividades de aprendizaje" sectionKey="ACTIVIDADES_APRENDIZAJE" observations={observationsFor("ACTIVIDADES_APRENDIZAJE")} onAddObservation={onAddObservation}>
        <p className="whitespace-pre-wrap">{detail.actividades_aprendizaje || <EmptyValue />}</p>
        {detail.descripcion_evidencia && (
          <div className="mt-4 rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60">
            <strong>Evidencia de aprendizaje:</strong>
            <p className="mt-1 whitespace-pre-wrap">{detail.descripcion_evidencia}</p>
          </div>
        )}
      </RevisionSection>

      <RevisionSection title="Saberes" sectionKey="SABERES" observations={observationsFor("SABERES")} onAddObservation={onAddObservation}>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <strong className="text-xs uppercase tracking-wider text-slate-500">Conocimientos de saber</strong>
            {detail.conocimientos_saber.length > 0 ? (
              <ul className="mt-2 list-disc space-y-1 pl-5">{detail.conocimientos_saber.map((item) => <li key={item.id}>{item.descripcion}</li>)}</ul>
            ) : <p className="mt-2"><EmptyValue /></p>}
          </div>
          <div>
            <strong className="text-xs uppercase tracking-wider text-slate-500">Conocimientos de proceso</strong>
            {detail.conocimientos_proceso.length > 0 ? (
              <ul className="mt-2 list-disc space-y-1 pl-5">{detail.conocimientos_proceso.map((item) => <li key={item.id}>{item.descripcion}</li>)}</ul>
            ) : <p className="mt-2"><EmptyValue /></p>}
          </div>
        </div>
      </RevisionSection>

      <RevisionSection title="Criterios de evaluación" sectionKey="CRITERIOS_EVALUACION" observations={observationsFor("CRITERIOS_EVALUACION")} onAddObservation={onAddObservation}>
        {detail.criterios_evaluacion.length > 0 ? (
          <ul className="list-disc space-y-1 pl-5">{detail.criterios_evaluacion.map((item) => <li key={item.id}>{item.descripcion}</li>)}</ul>
        ) : <EmptyValue />}
      </RevisionSection>

      {([
        ["Estrategias didácticas", "ESTRATEGIAS_DIDACTICAS", detail.estrategias_didacticas],
        ["Ambientes", "AMBIENTES", detail.ambientes],
        ["Materiales", "MATERIALES", detail.materiales],
        ["Instructores", "INSTRUCTORES", detail.instructores],
      ] as const).map(([title, key, value]) => (
        <RevisionSection key={key} title={title} sectionKey={key} observations={observationsFor(key)} onAddObservation={onAddObservation}>
          <p className="whitespace-pre-wrap">{value || <EmptyValue />}</p>
        </RevisionSection>
      ))}

      <RevisionSection title="Horas" sectionKey="HORAS" observations={observationsFor("HORAS")} onAddObservation={onAddObservation}>
        <dl className="grid gap-3 sm:grid-cols-3">
          <div><dt className="text-xs uppercase text-slate-500">Directas</dt><dd className="text-xl font-black">{detail.horas.directas}h</dd></div>
          <div><dt className="text-xs uppercase text-slate-500">Independientes</dt><dd className="text-xl font-black">{detail.horas.independientes}h</dd></div>
          <div><dt className="text-xs uppercase text-slate-500">Total</dt><dd className="text-xl font-black text-emerald-700">{detail.horas.total}h</dd></div>
        </dl>
        {detail.observaciones_didacticas && <p className="mt-4 whitespace-pre-wrap border-t border-slate-100 pt-3 dark:border-slate-800">{detail.observaciones_didacticas}</p>}
      </RevisionSection>

      {observationsFor("GENERAL").length > 0 && (
        <RevisionSection title="Observaciones generales" sectionKey="GENERAL" observations={observationsFor("GENERAL")} onAddObservation={onAddObservation}>
          <span className="text-slate-500">Comentarios transversales sobre la planeación.</span>
        </RevisionSection>
      )}

      <div className="flex flex-col gap-3 rounded-2xl border border-emerald-200 bg-emerald-50/70 p-4 sm:flex-row sm:items-center sm:justify-between dark:border-emerald-900 dark:bg-emerald-950/20">
        <div>
          <p className="text-sm font-bold text-slate-900 dark:text-white">¿Terminaste de revisar esta planeación?</p>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
            Regresa al árbol para continuar con las demás planeaciones de la entrega.
          </p>
        </div>
        <button
          type="button"
          onClick={onBack}
          className="inline-flex shrink-0 items-center justify-center gap-1.5 rounded-lg bg-emerald-700 px-4 py-2.5 text-xs font-bold text-white hover:bg-emerald-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Finalizar revisión y volver al árbol
        </button>
      </div>
    </div>
  );
}
