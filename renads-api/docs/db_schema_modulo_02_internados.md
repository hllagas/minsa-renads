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
- Un **tutor** pertenece de **1 a 2 universidades** (tope de negocio) vía `tutor_universidad` (RN-24).
- **Registro de internos por la universidad con alcance institucional** (RN-20): el usuario de universidad solo registra/ve internos de las universidades dentro de su ámbito (`perfil_usuario_entidad` con entidad `universidad`; 1..N universidades). Superusuario y `Administrador RENADS` exentos.
- **Unicidad de interno por DNI** (RN-21): un estudiante no puede tener más de un internado **vigente**. Estados **bloqueantes**: `REGISTRADO`, `PENDIENTE_VALIDACION`, `OBSERVADO`, `VALIDADO`, `ACTIVO`, `EN_ROTACION_SOLICITADA`, `EN_ROTACION_AUTORIZADA`, `EN_ROTACION_OBSERVADA`. Estados **liberadores** (permiten un nuevo registro): `SUSPENDIDO`, `RETIRADO`, `CULMINADO`, `ANULADO`.
- **Onboarding del interno** (RN-22): al registrar el internado se crea (o reutiliza) un `User` con `username = numero_documento`, contraseña temporal, `debe_cambiar_password=True` (tabla `seguridad_usuario`), grupo `Interno` y `perfil_usuario_entidad` sobre su `estudiante`. Solo lee sus datos y adjunta sus declaraciones juradas; no edita datos personales ni ve otros internos. Se le **notifica por correo** (sede docente, fechas, tutor, instrucción de adjuntar DJ) — best-effort post-commit.
- **Estado de las declaraciones juradas** (RN-23): `interno.estado_declaraciones` (`PENDIENTE`/`COMPLETAS`/`OBSERVADAS`/`VALIDADAS`). `PENDIENTE→COMPLETAS` automático al completar las DJ obligatorias del actor `INTERNO`; revisión humana `COMPLETAS→VALIDADAS`/`OBSERVADAS`; `OBSERVADAS→COMPLETAS` al re-adjuntar. **Gate:** el internado no pasa a `ACTIVO` salvo `estado_declaraciones = VALIDADAS`.

> **Convenciones (heredadas del módulo 1):** tablas/columnas/descripciones en **español**; adjuntos en **repositorio externo** (solo `referencia_externa`); se reutilizan tablas nativas de Django y las tablas del **módulo 1** (`convenio`, `campo_clinico`, `ipress`, `universidad`, `carrera_profesional`, `especialidad`, `ambito_geografico_sanitario`, `participante_convenio`, `documento`, `bitacora_auditoria`).

---

## 1. Tablas reutilizadas

### Nativas de Django
`auth_user`, `auth_group`, `auth_permission`, `django_content_type` (relación genérica de `documento` y `bitacora_auditoria`).

### Transversal (app `common`)
| Tabla | Uso en el módulo 2 |
|-------|--------------------|
| `seguridad_usuario` | Extensión 1:1 de `auth_user`. Columna `debe_cambiar_password` (bool): fuerza el cambio de la contraseña temporal del interno (RN-22). Expuesta como claim del JWT y en `GET /api/v1/auth/me/`; se limpia en `POST /api/v1/auth/me/cambiar-password/`. |

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
| `periodo_academico` | Periodo académico (semestre) del estudiante — aplica al nivel Pregrado (RN-19) | — |
| `documentos_anexos` | Catálogo maestro de documentos requeridos **por actor** (declaraciones juradas, resolución del cargo, documento de identidad) a adjuntar tras el registro | `tipo_actor` (choices: `INTERNO` / `AUTORIDAD_UNIVERSIDAD` / `REPRESENTANTE`, default `INTERNO`), `descripcion` (text), `obligatorio` (bool, default `True`) |

### Valores de `estado_internado`
`REGISTRADO`, `PENDIENTE_VALIDACION`, `OBSERVADO`, `VALIDADO`, `ACTIVO`, `EN_ROTACION_SOLICITADA`, `EN_ROTACION_AUTORIZADA`, `EN_ROTACION_OBSERVADA`, `SUSPENDIDO`, `RETIRADO`, `CULMINADO`, `ANULADO`.

### Valores de `estado_rotacion`
`SOLICITADA`, `PENDIENTE_AUTORIZACION`, `OBSERVADA`, `AUTORIZADA`, `RECHAZADA`, `EN_CURSO`, `CULMINADA`, `CANCELADA`.

### Valores de `parentesco`
`PADRE`, `MADRE`, `HERMANO`, `CONYUGE`, `HIJO`, `ABUELO`, `TIO`, `OTRO`.

### Valores de `periodo_academico` (semilla)
`2025-I`, `2025-II`, `2026-I`, `2026-II` (nombre `Semestre <codigo>`).

### Valores de `documentos_anexos` (semilla)

**`tipo_actor = INTERNO`** (declaraciones juradas del estudiante): `DJ_DATOS` (Declaración jurada de veracidad de datos), `DJ_ANTECEDENTES` (Declaración jurada de no tener antecedentes penales/policiales), `DJ_SALUD` (Declaración jurada de aptitud de salud), `DJ_CONFIDENCIALIDAD` (Compromiso de confidencialidad).

**`tipo_actor = AUTORIDAD_UNIVERSIDAD`**: `RESOL_AUTUNI` (Resolución de designación del cargo), `DNI_AUTUNI` (Documento de identidad).

**`tipo_actor = REPRESENTANTE`** (incluye autoridades de CONAPRES): `RESOL_REP` (Resolución de designación del cargo), `DNI_REP` (Documento de identidad).

Todos con `obligatorio = True`.

### Adjunto real de anexos por actor (en alcance)

El **PDF real** de cada anexo de `documentos_anexos` se adjunta como un
`documento` (módulo 1) **versionado** por el par `(entidad, documento_anexo)`,
usando la FK `documento.documento_anexo_id`. El adjunto se hace por entidad según
el `tipo_actor`:

- `INTERNO` → `interno` (endpoints `interns/{id}/annex-upload/` y `.../annex-checklist/`).
- `AUTORIDAD_UNIVERSIDAD` → `autoridad_universidad`.
- `REPRESENTANTE` → `representante`.

Re-subir el mismo anexo a la misma entidad genera una nueva versión del
`documento`. Detalle de endpoints, content-types (PDF), tamaño y errores en
`docs/api_almacenamiento_frontend.md`.

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
| `periodo_academico_id` | FK → `periodo_academico` | Sí | Periodo académico (obligatorio para nivel `PREGRADO` — RN-19; PROTECT) |
| `especialidad_id` | FK → `especialidad` | Sí | Especialidad (obligatoria para niveles distintos de `PREGRADO` — RN-19; SET_NULL) |
| `codigo_universitario` | varchar(50) | Sí | Código universitario / matrícula |
| `nota_promedio_ponderado` | decimal(4,2) | Sí | Nota promedio ponderado (escala 0–20) |
| `activo` | bool | No | |
| `creado_por` | FK → `auth_user` | No | |
| `creado_en` | datetime | No | |
| **Único** | (`tipo_documento_identidad_id`, `numero_documento`) | | |

> **Contacto de emergencia:** el contacto de emergencia (`contacto_emergencia_nombre`, `contacto_emergencia_telefono`, `contacto_emergencia_parentesco_id`) se registra en la tabla **`interno`** (aplica al internado concreto), no en `estudiante`.

> **RN-19 (periodo académico vs. especialidad):** según el nivel académico de la carrera (`carrera_profesional.nivel_academico.codigo`), el estudiante lleva **uno u otro**: nivel `PREGRADO` ⇒ `periodo_academico_id` obligatorio y `especialidad_id` nulo; cualquier otro nivel (`SEGUNDA_ESPECIALIDAD`/`MAESTRIA`/`DOCTORADO`/…) ⇒ `especialidad_id` obligatorio y `periodo_academico_id` nulo. Ambas columnas son nullable en BD; la obligatoriedad condicional se valida a nivel de aplicación (`services.validar_regla_periodo_especialidad`).

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

> **RN-24:** un tutor pertenece **de 1 a 2 universidades** (tope de negocio, validado a nivel de aplicación). La relación N–N se materializa en la tabla puente `tutor_universidad`.

### `tutor_universidad` (puente tutor ↔ universidad — RN-24)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `tutor_id` | FK → `tutor` | No | Tutor (CASCADE) |
| `universidad_id` | FK → `universidad` | No | Universidad (PROTECT) |

Único por `(tutor_id, universidad_id)`. Cada tutor debe tener entre **1 y 2** filas (RN-24).

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
| `estado_declaraciones` | varchar(20) | No | Estado de las declaraciones juradas del interno (RN-23). Valores: `PENDIENTE` (default), `COMPLETAS`, `OBSERVADAS`, `VALIDADAS` |
| `contacto_emergencia_nombre` | varchar(255) | Sí | Nombre del contacto de emergencia |
| `contacto_emergencia_telefono` | varchar(30) | Sí | Teléfono del contacto de emergencia |
| `contacto_emergencia_parentesco_id` | FK → `parentesco` | Sí | Parentesco del contacto de emergencia (PROTECT) |
| `fecha_inicio` | date | No | Fecha de inicio |
| `fecha_fin` | date | No | Fecha de fin (máx. 1 año) |
| `observaciones` | text | Sí | Observaciones |
| `creado_por` | FK → `auth_user` | No | |
| `creado_en` | datetime | No | |
| `actualizado_en` | datetime | No | |

> **`estado_declaraciones` (RN-23):** independiente de `estado_actual`. `PENDIENTE→COMPLETAS` automático (todas las `documentos_anexos` de `tipo_actor=INTERNO` `obligatorio=True` tienen versión `ACTIVO` adjunta para el interno); revisión humana `COMPLETAS→VALIDADAS`/`OBSERVADAS` (rol `Universidad`/`Administrador RENADS`, acción `POST /api/v1/interns/{id}/revisar-declaraciones/`); `OBSERVADAS→COMPLETAS` al re-adjuntar. El internado no pasa a `ACTIVO` sin `estado_declaraciones = VALIDADAS`.

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

### Estructura del archivo Excel (trama oficial `TramaCargaEstudiante.xlsx`, hoja `carga`)

La estructura de referencia es la trama oficial **`TramaCargaEstudiante.xlsx`** (hoja `carga`): sus encabezados llevan el sufijo **`_id`** (`tipo_documento_identidad_id`, `universidad_id`, …). El valor de cada columna de catálogo/entidad puede ser un **id numérico** o su **código** (los resolvers aceptan ambos). Por retrocompatibilidad, la carga también acepta los encabezados históricos sin sufijo (mapeados vía `services.CARGA_ALIAS_COLUMNAS`). Columnas requeridas (R) / opcionales (O):

| Columna Excel (trama) | Alias histórico | Req. | Mapea a | Formato / valor aceptado |
|-----------------------|-----------------|------|---------|--------------------------|
| `tipo_documento_identidad_id` | `tipo_documento` | R | `tipo_documento_identidad` | `codigo` (`DNI`/`CE`/`PASAPORTE`) o id |
| `numero_documento` | — | R | `numero_documento` | texto (único con el tipo de documento) |
| `nombres` | — | R | `nombres` | texto |
| `apellido_paterno` | — | R | `apellido_paterno` | texto |
| `apellido_materno` | — | O | `apellido_materno` | texto |
| `fecha_nacimiento` | — | O | `fecha_nacimiento` | `YYYY-MM-DD` |
| `sexo` | — | O | `sexo` | `M` / `F` |
| `correo` | — | O | `correo` | email |
| `telefono` | — | O | `telefono` | texto |
| `direccion` | — | O | `direccion` | texto |
| `ubigeo_id` | `ubigeo` | O | `ubigeo` | 6 dígitos INEI (`codigo`) o id |
| `universidad_id` | `universidad` | R | `universidad` | id o código INEI; debe existir y estar en el ámbito del usuario |
| `carrera_profesional_id` | `carrera_profesional` | R | `carrera_profesional` | id o nombre de la carrera |
| `periodo_academico_id` | `periodo_academico` | O | `periodo_academico` | `codigo` (p. ej. `2025-01`) o id; requerido si el nivel es `PREGRADO` (RN-19) |
| `especialidad_id` | `especialidad` | O | `especialidad` | `codigo` o id; requerido si el nivel no es `PREGRADO` (RN-19) |
| `codigo_universitario` | — | O | `codigo_universitario` | texto |
| `nota_promedio_ponderado` | — | O | `nota_promedio_ponderado` | decimal 0–20 (usado en la prelación, RN-18) |

> El campo `anio_academico` fue **eliminado** de `estudiante` por redundante con `periodo_academico` (F6). Si la trama del Excel aún incluye la columna `anio_academico`, se **ignora silenciosamente**: no se lee ni se valida, y no rompe el lote.

> El **contacto de emergencia** ya no forma parte de la carga masiva de estudiantes: se registra en el **internado** (`interno`) al crear/actualizar el internado, no en el estudiante.

**Validaciones de la carga:** por fila se valida unicidad (`tipo_documento` + `numero_documento`), existencia de catálogos/entidades referenciadas, alcance institucional de la `universidad` y la regla **RN-19** (coherencia entre nivel académico, `periodo_academico` y `especialidad`). Filas inválidas **no** detienen el lote: se reportan con número de fila y motivo. Se registra auditoría por cada creación (RNF-AUD-01/02) y se puede adjuntar el archivo origen como `documento`.

---

## 7. Adjuntos y auditoría

Se reutiliza la tabla `documento` (módulo 1, relación genérica vía `django_content_type`). En este módulo se adjunta a: `interno`, `rotacion`, `autorizacion_rotacion`.

La tabla `bitacora_auditoria` (módulo 1) registra cambios de tutor, sede, estado y rotación (RNF específico 5).

---

## 8. Mapa de relaciones

```
estudiante >── universidad / carrera_profesional / tipo_documento_identidad
estudiante >── periodo_academico / especialidad   (uno u otro según nivel — RN-19)
tutor   >── especialidad / ipress / tipo_documento_identidad
tutor   ──< tutor_universidad >── universidad   (1 a 2 universidades — RN-24)

interno >── estudiante
interno >── convenio (Convenio Específico, módulo 1)
interno >── campo_clinico (módulo 1)
interno >── ipress (sede principal)
interno >── tutor
interno >── parentesco (contacto_emergencia_parentesco_id)
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
- **RN-19 (periodo académico vs. especialidad según nivel):** deriva `nivel = estudiante.carrera_profesional.nivel_academico.codigo`; `PREGRADO` ⇒ `periodo_academico_id` requerido / `especialidad_id` nulo; otro nivel ⇒ `especialidad_id` requerido / `periodo_academico_id` nulo. Regla única en `services.validar_regla_periodo_especialidad`, invocada por `StudentSerializer.validate` (individual) y por `registrar_estudiantes_masivo` (carga masiva).
- **RN-24 (universidades del tutor):** un tutor pertenece de **1 a 2** universidades vía `tutor_universidad`. Regla única en `services.validar_universidades_tutor`, invocada por `TutorSerializer` (create/update). El endpoint `tutors` acepta y filtra por `universidades`.

> **Nota — `documentos_anexos`:** catálogo maestro de documentos requeridos **por actor** (`tipo_actor`): `INTERNO` → declaraciones juradas del estudiante; `AUTORIDAD_UNIVERSIDAD` y `REPRESENTANTE` (incluye autoridades de CONAPRES) → resolución del cargo y documento de identidad. Filtrable por `tipo_actor` en el endpoint. Este spec cubre solo el catálogo maestro y su CRUD (`/api/v1/annex-documents/`). El flujo de adjunto real por entidad (tabla puente entidad↔anexo, carga del PDF, estados de presentación) queda fuera de alcance.
