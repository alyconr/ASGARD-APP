const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";

let inMemoryAccessToken: string | null = null;
export interface SessionRefreshResult {
  accessToken: string;
  user: any;
}

let refreshSessionPromise: Promise<SessionRefreshResult | null> | null = null;

export type AuthInvalidationHandler = () => void;
let authInvalidationHandler: AuthInvalidationHandler | null = null;

export function setAuthInvalidationHandler(
  handler: AuthInvalidationHandler | null,
): void {
  authInvalidationHandler = handler;
}

export function notifyAuthInvalidated(): void {
  setAuthToken(null);
  if (authInvalidationHandler) {
    try {
      authInvalidationHandler();
    } catch {
      // Evitar que errores en el listener interrumpan el flujo de red
    }
  }
}

export function getApiBaseUrl(): string {
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
    DEFAULT_API_BASE_URL
  );
}

export function getAuthToken(): string | null {
  return inMemoryAccessToken;
}

export function setAuthToken(token: string | null): void {
  inMemoryAccessToken = token;
}

/**
 * Single-flight session refresh exchange.
 * Ensures concurrent requests or component mounts reuse a single in-flight refresh request
 * avoiding race conditions with single-use refresh token rotation.
 */
export async function refreshSessionSingleFlight(): Promise<SessionRefreshResult | null> {
  if (refreshSessionPromise) {
    return refreshSessionPromise;
  }

  refreshSessionPromise = (async () => {
    try {
      const res = await fetch(`${getApiBaseUrl()}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      if (!res.ok) {
        notifyAuthInvalidated();
        return null;
      }

      const data = await res.json();
      const newToken = (data.access_token as string) || null;
      if (!newToken) {
        notifyAuthInvalidated();
        return null;
      }
      setAuthToken(newToken);
      return {
        accessToken: newToken,
        user: data.user,
      };
    } catch {
      notifyAuthInvalidated();
      return null;
    } finally {
      refreshSessionPromise = null;
    }
  })();

  return refreshSessionPromise;
}

export async function refreshTokenSingleFlight(): Promise<string | null> {
  const result = await refreshSessionSingleFlight();
  return result?.accessToken ?? null;
}

export async function authFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const headers = new Headers(init?.headers);
  const token = getAuthToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(input, {
    ...init,
    credentials: init?.credentials ?? "include",
    headers,
  });

  // Intercept 401 and attempt automatic single-flight token refresh once
  const urlString =
    typeof input === "string"
      ? input
      : input instanceof URL
      ? input.toString()
      : (input as Request).url || "";
  const isAuthRoute =
    urlString.includes("/auth/login") || urlString.includes("/auth/refresh");

  if (response.status === 401 && !isAuthRoute) {
    const newToken = await refreshTokenSingleFlight();
    if (newToken) {
      const retryHeaders = new Headers(init?.headers);
      retryHeaders.set("Authorization", `Bearer ${newToken}`);
      return fetch(input, {
        ...init,
        credentials: init?.credentials ?? "include",
        headers: retryHeaders,
      });
    } else {
      notifyAuthInvalidated();
    }
  }

  return response;
}

