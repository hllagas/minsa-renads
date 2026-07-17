# Esquema de Base de Datos — Módulo 2: Registrar Internados (RENADS)

## Contexto y alcance

El módulo **Registrar Internados** registra a los estudiantes (alumnos de último año de pregrado o profesionales de segunda especialidad) y los vincula a una universidad, un **Convenio Específico vigente** (módulo 1), una sede docente (`ipress`), un tutor responsable y un ámbito geográfico sanitario. También controla las **rotaciones** del estudiante entre establecimientos del mismo ámbito geográfico sanitario y su autorización por las autoridades suscritas en el Convenio Específico.

### Reglas de negocio clave (validación a nivel de aplicación)

- Todo estudiante se asocia a una universidad y a un Convenio Específico **vigente/suscrito/publicado** (RN-1..4).
- Todo estudiante tiene un tutor responsable (RN-5).
- Duración máxima del internado: **1 año** (RN-6).
- Rotaciones solo entre establecimientos del **mismo ámbito geográfico sanitario** (RN-8).
- Máximo **4 rotaciones** por estudiante en todo el internado (RN-9).
- Rotaciones autorizadas **solo** por autoridades suscritas en el Convenio Específico (RN-10).
- No iniciar rotación sin autorización registrada (RN-11).
- No registrar rotaciones fuera de las fechas del internado (RN-12).
- No exceder los campos clínicos autorizados (RN-13).
- Cambio de tutor registrado con fecha, motivo y responsable (RN-14).
- Todo cambio de estado de internado/rotación queda en bitácora (RN-15).
- Registro de estudiantes en **doble modalidad**: **individual** y **masiva** vía archivo Excel (RN-16, ver §7 bis).
- La **universidad** asigna internos a los **campos clínicos disponibles** por sede docente y carrera profesional definidos en los Convenios Específicos (RN-17).
- **Orden de prelación** de asignación de internos: por **orden de mérito** según `nota_promedio_ponderado` (mayor a menor) (RN-18).

> **Convenciones (heredadas del módulo 1):** tablas/columnas/descripciones en **español**; adjuntos en **repositorio externo** (solo `referencia_externa`); se reutilizan tablas nativas de Django y las tablas del **módulo 1** (`convenio`, `campo_clinico`, `ipress`, `universidad`, `carrera_profesional`, `especialidad`, `ambito_geografico_sanitario`, `participante_convenio`, `documento`, `bitacora_auditoria`).

---

## 1. Tablas reutilizadas

### Nativas de Django
`auth_user`, `auth_group`, `auth_permission`, `django_content_type` (relación genérica de `documento` y `bitacora_auditoria`).

### Del módulo 1 (Gestionar Convenios)
| Tabla | Uso en el módulo 2 |
|-------|--------------------|
| `convenio` | Convenio Específico vigente que respalda el internado |
| `campo_clinico` | Validación de disponibilidad de campo clínico |
| `ipress` | Sede docente principal y sedes de rotación |
| `universidad` | Universidad del estudiante |
| `carrera_profesional` | Carrera / programa del estudiante |
| `especialidad` | Especialidad (segunda especialidad) |
| `ambito_geografico_sanitario` | Ámbito permitido para internado y rotaciones |
| `ubigeo` | Ubicación geográfica (distrito INEI) de estudiante y tutor |
| `participante_convenio` | Autoridades suscritas que autorizan rotaciones |
| `documento` | Adjuntos PDF (autorizaciones, sustentos) |
| `bitacora_auditoria` | Auditoría transversal |

---

## 2. Catálogos

Patrón común: `id` (PK), `codigo` (varchar, único), `nombre` (varchar), `activo` (bool).

| Tabla | Descripción | Columnas adicionales |
|-------|-------------|----------------------|
| `estado_internado` | Estados del internado (12) | `orden` (int) |
| `estado_rotacion` | Estados de la rotación (8) | `orden` (int) |
| `servicio_area` | Servicio, área o unidad de rotación | — |
| `tipo_documento_identidad` | Tipo de documento de identidad | valores: `DNI`, `CE`, `PASAPORTE` |
| `parentesco` | Tipo de parentesco del contacto de emergencia del estudiante | — |

### Valores de `estado_internado`
`REGISTRADO`, `PENDIENTE_VALIDACION`, `OBSERVADO`, `VALIDADO`, `ACTIVO`, `EN_ROTACION_SOLICITADA`, `EN_ROTACION_AUTORIZADA`, `EN_ROTACION_OBSERVADA`, `SUSPENDIDO`, `RETIRADO`, `CULMINADO`, `ANULADO`.

### Valores de `estado_rotacion`
`SOLICITADA`, `PENDIENTE_AUTORIZACION`, `OBSERVADA`, `AUTORIZADA`, `RECHAZADA`, `EN_CURSO`, `CULMINADA`, `CANCELADA`.

### Valores de `parentesco`
`PADRE`, `MADRE`, `HERMANO`, `CONYUGE`, `HIJO`, `ABUELO`, `TIO`, `OTRO`.

---

## 3. Estudiante

### `estudiante`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `tipo_documento_identidad_id` | FK → `tipo_documento_identidad` | No | Tipo de documento |
| `numero_documento` | varchar(20) | No | Número de documento de identidad |
| `nombres` | varchar(150) | No | Nombres |
| `apellido_paterno` | varchar(100) | No | Apellido paterno |
| `apellido_materno` | varchar(100) | Sí | Apellido materno |
| `fecha_nacimiento` | date | Sí | Fecha de nacimiento |
| `sexo` | varchar(1) | Sí | `M` / `F` |
| `correo` | varchar(255) | Sí | Correo electrónico |
| `telefono` | varchar(30) | Sí | Teléfono |
| `direccion` | varchar(500) | Sí | Dirección |
| `ubigeo_id` | FK → `ubigeo` (módulo 1) | Sí | Ubicación geográfica (UBIGEO) |
| `universidad_id` | FK → `universidad` | No | Universidad de procedencia |
| `carrera_profesional_id` | FK → `carrera_profesional` | No | Carrera / programa |
| `codigo_universitario` | varchar(50) | Sí | Código universitario / matrícula |
| `anio_academico` | int | Sí | Año académico |
| `nota_promedio_ponderado` | decimal(4,2) | Sí | Nota promedio ponderado (escala 0–20) |
| `contacto_emergencia_nombre` | varchar(255) | Sí | Nombre del contacto de emergencia |
| `contacto_emergencia_telefono` | varchar(30) | Sí | Teléfono del contacto de emergencia |
| `contacto_emergencia_parentesco_id` | FK → `parentesco` | Sí | Parentesco del contacto de emergencia |
| `activo` | bool | No | |
| `creado_por` | FK → `auth_user` | No | |
| `creado_en` | datetime | No | |
| **Único** | (`tipo_documento_identidad_id`, `numero_documento`) | | |

---

## 4. Tutor / docente

### `tutor`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `tipo_documento_identidad_id` | FK → `tipo_documento_identidad` | No | Tipo de documento |
| `numero_documento` | varchar(20) | No | Número de documento de identidad |
| `nombres` | varchar(150) | No | Nombres |
| `apellido_paterno` | varchar(100) | No | Apellido paterno |
| `apellido_materno` | varchar(100) | Sí | Apellido materno |
| `correo` | varchar(255) | Sí | Correo electrónico |
| `telefono` | varchar(30) | Sí | Teléfono |
| `numero_colegiatura` | varchar(50) | Sí | Número de colegiatura |
| `direccion` | varchar(500) | Sí | Dirección |
| `ubigeo_id` | FK → `ubigeo` (módulo 1) | Sí | Ubicación geográfica (UBIGEO) |
| `especialidad_id` | FK → `especialidad` | Sí | Especialidad del tutor |
| `ipress_id` | FK → `ipress` | Sí | Establecimiento al que pertenece |
| `activo` | bool | No | |

---

## 5. Interno

### `interno`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `estudiante_id` | FK → `estudiante` | No | Estudiante |
| `convenio_id` | FK → `convenio` | No | Convenio Específico vigente que lo respalda |
| `campo_clinico_id` | FK → `campo_clinico` | No | Campo clínico autorizado asignado |
| `ipress_id` | FK → `ipress` | No | Sede docente principal |
| `tutor_id` | FK → `tutor` | No | Tutor responsable actual |
| `ambito_geografico_sanitario_id` | FK → `ambito_geografico_sanitario` | No | Ámbito geográfico sanitario |
| `estado_actual_id` | FK → `estado_internado` | No | Estado actual |
| `fecha_inicio` | date | No | Fecha de inicio |
| `fecha_fin` | date | No | Fecha de fin (máx. 1 año) |
| `observaciones` | text | Sí | Observaciones |
| `creado_por` | FK → `auth_user` | No | |
| `creado_en` | datetime | No | |
| `actualizado_en` | datetime | No | |

### `historial_estado_internado` (trazabilidad — RN-15)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `interno_id` | FK → `interno` | No | |
| `estado_id` | FK → `estado_internado` | No | Estado registrado |
| `cambiado_por` | FK → `auth_user` | No | Responsable |
| `cambiado_en` | datetime | No | Fecha y hora |
| `observacion` | text | Sí | Observaciones |

### `historial_tutor` (cambio de tutor — RN-14)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `interno_id` | FK → `interno` | No | |
| `tutor_id` | FK → `tutor` | No | Tutor asignado en este registro |
| `fecha_cambio` | date | No | Fecha del cambio |
| `motivo` | text | No | Motivo del cambio |
| `responsable_id` | FK → `auth_user` | No | Responsable del cambio |
| `creado_en` | datetime | No | |

---

## 6. Rotaciones

### `rotacion`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `interno_id` | FK → `interno` | No | Interno |
| `numero_rotacion` | int | No | Número de rotación (1–4, RN-9) |
| `ipress_origen_id` | FK → `ipress` | No | Sede de origen |
| `ipress_destino_id` | FK → `ipress` | No | Sede de destino |
| `servicio_area_id` | FK → `servicio_area` | No | Servicio, área o unidad |
| `estado_actual_id` | FK → `estado_rotacion` | No | Estado actual |
| `fecha_inicio` | date | No | Inicio de la rotación |
| `fecha_fin` | date | No | Fin de la rotación |
| `observaciones` | text | Sí | Observaciones |
| `creado_por` | FK → `auth_user` | No | |
| `creado_en` | datetime | No | |

### `autorizacion_rotacion` (RN-10/11)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `rotacion_id` | FK → `rotacion` | No | Rotación |
| `participante_convenio_id` | FK → `participante_convenio` | No | Autoridad suscrita en el Convenio Específico que autoriza |
| `resultado` | varchar(20) | No | `APROBADO` / `OBSERVADO` / `RECHAZADO` |
| `fecha_autorizacion` | date | No | Fecha de autorización |
| `observaciones` | text | Sí | Observaciones |
| `autorizado_por` | FK → `auth_user` | No | Usuario que registra la autorización |
| `creado_en` | datetime | No | |

### `historial_estado_rotacion` (trazabilidad — RN-15)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `rotacion_id` | FK → `rotacion` | No | |
| `estado_id` | FK → `estado_rotacion` | No | Estado registrado |
| `cambiado_por` | FK → `auth_user` | No | Responsable |
| `cambiado_en` | datetime | No | Fecha y hora |
| `observacion` | text | Sí | Observaciones |

---

## 6 bis. Carga masiva de estudiantes (propuesta)

El registro de estudiantes tiene **doble modalidad** (RN-16):

- **Individual:** `POST /api/v1/students/` (contemplado).
- **Masiva:** carga de un **archivo Excel** (`.xlsx`) con una fila por estudiante. Endpoint: `POST /api/v1/students/bulk-upload/` (multipart con el campo `archivo`), que **valida y crea** en lote dentro de una transacción (savepoint por fila) y devuelve un **resumen** `{creados, omitidos, errores:[{fila, motivo}]}`. Implementado con **openpyxl** (`apps/internados/services.registrar_estudiantes_masivo`).

### Estructura del archivo Excel (una hoja `estudiantes`)

Los catálogos se referencian por **`codigo`** (no por id), para que el archivo sea legible y estable. Columnas requeridas (R) / opcionales (O):

| Columna Excel | Req. | Mapea a | Formato / catálogo |
|---------------|------|---------|--------------------|
| `tipo_documento` | R | `tipo_documento_identidad.codigo` | `DNI` / `CE` / `PASAPORTE` |
| `numero_documento` | R | `numero_documento` | texto (único con `tipo_documento`) |
| `nombres` | R | `nombres` | texto |
| `apellido_paterno` | R | `apellido_paterno` | texto |
| `apellido_materno` | O | `apellido_materno` | texto |
| `fecha_nacimiento` | O | `fecha_nacimiento` | `YYYY-MM-DD` |
| `sexo` | O | `sexo` | `M` / `F` |
| `correo` | O | `correo` | email |
| `telefono` | O | `telefono` | texto |
| `direccion` | O | `direccion` | texto |
| `ubigeo` | O | `ubigeo.codigo` | 6 dígitos INEI |
| `universidad` | R | `universidad` (id o código INEI) | debe existir y estar en el ámbito del usuario |
| `carrera_profesional` | R | `carrera_profesional` | id / nombre de la carrera de la universidad |
| `codigo_universitario` | O | `codigo_universitario` | texto |
| `anio_academico` | O | `anio_academico` | entero |
| `nota_promedio_ponderado` | O | `nota_promedio_ponderado` | decimal 0–20 (usado en la prelación, RN-18) |
| `contacto_emergencia_nombre` | O | `contacto_emergencia_nombre` | texto |
| `contacto_emergencia_telefono` | O | `contacto_emergencia_telefono` | texto |
| `contacto_emergencia_parentesco` | O | `parentesco.codigo` | `PADRE` / `MADRE` / … |

**Validaciones de la carga:** por fila se valida unicidad (`tipo_documento` + `numero_documento`), existencia de catálogos/entidades referenciadas y alcance institucional de la `universidad`. Filas inválidas **no** detienen el lote: se reportan con número de fila y motivo. Se registra auditoría por cada creación (RNF-AUD-01/02) y se puede adjuntar el archivo origen como `documento`.

---

## 7. Adjuntos y auditoría

Se reutiliza la tabla `documento` (módulo 1, relación genérica vía `django_content_type`). En este módulo se adjunta a: `interno`, `rotacion`, `autorizacion_rotacion`.

La tabla `bitacora_auditoria` (módulo 1) registra cambios de tutor, sede, estado y rotación (RNF específico 5).

---

## 8. Mapa de relaciones

```
estudiante >── universidad / carrera_profesional / tipo_documento_identidad / parentesco (contacto_emergencia_parentesco_id)
tutor   >── especialidad / ipress / tipo_documento_identidad

interno >── estudiante
interno >── convenio (Convenio Específico, módulo 1)
interno >── campo_clinico (módulo 1)
interno >── ipress (sede principal)
interno >── tutor
interno >── ambito_geografico_sanitario
interno >── estado_internado (estado_actual)
interno ──< historial_estado_internado >── estado_internado
interno ──< historial_tutor >── tutor

interno ──< rotacion
rotacion >── ipress (origen) / ipress (destino) / servicio_area
rotacion >── estado_rotacion (estado_actual)
rotacion ──< historial_estado_rotacion >── estado_rotacion
rotacion ──< autorizacion_rotacion >── participante_convenio (módulo 1)

documento          >── django_content_type  (genérico → interno / rotacion / autorizacion_rotacion)
bitacora_auditoria >── django_content_type  (genérico)
```

---

## 9. Trazabilidad de requerimientos

- **RN-1..4 (estudiante sobre Convenio Específico vigente):** `interno.convenio_id` + validación de estado del convenio.
- **RN-5 (tutor obligatorio):** `interno.tutor_id` (no nulo).
- **RN-6 (máx. 1 año):** validación sobre `interno.fecha_inicio` / `fecha_fin`.
- **RN-8 (mismo ámbito sanitario):** validación entre `rotacion.ipress_origen_id`, `ipress_destino_id` y `interno.ambito_geografico_sanitario_id`.
- **RN-9 (máx. 4 rotaciones):** validación sobre `rotacion.numero_rotacion` por `interno`.
- **RN-10/11 (autorización por autoridad suscrita):** `autorizacion_rotacion.participante_convenio_id`; rotación no inicia sin registro `AUTORIZADO`.
- **RN-12 (fechas dentro del internado):** validación de fechas de `rotacion` contra `interno`.
- **RN-13 (no exceder campos clínicos):** validación contra `campo_clinico.cantidad_maxima` (módulo 1).
- **RN-14 (cambio de tutor):** `historial_tutor`.
- **RN-15 (trazabilidad de estados):** `historial_estado_internado`, `historial_estado_rotacion`, `bitacora_auditoria`.
- **RN-16 (registro individual y masivo):** `POST /students/` y `POST /students/bulk-upload/` (ver §6 bis).
- **RN-17 (asignación a campos clínicos por sede/carrera):** validación contra `campo_clinico` del Convenio Específico (disponibilidad = `cantidad_maxima` − asignados).
- **RN-18 (prelación por mérito):** ordenamiento por `estudiante.nota_promedio_ponderado` descendente al asignar cupos.
