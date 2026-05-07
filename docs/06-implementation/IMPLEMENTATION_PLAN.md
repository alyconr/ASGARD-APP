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

## Decision funcional TASK-08.5

Antes de continuar con TASK-09, se introduce una tarea puente:

- desactivar la extraccion curricular desde PDF en el flujo activo;
- conservar PDF como evidencia documental en MinIO;
- agregar importacion estructurada desde Excel canonico `.xlsx`;
- exigir preview sin persistencia relacional antes de confirmacion;
- confirmar importacion para materializar programa, competencias, resultados, conocimientos y criterios.

---

# 3. Objetivo general de implementación

Construir la Fase 1 de una aplicación web que permita:

- cargar información del programa de formación,
- cargar información del proyecto formativo,
- conservar PDF como evidencia documental,
- importar datos desde Excel canonico cuando aplique,
- permitir fallback manual cuando no sea posible,
- guardar siempre el avance en borrador,
- revisar y validar la información,
- bloquear el proyecto hasta que el programa esté completo,
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
- Diagnóstico de legibilidad del PDF
- Extracción híbrida de PDF
- Revisión consolidada editable
- Validación de completitud
- Bloqueo/desbloqueo del proyecto
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

## PI-07. Soporte a extracción parcial
La extracción automática debe diseñarse para convivir con edición manual sin romper el flujo.

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
6. Importacion estructurada desde Excel canonico
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

## 7.5 Extracción documental
- lectura PDF con capa de texto
- OCR opcional si luego se decide habilitarlo
- fallback manual obligatorio

## 7.6 Almacenamiento de archivos
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
- Implementar navegación entre pasos
- Integrar autosave
- Mostrar barra o indicador de progreso
- Mostrar estado por bloque

### Entregables
- wizard funcional del programa
- persistencia entre pasos
- navegación adelante/atrás sin pérdida de datos

---

## Fase Técnica 5. Extracción híbrida del programa

### Objetivo
Permitir el cargue por PDF del programa con fallback manual.

### Tareas
- Crear endpoint de carga de PDF
- Validar tipo de archivo
- Analizar legibilidad del PDF
- Intentar extracción de campos del programa
- Marcar campos extraídos, pendientes o ambiguos
- Mostrar motivo de fallo de extracción
- Permitir completar manualmente los faltantes

### Campos a extraer
- código del programa
- nombre del programa
- competencias
- resultados de aprendizaje
- conocimientos de saber
- conocimientos de proceso
- criterios de evaluación

### Entregables
- carga PDF funcional
- diagnóstico de legibilidad
- respuesta estructurada de extracción
- fallback manual habilitado

---

## Fase Técnica 6. Gestión curricular

### Objetivo
Permitir CRUD completo de la estructura curricular del programa.

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
- Mostrar progreso y estados
- Permitir navegación adelante/atrás

### Entregables
- wizard funcional del proyecto
- persistencia activa
- relación con el programa existente

---

## Fase Técnica 10. Extracción híbrida del proyecto

### Objetivo
Permitir cargue por PDF del proyecto con fallback manual.

### Tareas
- Crear endpoint de carga del PDF del proyecto
- Validar tipo de archivo
- Analizar legibilidad
- Intentar extracción de:
  - nombre del proyecto
  - código del proyecto
  - versión del proyecto
  - fases del proyecto
  - actividades del proyecto
- Marcar campos faltantes
- Permitir ingreso manual de campos no extraídos

### Entregables
- flujo híbrido del proyecto funcional
- prellenado parcial o total
- fallback manual activo

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
- Extracción híbrida del programa
- Fallback manual

## Iteración 4
- CRUD curricular completo

## Iteración 5
- Revisión y cierre del programa
- Bloqueo/desbloqueo del proyecto

## Iteración 6
- Wizard del proyecto
- Extracción híbrida del proyecto

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
Escenarios mínimos:
1. Programa manual completo
2. Programa con extracción parcial + completado manual
3. Proyecto bloqueado por programa incompleto
4. Proyecto habilitado después del cierre del programa
5. Proyecto completo con fases y actividades
6. Programa editado después del cierre y advertencia de impacto

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
- [ ] fallback manual
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
- [ ] fuente estructurada proyecto por definir antes de implementacion
- [ ] fallback manual
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
