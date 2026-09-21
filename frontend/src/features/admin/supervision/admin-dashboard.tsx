"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authFetch, getApiBaseUrl } from "@/lib/api";
import { SummaryCards } from "./summary-cards";
import { ProcessFilters } from "./process-filters";
import { ProcessesTable } from "./processes-table";
import { ProcessDetailDrawer } from "./process-detail-drawer";
import {
  AdminDashboardResumen,
  AdminProcesoItem,
  PaginatedAdminProcesos,
  SupervisionFilters,
} from "../types";

export function AdminDashboard(): React.JSX.Element {
  const router = useRouter();

  const [resumen, setResumen] = useState<AdminDashboardResumen | null>(null);
  const [resumenLoading, setResumenLoading] = useState(true);

  const [procesos, setProcesos] = useState<AdminProcesoItem[]>([]);
  const [tableLoading, setTableLoading] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = 15;
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  const [filters, setFilters] = useState<SupervisionFilters>({});
  const [selectedProceso, setSelectedProceso] = useState<AdminProcesoItem | null>(null);

  // Build query string from filters
  const buildQueryString = useCallback(
    (customPage?: number) => {
      const params = new URLSearchParams();
      if (customPage) params.set("page", String(customPage));
      params.set("page_size", String(pageSize));

      if (filters.search) params.set("search", filters.search);
      if (filters.coordinacion_id) params.set("coordinacion_id", filters.coordinacion_id);
      if (filters.especialidad_id) params.set("especialidad_id", filters.especialidad_id);
      if (filters.equipo_ejecutor_id) params.set("equipo_ejecutor_id", filters.equipo_ejecutor_id);
      if (filters.lider_id) params.set("lider_id", filters.lider_id);
      if (filters.estado_scope) params.set("estado_scope", filters.estado_scope);
      if (filters.solo_sin_asignar) params.set("solo_sin_asignar", "true");

      return params.toString();
    },
    [filters, pageSize]
  );

  // Load summary metrics
  const fetchResumen = useCallback(async () => {
    try {
      setResumenLoading(true);
      const query = buildQueryString();
      const res = await authFetch(`${getApiBaseUrl()}/admin/dashboard/resumen?${query}`);
      if (res.ok) {
        const data: AdminDashboardResumen = await res.json();
        setResumen(data);
      }
    } catch (err) {
      console.error("Error loading supervision resumen:", err);
    } finally {
      setResumenLoading(false);
    }
  }, [buildQueryString]);

  // Load paginated processes
  const fetchProcesos = useCallback(
    async (targetPage: number) => {
      try {
        setTableLoading(true);
        const query = buildQueryString(targetPage);
        const res = await authFetch(`${getApiBaseUrl()}/admin/dashboard/procesos?${query}`);
        if (res.ok) {
          const data: PaginatedAdminProcesos = await res.json();
          setProcesos(data.items);
          setTotal(data.total);
          setTotalPages(data.total_pages);
          setPage(data.page);
        }
      } catch (err) {
        console.error("Error loading supervision procesos:", err);
      } finally {
        setTableLoading(false);
      }
    },
    [buildQueryString]
  );

  useEffect(() => {
    fetchResumen();
  }, [fetchResumen]);

  useEffect(() => {
    fetchProcesos(page);
  }, [fetchProcesos, page]);

  const handleFilterChange = (newFilters: SupervisionFilters) => {
    setFilters(newFilters);
    setPage(1);
  };

  const handleResetFilters = () => {
    setFilters({});
    setPage(1);
  };

  const handleActivateProcess = (referenciaId: string) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("asgard_active_referencia_id", referenciaId);
    }
    router.push(`/?ref=${referenciaId}`);
  };

  return (
    <div className="space-y-6">
      {/* 1. Macro Summary KPI Cards */}
      <SummaryCards resumen={resumen} loading={resumenLoading} />

      {/* 2. Reactive Filters */}
      <ProcessFilters
        filters={filters}
        onFilterChange={handleFilterChange}
        onReset={handleResetFilters}
      />

      {/* 3. Processes Table */}
      <ProcessesTable
        procesos={procesos}
        loading={tableLoading}
        page={page}
        pageSize={pageSize}
        total={total}
        totalPages={totalPages}
        onPageChange={(newPage) => setPage(newPage)}
        onSelectProceso={(p) => setSelectedProceso(p)}
        onActivateProcess={handleActivateProcess}
      />

      {/* 4. Slide-over Drill-down Drawer */}
      <ProcessDetailDrawer
        proceso={selectedProceso}
        onClose={() => setSelectedProceso(null)}
        onActivateProcess={handleActivateProcess}
      />
    </div>
  );
}
