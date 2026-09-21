import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { authFetch, getAuthToken, refreshTokenSingleFlight, setAuthToken } from "./api";

describe("api / authFetch single-flight refresh", () => {
  beforeEach(() => {
    setAuthToken(null);
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("coalesces concurrent refresh calls into a single HTTP request", async () => {
    let networkCalls = 0;
    const mockFetch = vi.fn().mockImplementation(async () => {
      networkCalls++;
      // Simulate network latency
      await new Promise((resolve) => setTimeout(resolve, 50));
      return {
        ok: true,
        json: async () => ({ access_token: "rotated-jwt-token-123" }),
      };
    });
    vi.stubGlobal("fetch", mockFetch);

    // Call 3 refreshes simultaneously
    const [t1, t2, t3] = await Promise.all([
      refreshTokenSingleFlight(),
      refreshTokenSingleFlight(),
      refreshTokenSingleFlight(),
    ]);

    expect(networkCalls).toBe(1);
    expect(t1).toBe("rotated-jwt-token-123");
    expect(t2).toBe("rotated-jwt-token-123");
    expect(t3).toBe("rotated-jwt-token-123");
    expect(getAuthToken()).toBe("rotated-jwt-token-123");

    vi.unstubAllGlobals();
  });

  it("retries request once after 401 when refresh succeeds", async () => {
    let callCount = 0;
    const mockFetch = vi.fn().mockImplementation(async (url: string) => {
      if (url.includes("/auth/refresh")) {
        return {
          ok: true,
          json: async () => ({ access_token: "fresh-token-456" }),
        };
      }
      callCount++;
      if (callCount === 1) {
        return {
          status: 401,
          ok: false,
        };
      }
      return {
        status: 200,
        ok: true,
        json: async () => ({ data: "success" }),
      };
    });
    vi.stubGlobal("fetch", mockFetch);

    setAuthToken("initial-stale-token");
    const res = await authFetch("http://localhost:8000/api/v1/protected-data");

    expect(res.status).toBe(200);
    expect(getAuthToken()).toBe("fresh-token-456");

    vi.unstubAllGlobals();
  });
});
