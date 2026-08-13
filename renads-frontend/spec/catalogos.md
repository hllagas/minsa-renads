# Spec — Módulo Catálogos (`/catalogos`)

> **Estado: APROBADO (humano) — listo para Implement.** Las 5 preguntas se resolvieron en §5
> (campos exactos extraídos de `apps/convenios/models.py`). Flujo SDD: `spec` → **(APROBADO)** →
> `implement` → `validator`.
> Fuente de verdad del contrato: `docs/api-catalogos.md` (+ `docs/api-convenios.md`,
> `docs/api-auth.md`). **§5 (Resoluciones) es autoritativa y prevalece sobre el texto de las tareas
> donde haya diferencia.**
> ⚠️ **Pendiente:** aplicar la sección «Actualización de contrato 2 (2026-07-17)» (al final).

## 1. Resumen del módulo

`/catalogos` es el módulo transversal de **mantenimiento de tablas maestras** (Módulo 6 del MVP,
CRUD de soporte del Módulo 1 del backend). Cubre cuatro grupos de recursos:

1. **Entidades organizacionales / académicas (CRUD)** — alta/edición/baja, escritura solo
   `Administrador RENADS`.
2. **Representantes** (`representatives`) — CRUD polimórfico, escritura solo `Administrador RENADS`.
3. **Catálogos de solo lectura** (18 catálogos + `ubigeos`) — listado/consulta para visualización y
   como fuente de selects. **Su escritura está fuera de alcance** (ya poblados en backend).
4. **Documentos** (`documents`) — gestión documental polimórfica con versionado: listado/consulta +
   alta + baja + acción `url-descarga`. Lectura/escritura: miembro institucional autenticado.
5. **Bitácora de auditoría** (`audit-logs`) — vista de solo lectura con filtros, acceso
   `Administrador RENADS` / `Auditor`.

### Pantallas que cubre

- `/catalogos` — **índice** con tarjetas agrupadas por sección (Entidades, Representantes,
  Catálogos, Documentos, Auditoría).
- `/catalogos/entidades/[entidad]` — CRUD genérico de cada entidad organizacional/académica.
- `/catalogos/representantes` — CRUD de representantes.
- `/catalogos/listas/[catalogo]` — vista de solo lectura de cada catálogo / `ubigeos`.
- `/catalogos/documentos` — gestión documental.
- `/catalogos/auditoria` — bitácora de auditoría.

> Nota de rutas (aprobada): segmentos `entidades` / `listas` para no colisionar con
> `/convenios/maestros/[entidad]`. La estructura interna reutiliza `ResourceCrud` y `lib/crud/*`.

### Fuera de alcance (NO implementar en este spec)

- `/usuarios`: `user-entity-profiles`, grupos/roles (Módulo 7 del MVP, `docs/api-auth.md`). Solo se
  referencia como enlace externo si procede.
- **Alta/edición de catálogos de solo lectura** (los 18 + `ubigeos`): solo se listan/consultan.
- Endpoints `/stats/` y cualquier analítica (eso es Dashboard, ya hecho).
- Tests automatizados (no hay runner configurado; el módulo no los pide).

---

## 2. Dependencias y reutilización

- `components/crud/resource-crud.tsx` — CRUD declarativo (lista + búsqueda + diálogo alta/edición +
  borrado, gating de escritura por rol). **Se extiende** para soportar filtros declarativos (ver T2).
- `lib/crud/types.ts` (`ResourceConfig`, `FieldConfig`, `ColumnConfig`) y
  `lib/crud/hooks.ts` (`createResourceHooks`) — base CRUD + TanStack Query (keys + invalidación).
- `components/crud/resource-form.tsx` — formulario declarativo (text/number/boolean/date/email/select).
- `components/form/entity-combobox.tsx` — select FK con búsqueda server-side (para filtros FK y selects).
- `lib/api/query.ts` (`createResourceApi`, `resourceKeys`, `buildListParams`, `ListParams.filters`),
  `lib/api/lookup.ts`, `lib/api/client.ts` (Axios único + paginación DRF).
- Patrón `lib/convenios/entities.ts` + `app/(app)/convenios/maestros/*` — modelo a replicar para el
  índice y el CRUD por slug.
- `components/data/page-header.tsx`, `components/ui/data-table.tsx`,
  `components/data/data-table-pagination.tsx`, `components/ui/badge`, `card`, `dialog`, `button`.
- `lib/auth/store.ts` (`useAuthStore`, `userHasRole`) — gating por `me.grupos`.

> **Regla:** no reinventar CRUD/tablas/selects; extender la infraestructura existente. Axios solo en
> `lib/api/`, server-state solo con TanStack Query, Zustand solo cliente/UI, tablas vía `<DataTable>`.

---

## 3. Tareas

### A. Tipos / contrato

- [x] **T1 — Tipos TS de los recursos del módulo.**
  Definir/confirmar tipos de lectura (claves del API en español, sin traducir) para:
  entidades (`regional-governments`, `regional-organs`, `executing-units`, `ipress`, `minsa-organs`,
  `conapres`, `universities`, `university-authorities`, `faculties`, `professional-careers`,
  `university-campuses`), `representatives`, `documents` (campos de lectura del §4 de
  `docs/api-catalogos.md`), `audit-logs` (campos del §5) y un tipo genérico de catálogo
  (`{ id, codigo, nombre, activo, ... }`) + `ubigeo`
  (`{ id, codigo, departamento, provincia, distrito, activo }`).
  - **Preferencia:** generar de OpenAPI (`/api/v1/schema/`, `lib/api/schema.d.ts`) cuando exista el
    tipo; si se tipa a mano, usar las claves exactas de `docs/api-catalogos.md`.
  - **Criterio de aceptación:** los tipos compilan en TS strict, no traducen claves, y `documents` /
    `audit-logs` incluyen exactamente los campos read-only listados en el contrato (`version`,
    `estado`, `cargado_por`, `cargado_en`, etc. / `usuario_nombre`, `tipo_contenido_label`,
    `creado_en`, etc.).
  - **❓Pregunta de contrato:** los campos de escritura exactos de las entidades nuevas
    (`university-authorities`, `faculties`, `professional-careers`, `university-campuses`,
    `representatives`) no están enumerados en `docs/api-*.md` (el doc dice «`id` + todos los campos
    del modelo»). Confirmar contra OpenAPI/serializer antes de fijar `fields` (ver T7–T9).

### B. Infraestructura CRUD (extensión transversal — habilita filtros del backend)

- [x] **T2 — Filtros declarativos en `ResourceConfig` + `ResourceCrud`.**
  Hoy `ResourceCrud` solo aplica `search` (`useList({ page, search, ordering })`). El contrato exige
  exponer los `filterset_fields` reales de cada recurso. Extender:
  - `lib/crud/types.ts`: añadir a `ResourceConfig` un `filters?: FilterConfig[]`, con
    `FilterConfig = { name; label; type: "select" | "boolean" | "text"; optionsEndpoint?;
    optionsParams?; choices? }` (reutilizando la forma de `FieldConfig`).
  - `components/crud/resource-crud.tsx`: barra de filtros (shadcn `Select`/`EntityCombobox`/`Switch`)
    que alimenta `useList({ ..., filters })` vía `ListParams.filters` (ya soportado por
    `buildListParams`). Resetear `page` al cambiar filtros; permitir limpiar filtros.
  - `ordering`: permitir `config.defaultOrdering` (default `id`) sin romper el actual.
  - **Criterio de aceptación:** un recurso con `filters` muestra controles, y al seleccionar un valor
    se envía el query param correcto (p. ej. `?universidad=12&activo=true`) verificable en la pestaña
    de red; sin `filters` el componente se comporta igual que hoy (no regresión en `/convenios/maestros`).
  - **Dependencia:** previa a T7–T13.

- [x] **T3 — Modo de solo lectura explícito en `ResourceCrud`.**
  Para catálogos de solo lectura, soportar `config.readOnly?: boolean`. Cuando `readOnly` (o
  `writeRoles: []`), ocultar «Nuevo»/«Editar»/«Eliminar» y mostrar `Badge` «Solo lectura». (Hoy ya se
  logra con `writeRoles: []` ⇒ `canWrite=false`; formalizar con la flag para legibilidad y para no
  depender de un truco.)
  - **Criterio de aceptación:** una config con `readOnly: true` renderiza tabla + búsqueda + filtros +
    paginación, sin acciones de escritura ni diálogos, para cualquier rol (incluido Admin).

- [x] **T4 — Hooks de datos del módulo (TanStack Query).**
  Reutilizar `createResourceHooks(endpoint)` para todos los recursos estándar (entidades, catálogos,
  representantes). No crear hooks nuevos salvo para `documents` (T11) y `audit-logs` (T12). Verificar
  que las keys e invalidación de `resourceKeys` cubren list/detail/create/update/remove.
  - **Criterio de aceptación:** crear/editar/eliminar una entidad invalida y refresca su lista sin
    recarga; selects (`EntityCombobox`) que apuntan al recurso reflejan los cambios al reabrir.

### C. Configuración de recursos CRUD — Entidades organizacionales / académicas

> Endpoints, filtros y search **exactos** del §2 de `docs/api-catalogos.md`. Escritura solo
> `Administrador RENADS` (autoridad final: backend). Ordering default `id`. Reutilizar el patrón de
> `lib/convenios/entities.ts`; mover/centralizar las configs en `lib/catalogos/entities.ts`
> (reexportando o reaprovechando las ya definidas para `universities`, `ipress`,
> `regional-governments`, `executing-units`, `regional-organs`, `minsa-organs`, `conapres`).

- [x] **T5 — Centralizar registro de entidades en `lib/catalogos/entities.ts`.**
  Mapa `slug → ResourceConfig` + menú ordenado. Reutilizar las 7 configs ya existentes en
  `lib/convenios/entities.ts` (sin duplicar; importar o trasladar con cuidado de no romper
  `/convenios/maestros`).
  - **Criterio de aceptación:** un único origen de verdad para las configs de entidad; ambos índices
    (`/convenios/maestros` y `/catalogos`) consumen el mismo registro o uno deriva del otro sin duplicar.

- [x] **T6 — Añadir filtros a las 7 entidades ya configuradas.**
  Completar `filters` (según `filterset_fields` del contrato) en:
  - `regional-governments`: `region` (FK `regions`), `activo`. Search `nombre`.
  - `regional-organs`: `gobierno_regional` (FK), `tipo_organo_regional` (FK `regional-organ-types`),
    `activo`. Search `nombre`, `siglas`.
  - `executing-units`: `organo_regional` (FK), `tipo_unidad_ejecutora` (FK `executing-unit-types`),
    `activo`. Search `nombre`, `codigo`.
  - `ipress`: `unidad_ejecutora` (FK), `ambito_geografico_sanitario` (FK `health-geographic-scopes`),
    `activo`. Search `nombre`, `codigo_renipress`.
  - `minsa-organs`: `tipo_organo_minsa` (FK `minsa-organ-types`), `activo`. Search `nombre`, `siglas`.
  - `conapres`: `activo`. Search `nombre`.
  - `universities`: `tipo_gestion`, `tipo_entidad`, `tipo_autorizacion` (FK respectivos), `activo`.
    Search `nombre`, `siglas`.
  - **Criterio de aceptación:** cada filtro emite el query param exacto del contrato; el `activo` se
    envía como `true`/`false`; los FK usan `EntityCombobox` contra el catálogo correcto.

- [x] **T7 — Config `university-authorities`.**
  Endpoint `university-authorities`. Filtros: `universidad` (FK `universities`), `activo`.
  Search `nombre`, `cargo`. Columnas sugeridas: `nombre`, `cargo`, `universidad` (etiqueta), `activo`.
  Campos de escritura: `universidad` (FK, requerido), `nombre`, `cargo`, `activo` (+ los demás del
  modelo según OpenAPI — **confirmar T1**).
  - **Criterio de aceptación:** lista/alta/edición/baja funcionan contra el endpoint real; filtro por
    universidad y búsqueda por `nombre`/`cargo` operan; escritura visible solo a `Administrador RENADS`.

- [x] **T8 — Config `faculties` y `professional-careers`.**
  - `faculties`: filtros `universidad` (FK), `activo`; search `nombre`. Campos: `nombre`,
    `universidad` (FK, requerido), `activo`.
  - `professional-careers`: filtros `facultad` (FK `faculties`), `nivel_academico`
    (FK `academic-levels`), `especialidad` (FK `specialties`), `activo`; search `nombre`.
    Campos: `nombre`, `facultad` (FK, requerido), `nivel_academico` (FK), `especialidad` (FK), `activo`.
  - **Criterio de aceptación:** ambos CRUD operan con sus filtros reales; los selects dependientes
    (carrera → facultad/nivel/especialidad) cargan de los catálogos correctos. Confirmar campos exactos
    de escritura vía OpenAPI (T1).

- [x] **T9 — Config `university-campuses`.**
  Endpoint `university-campuses`. Filtros: `universidad` (FK), `region` (FK `regions`), `activo`.
  Search `nombre`. Campos: `nombre`, `universidad` (FK, requerido), `region` (FK), `activo` (+ campos
  del modelo según OpenAPI — confirmar T1).
  - **Criterio de aceptación:** CRUD operativo con filtros por universidad/región y búsqueda por nombre.

### D. Representantes (`representatives`) — CRUD polimórfico

- [x] **T10 — CRUD de `representatives`.**
  Endpoint `representatives`. Filtros: `tipo_contenido`, `id_objeto`, `cargo_ejecutivo`
  (FK `executive-positions`), `activo`. Escritura solo `Administrador RENADS`.
  - El recurso es **polimórfico**: `tipo_contenido` (id de ContentType: órgano MINSA / órgano regional
    / unidad ejecutora / IPRESS / CONAPRES) + `id_objeto` (id de la entidad concreta). El select de
    `id_objeto` debe depender del `tipo_contenido` elegido (apuntar al endpoint de entidad correcto).
  - Columnas: identificación del representante, `tipo_contenido_label`/entidad, `cargo_ejecutivo`,
    `activo`.
  - **Criterio de aceptación:** se puede crear un representante eligiendo tipo de entidad y luego el
    objeto concreto; el filtro por `tipo_contenido` + `id_objeto` funciona; campos de escritura
    confirmados vía OpenAPI.
  - **❓Pregunta de contrato:** (1) ¿qué valores admite `tipo_contenido` y cómo se obtiene el id de
    ContentType y su etiqueta (¿endpoint de content-types?)? (2) campos exactos de la persona
    representante (nombre, documento, cargo, correo, fechas). `docs/api-catalogos.md` §3 no los
    enumera. **Bloqueante para fijar `fields`; resolver antes de Implement.** Si no hay endpoint de
    content-types, definir un mapa estático `tipo_contenido → { id, label, endpointObjeto }` aprobado
    por backend.

### E. Catálogos de solo lectura + Ubigeos

- [x] **T11 — Configs de los 18 catálogos (solo lectura).**
  Registrar en `lib/catalogos/catalogs.ts` un mapa `slug → ResourceConfig` con `readOnly: true` para:
  `regions`, `health-geographic-scopes`, `convention-types`, `convention-statuses`, `document-types`,
  `university-management-types`, `university-entity-types`, `authorization-types`, `academic-levels`,
  `specialties`, `signing-authority-types`, `regional-organ-types`, `executing-unit-types`,
  `minsa-organ-types`, `executive-positions`, `observation-reasons`, `rejection-reasons`,
  `closure-reasons`.
  - Columnas comunes: `codigo`, `nombre`, `activo`. Filtro: `activo`. Search: `codigo`/`nombre`.
    Ordering default `id`.
  - **Criterio de aceptación:** cada catálogo se lista/consulta en solo lectura (sin botones de
    escritura para ningún rol), con búsqueda y filtro `activo`; ningún catálogo expone alta/edición/baja.

- [x] **T12 — Vista de `ubigeos` (solo lectura).**
  Endpoint `ubigeos`. Filtros: `departamento`, `provincia`, `distrito`, `activo`. Search: `codigo`,
  `distrito`, `provincia`, `departamento`. Columnas: `codigo`, `departamento`, `provincia`,
  `distrito`, `activo`. `readOnly: true`.
  - **Criterio de aceptación:** lista paginada de ubigeos con filtros por nivel geográfico y búsqueda;
    sin escritura. Manejar el volumen vía paginación del backend (no traer todo).

### F. Documentos (`documents`)

- [x] **T13 — API layer + hooks de `documents`.**
  En `lib/api/` (Axios) + hook TanStack Query:
  - `GET /documents/` (lista, filtros `tipo_contenido`, `id_objeto`, `tipo_documento`, `estado`).
  - `GET /documents/{id}/` (detalle).
  - `POST /documents/` (alta) con cuerpo exacto: `tipo_contenido`, `id_objeto`, `tipo_documento`,
    `nombre_archivo`, `referencia_externa` (§4 del contrato). `version`/`estado`/`version_anterior`
    los fija el backend — **no enviarlos**.
  - `DELETE /documents/{id}/`.
  - `GET /documents/{id}/url-descarga/` → `{ url }` (acción; no cachear como query persistente —
    usar `mutation`/fetch puntual y abrir/copy del enlace).
  - **Criterio de aceptación:** funciones aisladas en `lib/api/`, hooks con invalidación de la lista al
    crear/eliminar; el POST nunca envía campos read-only; `url-descarga` devuelve la URL y la UI la
    abre/copia.

- [x] **T14 — Pantalla `/catalogos/documentos`.**
  Tabla `<DataTable>` con columnas: `tipo_documento_nombre`, `nombre_archivo`,
  `tipo_contenido_label` + `id_objeto`, `version`, `estado`, `cargado_por`, `cargado_en`, y acciones
  (descargar via `url-descarga`; eliminar). Barra de filtros (`tipo_contenido`, `id_objeto`,
  `tipo_documento` (FK `document-types`), `estado`). Diálogo de alta con los 5 campos de escritura
  (incluye `tipo_documento` desde `document-types`).
  - Permisos: lectura/escritura para **miembro institucional autenticado** (no exclusivo de Admin).
  - **Criterio de aceptación:** se adjunta un documento por `referencia_externa` a un objeto existente,
    se lista con su versión/estado, se descarga (abre la URL firmada) y se elimina; los filtros del
    contrato funcionan. La validación de «objeto destino debe existir» se maneja mostrando el error del
    backend (`extractApiError`).
  - **❓Pregunta de UX:** cómo se elige `tipo_contenido`/`id_objeto` en el alta (igual que
    representantes T10: selector de tipo de entidad + combobox dependiente). Reutilizar la solución de
    T10.

### G. Bitácora de auditoría (`audit-logs`)

- [x] **T15 — API layer + hook de `audit-logs` (solo lectura).**
  `GET /audit-logs/` y `/audit-logs/{id}/`. Filtros: `usuario`, `accion`, `tipo_contenido`,
  `id_objeto`, y **rango de fechas** sobre `creado_en` (confirmar nombres de los params de rango,
  p. ej. `creado_en_after`/`creado_en_before` de django-filter — **❓pregunta de contrato**: el doc
  dice «rango de fechas» sin nombrar params). Search: `accion`. Ordering: `creado_en` desc (default),
  `id`. Sin create/update/delete.
  - **Criterio de aceptación:** hook de solo lectura paginado; envía exactamente los params de filtro
    soportados por el backend; no expone mutaciones.

- [x] **T16 — Pantalla `/catalogos/auditoria`.**
  Tabla `<DataTable>` (solo lectura) con columnas: `creado_en`, `usuario_nombre`, `accion`,
  `tipo_contenido_label` + `id_objeto`, `nombre_campo`, `valor_anterior` → `valor_nuevo`,
  `direccion_ip`. Barra de filtros: usuario, acción (search/select), entidad (`tipo_contenido`),
  objeto (`id_objeto`), rango de fechas (date pickers shadcn). Paginación del backend.
  - **Gating:** visible solo a `Administrador RENADS` / `Auditor`. Si el usuario no tiene rol,
    no mostrar la tarjeta en el índice ni permitir la ruta (redirigir/placeholder).
  - **Criterio de aceptación:** un Admin/Auditor consulta la bitácora con todos los filtros; un usuario
    sin rol no ve la sección; el orden por defecto es `creado_en` descendente.

### H. Páginas / rutas (App Router)

- [x] **T17 — Índice `/catalogos`.**
  Reemplazar el placeholder actual (`app/(app)/catalogos/page.tsx`) por un índice con tarjetas shadcn
  (`Card`) agrupadas por sección: **Entidades** (T5–T9), **Representantes** (T10), **Catálogos**
  (T11–T12), **Documentos** (T14), **Auditoría** (T16). Cada tarjeta enlaza a su ruta. Replicar el
  patrón de `app/(app)/convenios/maestros/page.tsx`.
  - **Gating por sección:** «Auditoría» solo para `Administrador RENADS`/`Auditor`; el resto visible a
    usuario autenticado; las acciones de escritura dentro de cada CRUD ya se gatean en `ResourceCrud`.
  - **Criterio de aceptación:** el índice muestra solo las secciones permitidas al rol; cada enlace
    navega a la pantalla correcta.

- [x] **T18 — Ruta dinámica de entidades `/catalogos/entidades/[entidad]`.**
  Página que resuelve `ResourceConfig` por slug desde `lib/catalogos/entities.ts` y renderiza
  `ResourceCrud`. Estado «entidad no encontrada» + enlace de regreso (patrón de
  `convenios/maestros/[entidad]/page.tsx`).
  - **Criterio de aceptación:** cada slug de entidad (T5–T9) abre su CRUD; slug inválido muestra el
    estado vacío sin romper.

- [x] **T19 — Ruta dinámica de catálogos `/catalogos/listas/[catalogo]`.**
  Análoga a T18 pero contra `lib/catalogos/catalogs.ts` (incluye `ubigeos`), siempre en `readOnly`.
  - **Criterio de aceptación:** cada slug de catálogo abre su vista de solo lectura.

- [x] **T20 — Rutas dedicadas:** `/catalogos/representantes` (T10), `/catalogos/documentos` (T14),
  `/catalogos/auditoria` (T16) como páginas propias.
  - **Criterio de aceptación:** las tres rutas existen, montan su componente y respetan el gating.

- [x] **T21 — Navegación.**
  Revisar `components/layout/app-shell.tsx`: el ítem `/catalogos` hoy está gateado solo a
  `["Administrador RENADS"]`. Como la lectura de catálogos/entidades/documentos es para miembro
  institucional autenticado y la bitácora suma `Auditor`, **decidir en aprobación** si se amplía el
  gating del menú (p. ej. añadir `Auditor`, o abrir el menú a autenticados y gatear por sección dentro
  del índice). El gating fino real vive en el índice (T17) y en `ResourceCrud`.
  - **Criterio de aceptación:** el ítem de menú aparece según la política aprobada; ningún usuario ve
    una sección que su rol no permite.

### I. Calidad / UX

- [x] **T22 — Estados de carga / error / vacío.**
  Reutilizar los de `ResourceCrud`/`DataTable` (loading, error con reintento, sin resultados). Para
  documentos y auditoría replicar los mismos patrones (toast con `extractApiError`, skeleton/loading,
  vacío).
  - **Criterio de aceptación:** ninguna pantalla queda en blanco; errores muestran mensaje + reintento;
    listas vacías muestran texto claro.

- [x] **T23 — Idioma y convenciones.**
  UI/labels/comentarios en español; código y claves del API en inglés/español del payload sin
  traducir. Sin `fetch`/Axios suelto en componentes (todo vía `lib/api/` + TanStack Query). Tablas solo
  vía `<DataTable>`. Sin estado de servidor en Zustand.
  - **Criterio de aceptación:** `npm run lint` y `npm run build` pasan; revisión confirma que no hay
    Axios fuera de `lib/api/` ni duplicación de server-state en Zustand.

- [x] **T24 — Verificación de gating UX.**
  Confirmar matriz: escritura de entidades/representantes solo `Administrador RENADS`; documentos
  lectura+escritura para autenticado; bitácora solo `Administrador RENADS`/`Auditor`; catálogos solo
  lectura para todos.
  - **Criterio de aceptación:** probar con un usuario no-Admin que solo ve lectura donde corresponde y
    que la bitácora no es accesible; recordar que el backend es la autoridad final (el gating es UX).

---

## 4. Matriz recurso → endpoint → permiso (referencia rápida del contrato)

| Recurso | Endpoint | Operaciones (front) | Escritura |
|---------|----------|---------------------|-----------|
| Entidades org./acad. (11) | ver §2 `docs/api-catalogos.md` | list/retrieve/create/update/delete | `Administrador RENADS` |
| Representantes | `representatives` | CRUD polimórfico | `Administrador RENADS` |
| Catálogos (18) | ver §1 `docs/api-catalogos.md` | list/retrieve | — (fuera de alcance) |
| Ubigeos | `ubigeos` | list/retrieve | — |
| Documentos | `documents` (+ `url-descarga`) | list/retrieve/create/delete + acción | miembro institucional autenticado |
| Bitácora | `audit-logs` | list/retrieve | — (solo lectura; `Admin`/`Auditor`) |

---

## 5. Resoluciones (APROBADO — autoritativo)

Campos verificados contra `D:\dev\renads\renads-api\apps\convenios\models.py`. Todos los FK se
editan con `EntityCombobox` apuntando al endpoint indicado; `activo` es boolean (default `true`).

### R1 — Campos de escritura exactos por recurso

> Nota: los campos `referencia_logo` / `referencia_documento_resolucion` son texto (referencia
> externa, sin subida de archivo). Fechas = `date`. `correo_institucional` = email.

- **regional-governments:** `nombre`*, `region`* (FK `regions`), `referencia_logo`, `activo`.
- **regional-organs:** `gobierno_regional`* (FK `regional-governments`), `tipo_organo_regional`*
  (FK `regional-organ-types`), `nombre`*, `siglas`, `direccion`, `ubigeo` (FK `ubigeos`, opcional),
  `referencia_logo`, `activo`.
- **executing-units:** `organo_regional`* (FK `regional-organs`), `tipo_unidad_ejecutora`*
  (FK `executing-unit-types`), `nombre`*, `codigo`, `direccion`, `ubigeo` (opc), `referencia_logo`, `activo`.
- **ipress:** `unidad_ejecutora`* (FK `executing-units`), `nombre`*, `codigo_renipress`, `direccion`,
  `ubigeo` (opc), `ambito_geografico_sanitario`* (FK `health-geographic-scopes`), `activo`.
- **minsa-organs:** `tipo_organo_minsa`* (FK `minsa-organ-types`), `nombre`*, `siglas`, `activo`.
- **conapres:** `nombre`*, `descripcion`, `activo`.
- **universities:** `nombre`*, `siglas`, `tipo_gestion`* (FK `university-management-types`),
  `tipo_entidad`* (FK `university-entity-types`), `tipo_autorizacion`* (FK `authorization-types`),
  `codigo_inei`, `fecha_constitucion` (date), `fecha_autorizacion` (date), `numero_resolucion`,
  `direccion_legal`, `telefono`, `correo_institucional` (email), `ubigeo` (opc), `referencia_logo`, `activo`.
- **university-authorities:** `universidad`* (FK `universities`), `nombre`*, `cargo`*,
  `fecha_inicio_cargo`* (date), `fecha_fin_cargo` (date), `numero_resolucion`,
  `referencia_documento_resolucion`, `activo`.
- **faculties:** `universidad`* (FK `universities`), `nombre`*, `activo`.
- **professional-careers:** `facultad`* (FK `faculties`), `nombre`*, `nivel_academico`*
  (FK `academic-levels`), `especialidad` (FK `specialties`, opcional), `activo`.
- **university-campuses:** `universidad`* (FK `universities`), `nombre`*, `direccion`,
  `region` (FK `regions`, opcional), `ubigeo` (opc), `activo`.
- **representatives:** `tipo_contenido`* (FK ContentType — ver R2), `id_objeto`* (id de la entidad),
  `nombre`*, `cargo_ejecutivo`* (FK `executive-positions`), `origen`
  (choices: `MINSA` | `GOBIERNO_REGIONAL` | `ASOCIACION_FACULTADES`, solo para CONAPRES),
  `fecha_inicio` (date), `fecha_fin` (date), `activo`.
  *(El representante NO tiene documento/correo: solo `nombre` + `cargo_ejecutivo` + `origen` + fechas.)*

(\* = requerido.)

### R2 — Polimorfismo (`representatives` y alta de `documents`): **NO hay endpoint de content-types**

Verificado: el backend **no expone** ningún endpoint de ContentType ni acepta natural-key; el PK de
`ContentType` es específico de la BD, así que el front **no puede** resolver `tipo_contenido` por sí
mismo. Resolución aprobada:

- **v1 (este spec):**
  - **representatives** → implementar **list + filtros + EDITAR (solo campos no polimórficos:
    `nombre`, `cargo_ejecutivo`, `origen`, `fecha_inicio`, `fecha_fin`, `activo`) + ELIMINAR**.
    El `tipo_contenido`/`id_objeto`/entidad se muestran **solo lectura** en la fila/diálogo. **El ALTA
    queda diferida** (necesita resolver `tipo_contenido`).
  - **documents** (T14) → implementar **list + filtros + `url-descarga` + ELIMINAR**. **El ALTA queda
    diferida** (necesita `tipo_contenido` + selección del objeto padre).
- **Requerimiento backend (Vía B, registrar en paralelo):** endpoint **solo lectura** `content-types`
  que devuelva `{ id, app_label, model, label }` para los tipos permitidos
  (representantes: `minsa-organ`, `regional-organ`, `executing-unit`, `ipress`, `conapres`;
  documentos: entidades adjuntables). Con eso, **v2** habilita el ALTA con selector de tipo + combobox
  dependiente de `id_objeto`.
- **Ajusta T10 y T14:** su criterio de «crear» pasa a **v2**; el resto (list/filtros/editar/eliminar/
  descargar) es v1.

### R3 — Filtros de `audit-logs` (T15/T16)

`AuditLogFilter` real (`apps/convenios/filters.py`):
- Exactos: `usuario`, `accion`, `tipo_contenido`, `id_objeto`.
- `accion_contiene` (icontains sobre `accion`).
- **Rango de fechas:** `creado_en_desde` y `creado_en_hasta` (DateTime, `gte`/`lte`).
- Search: `accion`. Ordering: `creado_en` (desc por defecto), `id`.

### R4 — Política de menú `/catalogos` (T21)

Ítem de nav `/catalogos` con `roles: ["Administrador RENADS", "Auditor"]`. Dentro del índice (T17):
sección **Auditoría** visible a Admin/Auditor; **entidades/representantes/catálogos/documentos**
visibles en el área (escritura de entidades/representantes solo Admin vía `canWrite` de `ResourceCrud`;
el Auditor las ve en solo lectura). Catálogos siempre solo lectura.

### R5 — Segmentos de ruta (aprobado)

`/catalogos` · `/catalogos/entidades/[entidad]` · `/catalogos/representantes` ·
`/catalogos/listas/[catalogo]` · `/catalogos/documentos` · `/catalogos/auditoria`.
(Se evita `/catalogos/catalogos`; sin colisión con `/convenios/maestros`.)

> **Aprobado para Implement.** El ALTA de representantes/documentos queda fuera de v1 (depende del
> endpoint `content-types`); registrar ese requerimiento al backend. Todo lo demás es v1.

---

## Actualización de contrato 2 (2026-07-17)

Segundo delta del backend (commit `fdd5770`). Fuente de verdad: `docs/api-catalogos.md` §2
(**ya sincronizado**) y `lib/api/schema.d.ts` (**ya regenerado**). Cambio: **`ipress`** gana el
booleano **`es_sede_docente`** (default `false`), el filtro homónimo y la acción
**`POST /ipress/{id}/autorizar-sede-docente/`** — body `{ "autorizar": true|false }` (default
`true`), **solo rol `CONAPRES`**; devuelve la IPRESS actualizada. `es_sede_docente=true` es
requisito para que la IPRESS pueda usarse en campos clínicos de convenios (regla cubierta en
`spec/convenios.md`, «Actualización de contrato 2»).

- [x] **U1 Config `ipress` — columna + filtro.** `lib/convenios/entities.ts` (config compartida por
  `/catalogos/entidades/ipress` y `/convenios/maestros/ipress`):
  - Columna nueva «Sede docente» con render Sí/No sobre `es_sede_docente` (mismo patrón `siNo` de
    `activo`).
  - Filtro nuevo `{ name: "es_sede_docente", label: "Sede docente", type: "boolean" }` junto a los
    existentes (`unidad_ejecutora`, `ambito_geografico_sanitario`, `activo`).
  - **Decisión (aprobar):** **NO** exponer `es_sede_docente` en los `fields` del formulario — la
    autorización/revocación se hace exclusivamente con la acción CONAPRES (U2), aunque el
    serializer lo admita nominalmente. Así la UI refleja el flujo de negocio del contrato.
  - **Criterio:** la columna y el filtro aparecen en ambos índices; el filtro emite
    `?es_sede_docente=true|false` (verificable en Network); alta/edición de IPRESS no envía
    `es_sede_docente`.
- [x] **U2 Acción «sede docente» (CONAPRES).** Nuevo
  `components/catalogos/ipress-sede-docente-action.tsx`: diálogo de confirmación (shadcn `Dialog` o
  `AlertDialog`) que llama `useResourceAction("ipress", row.id, "autorizar-sede-docente")` con body
  `{ autorizar }`:
  - Fila con `es_sede_docente: false` → acción «Autorizar sede docente» (`{ autorizar: true }`).
  - Fila con `es_sede_docente: true` → acción «Revocar sede docente» (`{ autorizar: false }`).
  - Al éxito: toast + invalidar **además** `resourceKeys.all("ipress")` (nota: `useResourceAction`
    solo invalida el detalle y las keys de flujo — la invalidación de la lista se añade en el
    `onSuccess` del `mutate` en el componente). Errores con `extractApiError`.
  - **Criterio:** el POST va a `/api/v1/ipress/{id}/autorizar-sede-docente/` con el body exacto;
    tras autorizar/revocar la tabla refresca y la columna «Sede docente» cambia; ambos sentidos
    funcionan.
- [x] **U3 Inyección de la acción por fila + navegación.**
  - `app/(app)/catalogos/entidades/[entidad]/page.tsx`: cuando `params.entidad === "ipress"` y
    `userHasRole(user, "CONAPRES")`, pasar `rowActions` (prop ya soportada por `ResourceCrud`) con
    la acción U2. Para el resto de slugs/roles no se pasa nada.
  - **Decisión (aprobar):** la acción vive **solo** en `/catalogos/entidades/ipress`;
    `/convenios/maestros/ipress` muestra columna/filtro (U1) pero no la acción.
  - **Decisión (aprobar):** `components/layout/app-shell.tsx` — añadir `"CONAPRES"` a los roles del
    ítem de menú `/catalogos` (política R4 ampliada: hoy `["Administrador RENADS", "Auditor"]`; sin
    esto un usuario CONAPRES no puede llegar a la acción por navegación). El índice `/catalogos`
    sigue gateando Auditoría a Admin/Auditor.
  - **Criterio:** un usuario `CONAPRES` ve el ítem `/catalogos`, entra a IPRESS y ve la acción por
    fila; un Admin/Auditor **no** ve la acción (solo CONAPRES); en otros slugs de entidad no
    aparece ninguna acción extra. El gating es UX; el backend (rol `CONAPRES`) es la autoridad.
- [x] **U4 Verificación.** `npx tsc --noEmit` y `npm run lint` limpios. Smoke: con rol CONAPRES
  autorizar y revocar una IPRESS (columna cambia, lista refresca); filtro `es_sede_docente` en
  ambos índices; con rol no-CONAPRES la acción no aparece.
  - **Criterio:** cero errores de TypeScript/ESLint; los flujos del smoke responden 2xx.

> **Aprobación humana requerida:** esta lista de tareas delta (U1–U4, con las 3 decisiones
> marcadas) debe ser aprobada antes de pasar al agente Implement.

---

## Actualización de contrato — Catálogos maestros con CRUD (2026-07-22)

Delta del backend (`docs/modulo_01_crud_transversales.md` §Catálogos maestros; `spec/convenios.md`
T8). Seis catálogos pasan de solo lectura a **CRUD** (escritura solo `Administrador RENADS` +
auditoría). Modelo base `Catalog`: `codigo` (único, obligatorio), `nombre` (obligatorio), `activo`.
Fuente de verdad: `lib/api/schema.d.ts` regenerado — confirma `*_create/update/partial_update/destroy`
para los seis basenames.

Basenames: `document-types`, `university-entity-types`, `authorization-types`, `academic-levels`,
`regional-organ-types`, `minsa-organ-types`.

- [x] **W1** `lib/catalogos/catalogs.ts`: nuevo helper `writableCatalog(endpoint, title, singular)`
  (columnas/búsqueda del catálogo estándar + `fields` `codigo`/`nombre`/`activo` y
  `writeRoles: ["Administrador RENADS"]`, sin `readOnly`). Los seis basenames pasan de
  `readOnlyCatalog(...)` a `writableCatalog(...)`; los 12 restantes no cambian.
  - **Criterio:** en `/catalogos/listas/<slug>` un `Administrador RENADS` ve «Nuevo»/editar/eliminar
    y persiste contra `/<slug>/`; otros roles siguen en solo lectura (canWrite = false).
- [x] **W2** Docs: `docs/api-catalogos.md` §1 dividido en 12 de solo lectura + §1.1 los seis CRUD.
- [x] **W3** Verificación: `npx tsc --noEmit` y `npm run lint` limpios.

> Sincronización directa de contrato ya mergeado en el backend; implementado en el mismo ciclo.

## Actualización de contrato — Categorías / Clasificaciones / Redes / Microrredes (2026-08-13)

> **Estado: APROBADO (humano) — 2026-08-13.** Lista N1–N11 aprobada para Implement. Las preguntas
> abiertas fueron resueltas por el humano (ver «Resoluciones humanas» abajo); la lista pasó de N1–N8 a
> **N1–N11** (se añadió infra de selects dependientes). Flujo SDD: `spec` → **(APROBADO)** →
> `implement` → `validator`.

> **Resoluciones humanas (2026-08-13):**
> 1. **Selects dependientes field→field: SÍ (opción (b)).** Se extiende la infraestructura de fields
>    para soportar cascada. En el alta de **microrred** se añade un selector **virtual** «Ámbito
>    geográfico sanitario» (no se envía al backend) que **filtra** el select de `red`. Tareas de infra:
>    **N9–N11**.
> 2. **Ubicación:** `networks`/`micro-networks` van en una **constante hermana
>    `SANITARY_ENTITY_CONFIGS`** en `lib/catalogos/entities.ts`, fusionada igual en
>    `CATALOGO_ENTITY_CONFIGS` (no dentro de `ACADEMIC_ENTITY_CONFIGS`).
> 3. **Copia de tarjetas «Catálogos»:** sin cambio (se mantiene el precedente W1); fuera de alcance.

### Contexto / contrato

Delta del backend ya documentado en **`docs/api-catalogos.md` §1.1 y §1.2**. Cuatro recursos nuevos
pasan a mantenerse desde la UI de `/catalogos`. **Escritura solo `Administrador RENADS`**
(`IsAdminRoleOrReadOnly`) + auditoría; **ordering** default `id`; **search** `codigo`/`nombre`.
Fuente de verdad de campos: `lib/api/schema.d.ts` (ya generado). **No traducir claves del API.**

| Recurso (endpoint) | Modelo (schema) | Naturaleza | Campos de **escritura** exactos | Filtros backend | Search |
|--------------------|-----------------|------------|----------------------------------|-----------------|--------|
| `categories` | `CategoryAuto` (base `Catalog`) | Catálogo maestro simple | `codigo` (req), `nombre` (req), `activo?` | `activo` | `codigo`, `nombre` |
| `classification-types` | `ClassificationTypeAuto` (base `Catalog`) | Catálogo maestro simple | `codigo` (req), `nombre` (req), `activo?` | `activo` | `codigo`, `nombre` |
| `networks` | `RedAuto` | Entidad CRUD con FK | `codigo` (req), `nombre` (req), `activo?`, `ambito_geografico_sanitario` (req, FK → `health-geographic-scopes`) | `ambito_geografico_sanitario`, `activo` | `codigo`, `nombre` |
| `micro-networks` | `MicroredAuto` | Entidad CRUD con FK | `codigo` (req), `nombre` (req), `activo?`, `red` (req, FK → `networks`) | `red`, `activo` | `codigo`, `nombre` |

> Jerarquía: `health-geographic-scopes` → `networks` → `micro-networks`.
> Verificado en `lib/api/schema.d.ts`: `RedAuto` = `{ id (ro), codigo, nombre, activo?,
> ambito_geografico_sanitario }`; `MicroredAuto` = `{ id (ro), codigo, nombre, activo?, red }`.
> `networks_list` acepta query `activo`, `ambito_geografico_sanitario`, `ordering`, `search`;
> `micro_networks_list` acepta `activo`, `red`, `ordering`, `search`. (Ambos usan el mismo schema
> para list/create/update; los `Patched*` confirman los mismos campos opcionales para PATCH.)

### Decisiones de diseño (aprobar)

- **D1 — `categories` y `classification-types` como catálogos maestros simples.** Se registran con
  `writableCatalog(endpoint, title, singular)` en `lib/catalogos/catalogs.ts` (mismo patrón que los
  seis basenames de W1) y se listan bajo la sección **«Catálogos»** del índice (ruta
  `/catalogos/listas/<slug>`). Aunque las tarjetas de catálogos rotulan «Consulta (solo lectura)»,
  `ResourceCrud` ya muestra alta/edición/baja cuando el rol lo permite (precedente W1: los seis
  catálogos promovidos conviven con ese mismo rótulo). **No** se cambia la copia de las tarjetas en
  este delta (se registra como mejora menor en las preguntas abiertas).
- **D2 — `networks` y `micro-networks` como entidades CRUD con FK.** Se registran como configs en
  `lib/catalogos/entities.ts` (constante hermana **`SANITARY_ENTITY_CONFIGS`**, ver D4) usando
  `select` con `optionsEndpoint`, como `faculties` / `professional-careers` (FK vía `EntityCombobox`).
  Se listan bajo la sección **«Entidades»** (ruta `/catalogos/entidades/<slug>`). **Motivo:** tienen
  FK de jerarquía; el helper `writableCatalog` no soporta campos FK.
- **D3 — Selects dependientes field→field: SÍ (opción (b), aprobado por el humano).** Se extiende la
  infra de fields (N9–N11). En el alta de **microrred**: campo **virtual** `_ambito` (select →
  `health-geographic-scopes`, **no** se envía en el POST) que filtra el select `red` mediante
  `?ambito_geografico_sanitario=<id>`; al cambiar `_ambito` se **resetea** `red`.
- **D4 — Ubicación en `lib/catalogos/entities.ts`: constante hermana `SANITARY_ENTITY_CONFIGS`**
  (redes/microrredes), fusionada en `CATALOGO_ENTITY_CONFIGS` junto a `ACADEMIC_ENTITY_CONFIGS`.

### Tareas

- [x] **N1 Registrar `categories` como catálogo maestro CRUD.**
  - Archivo: `lib/catalogos/catalogs.ts`.
  - En `CATALOG_CONFIGS` añadir
    `categories: writableCatalog("categories", "Categorías", "categoría")`.
  - **Criterio:** `/catalogos/listas/categories` lista `codigo`/`nombre`/`activo`, filtro `activo`,
    búsqueda por `codigo`/`nombre`; un `Administrador RENADS` ve «Nuevo»/editar/eliminar; el alta
    hace `POST /api/v1/categories/` con body `{ codigo, nombre, activo }` (claves sin traducir);
    otro rol lo ve en solo lectura (`canWrite = false`). Aparece en `CATALOG_MENU` (se deriva de
    `CATALOG_CONFIGS`, sin edición manual del menú).

- [x] **N2 Registrar `classification-types` como catálogo maestro CRUD.**
  - Archivo: `lib/catalogos/catalogs.ts`.
  - En `CATALOG_CONFIGS` añadir
    `"classification-types": writableCatalog("classification-types", "Tipos de clasificación", "tipo de clasificación")`.
  - **Criterio:** idéntico a N1 sobre `/catalogos/listas/classification-types`; el alta hace
    `POST /api/v1/classification-types/` con `{ codigo, nombre, activo }`.

- [x] **N3 Config CRUD de `networks` (Redes) con FK a ámbito geográfico sanitario.**
  - Archivo: `lib/catalogos/entities.ts` — nueva constante `SANITARY_ENTITY_CONFIGS` (fusionada en
    `CATALOGO_ENTITY_CONFIGS`).
  - `endpoint: "networks"`, `title: "Redes"`, `singular: "red"`,
    `searchPlaceholder: "Buscar por código o nombre…"`.
  - **Columns:** `codigo`, `nombre`, `activo` (render `Sí/No`).
  - **Filters:** `{ name: "ambito_geografico_sanitario", label: "Ámbito geográfico sanitario",
    type: "select", optionsEndpoint: "health-geographic-scopes" }` + `activoFilter`.
  - **Fields (orden):** `codigo` (text, req), `nombre` (text, req),
    `ambito_geografico_sanitario` (select, req, `optionsEndpoint: "health-geographic-scopes"`),
    `activo` (boolean, `defaultValue: true`). Escritura solo `Administrador RENADS` (default de
    `ResourceCrud`; no fijar `writeRoles` salvo para explicitarlo).
  - **Criterio:** `/catalogos/entidades/networks` lista/filtra; el filtro por ámbito emite
    `?ambito_geografico_sanitario=<id>&activo=true`; el alta hace `POST /api/v1/networks/` con body
    `{ codigo, nombre, ambito_geografico_sanitario, activo }` (FK como número, claves sin traducir);
    la edición precarga el ámbito seleccionado (`EntityCombobox` resuelve la etiqueta por id).

- [x] **N4 Config CRUD de `micro-networks` (Microrredes) con FK a red + cascada por ámbito.**
  - Archivo: `lib/catalogos/entities.ts` (`SANITARY_ENTITY_CONFIGS`). **Depende de N9–N11.**
  - `endpoint: "micro-networks"`, `title: "Microrredes"`, `singular: "microrred"`,
    `searchPlaceholder: "Buscar por código o nombre…"`.
  - **Columns:** `codigo`, `nombre`, `activo` (render `Sí/No`).
  - **Filters (lista):** `{ name: "red", label: "Red", type: "select", optionsEndpoint: "networks" }`
    + `activoFilter`. (El filtro de lista queda plano; la cascada es solo del **formulario**.)
  - **Fields (orden):**
    - `_ambito` — **virtual** (`virtual: true`, no se envía en el payload): select, `optionsEndpoint:
      "health-geographic-scopes"`, label «Ámbito geográfico sanitario». No `required` en el envío
      (es UI), pero se pide primero por UX.
    - `red` — select, req, `optionsEndpoint: "networks"`,
      `optionsParamsFrom: (v) => v._ambito ? { ambito_geografico_sanitario: String(v._ambito) } : {}`,
      `resetsOn: ["_ambito"]` (se limpia al cambiar el ámbito).
    - `codigo` (text, req), `nombre` (text, req), `activo` (boolean, `defaultValue: true`).
  - **Criterio:** al elegir un ámbito, el select `red` solo muestra redes de ese ámbito (petición
    `GET /networks/?ambito_geografico_sanitario=<id>&search=…`); cambiar el ámbito **resetea** `red`;
    el alta hace `POST /api/v1/micro-networks/` con body **`{ codigo, nombre, red, activo }`**
    (SIN `_ambito`; FK como número, claves sin traducir). En **edición**, `red` precarga su etiqueta
    (`EntityCombobox` por id) aunque `_ambito` arranque vacío (no bloquea el guardado). El filtro de
    lista por red emite `?red=<id>&activo=true`.

- [x] **N5 Añadir Redes y Microrredes al menú de entidades.**
  - Archivo: `lib/catalogos/entities.ts` (`CATALOGO_ENTITY_MENU`; las configs viven en
    `SANITARY_ENTITY_CONFIGS`).
  - Añadir, en orden coherente con la jerarquía (tras IPRESS / bloque sanitario):
    `{ slug: "networks", title: "Redes" }` y `{ slug: "micro-networks", title: "Microrredes" }`.
  - **Criterio:** el índice `/catalogos` muestra tarjetas «Redes» y «Microrredes» en la sección
    **Entidades**, enlazando a `/catalogos/entidades/networks` y `/catalogos/entidades/micro-networks`.
  - **Nota:** `categories`/`classification-types` NO se añaden aquí; aparecen en la sección
    «Catálogos» vía `CATALOG_MENU` (derivado de `CATALOG_CONFIGS` en N1/N2).

- [x] **N6 Verificar resolución de slug en las páginas dinámicas (sin cambios de código esperados).**
  - Archivos: `app/(app)/catalogos/entidades/[entidad]/page.tsx`,
    `app/(app)/catalogos/listas/[catalogo]/page.tsx`.
  - Confirmar que `networks`/`micro-networks` resuelven contra `CATALOGO_ENTITY_CONFIGS` y
    `categories`/`classification-types` contra `CATALOG_CONFIGS`, sin ramas especiales.
  - **Criterio:** navegar a los 4 slugs no muestra «Entidad/Catálogo no encontrado»; `ResourceCrud`
    monta la config correcta. No se esperan `rowActions` extra (ninguno de los 4 usa logo/anexos/
    acción CONAPRES; los condicionales de la página no aplican).

- [x] **N7 Docs: reflejar «config de front implementada».**
  - Archivo: `docs/api-catalogos.md`.
  - Ajustar la nota final de §1.2 (hoy dice «Aún sin config de front … pendiente SDD») para indicar
    que `networks`/`micro-networks` ya tienen config en `lib/catalogos/entities.ts` y que
    `categories`/`classification-types` están en `lib/catalogos/catalogs.ts` (§1.1).
  - **Criterio:** la doc no contradice el estado del front tras N1–N5.

#### Infra de selects dependientes (prerequisito de N4; aprobado opción (b))

- [x] **N9 Extender `FieldConfig` con soporte de campo virtual y params dependientes.**
  - Archivo: `lib/crud/types.ts`.
  - Añadir a `FieldConfig` (todos opcionales, retrocompatibles):
    - `virtual?: boolean` — el campo se renderiza y valida en el form pero **se excluye del payload**
      enviado al backend.
    - `optionsParamsFrom?: (values: Record<string, unknown>) => Record<string, string>` — calcula los
      `optionsParams` del select a partir de los valores en vivo del formulario. Tiene prioridad sobre
      `optionsParams` estático si ambos existen.
    - `resetsOn?: string[]` — nombres de campos padre; al cambiar cualquiera, este campo se resetea a
      su valor vacío.
  - **Criterio:** compila; los campos existentes (sin estas props) no cambian de comportamiento.

- [x] **N10 Consumir params dependientes + reset en el formulario declarativo.**
  - Archivo: `components/crud/resource-form.tsx`.
  - En el render del select (`SelectFieldRow`/equivalente): si `field.optionsParamsFrom` existe, usar
    `useWatch({ control })` para obtener los valores y pasar el resultado como `params`/`optionsParams`
    a `EntityCombobox` (recalcula al cambiar el padre).
  - Implementar `resetsOn`: al detectar cambio en un campo padre listado, `setValue(field.name,
    <vacío>)` (efecto con `useWatch` de los padres). Evitar bucles (solo resetear si el valor actual
    ya no es válido / cuando el padre cambia de verdad).
  - **Criterio:** cambiar `_ambito` limpia `red` y refresca sus opciones filtradas; sin `optionsParamsFrom`
    el comportamiento previo es idéntico (sin regresiones en otros formularios).

- [x] **N11 Excluir campos `virtual` del payload de envío.**
  - Archivo: `components/crud/resource-form.tsx` (y/o el punto donde se arma el `onSubmit`).
  - Al construir el body de create/update, **omitir** las claves cuyos `FieldConfig.virtual === true`.
  - **Criterio:** el POST/PATCH de microrred NO incluye `_ambito`; verificado en Network. Formularios
    sin campos virtuales envían exactamente lo mismo que antes.

- [x] **N8 Verificación final.**
  - Ejecutar `npx tsc --noEmit` y `npm run lint`.
  - **Criterio:** cero errores/warnings nuevos (solo los 2 preexistentes ajenos al módulo). Smoke
    manual (rol `Administrador RENADS`): alta/edición/baja de una categoría, un tipo de
    clasificación, una red (con ámbito) y una microrred; en el alta de microrred **verificar la
    cascada**: elegir ámbito → `red` se filtra (`GET /networks/?ambito_geografico_sanitario=<id>…`),
    cambiar ámbito resetea `red`, y el `POST /micro-networks/` **no** incluye `_ambito`. Verificar en
    Network los query params de filtro y los bodies de POST descritos en N1–N4; con un rol no-Admin
    los 4 recursos se ven en solo lectura.

### Punto abierto — Selects dependientes field→field (RESUELTO: opción (b), 2026-08-13)

> **RESUELTO por el humano:** se aprueba la **opción (b)** — extender la infraestructura de fields
> (tareas N9–N11) para la cascada ámbito→red en el alta de microrred. El análisis original se conserva
> abajo como justificación de diseño.

**Hallazgo (infra actual, verificado):** el formulario declarativo (`components/crud/resource-form.tsx`)
renderiza cada `FieldConfig` de forma aislada (`FieldRow`) y pasa `field.optionsParams` (un
`Record<string, string>` **estático**) directo a `EntityCombobox`. **No** existe hoy un mecanismo
para que el `optionsParams` de un campo dependa del **valor en vivo** de otro campo del mismo
formulario (no se lee el `watch`/`control` de react-hook-form para construir los params). Por tanto,
**el filtrado en cascada dentro del alta NO está soportado** sin extender la infraestructura.

Consecuencia para este delta: en el **alta de microrred** el select de `red` mostraría **todas** las
redes (no solo las de un ámbito), pero microrred solo tiene la FK directa `red` (no hay campo
«ámbito» en su formulario), así que no hay cascada real que perder. Para `networks`, su único FK es
`health-geographic-scopes` (tampoco encadena). El escenario de cascada solo aplicaría si se quisiera,
en el alta de microrred, **acotar `red` por un ámbito elegido primero** — algo no requerido por el
contrato.

**Decisión propuesta (D3): opción (a) — select plano sin dependencia en v1.** Es coherente con todas
las entidades FK ya existentes (`faculties.universidad`, `professional-careers.nivel_academico`,
`executing-units.organo_regional`, `regional-organs.gobierno_regional`, etc.), ninguna de las cuales
encadena selects. El backend valida la integridad (FK requerida) y el `EntityCombobox` tiene búsqueda
server-side, mitigando listas largas. **No se inventa infraestructura nueva.**

**Alternativa (b) — extender la infra de fields para dependencia** (solo si el humano lo aprueba
explícitamente): añadir a `FieldConfig` algo como
`optionsParamsFrom?: (values: FormValues) => Record<string, string>` y hacer que
`SelectFieldRow`/`MultiSelectFieldRow` usen `useWatch` para recalcular `params` y **resetear** el
valor del campo dependiente al cambiar el padre. Es un cambio transversal a `lib/crud/types.ts` +
`components/crud/resource-form.tsx` (+ posiblemente `entity-combobox.tsx`) y **debería ser su propio
ciclo SDD**, no colarse en este delta.

### Preguntas abiertas para la aprobación humana — RESUELTAS (2026-08-13)

1. **Cascada red↔ámbito en el alta de microrred:** → **(b) aprobada.** Cascada real vía infra N9–N11
   (dentro de este delta, no un ciclo aparte). Ámbito virtual filtra `red` y la resetea al cambiar.
2. **Copia de tarjetas de «Catálogos»:** → **sin cambio** (se mantiene el precedente W1).
3. **Ubicación de `networks`/`micro-networks`:** → **constante hermana `SANITARY_ENTITY_CONFIGS`**
   fusionada en `CATALOGO_ENTITY_CONFIGS`.

<!-- Redacción original de las preguntas (histórico):
1. ¿opción (a) select plano o (b) cascada? 2. ¿copia de tarjetas? 3. ¿ACADEMIC vs SANITARY?
(Cosmético;
   propuesta: constante hermana para no ampliar la semántica de «academic».)*
-->

> **Nota de infra (D3 aprobado):** la «Alternativa (b)» de arriba es ahora el plan vigente
> (tareas N9–N11). El texto de «opción (a)» se conserva solo como contexto de la decisión.
