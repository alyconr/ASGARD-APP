"use client";

import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from "react";
import { Info, TriangleAlert } from "lucide-react";
import { cn } from "@/lib/utils";

interface ConfirmOptions {
  title: string;
  message: string;
  isDestructive?: boolean;
  confirmLabel?: string;
  cancelLabel?: string;
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
  const resolveRef = useRef<((value: boolean) => void) | null>(null);

  const confirm = useCallback((opts: ConfirmOptions): Promise<boolean> => {
    setOptions(opts);
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
                className={cn(
                  "inline-flex min-h-9 items-center justify-center rounded-lg px-3.5 py-2 text-xs font-semibold text-white transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2",
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
