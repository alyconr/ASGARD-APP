import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LandingPage } from "./landing-page";

const auth = vi.hoisted(() => ({
  isAuthenticated: false,
  isLoading: false,
  user: null as null | { debe_cambiar_password: boolean },
  refreshUser: vi.fn(),
}));
const push = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/features/auth/auth-context", () => ({ useAuth: () => auth }));
vi.mock("@/features/auth/login-dialog", () => ({
  LoginDialog: ({ isOpen }: { isOpen: boolean }) =>
    isOpen ? <div role="dialog">Login existente</div> : null,
}));
vi.mock("@/features/auth/force-change-password-dialog", () => ({
  ForceChangePasswordDialog: ({ isOpen }: { isOpen: boolean }) =>
    isOpen ? <div role="dialog">Cambio obligatorio</div> : null,
}));

beforeEach(() => {
  auth.isAuthenticated = false;
  auth.isLoading = false;
  auth.user = null;
  push.mockClear();
});
afterEach(cleanup);

describe("Landing ASGARD", () => {
  it("muestra el hero, las acciones y las cinco capacidades", () => {
    render(<LandingPage />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Construye planeaciones pedagógicas con claridad y acompañamiento",
    );
    expect(
      screen.getByRole("link", { name: "Ver cómo funciona" }),
    ).toHaveAttribute("href", "#proceso");
    expect(
      within(
        screen.getByRole("region", { name: "Proceso y capacidades de ASGARD" }),
      ).getAllByRole("listitem"),
    ).toHaveLength(5);
  });
  it.each(["Ingresar", "Comenzar ahora"])(
    "%s abre el login existente para visitantes",
    (name) => {
      render(<LandingPage />);
      fireEvent.click(screen.getByRole("button", { name }));
      expect(screen.getByRole("dialog")).toHaveTextContent("Login existente");
      expect(push).not.toHaveBeenCalled();
    },
  );
  it.each(["Ir al panel", "Comenzar ahora"])(
    "%s lleva al usuario autenticado al panel",
    (name) => {
      auth.isAuthenticated = true;
      auth.user = { debe_cambiar_password: false };
      render(<LandingPage />);
      fireEvent.click(screen.getByRole("button", { name }));
      expect(push).toHaveBeenCalledWith("/dashboard");
    },
  );
  it("espera el cambio obligatorio de contraseña antes de entrar", () => {
    const { rerender } = render(<LandingPage />);
    fireEvent.click(screen.getByRole("button", { name: "Comenzar ahora" }));
    auth.isAuthenticated = true;
    auth.user = { debe_cambiar_password: true };
    rerender(<LandingPage />);
    expect(screen.getByRole("dialog")).toHaveTextContent("Cambio obligatorio");
    expect(push).not.toHaveBeenCalled();
    auth.user = { debe_cambiar_password: false };
    rerender(<LandingPage />);
    expect(push).toHaveBeenCalledWith("/dashboard");
  });
  it("espera a resolver la sesión existente", () => {
    auth.isLoading = true;
    render(<LandingPage />);
    expect(screen.getByRole("button", { name: "Ingresar" })).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Comenzar ahora" }),
    ).toBeDisabled();
  });
});
