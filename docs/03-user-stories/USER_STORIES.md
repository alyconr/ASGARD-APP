# USER_STORIES.md
## Proyecto: Aplicación web para construcción de guías de aprendizaje SENA
## Fase: 1
## Última actualización: [YYYY-MM-DD]

## Decision funcional TASK-08.5

Las historias de cargue hibrido del programa se reinterpretan asi desde TASK-08.5:

- HU-03 y HU-04 conservan PDF solo como soporte documental en MinIO.
- HU-05 deja de ejecutarse desde PDF para el programa.
- La nueva tarea puente TASK-08.5 agrega preview e importacion desde Excel canonico antes de TASK-09.

---

# 1. Épica: Inicio y borradores

## HU-01. Iniciar cargue del programa
**Como** usuario gestor pedagógico  
**Quiero** iniciar un nuevo proceso de cargue del programa  
**Para** comenzar el diligenciamiento de la estructura base.

### Criterios de aceptación
- Debe existir un botón u opción para iniciar el proceso.
- Debe permitirse elegir entre PDF, manual o continuar borrador.
- El sistema debe abrir el wizard en el paso correspondiente.

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

# 2. Épica: Cargue híbrido del programa

## HU-03. Cargar PDF del programa
**Como** usuario gestor pedagógico  
**Quiero** cargar el PDF del programa  
**Para** que el sistema intente extraer la información automáticamente.

### Criterios de aceptación
- Debe aceptarse un archivo PDF.
- El archivo debe validarse antes de procesarlo.
- Debe iniciarse el análisis del documento.

---

## HU-04. Detectar legibilidad del PDF del programa
**Como** usuario gestor pedagógico  
**Quiero** que el sistema evalúe el PDF  
**Para** saber si la extracción será automática o manual.

### Criterios de aceptación
- El sistema debe clasificar el PDF como legible, parcial o no legible.
- Debe informarse el resultado al usuario.
- Debe ofrecerse fallback manual si aplica.

---

## HU-05. Extraer automáticamente datos del programa
**Como** usuario gestor pedagógico  
**Quiero** que el sistema extraiga los datos del programa  
**Para** ahorrar tiempo de digitación.

### Criterios de aceptación
- Deben intentarse extraer los campos definidos en SPECS.
- Los datos deben quedar prellenados.
- Todo debe guardarse en borrador.
- Debe requerirse revisión humana.

---

## HU-06. Completar manualmente campos faltantes del programa
**Como** usuario gestor pedagógico  
**Quiero** completar manualmente los campos no extraídos  
**Para** continuar el proceso sin bloqueos.

### Criterios de aceptación
- Los campos faltantes deben marcarse como pendientes.
- Debe mostrarse el motivo del fallo.
- Debe existir una acción visible para diligenciarlos.

---

# 3. Épica: Gestión curricular del programa

## HU-07. Registrar competencias
**Como** usuario gestor pedagógico  
**Quiero** registrar competencias  
**Para** estructurar el programa correctamente.

### Criterios de aceptación
- Debe permitirse crear una o muchas competencias.
- Cada competencia debe tener código y nombre.
- No deben permitirse duplicados de código.

---

## HU-08. Registrar resultados de aprendizaje
**Como** usuario gestor pedagógico  
**Quiero** agregar resultados por competencia  
**Para** completar la estructura curricular.

### Criterios de aceptación
- Debe permitirse agregar múltiples resultados por competencia.
- Deben evitarse registros vacíos o duplicados.

---

## HU-09. Registrar conocimientos de saber
**Como** usuario gestor pedagógico  
**Quiero** agregar conocimientos de saber  
**Para** mantener la estructura mínima obligatoria.

### Criterios de aceptación
- Deben asociarse a una competencia.
- No deben permitirse vacíos ni duplicados.

---

## HU-10. Registrar conocimientos de proceso
**Como** usuario gestor pedagógico  
**Quiero** agregar conocimientos de proceso  
**Para** completar la estructura mínima.

### Criterios de aceptación
- Deben asociarse a una competencia.
- No deben permitirse vacíos ni duplicados.

---

## HU-11. Registrar criterios de evaluación
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
**Para** intentar extraer sus datos automáticamente.

### Criterios de aceptación
- Debe aceptarse un PDF válido.
- Debe analizarse su legibilidad.

---

## HU-18. Extraer datos del proyecto
**Como** usuario gestor pedagógico  
**Quiero** que el sistema extraiga nombre, código, versión, fases y actividades  
**Para** reducir el trabajo manual.

### Criterios de aceptación
- Los datos extraídos deben prellenarse.
- Deben guardarse en borrador.
- Debe permitirse corrección manual.

---

## HU-19. Completar manualmente el proyecto
**Como** usuario gestor pedagógico  
**Quiero** completar manualmente el proyecto  
**Para** terminar la captura si la extracción no fue suficiente.

### Criterios de aceptación
- Debe permitirse ingresar los campos faltantes.
- Debe validarse la relación fase-actividad.

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
