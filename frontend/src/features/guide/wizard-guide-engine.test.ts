import { describe, expect, it } from "vitest";

import {
  buildBlockedModuleGuide,
  buildPlaneacionWizardGuide,
  buildProgramaWizardGuide,
  buildProyectoWizardGuide,
} from "@/features/guide/wizard-guide-engine";

describe("wizard guide engine", () => {
  it("blocks program users when the Excel preview is valid but not imported", () => {
    const guide = buildProgramaWizardGuide({
      activeReferenceId: "11111111-1111-4111-9111-111111111111",
      currentStepId: "revision-programa",
      draftStatus: "BORRADOR",
      isWizardActive: true,
      payload: {
        meta: {
          referenciaId: "11111111-1111-4111-9111-111111111111",
          entryMode: "EXCEL",
          touchedSteps: ["revision-programa"],
          startedAt: "2026-06-22T00:00:00.000Z",
          lastInteractionAt: "2026-06-22T00:00:00.000Z",
        },
        programa: {
          codigo_programa: "228118",
          nombre_programa: "Analisis de software",
          version_programa: "1",
        },
        wizard: { notesByStep: {} },
        documental: {
          programa_pdf: null,
          programa_excel: {
            documento: null,
            preview: {
              referencia_id: "11111111-1111-4111-9111-111111111111",
              documento: null,
              valid: true,
              estado_validacion: "VALIDO",
              resumen: {
                programa: 1,
                competencias: 1,
                resultados: 1,
                conocimientos: 1,
                criterios: 1,
              },
              pendientes_resumen: {
                total: 0,
                conocimientos: 0,
                criterios: 0,
              },
              programa: null,
              competencias: [],
              pendientes: [],
              errores: [],
            },
            confirmacion: { estado: "PENDIENTE" },
          },
        },
        curricular: {
          programa_formacion_id: null,
          competencias: [],
        },
      },
    });

    expect(guide.severity).toBe("blocked");
    expect(guide.title).toBe("Importacion pendiente");
  });

  it("blocks project guidance when the backend availability says the program is incomplete", () => {
    const guide = buildProyectoWizardGuide({
      activeReferenceId: null,
      availability: {
        referencia_id: "22222222-2222-4222-9222-222222222222",
        programa_id: null,
        estado_programa: "BORRADOR",
        programa_completo: false,
        proyecto_bloqueado: true,
        estado_proyecto: "BLOQUEADO",
        motivo: "PROGRAMA_NO_COMPLETO",
        mensaje:
          "Debes cerrar el programa de formacion como COMPLETO antes de iniciar el proyecto formativo.",
        accion_sugerida: "completar_y_cerrar_programa",
      },
      currentStepId: "revision-proyecto",
      draftStatus: "BLOQUEADO",
      isWizardActive: false,
      payload: null,
    });

    expect(guide.severity).toBe("blocked");
    expect(guide.message).toContain("programa de formacion");
  });

  it("warns planning users about missing complementary fields", () => {
    const guide = buildPlaneacionWizardGuide({
      activeStep: "complementario",
      competenciasCount: 2,
      fasesCount: 1,
      selectedCompetencia: true,
      selectedResultado: true,
      faseSelected: true,
      actividadSelected: true,
      conocimientosSelected: 3,
      criteriosSelected: 2,
      instructor: "",
      duracionHoras: 0,
      estrategias: "Trabajo colaborativo",
      ambientes: "",
      recursos: "",
      confirmed: false,
    });

    expect(guide.severity).toBe("warning");
    expect(guide.checklist.some((item) => item.status === "current")).toBe(true);
  });

  it("blocks official generation with backend-derived gaps", () => {
    const guide = buildPlaneacionWizardGuide({
      activeStep: "preview",
      competenciasCount: 2,
      fasesCount: 1,
      selectedCompetencia: true,
      selectedResultado: true,
      faseSelected: true,
      actividadSelected: true,
      conocimientosSelected: 3,
      criteriosSelected: 2,
      instructor: "Ana Instructor",
      duracionHoras: 12,
      estrategias: "Trabajo colaborativo",
      ambientes: "Aula TIC",
      recursos: "Computadores",
      confirmed: false,
      officialMissing: [
        "Falta la regional.",
        "La duracion total no coincide.",
      ],
    });

    expect(guide.severity).toBe("blocked");
    expect(guide.checklist[0].label).toBe("Falta la regional.");
  });

  it("creates a blocked inter-wizard guide with a dashboard CTA", () => {
    const guide = buildBlockedModuleGuide(
      "planeacion",
      "Planeacion pedagogica no disponible",
      "Debes cerrar el proyecto formativo como COMPLETO antes de iniciar la planeacion pedagogica.",
    );

    expect(guide.severity).toBe("blocked");
    expect(guide.primaryAction?.href).toBe("/");
  });
});
