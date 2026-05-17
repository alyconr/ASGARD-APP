import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProgramaConsolidadoRevision } from "./programa-consolidado-revision";
import type {
  CriterioEvaluacionCurricular,
  ConocimientoCurricular,
  ProgramaCompletitudResponse,
  ProgramaCompetencia,
  ResultadoAprendizaje,
} from "@/features/programa/types";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

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
    fecha_creacion: "2026-05-01T00:00:00Z",
    fecha_actualizacion: "2026-05-14T00:00:00Z",
    ...overrides,
  };
}

function buildResultado(
  overrides: Partial<ResultadoAprendizaje> = {},
): ResultadoAprendizaje {
  return {
    id: "cccccccc-cccc-4ccc-9ccc-cccccccccccc",
    competencia_id: "aaaaaaaa-aaaa-4aaa-9aaa-aaaaaaaaaaaa",
    codigo_resultado: null,
    descripcion: "Analiza los requisitos del software",
    orden: 1,
    estado: "VALIDADO",
    fecha_creacion: "2026-05-11T00:00:00Z",
    fecha_actualizacion: "2026-05-11T00:00:00Z",
    ...overrides,
  };
}

function buildSaber(
  overrides: Partial<ConocimientoCurricular> = {},
): ConocimientoCurricular {
  return {
    id: "dddddddd-dddd-4ddd-9ddd-dddddddddddd",
    competencia_id: "aaaaaaaa-aaaa-4aaa-9aaa-aaaaaaaaaaaa",
    resultado_id: null,
    tipo: "SABER",
    descripcion: "Arquitectura del software",
    orden: 1,
    estado: "VALIDADO",
    fecha_creacion: "2026-05-14T00:00:00Z",
    fecha_actualizacion: "2026-05-14T00:00:00Z",
    ...overrides,
  };
}

function buildProceso(
  overrides: Partial<ConocimientoCurricular> = {},
): ConocimientoCurricular {
  return {
    id: "eeeeeeee-eeee-4eee-9eee-eeeeeeeeeeee",
    competencia_id: "aaaaaaaa-aaaa-4aaa-9aaa-aaaaaaaaaaaa",
    resultado_id: null,
    tipo: "PROCESO",
    descripcion: "Codificar solucion",
    orden: 1,
    estado: "MANUAL",
    fecha_creacion: "2026-05-14T00:00:00Z",
    fecha_actualizacion: "2026-05-14T00:00:00Z",
    ...overrides,
  };
}

function buildCriterio(
  overrides: Partial<CriterioEvaluacionCurricular> = {},
): CriterioEvaluacionCurricular {
  return {
    id: "ffffffff-ffff-4fff-9fff-ffffffffffff",
    competencia_id: "aaaaaaaa-aaaa-4aaa-9aaa-aaaaaaaaaaaa",
    resultado_id: null,
    descripcion: "Pruebas unitarias",
    orden: 1,
    estado: "MANUAL",
    fecha_creacion: "2026-05-14T00:00:00Z",
    fecha_actualizacion: "2026-05-14T00:00:00Z",
    ...overrides,
  };
}

function buildCompletitudResponse(
  overrides: Partial<ProgramaCompletitudResponse> = {},
): ProgramaCompletitudResponse {
  return {
    referencia_id: "11111111-1111-4111-9111-111111111111",
    programa_id: "bbbbbbbb-bbbb-4bbb-9bbb-bbbbbbbbbbbb",
    estado_actual: "BORRADOR",
    cerrable: false,
    resumen: {
      competencias: 0,
      resultados: 0,
      conocimientos_saber: 0,
      conocimientos_proceso: 0,
      criterios: 0,
    },
    faltantes: [
      {
        codigo: "programa.competencias",
        campo: "competencias",
        mensaje: "Registra al menos una competencia asociada al programa.",
        competencia_id: null,
        competencia_codigo: null,
        competencia_nombre: null,
      },
    ],
    ...overrides,
  };
}

function mockFetchJson(payload: unknown, status = 200): void {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      json: async () => payload,
    }),
  );
}

describe("ProgramaConsolidadoRevision", () => {
  it("renders programme base data", () => {
    render(
      <ProgramaConsolidadoRevision
        codigoPrograma="228106"
        nombrePrograma="Analisis y desarrollo de software"
        versionPrograma="v1"
        competencias={[]}
        pdfResult={null}
        excelResult={null}
        onNavigateToStep={vi.fn()}
      />,
    );

    expect(screen.getByText("228106")).toBeInTheDocument();
    expect(
      screen.getByText("Analisis y desarrollo de software"),
    ).toBeInTheDocument();
    expect(screen.getByText("v1")).toBeInTheDocument();
    expect(screen.getAllByText("Excel canonico").length).toBeGreaterThanOrEqual(1);
  });

  it("shows empty curricular state when no competencias", () => {
    render(
      <ProgramaConsolidadoRevision
        codigoPrograma="228106"
        nombrePrograma="Test"
        versionPrograma="v1"
        competencias={[]}
        pdfResult={null}
        excelResult={null}
        onNavigateToStep={vi.fn()}
      />,
    );

    expect(screen.getByText("Sin estructura curricular")).toBeInTheDocument();
  });

  it("renders competencia with results, conocimientos and criterios", () => {
    const competencia = buildCompetencia({
      resultados: [buildResultado()],
      conocimientos: [buildSaber(), buildProceso()],
      criterios: [buildCriterio()],
    });

    render(
      <ProgramaConsolidadoRevision
        codigoPrograma="228106"
        nombrePrograma="Test"
        versionPrograma="v1"
        competencias={[competencia]}
        pdfResult={null}
        excelResult={null}
        onNavigateToStep={vi.fn()}
      />,
    );

    expect(screen.getByText("Desarrollar software")).toBeInTheDocument();
    expect(
      screen.getByText("Analiza los requisitos del software"),
    ).toBeInTheDocument();
    expect(screen.getByText("Arquitectura del software")).toBeInTheDocument();
    expect(screen.getByText("Codificar solucion")).toBeInTheDocument();
    expect(screen.getByText("Pruebas unitarias")).toBeInTheDocument();
  });

  it("shows origin badges for curricular items", () => {
    const competencia = buildCompetencia({
      origen_campo: "EXTRAIDO",
      resultados: [buildResultado({ estado: "VALIDADO" })],
      conocimientos: [buildSaber({ estado: "MANUAL" })],
      criterios: [buildCriterio({ estado: "PENDIENTE" })],
    });

    render(
      <ProgramaConsolidadoRevision
        codigoPrograma="228106"
        nombrePrograma="Test"
        versionPrograma="v1"
        competencias={[competencia]}
        pdfResult={null}
        excelResult={null}
        onNavigateToStep={vi.fn()}
      />,
    );

    expect(screen.getByText("Extraido")).toBeInTheDocument();
    expect(screen.getByText("Validado")).toBeInTheDocument();
    expect(screen.getByText("Manual")).toBeInTheDocument();
    expect(screen.getByText("Pendiente")).toBeInTheDocument();
  });

  it("shows document evidence status", () => {
    render(
      <ProgramaConsolidadoRevision
        codigoPrograma="228106"
        nombrePrograma="Test"
        versionPrograma="v1"
        competencias={[]}
        pdfResult={null}
        excelResult={null}
        onNavigateToStep={vi.fn()}
      />,
    );

    expect(screen.getByText("Sin PDF cargado como evidencia.")).toBeInTheDocument();
    expect(screen.getByText("Sin Excel canonico cargado.")).toBeInTheDocument();
  });

  it("calls onNavigateToStep when edit buttons are clicked", () => {
    const onNavigate = vi.fn();

    render(
      <ProgramaConsolidadoRevision
        codigoPrograma="228106"
        nombrePrograma="Test"
        versionPrograma="v1"
        competencias={[]}
        pdfResult={null}
        excelResult={null}
        onNavigateToStep={onNavigate}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /editar datos/i }));
    expect(onNavigate).toHaveBeenCalledWith("datos-programa");

    fireEvent.click(screen.getByRole("button", { name: /editar estructura/i }));
    expect(onNavigate).toHaveBeenCalledWith("estructura-curricular");
  });

  it("renders practical stage competencia without children", () => {
    const competencia = buildCompetencia({
      codigo_competencia: "999999999",
      nombre_competencia: "Etapa practica",
      resultados: [],
      conocimientos: [],
      criterios: [],
    });

    render(
      <ProgramaConsolidadoRevision
        codigoPrograma="228106"
        nombrePrograma="Test"
        versionPrograma="v1"
        competencias={[competencia]}
        pdfResult={null}
        excelResult={null}
        onNavigateToStep={vi.fn()}
      />,
    );

    expect(screen.getByText("Etapa practica")).toBeInTheDocument();
    expect(screen.getByText("Sin resultados")).toBeInTheDocument();
    expect(screen.getByText("Sin criterios")).toBeInTheDocument();
    expect(screen.getByText("Sin conocimientos SABER")).toBeInTheDocument();
    expect(screen.getByText("Sin conocimientos PROCESO")).toBeInTheDocument();
  });

  it("shows counts in summary banner", () => {
    const competencia = buildCompetencia({
      resultados: [buildResultado(), buildResultado({ id: "r2", descripcion: "Otro" })],
      conocimientos: [buildSaber()],
      criterios: [buildCriterio()],
    });

    render(
      <ProgramaConsolidadoRevision
        codigoPrograma="228106"
        nombrePrograma="Test"
        versionPrograma="v1"
        competencias={[competencia]}
        pdfResult={null}
        excelResult={null}
        onNavigateToStep={vi.fn()}
      />,
    );

    expect(screen.getAllByText("2").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("1").length).toBeGreaterThanOrEqual(1);
  });

  it("renders not ready for close after validation", async () => {
    mockFetchJson(buildCompletitudResponse());

    render(
      <ProgramaConsolidadoRevision
        codigoPrograma="228106"
        nombrePrograma="Test"
        versionPrograma="v1"
        referenciaId="11111111-1111-4111-9111-111111111111"
        competencias={[]}
        pdfResult={null}
        excelResult={null}
        onNavigateToStep={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /validar completitud/i }));

    expect(await screen.findByText(/Faltantes para cierre: 1/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /confirmar y cerrar programa/i }),
    ).toBeDisabled();
  });

  it("renders missing items list from completion validator", async () => {
    mockFetchJson(
      buildCompletitudResponse({
        faltantes: [
          {
            codigo: "competencia.resultados",
            campo: "resultados",
            mensaje: "Agrega al menos un resultado de aprendizaje.",
            competencia_id: "aaaaaaaa-aaaa-4aaa-9aaa-aaaaaaaaaaaa",
            competencia_codigo: "220501046",
            competencia_nombre: "Desarrollar software",
          },
        ],
      }),
    );

    render(
      <ProgramaConsolidadoRevision
        codigoPrograma="228106"
        nombrePrograma="Test"
        versionPrograma="v1"
        referenciaId="11111111-1111-4111-9111-111111111111"
        competencias={[]}
        pdfResult={null}
        excelResult={null}
        onNavigateToStep={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /validar completitud/i }));

    expect(
      await screen.findByText(/Agrega al menos un resultado de aprendizaje/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/220501046/i)).toBeInTheDocument();
  });

  it("navigates to corrections from missing items", async () => {
    mockFetchJson(buildCompletitudResponse());
    const onNavigate = vi.fn();

    render(
      <ProgramaConsolidadoRevision
        codigoPrograma=""
        nombrePrograma="Test"
        versionPrograma="v1"
        referenciaId="11111111-1111-4111-9111-111111111111"
        competencias={[]}
        pdfResult={null}
        excelResult={null}
        onNavigateToStep={onNavigate}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /validar completitud/i }));
    fireEvent.click(await screen.findByRole("button", { name: /corregir datos/i }));
    fireEvent.click(screen.getByRole("button", { name: /corregir estructura/i }));

    expect(onNavigate).toHaveBeenCalledWith("datos-programa");
    expect(onNavigate).toHaveBeenCalledWith("estructura-curricular");
  });

  it("requires explicit confirmation before closing", async () => {
    const validation = buildCompletitudResponse({
      cerrable: true,
      resumen: {
        competencias: 1,
        resultados: 1,
        conocimientos_saber: 1,
        conocimientos_proceso: 1,
        criterios: 1,
      },
      faltantes: [],
    });
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => validation,
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          referencia_id: validation.referencia_id,
          programa_id: validation.programa_id,
          estado: "COMPLETO",
          mensaje: "Programa cerrado correctamente.",
          completitud: { ...validation, estado_actual: "COMPLETO" },
        }),
      });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(
      <ProgramaConsolidadoRevision
        codigoPrograma="228106"
        nombrePrograma="Test"
        versionPrograma="v1"
        referenciaId={validation.referencia_id}
        competencias={[buildCompetencia()]}
        pdfResult={null}
        excelResult={null}
        onNavigateToStep={vi.fn()}
        onProgramaCerrado={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /validar completitud/i }));
    await screen.findByText(/listo para cierre/i);
    fireEvent.click(screen.getByRole("button", { name: /confirmar y cerrar programa/i }));

    await waitFor(() => expect(window.confirm).toHaveBeenCalled());
    expect(fetchMock).toHaveBeenLastCalledWith(
      expect.stringContaining("/cierre"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("renders success when program is closed", async () => {
    const validation = buildCompletitudResponse({ cerrable: true, faltantes: [] });
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => validation,
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({
            referencia_id: validation.referencia_id,
            programa_id: validation.programa_id,
            estado: "COMPLETO",
            mensaje: "Programa cerrado correctamente.",
            completitud: { ...validation, estado_actual: "COMPLETO" },
          }),
        }),
    );
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(
      <ProgramaConsolidadoRevision
        codigoPrograma="228106"
        nombrePrograma="Test"
        versionPrograma="v1"
        referenciaId={validation.referencia_id}
        competencias={[buildCompetencia()]}
        pdfResult={null}
        excelResult={null}
        onNavigateToStep={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /validar completitud/i }));
    await screen.findByText(/listo para cierre/i);
    fireEvent.click(screen.getByRole("button", { name: /confirmar y cerrar programa/i }));

    expect(
      await screen.findByText("Programa cerrado correctamente."),
    ).toBeInTheDocument();
    expect(screen.getByText(/Estado actual:/i)).toBeInTheDocument();
    expect(screen.getByText("COMPLETO")).toBeInTheDocument();
  });

  it("does not allow close when backend returns structured errors", async () => {
    const validation = buildCompletitudResponse({ cerrable: true, faltantes: [] });
    const rejected = buildCompletitudResponse({
      faltantes: [
        {
          codigo: "programa.criterios",
          campo: "criterios",
          mensaje: "El programa debe tener al menos un criterio de evaluacion.",
          competencia_id: null,
          competencia_codigo: null,
          competencia_nombre: null,
        },
      ],
    });
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => validation,
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 409,
          json: async () => ({ detail: rejected }),
        }),
    );
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(
      <ProgramaConsolidadoRevision
        codigoPrograma="228106"
        nombrePrograma="Test"
        versionPrograma="v1"
        referenciaId={validation.referencia_id}
        competencias={[buildCompetencia()]}
        pdfResult={null}
        excelResult={null}
        onNavigateToStep={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /validar completitud/i }));
    await screen.findByText(/listo para cierre/i);
    fireEvent.click(screen.getByRole("button", { name: /confirmar y cerrar programa/i }));

    expect(
      await screen.findByText(/El programa debe tener al menos un criterio/i),
    ).toBeInTheDocument();
    expect(screen.queryByText("COMPLETO")).not.toBeInTheDocument();
  });
});
