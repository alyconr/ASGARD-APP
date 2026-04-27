export type DraftBlockType = "PROGRAMA" | "PROYECTO";

export type DraftStatus =
  | "BORRADOR"
  | "EN_REVISION"
  | "COMPLETO"
  | "BLOQUEADO";

export interface DraftSaveRequest {
  paso_actual: string;
  payload_json: Record<string, unknown>;
  estado_borrador: DraftStatus;
}

export interface DraftResponse {
  id: string;
  tipo_bloque: DraftBlockType;
  referencia_id: string;
  paso_actual: string;
  payload_json: Record<string, unknown>;
  estado_borrador: DraftStatus;
  ultima_edicion: string;
}

export class DraftApiError extends Error {
  readonly status: number;

  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "DraftApiError";
    this.status = status;
    this.detail = detail;
  }
}
