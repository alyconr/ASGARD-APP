import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { WizardGuideAssistant } from "@/features/guide/wizard-guide-assistant";
import type { WizardGuideState } from "@/features/guide/wizard-guide-engine";

const guide: WizardGuideState = {
  wizard: "programa",
  severity: "warning",
  eyebrow: "Guia ASGARD",
  title: "Confirma la importacion",
  message: "El preview es valido; confirma la importacion.",
  checklist: [
    { id: "preview", label: "Preview valido", status: "done" },
    { id: "import", label: "Importacion pendiente", status: "current" },
  ],
  primaryAction: { label: "Ir a revision", href: "/programa" },
};

describe("WizardGuideAssistant", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("renders the floating assistant with severity, checklist and CTA", () => {
    render(<WizardGuideAssistant guide={guide} storageKey="test" />);

    expect(
      screen.getByLabelText("Asistente guiado ASGARD"),
    ).toBeInTheDocument();
    expect(screen.getByText("Confirma la importacion")).toBeInTheDocument();
    expect(screen.getByText("Checklist 1/2")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /ir a revision/i })).toHaveAttribute(
      "href",
      "/programa",
    );
  });

  it("persists the collapsed state in local storage", () => {
    const { unmount } = render(
      <WizardGuideAssistant guide={guide} storageKey="persist" />,
    );

    fireEvent.click(screen.getByRole("button", { name: /colapsar guia/i }));
    unmount();

    render(<WizardGuideAssistant guide={guide} storageKey="persist" />);

    expect(
      screen.getByLabelText("Asistente guiado ASGARD colapsado"),
    ).toBeInTheDocument();
  });
});
