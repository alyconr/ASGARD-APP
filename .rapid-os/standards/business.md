# Business Constitution
## Proyecto: Aplicación web para construcción de guías de aprendizaje SENA
## Fase activa: Fase 1
## Estado: Reglas obligatorias para implementación

---

# 1. Propósito del proyecto

Este proyecto construye la Fase 1 de una aplicación web para el equipo pedagógico del SENA.

La Fase 1 tiene como objetivo capturar, revisar, editar y validar la información base del:

- programa de formación,
- proyecto formativo,

para dejar preparada la estructura necesaria para la futura construcción de guías de aprendizaje.

La Fase 1 NO genera todavía la guía final.

---

# 2. Resultado de negocio esperado

El sistema debe permitir que un usuario gestor pedagógico:

1. cargue o diligencie el programa de formación,
2. capture competencias y su estructura curricular,
3. revise y cierre el programa,
4. cargue o diligencie el proyecto formativo,
5. capture fases y actividades,
6. revise y cierre el proyecto,
7. deje toda la información validada y persistida para fases posteriores.

---

# 3. Regla principal del dominio

El proyecto formativo depende obligatoriamente del programa de formación.

## Regla crítica
NO se puede habilitar, crear ni cerrar el proyecto formativo mientras el programa de formación no esté completo y revisado.

---

# 4. Alcance obligatorio de Fase 1

La Fase 1 SÍ incluye:

- cargue del programa de formación,
- cargue del proyecto formativo,
- flujo tipo wizard,
- extracción híbrida desde PDF,
- fallback manual,
- guardado automático en borrador,
- revisión consolidada editable,
- validación de completitud,
- bloqueo y desbloqueo del proyecto,
- auditoría básica,
- pruebas mínimas.

La Fase 1 NO incluye:

- generación automática de la guía de aprendizaje,
- exportación a PDF,
- exportación a DOCX,
- versionamiento avanzado,
- roles complejos,
- aprobaciones institucionales,
- panel administrativo avanzado,
- integraciones externas.

---

# 5. Flujo obligatorio de UX

La experiencia principal debe implementarse como un wizard.

El flujo obligatorio es:

1. iniciar nuevo proceso o continuar borrador,
2. cargar o diligenciar programa,
3. extraer información si el PDF es legible,
4. completar manualmente lo faltante,
5. gestionar competencias y estructura curricular,
6. revisar y cerrar programa,
7. habilitar proyecto,
8. cargar o diligenciar proyecto,
9. extraer información si el PDF es legible,
10. completar manualmente lo faltante,
11. gestionar fases y actividades,
12. revisar y cerrar proyecto.

No se deben crear flujos alternos que rompan esta secuencia.

---

# 6. Reglas obligatorias de persistencia

## Guardado automático
Todo avance del usuario debe guardarse automáticamente.

## El borrador debe conservar
- datos ingresados manualmente,
- datos extraídos automáticamente,
- campos pendientes,
- paso actual del wizard,
- estado del bloque.

## Restricción
Nunca se debe perder el trabajo del usuario al cambiar de paso, refrescar o retomar una sesión.

---

# 7. Reglas obligatorias de extracción híbrida

El sistema debe soportar dos modos:

- extracción automática desde PDF,
- diligenciamiento manual.

## Regla de fallback
Si el PDF no es legible, está escaneado o no permite extracción confiable, el sistema debe habilitar el ingreso manual inmediato.

## Regla de extracción parcial
Si solo se detectan algunos campos:
- conservar los datos extraídos,
- marcar los faltantes,
- mostrar motivo del fallo,
- permitir edición manual.

## Regla crítica
La extracción automática NO equivale a validación humana.

Todo dato extraído debe ser revisado por el usuario antes del cierre.

---

# 8. Reglas obligatorias del programa de formación

## Datos mínimos del programa
- código del programa,
- nombre del programa.

## Estructura mínima por competencia
Cada competencia debe tener:
- código,
- nombre,
- al menos un resultado de aprendizaje,
- al menos un conocimiento de saber,
- al menos un conocimiento de proceso,
- al menos un criterio de evaluación.

## Cierre del programa
El programa solo puede pasar a estado COMPLETO cuando:
- tiene datos mínimos,
- tiene competencias,
- cada competencia cumple estructura mínima,
- el usuario revisa y confirma el consolidado.

---

# 9. Reglas obligatorias del proyecto formativo

## Datos mínimos del proyecto
- código del proyecto,
- nombre del proyecto,
- versión del proyecto,
- al menos una fase,
- al menos una actividad por fase.

## Regla estructural
Toda actividad debe pertenecer a una fase.

## Cierre del proyecto
El proyecto solo puede pasar a estado COMPLETO cuando:
- el programa ya está COMPLETO,
- el proyecto tiene datos mínimos,
- tiene fases válidas,
- cada fase tiene actividades,
- el usuario revisa y confirma el consolidado.

---

# 10. Estados obligatorios del sistema

## Programa
- BORRADOR
- EN_REVISION
- COMPLETO

## Proyecto
- BLOQUEADO
- BORRADOR
- EN_REVISION
- COMPLETO

## Restricción
La lógica de estados debe estar centralizada y no dispersa en múltiples lugares inconsistentes.

---

# 11. Reglas de validación obligatorias

No permitir:

- programas duplicados según política definida,
- competencias duplicadas dentro del mismo programa,
- resultados duplicados dentro de la misma competencia,
- conocimientos duplicados dentro de la misma categoría y competencia,
- criterios duplicados dentro de la misma competencia,
- actividades duplicadas dentro de la misma fase,
- hijos sin padre relacional,
- cierre de bloques incompletos.

---

# 12. Reglas de revisión obligatoria

Antes de marcar un bloque como completo, el sistema debe mostrar una vista consolidada editable.

La vista consolidada debe permitir:
- revisar,
- corregir,
- agregar,
- borrar con confirmación,
- identificar origen del dato:
  - extraído,
  - manual,
  - corregido,
  - pendiente.

---

# 13. Impacto de cambios posteriores

Si un programa ya completo es modificado y deja de cumplir la estructura mínima:

- debe regresar a EN_REVISION,
- el sistema debe advertir el impacto sobre el proyecto asociado,
- el proyecto no debe considerarse confiable sin nueva revisión.

---

# 14. Stack permitido

El agente debe trabajar bajo estas restricciones técnicas:

- Frontend: Next.js + React + TypeScript + Tailwind CSS
- Backend: FastAPI
- Base de datos: PostgreSQL
- Arquitectura: modular por dominio
- Validación: explícita y cercana al dominio
- Testing: unitario, integración y end-to-end mínimo

## Restricción
No introducir stacks alternativos sin instrucción explícita.

No migrar a Supabase, NestJS, Django, Express u otros frameworks sin autorización explícita.

---

# 15. Estrategia obligatoria de implementación

La aplicación NO debe construirse de una sola vez.

Debe implementarse:

- módulo por módulo,
- tarea por tarea,
- respetando orden de dependencias,
- empezando por datos, borradores y programa,
- y dejando el proyecto para después del cierre del programa.

## Orden recomendado
1. modelo de datos,
2. borradores,
3. wizard del programa,
4. extracción del programa,
5. CRUD curricular,
6. cierre del programa,
7. bloqueo/desbloqueo del proyecto,
8. wizard del proyecto,
9. extracción del proyecto,
10. CRUD de fases y actividades,
11. cierre del proyecto,
12. auditoría y pruebas.

---

# 16. Restricciones de comportamiento del agente

El agente NO debe:

- implementar fuera de Fase 1,
- crear funcionalidades no definidas,
- asumir que un campo extraído ya fue validado,
- permitir proyecto sin programa completo,
- mezclar conocimientos de saber y proceso,
- saltarse el wizard,
- ignorar borradores,
- eliminar reglas del dominio por conveniencia técnica.

El agente SÍ debe:

- respetar los documentos fuente del proyecto,
- reportar ambigüedades,
- mantener trazabilidad,
- construir con incrementalidad,
- priorizar consistencia de negocio sobre velocidad.

---

# 17. Orden de lectura obligatorio para el agente

Antes de implementar cualquier módulo, leer en este orden:

1. /docs/01-business-rules/BUSINESS_RULES.md
2. /docs/02-specs/SPECS.md
3. /docs/03-user-stories/USER_STORIES.md
4. /docs/04-traceability/TRACEABILITY_MATRIX.md
5. /docs/05-architecture/DATA_MODEL.md
6. /docs/06-implementation/IMPLEMENTATION_PLAN.md
7. /docs/06-implementation/CODEX_TASKS.md

Si existe conflicto, manda primero:
- BUSINESS_RULES.md
- luego SPECS.md
- luego DATA_MODEL.md
- luego el resto.

---

# 18. Definición operativa de éxito en esta fase

La Fase 1 se considera exitosa cuando:

- el programa puede cargarse manualmente o desde PDF,
- el programa puede revisarse y cerrarse,
- el proyecto permanece bloqueado hasta ese momento,
- el proyecto puede cargarse manualmente o desde PDF,
- el proyecto puede revisarse y cerrarse,
- todo el avance se guarda en borrador,
- toda la información queda persistida y trazable.