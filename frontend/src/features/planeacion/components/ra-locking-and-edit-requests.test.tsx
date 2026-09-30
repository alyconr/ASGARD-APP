import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  LockStatusBadge,
  LearningResultLockBanner,
  EditRequestButton,
  EditRequestModal,
  EditRequestStatus,
  type SelectableLearningResult,
} from "./edit-requests-components";
import {
  AdminEditRequestList,
  EditRequestApprovalModal,
} from "@/features/admin/revision/admin-edit-requests";
import * as api from "../planeacion-api";
import type { PlanningEditRequest } from "../planeacion-api";

vi.mock("../planeacion-api", async () => {
  const actual = await vi.importActual<typeof import("../planeacion-api")>(
    "../planeacion-api",
  );
  return {
    ...actual,
    crearSolicitudModificacion: vi.fn(),
    listarSolicitudesModificacion: vi.fn(),
    obtenerSolicitudModificacion: vi.fn(),
    aprobarSolicitudModificacion: vi.fn(),
    rechazarSolicitudModificacion: vi.fn(),
    listarVersionesResultados: vi.fn(),
  };
});

const mockResultados: SelectableLearningResult[] = [
  {
    id: "ra-1",
    codigo: "RA1",
    descripcion: "Analizar requerimientos del cliente",
    edit_status: "LOCKED",
    approved_at: "2026-09-30T10:00:00Z",
    approved_version: 1,
    unlock_request_id: null,
  },
  {
    id: "ra-2",
    codigo: "RA2",
    descripcion: "Construir la solución de software",
    edit_status: "LOCKED",
    approved_at: "2026-09-30T10:00:00Z",
    approved_version: 1,
    unlock_request_id: null,
  },
  {
    id: "ra-3",
    codigo: "RA3",
    descripcion: "Validar la implementación técnica",
    edit_status: "EDITABLE",
    approved_at: "2026-09-30T10:00:00Z",
    approved_version: 1,
    unlock_request_id: "20260041-0000-0000-0000-000000000000",
  },
];

const mockPendingRequest: PlanningEditRequest = {
  id: "req-12345678-abcd",
  codigo: "REQ-2026-0041",
  planning_id: "plan-1",
  referencia_id: "ref-1",
  programa_codigo: "220501",
  programa_nombre: "Análisis y Desarrollo de Software",
  proyecto_codigo: "123456",
  proyecto_nombre: "Sistema de Gestión Curricular",
  fase_nombre: "Fase 1",
  actividad_descripcion: "Actividad 1",
  planning_actividad: "Diseñar arquitectura",
  team_id: "team-1",
  team_name: "Equipo ADSO",
  team_nombre: "Equipo ADSO",
  requested_by: "lider-1",
  requested_by_name: "Carlos Líder",
  requested_by_nombre: "Carlos Líder",
  requested_by_email: "lider@sena.edu.co",
  reason: "Se requiere actualizar el alcance técnico de las evidencias",
  requested_changes: "Ajustar las evidencias de producto y desempeño en RA2",
  status: "PENDING",
  reviewed_by: null,
  reviewed_by_nombre: null,
  admin_response: null,
  created_at: "2026-09-30T11:00:00Z",
  reviewed_at: null,
  version: 1,
  items: [
    {
      id: "item-1",
      request_id: "req-12345678-abcd",
      learning_result_id: "ra-1",
      codigo_resultado: "RA1",
      descripcion: "Analizar requerimientos del cliente",
      descripcion_resultado: "Analizar requerimientos del cliente",
      requested: true,
      approved: false,
      edit_status: "LOCKED",
    },
    {
      id: "item-2",
      request_id: "req-12345678-abcd",
      learning_result_id: "ra-2",
      codigo_resultado: "RA2",
      descripcion: "Construir la solución de software",
      descripcion_resultado: "Construir la solución de software",
      requested: true,
      approved: false,
      edit_status: "LOCKED",
    },
  ],
};

describe("Bloqueo de Resultados de Aprendizaje y Solicitudes de Reapertura", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. RA bloqueado se muestra en modo solo lectura con versión y fecha de aprobación", () => {
    render(
      <div>
        <LockStatusBadge
          editStatus={mockResultados[0].edit_status}
          unlockRequestId={mockResultados[0].unlock_request_id}
          approvedVersion={mockResultados[0].approved_version}
        />
        <LearningResultLockBanner ra={mockResultados[0]} />
      </div>,
    );

    expect(
      screen.getByText("Resultado de aprendizaje aprobado"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/bloqueado para edición/i),
    ).toBeInTheDocument();
    expect(screen.getAllByText("v1").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByTestId("ra-lock-badge-locked")).toHaveTextContent(
      "LOCKED",
    );
  });

  it("2. Botón 'Solicitar modificación' es visible únicamente para el líder cuando la planeación está aprobada, descarga habilitada y RA bloqueados", () => {
    const onClick = vi.fn();

    // Caso 1: Integrante adicional (no líder) -> no debe ver el botón
    const { rerender } = render(
      <EditRequestButton
        planningApproved={true}
        downloadEnabled={true}
        learningResultsLocked={true}
        isTeamLeader={false}
        onClick={onClick}
      />,
    );
    expect(
      screen.queryByTestId("btn-solicitar-modificacion"),
    ).not.toBeInTheDocument();

    // Caso 2: Líder pero descarga no habilitada -> no debe ver el botón
    rerender(
      <EditRequestButton
        planningApproved={true}
        downloadEnabled={false}
        learningResultsLocked={true}
        isTeamLeader={true}
        onClick={onClick}
      />,
    );
    expect(
      screen.queryByTestId("btn-solicitar-modificacion"),
    ).not.toBeInTheDocument();

    // Caso 3: Líder + planeación aprobada + descarga habilitada + RA bloqueados -> visible
    rerender(
      <EditRequestButton
        planningApproved={true}
        downloadEnabled={true}
        learningResultsLocked={true}
        isTeamLeader={true}
        onClick={onClick}
      />,
    );
    const btn = screen.getByTestId("btn-solicitar-modificacion");
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveTextContent("Solicitar modificación");
    fireEvent.click(btn);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("3. Modal de solicitud valida campos obligatorios (al menos un RA, motivo y cambios propuestos) y envía la solicitud", async () => {
    vi.mocked(api.crearSolicitudModificacion).mockResolvedValue(
      mockPendingRequest,
    );
    const onSuccess = vi.fn();
    const onClose = vi.fn();

    render(
      <EditRequestModal
        isOpen={true}
        onClose={onClose}
        planningId="plan-1"
        learningResults={[mockResultados[0], mockResultados[1]]}
        onSuccess={onSuccess}
      />,
    );

    expect(
      screen.getByText("Solicitar reapertura de planeación"),
    ).toBeInTheDocument();

    const submitBtn = screen.getByTestId("btn-submit-edit-request");

    // 1) Sin seleccionar RA -> error de validación
    fireEvent.click(submitBtn);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Debe seleccionar al menos un Resultado de Aprendizaje",
    );

    // 2) Seleccionar RA2 pero sin motivo
    fireEvent.click(screen.getByTestId("checkbox-ra-ra-2"));
    fireEvent.click(submitBtn);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "El motivo de la solicitud es obligatorio",
    );

    // 3) Ingresar motivo pero sin cambios propuestos
    fireEvent.change(screen.getByTestId("input-edit-request-reason"), {
      target: { value: "Actualizar instrumentos de evaluación" },
    });
    fireEvent.click(submitBtn);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Debe especificar qué cambios propone realizar",
    );

    // 4) Ingresar cambios propuestos y enviar
    fireEvent.change(screen.getByTestId("input-edit-request-changes"), {
      target: { value: "Incluir rúbrica para la evidencia de desempeño" },
    });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.crearSolicitudModificacion).toHaveBeenCalledWith({
        planning_id: "plan-1",
        learning_result_ids: ["ra-2"],
        reason: "Actualizar instrumentos de evaluación",
        requested_changes: "Incluir rúbrica para la evidencia de desempeño",
      });
      expect(onSuccess).toHaveBeenCalledWith(mockPendingRequest);
    });
  });

  it("4. Estado de solicitud pendiente se muestra correctamente sin desbloquear los RA", () => {
    render(
      <div>
        <EditRequestStatus requests={[mockPendingRequest]} />
        <LockStatusBadge editStatus={mockResultados[1].edit_status} />
      </div>,
    );

    expect(
      screen.getByText("Solicitud de modificación pendiente"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Pendiente de revisión del Equipo Pedagógico"),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/RA2/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByTestId("ra-lock-badge-locked")).toHaveTextContent(
      "LOCKED",
    );
  });

  it("5. RA aprobados parcialmente muestran 'Edición autorizada' con botón Editar mientras los demás siguen bloqueados", () => {
    const onEditRa3 = vi.fn();

    render(
      <div>
        <div data-testid="ra-1-container">
          <LearningResultLockBanner ra={mockResultados[0]} />
        </div>
        <div data-testid="ra-3-container">
          <LearningResultLockBanner
            ra={mockResultados[2]}
            requestCode="REQ-2026-0041"
            onFocusEdit={onEditRa3}
          />
        </div>
      </div>,
    );

    // RA1 permanece bloqueado
    expect(
      screen.getByText("Resultado de aprendizaje aprobado"),
    ).toBeInTheDocument();

    // RA3 muestra Edición autorizada + código de solicitud + botón Editar
    expect(screen.getByText("Edición autorizada")).toBeInTheDocument();
    expect(screen.getByText(/REQ-2026-0041/)).toBeInTheDocument();

    const editBtn = screen.getByRole("button", { name: /Editar/i });
    fireEvent.click(editBtn);
    expect(onEditRa3).toHaveBeenCalledTimes(1);
  });

  it("6. Panel administrador pedagógico permite revisar solicitud, aprobar parcialmente RAs seleccionados o rechazar la solicitud", async () => {
    vi.mocked(api.listarSolicitudesModificacion).mockResolvedValue([
      mockPendingRequest,
    ]);
    vi.mocked(api.aprobarSolicitudModificacion).mockResolvedValue({
      ...mockPendingRequest,
      status: "PARTIALLY_APPROVED",
      admin_response: "Se autoriza únicamente RA2",
      items: [
        { ...mockPendingRequest.items[0], approved: false, edit_status: "LOCKED" },
        { ...mockPendingRequest.items[1], approved: true, edit_status: "EDITABLE" },
      ],
    });

    const onUpdated = vi.fn();

    render(
      <AdminEditRequestList
        referenciaId="ref-1"
        onRequestProcessed={onUpdated}
      />,
    );

    // Esperar a que cargue la lista
    await waitFor(() => {
      expect(screen.getByText("Carlos Líder")).toBeInTheDocument();
    });
    expect(screen.getByText("Equipo ADSO")).toBeInTheDocument();

    // Abrir modal de revisión de solicitud
    fireEvent.click(
      screen.getByTestId(`btn-revisar-solicitud-${mockPendingRequest.id}`),
    );

    expect(
      screen.getByTestId("admin-edit-request-approval-modal"),
    ).toBeInTheDocument();

    // Desmarcar RA1 para aprobar solo RA2 (aprobación parcial)
    const checkboxRa1 = screen.getByTestId("admin-authorize-ra-ra-1");
    fireEvent.click(checkboxRa1);

    fireEvent.change(screen.getByTestId("input-admin-response"), {
      target: { value: "Se autoriza únicamente RA2" },
    });

    fireEvent.click(screen.getByTestId("btn-approve-selected-ras"));

    await waitFor(() => {
      expect(api.aprobarSolicitudModificacion).toHaveBeenCalledWith(
        mockPendingRequest.id,
        {
          approved_learning_result_ids: ["ra-2"],
          admin_response: "Se autoriza únicamente RA2",
          expected_version: 1,
        },
      );
      expect(onUpdated).toHaveBeenCalled();
    });
  });

  it("6b. Modal de administrador pedagógico permite rechazar una solicitud manteniendo RAs bloqueados", async () => {
    vi.mocked(api.rechazarSolicitudModificacion).mockResolvedValue({
      ...mockPendingRequest,
      status: "REJECTED",
      admin_response: "No se justifican cambios sobre la versión aprobada",
    });

    const onProcessed = vi.fn();
    render(
      <EditRequestApprovalModal
        request={mockPendingRequest}
        onClose={vi.fn()}
        onProcessed={onProcessed}
      />,
    );

    fireEvent.change(screen.getByTestId("input-admin-response"), {
      target: { value: "No se justifican cambios sobre la versión aprobada" },
    });

    fireEvent.click(screen.getByTestId("btn-reject-edit-request"));

    await waitFor(() => {
      expect(api.rechazarSolicitudModificacion).toHaveBeenCalledWith(
        mockPendingRequest.id,
        {
          admin_response: "No se justifican cambios sobre la versión aprobada",
          expected_version: 1,
        },
      );
      expect(onProcessed).toHaveBeenCalled();
    });
  });
});
