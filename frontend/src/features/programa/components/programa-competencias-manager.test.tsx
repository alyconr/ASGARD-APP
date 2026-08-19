import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProgramaCompetenciasManager } from "./programa-competencias-manager";
import * as competenciasApi from "@/features/programa/competencias-api";
import * as criteriosApi from "@/features/programa/criterios-api";
import * as conocimientosProcesoApi from "@/features/programa/conocimientos-proceso-api";
import * as conocimientosSaberApi from "@/features/programa/conocimientos-saber-api";
import * as resultadosApi from "@/features/programa/resultados-api";
import type {
  ConocimientoCurricular,
  ConocimientoProcesoListResponse,
  ConocimientoSaberListResponse,
  CriterioListResponse,
  ProgramaCompetencia,
  ProgramaCompetenciaListResponse,
  ResultadoAprendizaje,
  ResultadoAprendizajeListResponse,
} from "@/features/programa/types";

vi.mock("@/components/feedback/notifications", () => ({
  notify: {
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
  },
}));

vi.mock("@/features/programa/competencias-api", () => ({
  ProgramaCompetenciaError: class ProgramaCompetenciaError extends Error {
    readonly status: number;

    readonly detail: string;

    constructor(status: number, detail: string) {
      super(detail);
      this.status = status;
      this.detail = detail;
    }
  },
  createProgramaCompetencia: vi.fn(),
  deleteProgramaCompetencia: vi.fn(),
  listProgramaCompetencias: vi.fn(),
  updateProgramaCompetencia: vi.fn(),
}));

vi.mock("@/features/programa/resultados-api", () => ({
  ProgramaResultadoError: class ProgramaResultadoError extends Error {
    readonly status: number;

    readonly detail: string;

    constructor(status: number, detail: string) {
      super(detail);
      this.status = status;
      this.detail = detail;
    }
  },
  createProgramaResultado: vi.fn(),
  deleteProgramaResultado: vi.fn(),
  listProgramaResultados: vi.fn(),
  updateProgramaResultado: vi.fn(),
}));

vi.mock("@/features/programa/conocimientos-saber-api", () => ({
  ProgramaConocimientoSaberError: class ProgramaConocimientoSaberError extends Error {
    readonly status: number;

    readonly detail: string;

    constructor(status: number, detail: string) {
      super(detail);
      this.status = status;
      this.detail = detail;
    }
  },
  createProgramaConocimientoSaber: vi.fn(),
  deleteProgramaConocimientoSaber: vi.fn(),
  listProgramaConocimientosSaber: vi.fn(),
  updateProgramaConocimientoSaber: vi.fn(),
}));

vi.mock("@/features/programa/conocimientos-proceso-api", () => ({
  ProgramaConocimientoProcesoError: class ProgramaConocimientoProcesoError extends Error {
    readonly status: number;

    readonly detail: string;

    constructor(status: number, detail: string) {
      super(detail);
      this.status = status;
      this.detail = detail;
    }
  },
  createProgramaConocimientoProceso: vi.fn(),
  deleteProgramaConocimientoProceso: vi.fn(),
  listProgramaConocimientosProceso: vi.fn(),
  updateProgramaConocimientoProceso: vi.fn(),
}));

vi.mock("@/features/programa/criterios-api", () => ({
  ProgramaCriterioError: class ProgramaCriterioError extends Error {
    readonly status: number;

    readonly detail: string;

    constructor(status: number, detail: string) {
      super(detail);
      this.status = status;
      this.detail = detail;
    }
  },
  createProgramaCriterio: vi.fn(),
  deleteProgramaCriterio: vi.fn(),
  listProgramaCriterios: vi.fn(),
  updateProgramaCriterio: vi.fn(),
}));

const referenciaId = "12345678-1234-4234-9234-123456789abc";

function buildCompetencia(
  overrides: Partial<ProgramaCompetencia> = {},
): ProgramaCompetencia {
  return {
    id: "aaaaaaaa-aaaa-4aaa-9aaa-aaaaaaaaaaaa",
    programa_id: "bbbbbbbb-bbbb-4bbb-9bbb-bbbbbbbbbbbb",
    codigo_competencia: "220501046",
    nombre_competencia: "Desarrollar software",
    orden: 1,
    estado: "BORRADOR",
    origen_campo: "MANUAL",
    fecha_creacion: "2026-04-28T00:00:00Z",
    fecha_actualizacion: "2026-04-28T00:00:00Z",
    ...overrides,
  };
}

function buildResponse(
  competencias: ProgramaCompetencia[],
): ProgramaCompetenciaListResponse {
  return {
    referencia_id: referenciaId,
    programa_id: competencias[0]?.programa_id ?? null,
    competencias,
  };
}

function buildResultado(
  competenciaId: string,
  overrides: Partial<ResultadoAprendizaje> = {},
): ResultadoAprendizaje {
  return {
    id: "cccccccc-cccc-4ccc-9ccc-cccccccccccc",
    competencia_id: competenciaId,
    codigo_resultado: "RAP-01",
    descripcion: "Analizar los requisitos del software",
    orden: 1,
    estado: "MANUAL",
    fecha_creacion: "2026-05-11T00:00:00Z",
    fecha_actualizacion: "2026-05-11T00:00:00Z",
    ...overrides,
  };
}

function buildResultadoResponse(
  competenciaId: string,
  resultados: ResultadoAprendizaje[],
): ResultadoAprendizajeListResponse {
  return {
    referencia_id: referenciaId,
    competencia_id: competenciaId,
    resultados,
  };
}

function buildConocimientoSaber(
  competenciaId: string,
  overrides: Partial<ConocimientoCurricular> = {},
): ConocimientoCurricular {
  return {
    id: "dddddddd-dddd-4ddd-9ddd-dddddddddddd",
    competencia_id: competenciaId,
    resultado_id: null,
    tipo: "SABER",
    descripcion: "Arquitectura de software",
    orden: 1,
    estado: "MANUAL",
    fecha_creacion: "2026-05-14T00:00:00Z",
    fecha_actualizacion: "2026-05-14T00:00:00Z",
    ...overrides,
  };
}

function buildConocimientoSaberResponse(
  competenciaId: string,
  conocimientos: ConocimientoCurricular[],
): ConocimientoSaberListResponse {
  return {
    referencia_id: referenciaId,
    competencia_id: competenciaId,
    conocimientos,
  };
}

function buildConocimientoProceso(
  competenciaId: string,
  overrides: Partial<ConocimientoCurricular> = {},
): ConocimientoCurricular {
  return {
    id: "eeeeeeee-eeee-4eee-9eee-eeeeeeeeeeee",
    competencia_id: competenciaId,
    resultado_id: null,
    tipo: "PROCESO",
    descripcion: "Codificar solucion por competencia",
    orden: 1,
    estado: "MANUAL",
    fecha_creacion: "2026-05-14T00:00:00Z",
    fecha_actualizacion: "2026-05-14T00:00:00Z",
    ...overrides,
  };
}

function buildConocimientoProcesoResponse(
  competenciaId: string,
  conocimientos: ConocimientoCurricular[],
): ConocimientoProcesoListResponse {
  return {
    referencia_id: referenciaId,
    competencia_id: competenciaId,
    conocimientos,
  };
}

function buildCriterioResponse(
  competenciaId: string,
  criterios: import("@/features/programa/types").CriterioEvaluacionCurricular[],
): CriterioListResponse {
  return {
    referencia_id: referenciaId,
    competencia_id: competenciaId,
    criterios,
  };
}

describe("ProgramaCompetenciasManager", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(competenciasApi.listProgramaCompetencias).mockResolvedValue(
      buildResponse([]),
    );
    vi.mocked(resultadosApi.listProgramaResultados).mockImplementation(
      async (_referenciaId: string, competenciaId: string) =>
        buildResultadoResponse(competenciaId, []),
    );
    vi.mocked(
      conocimientosSaberApi.listProgramaConocimientosSaber,
    ).mockImplementation(async (_referenciaId: string, competenciaId: string) =>
      buildConocimientoSaberResponse(competenciaId, []),
    );
    vi.mocked(
      conocimientosProcesoApi.listProgramaConocimientosProceso,
    ).mockImplementation(async (_referenciaId: string, competenciaId: string) =>
      buildConocimientoProcesoResponse(competenciaId, []),
    );
    vi.mocked(criteriosApi.listProgramaCriterios).mockImplementation(
      async (_referenciaId: string, competenciaId: string) =>
        buildCriterioResponse(competenciaId, []),
    );
  });

  it("should show empty state and load persisted competencias", async () => {
    const onCompetenciasSynced = vi.fn();

    render(
      <ProgramaCompetenciasManager
        competencias={[]}
        referenciaId={referenciaId}
        onCompetenciasSynced={onCompetenciasSynced}
      />,
    );

    expect(screen.getByText("Sin competencias registradas")).toBeInTheDocument();
    await waitFor(() => {
      expect(competenciasApi.listProgramaCompetencias).toHaveBeenCalledWith(
        referenciaId,
      );
    });
    expect(onCompetenciasSynced).toHaveBeenCalledWith(buildResponse([]));
  });

  it("should create a competencia from valid form values", async () => {
    const competencia = buildCompetencia();
    vi.mocked(competenciasApi.createProgramaCompetencia).mockResolvedValue(
      buildResponse([competencia]),
    );
    const onCompetenciasSynced = vi.fn();

    render(
      <ProgramaCompetenciasManager
        competencias={[]}
        referenciaId={referenciaId}
        onCompetenciasSynced={onCompetenciasSynced}
      />,
    );
    await waitFor(() => {
      expect(
        screen.queryByText("Cargando competencias del borrador..."),
      ).not.toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText("Ej. 220501046"), {
      target: { value: " 220501046 " },
    });
    fireEvent.change(
      screen.getByPlaceholderText("Describe la competencia del programa."),
      {
        target: { value: " Desarrollar software " },
      },
    );
    fireEvent.submit(
      screen
        .getByRole("button", { name: /crear competencia/i })
        .closest("form") as HTMLFormElement,
    );

    await waitFor(() => {
      expect(competenciasApi.createProgramaCompetencia).toHaveBeenCalledWith(
        referenciaId,
        {
          codigo_competencia: "220501046",
          nombre_competencia: "Desarrollar software",
        },
      );
    });
    expect(onCompetenciasSynced).toHaveBeenCalledWith(buildResponse([competencia]));
  });

  it("should show validation message for blank code", async () => {
    const onCompetenciasSynced = vi.fn();

    render(
      <ProgramaCompetenciasManager
        competencias={[]}
        referenciaId={referenciaId}
        onCompetenciasSynced={onCompetenciasSynced}
      />,
    );
    await waitFor(() => {
      expect(
        screen.queryByText("Cargando competencias del borrador..."),
      ).not.toBeInTheDocument();
    });

    fireEvent.change(
      screen.getByPlaceholderText("Describe la competencia del programa."),
      {
        target: { value: "Desarrollar software" },
      },
    );
    fireEvent.submit(
      screen
        .getByRole("button", { name: /crear competencia/i })
        .closest("form") as HTMLFormElement,
    );

    await waitFor(() => {
      expect(
        screen.getByText("codigo_competencia es obligatorio."),
      ).toBeInTheDocument();
    });
    expect(competenciasApi.createProgramaCompetencia).not.toHaveBeenCalled();
  });

  it("should edit an existing competencia", async () => {
    const competencia = buildCompetencia();
    const updated = buildCompetencia({
      codigo_competencia: "220501047",
      nombre_competencia: "Implementar soluciones de software",
    });
    vi.mocked(competenciasApi.updateProgramaCompetencia).mockResolvedValue(
      buildResponse([updated]),
    );
    const onCompetenciasSynced = vi.fn();

    render(
      <ProgramaCompetenciasManager
        competencias={[competencia]}
        referenciaId={referenciaId}
        onCompetenciasSynced={onCompetenciasSynced}
      />,
    );
    await waitFor(() => {
      expect(
        screen.queryByText("Cargando competencias del borrador..."),
      ).not.toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /editar/i }));
    fireEvent.change(screen.getByPlaceholderText("Ej. 220501046"), {
      target: { value: "220501047" },
    });
    fireEvent.change(
      screen.getByPlaceholderText("Describe la competencia del programa."),
      {
        target: { value: "Implementar soluciones de software" },
      },
    );
    fireEvent.submit(
      screen
        .getByRole("button", { name: /guardar cambios/i })
        .closest("form") as HTMLFormElement,
    );

    await waitFor(() => {
      expect(competenciasApi.updateProgramaCompetencia).toHaveBeenCalledWith(
        referenciaId,
        competencia.id,
        {
          codigo_competencia: "220501047",
          nombre_competencia: "Implementar soluciones de software",
        },
      );
    });
    expect(onCompetenciasSynced).toHaveBeenCalledWith(buildResponse([updated]));
  });

  it("should delete only after explicit confirmation", async () => {
    const competencia = buildCompetencia();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(competenciasApi.deleteProgramaCompetencia).mockResolvedValue({
      referencia_id: referenciaId,
      programa_id: competencia.programa_id,
      competencia_id: competencia.id,
      eliminado: true,
    });
    vi.mocked(competenciasApi.listProgramaCompetencias).mockResolvedValue(
      buildResponse([]),
    );
    const onCompetenciasSynced = vi.fn();

    render(
      <ProgramaCompetenciasManager
        competencias={[competencia]}
        referenciaId={referenciaId}
        onCompetenciasSynced={onCompetenciasSynced}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /eliminar/i }));

    await waitFor(() => {
      expect(competenciasApi.deleteProgramaCompetencia).toHaveBeenCalledWith(
        referenciaId,
        competencia.id,
      );
    });
    expect(onCompetenciasSynced).toHaveBeenCalledWith(buildResponse([]));
  });

  it("should create a learning outcome inside a competencia", async () => {
    const competencia = buildCompetencia();
    const resultado = buildResultado(competencia.id);
    vi.mocked(resultadosApi.createProgramaResultado).mockResolvedValue(
      buildResultadoResponse(competencia.id, [resultado]),
    );
    const onCompetenciasSynced = vi.fn();

    render(
      <ProgramaCompetenciasManager
        competencias={[competencia]}
        referenciaId={referenciaId}
        onCompetenciasSynced={onCompetenciasSynced}
      />,
    );
    expect(screen.getByText("Resultados de aprendizaje")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Ej. RAP-01"), {
      target: { value: " RAP-01 " },
    });
    fireEvent.change(
      screen.getByPlaceholderText("Describe el resultado de aprendizaje."),
      {
        target: { value: " Analizar los requisitos del software " },
      },
    );
    fireEvent.submit(
      screen
        .getByRole("button", { name: /crear resultado/i })
        .closest("form") as HTMLFormElement,
    );

    await waitFor(() => {
      expect(resultadosApi.createProgramaResultado).toHaveBeenCalledWith(
        referenciaId,
        competencia.id,
        {
          codigo_resultado: "RAP-01",
          descripcion: "Analizar los requisitos del software",
        },
      );
    });
    expect(onCompetenciasSynced).toHaveBeenCalledWith(
      buildResponse([{ ...competencia, resultados: [resultado] }]),
    );
  });

  it("should edit a learning outcome inside a competencia", async () => {
    const competencia = buildCompetencia();
    const resultado = buildResultado(competencia.id);
    const updated = buildResultado(competencia.id, {
      id: resultado.id,
      codigo_resultado: "RAP-02",
      descripcion: "Disenar la solucion de software",
    });
    vi.mocked(resultadosApi.listProgramaResultados).mockResolvedValue(
      buildResultadoResponse(competencia.id, [resultado]),
    );
    vi.mocked(resultadosApi.updateProgramaResultado).mockResolvedValue(
      buildResultadoResponse(competencia.id, [updated]),
    );
    const onCompetenciasSynced = vi.fn();

    render(
      <ProgramaCompetenciasManager
        competencias={[{ ...competencia, resultados: [resultado] }]}
        referenciaId={referenciaId}
        onCompetenciasSynced={onCompetenciasSynced}
      />,
    );

    expect(
      await screen.findByText("Analizar los requisitos del software"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: /editar/i })[1]);
    fireEvent.change(screen.getByPlaceholderText("Ej. RAP-01"), {
      target: { value: " RAP-02 " },
    });
    fireEvent.change(
      screen.getByPlaceholderText("Describe el resultado de aprendizaje."),
      {
        target: { value: " Disenar la solucion de software " },
      },
    );
    fireEvent.submit(
      screen
        .getByRole("button", { name: /guardar resultado/i })
        .closest("form") as HTMLFormElement,
    );

    await waitFor(() => {
      expect(resultadosApi.updateProgramaResultado).toHaveBeenCalledWith(
        referenciaId,
        competencia.id,
        resultado.id,
        {
          codigo_resultado: "RAP-02",
          descripcion: "Disenar la solucion de software",
        },
      );
    });
    expect(onCompetenciasSynced).toHaveBeenCalledWith(
      buildResponse([{ ...competencia, resultados: [updated] }]),
    );
  });

  it("should delete a learning outcome after confirmation", async () => {
    const competencia = buildCompetencia();
    const resultado = buildResultado(competencia.id);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(resultadosApi.listProgramaResultados).mockResolvedValue(
      buildResultadoResponse(competencia.id, []),
    );
    vi.mocked(resultadosApi.deleteProgramaResultado).mockResolvedValue({
      referencia_id: referenciaId,
      competencia_id: competencia.id,
      resultado_id: resultado.id,
      eliminado: true,
    });
    const onCompetenciasSynced = vi.fn();

    render(
      <ProgramaCompetenciasManager
        competencias={[{ ...competencia, resultados: [resultado] }]}
        referenciaId={referenciaId}
        onCompetenciasSynced={onCompetenciasSynced}
      />,
    );

    expect(
      await screen.findByText("Analizar los requisitos del software"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: /eliminar/i })[1]);

    await waitFor(() => {
      expect(resultadosApi.deleteProgramaResultado).toHaveBeenCalledWith(
        referenciaId,
        competencia.id,
        resultado.id,
      );
    });
    expect(onCompetenciasSynced).toHaveBeenLastCalledWith(
      buildResponse([{ ...competencia, resultados: [] }]),
    );
  });

  it("should reject blank learning outcome descriptions before calling the API", async () => {
    const competencia = buildCompetencia();
    const onCompetenciasSynced = vi.fn();

    render(
      <ProgramaCompetenciasManager
        competencias={[competencia]}
        referenciaId={referenciaId}
        onCompetenciasSynced={onCompetenciasSynced}
      />,
    );
    expect(screen.getByText("Resultados de aprendizaje")).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText("Describe el resultado de aprendizaje."),
      {
        target: { value: "   " },
      },
    );
    fireEvent.submit(
      screen
        .getByRole("button", { name: /crear resultado/i })
        .closest("form") as HTMLFormElement,
    );

    expect(
      await screen.findByText("descripcion es obligatoria."),
    ).toBeInTheDocument();
    expect(resultadosApi.createProgramaResultado).not.toHaveBeenCalled();
  });

  it("should show API errors such as duplicate learning outcomes", async () => {
    const competencia = buildCompetencia();
    vi.mocked(resultadosApi.createProgramaResultado).mockRejectedValue(
      new resultadosApi.ProgramaResultadoError(
        409,
        "Ya existe un resultado de aprendizaje con esta descripcion exacta en la competencia",
      ),
    );

    render(
      <ProgramaCompetenciasManager
        competencias={[competencia]}
        referenciaId={referenciaId}
        onCompetenciasSynced={vi.fn()}
      />,
    );
    expect(screen.getByText("Resultados de aprendizaje")).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText("Describe el resultado de aprendizaje."),
      {
        target: { value: "Analizar requisitos" },
      },
    );
    fireEvent.submit(
      screen
        .getByRole("button", { name: /crear resultado/i })
        .closest("form") as HTMLFormElement,
    );

    expect(
      await screen.findByText(
        "Ya existe un resultado de aprendizaje con esta descripcion exacta en la competencia",
      ),
    ).toBeInTheDocument();
  });

  it("should create a SABER knowledge item without affecting PROCESO", async () => {
    const proceso: ConocimientoCurricular = buildConocimientoSaber(
      "aaaaaaaa-aaaa-4aaa-9aaa-aaaaaaaaaaaa",
      {
        id: "eeeeeeee-eeee-4eee-9eee-eeeeeeeeeeee",
        tipo: "PROCESO",
        descripcion: "Codificar solucion por competencia",
      },
    );
    const competencia = buildCompetencia({ conocimientos: [proceso] });
    const saber = buildConocimientoSaber(competencia.id);
    vi.mocked(
      conocimientosSaberApi.createProgramaConocimientoSaber,
    ).mockResolvedValue(buildConocimientoSaberResponse(competencia.id, [saber]));
    const onCompetenciasSynced = vi.fn();

    render(
      <ProgramaCompetenciasManager
        competencias={[competencia]}
        referenciaId={referenciaId}
        onCompetenciasSynced={onCompetenciasSynced}
      />,
    );
    expect(screen.getByText("Conocimientos")).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText("Describe el conocimiento de saber."),
      {
        target: { value: " Arquitectura de software " },
      },
    );
    fireEvent.submit(
      screen
        .getByRole("button", { name: /crear saber/i })
        .closest("form") as HTMLFormElement,
    );

    await waitFor(() => {
      expect(
        conocimientosSaberApi.createProgramaConocimientoSaber,
      ).toHaveBeenCalledWith(referenciaId, competencia.id, {
        descripcion: "Arquitectura de software",
      });
    });
    expect(onCompetenciasSynced).toHaveBeenCalledWith(
      buildResponse([{ ...competencia, conocimientos: [saber, proceso] }]),
    );
  });

  it("should edit a SABER knowledge item inside a competencia", async () => {
    const competencia = buildCompetencia();
    const saber = buildConocimientoSaber(competencia.id);
    const updated = buildConocimientoSaber(competencia.id, {
      id: saber.id,
      descripcion: "Patrones de arquitectura",
    });
    vi.mocked(
      conocimientosSaberApi.listProgramaConocimientosSaber,
    ).mockResolvedValue(buildConocimientoSaberResponse(competencia.id, [saber]));
    vi.mocked(
      conocimientosSaberApi.updateProgramaConocimientoSaber,
    ).mockResolvedValue(buildConocimientoSaberResponse(competencia.id, [updated]));
    const onCompetenciasSynced = vi.fn();

    render(
      <ProgramaCompetenciasManager
        competencias={[{ ...competencia, conocimientos: [saber] }]}
        referenciaId={referenciaId}
        onCompetenciasSynced={onCompetenciasSynced}
      />,
    );

    fireEvent.change(screen.getByLabelText("Seleccionar conocimiento SABER"), {
      target: { value: saber.id },
    });
    expect(await screen.findAllByText("Arquitectura de software")).toHaveLength(2);
    fireEvent.click(screen.getAllByRole("button", { name: /editar/i })[1]);
    fireEvent.change(
      screen.getByPlaceholderText("Describe el conocimiento de saber."),
      {
        target: { value: " Patrones de arquitectura " },
      },
    );
    fireEvent.submit(
      screen
        .getByRole("button", { name: /guardar saber/i })
        .closest("form") as HTMLFormElement,
    );

    await waitFor(() => {
      expect(
        conocimientosSaberApi.updateProgramaConocimientoSaber,
      ).toHaveBeenCalledWith(referenciaId, competencia.id, saber.id, {
        descripcion: "Patrones de arquitectura",
      });
    });
    expect(onCompetenciasSynced).toHaveBeenCalledWith(
      buildResponse([{ ...competencia, conocimientos: [updated] }]),
    );
  });

  it("should delete a SABER knowledge item after confirmation", async () => {
    const competencia = buildCompetencia();
    const saber = buildConocimientoSaber(competencia.id);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(conocimientosSaberApi.listProgramaConocimientosSaber).mockResolvedValue(
      buildConocimientoSaberResponse(competencia.id, []),
    );
    vi.mocked(
      conocimientosSaberApi.deleteProgramaConocimientoSaber,
    ).mockResolvedValue({
      referencia_id: referenciaId,
      competencia_id: competencia.id,
      conocimiento_id: saber.id,
      eliminado: true,
    });
    const onCompetenciasSynced = vi.fn();

    render(
      <ProgramaCompetenciasManager
        competencias={[{ ...competencia, conocimientos: [saber] }]}
        referenciaId={referenciaId}
        onCompetenciasSynced={onCompetenciasSynced}
      />,
    );

    fireEvent.change(screen.getByLabelText("Seleccionar conocimiento SABER"), {
      target: { value: saber.id },
    });
    expect(await screen.findAllByText("Arquitectura de software")).toHaveLength(2);
    fireEvent.click(screen.getAllByRole("button", { name: /eliminar/i })[1]);

    await waitFor(() => {
      expect(
        conocimientosSaberApi.deleteProgramaConocimientoSaber,
      ).toHaveBeenCalledWith(referenciaId, competencia.id, saber.id);
    });
    expect(onCompetenciasSynced).toHaveBeenLastCalledWith(
      buildResponse([{ ...competencia, conocimientos: [] }]),
    );
  });

  it("should reject blank SABER descriptions before calling the API", async () => {
    const competencia = buildCompetencia();

    render(
      <ProgramaCompetenciasManager
        competencias={[competencia]}
        referenciaId={referenciaId}
        onCompetenciasSynced={vi.fn()}
      />,
    );
    expect(screen.getByText("Conocimientos")).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText("Describe el conocimiento de saber."),
      {
        target: { value: "   " },
      },
    );
    fireEvent.submit(
      screen
        .getByRole("button", { name: /crear saber/i })
        .closest("form") as HTMLFormElement,
    );

    expect(
      await screen.findByText("descripcion es obligatoria."),
    ).toBeInTheDocument();
    expect(
      conocimientosSaberApi.createProgramaConocimientoSaber,
    ).not.toHaveBeenCalled();
  });

  it("should show API errors such as duplicate SABER knowledge", async () => {
    const competencia = buildCompetencia();
    vi.mocked(
      conocimientosSaberApi.createProgramaConocimientoSaber,
    ).mockRejectedValue(
      new conocimientosSaberApi.ProgramaConocimientoSaberError(
        409,
        "Ya existe un conocimiento SABER con esta descripcion exacta en la competencia",
      ),
    );

    render(
      <ProgramaCompetenciasManager
        competencias={[competencia]}
        referenciaId={referenciaId}
        onCompetenciasSynced={vi.fn()}
      />,
    );
    expect(screen.getByText("Conocimientos")).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText("Describe el conocimiento de saber."),
      {
        target: { value: "Arquitectura" },
      },
    );
    fireEvent.submit(
      screen
        .getByRole("button", { name: /crear saber/i })
        .closest("form") as HTMLFormElement,
    );

    expect(
      await screen.findByText(
        "Ya existe un conocimiento SABER con esta descripcion exacta en la competencia",
      ),
    ).toBeInTheDocument();
  });

  it("should create a PROCESO knowledge item without affecting SABER", async () => {
    const saber = buildConocimientoSaber(
      "aaaaaaaa-aaaa-4aaa-9aaa-aaaaaaaaaaaa",
    );
    const competencia = buildCompetencia({ conocimientos: [saber] });
    const proceso = buildConocimientoProceso(competencia.id);
    vi.mocked(
      conocimientosProcesoApi.createProgramaConocimientoProceso,
    ).mockResolvedValue(buildConocimientoProcesoResponse(competencia.id, [proceso]));
    const onCompetenciasSynced = vi.fn();

    render(
      <ProgramaCompetenciasManager
        competencias={[competencia]}
        referenciaId={referenciaId}
        onCompetenciasSynced={onCompetenciasSynced}
      />,
    );
    expect(screen.getByText("Conocimientos")).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText("Describe el conocimiento de proceso."),
      {
        target: { value: " Codificar solucion por competencia " },
      },
    );
    fireEvent.submit(
      screen
        .getByRole("button", { name: /crear proceso/i })
        .closest("form") as HTMLFormElement,
    );

    await waitFor(() => {
      expect(
        conocimientosProcesoApi.createProgramaConocimientoProceso,
      ).toHaveBeenCalledWith(referenciaId, competencia.id, {
        descripcion: "Codificar solucion por competencia",
      });
    });
    expect(onCompetenciasSynced).toHaveBeenCalledWith(
      buildResponse([{ ...competencia, conocimientos: [saber, proceso] }]),
    );
  });

  it("should edit a PROCESO knowledge item inside a competencia", async () => {
    const competencia = buildCompetencia();
    const proceso = buildConocimientoProceso(competencia.id);
    const updated = buildConocimientoProceso(competencia.id, {
      id: proceso.id,
      descripcion: "Automatizar despliegue por competencia",
    });
    vi.mocked(
      conocimientosProcesoApi.listProgramaConocimientosProceso,
    ).mockResolvedValue(buildConocimientoProcesoResponse(competencia.id, [proceso]));
    vi.mocked(
      conocimientosProcesoApi.updateProgramaConocimientoProceso,
    ).mockResolvedValue(buildConocimientoProcesoResponse(competencia.id, [updated]));
    const onCompetenciasSynced = vi.fn();

    render(
      <ProgramaCompetenciasManager
        competencias={[{ ...competencia, conocimientos: [proceso] }]}
        referenciaId={referenciaId}
        onCompetenciasSynced={onCompetenciasSynced}
      />,
    );

    fireEvent.change(screen.getByLabelText("Seleccionar conocimiento PROCESO"), {
      target: { value: proceso.id },
    });
    expect(
      await screen.findAllByText("Codificar solucion por competencia"),
    ).toHaveLength(2);
    fireEvent.click(screen.getAllByRole("button", { name: /editar/i })[1]);
    fireEvent.change(
      screen.getByPlaceholderText("Describe el conocimiento de proceso."),
      {
        target: { value: " Automatizar despliegue por competencia " },
      },
    );
    fireEvent.submit(
      screen
        .getByRole("button", { name: /guardar proceso/i })
        .closest("form") as HTMLFormElement,
    );

    await waitFor(() => {
      expect(
        conocimientosProcesoApi.updateProgramaConocimientoProceso,
      ).toHaveBeenCalledWith(referenciaId, competencia.id, proceso.id, {
        descripcion: "Automatizar despliegue por competencia",
      });
    });
    expect(onCompetenciasSynced).toHaveBeenCalledWith(
      buildResponse([{ ...competencia, conocimientos: [updated] }]),
    );
  });

  it("should delete a PROCESO knowledge item after confirmation", async () => {
    const competencia = buildCompetencia();
    const proceso = buildConocimientoProceso(competencia.id);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(conocimientosProcesoApi.listProgramaConocimientosProceso).mockResolvedValue(
      buildConocimientoProcesoResponse(competencia.id, []),
    );
    vi.mocked(
      conocimientosProcesoApi.deleteProgramaConocimientoProceso,
    ).mockResolvedValue({
      referencia_id: referenciaId,
      competencia_id: competencia.id,
      conocimiento_id: proceso.id,
      eliminado: true,
    });
    const onCompetenciasSynced = vi.fn();

    render(
      <ProgramaCompetenciasManager
        competencias={[{ ...competencia, conocimientos: [proceso] }]}
        referenciaId={referenciaId}
        onCompetenciasSynced={onCompetenciasSynced}
      />,
    );

    fireEvent.change(screen.getByLabelText("Seleccionar conocimiento PROCESO"), {
      target: { value: proceso.id },
    });
    expect(
      await screen.findAllByText("Codificar solucion por competencia"),
    ).toHaveLength(2);
    fireEvent.click(screen.getAllByRole("button", { name: /eliminar/i })[1]);

    await waitFor(() => {
      expect(
        conocimientosProcesoApi.deleteProgramaConocimientoProceso,
      ).toHaveBeenCalledWith(referenciaId, competencia.id, proceso.id);
    });
    expect(onCompetenciasSynced).toHaveBeenLastCalledWith(
      buildResponse([{ ...competencia, conocimientos: [] }]),
    );
  });

  it("should reject blank PROCESO descriptions before calling the API", async () => {
    const competencia = buildCompetencia();

    render(
      <ProgramaCompetenciasManager
        competencias={[competencia]}
        referenciaId={referenciaId}
        onCompetenciasSynced={vi.fn()}
      />,
    );
    expect(screen.getByText("Conocimientos")).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText("Describe el conocimiento de proceso."),
      {
        target: { value: "   " },
      },
    );
    fireEvent.submit(
      screen
        .getByRole("button", { name: /crear proceso/i })
        .closest("form") as HTMLFormElement,
    );

    expect(
      await screen.findByText("descripcion es obligatoria."),
    ).toBeInTheDocument();
    expect(
      conocimientosProcesoApi.createProgramaConocimientoProceso,
    ).not.toHaveBeenCalled();
  });

  it("should show API errors such as duplicate PROCESO knowledge", async () => {
    const competencia = buildCompetencia();
    vi.mocked(
      conocimientosProcesoApi.createProgramaConocimientoProceso,
    ).mockRejectedValue(
      new conocimientosProcesoApi.ProgramaConocimientoProcesoError(
        409,
        "Ya existe un conocimiento PROCESO con esta descripcion exacta en la competencia",
      ),
    );

    render(
      <ProgramaCompetenciasManager
        competencias={[competencia]}
        referenciaId={referenciaId}
        onCompetenciasSynced={vi.fn()}
      />,
    );
    expect(screen.getByText("Conocimientos")).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText("Describe el conocimiento de proceso."),
      {
        target: { value: "Codificar solucion" },
      },
    );
    fireEvent.submit(
      screen
        .getByRole("button", { name: /crear proceso/i })
        .closest("form") as HTMLFormElement,
    );

    expect(
      await screen.findByText(
        "Ya existe un conocimiento PROCESO con esta descripcion exacta en la competencia",
      ),
    ).toBeInTheDocument();
  });

  it("should render competencia as the container for resultados, conocimientos and criterios", async () => {
    const competencia = buildCompetencia({
      resultados: [buildResultado("aaaaaaaa-aaaa-4aaa-9aaa-aaaaaaaaaaaa")],
      conocimientos: [
        {
          id: "dddddddd-dddd-4ddd-9ddd-dddddddddddd",
          competencia_id: "aaaaaaaa-aaaa-4aaa-9aaa-aaaaaaaaaaaa",
          resultado_id: null,
          tipo: "SABER",
          descripcion: "Arquitectura por competencia",
          orden: 1,
          estado: "VALIDADO",
          fecha_creacion: "2026-05-13T00:00:00Z",
          fecha_actualizacion: "2026-05-13T00:00:00Z",
        },
        {
          id: "eeeeeeee-eeee-4eee-9eee-eeeeeeeeeeee",
          competencia_id: "aaaaaaaa-aaaa-4aaa-9aaa-aaaaaaaaaaaa",
          resultado_id: null,
          tipo: "PROCESO",
          descripcion: "Codificar solucion por competencia",
          orden: 2,
          estado: "VALIDADO",
          fecha_creacion: "2026-05-13T00:00:00Z",
          fecha_actualizacion: "2026-05-13T00:00:00Z",
        },
      ],
      criterios: [
        {
          id: "ffffffff-ffff-4fff-9fff-ffffffffffff",
          competencia_id: "aaaaaaaa-aaaa-4aaa-9aaa-aaaaaaaaaaaa",
          resultado_id: null,
          descripcion: "Verifica componentes por competencia",
          orden: 1,
          estado: "VALIDADO",
          fecha_creacion: "2026-05-13T00:00:00Z",
          fecha_actualizacion: "2026-05-13T00:00:00Z",
        },
      ],
    });
    vi.mocked(resultadosApi.listProgramaResultados).mockResolvedValue(
      buildResultadoResponse(competencia.id, competencia.resultados ?? []),
    );
    vi.mocked(
      conocimientosSaberApi.listProgramaConocimientosSaber,
    ).mockResolvedValue(
      buildConocimientoSaberResponse(
        competencia.id,
        (competencia.conocimientos ?? []).filter(
          (item) => item.tipo === "SABER",
        ),
      ),
    );
    vi.mocked(
      conocimientosProcesoApi.listProgramaConocimientosProceso,
    ).mockResolvedValue(
      buildConocimientoProcesoResponse(
        competencia.id,
        (competencia.conocimientos ?? []).filter(
          (item) => item.tipo === "PROCESO",
        ),
      ),
    );
    vi.mocked(criteriosApi.listProgramaCriterios).mockResolvedValue(
      buildCriterioResponse(competencia.id, competencia.criterios ?? []),
    );

    render(
      <ProgramaCompetenciasManager
        competencias={[competencia]}
        referenciaId={referenciaId}
        onCompetenciasSynced={vi.fn()}
      />,
    );

    expect(screen.getByText("Resultados de aprendizaje")).toBeInTheDocument();
    expect(screen.getByText("Conocimientos")).toBeInTheDocument();
    expect(screen.getByText("Criterios de evaluacion")).toBeInTheDocument();
    expect(screen.getByText("Saber")).toBeInTheDocument();
    expect(screen.getByText("Proceso")).toBeInTheDocument();
    expect(
      screen.getByText("Los conocimientos SABER estan disponibles en el selector."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Los conocimientos PROCESO estan disponibles en el selector."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Los criterios estan disponibles en el selector."),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("Analizar los requisitos del software"),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Seleccionar conocimiento SABER"), {
      target: { value: "dddddddd-dddd-4ddd-9ddd-dddddddddddd" },
    });
    fireEvent.change(screen.getByLabelText("Seleccionar conocimiento PROCESO"), {
      target: { value: "eeeeeeee-eeee-4eee-9eee-eeeeeeeeeeee" },
    });
    fireEvent.change(screen.getByLabelText("Seleccionar criterio"), {
      target: { value: "ffffffff-ffff-4fff-9fff-ffffffffffff" },
    });
    expect(screen.getAllByText("Arquitectura por competencia")).toHaveLength(2);
    expect(
      screen.getAllByText("Codificar solucion por competencia"),
    ).toHaveLength(2);
    expect(
      screen.getAllByText("Verifica componentes por competencia"),
    ).toHaveLength(2);
  });

  it("should keep practical-stage competencias readable when they have no children", async () => {
    const competencia = buildCompetencia({
      codigo_competencia: "999999999",
      nombre_competencia: "Etapa practica",
      resultados: [],
      conocimientos: [],
      criterios: [],
    });
    render(
      <ProgramaCompetenciasManager
        competencias={[competencia]}
        referenciaId={referenciaId}
        onCompetenciasSynced={vi.fn()}
      />,
    );

    expect(screen.getByText("Etapa practica")).toBeInTheDocument();
    expect(screen.getByText("Resultados de aprendizaje")).toBeInTheDocument();
    expect(screen.getByText("Conocimientos")).toBeInTheDocument();
    expect(screen.getByText("Criterios de evaluacion")).toBeInTheDocument();
    expect(
      await screen.findByText(
        "Sin resultados de aprendizaje registrados para esta competencia.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Sin conocimientos SABER registrados para esta competencia."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Sin conocimientos PROCESO registrados para esta competencia."),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Sin criterios de evaluacion registrados para esta competencia.",
      ),
    ).toBeInTheDocument();
  });

  it("should create a criterio from panel form", async () => {
    const competencia = buildCompetencia();
    vi.mocked(criteriosApi.createProgramaCriterio).mockImplementation(
      async (_ref, _comp, payload) =>
        buildCriterioResponse(competencia.id, [
          {
            id: "11111111-1111-4111-9111-111111111111",
            competencia_id: competencia.id,
            resultado_id: null,
            descripcion: payload.descripcion,
            orden: 1,
            estado: "MANUAL",
            fecha_creacion: "2026-05-14T00:00:00Z",
            fecha_actualizacion: "2026-05-14T00:00:00Z",
          },
        ]),
    );

    render(
      <ProgramaCompetenciasManager
        competencias={[competencia]}
        referenciaId={referenciaId}
        onCompetenciasSynced={vi.fn()}
      />,
    );
    expect(screen.getByText("Criterios de evaluacion")).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText("Describe el criterio de evaluacion."),
      {
        target: { value: "  Realiza pruebas unitarias  " },
      },
    );
    fireEvent.submit(
      screen
        .getByRole("button", { name: /crear criterio/i })
        .closest("form") as HTMLFormElement,
    );

    expect(
      await screen.findByText("Realiza pruebas unitarias"),
    ).toBeInTheDocument();
  });

  it("should reject empty criterio form", async () => {
    const competencia = buildCompetencia();
    render(
      <ProgramaCompetenciasManager
        competencias={[competencia]}
        referenciaId={referenciaId}
        onCompetenciasSynced={vi.fn()}
      />,
    );
    expect(screen.getByText("Criterios de evaluacion")).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText("Describe el criterio de evaluacion."),
      {
        target: { value: "   " },
      },
    );
    fireEvent.submit(
      screen
        .getByRole("button", { name: /crear criterio/i })
        .closest("form") as HTMLFormElement,
    );

    expect(await screen.findByText(/descripcion es obligatoria/i)).toBeInTheDocument();
  });

  it("should show duplicate error for criterio", async () => {
    const competencia = buildCompetencia();
    vi.mocked(criteriosApi.createProgramaCriterio).mockRejectedValue(
      new criteriosApi.ProgramaCriterioError(
        409,
        "Ya existe un criterio de evaluacion con esta descripcion exacta en la competencia",
      ),
    );

    render(
      <ProgramaCompetenciasManager
        competencias={[competencia]}
        referenciaId={referenciaId}
        onCompetenciasSynced={vi.fn()}
      />,
    );
    expect(screen.getByText("Criterios de evaluacion")).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText("Describe el criterio de evaluacion."),
      {
        target: { value: "Duplicado" },
      },
    );
    fireEvent.submit(
      screen
        .getByRole("button", { name: /crear criterio/i })
        .closest("form") as HTMLFormElement,
    );

    expect(
      await screen.findByText(
        "Ya existe un criterio de evaluacion con esta descripcion exacta en la competencia",
      ),
    ).toBeInTheDocument();
  });
});
