import {
  DraftApiError,
  type DraftBlockType,
  type DraftResponse,
  type DraftSaveRequest,
} from "@/features/drafts/types";
import { getApiBaseUrl } from "@/lib/api";

function buildDraftUrl(blockType: DraftBlockType, referenceId: string): string {
  return `${getApiBaseUrl()}/drafts/${blockType}/${referenceId}`;
}

async function parseErrorResponse(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
  } catch {
    return "No fue posible completar la operacion con borradores.";
  }

  return "No fue posible completar la operacion con borradores.";
}

async function requestDraft(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<DraftResponse> {
  const response = await fetch(input, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new DraftApiError(
      response.status,
      await parseErrorResponse(response),
    );
  }

  return (await response.json()) as DraftResponse;
}

export async function getDraft(
  blockType: DraftBlockType,
  referenceId: string,
): Promise<DraftResponse> {
  return requestDraft(buildDraftUrl(blockType, referenceId), {
    method: "GET",
  });
}

export async function saveDraft(
  blockType: DraftBlockType,
  referenceId: string,
  payload: DraftSaveRequest,
): Promise<DraftResponse> {
  return requestDraft(buildDraftUrl(blockType, referenceId), {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
