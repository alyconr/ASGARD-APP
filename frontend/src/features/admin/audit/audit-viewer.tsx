"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Lock } from "lucide-react";
import { authFetch, getApiBaseUrl } from "@/lib/api";
import { AuditFiltersComponent } from "./audit-filters";
import { AuditTable } from "./audit-table";
import { AuditDetailDialog } from "./audit-detail-dialog";
import { AuditFilters, AuditItem, PaginatedAuditResponse } from "../types";

export function AuditViewer(): React.JSX.Element {
  const [events, setEvents] = useState<AuditItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = 25;
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  const [filters, setFilters] = useState<AuditFilters>({});
  const [selectedEvent, setSelectedEvent] = useState<AuditItem | null>(null);

  const buildQueryString = useCallback(
    (targetPage?: number) => {
      const params = new URLSearchParams();
      params.set("page", String(targetPage || page));
      params.set("page_size", String(pageSize));

      if (filters.search) params.set("search", filters.search);
      if (filters.accion) params.set("accion", filters.accion);
      if (filters.entidad) params.set("entidad", filters.entidad);
      if (filters.fecha_desde) params.set("fecha_desde", filters.fecha_desde);
      if (filters.fecha_hasta) params.set("fecha_hasta", filters.fecha_hasta);

      return params.toString();
    },
    [filters, page, pageSize]
  );

  const fetchEvents = useCallback(
    async (targetPage: number) => {
      try {
        setLoading(true);
        const query = buildQueryString(targetPage);
        const res = await authFetch(`${getApiBaseUrl()}/admin/audit?${query}`);
        if (res.ok) {
          const data: PaginatedAuditResponse = await res.json();
          setEvents(data.items);
          setTotal(data.total);
          setTotalPages(data.total_pages);
          setPage(data.page);
        }
      } catch (err) {
        console.error("Error loading audit events:", err);
      } finally {
        setLoading(false);
      }
    },
    [buildQueryString]
  );

  useEffect(() => {
    fetchEvents(page);
  }, [fetchEvents, page]);

  const handleFilterChange = (newFilters: AuditFilters) => {
    setFilters(newFilters);
    setPage(1);
  };

  const handleResetFilters = () => {
    setFilters({});
    setPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Informative Banner */}
      <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-4 dark:border-emerald-950 dark:bg-emerald-950/20">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700 dark:bg-emerald-900/60 dark:text-emerald-300">
            <Lock className="h-5 w-5" />
          </div>
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-800 dark:text-emerald-300">
              Visor de Auditoría Inmutable & Sanitizado
            </h4>
            <p className="text-xs text-emerald-700/90 dark:text-emerald-400">
              Trazabilidad integral de operaciones críticas del sistema. Los campos de credenciales, contraseñas temporales y tokens de sesión son automáticamente redactados en este visor.
            </p>
          </div>
        </div>
      </div>

      {/* Filters Toolbar */}
      <AuditFiltersComponent
        filters={filters}
        onFilterChange={handleFilterChange}
        onReset={handleResetFilters}
      />

      {/* Events Table */}
      <AuditTable
        events={events}
        loading={loading}
        page={page}
        pageSize={pageSize}
        total={total}
        totalPages={totalPages}
        onPageChange={(newPage) => setPage(newPage)}
        onSelectEvent={(ev) => setSelectedEvent(ev)}
      />

      {/* Event Detail Modal */}
      <AuditDetailDialog
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
      />
    </div>
  );
}
