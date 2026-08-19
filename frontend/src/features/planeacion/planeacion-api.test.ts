import { afterEach, describe, expect, it, vi } from "vitest";

import {
  downloadFormatoOficialConsolidado,
  downloadFormatoOficialIndividual,
  generarFormatoOficialConsolidado,
} from "./planeacion-api";

describe("planeacion official workbook API", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("downloads the individual workbook as a backend Blob", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(new Blob(["xlsx"]), {
        status: 200,
        headers: {
          "Content-Disposition":
            "attachment; filename*=UTF-8''GPFI-F-134V05-planeacion.xlsx",
        },
      }),
    );
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:official-workbook");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    await downloadFormatoOficialIndividual("plan-1");

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(
        "/planeaciones/plan-1/descargar-formato-oficial",
      ),
      expect.objectContaining({ method: "GET" }),
    );
    expect(URL.createObjectURL).toHaveBeenCalled();
  });

  it("uses the project endpoints for consolidated generation and download", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            storage_key: "consolidado.xlsx",
            file_name: "GPFI-F-134V05-planeacion-pedagogica.xlsx",
            content_type:
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            checksum_sha256: "a".repeat(64),
            fecha_generacion: "2026-07-29T12:00:00Z",
            version: 1,
            filas_generadas: 2,
            planeaciones_incluidas: 2,
            borradores_excluidos: 1,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(new Blob(["xlsx"]), { status: 200 }),
      );
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:consolidated");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    const generated = await generarFormatoOficialConsolidado("project-1");
    await downloadFormatoOficialConsolidado("project-1");

    expect(generated.planeaciones_incluidas).toBe(2);
    expect(fetchMock.mock.calls[0][0]).toContain(
      "/planeaciones/proyecto/project-1/generar-formato-oficial",
    );
    expect(fetchMock.mock.calls[1][0]).toContain(
      "/planeaciones/proyecto/project-1/descargar-formato-oficial",
    );
  });
});
