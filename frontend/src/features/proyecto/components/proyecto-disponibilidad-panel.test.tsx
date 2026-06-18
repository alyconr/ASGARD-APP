import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProyectoDisponibilidadPanel } from "./proyecto-disponibilidad-panel";
import type { ProyectoDisponibilidadResponse } from "@/features/proyecto/types";

const referenciaId = "11111111-1111-4111-9111-111111111111";

afterEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function buildAvailability(
  overrides: Partial<ProyectoDisponibilidadResponse> = {},
): ProyectoDisponibilidadResponse {
  return {
    referencia_id: referenciaId,
    programa_id: "22222222-2222-4222-9222-222222222222",
    estado_programa: "BORRADOR",
    programa_completo: false,
    proyecto_bloqueado: true,
    estado_proyecto: "BLOQUEADO",
    motivo: "PROGRAMA_NO_COMPLETO",
    mensaje:
      "El modulo proyecto formativo esta bloqueado hasta que el programa de formación quede cerrado como COMPLETO.",
    accion_sugerida: "completar_y_cerrar_programa",
    ...overrides,
  };
}

function mockFetchJson(payload: ProyectoDisponibilidadResponse): void {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => payload,
    }),
  );
}

describe("ProyectoDisponibilidadPanel", () => {
  it("renders blocked state and explanatory message", async () => {
    mockFetchJson(buildAvailability());

    render(
      <ProyectoDisponibilidadPanel
        referenciaId={referenciaId}
        programaEstado="BORRADOR"
      />,
    );

    expect(
      await screen.findByText("Modulo proyecto bloqueado"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/bloqueado hasta que el programa/i),
    ).toBeInTheDocument();
    expect(screen.getByText("BLOQUEADO")).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Wizard base del proyecto formativo"),
    ).not.toBeInTheDocument();
  });

  it("does not render the old complete program action", async () => {
    mockFetchJson(buildAvailability());

    render(
      <ProyectoDisponibilidadPanel
        referenciaId={referenciaId}
        programaEstado="BORRADOR"
      />,
    );

    await screen.findByText("Modulo proyecto bloqueado");
    expect(
      screen.queryByRole("button", { name: /completar programa/i }),
    ).not.toBeInTheDocument();
  });

  it("renders enabled state when the program is complete", async () => {
    mockFetchJson(
      buildAvailability({
        estado_programa: "COMPLETO",
        programa_completo: true,
        proyecto_bloqueado: false,
        estado_proyecto: "BORRADOR",
        motivo: null,
        mensaje:
          "El proyecto formativo esta habilitado porque el programa de formación esta COMPLETO.",
        accion_sugerida: "iniciar_proyecto",
      }),
    );

    render(
      <ProyectoDisponibilidadPanel
        referenciaId={referenciaId}
        programaEstado="COMPLETO"
      />,
    );

    expect(
      await screen.findByText("Modulo proyecto habilitado"),
    ).toBeInTheDocument();
    expect(screen.getByText("LISTO PARA INICIAR")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /completar programa/i }),
    ).not.toBeInTheDocument();
    expect(
      await screen.findByLabelText("Wizard base del proyecto formativo"),
    ).toBeInTheDocument();
  });

  it("updates visually when the program status changes to complete", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => buildAvailability(),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () =>
          buildAvailability({
            estado_programa: "COMPLETO",
            programa_completo: true,
            proyecto_bloqueado: false,
            estado_proyecto: "BORRADOR",
            motivo: null,
            mensaje:
              "El proyecto formativo esta habilitado porque el programa de formación esta COMPLETO.",
            accion_sugerida: "iniciar_proyecto",
          }),
      });
    vi.stubGlobal("fetch", fetchMock);

    const { rerender } = render(
      <ProyectoDisponibilidadPanel
        referenciaId={referenciaId}
        programaEstado="BORRADOR"
      />,
    );

    await screen.findByText("Modulo proyecto bloqueado");

    rerender(
      <ProyectoDisponibilidadPanel
        referenciaId={referenciaId}
        programaEstado="COMPLETO"
      />,
    );

    await waitFor(() =>
      expect(
        screen.getByText("Modulo proyecto habilitado"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText("LISTO PARA INICIAR")).toBeInTheDocument();
  });
});
