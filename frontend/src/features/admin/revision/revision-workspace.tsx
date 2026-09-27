"use client";

import React, { useState } from "react";
import { RevisionInbox } from "./revision-inbox";
import { RevisionDetailView } from "./revision-detail-view";

export function RevisionWorkspace(): React.JSX.Element {
  const [selectedEntregaId, setSelectedEntregaId] = useState<string | null>(null);

  if (selectedEntregaId) {
    return (
      <RevisionDetailView
        entregaId={selectedEntregaId}
        onBack={() => setSelectedEntregaId(null)}
      />
    );
  }

  return <RevisionInbox onSelectEntrega={setSelectedEntregaId} />;
}
