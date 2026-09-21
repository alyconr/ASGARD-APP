# BUSINESS_RULES.md
## Proyecto: Aplicación web para construcción de guías de aprendizaje SENA
## Fase: 1
## Estado: Aprobado para implementación
## Última actualización: [YYYY-MM-DD]

---

# 1. Propósito

Este documento define las reglas de negocio obligatorias para la Fase 1 de la aplicación web de construcción de guías de aprendizaje SENA.

Su objetivo es establecer:

- el alcance real de la fase,
- las restricciones funcionales,
- las dependencias del dominio,
- las reglas de completitud,
- los estados del sistema,
- y las condiciones mínimas que deben respetarse en toda implementación.

Este documento es la **fuente de verdad del negocio** para la Fase 1.

## Decision funcional TASK-08.5

Desde TASK-08.5, la estrategia documental del programa cambia:

- el PDF del programa se carga y conserva solo como evidencia documental en MinIO;
- el PDF ya no es fuente activa de extraccion curricular;
- el Excel canonico `.xlsx` es la fuente estructurada para validar, previsualizar e importar programa, competencias, resultados, conocimientos y criterios;
- la estructura importada se organiza por competencia: cada competencia contiene sus resultados, conocimientos y criterios;
- los conocimientos y criterios se asocian inicialmente a la competencia, no al resultado de aprendizaje;
- `resultado_id` en conocimientos y criterios es una relacion opcional y secundaria para asignaciones posteriores;
- solo quedan en conciliacion manual los elementos sin competencia confiable;
- cualquier regla anterior de extraccion hibrida desde PDF queda reemplazada por esta decision para el flujo del programa.

---

## Decision funcional TASK-UNICO-CARRIL

Desde esta refactorizacion integral, el sistema opera con un unico carril funcional:

- el Excel canonico `.xlsx` es la unica fuente estructurada activa para programa y proyecto;
- el PDF queda exclusivamente como evidencia documental en MinIO para programa y proyecto;
- el carril manual deja de existir como fuente de captura;
- no se debe iniciar ningun flujo "MANUAL" como modo operativo;
- el proyecto tambien queda orientado a fuente estructurada (Excel/matriz) como base;
- las tareas TASK-18, TASK-19 y siguientes deben reinterpretarse en coherencia con este unico carril.

Esta decision reemplaza las reglas RN-13, RN-14, RN-15 y RN-35 anteriores que admitian captura manual o PDF como fuente activa.

## Decision funcional REFACTOR-FLUJO-PROGRAMA-PROYECTO

Desde este refactor, `datos-programa` no existe como paso funcional ni informativo. El programa inicia en `origen-documental`, conserva PDF como evidencia documental y usa Excel canonico como unica fuente estructurada activa. Despues de confirmar la importacion, el sistema muestra un resumen compacto del workbook y la revision de competencias importadas se abre en una modal paginada.

La gestion de `estructura-curricular` debe iniciar con selector/filtro de competencia. Resultados se muestran al seleccionar la competencia; conocimientos y criterios se exponen primero mediante selectores progresivos y solo se renderizan cuando el usuario los elige.

El proyecto formativo se habilita solo cuando el programa esta `COMPLETO`, usa PDF como evidencia y Excel/matriz como fuente estructurada. No existe paso `datos-proyecto` como carril manual de entrada. Los documentos del proyecto se almacenan bajo `proyectos-formativos/{referencia_id}/documentos/...` y los Excel bajo `proyectos-formativos/{referencia_id}/excel/...`.

---

## Decision funcional DASHBOARD-MAESTRO-ASGARD

El dashboard maestro ASGARD es la entrada principal del sistema. Debe centralizar acceso, estado, bloqueos, acciones requeridas, metricas y mapa navegable de la Fase 1 sin crear flujos alternos al wizard.

Reglas vigentes:

- `/` muestra el dashboard maestro y `/programa` abre el wizard del programa;
- el proyecto se habilita unicamente cuando el programa esta `COMPLETO`;
- la planeacion pedagogica se habilita unicamente cuando programa y proyecto estan `COMPLETO`;
- PDF evidencia, carga documental o importacion pendiente no equivalen a cierre humano ni habilitan modulos siguientes;
- las metricas deben derivarse de datos persistidos: competencias, resultados, conocimientos, criterios, fases, actividades y planeaciones;
- el mapa grafico debe representar la dependencia programa -> estructura curricular -> proyecto -> planeacion y respetar los bloqueos reales.

---

## Decision funcional ASISTENTE-GUIADO-TRANSVERSAL

Los wizards de programa, proyecto y planeacion pedagogica cuentan con un asistente visual transversal que explica el paso actual, muestra faltantes, advierte bloqueos y recomienda la siguiente accion.

Reglas vigentes:

- la guia deriva sus mensajes del estado real del wizard y de gates/backend disponibles;
- las severidades minimas son `info`, `warning`, `blocked` y `success`;
- el checklist distingue requisitos completos, pendientes y requisito actual;
- el asistente no reemplaza validaciones funcionales ni habilita modulos por si solo;
- el proyecto sigue dependiendo de programa `COMPLETO`;
- la planeacion sigue dependiendo de programa y proyecto `COMPLETO`;
- la experiencia puede recordar preferencias ligeras como panel colapsado o ayuda inicial vista.

---

# 2. Contexto de negocio

El equipo pedagógico del SENA requiere una aplicación web que permita estructurar la información necesaria para la futura construcción de guías de aprendizaje.

En esta primera fase, la aplicación no generará aún la guía final.  
La prioridad es construir una base confiable para capturar, revisar, editar y validar la información correspondiente a:

- el **programa de formación** (cargado desde Excel canónico con PDF como evidencia),
- y el **proyecto formativo** (cargado desde Excel/matriz con PDF como evidencia).

La solución debe permitir la carga asistida desde la matriz Excel con conservacion de PDF como evidencia, manteniendo trazabilidad, integridad de datos y control de estados.

---

# 3. Alcance de la Fase 1

## 3.1 Incluye

La Fase 1 sí incluye:

- cargue del programa de formación desde Excel canónico,
- cargue del proyecto formativo desde fuente estructurada,
- flujo de usuario tipo wizard,
- carga documental PDF como evidencia,
- importacion estructurada desde Excel canonico,
- guardado automático en borrador,
- edición y eliminación de registros,
- revisión consolidada de la información,
- validación de completitud,
- bloqueo del proyecto hasta completar el programa,
- auditoría básica,
- persistencia estructurada en base de datos.

## 3.2 No incluye

La Fase 1 no incluye:

- generación automática de la guía de aprendizaje,
- exportación a PDF,
- exportación a DOCX,
- versionamiento avanzado de documentos,
- aprobaciones institucionales,
- workflow de coordinación académica,
- panel administrativo avanzado,
- integración con sistemas externos,
- control de permisos complejos por rol,
- ayudas documentales laterales por campo.

---

# 4. Actores del negocio

## 4.1 Actor principal
**Usuario gestor pedagógico**

Es la persona encargada de:

- cargar documentos,
- revisar datos importados desde Excel,
- corregir inconsistencias,
- cerrar el programa,
- habilitar el proyecto,
- y cerrar la Fase 1 desde el punto de vista funcional.

## 4.2 Actor secundario
**Sistema de almacenamiento documental**

Es el componente que:

- recibe archivos PDF,
- valida basicamente su formato,
- los almacena en MinIO como evidencia documental,
- y deja metadata de validacion en el borrador.

---

# 5. Entidades del dominio

Las entidades de negocio de la Fase 1 son:

- Programa de formación
- Competencia
- Resultado de aprendizaje
- Conocimiento de saber
- Conocimiento de proceso
- Criterio de evaluación
- Proyecto formativo
- Fase del proyecto
- Actividad del proyecto
- Borrador
- Evento de auditoría

---

# 6. Regla estructural principal del dominio

## RN-01. Dependencia entre bloques
El **proyecto formativo** depende obligatoriamente del **programa de formación**.

## RN-02. Bloqueo del proyecto
El sistema no debe permitir el cargue, revisión ni cierre del proyecto formativo mientras el programa de formación no esté completamente diligenciado, revisado y marcado como completo.

## RN-03. Orden de trabajo
La secuencia funcional obligatoria de la Fase 1 es:

1. abrir el origen documental del programa,
2. cargar PDF del programa como evidencia si existe,
3. cargar, validar, previsualizar y confirmar Excel canonico del programa,
4. revisar competencias importadas desde el resumen compacto y la modal paginada,
5. gestionar estructura curricular por competencia seleccionada,
6. revisar programa,
7. cerrar programa,
8. habilitar proyecto,
9. abrir fuente del proyecto,
10. cargar PDF del proyecto como evidencia,
11. cargar, validar, previsualizar y confirmar Excel/matriz del proyecto,
12. gestionar fases y actividades,
13. revisar proyecto,
14. cerrar proyecto.

No se deben permitir flujos alternos que rompan esta secuencia.

---

# 7. Reglas del flujo UX/UI

## RN-04. Flujo obligatorio tipo wizard
La interacción principal de la Fase 1 debe implementarse mediante un flujo tipo wizard.

## RN-05. Navegación controlada
El wizard debe permitir:

- avanzar,
- retroceder,
- retomar el proceso,
- y revisar información sin perder avance.

## RN-06. Progreso visible
El sistema debe mostrar el estado de avance del proceso por pasos o bloques.

## RN-07. Validación por etapas
Cada paso del wizard debe validar información mínima antes de permitir el avance al siguiente paso.

## RN-08. Revisión obligatoria
Antes de cerrar el programa o el proyecto, el sistema debe mostrar una vista consolidada editable.

---

# 8. Reglas de persistencia y borradores

## RN-09. Guardado automático obligatorio
Todo avance del usuario debe guardarse automáticamente como borrador.

## RN-10. Persistencia continua
El sistema debe conservar:

- datos ingresados manualmente,
- datos extraídos automáticamente,
- campos incompletos,
- campos pendientes,
- paso actual del wizard,
- estado del bloque.

## RN-11. No pérdida de información
El sistema no debe perder el trabajo del usuario por:

- cambio de paso,
- recarga de pantalla,
- salida accidental,
- interrupción de sesión.

## RN-12. Continuación del borrador
El usuario debe poder retomar un borrador desde el mismo punto donde quedó.

---

# 9. Reglas de fuente documental e importacion estructurada

> TASK-08.5 reemplaza la extraccion curricular desde PDF para el programa.
> TASK-UNICO-CARRIL reemplaza el carril manual: Excel canonico es la unica
> fuente estructurada para programa y proyecto.

## RN-13. Fuente estructurada unica

La informacion estructurada del programa y del proyecto debe partir **unicamente** de la matriz Excel.

- El Excel canonico `.xlsx` es la unica fuente estructurada activa.
- El PDF se carga y almacena en MinIO como evidencia documental SOLO.
- El PDF no se usa para extraccion ni prellenado de programa ni proyecto.
- No existe carril manual como fuente de captura principal.
- No se debe iniciar ningun flujo "MANUAL" como modo operativo.

## RN-13A. Organizacion curricular por competencia
La importacion estructurada desde Excel canonico debe tratar la competencia como
contenedor principal. Los resultados de aprendizaje, conocimientos de saber,
conocimientos de proceso y criterios de evaluacion deben quedar asociados a su
competencia cuando `competencia_id` sea confiable.

Los conocimientos y criterios no deben quedar pendientes ni fallar solo por no
tener `rap_id`. Si se puede resolver un resultado especifico, el sistema puede
guardar `resultado_id`; si no, debe importar el elemento con `resultado_id = NULL`
y conservarlo asociado a la competencia.

## RN-14. Correccion editorial post-importacion
Si la importacion Excel no permite resolver ciertos campos de forma confiable, el sistema debe habilitar la correccion editorial **solo para completar lo faltante**, nunca como fuente alternativa de construccion curricular.

## RN-15. Confirmacion humana obligatoria
Ningun dato importado automaticamente se considera definitivo sin revision y confirmacion explícita del usuario.

## RN-16. Clasificacion minima de fallos de importacion Excel
El sistema debe informar como minimo estas causas:

- archivo Excel no canonico,
- hojas faltantes,
- encabezados invalidos,
- claves cruzadas rotas,
- duplicados,
- datos ambiguos.

---

# 10. Reglas del programa de formación

## RN-18. Datos mínimos del programa
El programa de formación debe registrar como mínimo:

- código del programa,
- nombre del programa.

## RN-19. Unicidad del programa
No debe permitirse duplicar un programa con el mismo código y misma versión lógica, según la política técnica definida.

## RN-20. Relación raíz del programa
El programa de formación es la entidad raíz de la estructura curricular de la Fase 1.

## RN-21. Asociación de competencias
Cada competencia debe pertenecer a un único programa.

## RN-22. Datos mínimos de competencia
Cada competencia debe tener como mínimo:

- código de competencia,
- nombre de la competencia.

## RN-23. Estructura mínima de competencia
Cada competencia debe tener obligatoriamente:

- al menos un resultado de aprendizaje,
- al menos un conocimiento de saber,
- al menos un conocimiento de proceso,
- al menos un criterio de evaluación.

Esta estructura minima aplica al cierre del programa, no al preview ni a la
importacion parcial del Excel canonico. La competencia de etapa practica puede
existir sin resultados, conocimientos ni criterios, y no debe invalidar el
workbook por esa ausencia.

## RN-24. Completitud del programa
El programa solo puede pasar a estado **COMPLETO** cuando:

- tiene código,
- tiene nombre,
- tiene al menos una competencia,
- cada competencia cumple estructura mínima,
- y el usuario confirma la revisión del consolidado.

---

# 11. Reglas de resultados de aprendizaje

## RN-25. Asociación obligatoria
Todo resultado de aprendizaje debe pertenecer a una única competencia.

## RN-26. Descripción obligatoria
No se deben permitir resultados de aprendizaje vacíos.

## RN-27. No duplicidad
No debe permitirse duplicar el mismo resultado exacto dentro de una misma competencia.

---

# 12. Reglas de conocimientos

## RN-28. Separación obligatoria por categoría
Los conocimientos deben registrarse por separado como:

- conocimiento de saber,
- conocimiento de proceso.

## RN-29. Asociación obligatoria
Todo conocimiento debe pertenecer a una única competencia.

## RN-30. Descripción obligatoria
No se deben permitir conocimientos vacíos.

## RN-31. No duplicidad
No deben permitirse conocimientos idénticos dentro de la misma categoría y competencia.

---

# 13. Reglas de criterios de evaluación

## RN-32. Asociación obligatoria
Todo criterio de evaluación debe pertenecer a una única competencia.

## RN-33. Descripción obligatoria
No se deben permitir criterios vacíos.

## RN-34. No duplicidad
No deben permitirse criterios idénticos dentro de la misma competencia.

---

## RN-34A. Pendientes de asignacion desde Excel
Cuando el Excel canonico trae conocimientos o criterios sin competencia
confiable, las filas deben conservarse como pendientes de asignacion manual y no
deben bloquear todo el workbook.

La ausencia de `rap_id`, o un `rap_id` que no pueda resolverse a un resultado,
no convierte por si sola una fila en pendiente si la competencia esta clara.

# 14. Reglas del proyecto formativo

## RN-35. Dependencia del programa
No debe crearse funcionalmente un proyecto formativo sin un programa previamente completo.

## RN-35A. Fuente estructurada del proyecto
El proyecto formativo debe partir de una fuente estructurada tipo matriz/Excel, no de extraccion PDF ni captura manual como via principal.

## RN-36. Datos mínimos del proyecto
El proyecto formativo debe registrar como mínimo:

- código del proyecto,
- nombre del proyecto,
- versión del proyecto,
- al menos una fase,
- al menos una actividad por fase.

## RN-37. Asociación de fases
Cada fase debe pertenecer a un único proyecto.

## RN-38. Asociación de actividades
Toda actividad debe pertenecer obligatoriamente a una fase.

## RN-39. No duplicidad de actividades
No deben permitirse actividades idénticas dentro de la misma fase.

## RN-40. Completitud del proyecto
El proyecto solo puede pasar a estado **COMPLETO** cuando:

- el programa ya está completo,
- el proyecto tiene datos mínimos,
- tiene al menos una fase,
- cada fase tiene al menos una actividad,
- y el usuario confirma la revisión del consolidado.

---

# 15. Reglas de estados del sistema

## RN-41. Estados del programa
El programa de formación debe manejar estos estados:

- BORRADOR
- EN_REVISION
- COMPLETO

## RN-42. Estados del proyecto
El proyecto formativo debe manejar estos estados:

- BLOQUEADO
- BORRADOR
- EN_REVISION
- COMPLETO

## RN-43. Centralización de estados
La lógica de estados no debe estar dispersa ni duplicada en múltiples capas inconsistentes.

---

# 16. Reglas de transición de estados

## RN-44. Inicio en borrador
Todo nuevo registro debe iniciar en estado BORRADOR.

## RN-45. Transición a revisión
Un bloque puede pasar a EN_REVISION cuando ya tenga información mínima cargada y se encuentre listo para revisión humana.

## RN-46. Transición a completo del programa
El programa solo puede pasar a COMPLETO si cumple las reglas de completitud y el usuario confirma su revisión.

## RN-47. Desbloqueo del proyecto
El proyecto solo puede pasar de BLOQUEADO a BORRADOR cuando el programa esté en COMPLETO.

## RN-48. Transición a completo del proyecto
El proyecto solo puede pasar a COMPLETO cuando cumple las reglas de completitud y el usuario confirma su revisión.

## RN-49. Regresión por inconsistencia
Si un programa ya completo es modificado y pierde consistencia, debe regresar a EN_REVISION.

## RN-50. Impacto sobre el proyecto
Si el programa vuelve a EN_REVISION, el sistema debe advertir que el proyecto asociado puede quedar afectado.

---

# 17. Reglas de revisión consolidada

## RN-51. Vista consolidada obligatoria
Antes del cierre del programa o del proyecto, el sistema debe mostrar una vista consolidada editable.

## RN-52. Información visible en revisión
La vista consolidada debe mostrar:

- estructura jerárquica,
- estado por bloque,
- origen del dato.

## RN-53. Origen del dato
Cada dato debe poder identificarse como:

- extraído,
- manual,
- corregido,
- pendiente.

## RN-54. Edición desde consolidado
La vista consolidada debe permitir volver a editar los registros antes del cierre.

---

# 18. Reglas de integridad del dominio

## RN-55. No hijos sin padre
No debe permitirse:

- competencia sin programa,
- resultado sin competencia,
- conocimiento sin competencia,
- criterio sin competencia,
- fase sin proyecto,
- actividad sin fase.

## RN-56. Protección de consistencia
Toda operación de creación, edición o eliminación debe respetar la integridad relacional.

## RN-57. Confirmación de borrado
Toda eliminación debe requerir confirmación explícita.

---

# 19. Reglas de auditoría mínima

## RN-58. Auditoría básica obligatoria
El sistema debe registrar como mínimo:

- creación,
- actualización,
- cierre,
- cambio de estado,
- y eventos relevantes de inconsistencia.

## RN-59. Persistencia de trazabilidad
Toda entidad principal debe conservar fecha de creación, fecha de actualización y estado actual.

---

# 20. Reglas de implementación

## RN-60. Estrategia incremental obligatoria
La aplicación no debe construirse de una sola vez.

Debe implementarse:

- módulo por módulo,
- tarea por tarea,
- respetando dependencias del dominio.

## RN-61. Orden recomendado de implementación
El orden obligatorio para Fase 1 es:

1. modelo de datos,
2. borradores,
3. wizard del programa,
4. extracción del programa,
5. CRUD curricular,
6. revisión y cierre del programa,
7. bloqueo/desbloqueo del proyecto,
8. wizard del proyecto,
9. extracción del proyecto,
10. CRUD de fases y actividades,
11. revisión y cierre del proyecto,
12. auditoría y pruebas.

## RN-62. Prohibición de adelantar fases
No deben implementarse funcionalidades de Fase 2 o posteriores dentro de la Fase 1.

---

# 21. Restricciones técnicas del proyecto

## RN-63. Stack permitido
La implementación debe respetar estas decisiones técnicas:

- Frontend: Next.js + React + TypeScript + Tailwind CSS
- Backend: FastAPI
- Base de datos: PostgreSQL
- Arquitectura: modular por dominio
- Validaciones cercanas al dominio
- Testing mínimo: unitario, integración y end-to-end

## RN-64. No sustitución no autorizada
No se deben introducir stacks alternativos sin decisión explícita del proyecto.

---

# 22. Invariantes del dominio

Estas condiciones deben cumplirse siempre:

- el proyecto no puede habilitarse sin programa completo,
- el sistema no puede perder borradores,
- la extracción automática no equivale a validación humana,
- toda competencia debe tener estructura curricular mínima para cerrar el programa,
- toda fase debe tener actividades para cerrar el proyecto,
- toda vista final debe ser revisable antes del cierre.

---

# 23. Definición de éxito de la Fase 1

La Fase 1 se considera exitosa cuando:

- el programa puede cargarse desde Excel canonico,
- el PDF del programa puede conservarse como evidencia documental,
- el programa puede revisarse y cerrarse,
- el proyecto permanece bloqueado hasta ese momento,
- el proyecto puede cargarse mediante fuente estructurada (Excel/matriz),
- el proyecto puede revisarse y cerrarse,
- todo el avance se guarda en borrador,
- toda la información queda persistida,
- y el sistema deja lista la base estructural para fases posteriores.

---

# 24. Regla de precedencia documental

En caso de conflicto entre documentos del proyecto, el orden de precedencia es:

1. `BUSINESS_RULES.md`
2. `SPECS.md`
3. `DATA_MODEL.md`
4. `USER_STORIES.md`
5. `IMPLEMENTATION_PLAN.md`
6. `CODEX_TASKS.md`

---

# 25. Decisiones cerradas de esta fase

Quedan cerradas para la Fase 1 las siguientes decisiones:

- la UX principal será tipo wizard,
- siempre habrá guardado automático en borrador,
- el sistema soportara PDF como evidencia y Excel canonico como fuente estructurada unica,
- el carril manual deja de existir como modo operativo,
- el proyecto estará bloqueado hasta completar el programa,
- la validación humana será obligatoria antes del cierre,
- el alcance se limitará a la Fase 1,
- la implementación se hará de forma incremental.

## Formato oficial de planeacion pedagogica

- La salida institucional obligatoria es `GPFI-F-134 V05` en `.xlsx`, generada desde la plantilla canónica y almacenada en MinIO.
- La planeación individual materializa una fila por cada asignación única de fase y actividad.
- El consolidado incluye solo planeaciones `COMPLETO`; los borradores se excluyen y se reportan.
- La duración total debe coincidir con horas de trabajo directo más independiente; cualquier diferencia bloquea la generación.
- Modalidad, fecha, clasificación, equipo curricular, regional y centro son obligatorios.
- Saberes SABER y PROCESO se separan, incorporan temáticas adicionales y eliminan duplicados exactos conservando orden estable.

## Múltiples actividades de aprendizaje por actividad de proyecto

- Una `ActividadProyecto` puede asociarse a 1..N `PlaneacionPedagogica` (1:N), permitiendo crear y gestionar múltiples actividades de aprendizaje dentro de la misma actividad de proyecto formativo.
- Cada `PlaneacionPedagogica` integra 1..N Competencias y 1..N Resultados de Aprendizaje (RAP).
- Las horas didácticas se asignan por `PlaneacionPedagogica` y se escriben en la primera fila del bloque correspondientes a cada planeación en la exportación oficial.

## Tipado opcional de tipo_resultado

- `tipo_resultado` es opcional en la matriz del proyecto: la columna puede faltar o la celda puede estar vacía sin bloquear la carga.
- `rap_numero` también es opcional: puede faltar la columna o quedar vacía la celda; `rap_id` continúa siendo el identificador estable del resultado.
- Cuando viene informado, su dominio queda restringido al enum `TipoResultadoProyecto`; se normalizan espacios y mayúsculas durante la carga del Excel canónico y cualquier valor no equivalente es rechazado con error claro indicando hoja, fila y campo.
- No se aplica ninguna regla de inferencia basada en códigos o nombres de competencia; la matriz Excel es la única fuente autoritativa.
- La ausencia de `tipo_resultado` se conserva como `NULL` y no invalida la fila ni la importación.

---

# 26. RBAC, Equipos Ejecutores y Aislamiento de Procesos Curriculares

A partir del refactor de seguridad y control de acceso multiusuario, el sistema adopta una arquitectura de aislamiento basada en:
`RBAC` + `EquipoEjecutor` + `Membership` + `ProcesoCurricular` + `Ownership` + `AccessScopeService`.

## 26.1 Roles del Sistema (`RolUsuario`)
- **SUPERADMIN**: Administrador de plataforma y sistema con visibilidad y control global absoluto.
- **ADMIN**: Administrador pedagógico. Gestiona coordinaciones, especialidades, equipos ejecutores, asignaciones de procesos curriculares y supervisa todos los programas y planeaciones.
- **LIDER_EQUIPO_EJECUTOR**: Instructor líder a cargo de un equipo ejecutor. Requiere asignación obligatoria de coordinación y especialidad. Tiene visibilidad y control exclusivo sobre los procesos asignados a su equipo.
- **USUARIO_ADICIONAL**: Instructor o apoyo vinculado a un equipo ejecutor. Requiere coordinación y especialidad. Accede a los procesos del equipo mientras su membresía esté en estado activo (`activo == True`).

## 26.2 Regla de Aislamiento Estricto por Equipo Ejecutor
- El aislamiento de datos **no** depende únicamente de `coordinacion_id` y `especialidad_id`.
- **Dos líderes de la misma coordinación y de la misma especialidad NO deben ver ni editar las planeaciones o procesos del otro.** Cada líder gestiona exclusivamente los procesos curriculares asignados a su propio equipo ejecutor.
- Toda consulta de flujos, programas, proyectos, borradores y planeaciones pedagógicas valida el alcance mediante `AccessScopeService`.

## 26.3 Ciclo de Vida y Membresía (`EquipoEjecutorMiembro`)
- Un equipo ejecutor agrupa 1 líder y 0..N miembros adicionales (`USUARIO_ADICIONAL`).
- Un `USUARIO_ADICIONAL` solo puede acceder a un proceso curricular si existe un registro `EquipoEjecutorMiembro` con `activo = True` para el equipo ejecutor propietario del proceso. Si el administrador o líder desactiva al miembro (`activo = False`), el acceso se revoca de manera inmediata.

## 26.4 Vinculación y Auto-anclaje de Procesos Curriculares
- La entidad `ProcesoCurricular` correlaciona el `referencia_id` (UUID canónico del borrador/flujo) con su `EquipoEjecutor`.
- Cuando un `LIDER_EQUIPO_EJECUTOR` inicia y guarda un nuevo borrador o flujo de programa:
  - Si el líder tiene 0 equipos ejecutores activos: la solicitud es rechazada con HTTP 422 ("El usuario no tiene un equipo ejecutor activo asignado.").
  - Si el líder tiene exactamente 1 equipo ejecutor activo: el proceso se auto-ancla automáticamente a dicho equipo.
  - Si el líder lidera 2 o más equipos activos: el payload debe indicar explícitamente `equipo_ejecutor_id`. De lo contrario se rechaza con HTTP 422 para evitar ambigüedad en el ownership.
- Si un proceso es creado sin usuario autenticado en entornos de migración/compatibilidad, queda con `equipo_id = NULL` (estado `SIN_ASIGNAR`) y solo es visible y reasignable por roles `ADMIN` o `SUPERADMIN`.
- Si un equipo ejecutor pasa a estado `INACTIVO`, se bloquea el acceso operativo al proceso curricular para el líder y los miembros del equipo (HTTP 403).

## 26.5 Protección Integral contra IDOR
- Todos los endpoints en controladores de programa (`/programas/...`), proyectos (`/proyectos/...`), planeación (`/planeaciones/...`), borradores (`/drafts/...`) y dashboard (`/dashboard/...`) verifican de manera estricta los permisos de acceso antes de leer, crear, modificar o eliminar recursos (`AccessScopeService.require_process_access`, `require_project_access`, `require_planning_access`). Intentos de acceso no autorizados arrojan código HTTP 403 Forbidden.

# 27. Endurecimiento de Seguridad, Sesiones y Autenticación (Sprint RBAC-6)

## 27.1 Revocación Inmediata de Sesiones (`token_version`)
- Cada usuario posee una columna `token_version` (entero incremental) en base de datos.
- Todo JWT emitido incluye el claim `token_version`.
- La dependencia de autenticación (`get_current_user`) compara en cada petición el claim `token_version` del token contra el valor actual en base de datos.
- Las operaciones de logout (`POST /api/v1/auth/logout`) y cambio de contraseña (`POST /api/v1/auth/change-password`) incrementan `token_version` en base de datos, revocando instantáneamente todos los access tokens y refresh tokens emitidos con anterioridad.

## 27.2 Manejo de Tokens en Frontend y Rotación de Refresh Tokens
- El frontend almacena el `access_token` estrictamente en memoria volátil de la aplicación (`inMemoryAccessToken`). No se persiste ningún token en `localStorage` o `sessionStorage`.
- El `refresh_token` se maneja mediante cookies seguras `HttpOnly` (`asgard_refresh_token`), protegidas contra robo mediante ataques XSS.
- Cada invocación a `POST /api/v1/auth/refresh` rota el `refresh_token` y entrega un nuevo `access_token` en memoria.

## 27.3 Prevención de Escalamiento de Privilegios
- Los administradores (`ADMIN`) tienen prohibido crear o asignar el rol `SUPERADMIN` a cualquier usuario (HTTP 403 Forbidden).
- Solo un usuario autenticado con rol `SUPERADMIN` puede asignar dicho rol.
- Líderes de equipo y usuarios adicionales no pueden acceder a endpoints administrativos ni alterar membresías o asignaciones ajenas.

## 27.4 Rate Limiting en Autenticación
- El endpoint de inicio de sesión (`POST /api/v1/auth/login`) implementa una ventana deslizante de rate limiting por dirección IP / correo institucional: un máximo de 5 intentos fallidos por minuto. Al superar el límite, se bloquean intentos adicionales con HTTP 429 Too Many Requests.

---

# 28. Micro-Hardening Final de Seguridad (RBAC-AUTH-FINAL-HARDENING-ASGARD)

## 28.1 Política CSRF y Validación de Origen
- Toda operación mutable basada en cookies (`/api/v1/auth/refresh`, `/api/v1/auth/logout`, `/api/v1/auth/change-password`) está protegida por la dependencia `verify_csrf_origin`.
- Se valida que el encabezado `Origin` (o `Referer` en su defecto) pertenezca estrictamente a la lista de orígenes autorizados (`cors_allow_origin_list`).
- Cualquier solicitud proveniente de un origen no autorizado es rechazada inmediatamente con HTTP 403 Forbidden.
- En entornos de producción y staging, las solicitudes autenticadas con cookie requieren obligatoriamente un origen verificado.

## 28.2 Atributos Centralizados de Cookies
- Nombre canónico: `asgard_refresh_token`.
- Atributos obligatorios: `HttpOnly=True`, `SameSite=Lax`, `Path=/api/v1/auth`.
- En producción y staging, `Secure=True` es forzoso (`effective_cookie_secure`).
- El dominio es parametrizable mediante `AUTH_COOKIE_DOMAIN`.

## 28.3 Rotación Real de Refresh Tokens y Prevención de Replay (OAuth 2.0 / RFC 6749)
- Las sesiones activas se registran en la tabla `user_sessions` identificadas por hash SHA-256 (`refresh_token_hash`), identificador criptográfico único (`jti`) y familia de sesión (`token_family`). No se almacena el refresh token en texto plano.
- **Rotación de un solo uso (Single-use)**: Cada invocación a `/api/v1/auth/refresh` marca la sesión consumida con `revoked_at = now()` y emite una nueva sesión hija dentro de la misma `token_family`.
- **Detección de Replay**: Si se recibe un refresh token cuya sesión ya ha sido revocada:
  1. Se detecta intento de reuso malicioso (replay attack).
  2. Se revocan inmediatamente todas las sesiones de dicha familia (`token_family`).
  3. Se incrementa `user.token_version`, invalidando todos los tokens de acceso del usuario.
  4. Se elimina la cookie y se registra evento de auditoría `REFRESH_TOKEN_REPLAY_DETECTED`.
  5. Se rechaza con HTTP 401 Unauthorized.
- Un usuario inactivo o bloqueado es rechazado de inmediato al intentar refrescar (HTTP 401).

## 28.4 Semántica de Cierre de Sesión y Cambio de Contraseña
- `/api/v1/auth/logout`: Revoca todas las sesiones activas del usuario en base de datos, incrementa `token_version` y limpia la cookie.
- `/api/v1/auth/change-password`: Modifica el hash de contraseña, incrementa `token_version`, revoca todas las sesiones activas en `user_sessions` y limpia la cookie.

## 28.5 Política CORS Restrictiva
- La lista de orígenes permitidos se obtiene de `cors_allow_origins`.
- Queda terminantemente prohibido combinar el wildcard `*` con `allow_credentials=True`. La configuración filtra automáticamente cualquier comodín para evitar que los navegadores bloqueen credenciales o queden expuestas.

## 28.6 Autorización Estricta en Descargas Documentales
- Endpoints dedicados para descargas de evidencia y matrices:
  - `GET /api/v1/programas/{referencia_id}/documentos/programa-pdf`
  - `GET /api/v1/programas/{referencia_id}/documentos/programa-excel`
  - `GET /api/v1/proyectos/{referencia_id}/documentos/proyecto-pdf`
  - `GET /api/v1/proyectos/{referencia_id}/excel`
  - `GET /api/v1/planeaciones/{planeacion_id}/descargar-formato-oficial`
  - `GET /api/v1/planeaciones/proyecto/{proyecto_id}/descargar-formato-oficial`
- Principio Deny-by-default: Un UUID válido nunca concede acceso. Una `storage_key` nunca concede acceso directo.
- Toda descarga valida autorización mediante `AccessScopeService` (`require_process_access`, `can_access_project`, `can_access_planning`).
- Los líderes solo pueden descargar artefactos correspondientes a procesos de sus equipos ejecutores. Intentos entre equipos distintos generan HTTP 403 Forbidden.
- Los administradores y superadministradores conservan acceso institucional global.

## 28.7 Frontend Single-Flight Refresh
- La capa de red del frontend (`authFetch` en `lib/api.ts`) implementa un mecanismo de bloqueo con promesa compartida (`refreshTokenSingleFlight`).
- Múltiples errores 401 simultáneos disparan una sola solicitud a `/auth/refresh`. Todas las peticiones esperan la misma promesa y reintentan con el nuevo token, impidiendo condiciones de carrera frente a la rotación de un solo uso.

## 28.8 Limitación del Rate Limiter en Memoria
- El rate limiter actual opera en memoria por instancia (sliding window).
- **Nota técnica de escalabilidad**: Si el despliegue escala a múltiples réplicas (`replicas > 1`), el estado del rate limiting debe migrarse a un backend compartido (Redis o tabla en base de datos). Para la arquitectura actual de instancia única, la implementación en memoria es suficiente y eficiente.

---

# 29. Cierre Definitivo de Seguridad y Autenticación Obligatoria (RBAC-AUTH-MANDATORY-PRIVATE-ROUTES)

## 29.1 Autenticación Obligatoria en Endpoints Privados
- Queda eliminada la dependencia `get_optional_current_user` en todas las rutas privadas de la API.
- Todo endpoint privado requiere estrictamente `get_current_user` (o `require_roles(...)` que lo extiende).
- Cualquier petición sin encabezado `Authorization: Bearer <token>` válido responde inmediatamente `HTTP 401 Unauthorized`.
- Las verificaciones de `AccessScopeService` se aplican de forma obligatoria e incondicional sobre el usuario autenticado.

## 29.2 Confinamiento del Refresh Token a Cookie HttpOnly
- Los endpoints `/api/v1/auth/login` y `/api/v1/auth/refresh` NO devuelven el `refresh_token` en el payload JSON.
- `TokenResponse` expone únicamente `access_token`, `token_type` y `user`.
- El refresh token viaja exclusivamente a través de la cookie HttpOnly protegida `asgard_refresh_token`.

## 29.3 Consumo Atómico del Refresh Token en PostgreSQL
- Toda consulta de verificación y rotación de sesión en `/api/v1/auth/refresh` ejecuta bloqueo de fila `with_for_update()`.
- Se serializa el acceso concurrente al mismo `jti`. Si dos solicitudes concurrentes intentan rotar el mismo refresh token, una adquiere el bloqueo y rota la sesión; la segunda detecta inmediatamente `revoked_at is not None` y desencadena la revocación de la familia y respuesta `HTTP 401 Unauthorized`.

## 29.4 Sanitización CORS en Manejador Global de Excepciones 500
- El exception handler no controlado para errores HTTP 500 valida si el encabezado `Origin` está explícitamente en `settings.cors_allow_origin_list`.
- Si el origen no es de confianza o no está en la lista blanca, NO se inyecta `Access-Control-Allow-Origin`.

## 29.5 Fail-Fast en Producción y Staging ante Secretos Inseguros
- Validación en tiempo de inicialización de `Settings` (`validate_production_secrets`): si `app_env` es `production` o `staging`, el sistema falla de inmediato (`ValidationError`) si:
  - `jwt_secret_key` utiliza valores por defecto conocidos (`asgard-super-secret-key-change-in-production-2026`, etc.) o tiene menos de 32 caracteres.
  - Las credenciales de MinIO (`storage_access_key` o `storage_secret_key`) usan valores inseguros por defecto (`admin`, `admin123`, `minioadmin`).

## 29.6 TTL Reducido del Access Token
- El tiempo de expiración por defecto del Access Token se reduce a 30 minutos (`jwt_access_token_expire_minutes = 30`), limitando la ventana de exposición en caso de filtración de token de memoria.

---

# 30. Administración Organizacional Multiusuario (SPRINT-B-ADMINISTRACION-ORGANIZACIONAL-ASGARD)

## 30.1 Roles Canónicos y Jerarquía Estricta
- El sistema restringe las cuentas a los cuatro roles oficiales de dominio: `SUPERADMIN`, `ADMIN`, `LIDER_EQUIPO_EJECUTOR`, `USUARIO_ADICIONAL`.
- No se permiten roles fuera del enum ni combinaciones arbitrarias.
- Jerarquía de administración: Un usuario con rol `ADMIN` no puede crear, editar, listar en detalle, bloquear, desactivar ni resetear credenciales de un usuario con rol `SUPERADMIN` (responde HTTP 403 Forbidden).
- Solo un `SUPERADMIN` puede administrar a otros usuarios con rol `SUPERADMIN`.

## 30.2 Invariantes de Usuario y Asociación Curricular
- Todo usuario con rol `LIDER_EQUIPO_EJECUTOR` o `USUARIO_ADICIONAL` requiere obligatoriamente una coordinación académica activa (`coordinacion_id`) y una especialidad activa (`especialidad_id`).
- La especialidad seleccionada debe pertenecer estrictamente a la coordinación asignada.
- Los usuarios de rol directivo (`SUPERADMIN`, `ADMIN`) pueden operar a nivel institucional global sin requerir coordinación ni especialidad fija.

## 30.3 Ciclo de Vida del Usuario y Revocación Inmediata de Sesiones
- El estado del usuario soporta los valores: `ACTIVO`, `INACTIVO`, `BLOQUEADO`.
- Intentos de inicio de sesión de usuarios no activos son rechazados de inmediato (`HTTP 401 Unauthorized`).
- Al inactivar o bloquear a un usuario, o al ejecutar un reseteo administrativo de contraseña, el sistema invalida atómicamente todas sus sesiones en base de datos (`revoked_at = now()`) e incrementa su `token_version` en PostgreSQL.
- Los tokens JWT emitidos con versiones anteriores quedan revocados de forma inmediata en las verificaciones centrales.

## 30.4 Política de Primer Acceso y Clave Temporal
- Al crearse una cuenta de usuario o al resetear administrativamente su contraseña, el flag `debe_cambiar_password` se establece en `True`.
- Un usuario con `debe_cambiar_password == True` tiene bloqueado el acceso a cualquier endpoint del sistema (responde HTTP 403 Forbidden), con excepción estricta de la lista blanca de autenticación (`/auth/me`, `/auth/change-password`, `/auth/refresh`, `/auth/logout`).
- La pantalla muestra un modal obligatorio y no cerrable que fuerza a ingresar la clave actual y una nueva contraseña de al menos 8 caracteres con confirmación idéntica.
- Tras completar el cambio de clave exitosamente, se borra el flag `debe_cambiar_password = False`, se incrementa `token_version` y se revocan sesiones previas.

## 30.5 Integridad del Catálogo de Coordinaciones y Especialidades
- Los códigos de coordinación y especialidad deben ser alfanuméricos en mayúsculas y únicos en el sistema.
- Guardias de integridad referencial activa:
  - Una coordinación no puede ser inactivada si cuenta con especialidades activas vinculadas.
  - Una especialidad no puede ser inactivada si cuenta con equipos ejecutores activos vinculados.

## 30.6 Equipos Ejecutores y Sincronización Transaccional de Procesos
- Un equipo ejecutor requiere un líder activo con rol `LIDER_EQUIPO_EJECUTOR` cuya coordinación y especialidad coincidan con las del equipo.
- Los miembros de apoyo deben tener rol `USUARIO_ADICIONAL` y pertenecer a la misma coordinación y especialidad.
- Sincronización atómica de procesos: Cuando el administrador cambia el líder de un equipo ejecutor (`PATCH /api/v1/equipos/{equipo_id}` con nuevo `lider_id`), el backend actualiza de forma transaccional la columna `usuario_lider_id` en todos los registros de `procesos_curriculares` asignados a dicho equipo, garantizando coherencia inmediata en `AccessScopeService`.

## 30.7 Intactibilidad del Dominio Curricular
- La administración organizacional opera de manera desacoplada de la lógica pedagógica: no se mutan modelos ni estructuras de `Programa`, `Proyecto`, `PlaneacionPedagogica` ni la generación oficial del formato `GPFI-F-134 V05`.

---

# 31. Supervisión Jerárquica Institucional, Visor de Auditoría y Verificación E2E (SPRINT-C-SUPERVISION-AUDIT-E2E-ASGARD)

## 31.1 Supervisión Jerárquica y Panel Directivo
- El panel de supervisión directiva consolida la trazabilidad institucional bajo la estructura jerárquica estricta: `Coordinación -> Especialidad -> Programa / Proceso -> Proyecto -> Equipo Ejecutor -> Líder -> Planeaciones / Estado`.
- Los roles autorizados para consultar este nivel de agregación institucional son exclusivamente `SUPERADMIN` y `ADMIN`. Los roles operativos (`LIDER_EQUIPO_EJECUTOR`, `USUARIO_ADICIONAL`) reciben `HTTP 403 Forbidden`.
- El panel no sustituye el dashboard operativo del líder (`/api/v1/dashboard/{referencia_id}`), el cual permanece intacto para la gestión individual de borradores.
- Métricas consolidadas en tiempo real:
  - Total de procesos curriculares activos y porcentaje global de avance institucional.
  - Procesos sin equipo ejecutor asignado (huérfanos de gestión directiva).
  - Tasa de completitud de planeaciones pedagógicas oficiales.
  - Distribución agregada de estados de programa y proyecto (`BORRADOR`, `EN_REVISION`, `COMPLETO`).
- Los filtros en cascada (`coordinacion_id`, `especialidad_id`, `equipo_id`, `estado_programa`, `estado_proyecto`, `solo_sin_asignar`, `search`) aplican de forma reactiva tanto al listado paginado como al recálculo de tarjetas resumen institucionales.

## 31.2 Visor Institucional de Auditoría Inmutable
- Todos los eventos de auditoría (`EventoAuditoria`) incorporan la identificación explícita del actor del cambio (`actor_usuario_id`), correlacionada con el proceso curricular (`referencia_id`).
- El visor de auditoría es estrictamente de solo lectura:
  - Solo los roles `SUPERADMIN` y `ADMIN` pueden consultar el log de auditoría.
  - Queda terminantemente prohibido cualquier endpoint o mutación que permita modificar o eliminar registros de auditoría (`HTTP 405 Method Not Allowed` ante `DELETE` o `PATCH`).
- Sanitización y Redacción de Secretos en Payload:
  - Todo payload de auditoría (`detalle`) es saneado recursivamente antes de su serialización JSON.
  - Claves sensibles que contengan o coincidan con patrones (`password`, `token`, `secret`, `cookie`, `key`, `credencial`, `hash`) son ofuscadas irrevocablemente a `[REDACTED]`.
  - La inspección forense en la interfaz institucional permite visualizar el detalle JSON formateado con resaltado de sintaxis y búsqueda rápida de eventos por actor, entidad, acción y rango de fechas.

## 31.3 Cobertura y Verificación E2E de Flujo Completo
- La plataforma cuenta con una suite integral de pruebas End-to-End basada en Playwright que verifica los 4 roles canónicos del sistema:
  - `SUPERADMIN`: Control global de usuarios, jerarquía institucional, catálogo organizacional y visor de auditoría.
  - `ADMIN`: Gestión de coordinación, especialidades, equipos ejecutores y supervisión jerárquica sin privilegios sobre `SUPERADMIN`.
  - `LIDER_EQUIPO_EJECUTOR`: Aislamiento estricto de ámbito (`AccessScopeService`), flujo completo de Programa -> Proyecto -> Planeación Pedagógica Integrada -> Generación de formato oficial GPFI-F-134 V05 en MinIO.
  - `USUARIO_ADICIONAL`: Acceso restringido como miembro de apoyo sin permisos de mutación administrativa u horizontal sobre otros equipos.
- Validación E2E del flujo de primer acceso: usuarios con flag `debe_cambiar_password = true` deben completar obligatoriamente el cambio de credenciales antes de interactuar con cualquier módulo de la aplicación.





