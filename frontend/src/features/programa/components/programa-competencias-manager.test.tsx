import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProgramaCompetenciasManager } from "./programa-competencias-manager";
import * as competenciasApi from "@/features/programa/competencias-api";
import type {
  ProgramaCompetencia,
  ProgramaCompetenciaListResponse,
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

describe("ProgramaCompetenciasManager", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(competenciasApi.listProgramaCompetencias).mockResolvedValue(
      buildResponse([]),
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
});
