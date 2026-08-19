import type { DraftStatus } from "@/features/drafts/types";
import type {
  ProgramaWizardPayload,
  ProgramaWizardStepId,
} from "@/features/programa/types";
import type {
  ProyectoDisponibilidadResponse,
  ProyectoWizardPayload,
  ProyectoWizardStepId,
} from "@/features/proyecto/types";

export type WizardGuideSeverity = "info" | "warning" | "blocked" | "success";

export type WizardGuideChecklistStatus = "done" | "pending" | "current";

export interface WizardGuideChecklistItem {
  id: string;
  label: string;
  status: WizardGuideChecklistStatus;
}

export interface WizardGuideAction {
  label: string;
  href?: string;
  targetId?: string;
}

export interface WizardGuideState {
  wizard: "programa" | "proyecto" | "planeacion";
  severity: WizardGuideSeverity;
  eyebrow: string;
  title: string;
  message: string;
  checklist: WizardGuideChecklistItem[];
  primaryAction?: WizardGuideAction;
  secondaryAction?: WizardGuideAction;
}

interface ProgramaGuideInput {
  activeReferenceId: string | null;
  currentStepId: ProgramaWizardStepId;
  draftStatus: DraftStatus;
  isWizardActive: boolean;
  payload: ProgramaWizardPayload | null;
}

interface ProyectoGuideInput {
  activeReferenceId: string | null;
  availability: ProyectoDisponibilidadResponse;
  currentStepId: ProyectoWizardStepId;
  draftStatus: DraftStatus;
  isWizardActive: boolean;
  payload: ProyectoWizardPayload | null;
}

export type PlaneacionGuideStepId =
  | "dashboard"
  | "curricular"
  | "complementario"
  | "preview"
  | "confirmacion";

interface PlaneacionGuideInput {
  activeStep: PlaneacionGuideStepId;
  competenciasCount: number;
  fasesCount: number;
  selectedCompetencia: boolean;
  selectedResultado: boolean;
  faseSelected: boolean;
  actividadSelected: boolean;
  conocimientosSelected: number;
  criteriosSelected: number;
  instructor: string;
  duracionHoras: number;
  estrategias: string;
  ambientes: string;
  recursos: string;
  confirmed: boolean;
  officialMissing?: string[];
  hoursMatch?: boolean;
  existingPlanningsCount?: number;
}

function item(
  id: string,
  label: string,
  done: boolean,
  current = false,
): WizardGuideChecklistItem {
  return {
    id,
    label,
    status: done ? "done" : current ? "current" : "pending",
  };
}

function hasText(value: string): boolean {
  return value.trim().length > 0;
}

export function buildProgramaWizardGuide({
  activeReferenceId,
  currentStepId,
  draftStatus,
  isWizardActive,
  payload,
}: ProgramaGuideInput): WizardGuideState {
  const excel = payload?.documental.programa_excel ?? null;
  const previewValid = excel?.preview?.valid === true;
  const imported = excel?.confirmacion.estado === "IMPORTADO";
  const hasCompetencias = (payload?.curricular.competencias.length ?? 0) > 0;
  const complete = draftStatus === "COMPLETO";

  if (!isWizardActive || payload === null) {
    return {
      wizard: "programa",
      severity: "info",
      eyebrow: "Guia ASGARD",
      title: "Inicia o recupera un programa",
      message:
        "Crea una referencia estable o recupera un borrador para cargar la matriz canonica del programa.",
      checklist: [
        item("referencia", "Referencia de borrador activa", activeReferenceId !== null, true),
        item("excel", "Matriz Excel validada", false),
        item("cierre", "Programa cerrado como COMPLETO", false),
      ],
      primaryAction: { label: "Usar matriz Excel", targetId: "programa-step-workspace" },
    };
  }

  if (complete) {
    return {
      wizard: "programa",
      severity: "success",
      eyebrow: "Programa listo",
      title: "Proyecto formativo habilitado",
      message:
        "El programa ya esta COMPLETO. El siguiente modulo puede abrirse con las reglas reales del backend.",
      checklist: [
        item("excel", "Matriz Excel importada", imported),
        item("curricular", "Estructura curricular disponible", hasCompetencias),
        item("cierre", "Cierre humano confirmado", true),
      ],
      primaryAction: activeReferenceId
        ? {
            label: "Abrir proyecto",
            href: `/proyecto/${activeReferenceId}`,
          }
        : undefined,
    };
  }

  if (currentStepId === "revision-programa") {
    return {
      wizard: "programa",
      severity: imported ? "warning" : "blocked",
      eyebrow: "Revision del programa",
      title: imported ? "Falta cerrar el programa" : "Importacion pendiente",
      message: imported
        ? "Revisa el consolidado y confirma el cierre para marcar el programa como COMPLETO."
        : "La revision solo debe cerrarse despues de validar e importar la matriz Excel canonica.",
      checklist: [
        item("preview", "Preview valido de matriz", previewValid),
        item("import", "Importacion confirmada", imported),
        item("close", "Programa en estado COMPLETO", complete, imported),
      ],
      primaryAction: {
        label: imported ? "Cerrar programa" : "Volver al origen",
        targetId: "programa-step-workspace",
      },
    };
  }

  return {
    wizard: "programa",
    severity: imported ? "success" : previewValid ? "warning" : "info",
    eyebrow: "Origen documental",
    title: imported
      ? "Matriz importada"
      : previewValid
        ? "Confirma la importacion"
        : "Valida la matriz canonica",
    message: imported
      ? "La estructura del programa ya fue materializada. Avanza a la revision y cierre."
      : previewValid
        ? "El preview es valido; confirma la importacion para crear la estructura curricular."
        : "Carga la matriz de programa y revisa que el preview quede valido antes de avanzar.",
    checklist: [
      item("preview", "Preview valido", previewValid, !previewValid),
      item("import", "Importacion confirmada", imported, previewValid && !imported),
      item("review", "Revision y cierre pendientes", complete),
    ],
    primaryAction: imported
      ? { label: "Ir a revision", targetId: "programa-step-workspace" }
      : undefined,
  };
}

export function buildProyectoWizardGuide({
  activeReferenceId,
  availability,
  currentStepId,
  draftStatus,
  isWizardActive,
  payload,
}: ProyectoGuideInput): WizardGuideState {
  if (availability.proyecto_bloqueado || !availability.programa_completo) {
    return buildBlockedModuleGuide(
      "proyecto",
      "Proyecto bloqueado",
      availability.mensaje ||
        "Debes cerrar el programa de formacion como COMPLETO antes de iniciar el proyecto formativo.",
      "Volver al dashboard",
      "/",
    );
  }

  const excel = payload?.documental.fuente_estructurada ?? null;
  const previewValid = excel?.preview?.valid === true;
  const imported = excel?.confirmacion.estado === "IMPORTADO";
  const complete = draftStatus === "COMPLETO";

  if (!isWizardActive || payload === null) {
    return {
      wizard: "proyecto",
      severity: "info",
      eyebrow: "Proyecto habilitado",
      title: "Inicia el cargue del proyecto",
      message:
        "El programa ya esta COMPLETO. Crea o recupera el borrador del proyecto para cargar su matriz.",
      checklist: [
        item("programa", "Programa COMPLETO", availability.programa_completo),
        item("referencia", "Borrador de proyecto activo", activeReferenceId !== null, true),
        item("cierre", "Proyecto cerrado como COMPLETO", false),
      ],
      primaryAction: { label: "Iniciar wizard", targetId: "proyecto-step-workspace" },
    };
  }

  if (complete) {
    return {
      wizard: "proyecto",
      severity: "success",
      eyebrow: "Proyecto listo",
      title: "Planeacion pedagogica habilitada",
      message:
        "El proyecto esta COMPLETO. Ya puedes pasar a la planeacion pedagogica sin saltar reglas.",
      checklist: [
        item("programa", "Programa COMPLETO", true),
        item("matriz", "Matriz del proyecto importada", imported),
        item("proyecto", "Proyecto COMPLETO", true),
      ],
      primaryAction: {
        label: "Abrir planeacion",
        href: `/planeacion/${payload.meta.programaReferenciaId}`,
      },
    };
  }

  if (currentStepId === "revision-proyecto") {
    return {
      wizard: "proyecto",
      severity: imported ? "warning" : "blocked",
      eyebrow: "Revision del proyecto",
      title: imported ? "Falta cerrar el proyecto" : "Matriz pendiente",
      message: imported
        ? "Revisa fases y actividades, luego confirma el cierre para habilitar planeacion."
        : "La planeacion seguira bloqueada hasta importar y cerrar el proyecto formativo.",
      checklist: [
        item("preview", "Preview valido de matriz", previewValid),
        item("import", "Importacion confirmada", imported),
        item("close", "Proyecto en estado COMPLETO", complete, imported),
      ],
      primaryAction: {
        label: imported ? "Cerrar proyecto" : "Volver al origen",
        targetId: "proyecto-step-workspace",
      },
    };
  }

  return {
    wizard: "proyecto",
    severity: imported ? "success" : previewValid ? "warning" : "info",
    eyebrow: "Fuente del proyecto",
    title: imported
      ? "Proyecto materializado"
      : previewValid
        ? "Confirma la matriz del proyecto"
        : "Carga la matriz del proyecto",
    message: imported
      ? "La matriz ya creo el proyecto, fases y actividades. Avanza a revision."
      : previewValid
        ? "El preview esta valido; confirma la importacion antes de cerrar."
        : "Valida el Excel/matriz del proyecto para construir fases y actividades.",
    checklist: [
      item("programa", "Programa COMPLETO", availability.programa_completo),
      item("preview", "Preview del proyecto valido", previewValid, !previewValid),
      item("import", "Importacion confirmada", imported, previewValid && !imported),
    ],
    primaryAction: imported
      ? { label: "Ir a revision", targetId: "proyecto-step-workspace" }
      : undefined,
  };
}

export function buildPlaneacionWizardGuide({
  activeStep,
  competenciasCount,
  fasesCount,
  selectedCompetencia,
  selectedResultado,
  faseSelected,
  actividadSelected,
  conocimientosSelected,
  criteriosSelected,
  instructor,
  duracionHoras,
  estrategias,
  ambientes,
  recursos,
  confirmed,
  officialMissing = [],
  hoursMatch = true,
  existingPlanningsCount = 0,
}: PlaneacionGuideInput): WizardGuideState {
  if (confirmed || activeStep === "confirmacion") {
    return {
      wizard: "planeacion",
      severity: "success",
      eyebrow: "Planeacion aprobada",
      title: "Actividad de aprendizaje planificada",
      message:
        "La planeacion integrada quedo confirmada y el formato oficial fue almacenado.",
      checklist: [
        item("curricular", "Vinculacion curricular completa", true),
        item("complementario", "Campos didacticos definidos", true),
        item("confirmacion", "Aprobacion generada", true),
      ],
      primaryAction: {
        label: "Planificar otra actividad",
        targetId: "planeacion-step-workspace",
      },
    };
  }

  if (activeStep === "dashboard") {
    const planningsText =
      existingPlanningsCount && existingPlanningsCount > 0
        ? `Esta actividad de proyecto ya tiene ${existingPlanningsCount} actividad(es) de aprendizaje. Puedes continuar una existente o crear una nueva.`
        : "Selecciona la fase y la actividad del proyecto para integrar sus competencias y RAP en una nueva actividad de aprendizaje.";

    return {
      wizard: "planeacion",
      severity:
        competenciasCount === 0 || fasesCount === 0
          ? "blocked"
          : officialMissing.length > 0
            ? "warning"
            : "info",
      eyebrow: "Planeacion pedagogica",
      title:
        officialMissing.length > 0
          ? "Prepara el formato oficial"
          : "Selecciona fase y actividad",
      message: officialMissing[0] ?? planningsText,
      checklist: [
        item("fases", "Fases del proyecto disponibles", fasesCount > 0, true),
        item("fase", "Fase seleccionada", faseSelected),
        item("actividad", "Actividad seleccionada", actividadSelected),
        item("resultado", "Resultados de aprendizaje elegidos", selectedResultado),
        ...officialMissing.slice(0, 3).map((label, index) =>
          item(`official-${index}`, label, false),
        ),
      ],
      primaryAction: { label: "Crear planeacion", targetId: "planeacion-step-workspace" },
    };
  }

  if (activeStep === "curricular") {
    const curricularReady =
      faseSelected &&
      actividadSelected &&
      selectedCompetencia &&
      selectedResultado &&
      conocimientosSelected > 0 &&
      criteriosSelected > 0;
    return {
      wizard: "planeacion",
      severity: curricularReady ? "success" : "warning",
      eyebrow: "Seleccion curricular",
      title: curricularReady ? "Seleccion curricular lista" : "Completa la vinculacion",
      message: curricularReady
        ? "Ya puedes guardar el borrador y pasar a campos complementarios."
        : "Selecciona la fase, actividad, competencias, RAPs, saberes y criterios.",
      checklist: [
        item("fase", "1. Fase seleccionada", faseSelected, !faseSelected),
        item("actividad", "2. Actividad de proyecto seleccionada", actividadSelected, faseSelected && !actividadSelected),
        item("competencias", "3. Competencias seleccionadas", selectedCompetencia, actividadSelected && !selectedCompetencia),
        item("resultado", "4. Resultados (RAP) seleccionados", selectedResultado, selectedCompetencia && !selectedResultado),
        item("saberes", "5. Saberes seleccionados", conocimientosSelected > 0),
        item("criterios", "6. Criterios seleccionados", criteriosSelected > 0),
      ],
      primaryAction: { label: "Guardar borrador", targetId: "planeacion-step-workspace" },
    };
  }

  if (activeStep === "complementario") {
    const complementReady =
      hasText(instructor) &&
      duracionHoras > 0 &&
      hasText(estrategias) &&
      hasText(ambientes) &&
      hasText(recursos);
    return {
      wizard: "planeacion",
      severity: complementReady ? "success" : "warning",
      eyebrow: "Campos didacticos",
      title: complementReady ? "Campos complementarios listos" : "Faltan campos didacticos",
      message: complementReady
        ? "Puedes guardar y abrir la vista previa de la planeacion."
        : "Define instructor, duracion, estrategias, ambientes y recursos antes de aprobar.",
      checklist: [
        item("instructor", "Instructor responsable", hasText(instructor), true),
        item("duracion", "Duracion en horas", duracionHoras > 0),
        item("horas", "Duracion y distribucion de horas coherentes", hoursMatch),
        item("estrategias", "Estrategias didacticas", hasText(estrategias)),
        item("ambientes", "Ambientes de aprendizaje", hasText(ambientes)),
        item("recursos", "Recursos y medios", hasText(recursos)),
      ],
      primaryAction: {
        label: "Ver previsualizacion",
        targetId: "planeacion-step-workspace",
      },
    };
  }

  if (officialMissing.length > 0) {
    return {
      wizard: "planeacion",
      severity: "blocked",
      eyebrow: "Formato oficial GPFI-F-134 V05",
      title: "Hay datos pendientes para generar",
      message:
        "Corrige los faltantes indicados por el backend antes de aprobar la planeacion.",
      checklist: officialMissing.slice(0, 6).map((label, index) =>
        item(`official-${index}`, label, false, index === 0),
      ),
      primaryAction: {
        label: "Ir al primer faltante",
        targetId: "planeacion-step-workspace",
      },
    };
  }

  return {
    wizard: "planeacion",
    severity: "info",
    eyebrow: "Vista previa",
    title: "Revisa antes de aprobar",
    message:
      "Confirma la integración de competencias, RAP, saberes, criterios y campos didácticos.",
    checklist: [
      item("curricular", "Seleccion curricular revisada", true),
      item("complementario", "Campos didacticos revisados", true),
      item("approve", "Aprobacion pendiente", false, true),
    ],
    primaryAction: { label: "Aprobar y guardar", targetId: "planeacion-step-workspace" },
  };
}

export function buildBlockedModuleGuide(
  wizard: "proyecto" | "planeacion",
  title: string,
  message: string,
  actionLabel = "Volver al dashboard",
  href = "/",
): WizardGuideState {
  return {
    wizard,
    severity: "blocked",
    eyebrow: "Bloqueo de secuencia",
    title,
    message,
    checklist: [
      item("programa", "Programa de formacion COMPLETO", true),
      item(
        "proyecto",
        wizard === "proyecto"
          ? "Programa requerido para abrir proyecto"
          : "Proyecto formativo COMPLETO",
        false,
        true,
      ),
      item("next", "Siguiente wizard habilitado", false),
    ],
    primaryAction: { label: actionLabel, href },
  };
}
