"use client";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import {
  BookOpen,
  CheckCircle2,
  ChevronRight,
  Download,
  Lock,
  RefreshCcw,
  Save,
  Trash2,
  Check,
  X,
  Search,
  Info,
  Plus,
} from "lucide-react";
import { toast } from "sonner";

import {
  type PlaneacionContextoResponse,
  type PlaneacionListResponse,
  type PlaneacionResponse,
  type PlaneacionSaveRequest,
  type ContextoCompetencia,
  type ContextoFase,
  type ContextoAsignacionProyecto,
  savePlaneacionBorrador,
  confirmarPlaneacion,
  deletePlaneacion,
  listPlaneacionesProyecto,
  fetchPlaneacionDetalle,
} from "../planeacion-api";
import { WizardGuideAssistant } from "@/features/guide/wizard-guide-assistant";
import { buildPlaneacionWizardGuide } from "@/features/guide/wizard-guide-engine";
import { cn } from "@/lib/utils";
import { useConfirm } from "@/components/feedback/confirm-context";

type StepId = "dashboard" | "curricular" | "complementario" | "preview" | "confirmacion";
type InstructionStep = "curricular" | "complementario";
type ComplementaryFieldId =
  | "actividades_aprendizaje"
  | "duracion_actividad_horas"
  | "horas_trabajo_directo"
  | "horas_trabajo_independiente"
  | "descripcion_evidencia_aprendizaje"
  | "estrategias_didacticas"
  | "ambientes_tipificados"
  | "ambiente"
  | "materiales_formacion"
  | "instructores"
  | "observaciones";

type InstructionTarget =
  | { kind: "step"; step: InstructionStep }
  | { field: ComplementaryFieldId; kind: "field" };

interface ComplementaryFieldDefinition {
  id: ComplementaryFieldId;
  label: string;
  placeholder: string;
  rows?: number;
  type: "number" | "text" | "textarea";
  intro: string;
  preguntate: string;
  reto: string;
  verifica: string;
}

interface StepDefinition {
  id: StepId;
  label: string;
  description: string;
}

const WIZARD_STEPS: StepDefinition[] = [
  { id: "curricular", label: "Estructura Curricular", description: "Vincular fase, actividad y componentes curriculares del RAP" },
  { id: "complementario", label: "Campos Complementarios", description: "Definir estrategias didácticas y recursos de apoyo" },
  { id: "preview", label: "Vista Previa", description: "Revisar la planeación pedagógica del resultado" },
  { id: "confirmacion", label: "Finalizado", description: "Descargar planeación aprobada" },
];

const COMPLEMENTARY_FIELDS: ComplementaryFieldDefinition[] = [
  {
    id: "actividades_aprendizaje",
    label: "Actividades de aprendizaje a desarrollar",
    type: "textarea",
    rows: 5,
    placeholder: "Ejemplo: Determinar la situación actual de la organización mediante...",
    intro:
      "La actividad de aprendizaje debe formularse como una actividad genérica que posteriormente se desarrollará en la guía de aprendizaje a través de subactividades. Para ello, pongamos ahora al aprendiz en acción. ¿Qué hará concretamente para construir y demostrar el aprendizaje esperado?",
    preguntate:
      "¿La acción puede observarse? ¿Sobre qué objeto, problema, proceso o situación trabajará? ¿Bajo qué condición, contexto, recurso o referente deberá realizarla?",
    reto:
      "Redacta la actividad con la estructura verbo en infinitivo + objeto + condición. Procura que integre saber, hacer y ser, y que sea clara, pertinente y medible.",
    verifica:
      "Lee la actividad como si fueras otro instructor: ¿puedes imaginar qué hará el aprendiz? ¿Se relaciona directamente con los resultados? ¿Es coherente con la actividad del proyecto?",
  },
  {
    id: "duracion_actividad_horas",
    label: "Duración de actividad de aprendizaje",
    type: "number",
    placeholder: "Horas totales",
    intro:
      "Ahora demos a la actividad un tiempo realista. Primero pensemos en todo el proceso y después distribuyamos las horas.",
    preguntate:
      "¿Cuánto tiempo requiere orientar, explorar, practicar, producir la evidencia y retroalimentar? ¿Qué parte necesita acompañamiento directo y cuál puede desarrollarse con autonomía?",
    reto:
      "Define la duración total con el equipo ejecutor y distribúyela entre trabajo directo e independiente. No asignes horas únicamente para completar el total disponible.",
    verifica:
      "Comprueba que trabajo directo + trabajo independiente coincidan con la duración total y que el tiempo sea proporcional a la complejidad de los resultados y de la evidencia.",
  },
  {
    id: "horas_trabajo_directo",
    label: "Horas de trabajo directo",
    type: "number",
    placeholder: "Horas con acompañamiento",
    intro: "Identifiquemos qué momentos requieren acompañamiento programado del instructor.",
    preguntate:
      "¿Cuándo necesita el aprendiz orientación, demostración, práctica acompañada, interacción sincrónica, seguimiento o retroalimentación inmediata?",
    reto:
      "Registra las horas en las que instructor y aprendices interactúan de manera programada, presencial o mediada por tecnología, dentro del ambiente de aprendizaje definido.",
    verifica:
      "¿Puedes explicar qué hará el instructor y qué hará el aprendiz durante esas horas? Si solo aparece una cantidad, todavía falta justificarla pedagógicamente.",
  },
  {
    id: "horas_trabajo_independiente",
    label: "Horas de trabajo independiente",
    type: "number",
    placeholder: "Horas autónomas",
    intro:
      "Veamos ahora qué parte del proceso puede desarrollar el aprendiz con autonomía y sin acompañamiento simultáneo.",
    preguntate:
      "¿Qué puede realizar por cuenta propia? ¿Cuenta con instrucciones, recursos, criterios y un resultado esperado? ¿El tiempo asignado es razonable para las condiciones de los aprendices?",
    reto:
      "No reduzcas estas horas a trabajo en casa. Pueden desarrollarse dentro o fuera del centro, siempre que exista una ruta clara y una relación directa con la actividad.",
    verifica:
      "¿El aprendiz sabrá qué debe hacer, para qué, con qué recursos y qué producto o avance se espera? Si alguna respuesta es no, ajusta la orientación.",
  },
  {
    id: "descripcion_evidencia_aprendizaje",
    label: "Descripción de la evidencia de aprendizaje",
    type: "textarea",
    rows: 5,
    placeholder: "Describe qué presentará, ejecutará o responderá el aprendiz.",
    intro:
      "Llegó el momento de comprobar el aprendizaje. Imagina que debes emitir un juicio sustentado sobre lo que el aprendiz alcanzó.",
    preguntate:
      "¿Qué presentará, ejecutará o responderá? ¿La evidencia permite valorar los criterios de evaluación? ¿Demuestra aprendizaje o solamente confirma que participó en una actividad?",
    reto:
      "No confundas actividad con evidencia: la actividad ayuda a aprender; la evidencia permite demostrar lo aprendido. Selecciona conocimiento, desempeño o producto según lo que realmente deba comprobarse.",
    verifica:
      "Haz esta prueba: si solo tuvieras esta evidencia, ¿podrías determinar con objetividad si se alcanzó el resultado? ¿Es observable, verificable y coherente con los criterios?",
  },
  {
    id: "estrategias_didacticas",
    label: "Estrategias Didácticas",
    type: "textarea",
    rows: 5,
    placeholder: "Aprendizaje basado en proyectos, casos, retos, simulaciones...",
    intro: "Ya definimos qué hará el aprendiz. Ahora pensemos cómo vamos a facilitar que aprenda.",
    preguntate:
      "¿Necesita resolver un problema, analizar un caso, desarrollar un proyecto, enfrentar un reto, experimentar, simular o trabajar colaborativamente? ¿Qué estrategia le permitirá asumir un papel activo?",
    reto:
      "No repitas la actividad ni reduzcas la estrategia a una explicación del instructor. Selecciona el camino metodológico que mejor permita alcanzar los resultados en ese contexto.",
    verifica:
      "¿La estrategia lleva al aprendiz a actuar, analizar, decidir, crear, practicar o resolver? ¿Es viable con el tiempo, el ambiente y los recursos disponibles?",
  },
  {
    id: "ambientes_tipificados",
    label: "Ambientes de Aprendizaje Tipificados",
    type: "textarea",
    rows: 4,
    placeholder: "Relaciona ambiente, materiales e instructores como una misma decisión.",
    intro:
      "Ahora vamos a organizar las condiciones que permitirán ejecutar la actividad: el ambiente, los materiales y los instructores deben responder a una misma decisión pedagógica.",
    preguntate:
      "¿Qué escenario requiere la actividad? ¿Con qué recursos debe contar? ¿Qué perfiles de instructores se necesitan para acompañarla y evaluarla?",
    reto:
      "No selecciones estos elementos por separado. Verifica que ambiente, materiales e instructores sean coherentes con la estrategia, la evidencia y las condiciones de seguridad, salud y ambiente.",
    verifica:
      "Imagina la actividad en ejecución: ¿el lugar, los recursos y el equipo humano permiten desarrollarla de principio a fin?",
  },
  {
    id: "ambiente",
    label: "Ambiente",
    type: "textarea",
    rows: 3,
    placeholder: "Aula, taller, laboratorio, empresa, simulador o ambiente virtual.",
    intro:
      "Aterricemos la actividad en un escenario concreto. ¿Dónde podrá el aprendiz realizar lo que has planeado?",
    preguntate:
      "¿Se necesita aula, taller, laboratorio, empresa, unidad productiva, simulador o ambiente virtual? ¿Qué condiciones técnicas, pedagógicas y de seguridad debe ofrecer?",
    reto:
      "Selecciona el ambiente por su pertinencia, no solamente porque esté disponible. Indica el espacio concreto en el que se ejecutará la actividad.",
    verifica:
      "¿Ese ambiente permite realizar la actividad, utilizar la estrategia y producir la evidencia? ¿Otra persona podría ubicarlo o gestionarlo con la información registrada?",
  },
  {
    id: "materiales_formacion",
    label: "Materiales de Formación",
    type: "textarea",
    rows: 4,
    placeholder: "Documentos, insumos, equipos, herramientas, software o recursos digitales.",
    intro:
      "Mira nuevamente la actividad y selecciona únicamente los recursos que realmente harán posible el aprendizaje.",
    preguntate:
      "¿Qué necesita el aprendiz? ¿Qué requiere el instructor? ¿Qué documentos, insumos, equipos, herramientas, software o recursos digitales son indispensables? ¿Están disponibles y en cantidad suficiente?",
    reto:
      "No construyas un inventario general ni selecciones materiales solo porque existen. Cada recurso debe cumplir una función concreta en la actividad.",
    verifica:
      "Revisa cada material: ¿puedes explicar para qué se utilizará? ¿Es compatible con el ambiente y la estrategia? ¿Su disponibilidad está confirmada?",
  },
  {
    id: "instructores",
    label: "Instructores",
    type: "textarea",
    rows: 3,
    placeholder: "Indica quién orienta, acompaña, hace seguimiento o evalúa.",
    intro: "Definamos ahora cómo participará el equipo ejecutor en esta actividad.",
    preguntate:
      "¿Quién orientará cada componente? ¿Quién acompañará la práctica? ¿Quién hará seguimiento o evaluará? ¿Las responsabilidades corresponden con el perfil de cada instructor?",
    reto:
      "No registres nombres sin función. Cuando participen varios instructores, su aporte debe integrar el proceso y evitar fragmentaciones o duplicidades.",
    verifica:
      "¿Cada instructor tiene una responsabilidad clara? ¿Las intervenciones están coordinadas? ¿El aprendiz percibirá una sola ruta formativa?",
  },
  {
    id: "observaciones",
    label: "Observaciones",
    type: "textarea",
    rows: 3,
    placeholder: "Acuerdos, adaptaciones, restricciones, contingencias o decisiones útiles.",
    intro:
      "Antes de cerrar, piensa en quien tendrá que ejecutar esta planeación. ¿Hay una condición importante que todavía no aparece en los demás campos?",
    preguntate:
      "¿Existen acuerdos, adaptaciones, restricciones, contingencias, distribución de grupos, condiciones del ambiente o decisiones metodológicas que puedan afectar la ejecución?",
    reto:
      "Registra solo información nueva y útil. No repitas datos ya consignados ni conviertas este espacio en comentarios generales.",
    verifica:
      "Lee la observación: ¿ayuda a prevenir un problema, tomar una decisión o garantizar la continuidad del proceso? Si no, revisa si realmente es necesaria.",
  },
];

const COMPLEMENTARY_FIELD_MAP = new Map(
  COMPLEMENTARY_FIELDS.map((field) => [field.id, field]),
);

function normalizeTematicas(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.filter((item): item is string => typeof item === "string");
  }
  if (typeof value === "string" && value.trim()) {
    return value
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return [];
}

function getStringValue(record: Record<string, unknown>, ...keys: string[]): string {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string") {
      return value;
    }
  }
  return "";
}

function getNumberValue(record: Record<string, unknown>, ...keys: string[]): number {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "number") {
      return value;
    }
    if (typeof value === "string" && value.trim()) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
  }
  return 0;
}

function formatCodigoVersion(codigo: string, version?: string | null): string {
  return version?.trim() ? `${codigo} / versión ${version}` : codigo;
}

function formatPreviewDate(date: Date): string {
  return date.toLocaleDateString("es-CO", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

export function PlaneacionWizardShell({
  contexto,
  referenciaId,
}: Readonly<{
  contexto: PlaneacionContextoResponse;
  referenciaId: string;
}>): React.JSX.Element {
  const confirm = useConfirm();
  const [activeStep, setActiveStep] = useState<StepId>("dashboard");
  const [planningsList, setPlanningsList] = useState<PlaneacionListResponse[]>([]);
  const [selectedCompId, setSelectedCompId] = useState<string | null>(null);
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);
  const [resultModalCompetenciaId, setResultModalCompetenciaId] = useState<string | null>(null);
  const [activePlanningId, setActivePlanningId] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [fechaPrevisualizacion, setFechaPrevisualizacion] = useState(() =>
    formatPreviewDate(new Date()),
  );
  
  // Form State
  const [faseId, setFaseId] = useState<string>("");
  const [actividadId, setActividadId] = useState<string>("");
  const [proyectoAsignaciones, setProyectoAsignaciones] = useState<
    ContextoAsignacionProyecto[]
  >([]);
  const [selectedConocimientos, setSelectedConocimientos] = useState<string[]>([]);
  const [selectedCriterios, setSelectedCriterios] = useState<string[]>([]);
  
  // Complementarios
  const [actividadesAprendizaje, setActividadesAprendizaje] = useState("");
  const [estrategias, setEstrategias] = useState("");
  const [ambientesTipificados, setAmbientesTipificados] = useState("");
  const [ambiente, setAmbiente] = useState("");
  const [materialesFormacion, setMaterialesFormacion] = useState("");
  const [descripcionEvidencia, setDescripcionEvidencia] = useState("");
  const [observaciones, setObservaciones] = useState("");
  const [duracionHoras, setDuracionHoras] = useState<number>(0);
  const [horasTrabajoDirecto, setHorasTrabajoDirecto] = useState<number>(0);
  const [horasTrabajoIndependiente, setHorasTrabajoIndependiente] = useState<number>(0);
  const [instructores, setInstructores] = useState("");
  const [tematicasSaber, setTematicasSaber] = useState<string[]>([]);
  const [tematicasProceso, setTematicasProceso] = useState<string[]>([]);
  const [nuevaTematicaSaber, setNuevaTematicaSaber] = useState("");
  const [nuevaTematicaProceso, setNuevaTematicaProceso] = useState("");
  const [instructionTarget, setInstructionTarget] = useState<InstructionTarget | null>(null);
  const [readComplementaryFields, setReadComplementaryFields] = useState<Set<ComplementaryFieldId>>(
    () => new Set(),
  );

  // Confirmed details
  const [confirmedPlanning, setConfirmedPlanning] = useState<PlaneacionResponse | null>(null);

  // Search query state
  const [searchQuery, setSearchQuery] = useState("");

  // Filter competencies based on code, name or learning results (RAP)
  const filteredCompetencias = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) {
      return contexto.competencias;
    }
    return contexto.competencias.filter((comp) => {
      const matchCodigo = comp.codigo_competencia.toLowerCase().includes(query);
      const matchNombre = comp.nombre_competencia.toLowerCase().includes(query);
      const matchResultado = comp.resultados.some((res) =>
        res.descripcion.toLowerCase().includes(query)
      );
      return matchCodigo || matchNombre || matchResultado;
    });
  }, [contexto.competencias, searchQuery]);

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

  useEffect(() => {
    if (activeStep === "curricular" || activeStep === "complementario") {
      setInstructionTarget({ kind: "step", step: activeStep });
    }
  }, [activeStep]);

  // Map competence map
  const competenciasMap = useMemo(() => {
    const map = new Map<string, ContextoCompetencia>();
    contexto.competencias.forEach((c) => map.set(c.id, c));
    return map;
  }, [contexto.competencias]);

  const selectedCompetencia = selectedCompId ? competenciasMap.get(selectedCompId) : null;
  const modalCompetencia = resultModalCompetenciaId ? competenciasMap.get(resultModalCompetenciaId) : null;
  const selectedResultado = useMemo(
    () => selectedCompetencia?.resultados.find((resultado) => resultado.id === selectedResultId) ?? null,
    [selectedCompetencia, selectedResultId],
  );

  const planningsByResultado = useMemo(() => {
    const map = new Map<string, PlaneacionListResponse>();
    planningsList.forEach((planning) => map.set(planning.resultado_id, planning));
    return map;
  }, [planningsList]);

  const planningsByCompetencia = useMemo(() => {
    const map = new Map<string, PlaneacionListResponse[]>();
    planningsList.forEach((planning) => {
      const current = map.get(planning.competencia_id) ?? [];
      current.push(planning);
      map.set(planning.competencia_id, current);
    });
    return map;
  }, [planningsList]);

  // Select All toggles
  const allSaberIds = useMemo(() => selectedCompetencia?.conocimientos_saber.map((k) => k.id) ?? [], [selectedCompetencia]);
  const allProcesoIds = useMemo(() => selectedCompetencia?.conocimientos_proceso.map((k) => k.id) ?? [], [selectedCompetencia]);
  const allConocimientosIds = useMemo(() => [...allSaberIds, ...allProcesoIds], [allSaberIds, allProcesoIds]);
  const allCriteriosIds = useMemo(() => selectedCompetencia?.criterios.map((cr) => cr.id) ?? [], [selectedCompetencia]);

  const totalSelectableCount = allConocimientosIds.length + allCriteriosIds.length;
  const totalSelectedCount = selectedConocimientos.length + selectedCriterios.length;

  const isAllSelected = totalSelectableCount > 0 && totalSelectedCount === totalSelectableCount;

  const handleToggleSelectAll = () => {
    if (isAllSelected) {
      setSelectedConocimientos([]);
      setSelectedCriterios([]);
    } else {
      setSelectedConocimientos(allConocimientosIds);
      setSelectedCriterios(allCriteriosIds);
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
    setProyectoAsignaciones([]);
    setSelectedResultId(null);
    setSelectedConocimientos([]);
    setSelectedCriterios([]);
    setActividadesAprendizaje("");
    setEstrategias("");
    setAmbientesTipificados("");
    setAmbiente("");
    setMaterialesFormacion("");
    setDescripcionEvidencia("");
    setObservaciones("");
    setDuracionHoras(0);
    setHorasTrabajoDirecto(0);
    setHorasTrabajoIndependiente(0);
    setInstructores("");
    setTematicasSaber([]);
    setTematicasProceso([]);
    setNuevaTematicaSaber("");
    setNuevaTematicaProceso("");
    setReadComplementaryFields(new Set());
    setActivePlanningId(null);
    setConfirmedPlanning(null);
  };

  const loadPlanningDetails = async (
    planning: PlaneacionListResponse,
    fallbackResultadoId: string,
  ) => {
    setIsLoadingDetails(true);
    try {
      const details = await fetchPlaneacionDetalle(planning.id);
      const resultId = details.resultado_id ?? details.resultados_ids[0] ?? fallbackResultadoId;
      const resultadoContexto = contexto.competencias
        .flatMap((competencia) => competencia.resultados)
        .find((resultado) => resultado.id === resultId);
      const savedAssignments = Array.isArray(
        details.datos_complementarios.asignaciones_proyecto,
      )
        ? (details.datos_complementarios
            .asignaciones_proyecto as ContextoAsignacionProyecto[])
        : [];
      const assignments =
        savedAssignments.length > 0
          ? savedAssignments
          : (resultadoContexto?.asignaciones_proyecto ?? []);
      setActivePlanningId(details.id);
      setSelectedResultId(resultId);
      setProyectoAsignaciones(assignments);
      setFaseId(assignments[0]?.fase_id ?? details.fase_id ?? "");
      setActividadId(assignments[0]?.actividad_id ?? details.actividad_id ?? "");
      setSelectedConocimientos(details.conocimientos_ids);
      setSelectedCriterios(details.criterios_ids);

      const c = details.datos_complementarios;
      setActividadesAprendizaje(getStringValue(c, "actividades_aprendizaje"));
      setEstrategias(getStringValue(c, "estrategias_didacticas"));
      setAmbientesTipificados(getStringValue(c, "ambientes_tipificados"));
      setAmbiente(getStringValue(c, "ambiente", "ambientes_aprendizaje"));
      setMaterialesFormacion(getStringValue(c, "materiales_formacion", "recursos_didacticos"));
      setDescripcionEvidencia(getStringValue(c, "descripcion_evidencia_aprendizaje"));
      setObservaciones(getStringValue(c, "observaciones"));
      setDuracionHoras(getNumberValue(c, "duracion_actividad_horas", "duracion_horas"));
      setHorasTrabajoDirecto(getNumberValue(c, "horas_trabajo_directo"));
      setHorasTrabajoIndependiente(getNumberValue(c, "horas_trabajo_independiente"));
      setInstructores(getStringValue(c, "instructores", "instructor_responsable"));
      setTematicasSaber(normalizeTematicas(c.tematicas_saber));
      setTematicasProceso(normalizeTematicas(c.tematicas_proceso));
      setReadComplementaryFields(new Set(COMPLEMENTARY_FIELDS.map((field) => field.id)));

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
  };

  const handleOpenResultadoModal = (competenciaId: string) => {
    resetForm();
    setSelectedCompId(competenciaId);
    setResultModalCompetenciaId(competenciaId);
  };

  const handleSelectResultado = async (resultadoId: string) => {
    if (!selectedCompId) return;

    const existing = planningsByResultado.get(resultadoId);
    if (existing?.estado === "COMPLETO") {
      toast.info("Este resultado ya tiene una planeacion completa.");
      return;
    }

    resetForm();
    setSelectedCompId(selectedCompId);
    setSelectedResultId(resultadoId);
    const resultado = contexto.competencias
      .find((competencia) => competencia.id === selectedCompId)
      ?.resultados.find((item) => item.id === resultadoId);
    const assignments = resultado?.asignaciones_proyecto ?? [];
    setProyectoAsignaciones(assignments);
    setFaseId(assignments[0]?.fase_id ?? resultado?.fase_id ?? "");
    setActividadId(assignments[0]?.actividad_id ?? resultado?.actividad_id ?? "");
    setResultModalCompetenciaId(null);

    if (existing) {
      await loadPlanningDetails(existing, resultadoId);
      return;
    }

    setActiveStep("curricular");
  };

  // Save current step to DB as a draft
  const handleSaveDraft = async (silent = false): Promise<string | null> => {
    if (!selectedCompId || !selectedResultId) {
      toast.error("Selecciona un resultado de aprendizaje antes de guardar.");
      return null;
    }
    
    setIsSaving(true);
    const payload: PlaneacionSaveRequest = {
      proyecto_id: contexto.proyecto_id,
      competencia_id: selectedCompId,
      resultado_id: selectedResultId,
      fase_id: faseId || null,
      actividad_id: actividadId || null,
      resultados_ids: [selectedResultId],
      conocimientos_ids: selectedConocimientos,
      criterios_ids: selectedCriterios,
      datos_complementarios: {
        actividades_aprendizaje: actividadesAprendizaje,
        duracion_actividad_horas: duracionHoras,
        horas_trabajo_directo: horasTrabajoDirecto,
        horas_trabajo_independiente: horasTrabajoIndependiente,
        descripcion_evidencia_aprendizaje: descripcionEvidencia,
        estrategias_didacticas: estrategias,
        ambientes_tipificados: ambientesTipificados,
        ambiente,
        materiales_formacion: materialesFormacion,
        instructores,
        observaciones,
        ambientes_aprendizaje: ambiente,
        recursos_didacticos: materialesFormacion,
        duracion_horas: duracionHoras,
        instructor_responsable: instructores,
        asignaciones_proyecto: proyectoAsignaciones,
        tematicas_saber: tematicasSaber,
        tematicas_proceso: tematicasProceso,
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
    const confirmed = await confirm({
      title: "Eliminar planeación pedagógica",
      message: "¿Estás seguro de que deseas eliminar esta planeación pedagógica? Esta acción borrará los datos de la base de datos y del almacenamiento físico en MinIO.",
      isDestructive: true,
    });
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

  const addTematica = (
    value: string,
    setValue: React.Dispatch<React.SetStateAction<string>>,
    setItems: React.Dispatch<React.SetStateAction<string[]>>,
  ) => {
    const normalized = value.trim();
    if (!normalized) {
      toast.warning("Escribe una temática antes de adicionarla.");
      return;
    }
    setItems((current) =>
      current.some((item) => item.toLocaleLowerCase() === normalized.toLocaleLowerCase())
        ? current
        : [...current, normalized],
    );
    setValue("");
  };

  const openComplementaryFieldInstruction = (field: ComplementaryFieldId) => {
    setInstructionTarget({ field, kind: "field" });
  };

  const closeInstruction = (markAsRead = false) => {
    if (markAsRead && instructionTarget?.kind === "field") {
      setReadComplementaryFields((current) => {
        const next = new Set(current);
        next.add(instructionTarget.field);
        return next;
      });
    }
    setInstructionTarget(null);
  };

  const getComplementaryFieldValue = (field: ComplementaryFieldId): string | number => {
    switch (field) {
      case "actividades_aprendizaje":
        return actividadesAprendizaje;
      case "duracion_actividad_horas":
        return duracionHoras || "";
      case "horas_trabajo_directo":
        return horasTrabajoDirecto || "";
      case "horas_trabajo_independiente":
        return horasTrabajoIndependiente || "";
      case "descripcion_evidencia_aprendizaje":
        return descripcionEvidencia;
      case "estrategias_didacticas":
        return estrategias;
      case "ambientes_tipificados":
        return ambientesTipificados;
      case "ambiente":
        return ambiente;
      case "materiales_formacion":
        return materialesFormacion;
      case "instructores":
        return instructores;
      case "observaciones":
        return observaciones;
    }
  };

  const updateComplementaryField = (field: ComplementaryFieldId, value: string) => {
    switch (field) {
      case "actividades_aprendizaje":
        setActividadesAprendizaje(value);
        break;
      case "duracion_actividad_horas":
        setDuracionHoras(Number(value) || 0);
        break;
      case "horas_trabajo_directo":
        setHorasTrabajoDirecto(Number(value) || 0);
        break;
      case "horas_trabajo_independiente":
        setHorasTrabajoIndependiente(Number(value) || 0);
        break;
      case "descripcion_evidencia_aprendizaje":
        setDescripcionEvidencia(value);
        break;
      case "estrategias_didacticas":
        setEstrategias(value);
        break;
      case "ambientes_tipificados":
        setAmbientesTipificados(value);
        break;
      case "ambiente":
        setAmbiente(value);
        break;
      case "materiales_formacion":
        setMaterialesFormacion(value);
        break;
      case "instructores":
        setInstructores(value);
        break;
      case "observaciones":
        setObservaciones(value);
        break;
    }
  };

  const getSavedComplementaryValue = (
    record: Record<string, unknown>,
    field: ComplementaryFieldId,
  ): string | number => {
    switch (field) {
      case "actividades_aprendizaje":
        return getStringValue(record, "actividades_aprendizaje");
      case "duracion_actividad_horas":
        return getNumberValue(record, "duracion_actividad_horas", "duracion_horas");
      case "horas_trabajo_directo":
        return getNumberValue(record, "horas_trabajo_directo");
      case "horas_trabajo_independiente":
        return getNumberValue(record, "horas_trabajo_independiente");
      case "descripcion_evidencia_aprendizaje":
        return getStringValue(record, "descripcion_evidencia_aprendizaje");
      case "estrategias_didacticas":
        return getStringValue(record, "estrategias_didacticas");
      case "ambientes_tipificados":
        return getStringValue(record, "ambientes_tipificados");
      case "ambiente":
        return getStringValue(record, "ambiente", "ambientes_aprendizaje");
      case "materiales_formacion":
        return getStringValue(record, "materiales_formacion", "recursos_didacticos");
      case "instructores":
        return getStringValue(record, "instructores", "instructor_responsable");
      case "observaciones":
        return getStringValue(record, "observaciones");
    }
  };

  // Sidebar step rendering
  const currentStepIndex = WIZARD_STEPS.findIndex((s) => s.id === activeStep);
  const guide = buildPlaneacionWizardGuide({
    activeStep,
    competenciasCount: contexto.competencias.length,
    fasesCount: contexto.fases.length,
    selectedCompetencia: selectedCompetencia !== null,
    selectedResultado: selectedResultado !== null,
    faseSelected: faseId.length > 0,
    actividadSelected: actividadId.length > 0,
    conocimientosSelected: selectedConocimientos.length,
    criteriosSelected: selectedCriterios.length,
    instructor: instructores,
    duracionHoras,
    estrategias,
    ambientes: ambiente,
    recursos: materialesFormacion,
    confirmed: confirmedPlanning !== null,
  });
  const activeFieldInstruction =
    instructionTarget?.kind === "field"
      ? (COMPLEMENTARY_FIELD_MAP.get(instructionTarget.field) ?? null)
      : null;

  return (
    <div id="planeacion-step-workspace" className="grid gap-6">
      <WizardGuideAssistant guide={guide} storageKey="planeacion" />
      {/* Header Info */}
      <header className="flex flex-col gap-2 rounded-lg border border-[color:var(--card-border)] bg-white p-5 shadow-[0_14px_32px_rgba(23,53,47,0.06)]">
        <div className="flex items-center gap-2 text-[var(--accent-strong)]">
          <BookOpen className="h-5 w-5" />
          <span className="text-xs font-bold uppercase tracking-wider">Planeación Pedagógica por Resultado</span>
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
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between rounded-lg border border-slate-100 bg-slate-50/50 p-4">
            <div className="max-w-xl">
              <h3 className="text-sm font-semibold text-slate-800 uppercase tracking-wider mb-1">Listado de Competencias del Programa</h3>
              <p className="text-xs text-[var(--muted)] leading-relaxed">
                Selecciona una competencia para elegir el resultado de aprendizaje que tendrá planeación. Los resultados completados quedan desactivados para evitar duplicidad.
              </p>
            </div>

            {/* Barra de Búsqueda de Competencias y Resultados */}
            <div className="relative w-full max-w-sm md:shrink-0">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                <Search className="h-4 w-4 text-slate-400" />
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Buscar competencia o resultado..."
                className="w-full rounded-lg border border-[color:var(--card-border)] bg-white py-2.5 pl-9 pr-9 text-xs placeholder-slate-400 outline-none transition focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)] shadow-sm"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 hover:text-slate-600 transition"
                  title="Limpiar búsqueda"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>

          {isLoadingDetails ? (
            <div className="flex min-h-48 items-center justify-center rounded-lg border border-[color:var(--card-border)] bg-white">
              <div className="flex items-center gap-2 text-[var(--accent-strong)]">
                <RefreshCcw className="h-5 w-5 animate-spin" />
                <p className="text-sm font-semibold">Cargando detalles de la planeación...</p>
              </div>
            </div>
          ) : filteredCompetencias.length === 0 ? (
            <div className="flex flex-col items-center justify-center min-h-[16rem] rounded-lg border border-dashed border-slate-200 bg-white p-6 text-center">
              <div className="rounded-full bg-slate-50 p-3 text-slate-400 mb-3 border border-slate-100">
                <Search className="h-6 w-6" />
              </div>
              <h4 className="text-sm font-semibold text-slate-800">No se encontraron resultados</h4>
              <p className="text-xs text-[var(--muted)] mt-1 max-w-sm">
                No hay competencias ni resultados de aprendizaje que coincidan con &ldquo;{searchQuery}&rdquo;. Intenta con otro término.
              </p>
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                className="mt-4 inline-flex items-center justify-center rounded-lg bg-[var(--accent-soft)] px-3.5 py-2 text-xs font-semibold text-[var(--accent-strong)] hover:bg-[var(--accent)] hover:text-white transition"
              >
                Restablecer Búsqueda
              </button>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {filteredCompetencias.map((comp) => {
                const plannings = planningsByCompetencia.get(comp.id) ?? [];
                const completedCount = plannings.filter((p) => p.estado === "COMPLETO").length;
                const draftCount = plannings.filter((p) => p.estado === "BORRADOR").length;
                const totalResultados = comp.resultados.length;
                const isComplete = totalResultados > 0 && completedCount === totalResultados;
                const isDraft = draftCount > 0;

                // Obtener resultados que coinciden con la búsqueda actual
                const matchingResultados = searchQuery
                  ? comp.resultados.filter((r) =>
                      r.descripcion.toLowerCase().includes(searchQuery.toLowerCase())
                    )
                  : [];

                return (
                  <article
                    key={comp.id}
                    onClick={() => handleOpenResultadoModal(comp.id)}
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
                          {isComplete ? "COMPLETA" : isDraft ? "CON BORRADOR" : "SIN PLANIFICAR"}
                        </span>
                      </div>
                      <h4 className="text-sm font-semibold text-[var(--foreground)] leading-relaxed">
                        {comp.nombre_competencia}
                      </h4>

                      {/* Mostrar los resultados que coinciden con la búsqueda */}
                      {matchingResultados.length > 0 && (
                        <div className="mt-3.5 rounded-lg border border-indigo-100 bg-indigo-50/30 p-3 text-[11px] leading-relaxed">
                          <p className="font-bold text-indigo-700 mb-1.5 uppercase tracking-wider text-[9px] flex items-center gap-1">
                            <span className="h-1.5 w-1.5 rounded-full bg-indigo-500 animate-pulse" />
                            Resultados que coinciden ({matchingResultados.length}):
                          </p>
                          <ul className="list-disc list-inside space-y-1 text-slate-700 font-medium">
                            {matchingResultados.map((r) => (
                              <li key={r.id} className="line-clamp-2">
                                {r.descripcion}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      <div className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-3">
                        <span className="rounded-lg bg-slate-50 px-2.5 py-2 font-semibold">
                          {totalResultados} RAP
                        </span>
                        <span className="rounded-lg bg-emerald-50 px-2.5 py-2 font-semibold text-emerald-700">
                          {completedCount} completos
                        </span>
                        <span className="rounded-lg bg-amber-50 px-2.5 py-2 font-semibold text-amber-700">
                          {draftCount} borradores
                        </span>
                      </div>
                    </div>

                    <div className="mt-5 flex items-center justify-between border-t border-[var(--line)] pt-3">
                      <div className="text-xs font-medium text-[var(--muted)]">
                        {completedCount}/{totalResultados} resultados planeados
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
                        Elegir Resultado
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

      {modalCompetencia && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="resultado-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4 py-6"
        >
          <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-2xl">
            <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-100 bg-white px-5 py-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-[var(--accent-strong)]">
                  {modalCompetencia.codigo_competencia}
                </p>
                <h2 id="resultado-modal-title" className="mt-1 text-lg font-semibold text-slate-900">
                  Elegir resultado de aprendizaje
                </h2>
                <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
                  Cada resultado permite una sola planeacion completa. Los resultados finalizados quedan bloqueados.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setResultModalCompetenciaId(null)}
                className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-900"
                title="Cerrar"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="grid gap-3 p-5">
              {modalCompetencia.resultados.map((resultado, index) => {
                const planning = planningsByResultado.get(resultado.id);
                const isComplete = planning?.estado === "COMPLETO";
                const isDraft = planning?.estado === "BORRADOR";

                return (
                  <div
                    key={resultado.id}
                    className={cn(
                      "grid gap-3 rounded-lg border p-4 sm:grid-cols-[auto_1fr_auto] sm:items-start",
                      isComplete
                        ? "border-emerald-100 bg-emerald-50/60"
                        : isDraft
                        ? "border-amber-100 bg-amber-50/50"
                        : "border-slate-200 bg-white",
                    )}
                  >
                    <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 text-xs font-bold text-slate-700">
                      RAP {index + 1}
                    </span>
                    <div>
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <span
                          className={cn(
                            "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold",
                            isComplete
                              ? "bg-emerald-100 text-emerald-800"
                              : isDraft
                              ? "bg-amber-100 text-amber-800"
                              : "bg-slate-100 text-slate-600",
                          )}
                        >
                          {isComplete && <Lock className="h-3 w-3" />}
                          {isComplete ? "COMPLETO" : isDraft ? "BORRADOR" : "DISPONIBLE"}
                        </span>
                        {planning && !isComplete && (
                          <button
                            type="button"
                            onClick={(event) => void handleDeletePlanning(planning.id, event)}
                            className="inline-flex h-7 w-7 items-center justify-center rounded-lg text-slate-400 hover:bg-rose-50 hover:text-rose-700"
                            title="Eliminar borrador"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                      <p className="text-sm leading-6 text-slate-800">{resultado.descripcion}</p>
                    </div>
                    <button
                      type="button"
                      disabled={isComplete || isLoadingDetails}
                      onClick={() => void handleSelectResultado(resultado.id)}
                      className={cn(
                        "inline-flex min-h-10 items-center justify-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60",
                        isComplete
                          ? "bg-slate-100 text-slate-500"
                          : isDraft
                          ? "bg-amber-100 text-amber-800 hover:bg-amber-200"
                          : "bg-[var(--accent)] text-white hover:bg-[var(--accent-strong)]",
                      )}
                    >
                      {isComplete ? "Bloqueado" : isDraft ? "Editar" : "Iniciar"}
                      {!isComplete && <ChevronRight className="h-4 w-4" />}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
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
              {selectedResultado && (
                <div className="mt-3 rounded-lg border border-slate-100 bg-slate-50 p-3">
                  <p className="mb-1 font-semibold uppercase tracking-wider text-slate-600">Resultado activo</p>
                  <p className="text-slate-800">{selectedResultado.descripcion}</p>
                </div>
              )}
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
                <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--accent-strong)]">
                      Orientación pedagógica
                    </p>
                    <h2 className="mt-1 text-xl font-semibold text-[var(--foreground)]">1. Estructura Curricular y de Proyecto</h2>
                  </div>
                  <button
                    type="button"
                    onClick={() => setInstructionTarget({ kind: "step", step: "curricular" })}
                    className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[var(--accent)] bg-[var(--accent-soft)] px-3 py-2 text-sm font-semibold text-[var(--accent-strong)] hover:bg-white"
                  >
                    <Info className="h-4 w-4" />
                    Instrucciones
                  </button>
                </div>
                
                <div className="grid gap-5">
                  <div>
                    <p className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-700">
                      Fases y actividades del proyecto
                    </p>
                    {proyectoAsignaciones.length > 0 ? (
                      <div className="grid gap-3">
                        {proyectoAsignaciones.map((assignment) => {
                          const fase = faseMap.get(assignment.fase_id);
                          const actividad = fase?.actividades.find(
                            (item) => item.id === assignment.actividad_id,
                          );
                          return (
                            <div
                              key={`${assignment.fase_id}-${assignment.actividad_id}`}
                              className="grid gap-1 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-950 sm:grid-cols-[12rem_1fr]"
                            >
                              <strong>{fase?.nombre_fase ?? "Fase no disponible"}</strong>
                              <span>
                                {actividad?.descripcion ?? "Actividad no disponible"}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
                        El RAP no tiene fases o actividades asociadas en la matriz del
                        proyecto.
                      </div>
                    )}
                  </div>
                  <p className="text-xs text-[var(--muted)]">
                    La fase y la actividad se cargan automáticamente desde la matriz del
                    proyecto al seleccionar el resultado de aprendizaje.
                  </p>

                  {/* Select All Toggle Control Bar */}
                  <div className="flex items-center justify-between border-t border-[var(--line)] pt-4">
                    <div>
                      <h3 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">
                        Contenido Curricular de la Planeacion
                      </h3>
                      <p className="text-xs text-[var(--muted)] mt-0.5">
                        El resultado de aprendizaje ya fue elegido. Agrega los conocimientos y criterios que se abordaran en esta planeacion.
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

                  <div className="border-t border-[var(--line)] pt-4">
                    <h3 className="text-sm font-semibold text-slate-800 uppercase tracking-wider mb-3">Resultado de Aprendizaje activo</h3>
                    <div className="rounded-lg border border-[var(--accent)] bg-[var(--accent-soft)]/20 p-4">
                      <p className="text-sm leading-6 text-slate-800">
                        {selectedResultado?.descripcion ?? "Resultado no seleccionado"}
                      </p>
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
                    <div className="mt-4">
                      <label htmlFor="tematicas-saber" className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-700">
                        Temáticas adicionales de conceptos y principios
                      </label>
                      <div className="flex flex-col gap-2 sm:flex-row">
                        <input
                          id="tematicas-saber"
                          value={nuevaTematicaSaber}
                          onChange={(event) => setNuevaTematicaSaber(event.target.value)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter") {
                              event.preventDefault();
                              addTematica(
                                nuevaTematicaSaber,
                                setNuevaTematicaSaber,
                                setTematicasSaber,
                              );
                            }
                          }}
                          placeholder="Escribe una temática complementaria."
                          className="min-h-10 flex-1 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
                        />
                        <button
                          type="button"
                          onClick={() =>
                            addTematica(
                              nuevaTematicaSaber,
                              setNuevaTematicaSaber,
                              setTematicasSaber,
                            )
                          }
                          className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white hover:bg-[var(--accent-strong)]"
                        >
                          <Plus className="h-4 w-4" />
                          Adicionar temática
                        </button>
                      </div>
                      {tematicasSaber.length > 0 && (
                        <ul className="mt-3 grid gap-2">
                          {tematicasSaber.map((tematica) => (
                            <li
                              key={tematica}
                              className="flex items-start justify-between gap-3 rounded-lg border border-emerald-100 bg-emerald-50 px-3 py-2 text-sm text-emerald-950"
                            >
                              <span>{tematica}</span>
                              <button
                                type="button"
                                onClick={() =>
                                  setTematicasSaber((items) =>
                                    items.filter((item) => item !== tematica),
                                  )
                                }
                                aria-label={`Eliminar temática ${tematica}`}
                                className="text-emerald-700 hover:text-rose-700"
                              >
                                <X className="h-4 w-4" />
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
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
                    <div className="mt-4">
                      <label htmlFor="tematicas-proceso" className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-700">
                        Temáticas adicionales de proceso
                      </label>
                      <div className="flex flex-col gap-2 sm:flex-row">
                        <input
                          id="tematicas-proceso"
                          value={nuevaTematicaProceso}
                          onChange={(event) => setNuevaTematicaProceso(event.target.value)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter") {
                              event.preventDefault();
                              addTematica(
                                nuevaTematicaProceso,
                                setNuevaTematicaProceso,
                                setTematicasProceso,
                              );
                            }
                          }}
                          placeholder="Escribe una temática procedimental."
                          className="min-h-10 flex-1 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
                        />
                        <button
                          type="button"
                          onClick={() =>
                            addTematica(
                              nuevaTematicaProceso,
                              setNuevaTematicaProceso,
                              setTematicasProceso,
                            )
                          }
                          className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white hover:bg-[var(--accent-strong)]"
                        >
                          <Plus className="h-4 w-4" />
                          Adicionar temática
                        </button>
                      </div>
                      {tematicasProceso.length > 0 && (
                        <ul className="mt-3 grid gap-2">
                          {tematicasProceso.map((tematica) => (
                            <li
                              key={tematica}
                              className="flex items-start justify-between gap-3 rounded-lg border border-emerald-100 bg-emerald-50 px-3 py-2 text-sm text-emerald-950"
                            >
                              <span>{tematica}</span>
                              <button
                                type="button"
                                onClick={() =>
                                  setTematicasProceso((items) =>
                                    items.filter((item) => item !== tematica),
                                  )
                                }
                                aria-label={`Eliminar temática ${tematica}`}
                                className="text-emerald-700 hover:text-rose-700"
                              >
                                <X className="h-4 w-4" />
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
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
                <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--accent-strong)]">
                      Orientación pedagógica
                    </p>
                    <h2 className="mt-1 text-xl font-semibold text-[var(--foreground)]">2. Campos Complementarios</h2>
                  </div>
                  <button
                    type="button"
                    onClick={() => setInstructionTarget({ kind: "step", step: "complementario" })}
                    className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[var(--accent)] bg-[var(--accent-soft)] px-3 py-2 text-sm font-semibold text-[var(--accent-strong)] hover:bg-white"
                  >
                    <Info className="h-4 w-4" />
                    Instrucciones
                  </button>
                </div>
                <p className="text-xs text-amber-700 mb-4 bg-amber-50 border border-amber-100 p-2.5 rounded-lg">
                  💡 <strong>Nota sobre Brecha Documental:</strong> No existe un formato de planeación institucional estricto configurado en este repositorio. Se expone un bloque extensible de campos didácticos recomendados.
                </p>

                <div className="grid gap-4">
                  {COMPLEMENTARY_FIELDS.map((field) => {
                    const hasReadInstruction = readComplementaryFields.has(field.id);
                    const value = getComplementaryFieldValue(field.id);
                    return (
                      <article
                        key={field.id}
                        className="grid gap-3 rounded-lg border border-[color:var(--card-border)] bg-white p-4"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="min-w-0">
                            <label
                              htmlFor={field.id}
                              className="block text-sm font-bold text-slate-800"
                            >
                              {field.label}
                            </label>
                          </div>
                          <div className="flex flex-wrap items-center gap-2">
                            <span
                              className={cn(
                                "inline-flex min-h-8 items-center rounded-lg px-2.5 py-1 text-xs font-semibold",
                                hasReadInstruction
                                  ? "bg-emerald-50 text-emerald-800"
                                  : "bg-amber-50 text-amber-800",
                              )}
                            >
                              {hasReadInstruction ? "Instrucción leída" : "Pendiente de lectura"}
                            </span>
                            <button
                              type="button"
                              onClick={() => openComplementaryFieldInstruction(field.id)}
                              className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-[var(--accent)] bg-[var(--accent-soft)] px-3 py-1.5 text-xs font-semibold text-[var(--accent-strong)] hover:bg-white"
                            >
                              <Info className="h-4 w-4" />
                              Leer instrucción
                            </button>
                          </div>
                        </div>
                        {field.type === "textarea" ? (
                          <textarea
                            id={field.id}
                            value={String(value)}
                            disabled={!hasReadInstruction}
                            onChange={(event) =>
                              updateComplementaryField(field.id, event.target.value)
                            }
                            placeholder={
                              hasReadInstruction
                                ? field.placeholder
                                : "Lee la instrucción para habilitar este campo."
                            }
                            rows={field.rows ?? 3}
                            className="w-full resize-y rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm text-[var(--foreground)] outline-none transition placeholder:text-[var(--muted)]/70 focus:border-[var(--accent)] disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500"
                          />
                        ) : (
                          <input
                            id={field.id}
                            type={field.type}
                            value={value}
                            disabled={!hasReadInstruction}
                            onChange={(event) =>
                              updateComplementaryField(field.id, event.target.value)
                            }
                            placeholder={
                              hasReadInstruction
                                ? field.placeholder
                                : "Lee la instrucción para habilitar este campo."
                            }
                            className="min-h-10 w-full rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm text-[var(--foreground)] outline-none transition placeholder:text-[var(--muted)]/70 focus:border-[var(--accent)] disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500"
                          />
                        )}
                      </article>
                    );
                  })}
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
                          setFechaPrevisualizacion(formatPreviewDate(new Date()));
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
                  <div className="grid gap-4 rounded-lg border border-slate-200 bg-white p-4 text-sm sm:grid-cols-2">
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase">Denominación del Programa de Formación</h4>
                      <p className="mt-1 font-semibold text-slate-800">{contexto.nombre_programa}</p>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase">Fecha de Elaboración</h4>
                      <p className="mt-1 font-semibold text-slate-800">{fechaPrevisualizacion}</p>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase">Código y versión del Programa de Formación</h4>
                      <p className="mt-1 font-semibold text-slate-800">
                        {formatCodigoVersion(contexto.codigo_programa, contexto.version_programa)}
                      </p>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase">Nombre del Proyecto Formativo</h4>
                      <p className="mt-1 font-semibold text-slate-800">
                        {contexto.nombre_proyecto || "No aplica para complementaria"}
                      </p>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase">Código del Proyecto</h4>
                      <p className="mt-1 font-semibold text-slate-800">
                        {contexto.codigo_proyecto
                          ? formatCodigoVersion(contexto.codigo_proyecto, contexto.version_proyecto)
                          : "No aplica para complementaria"}
                      </p>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase">Nombre del Instructor</h4>
                      <p className="mt-1 font-semibold text-slate-800">{instructores || "No asignado"}</p>
                    </div>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2 text-sm">
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase">Competencia</h4>
                      <p className="mt-1 font-semibold">{selectedCompetencia.codigo_competencia} - {selectedCompetencia.nombre_competencia}</p>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-500 uppercase">Instructores</h4>
                      <p className="mt-1 font-semibold">{instructores || "No asignado"}</p>
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
                    <h4 className="text-xs font-bold text-slate-500 uppercase mb-2">Resultado de Aprendizaje</h4>
                    <p className="text-sm leading-6 text-slate-700">
                      {selectedResultado?.descripcion ?? "Resultado no seleccionado"}
                    </p>
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
                    {tematicasSaber.length > 0 && (
                      <ul className="mt-3 list-disc rounded-lg bg-slate-100 py-3 pl-8 pr-3 text-sm text-slate-700">
                        {tematicasSaber.map((tematica) => (
                          <li key={tematica}>{tematica}</li>
                        ))}
                      </ul>
                    )}
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
                    {tematicasProceso.length > 0 && (
                      <ul className="mt-3 list-disc rounded-lg bg-slate-100 py-3 pl-8 pr-3 text-sm text-slate-700">
                        {tematicasProceso.map((tematica) => (
                          <li key={tematica}>{tematica}</li>
                        ))}
                      </ul>
                    )}
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
                    {COMPLEMENTARY_FIELDS.map((field) => (
                      <div key={field.id}>
                        <h4 className="text-xs font-bold text-slate-500 uppercase mb-1">{field.label}</h4>
                        <p className="whitespace-pre-wrap">
                          {String(getComplementaryFieldValue(field.id) || "No detallado")}
                        </p>
                      </div>
                    ))}
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
                    Los datos curriculares y de planeación del resultado de aprendizaje han sido validados, aprobados e integrados. El archivo JSON definitivo se ha guardado en el Object Storage MinIO.
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
                            <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider">Instructores</span>
                            <p className="mt-1 font-semibold text-slate-800">
                              {getStringValue(
                                confirmedPlanning.datos_complementarios,
                                "instructores",
                                "instructor_responsable",
                              ) || "No asignado"}
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
                            <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider">Duración de actividad</span>
                            <p className="mt-1 font-semibold text-slate-800">
                              {getNumberValue(
                                confirmedPlanning.datos_complementarios,
                                "duracion_actividad_horas",
                                "duracion_horas",
                              )
                                ? `${getNumberValue(
                                    confirmedPlanning.datos_complementarios,
                                    "duracion_actividad_horas",
                                    "duracion_horas",
                                  )} Horas`
                                : "No asignado"}
                            </p>
                          </div>
                        </div>

                        {/* Resultados de Aprendizaje */}
                        <div className="border-b border-slate-100 pb-4">
                          <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                            Resultado de Aprendizaje Planeado
                          </span>
                          <p className="text-sm leading-6 text-slate-700">
                            {selectedCompetencia.resultados.find((r) => r.id === confirmedPlanning.resultado_id)?.descripcion ??
                              confirmedPlanning.resultado_descripcion ??
                              "Resultado no disponible"}
                          </p>
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
                            {normalizeTematicas(
                              confirmedPlanning.datos_complementarios.tematicas_saber,
                            ).map((tematica) => (
                              <p
                                key={tematica}
                                className="mt-2 rounded-lg bg-slate-50 p-3 text-sm text-slate-700"
                              >
                                {tematica}
                              </p>
                            ))}
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
                            {normalizeTematicas(
                              confirmedPlanning.datos_complementarios.tematicas_proceso,
                            ).map((tematica) => (
                              <p
                                key={tematica}
                                className="mt-2 rounded-lg bg-slate-50 p-3 text-sm text-slate-700"
                              >
                                {tematica}
                              </p>
                            ))}
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
                          {COMPLEMENTARY_FIELDS.map((field) => (
                            <div key={field.id}>
                              <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
                                {field.label}
                              </span>
                              <p className="whitespace-pre-wrap text-slate-700 bg-slate-50 p-3 rounded-lg border border-slate-100">
                                {String(
                                  getSavedComplementaryValue(
                                    confirmedPlanning.datos_complementarios,
                                    field.id,
                                  ) || "No detallado",
                                )}
                              </p>
                            </div>
                          ))}
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
                      Planificar Otro Resultado
                    </button>
                  </div>
                </div>
              </section>
            )}
          </div>
        </section>
      )}

      {instructionTarget !== null && (
        <div
          role="presentation"
          className="fixed inset-0 z-50 grid place-items-center bg-slate-950/55 p-4 backdrop-blur-sm"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeInstruction();
            }
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="planning-instructions-title"
            className="w-full max-w-2xl overflow-hidden rounded-2xl border border-emerald-100 bg-white shadow-2xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-emerald-100 bg-emerald-50 px-6 py-5">
              <div className="flex gap-3">
                <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-700 text-white">
                  <Info className="h-5 w-5" />
                </span>
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-700">
                    Orientación pedagógica
                  </p>
                  <h2 id="planning-instructions-title" className="mt-1 text-xl font-bold text-slate-900">
                    Instrucciones antes de agregar información
                  </h2>
                  {activeFieldInstruction !== null ? (
                    <p className="mt-1 text-sm font-semibold text-emerald-800">
                      {activeFieldInstruction.label}
                    </p>
                  ) : null}
                </div>
              </div>
              <button
                type="button"
                onClick={() => closeInstruction()}
                aria-label="Cerrar instrucciones"
                className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 hover:bg-white hover:text-slate-900"
              >
                <X className="h-5 w-5" />
              </button>
            </header>

            <div className="grid gap-5 px-6 py-6 text-sm leading-6 text-slate-700">
              {activeFieldInstruction !== null ? (
                <p>{activeFieldInstruction.intro}</p>
              ) : instructionTarget.kind === "step" && instructionTarget.step === "curricular" ? (
                <p>
                  Vamos a iniciar la planeación pedagógica específica. Este es el
                  momento de transformar los resultados de aprendizaje en una ruta
                  formativa que pueda ejecutarse.
                </p>
              ) : (
                <p>
                  Llegamos a los campos que convierten las decisiones pedagógicas en
                  condiciones reales de ejecución. Vamos a completarlos sin perder de
                  vista el aprendizaje que buscamos.
                </p>
              )}
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <h3 className="font-bold text-slate-900">Pregúntate:</h3>
                <p className="mt-1">
                  {activeFieldInstruction !== null ? (
                    activeFieldInstruction.preguntate
                  ) : instructionTarget.kind === "step" && instructionTarget.step === "curricular" ? (
                    <>
                      ¿Tienes claros los resultados de aprendizaje, los conocimientos
                      del saber y de proceso, y los criterios de evaluación que vas a
                      integrar? ¿Reconoces la fase y la actividad del proyecto a las
                      que responderá la planeación?
                    </>
                  ) : (
                    <>
                      ¿Cada dato que vas a registrar se relaciona con la actividad de
                      aprendizaje? ¿Refleja los acuerdos del equipo ejecutor y las
                      condiciones reales del centro?
                    </>
                  )}
                </p>
              </div>
              <div>
                <h3 className="font-bold text-slate-900">Tu reto:</h3>
                <p className="mt-1">
                  {activeFieldInstruction !== null ? (
                    activeFieldInstruction.reto
                  ) : instructionTarget.kind === "step" && instructionTarget.step === "curricular" ? (
                    <>
                      No comiences por una lista de temas. Empieza por definir qué
                      debe lograr el aprendiz y cómo ese logro aporta al proyecto
                      formativo.
                    </>
                  ) : (
                    <>
                      Evita diligenciar estos campos como una lista independiente.
                      Ambiente, materiales, instructores, tiempo y evidencia deben
                      funcionar como un conjunto.
                    </>
                  )}
                </p>
              </div>
              <div className="rounded-xl border-l-4 border-amber-400 bg-amber-50 p-4">
                <h3 className="font-bold text-amber-950">Antes de continuar, verifica:</h3>
                <p className="mt-1 text-amber-950">
                  {activeFieldInstruction !== null ? (
                    activeFieldInstruction.verifica
                  ) : instructionTarget.kind === "step" && instructionTarget.step === "curricular" ? (
                    <>
                      Explícalo en una frase: ¿qué aprendizaje debe alcanzar el
                      aprendiz en esta parte del proceso? Si todavía no es claro,
                      revisa los referentes antes de continuar.
                    </>
                  ) : (
                    <>
                      Antes de avanzar, imagina que otro instructor recibe esta
                      planeación: ¿podría ejecutarla sin tener que adivinar
                      información?
                    </>
                  )}
                </p>
              </div>
            </div>

            <footer className="flex justify-end border-t border-slate-100 px-6 py-4">
              <button
                type="button"
                onClick={() => closeInstruction(true)}
                className="inline-flex min-h-10 items-center justify-center rounded-lg bg-[var(--accent)] px-5 py-2 text-sm font-semibold text-white hover:bg-[var(--accent-strong)]"
              >
                Entendido
              </button>
            </footer>
          </section>
        </div>
      )}
    </div>
  );
}
