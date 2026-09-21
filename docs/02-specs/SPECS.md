# SPECS.md
## Proyecto: Aplicación web para construcción de guías de aprendizaje SENA
## Fase: 1
## Estado: Ready for implementation
## Última actualización: [YYYY-MM-DD]

---

## Decision funcional TASK-UNICO-CARRIL

Desde esta refactorizacion integral, el sistema opera con un unico carril:

- el Excel canonico `.xlsx` es la unica fuente estructurada activa para programa y proyecto;
- el PDF queda exclusivamente como evidencia documental en MinIO;
- no se permite el carril manual como modo operativo;
- las tareas TASK-18, TASK-19 y siguientes quedan reinterpretadas.

## Decision funcional REFACTOR-FLUJO-PROGRAMA-PROYECTO

- El paso `datos-programa` queda eliminado del wizard, navegacion, tipos, tests y documentacion.
- El wizard del programa inicia en `origen-documental`, continua en `estructura-curricular` y cierra en `revision-programa`.
- El origen documental conserva PDF evidencia y Excel canonico; tras importacion confirmada muestra un resumen compacto y abre competencias en una modal paginada.
- La estructura curricular usa selector/filtro de competencia y evita render masivo; conocimientos y criterios se seleccionan progresivamente antes de mostrarse.
- El wizard del proyecto inicia en `fuente-proyecto`; no existe `datos-proyecto` como paso manual.
- Los documentos del proyecto se guardan en `proyectos-formativos/{referencia_id}/documentos/...` y los Excel en `proyectos-formativos/{referencia_id}/excel/...`.

## Decision funcional DASHBOARD-MAESTRO-ASGARD

- La home `/` es el dashboard maestro ASGARD.
- El wizard del programa se abre desde `/programa`.
- El dashboard consume `GET /api/v1/dashboard/{referencia_id}` para estado agregado, reglas de habilitacion, metricas y mapa navegable.
- El proyecto solo queda disponible si el programa esta `COMPLETO`.
- La planeacion pedagogica solo queda disponible si programa y proyecto estan `COMPLETO`.
- El dashboard muestra metricas de programa, proyecto y planeacion derivadas de persistencia, no de estado local.
- El mapa navegable expone nodos de programa, estructura curricular, proyecto y planeacion con enlaces activos solo cuando el modulo esta habilitado.

## Decision funcional ASISTENTE-GUIADO-TRANSVERSAL

- Los wizards de programa, proyecto y planeacion pedagogica muestran un asistente flotante, colapsable y reutilizable.
- El asistente presenta titulo, mensaje, severidad, checklist y CTA sugerido.
- El motor de guia calcula mensajes desde estado real: paso actual, importaciones, cierres, disponibilidad de proyecto y acceso de planeacion.
- Las advertencias entre wizards deben reflejar las reglas reales: proyecto requiere programa `COMPLETO`; planeacion requiere programa y proyecto `COMPLETO`.
- El asistente persiste de forma ligera preferencias de UX, como estado colapsado.
- El asistente no sustituye endpoints, validadores ni confirmaciones de cierre.

---

# 1. Resumen

Este documento define la especificación funcional y técnica de la Fase 1 del sistema para construcción de guías de aprendizaje SENA.

La Fase 1 debe permitir:

- cargar información del programa de formación desde Excel canónico,
- cargar información del proyecto formativo desde fuente estructurada,
- conservar PDF como evidencia documental cuando exista,
- importar datos desde Excel canonico cuando se use fuente estructurada,
- permitir correccion post-importacion SOLO para completar lo estrictamente faltante sin reactivar un carril manual,
- guardar automáticamente el avance en borrador,
- revisar y validar la información,
- bloquear el proyecto hasta completar el programa,
- centralizar el acceso desde un dashboard maestro con metricas y mapa navegable,
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

- Permitir el cargue asistido desde Excel canonico del programa.
- Permitir el cargue asistido desde fuente estructurada del proyecto.
- Permitir el cargue asistido desde fuente estructurada del proyecto.
- Permitir la gestión completa de competencias y su estructura curricular.
- Validar la completitud del programa antes de habilitar el proyecto.
- Permitir la carga del proyecto formativo desde fuente estructurada.
- Permitir la gestión de fases y actividades del proyecto.
- Validar la completitud del proyecto antes de cerrar la Fase 1.
- Centralizar acceso, progreso y bloqueos en el dashboard maestro.
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
- revisar la informacion,
- cerrar el programa,
- habilitar el proyecto,
- revisar y cerrar el proyecto.

## 5.2 Actor secundario
**Sistema de almacenamiento documental**

Responsable de:

- recibir archivos PDF,
- validar que sean procesables,
- almacenar como evidencia documental en MinIO,
- y dejar metadata de validacion en el borrador.

---

# 6. Supuestos del sistema

- El usuario cuenta con documentos fuente o con la matriz Excel canonica diligenciada.
- Los PDFs se almacenan como evidencia documental; no se asume extraccion curricular desde ellos.
- La revision humana es obligatoria antes de cerrar cualquier bloque.
- El programa de formación es el bloque padre de la estructura de Fase 1.
- El proyecto formativo solo se habilita cuando el programa ya está completo.

---

# 7. Flujo funcional principal

## Paso 1. Inicio
El usuario puede:

- iniciar un nuevo proceso,
- continuar un borrador existente.

## Paso 2. Origen documental del programa
El usuario sube el PDF del programa como evidencia documental y carga el Excel canonico del programa como fuente estructurada.

## Paso 3. Importacion estructurada del programa
El sistema importa desde Excel canónico:

- datos del programa,
- competencias,
- resultados,
- conocimientos de saber,
- conocimientos de proceso,
- criterios.

Tras confirmar la importacion, el usuario ve un resumen compacto del workbook y puede abrir una modal paginada para revisar competencias importadas.

## Paso 4. Estructura curricular del programa
El usuario selecciona una competencia para trabajar en contexto. Resultados se muestran con la competencia seleccionada; conocimientos y criterios se eligen progresivamente desde selectores antes de renderizarse.

## Paso 5. Revisión del programa
El sistema debe mostrar el consolidado del programa antes del cierre.

## Paso 6. Cierre del programa
El sistema debe validar completitud y, si procede, marcar el programa como COMPLETO.

## Paso 7. Habilitación del proyecto
Solo cuando el programa esté completo, el sistema debe habilitar el proyecto formativo.

## Paso 8. Fuente del proyecto
El usuario sube el PDF del proyecto como evidencia documental y carga la matriz Excel del proyecto como fuente estructurada.

## Paso 9. Importacion estructurada del proyecto
El sistema importa desde fuente estructurada (Excel/matriz):

- datos del proyecto,
- fases,
- actividades.

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
El sistema debe permitir subir un archivo PDF del programa como evidencia documental.

### RF-05. Validar formato del PDF del programa
El sistema debe verificar que el archivo subido sea un PDF valido.

### RF-06. Importar datos del programa desde Excel canonico
El sistema debe importar desde Excel canonico:

- codigo del programa,
- nombre del programa,
- competencias,
- resultados,
- conocimientos de saber,
- conocimientos de proceso,
- criterios.

### RF-07. Correccion post-importacion de lo faltante
Si la importacion Excel no resuelve ciertos campos de forma confiable, el sistema debe permitir correccion puntual SOLO de lo faltante, sin convertirlo en carril manual de entrada.

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
El sistema debe permitir subir un archivo PDF del proyecto como evidencia documental.

### RF-22. Validar formato del PDF del proyecto
El sistema debe verificar que el archivo subido sea un PDF valido.

### RF-23. Importar datos del proyecto desde fuente estructurada
El sistema debe importar desde Excel/matriz:

- código del proyecto,
- nombre del proyecto,
- versión del proyecto,
- fases,
- actividades.

### RF-24. Correccion post-importacion del proyecto
Si la importacion no resuelve ciertos campos de forma confiable, el sistema debe permitir correccion puntual SOLO de lo faltante, sin convertirlo en carril manual de entrada.

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

> TASK-08.5 deja el PDF como evidencia documental. TASK-UNICO-CARRIL elimina
> el carril manual: Excel canonico es la unica fuente estructurada para programa
> y proyecto.

## 13.1 Objetivo de carga del programa
El sistema debe permitir cargar el PDF del programa como evidencia documental
en MinIO. No se realiza extraccion curricular desde el PDF.

El sistema debe permitir importar datos del programa desde Excel canonico `.xlsx`
mediante preview y confirmacion explícita.

## 13.2 Objetivo de carga del proyecto
El sistema debe permitir cargar el PDF del proyecto como evidencia documental
en MinIO. No se realiza extraccion curricular desde el PDF.

El sistema debe permitir importar datos del proyecto desde fuente estructurada
tipo Excel/matriz. Los documentos del proyecto usan el prefijo MinIO
`proyectos-formativos/{referencia_id}/documentos/...` y los Excel usan
`proyectos-formativos/{referencia_id}/excel/...`.

## 13.3 Manejo de fallos
Cuando la importacion Excel no pueda resolver un campo de forma confiable, el sistema debe:

1. informar el motivo,
2. marcar el campo como pendiente,
3. habilitar correccion post-importacion SOLO para completar lo faltante sin reactivar captura manual como fuente.

## 13.4 Motivos mínimos de fallo
- archivo Excel no canonico
- hojas faltantes
- encabezados invalidos
- claves cruzadas rotas
- duplicados
- contenido ambiguo

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

## CA-02
El programa puede iniciarse desde Excel canonico; el PDF queda como soporte documental.

## CA-03
El sistema guarda automáticamente el avance en borrador.

## CA-04
El programa no puede cerrarse si no tiene estructura curricular mínima.

## CA-05
El proyecto permanece bloqueado mientras el programa no esté completo.

## CA-06
El proyecto puede iniciarse cuando el programa esté completo.

## CA-07
El proyecto puede iniciarse cuando el programa esté completo.

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
- gestionar la estructura curricular,
- validar y cerrar el programa,
- bloquear y habilitar el proyecto correctamente,
- crear y revisar el proyecto,
- guardar borradores del proyecto,
- gestionar fases y actividades,
- validar y cerrar el proyecto,
- y mantener trazabilidad básica del proceso.

## Exportacion GPFI-F-134 V05

- Plantilla: `backend/src/infrastructure/templates/planeacion/GPFI-F-134V05.xlsx`.
- Hojas: `Instrucciones` intacta y `FASE` diligenciada.
- Encabezado: fecha, programa, modalidad, código/versión, proyecto, equipo curricular, regional y centro.
- Tabla `FASE`: columnas A:P según fase, actividad, competencia, RAP, saberes, criterios y campos complementarios.
- Endpoints individuales: `POST/GET /api/v1/planeaciones/{planeacion_id}/generar-formato-oficial` y `descargar-formato-oficial`.
- Endpoints consolidados: `POST/GET /api/v1/planeaciones/proyecto/{proyecto_id}/generar-formato-oficial` y `descargar-formato-oficial`.
- La descarga usa `StreamingResponse`, content type OOXML y `Content-Disposition` UTF-8.

---

# 21. Especificación Técnica de Micro-Hardening de Seguridad (RBAC-AUTH-FINAL-HARDENING-ASGARD)

## 21.1 Protección CSRF y Validación de Origen
- Endpoints mutables dependientes de cookie (`POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout`, `POST /api/v1/auth/change-password`) aplican `verify_csrf_origin`.
- Comprobación estricta de encabezados `Origin` y `Referer` contra `cors_allow_origin_list`.
- Rechazo inmediato HTTP 403 Forbidden ante orígenes no permitidos o faltantes en producción/staging.

## 21.2 Gestión de Sesiones y Rotación de Refresh Tokens (RFC 6749)
- Modelo `UserSession` en base de datos:
  - `id`: UUID (PK).
  - `usuario_id`: UUID (FK `usuarios.id`, cascada).
  - `refresh_token_hash`: String(64) SHA-256 del token (indexado, sin texto plano).
  - `token_family`: UUID (indexado).
  - `jti`: UUID (único, indexado).
  - `expires_at`: DateTime con zona horaria.
  - `revoked_at`: DateTime con zona horaria (nullable, indexado).
  - `ip_address`: String(45) (nullable).
  - `user_agent`: Text (nullable).
- **Mecanismo Anti-Replay**:
  - Al refrescar, se marca la sesión actual con `revoked_at = now()` y se genera un nuevo par de tokens con nuevo `jti` y misma `token_family`.
  - Si un token ya revocado intenta refrescar: se detecta ataque de replay, se revocan todas las sesiones de la familia, se incrementa `user.token_version` invalidando todos los access tokens emitidos, y se retorna HTTP 401 Unauthorized.

## 21.3 Cookies y CORS
- Cookie `asgard_refresh_token`:
  - `HttpOnly`: true
  - `SameSite`: "lax"
  - `Path`: "/api/v1/auth"
  - `Secure`: true (producción/staging via `effective_cookie_secure`)
  - `Domain`: configurable via `AUTH_COOKIE_DOMAIN`
- CORS: `allow_credentials=True` con orígenes explícitos. Se descarta automáticamente `*` de la lista de orígenes.

## 21.4 Endpoints de Descarga Protegidos
- `GET /api/v1/programas/{referencia_id}/documentos/programa-pdf`
- `GET /api/v1/programas/{referencia_id}/documentos/programa-excel`
- `GET /api/v1/proyectos/{referencia_id}/documentos/proyecto-pdf`
- `GET /api/v1/proyectos/{referencia_id}/excel`
- `GET /api/v1/planeaciones/{planeacion_id}/descargar-formato-oficial`
- `GET /api/v1/planeaciones/proyecto/{proyecto_id}/descargar-formato-oficial`
- Todos los endpoints validan la identidad con `get_current_user` y el alcance de permisos con `AccessScopeService`. Si el usuario no pertenece al equipo ejecutor ni posee rol institucional (SUPERADMIN/ADMIN), la descarga es rechazada con HTTP 403 Forbidden.

## 21.5 Single-Flight en Cliente Web
- `authFetch` en frontend gestiona un singleton de refresco (`refreshTokenSingleFlight`).
- Las peticiones concurrentes que fallen con 401 esperan la resolución de una única solicitud de rotación y reintentan secuencialmente con el nuevo bearer token en memoria.

---

# 22. Especificación de Cierre Definitivo de Seguridad (RBAC-AUTH-MANDATORY-PRIVATE-ROUTES)

## 22.1 Autenticación Obligatoria en Rutas Privadas
- Se erradica `get_optional_current_user` en todos los controladores privados (`dashboard`, `drafts`, `programa_documentos`, `programa_excel`, `programa_cierre`, `competencias`, `resultados_aprendizaje`, `conocimientos_saber`, `conocimientos_proceso`, `criterios`, `pendientes_curriculares`, `proyecto_gate`, `proyecto_cargue`, `proyecto_documentos`, `proyecto_excel`, `proyecto_cierre`, `planeacion`, `equipos`).
- Todo endpoint privado declara `current_user: Annotated[Usuario, Depends(get_current_user)]`. Solicitudes sin token Bearer válido reciben `401 Unauthorized`.

## 22.2 Refresh Token Exclusivo en Cookie
- `/api/v1/auth/login` y `/api/v1/auth/refresh` emiten `TokenResponse` con:
  ```json
  {
    "access_token": "<jwt>",
    "token_type": "bearer",
    "user": { ... }
  }
  ```
- El `refresh_token` nunca se incluye en el cuerpo JSON; se transporta únicamente en la cookie `asgard_refresh_token` (`HttpOnly=True`).

## 22.3 Consumo Atómico de Refresh Token con Bloqueo de Fila
- En `/api/v1/auth/refresh`, la consulta de sesión ejecuta:
  ```python
  select(UserSession).where(UserSession.jti == jti).with_for_update()
  ```
  y ante detección de reuso de token revocado (`revoked_at is not None`), bloquea y revoca todas las sesiones de la familia:
  ```python
  select(UserSession).where(UserSession.token_family == user_sess.token_family, UserSession.revoked_at.is_(None)).with_for_update()
  ```
  garantizando atomicidad a nivel de PostgreSQL y evitando que múltiples peticiones concurrentes roten simultáneamente el mismo token.

## 22.4 Manejador de Errores 500 y Sanitización CORS
- El manejador global para `Exception` no controlada verifica `origin and origin in settings.cors_allow_origin_list` antes de incluir `Access-Control-Allow-Origin: <origin>`.
- Si el origen no está en la lista blanca de CORS, no se inyecta la cabecera.

## 22.5 Fail-Fast de Configuración en Producción y Staging
- `Settings.validate_production_secrets` intercepta la inicialización de la aplicación y rechaza el arranque si `app_env in ('production', 'staging')` y se detectan:
  - Claves JWT inseguras o por defecto (`asgard-super-secret-key-change-in-production-2026`, longitud < 32).
  - Credenciales MinIO inseguras (`admin`, `admin123`, `minioadmin`).

## 22.6 TTL de Access Token
- Configuración por defecto: `jwt_access_token_expire_minutes = 30`.

---

# 23. Especificación de Administración Organizacional Multiusuario (SPRINT-B-ADMINISTRACION-ORGANIZACIONAL-ASGARD)

## 23.1 Endpoints de Administración de Usuarios
- `POST /api/v1/auth/users`: Registra usuario nuevo. Requiere rol `SUPERADMIN` o `ADMIN`. `ADMIN` no puede crear cuentas con rol `SUPERADMIN`. Valida confirmación de contraseña, unicidad de correo institucional, coordinación y especialidad activas obligatorias para `LIDER_EQUIPO_EJECUTOR` y `USUARIO_ADICIONAL`. Establece `debe_cambiar_password = true`.
- `GET /api/v1/auth/users`: Listado paginado con filtros (`page`, `page_size`, `search`, `role`, `estado`, `coordinacion_id`, `especialidad_id`). `ADMIN` no recibe ni puede ver detalles de cuentas `SUPERADMIN`.
- `GET /api/v1/auth/users/{id}`: Detalle completo de usuario. `ADMIN` bloqueado ante `SUPERADMIN`.
- `PATCH /api/v1/auth/users/{id}`: Edición de nombre, apellido, roles, coordinación, especialidad y área.
- `PATCH /api/v1/auth/users/{id}/estado`: Transición de estado (`ACTIVO`, `INACTIVO`, `BLOQUEADO`). Revoca atómicamente sesiones e incrementa `token_version`.
- `POST /api/v1/auth/users/{id}/reset-password`: Reseteo administrativo de clave con contraseña temporal autogenerada o manual. Establece `debe_cambiar_password = true`, revoca sesiones previas e incrementa `token_version`.
- `GET /api/v1/auth/me`: Retorna el perfil completo del usuario autenticado (incluido en whitelist de primer acceso).

## 23.2 Endpoints de Coordinaciones y Especialidades
- `GET /api/v1/coordinaciones`: Catálogo con contadores de especialidades y equipos.
- `POST /api/v1/coordinaciones`: Creación con código alfanumérico en mayúsculas único.
- `PATCH /api/v1/coordinaciones/{id}`: Actualización de datos o estado. Inactivación rechazada si existen especialidades activas vinculadas.
- `GET /api/v1/coordinaciones/{id}/especialidades`: Listado de especialidades filtradas por coordinación (`solo_activas=true` opcional).
- `POST /api/v1/coordinaciones/{id}/especialidades`: Creación de especialidad bajo coordinación activa.
- `PATCH /api/v1/especialidades/{id}`: Actualización o cambio de estado. Inactivación rechazada si existen equipos ejecutores activos vinculados.

## 23.3 Endpoints de Equipos Ejecutores y Procesos
- `GET /api/v1/equipos`: Listado paginado de equipos ejecutores (`items`, `total`, `page`, `page_size`, `total_pages`).
- `POST /api/v1/equipos`: Creación validando líder con rol `LIDER_EQUIPO_EJECUTOR`, activo y de la misma coordinación/especialidad.
- `PATCH /api/v1/equipos/{id}`: Edición de equipo. Al cambiar `lider_id`, ejecuta una transacción que actualiza `usuario_lider_id` en todos los `procesos_curriculares` asignados a dicho equipo.
- `POST /api/v1/equipos/{id}/miembros`: Vinculación de `USUARIO_ADICIONAL` activo de la misma coordinación/especialidad.
- `PATCH /api/v1/equipos/{id}/miembros/{usuario_id}`: Activación/desactivación de membresía de apoyo.

## 23.4 Interfaz de Usuario y Flujo de Primer Acceso
- `AdminWorkspace`: Módulo unificado con pestañas institucionales:
  1. **Usuarios y Credenciales**: Tabla paginada con búsqueda, filtros, insignias de estado, acciones rápidas de edición, cambio de estado y reseteo de clave.
  2. **Coordinaciones & Especialidades**: Vista dividida (dual-pane) con creación, edición y activación/inactivación protegida.
  3. **Equipos Ejecutores & Procesos**: Cuadrícula de equipos, asignación de líderes, gestión de miembros de apoyo y asignación de procesos curriculares huérfanos.
- `ForceChangePasswordDialog`: Modal no cancelable montado globalmente en el dashboard maestro cuando `user.debe_cambiar_password == true`. Exige ingresar clave actual y nueva contraseña de al menos 8 caracteres con confirmación idéntica antes de desbloquear el acceso a la plataforma.

---

# 24. Especificación de Supervisión Jerárquica Institucional, Visor de Auditoría y Verificación E2E (SPRINT-C-SUPERVISION-AUDIT-E2E-ASGARD)

## 24.1 Endpoints del Dashboard Administrativo Jerárquico
- `GET /api/v1/admin/dashboard/resumen`:
  - Retorna métricas cuantitativas consolidadas (`total_procesos`, `procesos_sin_asignar`, `programas_completos`, `proyectos_completos`, `planeaciones_totales`, `planeaciones_completas`, `porcentaje_avance_global`).
  - Parámetros de consulta opcionales: `coordinacion_id`, `especialidad_id`, `equipo_id`, `estado_programa`, `estado_proyecto`, `solo_sin_asignar`, `search`.
  - Roles autorizados: `SUPERADMIN`, `ADMIN`.
- `GET /api/v1/admin/dashboard/procesos`:
  - Retorna listado paginado de procesos con resolución relacional completa (`referencia_id`, coordinación, especialidad, programa, proyecto, equipo ejecutor, líder asignado, contadores de planeaciones y estado global).
  - Parámetros de consulta: `page`, `page_size`, `coordinacion_id`, `especialidad_id`, `equipo_id`, `estado_programa`, `estado_proyecto`, `solo_sin_asignar`, `search`.
  - Roles autorizados: `SUPERADMIN`, `ADMIN`.
- `GET /api/v1/admin/dashboard/procesos/{referencia_id}`:
  - Retorna vista en profundidad (drill-down) del proceso curricular: configuración del borrador, miembros del equipo, planeaciones pedagógicas y enlaces a artefactos documentales generados.
  - Roles autorizados: `SUPERADMIN`, `ADMIN`.

## 24.2 Endpoints del Visor Institucional de Auditoría
- `GET /api/v1/admin/audit`:
  - Retorna historial paginado de eventos de auditoría ordenado descendentemente por `fecha_evento`.
  - Parámetros de consulta: `page`, `page_size`, `actor_id`, `accion`, `entidad`, `referencia_id`, `fecha_desde`, `fecha_hasta`.
  - Cada evento incluye: `id`, `fecha_evento`, `accion`, `entidad`, `registro_id`, `referencia_id`, `ip_origen`, `actor` (`id`, `email`, `nombre_completo`, `roles`) y `detalle` saneado (sin secretos ni contraseñas).
  - Roles autorizados: `SUPERADMIN`, `ADMIN`.
- `GET /api/v1/admin/audit/{event_id}`:
  - Retorna detalle JSON completo del evento con payload formateado e información forense ampliada.
  - Roles autorizados: `SUPERADMIN`, `ADMIN`.
- Inmutabilidad estricta: No existen endpoints de modificación (`DELETE`, `PATCH`, `PUT`) para el log de auditoría. Peticiones HTTP en estos verbos responden `HTTP 405 Method Not Allowed`.

## 24.3 Frontend de Supervisión y Auditoría
- Componentes de Supervisión:
  - `SummaryCards`: Tarjetas reactivas de KPIs con soporte de estado vacío y alertas sobre procesos sin equipo asignado.
  - `ProcessFilters`: Filtros en cascada con selectores dinámicos de coordinación, especialidad, equipo y estados curriculares.
  - `ProcessesTable`: Tabla institucional paginada con insignias de estado, barras de progreso y acción de inspección.
  - `ProcessDetailDrawer`: Drawer lateral que expone el detalle del proceso, asignación de equipo y planeaciones vinculadas.
- Componentes de Auditoría:
  - `AuditFilters`: Búsqueda por texto libre, filtros de acción (`CREACION`, `MODIFICACION`, `ELIMINACION`, `LOGIN`, `LOGOUT`), entidad y rango de fechas.
  - `AuditTable`: Tabla de auditoría con identificación de actor, acción etiquetada y botón de inspección técnica.
  - `AuditDetailDialog`: Modal con visor formateado de payload JSON y copiado seguro al portapapeles.
- Pestañas en `AdminWorkspace`: Integración de `Supervisión` y `Auditoría` junto a las existentes (`Usuarios`, `Organización`, `Equipos`).

## 24.4 Arquitectura y Especificación de Pruebas E2E (Playwright)
- Configuración: Playwright configurado en `frontend/playwright.config.ts` apuntando a `http://localhost:3000`.
- Especificaciones de prueba:
  - `auth.spec.ts`: Login para los 4 roles, bloqueo por rol, forzado de cambio de clave para usuarios con `debe_cambiar_password = true`, y deslogueo con destrucción de cookies HttpOnly.
  - `supervision-audit.spec.ts`: Visualización de tarjetas KPI, filtrado reactivo de procesos, inspección drawer, visor de auditoría, paginación y modal de inspección de payload saneado.
  - `curricular-flow.spec.ts`: Flujo completo desde creación/selección de programa, confirmación de matriz Excel estructurada, desbloqueo y confirmación de proyecto formativo, planeación pedagógica integrada multi-RAP y exportación oficial GPFI-F-134 V05 en MinIO.




