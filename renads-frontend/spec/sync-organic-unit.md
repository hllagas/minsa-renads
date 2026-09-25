# Spec — Sincronización de contrato: `OrganDirectory → OrganicUnit` + `UserProfile` endurecido

> **Estado:** PENDIENTE DE APROBACIÓN HUMANA antes de pasar a Implement.
> **Flujo SDD:** spec → (APROBACIÓN HUMANA) → implement → validator.

## Resumen del módulo

Sincroniza el frontend con **dos cambios de contrato** ya aplicados en el working tree del backend
(`D:\dev\renads\renads-api`, migraciones presentes):

- **Cambio 1 — Rename `OrganDirectory` → `OrganicUnit`** (mig convenios `0054_rename_organic_unit`, rename
  in-place, datos preservados). Renombra el **modelo**, la **tabla** (`organo_directorio` → `unidad_organica`),
  el **endpoint REST** (`organ-directories` → `organic-units`), las **FKs entrantes** (columna
  `unidad_organica_id`), los **campos de serializers/filtros** y el **`model` de ContentType** de Django
  (`organdirectory` → `organicunit`). Es mayormente un **rename mecánico** en el front, sin cambio de UX.
- **Cambio 2 — `UserProfile` endurecido** (mig common `0008`/`0009`/`0010`). Los 7 campos de la ficha de
  usuario pasan a **obligatorios (NOT NULL)** y `POST /users/` **ahora los exige** (400 si faltan). Es un
  **gap funcional**: el alta de usuario actual (`usersConfig.createFields`) no envía esos campos ⇒ fallará.

**No cubre pantallas nuevas.** Toca: Convenios (alta/edición/detalle/lista), Catálogos (entidades,
representantes, cargos/executive-positions), Usuarios (alta/edición/lista), y opcionalmente Perfil (`/auth/me`).

### Pantallas/archivos afectados (verificados en el working tree)

Rename (Cambio 1):
- `lib/usuarios/entity-endpoints.ts` — key `organdirectory` (línea 27-30), endpoint `organ-directories`.
- `lib/convenios/solicitante.ts` — key `organdirectory` (línea 20), label, endpoint.
- `lib/convenios/convention-fields.ts` — field `organo_directorio` (líneas 51-56), `optionsEndpoint:"organ-directories"`.
- `lib/convenios/flow-actions.ts` — flow `evaluacion-tecnica`, field `organo_directorio` + endpoint (líneas 39-43).
- `lib/convenios/entities.ts` — config `"organ-directories"` (línea 421-425) + entrada de menú (línea 485).
- `lib/catalogos/entities.ts` — entrada de menú `organ-directories` (línea 295).
- `lib/catalogos/catalogs.ts` — executive-positions: `organo_directivo_detalle` (líneas 188-190), field `organo_directivo` + `optionsEndpoint:"organ-directories"` (líneas 205-209, 225-232).
- `lib/catalogos/representantes-entities.ts` — `model:"organdirectory"` + `endpoint:"organ-directories"` (x3, líneas 40-60), prop `esOrganDirectory`, comentario.
- `lib/catalogos/organs.ts` — comentario.
- `components/convenios/convenio-create-form.tsx` — field `organo_directorio` + `endpoint="organ-directories"` (líneas 56, 124, 142, 279, 304, 310-311), filtros `organo_directivo*` (líneas 547-552), `esOrganDirectory` (línea 550), comentarios.
- `components/convenios/cascading-entity-field.tsx` — comentario.
- `app/(app)/convenios/page.tsx` — columna `organo_directorio_nombre` (líneas 67-74).
- `app/(app)/convenios/[id]/page.tsx` — `organo_directorio_nombre`, `tipo_organo_directorio` (líneas 135-136), `organo_directorio_detalle` (líneas 210-212).
- `app/(app)/convenios/[id]/editar/page.tsx` — initial `organo_directorio` (línea 34).
- `app/(app)/catalogos/representantes/page.tsx` — endpoint fallback `organ-directories`, filtros `organo_directivo*`, `esOrganDirectory`.
- `lib/api/schema.d.ts` — regenerar con `npm run gen:api`.

Perfil endurecido (Cambio 2):
- `lib/usuarios/configs.ts` — `usersConfig.createFields`/`editFields`.
- `lib/usuarios/types.ts` — `User`, `UserCreatePayload`, `UserUpdatePayload`.
- `app/(app)/perfil/page.tsx` + `lib/auth/store.ts` — opcional (mostrar `tiene_ficha_usuario` / detalle).

---

## CAMBIO 1 — Rename `OrganDirectory → OrganicUnit`

> Todas estas tareas son **rename mecánico**: cambian claves de API/endpoints/`model` de ContentType sin
> alterar la UX ni la lógica. Salvo indicación, mantener etiquetas visibles en español (p. ej. «Órgano del
> directorio») a menos que se decida renombrarlas (ver Riesgos R1).

### 1.1 Endpoint y `model` de ContentType

- [x] **T1 — `lib/usuarios/entity-endpoints.ts`.** Renombrar la clave del mapa `ENTITY_ENDPOINTS`:
  `organdirectory` → `organicunit`; cambiar `endpoint: "organ-directories"` → `"organic-units"`. Mantener
  `toLabel` igual. Actualizar el comentario JSDoc que menciona `ASSIGNABLE_PROFILE_MODELS`.
  - **Aceptación:** `ENTITY_ENDPOINTS.organicunit.endpoint === "organic-units"`; no queda ninguna clave
    `organdirectory`; el selector de entidades del `AssignProfilesDialog` lista contra `organic-units`.

- [x] **T2 — `lib/convenios/solicitante.ts`.** En `SOLICITANTE_ENTITIES` renombrar la clave `organdirectory`
  → `organicunit`; cambiar `endpoint: "organ-directories"` → `"organic-units"`. Mantener `label`
  («Órgano del directorio») o renombrar según R1.
  - **Aceptación:** `SOLICITANTE_ENTITIES.organicunit.endpoint === "organic-units"`; el `SolicitanteField`
    del alta de convenio resuelve el `ContentType` por `model === "organicunit"` (que ahora devuelve el
    backend) y lista contra `organic-units`.

- [x] **T3 — `lib/catalogos/representantes-entities.ts`.** En las 3 opciones de OrganDirectory
  (`organo-minsa`, `gobierno-regional`, `diris`): cambiar `model: "organdirectory"` → `"organicunit"` y
  `endpoint: "organ-directories"` → `"organic-units"`. Actualizar el comentario que dice «son el mismo
  modelo `OrganDirectory`». Renombrar la prop `esOrganDirectory` → `esOrganicUnit` (opcional, ver R2) y
  su JSDoc; si se renombra, actualizar todos los consumidores (T13, `convenio-create-form.tsx`).
  - **Aceptación:** las 3 opciones apuntan a `organic-units` y `model:"organicunit"`;
    `resolveTipoContenidoId("organicunit", ...)` resuelve el `ContentType.id`; la pantalla de representantes
    de MINSA/GORE/DIRIS lista y crea correctamente contra el modelo renombrado.

### 1.2 Convenios — campos de escritura/lectura

- [x] **T4 — `lib/convenios/convention-fields.ts`.** Renombrar el field `name: "organo_directorio"` →
  `"unidad_organica"` y `optionsEndpoint: "organ-directories"` → `"organic-units"` (líneas 51-56). Como
  `CONVENTION_EDIT_FIELDS` deriva de `CONVENTION_FIELDS` por filtro, hereda el cambio automáticamente.
  - **Aceptación:** el form declarativo de convenio (edición) envía `unidad_organica` y lista desde
    `organic-units`; el label sigue siendo «Órgano del directorio» (o R1).

- [x] **T5 — `components/convenios/convenio-create-form.tsx`.** Renombrar en el form de alta:
  `defaultValues.organo_directorio` → `unidad_organica`; el `useEffect` `setValue("organo_directorio", null)`
  → `setValue("unidad_organica", null)`; el payload `organo_directorio: Number(...)` →
  `unidad_organica: Number(...)`; `<Controller name="organo_directorio">` → `name="unidad_organica"`; el
  `endpoint="organ-directories"` del `EntityCombobox` → `"organic-units"`; los fallbacks
  `endpoint={tipoOpt?.endpoint ?? "organ-directories"}` → `?? "organic-units"`; los filtros
  `organo_directivo__isnull`/`organo_directivo` de la query de `executive-positions` →
  `unidad_organica__isnull`/`unidad_organica`; la referencia `tipoOpt.esOrganDirectory` → `esOrganicUnit`
  si se renombró (T3); comentarios que mencionan `organ-directories`/`OrganDirectory`.
  - **Aceptación:** `POST /conventions/` desde el alta envía `unidad_organica`; el selector filtra
    `organic-units?organo=<id>`; los cargos (executive-positions) se filtran por `unidad_organica*`; build OK.

- [x] **T6 — `lib/convenios/flow-actions.ts` (flow `evaluacion-tecnica`).** Renombrar el field
  `name: "organo_directorio"` → `"unidad_organica"` y `optionsEndpoint: "organ-directories"` →
  `"organic-units"` (líneas 39-43).
  - **Aceptación:** la acción de evaluación técnica (rol DIGEP) envía `unidad_organica` y lista desde
    `organic-units`; el resto de campos del flow intactos.

- [x] **T7 — `app/(app)/convenios/page.tsx` (lista).** Renombrar la columna: `accessorKey:
  "organo_directorio_nombre"` → `"unidad_organica_nombre"` y las lecturas `row.original.organo_directorio_nombre`
  → `row.original.unidad_organica_nombre` (título y celda).
  - **Aceptación:** la columna muestra el nombre de la unidad orgánica leyendo `unidad_organica_nombre`.

- [x] **T8 — `app/(app)/convenios/[id]/page.tsx` (detalle).** Renombrar las lecturas
  `c.organo_directorio_nombre` → `c.unidad_organica_nombre`, `c.tipo_organo_directorio` →
  `c.tipo_unidad_organica` (líneas 135-136) y la fila de la tabla `key:"organo_directorio_detalle"` +
  `detalleNombre(... .organo_directorio_detalle)` → `unidad_organica_detalle` (líneas 210-212).
  - **Aceptación:** el detalle muestra la unidad orgánica y su tipo leyendo las claves renombradas;
    `detalleNombre(unidad_organica_detalle)` (objeto `{id, nombre, ...}`) sin `[object Object]`.

- [x] **T9 — `app/(app)/convenios/[id]/editar/page.tsx` (initial).** Renombrar la clave del initial
  `organo_directorio: c.organo_directorio` → `unidad_organica: c.unidad_organica` (línea 34). Verificar
  que el nombre coincida con el `name` del field de T4 para que el pre-llenado funcione.
  - **Aceptación:** al editar un convenio, el selector de unidad orgánica se pre-rellena desde
    `c.unidad_organica`.

### 1.3 Catálogos — entidades, cargos y menú

- [x] **T10 — `lib/convenios/entities.ts`.** Renombrar la clave de config `"organ-directories"` →
  `"organic-units"` y su `endpoint: "organ-directories"` → `"organic-units"` (línea 421-425); renombrar el
  `slug` de la entrada de menú `{ slug: "organ-directories", ... }` → `"organic-units"` (línea 485).
  Revisar dentro de esa config cualquier columna/filtro/field que use claves `organo_directorio*`.
  - **Aceptación:** el CRUD de la entidad se sirve desde `organic-units`; la entrada del menú apunta al
    nuevo slug. Ver R3 (alias de ruta).

- [x] **T11 — `lib/catalogos/entities.ts`.** Renombrar el `slug` de la entrada de menú
  `{ slug: "organ-directories", title: "Órganos del Directorio" }` → `"organic-units"` (línea 295).
  - **Aceptación:** el menú de catálogos apunta a `organic-units`; la ruta `/catalogos/entidades/organic-units`
    resuelve la config renombrada en T10.

- [x] **T12 — `lib/catalogos/catalogs.ts` (executive-positions).** Renombrar la columna
  `key:"organo_directivo_detalle"` + `detalleNombre(r.organo_directivo_detalle)` →
  `unidad_organica_detalle` (líneas 188-190); renombrar el field/filtro `name:"organo_directivo"` →
  `"unidad_organica"` y `optionsEndpoint:"organ-directories"` → `"organic-units"` (líneas 205-209 y
  225-232, incluidos `optionsParamsFrom`/`resetsOn` que referencian `organo`). Verificar que la cascada
  `organo → unidad_organica` siga funcionando (el field `organo` no cambia).
  - **Aceptación:** el CRUD de cargos (executive-positions) muestra la columna de unidad orgánica desde
    `unidad_organica_detalle`, el form envía `unidad_organica` y filtra `organic-units?organo=<id>`.

- [x] **T13 — `app/(app)/catalogos/representantes/page.tsx`.** Renombrar el endpoint fallback
  `organ-directories` → `organic-units`; los filtros `organo_directivo`/`organo_directivo__isnull` de la
  query de cargos → `unidad_organica`/`unidad_organica__isnull`; la referencia `esOrganDirectory` →
  `esOrganicUnit` (si se renombró en T3). Verificar la resolución del `ContentType.id` por `model:"organicunit"`.
  - **Aceptación:** la pantalla de representantes (2 pasos) crea/lista para MINSA/GORE/DIRIS contra
    `organic-units`; los cargos se filtran por `unidad_organica*`; build OK.

### 1.4 Comentarios y regeneración de tipos

- [x] **T14 — Comentarios residuales.** Actualizar comentarios que mencionan `OrganDirectory` /
  `organ-directories` / `organo_directorio` / `organo_directivo` en: `lib/catalogos/organs.ts`,
  `components/convenios/cascading-entity-field.tsx`, y cualquier JSDoc tocado en T1-T13. No cambia lógica.
  - **Aceptación:** `rg -n "organ-directories|organdirectory|organo_directorio|organo_directivo"` sobre
    `lib/`, `components/`, `app/` no devuelve ocurrencias funcionales (solo, si acaso, referencias
    históricas en `spec/` y `CLAUDE.md`, que se tratan en T21).

- [x] **T15 — Regenerar `lib/api/schema.d.ts`.** Con el backend vivo en `http://localhost:8000`, correr
  `npm run gen:api`. Verificar que el schema regenerado exponga `organic-units`, `unidad_organica`,
  `unidad_organica_nombre`, `tipo_unidad_organica`, `unidad_organica_detalle`, `organicunit` en ContentTypes.
  - **Aceptación:** el diff de `schema.d.ts` refleja el rename; `npm run build` compila sin errores de tipos.

---

## CAMBIO 2 — `UserProfile` (ficha de usuario) endurecido

> El backend ahora **exige** en `POST /users/` los 7 campos de perfil (antes opcionales). El alta de
> usuario actual (`usersConfig.createFields`) **no los envía** ⇒ **gap funcional**: `POST /users/` devolverá
> 400. Estas tareas cierran el gap.
>
> Los 7 campos obligatorios: `tipo_documento` (choices DNI/CE/PASAPORTE/RUC), `numero_documento` (UNIQUE),
> `apellido_paterno`, `apellido_materno`, `telefono` (UNIQUE), `unidad_organica` (FK → `organic-units`),
> `cargo` (FK → `executive-positions`). Campo adicional opcional: `tiene_ficha_usuario` (boolean, default false).
> **`UserUpdateSerializer` los deja `required=False` pero `allow_blank/allow_null=False`** (no degrada un
> perfil ya completo): en edición se pueden enviar, pero no como vacío/nulo.

### 2.1 Tipos / contratos

- [x] **T16 — `lib/usuarios/types.ts`.** Ampliar:
  - `User` (lectura): agregar `tipo_documento: string`, `numero_documento: string`, `apellido_paterno: string`,
    `apellido_materno: string`, `telefono: string`, `unidad_organica: number`, `cargo: number`,
    `tiene_ficha_usuario: boolean`, y los detalles de lectura `unidad_organica_detalle` y `cargo_detalle`
    (objetos `{ id, nombre }` — confirmar forma exacta contra el serializer; ver R4).
  - `UserCreatePayload`: agregar los 7 campos (todos requeridos) + `tiene_ficha_usuario?: boolean`.
  - `UserUpdatePayload`: seguir siendo `Omit<UserCreatePayload,"password">`; documentar que en PATCH esos
    campos son opcionales pero **no** admiten vacío/nulo.
  - **Aceptación:** compilan; `UserCreatePayload` incluye exactamente los 7 campos obligatorios del contrato.

### 2.2 Formulario de alta / edición (GAP FUNCIONAL)

- [x] **T17 — `lib/usuarios/configs.ts` → `usersConfig.createFields`.** Agregar (todos `required: true`):
  - `tipo_documento` — `type:"select"` con `choices` **estáticos**: `DNI`, `CE`, `PASAPORTE`, `RUC`
    (patrón `sexo` de `lib/internados/persons.ts:94-101`). Ver R5 (hardcode vs endpoint).
  - `numero_documento` — `type:"text"`, `uppercase:false`.
  - `apellido_paterno` — `type:"text"`.
  - `apellido_materno` — `type:"text"`.
  - `telefono` — `type:"text"`, `uppercase:false`.
  - `unidad_organica` — `type:"select"`, `optionsEndpoint:"organic-units"`.
  - `cargo` — `type:"select"`, `optionsEndpoint:"executive-positions"`,
    `optionsToLabel` legible (p. ej. `nombre_masculino ?? nombre_femenino ?? id`; confirmar en R6).
  - `tiene_ficha_usuario` — `type:"boolean"` (opcional, sin `required`), colocado de forma coherente.
  - Colocar los campos en una sección visual (opcional `type:"separator"` «Ficha de usuario») tras los
    campos de cuenta y antes de `groups`.
  - **Aceptación:** `POST /users/` desde el alta envía los 7 campos; con datos válidos el usuario se crea
    sin 400; el select `tipo_documento` ofrece exactamente DNI/CE/PASAPORTE/RUC; `unidad_organica` lista
    desde `organic-units` y `cargo` desde `executive-positions`.

- [x] **T18 — `lib/usuarios/configs.ts` → `usersConfig.editFields`.** Agregar los mismos 7 campos +
  `tiene_ficha_usuario`, pero **sin** `required` (el `UserUpdateSerializer` los deja `required=False`).
  Mantener la exclusión de `password` (se cambia con `set-password`). No enviar valores vacíos/nulos (el
  backend rechaza `allow_blank/allow_null=False`): confirmar cómo el `ResourceForm` omite campos no tocados
  (ver R7); si el form envía siempre todas las claves, considerar dejarlos fuera del PATCH salvo edición
  explícita.
  - **Aceptación:** al editar un usuario, los campos de ficha se pre-rellenan (desde `unidad_organica`/`cargo`
    numéricos y los demás) y un PATCH que no degrada el perfil no produce 400 por blank/null.

### 2.3 Columnas (opcional — visibilidad)

- [x] **T19 — `lib/usuarios/configs.ts` → `usersConfig.columns` (opcional).** Añadir columnas legibles para
  `numero_documento`, `unidad_organica_detalle` y/o `tiene_ficha_usuario` usando `detalleNombre(...)` para los
  detalles. Decidir con el equipo qué columnas aportan valor (evitar sobrecargar la tabla).
  - **Aceptación:** si se implementan, las columnas muestran el valor legible (no `[object Object]`).

### 2.4 Perfil `/auth/me` (opcional)

- [ ] **T20 — `/perfil` + `lib/auth/store.ts` (opcional).** El backend expone en `/auth/me/` (vía
  `UserProfileReadSerializer`) `tiene_ficha_usuario`, `unidad_organica_detalle` y `cargo_detalle`.
  Decidir si mostrarlos en `app/(app)/perfil/page.tsx`. **Ojo:** `AuthUser.perfiles` (store) es el
  **alcance institucional** (`UserProfile` de scope: `tipo_entidad`/`id_objeto`/`entidad`/`rol`), **distinto**
  del `UserProfile`-ficha del backend; no confundir. Si se muestra, ampliar `AuthUser` con los campos
  nuevos y renderizarlos en una sección «Ficha de usuario».
  - **Aceptación:** si se implementa, `/perfil` muestra unidad orgánica, cargo y `tiene_ficha_usuario` del
    usuario autenticado; en caso contrario, la tarea se marca «fuera de alcance» con acuerdo del equipo.

---

## Documentación

- [x] **T21 — Actualizar `CLAUDE.md` (tabla de refactors).** Añadir una fila con fecha (2026-09-24),
  resumiendo ambos cambios (`OrganDirectory → OrganicUnit`, endpoint `organ-directories → organic-units`,
  `model` ContentType `organdirectory → organicunit`; y `UserProfile` endurecido con 7 campos obligatorios +
  `tiene_ficha_usuario`) y los archivos front tocados. Actualizar, si aplica, las notas del bloque de módulos
  que mencionan `organ-directories`/`OrganDirectory`. No es obligatorio reescribir `spec/` históricos.
  - **Aceptación:** la fila existe en la tabla; menciona los endpoints/claves nuevas y los archivos afectados.

- [x] **T22 — Verificación final.** `npm run lint` y `npm run build` sin errores; `rg -n
  "organ-directories|organdirectory|organo_directorio|organo_directivo"` sobre `lib/`, `components/`, `app/`
  sin ocurrencias funcionales.
  - **Aceptación:** lint y build limpios; sin referencias vivas al nombre viejo en código de app.

---

## Referencias al contrato (verificar en `docs/api-*.md` tras el rename)

- `docs/api-convenios.md` — actualmente lista `organo_directorio, organo_directorio_nombre,
  tipo_organo_directorio` (líneas ~60/111/118). El backend ya renombró a `unidad_organica,
  unidad_organica_nombre, tipo_unidad_organica, unidad_organica_detalle {id, nombre, siglas}`. **Pregunta
  abierta:** ¿se actualiza también `docs/api-convenios.md`/`docs/api-catalogos.md` en este spec o van por
  otro flujo? (ver R8).
- `docs/api-usuarios.md` — debe reflejar los 7 campos obligatorios de `POST /users/` + `tiene_ficha_usuario`
  + los detalles en `/auth/me/`. Confirmar la forma exacta de `unidad_organica_detalle`/`cargo_detalle`.

---

## Riesgos / decisiones abiertas

- **R1 — Etiquetas visibles.** El rename es de claves de API; las etiquetas UI («Órgano del directorio»,
  «Órganos del Directorio») pueden mantenerse o migrar a «Unidad orgánica». **Decisión requerida.**
  Recomendación: mantener las etiquetas actuales salvo que negocio pida el cambio, para acotar el diff.
- **R2 — Prop `esOrganDirectory`.** Renombrarla a `esOrganicUnit` es cosmético pero toca varios consumidores
  (`representantes-entities.ts`, `convenio-create-form.tsx`, `representantes/page.tsx`). **Decisión:**
  renombrar (coherencia) o dejar el nombre viejo con comentario. Recomendación: renombrar en el mismo spec.
- **R3 — Slug de ruta `/catalogos/entidades/[entidad]`.** Al cambiar el slug de menú `organ-directories` →
  `organic-units`, cualquier enlace hardcodeado a `/catalogos/entidades/organ-directories` se rompe.
  **Verificar** con `rg` que no existan enlaces hardcodeados. **Decisión abierta:** ¿cambiar el slug (URL
  nueva) o mantener alias `organ-directories` en el front apuntando al endpoint `organic-units`?
  Recomendación: cambiar el slug (no hay marcadores externos conocidos) y verificar rutas.
- **R4 — Forma de `unidad_organica_detalle` / `cargo_detalle`.** Confirmar contra el serializer si son
  objetos `{id, nombre}` (patrón `_detalle_fk`) u otra forma, antes de tiparlos y renderizarlos con
  `detalleNombre(...)`. No asumir.
- **R5 — `tipo_documento` choices.** El contrato las define como choices estáticos (DNI/CE/PASAPORTE/RUC).
  **Decisión:** hardcodear en el front (patrón `sexo`) — recomendado por ser conjunto cerrado — o leerlas de
  un endpoint si el backend lo expone. Si se hardcodea, documentar que un cambio de choices en el backend
  exige tocar el front.
- **R6 — `optionsToLabel` de `cargo` (executive-positions).** El modelo usa `nombre_masculino`/`nombre_femenino`
  (no `nombre`). Definir la etiqueta legible del select. Recomendación: `nombre_masculino ?? nombre_femenino ?? id`.
- **R7 — PATCH y `allow_blank/allow_null=False` en edición.** El `ResourceForm` declarativo puede enviar
  todas las claves del `editFields` en cada PATCH. Si envía cadenas vacías/nulas para campos de ficha no
  tocados, el backend responderá 400. **Verificar** el comportamiento de `components/crud/resource-form.tsx`
  (¿omite campos sin cambios? ¿envía `undefined`?) antes de decidir si los campos de ficha van en `editFields`
  o se editan por otra vía. Posible dependencia con la infra CRUD.
- **R8 — Sincronización de `docs/api-*.md`.** ¿Este spec incluye actualizar la documentación de contrato
  (`docs/api-convenios.md`, `docs/api-catalogos.md`, `docs/api-usuarios.md`) o va por otro flujo? Definir
  alcance para no dejar docs desincronizadas.
- **R9 — `npm run gen:api` requiere backend vivo.** T15 depende de tener el backend corriendo en `:8000` con
  las migraciones aplicadas. Si el entorno de implementación no lo tiene, T15 queda bloqueada y el resto de
  tareas (que usan claves string, no tipos generados) puede avanzar, pero el `build` con tipos estrictos
  podría fallar hasta regenerar. Coordinar.
