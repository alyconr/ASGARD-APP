import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PlaneacionWizardShell } from "./planeacion-wizard-shell";
import type {
  ContextoCompetencia,
  PlaneacionContextoResponse,
  PlaneacionListResponse,
  PlaneacionResponse,
} from "../planeacion-api";
import * as api from "../planeacion-api";

vi.mock("../planeacion-api", () => ({
  listPlaneacionesProyecto: vi.fn(),
  fetchPlaneacionDetalle: vi.fn(),
  savePlaneacionBorrador: vi.fn(),
  confirmarPlaneacion: vi.fn(),
  deletePlaneacion: vi.fn(),
  fetchPlaneacionDocumentoConfig: vi.fn(),
  savePlaneacionDocumentoConfig: vi.fn(),
  fetchFormatoOficialEstadoIndividual: vi.fn(),
  fetchFormatoOficialEstadoConsolidado: vi.fn(),
  generarFormatoOficialConsolidado: vi.fn(),
  downloadFormatoOficialIndividual: vi.fn(),
  downloadFormatoOficialConsolidado: vi.fn(),
  fetchEstadoActualRevision: vi.fn(),
  fetchPreflightRevision: vi.fn(),
  enviarProcesoARevision: vi.fn(),
  listarSolicitudesModificacion: vi.fn(),
}));

const mockCompetencia: ContextoCompetencia = {
  id: "comp-1",
  codigo_competencia: "220501001",
  nombre_competencia: "Diseñar la arquitectura del software",
  resultados: [
    {
      id: "rap-1",
      codigo_resultado: "220501001-01",
      descripcion: "Resultado 1: Identificar requisitos técnicos",
      tipo_resultado: "ESPECIFICO",
      edit_status: "EDITABLE",
    },
  ],
  conocimientos_saber: [
    {
      id: "know-saber-1",
      descripcion: "Concepto 1: Fundamentos de bases de datos",
    },
  ],
  conocimientos_proceso: [
    {
      id: "know-proc-1",
      descripcion: "Proceso 1: Aplicar diagramas UML",
    },
  ],
  criterios: [
    {
      id: "crit-1",
      descripcion: "Criterio 1: Elabora el modelo conceptual",
    },
  ],
};

const mockContexto: PlaneacionContextoResponse = {
  programa_id: "prog-1",
  codigo_programa: "220501",
  nombre_programa: "Análisis y Desarrollo de Software",
  version_programa: "1",
  proyecto_id: "proj-1",
  codigo_proyecto: "123456",
  nombre_proyecto: "Sistema de Información de Pruebas",
  version_proyecto: "2",
  fases: [
    {
      id: "fase-1",
      nombre_fase: "Fase 1: Análisis",
      actividades: [
        {
          id: "act-1",
          descripcion: "Actividad 1: Levantar requerimientos",
          competencias: [mockCompetencia],
        },
      ],
    },
  ],
};

const mockPlanningsList: PlaneacionListResponse[] = [
  {
    id: "plan-1",
    proyecto_id: "proj-1",
    fase_id: "fase-1",
    actividad_id: "act-1",
    nombre_fase: "Fase 1: Análisis",
    descripcion_actividad: "Actividad 1: Levantar requerimientos",
    actividades_aprendizaje: "Determinar requerimientos de software",
    estado: "COMPLETO",
    official_document_status: "NOT_GENERATED",
    competencias_count: 1,
    resultados_count: 1,
    resultados_especificos: 1,
    resultados_transversales: 0,
    fecha_actualizacion: "2026-09-30T10:00:00Z",
  },
];

const mockPlanningDetail: PlaneacionResponse = {
  id: "plan-1",
  proyecto_id: "proj-1",
  fase_id: "fase-1",
  actividad_id: "act-1",
  estado: "COMPLETO",
  datos_complementarios: {
    actividades_aprendizaje: "Determinar requerimientos de software",
  },
  resultados_ids: ["rap-1"],
  conocimientos_ids: ["know-saber-1", "know-proc-1"],
  criterios_ids: ["crit-1"],
  competencias: [],
  storage_key: null,
  file_name: null,
  content_type: null,
  checksum_sha256: null,
  fecha_generacion: null,
  version: 1,
  official_document_status: "NOT_GENERATED",
};

describe("Official Format Sync & Assisted Review Submission Flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(api, "listPlaneacionesProyecto").mockResolvedValue(mockPlanningsList);
    vi.spyOn(api, "fetchPlaneacionDetalle").mockResolvedValue(mockPlanningDetail);
    vi.spyOn(api, "fetchEstadoActualRevision").mockResolvedValue(null);
    vi.spyOn(api, "listarSolicitudesModificacion").mockResolvedValue([]);
    vi.spyOn(api, "fetchPlaneacionDocumentoConfig").mockResolvedValue({
      proyecto_id: "proj-1",
      fecha_elaboracion: "2026-09-30",
      modalidad_formacion: "Presencial",
      clasificacion_informacion: "PUBLICA",
      equipo_gestion_curricular: ["Ana Instructor"],
      regional: "Distrito Capital",
      centro_formacion: "Centro de prueba",
      storage_key: null,
      file_name: null,
      content_type: null,
      checksum_sha256: null,
      fecha_generacion: null,
      version: 1,
      official_document_status: "NOT_GENERATED",
    });
  });

  it("1. shows assisted modal when official format is NOT_GENERATED, then generates format in MinIO and submits to review", async () => {
    vi.spyOn(api, "fetchFormatoOficialEstadoConsolidado").mockResolvedValue({
      listo: true,
      official_document_status: "NOT_GENERATED",
      faltantes: [],
      planeaciones_completas: 1,
      borradores_excluidos: 0,
      storage_key: null,
      file_name: null,
      checksum_sha256: null,
      fecha_generacion: null,
    });

    vi.spyOn(api, "fetchPreflightRevision").mockResolvedValue({
      listo: false,
      official_document_status: "NOT_GENERATED",
      requiere_generar_formato: true,
      pendientes: ["Debe generar previamente el consolidado oficial GPFI-F-134 V05 en MinIO."],
      resumen: {
        total_actividades_proyecto: 1,
        planeaciones_completas: 1,
        planeaciones_borrador: 0,
        actividades_sin_planeacion: [],
        es_entrega_parcial: false,
        faltantes_count: 1,
        version_actual: 0,
        estado_actual: "BORRADOR",
        official_document_status: "NOT_GENERATED",
        requiere_generar_formato: true,
      },
    });

    vi.spyOn(api, "generarFormatoOficialConsolidado").mockResolvedValue({
      storage_key: "planeacion/consolidado.xlsx",
      file_name: "GPFI-F-134V05-planeacion-pedagogica.xlsx",
      content_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      checksum_sha256: "abc123456",
      fecha_generacion: "2026-09-30T12:00:00Z",
      version: 1,
      filas_generadas: 2,
      planeaciones_incluidas: 1,
      borradores_excluidos: 0,
      official_document_status: "CURRENT",
    });

    vi.spyOn(api, "enviarProcesoARevision").mockResolvedValue({
      id: "ent-1",
      proceso_curricular_id: "proc-1",
      referencia_id: "ref-uuid",
      equipo_ejecutor_nombre: "Equipo ADSO",
      codigo_programa: "220501",
      nombre_programa: "Análisis y Desarrollo de Software",
      codigo_proyecto: "123456",
      nombre_proyecto: "Sistema de Información",
      lider_nombre: "Juan Lider",
      lider_email: "lider@sena.edu.co",
      version: 1,
      estado: "ENVIADO_REVISION",
      fecha_envio: "2026-09-30T12:01:00Z",
      observaciones_pendientes_count: 0,
      observaciones_ajustadas_count: 0,
      observaciones_resueltas_count: 0,
      descarga_habilitada: false,
      snapshot_metadatos: {},
      observaciones: [],
      historial_versiones: [],
    });

    render(<PlaneacionWizardShell contexto={mockContexto} referenciaId="ref-uuid" />);

    expect(await screen.findByText("○ Formato todavía no generado")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generar formato oficial" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Descargar consolidado oficial" })).toBeInTheDocument();

    fireEvent.click(
      screen.getAllByRole("button", { name: /Enviar a Revisión Pedagógica/i })[0],
    );

    expect(
      await screen.findByText("La planeación tiene cambios pendientes"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/La versión oficial almacenada todavía no contiene los últimos cambios realizados en esta planeación/i),
    ).toBeInTheDocument();

    const generateAndSubmitBtn = screen.getByRole("button", {
      name: "Generar formato oficial y enviar a revisión",
    });
    fireEvent.click(generateAndSubmitBtn);

    await waitFor(() => {
      expect(api.generarFormatoOficialConsolidado).toHaveBeenCalledWith("proj-1");
      expect(api.enviarProcesoARevision).toHaveBeenCalledWith("ref-uuid", undefined);
    });
  });

  it("2. submits directly without showing the pending changes modal when official_document_status is CURRENT", async () => {
    vi.spyOn(api, "fetchFormatoOficialEstadoConsolidado").mockResolvedValue({
      listo: true,
      official_document_status: "CURRENT",
      faltantes: [],
      planeaciones_completas: 1,
      borradores_excluidos: 0,
      storage_key: "planeacion/consolidado.xlsx",
      file_name: "GPFI-F-134V05-planeacion-pedagogica.xlsx",
      checksum_sha256: "abc123456",
      fecha_generacion: "2026-09-30T12:00:00Z",
    });

    vi.spyOn(api, "fetchPreflightRevision").mockResolvedValue({
      listo: true,
      official_document_status: "CURRENT",
      requiere_generar_formato: false,
      pendientes: [],
      resumen: {
        total_actividades_proyecto: 1,
        planeaciones_completas: 1,
        planeaciones_borrador: 0,
        actividades_sin_planeacion: [],
        es_entrega_parcial: false,
        faltantes_count: 0,
        version_actual: 0,
        estado_actual: "BORRADOR",
        official_document_status: "CURRENT",
        requiere_generar_formato: false,
      },
    });

    vi.spyOn(api, "enviarProcesoARevision").mockResolvedValue({
      id: "ent-1",
      proceso_curricular_id: "proc-1",
      referencia_id: "ref-uuid",
      equipo_ejecutor_nombre: "Equipo ADSO",
      codigo_programa: "220501",
      nombre_programa: "Análisis y Desarrollo de Software",
      codigo_proyecto: "123456",
      nombre_proyecto: "Sistema de Información",
      lider_nombre: "Juan Lider",
      lider_email: "lider@sena.edu.co",
      version: 1,
      estado: "ENVIADO_REVISION",
      fecha_envio: "2026-09-30T12:01:00Z",
      observaciones_pendientes_count: 0,
      observaciones_ajustadas_count: 0,
      observaciones_resueltas_count: 0,
      descarga_habilitada: false,
      snapshot_metadatos: {},
      observaciones: [],
      historial_versiones: [],
    });

    render(<PlaneacionWizardShell contexto={mockContexto} referenciaId="ref-uuid" />);

    expect(await screen.findByText("✓ Formato actualizado")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Formato oficial actualizado" })).toBeInTheDocument();

    fireEvent.click(
      screen.getAllByRole("button", { name: /Enviar a Revisión Pedagógica/i })[0],
    );

    await waitFor(() => {
      expect(api.enviarProcesoARevision).toHaveBeenCalledWith("ref-uuid");
    });
    expect(screen.queryByText("La planeación tiene cambios pendientes")).not.toBeInTheDocument();
  });

  it("3. detects OUTDATED status after editing planning/RAP, shows 'Actualizar formato oficial', and runs assisted sync on submit", async () => {
    vi.spyOn(api, "fetchFormatoOficialEstadoConsolidado").mockResolvedValue({
      listo: true,
      official_document_status: "OUTDATED",
      faltantes: [],
      planeaciones_completas: 1,
      borradores_excluidos: 0,
      storage_key: "planeacion/consolidado.xlsx",
      file_name: "GPFI-F-134V05-planeacion-pedagogica.xlsx",
      checksum_sha256: "abc123456",
      fecha_generacion: "2026-09-30T10:00:00Z",
    });

    vi.spyOn(api, "fetchPreflightRevision").mockResolvedValue({
      listo: false,
      official_document_status: "OUTDATED",
      requiere_generar_formato: true,
      pendientes: [
        "La versión oficial almacenada todavía no contiene los últimos cambios realizados en esta planeación.",
      ],
      resumen: {
        total_actividades_proyecto: 1,
        planeaciones_completas: 1,
        planeaciones_borrador: 0,
        actividades_sin_planeacion: [],
        es_entrega_parcial: false,
        faltantes_count: 1,
        version_actual: 1,
        estado_actual: "AJUSTES_SOLICITADOS",
        official_document_status: "OUTDATED",
        requiere_generar_formato: true,
      },
    });

    render(<PlaneacionWizardShell contexto={mockContexto} referenciaId="ref-uuid" />);

    expect(await screen.findByText("⚠ Cambios pendientes de actualizar")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Actualizar formato oficial" })).toBeInTheDocument();

    fireEvent.click(
      screen.getAllByRole("button", { name: /Enviar a Revisión Pedagógica/i })[0],
    );

    expect(
      await screen.findByText("La planeación tiene cambios pendientes"),
    ).toBeInTheDocument();
  });

  it("4. displays friendly institutional error on MinIO failure and does NOT submit planning for review", async () => {
    vi.spyOn(api, "fetchFormatoOficialEstadoConsolidado").mockResolvedValue({
      listo: true,
      official_document_status: "OUTDATED",
      faltantes: [],
      planeaciones_completas: 1,
      borradores_excluidos: 0,
      storage_key: "planeacion/consolidado.xlsx",
      file_name: "GPFI-F-134V05-planeacion-pedagogica.xlsx",
      checksum_sha256: "abc123456",
      fecha_generacion: "2026-09-30T10:00:00Z",
    });

    vi.spyOn(api, "fetchPreflightRevision").mockResolvedValue({
      listo: false,
      official_document_status: "OUTDATED",
      requiere_generar_formato: true,
      pendientes: [
        "La versión oficial almacenada todavía no contiene los últimos cambios realizados en esta planeación.",
      ],
      resumen: {
        total_actividades_proyecto: 1,
        planeaciones_completas: 1,
        planeaciones_borrador: 0,
        actividades_sin_planeacion: [],
        es_entrega_parcial: false,
        faltantes_count: 1,
        version_actual: 1,
        estado_actual: "BORRADOR",
        official_document_status: "OUTDATED",
        requiere_generar_formato: true,
      },
    });

    vi.spyOn(api, "generarFormatoOficialConsolidado").mockRejectedValue(
      new Error("MinIO key missing / storage error"),
    );

    render(<PlaneacionWizardShell contexto={mockContexto} referenciaId="ref-uuid" />);

    const submitButtons = await screen.findAllByRole("button", {
      name: /Enviar a Revisión Pedagógica/i,
    });
    fireEvent.click(submitButtons[0]);

    const generateAndSubmitBtn = await screen.findByRole("button", {
      name: "Generar formato oficial y enviar a revisión",
    });
    fireEvent.click(generateAndSubmitBtn);

    expect(
      await screen.findByText(
        "No fue posible almacenar el formato oficial en el repositorio documental. Intenta nuevamente.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/MinIO key missing/i)).not.toBeInTheDocument();
    expect(api.enviarProcesoARevision).not.toHaveBeenCalled();
  });

  it("5. downloads consolidated official document when approved without triggering format generation", async () => {
    vi.spyOn(api, "fetchFormatoOficialEstadoConsolidado").mockResolvedValue({
      listo: true,
      official_document_status: "CURRENT",
      faltantes: [],
      planeaciones_completas: 1,
      borradores_excluidos: 0,
      storage_key: "planeacion/consolidado.xlsx",
      file_name: "GPFI-F-134V05-planeacion-pedagogica.xlsx",
      checksum_sha256: "abc123456",
      fecha_generacion: "2026-09-30T12:00:00Z",
    });

    vi.spyOn(api, "fetchEstadoActualRevision").mockResolvedValue({
      id: "ent-1",
      proceso_curricular_id: "proc-1",
      referencia_id: "ref-uuid",
      equipo_ejecutor_nombre: "Equipo ADSO",
      codigo_programa: "220501",
      nombre_programa: "Análisis y Desarrollo de Software",
      codigo_proyecto: "123456",
      nombre_proyecto: "Sistema de Información",
      lider_nombre: "Juan Lider",
      lider_email: "lider@sena.edu.co",
      version: 1,
      estado: "APROBADO",
      fecha_envio: "2026-09-30T12:01:00Z",
      observaciones_pendientes_count: 0,
      observaciones_ajustadas_count: 0,
      observaciones_resueltas_count: 0,
      descarga_habilitada: true,
      snapshot_metadatos: {},
      observaciones: [],
      historial_versiones: [],
    });

    vi.spyOn(api, "downloadFormatoOficialConsolidado").mockResolvedValue();

    render(<PlaneacionWizardShell contexto={mockContexto} referenciaId="ref-uuid" />);

    const downloadBtn = await screen.findByRole("button", {
      name: "Descargar consolidado oficial",
    });
    expect(downloadBtn).not.toBeDisabled();
    fireEvent.click(downloadBtn);

    await waitFor(() => {
      expect(api.downloadFormatoOficialConsolidado).toHaveBeenCalledWith("proj-1");
    });
    expect(api.generarFormatoOficialConsolidado).not.toHaveBeenCalled();
  });
});
