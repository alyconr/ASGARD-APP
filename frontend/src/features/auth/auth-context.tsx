"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { AuthState, User } from "./types";
import { authFetch, getApiBaseUrl } from "@/lib/api";

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<User>;
  logout: () => void;
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
    const token = localStorage.getItem("asgard_token");
    if (!token) {
      setState({
        user: null,
        token: null,
        isLoading: false,
        isAuthenticated: false,
      });
      return;
    }

    authFetch(`${getApiBaseUrl()}/auth/me`)
      .then(async (res) => {
        if (!res.ok) {
          throw new Error("Token expirado");
        }
        const user = (await res.json()) as User;
        setState({
          user,
          token,
          isLoading: false,
          isAuthenticated: true,
        });
      })
      .catch(() => {
        localStorage.removeItem("asgard_token");
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Error al iniciar sesión" }));
      throw new Error(err.detail || "Credenciales incorrectas");
    }

    const data = await res.json();
    localStorage.setItem("asgard_token", data.access_token);
    setState({
      user: data.user,
      token: data.access_token,
      isLoading: false,
      isAuthenticated: true,
    });
    return data.user;
  };

  const logout = () => {
    localStorage.removeItem("asgard_token");
    setState({
      user: null,
      token: null,
      isLoading: false,
      isAuthenticated: false,
    });
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
