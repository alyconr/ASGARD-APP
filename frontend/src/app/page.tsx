const checkpoints = [
  "Frontend desacoplado en Next.js con App Router",
  "Backend listo para consumir API REST",
  "Configuracion base para PostgreSQL por backend",
];

const modules = [
  "programa",
  "proyecto",
  "drafts",
  "upload",
];

export default function HomePage(): React.JSX.Element {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-8 px-6 py-12 lg:px-10">
      <section className="overflow-hidden rounded-[2rem] border border-[var(--card-border)] bg-[var(--card)] shadow-[0_30px_80px_rgba(17,33,58,0.12)] backdrop-blur">
        <div className="grid gap-10 px-8 py-10 lg:grid-cols-[1.4fr_0.9fr] lg:px-10 lg:py-12">
          <div className="space-y-6">
            <span className="inline-flex rounded-full bg-[var(--accent-soft)] px-4 py-1 text-sm font-medium text-[var(--accent)]">
              Fase 1 - Base tecnica inicial
            </span>
            <div className="space-y-3">
              <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-balance lg:text-5xl">
                Estructura lista para construir el flujo de programa y proyecto
                sin adelantar logica de negocio.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-[var(--muted)] lg:text-lg">
                Esta pantalla valida que el frontend levanta correctamente y que
                la base del repositorio quedo preparada para continuar con las
                siguientes tareas de la Fase 1.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {checkpoints.map((checkpoint) => (
                <article
                  key={checkpoint}
                  className="rounded-2xl border border-[var(--card-border)] bg-white/80 p-4"
                >
                  <p className="text-sm leading-6 text-[var(--foreground)]">
                    {checkpoint}
                  </p>
                </article>
              ))}
            </div>
          </div>

          <aside className="rounded-[1.75rem] border border-[var(--card-border)] bg-[#11213a] p-6 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
            <div className="space-y-4">
              <p className="text-sm uppercase tracking-[0.24em] text-white/60">
                Estructura modular
              </p>
              <ul className="grid gap-3">
                {modules.map((moduleName) => (
                  <li
                    key={moduleName}
                    className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3"
                  >
                    <span className="font-medium capitalize">{moduleName}</span>
                    <span className="text-sm text-white/65">Preparado</span>
                  </li>
                ))}
              </ul>
              <div className="rounded-2xl bg-white/8 p-4 text-sm leading-6 text-white/75">
                API base esperada en
                {" "}
                <code className="rounded bg-white/10 px-2 py-1 text-white">
                  NEXT_PUBLIC_API_BASE_URL
                </code>
                .
              </div>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}
