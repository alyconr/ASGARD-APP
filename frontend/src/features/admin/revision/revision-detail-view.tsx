"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  Send,
  MessageSquare,
  Plus,
  Layers,
  FileSpreadsheet,
  X,
  Building,
  Check,
  RefreshCcw,
  AlertCircle,
} from "lucide-react";
import { toast } from "sonner";
import {
  type EntregaRevisionDetalle,
  type ObservacionRevision,
  type PlaneacionRevisionDetalle,
  type PlaneacionesEntregaList,
  type SeccionObservacionPlaneacion,
  type TipoElementoObservacion,
  fetchDetalleEntrega,
  iniciarRevisionEntrega,
  crearObservacionEntrega,
  solicitarAjustesEntrega,
  resolverObservacion,
  aprobarEntregaRevision,
  downloadFormatoOficialConsolidado,
  fetchPlaneacionRevisionDetalle,
  fetchPlaneacionesEntrega,
} from "@/features/planeacion/planeacion-api";
import { cn } from "@/lib/utils";
import { RevisionPlanningTree } from "./revision-planning-tree";
import { RevisionPlanningViewer } from "./revision-planning-viewer";

interface RevisionDetailViewProps {
  entregaId: string;
  onBack: () => void;
}

type TabInspector = "planeaciones" | "configuracion" | "observaciones" | "historial";

interface DocumentConfigSnapshot {
  fecha_elaboracion?: string;
  modalidad_formacion?: string;
  clasificacion_informacion?: string;
  regional?: string;
  centro_formacion?: string;
  equipo_gestion_curricular?: string[];
  storage_key?: string | null;
}

interface SnapshotMetadata {
  planeaciones_count?: number;
  configuracion_documental?: DocumentConfigSnapshot;
  [key: string]: unknown;
}

export function RevisionDetailView({ entregaId, onBack }: RevisionDetailViewProps): React.JSX.Element {
  const [entrega, setEntrega] = useState<EntregaRevisionDetalle | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabInspector>("planeaciones");
  const [planeaciones, setPlaneaciones] = useState<PlaneacionesEntregaList | null>(null);
  const [planeacionesLoading, setPlaneacionesLoading] = useState(true);
  const [planeacionesError, setPlaneacionesError] = useState<string | null>(null);
  const [selectedPlaneacionId, setSelectedPlaneacionId] = useState<string | null>(null);
  const [selectedPlaneacion, setSelectedPlaneacion] = useState<PlaneacionRevisionDetalle | null>(null);
  const [selectedPlaneacionLoading, setSelectedPlaneacionLoading] = useState(false);
  const [selectedPlaneacionError, setSelectedPlaneacionError] = useState<string | null>(null);

  // Observation Modal state
  const [isObsModalOpen, setIsObsModalOpen] = useState(false);
  const [obsTargetType, setObsTargetType] = useState<TipoElementoObservacion>("PLANEACION");
  const [obsTargetId, setObsTargetId] = useState<string | null>(null);
  const [obsSectionKey, setObsSectionKey] = useState("");
  const [obsComentario, setObsComentario] = useState("");
  const [isSavingObs, setIsSavingObs] = useState(false);

  // Approval Modal state
  const [isApproveModalOpen, setIsApproveModalOpen] = useState(false);
  const [approvalNotes, setApprovalNotes] = useState("");
  const [isApproving, setIsApproving] = useState(false);

  // Request Changes Modal state
  const [isRequestChangesOpen, setIsRequestChangesOpen] = useState(false);
  const [isRequestingChanges, setIsRequestingChanges] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadDetalle = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await fetchDetalleEntrega(entregaId);
      setEntrega(data);
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Error al cargar el detalle de la entrega";
      setLoadError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, [entregaId]);

  const loadPlaneaciones = useCallback(async () => {
    setPlaneacionesLoading(true);
    setPlaneacionesError(null);
    try {
      setPlaneaciones(await fetchPlaneacionesEntrega(entregaId));
    } catch (error) {
      setPlaneacionesError(
        error instanceof Error ? error.message : "Error al cargar las planeaciones de la entrega",
      );
    } finally {
      setPlaneacionesLoading(false);
    }
  }, [entregaId]);

  const loadSelectedPlaneacion = useCallback(async () => {
    if (!selectedPlaneacionId) return;
    setSelectedPlaneacionLoading(true);
    setSelectedPlaneacionError(null);
    try {
      setSelectedPlaneacion(
        await fetchPlaneacionRevisionDetalle(entregaId, selectedPlaneacionId),
      );
    } catch (error) {
      setSelectedPlaneacionError(
        error instanceof Error ? error.message : "Error al cargar la planeación",
      );
    } finally {
      setSelectedPlaneacionLoading(false);
    }
  }, [entregaId, selectedPlaneacionId]);

  useEffect(() => {
    void loadDetalle();
    void loadPlaneaciones();
  }, [loadDetalle, loadPlaneaciones]);

  useEffect(() => {
    void loadSelectedPlaneacion();
  }, [loadSelectedPlaneacion]);

  const applyObservation = useCallback((observation: ObservacionRevision, isNew = false) => {
    setEntrega((current) => {
      if (!current) return current;
      const observations = current.observaciones.some((item) => item.id === observation.id)
        ? current.observaciones.map((item) => (item.id === observation.id ? observation : item))
        : [...current.observaciones, observation];
      return {
        ...current,
        observaciones: observations,
        observaciones_pendientes_count: observations.filter((item) => item.estado === "PENDIENTE").length,
        observaciones_ajustadas_count: observations.filter((item) => item.estado === "AJUSTE_REPORTADO").length,
        observaciones_resueltas_count: observations.filter((item) => item.estado === "RESUELTO").length,
      };
    });
    setSelectedPlaneacion((current) => {
      if (!current || observation.target_id !== current.id) return current;
      const observations = current.observaciones.some((item) => item.id === observation.id)
        ? current.observaciones.map((item) => (item.id === observation.id ? observation : item))
        : [...current.observaciones, observation];
      return { ...current, observaciones: observations };
    });
    if (observation.target_type === "PLANEACION" && observation.target_id) {
      setPlaneaciones((current) => current ? {
        ...current,
        planeaciones: (current.planeaciones || []).map((planning) => {
          if (planning.id !== observation.target_id) return planning;
          return {
            ...planning,
            observaciones_count: planning.observaciones_count + (isNew ? 1 : 0),
            observaciones_pendientes_count:
              planning.observaciones_pendientes_count +
              (isNew && observation.estado === "PENDIENTE" ? 1 : 0),
          };
        }),
      } : current);
    }
  }, []);

  // Actions
  const handleIniciarRevision = async () => {
    try {
      const updated = await iniciarRevisionEntrega(entregaId);
      setEntrega(updated);
      toast.success("Revisión iniciada formalmente. Ahora puedes registrar observaciones pedagógicas.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "No fue posible iniciar la revisión");
    }
  };

  const handleCreateObservation = async () => {
    if (!obsComentario.trim()) {
      toast.error("El comentario de la observación es obligatorio.");
      return;
    }
    setIsSavingObs(true);
    try {
      const observation = await crearObservacionEntrega(entregaId, {
        target_type: obsTargetType,
        target_id: obsTargetId || null,
        section_key: obsSectionKey || null,
        comentario: obsComentario.trim(),
      });
      applyObservation(observation, true);
      setIsObsModalOpen(false);
      setObsComentario("");
      setObsSectionKey("");
      setObsTargetId(null);
      toast.success("Observación pedagógica registrada con éxito.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Error al crear la observación");
    } finally {
      setIsSavingObs(false);
    }
  };

  const handleResolverObservacion = async (obsId: string) => {
    try {
      applyObservation(await resolverObservacion(obsId));
      await loadPlaneaciones();
      toast.success("Observación marcada como resuelta.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Error al resolver la observación");
    }
  };

  const handleSolicitarAjustes = async () => {
    setIsRequestingChanges(true);
    try {
      const updated = await solicitarAjustesEntrega(entregaId);
      setEntrega(updated);
      setIsRequestChangesOpen(false);
      toast.success("Ajustes solicitados con éxito. Se notificó al Equipo Ejecutor.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Error al solicitar ajustes");
    } finally {
      setIsRequestingChanges(false);
    }
  };

  const handleAprobarEntrega = async () => {
    setIsApproving(true);
    try {
      const updated = await aprobarEntregaRevision(entregaId, approvalNotes.trim());
      setEntrega(updated);
      setIsApproveModalOpen(false);
      toast.success("¡Entrega curricular aprobada! Se habilitó formalmente la descarga oficial.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "No fue posible aprobar la entrega");
    } finally {
      setIsApproving(false);
    }
  };

  const handleDownloadPreview = async () => {
    if (!entrega?.proyecto_id) return;
    try {
      await downloadFormatoOficialConsolidado(entrega.proyecto_id);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Error al descargar el archivo consolidado");
    }
  };

  const openNewObsFor = (type: TipoElementoObservacion, id: string | null = null, section: string = "") => {
    setObsTargetType(type);
    setObsTargetId(id);
    setObsSectionKey(section);
    setObsComentario("");
    setIsObsModalOpen(true);
  };

  const openPlanning = (planeacionId: string) => {
    setSelectedPlaneacion(null);
    setSelectedPlaneacionError(null);
    setSelectedPlaneacionId(planeacionId);
  };

  const openPlanningObservation = (section: SeccionObservacionPlaneacion) => {
    if (selectedPlaneacionId) {
      openNewObsFor("PLANEACION", selectedPlaneacionId, section);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-96 items-center justify-center rounded-2xl border border-slate-200 bg-white p-8 dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center gap-2 text-emerald-600">
          <RefreshCcw className="h-5 w-5 animate-spin" />
          <span className="text-sm font-semibold">Cargando expediente de revisión...</span>
        </div>
      </div>
    );
  }

  if (loadError || !entrega) {
    return (
      <div className="flex min-h-96 flex-col items-center justify-center gap-4 rounded-2xl border border-slate-200 bg-white p-8 text-center dark:border-slate-800 dark:bg-slate-900">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-rose-50 text-rose-600 dark:bg-rose-950/30">
          <AlertCircle className="h-6 w-6" />
        </div>
        <div>
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
            No fue posible cargar el expediente
          </h3>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 max-w-sm">
            {loadError || "El expediente solicitado no se encuentra disponible o no existe."}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onBack}
            className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300"
          >
            Volver a la bandeja
          </button>
          <button
            type="button"
            onClick={() => void loadDetalle()}
            className="rounded-lg bg-emerald-700 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-800"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  const snapshot = (entrega.snapshot_metadatos || {}) as SnapshotMetadata;
  const configSnapshot = snapshot.configuracion_documental || {};
  const pendingObsCount = entrega.observaciones_pendientes_count;
  const adjustedObsCount = entrega.observaciones_ajustadas_count;
  const canApprove = pendingObsCount === 0 && adjustedObsCount === 0;

  return (
    <div className="space-y-6">
      {/* Top Bar with Back and Actions */}
      <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:flex-row sm:items-center sm:justify-between dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
            title="Volver a la bandeja"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
                Expediente de Revisión Pedagógica · Versión {entrega.version}
              </span>
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase",
                  entrega.estado === "APROBADO"
                    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                    : entrega.estado === "AJUSTES_SOLICITADOS"
                    ? "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                    : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
                )}
              >
                {entrega.estado}
              </span>
            </div>
            <h1 className="mt-0.5 text-xl font-bold text-slate-900 dark:text-white">
              {entrega.equipo_ejecutor_nombre}
            </h1>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {entrega.proyecto_id && (
            <button
              type="button"
              onClick={() => void handleDownloadPreview()}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
              title="Descargar libro consolidado GPFI-F-134 V05 para revisión"
            >
              <FileSpreadsheet className="h-4 w-4 text-emerald-600" />
              Previsualizar Excel
            </button>
          )}

          {(entrega.estado === "ENVIADO_REVISION" || entrega.estado === "REENVIADO") && (
            <button
              type="button"
              onClick={() => void handleIniciarRevision()}
              className="inline-flex items-center gap-1.5 rounded-lg bg-sky-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-sky-700 transition"
            >
              <Send className="h-3.5 w-3.5" />
              Iniciar Revisión
            </button>
          )}

          {entrega.estado !== "APROBADO" && (
            <>
              <button
                type="button"
                onClick={() => setIsRequestChangesOpen(true)}
                disabled={entrega.observaciones.length === 0}
                className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-100 transition disabled:opacity-50"
                title={
                  entrega.observaciones.length === 0
                    ? "Debes registrar al menos una observación antes de solicitar ajustes"
                    : "Devolver al equipo ejecutor con las observaciones registradas"
                }
              >
                <AlertTriangle className="h-3.5 w-3.5" />
                Solicitar Ajustes
              </button>

              <button
                type="button"
                onClick={() => setIsApproveModalOpen(true)}
                disabled={!canApprove}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 transition disabled:cursor-not-allowed disabled:opacity-50"
                title={
                  !canApprove
                    ? `No se puede aprobar. Hay ${pendingObsCount + adjustedObsCount} observaciones pendientes o sin resolver.`
                    : "Aprobar la planeación y autorizar descarga consolidada"
                }
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                Aprobar y Habilitar Descarga
              </button>
            </>
          )}
        </div>
      </div>

      {/* Process Meta Card */}
      <div className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:grid-cols-3 dark:border-slate-800 dark:bg-slate-900">
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Programa de Formación
          </span>
          <p className="mt-1 text-xs font-semibold text-slate-800 dark:text-slate-200">
            {entrega.codigo_programa} - {entrega.nombre_programa}
          </p>
        </div>
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Proyecto Formativo
          </span>
          <p className="mt-1 text-xs font-semibold text-slate-800 dark:text-slate-200">
            {entrega.codigo_proyecto} - {entrega.nombre_proyecto}
          </p>
        </div>
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Líder del Equipo Ejecutor
          </span>
          <p className="mt-1 text-xs font-semibold text-slate-800 dark:text-slate-200">
            {entrega.lider_nombre} ({entrega.lider_email})
          </p>
        </div>
        {entrega.notas_entrega && (
          <div className="col-span-full rounded-xl bg-slate-50 p-3 text-xs text-slate-700 dark:bg-slate-800/50 dark:text-slate-300">
            <span className="font-bold uppercase tracking-wider text-slate-500">Notas del Equipo:</span>{" "}
            {entrega.notas_entrega}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 gap-6 overflow-x-auto dark:border-slate-800">
        <button
          type="button"
          onClick={() => setActiveTab("planeaciones")}
          className={cn(
            "inline-flex items-center gap-2 pb-3 text-xs font-semibold border-b-2 -mb-px transition",
            activeTab === "planeaciones"
              ? "border-emerald-600 text-emerald-700 dark:border-emerald-400 dark:text-emerald-400"
              : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200",
          )}
        >
          <Layers className="h-4 w-4" />
          Árbol de Planeaciones ({planeaciones?.total_planeaciones ?? snapshot.planeaciones_count ?? 0})
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("configuracion")}
          className={cn(
            "inline-flex items-center gap-2 pb-3 text-xs font-semibold border-b-2 -mb-px transition",
            activeTab === "configuracion"
              ? "border-emerald-600 text-emerald-700 dark:border-emerald-400 dark:text-emerald-400"
              : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200",
          )}
        >
          <Building className="h-4 w-4" />
          Configuración Documental
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("observaciones")}
          className={cn(
            "inline-flex items-center gap-2 pb-3 text-xs font-semibold border-b-2 -mb-px transition",
            activeTab === "observaciones"
              ? "border-emerald-600 text-emerald-700 dark:border-emerald-400 dark:text-emerald-400"
              : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200",
          )}
        >
          <MessageSquare className="h-4 w-4" />
          Observaciones & Ajustes ({entrega.observaciones.length})
          {pendingObsCount > 0 && (
            <span className="rounded-full bg-amber-100 px-1.5 py-0.2 text-[10px] font-bold text-amber-800">
              {pendingObsCount}
            </span>
          )}
        </button>
      </div>

      {/* TAB 1: PLANEACIONES */}
      {activeTab === "planeaciones" && (
        selectedPlaneacionId ? (
          <RevisionPlanningViewer
            detail={selectedPlaneacion}
            loading={selectedPlaneacionLoading}
            error={selectedPlaneacionError}
            onBack={() => {
              setSelectedPlaneacionId(null);
              setSelectedPlaneacion(null);
            }}
            onRetry={() => void loadSelectedPlaneacion()}
            onAddObservation={openPlanningObservation}
          />
        ) : (
          <RevisionPlanningTree
            data={planeaciones}
            loading={planeacionesLoading}
            error={planeacionesError}
            onRetry={() => void loadPlaneaciones()}
            onSelect={openPlanning}
          />
        )
      )}

      {/* TAB 2: CONFIGURACION DOCUMENTAL */}
      {activeTab === "configuracion" && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                Configuración Documental Institucional (GPFI-F-134 V05)
              </h3>
              <p className="mt-0.5 text-xs text-slate-500">
                Información oficial del centro, regional y equipo gestor registrada para el proyecto.
              </p>
            </div>
            <button
              type="button"
              onClick={() => openNewObsFor("CONFIGURACION_DOCUMENTAL", null, "Metadatos Institucionales")}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
            >
              <Plus className="h-3 w-3" />
              Observar Configuración
            </button>
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-2 text-xs">
            <div>
              <span className="block font-semibold text-slate-400 uppercase tracking-wider">Fecha de Elaboración</span>
              <p className="mt-1 text-sm font-medium text-slate-800 dark:text-slate-200">
                {configSnapshot.fecha_elaboracion || "No registrada"}
              </p>
            </div>
            <div>
              <span className="block font-semibold text-slate-400 uppercase tracking-wider">Clasificación Información</span>
              <p className="mt-1 text-sm font-medium text-slate-800 dark:text-slate-200">
                {configSnapshot.clasificacion_informacion || "PUBLICA"}
              </p>
            </div>
            <div>
              <span className="block font-semibold text-slate-400 uppercase tracking-wider">Regional</span>
              <p className="mt-1 text-sm font-medium text-slate-800 dark:text-slate-200">
                {configSnapshot.regional || "No registrada"}
              </p>
            </div>
            <div>
              <span className="block font-semibold text-slate-400 uppercase tracking-wider">Centro de Formación</span>
              <p className="mt-1 text-sm font-medium text-slate-800 dark:text-slate-200">
                {configSnapshot.centro_formacion || "No registrado"}
              </p>
            </div>
            <div className="col-span-full">
              <span className="block font-semibold text-slate-400 uppercase tracking-wider">Equipo de Gestión Curricular</span>
              <div className="mt-1 rounded-lg bg-slate-50 p-3 text-slate-700 dark:bg-slate-800/50 dark:text-slate-300">
                {Array.isArray(configSnapshot.equipo_gestion_curricular) && configSnapshot.equipo_gestion_curricular.length > 0 ? (
                  <ul className="list-disc pl-4 space-y-1">
                    {configSnapshot.equipo_gestion_curricular.map((m: string, i: number) => (
                      <li key={i}>{m}</li>
                    ))}
                  </ul>
                ) : (
                  "Sin integrantes registrados"
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: OBSERVACIONES */}
      {activeTab === "observaciones" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Observaciones Pedagógicas Registradas
            </h3>
            <button
              type="button"
              onClick={() => openNewObsFor("PROCESO_GENERAL", null, "Observación General")}
              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 transition"
            >
              <Plus className="h-3.5 w-3.5" />
              Nueva Observación
            </button>
          </div>

          {entrega.observaciones.length === 0 ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900">
              No hay observaciones registradas en esta entrega.
            </div>
          ) : (
            <div className="grid gap-3">
              {entrega.observaciones.map((obs) => (
                <div
                  key={obs.id}
                  className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900"
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-bold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                          {obs.target_type}
                        </span>
                        {obs.section_key && (
                          <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                            {obs.section_key}
                          </span>
                        )}
                        <span className="text-slate-300">·</span>
                        <span className="text-[11px] text-slate-400">
                          {new Date(obs.fecha_creacion).toLocaleString("es-CO")} por {obs.creado_por_nombre}
                        </span>
                      </div>
                      <p className="mt-2 text-xs text-slate-800 dark:text-slate-200 whitespace-pre-wrap">
                        {obs.comentario}
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          "rounded-full px-2.5 py-0.5 text-[11px] font-semibold",
                          obs.estado === "RESUELTO"
                            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                            : obs.estado === "AJUSTE_REPORTADO"
                            ? "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300"
                            : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
                        )}
                      >
                        {obs.estado === "RESUELTO"
                          ? "Resuelto"
                          : obs.estado === "AJUSTE_REPORTADO"
                          ? "Ajuste Reportado"
                          : "Pendiente"}
                      </span>

                      {obs.estado !== "RESUELTO" && (
                        <button
                          type="button"
                          onClick={() => void handleResolverObservacion(obs.id)}
                          className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800 hover:bg-emerald-100 transition"
                        >
                          <Check className="h-3 w-3" />
                          Marcar Resuelto
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Team Response if reported */}
                  {obs.comentario_ajuste && (
                    <div className="mt-3 rounded-lg border border-blue-100 bg-blue-50/70 p-3 text-xs text-blue-950 dark:border-blue-900/50 dark:bg-blue-950/20 dark:text-blue-200">
                      <span className="font-bold text-blue-900 dark:text-blue-300">
                        Respuesta del Equipo ({obs.ajuste_reportado_por_nombre || "Equipo Ejecutor"}):
                      </span>{" "}
                      {obs.comentario_ajuste}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* CREATE OBSERVATION MODAL */}
      {isObsModalOpen && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                Nueva Observación Pedagógica
              </h3>
              <button
                type="button"
                onClick={() => setIsObsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-4 space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">
                  Elemento a Observar
                </label>
                <select
                  value={obsTargetType}
                  onChange={(e) => setObsTargetType(e.target.value as TipoElementoObservacion)}
                  disabled={obsTargetType === "PLANEACION" && Boolean(obsTargetId)}
                  className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs outline-none focus:border-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-900"
                >
                  <option value="PLANEACION">Planeación / Actividad Específica</option>
                  <option value="CONFIGURACION_DOCUMENTAL">Configuración Documental</option>
                  <option value="PROGRAMA">Programa de Formación</option>
                  <option value="PROYECTO">Proyecto Formativo</option>
                  <option value="PROCESO_GENERAL">Proceso General</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">
                  {obsTargetType === "PLANEACION" && obsTargetId
                    ? "Sección de la planeación"
                    : "Sección / Campo (Opcional)"}
                </label>
                <input
                  type="text"
                  value={obsSectionKey}
                  onChange={(e) => setObsSectionKey(e.target.value)}
                  readOnly={obsTargetType === "PLANEACION" && Boolean(obsTargetId)}
                  placeholder="Ej. Estrategias Didácticas, Duración de Horas..."
                  className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs outline-none focus:border-emerald-500 read-only:cursor-not-allowed read-only:bg-slate-100 read-only:text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:read-only:bg-slate-900"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300">
                  Observación Pedagógica / Instrucciones de Mejora
                </label>
                <textarea
                  rows={4}
                  value={obsComentario}
                  onChange={(e) => setObsComentario(e.target.value)}
                  placeholder="Detalla con claridad los aspectos técnicos o pedagógicos que el equipo ejecutor debe ajustar..."
                  className="mt-1 w-full resize-y rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs outline-none focus:border-emerald-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                />
              </div>
            </div>

            <div className="mt-5 flex justify-end gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
              <button
                type="button"
                onClick={() => setIsObsModalOpen(false)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={isSavingObs || !obsComentario.trim()}
                onClick={() => void handleCreateObservation()}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                {isSavingObs ? "Guardando..." : "Guardar Observación"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* REQUEST CHANGES MODAL */}
      {isRequestChangesOpen && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-rose-200 bg-white p-6 shadow-2xl dark:border-rose-900 dark:bg-slate-900">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-rose-100 p-2 text-rose-700 dark:bg-rose-950 dark:text-rose-400">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                Solicitar Ajustes Pedagógicos
              </h3>
            </div>
            <p className="mt-3 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
              Al confirmar, la entrega pasará a estado <strong>AJUSTES_SOLICITADOS</strong> y se notificará al líder del equipo ejecutor con las <strong>{entrega.observaciones.length}</strong> observación(es) formuladas.
            </p>

            <div className="mt-5 flex justify-end gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
              <button
                type="button"
                onClick={() => setIsRequestChangesOpen(false)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={isRequestingChanges}
                onClick={() => void handleSolicitarAjustes()}
                className="rounded-lg bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-50"
              >
                {isRequestingChanges ? "Enviando..." : "Confirmar y Solicitar Ajustes"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* APPROVAL MODAL */}
      {isApproveModalOpen && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-emerald-200 bg-white p-6 shadow-2xl dark:border-emerald-900 dark:bg-slate-900">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-emerald-100 p-2 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400">
                <CheckCircle2 className="h-5 w-5" />
              </div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                Aprobar Entrega Curricular
              </h3>
            </div>
            <p className="mt-3 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
              Todas las observaciones han sido resueltas. Al aprobar, se validará la integridad de la planeación y se habilitará formalmente la descarga del formato oficial GPFI-F-134 V05 para el equipo ejecutor.
            </p>

            <div className="mt-3 text-xs">
              <label className="font-semibold text-slate-700 dark:text-slate-300">
                Notas de Aprobación (Opcional)
              </label>
              <textarea
                rows={3}
                value={approvalNotes}
                onChange={(e) => setApprovalNotes(e.target.value)}
                placeholder="Observaciones de cierre institucional..."
                className="mt-1 w-full resize-y rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs outline-none focus:border-emerald-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />
            </div>

            <div className="mt-5 flex justify-end gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
              <button
                type="button"
                onClick={() => setIsApproveModalOpen(false)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={isApproving}
                onClick={() => void handleAprobarEntrega()}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                {isApproving ? "Aprobando..." : "Confirmar Aprobación"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
