"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/auth-context";
import { getActiveProgramaDraftReference } from "@/features/drafts/storage";
import { authFetch, getApiBaseUrl } from "@/lib/api";
import { notify } from "@/components/feedback/notifications";

interface ExecutorTeamGuardProps {
  children: React.ReactNode;
  referenciaId?: string;
}

export function ExecutorTeamGuard({
  children,
  referenciaId,
}: ExecutorTeamGuardProps): React.JSX.Element | null {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const [isVerifying, setIsVerifying] = useState(true);
  const [hasAccess, setHasAccess] = useState(false);

  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated || !user) {
      router.replace("/");
      return;
    }

    const activeRef = referenciaId || getActiveProgramaDraftReference();

    // Verify user belongs to at least one active executor team
    authFetch(`${getApiBaseUrl()}/equipos/mis-equipos`)
      .then(async (res) => {
        if (!res.ok) {
          throw new Error("No fue posible verificar tus equipos ejecutores");
        }
        const teams = await res.json();
        const activeTeams = Array.isArray(teams)
          ? teams.filter(
              (t: { estado?: string }) => !t.estado || t.estado === "ACTIVO",
            )
          : [];

        if (activeTeams.length === 0) {
          notify.error("Acceso restringido a procesos curriculares", {
            description:
              "Debes pertenecer a un Equipo Ejecutor activo para acceder al wizard curricular. Inicia o solicita tu asignación desde el panel principal.",
          });
          router.replace("/dashboard");
          return;
        }

        // If an active process reference is set, verify access to this specific process
        if (activeRef) {
          try {
            const procRes = await authFetch(
              `${getApiBaseUrl()}/procesos/${activeRef}/acceso`,
            );
            if (!procRes.ok && procRes.status === 403) {
              notify.error("Acceso no autorizado al proceso", {
                description:
                  "No tienes autorización para operar en este proceso curricular dentro de tu equipo ejecutor.",
              });
              router.replace("/dashboard");
              return;
            }
          } catch (e) {
            console.warn("Could not verify specific process access:", e);
          }
        }

        setHasAccess(true);
      })
      .catch((err) => {
        console.error("ExecutorTeamGuard check failed:", err);
        notify.error("Error de verificación", {
          description:
            "Ocurrió un error verificando la autorización de tu equipo ejecutor.",
        });
        router.replace("/dashboard");
      })
      .finally(() => {
        setIsVerifying(false);
      });
  }, [isAuthenticated, isLoading, user, router]);

  if (isLoading || isVerifying) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-6">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-600 border-t-transparent" />
          <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
            Verificando autorización de Equipo Ejecutor...
          </p>
        </div>
      </div>
    );
  }

  if (!hasAccess) {
    return null;
  }

  return <>{children}</>;
}
