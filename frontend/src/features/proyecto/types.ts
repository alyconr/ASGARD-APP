import type { DraftStatus } from "@/features/drafts/types";

export interface ProyectoDisponibilidadResponse {
  referencia_id: string;
  programa_id: string | null;
  estado_programa: DraftStatus | null;
  programa_completo: boolean;
  proyecto_bloqueado: boolean;
  estado_proyecto: DraftStatus;
  motivo: string | null;
  mensaje: string;
  accion_sugerida: "completar_y_cerrar_programa" | "iniciar_proyecto" | string;
}
