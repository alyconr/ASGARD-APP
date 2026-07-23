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

## Decision funcional TASK-UNICO-CARRIL

TASK-08.5 se ejecutó y alineó el programa a Excel canonico.
Esta refactorizacion completa TASK-UNICO-CARRIL:

- elimina el carril manual como modo operativo para programa y proyecto;
- reinterpreta TASK-18, TASK-19 y siguientes en coherencia con el unico carril;
- el PDF queda como evidencia documental para programa y proyecto;
- el Excel/matriz es la unica fuente estructurada activa.
- `datos-programa` y `datos-proyecto` quedan eliminados como pasos funcionales;
- el programa inicia en `origen-documental`, muestra resumen compacto tras importacion y revisa competencias en modal paginada;
- `estructura-curricular` trabaja por competencia seleccionada y usa selectores progresivos para conocimientos/criterios;
- el proyecto inicia en `fuente-proyecto`;
- MinIO usa `proyectos-formativos/{referencia_id}/documentos/...` para PDF de proyecto y `proyectos-formativos/{referencia_id}/excel/...` para matriz Excel.

La importacion curricular se organiza principalmente por competencia. Los
resultados, conocimientos y criterios quedan bajo la competencia; `resultado_id`
en conocimientos y criterios es opcional y secundario. Solo los elementos sin
competencia confiable quedan pendientes de conciliacion.

## Decision funcional DASHBOARD-MAESTRO-ASGARD

Se incorpora un dashboard maestro ASGARD como entrada principal:

- `/` muestra estado agregado, metricas, bloqueos y mapa navegable;
- `/programa` contiene el wizard de programa;
- proyecto requiere programa `COMPLETO`;
- planeacion requiere programa y proyecto `COMPLETO`;
- el backend expone el agregado por `GET /api/v1/dashboard/{referencia_id}`;
- las pruebas deben cubrir servicio backend, gates y UI.

## Decision funcional ASISTENTE-GUIADO-TRANSVERSAL

Se incorpora un asistente guiado transversal para los wizards:

- visible en programa, proyecto y planeacion;
- flotante, colapsable y no invasivo;
- con severidad, mensaje, checklist y CTA;
- basado en estado real de wizard, gates backend y contexto de planeacion;
- con persistencia local ligera de experiencia;
- sin reemplazar validadores ni reglas de habilitacion.

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

## TASK-DASHBOARD-MAESTRO-ASGARD. Centralizar acceso y progreso de Fase 1

### Objetivo
Convertir la home en un panel maestro que agregue programa, proyecto y planeacion sin saltar reglas de negocio.

### Debe hacer
- mover el wizard de programa a `/programa`,
- crear endpoint agregado `GET /api/v1/dashboard/{referencia_id}`,
- mostrar estados, acciones requeridas, metricas y mapa navegable,
- bloquear proyecto hasta programa `COMPLETO`,
- bloquear planeacion hasta programa y proyecto `COMPLETO`.

### Debe entregar
- servicio backend de dashboard,
- contratos HTTP,
- UI del dashboard maestro,
- pruebas backend y frontend del flujo habilitado/bloqueado.

### Aceptacion
- `/` no abre directamente un wizard;
- el proyecto no se habilita por PDF evidencia ni por programa incompleto;
- la planeacion no permite guardar ni confirmar si el proyecto no esta `COMPLETO`;
- el mapa navegable solo activa enlaces disponibles.

---

## TASK-ASISTENTE-GUIADO-ASGARD. Guia transversal de usuario

### Objetivo
Agregar un asistente visual reutilizable que oriente al usuario durante los wizards de programa, proyecto y planeacion.

### Debe hacer
- crear motor de reglas de guia;
- crear componente flotante colapsable;
- integrar programa, proyecto y planeacion;
- mostrar advertencias entre wizards;
- persistir preferencias ligeras de UX;
- agregar pruebas de motor y componente.

### Aceptacion
- el asistente aparece en los tres wizards;
- muestra mensajes por paso y severidad;
- advierte cuando proyecto o planeacion estan bloqueados;
- no reemplaza validaciones reales ni modifica gates;
- conserva UX ligera y no invasiva.

---

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

## TASK-05. Implementar formulario base del programa [DEPRECATED - eliminado por REFACTOR-FLUJO-PROGRAMA-PROYECTO]

Nota vigente: esta tarea queda reemplazada por importacion Excel canonica. El paso `datos-programa` no existe y no debe reactivarse como captura manual.

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

## TASK-06. Implementar carga y diagnóstico de PDF del programa como evidencia

### Objetivo
Permitir subir un PDF del programa como evidencia documental en MinIO.

### Debe hacer
- implementar carga de archivo PDF,
- validar formato,
- almacenar en MinIO como evidencia,
- registrar metadata en el borrador.

### Debe entregar
- endpoint/controlador de carga,
- almacenamiento en MinIO,
- metadata de validación en borrador.

### No debe hacer
- realizar extracción curricular desde el PDF,
- intentar leer contenido del PDF para poblar campos,
- clasificar legibilidad como fuente de datos.

### Aceptación
- el sistema acepta PDF válido,
- el sistema rechaza formatos no válidos,
- el PDF se almacena como evidencia en MinIO.

---

## TASK-07. Carga PDF del programa como evidencia [DEPRECATED - reemplazado por TASK-06]

### Objetivo
Esta tarea queda reemplazada por TASK-06. El PDF ya no es fuente de extracción curricular.

### Debe hacer
- marcar esta tarea como DEPRECATED,
- actualizar referencias cruzadas.

### No debe hacer
- implementar ningun flujo de extracción desde PDF.

### Aceptación
- la tarea queda marcada como obsoleta.

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

## TASK-08.5. Refactorizar fuente de extraccion a Excel canonico

### Objetivo
Desactivar la extraccion curricular desde PDF y habilitar un carril de Excel canonico antes de TASK-09.

### Debe hacer
- conservar la carga del PDF como evidencia documental en MinIO,
- eliminar el endpoint y la UI activa de extraccion desde PDF,
- validar workbook `.xlsx` con hojas `Programa`, `Competencias`, `Resultados`, `Conocimientos` y `Criterios`,
- validar encabezados exactos, claves cruzadas, tipos minimos y duplicados,
- generar preview sin persistir tablas relacionales,
- confirmar importacion para materializar ProgramaFormacion, Competencia, ResultadoAprendizaje, Conocimiento y CriterioEvaluacion,
- asociar conocimientos y criterios a la competencia aunque no tengan `rap_id`,
- crear pendientes solo para conocimientos o criterios sin competencia confiable,
- mantener el mismo `referencia_id` del wizard y sincronizar metadata en `payload_json`.

### No debe hacer
- no implementar el CRUD manual de resultados de TASK-09,
- no reactivar extraccion PDF,
- no guardar binarios Excel en PostgreSQL.

### Aceptacion
- PDF sigue en MinIO como soporte documental,
- Excel canonico valida y muestra preview,
- confirmacion importa la estructura curricular completa,
- conocimientos y criterios quedan organizados por competencia y no dependen de RAP,
- el borrador conserva el mismo `referencia_id`,
- TASK-09 puede continuar sobre la base importada.

---

## TASK-08.6. Refactor visual y funcional del flujo programa [COMPLETA]

### Objetivo
Eliminar `datos-programa`, compactar el origen documental y focalizar la gestion curricular.

### Debe hacer
- iniciar el wizard en `origen-documental`,
- mostrar resumen compacto tras importacion confirmada,
- abrir competencias importadas en modal paginada,
- usar selector/filtro de competencia en `estructura-curricular`,
- seleccionar conocimientos y criterios progresivamente antes de renderizarlos.

### Aceptacion
- no existe `datos-programa`,
- no hay render masivo de competencias en origen documental,
- el paso curricular trabaja por competencia seleccionada.

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

## TASK-17. Implementar formulario base del proyecto [DEPRECATED - eliminado por REFACTOR-FLUJO-PROGRAMA-PROYECTO]

Nota vigente: esta tarea queda reemplazada por `fuente-proyecto`, con PDF evidencia y Excel/matriz estructurada. El paso `datos-proyecto` no existe y no debe reactivarse como captura manual.

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

## TASK-18. Implementar carga y diagnóstico de PDF del proyecto como evidencia ✅ COMPLETA

### Objetivo
Permitir subir el PDF del proyecto como evidencia documental en MinIO.

### Debe hacer
- carga de PDF,
- validación de archivo,
- almacenamiento en MinIO como evidencia bajo `proyectos-formativos/{referencia_id}/documentos/...`,
- registro de metadata en borrador.

### Debe entregar
- endpoint de carga,
- almacenamiento en MinIO,
- metadata de validación en borrador.

### No debe hacer
- realizar extracción curricular desde el PDF del proyecto,
- intentar leer contenido del PDF para poblar campos,
- clasificar legibilidad como fuente de datos.

### Aceptación
- el sistema clasifica correctamente el archivo como evidencia,
- el usuario ve el PDF almacenado como soporte documental.

### Implementado
- backend: `proyecto_documentos.py` (servicio, DTOs, controller, endpoint `POST /proyectos/{ref}/documentos/proyecto-pdf`)
- frontend: `proyecto-document-upload.tsx` (uploader), `document-upload-api.ts` (client), integración en `proyecto-wizard-shell.tsx`
- tipos: `ProyectoPdfUploadResult`, `ProyectoStoredDocument`, `normalizeProyectoDocumental`
- pruebas: `test_proyecto_documentos_service.py`, `proyecto-document-upload.test.tsx`

---

## TASK-19. Definir e implementar fuente estructurada del proyecto [reinterpretada] ✅ COMPLETA

### Objetivo
Implementar la importación estructurada del proyecto desde una matriz/Excel, alineada con el unico carril funcional.

### Debe hacer
- definir el contrato canonico del workbook del proyecto (hojas: Proyecto, Fases, Actividades),
- validar workbook `.xlsx`,
- almacenar Excel bajo `proyectos-formativos/{referencia_id}/excel/...`,
- generar preview sin persistencia relacional,
- confirmar importacion para materializar ProyectoFormativo, FaseProyecto y ActividadProyecto,
- permitir correccion post-importacion SOLO para lo estrictamente faltante.

### Debe entregar
- servicio de importacion del proyecto,
- preview funcional,
- confirmacion de importacion,
- integracion con wizard del proyecto.

### Aceptacion
- el sistema importa desde Excel/matriz cuando se disponga,
- deja pendiente lo que no puede importar,
- no asume validacion automatica,
- no intenta extraccion desde PDF.

### Implementado
- backend: `proyecto_excel.py` (servicio, DTOs, controller, endpoints preview/confirm, repository adapter)
- frontend: `proyecto-excel-import.tsx` (uploader + preview + confirmacion), `excel-import-api.ts` (client)
- integracion: wizard-shell renderiza ambos uploaders en paso `fuente-proyecto`
- normalizacion: `normalizeProyectoDocumental` restaura preview y confirmacion desde borrador
- tipos: `ProyectoExcelPreviewState`, `ExcelPreviewSummary`, `ExcelFasePreview`, `ExcelValidationIssue`
- pruebas: `test_proyecto_excel_service.py` (13 tests), `proyecto-excel-import.test.tsx` (10 tests)

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
- escenario programa importado desde Excel,
- escenario programa con correccion post-importacion,
- escenario proyecto bloqueado,
- escenario proyecto habilitado,
- escenario proyecto completo,
- escenario impacto por edicion posterior.

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
9. TASK-08.5
10. TASK-09
11. TASK-10
12. TASK-11
13. TASK-12
14. TASK-13
15. TASK-14
16. TASK-15
17. TASK-16
18. TASK-17
19. TASK-18
20. TASK-19
21. TASK-20
22. TASK-21
23. TASK-22
24. TASK-23
25. TASK-24
26. TASK-25
27. TASK-26
28. TASK-27
29. TASK-28
30. TASK-29

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
