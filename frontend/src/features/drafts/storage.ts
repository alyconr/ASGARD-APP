import type { DraftStatus } from "@/features/drafts/types";

const ACTIVE_PROGRAMA_DRAFT_KEY = "sena.active-programa-draft-reference";
const KNOWN_PROGRAMA_DRAFTS_KEY = "sena.known-programa-drafts";

export interface KnownDraftSummary {
  referenciaId: string;
  pasoActual: string;
  updatedAt: string;
  estado: DraftStatus;
  label: string;
}

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

function readLocalStorage(key: string): string | null {
  if (!isBrowser()) {
    return null;
  }

  return window.localStorage.getItem(key);
}

function writeLocalStorage(key: string, value: string): void {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.setItem(key, value);
}

function removeLocalStorage(key: string): void {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.removeItem(key);
}

export function getActiveProgramaDraftReference(): string | null {
  return readLocalStorage(ACTIVE_PROGRAMA_DRAFT_KEY);
}

export function setActiveProgramaDraftReference(referenceId: string): void {
  writeLocalStorage(ACTIVE_PROGRAMA_DRAFT_KEY, referenceId);
}

export function clearActiveProgramaDraftReference(): void {
  removeLocalStorage(ACTIVE_PROGRAMA_DRAFT_KEY);
}

export function listKnownProgramaDrafts(): KnownDraftSummary[] {
  const rawValue = readLocalStorage(KNOWN_PROGRAMA_DRAFTS_KEY);
  if (rawValue === null) {
    return [];
  }

  try {
    const parsed = JSON.parse(rawValue) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed
      .filter((item): item is KnownDraftSummary => {
        if (typeof item !== "object" || item === null) {
          return false;
        }

        const candidate = item as Partial<KnownDraftSummary>;
        return (
          typeof candidate.referenciaId === "string" &&
          typeof candidate.pasoActual === "string" &&
          typeof candidate.updatedAt === "string" &&
          typeof candidate.estado === "string" &&
          typeof candidate.label === "string"
        );
      })
      .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
  } catch {
    return [];
  }
}

export function rememberProgramaDraft(
  summary: KnownDraftSummary,
): KnownDraftSummary[] {
  const nextDrafts = [
    summary,
    ...listKnownProgramaDrafts().filter(
      (draft) => draft.referenciaId !== summary.referenciaId,
    ),
  ].slice(0, 8);

  writeLocalStorage(KNOWN_PROGRAMA_DRAFTS_KEY, JSON.stringify(nextDrafts));
  return nextDrafts;
}

export function forgetProgramaDraft(referenceId: string): KnownDraftSummary[] {
  const nextDrafts = listKnownProgramaDrafts().filter(
    (draft) => draft.referenciaId !== referenceId,
  );
  writeLocalStorage(KNOWN_PROGRAMA_DRAFTS_KEY, JSON.stringify(nextDrafts));
  return nextDrafts;
}

export function clearKnownProgramaDrafts(): KnownDraftSummary[] {
  removeLocalStorage(KNOWN_PROGRAMA_DRAFTS_KEY);
  return [];
}
