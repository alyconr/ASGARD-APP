"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  aprobarSolicitudModificacion,
  listarSolicitudesModificacion,
  PlanningEditRequest,
  rechazarSolicitudModificacion,
} from "@/features/planeacion/planeacion-api";

// -----------------------------------------------------------------------------
// 1. EditRequestApprovalModal (Section 10)
// -----------------------------------------------------------------------------
export interface EditRequestApprovalModalProps {
  request: PlanningEditRequest | null;
  onClose: () => void;
  onProcessed: (updated: PlanningEditRequest) => void;
}

export function EditRequestApprovalModal({
  request,
  onClose,
  onProcessed,
}: EditRequestApprovalModalProps) {
  const [selectedRaIds, setSelectedRaIds] = useState<string[]>([]);
  const [adminResponse, setAdminResponse] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (request) {
      setSelectedRaIds(request.items.map((item) => item.learning_result_id));
      setAdminResponse(request.admin_response || "");
      setError(null);
    }
  }, [request]);

  if (!request) return null;

  const isPending = request.status === "PENDING";
  const codeLabel =
    request.codigo || request.code || `REQ-${request.id.slice(0, 6).toUpperCase()}`;

  const toggleRa = (raId: string) => {
    if (!isPending) return;
    setSelectedRaIds((prev) =>
      prev.includes(raId) ? prev.filter((id) => id !== raId) : [...prev, raId],
    );
  };

  const handleApproveSelected = async () => {
    setError(null);
    if (selectedRaIds.length === 0) {
      setError(
        "Seleccione al menos un Resultado de Aprendizaje para autorizar, o utilice 'Rechazar solicitud'.",
      );
      return;
    }
    try {
      setSubmitting(true);
      const updated = await aprobarSolicitudModificacion(request.id, {
        approved_learning_result_ids: selectedRaIds,
        admin_response: adminResponse.trim() || null,
        expected_version: request.version,
      });
      onProcessed(updated);
      onClose();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No fue posible aprobar la solicitud de modificación.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    setError(null);
    try {
      setSubmitting(true);
      const updated = await rechazarSolicitudModificacion(request.id, {
        admin_response: adminResponse.trim() || null,
        expected_version: request.version,
      });
      onProcessed(updated);
      onClose();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No fue posible rechazar la solicitud de modificación.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      data-testid="admin-edit-request-approval-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs"
    >
      <div className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50 px-6 py-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded bg-slate-900 px-2 py-0.5 font-mono text-xs font-bold text-white">
                {codeLabel}
              </span>
              <h3 className="text-base font-extrabold text-slate-900">
                Revisar solicitud de modificación
              </h3>
            </div>
            <p className="mt-0.5 text-xs text-slate-500">
              {request.programa_nombre || "Programa"} • Equipo:{" "}
              {request.team_name || request.team_nombre || "Equipo Ejecutor"}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-200/60 hover:text-slate-700"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto p-6">
          {error && (
            <div
              role="alert"
              className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs font-semibold text-rose-700"
            >
              {error}
            </div>
          )}

          <div className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50/70 p-4 text-xs sm:grid-cols-2">
            <div>
              <span className="block text-[10px] font-bold text-slate-400 uppercase">
                Líder solicitante
              </span>
              <p className="mt-0.5 font-bold text-slate-900">
                {request.requested_by_name || request.requested_by_nombre || "Líder"}
              </p>
              <p className="text-[11px] text-slate-500">{request.requested_by_email}</p>
            </div>
            <div>
              <span className="block text-[10px] font-bold text-slate-400 uppercase">
                Planeación
              </span>
              <p className="mt-0.5 font-bold text-slate-900">
                {request.planning_actividad ||
                  `${request.fase_nombre || "Fase"} — ${request.actividad_descripcion || "Actividad"}`}
              </p>
            </div>
            <div className="sm:col-span-2">
              <span className="block text-[10px] font-bold text-slate-400 uppercase">
                Motivo de la solicitud
              </span>
              <p className="mt-0.5 text-slate-800">{request.reason}</p>
            </div>
            <div className="sm:col-span-2">
              <span className="block text-[10px] font-bold text-slate-400 uppercase">
                Cambios propuestos
              </span>
              <p className="mt-0.5 text-slate-800">{request.requested_changes}</p>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <label className="block text-xs font-bold tracking-wide text-slate-700 uppercase">
                Resultados de Aprendizaje solicitados ({selectedRaIds.length} de{" "}
                {request.items.length} seleccionados para autorizar)
              </label>
            </div>
            <p className="mt-0.5 text-xs text-slate-500">
              Marque los Resultados de Aprendizaje cuya edición desea autorizar. Los RA
              no marcados permanecerán en estado LOCKED.
            </p>
            <div className="mt-3 space-y-2">
              {request.items.map((item, idx) => {
                const checked = isPending
                  ? selectedRaIds.includes(item.learning_result_id)
                  : Boolean(item.approved);
                const code = item.codigo_resultado || `RA${idx + 1}`;
                return (
                  <label
                    key={item.id}
                    className={`flex cursor-pointer items-start justify-between gap-3 rounded-xl border p-3.5 transition ${
                      checked
                        ? "border-emerald-400 bg-emerald-50/70"
                        : "border-slate-200 bg-white"
                    } ${!isPending ? "cursor-default" : ""}`}
                  >
                    <div className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        data-testid={`admin-authorize-ra-${item.learning_result_id}`}
                        checked={checked}
                        disabled={!isPending}
                        onChange={() => toggleRa(item.learning_result_id)}
                        className="mt-0.5 h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                      />
                      <div className="text-xs">
                        <span className="font-bold text-slate-900">
                          {code} — {item.descripcion || item.descripcion_resultado}
                        </span>
                        {item.competencia_nombre && (
                          <p className="mt-0.5 text-[11px] text-slate-500">
                            Competencia: {item.competencia_codigo} —{" "}
                            {item.competencia_nombre}
                          </p>
                        )}
                      </div>
                    </div>
                    <span
                      className={`shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
                        checked
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-slate-200 text-slate-700"
                      }`}
                    >
                      {checked ? "☑ Autorizar (EDITABLE)" : "☐ Permanece LOCKED"}
                    </span>
                  </label>
                );
              })}
            </div>
          </div>

          <div>
            <label
              htmlFor="admin-edit-request-response"
              className="block text-xs font-bold tracking-wide text-slate-700 uppercase"
            >
              Respuesta / observaciones del administrador
            </label>
            <textarea
              id="admin-edit-request-response"
              data-testid="input-admin-response"
              rows={3}
              disabled={!isPending}
              value={adminResponse}
              onChange={(e) => setAdminResponse(e.target.value)}
              placeholder="Indique observaciones pedagógicas sobre la aprobación total, parcial o rechazo..."
              className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-xs text-slate-900 focus:border-emerald-600 focus:outline-none disabled:bg-slate-50"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 bg-slate-50 px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-100"
          >
            Cerrar
          </button>

          {isPending && (
            <div className="flex items-center gap-3">
              <button
                type="button"
                data-testid="btn-reject-edit-request"
                disabled={submitting}
                onClick={handleReject}
                className="rounded-xl border border-rose-300 bg-rose-50 px-4 py-2 text-xs font-bold text-rose-700 transition hover:bg-rose-100 disabled:opacity-50"
              >
                Rechazar solicitud
              </button>
              <button
                type="button"
                data-testid="btn-approve-selected-ras"
                disabled={submitting}
                onClick={handleApproveSelected}
                className="rounded-xl bg-emerald-600 px-5 py-2 text-xs font-bold text-white shadow-xs transition hover:bg-emerald-700 disabled:opacity-50"
              >
                {submitting ? "Procesando..." : "Aprobar seleccionados"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// 2. AdminEditRequestDetail
// -----------------------------------------------------------------------------
export interface AdminEditRequestDetailProps {
  request: PlanningEditRequest;
  onReviewClick: (req: PlanningEditRequest) => void;
  onViewPlanning?: (req: PlanningEditRequest) => void;
}

export function AdminEditRequestDetail({
  request,
  onReviewClick,
  onViewPlanning,
}: AdminEditRequestDetailProps) {
  const codeLabel =
    request.codigo || request.code || `REQ-${request.id.slice(0, 6).toUpperCase()}`;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded bg-slate-900 px-2 py-0.5 font-mono text-xs font-bold text-white">
              {codeLabel}
            </span>
            <span className="text-sm font-extrabold text-slate-900">
              {request.programa_nombre || "Programa de Formación"}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Equipo: <strong>{request.team_name || request.team_nombre || "—"}</strong> •
            Líder:{" "}
            <strong>
              {request.requested_by_name || request.requested_by_nombre || "—"}
            </strong>
          </p>
        </div>
        <div className="flex items-center gap-2">
          {onViewPlanning && (
            <button
              type="button"
              onClick={() => onViewPlanning(request)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-50"
            >
              Ver planeación
            </button>
          )}
          <button
            type="button"
            onClick={() => onReviewClick(request)}
            className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-bold text-white hover:bg-slate-800"
          >
            Revisar solicitud
          </button>
        </div>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// 3. AdminEditRequestList (Section 9)
// -----------------------------------------------------------------------------
export interface AdminEditRequestListProps {
  referenciaId?: string | null;
  planningId?: string | null;
  onViewPlanning?: (req: PlanningEditRequest) => void;
  onRequestProcessed?: (req: PlanningEditRequest) => void;
}

export function AdminEditRequestList({
  referenciaId,
  planningId,
  onViewPlanning,
  onRequestProcessed,
}: AdminEditRequestListProps) {
  const [requests, setRequests] = useState<PlanningEditRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [activeRequest, setActiveRequest] = useState<PlanningEditRequest | null>(null);

  const loadRequests = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listarSolicitudesModificacion({
        referencia_id: referenciaId || undefined,
        planning_id: planningId || undefined,
        status: statusFilter || undefined,
      });
      setRequests(data);
    } catch {
      setRequests([]);
    } finally {
      setLoading(false);
    }
  }, [referenciaId, planningId, statusFilter]);

  useEffect(() => {
    loadRequests();
  }, [loadRequests]);

  const statusBadge = (status: string) => {
    switch (status) {
      case "PENDING":
        return "bg-amber-100 text-amber-800 border-amber-300";
      case "APPROVED":
        return "bg-emerald-100 text-emerald-800 border-emerald-300";
      case "PARTIALLY_APPROVED":
        return "bg-teal-100 text-teal-800 border-teal-300";
      case "REJECTED":
        return "bg-rose-100 text-rose-800 border-rose-300";
      case "COMPLETED":
        return "bg-slate-200 text-slate-800 border-slate-300";
      default:
        return "bg-slate-100 text-slate-600 border-slate-200";
    }
  };

  return (
    <div className="space-y-4" data-testid="admin-edit-request-list">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-2xs">
        <div>
          <h3 className="text-sm font-extrabold text-slate-900">
            Solicitudes de modificación de Resultados de Aprendizaje
          </h3>
          <p className="text-xs text-slate-500">
            Gestione la reapertura controlada de Resultados de Aprendizaje aprobados y
            bloqueados.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            aria-label="Filtrar estado de solicitud"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700"
          >
            <option value="">Todos los estados</option>
            <option value="PENDING">Pendientes (PENDING)</option>
            <option value="APPROVED">Aprobadas (APPROVED)</option>
            <option value="PARTIALLY_APPROVED">
              Aprobadas parcialmente (PARTIALLY_APPROVED)
            </option>
            <option value="REJECTED">Rechazadas (REJECTED)</option>
            <option value="COMPLETED">Completadas (COMPLETED)</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
          Cargando solicitudes de modificación...
        </div>
      ) : requests.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
          No hay solicitudes de modificación registradas para los criterios actuales.
        </div>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold tracking-wider text-slate-500 uppercase">
                <tr>
                  <th className="px-4 py-3">Solicitud / Fecha</th>
                  <th className="px-4 py-3">Programa / Equipo</th>
                  <th className="px-4 py-3">Líder solicitante</th>
                  <th className="px-4 py-3">Planeación</th>
                  <th className="px-4 py-3">RA solicitados</th>
                  <th className="px-4 py-3">Motivo y cambios</th>
                  <th className="px-4 py-3">Estado</th>
                  <th className="px-4 py-3 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {requests.map((req) => {
                  const codeLabel =
                    req.codigo ||
                    req.code ||
                    `REQ-${req.id.slice(0, 6).toUpperCase()}`;
                  return (
                    <tr key={req.id} className="hover:bg-slate-50/70">
                      <td className="px-4 py-3 align-top">
                        <span className="rounded bg-slate-900 px-2 py-0.5 font-mono text-[11px] font-bold text-white">
                          {codeLabel}
                        </span>
                        <div className="mt-1 text-[11px] text-slate-500">
                          {req.created_at
                            ? new Date(req.created_at).toLocaleDateString("es-CO")
                            : "—"}
                        </div>
                      </td>
                      <td className="px-4 py-3 align-top">
                        <div className="font-bold text-slate-900">
                          {req.programa_nombre || "Programa"}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          {req.team_name || req.team_nombre || "Equipo Ejecutor"}
                        </div>
                      </td>
                      <td className="px-4 py-3 align-top">
                        <div className="font-semibold text-slate-800">
                          {req.requested_by_name || req.requested_by_nombre || "Líder"}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          {req.requested_by_email}
                        </div>
                      </td>
                      <td className="px-4 py-3 align-top text-slate-700">
                        {req.planning_actividad ||
                          `${req.fase_nombre || "Fase"} — ${req.actividad_descripcion || "Actividad"}`}
                      </td>
                      <td className="px-4 py-3 align-top">
                        <div className="flex flex-wrap gap-1">
                          {req.items.map((item, idx) => (
                            <span
                              key={item.id}
                              className={`rounded border px-1.5 py-0.5 text-[10px] font-bold ${
                                item.approved
                                  ? "border-emerald-300 bg-emerald-50 text-emerald-800"
                                  : "border-slate-200 bg-slate-100 text-slate-700"
                              }`}
                            >
                              {item.codigo_resultado || `RA${idx + 1}`}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="max-w-xs px-4 py-3 align-top">
                        <p className="line-clamp-2 font-medium text-slate-800">
                          {req.reason}
                        </p>
                        <p className="mt-0.5 line-clamp-1 text-[11px] text-slate-500">
                          Cambios: {req.requested_changes}
                        </p>
                      </td>
                      <td className="px-4 py-3 align-top">
                        <span
                          className={`inline-block rounded-full border px-2.5 py-0.5 text-[10px] font-bold ${statusBadge(
                            req.status,
                          )}`}
                        >
                          {req.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right align-top">
                        <div className="flex items-center justify-end gap-2">
                          {onViewPlanning && (
                            <button
                              type="button"
                              onClick={() => onViewPlanning(req)}
                              className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-bold text-slate-700 hover:bg-slate-50"
                            >
                              Ver planeación
                            </button>
                          )}
                          <button
                            type="button"
                            data-testid={`btn-revisar-solicitud-${req.id}`}
                            onClick={() => setActiveRequest(req)}
                            className="rounded-lg bg-slate-900 px-3 py-1 text-[11px] font-bold text-white hover:bg-slate-800"
                          >
                            Revisar solicitud
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <EditRequestApprovalModal
        request={activeRequest}
        onClose={() => setActiveRequest(null)}
        onProcessed={(updated) => {
          setRequests((prev) =>
            prev.map((item) => (item.id === updated.id ? updated : item)),
          );
          if (onRequestProcessed) onRequestProcessed(updated);
        }}
      />
    </div>
  );
}
