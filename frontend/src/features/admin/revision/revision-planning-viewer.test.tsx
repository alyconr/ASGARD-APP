import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { PlaneacionRevisionDetalle } from "@/features/planeacion/planeacion-api";
import { RevisionPlanningViewer } from "./revision-planning-viewer";

const detail: PlaneacionRevisionDetalle = {
  id: "planning-a",
  entrega_id: "delivery-1",
  version_entrega: 1,
  estado: "COMPLETO",
  fase: { id: "phase-1", nombre: "ANÁLISIS", orden: 1 },
  actividad_proyecto: { id: "activity-1", descripcion: "Analizar requerimientos", orden: 1 },
  competencias: [{
    id: "competence-1",
    codigo: "220501096",
    nombre: "Desarrollo de software",
    resultados_count: 1,
    resultados: [{ id: "rap-1", codigo: "RA1", descripcion: "Diseñar la solución" }],
  }],
  conocimientos_saber: [{ id: "knowledge-1", tipo: "SABER", descripcion: "Arquitectura" }],
  conocimientos_proceso: [{ id: "knowledge-2", tipo: "PROCESO", descripcion: "Modelar" }],
  criterios_evaluacion: [{ id: "criterion-1", descripcion: "Valida la solución" }],
  actividades_aprendizaje: "Diseñar la arquitectura",
  descripcion_evidencia: "Diagrama de componentes",
  estrategias_didacticas: "Aprendizaje basado en proyectos",
  ambientes: "Laboratorio",
  materiales: "Computador",
  instructores: "Ana Pérez",
  horas: { directas: 20, independientes: 10, total: 30 },
  observaciones_didacticas: "Trabajo integrado",
  observaciones: [{
    id: "observation-1",
    entrega_id: "delivery-1",
    target_type: "PLANEACION",
    target_id: "planning-a",
    section_key: "ACTIVIDADES_APRENDIZAJE",
    comentario: "Precisar el producto esperado",
    estado: "PENDIENTE",
    creado_por_id: "admin-1",
    creado_por_nombre: "María Admin",
    fecha_creacion: "2026-09-27T10:00:00Z",
  }],
};

describe("RevisionPlanningViewer", () => {
  it("renders the complete curriculum and contextual observations in read-only sections", () => {
    render(<RevisionPlanningViewer detail={detail} loading={false} error={null} onBack={vi.fn()} onRetry={vi.fn()} onAddObservation={vi.fn()} />);

    for (const heading of ["Fase", "Actividad de proyecto", "Competencias", "Resultados de aprendizaje", "Actividades de aprendizaje", "Descripción de la evidencia de aprendizaje", "Saberes", "Criterios de evaluación", "Estrategias didácticas", "Ambientes", "Materiales", "Instructores", "Horas"]) {
      expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
    }
    expect(screen.getByText("Precisar el producto esperado")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("targets the exact section when adding an observation", () => {
    const onAddObservation = vi.fn();
    render(<RevisionPlanningViewer detail={detail} loading={false} error={null} onBack={vi.fn()} onRetry={vi.fn()} onAddObservation={onAddObservation} />);

    const section = screen.getByRole("heading", { name: "Estrategias didácticas" }).closest("section");
    fireEvent.click(section!.querySelector("button")!);
    expect(onAddObservation).toHaveBeenCalledWith("ESTRATEGIAS_DIDACTICAS");
  });

  it("targets the learning evidence description independently", () => {
    const onAddObservation = vi.fn();
    render(<RevisionPlanningViewer detail={detail} loading={false} error={null} onBack={vi.fn()} onRetry={vi.fn()} onAddObservation={onAddObservation} />);

    const section = screen.getByRole("heading", { name: "Descripción de la evidencia de aprendizaje" }).closest("section");
    expect(section).toHaveTextContent("Diagrama de componentes");
    fireEvent.click(section!.querySelector("button")!);

    expect(onAddObservation).toHaveBeenCalledWith("DESCRIPCION_EVIDENCIA_APRENDIZAJE");
  });

  it("returns to the planning tree from the end of the review", () => {
    const onBack = vi.fn();
    render(<RevisionPlanningViewer detail={detail} loading={false} error={null} onBack={onBack} onRetry={vi.fn()} onAddObservation={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Finalizar revisión y volver al árbol" }));

    expect(onBack).toHaveBeenCalledOnce();
  });
});
