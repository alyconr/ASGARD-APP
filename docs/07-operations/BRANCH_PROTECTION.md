# Guía Operacional: Protección de Ramas (Branch Protection) en ASGARD-APP

> [!IMPORTANT]
> Este documento define la **configuración recomendada de protección de ramas** para el repositorio `alyconr/ASGARD-APP` en GitHub.
> Esta configuración **no se aplica automáticamente por archivos en el repositorio**; debe ser configurada manualmente por el administrador de la organización o repositorio en la interfaz de GitHub (`Settings -> Branches -> Branch protection rules`) o vía GitHub API con tokens administrativos apropiados.

---

## 1. Rama `main` (Producción)

La rama `main` representa el estado productivo y canónico del sistema. Ningún cambio directo está permitido.

### Reglas Requeridas en GitHub
1. **Require a pull request before merging**:
   - **Require approvals**: Al menos 1 aprobación requerida por pares / revisor técnico.
   - **Dismiss stale pull request approvals when new commits are pushed**: Habilitado.
   - **Require review from Code Owners**: Opcional / Recomendado.
2. **Require status checks to pass before merging**:
   - Require branches to be up to date before merging: Habilitado.
   - **Checks obligatorios**:
     - `Verify ASGARD Repository Context` (definido en `.github/workflows/repository-guard.yml`)
     - Pruebas backend (`pytest`)
     - Typecheck frontend (`tsc --noEmit`)
     - Build de producción frontend (`next build`)
3. **Do not allow bypassing the above settings**: Habilitado (incluso administradores deben usar PR para trazabilidad).
4. **Restrict pushes that create matching branches**: Habilitado.
5. **Lock branch**: Deshabilitado (para permitir merges mediante PRs aprobados).
6. **Do not allow force pushes**: Habilitado (estrictamente prohibido `git push --force`).
7. **Do not allow deletions**: Habilitado (la rama `main` no puede ser eliminada).

---

## 2. Rama `develop` (Integración Continua)

La rama `develop` es la rama de trabajo e integración principal para agentes y desarrolladores.

### Reglas Requeridas en GitHub
1. **Require status checks to pass before merging / pushing**:
   - Require branches to be up to date before merging: Habilitado.
   - **Checks obligatorios**:
     - `Verify ASGARD Repository Context`
     - Test suite backend y frontend
2. **Do not allow force pushes**: Habilitado (prohibido `git push --force` para evitar reescritura de historial compartido).
3. **Do not allow deletions**: Habilitado.
4. **Require a pull request before merging**:
   - Recomendado para contribuciones de agentes y colaboradores (`feature/*`, `fix/*`, `chore/*` -> `develop`).

---

## 3. Matriz de Permisos para Agentes de Desarrollo

| Rama / Patrón | Modificación Directa por Agente | Vía Pull Request | Estado de Guardrail Técnico |
| :--- | :---: | :---: | :--- |
| `main` | ❌ Bloqueado | ❌ (Solo vía develop) | Aborto automático por `assert_asgard_context.py` |
| `develop` | ⚠️ Solo integración controlada | ✅ Recomendado | Aceptado por guardrail |
| `feature/*` | ✅ Permitido | ✅ Recomendado | Aceptado por guardrail |
| `fix/*` | ✅ Permitido | ✅ Recomendado | Aceptado por guardrail |
| `chore/*` | ✅ Permitido | ✅ Recomendado | Aceptado por guardrail |
| `test/*` | ✅ Permitido | ✅ Recomendado | Aceptado por guardrail |
| `docs/*` | ✅ Permitido | ✅ Recomendado | Aceptado por guardrail |

---

## 4. Auditoría de Estado

- **Estado actual de la protección**: Documentada.
- **Acción requerida del administrador humano**: Acceder a `https://github.com/alyconr/ASGARD-APP/settings/branches` y agregar las reglas listadas anteriormente para `main` y `develop`.
