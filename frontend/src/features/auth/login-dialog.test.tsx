import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LoginDialog } from "./login-dialog";

vi.mock("./auth-context", () => ({
  useAuth: () => ({
    login: vi.fn(),
    logout: vi.fn(),
    hasRole: vi.fn(),
    user: null,
    token: null,
    isLoading: false,
    isAuthenticated: false,
  }),
}));

describe("LoginDialog", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders quick login buttons in development environment", () => {
    render(<LoginDialog isOpen={true} onClose={vi.fn()} />);

    expect(screen.getByText(/Iniciar Sesión en ASGARD/i)).toBeDefined();
    expect(screen.getByText(/Accesos de prueba rápidos:/i)).toBeDefined();
    expect(screen.getByText(/Admin Pedagógico/i)).toBeDefined();
    expect(screen.getByText(/Líder Redes 01/i)).toBeDefined();
  });

  it("does not render quick login buttons in production environment", () => {
    vi.stubEnv("NODE_ENV", "production");

    render(<LoginDialog isOpen={true} onClose={vi.fn()} />);

    expect(screen.getByText(/Iniciar Sesión en ASGARD/i)).toBeDefined();
    expect(screen.queryByText(/Accesos de prueba rápidos:/i)).toBeNull();
    expect(screen.queryByText(/Admin Pedagógico/i)).toBeNull();
    expect(screen.queryByText(/Líder Redes 01/i)).toBeNull();

    vi.unstubAllEnvs();
  });
});
