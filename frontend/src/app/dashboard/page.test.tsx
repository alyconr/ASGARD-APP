import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DashboardPage from "./page";

const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: mockReplace,
    push: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

import type { User } from "@/features/auth/types";

vi.mock("@/features/dashboard/master-dashboard", () => ({
  MasterDashboard: () => <div data-testid="master-dashboard-content">Master Dashboard Real</div>,
}));

let mockAuthState: {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
} = {
  user: null,
  token: null,
  isLoading: false,
  isAuthenticated: false,
};

vi.mock("@/features/auth/auth-context", () => ({
  useAuth: () => mockAuthState,
}));

describe("DashboardPage (/dashboard)", () => {
  beforeEach(() => {
    mockReplace.mockReset();
    mockAuthState = {
      user: null,
      token: null,
      isLoading: false,
      isAuthenticated: false,
    };
  });

  it("never mounts MasterDashboard when unauthenticated and redirects to /", () => {
    render(<DashboardPage />);

    expect(screen.queryByTestId("master-dashboard-content")).toBeNull();
    expect(mockReplace).toHaveBeenCalledWith("/");
  });

  it("never mounts MasterDashboard while AuthProvider is loading", () => {
    mockAuthState = {
      user: null,
      token: null,
      isLoading: true,
      isAuthenticated: false,
    };

    render(<DashboardPage />);

    expect(screen.queryByTestId("master-dashboard-content")).toBeNull();
    expect(screen.getByTestId("asgard-loading-shield")).toBeDefined();
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it("mounts MasterDashboard when user is authenticated with a valid role", () => {
    mockAuthState = {
      user: {
        id: "usr-1",
        email: "superadmin@sena.edu.co",
        nombre: "Super",
        apellido: "Admin",
        roles: ["SUPERADMIN"],
        activo: true,
        estado: "ACTIVO",
        debe_cambiar_password: false,
      },
      token: "jwt-token",
      isLoading: false,
      isAuthenticated: true,
    };

    render(<DashboardPage />);

    expect(screen.getByTestId("master-dashboard-content")).toBeDefined();
    expect(mockReplace).not.toHaveBeenCalled();
  });
});
