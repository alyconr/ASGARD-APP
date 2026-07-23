"use client";

import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from "react";
import { Check, Copy, Info, TriangleAlert } from "lucide-react";
import { cn } from "@/lib/utils";

interface ConfirmOptions {
  title: string;
  message: string;
  isDestructive?: boolean;
  confirmLabel?: string;
  cancelLabel?: string;
  details?: Array<{ label: string; value: string }>;
  requiredConfirmationText?: string;
}

type ConfirmFunction = (options: ConfirmOptions) => Promise<boolean>;

const ConfirmContext = createContext<ConfirmFunction | null>(null);

export function useConfirm(): ConfirmFunction {
  const context = useContext(ConfirmContext);
  if (!context) {
    throw new Error("useConfirm debe ser utilizado dentro de un ConfirmProvider");
  }
  return context;
}

interface ConfirmProviderProps {
  children: React.ReactNode;
}

export function ConfirmProvider({ children }: ConfirmProviderProps): React.JSX.Element {
  const [isOpen, setIsOpen] = useState(false);
  const [options, setOptions] = useState<ConfirmOptions | null>(null);
  const [confirmationText, setConfirmationText] = useState("");
  const [copiedValue, setCopiedValue] = useState<string | null>(null);
  const resolveRef = useRef<((value: boolean) => void) | null>(null);

  const confirm = useCallback((opts: ConfirmOptions): Promise<boolean> => {
    setOptions(opts);
    setConfirmationText("");
    setCopiedValue(null);
    setIsOpen(true);
    return new Promise<boolean>((resolve) => {
      resolveRef.current = resolve;
    });
  }, []);

  const handleConfirm = useCallback(() => {
    setIsOpen(false);
    if (resolveRef.current) {
      resolveRef.current(true);
      resolveRef.current = null;
    }
  }, []);

  const handleCancel = useCallback(() => {
    setIsOpen(false);
    if (resolveRef.current) {
      resolveRef.current(false);
      resolveRef.current = null;
    }
  }, []);

  const copyValue = useCallback(async (value: string) => {
    await navigator.clipboard.writeText(value);
    setCopiedValue(value);
  }, []);

  const confirmationMatches =
    !options?.requiredConfirmationText ||
    confirmationText.trim() === options.requiredConfirmationText;

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        handleCancel();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleCancel]);

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {isOpen && options && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity duration-300 animate-in fade-in"
            onClick={handleCancel}
          />

          {/* Modal Container */}
          <div className="relative w-full max-w-md transform overflow-hidden rounded-xl bg-white p-6 shadow-2xl transition-all duration-300 border border-slate-100 scale-100 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-start gap-3">
              {options.isDestructive ? (
                <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-rose-50 text-rose-600 border border-rose-100">
                  <TriangleAlert className="h-5 w-5" />
                </span>
              ) : (
                <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-100">
                  <Info className="h-5 w-5" />
                </span>
              )}
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-bold text-slate-950 uppercase tracking-wide">
                  {options.title}
                </h3>
                <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                  {options.message}
                </p>
                {options.details?.length ? (
                  <dl className="mt-4 grid gap-2">
                    {options.details.map((detail) => (
                      <div
                        key={detail.label}
                        className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2"
                      >
                        <dt className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">
                          {detail.label}
                        </dt>
                        <dd className="mt-1 flex items-center justify-between gap-3">
                          <span className="min-w-0 break-all text-xs font-semibold text-slate-900">
                            {detail.value}
                          </span>
                          <button
                            type="button"
                            aria-label={`Copiar ${detail.label}`}
                            onClick={() => void copyValue(detail.value)}
                            className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 transition hover:border-slate-300 hover:text-slate-900"
                          >
                            {copiedValue === detail.value ? (
                              <Check className="h-3.5 w-3.5" />
                            ) : (
                              <Copy className="h-3.5 w-3.5" />
                            )}
                          </button>
                        </dd>
                      </div>
                    ))}
                  </dl>
                ) : null}
                {options.requiredConfirmationText ? (
                  <label className="mt-4 block">
                    <span className="text-xs font-semibold text-slate-700">
                      Copia y pega este valor para confirmar:
                    </span>
                    <code className="mt-2 block break-all rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-900">
                      {options.requiredConfirmationText}
                    </code>
                    <input
                      autoFocus
                      value={confirmationText}
                      onChange={(event) => setConfirmationText(event.target.value)}
                      placeholder="Pega aquí el valor de confirmación"
                      className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-rose-500 focus:ring-2 focus:ring-rose-100"
                    />
                  </label>
                ) : null}
              </div>
            </div>

            <div className="mt-6 flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={handleCancel}
                className="inline-flex min-h-9 items-center justify-center rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
              >
                {options.cancelLabel ?? "Cancelar"}
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                disabled={!confirmationMatches}
                className={cn(
                  "inline-flex min-h-9 items-center justify-center rounded-lg px-3.5 py-2 text-xs font-semibold text-white transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-40",
                  options.isDestructive
                    ? "bg-rose-600 hover:bg-rose-700 focus-visible:outline-rose-600 shadow-md shadow-rose-600/10"
                    : "bg-[var(--accent)] hover:bg-[var(--accent-strong)] focus-visible:outline-[var(--accent)] shadow-md shadow-[var(--accent)]/10"
                )}
              >
                {options.confirmLabel ?? "Confirmar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  );
}
