# Landing pública ASGARD

Solicitud del 21 de septiembre de 2026. Esta decisión sustituye exclusivamente la ubicación anterior del dashboard en `/`: la entrada pública es ahora la landing y el panel operativo se conserva en `/dashboard`.

## Implementación

- `app/page.tsx` conserva el render de ruta en servidor, define metadata del producto y carga Plus Jakarta Sans y Caveat mediante `next/font/google`, con variables limitadas a la landing.
- `LandingPage` compone navegación, hero, imagen, capacidades y un pie de orientación breve. CSS Modules aísla el diseño de los wizards y del dashboard.
- `app/dashboard/page.tsx` renderiza el mismo `MasterDashboard`, sin duplicar ni modificar su implementación.
- Los enlaces explícitos de retorno al panel desde programa, proyecto, planeación y el asistente guiado apuntan a `/dashboard`.
- Se reutilizan el `AuthProvider` global, `useAuth`, `LoginDialog` y `ForceChangePasswordDialog`. Ambos botones de entrada abren el login existente para visitantes; los usuarios autenticados acceden al panel. La navegación posterior al login espera el cambio obligatorio de contraseña cuando corresponde.
- `Ver cómo funciona` desplaza a `#proceso`, con movimiento instantáneo cuando el usuario prefiere movimiento reducido.
- Las formas orgánicas, curva SVG, partículas, luces y tarjetas usan animaciones CSS lentas con diferentes duraciones. `prefers-reduced-motion` las desactiva.
- No se añadieron dependencias de aplicación ni se modificaron backend, contratos HTTP, persistencia, gates curriculares o lógica de los wizards.

## Referencia y ajustes visuales

La figura se obtuvo mediante edición de la imagen adjunta para aislar la instructora sobre transparencia. Conserva los elementos visuales solicitados, pero es una extracción asistida por generación y no un recorte idéntico píxel a píxel. El logo ASGARD es SVG propio, los iconos son Lucide y toda la interfaz y las tarjetas son HTML real. No se utiliza el screenshot completo como fondo.

Se revisaron dos pasadas de composición en escritorio y móvil. Se amplió la instructora, se reubicó la checklist para despejar el rostro en pantallas estrechas y se ajustaron los cinco bloques inferiores para evitar recortes en tablet. Los textos secundarios manuscritos usan Caveat; no reproducen exactamente el trazo de la referencia. Se omite la búsqueda opcional, que no tiene funcionalidad definida.

## Validación local

- Preflight: `ASGARD context OK`; rama `develop`, repositorio `alyconr/ASGARD-APP`. Actualización fast-forward: ya estaba actualizado.
- Lint: sin errores; seis advertencias preexistentes en administración, revisión de programa y wizard de proyecto.
- TypeScript: `npm run typecheck -- --incremental false` aprobado. La primera ejecución sin ese argumento no pudo escribir la caché por permisos de Windows.
- Suite completa: `npm test -- --pool=forks --maxWorkers=2`: **25 archivos, 144 pruebas aprobadas**. El pool de threads falló en Windows. El mock de usuario de las pruebas del dashboard se estabilizó para evitar recargas infinitas causadas por una identidad nueva en cada render.
- Navegador: `PLAYWRIGHT_TEST_BASE_URL=http://localhost:3001 npm run test:e2e -- e2e/landing.spec.ts`: **6 pruebas aprobadas**. Incluye 1440×900, 1920×1080, 390×844 y 820×1180, carga del retrato, ausencia de overflow horizontal, cinco capacidades, movimiento reducido, ancla de proceso, ambos botones de login y acceso al panel.
- Las pruebas de navegador de esta landing simulan una sesión anónima. No constituyen validación E2E del backend, RBAC ni del flujo curricular real. Las suites anteriores que requieren usuarios/datos reales no se ejecutaron.
- Compilación de producción: `npm run build` aprobado con Next.js 15.5.15. Genera `/` y `/dashboard` como rutas independientes; conserva `/programa`, `/proyecto/[referencia_id]` y `/planeacion/[referencia_id]`.
- Capturas locales: `frontend/test-results/landing-1440.png`, `landing-1920.png`, `landing-390.png` y `landing-820.png` (artefactos ignorados por Git).

## Archivos creados

```text
docs/06-implementation/LANDING_ASGARD.md
frontend/e2e/landing.spec.ts
frontend/public/landing/asgard-instructor.png
frontend/src/app/dashboard/page.tsx
frontend/src/app/routes.test.tsx
frontend/src/features/landing/landing-page.tsx
frontend/src/features/landing/landing-header.tsx
frontend/src/features/landing/hero-visual.tsx
frontend/src/features/landing/hero-feature-strip.tsx
frontend/src/features/landing/landing.module.css
frontend/src/features/landing/landing-page.test.tsx
```

## Archivos modificados

```text
.gitignore
frontend/e2e/curricular-flow.spec.ts
frontend/src/app/page.tsx
frontend/src/app/programa/page.tsx
frontend/src/app/proyecto/[referencia_id]/page.tsx
frontend/src/app/planeacion/[referencia_id]/page.tsx
frontend/src/features/dashboard/master-dashboard.test.tsx
frontend/src/features/guide/wizard-guide-engine.ts
frontend/src/features/guide/wizard-guide-engine.test.ts
```

## Publicación

No se ha realizado commit, push ni merge. La publicación y comprobación de `https://asgard-dev.datasena.com` requieren identificar el mecanismo de despliegue del entorno. El repositorio aporta `docker-compose.staging.yml`, pero no un pipeline de publicación ni un destino remoto operativo documentado. El criterio de aceptación sobre esa URL permanece pendiente.
