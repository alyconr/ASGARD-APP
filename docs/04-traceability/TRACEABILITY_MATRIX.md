# TRACEABILITY_MATRIX.md
## Proyecto: Aplicación web para construcción de guías de aprendizaje SENA
## Fase: 1
## Estado: Matriz de trazabilidad inicial
## Última actualización: [YYYY-MM-DD]

## Decision funcional TASK-UNICO-CARRIL

La trazabilidad queda reinterpretada asi:

- Upload Module PDF Evidencia: carga, validacion basica y MinIO para programa y proyecto.
- Excel Import Module: validacion canonica `.xlsx`, preview, confirmacion e importacion relacional para programa y proyecto.
- Curriculum Module: consume la base importada por competencia sin adelantar el CRUD manual de TASK-09.
- Pending Reconciliation: solo atiende excepciones sin competencia confiable.
- No existe trazabilidad para carril manual como fuente activa.
- `datos-programa` y `datos-proyecto` quedan fuera de trazabilidad activa.
- La revision post-importacion del programa se traza a resumen compacto y modal paginada de competencias.
- La gestion curricular se traza a selector/filtro de competencia y seleccion progresiva de conocimientos/criterios.
- Proyecto usa MinIO `proyectos-formativos/{referencia_id}/documentos/...` para PDF evidencia y `proyectos-formativos/{referencia_id}/excel/...` para matriz Excel.

## Decision funcional DASHBOARD-MAESTRO-ASGARD

Se agrega trazabilidad para el dashboard maestro como entrada central de la Fase 1. Este componente agrega estado, metricas y mapa navegable, pero respeta las reglas existentes de cierre humano y dependencia entre modulos.

## Decision funcional ASISTENTE-GUIADO-TRANSVERSAL

Se agrega trazabilidad para un asistente visual reutilizable en los wizards de programa, proyecto y planeacion. Este asistente muestra instrucciones, faltantes, bloqueos y CTA derivados del estado real del sistema.

---

# 1. Propósito

Este documento conecta reglas de negocio, especificaciones funcionales, historias de usuario, componentes técnicos y casos de prueba sugeridos.

Su objetivo es asegurar consistencia entre:

- el dominio del negocio,
- la especificación funcional,
- la perspectiva del usuario,
- la implementación técnica,
- y la validación posterior.

La matriz de trazabilidad evita que se implementen funcionalidades fuera de alcance o sin sustento en los documentos base.

---

# 2. Regla de uso

Toda funcionalidad implementada en Fase 1 debe poder trazarse al menos a:

- una regla de negocio,
- un requisito funcional o técnico,
- una historia de usuario,
- y un componente o módulo de implementación.

Si una funcionalidad no puede trazarse, debe considerarse fuera de alcance hasta nueva revisión.

---

# 3. Matriz de trazabilidad principal

| Regla de Negocio | Descripción resumida | Spec relacionado | Historia relacionada | Componente sugerido | Caso de prueba sugerido |
|---|---|---|---|---|---|
| RN-04 | El flujo principal debe ser tipo wizard | RF-01, RF-13, RF-21 | HU-01, HU-13, HU-22 | Wizard UI | Validar navegación paso a paso |
| RN-09 | Todo avance debe guardarse automáticamente | RF-30, RF-31 | HU-02, HU-23 | Draft Service | Validar persistencia automática |
| RN-10 | El borrador debe conservar paso actual y datos parciales | RF-30, RF-31 | HU-02, HU-23 | Draft Service | Recuperar borrador desde el mismo paso |
| RN-DASHBOARD-ASGARD | La home debe centralizar acceso, bloqueos, metricas y mapa navegable sin saltar reglas de negocio | RF-DASHBOARD | HU-02A | Dashboard Service / Master Dashboard UI | Validar modulos habilitados, metricas y grafo navegable |
| RN-ASISTENTE-GUIADO | Los wizards deben mostrar guia contextual con severidad, checklist y acciones sin reemplazar validaciones reales | RF-GUIA-ASGARD | HU-02B | Wizard Guide Engine / WizardGuideAssistant | Validar mensajes por paso, bloqueos entre modulos y persistencia UX |
| RN-13 / RN-13A / RN-UNICO-CARRIL | El programa y proyecto soportan PDF evidencia y Excel canonico como unica fuente estructurada; no existe carril manual ni pasos `datos-programa`/`datos-proyecto` | RF-04, RF-05, RF-06, RF-07, RF-21, RF-22, RF-23, RF-24 | HU-03, HU-04, HU-05, HU-06, HU-17, HU-18, HU-19 | Excel Import Service | Validar preview e importacion Excel por competencia |
| RN-FLUJO-COMPACTO | El origen documental del programa muestra resumen compacto tras importacion y abre modal paginada de competencias | RF-06, RF-13 | HU-05, HU-13 | Programa Wizard / Excel Import UI | Validar resumen compacto, apertura de modal y paginacion |
| RN-CURRICULO-FOCALIZADO | La estructura curricular carga una competencia seleccionada y conocimientos/criterios se eligen progresivamente | RF-08, RF-09, RF-10, RF-11, RF-12 | HU-07, HU-08, HU-09, HU-10, HU-11 | Curriculum Module | Validar selector de competencia y render progresivo |
| RN-14 | Si la importacion Excel no resuelve campos, debe habilitarse cargue manual SOLO para lo faltante | RF-07, RF-24 | HU-06, HU-19 | Extraction Feedback UI | Validar fallback manual para lo faltante |
| RN-15 | La validacion Excel debe conservar errores y habilitar fallback manual SOLO para lo estrictamente faltante | RF-06, RF-07 | HU-05, HU-06 | Excel Import Service | Validar workbook invalido y fallback manual para lo faltante |
| RN-16 | La extracción automática no equivale a validación humana | RF-13, RF-27 | HU-13, HU-22 | Review Screen | Validar confirmación explícita |
| RN-18 | El programa debe tener código y nombre | RF-02 | HU-01, HU-14 | Programa Form | Validar obligatorios mínimos |
| RN-22 | Cada competencia debe tener código y nombre | RF-08 | HU-07 | Competencia Module | Validar estructura mínima de competencia |
| RN-23 | Cada competencia debe tener resultados, saber, proceso y criterios para cierre, excepto etapa practica sin hijos | RF-09, RF-10, RF-11, RF-12, RF-14 | HU-08, HU-09, HU-10, HU-11, HU-14 | Curriculum Module | Validar completitud curricular |
| RN-24 | El programa solo se completa cuando toda competencia está completa | RF-14, RF-15 | HU-13, HU-14 | Completion Validator | Validar cierre del programa |
| RN-25 | Todo resultado pertenece a una competencia | RF-09 | HU-08 | Curriculum Module | Validar integridad relacional de resultados |
| RN-28 | Saber y proceso se almacenan separados | RF-10, RF-11 | HU-09, HU-10 | Knowledge Module | Validar separación por tipo |
| RN-32 | Todo criterio pertenece a una competencia | RF-12 | HU-11 | Criteria Module | Validar integridad relacional de criterios |
| RN-34A | Solo conocimientos y criterios sin competencia confiable quedan pendientes de asignacion | RF-06, RF-07, RF-10, RF-12 | HU-05, HU-06, HU-10, HU-11 | Excel Import Service / Pending Reconciliation | Preview con importacion por competencia y pendientes reales |
| RN-35 | El proyecto depende del programa completo | RF-16, RF-17, RF-18 | HU-15, HU-16 | State Gate / Access Control | Validar bloqueo del proyecto |
| RN-35A | El proyecto debe partir de fuente estructurada (Excel/matriz) | RF-21, RF-22, RF-23, RF-24 | HU-17, HU-18, HU-19 | Fuente estructurada Proyecto | Validar importacion Excel del proyecto |
| RN-36 | El proyecto debe tener código, nombre, versión, fases y actividades | RF-19, RF-25, RF-26, RF-28, RF-29 | HU-20, HU-21, HU-22 | Proyecto Module | Validar estructura mínima del proyecto |
| RN-38 | Toda actividad debe pertenecer a una fase | RF-26 | HU-21 | Actividad Module | Validar relación fase-actividad |
| RN-40 | El proyecto solo se cierra con estructura mínima válida | RF-28, RF-29 | HU-22 | Completion Validator Proyecto | Validar cierre del proyecto |
| RN-41 | El programa maneja BORRADOR, EN_REVISION y COMPLETO | ET-01, ET-02, ET-03 | HU-14, HU-24 | State Machine | Validar transición de estados del programa |
| RN-42 | El proyecto maneja BLOQUEADO, BORRADOR, EN_REVISION y COMPLETO | ET-04, ET-05, ET-06, ET-07 | HU-15, HU-16, HU-22 | State Machine | Validar transición de estados del proyecto |
| RN-49 | Si un programa completo pierde consistencia, vuelve a revisión | ET-08 | HU-24 | State Machine | Validar regresión a EN_REVISION |
| RN-50 | El sistema debe advertir impacto sobre el proyecto asociado | RF-35 | HU-24 | Warning / Notification UI | Validar advertencia de impacto |
| RN-51 | Antes de cerrar un bloque debe existir vista consolidada editable | RF-13, RF-27 | HU-13, HU-22 | Review Screen | Validar revisión previa al cierre |
| RN-55 | No puede existir hijo sin padre relacional | RF-09, RF-10, RF-11, RF-12, RF-25, RF-26 | HU-08, HU-09, HU-10, HU-11, HU-21 | Domain Validation Layer | Validar integridad relacional |
| RN-58 | Debe existir auditoría básica | RF-34 | HU-24 | Audit Service | Validar creación de eventos de auditoría |
| RN-60 | La implementación debe ser incremental y por módulos | Sección 17 del SPECS | No aplica directamente | Implementation Plan / Codex Tasks | Validar orden de ejecución de tareas |
| RN-63 | Debe respetarse el stack técnico definido | Sección 17 del SPECS | No aplica directamente | Architecture Layer | Validar coherencia con stack aprobado |

---

# 4. Trazabilidad por épica funcional

## 4.1 Épica: Inicio y borradores
Incluye:
- HU-01
- HU-02
- HU-23

Relaciona principalmente:
- RN-04
- RN-09
- RN-10

Componentes:
- Wizard UI
- Draft Service

---

## 4.2 Épica: Carga y importacion del programa
Incluye:
- HU-03
- HU-04
- HU-05
- HU-06

Relaciona principalmente:
- RN-13 / RN-UNICO-CARRIL
- RN-13A
- RN-14
- RN-15
- RN-16

Componentes:
- Upload Module
- Excel Import Service
- Curriculum Module

---

## 4.3 Épica: Gestión curricular del programa
Incluye:
- HU-07
- HU-08
- HU-09
- HU-10
- HU-11
- HU-12
- HU-13
- HU-14

Relaciona principalmente:
- RN-18
- RN-22
- RN-23
- RN-24
- RN-25
- RN-28
- RN-32

Componentes:
- Programa Module
- Competencia Module
- Curriculum Module
- Review Screen
- Completion Validator

---

## 4.4 Épica: Habilitación del proyecto
Incluye:
- HU-15
- HU-16

Relaciona principalmente:
- RN-01
- RN-02
- RN-35
- RN-42

Componentes:
- State Gate
- Access Control
- State Machine

---

## 4.5 Épica: Carga y importacion del proyecto
Incluye:
- HU-17
- HU-18
- HU-19

Relaciona principalmente:
- RN-13
- RN-14
- RN-15
- RN-16
- RN-35A
- RN-36

Componentes:
- Upload Module Proyecto
- Fuente estructurada Proyecto (Excel/matriz)
- Proyecto Module

---

## 4.6 Épica: Gestión de fases y actividades
Incluye:
- HU-20
- HU-21
- HU-22

Relaciona principalmente:
- RN-36
- RN-38
- RN-40

Componentes:
- Fase Module
- Actividad Module
- Review Screen Proyecto
- Completion Validator Proyecto

---

## 4.7 Épica: Persistencia e impacto
Incluye:
- HU-23
- HU-24

Relaciona principalmente:
- RN-09
- RN-10
- RN-49
- RN-50
- RN-58

Componentes:
- Draft Service
- State Machine
- Warning UI
- Audit Service

---

# 5. Trazabilidad por componente técnico

## Wizard UI
Relaciona:
- RN-04
- RF-01
- RF-13
- HU-01
- HU-13
- HU-22

## Draft Service
Relaciona:
- RN-09
- RN-10
- RF-30
- RF-31
- HU-02
- HU-23

## Upload Module
Relaciona:
- RF-04
- RF-21
- HU-03
- HU-17

## Excel Import Service
Relaciona:
- RN-13
- RN-13A
- RN-15
- RN-16
- RF-05
- RF-06
- RF-07
- RF-22
- RF-23
- RF-24
- HU-04
- HU-05
- HU-06
- HU-18
- HU-19

## Programa Module
Relaciona:
- RN-18
- RF-01
- RF-02
- HU-01
- HU-14

## Competencia Module
Relaciona:
- RN-22
- RF-08
- HU-07

## Curriculum Module
Relaciona:
- RN-23
- RN-25
- RN-28
- RN-32
- RF-09
- RF-10
- RF-11
- RF-12
- HU-08
- HU-09
- HU-10
- HU-11

## Review Screen
Relaciona:
- RN-16
- RN-51
- RF-13
- RF-27
- HU-13
- HU-22

## Completion Validator
Relaciona:
- RN-24
- RN-40
- RF-14
- RF-15
- RF-28
- RF-29
- HU-14
- HU-22

## State Machine
Relaciona:
- RN-41
- RN-42
- RN-49
- RN-50
- ET-01
- ET-02
- ET-03
- ET-04
- ET-05
- ET-06
- ET-07
- ET-08
- ET-09

## Proyecto Module
Relaciona:
- RN-35
- RN-36
- RF-16
- RF-17
- RF-18
- RF-19
- RF-20
- HU-15
- HU-16
- HU-17
- HU-18
- HU-19

## Fase Module
Relaciona:
- RN-36
- RF-25
- HU-20

## Actividad Module
Relaciona:
- RN-38
- RF-26
- HU-21

## Audit Service
Relaciona:
- RN-58
- RF-34
- HU-24

---

# 6. Casos de prueba funcionales sugeridos

## CP-01. Programa desde Excel canonico completo
Validar que un usuario pueda:
- iniciar programa,
- cargar PDF como evidencia si existe,
- cargar y confirmar Excel canonico,
- revisar resumen compacto y modal de competencias,
- gestionar una competencia seleccionada,
- revisar consolidado,
- cerrar programa.

## CP-02. Programa con importacion Excel parcial
Validar que el sistema:
- reciba PDF,
- conserve PDF como evidencia,
- detecte pendientes de importacion Excel,
- permita correccion puntual de faltantes,
- y cierre el programa correctamente.

## CP-03. Proyecto bloqueado
Validar que el proyecto:
- permanezca bloqueado,
- muestre mensaje explicativo,
- y no permita acceso funcional mientras el programa esté incompleto.

## CP-04. Proyecto habilitado
Validar que al cerrar el programa:
- el proyecto se desbloquee,
- pueda iniciarse,
- y quede asociado al programa.

## CP-05. Proyecto completo
Validar que un usuario pueda:
- cargar PDF del proyecto como evidencia,
- importar proyecto desde Excel/matriz,
- crear fases,
- crear actividades,
- revisar consolidado,
- cerrar proyecto.

## CP-06. Impacto por edición posterior
Validar que si un programa completo se edita y pierde consistencia:
- vuelva a EN_REVISION,
- el sistema emita advertencia,
- y quede visible el posible impacto sobre el proyecto.

---

# 7. Reglas de mantenimiento de la matriz

## MT-01
Toda nueva regla de negocio debe mapearse a uno o más requisitos funcionales.

## MT-02
Todo requisito funcional importante debe mapearse a una o más historias de usuario.

## MT-03
Toda funcionalidad implementada debe poder vincularse a un componente técnico.

## MT-04
Toda funcionalidad crítica debe tener al menos un caso de prueba sugerido.

## MT-05
Si un módulo nuevo no tiene trazabilidad, debe revisarse antes de implementarse.

---

# 8. Convención de actualización

Cuando el proyecto cambie:

1. primero se actualiza `BUSINESS_RULES.md`,
2. luego `SPECS.md`,
3. luego `USER_STORIES.md`,
4. después `TRACEABILITY_MATRIX.md`,
5. y por último los planes operativos.

La matriz no debe ser el origen del cambio; debe reflejarlo.

---

# 9. Definición operativa de uso

Esta matriz se usa para:

- validar que el desarrollo respete el negocio,
- verificar cobertura funcional,
- organizar pruebas,
- justificar decisiones de implementación,
- y evitar desarrollo fuera de alcance.
