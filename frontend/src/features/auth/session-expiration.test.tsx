import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import React, { useEffect } from "react";

import { AuthProvider, useAuth } from "./auth-context";
import { ProtectedRoute } from "./protected-route";
import { authFetch } from "@/lib/api";

const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: mockReplace,
    push: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

function ConsumerComponent(): React.JSX.Element {
  const { isAuthenticated, user } = useAuth();

  useEffect(() => {
    // Trigger protected fetch when authenticated
    if (isAuthenticated) {
      void authFetch("http://localhost:8000/api/v1/dashboard/programas");
    }
  }, [isAuthenticated]);

  return (
    <div>
      <div data-testid="auth-status">
        {isAuthenticated ? "AUTHENTICATED" : "UNAUTHENTICATED"}
      </div>
      <div data-testid="user-email">{user?.email ?? "NO_USER"}</div>
    </div>
  );
}

describe("Session Expiration Integration", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("invalidates session cleanly when protected request returns 401 and refresh fails", async () => {
    // 1. First call on mount: initial silent refresh succeeds
    let refreshAttempts = 0;
    const mockFetch = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/auth/refresh")) {
        refreshAttempts += 1;
        if (refreshAttempts === 1) {
          // Mount silent refresh succeeds
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => ({
              access_token: "initial-valid-token",
              user: {
                id: "user-123",
                email: "instructor@sena.edu.co",
                nombre: "Carlos",
                apellido: "Pérez",
                estado: "ACTIVO",
                activo: true,
                debe_cambiar_password: false,
                roles: ["SUPERADMIN"],
              },
            }),
          });
        }
        // Second refresh attempt (after 401) fails!
        return Promise.resolve({
          ok: false,
          status: 401,
          json: async () => ({ detail: "Refresh token revocado o expirado" }),
        });
      }

      if (url.includes("/dashboard/programas")) {
        // Protected API returns 401 (expired access token)
        return Promise.resolve({
          ok: false,
          status: 401,
          json: async () => ({ detail: "Token expirado" }),
        });
      }

      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({}),
      });
    });

    vi.stubGlobal("fetch", mockFetch);

    render(
      <AuthProvider>
        <ProtectedRoute>
          <ConsumerComponent />
        </ProtectedRoute>
      </AuthProvider>,
    );

    // Initial state: resolves to authenticated
    await waitFor(() => {
      expect(screen.getByTestId("auth-status")).toHaveTextContent("AUTHENTICATED");
      expect(screen.getByTestId("user-email")).toHaveTextContent("instructor@sena.edu.co");
    });

    // When /dashboard/programas returns 401 and refresh fails:
    // AuthProvider must transition immediately to unauthenticated
    // and ProtectedRoute must unmount children and call router.replace("/")
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/");
    });

    await waitFor(() => {
      expect(screen.queryByTestId("auth-status")).toBeNull();
    });
  });
});
