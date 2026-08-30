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
| `django_content_type` | Relación genérica de `documento_adjunto`, `bitacora_auditoria` y de las relaciones de participación de convenios |
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
| `tipo_gestion_universidad` | Tipo de gestión | valores: `PUBLICA`, `PRIVADA` |
| `tipo_autorizacion` | Estado de autorización SUNEDU | valores: `LICENCIADA`, `DENEGADA`, `PENDIENTE` |
| `nivel_academico` | Nivel académico de la carrera | valores: `PREGRADO`, `SEGUNDA_ESPECIALIDAD`, `MAESTRIA`, `DOCTORADO` |
| `especialidad` | Especialidades de salud (seed: 46 especialidades médicas, nomenclatura oficial CONAREME) | — |
| `tipo_autoridad_firmante` | Tipo de autoridad firmante | — |
| `cargo_ejecutivo` | Cargos ejecutivos de representantes. **No** hereda de `Catalog`: FK `organo_id` → `organo`, unicidad `(organo_id, codigo)` | `organo_id` (FK → `organo`), `codigo`, `nombre`, `activo` |
| `motivo_observacion` | Motivos de observación | — |
| `motivo_rechazo` | Motivos de rechazo | — |
| `motivo_cierre` | Motivos de cierre o anulación | — |
| `categoria` | Categoría del establecimiento de salud (clasificación de IPRESS). Hereda de `Catalog` (`codigo` único global) | — |
| `tipo_clasificacion` | Tipo de clasificación del establecimiento de salud (clasificación de IPRESS). Hereda de `Catalog` (`codigo` único global) | — |

### Jerarquía geográfica sanitaria: `red` y `microred`

`red` y `microred` **no** son catálogos `Catalog` (su `codigo` no es único global sino por padre, vía `unique_together`). Cuelgan de `ambito_geografico_sanitario`: `ambito_geografico_sanitario → red → microred`.

#### `red`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `ambito_geografico_sanitario_id` | FK → `ambito_geografico_sanitario` (PROTECT) | No | Ámbito geográfico sanitario al que pertenece la red |
| `codigo` | varchar(50) | No | Código de la red (único dentro del ámbito) |
| `nombre` | varchar(255) | No | Nombre de la red |
| `activo` | bool | No | |

`unique_together = (ambito_geografico_sanitario, codigo)`.

#### `microred`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `red_id` | FK → `red` (PROTECT) | No | Red a la que pertenece la microred |
| `codigo` | varchar(50) | No | Código de la microred (único dentro de la red) |
| `nombre` | varchar(255) | No | Nombre de la microred |
| `activo` | bool | No | |

`unique_together = (red, codigo)`.

### `organo` — categorías de órgano (tabla normalizada)

Reemplaza el campo discriminador `VARCHAR` que tenía `tipo_organo.organo`. Contiene las cuatro categorías canónicas. Endpoint: `/api/v1/organs/` (CRUD, escritura solo `Administrador RENADS`).

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `nombre` | varchar(255) | No | Nombre del órgano |
| `estado` | bool | No | Indica si está activo (default `true`) |

Seed: 4 registros — `Órgano del MINSA`, `Universidad`, `Órgano Regional`, `Unidad Ejecutora`.

### `tipo_organo` — catálogo unificado de tipos de órgano

No hereda de `Catalog` (unicidad por `(organo_id, codigo)`, no global). Reemplaza las cuatro tablas `tipo_entidad_universidad`, `tipo_organo_regional`, `tipo_unidad_ejecutora` y `tipo_organo_minsa`.

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `organo_id` | FK → `organo` (PROTECT) | No | Categoría del órgano |
| `codigo` | varchar(50) | No | Código del tipo (único dentro de la categoría) |
| `nombre` | varchar(255) | No | Nombre |
| `activo` | bool | No | |

`unique_together = (organo_id, codigo)`. Seed: 14 registros canónicos.

Valores por categoría (filtrar con `?organo=<id>` en `/api/v1/organ-types/`):
- Órgano del MINSA: `DIGEP`, `OGAJ`, `SG`, `VICEPAS`
- Universidad: `UNIVERSIDAD`, `ESCUELA_POSGRADO`, `ESCUELA_SUPERIOR`, `INSTITUTO`
- Órgano Regional: `GERESA`, `DIRESA`, `DIRIS`
- Unidad Ejecutora: `HOSPITAL`, `INSTITUTO_ESPECIALIZADO`, `RED_SALUD`

---

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
| `referencia_logo` | varchar(500) | Sí | Logo institucional (`ImageField`; guarda el path del objeto en el repositorio de medios). Nullable. |
| `activo` | bool | No | |

### `organo_directorio` (directorio general de órganos: regionales y del MINSA)

Tabla **standalone** que unifica los antiguos `organo_regional` y `organo_minsa`, discriminada por `organo_id` (→ `organo`). Los órganos regionales llevan `gobierno_regional_id`; los del MINSA lo dejan nulo.

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `organo_id` | FK → `organo` (PROTECT) | No | Categoría del órgano (discriminador) |
| `tipo_organo_id` | FK → `tipo_organo` (PROTECT) | Sí | Tipo de órgano (GERESA/DIRESA/DIGEP…); nulo para órganos sin tipo |
| `gobierno_regional_id` | FK → `gobierno_regional` (PROTECT) | Sí | GORE (solo órganos regionales) |
| `nombre` | varchar(255) | No | Nombre del órgano |
| `siglas` | varchar(50) | Sí | Siglas |
| `direccion` | varchar(500) | Sí | Dirección |
| `numero_ruc` | varchar(11) | Sí | RUC (11 dígitos; texto para conservar ceros a la izquierda) |
| `correo` | email | Sí | Correo institucional |
| `telefono_institucional` | varchar(30) | Sí | Teléfono institucional |
| `ubigeo_id` | FK → `ubigeo` | Sí | Ubicación geográfica (UBIGEO) |
| `referencia_logo` | varchar(500) | Sí | Logo institucional (`ImageField`; guarda el path del objeto en el repositorio de medios). Nullable. |
| `activo` | bool | No | |

### `unidad_ejecutora`

Unidad ejecutora asociada a un **gobierno regional**.

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `codigo` | varchar(50) | Sí | Código presupuestal |
| `nombre` | varchar(255) | No | Nombre |
| `tipo_organo_id` | FK → `tipo_organo` (PROTECT) | No | Tipo de unidad ejecutora (Hospital / Instituto especializado / Red de salud; categoría `Unidad Ejecutora`) |
| `gobierno_regional_id` | FK → `gobierno_regional` (PROTECT) | No | Gobierno regional al que pertenece |
| `direccion` | varchar(500) | Sí | Dirección |
| `ubigeo_id` | FK → `ubigeo` | Sí | Ubicación geográfica (UBIGEO) |
| `referencia_logo` | varchar(500) | Sí | Logo institucional (`ImageField`; guarda el path del objeto en el repositorio de medios). Nullable. |
| `activo` | bool | No | |

`tipo_organo` filtra a la categoría `Unidad Ejecutora` (`limit_choices_to`).

Endpoint: `/api/v1/executing-units/` (CRUD con logo, escritura solo `Administrador RENADS`; filtros `tipo_organo`, `gobierno_regional`, `activo`; búsqueda `nombre`, `codigo`; lectura expone `tipo_organo_detalle`, `gobierno_regional_detalle` y `ubigeo_detalle`).

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
| `categoria_id` | FK → `categoria` (PROTECT) | Sí | Categoría del establecimiento |
| `tipo_clasificacion_id` | FK → `tipo_clasificacion` (PROTECT) | Sí | Tipo de clasificación del establecimiento |
| `microred_id` | FK → `microred` (PROTECT) | Sí | Microred a la que pertenece el establecimiento |
| `latitud` | decimal(9,6) | Sí | Latitud (coordenada geográfica) |
| `longitud` | decimal(9,6) | Sí | Longitud (coordenada geográfica) |
| `cantidad_camas` | int positivo | Sí | Número de camas del establecimiento |
| `numero_ruc` | varchar(11) | Sí | RUC (11 dígitos; texto para conservar ceros a la izquierda). Validación de formato: exactamente 11 dígitos numéricos si no es vacío. No `unique` en el MVP |
| `es_sede_docente` | bool | No | Autorizada por CONAPRES como sede docente (default `false`) |
| `referencia_logo` | varchar(500) | Sí | Logo institucional (`ImageField`; guarda el path del objeto en el repositorio de medios). Nullable. |
| `activo` | bool | No | |

> La **sede docente** del módulo de convenios es una `ipress`.
>
> **Autorización de sede docente (CONAPRES):** una `ipress` solo actúa como sede docente si **CONAPRES** la autoriza y registra tras verificar los criterios de evaluación: establecimiento **asistencial**, perteneciente al **MINSA** o a la **sanidad de las Fuerzas Armadas/Policiales**, y de gestión **pública**.

> Los órganos del MINSA (DIGEP / OGAJ / SG / VICEPAS) también viven en `organo_directorio` (con `gobierno_regional_id` nulo y `tipo_organo_id` opcional).

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

Los representantes de CONAPRES y de los demás órganos se registran en `organo_representante` (sección 6 bis), con FK directo a `organo_directorio`.

---

## 6. Entidades — Universidades

### `universidad`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `nombre` | varchar(255) | No | Nombre de la universidad |
| `siglas` | varchar(50) | Sí | Siglas |
| `numero_ruc` | varchar(11) | Sí | Número de RUC |
| `tipo_gestion_id` | FK → `tipo_gestion_universidad` | No | Pública / privada |
| `tipo_entidad_id` | FK → `tipo_organo` (PROTECT) | No | Universidad / Escuela posgrado / Escuela superior / Instituto (discriminador `UNIVERSIDAD`) |
| `tipo_autorizacion_id` | FK → `tipo_autorizacion` | No | Licenciada / Denegada / Pendiente |
| `codigo_inei` | varchar(20) | Sí | Código INEI |
| `fecha_constitucion` | date | Sí | Fecha de constitución |
| `fecha_autorizacion` | date | Sí | Fecha de autorización |
| `numero_resolucion` | varchar(100) | Sí | Número de resolución |
| `direccion_legal` | varchar(500) | Sí | Dirección legal |
| `telefono` | varchar(30) | Sí | Teléfono |
| `correo_institucional` | varchar(255) | Sí | Correo institucional |
| `ubigeo_id` | FK → `ubigeo` | Sí | Ubicación geográfica (UBIGEO) |
| `referencia_logo` | varchar(500) | Sí | Logo institucional (`ImageField`; guarda el path del objeto en el repositorio de medios). Nullable. |
| `activo` | bool | No | |

> Las autoridades de universidad se registran en `organo_representante` (sección 6 bis) contra un `organo_directorio` de la categoría `Universidad`; la tabla `autoridad_universidad` fue retirada.

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
| `nombre` | varchar(255) | No | Nombre de la carrera o programa |
| `nivel_academico_id` | FK → `nivel_academico` | No | Carrera profesional / segunda especialidad / maestría / doctorado |
| `activo` | bool | No | |

### `universidad_carrera`

Tabla puente universidad ↔ carrera profesional (carreras que dicta cada universidad). `unique_together = (universidad, carrera_profesional)`.

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `universidad_id` | FK → `universidad` (PROTECT) | No | Universidad |
| `carrera_profesional_id` | FK → `carrera_profesional` (PROTECT) | No | Carrera profesional |
| `activo` | bool | No | |

Endpoint: `/api/v1/university-careers/` (CRUD, escritura solo `Administrador RENADS`; filtros `universidad`, `carrera_profesional`, `activo`; lectura expone `universidad_detalle` y `carrera_profesional_detalle`).

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

## 6 bis. Representantes de órgano

Representantes/autoridades de un órgano del directorio (FK **directo** a `organo_directorio`, sin relación polimórfica). Cubre CONAPRES, órganos del MINSA, órganos regionales y universidades. Al designar un nuevo representante para el mismo `(organo_directorio, cargo_ejecutivo)` activo, el service `registrar_organo_representante` da de baja al anterior (`activo=False`) y lo copia a `historial_organo_representante`.

### `organo_representante`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `organo_directorio_id` | FK → `organo_directorio` (PROTECT) | No | Órgano del directorio representado |
| `nombre` | varchar(255) | No | Nombre del representante |
| `tipo_documento_identidad_id` | FK → `tipo_documento_identidad` (módulo 2, PROTECT) | No | Tipo de documento de identidad |
| `numero_documento_identidad` | varchar(20) | No | Número de documento de identidad |
| `sexo` | varchar(1) | No | `M` / `F` |
| `cargo_ejecutivo_id` | FK → `cargo_ejecutivo` (PROTECT) | No | Cargo ejecutivo |
| `fecha_inicio_designacion` | date | No | Inicio de la designación |
| `numero_resolucion_designacion` | varchar(100) | Sí | Número de resolución de designación |
| `fecha_inicio_facultades` | date | Sí | Otorgamiento de facultades |
| `activo` | bool | No | |

> El PDF de la resolución **no** es columna: se adjunta vía `annex-upload` (actor `REPRESENTANTE`) como `documento_adjunto`.

### `historial_organo_representante`

Snapshot denormalizado de un representante dado de baja (preserva el estado aunque cambie el maestro).

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `representante_id` | FK → `organo_representante` (PROTECT) | No | Representante dado de baja |
| `organo_directorio_id` | FK → `organo_directorio` (PROTECT) | No | Órgano del directorio representado |
| `nombre` | varchar(255) | No | Nombre del representante |
| `tipo_documento_identidad_id` | FK → `tipo_documento_identidad` (módulo 2) | No | Tipo de documento de identidad |
| `numero_documento_identidad` | varchar(20) | No | Número de documento de identidad |
| `sexo` | varchar(1) | No | `M` / `F` |
| `cargo_ejecutivo_id` | FK → `cargo_ejecutivo` (PROTECT) | No | Cargo ejecutivo |
| `fecha_inicio_designacion` | date | No | Inicio de la designación |
| `numero_resolucion_designacion` | varchar(100) | Sí | Número de resolución de designación |
| `fecha_inicio_facultades` | date | Sí | Otorgamiento de facultades |
| `fecha_baja` | date | No | Fecha en que se dio de baja al representante |
| `motivo` | varchar(255) | Sí | Motivo de la baja |
| `creado_en` | datetime | No | Fecha y hora de creación del histórico |

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

La entidad solicitante es polimórfica (universidad, órgano regional, etc.). Adicionalmente,
las dos partes concretas de la articulación docencia-servicio se modelan con FK explícitas:
`organo_directorio_id` (lado prestador) y `universidad_id` (lado académico). Los "tipos"
(tipo de órgano, tipo de entidad universitaria) **no se almacenan**: se derivan de la
entidad referenciada (`organo_directorio → tipo_organo`, `universidad → tipo_entidad`),
evitando redundancia. En el formulario son selectores en cascada que filtran la lista de entidades.

> **Reglas de solicitud (validación a nivel de aplicación):**
> - Solo **GERESA** o **DIRESA** pueden solicitar un **Convenio Marco** (`tipo_convenio = MARCO`).
> - Las **DIRIS** solicitan directamente **Convenio Específico** sin requerir Convenio Marco (`convenio_marco_id` nulo).
> - **Opinión jurídica (OGAJ):** solo para **Marco**. **Opinión favorable (CONAPRES):** solo para **Específico**.

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `tipo_convenio_id` | FK → `tipo_convenio` | No | Marco / Específico |
| `convenio_marco_id` | FK → `convenio` (self) | Sí | Convenio Marco vigente del que depende el Específico (RN-3). **Obligatorio** salvo cuando la solicitante es una **DIRIS** (no requiere Marco) |
| `plantilla_id` | FK → `plantilla_convenio` | Sí | Plantilla utilizada |
| `codigo` | varchar(50) | Sí | Código oficial |
| `titulo` | varchar(255) | No | Título / denominación |
| `solicitante_tipo_contenido_id` | FK → `django_content_type` | No | Tipo de entidad solicitante |
| `solicitante_id_objeto` | int | No | Identificador de la entidad solicitante |
| `organo_directorio_id` | FK → `organo_directorio` | No | Órgano del directorio (GERESA/DIRESA/DIRIS) parte del convenio. Su tipo se deriva de la entidad |
| `universidad_id` | FK → `universidad` | No | Universidad parte del convenio. Su tipo de entidad se deriva de la entidad |
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
| `organo_directorio_id` | FK → `organo_directorio` (SET_NULL) | Sí | Unidad evaluadora (DIGEP) del directorio |
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

### Campos clínicos (proceso 4.4 — solo Específico)

El registro de campos clínicos se modela en **dos tablas** que separan las dos
competencias del proceso:

1. **`campo_clinico_ipress`** — el **registro** que hace **CONAPRES** del **total** de campos
   clínicos por **sede docente (`ipress`) y carrera profesional** (tope de la sede/carrera).
2. **`campo_clinico_ipress_universidad`** — la **asignación** que hace el **Órgano Regional**
   (GERESA/DIRESA/DIRIS, grupo `Gobierno Regional`) de cupos **por universidad** contra un
   registro, sujeta a la disponibilidad del registro padre.

> **Reglas de asignación de campos clínicos:**
> - **CONAPRES** autoriza/registra el **total** de campos clínicos por **sede docente (`ipress`) y carrera profesional** en `campo_clinico_ipress.campos_clinicos_registrados` (tope de la sede/carrera). Escritura: rol **CONAPRES**.
> - El **Órgano Regional** (GERESA/DIRESA/DIRIS) asigna la **cantidad por universidad** en `campo_clinico_ipress_universidad.campos_clinicos_autorizados`, para universidades con Convenios Específicos aprobados en el **mismo ámbito geográfico sanitario**. Escritura: grupo **Gobierno Regional**.
> - **Disponibilidad:** `campos_clinicos_autorizados ≤ campos_clinicos_registrados − Σ autorizados de las demás asignaciones del mismo registro`. Además, la asignación exige convenio **Específico + vigente**, `convenio.universidad == asignacion.universidad`, e `ipress`/`carrera_profesional` coherentes con el registro padre.
> - **Acumulador:** `campo_clinico_ipress.campos_clinicos_asignados` es la suma (Σ) de los `campos_clinicos_autorizados` de sus asignaciones; el service lo **recalcula** tras crear/actualizar/eliminar una asignación. Es de **solo lectura** en la API (la disponibilidad expuesta = `registrados − asignados`).

#### `campo_clinico_ipress` (registro por sede + carrera — CONAPRES)

Reemplaza a la antigua tabla `campo_clinico`. `unique_together = (convenio, ipress, carrera_profesional, especialidad)`.

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `convenio_id` | FK → `convenio` (CASCADE) | No | Convenio Específico |
| `ipress_id` | FK → `ipress` (PROTECT) | No | Sede docente (establecimiento) autorizada por CONAPRES (`es_sede_docente = true`) |
| `carrera_profesional_id` | FK → `carrera_profesional` (PROTECT) | No | Carrera / programa académico |
| `especialidad_id` | FK → `especialidad` (SET_NULL) | Sí | Especialidad |
| `campos_clinicos_registrados` | int positivo | No | Total de campos clínicos registrados por CONAPRES para la sede y carrera (renombra `cantidad_maxima`) |
| `campos_clinicos_asignados` | int positivo | No (default `0`) | Acumulador Σ de los campos autorizados en las asignaciones por universidad; lo recalcula el service (**solo lectura** en la API) |
| `creado_en` | datetime | No | |
| `creado_por` | FK → `auth_user` (SET_NULL) | Sí | Usuario que creó el registro |
| `actualizado_en` | datetime | No | |
| `actualizado_por` | FK → `auth_user` (SET_NULL) | Sí | Usuario que actualizó el registro |

#### `campo_clinico_ipress_universidad` (asignación por universidad — Órgano Regional)

Tabla nueva. `unique_together = (campo_clinico_ipress, universidad, convenio)`. `related_name` del registro padre: `asignaciones`.

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `campo_clinico_ipress_id` | FK → `campo_clinico_ipress` (PROTECT) | No | Registro de campos clínicos (sede + carrera) del que descuenta la asignación |
| `convenio_id` | FK → `convenio` (PROTECT) | No | Convenio Específico vigente que respalda la asignación |
| `ipress_id` | FK → `ipress` (PROTECT) | No | Sede docente (coherente con el registro padre) |
| `carrera_profesional_id` | FK → `carrera_profesional` (PROTECT) | No | Carrera / programa académico (coherente con el registro padre) |
| `especialidad_id` | FK → `especialidad` (SET_NULL) | Sí | Especialidad |
| `universidad_id` | FK → `universidad` (PROTECT) | No | Universidad a la que se asignan los cupos |
| `fecha_inicio` | date | No | Inicio de vigencia de la asignación |
| `fecha_fin` | date | No | Fin de vigencia de la asignación |
| `campos_clinicos_autorizados` | int positivo | No | Cupos autorizados para la universidad (sujetos a la disponibilidad del registro padre) |
| `creado_en` | datetime | No | |
| `creado_por` | FK → `auth_user` (SET_NULL) | Sí | Usuario que creó la asignación |
| `actualizado_en` | datetime | No | |
| `actualizado_por` | FK → `auth_user` (SET_NULL) | Sí | Usuario que actualizó la asignación |

### `opinion_juridica` (OGAJ — proceso 4.5)

> **Regla:** la opinión jurídica de **OGAJ se solicita solo para Convenios Marco** (`convenio.tipo_convenio = MARCO`).

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

### `documento_adjunto`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `tipo_contenido_id` | FK → `django_content_type` | No | Tabla destino |
| `id_objeto` | int | No | Registro destino |
| `referencia_externa` | varchar(500) | No | Clave/URL del archivo en el repositorio externo |
| `version` | int | No | Versión |
| `estado` | varchar(20) | No | `ACTIVO` / `REEMPLAZADO` / `ANULADO` / `OBSERVADO` / `VALIDADO` |
| `version_anterior_id` | FK → `documento_adjunto` (self) | Sí | Versión previa reemplazada (RNF-DOC-04 / AUD-04) |
| `documento_anexo_id` | FK → `documento_anexo` (módulo 2, PROTECT) | **No** | Anexo/tipo al que corresponde el documento. **Único discriminador de versionado** (par `(objeto, documento_anexo)`) |
| `cargado_por` | FK → `auth_user` | No | Usuario que cargó |
| `cargado_en` | datetime | No | Fecha y hora de carga |

> Se retiraron las columnas `tipo_documento_id`, `nombre_archivo` y `texto_extraido`. El nombre de archivo se usa solo como ruta de storage al subir; no se persiste. El versionado se discrimina **siempre** por `documento_anexo`.

Se adjunta a: `convenio`, `evaluacion_tecnica`, `opinion_conapres`, `campo_clinico_ipress`, `campo_clinico_ipress_universidad`, `opinion_juridica`, `firma`, `publicacion`. **Anexos (declaraciones juradas por actor):** también se adjunta al `interno` (`INTERNO`) y al `organo_representante` (`REPRESENTANTE`, cubre autoridades de universidad y CONAPRES) con `documento_anexo_id` (ver módulo 2 y `docs/api_almacenamiento_frontend.md`).

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
ubigeo (distrito INEI) >──< organo_directorio / unidad_ejecutora / ipress / universidad / local_universidad   (también estudiante / tutor del módulo 2)
gobierno_regional ──< organo_directorio
gobierno_regional ──< unidad_ejecutora ──< ipress
gobierno_regional >── region
organo_directorio >── organo (discriminador) / tipo_organo (opcional) / gobierno_regional (opcional, solo regionales)
unidad_ejecutora >── gobierno_regional / tipo_organo (Unidad Ejecutora) / ubigeo
unidad_ejecutora >── gobierno_regional / ubigeo
ipress >── ambito_geografico_sanitario
ambito_geografico_sanitario ──< red ──< microred ──< ipress
ipress >── categoria / tipo_clasificacion / microred

conapres

organo_representante >── organo_directorio
organo_representante >── cargo_ejecutivo >── organo
organo_representante >── tipo_documento_identidad (módulo 2)
organo_representante ──< historial_organo_representante   (baja del anterior al designar uno nuevo)

universidad >── tipo_gestion_universidad / tipo_organo (discriminador UNIVERSIDAD) / tipo_autorizacion
universidad ──< facultad
universidad ──< universidad_carrera >── carrera_profesional   (carreras que dicta cada universidad)
carrera_profesional >── nivel_academico
universidad ──< local_universidad >── region

auth_user ──< perfil_usuario_entidad >── django_content_type (entidad polimórfica)
                       perfil_usuario_entidad >── auth_group

convenio >── tipo_convenio
convenio ──self< (Específico → Marco)            [convenio_marco_id]
convenio >── plantilla_convenio
convenio >── django_content_type (entidad solicitante, polimórfico)
convenio >── organo_directorio / universidad
convenio >── estado_convenio (estado_actual)
convenio ──< participante_convenio >── django_content_type (participante polimórfico)
convenio ──< historial_estado_convenio >── estado_convenio
convenio ──< evaluacion_tecnica >── organo_directorio
convenio ──< opinion_conapres                    (solo Específico)
convenio ──< campo_clinico_ipress >── ipress / carrera_profesional / especialidad   (registro CONAPRES, solo Específico)
campo_clinico_ipress ──< campo_clinico_ipress_universidad >── ipress / carrera_profesional / especialidad / universidad   (asignación Órgano Regional)
convenio ──< campo_clinico_ipress_universidad
convenio ──< opinion_juridica
convenio ──< firma >── django_content_type (firmante polimórfico)
convenio ──< publicacion

documento_adjunto  >── django_content_type   (genérico → cualquier tabla del flujo / anexos por actor)
documento_adjunto  >── documento_anexo        (módulo 2; obligatorio, único discriminador de versionado)
bitacora_auditoria >── django_content_type   (genérico → cualquier entidad)
```

---

## 13. Trazabilidad de requerimientos

- **RN-3 (Específico requiere Marco vigente):** `convenio.convenio_marco_id`. **Excepción DIRIS:** solicitan Específico sin Marco (`convenio_marco_id` nulo).
- **Solicitud de Convenio Marco (solo GERESA/DIRESA):** validación sobre la entidad solicitante (`organo_directorio → tipo_organo`, discriminador `ORGANO_REGIONAL`).
- **CONAPRES y campos clínicos solo en Específico:** tablas `opinion_conapres`, `campo_clinico_ipress` y `campo_clinico_ipress_universidad`; estados con `aplica_a = ESPECIFICO`.
- **Opinión jurídica (OGAJ) solo para Marco:** `opinion_juridica` se registra únicamente cuando `convenio.tipo_convenio = MARCO`.
- **Opinión favorable (CONAPRES) solo para Específico:** `opinion_conapres`.
- **Autorización de sede docente (CONAPRES):** `ipress` autorizada bajo criterios (asistencial, MINSA/FF.AA.-FF.PP., pública).
- **Campos clínicos (dos tablas):** el total por sede/carrera lo registra **CONAPRES** en `campo_clinico_ipress.campos_clinicos_registrados`; los cupos por universidad los asigna el **Órgano Regional** (GERESA/DIRESA/DIRIS) en `campo_clinico_ipress_universidad.campos_clinicos_autorizados`, sin exceder la disponibilidad del registro (`registrados − Σ autorizados`), en el mismo ámbito geográfico sanitario. El acumulador `campo_clinico_ipress.campos_clinicos_asignados` lo recalcula el service tras cada create/update/delete de asignación. Endpoints: `clinical-field-registrations` (CONAPRES) y `clinical-field-allocations` (Gobierno Regional).
- **Versionado documental (RNF-DOC-04 / AUD-04):** `documento_adjunto.version_anterior_id` + `estado`. El versionado se discrimina **siempre** por `documento_adjunto.documento_anexo_id` (par `(objeto, documento_anexo)`).
- **Adjuntos en repositorio externo:** columna `referencia_externa` (en `documento_adjunto`, `plantilla_convenio`). Las columnas `referencia_logo` (logos de `universidad`, `gobierno_regional`, `organo_directorio`, `unidad_ejecutora`, `ipress`) son **`ImageField`** de Django (Etapa 4): guardan el path relativo del objeto en el repositorio de medios (`STORAGES["default"]` = django-storages sobre GCS en prod, `FileSystemStorage` en dev); su `.url` es un signed URL V4 efímero. El **adjunto real** (logos e imágenes / PDFs de anexos) se sirve vía el backend de almacenamiento; ver `docs/api_almacenamiento_frontend.md`. El nombre de archivo se usa solo como ruta de storage al subir; no se persiste en `documento_adjunto`.
- **Trazabilidad de estados (RNF-AUD-03):** `historial_estado_convenio`.
- **Bitácora de auditoría (RNF-AUD-01/02):** `bitacora_auditoria`.
- **Roles y ámbito institucional (RNF-SEG-02/03):** `auth_group` + `perfil_usuario_entidad`.
- **Catálogos parametrizables (RNF-MAN-01):** sección 2.
