import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProgramaConsolidadoRevision } from "./programa-consolidado-revision";
import type {
  CriterioEvaluacionCurricular,
  ConocimientoCurricular,
  ProgramaCompletitudResponse,
  ProgramaCompetencia,
  ResultadoAprendizaje,
} from "@/features/programa/types";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((input: string | Request | URL) => {
      const url = typeof input === "string" ? input : (input instanceof URL ? input.href : input.url);
      if (url.includes("/pendientes-curriculares")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ pendientes: [] }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
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
          faltantes: [],
        }),
      });
    }),
  );
});

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
    vi.fn().mockImplementation((input: string | Request | URL) => {
      const url = typeof input === "string" ? input : (input instanceof URL ? input.href : input.url);
      if (url.includes("/pendientes-curriculares")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ pendientes: [] }),
        });
      }
      return Promise.resolve({
        ok: status >= 200 && status < 300,
        status,
        json: async () => payload,
      });
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
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /revisar estructura/i }));

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
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /revisar estructura/i }));

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
      />,
    );

    expect(screen.getByText("Sin PDF cargado como evidencia.")).toBeInTheDocument();
    expect(screen.getByText("Sin Excel canonico cargado.")).toBeInTheDocument();
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
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /revisar estructura/i }));

    expect(screen.getByText("Etapa practica")).toBeInTheDocument();
    expect(screen.getByText("Sin resultados")).toBeInTheDocument();
    expect(screen.getByText("Sin criterios")).toBeInTheDocument();
    expect(screen.getByText("Sin conocimientos SABER")).toBeInTheDocument();
    expect(screen.getByText("Sin conocimientos PROCESO")).toBeInTheDocument();
  });

  it("allows selecting and reviewing different competencias in the modal select", () => {
    const competencia1 = buildCompetencia({
      id: "comp-1",
      codigo_competencia: "111111",
      nombre_competencia: "Competencia Primera",
      resultados: [buildResultado({ id: "res-1", descripcion: "Resultado Uno" })],
    });
    const competencia2 = buildCompetencia({
      id: "comp-2",
      codigo_competencia: "222222",
      nombre_competencia: "Competencia Segunda",
      resultados: [buildResultado({ id: "res-2", descripcion: "Resultado Dos" })],
    });

    render(
      <ProgramaConsolidadoRevision
        codigoPrograma="228106"
        nombrePrograma="Test"
        versionPrograma="v1"
        competencias={[competencia1, competencia2]}
        pdfResult={null}
        excelResult={null}
      />,
    );

    // Open modal
    fireEvent.click(screen.getByRole("button", { name: /revisar estructura/i }));

    // By default, the first competency should be active
    expect(screen.getByText("Competencia Primera")).toBeInTheDocument();
    expect(screen.getByText("Resultado Uno")).toBeInTheDocument();
    expect(screen.queryByText("Competencia Segunda")).not.toBeInTheDocument();

    // Select second competency using the dropdown
    const select = screen.getByLabelText(/Seleccione la competencia a revisar/i);
    fireEvent.change(select, { target: { value: "comp-2" } });

    // Now the second competency should be active
    expect(screen.getByText("Competencia Segunda")).toBeInTheDocument();
    expect(screen.getByText("Resultado Dos")).toBeInTheDocument();
    expect(screen.queryByText("Competencia Primera")).not.toBeInTheDocument();
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
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /validar completitud/i }));

    expect(
      await screen.findByText(/Agrega al menos un resultado de aprendizaje/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/220501046/i)).toBeInTheDocument();
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
    const fetchMock = vi.fn().mockImplementation((input: string | Request | URL) => {
      const url = typeof input === "string" ? input : (input instanceof URL ? input.href : input.url);
      if (url.includes("/pendientes-curriculares")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ pendientes: [] }),
        });
      }
      if (url.includes("/completitud")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => validation,
        });
      }
      if (url.includes("/cierre")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            referencia_id: validation.referencia_id,
            programa_id: validation.programa_id,
            estado: "COMPLETO",
            mensaje: "Programa de formación cerrado correctamente.",
            completitud: { ...validation, estado_actual: "COMPLETO" },
          }),
        });
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
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
      vi.fn().mockImplementation((input: string | Request | URL) => {
        const url = typeof input === "string" ? input : (input instanceof URL ? input.href : input.url);
        if (url.includes("/pendientes-curriculares")) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => ({ pendientes: [] }),
          });
        }
        if (url.includes("/completitud")) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => validation,
          });
        }
        if (url.includes("/cierre")) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => ({
              referencia_id: validation.referencia_id,
              programa_id: validation.programa_id,
              estado: "COMPLETO",
              mensaje: "Programa de formación cerrado correctamente.",
              completitud: { ...validation, estado_actual: "COMPLETO" },
            }),
          });
        }
        return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
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
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /validar completitud/i }));
    await screen.findByText(/listo para cierre/i);
    fireEvent.click(screen.getByRole("button", { name: /confirmar y cerrar programa/i }));

    expect(
      await screen.findByText("Programa de formación cerrado correctamente."),
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
          mensaje: "El programa de formación debe tener al menos un criterio de evaluacion.",
          competencia_id: null,
          competencia_codigo: null,
          competencia_nombre: null,
        },
      ],
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((input: string | Request | URL) => {
        const url = typeof input === "string" ? input : (input instanceof URL ? input.href : input.url);
        if (url.includes("/pendientes-curriculares")) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => ({ pendientes: [] }),
          });
        }
        if (url.includes("/completitud")) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => validation,
          });
        }
        if (url.includes("/cierre")) {
          return Promise.resolve({
            ok: false,
            status: 409,
            json: async () => ({ detail: rejected }),
          });
        }
        return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
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
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /validar completitud/i }));
    await screen.findByText(/listo para cierre/i);
    fireEvent.click(screen.getByRole("button", { name: /confirmar y cerrar programa/i }));

    expect(
      await screen.findByText(/El programa de formación debe tener al menos un criterio/i),
    ).toBeInTheDocument();
    expect(screen.queryByText("COMPLETO")).not.toBeInTheDocument();
  });
});
