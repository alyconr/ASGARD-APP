import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { ExtractorSenaInstructions } from "./extractor-sena-instructions";

const referenceId = "11111111-1111-4111-9111-111111111111";
const gptUrl =
  "https://chatgpt.com/g/g-69babd0cd3408191aea277054eb1071d-extractor-sena-de-competencias-y-rap";

describe("ExtractorSenaInstructions", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("opens automatically once per program reference and remembers acknowledgement", async () => {
    render(
      <ExtractorSenaInstructions referenceId={referenceId} scope="programa" />,
    );

    expect(
      await screen.findByRole("dialog", {
        name: /instrucciones para cargar el programa de formacion/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /abrir gpt extractor sena/i }),
    ).toHaveAttribute("href", gptUrl);

    fireEvent.click(screen.getByRole("button", { name: /entendido/i }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    render(
      <ExtractorSenaInstructions referenceId={referenceId} scope="programa" />,
    );

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("keeps instructions available for manual reopening", async () => {
    window.localStorage.setItem(
      `sena-extractor-instructions:proyecto:${referenceId}`,
      "seen",
    );

    render(
      <ExtractorSenaInstructions referenceId={referenceId} scope="proyecto" />,
    );

    fireEvent.click(screen.getByRole("button", { name: /instrucciones/i }));

    expect(
      await screen.findByRole("dialog", {
        name: /instrucciones para cargar el proyecto formativo/i,
      }),
    ).toBeInTheDocument();
  });
});
