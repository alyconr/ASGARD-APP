# DATA_MODEL.md
## Proyecto: Aplicación web para construcción de guías de aprendizaje SENA
## Fase: 1
## Estado: Base de arquitectura de datos
## Última actualización: [YYYY-MM-DD]

---

# 1. Propósito

Este documento define el modelo de datos conceptual y lógico de la Fase 1 del sistema.

Su objetivo es describir:

- entidades principales,
- atributos clave,
- relaciones,
- restricciones,
- estados,
- reglas de integridad,
- y lineamientos de persistencia.

Este archivo debe servir como base para construir:

- esquema de base de datos,
- modelos ORM,
- migraciones,
- validadores,
- servicios de persistencia,
- contratos de API,
- y lógica de completitud.

## Decision funcional TASK-08.5

El modelo relacional vigente ya soporta la importacion Excel canonica hacia `ProgramaFormacion`, `Competencia`, `ResultadoAprendizaje`, `Conocimiento` y `CriterioEvaluacion`.

El PDF del programa permanece como evidencia documental en MinIO y solo deja metadata en `payload_json`. El Excel canonico `.xlsx` tambien se almacena en MinIO como soporte auditable; `payload_json` conserva metadata de preview, validacion, confirmacion e identificadores relacionales creados, nunca el binario.

Los conocimientos y criterios del Excel que no puedan enlazarse con seguridad a
competencia o RAP no se insertan aun en `Conocimiento` ni `CriterioEvaluacion`;
se conservan en `ElementoCurricularPendiente` para conciliacion manual
posterior.

---

# 2. Alcance del modelo

Este modelo cubre exclusivamente la información requerida para la Fase 1:

- programa de formación,
- competencias,
- resultados de aprendizaje,
- conocimientos de saber,
- conocimientos de proceso,
- criterios de evaluación,
- proyecto formativo,
- fases del proyecto,
- actividades del proyecto,
- borradores,
- auditoría básica.

No cubre todavía:

- generación de guías,
- exportación,
- versionamiento documental,
- roles avanzados,
- aprobaciones,
- ayudas documentales por campo,
- relaciones pedagógicas avanzadas entre proyecto y resultados de aprendizaje.

---

# 3. Principios del modelo

## PM-01. Integridad jerárquica
Toda entidad hija debe tener una referencia válida a su entidad padre.

## PM-02. Persistencia incremental
Programa y proyecto deben poder guardarse parcialmente en estado borrador.

## PM-03. Soporte para evidencia documental e importacion estructurada
Cada dato debe poder registrarse como:

- extraído automáticamente,
- ingresado manualmente,
- corregido por el usuario,
- pendiente de validación.

## PM-04. Trazabilidad mínima
Las entidades principales deben registrar creación, actualización y estado actual.

## PM-05. Preparación para crecimiento
El modelo debe ser extensible para fases futuras sin rediseño profundo del núcleo.

---

# 4. Enums y catálogos

## 4.1 EstadoBloque
Valores permitidos:

- BORRADOR
- EN_REVISION
- COMPLETO
- BLOQUEADO

## 4.2 TipoFuenteCargue
Valores permitidos:

- PDF_EXTRACCION
- PDF_EVIDENCIA
- EXCEL_CANONICO
- MANUAL
- MIXTO

`PDF_EXTRACCION` queda como valor historico/deprecated. Para TASK-08.5, usar `PDF_EVIDENCIA` cuando aplique al soporte documental y `EXCEL_CANONICO` para materializacion curricular desde workbook.

## 4.3 TipoConocimiento
Valores permitidos:

- SABER
- PROCESO

## 4.4 EstadoCampo
Valores permitidos:

- EXTRAIDO
- MANUAL
- CORREGIDO
- PENDIENTE
- VALIDADO

## 4.5 MotivoFalloExtraccion
Valores permitidos:

- PDF_ESCANEADO
- DOCUMENTO_ILEGIBLE
- BAJA_RESOLUCION
- ESTRUCTURA_NO_RECONOCIDA
- CAMPO_NO_ENCONTRADO
- CONTENIDO_AMBIGUO
- ARCHIVO_PROTEGIDO

---

# 5. Entidades principales

## 5.1 ProgramaFormacion

Representa el bloque principal del programa de formación.

### Campos
- id
- codigo_programa
- nombre_programa
- version_programa
- estado
- fuente_cargue
- observaciones_revision
- fecha_creacion
- fecha_actualizacion

### Tipos sugeridos
- id: UUID o bigint
- codigo_programa: string
- nombre_programa: string
- version_programa: string nullable
- estado: EstadoBloque
- fuente_cargue: TipoFuenteCargue
- observaciones_revision: text nullable
- fecha_creacion: datetime
- fecha_actualizacion: datetime

### Restricciones
- codigo_programa es obligatorio
- nombre_programa es obligatorio
- la combinación lógica de codigo_programa + version_programa no debe duplicarse según la política del proyecto

---

## 5.2 Competencia

Representa una competencia asociada al programa.

### Campos
- id
- programa_id
- codigo_competencia
- nombre_competencia
- orden
- estado
- origen_campo
- fecha_creacion
- fecha_actualizacion

### Tipos sugeridos
- id: UUID o bigint
- programa_id: FK
- codigo_competencia: string
- nombre_competencia: text
- orden: integer nullable
- estado: EstadoBloque
- origen_campo: EstadoCampo
- fecha_creacion: datetime
- fecha_actualizacion: datetime

### Restricciones
- programa_id es obligatorio
- codigo_competencia es obligatorio
- nombre_competencia es obligatorio
- codigo_competencia debe ser único dentro del mismo programa

---

## 5.3 ResultadoAprendizaje

Representa un resultado de aprendizaje asociado a una competencia.

### Campos
- id
- competencia_id
- codigo_resultado
- descripcion
- orden
- estado
- motivo_fallo_extraccion
- fecha_creacion
- fecha_actualizacion

### Tipos sugeridos
- id: UUID o bigint
- competencia_id: FK
- codigo_resultado: string nullable; para importacion Excel canonica guarda el `rap_id` estable del workbook, no el `rap_numero` visible
- descripcion: text
- orden: integer nullable
- estado: EstadoCampo
- motivo_fallo_extraccion: MotivoFalloExtraccion nullable
- fecha_creacion: datetime
- fecha_actualizacion: datetime

### Restricciones
- competencia_id es obligatorio
- descripcion es obligatoria
- no debe duplicarse la misma descripcion exacta dentro de la misma competencia

---

## 5.4 Conocimiento

Representa conocimientos de tipo saber o proceso asociados a una competencia.

### Campos
- id
- competencia_id
- resultado_id
- tipo
- descripcion
- orden
- estado
- motivo_fallo_extraccion
- fecha_creacion
- fecha_actualizacion

### Tipos sugeridos
- id: UUID o bigint
- competencia_id: FK
- resultado_id: FK nullable a ResultadoAprendizaje
- tipo: TipoConocimiento
- descripcion: text
- orden: integer nullable
- estado: EstadoCampo
- motivo_fallo_extraccion: MotivoFalloExtraccion nullable
- fecha_creacion: datetime
- fecha_actualizacion: datetime

### Restricciones
- competencia_id es obligatorio
- resultado_id es opcional; cuando existe, debe pertenecer a un ResultadoAprendizaje de la misma competencia
- tipo es obligatorio
- descripcion es obligatoria
- no debe duplicarse la misma descripcion exacta dentro de la misma categoría, competencia y RAP cuando resultado_id exista
- los conocimientos sin resultado_id se validan a nivel de categoría y competencia

---

## 5.5 CriterioEvaluacion

Representa criterios de evaluación asociados a una competencia.

### Campos
- id
- competencia_id
- resultado_id
- descripcion
- orden
- estado
- motivo_fallo_extraccion
- fecha_creacion
- fecha_actualizacion

### Tipos sugeridos
- id: UUID o bigint
- competencia_id: FK
- resultado_id: FK nullable a ResultadoAprendizaje
- descripcion: text
- orden: integer nullable
- estado: EstadoCampo
- motivo_fallo_extraccion: MotivoFalloExtraccion nullable
- fecha_creacion: datetime
- fecha_actualizacion: datetime

### Restricciones
- competencia_id es obligatorio
- resultado_id es opcional; cuando existe, debe pertenecer a un ResultadoAprendizaje de la misma competencia
- descripcion es obligatoria
- no debe duplicarse la misma descripcion exacta dentro de la misma competencia y RAP cuando resultado_id exista
- los criterios sin resultado_id se validan a nivel de competencia

---

## 5.5.1 ElementoCurricularPendiente

Representa una fila de Excel canonico de tipo conocimiento o criterio que
requiere asignacion manual antes de materializarse en la estructura final.

### Campos
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
- orden
- raw_excel
- fecha_creacion
- fecha_actualizacion

### Restricciones
- descripcion es obligatoria
- tipo_elemento solo puede ser CONOCIMIENTO o CRITERIO
- estado inicia en PENDIENTE y pasa a ASIGNADO cuando se crea el elemento final
- la competencia de etapa practica puede existir sin hijos curriculares

---

## 5.6 ProyectoFormativo

Representa el bloque principal del proyecto formativo.

### Campos
- id
- programa_id
- codigo_proyecto
- nombre_proyecto
- version_proyecto
- estado
- fuente_cargue
- observaciones_revision
- fecha_creacion
- fecha_actualizacion

### Tipos sugeridos
- id: UUID o bigint
- programa_id: FK
- codigo_proyecto: string
- nombre_proyecto: text
- version_proyecto: string
- estado: EstadoBloque
- fuente_cargue: TipoFuenteCargue
- observaciones_revision: text nullable
- fecha_creacion: datetime
- fecha_actualizacion: datetime

### Restricciones
- programa_id es obligatorio
- codigo_proyecto es obligatorio
- nombre_proyecto es obligatorio
- version_proyecto es obligatoria
- no debe crearse funcionalmente si el programa no está COMPLETO

---

## 5.7 FaseProyecto

Representa una fase del proyecto formativo.

### Campos
- id
- proyecto_id
- nombre_fase
- orden
- estado
- fecha_creacion
- fecha_actualizacion

### Tipos sugeridos
- id: UUID o bigint
- proyecto_id: FK
- nombre_fase: string
- orden: integer nullable
- estado: EstadoCampo
- fecha_creacion: datetime
- fecha_actualizacion: datetime

### Restricciones
- proyecto_id es obligatorio
- nombre_fase es obligatorio
- no deben quedar fases vacías al cerrar el proyecto

---

## 5.8 ActividadProyecto

Representa una actividad perteneciente a una fase del proyecto.

### Campos
- id
- fase_id
- descripcion
- orden
- estado
- motivo_fallo_extraccion
- fecha_creacion
- fecha_actualizacion

### Tipos sugeridos
- id: UUID o bigint
- fase_id: FK
- descripcion: text
- orden: integer nullable
- estado: EstadoCampo
- motivo_fallo_extraccion: MotivoFalloExtraccion nullable
- fecha_creacion: datetime
- fecha_actualizacion: datetime

### Restricciones
- fase_id es obligatorio
- descripcion es obligatoria
- no debe duplicarse la misma descripcion exacta dentro de la misma fase

---

## 5.9 BorradorSesion

Representa el estado persistido del wizard.

### Campos
- id
- tipo_bloque
- referencia_id
- paso_actual
- payload_json
- estado_borrador
- ultima_edicion

### Tipos sugeridos
- id: UUID o bigint
- tipo_bloque: string
- referencia_id: UUID o bigint
- paso_actual: string
- payload_json: json o jsonb
- estado_borrador: EstadoBloque
- ultima_edicion: datetime

### Restricciones
- tipo_bloque es obligatorio
- referencia_id es obligatorio
- paso_actual es obligatorio
- payload_json es obligatorio

---

## 5.10 EventoAuditoria

Representa la trazabilidad mínima del sistema.

### Campos
- id
- entidad
- entidad_id
- accion
- detalle
- fecha_evento

### Tipos sugeridos
- id: UUID o bigint
- entidad: string
- entidad_id: UUID o bigint
- accion: string
- detalle: json o text nullable
- fecha_evento: datetime

### Restricciones
- entidad es obligatoria
- entidad_id es obligatorio
- accion es obligatoria

---

# 6. Relaciones del modelo

## ProgramaFormacion
- 1:N con Competencia
- 1:N con ProyectoFormativo

## Competencia
- 1:N con ResultadoAprendizaje
- 1:N con Conocimiento
- 1:N con CriterioEvaluacion

## ResultadoAprendizaje
- 1:N opcional con Conocimiento
- 1:N opcional con CriterioEvaluacion

## ProyectoFormativo
- 1:N con FaseProyecto

## FaseProyecto
- 1:N con ActividadProyecto

---

# 7. Reglas de integridad

## RI-01
No puede existir una competencia sin programa.

## RI-02
No puede existir un resultado sin competencia.

## RI-03
No puede existir un conocimiento sin competencia.

## RI-04
No puede existir un criterio sin competencia.

## RI-05
No puede existir una fase sin proyecto.

## RI-06
No puede existir una actividad sin fase.

## RI-07
No puede existir un proyecto funcionalmente activo si el programa no está completo.

## RI-08
Las eliminaciones deben proteger integridad mediante:
- cascada controlada,
- o borrado lógico,
- según la estrategia técnica elegida.

---

# 8. Reglas de completitud modelables

## 8.1 Programa completo
Un programa puede pasar a COMPLETO si:

- tiene codigo_programa,
- tiene nombre_programa,
- tiene al menos una competencia,
- cada competencia tiene:
  - al menos un resultado,
  - al menos un conocimiento SABER,
  - al menos un conocimiento PROCESO,
  - al menos un criterio,
- y el usuario confirma revisión.

## 8.2 Proyecto completo
Un proyecto puede pasar a COMPLETO si:

- tiene codigo_proyecto,
- tiene nombre_proyecto,
- tiene version_proyecto,
- tiene al menos una fase,
- cada fase tiene al menos una actividad,
- y el usuario confirma revisión.

---

# 9. Reglas de unicidad

## U-01. Programa
No duplicar combinación lógica de codigo_programa + version_programa.

## U-02. Competencia
No duplicar codigo_competencia dentro del mismo programa.

## U-03. Resultado
No duplicar `codigo_resultado`/`rap_id` dentro de la misma competencia cuando provenga de Excel canonico. Tampoco se debe duplicar la misma descripcion exacta dentro de la misma competencia.

## U-04. Conocimiento
No duplicar descripcion exacta dentro de la misma categoría, competencia y RAP cuando tenga resultado_id. Si resultado_id es nulo, no duplicar dentro de la misma categoría y competencia.

## U-05. Criterio
No duplicar descripcion exacta dentro de la misma competencia y RAP cuando tenga resultado_id. Si resultado_id es nulo, no duplicar dentro de la misma competencia.

## U-06. Actividad
No duplicar descripcion exacta dentro de la misma fase.

---

# 10. Reglas de trazabilidad del dato

El modelo debe permitir identificar si un dato fue:

- extraído automáticamente,
- ingresado manualmente,
- corregido por el usuario,
- dejado pendiente por revisión.

Esta trazabilidad es obligatoria para las entidades de contenido curricular y de proyecto, especialmente:

- competencia,
- resultado,
- conocimiento,
- criterio,
- actividad.

---

# 11. Recomendación relacional SQL

## Tablas sugeridas
- programas_formacion
- competencias
- resultados_aprendizaje
- conocimientos
- criterios_evaluacion
- proyectos_formativos
- fases_proyecto
- actividades_proyecto
- borradores_sesion
- eventos_auditoria

## Índices recomendados
- index programas_formacion(codigo_programa)
- unique competencias(programa_id, codigo_competencia)
- index resultados_aprendizaje(competencia_id)
- index conocimientos(competencia_id, tipo)
- index criterios_evaluacion(competencia_id)
- index proyectos_formativos(programa_id)
- index fases_proyecto(proyecto_id)
- index actividades_proyecto(fase_id)
- index borradores_sesion(tipo_bloque, referencia_id)

---

# 12. Convenciones recomendadas

## 12.1 Nombres
- tablas en plural snake_case
- columnas en snake_case
- claves foráneas con sufijo `_id`

## 12.2 Fechas
Todas las entidades persistentes deben tener:
- fecha_creacion
- fecha_actualizacion

## 12.3 Persistencia de borradores
Los borradores deben conservar el estado del wizard y el payload parcial de cada bloque.

## 12.4 Origen del dato
Cuando aplique, se debe almacenar el origen del dato o estado del campo.

---

# 13. Estrategia de borrado

## 13.1 Recomendación
Para Fase 1 puede usarse:

- hard delete controlado + auditoría,
- o soft delete si se quiere preservar recuperación futura.

## 13.2 Restricción funcional
Toda eliminación debe requerir confirmación explícita del usuario desde la capa funcional.

---

# 14. Preparación para fases futuras

Este modelo debe quedar preparado para futuras extensiones como:

- relación entre fases/actividades y resultados de aprendizaje,
- versionamiento documental,
- roles y permisos,
- ayudas documentales por campo,
- exportación,
- aprobaciones,
- historial ampliado de cambios.

Estas extensiones no deben implementarse todavía, pero el modelo no debe impedirlas.

---

# 15. Preguntas que no debe resolver automáticamente el modelo

El modelo no debe asumir por sí solo:

- relaciones pedagógicas no definidas entre actividades y resultados,
- múltiples jerarquías paralelas no aprobadas,
- lógica de permisos avanzada,
- reglas de exportación,
- comportamientos de fases futuras.

---

# 16. Decisiones cerradas del modelo

Quedan cerradas para Fase 1 estas decisiones:

- el programa es la raíz del dominio,
- la competencia es el contenedor curricular directo,
- saber y proceso se almacenan separados,
- el proyecto depende del programa,
- las actividades dependen de una fase,
- los borradores son persistentes,
- existe auditoría básica,
- la completitud se calcula por reglas explícitas del dominio.
