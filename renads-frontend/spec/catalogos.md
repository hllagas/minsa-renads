# Spec — Módulo Catálogos (`/catalogos`)

> **Estado: APROBADO (humano) — listo para Implement.** Las 5 preguntas se resolvieron en §5
> (campos exactos extraídos de `apps/convenios/models.py`). Flujo SDD: `spec` → **(APROBADO)** →
> `implement` → `validator`.
> Fuente de verdad del contrato: `docs/api-catalogos.md` (+ `docs/api-convenios.md`,
> `docs/api-auth.md`). **§5 (Resoluciones) es autoritativa y prevalece sobre el texto de las tareas
> donde haya diferencia.**

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
