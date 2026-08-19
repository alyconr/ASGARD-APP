import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProgramaPendientesConciliacion } from "./programa-pendientes-conciliacion";
import {
  assignPendienteCurricular,
  listPendientesCurriculares,
} from "@/features/programa/pendientes-api";
import type {
  PendienteCurricular,
  ProgramaCompetencia,
} from "@/features/programa/types";

vi.mock("@/features/programa/pendientes-api", () => ({
  ProgramaPendienteError: class ProgramaPendienteError extends Error {
    readonly status: number;

    readonly detail: string;

    constructor(status: number, detail: string) {
      super(detail);
      this.status = status;
      this.detail = detail;
    }
  },
  assignPendienteCurricular: vi.fn(),
  listPendientesCurriculares: vi.fn(),
}));

const mockListPendientes = vi.mocked(listPendientesCurriculares);
const mockAssignPendiente = vi.mocked(assignPendienteCurricular);

function buildCompetencias(): ProgramaCompetencia[] {
  return [
    {
      id: "comp-1",
      programa_id: "programa-1",
      codigo_competencia: "220501046",
      nombre_competencia: "Desarrollar software",
      orden: 1,
      estado: "BORRADOR",
      origen_campo: "VALIDADO",
      fecha_creacion: "2026-05-11T10:00:00Z",
      fecha_actualizacion: "2026-05-11T10:00:00Z",
      resultados: [
        {
          id: "rap-1",
          competencia_id: "comp-1",
          codigo_resultado: "RAP-1",
          descripcion: "Construye componentes",
          orden: 1,
          estado: "VALIDADO",
          fecha_creacion: "2026-05-11T10:00:00Z",
          fecha_actualizacion: "2026-05-11T10:00:00Z",
        },
      ],
    },
    {
      id: "comp-practica",
      programa_id: "programa-1",
      codigo_competencia: "999999999",
      nombre_competencia: "Aplicar etapa practica",
      orden: 2,
      estado: "BORRADOR",
      origen_campo: "VALIDADO",
      fecha_creacion: "2026-05-11T10:00:00Z",
      fecha_actualizacion: "2026-05-11T10:00:00Z",
      resultados: [],
    },
  ];
}

function buildPendiente(
  overrides: Partial<PendienteCurricular> = {},
): PendienteCurricular {
  return {
    id: "pend-1",
    referencia_id: "ref-123",
    programa_id: "programa-1",
    tipo_elemento: "CONOCIMIENTO",
    tipo_conocimiento: "SABER",
    descripcion: "Arquitectura pendiente",
    competencia_id_origen_excel: null,
    rap_id_origen_excel: null,
    motivo: "COMPETENCIA_NO_IDENTIFICADA",
    estado: "PENDIENTE",
    competencia_destino_id: null,
    resultado_destino_id: null,
    elemento_creado_id: null,
    fecha_creacion: "2026-05-11T10:00:00Z",
    fecha_actualizacion: "2026-05-11T10:00:00Z",
    ...overrides,
  };
}

describe("ProgramaPendientesConciliacion", () => {
  it("renders pending rows and filters by type", async () => {
    mockListPendientes.mockResolvedValueOnce({
      referencia_id: "ref-123",
      pendientes: [
        buildPendiente(),
        buildPendiente({
          id: "pend-2",
          tipo_elemento: "CRITERIO",
          tipo_conocimiento: null,
          descripcion: "Criterio pendiente",
        }),
      ],
    });

    render(
      <ProgramaPendientesConciliacion
        competencias={buildCompetencias()}
        referenciaId="ref-123"
      />,
    );

    expect(await screen.findByText("Arquitectura pendiente")).toBeInTheDocument();
    expect(screen.getByText("Criterio pendiente")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "CRITERIO" }));

    expect(screen.queryByText("Arquitectura pendiente")).not.toBeInTheDocument();
    expect(screen.getByText("Criterio pendiente")).toBeInTheDocument();
  });

  it("selects competence and result before assigning", async () => {
    const pending = buildPendiente();
    mockListPendientes.mockResolvedValueOnce({
      referencia_id: "ref-123",
      pendientes: [pending],
    });
    mockAssignPendiente.mockResolvedValueOnce({
      referencia_id: "ref-123",
      pendiente: {
        ...pending,
        estado: "ASIGNADO",
        competencia_destino_id: "comp-1",
        resultado_destino_id: "rap-1",
        elemento_creado_id: "created-1",
      },
    });

    render(
      <ProgramaPendientesConciliacion
        competencias={buildCompetencias()}
        referenciaId="ref-123"
      />,
    );

    await screen.findByText("Arquitectura pendiente");
    fireEvent.change(
      screen.getByLabelText(/Competencia destino para Arquitectura pendiente/i),
      { target: { value: "comp-1" } },
    );
    fireEvent.change(
      screen.getByLabelText(/Resultado destino para Arquitectura pendiente/i),
      { target: { value: "rap-1" } },
    );
    fireEvent.click(screen.getByRole("button", { name: /asignar/i }));

    await waitFor(() => {
      expect(mockAssignPendiente).toHaveBeenCalledWith("ref-123", "pend-1", {
        competencia_id: "comp-1",
        resultado_id: "rap-1",
      });
    });
    expect(await screen.findByText("ASIGNADO")).toBeInTheDocument();
  });

  it("allows practical-stage competence without child results", async () => {
    const pending = buildPendiente();
    mockListPendientes.mockResolvedValueOnce({
      referencia_id: "ref-123",
      pendientes: [pending],
    });
    mockAssignPendiente.mockResolvedValueOnce({
      referencia_id: "ref-123",
      pendiente: {
        ...pending,
        estado: "ASIGNADO",
        competencia_destino_id: "comp-practica",
      },
    });

    render(
      <ProgramaPendientesConciliacion
        competencias={buildCompetencias()}
        referenciaId="ref-123"
      />,
    );

    await screen.findByText("Arquitectura pendiente");
    fireEvent.change(
      screen.getByLabelText(/Competencia destino para Arquitectura pendiente/i),
      { target: { value: "comp-practica" } },
    );
    expect(
      screen.getByRole("option", { name: "Sin resultado especifico" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /asignar/i }));

    await waitFor(() => {
      expect(mockAssignPendiente).toHaveBeenCalledWith("ref-123", "pend-1", {
        competencia_id: "comp-practica",
        resultado_id: null,
      });
    });
  });
});
