# Esquema de Base de Datos — Módulo 3: Registrar Actividades Docente-Asistenciales (RENADS)

## Contexto y alcance

El módulo **Registrar Actividades Docente-Asistenciales** registra las actividades realizadas por los internos en una sede docente, como evidencia del cumplimiento de servicios, prácticas, rotaciones o actividades formativas supervisadas. Cada actividad se vincula a un **interno**, un **internado activo** (módulo 2), una **sede docente** (`ipress`), un **tutor** responsable, un periodo y —cuando corresponda— una **rotación autorizada** (módulo 2). El tutor valida, observa o rechaza cada actividad.

### Reglas de negocio clave (validación a nivel de aplicación)

- Solo se registran actividades para internados **activos** (RN-1).
- La actividad debe pertenecer al **periodo vigente** del internado (RN-2).
- Si ocurre durante una rotación, debe asociarse a una rotación **autorizada** (RN-3/4).
- Toda actividad se asocia a una **sede docente** (RN-5) y a un **tutor** responsable (RN-6).
- Las actividades **observadas** pueden ser **subsanadas** (RN-7).
- Las actividades **validadas** no se modifican sin registrar trazabilidad (RN-8); requieren permisos especiales (RNF-4).
- Control de **duplicidad** por interno, fecha, sede, servicio y horario (RN-9).
- Evidencias documentales en **PDF** en repositorio externo (RN-10).

> **Convenciones (heredadas):** tablas/columnas/descripciones en **español**; adjuntos en **repositorio externo** (solo `referencia_externa`); se reutilizan tablas nativas de Django y tablas de los **módulos 1 y 2**.

---

## 1. Tablas reutilizadas

### Nativas de Django
`auth_user`, `auth_group`, `auth_permission`, `django_content_type`.

### De módulos 1 y 2
| Tabla | Origen | Uso en el módulo 3 |
|-------|--------|--------------------|
| `interno` | Módulo 2 | Interno que realiza la actividad |
| `internado` | Módulo 2 | Internado activo al que pertenece |
| `rotacion` | Módulo 2 | Rotación autorizada asociada (opcional) |
| `tutor` | Módulo 2 | Tutor / docente supervisor |
| `ipress` | Módulo 1 | Sede docente |
| `servicio_area` | Módulo 2 | Servicio, área o unidad |
| `documento` | Módulo 1 | Evidencia PDF |
| `bitacora_auditoria` | Módulo 1 | Auditoría transversal |

---

## 2. Catálogos

Patrón común: `id` (PK), `codigo` (varchar, único), `nombre` (varchar), `activo` (bool).

| Tabla | Descripción | Columnas adicionales |
|-------|-------------|----------------------|
| `tipo_actividad` | Tipo de actividad docente-asistencial | — |
| `estado_actividad` | Estados de la actividad (7) | `orden` (int) |

### Valores de `estado_actividad`
`REGISTRADA`, `PENDIENTE_VALIDACION`, `OBSERVADA`, `SUBSANADA`, `VALIDADA`, `RECHAZADA`, `CERRADA`.

---

## 3. Actividad docente-asistencial

### `actividad_docente_asistencial`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `interno_id` | FK → `interno` | No | Interno |
| `internado_id` | FK → `internado` | No | Internado activo |
| `ipress_id` | FK → `ipress` | No | Sede docente |
| `rotacion_id` | FK → `rotacion` | Sí | Rotación autorizada asociada (si corresponde) |
| `tutor_id` | FK → `tutor` | No | Tutor / docente responsable |
| `servicio_area_id` | FK → `servicio_area` | No | Servicio, área o unidad |
| `tipo_actividad_id` | FK → `tipo_actividad` | No | Tipo de actividad |
| `estado_actual_id` | FK → `estado_actividad` | No | Estado actual |
| `fecha_actividad` | date | No | Fecha de la actividad |
| `descripcion` | text | Sí | Descripción o detalle |
| `carga_horaria` | decimal(5,2) | Sí | Horas o carga horaria |
| `creado_por` | FK → `auth_user` | No | |
| `creado_en` | datetime | No | |
| `actualizado_en` | datetime | No | |

### `validacion_actividad` (procesos 3.2 — RF-DA-13/14/15)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `actividad_id` | FK → `actividad_docente_asistencial` | No | Actividad validada |
| `resultado` | varchar(20) | No | `VALIDADA` / `OBSERVADA` / `RECHAZADA` |
| `comentario` | text | Sí | Comentario de validación |
| `validado_por` | FK → `auth_user` | No | Usuario validador |
| `fecha_validacion` | datetime | No | Fecha y usuario validador |
| `creado_en` | datetime | No | |

### `historial_estado_actividad` (trazabilidad — RN-8 / RF-DA-20)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `actividad_id` | FK → `actividad_docente_asistencial` | No | |
| `estado_id` | FK → `estado_actividad` | No | Estado registrado |
| `cambiado_por` | FK → `auth_user` | No | Responsable |
| `cambiado_en` | datetime | No | Fecha y hora |
| `observacion` | text | Sí | Observaciones |

---

## 4. Adjuntos y auditoría

Se reutiliza la tabla `documento` (módulo 1, relación genérica vía `django_content_type`); en este módulo se adjunta a `actividad_docente_asistencial` como evidencia PDF. La tabla `bitacora_auditoria` registra cambios sobre actividades (RN-8, RNF-3/4).

---

## 5. Mapa de relaciones

```
actividad_docente_asistencial >── interno (módulo 2)
actividad_docente_asistencial >── internado (módulo 2, activo)
actividad_docente_asistencial >── ipress (módulo 1, sede docente)
actividad_docente_asistencial >── rotacion (módulo 2, opcional)
actividad_docente_asistencial >── tutor (módulo 2)
actividad_docente_asistencial >── servicio_area (módulo 2)
actividad_docente_asistencial >── tipo_actividad
actividad_docente_asistencial >── estado_actividad (estado_actual)
actividad_docente_asistencial ──< validacion_actividad
actividad_docente_asistencial ──< historial_estado_actividad >── estado_actividad

documento          >── django_content_type  (genérico → actividad_docente_asistencial)
bitacora_auditoria >── django_content_type  (genérico)
```

---

## 6. Trazabilidad de requerimientos

- **RN-1 (solo internados activos):** validación sobre `internado.estado_actual_id = ACTIVO`.
- **RN-2 (periodo vigente):** validación de `fecha_actividad` contra fechas del `internado`.
- **RN-3/4 (rotación autorizada):** `actividad.rotacion_id` debe referir una `rotacion` en estado `AUTORIZADA`/`EN_CURSO`.
- **RN-5/6 (sede y tutor):** `ipress_id` y `tutor_id` no nulos.
- **RN-7 (subsanación):** estado `OBSERVADA` → `SUBSANADA` en `historial_estado_actividad`.
- **RN-8 (validadas no se modifican sin trazabilidad):** `historial_estado_actividad` + `bitacora_auditoria`; permisos vía `auth_permission`.
- **RN-9 (duplicidad):** validación por (`interno_id`, `fecha_actividad`, `ipress_id`, `servicio_area_id`).
- **RN-10 (evidencia PDF):** `documento` con `referencia_externa`.
- **RF-DA-13/14/15/16 (validar/observar/rechazar/subsanar):** `validacion_actividad` + `estado_actividad`.
- **RF-DA-17/18/19 (consultas, consolidado, exportación PDF/Excel):** lectura sobre `actividad_docente_asistencial` con joins a módulos 1 y 2.
