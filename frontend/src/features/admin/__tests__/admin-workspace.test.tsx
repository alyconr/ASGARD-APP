import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AdminWorkspace } from "../admin-workspace";

vi.mock("@/features/auth/auth-context", () => ({
  useAuth: () => ({
    user: {
      id: "admin-uuid",
      nombre: "Admin",
      apellido: "Principal",
      email: "admin@sena.edu.co",
      roles: ["SUPERADMIN"],
      estado: "ACTIVO",
      debe_cambiar_password: false,
    },
    isAuthenticated: true,
    hasRole: () => true,
    logout: vi.fn(),
    refreshUser: vi.fn(),
  }),
}));

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("AdminWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockImplementation(async (url: string) => {
      const urlStr = String(url);
      if (urlStr.includes("/auth/users")) {
        return {
          ok: true,
          json: async () => ({
            items: [
              {
                id: "u-1",
                nombre: "Carlos",
                apellido: "Pérez",
                email: "carlos@sena.edu.co",
                roles: ["LIDER_EQUIPO_EJECUTOR"],
                estado: "ACTIVO",
                debe_cambiar_password: false,
                area: "Teleinformática",
                coordinacion: { id: "c-1", codigo: "TEL", nombre: "Teleinformática" },
                especialidad: { id: "e-1", codigo: "ADSO", nombre: "Análisis y Desarrollo" },
              },
            ],
            total: 1,
            page: 1,
            page_size: 15,
            total_pages: 1,
          }),
        };
      }
      if (urlStr.includes("/coordinaciones")) {
        return {
          ok: true,
          json: async () => [
            {
              id: "c-1",
              codigo: "TEL",
              nombre: "Teleinformática",
              estado: "ACTIVO",
              especialidades_count: 2,
              equipos_count: 1,
            },
          ],
        };
      }
      if (urlStr.includes("/equipos")) {
        return {
          ok: true,
          json: async () => ({
            items: [
              {
                id: "eq-1",
                nombre: "Equipo ADSO 01",
                coordinacion_id: "c-1",
                especialidad_id: "e-1",
                lider_id: "u-1",
                estado: "ACTIVO",
                coordinacion: { id: "c-1", codigo: "TEL", nombre: "Teleinformática" },
                especialidad: { id: "e-1", codigo: "ADSO", nombre: "Análisis y Desarrollo" },
                lider: { id: "u-1", nombre: "Carlos", apellido: "Pérez", email: "carlos@sena.edu.co", roles: ["LIDER_EQUIPO_EJECUTOR"] },
                miembros: [],
              },
            ],
            total: 1,
            page: 1,
            page_size: 9,
            total_pages: 1,
          }),
        };
      }
      if (urlStr.includes("/procesos/sin-asignar")) {
        return {
          ok: true,
          json: async () => [],
        };
      }
      return {
        ok: true,
        json: async () => [],
      };
    });
  });

  it("renders the administration banner and 3 navigation tabs", () => {
    render(<AdminWorkspace />);

    expect(screen.getByText("Administración Central ASGARD")).toBeInTheDocument();
    expect(screen.getByText("Usuarios y Credenciales")).toBeInTheDocument();
    expect(screen.getByText("Coordinaciones & Especialidades")).toBeInTheDocument();
    expect(screen.getByText("Equipos Ejecutores & Procesos")).toBeInTheDocument();
  });

  it("switches to Organizacion tab when clicked", async () => {
    render(<AdminWorkspace />);

    const orgTabBtn = screen.getByRole("button", { name: /coordinaciones & especialidades/i });
    fireEvent.click(orgTabBtn);

    await waitFor(() => {
      expect(screen.getByText("Estructura Organizacional SENA")).toBeInTheDocument();
    });
  });

  it("switches to Equipos tab when clicked", async () => {
    render(<AdminWorkspace />);

    const equiposTabBtn = screen.getByRole("button", { name: /equipos ejecutores & procesos/i });
    fireEvent.click(equiposTabBtn);

    await waitFor(() => {
      expect(screen.getByText("Gestión de Equipos Ejecutores")).toBeInTheDocument();
    });
  });
});
