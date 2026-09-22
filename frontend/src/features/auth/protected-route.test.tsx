import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProtectedRoute } from "./protected-route";
import type { User } from "./types";

const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: mockReplace,
    push: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

let mockAuthState = {
  user: null as User | null,
  token: null as string | null,
  isLoading: false,
  isAuthenticated: false,
};

vi.mock("./auth-context", () => ({
  useAuth: () => mockAuthState,
}));

function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: "user-test-uuid",
    email: "test@sena.edu.co",
    nombre: "Instructor",
    apellido: "SENA",
    estado: "ACTIVO",
    activo: true,
    debe_cambiar_password: false,
    roles: ["SUPERADMIN"],
    ...overrides,
  };
}

describe("ProtectedRoute", () => {
  beforeEach(() => {
    mockReplace.mockReset();
    mockAuthState = {
      user: null,
      token: null,
      isLoading: false,
      isAuthenticated: false,
    };
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("A. isLoading=true: no renderiza children, no monta contenido protegido y no redirige prematuramente", () => {
    mockAuthState = {
      user: null,
      token: null,
      isLoading: true,
      isAuthenticated: false,
    };

    render(
      <ProtectedRoute>
        <div data-testid="protected-content">Contenido Privado</div>
      </ProtectedRoute>,
    );

    expect(screen.queryByTestId("protected-content")).toBeNull();
    expect(screen.getByTestId("asgard-loading-shield")).toBeDefined();
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it("B. no autenticado: children no se renderizan y router.replace('/') se ejecuta", () => {
    mockAuthState = {
      user: null,
      token: null,
      isLoading: false,
      isAuthenticated: false,
    };

    render(
      <ProtectedRoute>
        <div data-testid="protected-content">Contenido Privado</div>
      </ProtectedRoute>,
    );

    expect(screen.queryByTestId("protected-content")).toBeNull();
    expect(mockReplace).toHaveBeenCalledWith("/");
  });

  it("C. autenticado SUPERADMIN: renderiza children y no redirige", () => {
    mockAuthState = {
      user: makeUser({ roles: ["SUPERADMIN"] }),
      token: "valid-jwt",
      isLoading: false,
      isAuthenticated: true,
    };

    render(
      <ProtectedRoute>
        <div data-testid="protected-content">Contenido Privado</div>
      </ProtectedRoute>,
    );

    expect(screen.getByTestId("protected-content")).toBeDefined();
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it("D. autenticado ADMIN: renderiza children y no redirige", () => {
    mockAuthState = {
      user: makeUser({ roles: ["ADMIN"] }),
      token: "valid-jwt",
      isLoading: false,
      isAuthenticated: true,
    };

    render(
      <ProtectedRoute>
        <div data-testid="protected-content">Contenido Privado</div>
      </ProtectedRoute>,
    );

    expect(screen.getByTestId("protected-content")).toBeDefined();
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it("E. autenticado LIDER_EQUIPO_EJECUTOR: renderiza children y no redirige", () => {
    mockAuthState = {
      user: makeUser({ roles: ["LIDER_EQUIPO_EJECUTOR"] }),
      token: "valid-jwt",
      isLoading: false,
      isAuthenticated: true,
    };

    render(
      <ProtectedRoute>
        <div data-testid="protected-content">Contenido Privado</div>
      </ProtectedRoute>,
    );

    expect(screen.getByTestId("protected-content")).toBeDefined();
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it("F. autenticado USUARIO_ADICIONAL: renderiza children y no redirige", () => {
    mockAuthState = {
      user: makeUser({ roles: ["USUARIO_ADICIONAL"] }),
      token: "valid-jwt",
      isLoading: false,
      isAuthenticated: true,
    };

    render(
      <ProtectedRoute>
        <div data-testid="protected-content">Contenido Privado</div>
      </ProtectedRoute>,
    );

    expect(screen.getByTestId("protected-content")).toBeDefined();
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it("G. usuario sin rol permitido: no renderiza children y redirige a '/'", () => {
    mockAuthState = {
      user: makeUser({ roles: ["ROL_NO_PERMITIDO"] }),
      token: "valid-jwt",
      isLoading: false,
      isAuthenticated: true,
    };

    render(
      <ProtectedRoute>
        <div data-testid="protected-content">Contenido Privado</div>
      </ProtectedRoute>,
    );

    expect(screen.queryByTestId("protected-content")).toBeNull();
    expect(mockReplace).toHaveBeenCalledWith("/");
  });

  it("H. debe_cambiar_password=true: no renderiza children y redirige a '/'", () => {
    mockAuthState = {
      user: makeUser({ roles: ["SUPERADMIN"], debe_cambiar_password: true }),
      token: "valid-jwt",
      isLoading: false,
      isAuthenticated: true,
    };

    render(
      <ProtectedRoute>
        <div data-testid="protected-content">Contenido Privado</div>
      </ProtectedRoute>,
    );

    expect(screen.queryByTestId("protected-content")).toBeNull();
    expect(mockReplace).toHaveBeenCalledWith("/");
  });
});
