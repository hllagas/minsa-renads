# Esquema de Base de Datos — Módulo 1: Gestionar Convenios (RENADS)

Este documento define el modelo de datos del módulo **Gestionar Convenios** (Convenio Marco y Convenio Específico). Tablas, columnas y descripciones están en **español**.

> **Notas de diseño:**
> - Las entidades organizacionales se modelan en **tablas separadas** (sin tabla genérica), respetando la jerarquía real de cada sector.
> - Los **archivos adjuntos** (PDF, imágenes, logos) se almacenan en un **repositorio externo** a configurar posteriormente. En la BD solo se guarda una **referencia externa** (clave/URL), no el binario.
> - Se reutilizan tablas nativas de Django (`auth_user`, `auth_group`, `auth_permission`, `django_content_type`).
> - Toda PK es entero autoincremental salvo indicación. `creado_en` / `actualizado_en` son `datetime`.

---

## 1. Tablas nativas de Django reutilizadas

| Tabla nativa | Uso en RENADS |
|--------------|---------------|
| `auth_user` | Usuarios del sistema (`creado_por`, `cargado_por`, etc.) |
| `auth_group` | Roles |
| `auth_permission` | Permisos |
| `auth_user_groups`, `auth_group_permissions`, `auth_user_user_permissions` | Relaciones M2M nativas |
| `django_content_type` | Relación genérica de `documento`, `bitacora_auditoria` y de las relaciones de participación de convenios |
| `django_admin_log`, `django_session`, `django_migrations` | Infraestructura |

---

## 2. Catálogos

Tablas paramétricas (RNF-MAN-01). Patrón común: `id` (PK), `codigo` (varchar, único), `nombre` (varchar), `activo` (bool).

| Tabla | Descripción | Columnas adicionales |
|-------|-------------|----------------------|
| `ubigeo` | Ubicación geográfica del Perú a nivel distrito (INEI). Columnas propias: `codigo` (6 dígitos, único), `departamento`, `provincia`, `distrito`, `activo`. Carga vía comando `load_ubigeo` | — |
| `region` | Regiones políticas del Perú (seed: 25 regiones, códigos INEI) | — |
| `ambito_geografico_sanitario` | Ámbito geográfico sanitario (seed: 29 — autoridades sanitarias regionales DIRESA/GERESA + 4 DIRIS de Lima Metropolitana) | — |
| `tipo_convenio` | Tipo de convenio | `anios_vigencia` (int) — Marco=4, Específico=3 |
| `estado_convenio` | Estados del flujo (26) | `aplica_a` (`TODOS` \| `ESPECIFICO`), `orden` (int) |
| `tipo_documento` | Tipos de documento | — |
| `tipo_gestion_universidad` | Tipo de gestión | valores: `PUBLICA`, `PRIVADA` |
| `tipo_entidad_universidad` | Tipo de entidad educativa | valores: `UNIVERSIDAD`, `ESCUELA_POSGRADO`, `ESCUELA_SUPERIOR`, `INSTITUTO` |
| `tipo_autorizacion` | Estado de autorización SUNEDU | valores: `LICENCIADA`, `DENEGADA`, `PENDIENTE` |
| `nivel_academico` | Nivel académico de la carrera | valores: `CARRERA_PROFESIONAL`, `SEGUNDA_ESPECIALIDAD`, `MAESTRIA`, `DOCTORADO` |
| `especialidad` | Especialidades de salud (seed: 46 especialidades médicas, nomenclatura oficial CONAREME) | — |
| `tipo_autoridad_firmante` | Tipo de autoridad firmante | — |
| `tipo_organo_regional` | Tipo de órgano regional | valores: `GERESA`, `DIRESA`, `DIRIS` |
| `tipo_unidad_ejecutora` | Tipo de unidad ejecutora | valores: `HOSPITAL`, `INSTITUTO_ESPECIALIZADO`, `RED_SALUD` |
| `tipo_organo_minsa` | Órgano del MINSA | valores: `DIGEP`, `OGAJ`, `SG`, `VICEPAS` |
| `cargo_ejecutivo` | Cargos ejecutivos de representantes | — |
| `motivo_observacion` | Motivos de observación | — |
| `motivo_rechazo` | Motivos de rechazo | — |
| `motivo_cierre` | Motivos de cierre o anulación | — |

### Valores del catálogo `estado_convenio`

`aplica_a = ESPECIFICO` marca los exclusivos de Convenio Específico:

`SOLICITUD_REGISTRADA`, `PDF_PRELIMINAR_GENERADO`, `EN_EVALUACION_DIGEP`, `OBSERVADO_DIGEP`, `SUBSANADO`, `VALIDADO_TECNICAMENTE`, `PENDIENTE_CONAPRES` *(ESPECIFICO)*, `CONAPRES_FAVORABLE` *(ESPECIFICO)*, `CONAPRES_OBSERVADO` *(ESPECIFICO)*, `CAMPOS_CLINICOS_DEFINIDOS` *(ESPECIFICO)*, `PENDIENTE_OGAJ`, `OGAJ_FAVORABLE`, `OGAJ_OBSERVADO`, `ENVIADO_SG`, `ENVIADO_VICEPAS`, `FIRMADO_MINSA`, `ENVIADO_EXTERNOS`, `FIRMADO_EXTERNOS`, `SUSCRITO`, `PUBLICADO`, `VIGENTE`, `PROXIMO_A_VENCER`, `VENCIDO`, `AMPLIADO`, `CERRADO`, `ANULADO`.

---

## 3. Entidades — Gobiernos Regionales (GORE)

Jerarquía: **GORE → Órgano Regional (GERESA/DIRESA/DIRIS) → Unidad Ejecutora → IPRESS**.

### `gobierno_regional`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `nombre` | varchar(255) | No | Nombre del gobierno regional |
| `region_id` | FK → `region` | No | Región |
| `referencia_logo` | varchar(500) | Sí | Referencia externa del logo (repositorio externo) |
| `activo` | bool | No | |

### `organo_regional` (GERESA / DIRESA / DIRIS)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `gobierno_regional_id` | FK → `gobierno_regional` | No | GORE al que pertenece |
| `tipo_organo_regional_id` | FK → `tipo_organo_regional` | No | GERESA / DIRESA / DIRIS |
| `nombre` | varchar(255) | No | Nombre del órgano |
| `siglas` | varchar(50) | Sí | Siglas |
| `direccion` | varchar(500) | Sí | Dirección |
| `ubigeo_id` | FK → `ubigeo` | Sí | Ubicación geográfica (UBIGEO) |
| `referencia_logo` | varchar(500) | Sí | Referencia externa del logo (repositorio externo) |
| `activo` | bool | No | |

### `unidad_ejecutora` (Hospital / Instituto especializado / Red de salud)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `organo_regional_id` | FK → `organo_regional` | No | Órgano regional que la administra |
| `tipo_unidad_ejecutora_id` | FK → `tipo_unidad_ejecutora` | No | Hospital / Instituto / Red |
| `nombre` | varchar(255) | No | Nombre |
| `codigo` | varchar(50) | Sí | Código presupuestal de la unidad ejecutora |
| `direccion` | varchar(500) | Sí | Dirección |
| `ubigeo_id` | FK → `ubigeo` | Sí | Ubicación geográfica (UBIGEO) |
| `referencia_logo` | varchar(500) | Sí | Referencia externa del logo (repositorio externo) |
| `activo` | bool | No | |

### `ipress` (Institución Prestadora de Servicios de Salud)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `unidad_ejecutora_id` | FK → `unidad_ejecutora` | No | Unidad ejecutora a la que pertenece |
| `nombre` | varchar(255) | No | Nombre del establecimiento |
| `codigo_renipress` | varchar(20) | Sí | Código RENIPRESS |
| `direccion` | varchar(500) | Sí | Dirección |
| `ubigeo_id` | FK → `ubigeo` | Sí | Ubicación geográfica (UBIGEO) |
| `ambito_geografico_sanitario_id` | FK → `ambito_geografico_sanitario` | No | Ámbito geográfico sanitario |
| `activo` | bool | No | |

> La **sede docente** del módulo de convenios es una `ipress`.

---

## 4. Entidades — MINSA

### `organo_minsa` (DIGEP / OGAJ / SG / VICEPAS)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `tipo_organo_minsa_id` | FK → `tipo_organo_minsa` | No | DIGEP / OGAJ / SG / VICEPAS |
| `nombre` | varchar(255) | No | Nombre del órgano |
| `siglas` | varchar(50) | Sí | Siglas |
| `activo` | bool | No | |

---

## 5. Entidades — CONAPRES

Entidad independiente, máxima instancia del SINAPRES. Conformada por autoridades del MINSA, gobiernos regionales y asociaciones de facultades de profesiones de la salud.

### `conapres`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `nombre` | varchar(255) | No | Denominación |
| `descripcion` | text | Sí | Descripción |
| `activo` | bool | No | |

Los miembros de CONAPRES se registran en la tabla genérica `representante` (sección 6 bis), igual que los representantes de los órganos del MINSA y de las entidades regionales.

---

## 6. Entidades — Universidades

### `universidad`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `nombre` | varchar(255) | No | Nombre de la universidad |
| `siglas` | varchar(50) | Sí | Siglas |
| `tipo_gestion_id` | FK → `tipo_gestion_universidad` | No | Pública / privada |
| `tipo_entidad_id` | FK → `tipo_entidad_universidad` | No | Universidad / Escuela posgrado / Escuela superior / Instituto |
| `tipo_autorizacion_id` | FK → `tipo_autorizacion` | No | Licenciada / Denegada / Pendiente |
| `codigo_inei` | varchar(20) | Sí | Código INEI |
| `fecha_constitucion` | date | Sí | Fecha de constitución |
| `fecha_autorizacion` | date | Sí | Fecha de autorización |
| `numero_resolucion` | varchar(100) | Sí | Número de resolución |
| `direccion_legal` | varchar(500) | Sí | Dirección legal |
| `telefono` | varchar(30) | Sí | Teléfono |
| `correo_institucional` | varchar(255) | Sí | Correo institucional |
| `ubigeo_id` | FK → `ubigeo` | Sí | Ubicación geográfica (UBIGEO) |
| `referencia_logo` | varchar(500) | Sí | Referencia externa del logo (repositorio externo) |
| `activo` | bool | No | |

### `autoridad_universidad`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `universidad_id` | FK → `universidad` | No | Universidad |
| `nombre` | varchar(255) | No | Nombre de la autoridad |
| `cargo` | varchar(150) | No | Cargo |
| `fecha_inicio_cargo` | date | No | Inicio del cargo |
| `fecha_fin_cargo` | date | Sí | Fin del cargo |
| `numero_resolucion` | varchar(100) | Sí | Número de resolución de designación |
| `referencia_documento_resolucion` | varchar(500) | Sí | Referencia externa del PDF de la resolución |
| `activo` | bool | No | |

### `facultad`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `universidad_id` | FK → `universidad` | No | Universidad |
| `nombre` | varchar(255) | No | Nombre de la facultad |
| `activo` | bool | No | |

### `carrera_profesional`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `facultad_id` | FK → `facultad` | No | Facultad |
| `nombre` | varchar(255) | No | Nombre de la carrera o programa |
| `nivel_academico_id` | FK → `nivel_academico` | No | Carrera profesional / segunda especialidad / maestría / doctorado |
| `especialidad_id` | FK → `especialidad` | Sí | Especialidad asociada |
| `activo` | bool | No | |

### `local_universidad`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `universidad_id` | FK → `universidad` | No | Universidad |
| `nombre` | varchar(255) | No | Nombre del local |
| `direccion` | varchar(500) | Sí | Dirección |
| `region_id` | FK → `region` | Sí | Región |
| `ubigeo_id` | FK → `ubigeo` | Sí | Ubicación geográfica (UBIGEO) |
| `activo` | bool | No | |

---

## 6 bis. Representantes

Tabla genérica de representantes/autoridades de entidades. Aplica por **jerarquía** (relación polimórfica vía `django_content_type`) a: `organo_minsa`, `organo_regional`, `unidad_ejecutora`, `ipress` y `conapres`. Reemplaza a la antigua `miembro_conapres`.

### `representante`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `tipo_contenido_id` | FK → `django_content_type` | No | Tipo de entidad representada |
| `id_objeto` | int | No | Identificador de la entidad representada |
| `nombre` | varchar(255) | No | Nombre del representante |
| `cargo_ejecutivo_id` | FK → `cargo_ejecutivo` | No | Cargo (catálogo) |
| `origen` | varchar(30) | Sí | Solo para CONAPRES: `MINSA` / `GOBIERNO_REGIONAL` / `ASOCIACION_FACULTADES` |
| `fecha_inicio` | date | Sí | Inicio de participación / cargo |
| `fecha_fin` | date | Sí | Fin de participación / cargo |
| `activo` | bool | No | |

---

## 7. Seguridad y perfil institucional

Los roles son `auth_group` y los permisos `auth_permission`. Como la entidad del usuario puede ser heterogénea (órgano MINSA, órgano regional, universidad, CONAPRES), el vínculo usuario↔entidad es **polimórfico** vía `django_content_type` (RNF-SEG-02/03).

### `perfil_usuario_entidad`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `usuario_id` | FK → `auth_user` | No | Usuario |
| `tipo_contenido_id` | FK → `django_content_type` | No | Tipo de entidad asociada |
| `id_objeto` | int | No | Identificador de la entidad asociada |
| `grupo_id` | FK → `auth_group` | No | Rol institucional |
| `activo` | bool | No | |
| **Único** | (`usuario_id`, `tipo_contenido_id`, `id_objeto`, `grupo_id`) | | |

---

## 8. Núcleo de convenios

### `plantilla_convenio`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `tipo_convenio_id` | FK → `tipo_convenio` | No | Tipo al que aplica |
| `nombre` | varchar(255) | No | Nombre de la plantilla |
| `referencia_externa` | varchar(500) | No | Referencia externa del archivo de plantilla |
| `version` | int | No | Versión |
| `activo` | bool | No | |
| `creado_en` | datetime | No | |

### `convenio`

La entidad solicitante es polimórfica (universidad, órgano regional, etc.).

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `tipo_convenio_id` | FK → `tipo_convenio` | No | Marco / Específico |
| `convenio_marco_id` | FK → `convenio` (self) | Sí | Convenio Marco vigente del que depende el Específico (RN-3) |
| `plantilla_id` | FK → `plantilla_convenio` | Sí | Plantilla utilizada |
| `codigo` | varchar(50) | Sí | Código oficial |
| `titulo` | varchar(255) | No | Título / denominación |
| `solicitante_tipo_contenido_id` | FK → `django_content_type` | No | Tipo de entidad solicitante |
| `solicitante_id_objeto` | int | No | Identificador de la entidad solicitante |
| `estado_actual_id` | FK → `estado_convenio` | No | Estado actual |
| `fecha_solicitud` | date | No | Fecha de solicitud |
| `fecha_inicio` | date | Sí | Inicio de vigencia |
| `fecha_fin` | date | Sí | Fin de vigencia (4 años Marco / 3 años Específico) |
| `max_campos_clinicos` | int | Sí | Cantidad máxima de campos clínicos (solo Específico) |
| `creado_por` | FK → `auth_user` | No | Usuario que registró |
| `creado_en` | datetime | No | |
| `actualizado_en` | datetime | No | |

### `participante_convenio` (entidades participantes — polimórfico)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `convenio_id` | FK → `convenio` | No | |
| `tipo_contenido_id` | FK → `django_content_type` | No | Tipo de entidad participante |
| `id_objeto` | int | No | Identificador de la entidad participante |
| `tipo_autoridad_firmante_id` | FK → `tipo_autoridad_firmante` | Sí | Tipo de autoridad firmante |
| `es_firmante` | bool | No | Indica si firma el convenio |
| `creado_en` | datetime | No | |
| **Único** | (`convenio_id`, `tipo_contenido_id`, `id_objeto`) | | |

### `historial_estado_convenio` (trazabilidad — RNF-AUD-03)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `convenio_id` | FK → `convenio` | No | |
| `estado_id` | FK → `estado_convenio` | No | Estado registrado |
| `cambiado_por` | FK → `auth_user` | No | Responsable del cambio |
| `cambiado_en` | datetime | No | Fecha y hora |
| `observacion` | text | Sí | Observaciones |

---

## 9. Tablas del flujo

Cada actividad soporta documentos PDF mediante la tabla `documento` (sección 10).

### `evaluacion_tecnica` (DIGEP — proceso 4.2)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `convenio_id` | FK → `convenio` | No | |
| `resultado` | varchar(20) | No | `VALIDADO` / `OBSERVADO` / `RECHAZADO` |
| `observaciones` | text | Sí | Observaciones |
| `subsanacion` | text | Sí | Subsanación |
| `evaluado_por` | FK → `auth_user` | No | Responsable |
| `organo_minsa_id` | FK → `organo_minsa` | Sí | Unidad evaluadora (DIGEP) |
| `fecha_evaluacion` | date | No | |
| `creado_en` | datetime | No | |

### `opinion_conapres` (proceso 4.3 — solo Específico)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `convenio_id` | FK → `convenio` | No | |
| `fecha_solicitud` | date | No | Fecha de solicitud de opinión |
| `estado_atencion` | varchar(20) | No | Estado de atención |
| `resultado_opinion` | varchar(20) | Sí | `FAVORABLE` / `OBSERVADO` |
| `fecha_respuesta` | date | Sí | Fecha de respuesta |
| `creado_en` | datetime | No | |

### `campo_clinico` (proceso 4.4 — solo Específico)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `convenio_id` | FK → `convenio` | No | |
| `ipress_id` | FK → `ipress` | No | Sede docente (establecimiento de salud) |
| `carrera_profesional_id` | FK → `carrera_profesional` | No | Carrera / programa académico |
| `especialidad_id` | FK → `especialidad` | Sí | Especialidad |
| `cantidad_maxima` | int | No | Cantidad máxima de campos clínicos autorizados |
| `vigencia_inicio` | date | No | Inicio de vigencia |
| `vigencia_fin` | date | No | Fin de vigencia |
| `ambito_geografico_sanitario_id` | FK → `ambito_geografico_sanitario` | No | Ámbito |
| `observaciones` | text | Sí | Observaciones |
| `creado_en` | datetime | No | |

### `opinion_juridica` (OGAJ — proceso 4.5)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `convenio_id` | FK → `convenio` | No | |
| `fecha_envio` | date | No | Fecha de envío a OGAJ |
| `resultado_opinion` | varchar(20) | Sí | `FAVORABLE` / `OBSERVADO` |
| `observaciones_legales` | text | Sí | Observaciones legales |
| `subsanacion` | text | Sí | Subsanación |
| `fecha_respuesta` | date | Sí | Fecha de respuesta |
| `creado_en` | datetime | No | |

### `firma` (firma MINSA y entidades externas — procesos 4.6 y 4.7)

El firmante es polimórfico (órgano MINSA, universidad, órgano regional, etc.).

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `convenio_id` | FK → `convenio` | No | |
| `firmante_tipo_contenido_id` | FK → `django_content_type` | No | Tipo de entidad firmante |
| `firmante_id_objeto` | int | No | Identificador de la entidad firmante |
| `tipo_autoridad_firmante_id` | FK → `tipo_autoridad_firmante` | Sí | Tipo de autoridad firmante |
| `orden_firma` | int | Sí | Orden dentro del circuito de firmas |
| `fecha_envio` | date | Sí | Fecha de envío |
| `fecha_recepcion` | date | Sí | Fecha de recepción |
| `estado_firma` | varchar(20) | No | `PENDIENTE` / `FIRMADO` / `DEVUELTO` |
| `observaciones` | text | Sí | Observaciones o devoluciones |
| `creado_en` | datetime | No | |

### `publicacion` (proceso 4.8)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `convenio_id` | FK → `convenio` | No | |
| `fecha_publicacion` | date | No | Fecha de publicación |
| `referencia_publicacion` | varchar(255) | Sí | Enlace, código o constancia |
| `creado_por` | FK → `auth_user` | No | |
| `creado_en` | datetime | No | |

---

## 10. Documento (adjuntos en repositorio externo)

Tabla única para todo adjunto del expediente (RNF-DOC-01..05). El binario vive en un **repositorio externo**; aquí solo se guarda la **referencia externa**. Se vincula a cualquier tabla del flujo vía relación genérica de Django.

### `documento`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `tipo_documento_id` | FK → `tipo_documento` | No | Tipo de documento |
| `tipo_contenido_id` | FK → `django_content_type` | No | Tabla destino |
| `id_objeto` | int | No | Registro destino |
| `referencia_externa` | varchar(500) | No | Clave/URL del archivo en el repositorio externo |
| `nombre_archivo` | varchar(255) | No | Nombre del archivo |
| `version` | int | No | Versión |
| `estado` | varchar(20) | No | `ACTIVO` / `REEMPLAZADO` / `ANULADO` / `OBSERVADO` / `VALIDADO` |
| `version_anterior_id` | FK → `documento` (self) | Sí | Versión previa reemplazada (RNF-DOC-04 / AUD-04) |
| `cargado_por` | FK → `auth_user` | No | Usuario que cargó |
| `cargado_en` | datetime | No | Fecha y hora de carga |

Se adjunta a: `convenio`, `evaluacion_tecnica`, `opinion_conapres`, `campo_clinico`, `opinion_juridica`, `firma`, `publicacion`.

---

## 11. Auditoría

### `bitacora_auditoria` (RNF-AUD-01/02)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `usuario_id` | FK → `auth_user` | Sí | Usuario que ejecutó la acción |
| `accion` | varchar(30) | No | `CREAR` / `ACTUALIZAR` / `ELIMINAR` / `CAMBIO_ESTADO` / … |
| `tipo_contenido_id` | FK → `django_content_type` | No | Entidad afectada |
| `id_objeto` | int | No | Registro afectado |
| `nombre_campo` | varchar(100) | Sí | Campo modificado |
| `valor_anterior` | text | Sí | Valor anterior |
| `valor_nuevo` | text | Sí | Valor nuevo |
| `direccion_ip` | varchar(45) | Sí | IP de origen |
| `creado_en` | datetime | No | Fecha y hora |

---

## 12. Mapa de relaciones

```
ubigeo (distrito INEI) >──< organo_regional / unidad_ejecutora / ipress / universidad / local_universidad   (también interno / tutor del módulo 2)
gobierno_regional ──< organo_regional ──< unidad_ejecutora ──< ipress
gobierno_regional >── region
organo_regional >── tipo_organo_regional
unidad_ejecutora >── tipo_unidad_ejecutora
ipress >── ambito_geografico_sanitario

organo_minsa >── tipo_organo_minsa
conapres

representante >── django_content_type (entidad representada: organo_minsa / organo_regional / unidad_ejecutora / ipress / conapres)
representante >── cargo_ejecutivo

universidad >── tipo_gestion_universidad / tipo_entidad_universidad / tipo_autorizacion
universidad ──< autoridad_universidad
universidad ──< facultad ──< carrera_profesional >── nivel_academico / especialidad
universidad ──< local_universidad >── region

auth_user ──< perfil_usuario_entidad >── django_content_type (entidad polimórfica)
                       perfil_usuario_entidad >── auth_group

convenio >── tipo_convenio
convenio ──self< (Específico → Marco)            [convenio_marco_id]
convenio >── plantilla_convenio
convenio >── django_content_type (entidad solicitante, polimórfico)
convenio >── estado_convenio (estado_actual)
convenio ──< participante_convenio >── django_content_type (participante polimórfico)
convenio ──< historial_estado_convenio >── estado_convenio
convenio ──< evaluacion_tecnica >── organo_minsa
convenio ──< opinion_conapres                    (solo Específico)
convenio ──< campo_clinico >── ipress / carrera_profesional / especialidad / ambito_geografico_sanitario   (solo Específico)
convenio ──< opinion_juridica
convenio ──< firma >── django_content_type (firmante polimórfico)
convenio ──< publicacion

documento          >── django_content_type   (genérico → cualquier tabla del flujo)
bitacora_auditoria >── django_content_type   (genérico → cualquier entidad)
```

---

## 13. Trazabilidad de requerimientos

- **RN-3 (Específico requiere Marco vigente):** `convenio.convenio_marco_id`.
- **CONAPRES y campos clínicos solo en Específico:** tablas `opinion_conapres` y `campo_clinico`; estados con `aplica_a = ESPECIFICO`.
- **Versionado documental (RNF-DOC-04 / AUD-04):** `documento.version_anterior_id` + `estado`.
- **Adjuntos en repositorio externo:** columnas `referencia_externa` (en `documento`, `plantilla_convenio`, `universidad.referencia_logo`, `autoridad_universidad.referencia_documento_resolucion`).
- **Trazabilidad de estados (RNF-AUD-03):** `historial_estado_convenio`.
- **Bitácora de auditoría (RNF-AUD-01/02):** `bitacora_auditoria`.
- **Roles y ámbito institucional (RNF-SEG-02/03):** `auth_group` + `perfil_usuario_entidad`.
- **Catálogos parametrizables (RNF-MAN-01):** sección 2.
