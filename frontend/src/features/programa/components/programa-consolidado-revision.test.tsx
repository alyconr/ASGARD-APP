import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProgramaConsolidadoRevision } from "./programa-consolidado-revision";
import type {
  CriterioEvaluacionCurricular,
  ConocimientoCurricular,
  ProgramaCompetencia,
  ResultadoAprendizaje,
} from "@/features/programa/types";

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

describe("ProgramaConsolidadoRevision", () => {
  it("renders programme base data", () => {
    render(
      <ProgramaConsolidadoRevision
        codigoPrograma="228106"
        nombrePrograma="Analisis y desarrollo de software"
        versionPrograma="v1"
        entryMode="EXCEL"
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
        entryMode="MANUAL"
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
        entryMode="EXCEL"
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
        entryMode="EXCEL"
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
        entryMode="PDF"
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
        entryMode="MANUAL"
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
        entryMode="EXCEL"
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
        entryMode="EXCEL"
        competencias={[competencia]}
        pdfResult={null}
        excelResult={null}
        onNavigateToStep={vi.fn()}
      />,
    );

    expect(screen.getAllByText("2").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("1").length).toBeGreaterThanOrEqual(1);
  });
});
