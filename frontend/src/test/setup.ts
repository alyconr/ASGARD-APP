import "@testing-library/jest-dom";
import { vi } from "vitest";

// Mock useConfirm globally so tests do not throw "useConfirm debe ser utilizado dentro de un ConfirmProvider"
vi.mock("@/components/feedback/confirm-context", () => ({
  useConfirm: () => (options: any) => {
    // If window.confirm is stubbed/mocked, we can call it to satisfy old tests!
    if (typeof window !== "undefined" && typeof window.confirm === "function") {
      try {
        const res = window.confirm(options.message);
        return Promise.resolve(res);
      } catch {
        // Fallback
      }
    }
    return Promise.resolve(true);
  },
  ConfirmProvider: ({ children }: { children: React.ReactNode }) => children,
}));
