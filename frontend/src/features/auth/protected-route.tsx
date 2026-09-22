"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./auth-context";

export const DEFAULT_ALLOWED_ROLES = [
  "SUPERADMIN",
  "ADMIN",
  "LIDER_EQUIPO_EJECUTOR",
  "USUARIO_ADICIONAL",
] as const;

export interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: readonly string[] | string[];
}

export function ProtectedRoute({
  children,
  allowedRoles = DEFAULT_ALLOWED_ROLES,
}: ProtectedRouteProps): React.JSX.Element | null {
  const { user, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  const hasSession = isAuthenticated && !!user;
  const needsPasswordChange = Boolean(hasSession && user?.debe_cambiar_password);
  const hasAllowedRole = Boolean(
    hasSession && user?.roles && user.roles.some((role) => allowedRoles.includes(role)),
  );

  const isAuthorized = hasSession && !needsPasswordChange && hasAllowedRole;

  useEffect(() => {
    if (isLoading) return;

    if (!isAuthorized) {
      router.replace("/");
    }
  }, [isLoading, isAuthorized, router]);

  if (isLoading) {
    return (
      <div
        data-testid="asgard-loading-shield"
        className="flex min-h-screen flex-col items-center justify-center bg-[var(--paper)]"
      >
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-emerald-600" />
          <p className="text-sm font-semibold text-slate-600">
            Verificando sesión institucional...
          </p>
        </div>
      </div>
    );
  }

  if (!isAuthorized) {
    return null;
  }

  return <>{children}</>;
}
