# API — CRUD transversales del Módulo 1 (Catálogos, Entidades, Documentos, Auditoría)

Contrato de los **CRUD de soporte transversales** del Módulo 1 del backend (`apps/convenios`,
`apps/common`). Alimentan las rutas **`/catalogos`** (mantenimiento de tablas maestras) y, en parte,
**`/usuarios`** (perfiles institucionales). El núcleo del convenio está en `docs/api-convenios.md`.

> Fuente de verdad backend: `D:\dev\renads\renads-api` y el código `apps/convenios/{urls,views,serializers}.py`.
> Base: `/api/v1/`. JWT en todos los endpoints.
> Tipos generados del OpenAPI en `lib/api/schema.d.ts` (`npm run gen:api` contra el backend vivo).

**Última revisión de contrato: 2026-08-29** (refactor tabla de órganos unificada).

## Mapa UI → recursos

| Ruta del front | Mantiene |
|----------------|----------|
| `/catalogos` | Catálogos (solo lectura), Entidades organizacionales/académicas (CRUD), Representantes, Ubigeos, Documentos, Bitácora de auditoría |
| `/usuarios` | `user-entity-profiles` (perfil institucional usuario↔entidad), grupos/roles (ver `docs/api-auth.md`) |

---

## 1. Catálogos (solo lectura)

CRUD de solo lectura (`list`/`retrieve`). Patrón común: filtro `activo`, search `codigo`/`nombre`,
ordering `id`/`codigo`/`nombre` (default `id`). Se usan para poblar selects.

**Solo lectura (sin CRUD admin):**
`regions`, `convention-types`, `convention-statuses`, `university-management-types`, `specialties`,
`signing-authority-types`, `observation-reasons`, `rejection-reasons`,
`closure-reasons`, `identity-document-types`, `relationship-types`

`ubigeos` — catálogo INEI (solo lectura). Filtros: `departamento`, `provincia`, `distrito`, `activo`;
search `codigo`/`distrito`/`provincia`/`departamento`.

`organs` — tabla de categorías canónicas (solo lectura): MINSA, Universidad, Órgano Regional, UE.
Campos: `id`, `nombre`. Sin CRUD admin.

### 1.1. Catálogos maestros con CRUD (RNF-MAN-01/02/03)

Catálogos que aceptan **CRUD completo** (`create`/`update`/`partial_update`/`destroy`).
Escritura solo **`Administrador RENADS`** (`IsAdminRoleOrReadOnly`) + auditoría.
Campos del modelo base `Catalog`: `codigo` (único, obligatorio), `nombre` (obligatorio), `activo`.

| Endpoint | Notas | Filtros extra |
|----------|-------|---------------|
| `authorization-types` | Tipo de autorización | — |
| `academic-levels` | Nivel académico de carrera | — |
| `executive-positions` | Cargo ejecutivo de órgano. FK `organo` → `organs`. Campos: `organo`, `nombre_masculino` (req), `nombre_femenino` (opt), `activo` | `organo` |
| `categories` | Categoría de convenio | — |
| `classification-types` | Clasificación de convenio | — |
| `health-geographic-scopes` | Ámbito geográfico sanitario (cúspide: ámbito→red→microrred) | — |

> **Eliminados del backend (no usar):** `organ-types`, `document-types`, `university-entity-types`,
> `regional-organ-types`, `minsa-organ-types`, `executing-unit-types`.

> Front: configurados con `writableCatalog()` en `lib/catalogos/catalogs.ts`. Se editan desde
> `/catalogos/listas/<slug>`.

### 1.2. Estructura sanitaria — redes y microrredes (CRUD)

Jerarquía de red asistencial, CRUD (escritura solo **`Administrador RENADS`** + auditoría).
Campos base `Catalog` (`codigo`/`nombre`/`activo`) más su FK de jerarquía:

| Endpoint | Modelo | Filtros | Search |
|----------|--------|---------|--------|
| `networks` | `Red` | `ambito_geografico_sanitario`, `activo` | `codigo`, `nombre` |
| `micro-networks` | `Microred` | `red`, `activo` | `codigo`, `nombre` |

> `Red` cuelga de `health-geographic-scopes` (ámbito geográfico sanitario) y `Microred` de `Red`.
> Front: `networks`/`micro-networks` ya tienen config de entidad en `lib/catalogos/entities.ts`
> (`SANITARY_ENTITY_CONFIGS`), editables desde `/catalogos/entidades/<slug>`. En el alta de
> microrred, un selector auxiliar de ámbito filtra el select de `red` (cascada).

---

## 2. Entidades organizacionales / académicas (CRUD)

Escritura solo **`Administrador RENADS`** (la autoridad final es el backend). Ordering default `id`.
Cada recurso expone `id` + todos los campos del modelo, con estos filtros/búsqueda.

**Refactor 2026-08-29:** `regional-organs` y `minsa-organs` se unificaron en `organ-directories`.
`executing-units` cambió `organo_regional`/`tipo_unidad_ejecutora` por `gobierno_regional`/`tipo_organo`.
`university-authorities` fue eliminado.

**Refactor 2026-08-30:** `organ-directories` reemplaza FK `organo`+`tipo_organo` (→ `organs`/`organ-types`)
por campo CharField `categoria` con choices (`ORGANO_MINSA | UNIVERSIDAD | GOBIERNO_REGIONAL | MINSA_DIRIS | UNIDAD_EJECUTORA`).
Eliminados de `organ-directories`: `ubigeo`, `direccion`, `numero_ruc`, `correo`, `telefono_institucional`.
Añadidos a `regional-governments`: `sigla`, `ubigeo`, `numero_ruc`, `direccion`, `correo`, `telefono`.
`executing-units.tipo_organo` ahora apunta a `organ-directories?categoria=UNIDAD_EJECUTORA` (no a `organ-types`).

| Endpoint | Filtros (`filterset_fields`) | Search | Detalles |
|----------|------------------------------|--------|----------|
| `organs` | — | — | Solo lectura. 4 categorías canónicas. |
| `organ-directories` | `categoria`, `gobierno_regional`, `activo` | `nombre`, `siglas` | `gobierno_regional_detalle` (string) |
| `executing-units` | `tipo_organo`, `gobierno_regional`, `activo` | `nombre`, `codigo` | `tipo_organo_detalle`, `gobierno_regional_detalle`, `ubigeo_detalle` |
| `regional-governments` | `region`, `ubigeo`, `activo` | `nombre` | `ubigeo_detalle` (string) |
| `ipress` | `unidad_ejecutora`, `ambito_geografico_sanitario`, `es_sede_docente`, `activo` | `nombre`, `codigo_renipress` | — |
| `conapres` | `activo` | `nombre` | — |
| `universities` | `tipo_gestion`, `tipo_entidad`, `tipo_autorizacion`, `activo` | `nombre`, `siglas` | `tipo_gestion_detalle`, `tipo_entidad_detalle`, `tipo_autorizacion_detalle` |
| `faculties` | `universidad`, `ubigeo`, `activo` | `nombre`, `direccion` | `ubigeo_detalle` (objeto ubigeo); `referencia_logo` (logo) |
| `professional-careers` | `nivel_academico`, `activo` | `nombre` | — |
| `university-campuses` | `universidad`, `region`, `activo` | `nombre` | — |
| `university-careers` | `universidad`, `carrera_profesional`, `facultad`, `activo` | — | `universidad_detalle`, `carrera_profesional_detalle`, `facultad_detalle` (todos strings) |
| `user-entity-profiles` | `usuario`, `grupo`, `activo` | — | Solo `Administrador RENADS`. |

> Los campos `*_detalle` son **objetos JSON** (no strings). `_detalle_nombre` → `{id, codigo, nombre}`; `_detalle_ubigeo` → `{id, codigo, distrito, provincia, departamento}`. En columnas usar `detalleNombre(r.*_detalle)` o `ubigeoDetalleLabel(r.ubigeo_detalle)`. Nunca `String(r.*_detalle)` (produce `[object Object]`).

### `organ-directories` — campo `categoria`

El campo `categoria` es un CharField con choices (reemplaza al FK `organo`). Valores:

| Valor | Label |
|-------|-------|
| `ORGANO_MINSA` | Órgano del MINSA |
| `UNIVERSIDAD` | Universidad |
| `GOBIERNO_REGIONAL` | Gobierno Regional |
| `MINSA_DIRIS` | MINSA DIRIS |
| `UNIDAD_EJECUTORA` | Unidad Ejecutora |

Filtrar por categoría: `?categoria=GOBIERNO_REGIONAL`. No hay `tipo_organo` ni `ubigeo` en el directorio.
`gobierno_regional` (FK opcional) aplica solo a categorías regionales.

### `regional-governments` — campos de contacto e identificación

```
id (readonly), referencia_logo (readonly), ubigeo_detalle (readonly string),
nombre (req), sigla?, region (FK req), ubigeo (FK|null),
numero_ruc?, direccion?, correo?, telefono?, activo?
```

### `executing-units` — `tipo_organo` apunta a `organ-directories`

El campo `tipo_organo` es FK a `organ-directories` con `limit_choices_to={"categoria": "UNIDAD_EJECUTORA"}`.
Para el selector del front usar `?categoria=UNIDAD_EJECUTORA`. El `tipo_organo_detalle` es el `nombre`
del órgano del directorio seleccionado.

### `ipress` — sede docente (CONAPRES)

- Campo booleano **`es_sede_docente`** (default `false`): IPRESS autorizada por CONAPRES.
  Requisito para registrar **campos clínicos** de un convenio.
- Acción **`POST /ipress/{id}/autorizar-sede-docente/`** — rol **`CONAPRES`**.
  Body: `{ "autorizar": true|false }` (default `true`). Devuelve la IPRESS actualizada.

### `university-careers` — FK `facultad` requerida (RN-FC-02/03)

`UniversityCareerSerializer` (no `_auto_serializer`). Campos escritura: `universidad`, `carrera_profesional`,
`facultad` (requerida), `activo`. Campos solo lectura: `universidad_detalle`, `carrera_profesional_detalle`,
`facultad_detalle` (strings planos, no `{id, nombre}`). Validación: la facultad debe pertenecer a la
universidad del registro (error 400 si no). Filtros: `universidad`, `carrera_profesional`, `facultad`, `activo`.

Acción bulk en `FacultyViewSet`: `POST /faculties/{id}/careers/` con body `{ carreras: [ids] }` —
asigna en lote las carreras de la facultad (idempotente); devuelve lista `university-careers` activas.
Solo `Administrador RENADS`.

> **`faculties`**: `FacultyAuto` no expone `universidad_detalle` (viewset sin kwarg `detalles`).
> La tabla de facultades solo muestra `nombre` + `activo`. Ver REQ-BACK-03 en `CLAUDE.md`.

### `universities` — `tipo_entidad` apunta a `organ-directories`

El campo `tipo_entidad` es FK a `OrganDirectory` con `limit_choices_to={"categoria": "UNIVERSIDAD"}`.
Para el selector del front usar `?categoria=UNIVERSIDAD`.

### Endpoints eliminados (no usar)

`regional-organs`, `minsa-organs`, `university-authorities`, `organ-types` — eliminados del backend.
Usar `organ-directories` con filtro `?categoria=<VALOR>` según corresponda.

---

## 3. Cargos por órgano del directorio — `organ-directory-positions` (puente N:M)

Tabla puente `organo_directorio_cargo` que declara **qué cargos** tiene habilitados cada entidad
del directorio, independientemente de la persona designada (que la aporta `organ-representatives`).

Escritura solo **`Administrador RENADS`** (con auditoría).

**Filtros:** `organo_directorio`, `cargo_ejecutivo`, `activo`.

### OrganDirectoryPosition — lectura

```
id, organo_directorio (FK int), cargo_ejecutivo (FK int), activo
organo_directorio_detalle: { id, nombre, categoria (display label) }
cargo_ejecutivo_detalle:   { id, nombre_masculino, nombre_femenino }
```

### OrganDirectoryPosition — escritura

```
organo_directorio (FK int, req), cargo_ejecutivo (FK int, req), activo (bool, default true)
```

> **Validaciones backend:**
> - **Coherencia cargo↔categoría:** `cargo.organo.nombre == organo_directorio.get_categoria_display()`.
>   Los `organs.nombre` coinciden exactamente con los display labels de `ORGAN_DIRECTORY_CATEGORY`:
>   `"Órgano del MINSA"` / `"Universidad"` / `"Gobierno Regional"` / `"MINSA DIRIS"` / `"Unidad Ejecutora"`.
> - **Unicidad:** `unique_together (organo_directorio, cargo_ejecutivo)` — error 400 si el par existe.
>
> **Uso en el front:** el form de `organ-representatives` consulta
> `?organo_directorio=<id>&activo=true` para obtener los cargos válidos del órgano seleccionado
> antes de desplegar el selector de cargo ejecutivo.

---

## 4. Representantes de órgano — `organ-representatives`

CRUD directo (representante con FK directa a `organo_directorio`). **Reemplaza** al antiguo
`representatives` (polimórfico) eliminado en el refactor 2026-08-29.

Escritura solo **`Administrador RENADS`** (`IsAdminRoleOrReadOnly`).
AnnexAttachmentMixin: adjunta PDFs del actor `REPRESENTANTE` (`annex-upload`/`annex-checklist`).

Al crear, el backend ejecuta `registrar_organo_representante`: da de baja automáticamente al
representante anterior activo del mismo par `(organo_directorio, cargo_ejecutivo)` y lo mueve al
histórico (`organ-representative-history`).

**Filtros:** `organo_directorio`, `cargo_ejecutivo`, `activo`.
**Search:** `nombre`, `numero_documento_identidad`.

### OrganRepresentative — campos

```
id (readonly), nombre, numero_documento_identidad, sexo (M|F),
fecha_inicio_designacion (date), numero_resolucion_designacion?,
fecha_inicio_facultades? (date|null), activo?,
organo_directorio (FK int), tipo_documento_identidad (FK int → identity-document-types),
cargo_ejecutivo (FK int → executive-positions)
```

> No expone `*_detalle` — el serializer usa `fields = "__all__"`. En tabla mostrar
> `nombre`, `numero_documento_identidad`, `sexo`, `fecha_inicio_designacion`, `activo`.

### Histórico — `organ-representative-history` (solo lectura)

Registro de representantes dados de baja. Filtros: `organo_directorio`, `cargo_ejecutivo`, `representante`.
Campos adicionales: `fecha_baja`, `motivo`, `creado_en`.

---

## 5. Documentos — `documents` (gestión documental polimórfica + versionado)

Adjunta documentos a **cualquier entidad** (convenio, actividad, …) vía `tipo_contenido` + `id_objeto`,
con versionado. Almacenamiento **por referencia externa (stub)** — no sube binarios; guarda una
`referencia_externa`. Permisos: **miembro institucional autenticado**.

| Método | Ruta | Notas |
|--------|------|-------|
| GET | `/documents/` , `/documents/{id}/` | lista/detalle; filtros abajo |
| POST | `/documents/` | crea (el `version`/`estado`/`version_anterior` los fija el service) |
| DELETE | `/documents/{id}/` | elimina |
| GET | `/documents/{id}/url-descarga/` | devuelve `{ "url": "<referencia firmada>" }` |

**Filtros** (`DocumentFilter`): `tipo_contenido`, `id_objeto`, `tipo_documento`, `estado`.

### Document — lectura (`GET`)
```
id, tipo_documento, tipo_documento_nombre, tipo_contenido, tipo_contenido_label, id_objeto,
referencia_externa, nombre_archivo, version, estado, version_anterior, cargado_por, cargado_en
```
Read-only: `version`, `estado`, `version_anterior`, `cargado_por`, `cargado_en`.

### Document — escritura (`POST`)
```
tipo_contenido, id_objeto, tipo_documento, nombre_archivo, referencia_externa
```
> Validación: el objeto destino (`tipo_contenido` + `id_objeto`) debe existir.

---

## 6. Bitácora de auditoría — `audit-logs` (solo lectura)

Endpoint **read-only** (`ReadOnlyModelViewSet`) para consultar la bitácora. Acceso restringido a
**`Administrador RENADS` / Auditor** (`IsAdminRole`). Ordenado por `creado_en` desc.

| Método | Ruta | Notas |
|--------|------|-------|
| GET | `/audit-logs/` , `/audit-logs/{id}/` | solo lectura |

**Filtros:** por usuario, acción, entidad (`tipo_contenido`), objeto (`id_objeto`) y rango de fechas.
**Search:** `accion`. **Ordering:** `creado_en`, `id`.

### AuditLog — lectura (`GET`)
```
id, usuario, usuario_nombre, accion, tipo_contenido, tipo_contenido_label, id_objeto,
nombre_campo, valor_anterior, valor_nuevo, direccion_ip, creado_en
```
Todos los campos son read-only.

---

## Roles (gating UX; el backend es la autoridad)

- **Catálogos / Entidades / Representantes / Documentos:** lectura para miembro institucional
  autenticado; escritura de entidades solo `Administrador RENADS`.
- **`user-entity-profiles` / `audit-logs`:** solo `Administrador RENADS` (Auditor para consulta de
  bitácora).
