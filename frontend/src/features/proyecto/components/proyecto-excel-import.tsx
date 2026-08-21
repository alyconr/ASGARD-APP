"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileSpreadsheet,
  Layers,
  Loader2,
  Upload,
  X,
} from "lucide-react";

import {
  confirmProjectExcelImport,
  uploadProjectExcelPreview,
} from "@/features/proyecto/excel-import-api";
import { AlreadyLoadedModal } from "@/components/wizard/already-loaded-modal";
import { eliminarCargueProyecto } from "@/features/proyecto/cargue-api";
import { notify } from "@/components/feedback/notifications";
import { useConfirm } from "@/components/feedback/confirm-context";

import type {
  ExcelFasePreview,
  ProyectoExcelPreviewState,
} from "@/features/proyecto/types";
import { cn } from "@/lib/utils";

type UploadState = "idle" | "uploading" | "preview" | "confirming" | "success" | "error";

function formatFileSize(sizeBytes: number): string {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }

  const sizeKb = sizeBytes / 1024;
  if (sizeKb < 1024) {
    return `${sizeKb.toFixed(1)} KB`;
  }

  return `${(sizeKb / 1024).toFixed(1)} MB`;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && "detail" in error) {
    return (error as { detail: string }).detail;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "No fue posible procesar el Excel del proyecto.";
}

function validateExcelFile(file: File | null): string | null {
  if (file === null) {
    return "Selecciona un archivo Excel antes de cargar.";
  }

  if (
    file.type !==
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" &&
    !file.name.toLowerCase().endsWith(".xlsx")
  ) {
    return "Solo se aceptan archivos .xlsx.";
  }

  if (file.size === 0) {
    return "El Excel seleccionado esta vacio.";
  }

  return null;
}

function isAlreadyLoadedMessage(message: string): boolean {
  const normalized = message.toLowerCase();
  return (
    normalized.includes("ya fue cargado") ||
    normalized.includes("ya han sido cargados") ||
    normalized.includes("planeacion pedagogica")
  );
}

interface CurriculumFasesModalProps {
  isOpen: boolean;
  onClose: () => void;
  fases: ExcelFasePreview[];
}

function CurriculumFasesModal({
  isOpen,
  onClose,
  fases,
}: Readonly<CurriculumFasesModalProps>): React.JSX.Element | null {
  const [expandedFases, setExpandedFases] = useState<Record<string, boolean>>({});
  const [expandedActivities, setExpandedActivities] = useState<Record<string, boolean>>({});
  const [selectedCompetenciaByActivity, setSelectedCompetenciaByActivity] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!isOpen) return;
    setSelectedCompetenciaByActivity((prev) => {
      const next = { ...prev };
      let changed = false;
      fases.forEach((fase) => {
        fase.actividades.forEach((act) => {
          if (!next[act.actividad_id] && act.competencias.length > 0) {
            next[act.actividad_id] = act.competencias[0].competencia_id;
            changed = true;
          }
        });
      });
      return changed ? next : prev;
    });
  }, [fases, isOpen]);

  if (!isOpen) {
    return null;
  }

  const toggleFase = (faseId: string): void => {
    setExpandedFases((prev) => ({
      ...prev,
      [faseId]: !prev[faseId],
    }));
  };

  const toggleActivity = (actId: string): void => {
    setExpandedActivities((prev) => ({
      ...prev,
      [actId]: !prev[actId],
    }));
  };

  const handleCompetenciaChange = (actId: string, compId: string): void => {
    setSelectedCompetenciaByActivity((prev) => ({
      ...prev,
      [actId]: compId,
    }));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm transition-all duration-300">
      <div className="relative flex flex-col w-full max-w-4xl max-h-[85vh] bg-white rounded-xl shadow-2xl border border-[color:var(--card-border)] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-[color:var(--card-border)] bg-[var(--paper-strong)]">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent-strong)]">
              <Layers className="h-5 w-5" />
            </span>
            <div>
              <h2 className="text-lg font-bold text-[var(--foreground)]">
                Fases y Estructura Curricular del Proyecto
              </h2>
              <p className="text-xs text-[var(--muted)]">
                Previsualización detallada de la planeación pedagógica importada
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg border border-[color:var(--card-border)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent-strong)] transition-all"
            aria-label="Cerrar modal"
          >
            <X className="h-5 w-5" />
          </button>
        </header>

        {/* Scrollable Content */}
        <div className="flex-1 p-6 overflow-y-auto space-y-4">
          {fases.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <AlertCircle className="h-10 w-10 text-[var(--muted)] mb-2" />
              <p className="text-sm font-semibold text-[var(--foreground)]">No hay fases detectadas</p>
              <p className="text-xs text-[var(--muted)]">El archivo Excel no contiene datos de planeación válidos.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {fases.map((fase) => {
                const isFaseExpanded = !!expandedFases[fase.fase_id];
                return (
                  <div
                    key={fase.fase_id}
                    className="border border-[color:var(--card-border)] rounded-lg overflow-hidden bg-white shadow-sm transition-all"
                  >
                    {/* Fase Accordion Header */}
                    <button
                      type="button"
                      onClick={() => toggleFase(fase.fase_id)}
                      className="flex items-center justify-between w-full px-5 py-4 text-left font-semibold hover:bg-[var(--paper-strong)] transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-xs bg-[var(--accent-soft)] text-[var(--accent-strong)] px-2 py-0.5 rounded font-mono">
                          Fase {fase.orden !== null ? fase.orden : ""}
                        </span>
                        <span className="text-base font-bold text-[var(--foreground)]">
                          {fase.nombre_fase}
                        </span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-xs text-[var(--muted)] hidden sm:inline">
                          {fase.actividades.length} Actividad{fase.actividades.length !== 1 ? "es" : ""} • {fase.numero_competencias} Competencia{fase.numero_competencias !== 1 ? "s" : ""} • {fase.numero_resultados} RAP{fase.numero_resultados !== 1 ? "s" : ""}
                        </span>
                        {isFaseExpanded ? (
                          <ChevronUp className="h-5 w-5 text-[var(--muted)]" />
                        ) : (
                          <ChevronDown className="h-5 w-5 text-[var(--muted)]" />
                        )}
                      </div>
                    </button>

                    {/* Fase Content (Activities Accordion) */}
                    {isFaseExpanded && (
                      <div className="px-5 pb-4 border-t border-[color:var(--card-border)] bg-[var(--paper-strong)]/30 space-y-3 pt-3">
                        {fase.actividades.length === 0 ? (
                          <p className="text-xs text-[var(--muted)] py-2">
                            No hay actividades registradas en esta fase.
                          </p>
                        ) : (
                          fase.actividades.map((act) => {
                            const isActExpanded = !!expandedActivities[act.actividad_id];
                            const selectedCompId = selectedCompetenciaByActivity[act.actividad_id] ?? "";
                            const selectedComp = act.competencias.find(
                              (c) => c.competencia_id === selectedCompId
                            );

                            const compCount = act.competencias.length;
                            const resCount = act.competencias.reduce(
                              (acc, c) => acc + c.resultados.length,
                              0
                            );

                            return (
                              <div
                                key={act.actividad_id}
                                className="border border-[color:var(--card-border)] rounded-md bg-white overflow-hidden shadow-sm"
                              >
                                {/* Activity Accordion Header */}
                                <button
                                  type="button"
                                  onClick={() => toggleActivity(act.actividad_id)}
                                  className="flex items-center justify-between w-full px-4 py-3 text-left hover:bg-[var(--paper-strong)] transition-colors"
                                >
                                  <div className="flex items-start gap-2.5 min-w-0 pr-4">
                                    <span className="text-xs bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded font-mono shrink-0 mt-0.5">
                                      Act {act.orden !== null ? act.orden : ""}
                                    </span>
                                    <span className="text-sm font-semibold text-[var(--foreground)] truncate">
                                      {act.descripcion}
                                    </span>
                                  </div>
                                  <div className="flex items-center gap-3 shrink-0">
                                    <span className="text-xs text-[var(--muted)]">
                                      {compCount} Comp. • {resCount} RAP
                                    </span>
                                    {isActExpanded ? (
                                      <ChevronUp className="h-4 w-4 text-[var(--muted)]" />
                                    ) : (
                                      <ChevronDown className="h-4 w-4 text-[var(--muted)]" />
                                    )}
                                  </div>
                                </button>

                                {/* Activity Content */}
                                {isActExpanded && (
                                  <div className="p-4 border-t border-[color:var(--card-border)] bg-slate-50/50 space-y-4">
                                    {/* Competence Selector */}
                                    <div className="flex flex-col gap-1.5">
                                      <label
                                        htmlFor={`comp-select-${act.actividad_id}`}
                                        className="text-xs font-semibold text-[var(--muted)] uppercase tracking-wider"
                                      >
                                        Seleccionar Competencia
                                      </label>
                                      {act.competencias.length === 0 ? (
                                        <p className="text-xs text-amber-600 bg-amber-50 border border-amber-100 p-2 rounded">
                                          Esta actividad no tiene competencias asociadas.
                                        </p>
                                      ) : (
                                        <select
                                          id={`comp-select-${act.actividad_id}`}
                                          value={selectedCompId}
                                          onChange={(e) =>
                                            handleCompetenciaChange(act.actividad_id, e.target.value)
                                          }
                                          className="w-full max-w-full rounded-md border border-[color:var(--card-border)] bg-white px-3 py-2 text-sm shadow-sm focus:border-[var(--accent)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                                        >
                                          {act.competencias.map((comp) => (
                                            <option key={comp.competencia_id} value={comp.competencia_id}>
                                              [{comp.codigo_competencia}] {comp.nombre_competencia}
                                            </option>
                                          ))}
                                        </select>
                                      )}
                                    </div>

                                    {/* RAPs for the selected Competence */}
                                    {selectedComp && (
                                      <div className="space-y-2">
                                        <p className="text-xs font-semibold text-[var(--muted)] uppercase tracking-wider">
                                          Resultados de Aprendizaje ({selectedComp.resultados.length})
                                        </p>
                                        {selectedComp.resultados.length === 0 ? (
                                          <p className="text-xs text-[var(--muted)] italic">
                                            No hay resultados asociados a esta competencia en esta actividad.
                                          </p>
                                        ) : (
                                          <div className="grid gap-2">
                                            {selectedComp.resultados.map((rap) => (
                                              <div
                                                key={rap.rap_id}
                                                className="bg-white border border-[color:var(--card-border)] rounded p-3 text-xs shadow-sm flex flex-col gap-2"
                                              >
                                                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-dashed border-slate-100 pb-1.5">
                                                  <span className="font-semibold text-slate-800">
                                                    {rap.rap_numero ? `RAP #${rap.rap_numero}` : "RAP sin número"}
                                                  </span>
                                                  <div className="flex gap-1.5">
                                                    <span className={cn(
                                                      "px-1.5 py-0.5 rounded-full text-[10px] font-bold uppercase",
                                                      (rap.tipo_resultado || "").trim().toUpperCase() === "ESPECIFICO"
                                                        ? "bg-indigo-50 text-indigo-700 border border-indigo-100"
                                                        : "bg-slate-100 text-slate-600"
                                                    )}>
                                                      {rap.tipo_resultado || "Sin clasificar"}
                                                    </span>
                                                    {rap.pagina_origen && (
                                                      <span className="bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded font-mono">
                                                        Pág. {rap.pagina_origen}
                                                      </span>
                                                    )}
                                                  </div>
                                                </div>
                                                <p className="text-slate-600 leading-relaxed font-medium">
                                                  {rap.resultado_aprendizaje}
                                                </p>
                                                {rap.observaciones && (
                                                  <div className="text-[10px] text-amber-700 bg-amber-50/50 border border-amber-100/50 rounded p-1.5 font-medium">
                                                    <strong>Obs:</strong> {rap.observaciones}
                                                  </div>
                                                )}
                                              </div>
                                            ))}
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            );
                          })
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <footer className="flex justify-end gap-3 px-6 py-4 border-t border-[color:var(--card-border)] bg-[var(--paper-strong)]">
          <button
            type="button"
            onClick={onClose}
            className="inline-flex min-h-9 items-center justify-center rounded-lg border border-[color:var(--card-border)] bg-white px-4 py-2 text-sm font-semibold text-[var(--foreground)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent-strong)] transition-all"
          >
            Cerrar vista
          </button>
        </footer>
      </div>
    </div>
  );
}

function PreviewSection({
  onOpenFases,
  preview,
}: Readonly<{
  onOpenFases: () => void;
  preview: ProyectoExcelPreviewState["preview"];
}>): React.JSX.Element | null {
  if (preview === null) {
    return null;
  }

  return (
    <section aria-label="Preview Excel del proyecto" className="grid gap-4">
      <div
        className={cn(
          "rounded-lg border p-4",
          preview.valid
            ? "border-emerald-200 bg-emerald-50 text-emerald-900"
            : "border-amber-200 bg-amber-50 text-amber-950",
        )}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            {preview.valid ? (
              <CheckCircle2 className="h-5 w-5" />
            ) : (
              <AlertCircle className="h-5 w-5" />
            )}
            <p className="text-sm font-semibold">
              {preview.valid
                ? "Excel valido - listo para confirmar importacion"
                : "Excel con errores de validacion"}
            </p>
          </div>
          <span className="text-xs font-semibold">{preview.estado_validacion}</span>
        </div>

        {preview.proyecto !== null ? (
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="font-semibold">Codigo del proyecto</dt>
              <dd className="mt-1">{preview.proyecto.codigo_proyecto}</dd>
            </div>
            <div>
              <dt className="font-semibold">Version</dt>
              <dd className="mt-1">{preview.proyecto.version_proyecto}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="font-semibold">Nombre del proyecto</dt>
              <dd className="mt-1">{preview.proyecto.nombre_proyecto}</dd>
            </div>
          </dl>
        ) : null}

        <div className="mt-4 grid grid-cols-2 gap-3 text-center sm:grid-cols-4">
          <div className="rounded-lg bg-white/60 p-3">
            <p className="text-2xl font-bold">{preview.resumen.proyecto}</p>
            <p className="text-xs text-[var(--muted)]">Proyecto</p>
          </div>
          <div className="rounded-lg bg-white/60 p-3">
            <p className="text-2xl font-bold">{preview.resumen.fases}</p>
            <p className="text-xs text-[var(--muted)]">Fases</p>
          </div>
          <div className="rounded-lg bg-white/60 p-3">
            <p className="text-2xl font-bold">{preview.resumen.actividades}</p>
            <p className="text-xs text-[var(--muted)]">Actividades</p>
          </div>
          <div className="rounded-lg bg-white/60 p-3">
            <p className="text-2xl font-bold">{preview.resumen.resultados_especificos}</p>
            <p className="text-xs text-[var(--muted)]">Resultados específicos</p>
          </div>
        </div>
      </div>

      {preview.fases.length > 0 ? (
        <section className="rounded-lg border border-[color:var(--card-border)] bg-white p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <p className="text-xs font-semibold tracking-[0.16em] text-[var(--muted)] uppercase">
              Estructura de Fases
            </p>
            <p className="mt-1 text-sm text-[var(--muted)]">
              Se detectaron {preview.fases.length} fases con actividades y planeación curricular.
            </p>
          </div>
          <button
            type="button"
            onClick={onOpenFases}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[var(--accent)] bg-white px-4 py-2 text-sm font-semibold text-[var(--accent-strong)] transition hover:bg-[var(--accent-soft)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            <Layers className="h-4 w-4" />
            Ver fases de proyecto
          </button>
        </section>
      ) : null}

      {preview.errores.length > 0 ? (
        <section className="rounded-lg border border-rose-200 bg-rose-50 p-4">
          <p className="text-sm font-semibold text-rose-900">
            Errores de validacion ({preview.errores.length})
          </p>
          <ul className="mt-2 grid gap-1">
            {preview.errores.map((error, index) => (
              <li
                key={index}
                className="flex items-start gap-2 text-xs text-rose-800"
              >
                <AlertCircle className="mt-0.5 h-3 w-3 shrink-0" />
                <span>
                  [{error.hoja}
                  {error.fila !== null ? ` - Fila ${error.fila}` : ""}
                  {error.campo ? `, Campo '${error.campo}'` : ""}]: {error.mensaje}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}

export function ProyectoExcelImport({
  currentResult,
  onPreview,
  onImported,
  planeacionHref,
  referenciaId,
}: Readonly<{
  currentResult: ProyectoExcelPreviewState | null;
  onPreview: (result: ProyectoExcelPreviewState) => void;
  onImported: (result: ProyectoExcelPreviewState) => void;
  planeacionHref?: string;
  referenciaId: string;
}>): React.JSX.Element {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [localResult, setLocalResult] =

    useState<ProyectoExcelPreviewState | null>(currentResult);
  const [state, setState] = useState<UploadState>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [alreadyLoadedMessage, setAlreadyLoadedMessage] = useState<
    string | null
  >(null);
  const [isFasesModalOpen, setIsFasesModalOpen] = useState<boolean>(false);
  const effectiveResult = localResult ?? currentResult;

  const confirm = useConfirm();

  const handleEliminarCargue = async (): Promise<void> => {
    const confirmed = await confirm({
      title: "Eliminar cargue de proyecto",
      message: "¿Estás seguro de que deseas eliminar por completo el cargue del proyecto formativo? Esta acción eliminará permanentemente todos los datos y archivos del proyecto de la base de datos y de MinIO, preservando el programa de formación.",
      isDestructive: true,
    });
    if (!confirmed) return;

    setIsDeleting(true);
    try {
      await eliminarCargueProyecto(referenciaId);
      setSelectedFile(null);
      setLocalResult(null);
      setState("idle");
      setMessage("El cargue del proyecto ha sido eliminado con exito. Puedes subir un nuevo archivo Excel para el proyecto.");
      notify.success("Cargue del proyecto eliminado", {
        description: "Los datos y archivos del proyecto formativo han sido borrados de la base de datos y MinIO.",
      });
      window.location.reload();
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : "Error al eliminar el cargue del proyecto.";
      notify.error("Error al eliminar cargue del proyecto", {
        description: errMsg,
      });
    } finally {
      setIsDeleting(false);
    }
  };


  useEffect(() => {
    setLocalResult(currentResult);
  }, [currentResult]);

  const handlePreview = async (): Promise<void> => {
    const validationError = validateExcelFile(selectedFile);
    if (validationError !== null) {
      setState("error");
      setMessage(validationError);
      notify.warning("No se pudo cargar el Excel", {
        description: validationError,
      });
      return;
    }

    const file = selectedFile;
    if (file === null) {
      return;
    }

    setState("uploading");
    setMessage(null);

    try {
      const result = await uploadProjectExcelPreview(referenciaId, file);
      const previewState: ProyectoExcelPreviewState = {
        documento: result.documento ?? null,
        preview: {
          valid: result.valid,
          estado_validacion: result.estado_validacion,
          resumen: result.resumen,
          proyecto: result.proyecto,
          fases: result.fases,
          pendientes_resumen: result.pendientes_resumen,
          errores: result.errores,
        },
        confirmacion: { estado: "PENDIENTE" },
        updated_at: new Date().toISOString(),
      };
      setLocalResult(previewState);
      onPreview(previewState);
      setState("preview");
      setMessage(
        result.valid
          ? "Excel validado correctamente. Revisa el preview y confirma la importacion."
          : "El Excel tiene errores. Corrigelos antes de confirmar.",
      );
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      setState("error");
      setMessage(errorMessage);
      if (isAlreadyLoadedMessage(errorMessage)) {
        setAlreadyLoadedMessage(errorMessage);
      }
      notify.error("No fue posible procesar el Excel", {
        description: errorMessage,
      });
    }
  };

  const handleConfirm = async (): Promise<void> => {
    setState("confirming");
    setMessage(null);

    try {
      const result = await confirmProjectExcelImport(referenciaId);
      const importedState: ProyectoExcelPreviewState = {
        documento: effectiveResult?.documento ?? null,
        preview: effectiveResult?.preview ?? null,
        confirmacion: {
          estado: "IMPORTADO",
          confirmed_at: new Date().toISOString(),
          proyecto_id: result.proyecto_id,
          fase_ids: result.fase_ids,
          actividad_ids: result.actividad_ids,
          pendientes_resumen: result.pendientes_resumen,
        },
        updated_at: new Date().toISOString(),
      };
      setLocalResult(importedState);
      onImported(importedState);
      setState("success");
      setMessage(
        `Importacion completada: ${result.resumen.fases} fases y ${result.resumen.actividades} actividades materializadas.`,
      );
      notify.success("Importacion completada", {
        description: importedState.confirmacion.confirmed_at
          ? `Proyecto creado con ${result.fase_ids.length} fases y ${result.actividad_ids.length} actividades.`
          : "Datos del proyecto actualizados.",
      });
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      setState("error");
      setMessage(errorMessage);
      if (isAlreadyLoadedMessage(errorMessage)) {
        setAlreadyLoadedMessage(errorMessage);
      }
      notify.error("No fue posible confirmar la importacion", {
        description: errorMessage,
      });
    }
  };

  const isImported = effectiveResult?.confirmacion.estado === "IMPORTADO";
  const hasPreview =
    effectiveResult?.preview !== null && effectiveResult?.preview !== undefined;
  const hasErrors = (effectiveResult?.preview?.errores.length ?? 0) > 0;
  const canConfirm = hasPreview && !hasErrors && !isImported;

  return (
    <section aria-label="Cargue Excel del proyecto" className="grid gap-4">
      {alreadyLoadedMessage !== null ? (
        <AlreadyLoadedModal
          message={alreadyLoadedMessage}
          onClose={() => setAlreadyLoadedMessage(null)}
          planeacionHref={planeacionHref ?? `/planeacion/${referenciaId}`}
        />
      ) : null}

      <div className="rounded-lg border border-[color:var(--card-border)] bg-[var(--paper-strong)] p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="inline-flex h-11 w-11 items-center justify-center rounded-lg bg-white text-[var(--accent-strong)]">
              <FileSpreadsheet className="h-5 w-5" />
            </span>
            <div>
              <p className="text-sm font-semibold text-[var(--foreground)]">
                Matriz Excel del proyecto formativo
              </p>
              <p className="mt-1 text-sm leading-6 text-[var(--muted)]">
                Fuente estructurada del proyecto formativo. Define Proyecto formativo, Fases y
                Actividades. El PDF cargado anteriormente es solo evidencia
                documental.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[var(--accent)] bg-white px-3 py-2 text-sm font-semibold text-[var(--accent-strong)] transition hover:bg-[var(--accent-soft)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
            disabled={isImported}
          >
            <Upload className="h-4 w-4" />
            Seleccionar Excel
          </button>
        </div>

        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          className="sr-only"
          onChange={(event) => {
            const file = event.target.files?.[0] ?? null;
            setSelectedFile(file);
            setState("idle");
            setMessage(file === null ? null : "Archivo listo para previsualizar.");
          }}
        />

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-[var(--foreground)]">
              {selectedFile?.name ?? "Sin archivo seleccionado"}
            </p>
            <p className="mt-1 text-xs text-[var(--muted)]">
              {selectedFile === null
                ? "Excel requerido"
                : formatFileSize(selectedFile.size)}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={state === "uploading" || isImported}
              onClick={() => void handlePreview()}
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
            >
              {state === "uploading" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : isImported ? (
                <CheckCircle2 className="h-4 w-4" />
              ) : (
                <FileSpreadsheet className="h-4 w-4" />
              )}
              {state === "uploading"
                ? "Procesando..."
                : isImported
                  ? "Importado"
                  : "Previsualizar"}
            </button>

            {canConfirm && (
              <button
                type="button"
                disabled={state === "confirming"}
                onClick={() => void handleConfirm()}
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-emerald-600 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
              >
                {state === "confirming" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-4 w-4" />
                )}
                {state === "confirming" ? "Importando..." : "Confirmar importacion"}
              </button>
            )}
          </div>
        </div>
      </div>

      {message !== null ? (
        <div
          role={state === "error" || (state === "preview" && effectiveResult?.preview?.valid === false) ? "alert" : "status"}
          className={cn(
            "flex flex-col gap-2 rounded-lg border px-4 py-3 text-sm leading-6",
            state === "error" || (state === "preview" && effectiveResult?.preview?.valid === false)
              ? "border-rose-200 bg-rose-50 text-rose-900"
              : state === "success"
                ? "border-emerald-200 bg-emerald-50 text-emerald-900"
                : "border-blue-200 bg-blue-50 text-blue-900",
          )}
        >
          <div className="flex items-start gap-2">
            {state === "error" || (state === "preview" && effectiveResult?.preview?.valid === false) ? (
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            ) : (
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            )}
            <p className="font-semibold">{message}</p>
          </div>
          {state === "preview" && effectiveResult?.preview?.valid === false && effectiveResult.preview.errores.length > 0 && (
            <ul className="mt-1 ml-6 list-disc text-xs text-rose-800 grid gap-1">
              {effectiveResult.preview.errores.map((error, index) => (
                <li key={index}>
                  [{error.hoja}
                  {error.fila !== null ? ` - Fila ${error.fila}` : ""}
                  {error.campo ? `, Campo '${error.campo}'` : ""}]: {error.mensaje}
                </li>
              ))}
            </ul>
          )}
          {(message.includes("ya ha sido importado") || message.includes("ya tiene un proyecto")) && (
            <div className="mt-3 flex justify-end border-t border-rose-100 pt-2">
              <button
                type="button"
                disabled={isDeleting}
                onClick={() => void handleEliminarCargue()}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-red-200 bg-red-100/50 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-100 transition-colors"
              >
                Eliminar cargue actual
              </button>
            </div>
          )}
        </div>
      ) : null}


      {effectiveResult && effectiveResult.preview !== null ? (
        <>
          <PreviewSection
            preview={effectiveResult.preview}
            onOpenFases={() => setIsFasesModalOpen(true)}
          />
          <CurriculumFasesModal
            isOpen={isFasesModalOpen}
            onClose={() => setIsFasesModalOpen(false)}
            fases={effectiveResult.preview.fases}
          />
        </>
      ) : null}

      {effectiveResult && effectiveResult.confirmacion.proyecto_id && isImported ? (
        <section className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-emerald-700" />
            <p className="text-sm font-semibold text-emerald-900">
              Importacion confirmada
            </p>
          </div>
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="font-semibold">Proyecto ID</dt>
              <dd className="mt-1 text-xs break-all">
                {effectiveResult.confirmacion.proyecto_id}
              </dd>
            </div>
            <div>
              <dt className="font-semibold">Fases creadas</dt>
              <dd className="mt-1">
                {effectiveResult.confirmacion.fase_ids?.length ?? 0}
              </dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="font-semibold">Actividades creadas</dt>
              <dd className="mt-1">
                {effectiveResult.confirmacion.actividad_ids?.length ?? 0}
              </dd>
            </div>
          </dl>
          <div className="mt-4 flex justify-end border-t border-emerald-100 pt-3">
            <button
              type="button"
              disabled={isDeleting}
              onClick={() => void handleEliminarCargue()}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50 transition-colors"
            >
              Eliminar cargue y volver a empezar
            </button>
          </div>
        </section>
      ) : null}

    </section>
  );
}
