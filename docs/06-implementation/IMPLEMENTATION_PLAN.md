# IMPLEMENTATION_PLAN.md
## Proyecto: Aplicación web para construcción de guías de aprendizaje SENA
## Fase: 1
## Estado: Plan de implementación listo para ejecución
## Última actualización: [YYYY-MM-DD]

---

# 1. Propósito

Este documento define el plan de implementación técnico de la Fase 1 del sistema para construcción de guías de aprendizaje SENA.

Su objetivo es establecer:

- el orden de construcción,
- los módulos a implementar,
- las dependencias entre componentes,
- los entregables técnicos,
- la estrategia mínima de validación,
- y la forma correcta de ejecutar el trabajo con Codex bajo enfoque de spec-driven development y context engineering.

---

# 2. Fuente de verdad

Antes de implementar cualquier módulo, el agente o desarrollador debe leer y respetar estos documentos en el siguiente orden:

1. `/docs/01-business-rules/BUSINESS_RULES.md`
2. `/docs/02-specs/SPECS.md`
3. `/docs/03-user-stories/USER_STORIES.md`
4. `/docs/04-traceability/TRACEABILITY_MATRIX.md`
5. `/docs/05-architecture/DATA_MODEL.md`
6. `/docs/06-implementation/IMPLEMENTATION_PLAN.md`
7. `/docs/06-implementation/CODEX_TASKS.md`

Ninguna implementación debe contradecir estos documentos.

## Decision funcional TASK-UNICO-CARRIL

Desde esta refactorizacion integral:

- el Excel canonico `.xlsx` es la unica fuente estructurada activa para programa y proyecto;
- el PDF queda exclusivamente como evidencia documental en MinIO para programa y proyecto;
- el carril manual deja de existir como modo operativo;
- TASK-05, TASK-06, TASK-07, TASK-18, TASK-19 y las fases tecnicas asociadas quedan reinterpretadas.

## Decision funcional REFACTOR-FLUJO-PROGRAMA-PROYECTO

- El paso `datos-programa` se elimina por completo; el programa inicia en `origen-documental`.
- El origen documental del programa mantiene PDF evidencia y Excel canonico, pero tras importacion confirmada muestra resumen compacto y modal paginada de competencias.
- `estructura-curricular` usa selector/filtro de competencia y seleccion progresiva de conocimientos/criterios.
- El proyecto inicia en `fuente-proyecto`; no existe `datos-proyecto` como carril manual.
- El almacenamiento del proyecto usa `proyectos-formativos/{referencia_id}/documentos/...` para PDF y `proyectos-formativos/{referencia_id}/excel/...` para Excel/matriz.

## Decision funcional DASHBOARD-MAESTRO-ASGARD

- La ruta `/` se implementa como dashboard maestro.
- El wizard del programa se mueve a `/programa`.
- Se agrega un servicio backend agregado para estado, metricas, gates y mapa navegable.
- La regla de habilitacion queda centralizada: proyecto requiere programa `COMPLETO`; planeacion requiere programa y proyecto `COMPLETO`.
- Las pruebas deben cubrir el agregado backend, el gate de proyecto, el acceso de planeacion y la UI del dashboard.

## Decision funcional ASISTENTE-GUIADO-TRANSVERSAL

- Se agrega un componente visual compartido para guiar programa, proyecto y planeacion.
- Se agrega un motor de guia que traduce estados reales en severidad, mensaje, checklist y CTA.
- El componente se integra sin alterar la secuencia de los wizards ni sus validaciones.
- La experiencia persiste preferencias ligeras en `localStorage`.
- Las pruebas deben cubrir motor, render, persistencia y mensajes de bloqueo entre wizards.

---

# 3. Objetivo general de implementación

Construir la Fase 1 de una aplicación web que permita:

- cargar información del programa de formación,
- cargar información del proyecto formativo,
- conservar PDF como evidencia documental,
- importar datos desde Excel canonico cuando aplique,
- permitir correccion post-importacion cuando no sea posible,
- guardar siempre el avance en borrador,
- revisar y validar la información,
- bloquear el proyecto hasta que el programa esté completo,
- mostrar acceso centralizado, metricas y mapa navegable desde el dashboard maestro,
- y persistir toda la estructura de forma trazable.

---

# 4. Alcance técnico de la Fase 1

## 4.1 Incluye

- Modelo de datos base
- Migraciones iniciales
- CRUD del programa de formación
- CRUD curricular por competencia
- CRUD del proyecto formativo
- CRUD de fases y actividades
- Wizard del programa
- Wizard del proyecto
- Guardado automático en borrador
- Carga PDF como evidencia documental
- Importacion estructurada desde Excel canonico
- Revisión consolidada editable
- Validación de completitud
- Bloqueo/desbloqueo del proyecto
- Dashboard maestro ASGARD con metricas, gates y mapa navegable
- Auditoría básica
- Testing mínimo funcional

## 4.2 No incluye

- Exportación a PDF o DOCX
- Generación automática de la guía final
- Versionamiento documental completo
- Roles y permisos completos
- Aprobaciones institucionales
- Integraciones externas
- Panel administrativo avanzado

---

# 5. Principios de implementación

## PI-01. No inventar requisitos
Solo se debe implementar lo que esté definido en los documentos de negocio, specs, historias y trazabilidad.

## PI-02. Construcción incremental
La implementación debe hacerse por módulos pequeños, funcionales y verificables.

## PI-03. Persistencia temprana
El sistema de borradores debe implementarse desde el inicio, no al final.

## PI-04. Reglas de negocio en dominio
Las reglas críticas deben estar centralizadas en el dominio o en servicios de aplicación, no solo en la interfaz.

## PI-05. Estados consistentes
Los estados del programa y del proyecto deben manejarse de forma centralizada y auditable.

## PI-06. Confirmación explícita
El cierre de cada bloque debe requerir validación funcional y confirmación explícita del usuario.

## PI-07. Soporte a correccion post-importacion
La correccion editorial post-importacion debe diseñarse para convivir con la importacion Excel sin romper el flujo.

## PI-08. Preparación para crecimiento
La arquitectura debe quedar lista para futuras fases sin necesidad de rehacer el núcleo de datos.

---

# 6. Estrategia general

La implementación debe seguir este orden:

1. Fundaciones técnicas
2. Modelo de datos
3. Persistencia de borradores
4. Wizard del programa
5. Carga PDF del programa como evidencia
6. Importacion estructurada desde Excel canonico organizada por competencia
7. Gestión curricular
8. Revisión y cierre del programa
9. Bloqueo/desbloqueo del proyecto
10. Wizard del proyecto
11. Gestión de fases y actividades
12. Revisión y cierre del proyecto
13. Auditoría básica
14. Testing y estabilización

Este orden respeta las dependencias del dominio:

- primero programa,
- después proyecto,
- con borradores desde el inicio.

---

# 7. Stack técnico sugerido

> Ajustar según decisión final del equipo.

## 7.1 Frontend
- Next.js
- TypeScript
- React
- Tailwind CSS
- React Hook Form
- Zod

## 7.2 Backend
- FastAPI
- API REST
- capa de servicios de aplicación
- capa de dominio con validadores y reglas

## 7.3 Base de datos
- PostgreSQL

## 7.4 ORM recomendado
- SQLAlchemy

## 7.5 Almacenamiento de archivos
- local en desarrollo
- S3-compatible en producción si se requiere

---

# 8. Estructura de carpetas sugerida

## 8.1 Frontend

```text
/src
  /app
  /components
    /wizard
    /forms
    /review
    /status
    /tables
    /cards
  /features
    /programa
    /proyecto
    /drafts
    /upload
  /lib
  /types
  /validators
  /services
```

## 8.2 Backend

```text
/src
  /domain
    /programa
    /proyecto
    /competencia
    /drafts
    /auditoria
    /shared
  /application
    /use-cases
    /services
    /dto
  /infrastructure
    /db
    /repositories
    /extractors
    /storage
  /interfaces
    /http
      /controllers
      /schemas
      /middlewares
```

---

# 9. Fases técnicas de implementación

## Fase Técnica 1. Fundaciones

### Objetivo
Preparar la base del proyecto y dejar lista la infraestructura mínima.

### Tareas
- Crear repositorio base
- Configurar entorno de desarrollo
- Configurar frontend y backend
- Configurar base de datos
- Configurar variables de entorno
- Crear estructura de carpetas
- Crear configuración de linting y formato

### Entregables
- proyecto levanta localmente
- frontend compila
- backend responde
- base de datos conectada

---

## Fase Técnica 2. Modelo de datos y migraciones

### Objetivo
Construir el esquema relacional base de la Fase 1.

### Tareas
- Crear modelos de:
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
- Crear enums del sistema
- Crear migraciones
- Crear índices y restricciones básicas

### Entregables
- migración inicial aplicada
- modelos ORM definidos
- esquema consistente con `DATA_MODEL.md`

---

## Fase Técnica 3. Servicio de borradores

### Objetivo
Garantizar persistencia del avance desde el inicio.

### Tareas
- Crear servicio de guardado automático
- Crear servicio de recuperación de borrador
- Persistir paso actual del wizard
- Persistir payload parcial
- Asociar borradores a programa y proyecto

### Entregables
- autosave funcional
- recuperación de sesión funcional
- reanudación desde paso previo

---

## Fase Técnica 4. Wizard del programa

### Objetivo
Implementar el flujo principal del programa de formación.

### Tareas
- Crear vista inicial del wizard
- Crear pasos del programa
- Eliminar `datos-programa` de pasos, tipos, sidebar y navegacion
- Implementar navegación entre pasos
- Integrar autosave
- Mostrar barra o indicador de progreso
- Mostrar estado por bloque

### Entregables
- wizard funcional del programa
- persistencia entre pasos
- navegación adelante/atrás sin pérdida de datos

---

## Fase Técnica 5. Carga documental del programa como evidencia

### Objetivo
Permitir la carga del PDF del programa como evidencia documental.

### Tareas
- Crear endpoint de carga de PDF
- Validar tipo de archivo
- Almacenar en MinIO como evidencia
- Registrar metadata en borrador

### Entregables
- carga PDF funcional
- almacenamiento en MinIO
- metadata de validacion en borrador

---

## Fase Técnica 6. Importacion estructurada desde Excel canonico organizada por competencia

### Objetivo
Permitir la importacion estructurada desde Excel canonico del programa.

### Tareas
- Crear endpoint de preview de Excel canonico
- Validar workbook `.xlsx` con hojas Programa, Competencias, Resultados, Conocimientos y Criterios
- Generar preview sin persistencia relacional
- Confirmar importacion para materializar datos
- Organizar la estructura importada por competencia
- Mostrar resumen compacto tras importacion confirmada
- Abrir revision curricular importada en modal paginada por competencia

### Entregables
- preview funcional de Excel
- confirmacion de importacion
- estructura curricular importada por competencia
- resumen compacto y modal de competencias

La competencia es el contenedor principal de la estructura. Los resultados,
conocimientos y criterios se muestran y gestionan bajo la competencia. La
relacion de conocimientos y criterios con resultados de aprendizaje es opcional
y secundaria.

La UI curricular debe iniciar con selector/filtro de competencia. Resultados se
muestran para la competencia seleccionada; conocimientos y criterios se exponen
primero en selectores progresivos y solo se renderizan cuando el usuario los
elige.

### Tareas
- CRUD de competencias
- CRUD de resultados de aprendizaje
- CRUD de conocimientos de saber
- CRUD de conocimientos de proceso
- CRUD de criterios de evaluación
- Validaciones de no duplicidad
- Validaciones de campos obligatorios
- Integridad relacional

### Entregables
- módulo curricular completo
- validaciones activas
- datos persistidos correctamente

---

## Fase Técnica 7. Revisión y cierre del programa

### Objetivo
Cerrar el programa correctamente antes de habilitar el proyecto.

### Tareas
- Crear vista consolidada editable del programa
- Mostrar estructura jerárquica completa
- Mostrar estados por campo
- Crear validador de completitud del programa
- Crear acción explícita para cerrar programa
- Registrar auditoría de cierre

### Entregables
- vista consolidada funcional
- validación de completitud
- transición de estado a COMPLETO

---

## Fase Técnica 8. Bloqueo y habilitación del proyecto

### Objetivo
Respetar la dependencia del proyecto con el programa.

### Tareas
- Bloquear módulo del proyecto si el programa no está completo
- Mostrar mensaje explicativo
- Habilitar proyecto cuando el programa esté completo
- Habilitar `fuente-proyecto` con PDF evidencia y Excel/matriz estructurada
- Validar que el backend también impida acceso indebido

### Entregables
- bloqueo visual
- bloqueo funcional
- desbloqueo automático al completar programa

---

## Fase Técnica 9. Wizard del proyecto

### Objetivo
Implementar el flujo del proyecto formativo.

### Tareas
- Crear wizard del proyecto
- Integrar borradores del proyecto
- Definir pasos del proyecto
- Eliminar `datos-proyecto` como paso de entrada manual
- Mostrar progreso y estados
- Permitir navegación adelante/atrás

### Entregables
- wizard funcional del proyecto
- persistencia activa
- relación con el programa existente

---

## Fase Técnica 10. Carga documental del proyecto como evidencia

### Objetivo
Permitir la carga del PDF del proyecto como evidencia documental.

### Tareas
- Crear endpoint de carga del PDF del proyecto
- Validar tipo de archivo
- Almacenar en MinIO como evidencia bajo `proyectos-formativos/{referencia_id}/documentos/...`
- Registrar metadata en borrador

### Entregables
- flujo de carga PDF del proyecto funcional
- almacenamiento en MinIO con prefijo canonico de proyecto
- metadata de validacion en borrador

---

## Fase Tecnica 10B. Importacion estructurada del proyecto

### Objetivo
Permitir la carga de Excel/matriz del proyecto como unica fuente estructurada.

### Tareas
- Crear endpoint de preview de Excel/matriz del proyecto
- Validar hojas Proyecto, Fases y Actividades
- Generar preview sin persistencia relacional
- Confirmar importacion para materializar ProyectoFormativo, FaseProyecto y ActividadProyecto
- Almacenar Excel bajo `proyectos-formativos/{referencia_id}/excel/...`

### Entregables
- preview funcional del proyecto
- confirmacion de importacion
- metadata de Excel en borrador
- persistencia estructurada de proyecto, fases y actividades

---

## Fase Técnica 11. Gestión de fases y actividades

### Objetivo
Permitir CRUD completo de la estructura del proyecto.

### Tareas
- CRUD de fases
- CRUD de actividades
- Validar actividad obligatoriamente ligada a fase
- Validar no duplicidad dentro de la misma fase
- Mostrar resumen consolidado del proyecto

### Entregables
- módulo de fases funcional
- módulo de actividades funcional
- validaciones activas

---

## Fase Técnica 12. Revisión y cierre del proyecto

### Objetivo
Cerrar correctamente el proyecto y completar la Fase 1.

### Tareas
- Crear vista consolidada editable del proyecto
- Validar estructura mínima
- Crear acción explícita de cierre
- Registrar auditoría de cierre
- Mantener consistencia de estados

### Entregables
- proyecto puede pasar a COMPLETO
- cierre auditable
- consolidado final funcional

---

## Fase Técnica 13. Auditoría básica

### Objetivo
Registrar eventos mínimos del sistema.

### Tareas
- Registrar creación de programa
- Registrar actualización de programa
- Registrar cierre del programa
- Registrar creación de proyecto
- Registrar actualización de proyecto
- Registrar cierre del proyecto
- Registrar cambio de estado por inconsistencia posterior

### Entregables
- eventos mínimos persistidos
- trazabilidad base disponible

---

## Fase Técnica 14. Testing y estabilización

### Objetivo
Asegurar consistencia funcional del flujo punta a punta.

### Tareas
- Pruebas unitarias de validadores
- Pruebas de integración de módulos clave
- Pruebas end-to-end del flujo principal
- Validación de regresión
- Revisión de mensajes de error
- Corrección de estados inconsistentes

### Entregables
- flujo estable
- errores críticos corregidos
- criterios mínimos de calidad cumplidos

---

# 10. Dependencias funcionales

## Dependencias críticas

- No se puede cerrar el programa sin estructura curricular mínima.
- No se puede iniciar funcionalmente el proyecto sin programa completo.
- No se puede cerrar el proyecto sin fases y actividades válidas.
- No se debe implementar el cierre antes de tener validadores de completitud.
- No se debe implementar extracción sin persistencia de borradores.

---

# 11. Orden recomendado de ejecución en Codex

## Iteración 1
- Fundaciones
- Modelo de datos
- Migraciones

## Iteración 2
- Borradores
- Estados
- Base del wizard del programa

## Iteración 3
- Carga PDF como evidencia del programa
- Importacion Excel canonico

## Iteración 4
- CRUD curricular completo

## Iteración 5
- Revisión y cierre del programa
- Bloqueo/desbloqueo del proyecto

## Iteración 6
- Wizard del proyecto
- Carga PDF como evidencia del proyecto
- Importacion Excel del proyecto

## Iteración 7
- CRUD de fases y actividades

## Iteración 8
- Revisión y cierre del proyecto
- Auditoría

## Iteración 9
- Testing
- Estabilización
- Ajustes finales

---

# 12. Estrategia mínima de pruebas

## 12.1 Pruebas unitarias
Validar:
- completitud del programa
- completitud del proyecto
- duplicados
- integridad relacional
- reglas de transición de estado
- reglas de bloqueo del proyecto

## 12.2 Pruebas de integración
Validar:
- creación de programa
- carga de PDF del programa
- guardado en borrador
- CRUD curricular
- cierre del programa
- desbloqueo del proyecto
- creación del proyecto
- CRUD de fases y actividades
- cierre del proyecto

## 12.3 Pruebas end-to-end
Escenarios minimos:
1. Programa importado desde Excel canonico
2. Programa con correccion post-importacion
3. Proyecto bloqueado por programa incompleto
4. Proyecto habilitado despues del cierre del programa
5. Proyecto completo con fases y actividades
6. Programa editado despues del cierre y advertencia de impacto

---

# 13. Criterios técnicos de terminado

Una tarea se considera terminada cuando:

- respeta `BUSINESS_RULES.md`,
- respeta `SPECS.md`,
- mantiene trazabilidad con `TRACEABILITY_MATRIX.md`,
- usa el modelo definido en `DATA_MODEL.md`,
- cumple el alcance de Fase 1,
- persiste correctamente los datos,
- y tiene validación razonable.

---

# 14. Antipatrones que deben evitarse

- Implementar reglas de negocio solo en el frontend
- Permitir crear proyecto sin programa completo
- Asumir que extracción automática equivale a validación humana
- Mezclar conocimientos de saber y proceso en una estructura no tipada
- Perder borradores al cambiar de paso
- Cerrar bloques sin revisión explícita
- Duplicar lógica de estados en muchos lugares
- Construir todo el proyecto de una sola vez sin iteraciones pequeñas

---

# 15. Checklist de implementación

## Base
- [ ] repositorio configurado
- [ ] entorno configurado
- [ ] BD conectada
- [ ] migración inicial aplicada

## Programa
- [ ] modelo programa
- [ ] endpoints programa
- [ ] wizard programa
- [ ] PDF evidencia programa
- [ ] importacion Excel canonico programa
- [ ] CRUD competencias
- [ ] CRUD resultados
- [ ] CRUD saber
- [ ] CRUD proceso
- [ ] CRUD criterios
- [ ] revisión consolidada
- [ ] cierre del programa

## Proyecto
- [ ] bloqueo del proyecto
- [ ] modelo proyecto
- [ ] wizard proyecto
- [ ] fuente estructurada proyecto (Excel/matriz)
- [ ] CRUD fases
- [ ] CRUD actividades
- [ ] revisión consolidada
- [ ] cierre del proyecto

## Persistencia
- [ ] guardado automático
- [ ] recuperación de borrador
- [ ] persistencia de paso actual

## Auditoría
- [ ] eventos de creación
- [ ] eventos de actualización
- [ ] eventos de cierre
- [ ] eventos de cambio de consistencia

## Calidad
- [ ] pruebas unitarias
- [ ] pruebas de integración
- [ ] pruebas end-to-end
- [ ] revisión de mensajes UX

---

# 16. Instrucción final para Codex

Antes de generar código, Codex debe:

1. leer los documentos de negocio,
2. leer las specs,
3. leer las historias,
4. leer la matriz de trazabilidad,
5. leer el modelo de datos,
6. leer este plan de implementación,
7. implementar solo el módulo solicitado,
8. reportar ambigüedades antes de asumir comportamientos no definidos.

## Hito - Formato oficial GPFI-F-134 V05

1. Incorporar plantilla canónica y configuración documental persistente.
2. Generar Excel individual con una fila por asignación fase/actividad.
3. Generar consolidado estable con planeaciones `COMPLETO`.
4. Guardar y leer los artefactos mediante MinIO.
5. Exponer generación, estado y descarga tipada.
6. Integrar configuración, brechas, contadores y Blob en el wizard.
7. Verificar OOXML, imágenes, merges, filas adicionales, impresión y regresiones.
