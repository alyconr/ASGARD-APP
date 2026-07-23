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
