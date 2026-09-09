# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este proyecto

Frontend (Next.js) de **RENADS** — Registro Nacional de Articulación Docencia-Servicio en Salud
(MINSA, Perú). Consume el backend **RENADS API** (Django + DRF) ubicado en `D:\dev\renads\renads-api`
(monorepo: back y front comparten el repo raíz `D:\dev\renads`, con historial de commits común).

**Antes de construir cualquier vista, leer `docs/`** — contiene el contrato del backend (endpoints,
campos, roles, estados) sin necesidad de abrir el repo del backend:

| Doc | Contenido |
|-----|-----------|
| `docs/README.md` | Índice y fuentes de verdad |
| `docs/mvp.md` | **Orden obligatorio de módulos** y alcance de cada uno |
| `docs/backend-overview.md` | Stack, base URL (`http://localhost:8000/api/v1/`), paginación, filtros, roles, OpenAPI |
| `docs/api-auth.md` | JWT (`/auth/token`, `/refresh`, `/me`), roles/grupos, alcance institucional |
| `docs/api-convenios.md` | Módulo 1 — Gestionar Convenios (núcleo) |
| `docs/api-catalogos.md` | Módulo 1 — CRUD transversales: catálogos, entidades, representantes, documentos, auditoría (rutas `/catalogos` y `/usuarios`) |
| `docs/api-internados.md` | Módulo 2 — Registrar Internados |
| `docs/api-actividades.md` | Módulo 3 — Registrar Actividades docente-asistenciales |
| `docs/api-usuarios.md` | Gestión de Usuarios — usuarios, roles/grupos y permisos (`apps/common`, ruta `/usuarios`, solo superusuario) |
| `docs/api-almacenamiento.md` | **Transversal** — adjuntos reales: logos de entidades (`upload-logo`/`logo-url`) y PDFs de anexos por actor (`annex-checklist`/`annex-upload`), sobre GCS + signed URLs; incluye Feature F3 (contraseña temporal + declaraciones juradas) |
| `docs/frontend-conventions.md` | Idioma, SDD, cliente HTTP, gating por rol, estructura propuesta |

### Estado de módulos (actualizado 2026-09-02)

| # | Módulo | Ruta front | Estado | Spec / Validación |
|---|--------|-----------|--------|-------------------|
| 1 | Auth | `/login`, `/auth/*` | ✅ **CERRADO** | `spec/auth.md` / `spec/auth.validacion.md` |
| 2 | Convenios | `/convenios` | ✅ **CERRADO** | `spec/convenios.md` / `spec/convenios.validacion.md` |
| 3 | Internados | `/internados` | ✅ **CERRADO** | `spec/internados.md` / `spec/internados.validacion.md` |
| 4 | Actividades | `/actividades` | ✅ **CERRADO** | `spec/actividades.md` / `spec/actividades.validacion.md` |
| 5 | Dashboard | `/dashboard` | ✅ **v1 hecho** | `spec/dashboard.md` / `spec/dashboard.validacion.md` |
| 6 | Catálogos | `/catalogos` | ✅ **CERRADO** | `spec/catalogos.md` / `spec/catalogos.validacion.md` |
| 7 | Usuarios | `/usuarios` | ✅ **CERRADO** | `spec/usuarios.md` / `spec/usuarios.validacion.md` |
| T | Almacenamiento | transversal | ✅ **CERRADO** | `spec/almacenamiento.md` / `spec/almacenamiento.validacion.md` |
| 8 | Campos de Formación | `/campos-clinicos` | 🟡 **en progreso** | — |
| 9 | Calendario de Actividades | `/calendario` | ✅ **implementado** | — |

> Para iniciar trabajo en un módulo nuevo, usar el flujo del orquestador SDD (ver §Metodología SDD).

### Módulos del backend y contrato

1. **Gestionar Convenios** (`apps/convenios`) — convenios Marco/Específicos, evaluaciones, opiniones (DIGEP/CONAPRES/OGAJ), firmas, publicación, vigencia.
   - **CRUD transversales del Módulo 1** (`apps/convenios` + `apps/common`): catálogos, entidades organizacionales/académicas (CRUD, escritura `Administrador RENADS`), representantes, `user-entity-profiles`, **documentos** (`documents`, gestión documental polimórfica con versionado) y **bitácora de auditoría** (`audit-logs`, solo lectura, `Administrador RENADS`/Auditor). Contrato: `docs/api-catalogos.md`. Rutas front: `/catalogos` y `/usuarios`.
   - **Catálogos con CRUD completo** (escritura `Administrador RENADS`, filtro `activo`, search `codigo`/`nombre`): `authorization-types`, `academic-levels`, `executive-positions` (**refactor 2026-09-01:** quitó FK `organo`→`Organ`; ahora FK `organo_directivo`→`OrganDirectory`; `unique_together (organo_directivo, nombre_masculino)`; campos: `organo_directivo` req, `nombre_masculino` req, `nombre_femenino` opt; detalle `organo_directivo_detalle: {id, nombre, categoria}`; filtros: `organo_directivo`, `activo`), `categories`, `classification-types`, `health-geographic-scopes` (6 catálogos). `organs` (**5 categorías canónicas** — solo lectura, cuyos `nombre` replican los display labels de `ORGAN_DIRECTORY_CATEGORY`: `"Órgano del MINSA"` / `"Universidad"` / `"Gobierno Regional"` / `"MINSA DIRIS"` / `"Unidad Ejecutora"`). `organ-types` **eliminado** del backend. Los demás son solo lectura.
   - **Entidades académicas con CRUD:** `faculties`, `professional-careers`, `university-campuses`, **`university-careers`** (tabla puente `universidad ↔ carrera_profesional ↔ facultad`; FK `facultad` requerida en escritura — RN-FC-02/03: facultad debe pertenecer a la universidad; `UniversityCareerSerializer` valida esto; expone `universidad_detalle`/`carrera_profesional_detalle`/`facultad_detalle` como strings; filtros: `universidad`, `carrera_profesional`, `facultad`, `activo`; acción bulk `POST /faculties/{id}/careers/ {carreras:[ids]}` en `FacultyViewSet`). Config en `lib/catalogos/entities.ts` (`ACADEMIC_ENTITY_CONFIGS`). `FacultyAuto` no expone `universidad_detalle` (ver REQ-BACK-03).
   - **`detalles` en viewsets:** los viewsets con `_auto_serializer` inyectan campos `*_detalle` como **objetos JSON** (nunca strings planos). Patrones: `_detalle_nombre` → `{id, codigo, nombre}`; `_detalle_ubigeo` → `{id, codigo, distrito, provincia, departamento}`; `_detalle_fk(obj, "nombre")` → `{id, nombre}`. En columnas usar `detalleNombre(r.*_detalle)` para FKs con `nombre`, y `ubigeoDetalleLabel(r.ubigeo_detalle)` para ubigeos. **Nunca `String(r.*_detalle)`** (produce `[object Object]`). Implementado para: `executive-positions` (`organo_directivo_detalle`: `{id, nombre, categoria}`), `organ-directories` (`gobierno_regional_detalle`), `executing-units` (`tipo_organo_detalle`, `gobierno_regional_detalle`, `ubigeo_detalle`), `regional-governments` (`ubigeo_detalle`), `faculties` (`ubigeo_detalle`), `university-careers` (`universidad_detalle`, `carrera_profesional_detalle`, `facultad_detalle`), `universities` (`tipo_gestion_detalle`, `tipo_entidad_detalle`, `tipo_autorizacion_detalle`). Los viewsets con serializer custom `__all__` sin `SerializerMethodField` (e.g. `organ-representatives`) NO exponen `*_detalle`.
   - **`organ-directory-positions` ELIMINADO** (migración 0034, 2026-09-01): la tabla puente fue reemplazada por FK directa `executive-positions.organo_directivo → OrganDirectory`.
   - **Representantes multi-entidad (polimórfico, mig 0038, 2026-09-07):** `organ-representatives` ya NO usa FK `organo_directorio`; enlaza a cualquier entidad vía `tipo_contenido`+`id_objeto` (GenericFK). Modelos permitidos: `OrganDirectory` (MINSA/GORE/DIRIS por `organo`), `University`, `ExecutingUnit`, `Conapres`, `Ipress`. Endpoint `representante-content-types` resuelve el `ContentType.id` por `model`. Serializer expone `entidad_detalle {tipo,id,nombre}`. Cargos del form = **globales** (`executive-positions?organo_directivo__isnull=true&activo=true`) ∪ por órgano (`?organo_directivo=<id>` solo si la entidad es OrganDirectory). Pantalla `/catalogos/representantes` en 2 pasos (tipo → entidad). Config de front en `lib/catalogos/representantes-entities.ts`. Ver `spec/representantes.md`.
   - **Refactor 2026-08 — tabla de órganos unificada:** el backend eliminó las tablas `regional-organs`, `minsa-organs`, `regional-organ-types`, `minsa-organ-types`, `executing-unit-types`, `document-types`, `university-entity-types` y las reemplazó con: `organs` (5 categorías canónicas; solo lectura), `organ-directories` (directorio unificado, discriminado por CharField `categoria` — ver refactor 2026-08-30). `organ-types` también eliminado (ver refactor 2026-08-31). `Convention` cambió campo `organo_regional`→`organo_directorio`. Representantes renombrados de `representatives`→`organ-representatives`. `university-authorities` eliminado.
   - **Refactor 2026-09-07 (mig 0039) — `organ-directories` vuelve a FK `organo`→Organ (reemplaza `categoria`):** el discriminador es de nuevo la **FK `organo`** (id-based, tabla canónica `organs`), NO el CharField `categoria` (que quedó obsoleto — ver nota histórica abajo). Filtrar `?organo=<id>` (el front resuelve el id vía `organs` en runtime, `lib/catalogos/organs.ts`; nunca hardcodear). Unicidad `(organo, gobierno_regional, nombre)` con caso GORE nulo. `executing-units.tipo_organo`/`University.tipo_entidad` `limit_choices_to={"organo__nombre": ...}`. Ver tabla de refactors.
   - **[HISTÓRICO, SUPERSEDED 2026-09-07] Refactor 2026-08-30 — `organ-directories` usó `categoria` CharField:** (ya no aplica: revertido a FK `organo` el 2026-09-07). Eliminó los FK `organo`/`tipo_organo` y `ubigeo`; discriminador `categoria` (choices). `regional-governments` ganó `sigla`, `ubigeo` (FK), `numero_ruc`, `direccion`, `correo`, `telefono` (migración 0027+0030 — esto sigue vigente).
   - **Refactor 2026-08-31 — `organ-types` eliminado; `executive-positions` + `faculties` cambiados:** `organ-types` eliminado del backend. `executive-positions` quitó `codigo`, `nombre` → `nombre_masculino` (req) + `nombre_femenino` (opt). `faculties` ganó `ubigeo` (FK) + `referencia_logo`. `University.tipo_entidad` FK ahora apunta a `OrganDirectory?categoria=UNIVERSIDAD` (antes a `OrganType`).
   - **Refactor 2026-09-01 — `executive-positions` FK a órgano concreto; `organ-directory-positions` eliminado:** `executive-positions` quitó FK `organo`→`Organ` (categoría) y añadió FK `organo_directivo`→`OrganDirectory` (órgano concreto); `unique_together (organo_directivo, nombre_masculino)`; filtro `organo_directivo`. La tabla puente `organ-directory-positions` fue eliminada (migración 0034). El form de `organ-representatives` filtra cargos con `executive-positions?organo_directivo=<id>&activo=true`.
   - **Refactor 2026-09-02 — Adendas, partes tipadas, resolución CONAPRES (migración 0025):** `Convention` ganó `convenio_origen` (self-FK), `es_adenda`, `nomenclatura` (asignada por DIGEP, no editable en alta/edición), `unidad_ejecutora` (FK ExecutingUnit, req. para Específico), `facultad` (FK Faculty, req. para Específico). Nuevo modelo `ConventionParty` + endpoint `conventions/{id}/parties` (GET/POST sincroniza lista completa; roles: MINSA/UNIVERSIDAD/GOBIERNO_REGIONAL/UNIDAD_EJECUTORA/FACULTAD). Acción `conventions/{id}/adenda` (POST). `ClinicalFieldRegistration` ganó `numero_resolucion_conapres` + `fecha_resolucion_conapres`. **Endpoint `conventions/{id}/campos-clinicos` ELIMINADO** — reemplazado por CRUD independiente `clinical-field-registrations`. `organ-types` ELIMINADO del backend: formulario de convenio ya no usa `CascadingEntityField`; ahora selecciona `organ-directories` y `universities` directamente. `nomenclatura` es read-only en `Convention`; `evaluacion-tecnica` acepta `nomenclatura` como campo write-only para Marcos.
   - **Estructura sanitaria (CRUD `Administrador RENADS`):** `networks` (`Red`, FK `ambito_geografico_sanitario` → `health-geographic-scopes`) y `micro-networks` (`Microred`, FK `red`). Jerarquía ámbito → red → microrred. **Config de front implementada** en `lib/catalogos/entities.ts` (`SANITARY_ENTITY_CONFIGS`); accesibles desde `/catalogos/entidades/networks` y `/catalogos/entidades/micro-networks`. El alta de microrred usa selector virtual de ámbito que filtra `red` en cascada (campo virtual `_ambito`, `N9-N11`). Contrato: `docs/api-catalogos.md` §1.2.
   - **Sede docente IPRESS:** campo booleano `ipress.es_sede_docente`; acción `POST /ipress/{id}/autorizar-sede-docente/` solo rol `CONAPRES`. UI en `components/catalogos/ipress-sede-docente-action.tsx`. Requisito para registrar campos clínicos.
   - **Borrado protegido → HTTP 409** (`ProtectedDeleteConflict`): al eliminar un registro referenciado por FK protegida, el backend devuelve 409 con mensaje legible. El front muestra el detalle (`extractApiError`).
   - **Tipos OpenAPI generados:** `lib/api/schema.d.ts` se regenera con `npm run gen:api` (openapi-typescript contra `http://localhost:8000/api/v1/schema/`). Regenerar tras cualquier cambio de contrato del backend.

2. **Registrar Internados** (`apps/internados`) — internos, tutores, internados, rotaciones, autorizaciones.
   Incluye Feature F3: onboarding del interno con contraseña temporal (`debe_cambiar_password` +
   `/auth/me/cambiar-password/`) y declaraciones juradas (`estado_declaraciones`, `revisar-declaraciones`).
   - **Tutor ↔ universidades** (RN-24): `tutors.universidades` es M2M de **1 a 2** universidades (400 si 0 o >2); filtro `?universidades=<id>`. Los tutores no están acotados por universidad en lectura (son compartidos).
   - **Contacto de emergencia** movido de `students` → **`interns`/internado** (`contacto_emergencia_nombre`/`_telefono`/`_parentesco` FK `relationship-types`). `students.anio_academico` **eliminado**.
   - **Anexos DJ del interno** (actor `INTERNO`, `annex-upload`/`annex-checklist`) se adjuntan **sobre el internado** (`interns/{id}/...`), **no** sobre el estudiante. El endpoint `students` ya no expone anexos. Puede adjuntar el rol `Universidad`/`Administrador RENADS` o el propio `Interno`.
   - **Accesos y alcance por universidad:** la UI resuelve el selector de universidad desde `perfiles` de `/auth/me/` (una → fija; varias → elegir; global → catálogo). Implementado en `lib/auth/scope.ts` (`useUniversityScope`).

3. **Registrar Actividades** (`apps/actividades`) — actividades docente-asistenciales y su validación.

4. **Campos de Formación** (transversal, `campos-clinicos`) — determinación y asignación de campos clínicos por convenio específico vigente. Incluye:
   - **`/campos-clinicos`** — índice con resumen por sede docente.
   - **`/campos-clinicos/registros`** — `DeterminacionView` (componente custom, `components/campos-clinicos/determinacion-view.tsx`): lista de campos clínicos con agrupación por ámbito/red/sede, columnas con totales registrados/asignados/disponibles, badge de convenio vigente, filtros servidor + cliente. Solo muestra IPRESS con `es_sede_docente=true`.
   - **`/campos-clinicos/asignaciones`** — vista de asignaciones por universidad.

5. **Calendario de Actividades** (`/calendario`, `apps/calendario`) — programación de actividades administrativas del proceso docencia-servicio. **Solo rol `Administrador RENADS`.** Implementado en `lib/calendario/activities.ts` + páginas en `app/(app)/calendario/`. El campo `responsables` es texto libre (sin M2M).

**Adjuntos reales (transversal, Módulos 1–2):** subida/visualización de **logos** de entidades
(`universities`, `regional-governments`, `organ-directories`, `executing-units`, `ipress`, `faculties`) con fallback
institucional, y **anexos PDF** (declaraciones juradas por actor: `interns` (INTERNO),
`organ-representatives` (REPRESENTANTE)). Contrato: `docs/api-almacenamiento.md`. Capa API en
`lib/api/storage.ts`; UI en `components/ui/entity-logo.tsx`,
`components/catalogos/logo-upload-dialog.tsx`,
`components/almacenamiento/annex-checklist-dialog.tsx`.

Más auth/transversal (`apps/common`): login JWT, `/auth/me`, alcance institucional, auditoría, y
**administración de usuarios/roles/permisos** (`users`, `groups`, `permissions` — solo superusuario;
contrato en `docs/api-usuarios.md`, ruta front `/usuarios`).

### Bloqueo de módulos por calendario (`ModuleGate`)

El componente `components/auth/module-gate.tsx` (`ModuleGate`) bloquea el acceso a un módulo cuando
está fuera de su ventana de registro en el Calendario de actividades. Comprueba `modulos_bloqueados`
de `/auth/me/` contra los `contentTypes` del módulo (e.g., `{ appLabel: "convenios", model: "convention" }`).
`Administrador RENADS` y superusuario quedan exentos. La autoridad final es el backend (`IsModuleEnabled`);
este gate es UX. Los layouts de módulo lo usan:

- `app/(app)/convenios/layout.tsx` — gate para convenios
- `app/(app)/internados/layout.tsx` — gate para internados (internship + student)
- `app/(app)/actividades/layout.tsx` — gate para actividades (teachingactivity)

### Convenciones de idioma

- **UI/comentarios/docs en español; código en inglés.** Las claves del API van en español
  (`fecha_inicio`, `estado_codigo`) — no traducirlas al tipar.
- El backend es la fuente de verdad del contrato; preferir tipos generados de OpenAPI
  (`/api/v1/schema/`). Mantener `docs/` sincronizada cuando cambie un contrato del backend.

## Metodología SDD (obligatoria)

El frontend se desarrolla con **Spec Driven Development (SDD)**, coordinado por el agente
**`orchestrator`** (`.claude/agents/orchestrator.md`). **Para todo desarrollo de un módulo o feature,
usar SIEMPRE el flujo del orquestador:**

```
orchestrator → spec → (APROBACIÓN HUMANA) → implement → validator → (repetir implement↔validator hasta OK)
```

- **`orchestrator`** — coordina; no escribe código ni specs. Elige el siguiente módulo según `docs/mvp.md`.
- **`spec`** — analiza el módulo y crea las tareas en `spec/<modulo>.md`. **La lista debe aprobarla un humano antes de Implement.**
- **`implement`** — escribe el código según el spec, con buenas prácticas Next.js (App Router) y SOLID.
- **`validator`** — verifica que el código cumpla el spec/contrato, **marca tareas hechas** en `spec/<modulo>.md` y genera `spec/<modulo>.validacion.md`.

**Regla de oro: un módulo a la vez.** El orden lo define `docs/mvp.md` (Auth → Convenios →
Internados → Actividades). No iniciar un módulo sin cerrar (validar) el anterior. Antes de
especificar o implementar, **leer siempre `docs/*.md`** (contrato del backend).

## Commands

- `npm run dev` — start dev server at http://localhost:3000 (hot reload)
- `npm run build` — production build
- `npm start` — serve the production build (run `build` first)
- `npm run lint` — ESLint
- `npm run gen:api` — regenerar `lib/api/schema.d.ts` desde el OpenAPI del backend vivo

No test runner is configured yet — there are no tests to run until one is added.

## Stack

Base: Next.js 16 (App Router) · React 19 · TypeScript 5 (strict) · Tailwind CSS v4 · ESLint 9 (flat config).

Librerías del proyecto (rol fijo por convención):

- **shadcn/ui** — todos los componentes de UI (Radix + Tailwind). No escribir UI a mano si existe componente shadcn.
- **TanStack Query** (`@tanstack/react-query`) — server-state: toda petición al backend (fetch, cache, invalidación, mutaciones). No usar `fetch`/Axios suelto en componentes.
- **TanStack Table** (`@tanstack/react-table`) — todas las tablas/listados, vía el wrapper `components/ui/data-table.tsx`.
- **Axios** — cliente HTTP único en `lib/api/` (JWT + refresh + unwrap de paginación DRF). Axios solo se usa dentro de `lib/api/`.
- **Zustand** — estado global de cliente (sesión/token, `me`, UI). No duplicar datos de servidor (eso es TanStack Query).

## Architecture notes

- **App Router**: all app code lives in `app/`. `app/layout.tsx` is the root layout — it loads Geist / Geist Mono via `next/font/google` and sets the html/body flex-column shell. `app/page.tsx` is the home route.
- **Tailwind v4 is configured in CSS, not JS** — there is no `tailwind.config.js`. Design tokens live in `app/globals.css` via `@import "tailwindcss"` and an `@theme inline` block. To add colors/fonts/tokens, edit `globals.css`, not a JS config. The PostCSS wiring is in `postcss.config.mjs`.
- **Dark mode** uses `prefers-color-scheme` with CSS variables (`--background` / `--foreground`) defined in `app/globals.css`.
- **Path alias**: `@/*` maps to the repo root (see `tsconfig.json`), e.g. `import x from "@/app/..."`.
- **ESLint** uses flat config in `eslint.config.mjs`, extending `eslint-config-next` core-web-vitals + typescript.

## Infraestructura CRUD declarativa (clave para nuevas vistas)

- `components/crud/resource-crud.tsx` — CRUD completo declarativo (tabla + búsqueda + filtros + diálogos alta/edición + borrado + row actions). Acepta `ResourceConfig` de `lib/crud/types.ts`.
- `components/crud/resource-form.tsx` — formulario declarativo con soporte de: `text`, `number`, `boolean`, `date`, `email`, `password`, `select` (FK vía `EntityCombobox`), `multiselect` (vía `MultiEntityCombobox`), `separator` (encabezado de sección visual, no genera payload), campos `virtual` (excluidos del payload, usados para cascada entre selects, `optionsParamsFrom`, `resetsOn`).
- `lib/crud/types.ts` — tipos `ResourceConfig`, `FieldConfig`, `FilterConfig`, `ColumnConfig`, `RowAction`. `FieldConfig.virtual` excluye el campo del payload; `optionsParamsFrom` + `resetsOn` para cascada de selects dependientes. `type: "separator"` → sección visual con etiqueta + línea horizontal, siempre full-width.
- `lib/api/query.ts` — `createResourceApi`, `createResourceHooks`, `resourceKeys`, `buildListParams`.
- `lib/api/flow.ts` — `useResourceAction` (acciones de flujo genéricas), `useResourceSubList`.
- `components/form/entity-combobox.tsx` — select FK server-side con búsqueda.
- `components/form/multi-entity-combobox.tsx` — select múltiple server-side.

## Refactors de backend aplicados al frontend

| Fecha | Cambio | Archivos front afectados |
|-------|--------|--------------------------|
| 2026-09-08 (mig 0046-0050, cross-app) | **PK textual en `ipress` y `ubigeo`; rename tabla `categoria`→`tipo_categoria`.** `Ipress` PK `id`→`codigo_renipress` (str8); `Ubigeo` PK `id`→`codigo` (str6). Las 7 FK a ipress + las 7 a ubigeo + `user-entity-profiles.id_objeto` (ipress) pasan a string. **Front (Fase B + ubigeo del spec `front-pk-string.md`, reusa la infra Fase 0):** `ipress` CRUD `pkField="codigo_renipress"`; todos los selects `ipress`/`ipress_origen`/`ipress_destino` (`clinical-fields`, `activity-fields`, `internship-fields`, `flow-actions`, `persons`, `determinacion-view`, `dashboard-filters`) con `valueKey/optionsValueKey="codigo_renipress"`+`optionsSearchable`; todos los selects `ubigeo` (catalogos/convenios/persons) con `valueKey="codigo"`; dashboard `entidad` filter → `string`. `0050` renombra la tabla `categoria` (Category) → `tipo_categoria` (sin impacto de contrato/front). `gen:api` regenerado. Backend specs: `renads-api/spec/convenios_ipress_pk_renipress.md`, `convenios_ubigeo_pk_codigo.md`. | `lib/convenios/{entities,clinical-fields}.ts`, `lib/actividades/activity-fields.ts`, `lib/internados/{internship-fields,flow-actions,persons}.ts`, `lib/catalogos/entities.ts`, `components/campos-clinicos/determinacion-view.tsx`, `components/dashboard/dashboard-filters.tsx`, `lib/dashboard/{types,use-dashboard-filters}.ts`, `docs/api-catalogos.md`, `lib/api/schema.d.ts`, `spec/front-pk-string.md`, `CLAUDE.md` |
| 2026-09-08 (mig 0043-0045 convenios) | **`executing-units` PK textual `codigo` + `ambito_geografico_sanitario`; infra CRUD para PK string.** `ExecutingUnit` PK `id`→`codigo` (str4); fuera `tipo_organo`/`gobierno_regional`/`direccion`/`ubigeo`/logo; entra FK `ambito_geografico_sanitario`(+detalle). `health-geographic-scopes` gana `gobierno_regional`(+detalle; nulo para DIRIS Lima). **Infra front generalizada a PK `string|number`:** `ResourceConfig.pkField`, `createResourceApi`/`hooks` con id `string|number`, `EntityCombobox`/`MultiEntityCombobox` genéricos `<T=number>` + prop `valueKey`, `FieldConfig`/`FilterConfig` con `optionsValueKey`+`optionsSearchable` (EntityCombobox de búsqueda para FK textual). Selects `unidad_ejecutora` (ipress/convenio/representantes/user-profiles) emiten `codigo` string. **`ipress` PK string (0046+) GATED**: la migración backend falló (`foreign key mismatch - interno referencing ipress`); Fase B del front en espera. `gen:api` diferido hasta desbloquear B. Spec: `spec/front-pk-string.md`. | `lib/api/query.ts`, `lib/crud/{types,hooks}.ts`, `components/crud/{resource-crud,resource-form,resource-filters}.tsx`, `components/form/{entity-combobox,multi-entity-combobox}.tsx`, `lib/convenios/{entities,convention-fields}.ts`, `components/convenios/convenio-create-form.tsx`, `app/(app)/catalogos/entidades/[entidad]/page.tsx`, `app/(app)/catalogos/representantes/page.tsx`, `lib/usuarios/entity-endpoints.ts`, `components/usuarios/assign-profiles-dialog.tsx`, `lib/catalogos/catalogs.ts`, `lib/api/storage.ts`, `docs/api-catalogos.md`, `spec/front-pk-string.md`, `CLAUDE.md` |
| 2026-09-07 (mig 0042 convenios) | **`executive-positions` (cargo) recupera FK `organo`→Organ (obligatoria) + coherencia.** `ExecutivePosition` gana `organo` (req) además de `organo_directivo`; RN `organo == organo_directivo.organo` cuando `organo_directivo` no es nulo (validada en serializer → 400). Read expone `organo_detalle`; filtro `organo`. **Front:** el form del cargo elige primero **Órgano** (`organs`, campo real enviado) y luego **Órgano del directorio** filtrado en cascada por `?organo=<id>` (`resetsOn`); columna/filtro `organo` añadidos. Backend spec: `renads-api/spec/convenios_cargo_organo.md`. | `renads-api/apps/convenios/{models,views}.py`, `renads-api/apps/convenios/migrations/0042_*`, `lib/catalogos/catalogs.ts`, `docs/api-catalogos.md`, `lib/api/schema.d.ts`, `CLAUDE.md` |
| 2026-09-07 (mig 0041 convenios) | **`gobierno_regional` trasladado de `OrganDirectory` → `Convention`.** `OrganDirectory` pierde `gobierno_regional` (unicidad colapsa a `(organo, nombre)`; endpoint ya no filtra/expone GORE). `Convention` gana FK `gobierno_regional` (nullable, solo Marco regional; la adenda lo hereda del origen); read expone `gobierno_regional`+`gobierno_regional_detalle {id,nombre,sigla}`; write lo acepta. PDF `_domicilio_entidad` GORE lee `convenio.gobierno_regional`. **Front:** quitado `gobierno_regional` de la config de `organ-directories` (columna/filtro/campo); añadido a `CONVENTION_FIELDS`/create-form/editar/detalle. `ExecutingUnit.gobierno_regional` **intacto**. Backend spec: `renads-api/spec/convenios_organo_directorio_gore.md`. | `renads-api/apps/convenios/{models,views,serializers,services,pdf}.py`, `renads-api/apps/convenios/migrations/0041_*`, `lib/convenios/entities.ts`, `lib/convenios/convention-fields.ts`, `components/convenios/convenio-create-form.tsx`, `app/(app)/convenios/[id]/{page,editar/page}.tsx`, `docs/api-catalogos.md`, `docs/api-convenios.md`, `lib/api/schema.d.ts`, `CLAUDE.md` |
| 2026-09-07 (mig 0039/0040 convenios) | **`organ-directories`: `categoria` (CharField) → FK `organo`→Organ; unicidad `(organo, gobierno_regional, nombre)`.** Reemplaza el discriminador de texto por FK id-based (data migration mapea por `Organ.nombre`). Dos constraints parciales: `uniq_organo_dir_organo_gore_nombre` (con GORE) + `uniq_organo_dir_organo_nombre_sin_gore` (GORE nulo); reemplaza `uniq_organo_directorio_por_gore` (0037). Un GORE puede tener varios órganos con nombre distinto. Serializer 400 en `nombre`. `_detalle_organo_directorio` clave `categoria`→`organo`. `pdf._seleccionar_plantilla` remapeado a `Organ.nombre`. `University.tipo_entidad`/`ExecutingUnit.tipo_organo` `limit_choices_to`→`organo__nombre`. **Front id puro (B2):** filtra `?organo=<id>` resolviendo el id vía `organs` en runtime (`lib/catalogos/organs.ts`: `useOrgans`/`organIdByNombre`/`ORGAN_NOMBRE`); la página de entidades inyecta `optionsParams:{organo:<id>}` en University/UE; `representantes-entities` usa `organoNombre` marker. Spec: `spec/organo-directorio.md`. | `renads-api/apps/convenios/{models,views,pdf}.py`, `renads-api/apps/convenios/migrations/0039_*,0040_*`, `lib/catalogos/organs.ts`, `lib/convenios/entities.ts`, `lib/catalogos/representantes-entities.ts`, `app/(app)/catalogos/entidades/[entidad]/page.tsx`, `app/(app)/catalogos/representantes/page.tsx`, `docs/api-catalogos.md`, `lib/api/schema.d.ts`, `spec/organo-directorio.md`, `CLAUDE.md` |
| 2026-09-07 (mig 0038 convenios) | **Representantes multi-entidad (polimórfico).** `OrganRepresentative` (+`OrganRepresentativeHistory`) reemplaza la FK `organo_directorio` por `tipo_contenido`+`id_objeto` (GenericFK `entidad`); enlaza a `OrganDirectory`/`University`/`ExecutingUnit`/`Conapres`/`Ipress` (5 modelos permitidos). Data migration puebla desde `organo_directorio`. Serializer expone `entidad_detalle {tipo,id,nombre}` + valida coherencia cargo↔entidad (D4) y ContentType permitido. Baja automática del anterior por par `(tipo_contenido,id_objeto,cargo)`. Nuevo endpoint `representante-content-types`. Cargos **globales** (`executive-positions?organo_directivo__isnull=true`) ∪ por órgano. Pantalla `/catalogos/representantes` rediseñada a 2 pasos (tipo → entidad). `ConventionParty` fuera de alcance (su coherencia actualizada al modelo genérico). Dead code `lib/catalogos/representatives.tsx` eliminado. Spec: `spec/representantes.md`. | `renads-api/apps/convenios/{models,serializers,services,views,urls}.py`, `renads-api/apps/convenios/migrations/0038_organrepresentative_polimorfico.py`, `app/(app)/catalogos/representantes/page.tsx`, `lib/catalogos/representantes-entities.ts`, `docs/api-catalogos.md`, `lib/api/schema.d.ts`, `spec/representantes.md`, `CLAUDE.md` |
| 2026-09-07 (mig 0037 convenios) | **`organ-directories` unicidad por gobierno regional.** `OrganDirectory` gana constraint parcial `uniq_organo_directorio_por_gore` (uno por `gobierno_regional` cuando no es nulo) + validación de serializer (HTTP 400 legible en alta/edición). Diagnóstico: la edición (PATCH `/organ-directories/{id}/`) nunca creó registros nuevos; la duplicación provenía de altas sin esta RN. La migración 0037 **fusiona duplicados existentes** (data migration: conserva el de menor id por GORE, repunta todas las FK inversas y borra el resto) antes del AddConstraint, en un solo `migrate`. Cambio solo backend; el front ya surface el 400 vía `extractApiError`. | `renads-api/apps/convenios/models.py`, `renads-api/apps/convenios/views.py`, `renads-api/apps/convenios/migrations/0037_organdirectory_uniq_por_gore.py`, `docs/api-catalogos.md`, `CLAUDE.md` |
| 2026-09-02 (mig 0025 convenios, 0019 internados) | **Adendas + partes tipadas + resolución CONAPRES.** `Convention` gana `convenio_origen` (self-FK), `es_adenda`, `nomenclatura` (read-only; DIGEP la asigna en `evaluacion-tecnica`), `unidad_ejecutora` (req. Específico), `facultad` (req. Específico). Nuevo `ConventionParty` + endpoint `conventions/{id}/parties`. Acción `conventions/{id}/adenda`. `ClinicalFieldRegistration` gana `numero_resolucion_conapres`/`fecha_resolucion_conapres`. **`conventions/{id}/campos-clinicos` ELIMINADO** → CRUD `clinical-field-registrations`. Formulario de convenio deja de usar `CascadingEntityField` (que usaba `organ-types` eliminado); ahora selects directos. `SimpleObjectTable` gana soporte `render`. | `lib/convenios/flow.ts`, `lib/convenios/flow-actions.ts`, `lib/convenios/convention-fields.ts`, `lib/convenios/clinical-fields.ts`, `components/convenios/convenio-create-form.tsx`, `app/(app)/convenios/page.tsx`, `app/(app)/convenios/[id]/page.tsx`, `app/(app)/convenios/[id]/editar/page.tsx`, `components/data/simple-object-table.tsx`, `docs/api-convenios.md`, `lib/api/schema.d.ts`, `CLAUDE.md` |
| 2026-09-01 (mig 0033→0034) | **`organ-directory-positions` creado y luego eliminado** en el mismo día. Migración 0034 reemplaza la tabla puente N:M por FK directa: `executive-positions` quitó FK `organo`→`Organ` y añadió FK `organo_directivo`→`OrganDirectory`; `unique_together (organo_directivo, nombre_masculino)`; `organo_directivo_detalle: {id, nombre, categoria}`. El form de `organ-representatives` ahora usa `executive-positions?organo_directivo=<id>`. `organ-directory-positions` **eliminado** del backend y del front (removida `DIRECTORY_POSITION_CONFIGS` y su menú). `organs` tiene **5** entradas canónicas. | `lib/catalogos/catalogs.ts`, `lib/catalogos/entities.ts`, `app/(app)/catalogos/representantes/page.tsx`, `docs/api-catalogos.md`, `lib/api/schema.d.ts`, `CLAUDE.md` |
| 2026-08-31 | `organ-types` endpoint eliminado del backend. `executive-positions` modelo cambiado: quitó `codigo`, `nombre` → `nombre_masculino` (req) + `nombre_femenino` (opt). `faculties` gana `referencia_logo` + `ubigeo` FK. `University.tipo_entidad` FK → `OrganDirectory?categoria=UNIVERSIDAD` (antes `OrganType`). | `lib/catalogos/catalogs.ts`, `lib/catalogos/entities.ts`, `lib/convenios/entities.ts`, `docs/api-catalogos.md` |
| 2026-08-30 | Nuevo endpoint `university-careers` (tabla puente universidad↔carrera); `universities` expone `tipo_gestion_detalle`/`tipo_entidad_detalle`/`tipo_autorizacion_detalle`; tipo `separator` en formularios declarativos; `CascadingEntityField` soporta `typeParams` | `lib/catalogos/entities.ts`, `lib/convenios/entities.ts`, `lib/crud/types.ts`, `components/crud/resource-form.tsx`, `components/convenios/cascading-entity-field.tsx`, `lib/api/schema.d.ts` |
| 2026-08-29 | `regional-organs`/`minsa-organs` → `organ-directories`; `regional-organ-types`/`minsa-organ-types`/`executing-unit-types` → `organ-types`; `organs` (tabla de categorías); `executive-positions` ahora writable con FK `organo`; `document-types`/`university-entity-types`/`university-authorities` eliminados; `representatives` → `organ-representatives`; `Convention.organo_regional` → `organo_directorio`; `TechnicalEvaluation.organo_minsa` → `organo_directorio`; `ExecutingUnit.organo_regional`/`tipo_unidad_ejecutora` → `organo_directorio`/`tipo_organo` | `lib/convenios/entities.ts`, `lib/catalogos/catalogs.ts`, `lib/catalogos/entities.ts`, `lib/convenios/convention-fields.ts`, `lib/convenios/flow-actions.ts`, `lib/convenios/solicitante.ts`, `lib/usuarios/entity-endpoints.ts`, `lib/api/storage.ts`, `components/convenios/convenio-create-form.tsx`, páginas de convenio |
| 2026-08-30 | `representatives` (polimórfico) → `organ-representatives` (FK directa a `organo_directorio`); ALTA habilitada; campos: `nombre`, `numero_documento_identidad`, `sexo`, `tipo_documento_identidad`, `fecha_inicio_designacion`, `numero_resolucion_designacion`, `fecha_inicio_facultades`, `cargo_ejecutivo`, `activo`; filtros: `organo_directorio`, `cargo_ejecutivo`, `activo`; sin `*_detalle` (serializer custom `__all__`) | `lib/catalogos/representatives.tsx`, `app/(app)/catalogos/representantes/page.tsx`, `docs/api-catalogos.md`, `docs/api-convenios.md` |
| 2026-08-30 | `university-careers` añade FK `facultad` requerida (RN-FC-02/03; `UniversityCareerSerializer` valida que facultad pertenezca a la universidad); `facultad_detalle` string detalle; filtro `facultad` nuevo; formulario con cascada `universidad`→`facultad` (`optionsParamsFrom`+`resetsOn`); bug: `detalleNombre()` usada en strings → corregida a `String()` | `lib/catalogos/entities.ts`, `lib/api/schema.d.ts` |
| 2026-08-30 | `organ-directories` cambia FK `organo`+`tipo_organo` por CharField `categoria` (choices enum); elimina `ubigeo`/`direccion`/`numero_ruc`/`correo`/`telefono_institucional`; sin logo. `executing-units.tipo_organo` FK → `OrganDirectory?categoria=UNIDAD_EJECUTORA`. `regional-governments` gana `sigla`, `ubigeo` (FK), `numero_ruc`, `direccion`, `correo`, `telefono`. Fix `detalleNombre()` → `String()` en `universities`/`executive-positions` columns. | `lib/convenios/entities.ts`, `lib/catalogos/catalogs.ts`, `docs/api-catalogos.md`, `lib/api/schema.d.ts` |
| 2026-08-30 | Campos de contacto movidos de `organ-directories` → `regional-governments` (migración backend 0027) | `lib/convenios/entities.ts`, `renads-api/apps/convenios/models.py`, `renads-api/apps/convenios/migrations/0027_*` |
| 2026-07 | DJ del interno movidas de `students` → `interns` (`annex-upload`/`annex-checklist`) | `lib/api/storage.ts`, `spec/almacenamiento.md`, `docs/api-almacenamiento.md` |

## Requerimientos pendientes al backend

| ID | Bloquea | Descripción |
|----|---------|-------------|
| REQ-BACK-02 | DELETE en catálogos/entidades referenciadas | Manejar `ProtectedError` → HTTP 409 (ya mitigado con `extractApiError` en el front). |
| REQ-BACK-03 | Tabla de facultades sin `universidad_detalle` | `FacultyViewSet` usa `_entity_viewset(m.Faculty)` sin kwarg `detalles`. La respuesta solo devuelve `universidad: number` (ID). Para mostrar el nombre de la universidad en la tabla de `/catalogos/entidades/faculties` se necesita agregar `detalles={"universidad": _detalle_nombre}` al viewset. |
