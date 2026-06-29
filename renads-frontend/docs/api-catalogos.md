# API — CRUD transversales del Módulo 1 (Catálogos, Entidades, Documentos, Auditoría)

Contrato de los **CRUD de soporte transversales** del Módulo 1 del backend (`apps/convenios`,
`apps/common`). Alimentan las rutas **`/catalogos`** (mantenimiento de tablas maestras) y, en parte,
**`/usuarios`** (perfiles institucionales). El núcleo del convenio está en `docs/api-convenios.md`.

> Fuente de verdad backend: `D:\dev\renads\renaes-api\docs\modulo_01_crud_transversales.md` y el
> código `apps/convenios/{urls,views,serializers}.py`. Base: `/api/v1/`. JWT en todos los endpoints.

## Mapa UI → recursos

| Ruta del front | Mantiene |
|----------------|----------|
| `/catalogos` | Catálogos (solo lectura), Entidades organizacionales/académicas (CRUD), Representantes, Ubigeos, Documentos, Bitácora de auditoría |
| `/usuarios` | `user-entity-profiles` (perfil institucional usuario↔entidad), grupos/roles (ver `docs/api-auth.md`) |

---

## 1. Catálogos (solo lectura)

CRUD de solo lectura (`list`/`retrieve`). Patrón común: filtro `activo`, search `codigo`/`nombre`,
ordering `id`/`codigo`/`nombre` (default `id`). Se usan para poblar selects.

`regions`, `health-geographic-scopes`, `convention-types`, `convention-statuses`, `document-types`,
`university-management-types`, `university-entity-types`, `authorization-types`, `academic-levels`,
`specialties`, `signing-authority-types`, `regional-organ-types`, `executing-unit-types`,
`minsa-organ-types`, `executive-positions`, `observation-reasons`, `rejection-reasons`,
`closure-reasons` (18 catálogos).

`ubigeos` — catálogo INEI (solo lectura). Filtros: `departamento`, `provincia`, `distrito`, `activo`;
search `codigo`/`distrito`/`provincia`/`departamento`.

> Escritura de catálogos: **fuera de alcance** (ya validada/poblada en backend). En `/catalogos` se
> listan/consultan; el alta/edición real aplica a las **entidades** de abajo.

## 2. Entidades organizacionales / académicas (CRUD)

Escritura solo **`Administrador RENADS`** (la autoridad final es el backend). Ordering default `id`.
Cada recurso expone `id` + todos los campos del modelo, con estos filtros/búsqueda:

| Endpoint | Filtros (`filterset_fields`) | Search |
|----------|------------------------------|--------|
| `regional-governments` | `region`, `activo` | `nombre` |
| `regional-organs` | `gobierno_regional`, `tipo_organo_regional`, `activo` | `nombre`, `siglas` |
| `executing-units` | `organo_regional`, `tipo_unidad_ejecutora`, `activo` | `nombre`, `codigo` |
| `ipress` | `unidad_ejecutora`, `ambito_geografico_sanitario`, `activo` | `nombre`, `codigo_renipress` |
| `minsa-organs` | `tipo_organo_minsa`, `activo` | `nombre`, `siglas` |
| `conapres` | `activo` | `nombre` |
| `universities` | `tipo_gestion`, `tipo_entidad`, `tipo_autorizacion`, `activo` | `nombre`, `siglas` |
| `university-authorities` | `universidad`, `activo` | `nombre`, `cargo` |
| `faculties` | `universidad`, `activo` | `nombre` |
| `professional-careers` | `facultad`, `nivel_academico`, `especialidad`, `activo` | `nombre` |
| `university-campuses` | `universidad`, `region`, `activo` | `nombre` |
| `user-entity-profiles` | `usuario`, `grupo`, `activo` | (sin lectura abierta — solo Admin) → ver `/usuarios` |

## 3. Representantes — `representatives`

CRUD polimórfico (representante de órgano MINSA / órgano regional / unidad ejecutora / IPRESS /
CONAPRES). Escritura solo `Administrador RENADS`. Filtros: `tipo_contenido`, `id_objeto`,
`cargo_ejecutivo`, `activo`.

---

## 4. Documentos — `documents` (gestión documental polimórfica + versionado)

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

## 5. Bitácora de auditoría — `audit-logs` (solo lectura)

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

## Pendiente (SDD)

Este documento es **contexto/contrato**. El siguiente paso del flujo SDD es el spec
`spec/catalogos.md` (aprobación humana antes de implementar). No iniciar implementación sin spec
aprobado. Ver `docs/mvp.md` (módulos 6 «Catálogos» y 7 «Gestión de Usuarios»).
