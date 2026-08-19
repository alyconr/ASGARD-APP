import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PlaneacionWizardShell } from "./planeacion-wizard-shell";
import type { ContextoCompetencia, PlaneacionContextoResponse, PlaneacionListResponse, PlaneacionResponse } from "../planeacion-api";
import * as api from "../planeacion-api";

// Mock the API client
vi.mock("../planeacion-api", () => ({
  listPlaneacionesProyecto: vi.fn(),
  fetchPlaneacionDetalle: vi.fn(),
  savePlaneacionBorrador: vi.fn(),
  confirmarPlaneacion: vi.fn(),
  deletePlaneacion: vi.fn(),
  fetchPlaneacionDocumentoConfig: vi.fn(),
  savePlaneacionDocumentoConfig: vi.fn(),
  fetchFormatoOficialEstadoIndividual: vi.fn(),
  fetchFormatoOficialEstadoConsolidado: vi.fn(),
  generarFormatoOficialConsolidado: vi.fn(),
  downloadFormatoOficialIndividual: vi.fn(),
  downloadFormatoOficialConsolidado: vi.fn(),
}));

const mockCompetencia: ContextoCompetencia = {
  id: "comp-1",
  codigo_competencia: "220501001",
  nombre_competencia: "Diseñar la arquitectura del software",
  resultados: [
    {
      id: "rap-1",
      codigo_resultado: "220501001-01",
      descripcion: "Resultado 1: Identificar requisitos técnicos",
      tipo_resultado: "ESPECIFICO",
    },
  ],
  conocimientos_saber: [
    {
      id: "know-saber-1",
      descripcion: "Concepto 1: Fundamentos de bases de datos",
    },
  ],
  conocimientos_proceso: [
    {
      id: "know-proc-1",
      descripcion: "Proceso 1: Aplicar diagramas UML",
    },
  ],
  criterios: [
    {
      id: "crit-1",
      descripcion: "Criterio 1: Elabora el modelo conceptual",
    },
  ],
};

const mockContexto: PlaneacionContextoResponse = {
  programa_id: "prog-1",
  codigo_programa: "220501",
  nombre_programa: "Análisis y Desarrollo de Software",
  version_programa: "1",
  proyecto_id: "proj-1",
  codigo_proyecto: "123456",
  nombre_proyecto: "Sistema de Información de Pruebas",
  version_proyecto: "2",
  fases: [
    {
      id: "fase-1",
      nombre_fase: "Fase 1: Análisis",
      actividades: [
        {
          id: "act-1",
          descripcion: "Actividad 1: Levantar requerimientos",
          competencias: [mockCompetencia],
        },
        {
          id: "act-2",
          descripcion: "Actividad 2: Diseñar arquitectura",
          competencias: [],
        },
      ],
    },
  ],
};

const mockPlanningsList: PlaneacionListResponse[] = [
  {
    id: "plan-1",
    proyecto_id: "proj-1",
    fase_id: "fase-1",
    actividad_id: "act-1",
    nombre_fase: "Fase 1: Análisis",
    descripcion_actividad: "Actividad 1: Levantar requerimientos",
    actividades_aprendizaje: "Determinar requerimientos de software",
    estado: "BORRADOR",
    competencias_count: 1,
    resultados_count: 1,
    resultados_especificos: 1,
    resultados_transversales: 0,
    fecha_actualizacion: "2026-05-27T10:00:00Z",
  },
];

const mockPlanningDetail: PlaneacionResponse = {
  id: "plan-1",
  proyecto_id: "proj-1",
  fase_id: "fase-1",
  actividad_id: "act-1",
  estado: "BORRADOR",
  datos_complementarios: {
    actividades_aprendizaje: "Determinar requerimientos de software",
    estrategias_didacticas: "Talleres prácticos",
    ambientes_aprendizaje: "Laboratorio 305",
    recursos_didacticos: "Computadores, guías de aprendizaje",
    duracion_horas: 40,
    instructor_responsable: "Juan Perez",
  },
  resultados_ids: ["rap-1"],
  conocimientos_ids: ["know-saber-1", "know-proc-1"],
  criterios_ids: ["crit-1"],
  competencias: [
    {
      competencia_id: "comp-1",
      codigo_competencia: "220501001",
      nombre_competencia: "Diseñar la arquitectura del software",
      tipo_resultado: "ESPECIFICO",
      resultados: [
        {
          id: "rap-1",
          codigo_resultado: "220501001-01",
          descripcion: "Resultado 1: Identificar requisitos técnicos",
          tipo_resultado: "ESPECIFICO",
        },
      ],
    },
  ],
  storage_key: null,
  file_name: null,
  content_type: null,
  checksum_sha256: null,
  fecha_generacion: null,
  version: 1,
};

describe("PlaneacionWizardShell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(api, "listPlaneacionesProyecto").mockResolvedValue([]);
    vi.spyOn(api, "fetchPlaneacionDetalle").mockResolvedValue(mockPlanningDetail);
    vi.spyOn(api, "fetchPlaneacionDocumentoConfig").mockResolvedValue({
      proyecto_id: "proj-1",
      fecha_elaboracion: "2026-07-29",
      modalidad_formacion: "Presencial",
      clasificacion_informacion: "PUBLICA",
      equipo_gestion_curricular: ["Ana Instructor"],
      regional: "Distrito Capital",
      centro_formacion: "Centro de prueba",
      storage_key: null,
      file_name: null,
      content_type: null,
      checksum_sha256: null,
      fecha_generacion: null,
      version: 1,
    });
    vi.spyOn(api, "fetchFormatoOficialEstadoConsolidado").mockResolvedValue({
      listo: false,
      faltantes: [
        {
          codigo: "SIN_PLANEACIONES_COMPLETAS",
          mensaje: "No existen planeaciones completas para exportar.",
          paso: "confirmacion",
        },
      ],
      planeaciones_completas: 0,
      borradores_excluidos: 0,
      storage_key: null,
      file_name: null,
      checksum_sha256: null,
      fecha_generacion: null,
    });
    vi.spyOn(api, "fetchFormatoOficialEstadoIndividual").mockResolvedValue({
      listo: true,
      faltantes: [],
      planeaciones_completas: 0,
      borradores_excluidos: 1,
      storage_key: null,
      file_name: null,
      checksum_sha256: null,
      fecha_generacion: null,
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
  });

  it("shows and saves the official document configuration", async () => {
    vi.spyOn(api, "savePlaneacionDocumentoConfig").mockResolvedValue({
      proyecto_id: "proj-1",
      fecha_elaboracion: "2026-07-29",
      modalidad_formacion: "Presencial",
      clasificacion_informacion: "PUBLICA",
      equipo_gestion_curricular: ["Ana Instructor"],
      regional: "Distrito Capital",
      centro_formacion: "Centro de prueba",
      storage_key: null,
      file_name: null,
      content_type: null,
      checksum_sha256: null,
      fecha_generacion: null,
      version: 1,
    });

    render(<PlaneacionWizardShell contexto={mockContexto} referenciaId="ref-uuid" />);

    expect(
      await screen.findByText("Configuración documental"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Generar consolidado oficial" }),
    ).toBeDisabled();
    fireEvent.click(
      screen.getByRole("button", { name: "Guardar configuración" }),
    );

    await waitFor(() => {
      expect(api.savePlaneacionDocumentoConfig).toHaveBeenCalledWith(
        "proj-1",
        expect.objectContaining({
          modalidad_formacion: "Presencial",
          equipo_gestion_curricular: ["Ana Instructor"],
        }),
      );
    });
  });

  it("renders the dashboard list of competencies and activities correctly", async () => {
    vi.spyOn(api, "listPlaneacionesProyecto").mockResolvedValue(mockPlanningsList);
    render(<PlaneacionWizardShell contexto={mockContexto} referenciaId="ref-uuid" />);

    expect(await screen.findByText("Planeaciones e Integraciones de Actividades de Aprendizaje")).toBeInTheDocument();
    expect(screen.getByText("Determinar requerimientos de software")).toBeInTheDocument();
    expect(screen.getByText("Fase 1: Análisis")).toBeInTheDocument();
    expect(screen.getByText("Actividad 1: Levantar requerimientos")).toBeInTheDocument();
  });

  it("navigates to curricular wizard step when starting a new planning", async () => {
    render(<PlaneacionWizardShell contexto={mockContexto} referenciaId="ref-uuid" />);

    fireEvent.click(screen.getByRole("button", { name: /Nueva actividad de aprendizaje/i }));

    await waitFor(() => {
      expect(screen.getByText("1. Estructura Curricular y de Proyecto")).toBeInTheDocument();
    });

    // Step 1: select phase
    fireEvent.change(screen.getByLabelText("1. Selecciona la Fase del Proyecto Formativo"), {
      target: { value: "fase-1" },
    });

    // Step 2: select activity
    fireEvent.change(await screen.findByLabelText("2. Selecciona la Actividad del Proyecto"), {
      target: { value: "act-1" },
    });

    // Step 3: check RAP
    const rapCheckbox = await screen.findByRole("checkbox", { name: /Resultado 1: Identificar requisitos técnicos/i });
    fireEvent.click(rapCheckbox);

    await waitFor(() => {
      expect(screen.getByText("Concepto 1: Fundamentos de bases de datos")).toBeInTheDocument();
      expect(screen.getByText("Proceso 1: Aplicar diagramas UML")).toBeInTheDocument();
      expect(screen.getByText("Criterio 1: Elabora el modelo conceptual")).toBeInTheDocument();
    });
  });

  it("loads existing draft details when editing a draft", async () => {
    vi.spyOn(api, "listPlaneacionesProyecto").mockResolvedValue(mockPlanningsList);
    vi.spyOn(api, "fetchPlaneacionDetalle").mockResolvedValue(mockPlanningDetail);

    render(<PlaneacionWizardShell contexto={mockContexto} referenciaId="ref-uuid" />);

    await waitFor(() => {
      expect(screen.getByText("BORRADOR")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Editar planeación/i }));

    await waitFor(() => {
      expect(api.fetchPlaneacionDetalle).toHaveBeenCalledWith("plan-1");
    });

    await waitFor(() => {
      expect(screen.getByText("1. Estructura Curricular y de Proyecto")).toBeInTheDocument();
    });
  });

  it("supports saving a draft and navigates steps", async () => {
    vi.spyOn(api, "savePlaneacionBorrador").mockResolvedValue({
      ...mockPlanningDetail,
      id: "plan-new-id",
    });

    render(<PlaneacionWizardShell contexto={mockContexto} referenciaId="ref-uuid" />);

    fireEvent.click(screen.getByRole("button", { name: /Nueva actividad de aprendizaje/i }));

    await waitFor(() => {
      expect(screen.getByText("1. Estructura Curricular y de Proyecto")).toBeInTheDocument();
    });

    // Select phase, activity, comp, rap
    fireEvent.change(screen.getByLabelText("1. Selecciona la Fase del Proyecto Formativo"), {
      target: { value: "fase-1" },
    });
    fireEvent.change(await screen.findByLabelText("2. Selecciona la Actividad del Proyecto"), {
      target: { value: "act-1" },
    });
    const compCheckboxes1 = await screen.findAllByRole("checkbox", { name: /220501001/i });
    if (!(compCheckboxes1[0] as HTMLInputElement).checked) {
      fireEvent.click(compCheckboxes1[0]);
    }
    fireEvent.click(await screen.findByRole("checkbox", { name: /Resultado 1: Identificar requisitos técnicos/i }));

    fireEvent.change(screen.getByLabelText("Temáticas adicionales de conceptos y principios"), {
      target: { value: "Arquitectura limpia" },
    });
    fireEvent.click(
      screen.getAllByRole("button", { name: "Adicionar temática" })[0],
    );

    // Save draft
    const saveBtn = screen.getByText("Guardar Borrador");
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(api.savePlaneacionBorrador).toHaveBeenCalled();
    });
    expect(api.savePlaneacionBorrador).toHaveBeenCalledWith(
      expect.objectContaining({
        fase_id: "fase-1",
        actividad_id: "act-1",
        resultados_ids: ["rap-1"],
        datos_complementarios: expect.objectContaining({
          tematicas_saber: ["Arquitectura limpia"],
        }),
      }),
    );

    // Click next step
    const nextBtn = screen.getByText("Siguiente");
    fireEvent.click(nextBtn);

    await waitFor(() => {
      expect(screen.getByText("2. Campos Complementarios")).toBeInTheDocument();
    });
  });

  it("toggles all checkboxes when using the Select All button", async () => {
    render(<PlaneacionWizardShell contexto={mockContexto} referenciaId="ref-uuid" />);

    fireEvent.click(screen.getByRole("button", { name: /Nueva actividad de aprendizaje/i }));

    await waitFor(() => {
      expect(screen.getByText("1. Estructura Curricular y de Proyecto")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("1. Selecciona la Fase del Proyecto Formativo"), {
      target: { value: "fase-1" },
    });
    fireEvent.change(await screen.findByLabelText("2. Selecciona la Actividad del Proyecto"), {
      target: { value: "act-1" },
    });
    const compCheckboxes2 = await screen.findAllByRole("checkbox", { name: /220501001/i });
    if (!(compCheckboxes2[0] as HTMLInputElement).checked) {
      fireEvent.click(compCheckboxes2[0]);
    }
    fireEvent.click(await screen.findByRole("checkbox", { name: /Resultado 1: Identificar requisitos técnicos/i }));

    const selectAllBtn = await screen.findByRole("button", { name: "Seleccionar Todo" });
    const knowSaberCheckbox = screen.getByLabelText("Concepto 1: Fundamentos de bases de datos");
    const knowProcCheckbox = screen.getByLabelText("Proceso 1: Aplicar diagramas UML");
    const critCheckbox = screen.getByLabelText("Criterio 1: Elabora el modelo conceptual");

    // Initially none are checked
    expect(knowSaberCheckbox).not.toBeChecked();
    expect(knowProcCheckbox).not.toBeChecked();
    expect(critCheckbox).not.toBeChecked();

    // Click Select All
    fireEvent.click(selectAllBtn);

    // All should be checked
    expect(knowSaberCheckbox).toBeChecked();
    expect(knowProcCheckbox).toBeChecked();
    expect(critCheckbox).toBeChecked();

    // Click Deselect All
    const deselectAllBtn = screen.getByRole("button", { name: "Deseleccionar Todo" });
    fireEvent.click(deselectAllBtn);

    // None should be checked
    expect(knowSaberCheckbox).not.toBeChecked();
    expect(knowProcCheckbox).not.toBeChecked();
    expect(critCheckbox).not.toBeChecked();
  });

  it("allows deleting an existing planning draft", async () => {
    vi.spyOn(api, "listPlaneacionesProyecto").mockResolvedValue(mockPlanningsList);
    vi.spyOn(api, "deletePlaneacion").mockResolvedValue();

    render(<PlaneacionWizardShell contexto={mockContexto} referenciaId="ref-uuid" />);

    await waitFor(() => {
      expect(screen.getByText("BORRADOR")).toBeInTheDocument();
    });

    const deleteBtn = await screen.findByTitle(/Eliminar planeación/i);
    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(api.deletePlaneacion).toHaveBeenCalledWith("plan-1");
    });
  });

  it("automatically infers the fase and pre-selects competencies when an activity is selected directly", async () => {
    render(<PlaneacionWizardShell contexto={mockContexto} referenciaId="ref-uuid" />);

    fireEvent.click(screen.getByRole("button", { name: /Nueva actividad de aprendizaje/i }));

    await waitFor(() => {
      expect(screen.getByText("1. Estructura Curricular y de Proyecto")).toBeInTheDocument();
    });

    // Select activity directly without selecting fase first
    fireEvent.change(screen.getByLabelText("2. Selecciona la Actividad del Proyecto"), {
      target: { value: "act-1" },
    });

    // Verify Fase is automatically populated and displayed
    await waitFor(() => {
      expect(screen.getByText(/Fase activa: Fase 1: Análisis/i)).toBeInTheDocument();
    });

    // Verify competencies are automatically pre-selected and RAPs are displayed
    const compCheckboxes = await screen.findAllByRole("checkbox", { name: /220501001/i });
    expect(compCheckboxes[0]).toBeChecked();
    expect(screen.getByText("Resultado 1: Identificar requisitos técnicos")).toBeInTheDocument();
  });
});

