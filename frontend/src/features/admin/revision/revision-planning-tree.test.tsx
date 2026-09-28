import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { PlaneacionesEntregaList } from "@/features/planeacion/planeacion-api";
import { RevisionPlanningTree } from "./revision-planning-tree";

const data: PlaneacionesEntregaList = {
  entrega_id: "delivery-1",
  version: 1,
  total: 2,
  horas_directas_total: 30,
  horas_independientes_total: 15,
  planeaciones: ["planning-a", "planning-b"].map((id, index) => ({
    id,
    estado: "COMPLETO",
    fase: { id: "phase-1", nombre: "ANÁLISIS", orden: 1 },
    actividad_proyecto: { id: "activity-1", descripcion: "Analizar requerimientos", orden: 1 },
    competencias: [{ id: "competence-1", codigo: "220501096", nombre: "Desarrollo", resultados_count: 1, resultados: [] }],
    raps: [{ id: `rap-${index}`, codigo: `RA${index + 1}`, descripcion: "Resultado" }],
    actividades_aprendizaje: `Planeación ${index + 1}`,
    horas: { directas: 15, independientes: 7.5, total: 22.5 },
    observaciones_count: index,
    observaciones_pendientes_count: index,
  })),
};

describe("RevisionPlanningTree", () => {
  it("renders loading, error and empty states", () => {
    const { rerender } = render(<RevisionPlanningTree data={null} loading error={null} onRetry={vi.fn()} onSelect={vi.fn()} />);
    expect(screen.getByText(/Cargando planeaciones/i)).toBeInTheDocument();

    rerender(<RevisionPlanningTree data={null} loading={false} error="No disponible" onRetry={vi.fn()} onSelect={vi.fn()} />);
    expect(screen.getByText("No disponible")).toBeInTheDocument();

    rerender(<RevisionPlanningTree data={{ ...data, total: 0, planeaciones: [] }} loading={false} error={null} onRetry={vi.fn()} onSelect={vi.fn()} />);
    expect(screen.getByText(/no contiene planeaciones/i)).toBeInTheDocument();
  });

  it("renders exactly two plannings and opens the selected read-only viewer", () => {
    const onSelect = vi.fn();
    render(<RevisionPlanningTree data={data} loading={false} error={null} onRetry={vi.fn()} onSelect={onSelect} />);

    expect(screen.getByText("2 planeaciones congeladas en la versión 1")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Revisar planeación" })).toHaveLength(2);
    fireEvent.click(screen.getAllByRole("button", { name: "Revisar planeación" })[1]);
    expect(onSelect).toHaveBeenCalledWith("planning-b");
  });
});
