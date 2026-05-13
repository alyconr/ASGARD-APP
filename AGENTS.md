# AGENTS.md
# SOURCE OF TRUTH FOR CODEX INSIDE THIS REPOSITORY

## Proyecto
Aplicación web para construcción de guías de aprendizaje SENA

## Fase activa
Fase 1

## Propósito operativo
Implementar únicamente la Fase 1 del sistema para capturar, revisar, editar y validar la información base del programa de formación y del proyecto formativo.

## Decision funcional TASK-08.5
A partir de TASK-08.5, toda mencion anterior a extraccion hibrida desde PDF queda reemplazada para el programa de formacion por esta estrategia:

- el PDF se carga, valida de forma basica, diagnostica y conserva solo como evidencia documental en MinIO;
- el PDF no se usa como fuente activa para extraer ni prellenar informacion curricular;
- el Excel canonico `.xlsx` es la fuente estructurada para analizar, validar, previsualizar e importar programa, competencias, resultados, conocimientos y criterios;
- la organizacion curricular base de la importacion Excel es por competencia: Competencia -> Resultados, Competencia -> Conocimientos y Competencia -> Criterios;
- conocimientos y criterios se asocian inicialmente a la competencia; `resultado_id` es opcional y secundario para uso posterior;
- solo quedan pendientes de conciliacion los conocimientos o criterios que no puedan asociarse a una competencia de forma confiable;
- la importacion Excel debe usar el `referencia_id` estable del wizard y no debe crear un flujo nuevo.

---

# 1. Prioridad de instrucciones

Si existe conflicto entre este archivo, una skill, MCP, o cualquier otro contexto, Codex debe obedecer en este orden:

1. `AGENTS.md`
2. `/docs/01-business-rules/BUSINESS_RULES.md`
3. `/docs/02-specs/SPECS.md`
4. `/docs/05-architecture/DATA_MODEL.md`
5. `/docs/03-user-stories/USER_STORIES.md`
6. `/docs/04-traceability/TRACEABILITY_MATRIX.md`
7. `/docs/06-implementation/IMPLEMENTATION_PLAN.md`
8. `/docs/06-implementation/CODEX_TASKS.md`
9. Skills invocadas en el hilo
10. MCPs configurados en el entorno

Las skills y los MCP nunca pueden sobreescribir reglas del proyecto.

---

# 2. Orden de lectura obligatorio

Antes de implementar cualquier tarea, leer en este orden:

1. `/docs/01-business-rules/BUSINESS_RULES.md`
2. `/docs/02-specs/SPECS.md`
3. `/docs/03-user-stories/USER_STORIES.md`
4. `/docs/04-traceability/TRACEABILITY_MATRIX.md`
5. `/docs/05-architecture/DATA_MODEL.md`
6. `/docs/06-implementation/IMPLEMENTATION_PLAN.md`
7. `/docs/06-implementation/CODEX_TASKS.md`

No asumir requisitos fuera de esos documentos.

---

# 3. Stack permitido

## Frontend
- Next.js 14+ o superior
- React
- TypeScript en modo estricto
- Tailwind CSS

## Backend
- FastAPI
- Python tipado estrictamente

## Base de datos
- PostgreSQL

## Persistencia y migraciones
- SQLAlchemy
- Alembic

## Testing
- Frontend: pruebas mínimas razonables cuando aplique
- Backend: pytest
- Validar lint, tipado y pruebas antes de cerrar tareas relevantes

## Restricción
No introducir sin autorización explícita:
- React Three Fiber
- Drei
- GSAP
- Framer Motion
- Shadcn UI
- Radix UI
- Zustand
- TanStack Query
- Supabase
- NestJS
- Django
- Express
- MongoDB
- GraphQL

Solo se permite agregar una librería nueva si:
1. resuelve una necesidad concreta de la tarea actual,
2. no contradice `/docs`,
3. y se reporta explícitamente en la entrega.

---

# 4. Topología obligatoria

## Arquitectura
- Frontend separado
- Backend separado
- Base de datos separada
- Comunicación por API HTTP

## Regla
El frontend nunca debe acceder directamente a la base de datos.  
Toda persistencia debe pasar por el backend.

---

# 5. Alcance estricto de Fase 1

La Fase 1 SÍ incluye:
- cargue del programa de formación,
- cargue del proyecto formativo,
- flujo tipo wizard,
- carga documental PDF como evidencia,
- importación estructurada desde Excel canónico,
- fallback manual,
- guardado automático en borrador,
- revisión consolidada editable,
- validación de completitud,
- bloqueo del proyecto hasta completar el programa,
- auditoría básica,
- pruebas mínimas.

La Fase 1 NO incluye:
- generación automática de la guía final,
- exportación a PDF,
- exportación a DOCX,
- versionamiento avanzado,
- roles complejos,
- autenticación avanzada no definida en `/docs`,
- aprobaciones institucionales,
- panel administrativo avanzado,
- integraciones externas.

---

# 6. Reglas críticas del dominio

## Dependencia principal
El proyecto formativo depende obligatoriamente del programa de formación.

## Regla crítica
No crear, habilitar ni cerrar el proyecto formativo mientras el programa de formación no esté completo y revisado.

## Flujo obligatorio
La UX principal debe implementarse como wizard y respetar esta secuencia:

1. iniciar nuevo proceso o continuar borrador,
2. cargar o diligenciar programa,
3. cargar PDF solo como evidencia cuando exista,
4. cargar, validar y previsualizar Excel canónico cuando se use fuente estructurada,
5. confirmar importación estructurada o completar manualmente lo faltante,
6. gestionar competencias y estructura curricular,
7. revisar y cerrar programa,
8. habilitar proyecto,
9. cargar o diligenciar proyecto,
10. completar manualmente lo faltante,
11. gestionar fases y actividades,
12. revisar y cerrar proyecto.

No crear flujos alternos que rompan esta secuencia.

---

# 7. Reglas obligatorias de persistencia

- Todo avance del usuario debe guardarse automáticamente.
- El borrador debe conservar:
  - datos manuales,
  - datos extraídos,
  - campos pendientes,
  - paso actual,
  - estado del bloque.
- Nunca se debe perder el avance al cambiar de paso, refrescar o retomar sesión.

---

# 8. Reglas obligatorias de fuente documental e importacion

El sistema debe soportar:
- carga de PDF como evidencia documental en MinIO,
- importacion estructurada desde Excel canonico `.xlsx`,
- diligenciamiento manual.

## Regla crítica
La carga documental o la importacion automatizada no equivalen a validacion humana sin revision del usuario.

## Regla de organizacion curricular
La importacion Excel debe organizar la estructura principalmente por competencia.
Los resultados se relacionan con la competencia. Los conocimientos y criterios
tambien se relacionan inicialmente con la competencia, aunque no tengan `rap_id`
o no pueda resolverse un resultado especifico. La asignacion posterior a un
resultado es opcional y secundaria.

## Regla de fallback
Si el Excel canonico falta, no cumple contrato o no permite importacion confiable:
- conservar la metadata del intento y errores de validacion,
- marcar faltantes,
- informar motivo,
- habilitar ingreso manual inmediato.

---

# 9. Estados obligatorios

## Programa
- BORRADOR
- EN_REVISION
- COMPLETO

## Proyecto
- BLOQUEADO
- BORRADOR
- EN_REVISION
- COMPLETO

La lógica de estados debe estar centralizada y no dispersa.

---

# 10. Estrategia obligatoria de implementación

La aplicación no debe construirse de una sola vez.

Debe implementarse:
- módulo por módulo,
- tarea por tarea,
- respetando dependencias,
- sin adelantarse a tareas futuras.

## Orden recomendado
1. modelo de datos
2. borradores
3. wizard del programa
4. extracción del programa
5. CRUD curricular
6. cierre del programa
7. bloqueo/desbloqueo del proyecto
8. wizard del proyecto
9. extracción del proyecto
10. CRUD de fases y actividades
11. cierre del proyecto
12. auditoría y pruebas

---

# 11. Restricciones de comportamiento de Codex

Codex NO debe:
- implementar fuera de Fase 1,
- crear funcionalidades no definidas,
- asumir que un dato extraído ya fue validado,
- permitir proyecto sin programa completo,
- mezclar conocimientos de saber y proceso,
- saltarse el wizard,
- ignorar borradores,
- cambiar el stack sin permiso,
- adelantar lógica de cierre o completitud antes de la tarea correspondiente.

Codex SÍ debe:
- respetar el orden de lectura,
- reportar ambigüedades,
- mantener trazabilidad,
- entregar soluciones incrementales,
- priorizar consistencia del dominio sobre velocidad.

---

# 12. Regla de skills en Codex

Si en una tarea se invoca una skill usando `$skill-name`, Codex debe seguir estas reglas:

1. La skill actúa como guía de proceso o playbook.
2. La skill no puede contradecir `AGENTS.md` ni los archivos de `/docs`.
3. Si la skill sugiere librerías, componentes o patrones no aprobados, Codex debe ignorarlos y reportarlo.
4. Las skills de frontend solo deben ayudar en:
   - estructura visual,
   - composición de componentes,
   - patrones de navegación,
   - feedback visual,
   - consistencia de UI.
5. Las skills no deben introducir por sí solas:
   - nuevas librerías,
   - nuevos dominios,
   - cambios de arquitectura,
   - lógica fuera de la tarea actual.

## Regla práctica
Si una tarea menciona una skill de diseño frontend, Codex debe:
- aplicar la skill solo al aspecto visual y estructural de la UI,
- obedecer primero este archivo y `/docs`,
- mantenerse dentro de la tarea actual.

---

# 13. Regla de MCPs

Si existe un MCP configurado, Codex puede usarlo solo como herramienta auxiliar.

## MCP de PostgreSQL
- puede usarse para inspeccionar tablas,
- validar estado del esquema,
- revisar relaciones,
- confirmar resultados de migraciones.

## Restricción
El MCP no reemplaza:
- SQLAlchemy,
- Alembic,
- el modelo definido en `DATA_MODEL.md`,
- ni las reglas del dominio.

## Regla práctica
Los MCPs sirven para inspección, validación y apoyo operativo.  
No deben convertirse en la fuente de verdad del proyecto.

---

# 14. Regla específica para tareas con wizard y borradores

Cuando una tarea implemente wizard y borradores:

- debe usar un `referencia_id` UUID estable desde el inicio del flujo,
- debe reutilizarlo en autosave y recuperación,
- no debe generar un UUID nuevo por paso,
- debe permitir continuar borrador con el mismo identificador lógico.

---

# 15. Seguridad mínima

- Nunca commitear `.env`
- Nunca concatenar SQL manual si existe capa ORM
- No loggear PII sensible en texto plano
- No introducir autenticación o JWT antes de que una tarea y `/docs` lo requieran explícitamente

---

# 16. Estándares de código

- TypeScript estricto
- Python tipado
- No usar `any` sin justificación explícita
- Mantener código modular y legible
- Toda entrega debe explicar:
  - qué cambió,
  - qué archivos tocó,
  - qué validaciones implementó,
  - qué dejó listo para la siguiente tarea

## Testing
No cerrar tareas relevantes sin pruebas mínimas razonables.  
La cobertura estricta se evalúa por hito o sprint, no como requisito rígido para bloquear cualquier tarea de infraestructura.

## Documentación
- Los métodos públicos importantes deben tener docstrings o documentación breve cuando aporte claridad.
- No agregar documentación ceremonial innecesaria.

---

# 17. Definición operativa de éxito de Fase 1

La Fase 1 se considera exitosa cuando:
- el programa puede cargarse manualmente o desde Excel canonico,
- el PDF del programa puede conservarse como evidencia documental,
- el programa puede revisarse y cerrarse,
- el proyecto permanece bloqueado hasta ese momento,
- el proyecto puede cargarse manualmente o mediante fuente estructurada definida antes de su tarea,
- el proyecto puede revisarse y cerrarse,
- todo el avance se guarda en borrador,
- toda la información queda persistida y trazable.
