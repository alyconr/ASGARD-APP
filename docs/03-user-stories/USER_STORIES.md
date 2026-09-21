# USER_STORIES.md
## Proyecto: Aplicación web para construcción de guías de aprendizaje SENA
## Fase: 1
## Última actualización: [YYYY-MM-DD]

## Decision funcional TASK-UNICO-CARRIL

Las historias de cargue se reinterpretan asi desde esta refactorizacion:

- HU-01: ya no ofrece MANUAL como opcion de entrada.
- HU-03 y HU-04: conservan PDF solo como soporte documental en MinIO.
- HU-05: deja de ejecutarse desde PDF para el programa; se reemplaza por importacion Excel.
- HU-06: se limita a completar lo estrictamente faltante, no como fuente alternativa.
- HU-17, HU-18, HU-19: se reinterpretan para proyecto orientado a Excel/matriz.
- `datos-programa` y `datos-proyecto` no existen como pasos de entrada manual.
- La revision de competencias importadas se hace desde resumen compacto y modal paginada.
- La estructura curricular se trabaja por competencia seleccionada, con conocimientos y criterios elegidos progresivamente.
- El proyecto usa prefijos MinIO `proyectos-formativos/{referencia_id}/documentos/...` y `proyectos-formativos/{referencia_id}/excel/...`.

## Decision funcional DASHBOARD-MAESTRO-ASGARD

El usuario entra por un dashboard maestro que permite seleccionar o continuar una referencia de programa, ver bloqueos reales y abrir solo los modulos habilitados. El dashboard no reemplaza la revision humana ni cambia la secuencia del wizard.

## Decision funcional ASISTENTE-GUIADO-TRANSVERSAL

El usuario cuenta con una guia visual persistente y no invasiva dentro de programa, proyecto y planeacion. La guia explica el paso actual, lista faltantes, muestra bloqueos reales y recomienda la accion siguiente sin reemplazar las validaciones del sistema.

---

## HU - Descargar la planeacion en el formato institucional

**Como** instructor o integrante del equipo de gestión curricular
**Quiero** generar la planeación individual o consolidada en `GPFI-F-134 V05`
**Para** obtener el documento institucional completo sin reconstruirlo manualmente.

### Criterios de aceptación

- El sistema conserva las hojas, logos, estilos, combinaciones y configuración de impresión de la plantilla.
- La vista previa informa faltantes y permite regresar al campo correspondiente.
- La generación individual repite una fila por asignación fase/actividad.
- El consolidado incluye completas, excluye borradores y muestra ambos contadores.
- El Excel se almacena en MinIO y se descarga como Blob desde el backend.
- Una duración inconsistente o metadata faltante impide generar.

# 1. Épica: Inicio y borradores

## HU-01. Iniciar cargue del programa
**Como** usuario gestor pedagógico  
**Quiero** iniciar un nuevo proceso de cargue del programa  
**Para** comenzar el diligenciamiento de la estructura base.

### Criterios de aceptación
- Debe existir un botón u opción para iniciar el proceso.
- Debe permitirse cargar Excel canónico o continuar borrador.
- El sistema debe abrir el wizard en el paso correspondiente.
- NO debe existir opción de modo manual como fuente de captura.

---

## HU-02. Continuar un borrador existente
**Como** usuario gestor pedagógico  
**Quiero** retomar un borrador  
**Para** seguir trabajando sin perder el avance.

### Criterios de aceptación
- El sistema debe identificar borradores disponibles.
- El usuario debe volver al mismo paso del wizard.
- Los datos previos deben mantenerse intactos.

---

## HU-02A. Visualizar dashboard maestro del proceso
**Como** usuario gestor pedagogico
**Quiero** ver un panel maestro con programa, proyecto y planeacion
**Para** entender el avance, bloqueos y acciones disponibles antes de abrir cada modulo.

### Criterios de aceptacion
- La ruta `/` debe mostrar el dashboard maestro ASGARD.
- El usuario debe poder abrir `/programa` desde el panel.
- El proyecto debe aparecer bloqueado hasta que el programa este `COMPLETO`.
- La planeacion debe aparecer bloqueada hasta que programa y proyecto esten `COMPLETO`.
- El panel debe mostrar metricas de programa, proyecto y planeacion.
- El panel debe mostrar un mapa navegable con enlaces activos solo para modulos habilitados.

---

# 2. Épica: Cargue híbrido del programa

## HU-03. Cargar PDF del programa
**Como** usuario gestor pedagógico  
**Quiero** cargar el PDF del programa  
**Para** conservarlo como evidencia documental en MinIO.

### Criterios de aceptación
- Debe aceptarse un archivo PDF.
- El archivo debe validarse antes de procesarlo.
- Debe almacenarse como evidencia documental.
- NO se realiza extraccion curricular desde el PDF.

---

## HU-04. Validar PDF del programa como evidencia
**Como** usuario gestor pedagógico  
**Quiero** que el sistema valide el PDF  
**Para** verificar que el archivo se guardó correctamente como evidencia.

### Criterios de aceptación
- El sistema debe verificar que el PDF es un archivo valido.
- Debe informarse el resultado al usuario.
- NO se clasifica por legibilidad ni extraccion.

---

## HU-05. Importar datos del programa desde Excel canonico
Nota vigente: despues de confirmar la importacion, el origen documental debe mostrar un resumen compacto y abrir la revision de competencias importadas en una modal paginada.

**Como** usuario gestor pedagógico  
**Quiero** que el sistema importe los datos del programa desde Excel  
**Para** ahorrar tiempo de digitacion y tener una base curricular estructurada.

### Criterios de aceptación
- Deben importarse los campos definidos en SPECS desde Excel canonico.
- Los datos deben quedar disponibles para revision.
- Todo debe guardarse en borrador.
- Debe requerirse confirmacion humana.

---

## HU-06. Completar campos faltantes post-importacion
**Como** usuario gestor pedagógico  
**Quiero** corregir puntualmente los campos no importados por Excel
**Para** continuar el proceso sin bloqueos.

### Criterios de aceptación
- Solo se habilita para campos que la importacion Excel no resolvió.
- Debe mostrarse el motivo de que un campo quede pendiente.
- Debe existir una accion visible para diligenciarlo.
- El ingreso manual NO es fuente alternativa de construccion curricular.

---

# 3. Épica: Gestión curricular del programa

## HU-07. Registrar competencias
Nota vigente: la gestion curricular inicia desde selector/filtro de competencia para evitar render masivo.

**Como** usuario gestor pedagógico  
**Quiero** registrar competencias  
**Para** estructurar el programa correctamente.

### Criterios de aceptación
- Debe permitirse crear una o muchas competencias.
- Cada competencia debe tener código y nombre.
- No deben permitirse duplicados de código.

---

## HU-08. Registrar resultados de aprendizaje
Nota vigente: los resultados cargan al seleccionar una competencia concreta.

**Como** usuario gestor pedagógico  
**Quiero** agregar resultados por competencia  
**Para** completar la estructura curricular.

### Criterios de aceptación
- Debe permitirse agregar múltiples resultados por competencia.
- Deben evitarse registros vacíos o duplicados.

---

## HU-09. Registrar conocimientos de saber
Nota vigente: los conocimientos SABER aparecen primero en un selector eficiente y se renderizan solo al seleccionarse.

**Como** usuario gestor pedagógico  
**Quiero** agregar conocimientos de saber  
**Para** mantener la estructura mínima obligatoria.

### Criterios de aceptación
- Deben asociarse a una competencia.
- No deben permitirse vacíos ni duplicados.

---

## HU-10. Registrar conocimientos de proceso
Nota vigente: los conocimientos PROCESO aparecen primero en un selector eficiente y se renderizan solo al seleccionarse.

**Como** usuario gestor pedagógico  
**Quiero** agregar conocimientos de proceso  
**Para** completar la estructura mínima.

### Criterios de aceptación
- Deben asociarse a una competencia.
- No deben permitirse vacíos ni duplicados.

---

## HU-11. Registrar criterios de evaluación
Nota vigente: los criterios aparecen primero en un selector eficiente y se renderizan solo al seleccionarse.

**Como** usuario gestor pedagógico  
**Quiero** agregar criterios de evaluación  
**Para** cerrar la estructura curricular de cada competencia.

### Criterios de aceptación
- Deben asociarse a una competencia.
- No deben permitirse vacíos ni duplicados.

---

## HU-12. Editar y corregir la estructura curricular
**Como** usuario gestor pedagógico  
**Quiero** editar, borrar y agregar registros  
**Para** corregir inconsistencias antes del cierre.

### Criterios de aceptación
- Debe permitirse CRUD en todos los niveles.
- Todo borrado debe confirmarse.
- El sistema debe actualizar el resumen consolidado.

---

# 4. Épica: Revisión y cierre del programa

## HU-13. Revisar consolidado del programa
**Como** usuario gestor pedagógico  
**Quiero** revisar el resumen completo del programa  
**Para** validar la información antes de cerrarla.

### Criterios de aceptación
- Debe mostrarse una vista jerárquica editable.
- Debe indicarse qué campos son extraídos, manuales o pendientes.

---

## HU-14. Marcar el programa como completo
**Como** usuario gestor pedagógico  
**Quiero** cerrar el programa como completo  
**Para** habilitar el cargue del proyecto.

### Criterios de aceptación
- Solo debe permitirse si la estructura mínima está completa.
- Debe requerirse confirmación explícita del usuario.

---

# 5. Épica: Habilitación y gestión del proyecto

## HU-15. Bloquear cargue del proyecto mientras el programa esté incompleto
**Como** usuario gestor pedagógico  
**Quiero** que el proyecto permanezca bloqueado  
**Para** respetar la dependencia con el programa.

### Criterios de aceptación
- El módulo debe bloquearse visual y funcionalmente.
- Debe mostrarse una razón clara del bloqueo.

---

## HU-16. Habilitar el proyecto cuando el programa esté completo
**Como** usuario gestor pedagógico  
**Quiero** poder iniciar el proyecto  
**Para** continuar con la Fase 1.

### Criterios de aceptación
- El proyecto solo se habilita si el programa está completo.
- Debe mantenerse la relación entre programa y proyecto.

---

## HU-17. Cargar PDF del proyecto
**Como** usuario gestor pedagógico  
**Quiero** cargar el PDF del proyecto  
**Para** conservarlo como evidencia documental en MinIO.

### Criterios de aceptación
- Debe aceptarse un PDF valido.
- Debe almacenarse como evidencia documental.

## HU-18. Importar datos del proyecto desde fuente estructurada
**Como** usuario gestor pedagógico  
**Quiero** que el sistema importe los datos del proyecto desde Excel/matriz  
**Para** reducir el trabajo manual.

### Criterios de aceptación
- Los datos importados deben revisarse.
- Deben guardarse en borrador.
- Debe permitirse correccion post-importacion de lo faltante.

## HU-19. Completar campos faltantes post-importacion del proyecto
**Como** usuario gestor pedagógico  
**Quiero** corregir puntualmente faltantes del proyecto
**Para** terminar la captura si la importacion no fue suficiente.

### Criterios de aceptación
- Debe permitirse ingresar los campos faltantes que la matriz no resolvió.
- Debe validarse la relacion fase-actividad.
- El ingreso manual NO es fuente alternativa de construccion curricular.

---

## HU-20. Gestionar fases del proyecto
**Como** usuario gestor pedagógico  
**Quiero** crear y editar fases  
**Para** estructurar el proyecto.

### Criterios de aceptación
- Debe permitirse crear varias fases.
- No deben quedar fases vacías al cerrar el proyecto.

---

## HU-21. Gestionar actividades por fase
**Como** usuario gestor pedagógico  
**Quiero** agregar actividades por fase  
**Para** completar la planeación del proyecto.

### Criterios de aceptación
- Cada actividad debe pertenecer a una fase.
- No deben permitirse actividades vacías o duplicadas.

---

## HU-22. Revisar y cerrar el proyecto
**Como** usuario gestor pedagógico  
**Quiero** revisar y marcar el proyecto como completo  
**Para** cerrar correctamente la Fase 1.

### Criterios de aceptación
- Debe existir vista consolidada editable.
- Solo puede cerrarse si existen fases y actividades válidas.
- Debe requerirse confirmación explícita.

---

# 6. Épica: Persistencia e integridad

## HU-23. Guardado automático en todo el flujo
**Como** usuario gestor pedagógico  
**Quiero** que todo el sistema guarde mi avance automáticamente  
**Para** no perder información en ningún punto.

### Criterios de aceptación
- Cada cambio relevante debe persistirse.
- Debe conservarse el paso del wizard y el estado del bloque.

---

## HU-24. Advertir impacto de cambios posteriores
**Como** usuario gestor pedagógico  
**Quiero** recibir una advertencia si editar el programa afecta el proyecto  
**Para** preservar la consistencia del sistema.

### Criterios de aceptación
- Si el programa cambia y queda inconsistente, debe mostrarse advertencia.
- Debe indicarse el posible impacto sobre el proyecto asociado.

---

## HU-02B. Recibir guia contextual durante los wizards
**Como** usuario gestor pedagogico
**Quiero** ver un asistente visual que me indique que hacer y que falta
**Para** avanzar por programa, proyecto y planeacion sin saltar reglas de negocio.

### Criterios de aceptacion
- El asistente debe aparecer en los tres wizards.
- Debe mostrar severidad `info`, `warning`, `blocked` o `success`.
- Debe mostrar checklist de requisitos completos y pendientes.
- Debe advertir que el proyecto requiere programa `COMPLETO`.
- Debe advertir que la planeacion requiere proyecto `COMPLETO`.
- Debe recordar si el usuario colapso la ayuda.

---

# 7. Épica: Administración Organizacional Multiusuario (SPRINT-B)

## HU-25. Administración multiusuario y credenciales
**Como** administrador o superadministrador de ASGARD  
**Quiero** registrar y gestionar usuarios con roles canónicos y asignación curricular  
**Para** gobernar el acceso de líderes y apoyos al sistema según su especialidad.

### Criterios de aceptación
- Solo `SUPERADMIN` y `ADMIN` pueden gestionar usuarios.
- `ADMIN` no puede crear, editar, listar en detalle, bloquear ni resetear a un `SUPERADMIN`.
- Roles `LIDER_EQUIPO_EJECUTOR` y `USUARIO_ADICIONAL` requieren coordinación y especialidad activas válidas.
- Toda cuenta creada administrativamente recibe flag `debe_cambiar_password = true`.

---

## HU-26. Control de estado y cambio de contraseña forzoso
**Como** usuario con credenciales temporales o administrador que bloquea acceso  
**Quiero** que el sistema impida el acceso no autorizado y fuerce la personalización de credenciales  
**Para** garantizar la seguridad institucional de la información curricular.

### Criterios de aceptación
- El estado puede ser `ACTIVO`, `INACTIVO` o `BLOQUEADO`.
- Al cambiar estado o resetear clave, se revoca inmediatamente toda sesión activa (`token_version` + revocación DB).
- Con `debe_cambiar_password = true`, se bloquea todo endpoint salvo la whitelist de autenticación y se despliega modal no cancelable.

---

## HU-27. Catálogo organizacional con guardias de integridad
**Como** administrador de la entidad  
**Quiero** gestionar el catálogo de coordinaciones y especialidades  
**Para** estructurar los centros de formación y restringir equipos ejecutores.

### Criterios de aceptación
- Los códigos son alfanuméricos en mayúsculas y únicos.
- No se permite inactivar una coordinación con especialidades activas.
- No se permite inactivar una especialidad con equipos ejecutores activos.

---

## HU-28. Equipos ejecutores y sincronización transaccional de procesos
**Como** administrador de formación  
**Quiero** crear equipos ejecutores, asociar miembros y actualizar su líder  
**Para** asegurar que los procesos curriculares queden bajo la responsabilidad del líder correcto de forma inmediata.

### Criterios de aceptación
- El líder debe tener rol `LIDER_EQUIPO_EJECUTOR` y coincidir en coordinación y especialidad.
- Los miembros de apoyo deben tener rol `USUARIO_ADICIONAL` y pertenecer a la misma coordinación y especialidad.
- Al cambiar el líder de un equipo, el sistema actualiza de forma transaccional `usuario_lider_id` en todos los procesos curriculares vinculados al equipo.

---

## HU-29. Supervisión jerárquica de procesos formativos
**Como** directivo institucional (SUPERADMIN o ADMIN)  
**Quiero** visualizar un tablero centralizado con filtros jerárquicos (Coordinación → Especialidad → Equipo → Líder)  
**Para** supervisar el estado global de programas, proyectos y planeaciones pedagógicas, identificando procesos huérfanos o rezagados.

### Criterios de aceptación
- Tarjetas KPI con totales agregados, procesos sin asignar y porcentaje de avance.
- Filtros reactivos en cascada que recalculan métricas y actualizan la lista paginada.
- Drawer lateral de inspección técnica con desglose de equipo y planeaciones vinculadas.
- Acceso restringido exclusivamente a roles directivos (`SUPERADMIN`, `ADMIN`).

---

## HU-30. Visor institucional de auditoría inmutable
**Como** oficial de cumplimiento y control institucional  
**Quiero** consultar la bitácora inmutable de eventos con identificación del actor y proceso  
**Para** realizar seguimiento forense de acciones y modificaciones curriculares sin riesgo de alteración del registro.

### Criterios de aceptación
- Registro con actor (`id`, `nombre`, `email`, `roles`), acción, entidad, fecha y proceso referenciado.
- Redacción recursiva automática de contraseñas, secretos y tokens en el payload JSON.
- Modal de inspección detallada con formateo JSON y función de copiado.
- Inmutabilidad total: ausencia de endpoints o capacidades de modificación/borrado (`405 Method Not Allowed`).

---

## HU-31. Verificación integral de flujo curricular y roles (E2E)
**Como** equipo de calidad y aseguramiento de la plataforma  
**Quiero** contar con pruebas End-to-End automatizadas sobre navegadores reales  
**Para** certificar que los 4 roles canónicos, el control de primer acceso y el flujo curricular completo (Programa → Proyecto → Planeación → GPFI) funcionan armónicamente sin regresiones.

### Criterios de aceptación
- Escenarios de autenticación y autorización para `SUPERADMIN`, `ADMIN`, `LIDER` y `USUARIO_ADICIONAL`.
- Verificación del modal obligatorio de primer acceso (`debe_cambiar_password = true`).
- Ejecución automatizada de supervisión, auditoría y flujo curricular completo.


