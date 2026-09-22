import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import HomePage from "./page";
import DashboardPage from "./dashboard/page";

vi.mock("next/font/google", () => ({
  Plus_Jakarta_Sans: () => ({ variable: "landing-font" }),
  Caveat: () => ({ variable: "handwriting-font" }),
}));
vi.mock("@/features/landing/landing-page", () => ({
  LandingPage: () => <h1>Landing pública</h1>,
}));
vi.mock("@/features/dashboard/master-dashboard", () => ({
  MasterDashboard: () => <h1>Panel maestro existente</h1>,
}));
vi.mock("@/features/auth/auth-context", () => ({
  useAuth: () => ({
    user: { id: "1", roles: ["SUPERADMIN"], debe_cambiar_password: false },
    isAuthenticated: true,
    isLoading: false,
  }),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: vi.fn(),
    push: vi.fn(),
  }),
}));
afterEach(cleanup);
it("la raíz renderiza la landing", () => {
  render(<HomePage />);
  expect(screen.getByRole("heading")).toHaveTextContent("Landing pública");
});
it("dashboard conserva el panel maestro", () => {
  render(<DashboardPage />);
  expect(screen.getByRole("heading")).toHaveTextContent(
    "Panel maestro existente",
  );
});
