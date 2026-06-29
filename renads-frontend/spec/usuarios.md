# Spec — Módulo Gestión de Usuarios (`/usuarios`)

> **Estado: APROBADO (humano) — listo para Implement.** Las 5 preguntas se resolvieron en §6
> (verificado contra `apps/common/{views,serializers}.py` y `apps/convenios` para `user-entity-profiles`).
> Flujo SDD: `spec` → **(APROBADO)** → `implement` → `validator`.
> Fuente de verdad del contrato: `docs/api-usuarios.md` (+ `docs/api-auth.md`, `docs/mvp.md` §7,
> `docs/frontend-conventions.md`). **§6 (Resoluciones) es autoritativa y prevalece sobre el texto de
> las tareas donde haya diferencia.**

---

## 1. Resumen del módulo

`/usuarios` es el módulo transversal de **administración de cuentas, roles/grupos, permisos y
perfiles institucionales** (Módulo 7 del MVP, `apps/common` del backend). Cubre cuatro recursos:

1. **Usuarios** (`users`) — CRUD; `DELETE` **desactiva** (`is_active=False`, no borra); acción
   **`set-password`** (cambio de contraseña en diálogo aparte). Campos de **alta ≠ edición**
   (el alta incluye `password` write-only; la edición no).
2. **Roles / Grupos** (`groups`) — CRUD; `name` + asignación **multi** de `permissions` (por ids).
3. **Permisos** (`permissions`) — **solo lectura** (catálogo de Django); alimenta el selector de
   permisos de un rol y una vista de consulta.
4. **Perfiles institucionales** (`user-entity-profiles`) — vínculo polimórfico usuario↔entidad para
   el alcance. **v1 parcial:** list + filtros + editar `activo` + eliminar. **Alta diferida**
   (depende de un endpoint `content-types` aún inexistente, ver §5/Fuera de alcance).

### Acceso (resumen; la autoridad final es el backend)

- **Usuarios / Roles / Permisos:** **solo superusuario** (`es_superusuario`). Es **más estricto**
  que `Administrador RENADS` (backend usa `IsSuperUser`).
- **Perfiles institucionales:** escritura `Administrador RENADS` (superusuario también pasa).

### Pantallas que cubre

- `/usuarios` — **índice** con tarjetas por sección, mostradas según permiso (ver §Gating).
- `/usuarios/cuentas` — CRUD de usuarios + acción de contraseña (superusuario).
- `/usuarios/roles` — CRUD de roles/grupos con selector multi de permisos (superusuario).
- `/usuarios/permisos` — consulta de permisos en solo lectura (superusuario).
- `/usuarios/perfiles` — perfiles institucionales: list + filtros + editar `activo` + eliminar
  (`Administrador RENADS` / superusuario).

> **Nota de rutas (a aprobar):** se usan slugs en español (`cuentas`/`roles`/`permisos`/`perfiles`)
> para no anidar `/usuarios/usuarios`. Páginas dedicadas (no `[slug]` dinámico) porque cada recurso
> tiene gating y comportamiento distinto (ver §A. Rutas/índice).

### Fuera de alcance / diferido (NO implementar en este spec)

- **Alta de perfiles institucionales** (`POST user-entity-profiles`): requiere resolver
  `tipo_contenido` (ContentType) vía un endpoint `content-types` **inexistente**. Queda **diferido**;
  registrar requerimiento al backend. En v1 la pantalla de perfiles usa `disableCreate`.
- **Borrado físico de usuarios**: el backend convierte `DELETE` en `is_active=False`; no existe borrado
  duro y no se implementa.
- Edición de contraseña dentro del formulario de edición de usuario (el contrato lo prohíbe: se usa
  solo la acción `set-password`).
- Tests automatizados (no hay runner configurado; el módulo no los pide).
- `/auth/me` (sesión) — ya cubierto por el módulo Auth; aquí solo se **lee** para gating.

---

## 2. Dependencias y reutilización

- `components/crud/resource-crud.tsx` — CRUD declarativo (lista + búsqueda + filtros + diálogo
  alta/edición + borrado, gating por rol). **Se extiende** (ver §B): `createFields`/`editFields`,
  `rowActions`, copy de borrado suave.
- `lib/crud/types.ts` (`ResourceConfig`, `FieldConfig`, `ColumnConfig`, `FilterConfig`),
  `lib/crud/hooks.ts` (`createResourceHooks`) — base CRUD + TanStack Query (keys + invalidación).
- `components/crud/resource-form.tsx` — formulario declarativo. **Se extiende** con los tipos de
  campo `password` y `multiselect` (ver §B).
- `components/crud/resource-filters.tsx` — barra de filtros declarativos (reutilizable tal cual).
- `components/form/entity-combobox.tsx` — select FK single con búsqueda server-side. **Se añade** un
  hermano **multi** (`MultiEntityCombobox`, ver §B/T6).
- `lib/api/query.ts` (`createResourceApi`, `resourceKeys`, `buildListParams`, `ListParams.filters`),
  `lib/api/lookup.ts` (`searchResource`/`getResourceItem`), `lib/api/client.ts` (Axios único +
  paginación DRF). **Acción `set-password` vive en `lib/api/`** (nunca Axios suelto en componentes).
- Patrón `lib/catalogos/*` + `app/(app)/catalogos/*` — modelo a replicar para índice + páginas.
- `lib/auth/store.ts` (`useAuthStore`, `userHasRole`, `AuthUser.es_superusuario`) — gating.
- `components/layout/app-shell.tsx` — `NAV_ITEMS` (ítem `/usuarios`, ver §Gating).
- `components/data/page-header.tsx`, `components/ui/{data-table,dialog,button,input,badge,card,label}`.

> **Regla:** no reinventar CRUD/tablas/selects. Extender la infraestructura. Axios solo en
> `lib/api/`; server-state solo con TanStack Query; Zustand solo cliente/UI; tablas vía `<DataTable>`;
> claves del API en español sin traducir; UI/comentarios en español, código en inglés.

---

## 3. Tareas

### A. Tipos / contrato

- [x] **T1 — Tipos TS de los recursos del módulo.**
  Definir tipos de lectura (claves del API en español/inglés exactas, sin traducir) en
  `lib/usuarios/types.ts` (o generados de OpenAPI `lib/api/schema.d.ts` si existen):
  - `User` (lectura): `id, username, email, first_name, last_name, is_active, is_staff,
    is_superuser, date_joined, last_login, groups (number[]), groups_detalle ({ id, name }[])`.
  - `UserCreatePayload`: `username, email, first_name, last_name, password (write-only),
    is_active, is_staff, is_superuser, groups (number[])`.
  - `UserUpdatePayload`: igual que create **sin** `password`.
  - `SetPasswordPayload`: `{ password: string }`.
  - `Group` (lectura/escritura): `id, name, permissions (number[]),
    permissions_detalle ({ id, name, codename, content_type, app_label, model }[])`.
  - `Permission` (lectura): `id, name, codename, content_type, app_label, model`.
  - `UserEntityProfile` (lectura): **campos por confirmar** (ver T16/❓Q1) — al menos `id`, `usuario`,
    `grupo`, `activo`, y la representación de la entidad polimórfica (`tipo_contenido`/`id_objeto`
    y/o etiqueta legible).
  - **Criterio de aceptación:** compila en TS strict; no traduce claves; los campos read-only y
    write-only coinciden exactamente con `docs/api-usuarios.md` §1–§3; `password` nunca aparece en
    tipos de lectura.
  - **Referencia:** `docs/api-usuarios.md` §1 (líneas 39–59), §2 (73–77), §3 (92–96).

### B. Infraestructura CRUD (multi-select FK · contraseña · alta≠edición · acción por fila)

> Justificación de diseño (decisión a aprobar): se **extiende `ResourceCrud`/`ResourceConfig`** en
> vez de construir pantallas dedicadas desde cero. La maquinaria (lista paginada, búsqueda, filtros,
> diálogo, borrado, invalidación, gating) es idéntica a la de catálogos/convenios; los deltas de
> usuarios (campos alta≠edición, una acción por fila, campos multi-FK y password) son **mejoras de
> infraestructura reutilizables** (también las usan roles). Una pantalla 100% dedicada duplicaría
> tabla/paginación/filtros (anti-DRY, viola SOLID). Las partes verdaderamente bespoke (diálogo de
> contraseña) se inyectan vía el prop `rowActions`, manteniendo `ResourceCrud` genérico.

- [x] **T2 — `FieldConfig`: nuevo tipo `password`.**
  Añadir `"password"` a `FieldType`; `resource-form` lo renderiza como `<Input type="password">`
  con `autoComplete="new-password"`.
  - **Criterio:** el valor **nunca** se imprime en consola/logs ni se incluye en payload si va vacío
    en edición; en alta es obligatorio si `required`. Sin almacenamiento en Zustand ni en cache.
  - **Dep.:** ninguna. **Usado por:** T9 (alta usuario), T13 (set-password).

- [x] **T3 — `FieldConfig`: nuevo tipo `multiselect` (FK multi por ids).**
  Añadir `"multiselect"` a `FieldType`. Reusa `optionsEndpoint`, `optionsParams`, `optionsToLabel`.
  El valor del campo es `number[]`.
  - **Criterio:** `resource-form` renderiza un `MultiEntityCombobox` (T6) para este tipo; el default
    es `[]`; `buildPayload` lo envía como array de ids (incluido `[]` para vaciar). No traduce claves.
  - **Dep.:** T6. **Usado por:** T9 (`groups` en usuario), T11 (`permissions` en rol).

- [x] **T4 — `ResourceConfig`: `createFields` vs `editFields`.**
  Añadir `createFields?: FieldConfig[]` y `editFields?: FieldConfig[]` (ambos opcionales; fallback a
  `fields`). `ResourceCrud` pasa a `ResourceForm` el set correcto según esté creando o editando.
  - **Criterio:** sin `createFields`/`editFields`, el comportamiento actual no cambia (catálogos
    intactos); con ellos, el alta usa `createFields` y la edición `editFields`.
  - **Dep.:** ninguna. **Usado por:** T9 (alta con `password`, edición sin `password`).

- [x] **T5 — `ResourceCrud`: prop `rowActions` (acciones por fila) + copy de borrado suave.**
  - Añadir prop **de componente** (no de data) `rowActions?: { key; label; variant?; render? ;
    onClick: (row: TRead) => void; visible?: (row) => boolean }[]`, renderizadas en la columna de
    acciones junto a Editar/Eliminar (solo si `canWrite`). El estado/diálogo de cada acción lo
    posee la página que monta `ResourceCrud` (ver T13).
  - Añadir a `ResourceConfig` overrides opcionales de copy de borrado: `deleteActionLabel`
    (p. ej. "Desactivar"), `deleteConfirmTitle`, `deleteConfirmDescription`, y un flag `softDelete`
    para el texto ("Esta acción desactiva el registro; podrá reactivarse." en vez de "no se puede
    deshacer").
  - **Criterio:** sin `rowActions`/overrides, comportamiento idéntico al actual. Para usuarios, el
    botón de borrado dice **"Desactivar"** y el toast de éxito dice "Usuario desactivado."
  - **Dep.:** ninguna. **Usado por:** T9/T13.

- [x] **T6 — `MultiEntityCombobox` (selector FK múltiple, server-side).**
  Nuevo `components/form/multi-entity-combobox.tsx`: búsqueda server-side (`searchResource`),
  selección múltiple, valor `number[]`, `onChange(number[])`, etiquetas resueltas para ids ya
  seleccionados aunque no estén en la página actual (`getResourceItem` por id), elementos
  seleccionados como **badges removibles**. Soporta `params` (p. ej. `content_type__app_label`).
  - **Criterio:** funciona para catálogos grandes (`permissions`) sin cargar todo; añade/quita ids;
    no duplica; accesible con teclado; reusa los helpers de `lib/api/lookup.ts` (Axios solo en
    `lib/api/`). No reinventa el `Combobox` base: lo envuelve o compone.
  - **Dep.:** ninguna. **Usado por:** T3, T9, T11.

- [x] **T7 — `buildPayload`/`defaultFor` soportan `multiselect` y `password`.**
  En `resource-form.tsx`: default `[]` para `multiselect`; enviar el array siempre (incluido vacío).
  Para `password`: en alta enviar si presente; en edición **omitir** (no debe existir como campo de
  edición de usuario). No imprimir el valor.
  - **Criterio:** payload de alta de usuario incluye `groups: number[]` y `password`; payload de
    edición incluye `groups` y **no** incluye `password`.
  - **Dep.:** T2, T3.

- [x] **T8 — Acción `set-password` en la capa API + hook.**
  En `lib/api/` (p. ej. `lib/usuarios/api.ts`): `setUserPassword(id: number, password: string)` →
  `POST /users/{id}/set-password/` con body `{ password }`. Hook `useSetPassword` (TanStack mutation)
  en `lib/usuarios/hooks.ts`; invalida `resourceKeys.all("users")` en éxito.
  - **Criterio:** Axios solo dentro de `lib/api/`/`lib/usuarios/`; el componente solo llama el hook;
    el `password` no se loguea; en éxito muestra toast "Contraseña actualizada."; en error usa
    `extractApiError`.
  - **Referencia:** `docs/api-usuarios.md` §1 (línea 34).

### C. Usuarios (`/usuarios/cuentas`)

- [x] **T9 — `ResourceConfig` de usuarios.**
  `lib/usuarios/configs.ts` → `usersConfig`:
  - `endpoint: "users"`, `writeRoles` = solo superusuario (ver T18), `defaultOrdering: "id"`,
    `searchPlaceholder: "Buscar por usuario, correo o nombre…"`, `softDelete: true`,
    `deleteActionLabel: "Desactivar"`.
  - **Columnas:** `username`, `email`, nombre (`first_name`+`last_name`), `is_active` (Sí/No),
    `is_superuser` (Sí/No), roles (de `groups_detalle.map(g => g.name)`), `last_login`.
  - **Filtros** (django-filter): `is_active` (boolean), `is_superuser` (boolean), `is_staff`
    (boolean), `groups` (select FK a `groups`, label `name`).
  - **`createFields`:** `username*`, `email*` (type `email`), `first_name`, `last_name`,
    `password*` (type `password`), `is_active` (boolean, default `true`), `is_staff` (boolean),
    `is_superuser` (boolean), `groups` (multiselect → endpoint `groups`).
  - **`editFields`:** igual **sin** `password`.
  - **Search:** `username`, `email`, `first_name`, `last_name` (lo maneja el backend).
  - **Criterio:** la tabla lista usuarios con filtros del backend; el alta crea con `password` y
    `groups`; la edición no envía `password`; "Desactivar" hace `DELETE` (→ `is_active=False`) y el
    registro sigue visible (filtrable por `is_active`).
  - **Referencia:** `docs/api-usuarios.md` §1 (filtros/search/ordering líneas 36–37; campos 39–57).

- [x] **T10 — Página `/usuarios/cuentas` con acción de contraseña.**
  `app/(app)/usuarios/cuentas/page.tsx` (client): guard superusuario (T18); monta
  `<ResourceCrud config={usersConfig} rowActions={[{ key:"set-password", label:"Contraseña",
  onClick: openSetPassword }]} />`. La página posee el **diálogo de contraseña** (T13).
  - **Criterio:** superusuario ve la tabla + botón "Contraseña" por fila; no-superusuario ve
    "No autorizado" + enlace a `/usuarios`; breadcrumb/volver a `/usuarios`.

- [x] **T13 — Diálogo de set-password.**
  Componente (en la página o `components/usuarios/set-password-dialog.tsx`): campos `password*` y
  `confirmar*` (ambos `type=password`), validación de coincidencia en cliente, llama `useSetPassword`
  (T8). Cierra y limpia al éxito.
  - **Criterio:** no permite enviar si no coinciden; nunca muestra/loguea el valor; éxito → toast
    "Contraseña actualizada." y diálogo cerrado; error → `extractApiError`. Política de fortaleza la
    valida el backend (no duplicar reglas; mostrar el error del backend si rechaza).
  - **Referencia:** `docs/api-usuarios.md` §1 (línea 34, 51).

### D. Roles / Grupos (`/usuarios/roles`)

- [x] **T11 — `ResourceConfig` de roles + página.**
  `lib/usuarios/configs.ts` → `groupsConfig`: `endpoint: "groups"`, `defaultOrdering: "name"`,
  `searchPlaceholder: "Buscar por nombre…"`, `writeRoles` = superusuario (T18).
  - **Columnas:** `name`, nº de permisos (`permissions_detalle.length`).
  - **`fields`** (alta = edición): `name*` (text), `permissions` (multiselect → endpoint
    `permissions`, label sugerida `\`${name} (${app_label}.${codename})\``, con filtro opcional
    `content_type__app_label` en el combobox).
  - **Search:** `name` (backend). **Sin filtros de listado** (el contrato solo expone search `name`).
  - Página `app/(app)/usuarios/roles/page.tsx` (client) con guard superusuario, monta `ResourceCrud`.
  - **Criterio:** crea/edita un rol asignando varios permisos por ids; `permissions_detalle` se usa
    solo para mostrar (read-only); el selector de permisos pagina/busca server-side.
  - **Referencia:** `docs/api-usuarios.md` §2 (líneas 65, 73–77).

### E. Permisos (`/usuarios/permisos`, solo lectura)

- [x] **T12 — `ResourceConfig` de permisos (read-only) + página.**
  `lib/usuarios/configs.ts` → `permissionsConfig`: `endpoint: "permissions"`, `readOnly: true`,
  `fields: []`, `searchPlaceholder: "Buscar por nombre o codename…"`,
  `defaultOrdering: "content_type"` (o `"id"` si DRF rechaza el compuesto — ver ❓Q3).
  - **Columnas:** `name`, `codename`, `app_label`, `model`.
  - **Filtros:** `content_type__app_label` (text), `content_type` (select FK a `content-types` **no
    disponible** → usar **text** por id, o omitir; ver ❓Q2). **Search:** `name`, `codename`.
  - Página `app/(app)/usuarios/permisos/page.tsx` (client) con guard superusuario.
  - **Criterio:** lista en solo lectura, sin acciones de escritura; filtra por `app_label` y busca por
    nombre/codename; sirve además de referencia para el selector de roles.
  - **Referencia:** `docs/api-usuarios.md` §3 (filtros/search/ordering líneas 89–90; campos 92–96).

### F. Perfiles institucionales (`/usuarios/perfiles`, v1 parcial)

- [x] **T16 — `ResourceConfig` de perfiles institucionales + página.**
  `lib/usuarios/configs.ts` → `userEntityProfilesConfig`: `endpoint: "user-entity-profiles"`,
  `disableCreate: true` (alta diferida), `writeRoles: ["Administrador RENADS"]`.
  - **Columnas:** usuario, grupo/rol, entidad (etiqueta de la relación polimórfica), `activo` (Sí/No).
    **Campos exactos por confirmar** (❓Q1).
  - **Filtros:** `usuario` (select FK → `users`, label `username`), `grupo` (select FK → `groups`,
    label `name`), `activo` (boolean).
  - **`editFields`:** solo `activo` (boolean). (No se edita el vínculo polimórfico en v1.)
  - Borrado: estándar (`DELETE`), copy normal.
  - Página `app/(app)/usuarios/perfiles/page.tsx` (client): guard `Administrador RENADS` o superusuario
    (T18); aviso visible "El alta de perfiles está deshabilitada temporalmente (pendiente endpoint
    `content-types` del backend)".
  - **Criterio:** lista con los 3 filtros; permite editar `activo` y eliminar; **no** muestra botón
    "Nuevo"; muestra el aviso de alta diferida.
  - **Referencia:** `docs/api-usuarios.md` §Perfiles institucionales (líneas 100–107).

### G. Rutas / índice

- [x] **T14 — Índice `/usuarios` con tarjetas por permiso.**
  Reescribir `app/(app)/usuarios/page.tsx` (hoy placeholder) siguiendo el patrón de
  `app/(app)/catalogos/page.tsx`: tarjetas `LinkCard` por sección. Registro de menú en
  `lib/usuarios/menu.ts`.
  - **Visibilidad de tarjetas:** Usuarios / Roles / Permisos → solo superusuario; Perfiles
    institucionales → superusuario **o** `Administrador RENADS`.
  - **Criterio:** un superusuario ve las 4 tarjetas; un `Administrador RENADS` no-superusuario ve solo
    "Perfiles institucionales"; un usuario sin ninguno no debería llegar aquí (gating de nav, T17) y,
    si llega por URL, ve "No autorizado".

- [x] **T15 — Páginas dedicadas + registro de configs.**
  Crear `lib/usuarios/configs.ts` (exporta `usersConfig`, `groupsConfig`, `permissionsConfig`,
  `userEntityProfilesConfig`) y las 4 páginas: `/usuarios/cuentas`, `/usuarios/roles`,
  `/usuarios/permisos`, `/usuarios/perfiles`. Cada página: enlace "← Usuarios", guard de acceso,
  `ResourceCrud` (o variante con `rowActions`).
  - **Criterio:** navegación coherente con catálogos; cada ruta resuelve su config; sin rutas muertas.

### H. Gating por rol / superusuario

- [x] **T17 — Gating del nav (`app-shell.tsx`).**
  El ítem `/usuarios` permanece visible para **superusuario** y `Administrador RENADS` (porque este
  último administra perfiles). Decisión: **no** restringir el nav a superusuario puro, ya que cortaría
  el acceso de `Administrador RENADS` a perfiles; la restricción estricta vive en las sub-rutas
  (T18). `userHasRole(user, "Administrador RENADS")` ya devuelve `true` para superusuario, por lo que
  el ítem actual `roles: ["Administrador RENADS"]` se mantiene.
  - **Criterio:** el menú "Gestión de Usuarios" aparece a superusuario y a `Administrador RENADS`;
    no aparece a otros roles.

- [x] **T18 — Helper de superusuario + guards de ruta.**
  Añadir helper `isSuperuser(user)` (`!!user?.es_superusuario`) en `lib/auth/store.ts`. Guard de
  ruta (componente reutilizable o check inline) que renderiza "No autorizado" + enlace a `/usuarios`
  cuando falla:
  - `/usuarios/cuentas`, `/usuarios/roles`, `/usuarios/permisos` → exigen **superusuario**.
  - `/usuarios/perfiles` → exige superusuario **o** `Administrador RENADS`.
  - En `usersConfig`/`groupsConfig`/`permissionsConfig`, `writeRoles` se define de modo que solo el
    superusuario tenga escritura (p. ej. `writeRoles: []` + guard superusuario, o un mecanismo
    equivalente; documentar la elección). Recordar: el gating del front es UX; el backend
    (`IsSuperUser`) es la autoridad.
  - **Criterio:** un `Administrador RENADS` no-superusuario que abra `/usuarios/cuentas` por URL ve
    "No autorizado"; un superusuario opera con normalidad; las acciones de escritura quedan ocultas a
    quien no es superusuario en usuarios/roles/permisos.

### I. Calidad / UX

- [x] **T19 — Manejo de errores y estados.**
  Reutilizar el manejo de `ResourceCrud` (error de listado con "Reintentar", toasts con
  `extractApiError`). Mensajes en español. `email` duplicado y validación de `password` se muestran
  con el error del backend.
  - **Criterio:** errores del backend (email único, password débil) se ven legibles; sin estados
    rotos al paginar/filtrar (`keepPreviousData`).

- [x] **T20 — Seguridad de contraseñas (transversal).**
  Verificar en toda la implementación: el `password` no se persiste en Zustand, no se cachea en
  Query, no se loguea, no se muestra en tablas/detalle, y los campos usan `type=password`.
  - **Criterio:** búsqueda en el diff no revela `console.log` de password ni el campo en tipos de
    lectura/tablas; los inputs son `type=password`.

- [x] **T21 — Lint/typecheck verdes.**
  `npm run lint` y build TS strict sin errores nuevos introducidos por el módulo.
  - **Criterio:** sin warnings/errores nuevos; tipos sin `any` salvo justificación puntual.

---

## 4. Mapa pantalla → endpoint (CRUD)

| Pantalla | Acción UI | Método/endpoint | Notas |
|----------|-----------|-----------------|-------|
| `/usuarios/cuentas` | listar | `GET /users/` | filtros `is_active`/`is_superuser`/`is_staff`/`groups`; search; ordering `id` |
| `/usuarios/cuentas` | crear | `POST /users/` | incluye `password`, `groups[]` |
| `/usuarios/cuentas` | editar | `PATCH /users/{id}/` | sin `password` |
| `/usuarios/cuentas` | desactivar | `DELETE /users/{id}/` | → `is_active=False` |
| `/usuarios/cuentas` | contraseña | `POST /users/{id}/set-password/` | body `{ password }` |
| `/usuarios/roles` | CRUD | `GET/POST/PATCH/DELETE /groups/…` | `permissions[]` por ids |
| `/usuarios/permisos` | listar | `GET /permissions/` | solo lectura; filtros `content_type__app_label` |
| `/usuarios/perfiles` | listar | `GET /user-entity-profiles/` | filtros `usuario`/`grupo`/`activo` |
| `/usuarios/perfiles` | editar `activo` | `PATCH /user-entity-profiles/{id}/` | solo `activo` |
| `/usuarios/perfiles` | eliminar | `DELETE /user-entity-profiles/{id}/` | — |
| `/usuarios/perfiles` | crear | — | **diferido** (falta `content-types`) |

---

## 5. Dependencias entre tareas

- T6 (MultiEntityCombobox) → bloquea T3, T9 (groups), T11 (permissions).
- T2 (password) + T4 (createFields/editFields) + T7 (buildPayload) → bloquean T9.
- T5 (rowActions) + T8 (set-password API) → bloquean T13 → bloquea T10.
- T18 (guards/superuser) → transversal a T10/T11/T12/T16; T14 depende de T18 para visibilidad de
  tarjetas.
- T1 (tipos) precede a todas las configs (T9/T11/T12/T16), pero puede afinarse al resolver ❓Q1.

---

## 6. Resoluciones (APROBADO — autoritativo)

Verificado contra `apps/common/{views,serializers}.py` y `apps/convenios` (para `user-entity-profiles`).

### R-Q1 — Campos de `user-entity-profiles` (perfiles)
El viewset es `_entity_viewset` con `ModelSerializer` `fields="__all__"`; el modelo `UserEntityProfile`
expone exactamente: **`id`, `usuario`** (FK User, id), **`tipo_contenido`** (FK ContentType, id),
**`id_objeto`** (entero), **`grupo`** (FK auth.Group, id), **`activo`** (boolean). **No hay etiquetas
ni `*_detalle`** — la lista devuelve ids crudos. Filtros reales: `usuario`, `grupo`, `activo`.
- v1: columnas `usuario`, `grupo`, `tipo_contenido`+`id_objeto`, `activo`; filtros `usuario`/`grupo`/
  `activo`; **editar solo `activo`**; eliminar; **alta diferida** (R-Q4). `tipo_contenido`/`id_objeto`/
  `usuario`/`grupo` se muestran solo lectura. (Como no hay endpoint de usuarios-por-label ni de
  content-types para selects amistosos, los filtros `usuario`/`grupo` usan **id**; opcionalmente
  `grupo` puede usar `EntityCombobox` contra `groups` —que sí existe— para elegir por nombre.)

### R-Q2 — Filtro de permisos
**No** exponer `content_type` (id) en la UI (no hay endpoint content-types). Usar **`content_type__app_label`
como filtro de texto** + `search` (`name`/`codename`). Los objetos `permission` ya traen `app_label`/`model`
para mostrar y agrupar.

### R-Q3 — Ordering de permisos
No enviar el `ordering` compuesto. Usar `defaultOrdering: "id"` (está en `ordering_fields`) o dejar que
el backend aplique su default. Nada de `content_type` compuesto por querystring.

### R-Q4 — Alta de perfiles institucionales: **diferida a v2**
`POST user-entity-profiles` requiere `tipo_contenido` (ContentType) → depende del endpoint
`content-types` (inexistente). v1: `disableCreate`. Registrar requerimiento backend (mismo que bloquea
representantes/documentos en Catálogos). Dejar `// TODO(v2 content-types)` en el punto exacto.

### R-Q5 — Gating a superusuario puro
Añadir helper **`isSuperuser(user) = !!user?.es_superusuario`** en `lib/auth/store.ts`. Aplicar:
- **Nav `/usuarios`:** visible a superusuario **y** `Administrador RENADS` (este último solo para la
  sección Perfiles). El guard fino vive en las sub-rutas.
- **Rutas `cuentas`/`roles`/`permisos`:** guard que exige `isSuperuser` (si no, placeholder «no
  autorizado», sin render del CRUD).
- **`ResourceConfig.requireSuperuser?: boolean`:** cuando `true`, `ResourceCrud` condiciona `canWrite`
  (y `canCreate`) a `isSuperuser` además de `writeRoles`. Usuarios/roles/permisos lo activan.
- **Perfiles:** escritura `Administrador RENADS` (sin `requireSuperuser`).

---

> **Aprobado para Implement.** El `validator` marcará los checkboxes y generará
> `spec/usuarios.validacion.md`. Diferido a v2: alta de `user-entity-profiles` (depende de
> `content-types`).
