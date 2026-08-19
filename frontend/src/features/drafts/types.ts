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

export interface DocumentoMetadataDTO {
  original_filename: string;
  storage_key: string;
  size_bytes: number;
  content_type: string;
  checksum_sha256: string;
  updated_at?: string | null;
}

export interface EstadoDocumentalResponse {
  programa_excel: DocumentoMetadataDTO | null;
  proyecto_excel: DocumentoMetadataDTO | null;
  programa_pdf: DocumentoMetadataDTO | null;
  proyecto_pdf: DocumentoMetadataDTO | null;
  programa_importado: boolean;
  proyecto_importado: boolean;
  documentos_habilitados: boolean;
  cargue_pdf_habilitado: boolean;
}
