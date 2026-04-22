# CODEX_TASKS.md
## Proyecto: Aplicación web para construcción de guías de aprendizaje SENA
## Fase: 1
## Estado: Tareas listas para ejecución incremental con Codex
## Última actualización: [YYYY-MM-DD]

---

# 1. Propósito

Este documento divide la implementación de la Fase 1 en tareas pequeñas, ordenadas y trazables para ejecutar con Codex.

Cada tarea debe resolverse de forma incremental y verificable.  
Codex no debe saltarse tareas ni mezclar varias iteraciones grandes en una sola entrega.

---

# 2. Instrucción general para todas las tareas

Antes de ejecutar cualquier tarea, Codex debe leer:

1. `/docs/01-business-rules/BUSINESS_RULES.md`
2. `/docs/02-specs/SPECS.md`
3. `/docs/03-user-stories/USER_STORIES.md`
4. `/docs/04-traceability/TRACEABILITY_MATRIX.md`
5. `/docs/05-architecture/DATA_MODEL.md`
6. `/docs/06-implementation/IMPLEMENTATION_PLAN.md`

Reglas generales:

- no inventar requisitos,
- no salir del alcance de Fase 1,
- reportar ambigüedades,
- mantener consistencia con estados y reglas de negocio,
- hacer entregas modulares,
- incluir validaciones mínimas,
- no romper lo ya implementado.

---

# 3. Tareas

## TASK-01. Crear la base del proyecto

### Objetivo
Preparar la estructura inicial del repositorio y el entorno de desarrollo.

### Debe hacer
- crear estructura base de frontend y backend,
- configurar dependencias principales,
- configurar lint y formato,
- crear variables de entorno iniciales,
- dejar el proyecto ejecutándose localmente.

### Debe entregar
- estructura de carpetas inicial,
- archivo de configuración del proyecto,
- README técnico mínimo de arranque.

### No debe hacer
- implementar lógica de negocio aún,
- crear módulos funcionales completos.

### Aceptación
- frontend levanta,
- backend levanta,
- base de datos puede configurarse,
- proyecto compila sin errores base.

---

## TASK-02. Implementar modelo de datos y migraciones

### Objetivo
Construir el esquema de datos inicial conforme a `DATA_MODEL.md`.

### Debe hacer
- crear modelos/tablas:
  - ProgramaFormacion
  - Competencia
  - ResultadoAprendizaje
  - Conocimiento
  - CriterioEvaluacion
  - ProyectoFormativo
  - FaseProyecto
  - ActividadProyecto
  - BorradorSesion
  - EventoAuditoria
- crear enums,
- crear migración inicial,
- crear restricciones e índices básicos.

### Debe entregar
- modelos ORM,
- migración funcional,
- script de seed opcional mínimo si aplica.

### No debe hacer
- implementar aún el wizard,
- crear interfaces completas de usuario.

### Aceptación
- la migración corre correctamente,
- las relaciones están bien definidas,
- las restricciones principales existen,
- el esquema respeta `DATA_MODEL.md`.

---

## TASK-03. Implementar servicio de borradores

### Objetivo
Garantizar persistencia automática del avance.

### Debe hacer
- crear servicio de autosave,
- crear endpoint o método para guardar borrador,
- crear recuperación de borrador,
- persistir `paso_actual`,
- persistir `payload_json`.

### Debe entregar
- servicio de borradores,
- contratos de entrada/salida,
- pruebas mínimas del servicio.

### No debe hacer
- cerrar bloques todavía,
- asumir que un borrador implica completitud.

### Aceptación
- el borrador puede guardarse,
- el borrador puede recuperarse,
- se conserva el paso actual,
- se conserva información parcial.

---

## TASK-04. Construir wizard base del programa

### Objetivo
Crear la navegación inicial del programa de formación.

### Debe hacer
- crear el flujo wizard del programa,
- permitir iniciar nuevo proceso,
- permitir continuar borrador,
- permitir retroceder y avanzar,
- mostrar progreso por pasos,
- integrar autosave.

### Debe entregar
- UI base del wizard,
- componentes de navegación,
- integración con borradores.

### No debe hacer
- implementar todavía el módulo curricular completo.

### Aceptación
- el usuario puede iniciar el proceso,
- puede navegar sin perder información,
- puede retomar un borrador existente.

---

## TASK-05. Implementar formulario base del programa

### Objetivo
Capturar los datos mínimos del programa.

### Debe hacer
- crear formulario para:
  - código del programa,
  - nombre del programa,
  - versión si aplica,
- validar obligatorios,
- guardar como borrador.

### Debe entregar
- formulario funcional,
- validaciones de campos mínimos,
- persistencia conectada.

### No debe hacer
- permitir cierre del programa aún.

### Aceptación
- no se puede guardar como completo con campos vacíos,
- sí se puede guardar en borrador con avance parcial,
- los datos se recuperan correctamente.

---

## TASK-06. Implementar carga y diagnóstico de PDF del programa

### Objetivo
Permitir subir un PDF del programa y evaluar si es legible.

### Debe hacer
- implementar carga de archivo PDF,
- validar formato,
- analizar si el PDF tiene texto extraíble,
- clasificar como:
  - legible,
  - parcialmente legible,
  - no legible.

### Debe entregar
- endpoint/controlador de carga,
- servicio de diagnóstico,
- respuesta estructurada con estado de legibilidad.

### No debe hacer
- extracción avanzada completa en esta tarea.

### Aceptación
- el sistema acepta PDF válido,
- el sistema rechaza formatos no válidos,
- el sistema devuelve diagnóstico legible/parcial/no legible.

---

## TASK-07. Implementar extracción híbrida del programa

### Objetivo
Extraer automáticamente los campos del programa cuando sea posible.

### Debe hacer
- extraer:
  - código del programa,
  - nombre del programa,
  - competencias,
  - resultados,
  - conocimientos de saber,
  - conocimientos de proceso,
  - criterios,
- marcar estado de cada campo,
- registrar motivo de fallo cuando no se pueda extraer,
- dejar listos los campos para revisión manual.

### Debe entregar
- servicio de extracción,
- estructura de respuesta por campo,
- integración con el wizard.

### No debe hacer
- asumir que lo extraído ya quedó validado.

### Aceptación
- los campos extraídos se prellenan,
- los campos faltantes quedan marcados,
- el usuario puede continuar con ingreso manual.

---

## TASK-08. Implementar CRUD de competencias

### Objetivo
Permitir registrar, editar y eliminar competencias del programa.

### Debe hacer
- crear endpoints y UI para competencias,
- validar código y nombre,
- impedir duplicados por código dentro del mismo programa,
- mantener integridad con programa.

### Debe entregar
- CRUD funcional de competencias,
- validaciones básicas,
- borrado con confirmación.

### No debe hacer
- mezclar resultados o conocimientos dentro de esta tarea.

### Aceptación
- se pueden crear varias competencias,
- no se aceptan competencias vacías,
- no se aceptan duplicados.

---

## TASK-09. Implementar CRUD de resultados de aprendizaje

### Objetivo
Permitir gestionar resultados por competencia.

### Debe hacer
- crear CRUD de resultados,
- asociarlos a competencia,
- validar descripción obligatoria,
- evitar duplicados exactos.

### Debe entregar
- endpoints y UI de resultados,
- validaciones básicas.

### Aceptación
- cada resultado queda ligado a una competencia,
- no se permiten vacíos ni duplicados.

---

## TASK-10. Implementar CRUD de conocimientos de saber

### Objetivo
Permitir gestionar conocimientos de tipo SABER.

### Debe hacer
- crear CRUD de conocimientos SABER,
- asociarlos a competencia,
- validar obligatorios,
- evitar duplicados.

### Debe entregar
- endpoints y UI de conocimientos SABER.

### Aceptación
- los conocimientos SABER se guardan correctamente,
- no se permiten duplicados ni vacíos.

---

## TASK-11. Implementar CRUD de conocimientos de proceso

### Objetivo
Permitir gestionar conocimientos de tipo PROCESO.

### Debe hacer
- crear CRUD de conocimientos PROCESO,
- asociarlos a competencia,
- validar obligatorios,
- evitar duplicados.

### Debe entregar
- endpoints y UI de conocimientos PROCESO.

### Aceptación
- los conocimientos PROCESO se guardan correctamente,
- no se permiten duplicados ni vacíos.

---

## TASK-12. Implementar CRUD de criterios de evaluación

### Objetivo
Permitir gestionar criterios por competencia.

### Debe hacer
- crear CRUD de criterios,
- asociarlos a competencia,
- validar descripción obligatoria,
- evitar duplicados exactos.

### Debe entregar
- endpoints y UI de criterios.

### Aceptación
- los criterios quedan ligados a la competencia,
- no se aceptan vacíos ni duplicados.

---

## TASK-13. Construir vista consolidada del programa

### Objetivo
Permitir revisar el programa completo antes del cierre.

### Debe hacer
- mostrar programa,
- mostrar competencias,
- mostrar resultados,
- mostrar conocimientos SABER,
- mostrar conocimientos PROCESO,
- mostrar criterios,
- indicar origen del dato:
  - extraído,
  - manual,
  - pendiente,
  - corregido.

### Debe entregar
- vista consolidada editable,
- navegación hacia correcciones.

### Aceptación
- el usuario puede revisar toda la estructura,
- el usuario puede volver a editar desde la vista consolidada.

---

## TASK-14. Implementar validador y cierre del programa

### Objetivo
Permitir marcar el programa como COMPLETO solo si cumple la estructura mínima.

### Debe hacer
- crear servicio validador de completitud,
- validar:
  - código,
  - nombre,
  - competencias,
  - resultados,
  - saber,
  - proceso,
  - criterios,
- crear acción explícita de confirmación,
- cambiar estado a COMPLETO.

### Debe entregar
- servicio de completitud,
- endpoint de cierre,
- mensajes de error por faltantes.

### Aceptación
- no se puede cerrar si falta estructura mínima,
- sí se puede cerrar cuando todo está completo,
- el estado cambia correctamente.

---

## TASK-15. Implementar bloqueo y desbloqueo del proyecto

### Objetivo
Respetar la dependencia del proyecto respecto al programa.

### Debe hacer
- bloquear módulo proyecto cuando programa no esté COMPLETO,
- mostrar mensaje explicativo en frontend,
- impedir acceso indebido desde backend,
- habilitar cuando programa esté COMPLETO.

### Debe entregar
- validación frontend,
- validación backend,
- mensaje de bloqueo.

### Aceptación
- el proyecto no puede iniciarse si el programa está incompleto,
- se habilita automáticamente al completar el programa.

---

## TASK-16. Construir wizard base del proyecto

### Objetivo
Crear el flujo principal del proyecto formativo.

### Debe hacer
- crear wizard del proyecto,
- integrar autosave,
- permitir navegación entre pasos,
- permitir continuar borrador.

### Debe entregar
- UI base del proyecto,
- integración con servicio de borradores.

### Aceptación
- el wizard del proyecto funciona solo si el programa está completo,
- el avance se guarda automáticamente.

---

## TASK-17. Implementar formulario base del proyecto

### Objetivo
Capturar los datos mínimos del proyecto.

### Debe hacer
- crear formulario para:
  - código del proyecto,
  - nombre del proyecto,
  - versión del proyecto,
- validar obligatorios,
- guardar en borrador.

### Debe entregar
- formulario funcional del proyecto,
- validaciones mínimas.

### Aceptación
- los campos mínimos se guardan,
- el borrador puede retomarse.

---

## TASK-18. Implementar carga y diagnóstico de PDF del proyecto

### Objetivo
Permitir subir el PDF del proyecto y evaluar legibilidad.

### Debe hacer
- carga de PDF,
- validación de archivo,
- diagnóstico de legibilidad,
- respuesta estructurada.

### Debe entregar
- endpoint de carga,
- servicio de diagnóstico.

### Aceptación
- el sistema clasifica correctamente el archivo,
- el usuario ve si podrá extraer o completar manualmente.

---

## TASK-19. Implementar extracción híbrida del proyecto

### Objetivo
Extraer automáticamente los datos del proyecto cuando sea posible.

### Debe hacer
- extraer:
  - nombre del proyecto,
  - código del proyecto,
  - versión,
  - fases,
  - actividades,
- marcar estado por campo,
- indicar motivo de fallo cuando aplique,
- habilitar edición manual de faltantes.

### Debe entregar
- servicio de extracción del proyecto,
- integración con wizard del proyecto.

### Aceptación
- el sistema prellena lo que identifica,
- deja pendiente lo que no puede extraer,
- no asume validación automática.

---

## TASK-20. Implementar CRUD de fases del proyecto

### Objetivo
Permitir crear, editar y eliminar fases.

### Debe hacer
- CRUD de fases,
- validación de nombre obligatorio,
- relación con proyecto.

### Debe entregar
- endpoints y UI de fases.

### Aceptación
- se pueden crear varias fases,
- no se aceptan fases vacías al cierre del proyecto.

---

## TASK-21. Implementar CRUD de actividades por fase

### Objetivo
Permitir crear, editar y eliminar actividades.

### Debe hacer
- CRUD de actividades,
- asociar actividad a fase,
- validar descripción obligatoria,
- evitar duplicados exactos dentro de la misma fase.

### Debe entregar
- endpoints y UI de actividades.

### Aceptación
- cada actividad pertenece a una fase,
- no se aceptan duplicados ni vacíos.

---

## TASK-22. Construir vista consolidada del proyecto

### Objetivo
Permitir revisar la estructura completa del proyecto antes del cierre.

### Debe hacer
- mostrar datos generales del proyecto,
- mostrar fases,
- mostrar actividades,
- mostrar origen del dato,
- permitir correcciones rápidas.

### Debe entregar
- vista consolidada del proyecto.

### Aceptación
- el usuario puede revisar y editar desde el consolidado,
- la estructura se muestra correctamente.

---

## TASK-23. Implementar validador y cierre del proyecto

### Objetivo
Permitir marcar el proyecto como COMPLETO.

### Debe hacer
- validar:
  - código,
  - nombre,
  - versión,
  - al menos una fase,
  - al menos una actividad por fase,
- crear acción explícita de confirmación,
- cambiar estado a COMPLETO.

### Debe entregar
- servicio de completitud del proyecto,
- endpoint de cierre,
- mensajes de error por faltantes.

### Aceptación
- no se puede cerrar si faltan fases o actividades,
- sí se puede cerrar cuando la estructura mínima está completa.

---

## TASK-24. Implementar auditoría básica

### Objetivo
Registrar eventos mínimos del sistema.

### Debe hacer
- registrar creación,
- registrar actualización,
- registrar cierre,
- registrar cambios de estado,
- registrar eventos de inconsistencia posterior.

### Debe entregar
- servicio de auditoría,
- persistencia de eventos básicos.

### Aceptación
- los eventos principales quedan registrados,
- pueden auditarse programa y proyecto.

---

## TASK-25. Implementar advertencia de impacto por cambios posteriores

### Objetivo
Advertir si un programa completo es editado y puede afectar al proyecto.

### Debe hacer
- detectar si una edición del programa rompe completitud,
- cambiar estado a EN_REVISION si aplica,
- mostrar advertencia sobre posible impacto al proyecto,
- mantener consistencia del dominio.

### Debe entregar
- lógica de impacto,
- mensaje o banner de advertencia.

### Aceptación
- editar el programa después de cerrado puede regresarlo a revisión,
- el sistema advierte el impacto sobre el proyecto asociado.

---

## TASK-26. Agregar pruebas unitarias

### Objetivo
Probar las reglas críticas del dominio.

### Debe hacer
- pruebas de completitud del programa,
- pruebas de completitud del proyecto,
- pruebas de duplicidad,
- pruebas de estados,
- pruebas de bloqueo del proyecto.

### Debe entregar
- suite de pruebas unitarias mínima.

### Aceptación
- las reglas críticas quedan cubiertas por tests.

---

## TASK-27. Agregar pruebas de integración

### Objetivo
Validar el comportamiento de los módulos conectados.

### Debe hacer
- prueba de creación de programa,
- prueba de guardado de borrador,
- prueba de CRUD curricular,
- prueba de cierre del programa,
- prueba de creación y cierre del proyecto.

### Debe entregar
- suite mínima de pruebas de integración.

### Aceptación
- los módulos principales funcionan de punta a punta a nivel backend.

---

## TASK-28. Agregar pruebas end-to-end

### Objetivo
Validar el flujo completo del usuario.

### Debe hacer
- escenario programa manual,
- escenario programa con extracción parcial,
- escenario proyecto bloqueado,
- escenario proyecto habilitado,
- escenario proyecto completo,
- escenario impacto por edición posterior.

### Debe entregar
- suite mínima end-to-end.

### Aceptación
- el flujo principal queda validado visual y funcionalmente.

---

## TASK-29. Estabilización final y documentación técnica mínima

### Objetivo
Cerrar la implementación de Fase 1 con consistencia.

### Debe hacer
- corregir bugs detectados,
- revisar mensajes UX,
- validar transiciones de estado,
- actualizar README técnico,
- documentar cómo correr el proyecto.

### Debe entregar
- sistema estable,
- documentación mínima de ejecución local.

### Aceptación
- la Fase 1 puede probarse de punta a punta,
- la documentación mínima existe.

---

# 4. Orden obligatorio recomendado

Ejecutar en este orden:

1. TASK-01
2. TASK-02
3. TASK-03
4. TASK-04
5. TASK-05
6. TASK-06
7. TASK-07
8. TASK-08
9. TASK-09
10. TASK-10
11. TASK-11
12. TASK-12
13. TASK-13
14. TASK-14
15. TASK-15
16. TASK-16
17. TASK-17
18. TASK-18
19. TASK-19
20. TASK-20
21. TASK-21
22. TASK-22
23. TASK-23
24. TASK-24
25. TASK-25
26. TASK-26
27. TASK-27
28. TASK-28
29. TASK-29

---

# 5. Prompt base para ejecutar cada tarea con Codex

Usar este formato:

## Plantilla
- Lee primero:
  - BUSINESS_RULES.md
  - SPECS.md
  - USER_STORIES.md
  - TRACEABILITY_MATRIX.md
  - DATA_MODEL.md
  - IMPLEMENTATION_PLAN.md
  - CODEX_TASKS.md

- Implementa únicamente: `TASK-XX`
- Respeta el alcance de Fase 1.
- No inventes requisitos fuera de los documentos.
- Si detectas ambigüedad, repórtala.
- Entrega:
  - archivos creados o modificados,
  - explicación breve,
  - validaciones implementadas,
  - y pruebas mínimas si aplican.

---

# 6. Criterio general de terminado por tarea

Una tarea se considera terminada cuando:

- cumple su objetivo,
- respeta reglas de negocio,
- no rompe tareas anteriores,
- mantiene persistencia y trazabilidad,
- y puede verificarse funcionalmente.
