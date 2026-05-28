"use client";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import {
  BookOpen,
  CheckCircle2,
  ChevronRight,
  Download,
  RefreshCcw,
  Save,
  Trash2,
  Check,
} from "lucide-react";
import { toast } from "sonner";

import {
  type PlaneacionContextoResponse,
  type PlaneacionListResponse,
  type PlaneacionResponse,
  type PlaneacionSaveRequest,
  type ContextoCompetencia,
  type ContextoFase,
  savePlaneacionBorrador,
  confirmarPlaneacion,
  deletePlaneacion,
  listPlaneacionesProyecto,
  fetchPlaneacionDetalle,
} from "../planeacion-api";
import { cn } from "@/lib/utils";

type StepId = "dashboard" | "curricular" | "complementario" | "preview" | "confirmacion";

interface StepDefinition {
  id: StepId;
  label: string;
  description: string;
}

const WIZARD_STEPS: StepDefinition[] = [
  { id: "curricular", label: "Estructura Curricular", description: "Vincular fases, actividades y componentes curriculares" },
  { id: "complementario", label: "Campos Complementarios", description: "Definir estrategias didácticas y recursos de apoyo" },
  { id: "preview", label: "Vista Previa", description: "Revisar la planeación pedagógica de la competencia" },
  { id: "confirmacion", label: "Finalizado", description: "Descargar planeación aprobada" },
];

export function PlaneacionWizardShell({
  contexto,
  referenciaId,
}: Readonly<{
  contexto: PlaneacionContextoResponse;
  referenciaId: string;
}>): React.JSX.Element {
  const [activeStep, setActiveStep] = useState<StepId>("dashboard");
  const [planningsList, setPlanningsList] = useState<PlaneacionListResponse[]>([]);
  const [selectedCompId, setSelectedCompId] = useState<string | null>(null);
  const [activePlanningId, setActivePlanningId] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  
  // Form State
  const [faseId, setFaseId] = useState<string>("");
  const [actividadId, setActividadId] = useState<string>("");
  const [selectedResultados, setSelectedResultados] = useState<string[]>([]);
  const [selectedConocimientos, setSelectedConocimientos] = useState<string[]>([]);
  const [selectedCriterios, setSelectedCriterios] = useState<string[]>([]);
  
  // Complementarios
  const [estrategias, setEstrategias] = useState("");
  const [ambientes, setAmbientes] = useState("");
  const [recursos, setRecursos] = useState("");
  const [duracionHoras, setDuracionHoras] = useState<number>(0);
  const [instructor, setInstructor] = useState("");

  // Confirmed details
  const [confirmedPlanning, setConfirmedPlanning] = useState<PlaneacionResponse | null>(null);

  // Load existing plannings for this project
  const loadPlannings = useCallback(async () => {
    try {
      const list = await listPlaneacionesProyecto(contexto.proyecto_id);
      setPlanningsList(list);
    } catch {
      toast.error("Error al cargar la lista de planeaciones");
    }
  }, [contexto.proyecto_id]);

  useEffect(() => {
    void loadPlannings();
  }, [loadPlannings]);

  // Map competence map
  const competenciasMap = useMemo(() => {
    const map = new Map<string, ContextoCompetencia>();
    contexto.competencias.forEach((c) => map.set(c.id, c));
    return map;
  }, [contexto.competencias]);

  const selectedCompetencia = selectedCompId ? competenciasMap.get(selectedCompId) : null;

  // Select All toggles
  const allResultadosIds = useMemo(() => selectedCompetencia?.resultados.map((r) => r.id) ?? [], [selectedCompetencia]);
  const allSaberIds = useMemo(() => selectedCompetencia?.conocimientos_saber.map((k) => k.id) ?? [], [selectedCompetencia]);
  const allProcesoIds = useMemo(() => selectedCompetencia?.conocimientos_proceso.map((k) => k.id) ?? [], [selectedCompetencia]);
  const allConocimientosIds = useMemo(() => [...allSaberIds, ...allProcesoIds], [allSaberIds, allProcesoIds]);
  const allCriteriosIds = useMemo(() => selectedCompetencia?.criterios.map((cr) => cr.id) ?? [], [selectedCompetencia]);

  const totalSelectableCount = allResultadosIds.length + allConocimientosIds.length + allCriteriosIds.length;
  const totalSelectedCount = selectedResultados.length + selectedConocimientos.length + selectedCriterios.length;

  const isAllSelected = totalSelectableCount > 0 && totalSelectedCount === totalSelectableCount;

  const handleToggleSelectAll = () => {
    if (isAllSelected) {
      setSelectedResultados([]);
      setSelectedConocimientos([]);
      setSelectedCriterios([]);
    } else {
      setSelectedResultados(allResultadosIds);
      setSelectedConocimientos(allConocimientosIds);
      setSelectedCriterios(allCriteriosIds);
    }
  };

  const isAllResultadosSelected = allResultadosIds.length > 0 && selectedResultados.length === allResultadosIds.length;
  const handleToggleAllResultados = () => {
    if (isAllResultadosSelected) {
      setSelectedResultados([]);
    } else {
      setSelectedResultados(allResultadosIds);
    }
  };

  const isAllSaberSelected = allSaberIds.length > 0 && allSaberIds.every((id) => selectedConocimientos.includes(id));
  const handleToggleAllSaber = () => {
    if (isAllSaberSelected) {
      setSelectedConocimientos((prev) => prev.filter((id) => !allSaberIds.includes(id)));
    } else {
      setSelectedConocimientos((prev) => [...new Set([...prev, ...allSaberIds])]);
    }
  };

  const isAllProcesoSelected = allProcesoIds.length > 0 && allProcesoIds.every((id) => selectedConocimientos.includes(id));
  const handleToggleAllProceso = () => {
    if (isAllProcesoSelected) {
      setSelectedConocimientos((prev) => prev.filter((id) => !allProcesoIds.includes(id)));
    } else {
      setSelectedConocimientos((prev) => [...new Set([...prev, ...allProcesoIds])]);
    }
  };

  const isAllCriteriosSelected = allCriteriosIds.length > 0 && selectedCriterios.length === allCriteriosIds.length;
  const handleToggleAllCriterios = () => {
    if (isAllCriteriosSelected) {
      setSelectedCriterios([]);
    } else {
      setSelectedCriterios(allCriteriosIds);
    }
  };

  // Filtered activities based on selected phase
  const faseMap = useMemo(() => {
    const map = new Map<string, ContextoFase>();
    contexto.fases.forEach((f) => map.set(f.id, f));
    return map;
  }, [contexto.fases]);

  const availableActividades = useMemo(() => {
    if (!faseId) return [];
    return faseMap.get(faseId)?.actividades ?? [];
  }, [faseId, faseMap]);

  // Clean form state
  const resetForm = () => {
    setFaseId("");
    setActividadId("");
    setSelectedResultados([]);
    setSelectedConocimientos([]);
    setSelectedCriterios([]);
    setEstrategias("");
    setAmbientes("");
    setRecursos("");
    setDuracionHoras(0);
    setInstructor("");
    setActivePlanningId(null);
    setConfirmedPlanning(null);
  };

  // Start or resume planning for a competence
  const handleStartPlanning = async (competenciaId: string) => {
    resetForm();
    setSelectedCompId(competenciaId);
    
    const existing = planningsList.find((p) => p.competencia_id === competenciaId);
    
    if (existing) {
      setIsLoadingDetails(true);
      try {
        const details = await fetchPlaneacionDetalle(existing.id);
        setActivePlanningId(details.id);
        setFaseId(details.fase_id ?? "");
        setActividadId(details.actividad_id ?? "");
        setSelectedResultados(details.resultados_ids);
        setSelectedConocimientos(details.conocimientos_ids);
        setSelectedCriterios(details.criterios_ids);
        
        // complementarios
        const c = details.datos_complementarios;
        setEstrategias((c.estrategias_didacticas as string) ?? "");
        setAmbientes((c.ambientes_aprendizaje as string) ?? "");
        setRecursos((c.recursos_didacticos as string) ?? "");
        setDuracionHoras((c.duracion_horas as number) ?? 0);
        setInstructor((c.instructor_responsable as string) ?? "");
        
        if (details.estado === "COMPLETO") {
          setConfirmedPlanning(details);
          setActiveStep("confirmacion");
        } else {
          setActiveStep("curricular");
        }
      } catch {
        toast.error("Error al cargar los detalles del borrador");
      } finally {
        setIsLoadingDetails(false);
      }
    } else {
      setActiveStep("curricular");
    }
  };

  // Save current step to DB as a draft
  const handleSaveDraft = async (silent = false): Promise<string | null> => {
    if (!selectedCompId) return null;
    
    setIsSaving(true);
    const payload: PlaneacionSaveRequest = {
      proyecto_id: contexto.proyecto_id,
      competencia_id: selectedCompId,
      fase_id: faseId || null,
      actividad_id: actividadId || null,
      resultados_ids: selectedResultados,
      conocimientos_ids: selectedConocimientos,
      criterios_ids: selectedCriterios,
      datos_complementarios: {
        estrategias_didacticas: estrategias,
        ambientes_aprendizaje: ambientes,
        recursos_didacticos: recursos,
        duracion_horas: duracionHoras,
        instructor_responsable: instructor,
      },
    };

    try {
      const res = await savePlaneacionBorrador(payload);
      setActivePlanningId(res.id);
      await loadPlannings();
      if (!silent) {
        toast.success("Borrador guardado correctamente");
      }
      return res.id;
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Error al guardar el borrador";
      toast.error(msg);
      return null;
    } finally {
      setIsSaving(false);
    }
  };

  // Transition to COMPLETE and generate MinIO link
  const handleConfirmAndApprove = async () => {
    const planningId = activePlanningId || (await handleSaveDraft(true));
    if (!planningId) {
      toast.error("No se pudo guardar la planeación antes de confirmar");
      return;
    }

    setIsSaving(true);
    try {
      const res = await confirmarPlaneacion(planningId);
      setConfirmedPlanning(res);
      await loadPlannings();
      toast.success("Planeación pedagógica aprobada y almacenada en MinIO");
      setActiveStep("confirmacion");
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Error al aprobar la planeación";
      toast.error(msg);
    } finally {
      setIsSaving(false);
    }
  };

  // Delete planning
  const handleDeletePlanning = async (planningId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    const confirmed = window.confirm(
      "¿Estás seguro de que deseas eliminar esta planeación pedagógica? Esta acción borrará los datos del lise de la base de datos y de MinIO."
    );
    if (!confirmed) return;

    try {
      await deletePlaneacion(planningId);
      toast.success("Planeación eliminada");
      await loadPlannings();
      resetForm();
      setActiveStep("dashboard");
    } catch {
      toast.error("Error al eliminar la planeación");
    }
  };

  // Download pedagogical planning file
  const handleDownload = () => {
    if (!confirmedPlanning) return;
    const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
      JSON.stringify(confirmedPlanning.datos_complementarios, null, 2)
    )}`;
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", jsonString);
    downloadAnchor.setAttribute("download", confirmedPlanning.file_name ?? "planeacion.json");
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  // Sidebar step rendering
  const currentStepIndex = WIZARD_STEPS.findIndex((s) => s.id === activeStep);

  return (
    <div className="grid gap-6">
      {/* Header Info */}
      <header className="flex flex-col gap-2 rounded-lg border border-[color:var(--card-border)] bg-white p-5 shadow-[0_14px_32px_rgba(23,53,47,0.06)]">
        <div className="flex items-center gap-2 text-[var(--accent-strong)]">
          <BookOpen className="h-5 w-5" />
          <span className="text-xs font-bold uppercase tracking-wider">Planeación Pedagógica por Competencia</span>
        </div>
        <h1 className="mt-1 text-2xl font-semibold text-[var(--foreground)] sm:text-3xl">
          {contexto.nombre_proyecto}
        </h1>
        <div className="mt-3 grid gap-3 text-sm text-[var(--muted)] sm:grid-cols-3 border-t border-[var(--line)] pt-3">
          <p>
            <span className="font-semibold text-[var(--foreground)]">Programa:</span> {contexto.nombre_programa} ({contexto.codigo_programa})
          </p>
          <p>
            <span className="font-semibold text-[var(--foreground)]">Código Proyecto:</span> {contexto.codigo_proyecto}
          </p>
          <p>
            <span className="font-semibold text-[var(--foreground)]">Ref. Sesión:</span> <code className="text-xs">{referenciaId.slice(0, 8)}...</code>
          </p>
        </div>
      </header>

      {/* DASHBOARD VIEW */}
      {activeStep === "dashboard" && (
        <section className="grid gap-6">
          <div className="rounded-lg border border-slate-100 bg-slate-50/50 p-4">
            <h3 className="text-sm font-semibold text-slate-800 uppercase tracking-wider mb-1">Listado de Competencias del Programa</h3>
            <p className="text-xs text-[var(--muted)] leading-relaxed">
              Selecciona una competencia para construir, editar o visualizar su planeación pedagógica. Las planeaciones completadas quedan guardadas de forma segura sin interferir con las otras competencias.
            </p>
          </div>

          {isLoadingDetails ? (
            <div className="flex min-h-48 items-center justify-center rounded-lg border border-[color:var(--card-border)] bg-white">
              <div className="flex items-center gap-2 text-[var(--accent-strong)]">
                <RefreshCcw className="h-5 w-5 animate-spin" />
                <p className="text-sm font-semibold">Cargando detalles de la planeación...</p>
              </div>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {contexto.competencias.map((comp) => {
                const planning = planningsList.find((p) => p.competencia_id === comp.id);
                const isComplete = planning?.estado === "COMPLETO";
                const isDraft = planning?.estado === "BORRADOR";

                return (
                  <article
                    key={comp.id}
                    onClick={() => void handleStartPlanning(comp.id)}
                    className={cn(
                      "flex flex-col justify-between rounded-lg border p-5 bg-white hover:border-[var(--accent)] hover:shadow-md transition cursor-pointer relative overflow-hidden",
                      isComplete ? "border-emerald-100" : isDraft ? "border-amber-100" : "border-[color:var(--card-border)]"
                    )}
                  >
                    <div>
                      <div className="flex items-start justify-between gap-3 mb-3">
                        <span className="inline-flex rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-mono font-bold text-slate-800">
                          {comp.codigo_competencia}
                        </span>
                        <span
                          className={cn(
                            "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold",
                            isComplete
                              ? "bg-emerald-50 text-emerald-700"
                              : isDraft
                              ? "bg-amber-50 text-amber-700"
                              : "bg-slate-50 text-slate-500"
                          )}
                        >
                          <span className={cn("h-1.5 w-1.5 rounded-full", isComplete ? "bg-emerald-500" : isDraft ? "bg-amber-500" : "bg-slate-400")} />
                          {isComplete ? "COMPLETO" : isDraft ? "BORRADOR" : "SIN PLANIFICAR"}
                        </span>
                      </div>
                      <h4 className="text-sm font-semibold text-[var(--foreground)] leading-relaxed">
                        {comp.nombre_competencia}
                      </h4>
                    </div>

                    <div className="mt-5 flex items-center justify-between border-t border-[var(--line)] pt-3">
                      <div className="flex items-center gap-2">
                        {planning && (
                          <button
                            type="button"
                            onClick={(e) => void handleDeletePlanning(planning.id, e)}
                            className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-rose-50 hover:text-rose-700 transition"
                            title="Eliminar planeación"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                      <button
                        type="button"
                        className={cn(
                          "inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition",
                          isComplete
                            ? "bg-emerald-100/50 text-emerald-800 hover:bg-emerald-100"
                            : isDraft
                            ? "bg-amber-100/50 text-amber-800 hover:bg-amber-100"
                            : "bg-[var(--accent-soft)] text-[var(--accent-strong)] hover:bg-[var(--accent)] hover:text-white"
                        )}
                      >
                        {isComplete ? "Ver Planeación" : isDraft ? "Editar Borrador" : "Iniciar Planeación"}
                        <ChevronRight className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      )}

      {/* WIZARD FLOW */}
      {activeStep !== "dashboard" && selectedCompetencia && (
        <section className="grid gap-5 lg:grid-cols-[20rem_minmax(0,1fr)]">
          {/* Sidebar */}
          <aside className="flex flex-col gap-4 self-start lg:sticky lg:top-6 w-full h-fit">
            <div className="rounded-lg border border-[color:var(--card-border)] bg-white p-4">
              <nav aria-label="Progreso del wizard de planeación" className="grid gap-2">
                {WIZARD_STEPS.map((step, idx) => {
                  const isCurrent = step.id === activeStep;
                  const isPassed = currentStepIndex > idx;
                  return (
                    <button
                      key={step.id}
                      type="button"
                      disabled={idx > currentStepIndex && !confirmedPlanning}
                      onClick={() => setActiveStep(step.id)}
                      className={cn(
                        "grid grid-cols-[2rem_1fr] gap-3 rounded-lg border px-3 py-2.5 text-left transition disabled:opacity-50 disabled:cursor-not-allowed",
                        isCurrent
                          ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                          : "border-transparent bg-white hover:border-[var(--card-border)]"
                      )}
                    >
                      <span
                        className={cn(
                          "inline-flex h-8 w-8 items-center justify-center rounded-lg text-xs font-semibold",
                          isCurrent
                            ? "bg-[var(--accent)] text-white"
                            : isPassed
                            ? "bg-emerald-100 text-emerald-800"
                            : "bg-slate-100 text-slate-400"
                        )}
                      >
                        {isPassed ? <Check className="h-3.5 w-3.5" /> : idx + 1}
                      </span>
                      <div>
                        <span className="block text-xs font-semibold text-[var(--foreground)]">{step.label}</span>
                        <span className="block text-[10px] text-[var(--muted)] truncate max-w-[14rem]">{step.description}</span>
                      </div>
                    </button>
                  );
                })}
              </nav>
            </div>

            <div className="rounded-lg border border-[color:var(--card-border)] bg-white p-4 text-xs leading-5">
              <p className="font-semibold text-[var(--foreground)] uppercase tracking-wider mb-2">Competencia Seleccionada</p>
              <p className="font-mono text-slate-800 font-bold mb-1">{selectedCompetencia.codigo_competencia}</p>
              <p className="text-[var(--muted)] leading-relaxed">{selectedCompetencia.nombre_competencia}</p>
            </div>

            <button
              type="button"
              onClick={() => {
                resetForm();
                setActiveStep("dashboard");
              }}
              className="inline-flex min-h-10 items-center justify-center rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm font-semibold text-[var(--foreground)] hover:border-slate-300 hover:bg-slate-50 transition"
            >
              Cancelar y volver a la lista
            </button>
          </aside>

          {/* Steps Workspaces */}
          <div className="grid gap-4">
            {/* STEP 1: CURRICULAR */}
            {activeStep === "curricular" && (
              <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-6 shadow-sm">
                <h2 className="text-xl font-semibold text-[var(--foreground)] mb-4">1. Estructura Curricular y de Proyecto</h2>
                
                <div className="grid gap-5">
                  {/* Selectores Proyecto */}
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label htmlFor="select-fase" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                        Fase del Proyecto Formativo
                      </label>
                      <select
                        id="select-fase"
                        value={faseId}
                        onChange={(e) => {
                          setFaseId(e.target.value);
                          setActividadId(""); // reset dependent activity
                        }}
                        className="w-full rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--accent)]"
                      >
                        <option value="">-- Selecciona una Fase --</option>
                        {contexto.fases.map((f) => (
                          <option key={f.id} value={f.id}>
                            {f.nombre_fase}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label htmlFor="select-actividad" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                        Actividad del Proyecto
                      </label>
                      <select
                        id="select-actividad"
                        value={actividadId}
                        disabled={!faseId}
                        onChange={(e) => setActividadId(e.target.value)}
                        className="w-full rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--accent)] disabled:bg-slate-50 disabled:opacity-50"
                      >
                        <option value="">-- Selecciona una Actividad --</option>
                        {availableActividades.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.descripcion}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* Select All Toggle Control Bar */}
                  <div className="flex items-center justify-between border-t border-[var(--line)] pt-4">
                    <div>
                      <h3 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">
                        Contenido Curricular de la Competencia
                      </h3>
                      <p className="text-xs text-[var(--muted)] mt-0.5">
                        Selecciona los resultados, conocimientos y criterios que se abordarán en esta planeación.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={handleToggleSelectAll}
                      className={cn(
                        "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold transition shadow-sm cursor-pointer",
                        isAllSelected
                          ? "bg-rose-50 border-rose-200 text-rose-700 hover:bg-rose-100 hover:border-rose-300"
                          : "bg-[var(--accent-soft)] border-[color:var(--card-border)] text-[var(--accent-strong)] hover:bg-[var(--accent)] hover:text-white"
                      )}
                    >
                      {isAllSelected ? "Deseleccionar Todo" : "Seleccionar Todo"}
                    </button>
                  </div>

                  {/* Resultados de Aprendizaje checklist */}
                  <div className="border-t border-[var(--line)] pt-4">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">Resultados de Aprendizaje (RAP) asociados</h3>
                      <button
                        type="button"
                        onClick={handleToggleAllResultados}
                        className="text-xs font-semibold text-[var(--accent-strong)] hover:underline cursor-pointer"
                      >
                        {isAllResultadosSelected ? "Deseleccionar todos" : "Seleccionar todos"}
                      </button>
                    </div>
                    <div className="grid gap-2">
                      {selectedCompetencia.resultados.map((r) => (
                        <label
                          key={r.id}
                          className={cn(
                            "flex items-start gap-3 rounded-lg border p-3 cursor-pointer hover:bg-slate-50 transition",
                            selectedResultados.includes(r.id) ? "border-[var(--accent)] bg-[var(--accent-soft)]/20" : "border-slate-200"
                          )}
                        >
                          <input
                            type="checkbox"
                            checked={selectedResultados.includes(r.id)}
                            onChange={() => {
                              setSelectedResultados((prev) =>
                                prev.includes(r.id) ? prev.filter((id) => id !== r.id) : [...prev, r.id]
                              );
                            }}
                            className="mt-1 h-4 w-4 rounded border-slate-300 text-[var(--accent)] focus:ring-[var(--accent)]"
                          />
                          <span className="text-sm leading-6 text-slate-800">{r.descripcion}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Saberes Saber checklist */}
                  <div className="border-t border-[var(--line)] pt-4">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">Saberes: Conceptos y Principios</h3>
                      <button
                        type="button"
                        onClick={handleToggleAllSaber}
                        className="text-xs font-semibold text-[var(--accent-strong)] hover:underline cursor-pointer"
                      >
                        {isAllSaberSelected ? "Deseleccionar todos" : "Seleccionar todos"}
                      </button>
                    </div>
                    <div className="grid gap-2 max-h-60 overflow-y-auto border border-slate-100 rounded-lg p-3">
                      {selectedCompetencia.conocimientos_saber.map((k) => (
                        <label
                          key={k.id}
                          className="flex items-start gap-3 py-1.5 cursor-pointer text-sm text-slate-700 hover:text-slate-900"
                        >
                          <input
                            type="checkbox"
                            checked={selectedConocimientos.includes(k.id)}
                            onChange={() => {
                              setSelectedConocimientos((prev) =>
                                prev.includes(k.id) ? prev.filter((id) => id !== k.id) : [...prev, k.id]
                              );
                            }}
                            className="mt-0.5 h-4 w-4 rounded border-slate-300 text-[var(--accent)] focus:ring-[var(--accent)]"
                          />
                          <span>{k.descripcion}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Saberes Proceso checklist */}
                  <div className="border-t border-[var(--line)] pt-4">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">Saberes de Proceso</h3>
                      <button
                        type="button"
                        onClick={handleToggleAllProceso}
                        className="text-xs font-semibold text-[var(--accent-strong)] hover:underline cursor-pointer"
                      >
                        {isAllProcesoSelected ? "Deseleccionar todos" : "Seleccionar todos"}
                      </button>
                    </div>
                    <div className="grid gap-2 max-h-60 overflow-y-auto border border-slate-100 rounded-lg p-3">
                      {selectedCompetencia.conocimientos_proceso.map((k) => (
                        <label
                          key={k.id}
                          className="flex items-start gap-3 py-1.5 cursor-pointer text-sm text-slate-700 hover:text-slate-900"
                        >
                          <input
                            type="checkbox"
                            checked={selectedConocimientos.includes(k.id)}
                            onChange={() => {
                              setSelectedConocimientos((prev) =>
                                prev.includes(k.id) ? prev.filter((id) => id !== k.id) : [...prev, k.id]
                              );
                            }}
                            className="mt-0.5 h-4 w-4 rounded border-slate-300 text-[var(--accent)] focus:ring-[var(--accent)]"
                          />
                          <span>{k.descripcion}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Criterios checklist */}
                  <div className="border-t border-[var(--line)] pt-4">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">Criterios de Evaluación</h3>
                      <button
                        type="button"
                        onClick={handleToggleAllCriterios}
                        className="text-xs font-semibold text-[var(--accent-strong)] hover:underline cursor-pointer"
                      >
                        {isAllCriteriosSelected ? "Deseleccionar todos" : "Seleccionar todos"}
                      </button>
                    </div>
                    <div className="grid gap-2 max-h-60 overflow-y-auto border border-slate-100 rounded-lg p-3">
                      {selectedCompetencia.criterios.map((cr) => (
                        <label
                          key={cr.id}
                          className="flex items-start gap-3 py-1.5 cursor-pointer text-sm text-slate-700 hover:text-slate-900"
                        >
                          <input
                            type="checkbox"
                            checked={selectedCriterios.includes(cr.id)}
                            onChange={() => {
                              setSelectedCriterios((prev) =>
                                prev.includes(cr.id) ? prev.filter((id) => id !== cr.id) : [...prev, cr.id]
                              );
                            }}
                            className="mt-0.5 h-4 w-4 rounded border-slate-300 text-[var(--accent)] focus:ring-[var(--accent)]"
                          />
                          <span>{cr.descripcion}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="mt-6 flex justify-end gap-3 border-t border-[var(--line)] pt-4">
                  <button
                    type="button"
                    disabled={isSaving}
                    onClick={() => void handleSaveDraft()}
                    className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-lg border border-[color:var(--card-border)] bg-white px-4 py-2 text-sm font-semibold text-[var(--foreground)] hover:bg-slate-50 transition"
                  >
                    <Save className="h-4 w-4" />
                    Guardar Borrador
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      const savedId = await handleSaveDraft(true);
                      if (savedId) {
                        setActiveStep("complementario");
                      }
                    }}
                    className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-lg bg-[var(--accent)] px-5 py-2 text-sm font-semibold text-white hover:bg-[var(--accent-strong)] transition"
                  >
                    Siguiente
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </section>
            )}

            {/* STEP 2: COMPLEMENTARIO */}
            {activeStep === "complementario" && (
              <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-6 shadow-sm">
                <h2 className="text-xl font-semibold text-[var(--foreground)] mb-2">2. Campos Complementarios</h2>
                <p className="text-xs text-amber-700 mb-4 bg-amber-50 border border-amber-100 p-2.5 rounded-lg">
                  💡 <strong>Nota sobre Brecha Documental:</strong> No existe un formato de planeación institucional estricto configurado en este repositorio. Se expone un bloque extensible de campos didácticos recomendados.
                </p>

                <div className="grid gap-5">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                      Instructor Responsable
                    </label>
                    <input
                      type="text"
                      value={instructor}
                      onChange={(e) => setInstructor(e.target.value)}
                      placeholder="Nombre del instructor a cargo"
                      className="w-full rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--accent)]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                      Duración de Acompañamiento (Horas)
                    </label>
                    <input
                      type="number"
                      value={duracionHoras || ""}
                      onChange={(e) => setDuracionHoras(parseInt(e.target.value) || 0)}
                      placeholder="Número de horas"
                      className="w-full rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--accent)]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                      Estrategias Didácticas Activas
                    </label>
                    <textarea
                      value={estrategias}
                      onChange={(e) => setEstrategias(e.target.value)}
                      placeholder="Actividades de aprendizaje, talleres, simulaciones, etc."
                      rows={4}
                      className="w-full rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--accent)] resize-y"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                      Ambientes de Aprendizaje
                    </label>
                    <textarea
                      value={ambientes}
                      onChange={(e) => setAmbientes(e.target.value)}
                      placeholder="Aulas teóricas, talleres de software, plataformas virtuales, etc."
                      rows={3}
                      className="w-full rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--accent)] resize-y"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                      Recursos Didácticos y Medios
                    </label>
                    <textarea
                      value={recursos}
                      onChange={(e) => setRecursos(e.target.value)}
                      placeholder="Equipos, guías de aprendizaje, computadores, licencias, etc."
                      rows={3}
                      className="w-full rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--accent)] resize-y"
                    />
                  </div>
                </div>

                <div className="mt-6 flex justify-between gap-3 border-t border-[var(--line)] pt-4">
                  <button
                    type="button"
                    onClick={() => setActiveStep("curricular")}
                    className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-lg border border-[color:var(--card-border)] bg-white px-4 py-2 text-sm font-semibold text-[var(--foreground)] hover:bg-slate-50 transition"
                  >
                    Anterior
                  </button>
                  <div className="flex gap-3">
                    <button
                      type="button"
                      disabled={isSaving}
                      onClick={() => void handleSaveDraft()}
                      className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-lg border border-[color:var(--card-border)] bg-white px-4 py-2 text-sm font-semibold text-[var(--foreground)] hover:bg-slate-50 transition"
                    >
                      <Save className="h-4 w-4" />
                      Guardar Borrador
                    </button>
                    <button
                      type="button"
                      onClick={async () => {
                        const savedId = await handleSaveDraft(true);
                        if (savedId) {
                          setActiveStep("preview");
                        }
                      }}
                      className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-lg bg-[var(--accent)] px-5 py-2 text-sm font-semibold text-white hover:bg-[var(--accent-strong)] transition"
                    >
                      Ver Previsualización
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </section>
            )}

            {/* STEP 3: PREVIEW */}
            {activeStep === "preview" && (
              <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-6 shadow-sm">
                <h2 className="text-xl font-semibold text-[var(--foreground)] mb-4">3. Previsualización y Control de Aprobación</h2>

                <div className="grid gap-6 border rounded-lg p-5 bg-slate-50/50">
                  <div className="grid gap-4 sm:grid-cols-2 text-sm">
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase">Competencia</h4>
                      <p className="mt-1 font-semibold">{selectedCompetencia.codigo_competencia} - {selectedCompetencia.nombre_competencia}</p>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase">Instructor</h4>
                      <p className="mt-1 font-semibold">{instructor || "No asignado"}</p>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase">Duración (Horas)</h4>
                      <p className="mt-1 font-semibold">{duracionHoras ? `${duracionHoras} Horas` : "No asignado"}</p>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase">Fase y Actividad</h4>
                      <p className="mt-1 font-semibold">
                        {faseId ? faseMap.get(faseId)?.nombre_fase : "Sin fase"} 
                        {actividadId ? ` / ${availableActividades.find((a) => a.id === actividadId)?.descripcion}` : ""}
                      </p>
                    </div>
                  </div>

                  <div className="border-t pt-4">
                    <h4 className="text-xs font-bold text-slate-500 uppercase mb-2">Resultados de Aprendizaje Seleccionados ({selectedResultados.length})</h4>
                    {selectedResultados.length > 0 ? (
                      <ul className="list-disc pl-5 text-sm text-slate-700 gap-1.5 grid">
                        {selectedCompetencia.resultados
                          .filter((r) => selectedResultados.includes(r.id))
                          .map((r) => (
                            <li key={r.id}>{r.descripcion}</li>
                          ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-rose-600 font-medium">⚠️ Ningún resultado seleccionado</p>
                    )}
                  </div>

                  <div className="border-t pt-4">
                    <h4 className="text-xs font-bold text-slate-500 uppercase mb-2">Saberes de Conceptos y Principios ({selectedConocimientos.filter(id => selectedCompetencia.conocimientos_saber.some(k => k.id === id)).length})</h4>
                    <ul className="list-disc pl-5 text-sm text-slate-700 gap-1 grid">
                      {selectedCompetencia.conocimientos_saber
                        .filter((k) => selectedConocimientos.includes(k.id))
                        .map((k) => (
                          <li key={k.id}>{k.descripcion}</li>
                        ))}
                    </ul>
                  </div>

                  <div className="border-t pt-4">
                    <h4 className="text-xs font-bold text-slate-500 uppercase mb-2">Saberes de Proceso ({selectedConocimientos.filter(id => selectedCompetencia.conocimientos_proceso.some(k => k.id === id)).length})</h4>
                    <ul className="list-disc pl-5 text-sm text-slate-700 gap-1 grid">
                      {selectedCompetencia.conocimientos_proceso
                        .filter((k) => selectedConocimientos.includes(k.id))
                        .map((k) => (
                          <li key={k.id}>{k.descripcion}</li>
                        ))}
                    </ul>
                  </div>

                  <div className="border-t pt-4">
                    <h4 className="text-xs font-bold text-slate-500 uppercase mb-2">Criterios de Evaluación Seleccionados ({selectedCriterios.length})</h4>
                    <ul className="list-disc pl-5 text-sm text-slate-700 gap-1 grid">
                      {selectedCompetencia.criterios
                        .filter((cr) => selectedCriterios.includes(cr.id))
                        .map((cr) => (
                          <li key={cr.id}>{cr.descripcion}</li>
                        ))}
                    </ul>
                  </div>

                  <div className="border-t pt-4 grid gap-3 text-sm text-slate-700">
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase mb-1">Estrategias Didácticas</h4>
                      <p className="whitespace-pre-wrap">{estrategias || "No detallado"}</p>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase mb-1">Ambientes</h4>
                      <p className="whitespace-pre-wrap">{ambientes || "No detallado"}</p>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase mb-1">Recursos</h4>
                      <p className="whitespace-pre-wrap">{recursos || "No detallado"}</p>
                    </div>
                  </div>
                </div>

                <div className="mt-6 flex justify-between gap-3 border-t border-[var(--line)] pt-4">
                  <button
                    type="button"
                    onClick={() => setActiveStep("complementario")}
                    className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-lg border border-[color:var(--card-border)] bg-white px-4 py-2 text-sm font-semibold text-[var(--foreground)] hover:bg-slate-50 transition"
                  >
                    Anterior
                  </button>
                  <button
                    type="button"
                    disabled={isSaving}
                    onClick={() => void handleConfirmAndApprove()}
                    className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-lg bg-emerald-600 px-5 py-2 text-sm font-semibold text-white hover:bg-emerald-700 transition"
                  >
                    Aprobar y Guardar en MinIO
                  </button>
                </div>
              </section>
            )}

            {/* STEP 4: CONFIRMACION */}
            {activeStep === "confirmacion" && (
              <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-6 shadow-sm">
                <div className="flex flex-col items-center justify-center text-center p-8">
                  <div className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 mb-4">
                    <CheckCircle2 className="h-10 w-10" />
                  </div>
                  <h2 className="text-2xl font-bold text-slate-800">¡Planeación Pedagógica Completada!</h2>
                  <p className="mt-2 text-sm text-[var(--muted)] max-w-md">
                    Los datos curriculares y de planeación de la competencia han sido validados, aprobados e integrados. El archivo JSON definitivo se ha guardado en el Object Storage MinIO.
                  </p>

                  <div className="mt-6 w-full max-w-md border rounded-lg bg-slate-50 p-4 text-left text-sm text-slate-700 grid gap-2">
                    <p>
                      <strong className="text-xs font-semibold text-slate-500 uppercase block">Clave en MinIO:</strong>
                      <span className="font-mono text-xs break-all block mt-0.5">{confirmedPlanning?.storage_key}</span>
                    </p>
                    <p>
                      <strong className="text-xs font-semibold text-slate-500 uppercase block">Nombre del Archivo:</strong>
                      <span className="mt-0.5 block">{confirmedPlanning?.file_name}</span>
                    </p>
                    <p>
                      <strong className="text-xs font-semibold text-slate-500 uppercase block">Fecha Generación:</strong>
                      <span className="mt-0.5 block">
                        {confirmedPlanning?.fecha_generacion
                          ? new Date(confirmedPlanning.fecha_generacion).toLocaleString()
                          : "Desconocida"}
                      </span>
                    </p>
                  </div>

                  {/* Resumen Detallado de la Planeación */}
                  {selectedCompetencia && confirmedPlanning && (
                    <div className="mt-8 w-full max-w-3xl text-left border border-slate-200 rounded-xl bg-white shadow-sm overflow-hidden">
                      <div className="bg-slate-50 border-b border-slate-200 px-5 py-4 flex items-center justify-between">
                        <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
                          Detalle de la Planeación Aprobada
                        </h3>
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                          APROBADO
                        </span>
                      </div>

                      <div className="p-6 grid gap-6">
                        {/* Metadatos Generales */}
                        <div className="grid gap-4 sm:grid-cols-2 text-sm border-b border-slate-100 pb-4">
                          <div>
                            <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider">Competencia</span>
                            <p className="mt-1 font-semibold text-slate-800">
                              {selectedCompetencia.codigo_competencia} - {selectedCompetencia.nombre_competencia}
                            </p>
                          </div>
                          <div>
                            <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider">Instructor Responsable</span>
                            <p className="mt-1 font-semibold text-slate-800">
                              {(confirmedPlanning.datos_complementarios.instructor_responsable as string) || "No asignado"}
                            </p>
                          </div>
                          <div>
                            <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider">Fase y Actividad del Proyecto</span>
                            <p className="mt-1 font-semibold text-slate-800">
                              {confirmedPlanning.fase_id ? faseMap.get(confirmedPlanning.fase_id)?.nombre_fase : "Sin fase"}
                              {confirmedPlanning.actividad_id && confirmedPlanning.fase_id
                                ? ` / ${
                                    faseMap.get(confirmedPlanning.fase_id)?.actividades.find(
                                      (a) => a.id === confirmedPlanning.actividad_id
                                    )?.descripcion ?? ""
                                  }`
                                : ""}
                            </p>
                          </div>
                          <div>
                            <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider">Duración de Acompañamiento</span>
                            <p className="mt-1 font-semibold text-slate-800">
                              {confirmedPlanning.datos_complementarios.duracion_horas ? `${confirmedPlanning.datos_complementarios.duracion_horas} Horas` : "No asignado"}
                            </p>
                          </div>
                        </div>

                        {/* Resultados de Aprendizaje */}
                        <div className="border-b border-slate-100 pb-4">
                          <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                            Resultados de Aprendizaje Seleccionados ({confirmedPlanning.resultados_ids.length})
                          </span>
                          {confirmedPlanning.resultados_ids.length > 0 ? (
                            <ul className="list-disc pl-5 text-sm text-slate-700 gap-1.5 grid">
                              {selectedCompetencia.resultados
                                .filter((r) => confirmedPlanning.resultados_ids.includes(r.id))
                                .map((r) => (
                                  <li key={r.id}>{r.descripcion}</li>
                                ))}
                            </ul>
                          ) : (
                            <p className="text-sm text-slate-400 italic">Ninguno seleccionado</p>
                          )}
                        </div>

                        {/* Saberes */}
                        <div className="grid gap-4 sm:grid-cols-2 border-b border-slate-100 pb-4">
                          <div>
                            <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                              Saberes: Conceptos y Principios
                            </span>
                            <ul className="list-disc pl-5 text-sm text-slate-700 gap-1 grid">
                              {selectedCompetencia.conocimientos_saber
                                .filter((k) => confirmedPlanning.conocimientos_ids.includes(k.id))
                                .map((k) => (
                                  <li key={k.id}>{k.descripcion}</li>
                                ))}
                            </ul>
                          </div>
                          <div>
                            <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                              Saberes de Proceso
                            </span>
                            <ul className="list-disc pl-5 text-sm text-slate-700 gap-1 grid">
                              {selectedCompetencia.conocimientos_proceso
                                .filter((k) => confirmedPlanning.conocimientos_ids.includes(k.id))
                                .map((k) => (
                                  <li key={k.id}>{k.descripcion}</li>
                                ))}
                            </ul>
                          </div>
                        </div>

                        {/* Criterios de Evaluación */}
                        <div className="border-b border-slate-100 pb-4">
                          <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                            Criterios de Evaluación Seleccionados ({confirmedPlanning.criterios_ids.length})
                          </span>
                          <ul className="list-disc pl-5 text-sm text-slate-700 gap-1 grid">
                            {selectedCompetencia.criterios
                              .filter((cr) => confirmedPlanning.criterios_ids.includes(cr.id))
                              .map((cr) => (
                                <li key={cr.id}>{cr.descripcion}</li>
                              ))}
                          </ul>
                        </div>

                        {/* Campos Complementarios */}
                        <div className="grid gap-4 text-sm">
                          <div>
                            <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Estrategias Didácticas Activas</span>
                            <p className="whitespace-pre-wrap text-slate-700 bg-slate-50 p-3 rounded-lg border border-slate-100">
                              {(confirmedPlanning.datos_complementarios.estrategias_didacticas as string) || "No detallado"}
                            </p>
                          </div>
                          <div>
                            <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Ambientes de Aprendizaje</span>
                            <p className="whitespace-pre-wrap text-slate-700 bg-slate-50 p-3 rounded-lg border border-slate-100">
                              {(confirmedPlanning.datos_complementarios.ambientes_aprendizaje as string) || "No detallado"}
                            </p>
                          </div>
                          <div>
                            <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Recursos Didácticos y Medios</span>
                            <p className="whitespace-pre-wrap text-slate-700 bg-slate-50 p-3 rounded-lg border border-slate-100">
                              {(confirmedPlanning.datos_complementarios.recursos_didacticos as string) || "No detallado"}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="mt-8 flex flex-col sm:flex-row gap-4 w-full justify-center">
                    <button
                      type="button"
                      onClick={handleDownload}
                      className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-6 py-2.5 text-sm font-semibold text-white hover:bg-[var(--accent-strong)] transition"
                    >
                      <Download className="h-4 w-4" />
                      Descargar Archivo Aprobado
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        resetForm();
                        setActiveStep("dashboard");
                        void loadPlannings();
                      }}
                      className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-6 py-2.5 text-sm font-semibold text-[var(--foreground)] hover:bg-slate-50 transition"
                    >
                      Planificar Otra Competencia
                    </button>
                  </div>
                </div>
              </section>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
