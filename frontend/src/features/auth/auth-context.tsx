"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { AuthState, User } from "./types";
import { authFetch, getApiBaseUrl, setAuthToken } from "@/lib/api";

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  hasRole: (...roleNames: string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isLoading: true,
    isAuthenticated: false,
  });

  useEffect(() => {
    // Attempt silent refresh using HttpOnly cookie on mount
    fetch(`${getApiBaseUrl()}/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    })
      .then(async (res) => {
        if (!res.ok) {
          throw new Error("No active session");
        }
        const data = await res.json();
        setAuthToken(data.access_token);
        setState({
          user: data.user,
          token: data.access_token,
          isLoading: false,
          isAuthenticated: true,
        });
      })
      .catch(() => {
        setAuthToken(null);
        setState({
          user: null,
          token: null,
          isLoading: false,
          isAuthenticated: false,
        });
      });
  }, []);

  const login = async (email: string, password: string): Promise<User> => {
    const res = await fetch(`${getApiBaseUrl()}/auth/login`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Error al iniciar sesión" }));
      throw new Error(err.detail || "Credenciales incorrectas");
    }

    const data = await res.json();
    setAuthToken(data.access_token);
    setState({
      user: data.user,
      token: data.access_token,
      isLoading: false,
      isAuthenticated: true,
    });
    return data.user;
  };

  const logout = async (): Promise<void> => {
    try {
      await authFetch(`${getApiBaseUrl()}/auth/logout`, {
        method: "POST",
      });
    } catch {
      // Ignorar errores de red al cerrar sesión
    } finally {
      setAuthToken(null);
      setState({
        user: null,
        token: null,
        isLoading: false,
        isAuthenticated: false,
      });
    }
  };

  const refreshUser = async (): Promise<void> => {
    try {
      const res = await authFetch(`${getApiBaseUrl()}/auth/me`);
      if (res.ok) {
        const userData = await res.json();
        setState((prev) => ({
          ...prev,
          user: userData,
        }));
      }
    } catch (err) {
      console.error("Error refreshing user profile:", err);
    }
  };

  const hasRole = (...roleNames: string[]): boolean => {
    if (!state.user || !state.user.roles) return false;
    return roleNames.some((r) => state.user?.roles.includes(r));
  };

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        logout,
        refreshUser,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth debe usarse dentro de un AuthProvider");
  }
  return context;
}
