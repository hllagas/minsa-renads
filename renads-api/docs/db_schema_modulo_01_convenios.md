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
| `ubigeo` | Ubicación geográfica del Perú a nivel distrito (INEI). **PK textual: `codigo` varchar(6), sin columna `id`**. Columnas: `codigo` (6 dígitos, PK), `departamento`, `provincia`, `distrito`, `activo`. Carga vía comando `load_ubigeo`. FK desde otras tablas: columna `ubigeo_id` varchar(6) | — |
| `region` | Regiones políticas del Perú (seed: 25 regiones, códigos INEI) | — |
| `ambito_geografico_sanitario` | Ámbito geográfico sanitario (seed: 29 — autoridades sanitarias regionales DIRESA/GERESA + 4 DIRIS de Lima Metropolitana). Ver sub-sección más abajo | `gobierno_regional_id` (FK nullable → `gobierno_regional`, PROTECT) |
| `tipo_convenio` | Tipo de convenio | `anios_vigencia` (int) — Marco=4, Específico=3 |
| `estado_convenio` | Estados del flujo (26) | `aplica_a` (`TODOS` \| `ESPECIFICO`), `orden` (int) |
| `tipo_gestion_universidad` | Tipo de gestión | valores: `PUBLICA`, `PRIVADA` |
| `tipo_autorizacion` | Estado de autorización SUNEDU | valores: `LICENCIADA`, `DENEGADA`, `PENDIENTE` |
| `nivel_academico` | Nivel académico de la carrera | valores: `PREGRADO`, `SEGUNDA_ESPECIALIDAD`, `MAESTRIA`, `DOCTORADO` |
| `especialidad` | Especialidades de salud (seed: 46 especialidades médicas, nomenclatura oficial CONAREME) | — |
| `tipo_autoridad_firmante` | Tipo de autoridad firmante | — |
| `cargo_ejecutivo` | Cargos ejecutivos de representantes. **No** hereda de `Catalog`: FK obligatorio `organo_id` → `organo` (categoría canónica) + FK `unidad_organica_id` → `unidad_organica` (1:N, nullable); coherencia `organo == unidad_organica.organo` cuando este está seteado; unicidad `(unidad_organica_id, nombre_masculino)` | `organo_id` (FK → `organo`, no null), `unidad_organica_id` (FK → `unidad_organica`, null), `nombre_masculino`, `nombre_femenino`, `activo` |
| `motivo_observacion` | Motivos de observación | — |
| `motivo_rechazo` | Motivos de rechazo | — |
| `motivo_cierre` | Motivos de cierre o anulación | — |
| `tipo_categoria` | Categoría del establecimiento de salud (clasificación de IPRESS). Hereda de `Catalog` (`codigo` único global). Tabla renombrada de `categoria` → `tipo_categoria` | — |
| `tipo_clasificacion` | Tipo de clasificación del establecimiento de salud (clasificación de IPRESS). Hereda de `Catalog` (`codigo` único global) | — |
| `tipo_entidad_universidad` | Tipo de entidad universitaria. Seed fijo: 4 tipos. | — |

### `tipo_entidad_universidad`

Catálogo fijo de tipos de entidad universitaria. Seed en migración `0052`.

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `nombre` | varchar(100) | No | Nombre del tipo (único) |
| `activo` | bool | No | |

Valores seed: `Universidad`, `Instituto`, `Escuela superior`, `Escuela de posgrado`.

Endpoint: `/api/v1/university-entity-types/` (solo lectura, `IsAuthenticated`; filtros `activo`; búsqueda `nombre`).

### Jerarquía geográfica sanitaria: `red` y `microred`

`red` y `microred` **no** son catálogos `Catalog` (su `codigo` no es único global sino por padre, vía `unique_together`). Cuelgan de `ambito_geografico_sanitario`: `ambito_geografico_sanitario → red → microred`.

**Mapeo RENIPRESS/SUSALUD y enlace por id surrogate.** La jerarquía se alimenta de RENIPRESS/SUSALUD: `codigo_DISA`/`DISA` → `ambito_geografico_sanitario.codigo`/`.nombre` (único global); `Codigo_Red` → `red.codigo` (único dentro del ámbito); `Codigo_Microred` → `microred.codigo` (único dentro de la red); y el código único de 8 dígitos de la IPRESS → `ipress.codigo_renipress`. Los FK jerárquicos se enlazan por **id surrogate** (`ambito_geografico_sanitario_id`, `red_id`, `microred_id`), **no** por el `codigo` varchar: los códigos de red/microred no son únicos a nivel nacional (se repiten entre DISAs, únicos solo dentro del padre vía `unique_together`). El loader resuelve `codigo → id` durante la carga.

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

#### `ambito_geografico_sanitario`

Hereda de `Catalog` (`codigo` único global, `nombre`, `activo`). Seed: 29 ámbitos — 25 regionales (DISA/GERESA/DIRESA, uno por GORE) + 4 DIRIS de Lima Metropolitana.

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `codigo` | varchar(50) | No | Código único del ámbito (equivalente al código DISA en RENIPRESS) |
| `nombre` | varchar(255) | No | Nombre del ámbito |
| `activo` | bool | No | |
| `gobierno_regional_id` | FK → `gobierno_regional` (PROTECT) | Sí | Gobierno regional al que corresponde el ámbito sanitario (nulo para los 4 DIRIS de Lima Metropolitana) |

Endpoint: `/api/v1/health-geographic-scopes/` (CRUD, escritura solo `Administrador RENADS`; filtros `activo`; búsqueda `codigo`, `nombre`; lectura expone `gobierno_regional_detalle` `{id, nombre}`).

### `organo` — categorías de órgano (tabla normalizada)

Reemplaza el campo discriminador `VARCHAR` que tenía el antiguo `tipo_organo.organo`. Contiene las cinco categorías canónicas. Endpoint: `/api/v1/organs/` (CRUD, escritura solo `Administrador RENADS`).

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `nombre` | varchar(255) | No | Nombre del órgano |
| `estado` | bool | No | Indica si está activo (default `true`) |

Seed: 5 registros — `Órgano del MINSA`, `Universidad`, `Gobierno Regional`, `MINSA DIRIS`, `Unidad Ejecutora`. Los nombres coinciden con los labels de `unidad_organica.categoria`. Nota: `cargo_ejecutivo` ya **no** referencia `organo` (categoría), sino `unidad_organica` (entidad concreta) vía `unidad_organica_id`; la coherencia del representante compara entidades (`cargo.unidad_organica == representante.unidad_organica`), no textos de categoría. La tabla `organo` se conserva solo como catálogo de las 5 categorías canónicas.

### `tipo_organo` — **RETIRADA**

La tabla `tipo_organo` (modelo `OrganType`) y su endpoint `/api/v1/organ-types/` fueron **retirados** (404). Sus filas se migraron a `unidad_organica` como filas con la `categoria` correspondiente (una fila de directorio por cada tipo de órgano). Las FKs que la referenciaban se reapuntaron a `unidad_organica`:
- `unidad_ejecutora.tipo_organo_id` → `unidad_organica` (categoría `UNIDAD_EJECUTORA`) — **posteriormente eliminada en migración 0045** (refactor de `unidad_ejecutora`).
- `universidad.tipo_entidad_id` → `tipo_entidad_universidad` (refactorizado en migración `0052`; antes apuntaba a `unidad_organica`).

El backfill de la `categoria` de las filas regionales derivó del antiguo `tipo_organo.codigo`: `GERESA`/`DIRESA` → `GOBIERNO_REGIONAL`, `DIRIS` → `MINSA_DIRIS`.

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
| `sigla` | varchar(50) | Sí | Sigla del gobierno regional |
| `ubigeo_id` | FK → `ubigeo` (PROTECT) — varchar(6) | Sí | Ubicación geográfica (UBIGEO) |
| `referencia_logo` | varchar(500) | Sí | Logo institucional (`ImageField`; guarda el path del objeto en el repositorio de medios). Nullable. |
| `activo` | bool | No | |

Endpoint: `/api/v1/regional-governments/` (CRUD con logo; filtros `region`, `ubigeo`, `activo`; búsqueda `nombre`; lectura expone `ubigeo_detalle`).

### `unidad_organica` (directorio unificado de unidades orgánicas/tipos institucionales)

Tabla **standalone** que cataloga órganos del MINSA, universidades, gobiernos regionales, DIRIS y unidades ejecutoras, discriminada por `categoria` (choices). Reemplaza al antiguo par `organo_id`/`tipo_organo_id` (retirados). El GORE ya no vive aquí: se trasladó a `convenio.gobierno_regional_id`.

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `categoria` | varchar(20) (choices) | No | Categoría del órgano (discriminador): `ORGANO_MINSA` / `UNIVERSIDAD` / `GOBIERNO_REGIONAL` / `MINSA_DIRIS` / `UNIDAD_EJECUTORA` |
| `nombre` | varchar(255) | No | Nombre del órgano |
| `siglas` | varchar(50) | Sí | Siglas |
| `activo` | bool | No | |

Unicidad: única por `(organo, nombre)` (constraint `uniq_organo_dir_organo_nombre`).

Endpoint: `/api/v1/organic-units/` (CRUD, escritura solo `Administrador RENADS`; filtros `categoria`, `activo`; búsqueda `nombre`, `siglas`; **sin logo**). Cada `unidad_organica` es un **órgano directivo** que agrupa 1..N `cargo_ejecutivo` (relación 1:N vía `cargo_ejecutivo.unidad_organica_id`).

### `cargo_ejecutivo` (cargos de un órgano directivo)

Cargos ejecutivos de un **órgano directivo** concreto (`unidad_organica`). Relación 1:N: un órgano directivo tiene varios cargos (p. ej. *Dirección General de Personal de la Salud* → "Director(a) General de Personal de la Salud", "Director(a) Adjunto(a)…"). La persona que ocupa el cargo la aporta `organo_representante` (cambiante, con histórico); el cargo y su órgano se mantienen estables.

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `organo_id` | FK → `organo` (PROTECT, `related_name='cargos_ejecutivos'`) | No | Categoría de órgano a la que pertenece el cargo; debe coincidir con `unidad_organica.organo` cuando este está seteado |
| `unidad_organica_id` | FK → `unidad_organica` (PROTECT, `related_name='cargos'`) | Sí | Órgano directivo al que pertenece el cargo (nullable en BD y API; filas seed legacy quedan sin asignar) |
| `nombre_masculino` | varchar(255) | No | Nombre del cargo en masculino |
| `nombre_femenino` | varchar(255) | Sí | Nombre del cargo en femenino |
| `activo` | bool | No | |

`unique_together = (unidad_organica, nombre_masculino)` (el `organo` no se incluye por derivarse del `unidad_organica`). **Coherencia (RN-CE-02):** cuando `unidad_organica` está seteado, `organo` debe coincidir con `unidad_organica.organo` — validado en el serializer del viewset (`_ExecutivePositionSerializer.validate`, soporta PATCH parcial); si `unidad_organica` es nulo (cargo global), la coherencia no aplica y solo se exige el `organo` obligatorio. Endpoint: `/api/v1/executive-positions/` (CRUD, escritura solo `Administrador RENADS`; filtros `organo`, `unidad_organica` (con `isnull`), `activo`; búsqueda `nombre_masculino`, `nombre_femenino`; lectura expone `organo_detalle` (id/codigo/nombre) y `unidad_organica_detalle` con id/nombre/organo).

### `unidad_ejecutora`

Unidad ejecutora vinculada directamente a un **ámbito geográfico sanitario** (tras refactor Migración 0045).

> **Columnas eliminadas respecto a la versión anterior:** `id` (AutoField), `tipo_organo_id`, `gobierno_regional_id`, `direccion`, `ubigeo_id`, `referencia_logo`.

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `codigo` | varchar(4) **PK** | No | Código presupuestal de 4 dígitos (PK textual) |
| `nombre` | varchar(255) | No | Nombre de la unidad ejecutora |
| `ambito_geografico_sanitario_id` | FK → `ambito_geografico_sanitario` (PROTECT) | No | Ámbito geográfico sanitario al que pertenece |
| `activo` | bool | No | |

> **Nota sobre `ipress.unidad_ejecutora_id` y `convenio.unidad_ejecutora_id`:** estas columnas mantienen el nombre de columna `unidad_ejecutora_id` en la BD, pero desde la migración 0045 almacenan un **varchar(4)** (el código presupuestal) en lugar del int AutoField anterior.

Endpoint: `/api/v1/executing-units/` (CRUD, escritura solo `Administrador RENADS`; filtros `ambito_geografico_sanitario`, `activo`; búsqueda `nombre`, `codigo`; lectura expone `ambito_geografico_sanitario_detalle` `{id, nombre}`). La PK en la URL es el código de 4 chars (p. ej. `/api/v1/executing-units/0032/`). Los filtros antiguos `tipo_organo` y `gobierno_regional` **no existen** en este endpoint (400 si se envían). El endpoint **no ofrece** `upload-logo` ni `logo-url`.

### `ipress` (Institución Prestadora de Servicios de Salud)

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `codigo_renipress` | **PK** varchar(8) | No | Código RENIPRESS de 8 caracteres — **clave primaria** de la tabla (no hay columna `id`; el valor lo provee el cliente al crear) |
| `unidad_ejecutora_id` | FK → `unidad_ejecutora` (PROTECT) — varchar(4) | No | Unidad ejecutora a la que pertenece (el valor almacenado es el código presupuestal de 4 chars, no un int) |
| `nombre` | varchar(255) | No | Nombre del establecimiento |
| `direccion` | varchar(500) | Sí | Dirección |
| `ubigeo_id` | FK → `ubigeo` (PROTECT) — varchar(6) | Sí | Ubicación geográfica (UBIGEO) |
| `ambito_geografico_sanitario_id` | FK → `ambito_geografico_sanitario` | No | Ámbito geográfico sanitario |
| `categoria_id` | FK → `tipo_categoria` (PROTECT) | Sí | Categoría del establecimiento |
| `tipo_clasificacion_id` | FK → `tipo_clasificacion` (PROTECT) | Sí | Tipo de clasificación del establecimiento |
| `microred_id` | FK → `microred` (PROTECT) | Sí | Microred a la que pertenece el establecimiento |
| `latitud` | decimal(9,6) | Sí | Latitud (coordenada geográfica) |
| `longitud` | decimal(9,6) | Sí | Longitud (coordenada geográfica) |
| `cantidad_camas` | int positivo | Sí | Número de camas del establecimiento |
| `numero_ruc` | varchar(11) | Sí | RUC (11 dígitos; texto para conservar ceros a la izquierda). Validación de formato: exactamente 11 dígitos numéricos si no es vacío. No `unique` en el MVP |
| `es_sede_docente` | bool | No | Autorizada por CONAPRES como sede docente (default `false`) |
| `referencia_logo` | varchar(500) | Sí | Logo institucional (`ImageField`; guarda el path del objeto en el repositorio de medios). Nullable. |
| `activo` | bool | No | |

> **Coherencia `microred ↔ ámbito` (denormalización deliberada):** si `microred_id` no es nulo, `microred.red.ambito_geografico_sanitario` debe coincidir con `ipress.ambito_geografico_sanitario` (el ámbito directo es la fuente autoritativa; RN-25 deriva de `ipress.ambito_geografico_sanitario_id`). Validado en `Ipress.clean()` y en el `validate()` del serializer del `IpressViewSet` (create y PATCH parcial). Si `microred_id` es nulo, no se valida.
>
> La **sede docente** del módulo de convenios es una `ipress`.
>
> **Autorización de sede docente (CONAPRES):** una `ipress` solo actúa como sede docente si **CONAPRES** la autoriza y registra tras verificar los criterios de evaluación: establecimiento **asistencial**, perteneciente al **MINSA** o a la **sanidad de las Fuerzas Armadas/Policiales**, y de gestión **pública**.

> Los órganos del MINSA (DIGEP / OGAJ / SG / VICEPAS) también viven en `unidad_organica` (categoría `ORGANO_MINSA`).

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

Los representantes de CONAPRES y de los demás órganos se registran en `organo_representante` (sección 6 bis), con FK directo a `unidad_organica`.

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
| `tipo_entidad_id` | FK → `tipo_entidad_universidad` (PROTECT) | No | Tipo de entidad universitaria |
| `tipo_autorizacion_id` | FK → `tipo_autorizacion` | No | Licenciada / Denegada / Pendiente |
| `codigo_inei` | varchar(20) | Sí | Código INEI |
| `fecha_constitucion` | date | Sí | Fecha de constitución |
| `fecha_autorizacion` | date | Sí | Fecha de autorización |
| `numero_resolucion` | varchar(100) | Sí | Número de resolución |
| `direccion_legal` | varchar(500) | Sí | Dirección legal |
| `telefono` | varchar(30) | Sí | Teléfono |
| `correo_institucional` | varchar(255) | Sí | Correo institucional |
| `ubigeo_id` | FK → `ubigeo` (PROTECT) — varchar(6) | Sí | Ubicación geográfica (UBIGEO) |
| `referencia_logo` | varchar(500) | Sí | Logo institucional (`ImageField`; guarda el path del objeto en el repositorio de medios). Nullable. |
| `activo` | bool | No | |

> Las autoridades de universidad se registran en `organo_representante` (sección 6 bis) contra un `unidad_organica` de la categoría `UNIVERSIDAD`; la tabla `autoridad_universidad` fue retirada.

### `facultad`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `universidad_id` | FK → `universidad` | No | Universidad |
| `nombre` | varchar(255) | No | Nombre de la facultad |
| `direccion` | varchar(255) | No | Dirección de la facultad (`blank`, cadena vacía por defecto) |
| `ubigeo_id` | FK → `ubigeo` (PROTECT) — varchar(6) | Sí | Ubicación geográfica (UBIGEO) |
| `referencia_logo` | varchar(500) | Sí | Logo institucional (`ImageField`; guarda el path del objeto en el repositorio de medios). Nullable. |
| `activo` | bool | No | |

Endpoint: `/api/v1/faculties/` (CRUD con logo, escritura solo `Administrador RENADS`; filtros `universidad`, `ubigeo`, `activo`; búsqueda `nombre`, `direccion`; lectura expone `ubigeo_detalle` y `referencia_logo` como URL). Acciones `faculties/{id}/upload-logo` y `faculties/{id}/logo-url`.

### `carrera_profesional`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `nombre` | varchar(255) | No | Nombre de la carrera o programa |
| `nivel_academico_id` | FK → `nivel_academico` | No | Carrera profesional / segunda especialidad / maestría / doctorado |
| `orden` | `int` | No | Orden de visualización en el listado (default 0, menor primero) |
| `activo` | bool | No | |

### `universidad_carrera`

Tabla puente universidad ↔ carrera profesional (carreras que dicta cada universidad), asociada a la facultad que la imparte. `unique_together = (universidad, carrera_profesional)` (la unicidad NO incluye `facultad`). Regla de coherencia (RN-FC-02): `facultad.universidad_id == universidad_id`.

**RN-FC-04 (carrera única por universidad):** una carrera profesional pertenece a **una sola facultad** dentro de la misma universidad. La `unique_together` garantiza una única fila `(universidad, carrera_profesional)`; una vez asignada y **activa** en una facultad, la carrera **no puede ser elegida por otra facultad** de esa universidad (la UI la muestra como no disponible). Si la carrera se da de baja (`activo=False`) de su facultad, queda libre y otra facultad puede tomarla.

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `universidad_id` | FK → `universidad` (PROTECT) | No | Universidad |
| `carrera_profesional_id` | FK → `carrera_profesional` (PROTECT) | No | Carrera profesional |
| `facultad_id` | FK → `facultad` (PROTECT) | No | Facultad de la universidad que imparte la carrera (obligatoria en BD y API desde `0032`) |
| `activo` | bool | No | |

Endpoint: `/api/v1/university-careers/` (CRUD, escritura solo `Administrador RENADS`; filtros `universidad`, `carrera_profesional`, `facultad`, `activo`; lectura expone `universidad_detalle`, `carrera_profesional_detalle` y `facultad_detalle`). La creación de una carrera ya asignada a otra facultad de la misma universidad se rechaza con 400 (RN-FC-04, `UniqueTogetherValidator`).

Endpoint en lote: `POST /api/v1/faculties/{id}/careers` (body `{carreras: [ids]}`) — sincronización idempotente (alta/reactivación + baja por `activo`) de las carreras **por facultad**; deriva `universidad` de la facultad; escritura solo `Administrador RENADS`; delega en `services.sincronizar_carreras_facultad`. Intentar asignar una carrera **activa** en otra facultad de la universidad devuelve 400 (RN-FC-04); si estaba libre (dada de baja), esta facultad la toma.

### `local_universidad`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `universidad_id` | FK → `universidad` | No | Universidad |
| `nombre` | varchar(255) | No | Nombre del local |
| `direccion` | varchar(500) | Sí | Dirección |
| `region_id` | FK → `region` | Sí | Región |
| `ubigeo_id` | FK → `ubigeo` (PROTECT) — varchar(6) | Sí | Ubicación geográfica (UBIGEO) |
| `activo` | bool | No | |

---

## 6 bis. Representantes de órgano

Representantes/autoridades de una unidad orgánica (FK **directo** a `unidad_organica`, sin relación polimórfica). Cubre CONAPRES, órganos del MINSA, órganos regionales y universidades. Al designar un nuevo representante para el mismo `(unidad_organica, cargo_ejecutivo)` activo, el service `registrar_organo_representante` da de baja al anterior (`activo=False`) y lo copia a `historial_organo_representante`. **Coherencia cargo↔órgano** (en `OrganRepresentativeSerializer`): si el cargo tiene `unidad_organica` asignado, debe coincidir con el `unidad_organica` del representante (`cargo.unidad_organica_id == unidad_organica_id`); los cargos legacy sin `unidad_organica` no se validan.

### `organo_representante`

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `unidad_organica_id` | FK → `unidad_organica` (PROTECT) | No | Unidad orgánica representada |
| `nombre` | varchar(255) | No | Nombre del representante |
| `tipo_documento_identidad_id` | FK → `tipo_documento_identidad` (módulo 2, PROTECT) | No | Tipo de documento de identidad |
| `numero_documento_identidad` | varchar(20) | No | Número de documento de identidad |
| `sexo` | varchar(1) | No | `M` / `F` |
| `cargo_ejecutivo_id` | FK → `cargo_ejecutivo` (PROTECT) | No | Cargo ejecutivo |
| `fecha_inicio_designacion` | date | No | Inicio de la designación |
| `numero_resolucion_designacion` | varchar(100) | Sí | Número de resolución de designación |
| `numero_resolucion_facultades` | varchar(100) | Sí | Número de resolución que otorga facultades al representante |
| `fecha_inicio_facultades` | date | Sí | Otorgamiento de facultades |
| `activo` | bool | No | |

> El PDF de la resolución **no** es columna: se adjunta vía `annex-upload` (actor `REPRESENTANTE`) como `documento_adjunto`.

### `historial_organo_representante`

Snapshot denormalizado de un representante dado de baja (preserva el estado aunque cambie el maestro).

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `representante_id` | FK → `organo_representante` (PROTECT) | No | Representante dado de baja |
| `unidad_organica_id` | FK → `unidad_organica` (PROTECT) | No | Unidad orgánica representada |
| `nombre` | varchar(255) | No | Nombre del representante |
| `tipo_documento_identidad_id` | FK → `tipo_documento_identidad` (módulo 2) | No | Tipo de documento de identidad |
| `numero_documento_identidad` | varchar(20) | No | Número de documento de identidad |
| `sexo` | varchar(1) | No | `M` / `F` |
| `cargo_ejecutivo_id` | FK → `cargo_ejecutivo` (PROTECT) | No | Cargo ejecutivo |
| `fecha_inicio_designacion` | date | No | Inicio de la designación |
| `numero_resolucion_designacion` | varchar(100) | Sí | Número de resolución de designación |
| `numero_resolucion_facultades` | varchar(100) | Sí | Número de resolución que otorga facultades al representante |
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
| `id_objeto` | varchar(64) | No | Identificador de la entidad asociada. Texto: para IPRESS es el código RENIPRESS (PK textual); para el resto de entidades es el pk entero casteado a `str`. Las comparaciones de alcance se normalizan a `str` |
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
`unidad_organica_id` (lado prestador) y `universidad_id` (lado académico). Los "tipos"
(categoría del órgano, tipo de entidad universitaria) **no se almacenan**: se derivan de la
entidad referenciada (`unidad_organica.categoria`, `universidad → tipo_entidad`),
evitando redundancia. En el formulario son selectores en cascada que filtran la lista de entidades.

> **Reglas de solicitud (validación a nivel de aplicación):**
> - Solo **GERESA** o **DIRESA** pueden solicitar un **Convenio Marco** (`tipo_convenio = MARCO`).
> - Las **DIRIS** solicitan directamente **Convenio Específico** sin requerir Convenio Marco (`convenio_marco_id` nulo).
> - **Opinión jurídica (OGAJ):** solo para **Marco**. **Opinión favorable (CONAPRES):** solo para **Específico**.

> **Partes por tipo (`unidad_ejecutora_id` / `facultad_id`):**
> - **Marco:** ambos **nulos** (un Marco no lleva unidad ejecutora ni facultad).
> - **Específico:** ambos **obligatorios**. La `facultad` debe pertenecer a la
>   universidad del Convenio Marco (`facultad.universidad_id == convenio_marco.universidad_id`);
>   para DIRIS sin Marco, a la universidad propia del Específico (`convenio.universidad_id`).
>   Regla en `services._validar_partes_por_tipo` (aplicada en `crear_convenio` y
>   `actualizar_convenio`, revalidando el estado final del objeto en PATCH parcial).

> **Adendas de ampliación (`convenio_origen_id` / `es_adenda`):** una adenda es una fila
> `convenio` encadenada por `convenio_origen_id` (self-FK, `related_name='adendas'`) a un
> Marco o Específico, con nuevo periodo de vigencia. **Sin límite de encadenamiento**
> (adendas de adendas). Hereda del origen: tipo, marco, universidad, unidad orgánica,
> unidad ejecutora, facultad y solicitante polimórfico. Se crea vía `services.crear_adenda`
> (acción `POST /api/v1/conventions/{id}/adenda`) en estado `SOLICITUD_REGISTRADA`.
> Al pasar una adenda a `VIGENTE`, su `convenio_origen` se marca `AMPLIADO` (salvo que ya
> esté `CERRADO`/`ANULADO`/`AMPLIADO`). La **vigencia efectiva** de un convenio
> (`selectors.vigencia_efectiva`) es la mayor `fecha_fin` de las adendas vigentes de su
> cadena, o su propia `fecha_fin` si no hay adenda vigente.

> **Requisito de campos clínicos antes de suscripción:** un Convenio **Específico** no puede
> avanzar a suscripción (transición a `ENVIADO_SG` o registro de firma) sin ≥1
> `campo_clinico_ipress` con `numero_resolucion_conapres` no vacío sobre una sede docente
> (`ipress.es_sede_docente = true`) cuya `ipress.unidad_ejecutora_id` coincida con la
> unidad ejecutora del convenio. La FK directa a `convenio` fue eliminada en migración 0051;
> el vínculo se deriva por `ipress.unidad_ejecutora_id`. Regla en `services._exigir_campos_clinicos_conapres`.

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `tipo_convenio_id` | FK → `tipo_convenio` | No | Marco / Específico |
| `convenio_marco_id` | FK → `convenio` (self) | Sí | Convenio Marco vigente del que depende el Específico (RN-3). **Obligatorio** salvo cuando la solicitante es una **DIRIS** (no requiere Marco) |
| `convenio_origen_id` | FK → `convenio` (self, PROTECT) | Sí | Convenio (Marco o Específico) que esta adenda amplía (`related_name='adendas'`) |
| `es_adenda` | bool | No (default `false`) | Marca la fila como adenda de ampliación (derivable de `convenio_origen`; explícito para filtros) |
| `plantilla_id` | FK → `plantilla_convenio` | Sí | Plantilla utilizada |
| `nomenclatura` | varchar(50) | Sí | Nomenclatura oficial del Convenio Marco (se asigna al aprobar DIGEP; renombra a `codigo`). No editable por PATCH libre: la fija el gate de `registrar_evaluacion_tecnica` (solo Marco validado) |
| `titulo` | varchar(255) | No | Título / denominación |
| `solicitante_tipo_contenido_id` | FK → `django_content_type` | No | Tipo de entidad solicitante |
| `solicitante_id_objeto` | int | No | Identificador de la entidad solicitante |
| `unidad_organica_id` | FK → `unidad_organica` | No | Unidad orgánica (GERESA/DIRESA/DIRIS) parte del convenio. Su tipo se deriva de la entidad |
| `gobierno_regional_id` | FK → `gobierno_regional` (PROTECT) | Sí | Gobierno Regional del convenio (solo Convenio Marco regional; `related_name='convenios'`) |
| `universidad_id` | FK → `universidad` | No | Universidad parte del convenio. Su tipo de entidad se deriva de la entidad |
| `unidad_ejecutora_id` | FK → `unidad_ejecutora` (PROTECT) — varchar(4) | Sí | Unidad ejecutora parte del Convenio Específico (nula en Marco; `related_name='convenios'`; valor almacenado es el código presupuestal de 4 chars) |
| `facultad_id` | FK → `facultad` (PROTECT) | Sí | Facultad (de la universidad del Marco) parte del Convenio Específico (nula en Marco; `related_name='convenios'`) |
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

### `parte_convenio` (partes firmantes estructuradas por rol)

Partes firmantes del convenio con relación explícita por rol institucional (no polimórfica). **Se conserva** `participante_convenio` (no la reemplaza). Se sincroniza (idempotente) por `(convenio, rol, orden)` vía `services.sincronizar_partes` y el endpoint `POST /api/v1/conventions/{id}/parties/`. La coherencia órgano↔representante↔cargo y la composición de roles requerida por tipo/categoría (Marco Lima ⇒ MINSA+UNIVERSIDAD; Marco región ⇒ MINSA+GOBIERNO_REGIONAL+UNIVERSIDAD; Específico ⇒ UNIDAD_EJECUTORA+FACULTAD) se validan en el service (no en `clean()`).

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `convenio_id` | FK → `convenio` (CASCADE) | No | Convenio al que pertenece la parte (`related_name='partes_firmantes'`) |
| `rol` | varchar(20) | No | Rol institucional: `MINSA` / `UNIVERSIDAD` / `GOBIERNO_REGIONAL` / `UNIDAD_EJECUTORA` / `FACULTAD` |
| `unidad_organica_id` | FK → `unidad_organica` (PROTECT) | No | Unidad orgánica que representa la parte |
| `organo_representante_id` | FK → `organo_representante` (PROTECT) | Sí | Representante que firma por la parte |
| `cargo_ejecutivo_id` | FK → `cargo_ejecutivo` (PROTECT) | Sí | Cargo ejecutivo del representante |
| `orden` | smallint | No (default `1`) | Orden de firma dentro del rol (apoderado = 2) |
| `es_firmante` | bool | No (default `true`) | Indica si la parte firma el convenio |
| `creado_en` | datetime | No | |
| **Único** | (`convenio_id`, `rol`, `orden`) | | |

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
| `unidad_organica_id` | FK → `unidad_organica` (SET_NULL) | Sí | Unidad evaluadora (DIGEP) — unidad orgánica |
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

Reemplaza a la antigua tabla `campo_clinico`. `unique_together = (ipress, carrera_profesional, especialidad)`.

> **Registro global (sin convenio):** el registro es independiente de cualquier convenio; modela
> la capacidad de la sede para la carrera. El vínculo con convenios se establece a través de las
> asignaciones (`campo_clinico_ipress_universidad`) que sí llevan `convenio_id`.
>
> **Resolución CONAPRES (PDF):** el número/fecha viven en las columnas
> `numero_resolucion_conapres`/`fecha_resolucion_conapres`; el PDF de la resolución se
> adjunta al registro (anexo `RESOL_CONAPRES`, `tipo_actor='CAMPO_CLINICO'`) vía
> `clinical-field-registrations/{id}/annex-upload`.
>
> **Carga masiva:** `POST /api/v1/clinical-field-registrations/bulk-upload/` — disponible para
> los roles **CONAPRES** y **Administrador RENADS** (estructura: `TramaDeterminacionCamposFormacion.xlsx`).

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `ipress_id` | FK → `ipress` (PROTECT) — varchar(8) | No | Sede docente (establecimiento) autorizada por CONAPRES (`es_sede_docente = true`); el valor almacenado es el código RENIPRESS de 8 chars (PK textual de `ipress`) |
| `carrera_profesional_id` | FK → `carrera_profesional` (PROTECT) | No | Carrera / programa académico |
| `especialidad_id` | FK → `especialidad` (SET_NULL) | Sí | Especialidad |
| `campos_clinicos_registrados` | int positivo | No | Total de campos clínicos registrados por CONAPRES para la sede y carrera (renombra `cantidad_maxima`) |
| `campos_clinicos_asignados` | int positivo | No (default `0`) | Acumulador Σ de los campos autorizados en las asignaciones por universidad; lo recalcula el service (**solo lectura** en la API) |
| `numero_resolucion_conapres` | varchar(100) | Sí (blank) | Número de la resolución CONAPRES que autoriza los campos clínicos de la sede |
| `fecha_resolucion_conapres` | date | Sí | Fecha de la resolución CONAPRES |
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
| `ipress_id` | FK → `ipress` (PROTECT) — varchar(8) | No | Sede docente (coherente con el registro padre); el valor almacenado es el código RENIPRESS de 8 chars (PK textual de `ipress`) |
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
| `id_objeto` | varchar(64) | No | Registro afectado. Texto: para IPRESS es el código RENIPRESS (PK textual); para el resto es el pk casteado a `str`. Las consultas por `(tipo_contenido, id_objeto)` usan `str` |
| `nombre_campo` | varchar(100) | Sí | Campo modificado |
| `valor_anterior` | text | Sí | Valor anterior |
| `valor_nuevo` | text | Sí | Valor nuevo |
| `direccion_ip` | varchar(45) | Sí | IP de origen |
| `creado_en` | datetime | No | Fecha y hora |

---

## 12. Mapa de relaciones

```
ubigeo (distrito INEI) >──< ipress / universidad / facultad / gobierno_regional / local_universidad   (también estudiante / tutor del módulo 2)
gobierno_regional ──< unidad_organica
gobierno_regional >── region / ubigeo
gobierno_regional ──< ambito_geografico_sanitario (gobierno_regional_id, nullable — los 4 DIRIS tienen NULL)
unidad_organica (categoria: ORGANO_MINSA / UNIVERSIDAD / GOBIERNO_REGIONAL / MINSA_DIRIS / UNIDAD_EJECUTORA) >── gobierno_regional (opcional, solo regionales)
ambito_geografico_sanitario ──< unidad_ejecutora (PK textual varchar 4)
unidad_ejecutora ──< ipress
ipress >── ambito_geografico_sanitario
ambito_geografico_sanitario ──< red ──< microred ──< ipress
ipress >── categoria / tipo_clasificacion / microred

conapres

organo_representante >── unidad_organica
organo_representante >── cargo_ejecutivo >── unidad_organica   (cargo pertenece a un órgano directivo, 1:N)
organo_representante >── tipo_documento_identidad (módulo 2)
organo_representante ──< historial_organo_representante   (baja del anterior al designar uno nuevo)

universidad >── tipo_gestion_universidad / tipo_entidad_universidad / tipo_autorizacion
universidad ──< facultad >── ubigeo
universidad ──< universidad_carrera >── carrera_profesional   (carreras que dicta cada universidad)
carrera_profesional >── nivel_academico
universidad ──< local_universidad >── region

auth_user ──< perfil_usuario_entidad >── django_content_type (entidad polimórfica)
                       perfil_usuario_entidad >── auth_group

convenio >── tipo_convenio
convenio ──self< (Específico → Marco)            [convenio_marco_id]
convenio >── plantilla_convenio
convenio >── django_content_type (entidad solicitante, polimórfico)
convenio >── unidad_organica / universidad
convenio >── estado_convenio (estado_actual)
convenio ──< participante_convenio >── django_content_type (participante polimórfico)
convenio ──< parte_convenio >── unidad_organica / organo_representante / cargo_ejecutivo   (partes firmantes por rol)
convenio ──< historial_estado_convenio >── estado_convenio
convenio ──< evaluacion_tecnica >── unidad_organica
convenio ──< opinion_conapres                    (solo Específico)
campo_clinico_ipress >── ipress / carrera_profesional / especialidad   (registro CONAPRES — global, sin FK a convenio)
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
- **Solicitud de Convenio Marco (solo GERESA/DIRESA):** validación sobre la entidad solicitante (`unidad_organica.categoria == GOBIERNO_REGIONAL`). Las DIRIS (`categoria == MINSA_DIRIS`) quedan exentas de Marco. Regla en `services.crear_convenio`.
- **CONAPRES y campos clínicos solo en Específico:** tablas `opinion_conapres`, `campo_clinico_ipress` y `campo_clinico_ipress_universidad`; estados con `aplica_a = ESPECIFICO`.
- **Opinión jurídica (OGAJ) solo para Marco:** `opinion_juridica` se registra únicamente cuando `convenio.tipo_convenio = MARCO`.
- **Opinión favorable (CONAPRES) solo para Específico:** `opinion_conapres`.
- **Autorización de sede docente (CONAPRES):** `ipress` autorizada bajo criterios (asistencial, MINSA/FF.AA.-FF.PP., pública).
- **Campos clínicos (dos tablas):** el total por sede/carrera lo registra **CONAPRES** en `campo_clinico_ipress.campos_clinicos_registrados`; los cupos por universidad los asigna el **Órgano Regional** (GERESA/DIRESA/DIRIS) en `campo_clinico_ipress_universidad.campos_clinicos_autorizados`, sin exceder la disponibilidad del registro (`registrados − Σ autorizados`), en el mismo ámbito geográfico sanitario. El acumulador `campo_clinico_ipress.campos_clinicos_asignados` lo recalcula el service tras cada create/update/delete de asignación. Endpoints: `clinical-field-registrations` (CONAPRES) y `clinical-field-allocations` (Gobierno Regional).
- **Versionado documental (RNF-DOC-04 / AUD-04):** `documento_adjunto.version_anterior_id` + `estado`. El versionado se discrimina **siempre** por `documento_adjunto.documento_anexo_id` (par `(objeto, documento_anexo)`).
- **Adjuntos en repositorio externo:** columna `referencia_externa` (en `documento_adjunto`, `plantilla_convenio`). Las columnas `referencia_logo` (logos de `universidad`, `gobierno_regional`, `unidad_organica`, `unidad_ejecutora`, `ipress`) son **`ImageField`** de Django (Etapa 4): guardan el path relativo del objeto en el repositorio de medios (`STORAGES["default"]` = django-storages sobre GCS en prod, `FileSystemStorage` en dev); su `.url` es un signed URL V4 efímero. El **adjunto real** (logos e imágenes / PDFs de anexos) se sirve vía el backend de almacenamiento; ver `docs/api_almacenamiento_frontend.md`. El nombre de archivo se usa solo como ruta de storage al subir; no se persiste en `documento_adjunto`.
- **Trazabilidad de estados (RNF-AUD-03):** `historial_estado_convenio`.
- **Bitácora de auditoría (RNF-AUD-01/02):** `bitacora_auditoria`.
- **Roles y ámbito institucional (RNF-SEG-02/03):** `auth_group` + `perfil_usuario_entidad`.
- **Catálogos parametrizables (RNF-MAN-01):** sección 2.
