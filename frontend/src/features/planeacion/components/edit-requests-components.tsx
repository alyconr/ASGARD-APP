"use client";

import React, { useEffect, useState } from "react";
import {
  crearSolicitudModificacion,
  LearningResultVersion,
  listarVersionesResultados,
  PlanningEditRequest,
} from "../planeacion-api";

export interface SelectableLearningResult {
  id: string;
  codigo?: string | null;
  descripcion: string;
  competencia_codigo?: string | null;
  competencia_nombre?: string | null;
  edit_status?: string | null;
  approved_version?: number;
  approved_at?: string | null;
  unlock_request_id?: string | null;
}

// -----------------------------------------------------------------------------
// 1. LockStatusBadge
// -----------------------------------------------------------------------------
export interface LockStatusBadgeProps {
  editStatus?: string | null;
  unlockRequestId?: string | null;
  approvedVersion?: number;
  compact?: boolean;
}

export function LockStatusBadge({
  editStatus = "EDITABLE",
  unlockRequestId,
  approvedVersion,
  compact = false,
}: LockStatusBadgeProps) {
  const isLocked = editStatus === "LOCKED";
  const isReopened = editStatus === "EDITABLE" && Boolean(unlockRequestId);

  if (isLocked) {
    return (
      <span
        data-testid="ra-lock-badge-locked"
        className={`inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-slate-100 font-bold text-slate-700 ${
          compact ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs"
        }`}
      >
        <span aria-hidden="true">🔒</span>
        <span>LOCKED</span>
        {approvedVersion && approvedVersion > 0 ? (
          <span className="ml-0.5 rounded bg-slate-200 px-1 text-[10px] text-slate-800">
            v{approvedVersion}
          </span>
        ) : null}
      </span>
    );
  }

  if (isReopened) {
    return (
      <span
        data-testid="ra-lock-badge-reopened"
        className={`inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 font-bold text-amber-800 ${
          compact ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs"
        }`}
      >
        <span aria-hidden="true">🟠</span>
        <span>Edición autorizada (EDITABLE)</span>
      </span>
    );
  }

  return (
    <span
      data-testid="ra-lock-badge-editable"
      className={`inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 font-bold text-emerald-700 ${
        compact ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs"
      }`}
    >
      <span aria-hidden="true">✏️</span>
      <span>EDITABLE</span>
    </span>
  );
}

// -----------------------------------------------------------------------------
// 2. LearningResultLockBanner (UX Section 12)
// -----------------------------------------------------------------------------
export interface LearningResultLockBannerProps {
  ra: SelectableLearningResult;
  requestCode?: string | null;
  onFocusEdit?: () => void;
}

export function LearningResultLockBanner({
  ra,
  requestCode,
  onFocusEdit,
}: LearningResultLockBannerProps) {
  const isLocked = ra.edit_status === "LOCKED";
  const isAuthorizedReopen =
    ra.edit_status === "EDITABLE" && Boolean(ra.unlock_request_id || requestCode);

  if (isLocked) {
    const formattedDate = ra.approved_at
      ? new Date(ra.approved_at).toLocaleDateString("es-CO")
      : "Vigente";
    const versionNum = ra.approved_version && ra.approved_version > 0 ? ra.approved_version : 1;

    return (
      <div
        data-testid={`ra-locked-banner-${ra.id}`}
        className="rounded-xl border border-slate-300 bg-slate-50/90 p-3.5 text-slate-800 shadow-xs"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-xs font-extrabold tracking-wide text-slate-900 uppercase">
            <span aria-hidden="true">🔒</span>
            <span>Resultado de aprendizaje aprobado</span>
          </div>
          <div className="flex items-center gap-3 text-[11px] font-semibold text-slate-600">
            <span>
              Versión: <strong className="text-slate-900">v{versionNum}</strong>
            </span>
            <span>
              Aprobado: <strong className="text-slate-900">{formattedDate}</strong>
            </span>
          </div>
        </div>
        <p className="mt-1.5 text-xs leading-relaxed text-slate-600">
          Este resultado de aprendizaje fue aprobado por el Equipo Pedagógico y se
          encuentra bloqueado para edición. Su contenido está disponible en modo
          lectura.
        </p>
      </div>
    );
  }

  if (isAuthorizedReopen) {
    return (
      <div
        data-testid={`ra-authorized-banner-${ra.id}`}
        className="rounded-xl border border-amber-300 bg-amber-50/90 p-3.5 text-amber-950 shadow-xs"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-xs font-extrabold tracking-wide text-amber-900 uppercase">
            <span aria-hidden="true">🟠</span>
            <span>Edición autorizada</span>
          </div>
          <div className="flex items-center gap-2">
            {requestCode && (
              <span className="rounded-md border border-amber-300 bg-white px-2 py-0.5 font-mono text-[11px] font-bold text-amber-900">
                Solicitud: {requestCode}
              </span>
            )}
            {onFocusEdit && (
              <button
                type="button"
                onClick={onFocusEdit}
                className="rounded-lg bg-amber-600 px-3 py-1 text-xs font-bold text-white transition hover:bg-amber-700"
              >
                Editar
              </button>
            )}
          </div>
        </div>
        <p className="mt-1.5 text-xs leading-relaxed text-amber-800">
          El Equipo Pedagógico autorizó modificaciones sobre este resultado de
          aprendizaje. Al finalizar los ajustes, recuerde volver a enviar la
          planeación a revisión.
        </p>
      </div>
    );
  }

  return null;
}

// -----------------------------------------------------------------------------
// 3. EditRequestButton (Rule Section 7)
// -----------------------------------------------------------------------------
export interface EditRequestButtonProps {
  planningApproved: boolean;
  downloadEnabled: boolean;
  learningResultsLocked: boolean;
  isTeamLeader: boolean;
  hasPendingRequest?: boolean;
  onClick: () => void;
}

export function EditRequestButton({
  planningApproved,
  downloadEnabled,
  learningResultsLocked,
  isTeamLeader,
  hasPendingRequest = false,
  onClick,
}: EditRequestButtonProps) {
  const canShow =
    planningApproved && downloadEnabled && learningResultsLocked && isTeamLeader;

  if (!canShow) {
    return null;
  }

  return (
    <button
      type="button"
      data-testid="btn-solicitar-modificacion"
      disabled={hasPendingRequest}
      onClick={onClick}
      className="inline-flex items-center gap-2 rounded-xl border border-amber-300 bg-amber-50 px-4 py-2 text-xs font-bold text-amber-900 shadow-xs transition hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60"
    >
      <span aria-hidden="true">🔓</span>
      <span>
        {hasPendingRequest
          ? "Solicitud de modificación en curso"
          : "Solicitar modificación"}
      </span>
    </button>
  );
}

// -----------------------------------------------------------------------------
// 4. EditRequestModal (Section 7)
// -----------------------------------------------------------------------------
export interface EditRequestModalProps {
  isOpen: boolean;
  planningId: string;
  planningLabel?: string;
  learningResults: SelectableLearningResult[];
  pendingRaIds?: string[];
  onClose: () => void;
  onSuccess: (created: PlanningEditRequest) => void;
}

export function EditRequestModal({
  isOpen,
  planningId,
  planningLabel,
  learningResults,
  pendingRaIds = [],
  onClose,
  onSuccess,
}: EditRequestModalProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [reason, setReason] = useState("");
  const [requestedChanges, setRequestedChanges] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setSelectedIds([]);
      setReason("");
      setRequestedChanges("");
      setError(null);
    }
  }, [isOpen, planningId]);

  if (!isOpen) return null;

  const pendingSet = new Set(pendingRaIds);
  const lockedResults = learningResults.filter(
    (ra) => !ra.edit_status || ra.edit_status === "LOCKED",
  );
  const displayResults = lockedResults.length > 0 ? lockedResults : learningResults;

  const toggleRa = (id: string) => {
    if (pendingSet.has(id)) return;
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (selectedIds.length === 0) {
      setError("Debe seleccionar al menos un Resultado de Aprendizaje.");
      return;
    }
    if (!reason.trim() || reason.trim().length < 5) {
      setError("El motivo de la solicitud es obligatorio (mínimo 5 caracteres).");
      return;
    }
    if (!requestedChanges.trim() || requestedChanges.trim().length < 5) {
      setError("Debe especificar qué cambios propone realizar (mínimo 5 caracteres).");
      return;
    }

    try {
      setSubmitting(true);
      const created = await crearSolicitudModificacion({
        planning_id: planningId,
        learning_result_ids: selectedIds,
        reason: reason.trim(),
        requested_changes: requestedChanges.trim(),
      });
      onSuccess(created);
      onClose();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No fue posible enviar la solicitud de reapertura.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      data-testid="edit-request-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs"
    >
      <div className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50 px-6 py-4">
          <div>
            <h3 className="text-base font-extrabold text-slate-900">
              Solicitar reapertura de planeación
            </h3>
            {planningLabel && (
              <p className="mt-0.5 text-xs text-slate-500">{planningLabel}</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-200/60 hover:text-slate-700"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 space-y-5 overflow-y-auto p-6">
          {error && (
            <div
              role="alert"
              className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs font-semibold text-rose-700"
            >
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-bold tracking-wide text-slate-700 uppercase">
              Resultados de Aprendizaje a modificar *
            </label>
            <p className="mt-0.5 text-xs text-slate-500">
              Seleccione únicamente los Resultados de Aprendizaje que requieren ajustes.
              Los demás permanecerán bloqueados.
            </p>
            <div className="mt-3 max-h-52 space-y-2 overflow-y-auto rounded-xl border border-slate-200 bg-slate-50/60 p-3">
              {displayResults.map((ra, idx) => {
                const isChecked = selectedIds.includes(ra.id);
                const isPending = pendingSet.has(ra.id);
                const labelCode = ra.codigo || `RA${idx + 1}`;
                return (
                  <label
                    key={ra.id}
                    className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition ${
                      isChecked
                        ? "border-amber-400 bg-amber-50/70"
                        : "border-slate-200 bg-white hover:border-slate-300"
                    } ${isPending ? "cursor-not-allowed opacity-60" : ""}`}
                  >
                    <input
                      type="checkbox"
                      data-testid={`checkbox-ra-${ra.id}`}
                      checked={isChecked}
                      disabled={isPending}
                      onChange={() => toggleRa(ra.id)}
                      className="mt-0.5 h-4 w-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500"
                    />
                    <div className="flex-1 text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-bold text-slate-900">
                          {labelCode} - {ra.descripcion}
                        </span>
                        {isPending && (
                          <span className="rounded bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-800">
                            Solicitud pendiente
                          </span>
                        )}
                      </div>
                      {ra.competencia_nombre && (
                        <p className="mt-1 text-[11px] text-slate-500">
                          Competencia: {ra.competencia_codigo} — {ra.competencia_nombre}
                        </p>
                      )}
                    </div>
                  </label>
                );
              })}
            </div>
          </div>

          <div>
            <label
              htmlFor="edit-request-reason"
              className="block text-xs font-bold tracking-wide text-slate-700 uppercase"
            >
              Motivo *
            </label>
            <textarea
              id="edit-request-reason"
              data-testid="input-edit-request-reason"
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Explique por qué necesita modificar estos resultados de aprendizaje."
              className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-xs text-slate-900 focus:border-amber-500 focus:outline-none"
            />
          </div>

          <div>
            <label
              htmlFor="edit-request-changes"
              className="block text-xs font-bold tracking-wide text-slate-700 uppercase"
            >
              Cambios propuestos *
            </label>
            <textarea
              id="edit-request-changes"
              data-testid="input-edit-request-changes"
              rows={3}
              value={requestedChanges}
              onChange={(e) => setRequestedChanges(e.target.value)}
              placeholder="Indique específicamente qué información desea modificar."
              className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-xs text-slate-900 focus:border-amber-500 focus:outline-none"
            />
          </div>

          <div className="flex items-center justify-end gap-3 border-t border-slate-100 pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              data-testid="btn-submit-edit-request"
              disabled={submitting}
              className="rounded-xl bg-amber-600 px-5 py-2 text-xs font-bold text-white shadow-sm transition hover:bg-amber-700 disabled:opacity-50"
            >
              {submitting
                ? "Enviando solicitud..."
                : "Enviar solicitud al Equipo Pedagógico"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// 5. EditRequestStatus (Section 8)
// -----------------------------------------------------------------------------
export interface EditRequestStatusProps {
  requests: PlanningEditRequest[];
}

export function EditRequestStatus({ requests }: EditRequestStatusProps) {
  if (!requests || requests.length === 0) return null;

  return (
    <div className="space-y-3" data-testid="edit-request-status-list">
      {requests.map((req) => {
        const isPending = req.status === "PENDING";
        const isApproved =
          req.status === "APPROVED" || req.status === "PARTIALLY_APPROVED";
        const isRejected = req.status === "REJECTED";
        const codeLabel = req.codigo || req.code || `REQ-${req.id.slice(0, 6).toUpperCase()}`;
        const formattedDate = req.created_at
          ? new Date(req.created_at).toLocaleString("es-CO")
          : "Reciente";

        return (
          <div
            key={req.id}
            data-testid={`edit-request-card-${req.status}`}
            className={`rounded-2xl border p-4 shadow-xs ${
              isPending
                ? "border-amber-300 bg-amber-50/70 text-amber-950"
                : isApproved
                  ? "border-emerald-300 bg-emerald-50/70 text-emerald-950"
                  : isRejected
                    ? "border-rose-300 bg-rose-50/70 text-rose-950"
                    : "border-slate-200 bg-slate-50 text-slate-800"
            }`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="rounded-md bg-white/90 px-2.5 py-0.5 font-mono text-xs font-extrabold shadow-2xs">
                  {codeLabel}
                </span>
                <h4 className="text-xs font-extrabold uppercase tracking-wide">
                  {isPending
                    ? "Solicitud de modificación pendiente"
                    : req.status === "PARTIALLY_APPROVED"
                      ? "Solicitud aprobada parcialmente"
                      : isApproved
                        ? "Solicitud de modificación aprobada"
                        : isRejected
                          ? "Solicitud de modificación rechazada"
                          : "Solicitud de modificación completada"}
                </h4>
              </div>
              <span className="text-[11px] font-semibold opacity-80">
                Fecha: {formattedDate}
              </span>
            </div>

            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl bg-white/70 p-3 text-xs">
                <span className="block text-[10px] font-bold uppercase opacity-70">
                  Resultados solicitados
                </span>
                <ul className="mt-1.5 space-y-1">
                  {req.items.map((item, idx) => (
                    <li
                      key={item.id}
                      className="flex items-center justify-between gap-2 font-medium"
                    >
                      <span>
                        <strong>{item.codigo_resultado || `RA${idx + 1}`}</strong>:{" "}
                        {item.descripcion || item.descripcion_resultado}
                      </span>
                      {req.status !== "PENDING" && (
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                            item.approved
                              ? "bg-emerald-100 text-emerald-800"
                              : "bg-slate-200 text-slate-700"
                          }`}
                        >
                          {item.approved ? "Autorizado (EDITABLE)" : "Permanece LOCKED"}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounded-xl bg-white/70 p-3 text-xs">
                <span className="block text-[10px] font-bold uppercase opacity-70">
                  Estado y trazabilidad
                </span>
                <p className="mt-1 font-bold">
                  {isPending
                    ? "Pendiente de revisión del Equipo Pedagógico"
                    : req.status === "PARTIALLY_APPROVED"
                      ? "Aprobación parcial — Solo los RA autorizados están habilitados para edición"
                      : isApproved
                        ? "Edición habilitada para los RA autorizados"
                        : isRejected
                          ? "Rechazada — Todos los RA permanecen bloqueados"
                          : "Ciclo de reapertura cerrado"}
                </p>
                <p className="mt-1.5 text-[11px] opacity-85">
                  <strong>Motivo:</strong> {req.reason}
                </p>
                <p className="mt-1 text-[11px] opacity-85">
                  <strong>Cambios propuestos:</strong> {req.requested_changes}
                </p>
                {req.admin_response && (
                  <p className="mt-1.5 rounded-lg border border-current/15 bg-white p-2 text-[11px]">
                    <strong>Respuesta Equipo Pedagógico:</strong> {req.admin_response}
                  </p>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// -----------------------------------------------------------------------------
// 6. LearningResultVersionHistory (Section 14)
// -----------------------------------------------------------------------------
export interface LearningResultVersionHistoryProps {
  isOpen: boolean;
  planningId: string;
  learningResultId?: string | null;
  onClose: () => void;
}

export function LearningResultVersionHistory({
  isOpen,
  planningId,
  learningResultId,
  onClose,
}: LearningResultVersionHistoryProps) {
  const [versions, setVersions] = useState<LearningResultVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !planningId) return;
    let active = true;
    setLoading(true);
    setError(null);
    listarVersionesResultados(planningId, learningResultId)
      .then((data) => {
        if (active) setVersions(data);
      })
      .catch((err) => {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : "Error al consultar el historial de versiones.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [isOpen, planningId, learningResultId]);

  if (!isOpen) return null;

  return (
    <div
      data-testid="version-history-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs"
    >
      <div className="flex max-h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50 px-6 py-4">
          <div>
            <h3 className="text-base font-extrabold text-slate-900">
              Historial de versiones aprobadas (Resultados de Aprendizaje)
            </h3>
            <p className="mt-0.5 text-xs text-slate-500">
              Registro inmutable de versiones aprobadas por el Equipo Pedagógico
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

        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <p className="text-center text-xs text-slate-500">
              Cargando historial de versiones...
            </p>
          ) : error ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-700">
              {error}
            </div>
          ) : versions.length === 0 ? (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 text-center text-xs text-slate-500">
              Aún no se registran versiones aprobadas para esta planeación.
            </div>
          ) : (
            <div className="space-y-3">
              {versions.map((v) => {
                const snap = v.snapshot_data || {};
                const approvedDate = v.approved_at
                  ? new Date(v.approved_at).toLocaleString("es-CO")
                  : "—";
                return (
                  <div
                    key={v.id}
                    className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 text-xs"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200/80 pb-2">
                      <div className="flex items-center gap-2">
                        <span className="rounded-md bg-slate-900 px-2 py-0.5 font-mono text-[11px] font-bold text-white">
                          v{v.version_number}
                        </span>
                        <span className="font-bold text-slate-900">
                          {String(snap.codigo_resultado || "RA")} —{" "}
                          {String(snap.descripcion || "")}
                        </span>
                        {v.is_official && (
                          <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-800">
                            Versión Oficial Vigente
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] text-slate-500">
                        Aprobado: {approvedDate}{" "}
                        {v.approved_by_name || v.approved_by_nombre
                          ? `por ${v.approved_by_name || v.approved_by_nombre}`
                          : ""}
                      </span>
                    </div>
                    <div className="mt-2.5 grid gap-2 sm:grid-cols-2">
                      <div>
                        <span className="font-semibold text-slate-600">
                          Actividades de aprendizaje:
                        </span>{" "}
                        <span className="text-slate-800">
                          {String(snap.actividades_aprendizaje || "—")}
                        </span>
                      </div>
                      <div>
                        <span className="font-semibold text-slate-600">
                          Duración (Directas / Indep. / Total):
                        </span>{" "}
                        <span className="text-slate-800">
                          {String(snap.horas_trabajo_directo ?? 0)}h /{" "}
                          {String(snap.horas_trabajo_independiente ?? 0)}h /{" "}
                          {String(snap.duracion_actividad_horas ?? 0)}h
                        </span>
                      </div>
                      <div>
                        <span className="font-semibold text-slate-600">
                          Estrategias didácticas:
                        </span>{" "}
                        <span className="text-slate-800">
                          {String(snap.estrategias_didacticas || "—")}
                        </span>
                      </div>
                      <div>
                        <span className="font-semibold text-slate-600">
                          Evidencia de aprendizaje:
                        </span>{" "}
                        <span className="text-slate-800">
                          {String(snap.descripcion_evidencia_aprendizaje || "—")}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
