import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AdminWorkspace } from "../admin-workspace";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

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
      if (urlStr.includes("/admin/dashboard/resumen")) {
        return {
          ok: true,
          json: async () => ({
            procesos_totales: 5,
            procesos_asignados: 4,
            procesos_sin_asignar: 1,
            programas_borrador: 1,
            programas_en_revision: 1,
            programas_completo: 3,
            proyectos_bloqueado: 0,
            proyectos_borrador: 1,
            proyectos_en_revision: 1,
            proyectos_completo: 3,
            planeaciones_totales: 10,
            planeaciones_borrador: 2,
            planeaciones_completo: 8,
            equipos_activos: 2,
            equipos_inactivos: 0,
            lideres_activos: 2,
            usuarios_apoyo_activos: 4,
          }),
        };
      }
      if (urlStr.includes("/admin/dashboard/procesos")) {
        return {
          ok: true,
          json: async () => ({
            items: [
              {
                referencia_id: "ref-1",
                tipo_necesidad: "CREAR_PLANEACION",
                estado_scope: "ASIGNADO",
                coordinacion: { id: "c-1", codigo: "TEL", nombre: "Teleinformática" },
                especialidad: { id: "e-1", codigo: "ADSO", nombre: "Software" },
                programa: { id: "p-1", codigo: "228106", nombre: "ADSO", estado: "COMPLETO" },
                proyecto: { id: "py-1", codigo: "PROY-01", nombre: "Sistema ASGARD", estado: "COMPLETO" },
                equipo: { id: "eq-1", nombre: "Equipo ADSO 01", estado: "ACTIVO" },
                lider: { id: "u-1", nombre: "Carlos", apellido: "Pérez", email: "carlos@sena.edu.co" },
                planeaciones: { total: 4, borrador: 1, completas: 3 },
                fecha_actualizacion: "2026-09-21T10:00:00Z",
              },
            ],
            total: 1,
            page: 1,
            page_size: 15,
            total_pages: 1,
          }),
        };
      }
      if (urlStr.includes("/admin/audit")) {
        return {
          ok: true,
          json: async () => ({
            items: [
              {
                id: "ev-1",
                fecha_evento: "2026-09-21T10:00:00Z",
                accion: "CREAR_USUARIO",
                entidad: "Usuario",
                entidad_id: "u-99",
                actor: {
                  id: "admin-uuid",
                  nombre: "Admin",
                  apellido: "Principal",
                  email: "admin@sena.edu.co",
                  rol: "SUPERADMIN",
                },
                referencia_id: "ref-1",
                detalle: { email: "nuevo@sena.edu.co" },
              },
            ],
            total: 1,
            page: 1,
            page_size: 25,
            total_pages: 1,
          }),
        };
      }
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
      return {
        ok: true,
        json: async () => [],
      };
    });
  });

  it("renders the administration banner and all 5 navigation tabs", () => {
    render(<AdminWorkspace />);

    expect(screen.getByText("Administración Central ASGARD")).toBeInTheDocument();
    expect(screen.getByText("Supervisión Institucional")).toBeInTheDocument();
    expect(screen.getByText("Usuarios y Credenciales")).toBeInTheDocument();
    expect(screen.getByText("Coordinaciones & Especialidades")).toBeInTheDocument();
    expect(screen.getByText("Equipos Ejecutores & Procesos")).toBeInTheDocument();
    expect(screen.getByText("Visor de Auditoría")).toBeInTheDocument();
  });

  it("renders supervision dashboard by default", async () => {
    render(<AdminWorkspace />);

    await waitFor(() => {
      expect(screen.getByText("Procesos Curriculares")).toBeInTheDocument();
      expect(screen.getByText("Programas Formación")).toBeInTheDocument();
    });
  });

  it("switches to Visor de Auditoria tab when clicked", async () => {
    render(<AdminWorkspace />);

    const auditTabBtn = screen.getByRole("button", { name: /visor de auditoría/i });
    fireEvent.click(auditTabBtn);

    await waitFor(() => {
      expect(screen.getByText(/visor de auditoría inmutable/i)).toBeInTheDocument();
    });
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
