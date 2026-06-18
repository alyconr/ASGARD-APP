import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { ProgramaWizardShell } from "@/features/programa/components/programa-wizard-shell";

export default function ProgramaPage(): React.JSX.Element {
  return (
    <>
      <div className="mx-auto w-full max-w-7xl px-5 pt-6 lg:px-8">
        <Link
          href="/"
          className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-[color:var(--card-border)] bg-white px-3 py-1.5 text-xs font-semibold text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)]"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Volver al dashboard
        </Link>
      </div>
      <ProgramaWizardShell />
    </>
  );
}
