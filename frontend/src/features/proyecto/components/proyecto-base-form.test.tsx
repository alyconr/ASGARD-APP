import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProyectoBaseForm } from "./proyecto-base-form";
import type { ProyectoWizardPayload } from "@/features/proyecto/types";

const emptyValue: ProyectoWizardPayload["proyecto"] = {
  proyecto_formativo_id: null,
  codigo_proyecto: "",
  nombre_proyecto: "",
  version_proyecto: "",
};

describe("ProyectoBaseForm", () => {
  it("renders the base project fields with required validation", () => {
    render(<ProyectoBaseForm value={emptyValue} onFieldChange={vi.fn()} />);

    expect(screen.getByLabelText(/codigo del proyecto/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/nombre del proyecto/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/version del proyecto/i)).toBeInTheDocument();
    expect(screen.getByText("0/3")).toBeInTheDocument();
    expect(
      screen.getAllByText(/este campo es obligatorio/i),
    ).toHaveLength(3);
  });

  it("emits edits for codigo, nombre and version", () => {
    const onFieldChange = vi.fn();
    render(
      <ProyectoBaseForm value={emptyValue} onFieldChange={onFieldChange} />,
    );

    fireEvent.change(screen.getByLabelText(/codigo del proyecto/i), {
      target: { value: "PR-001" },
    });
    fireEvent.change(screen.getByLabelText(/nombre del proyecto/i), {
      target: { value: "Proyecto formativo base" },
    });
    fireEvent.change(screen.getByLabelText(/version del proyecto/i), {
      target: { value: "1" },
    });

    expect(onFieldChange).toHaveBeenNthCalledWith(
      1,
      "codigo_proyecto",
      "PR-001",
    );
    expect(onFieldChange).toHaveBeenNthCalledWith(
      2,
      "nombre_proyecto",
      "Proyecto formativo base",
    );
    expect(onFieldChange).toHaveBeenNthCalledWith(
      3,
      "version_proyecto",
      "1",
    );
  });

  it("shows completed required count when values are present", () => {
    render(
      <ProyectoBaseForm
        value={{
          ...emptyValue,
          codigo_proyecto: "PR-001",
          nombre_proyecto: "Proyecto formativo base",
          version_proyecto: "1",
        }}
        onFieldChange={vi.fn()}
      />,
    );

    expect(screen.getByText("3/3")).toBeInTheDocument();
    expect(
      screen.queryByText(/este campo es obligatorio/i),
    ).not.toBeInTheDocument();
  });
});
