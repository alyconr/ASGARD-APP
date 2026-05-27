import { getApiBaseUrl } from "@/lib/api";
import { EstadoDocumentalResponse } from "@/features/drafts/types";

export async function eliminarCargueCompleto(referenciaId: string): Promise<void> {
  const response = await fetch(
    `${getApiBaseUrl()}/proyectos/cargue/${referenciaId}`,
    {
      method: "DELETE",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    let errorDetail = "No fue posible eliminar el cargue completo.";
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        errorDetail = payload.detail;
      }
    } catch {}
    throw new Error(errorDetail);
  }
}

export async function getEstadoDocumental(
  referenciaId: string,
): Promise<EstadoDocumentalResponse> {
  const response = await fetch(
    `${getApiBaseUrl()}/drafts/${referenciaId}/estado-documental`,
    {
      method: "GET",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error("No fue posible recuperar el estado documental.");
  }

  return response.json() as Promise<EstadoDocumentalResponse>;
}
