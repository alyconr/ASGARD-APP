import { getApiBaseUrl } from "@/lib/api";

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
