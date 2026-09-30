"use client";

import React, { useState } from "react";
import { RevisionInbox } from "./revision-inbox";
import { RevisionDetailView } from "./revision-detail-view";
import { AdminEditRequestList } from "./admin-edit-requests";

export function RevisionWorkspace(): React.JSX.Element {
  const [selectedEntregaId, setSelectedEntregaId] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<"bandeja" | "solicitudes">("bandeja");

  if (selectedEntregaId) {
    return (
      <RevisionDetailView
        entregaId={selectedEntregaId}
        onBack={() => setSelectedEntregaId(null)}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 border-b border-slate-200 pb-3 dark:border-slate-800">
        <button
          type="button"
          onClick={() => setActiveView("bandeja")}
          className={`rounded-xl px-4 py-2 text-xs font-bold transition ${
            activeView === "bandeja"
              ? "bg-emerald-600 text-white shadow-xs"
              : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"
          }`}
        >
          Bandeja de Entregas Curriculares
        </button>
        <button
          type="button"
          data-testid="tab-solicitudes-modificacion-global"
          onClick={() => setActiveView("solicitudes")}
          className={`rounded-xl px-4 py-2 text-xs font-bold transition ${
            activeView === "solicitudes"
              ? "bg-emerald-600 text-white shadow-xs"
              : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"
          }`}
        >
          Solicitudes de modificación
        </button>
      </div>

      {activeView === "bandeja" ? (
        <RevisionInbox onSelectEntrega={setSelectedEntregaId} />
      ) : (
        <AdminEditRequestList
          onViewPlanning={(req) => {
            if (req.entrega_id) {
              setSelectedEntregaId(req.entrega_id);
            }
          }}
        />
      )}
    </div>
  );
}
