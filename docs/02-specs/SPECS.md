# SPECS.md
## Proyecto: Aplicación web para construcción de guías de aprendizaje SENA
## Fase: 1
## Estado: Ready for implementation
## Última actualización: [YYYY-MM-DD]

---

# 1. Resumen

Este documento define la especificación funcional y técnica de la Fase 1 del sistema para construcción de guías de aprendizaje SENA.

La Fase 1 debe permitir:

- cargar información del programa de formación,
- cargar información del proyecto formativo,
- conservar PDF como evidencia documental cuando exista,
- importar datos desde Excel canonico cuando se use fuente estructurada,
- permitir diligenciamiento manual cuando no sea posible,
- guardar automáticamente el avance en borrador,
- revisar y validar la información,
- bloquear el proyecto hasta completar el programa,
- y persistir toda la información de forma estructurada y trazable.

La Fase 1 no genera aún la guía final; deja preparada la base funcional y de datos para fases posteriores.

## Decision funcional TASK-08.5

Desde TASK-08.5, el flujo del programa separa dos insumos:

- PDF: documento soporte, validado de forma basica y almacenado en MinIO; no se usa para extraccion curricular.
- Excel canonico `.xlsx`: fuente estructurada para validar hojas, encabezados, claves cruzadas, preview e importacion relacional.

El contrato canonico del workbook contiene las hojas `Programa`, `Competencias`, `Resultados`, `Conocimientos` y `Criterios`.

La organizacion funcional del workbook es por competencia. Cada competencia es
el nodo principal y contiene sus resultados, conocimientos y criterios. Los
conocimientos y criterios se importan asociados inicialmente a la competencia;
su asignacion a un resultado de aprendizaje es opcional y secundaria.

---

# 2. Objetivo general

Implementar un módulo web que permita registrar, extraer, revisar, editar y validar la información base del programa de formación y del proyecto formativo, como insumo para la futura construcción automatizada de guías de aprendizaje SENA.

---

# 3. Objetivos específicos

- Permitir el cargue manual o asistido del programa de formación.
- Permitir la importacion estructurada desde Excel canonico del programa.
- Permitir el diligenciamiento manual de los campos faltantes o no extraídos.
- Permitir la gestión completa de competencias y su estructura curricular.
- Validar la completitud del programa antes de habilitar el proyecto.
- Permitir el cargue manual o asistido del proyecto formativo.
- Permitir la gestión de fases y actividades del proyecto.
- Validar la completitud del proyecto antes de cerrar la Fase 1.
- Mantener guardado automático del avance en todo momento.
- Mantener trazabilidad básica de los cambios relevantes.

---

# 4. Alcance funcional

## 4.1 Incluye

La Fase 1 incluye:

- wizard del programa de formación,
- wizard del proyecto formativo,
- servicio de borradores,
- diagnóstico de legibilidad de PDF,
- carga documental PDF como evidencia,
- importacion estructurada desde Excel canonico,
- CRUD de competencias,
- CRUD de resultados de aprendizaje,
- CRUD de conocimientos de saber,
- CRUD de conocimientos de proceso,
- CRUD de criterios de evaluación,
- CRUD de fases del proyecto,
- CRUD de actividades del proyecto,
- vistas consolidadas de revisión,
- validadores de completitud,
- bloqueo/desbloqueo del proyecto,
- auditoría básica,
- pruebas mínimas.

## 4.2 No incluye

La Fase 1 no incluye:

- generación automática de la guía de aprendizaje,
- exportación a PDF,
- exportación a DOCX,
- versionamiento documental avanzado,
- aprobaciones institucionales,
- roles complejos,
- integraciones externas,
- panel administrativo avanzado,
- ayuda contextual documental por campo.

---

# 5. Actores

## 5.1 Actor principal
**Usuario gestor pedagógico**

Responsable de:

- iniciar el proceso,
- cargar documentos,
- completar datos manualmente,
- revisar la información,
- cerrar el programa,
- habilitar el proyecto,
- revisar y cerrar el proyecto.

## 5.2 Actor secundario
**Sistema de extracción documental**

Responsable de:

- recibir archivos PDF,
- validar que sean procesables,
- diagnosticar legibilidad,
- intentar extraer información,
- clasificar fallos,
- y dejar campos listos para revisión humana.

---

# 6. Supuestos del sistema

- El usuario cuenta con documentos fuente o con información suficiente para diligenciar manualmente el sistema.
- Los PDFs pueden tener texto extraíble o ser escaneados; el sistema debe soportar ambas situaciones mediante fallback manual.
- La revisión humana es obligatoria antes de cerrar cualquier bloque.
- El programa de formación es el bloque padre de la estructura de Fase 1.
- El proyecto formativo solo se habilita cuando el programa ya está completo.

---

# 7. Flujo funcional principal

## Paso 1. Inicio
El usuario puede:

- iniciar un nuevo proceso,
- cargar PDF del programa,
- diligenciar manualmente,
- continuar un borrador existente.

## Paso 2. Diagnóstico del programa
Si se carga PDF, el sistema debe determinar si el archivo es:

- legible,
- parcialmente legible,
- o no legible.

## Paso 3. Captura inicial del programa
El sistema debe mostrar:

- campos extraídos automáticamente,
- campos vacíos para diligenciar manualmente,
- campos pendientes por revisión.

## Paso 4. Gestión curricular del programa
El usuario debe poder crear, editar o eliminar:

- competencias,
- resultados,
- conocimientos de saber,
- conocimientos de proceso,
- criterios.

## Paso 5. Revisión del programa
El sistema debe mostrar el consolidado del programa antes del cierre.

## Paso 6. Cierre del programa
El sistema debe validar completitud y, si procede, marcar el programa como COMPLETO.

## Paso 7. Habilitación del proyecto
Solo cuando el programa esté completo, el sistema debe habilitar el proyecto formativo.

## Paso 8. Diagnóstico del proyecto
Si se carga PDF del proyecto, el sistema debe analizar su legibilidad.

## Paso 9. Captura inicial del proyecto
El sistema debe mostrar campos extraídos y permitir completar manualmente los faltantes.

## Paso 10. Gestión estructural del proyecto
El usuario debe poder crear, editar o eliminar:

- fases,
- actividades.

## Paso 11. Revisión del proyecto
El sistema debe mostrar el consolidado del proyecto antes del cierre.

## Paso 12. Cierre del proyecto
El sistema debe validar completitud y, si procede, marcar el proyecto como COMPLETO.

---

# 8. Requisitos funcionales

## 8.1 Requisitos funcionales del programa

### RF-01. Crear programa
El sistema debe permitir crear un registro de programa de formación.

### RF-02. Capturar datos mínimos del programa
Los campos mínimos del programa son:

- codigo_programa,
- nombre_programa.

### RF-03. Guardar programa en borrador
El sistema debe guardar el programa aunque esté incompleto.

### RF-04. Cargar PDF del programa
El sistema debe permitir subir un archivo PDF del programa.

### RF-05. Diagnosticar legibilidad del programa
El sistema debe clasificar el PDF del programa como:

- legible,
- parcialmente legible,
- no legible.

### RF-06. Extraer datos del programa
Cuando el documento sea legible, el sistema debe intentar extraer:

- código del programa,
- nombre del programa,
- competencias,
- resultados,
- conocimientos de saber,
- conocimientos de proceso,
- criterios.

### RF-07. Permitir fallback manual del programa
Si la extracción es parcial o falla, el sistema debe permitir completar manualmente la información faltante.

### RF-08. Gestionar competencias
El sistema debe permitir crear, editar y eliminar competencias.

### RF-09. Gestionar resultados
El sistema debe permitir crear, editar y eliminar resultados de aprendizaje por competencia.

### RF-10. Gestionar conocimientos de saber
El sistema debe permitir crear, editar y eliminar conocimientos de saber por competencia.

### RF-11. Gestionar conocimientos de proceso
El sistema debe permitir crear, editar y eliminar conocimientos de proceso por competencia.

### RF-12. Gestionar criterios
El sistema debe permitir crear, editar y eliminar criterios de evaluación por competencia.

### RF-13. Revisar consolidado del programa
El sistema debe mostrar una vista consolidada editable del programa antes del cierre.

### RF-14. Validar completitud del programa
El sistema debe impedir el cierre del programa si falta información obligatoria.

### RF-15. Cerrar el programa
El sistema debe permitir marcar el programa como COMPLETO solo cuando cumpla las reglas del dominio.

---

## 8.2 Requisitos funcionales del proyecto

### RF-16. Bloquear proyecto
El sistema debe mantener el proyecto BLOQUEADO mientras el programa no esté COMPLETO.

### RF-17. Habilitar proyecto
El sistema debe habilitar el proyecto automáticamente cuando el programa esté COMPLETO.

### RF-18. Crear proyecto
El sistema debe permitir crear un proyecto formativo asociado a un programa completo.

### RF-19. Capturar datos mínimos del proyecto
Los campos mínimos del proyecto son:

- codigo_proyecto,
- nombre_proyecto,
- version_proyecto.

### RF-20. Guardar proyecto en borrador
El sistema debe guardar el proyecto aunque esté incompleto.

### RF-21. Cargar PDF del proyecto
El sistema debe permitir subir un archivo PDF del proyecto.

### RF-22. Diagnosticar legibilidad del proyecto
El sistema debe clasificar el PDF del proyecto como:

- legible,
- parcialmente legible,
- no legible.

### RF-23. Extraer datos del proyecto
Cuando el documento sea legible, el sistema debe intentar extraer:

- código del proyecto,
- nombre del proyecto,
- versión del proyecto,
- fases,
- actividades.

### RF-24. Permitir fallback manual del proyecto
Si la extracción es parcial o falla, el sistema debe permitir completar manualmente la información faltante.

### RF-25. Gestionar fases
El sistema debe permitir crear, editar y eliminar fases del proyecto.

### RF-26. Gestionar actividades
El sistema debe permitir crear, editar y eliminar actividades por fase.

### RF-27. Revisar consolidado del proyecto
El sistema debe mostrar una vista consolidada editable del proyecto antes del cierre.

### RF-28. Validar completitud del proyecto
El sistema debe impedir el cierre del proyecto si faltan datos mínimos o actividades válidas.

### RF-29. Cerrar el proyecto
El sistema debe permitir marcar el proyecto como COMPLETO solo cuando cumpla las reglas del dominio.

---

## 8.3 Requisitos funcionales transversales

### RF-30. Guardado automático
Todo cambio relevante en el wizard debe persistirse automáticamente.

### RF-31. Recuperación de borradores
El sistema debe permitir retomar un proceso desde el último paso guardado.

### RF-32. Origen del dato
El sistema debe conservar y mostrar el origen del dato como:

- extraído,
- manual,
- corregido,
- pendiente.

### RF-33. Confirmación de eliminación
Toda eliminación debe requerir confirmación explícita.

### RF-34. Auditoría básica
El sistema debe registrar eventos mínimos de creación, actualización, cierre y cambio de estado.

### RF-35. Advertencia de impacto
Si un programa ya completo se edita y vuelve a estado EN_REVISION, el sistema debe advertir el posible impacto sobre el proyecto asociado.

---

# 9. Requisitos no funcionales

## RNF-01. Usabilidad
La interfaz debe ser comprensible para usuarios no técnicos del entorno pedagógico.

## RNF-02. Persistencia
El borrador debe mantenerse aunque el usuario cambie de paso o retome después.

## RNF-03. Tolerancia a errores
La falla de extracción de uno o varios campos no debe romper el flujo.

## RNF-04. Integridad
La base de datos debe garantizar integridad relacional.

## RNF-05. Escalabilidad
La solución debe quedar lista para soportar fases posteriores sin rediseño profundo del dominio.

## RNF-06. Trazabilidad
Toda entidad principal debe mantener fecha de creación, actualización y estado.

## RNF-07. Modularidad
La arquitectura debe estar organizada por dominio y responsabilidades claras.

---

# 10. Estados del sistema

## 10.1 Programa
- BORRADOR
- EN_REVISION
- COMPLETO

## 10.2 Proyecto
- BLOQUEADO
- BORRADOR
- EN_REVISION
- COMPLETO

---

# 11. Reglas de transición

## ET-01. Inicio de registros
Todo nuevo programa o proyecto inicia en BORRADOR.

## ET-02. Programa a revisión
El programa puede pasar a EN_REVISION cuando ya tiene datos mínimos y entra a revisión humana.

## ET-03. Programa a completo
El programa puede pasar a COMPLETO cuando:

- tiene datos mínimos,
- tiene al menos una competencia,
- cada competencia tiene:
  - resultados,
  - saber,
  - proceso,
  - criterios,
- y existe confirmación explícita del usuario.

## ET-04. Proyecto bloqueado
El proyecto permanece BLOQUEADO mientras el programa no esté COMPLETO.

## ET-05. Proyecto a borrador
El proyecto puede pasar a BORRADOR solo cuando el programa ya está COMPLETO.

## ET-06. Proyecto a revisión
El proyecto puede pasar a EN_REVISION cuando ya tiene datos mínimos y estructura parcial o total para revisión.

## ET-07. Proyecto a completo
El proyecto puede pasar a COMPLETO cuando:

- el programa está COMPLETO,
- tiene datos mínimos,
- tiene al menos una fase,
- cada fase tiene al menos una actividad,
- y existe confirmación explícita del usuario.

## ET-08. Regresión del programa
Si un programa completo pierde consistencia por una edición posterior, debe volver a EN_REVISION.

## ET-09. Impacto al proyecto
Si el programa vuelve a EN_REVISION, el sistema debe advertir que el proyecto asociado puede quedar afectado.

---

# 12. Validaciones funcionales

## 12.1 Validaciones generales
- no permitir campos obligatorios vacíos,
- no permitir valores compuestos solo por espacios,
- no permitir hijos sin padre relacional,
- no permitir cierre de bloques incompletos.

## 12.2 Validaciones del programa
- no duplicar código de programa según política definida,
- no duplicar competencia por código dentro del mismo programa,
- no duplicar resultados exactos dentro de una competencia,
- no duplicar conocimientos exactos dentro de la misma categoría y competencia,
- no duplicar criterios exactos dentro de la misma competencia.

Durante preview/importacion Excel, los conocimientos y criterios sin
competencia confiable no se consideran error fatal: se conservan como pendientes
de asignacion y la duplicidad se evalua cuando el usuario seleccione el destino
final. La ausencia de `rap_id` no genera pendiente si la competencia esta clara.

## 12.3 Validaciones del proyecto
- no duplicar actividad exacta dentro de la misma fase,
- no permitir actividades sin fase,
- no permitir fases vacías al cierre del proyecto,
- no permitir proyecto funcionalmente activo sin programa completo.

---

# 13. Reglas de fuente documental e importacion Excel

> TASK-08.5 deja el PDF como evidencia documental. La extraccion curricular
> del programa se realiza desde Excel canonico `.xlsx` mediante preview y
> confirmacion explicita.

El Excel canonico puede traer conocimientos y criterios sin `rap_id` o con un
`rap_id` que no se pueda resolver. El sistema debe importarlos por competencia
si `competencia_id` es confiable, dejando `resultado_id = NULL` cuando no exista
asociacion especifica a resultado. Solo lo que no pueda asociarse a competencia
queda como pendiente de conciliacion manual posterior.

## 13.1 Objetivo de extracción del programa
El sistema debe intentar extraer del PDF del programa:

- código,
- nombre,
- competencias,
- resultados,
- saber,
- proceso,
- criterios.

## 13.2 Objetivo de extracción del proyecto
El sistema debe intentar extraer del PDF del proyecto:

- código,
- nombre,
- versión,
- fases,
- actividades.

## 13.3 Manejo de fallos
Cuando un campo no pueda ser extraído, el sistema debe:

1. informar el motivo,
2. marcar el campo como pendiente,
3. habilitar edición manual.

## 13.4 Motivos mínimos de fallo
- PDF escaneado
- documento ilegible
- baja resolución
- estructura no reconocida
- campo no encontrado
- contenido ambiguo
- archivo protegido

---

# 14. Vista consolidada de revisión

## 14.1 Consolidado del programa
Debe mostrar:

- programa,
- competencias,
- resultados,
- conocimientos de saber,
- conocimientos de proceso,
- criterios,
- origen del dato,
- estado por bloque.

## 14.2 Consolidado del proyecto
Debe mostrar:

- datos generales del proyecto,
- fases,
- actividades,
- origen del dato,
- estado por bloque.

## 14.3 Edición desde consolidado
La vista consolidada debe permitir volver a editar antes del cierre.

---

# 15. Modelo de datos conceptual resumido

## ProgramaFormacion
- id
- codigo_programa
- nombre_programa
- version_programa
- estado
- fuente_cargue
- fecha_creacion
- fecha_actualizacion

## Competencia
- id
- programa_id
- codigo_competencia
- nombre_competencia
- estado
- orden

## ResultadoAprendizaje
- id
- competencia_id
- codigo_resultado (`rap_id` estable cuando proviene del Excel canonico)
- descripcion
- estado
- orden

## Conocimiento
- id
- competencia_id
- tipo
- descripcion
- estado
- orden

## CriterioEvaluacion
- id
- competencia_id
- descripcion
- estado
- orden

## ProyectoFormativo
- id
- programa_id
- codigo_proyecto
- nombre_proyecto
- version_proyecto

## ElementoCurricularPendiente
- id
- referencia_id
- programa_id
- tipo_elemento
- tipo_conocimiento
- descripcion
- competencia_id_origen_excel
- rap_id_origen_excel
- motivo
- estado
- competencia_destino_id
- resultado_destino_id
- elemento_creado_id
- estado
- fuente_cargue
- fecha_creacion
- fecha_actualizacion

## FaseProyecto
- id
- proyecto_id
- nombre_fase
- estado
- orden

## ActividadProyecto
- id
- fase_id
- descripcion
- estado
- orden

## BorradorSesion
- id
- tipo_bloque
- referencia_id
- paso_actual
- payload_json
- estado_borrador
- ultima_edicion

## EventoAuditoria
- id
- entidad
- entidad_id
- accion
- detalle
- fecha_evento

---

# 16. Relación entre componentes

- Un programa tiene muchas competencias.
- Una competencia tiene muchos resultados.
- Una competencia tiene muchos conocimientos.
- Una competencia tiene muchos criterios.
- Un programa puede tener uno o varios proyectos.
- Un proyecto tiene muchas fases.
- Una fase tiene muchas actividades.

---

# 17. Reglas de implementación

## 17.1 Estrategia de construcción
La Fase 1 debe implementarse módulo por módulo, no toda de una sola vez.

## 17.2 Orden recomendado
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

## 17.3 Restricción de alcance
No deben implementarse funcionalidades de fases futuras dentro de este alcance.

---

# 18. Criterios de aceptación globales

## CA-01
El programa puede iniciarse manualmente o desde Excel canonico; el PDF queda como soporte documental.

## CA-02
Si el PDF del programa no es legible, el sistema permite completar manualmente.

## CA-03
El sistema guarda automáticamente el avance en borrador.

## CA-04
El programa no puede cerrarse si no tiene estructura curricular mínima.

## CA-05
El proyecto permanece bloqueado mientras el programa no esté completo.

## CA-06
El proyecto puede iniciarse cuando el programa esté completo.

## CA-07
Si el PDF del proyecto no es legible, el sistema permite completar manualmente.

## CA-08
El proyecto no puede cerrarse si faltan fases o actividades válidas.

## CA-09
Toda vista final de programa o proyecto es editable antes del cierre.

## CA-10
Si un programa completo se edita y pierde consistencia, el sistema advierte el impacto sobre el proyecto relacionado.

---

# 19. Riesgos funcionales identificados

- PDFs escaneados o de baja calidad.
- Extracción incompleta o ambigua.
- Duplicidad de registros curriculares.
- Inconsistencia entre programa y proyecto por cambios posteriores.
- Cierre indebido de bloques incompletos.
- Pérdida de continuidad si el borrador no se maneja correctamente.

---

# 20. Definición de terminado de la Fase 1

La Fase 1 se considera terminada cuando el sistema permite:

- crear y revisar el programa,
- guardar borradores del programa,
- extraer y completar manualmente información del programa,
- gestionar la estructura curricular,
- validar y cerrar el programa,
- bloquear y habilitar el proyecto correctamente,
- crear y revisar el proyecto,
- guardar borradores del proyecto,
- extraer y completar manualmente información del proyecto,
- gestionar fases y actividades,
- validar y cerrar el proyecto,
- y mantener trazabilidad básica del proceso.
