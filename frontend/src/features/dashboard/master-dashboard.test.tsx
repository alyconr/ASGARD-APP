import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MasterDashboard } from "./master-dashboard";
import type { DashboardProgramFlow, DashboardResponse } from "./dashboard-api";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...props
  }: React.AnchorHTMLAttributes<HTMLAnchorElement> & {
    href: string;
    children: React.ReactNode;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

const referenciaId = "11111111-1111-4111-9111-111111111111";

afterEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function buildDashboard(
  overrides: Partial<DashboardResponse> = {},
): DashboardResponse {
  return {
    referencia_id: referenciaId,
    estado_global: "PROGRAMA_EN_CURSO",
    resumen:
      "Completa y cierra el programa para desbloquear los modulos siguientes.",
    modules: [
      {
        id: "programa",
        titulo: "Programa de formacion",
        estado: "EN_REVISION",
        disponible: true,
        href: "/programa",
        motivo_bloqueo: null,
        accion_requerida: "Cargar Excel, revisar estructura y cerrar programa.",
        descripcion: "Fuente estructurada del programa y revision curricular.",
        avance_porcentaje: 75,
      },
      {
        id: "proyecto",
        titulo: "Proyecto formativo",
        estado: "BLOQUEADO",
        disponible: false,
        href: `/proyecto/${referenciaId}`,
        motivo_bloqueo: "PROGRAMA_NO_COMPLETO",
        accion_requerida: "Cerrar el programa como COMPLETO.",
        descripcion: "PDF evidencia y matriz estructurada del proyecto.",
        avance_porcentaje: 0,
      },
      {
        id: "planeacion",
        titulo: "Planeacion pedagogica",
        estado: "BLOQUEADO",
        disponible: false,
        href: `/planeacion/${referenciaId}`,
        motivo_bloqueo: "PROGRAMA_NO_COMPLETO",
        accion_requerida: "Cerrar el proyecto como COMPLETO.",
        descripcion: "Planeaciones por RAP asociadas a fases y actividades.",
        avance_porcentaje: 0,
      },
    ],
    metricas: {
      programa: {
        estado: "EN_REVISION",
        competencias: 2,
        resultados: 5,
        conocimientos: 7,
        criterios: 9,
      },
      proyecto: {
        estado: "BLOQUEADO",
        fases: 0,
        actividades: 0,
        fuente_estructurada_cargada: false,
      },
      planeacion: {
        estado: "BLOQUEADO",
        total: 0,
        borrador: 0,
        completas: 0,
        competencias_con_planeacion: 0,
        competencias_sin_planear: 2,
      },
    },
    graph_nodes: [
      {
        id: "programa",
        label: "Programa",
        tipo: "wizard",
        estado: "EN_REVISION",
        href: "/programa",
        disponible: true,
        detalle: "2 competencias, 5 resultados",
      },
      {
        id: "estructura-curricular",
        label: "Estructura curricular",
        tipo: "contenido",
        estado: "EN_REVISION",
        href: "/programa",
        disponible: true,
        detalle: "7 conocimientos y 9 criterios",
      },
      {
        id: "proyecto",
        label: "Proyecto",
        tipo: "wizard",
        estado: "BLOQUEADO",
        href: `/proyecto/${referenciaId}`,
        disponible: false,
        detalle: "0 fases, 0 actividades",
      },
      {
        id: "planeacion",
        label: "Planeacion",
        tipo: "wizard",
        estado: "BLOQUEADO",
        href: `/planeacion/${referenciaId}`,
        disponible: false,
        detalle: "0 completas, 0 borradores",
      },
    ],
    graph_edges: [
      {
        origen: "programa",
        destino: "estructura-curricular",
        estado: "ACTIVA",
        label: "importa y organiza",
      },
      {
        origen: "estructura-curricular",
        destino: "proyecto",
        estado: "BLOQUEADA",
        label: "habilita si programa esta COMPLETO",
      },
      {
        origen: "proyecto",
        destino: "planeacion",
        estado: "BLOQUEADA",
        label: "habilita si proyecto esta COMPLETO",
      },
    ],
    ...overrides,
  };
}

function buildProgramFlow(
  overrides: Partial<DashboardProgramFlow> = {},
): DashboardProgramFlow {
  return {
    referencia_id: referenciaId,
    estado: "EN_REVISION",
    paso_actual: "revision-programa",
    ultima_edicion: "2026-06-18T14:30:00Z",
    titulo: "Analisis de software / 228118",
    codigo_programa: "228118",
    nombre_programa: "Analisis de software",
    href: `/programa?referencia_id=${referenciaId}`,
    ...overrides,
  };
}

function mockFetchJson(
  payload: DashboardResponse,
  flows: DashboardProgramFlow[] = [],
): void {
  let currentFlows = [...flows];
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (init?.method === "DELETE") {
        const referenceId = url.split("/dashboard/programas/")[1] ?? "";
        currentFlows = currentFlows.filter(
          (flow) => flow.referencia_id !== referenceId,
        );
        return Promise.resolve({
          ok: true,
          status: 204,
          json: async () => ({}),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () =>
          url.endsWith("/dashboard/programas") ? currentFlows : payload,
      });
    }),
  );
}

describe("MasterDashboard", () => {
  it("renders dashboard metrics and blocked downstream modules", async () => {
    localStorage.setItem("sena.active-programa-draft-reference", referenciaId);
    mockFetchJson(buildDashboard(), [buildProgramFlow()]);

    render(<MasterDashboard />);

    expect(await screen.findAllByText("PROGRAMA_EN_CURSO")).toHaveLength(2);
    expect(screen.getByText("Flujos abiertos de programa")).toBeInTheDocument();
    expect(screen.getByText("Analisis de software / 228118")).toBeInTheDocument();
    expect(screen.getByText("Programa de formacion")).toBeInTheDocument();
    expect(screen.getByText("Proyecto formativo")).toBeInTheDocument();
    expect(screen.getByText("Planeacion pedagogica")).toBeInTheDocument();
    expect(screen.getByText("Competencias")).toBeInTheDocument();
    expect(screen.getByText("Resultados")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getAllByText("No disponible")).toHaveLength(2);
    expect(
      screen.getByText("habilita si programa esta COMPLETO"),
    ).toBeInTheDocument();
  });

  it("renders enabled navigation when project and planning are available", async () => {
    localStorage.setItem("sena.active-programa-draft-reference", referenciaId);
    const enabled = buildDashboard({
      estado_global: "LISTO_PARA_PLANEACION",
      resumen:
        "Programa y proyecto completos; la planeacion pedagogica esta habilitada.",
    });
    enabled.modules = enabled.modules.map((module) =>
      module.id === "programa"
        ? { ...module, estado: "COMPLETO", avance_porcentaje: 100 }
        : {
            ...module,
            estado: module.id === "planeacion" ? "DISPONIBLE" : "COMPLETO",
            disponible: true,
            motivo_bloqueo: null,
            avance_porcentaje: module.id === "planeacion" ? 0 : 100,
          },
    );
    enabled.metricas.proyecto = {
      estado: "COMPLETO",
      fases: 3,
      actividades: 8,
      fuente_estructurada_cargada: true,
    };
    enabled.graph_nodes = enabled.graph_nodes.map((node) => ({
      ...node,
      estado: node.id === "planeacion" ? "DISPONIBLE" : "COMPLETO",
      disponible: true,
    }));
    enabled.graph_edges = enabled.graph_edges.map((edge) => ({
      ...edge,
      estado: "ACTIVA",
    }));
    mockFetchJson(enabled, [buildProgramFlow({ estado: "BORRADOR" })]);

    render(<MasterDashboard />);

    expect(await screen.findAllByText("LISTO_PARA_PLANEACION")).toHaveLength(2);
    await waitFor(() =>
      expect(screen.queryByText("No disponible")).not.toBeInTheDocument(),
    );
    expect(screen.getAllByRole("link", { name: /abrir modulo/i })).toHaveLength(3);
    expect(screen.getByText("Fases")).toBeInTheDocument();
    expect(screen.getByText("Actividades")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(
      screen.getByText("habilita si proyecto esta COMPLETO"),
    ).toBeInTheDocument();
  });

  it("allows starting a new program flow from the master panel", async () => {
    localStorage.setItem("sena.active-programa-draft-reference", referenciaId);
    mockFetchJson(buildDashboard(), [buildProgramFlow()]);

    render(<MasterDashboard />);

    const newProgramLink = await screen.findByRole("link", {
      name: /nuevo programa/i,
    });
    fireEvent.click(newProgramLink);

    expect(localStorage.getItem("sena.active-programa-draft-reference")).toBeNull();
    expect(newProgramLink).toHaveAttribute("href", "/programa?nuevo=programa");
  });

  it("selects and deletes the selected open program flow", async () => {
    localStorage.setItem("sena.active-programa-draft-reference", referenciaId);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mockFetchJson(buildDashboard(), [buildProgramFlow()]);

    render(<MasterDashboard />);

    const flowSelect = await screen.findByRole("combobox", {
      name: /seleccionar flujo abierto/i,
    });
    fireEvent.change(flowSelect, { target: { value: referenciaId } });
    fireEvent.click(screen.getByRole("button", { name: /eliminar/i }));

    await waitFor(() =>
      expect(
        localStorage.getItem("sena.active-programa-draft-reference"),
      ).toBeNull(),
    );
    await waitFor(() =>
      expect(screen.queryByText("Analisis de software / 228118")).not.toBeInTheDocument(),
    );
    expect(window.confirm).toHaveBeenCalledWith(
      expect.stringContaining("Vas a eliminar el flujo abierto"),
    );
  });
});
