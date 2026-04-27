import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProgramaBaseForm } from "./programa-base-form";
import { createEmptyProgramaPayload } from "../constants";

describe("ProgramaBaseForm", () => {
  it("should render correctly with empty values", () => {
    const value = createEmptyProgramaPayload("ref-123").programa;
    const onFieldChange = vi.fn();

    render(<ProgramaBaseForm value={value} onFieldChange={onFieldChange} />);

    // Titles
    expect(screen.getByText("Datos minimos del programa")).toBeInTheDocument();

    // Labels
    expect(screen.getByText("Codigo del programa")).toBeInTheDocument();
    expect(screen.getByText("Nombre del programa")).toBeInTheDocument();
    expect(screen.getByText("Version del programa")).toBeInTheDocument();

    // Required/Optional badges
    const requiredBadges = screen.getAllByText("Obligatorio");
    expect(requiredBadges.length).toBe(2); // codigo_programa, nombre_programa
    const optionalBadge = screen.getByText("Opcional");
    expect(optionalBadge).toBeInTheDocument();

    // Completed info
    expect(screen.getByText("0/2")).toBeInTheDocument();
  });

  it("should reflect filled values and calculate completed fields correctly", () => {
    const value = createEmptyProgramaPayload("ref-123").programa;
    value.codigo_programa = "123456";

    const onFieldChange = vi.fn();

    render(<ProgramaBaseForm value={value} onFieldChange={onFieldChange} />);

    expect(screen.getByDisplayValue("123456")).toBeInTheDocument();
    expect(screen.getByText("1/2")).toBeInTheDocument();
  });

  it("should call onFieldChange when input changes", () => {
    const value = createEmptyProgramaPayload("ref-123").programa;
    const onFieldChange = vi.fn();

    render(<ProgramaBaseForm value={value} onFieldChange={onFieldChange} />);

    const input = screen.getByPlaceholderText("Ej. 228118"); // codigo_programa
    fireEvent.change(input, { target: { value: "987654" } });

    expect(onFieldChange).toHaveBeenCalledWith("codigo_programa", "987654");
  });

  it("should show required hint when required input is empty", () => {
    const value = createEmptyProgramaPayload("ref-123").programa;
    const onFieldChange = vi.fn();

    render(<ProgramaBaseForm value={value} onFieldChange={onFieldChange} />);

    // Since it starts empty, the hint should be present for both required fields
    const hints = screen.getAllByText(
      "Puedes guardar el borrador incompleto; este dato sera necesario para avanzar en tareas posteriores.",
    );
    expect(hints.length).toBe(2);
  });
});
