"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Search,
  RefreshCcw,
  Eye,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Send,
} from "lucide-react";
import { toast } from "sonner";
import {
  type EntregaRevisionResumen,
  type EstadoEntregaRevision,
  fetchBandejaRevision,
  iniciarRevisionEntrega,
} from "@/features/planeacion/planeacion-api";
import { cn } from "@/lib/utils";

interface RevisionInboxProps {
  onSelectEntrega: (entregaId: string) => void;
}

const ESTADOS_MAP: Record<EstadoEntregaRevision, { label: string; color: string; bg: string }> = {
  BORRADOR: { label: "Borrador", color: "text-slate-600", bg: "bg-slate-100" },
  ENVIADO_REVISION: { label: "Enviado a Revisión", color: "text-amber-800", bg: "bg-amber-50 border-amber-200" },
  EN_REVISION: { label: "En Revisión", color: "text-sky-800", bg: "bg-sky-50 border-sky-200" },
  AJUSTES_SOLICITADOS: { label: "Ajustes Solicitados", color: "text-rose-800", bg: "bg-rose-50 border-rose-200" },
  AJUSTES_EN_PROGRESO: { label: "Ajustes en Progreso", color: "text-purple-800", bg: "bg-purple-50 border-purple-200" },
  REENVIADO: { label: "Reenviado con Ajustes", color: "text-indigo-800", bg: "bg-indigo-50 border-indigo-200" },
  APROBADO: { label: "Aprobado", color: "text-emerald-800", bg: "bg-emerald-50 border-emerald-200" },
};

export function RevisionInbox({ onSelectEntrega }: RevisionInboxProps): React.JSX.Element {
  const [items, setItems] = useState<EntregaRevisionResumen[]>([]);
  const [metricas, setMetricas] = useState<Record<string, number>>({});
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [selectedEstado, setSelectedEstado] = useState<EstadoEntregaRevision | "ALL">("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  const handleRevisarEntrega = async (item: EntregaRevisionResumen) => {
    if (item.estado === "ENVIADO_REVISION" || item.estado === "REENVIADO") {
      try {
        await iniciarRevisionEntrega(item.id);
      } catch {
        // Non-blocking: RevisionDetailView will still load and allow manual start if needed
      }
    }
    onSelectEntrega(item.id);
  };

  const loadBandeja = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchBandejaRevision({
        estado: selectedEstado === "ALL" ? null : selectedEstado,
        page,
        limit: 15,
      });
      setItems(res.items);
      setMetricas(res.metricas);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Error al cargar la bandeja de revisiones");
    } finally {
      setLoading(false);
    }
  }, [selectedEstado, page]);

  useEffect(() => {
    void loadBandeja();
  }, [loadBandeja]);

  // Client-side search filtering over current items for instantaneous responsiveness
  const filteredItems = items.filter((item) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      item.equipo_ejecutor_nombre.toLowerCase().includes(q) ||
      item.nombre_programa.toLowerCase().includes(q) ||
      item.codigo_programa.toLowerCase().includes(q) ||
      item.nombre_proyecto.toLowerCase().includes(q) ||
      item.codigo_proyecto.toLowerCase().includes(q) ||
      item.lider_nombre.toLowerCase().includes(q) ||
      item.lider_email.toLowerCase().includes(q)
    );
  });

  const pendientesCount =
    metricas["pendientes"] ??
    (metricas["pendientes_revision"] ?? 0) + (metricas["reenviadas"] ?? 0);
  const enRevisionCount = metricas["en_revision"] ?? 0;
  const conAjustesCount =
    metricas["ajustes_solicitados"] ?? metricas["con_ajustes_solicitados"] ?? 0;
  const aprobadasCount = metricas["aprobadas"] ?? 0;

  return (
    <div className="space-y-6">
      {/* Metric Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-4 dark:border-amber-900/50 dark:bg-amber-950/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-800 dark:text-amber-400">
              Pendientes
            </span>
            <Clock className="h-4 w-4 text-amber-600 dark:text-amber-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-amber-900 dark:text-amber-300">
            {pendientesCount}
          </p>
          <p className="mt-0.5 text-xs text-amber-700 dark:text-amber-500">
            Enviadas y reenviadas por equipos
          </p>
        </div>

        <div className="rounded-xl border border-sky-200 bg-sky-50/50 p-4 dark:border-sky-900/50 dark:bg-sky-950/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-sky-800 dark:text-sky-400">
              En Revisión
            </span>
            <Send className="h-4 w-4 text-sky-600 dark:text-sky-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-sky-900 dark:text-sky-300">
            {enRevisionCount}
          </p>
          <p className="mt-0.5 text-xs text-sky-700 dark:text-sky-500">
            Actualmente bajo análisis pedagógico
          </p>
        </div>

        <div className="rounded-xl border border-rose-200 bg-rose-50/50 p-4 dark:border-rose-900/50 dark:bg-rose-950/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-rose-800 dark:text-rose-400">
              Con Ajustes
            </span>
            <AlertTriangle className="h-4 w-4 text-rose-600 dark:text-rose-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-rose-900 dark:text-rose-300">
            {conAjustesCount}
          </p>
          <p className="mt-0.5 text-xs text-rose-700 dark:text-rose-500">
            Devueltas al equipo para corrección
          </p>
        </div>

        <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4 dark:border-emerald-900/50 dark:bg-emerald-950/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-800 dark:text-emerald-400">
              Aprobadas
            </span>
            <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
          </div>
          <p className="mt-2 text-2xl font-bold text-emerald-900 dark:text-emerald-300">
            {aprobadasCount}
          </p>
          <p className="mt-0.5 text-xs text-emerald-700 dark:text-emerald-500">
            Descarga oficial habilitada
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Estado:
          </span>
          <select
            value={selectedEstado}
            onChange={(e) => {
              setSelectedEstado(e.target.value as EstadoEntregaRevision | "ALL");
              setPage(1);
            }}
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 outline-none focus:border-emerald-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          >
            <option value="ALL">Todos los estados ({total})</option>
            <option value="ENVIADO_REVISION">Enviados a Revisión</option>
            <option value="REENVIADO">Reenviados con Ajustes</option>
            <option value="EN_REVISION">En Revisión</option>
            <option value="AJUSTES_SOLICITADOS">Ajustes Solicitados</option>
            <option value="AJUSTES_EN_PROGRESO">Ajustes en Progreso</option>
            <option value="APROBADO">Aprobados</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative w-full sm:w-72">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar equipo, programa o líder..."
              className="w-full rounded-lg border border-slate-200 bg-white py-1.5 pl-9 pr-3 text-xs outline-none focus:border-emerald-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            />
          </div>
          <button
            type="button"
            onClick={() => void loadBandeja()}
            disabled={loading}
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
            title="Refrescar bandeja"
          >
            <RefreshCcw className={cn("h-4 w-4", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Deliveries List */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-900 dark:text-white">
            Entregas Curriculares para Revisión Pedagógica
          </h2>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            Revisa las planeaciones pedagógicas consolidadas, emite observaciones tipificadas y autoriza la descarga oficial.
          </p>
        </div>

        {loading ? (
          <div className="flex min-h-64 items-center justify-center p-8">
            <div className="flex items-center gap-2 text-emerald-600">
              <RefreshCcw className="h-5 w-5 animate-spin" />
              <span className="text-sm font-medium">Cargando bandeja de revisiones...</span>
            </div>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="flex min-h-64 flex-col items-center justify-center p-8 text-center">
            <div className="rounded-full bg-slate-100 p-3 text-slate-400 dark:bg-slate-800">
              <CheckCircle2 className="h-8 w-8" />
            </div>
            <h3 className="mt-3 text-sm font-semibold text-slate-800 dark:text-slate-200">
              No hay entregas en esta sección
            </h3>
            <p className="mt-1 max-w-sm text-xs text-slate-500 dark:text-slate-400">
              {searchQuery
                ? "No se encontraron entregas que coincidan con la búsqueda."
                : "No hay planeaciones curriculares con el filtro de estado seleccionado."}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
              <thead className="border-b border-slate-200 bg-slate-50 font-semibold uppercase text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400">
                <tr>
                  <th className="px-6 py-3.5">Equipo & Líder</th>
                  <th className="px-6 py-3.5">Programa & Proyecto</th>
                  <th className="px-6 py-3.5 text-center">Versión</th>
                  <th className="px-6 py-3.5">Fecha Envío</th>
                  <th className="px-6 py-3.5 text-center">Observaciones</th>
                  <th className="px-6 py-3.5">Estado</th>
                  <th className="px-6 py-3.5 text-right">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {filteredItems.map((item) => {
                  const est = ESTADOS_MAP[item.estado] ?? {
                    label: item.estado,
                    color: "text-slate-600",
                    bg: "bg-slate-100",
                  };
                  return (
                    <tr
                      key={item.id}
                      className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition"
                    >
                      <td className="px-6 py-4">
                        <div className="font-bold text-slate-900 dark:text-white">
                          {item.equipo_ejecutor_nombre}
                        </div>
                        <div className="mt-0.5 text-slate-500 dark:text-slate-400">
                          {item.lider_nombre}
                        </div>
                        <div className="text-[11px] text-slate-400">{item.lider_email}</div>
                      </td>

                      <td className="px-6 py-4">
                        <div className="font-semibold text-slate-800 dark:text-slate-200 line-clamp-1">
                          {item.codigo_programa} - {item.nombre_programa}
                        </div>
                        <div className="mt-0.5 text-slate-500 dark:text-slate-400 line-clamp-1">
                          {item.codigo_proyecto} - {item.nombre_proyecto}
                        </div>
                      </td>

                      <td className="px-6 py-4 text-center font-bold text-slate-800 dark:text-slate-200">
                        v{item.version}
                      </td>

                      <td className="px-6 py-4 whitespace-nowrap text-slate-600 dark:text-slate-300">
                        {new Date(item.fecha_envio).toLocaleDateString("es-CO", {
                          day: "2-digit",
                          month: "short",
                          year: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>

                      <td className="px-6 py-4 text-center">
                        <div className="inline-flex items-center gap-1.5 text-xs font-semibold">
                          {item.observaciones_pendientes_count > 0 && (
                            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                              {item.observaciones_pendientes_count} pend.
                            </span>
                          )}
                          {item.observaciones_ajustadas_count > 0 && (
                            <span className="rounded-full bg-blue-100 px-2 py-0.5 text-blue-800 dark:bg-blue-950 dark:text-blue-300">
                              {item.observaciones_ajustadas_count} ajust.
                            </span>
                          )}
                          {item.observaciones_resueltas_count > 0 && (
                            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                              {item.observaciones_resueltas_count} res.
                            </span>
                          )}
                          {item.observaciones_pendientes_count === 0 &&
                            item.observaciones_ajustadas_count === 0 &&
                            item.observaciones_resueltas_count === 0 && (
                              <span className="text-slate-400">Sin obs.</span>
                            )}
                        </div>
                      </td>

                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={cn(
                            "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold",
                            est.bg,
                            est.color,
                          )}
                        >
                          {est.label}
                        </span>
                      </td>

                      <td className="px-6 py-4 text-right whitespace-nowrap">
                        <button
                          type="button"
                          onClick={() => void handleRevisarEntrega(item)}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 transition"
                        >
                          <Eye className="h-3.5 w-3.5" />
                          Revisar
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-200 px-6 py-3 dark:border-slate-800">
            <span className="text-xs text-slate-500">
              Página {page} de {totalPages} ({total} entregas)
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="rounded-lg border border-slate-200 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300"
              >
                Anterior
              </button>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="rounded-lg border border-slate-200 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300"
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
