import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type {
  EntregaRevisionDetalle,
  PlaneacionRevisionDetalle,
  PlaneacionesEntregaList,
} from "@/features/planeacion/planeacion-api";
import * as api from "@/features/planeacion/planeacion-api";
import { RevisionDetailView } from "./revision-detail-view";

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const entrega: EntregaRevisionDetalle = {
  id: "delivery-1",
  proceso_curricular_id: "process-1",
  referencia_id: "reference-1",
  equipo_ejecutor_id: "team-1",
  equipo_ejecutor_nombre: "Equipo ADSO",
  programa_id: "program-1",
  codigo_programa: "228106",
  nombre_programa: "ADSO",
  proyecto_id: "project-1",
  codigo_proyecto: "PRY-1",
  nombre_proyecto: "Sistema empresarial",
  lider_nombre: "Líder",
  lider_email: "lider@sena.edu.co",
  version: 1,
  estado: "EN_REVISION",
  fecha_envio: "2026-09-27T10:00:00Z",
  observaciones_pendientes_count: 0,
  observaciones_ajustadas_count: 0,
  observaciones_resueltas_count: 0,
  descarga_habilitada: false,
  snapshot_metadatos: { planeaciones_count: 1 },
  observaciones: [],
  historial_versiones: [],
};

const list: PlaneacionesEntregaList = {
  entrega_id: "delivery-1",
  version: 1,
  total: 1,
  horas_directas_total: 20,
  horas_independientes_total: 10,
  planeaciones: [{
    id: "planning-a",
    estado: "COMPLETO",
    fase: { id: "phase-1", nombre: "ANÁLISIS", orden: 1 },
    actividad_proyecto: { id: "activity-1", descripcion: "Analizar", orden: 1 },
    competencias: [],
    raps: [],
    actividades_aprendizaje: "Diseñar arquitectura",
    horas: { directas: 20, independientes: 10, total: 30 },
    observaciones_count: 0,
    observaciones_pendientes_count: 0,
  }],
};

const detail: PlaneacionRevisionDetalle = {
  id: "planning-a",
  entrega_id: "delivery-1",
  version_entrega: 1,
  estado: "COMPLETO",
  fase: list.planeaciones[0].fase,
  actividad_proyecto: list.planeaciones[0].actividad_proyecto,
  competencias: [],
  conocimientos_saber: [],
  conocimientos_proceso: [],
  criterios_evaluacion: [],
  actividades_aprendizaje: "Diseñar arquitectura",
  descripcion_evidencia: "Diagrama",
  estrategias_didacticas: "ABP",
  ambientes: "Laboratorio",
  materiales: "Computador",
  instructores: "Ana",
  horas: { directas: 20, independientes: 10, total: 30 },
  observaciones: [],
};

describe("RevisionDetailView", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "fetchDetalleEntrega").mockResolvedValue(entrega);
    vi.spyOn(api, "fetchPlaneacionesEntrega").mockResolvedValue(list);
    vi.spyOn(api, "fetchPlaneacionRevisionDetalle").mockResolvedValue(detail);
  });

  it("creates one contextual observation and shows it in the section and consolidated tab", async () => {
    const created = {
      id: "observation-1",
      entrega_id: "delivery-1",
      target_type: "PLANEACION" as const,
      target_id: "planning-a",
      section_key: "ESTRATEGIAS_DIDACTICAS",
      comentario: "Aclarar la estrategia",
      estado: "PENDIENTE" as const,
      creado_por_id: "admin-1",
      creado_por_nombre: "María Admin",
      fecha_creacion: "2026-09-27T11:00:00Z",
    };
    const createObservation = vi.spyOn(api, "crearObservacionEntrega").mockResolvedValue(created);

    render(<RevisionDetailView entregaId="delivery-1" onBack={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Revisar planeación" }));

    const section = await screen.findByRole("heading", { name: "Estrategias didácticas" });
    fireEvent.click(section.closest("section")!.querySelector("button")!);
    fireEvent.change(screen.getByPlaceholderText(/Detalla con claridad/i), {
      target: { value: "Aclarar la estrategia" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Guardar Observación" }));

    await waitFor(() => expect(createObservation).toHaveBeenCalledWith("delivery-1", {
      target_type: "PLANEACION",
      target_id: "planning-a",
      section_key: "ESTRATEGIAS_DIDACTICAS",
      comentario: "Aclarar la estrategia",
    }));
    expect(await screen.findByText("Aclarar la estrategia")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Observaciones & Ajustes/i }));
    expect(screen.getByText("Aclarar la estrategia")).toBeInTheDocument();
  });
});
