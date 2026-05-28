import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PlaneacionWizardShell } from "./planeacion-wizard-shell";
import type { PlaneacionContextoResponse, PlaneacionListResponse, PlaneacionResponse } from "../planeacion-api";
import * as api from "../planeacion-api";

// Mock the API client
vi.mock("../planeacion-api", () => ({
  listPlaneacionesProyecto: vi.fn(),
  fetchPlaneacionDetalle: vi.fn(),
  savePlaneacionBorrador: vi.fn(),
  confirmarPlaneacion: vi.fn(),
  deletePlaneacion: vi.fn(),
}));

const mockContexto: PlaneacionContextoResponse = {
  programa_id: "prog-1",
  codigo_programa: "220501",
  nombre_programa: "Análisis y Desarrollo de Software",
  proyecto_id: "proj-1",
  codigo_proyecto: "123456",
  nombre_proyecto: "Sistema de Información de Pruebas",
  fases: [
    {
      id: "fase-1",
      nombre_fase: "Fase 1: Análisis",
      actividades: [
        {
          id: "act-1",
          descripcion: "Actividad 1: Levantar requerimientos",
        },
        {
          id: "act-2",
          descripcion: "Actividad 2: Diseñar arquitectura",
        },
      ],
    },
  ],
  competencias: [
    {
      id: "comp-1",
      codigo_competencia: "220501001",
      nombre_competencia: "Diseñar la arquitectura del software",
      resultados: [
        {
          id: "rap-1",
          descripcion: "Resultado 1: Identificar requisitos técnicos",
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
    },
  ],
};

const mockPlanningsList: PlaneacionListResponse[] = [
  {
    id: "plan-1",
    proyecto_id: "proj-1",
    competencia_id: "comp-1",
    codigo_competencia: "220501001",
    nombre_competencia: "Diseñar la arquitectura del software",
    estado: "BORRADOR",
    fecha_actualizacion: "2026-05-27T10:00:00Z",
  },
];

const mockPlanningDetail: PlaneacionResponse = {
  id: "plan-1",
  proyecto_id: "proj-1",
  competencia_id: "comp-1",
  fase_id: "fase-1",
  actividad_id: "act-1",
  estado: "BORRADOR",
  datos_complementarios: {
    estrategias_didacticas: "Talleres prácticos",
    ambientes_aprendizaje: "Laboratorio 305",
    recursos_didacticos: "Computadores, guías de aprendizaje",
    duracion_horas: 40,
    instructor_responsable: "Juan Perez",
  },
  resultados_ids: ["rap-1"],
  conocimientos_ids: ["know-saber-1", "know-proc-1"],
  criterios_ids: ["crit-1"],
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
    vi.spyOn(window, "confirm").mockReturnValue(true);
  });

  it("renders the dashboard list of competencies correctly", async () => {
    render(<PlaneacionWizardShell contexto={mockContexto} referenciaId="ref-uuid" />);

    expect(screen.getByText("Listado de Competencias del Programa")).toBeInTheDocument();
    expect(screen.getByText("Diseñar la arquitectura del software")).toBeInTheDocument();
    expect(screen.getByText("220501001")).toBeInTheDocument();
    expect(screen.getByText("SIN PLANIFICAR")).toBeInTheDocument();
  });

  it("navigates to curricular wizard step when starting a new planning", async () => {
    render(<PlaneacionWizardShell contexto={mockContexto} referenciaId="ref-uuid" />);

    // Click on the competency item to start planning
    fireEvent.click(screen.getByText("Iniciar Planeación"));

    await waitFor(() => {
      expect(screen.getByText("1. Estructura Curricular y de Proyecto")).toBeInTheDocument();
    });

    // Check that we display results and criteria checkboxes
    expect(screen.getByText("Resultado 1: Identificar requisitos técnicos")).toBeInTheDocument();
    expect(screen.getByText("Concepto 1: Fundamentos de bases de datos")).toBeInTheDocument();
    expect(screen.getByText("Proceso 1: Aplicar diagramas UML")).toBeInTheDocument();
    expect(screen.getByText("Criterio 1: Elabora el modelo conceptual")).toBeInTheDocument();
  });

  it("loads existing draft details when editing a draft", async () => {
    vi.spyOn(api, "listPlaneacionesProyecto").mockResolvedValue(mockPlanningsList);
    vi.spyOn(api, "fetchPlaneacionDetalle").mockResolvedValue(mockPlanningDetail);

    render(<PlaneacionWizardShell contexto={mockContexto} referenciaId="ref-uuid" />);

    await waitFor(() => {
      expect(screen.getByText("BORRADOR")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Editar Borrador"));

    await waitFor(() => {
      expect(api.fetchPlaneacionDetalle).toHaveBeenCalledWith("plan-1");
    });

    await waitFor(() => {
      expect(screen.getByText("1. Estructura Curricular y de Proyecto")).toBeInTheDocument();
      // Check that options are selected
      const selectFase = screen.getByLabelText("Fase del Proyecto Formativo");
      expect(selectFase).toHaveValue("fase-1");
    });
  });

  it("supports saving a draft and navigates steps", async () => {
    vi.spyOn(api, "savePlaneacionBorrador").mockResolvedValue({
      ...mockPlanningDetail,
      id: "plan-new-id",
    });

    render(<PlaneacionWizardShell contexto={mockContexto} referenciaId="ref-uuid" />);

    // Click to start planning
    fireEvent.click(screen.getByText("Iniciar Planeación"));

    await waitFor(() => {
      expect(screen.getByText("1. Estructura Curricular y de Proyecto")).toBeInTheDocument();
    });

    // Select Phase
    const selectFase = screen.getByLabelText("Fase del Proyecto Formativo");
    fireEvent.change(selectFase, { target: { value: "fase-1" } });

    // Select Activity
    const selectActividad = screen.getByLabelText("Actividad del Proyecto");
    fireEvent.change(selectActividad, { target: { value: "act-1" } });

    // Click Resultado checkbox
    const resultCheckbox = screen.getByLabelText("Resultado 1: Identificar requisitos técnicos");
    fireEvent.click(resultCheckbox);

    // Save draft
    const saveBtn = screen.getByText("Guardar Borrador");
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(api.savePlaneacionBorrador).toHaveBeenCalled();
    });

    // Click next step
    const nextBtn = screen.getByText("Siguiente");
    fireEvent.click(nextBtn);

    await waitFor(() => {
      expect(screen.getByText("2. Campos Complementarios")).toBeInTheDocument();
    });
  });

  it("toggles all checkboxes when using the Select All button", async () => {
    render(<PlaneacionWizardShell contexto={mockContexto} referenciaId="ref-uuid" />);

    // Click to start planning
    fireEvent.click(screen.getByText("Iniciar Planeación"));

    await waitFor(() => {
      expect(screen.getByText("1. Estructura Curricular y de Proyecto")).toBeInTheDocument();
    });

    const selectAllBtn = screen.getByRole("button", { name: "Seleccionar Todo" });
    const resultCheckbox = screen.getByLabelText("Resultado 1: Identificar requisitos técnicos");
    const knowSaberCheckbox = screen.getByLabelText("Concepto 1: Fundamentos de bases de datos");
    const knowProcCheckbox = screen.getByLabelText("Proceso 1: Aplicar diagramas UML");
    const critCheckbox = screen.getByLabelText("Criterio 1: Elabora el modelo conceptual");

    // Initially none are checked
    expect(resultCheckbox).not.toBeChecked();
    expect(knowSaberCheckbox).not.toBeChecked();
    expect(knowProcCheckbox).not.toBeChecked();
    expect(critCheckbox).not.toBeChecked();

    // Click Select All
    fireEvent.click(selectAllBtn);

    // All should be checked
    expect(resultCheckbox).toBeChecked();
    expect(knowSaberCheckbox).toBeChecked();
    expect(knowProcCheckbox).toBeChecked();
    expect(critCheckbox).toBeChecked();

    // Click Deselect All
    const deselectAllBtn = screen.getByRole("button", { name: "Deseleccionar Todo" });
    fireEvent.click(deselectAllBtn);

    // None should be checked
    expect(resultCheckbox).not.toBeChecked();
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

    const deleteBtn = screen.getByTitle("Eliminar planeación");
    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(api.deletePlaneacion).toHaveBeenCalledWith("plan-1");
    });
  });

  it("loads and displays approved planning details when planning is COMPLETO", async () => {
    const mockCompletedPlanning: PlaneacionListResponse[] = [
      {
        ...mockPlanningsList[0],
        estado: "COMPLETO",
      },
    ];
    const mockCompletedDetail: PlaneacionResponse = {
      ...mockPlanningDetail,
      estado: "COMPLETO",
      storage_key: "planeaciones-pedagogicas/prog-1/proj-1/comp-1/planeacion.json",
      file_name: "planeacion.json",
      fecha_generacion: "2026-05-27T12:00:00Z",
    };

    vi.spyOn(api, "listPlaneacionesProyecto").mockResolvedValue(mockCompletedPlanning);
    vi.spyOn(api, "fetchPlaneacionDetalle").mockResolvedValue(mockCompletedDetail);

    render(<PlaneacionWizardShell contexto={mockContexto} referenciaId="ref-uuid" />);

    await waitFor(() => {
      expect(screen.getByText("COMPLETO")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Ver Planeación"));

    await waitFor(() => {
      expect(api.fetchPlaneacionDetalle).toHaveBeenCalledWith("plan-1");
    });

    await waitFor(() => {
      expect(screen.getByText("¡Planeación Pedagógica Completada!")).toBeInTheDocument();
      expect(screen.getByText("Detalle de la Planeación Aprobada")).toBeInTheDocument();
      expect(screen.getByText("Instructor Responsable")).toBeInTheDocument();
      expect(screen.getByText("Juan Perez")).toBeInTheDocument();
      expect(screen.getByText("Talleres prácticos")).toBeInTheDocument();
      expect(screen.getByText("Laboratorio 305")).toBeInTheDocument();
      expect(screen.getByText("Computadores, guías de aprendizaje")).toBeInTheDocument();
    });
  });
});
