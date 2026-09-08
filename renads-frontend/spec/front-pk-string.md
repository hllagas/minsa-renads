# Spec — Frontend: adaptar la UI a claves primarias de tipo texto (`string` PK)

> **✅ ESTADO: APROBADO (2026-09-08) — en `implement` (Fase 0 + Fase A). Fase B gated (backend).**
> Decisiones: P1=(b) `EntityCombobox`+`valueKey` vía flag `optionsSearchable`; P2=`codigo` disabled en edición; P3=diferir `gen:api` hasta desbloquear B (Fase A con tipos genéricos `WithId`); P4=Fase 0 + Fase A ahora, Fase B en espera.
> Flujo SDD: `spec` → **(APROBACIÓN HUMANA ✅)** → `implement` → `validator`.
> **Fase A** (executing-units) está desbloqueada: el backend ya aplicó `convenios/0043-0045` y el
> contrato está vivo.
> **Fase B** (ipress) está **BLOQUEADA por el backend**: el `promote` de `convenios/0046` +
> `internados/0047` + `actividades` falló en dev (`foreign key mismatch - interno referencing ipress`;
> BD a medio migrar). **NO implementar la Fase B hasta que el equipo de backend aplique limpio
> `0046`→`0051` y `makemigrations --check` quede limpio.** Sus tareas quedan listadas para ejecutarse
> cuando se desbloquee.
>
> Fuentes de verdad:
> - `renads-api/spec/convenios_refactor_ambito_ejecutora.md` §«Breaking changes de API» (Fase A).
> - `renads-api/spec/convenios_ipress_pk_renipress.md` §«Breaking changes de API» (Fase B).
> - `docs/api-catalogos.md`, `docs/api-convenios.md`, `docs/backend-overview.md`, `docs/frontend-conventions.md`.
>
> **Regla:** el gating de la UI es UX; la autoridad final del alcance y de la escritura es el backend.
> No inventar endpoints/campos/estados: respetar exactamente los `docs/api-*.md` y las specs del backend.

---

## 1. Resumen

Dos refactors del backend introducen **PK de tipo texto** en entidades que el front hoy asume con PK
numérica (`id: number`):

1. **`executing-units`** (Fase A, backend LISTO): la PK pasa de `id` (int) a **`codigo`
   (CharField(4), string)**. El cliente **provee** `codigo` al crear. La URL de detalle es
   `/executing-units/<codigo>/`. Se **eliminan** los campos `tipo_organo`, `gobierno_regional`,
   `direccion`, `ubigeo`, `referencia_logo` (y el endpoint de logo) y se **añade** la FK
   `ambito_geografico_sanitario` (+ `ambito_geografico_sanitario_detalle`). Filtros:
   `ambito_geografico_sanitario`, `activo`. El filtro `?ipress?unidad_ejecutora=` ahora recibe el
   `codigo` string de la UE.

2. **`ipress`** (Fase B, backend BLOQUEADO): la PK pasa de `id` (int) a **`codigo_renipress`
   (CharField(8), string)**. El cliente **provee** `codigo_renipress` (requerido) al crear. La URL de
   detalle es `/ipress/<codigo_renipress>/`. Ya no existe `id`. Las **7 FK** a ipress pasan a string,
   y `user-entity-profiles` (`id_objeto`/`ids`) para `tipo_entidad: "ipress"` pasa a string.

**`health-geographic-scopes` ganó `gobierno_regional` (+detalle) — YA ACTUALIZADO en el front**
(config custom en `lib/catalogos/catalogs.ts`). **NO re-hacer.**

### Superficies que cubre este spec

- **Fase 0 — Infra CRUD declarativa compartida:** generalizar la asunción de PK numérica en
  `lib/api/query.ts`, `lib/crud/hooks.ts`, `lib/crud/types.ts`, `components/crud/resource-crud.tsx`,
  `components/ui/data-table.tsx`, `components/form/entity-combobox.tsx`,
  `components/form/multi-entity-combobox.tsx`, `lib/api/lookup.ts`. Habilita A y B.
- **Fase A — executing-units:** reescribir su config CRUD, quitar la rama de inyección `organo`,
  migrar todos los selects `unidad_ejecutora` a valor string `codigo`, `gen:api`, docs.
- **Fase B (gated) — ipress:** config ipress CRUD PK string + las 7 FK selects + user-entity-profiles
  + filtros + `gen:api`, docs.
- **Docs:** `docs/api-catalogos.md`, `docs/api-convenios.md`, `CLAUDE.md`, `lib/api/schema.d.ts`.

---

## 2. Estado actual del front (verificado)

- **`lib/api/query.ts`:** `interface HasId { id: number }`; `WithId extends HasId`.
  `createResourceApi.retrieve/update/remove(id: number)` construye `/${endpoint}/${id}/`.
  `resourceKeys.detail(endpoint, id: number)`. **Todo asume `id: number`.**
- **`lib/crud/hooks.ts`:** `useDetail(id: number|null)`, `useUpdate({ id: number, payload })`,
  `useRemove(id: number)`. **Numérico.**
- **`lib/crud/types.ts` `ResourceConfig`:** **no** tiene `pkField`. `defaultOrdering` por defecto `id`.
  `FieldConfig.optionsValueKey?: string` **ya existe** (usa esa clave como valor string y renderiza un
  dropdown `CodeSelect`, no búsqueda). `defaultValue?: string|number|boolean|null` acepta string.
- **`components/crud/resource-crud.tsx`:** usa `row.id` (cardView key + `updateM.mutate({ id: editing.id })`),
  `deleting.id` (`removeM.mutate(deleting.id)`), `editing.id`. `defaultOrdering ?? "id"`. **Numérico.**
- **`components/ui/data-table.tsx`:** NO define `getRowId` → TanStack Table keyea por índice de fila,
  no por `row.id`. El key de fila real vive en `ResourceCrud` (cardView usa `row.id`; la tabla usa el
  índice). **No requiere `getRowId` para PK string** (verificar en Fase 0).
- **`components/form/entity-combobox.tsx`:** `value: number|null`, `onChange:(number|null)`, tipa
  `ComboboxItemData { id: number }`, usa `row.id`, `getResourceItem(endpoint, value as number)`.
  **Estrictamente numérico.** Lo usan directamente: `components/convenios/convenio-create-form.tsx`
  (unidad_ejecutora L~277, universidad, facultad) y `app/(app)/catalogos/representantes/page.tsx`
  (paso 2, `entidadId: number`, L271).
- **`components/form/multi-entity-combobox.tsx`:** `value: number[]`, `onChange:(number[])`,
  `ComboboxItemData { id: number }`. Lo usa `user-entity-profiles` (ids). **Numérico.**
- **`lib/api/lookup.ts`:** `getResourceItem(endpoint, id: number)` construye `/${endpoint}/${id}/`.
  `searchResource` no depende de id. **`getResourceItem` es numérico.**
- **`components/crud/resource-form.tsx` L376-393:** si `field.optionsValueKey` está → renderiza
  `CodeSelect` (Select shadcn, valor string, **carga solo la 1ª página** vía `searchResource`, sin
  búsqueda incremental); si no → `EntityCombobox` (búsqueda server-side, valor numérico). **El path
  `optionsValueKey` YA sirve** para selects FK de valor string (executing-units `codigo` / ipress
  `codigo_renipress`) **siempre que el catálogo quepa en una página** (ver Riesgos: `CodeSelect` no
  pagina; UE/ipress pueden ser grandes).

### Usos concretos a migrar (grep ya hecho)

**executing-units (Fase A):**
- `lib/convenios/entities.ts`: config CRUD `executing-units` (L350-427) + selects `unidad_ejecutora`
  de `ipress` (filtro L226-230; campo L270-276) + `logoColumn("executing-units")` (L357) a quitar.
- `lib/convenios/convention-fields.ts` L71-76: select `unidad_ejecutora`.
- `components/convenios/convenio-create-form.tsx` L270-285: `EntityCombobox` `unidad_ejecutora`.
- `lib/catalogos/representantes-entities.ts` L69-75: UE como entidad del paso 2 (`executingunit`).
- `lib/usuarios/entity-endpoints.ts` L26-29: `executingunit` (assignable UE).
- `app/(app)/catalogos/entidades/[entidad]/page.tsx` L47-60: rama `needsOrgan`/`injectOrganoParam`
  para `executing-units.tipo_organo` — **ese campo YA NO EXISTE**, hay que quitar esa rama.
- `lib/api/storage.ts` — **YA quitó** executing-units de `LOGO_ENTITIES` (no re-hacer; verificar).

**ipress (Fase B, BLOQUEADO):** el implement debe hacer un **grep exhaustivo** de `ipress` en el
front. Usos conocidos: config CRUD `ipress` (`lib/convenios/entities.ts`), FK `ipress` en
`lib/campos-clinicos/*` (clinical-field-registrations, clinical-field-allocations), `lib/internados/*`
(interns/rotations `ipress_origen`/`ipress_destino`/tutors), `lib/actividades/*` (teaching-activities),
`lib/usuarios/*` (user-entity-profiles ipress), y cualquier `EntityCombobox`/`MultiEntityCombobox` con
endpoint `ipress`.

---

## FASE 0 — Infra compartida (string PK). **Habilita A y B.**

Objetivo: que la infraestructura CRUD declarativa acepte PK `string|number` **sin romper** las
decenas de recursos con PK numérica existentes (retrocompatibilidad total: `pkField` default `"id"`,
tipos que aceptan `string|number`).

- [x] **F0-1 — `lib/api/query.ts`: generalizar `HasId`/`WithId` y `createResourceApi` a PK `string|number`.**
  - Cambiar `interface HasId { id: number }` → `interface HasId { id?: string | number }` **o**
    documentar que `HasId` deja de exigir `id` numérico. Preferencia: `HasId` pasa a
    `{ [key: string]: unknown }`-compatible manteniendo `id?: string | number` para compatibilidad;
    `WithId` sigue siendo el registro indexable genérico (ya lo es). El objetivo es que un recurso con
    PK `codigo` (sin `id`) satisfaga `WithId`.
  - `createResourceApi<TRead, TWrite>(endpoint)`: `retrieve/update/remove` aceptan
    `id: string | number`; `resourceKeys.detail(endpoint, id: string | number)`.
  - **Criterio de aceptación:** el proyecto compila (`npm run build`) con todos los recursos actuales
    (PK numérica) sin cambios; `createResourceApi("executing-units").retrieve("0032")` es válido en
    tipos; `resourceKeys.detail("executing-units", "0032")` no rompe el tipado.

- [x] **F0-2 — `lib/crud/hooks.ts`: `id: string | number` en `useDetail`/`useUpdate`/`useRemove`.**
  - `useDetail(id: string | number | null)`, `useUpdate({ id: string | number, payload })`,
    `useRemove(id: string | number)`. `resourceKeys.detail(endpoint, id ?? -1)` → usar un sentinela
    válido para ambos tipos (`id ?? ""` o mantener `-1`; no rompe la key).
  - **Criterio:** los hooks siguen funcionando para recursos numéricos; aceptan `string` para
    executing-units/ipress; sin cambios en las páginas que ya los usan con `number`.

- [x] **F0-3 — `lib/crud/types.ts`: añadir `ResourceConfig.pkField?: string` (default `"id"`).**
  - Documentar: «Nombre del campo PK del recurso (default `"id"`). Para recursos con PK textual usar
    `"codigo"` (executing-units) o `"codigo_renipress"` (ipress). Afecta al valor usado para
    editar/eliminar/keyear filas.»
  - **Criterio:** `ResourceConfig` acepta `pkField`; los configs existentes que no lo declaran siguen
    usando `"id"`.

- [x] **F0-4 — `components/crud/resource-crud.tsx`: usar `pkField` configurable para editar/eliminar/keyear.**
  - Definir `const pk = config.pkField ?? "id";` y helper `const pkOf = (row: TRead) => row[pk] as string | number;`.
  - Reemplazar `editing.id` → `pkOf(editing)` en `updateM.mutate({ id: pkOf(editing), payload })`.
  - Reemplazar `deleting.id` → `pkOf(deleting)` en `confirmDelete`.
  - Reemplazar `key={row.id}` de la grilla cardView → `key={String(pkOf(row))}`.
  - `defaultOrdering ?? "id"`: mantener `"id"` como default **pero** para recursos con `pkField ≠ "id"`
    y sin `defaultOrdering` explícito, ordenar por `config.pkField` (evita ordenar por un `id`
    inexistente en executing-units/ipress). Concretar: `config.defaultOrdering ?? config.pkField ?? "id"`.
  - **Criterio:** editar/eliminar/paginar funciona idéntico para recursos numéricos (sin `pkField`);
    para un recurso con `pkField:"codigo"`, el PATCH/DELETE va a `/executing-units/<codigo>/` y el
    listado ordena por `codigo`.

- [x] **F0-5 — `components/ui/data-table.tsx`: confirmar keyeo de filas y (si procede) `getRowId`.**
  - Verificar que la tabla keyea por índice (`row.id` de TanStack = índice al no haber `getRowId`) y
    que **no** depende de un `id` numérico del dato. Si se detecta dependencia, añadir prop opcional
    `getRowId?: (row: TData) => string` y pasarla desde `ResourceCrud` como
    `(row) => String(pkOf(row))`. Si no hay dependencia, **no** añadir nada (dejar constancia en el
    validador).
  - **Criterio:** las tablas de recursos con PK string no muestran warnings de key duplicada ni
    filas mal identificadas; los recursos numéricos no cambian de comportamiento.

- [x] **F0-6 — `lib/api/lookup.ts`: `getResourceItem(endpoint, id: string | number)`.**
  - Cambiar la firma a `id: string | number`; el template literal `/${endpoint}/${id}/` ya sirve.
  - **Criterio:** `getResourceItem("executing-units", "0032")` resuelve `/executing-units/0032/`.

- [x] **F0-7 — `components/form/entity-combobox.tsx`: valor `string | number` (+ `valueKey`).**
  - Generalizar `ComboboxItemData` a `{ id: string | number; label: string }`.
  - Firma nueva: `value: string | number | null | undefined`,
    `onChange: (value: string | number | null) => void`, y prop opcional
    **`valueKey?: string` (default `"id"`)**: la clave del registro cuyo valor se usa como identificador
    (para executing-units `"codigo"`, ipress `"codigo_renipress"`). El combobox lee `row[valueKey]`
    para construir el `id` del item y para `getResourceItem` (detalle del seleccionado).
  - **Importante sobre el detalle del seleccionado:** hoy `getResourceItem(endpoint, value)` resuelve
    la etiqueta al editar. Con PK string el `value` **es** el `codigo`, y la URL de detalle es
    `/<endpoint>/<codigo>/` → sigue funcionando pasando `value` directamente. Verificar que
    `selectedQuery` use `value` (no `row.id`) como parámetro de `getResourceItem`.
  - Mantener 100% de compatibilidad para los usos numéricos existentes (default `valueKey:"id"`,
    `value: number`).
  - **Criterio:** `<EntityCombobox endpoint="executing-units" valueKey="codigo" value={ue} onChange={setUe} />`
    lista UEs por búsqueda, emite el `codigo` string y resuelve la etiqueta al editar; los usos
    numéricos actuales (universities, faculties, etc.) no cambian.

- [x] **F0-8 — `components/form/multi-entity-combobox.tsx`: valor `(string|number)[]` (+ `valueKey`).**
  - Generalizar `value: (string | number)[]`, `onChange: (value: (string | number)[]) => void`,
    `ComboboxItemData { id: string | number; label }`, prop `valueKey?: string` (default `"id"`),
    `labelById: Map<string | number, string>`, `add`/`remove` con `string | number`.
  - `selectedQuery`: `Promise.all(value.map((v) => getResourceItem(endpoint, v)))`.
  - **Criterio:** el combo múltiple emite un array de `codigo` string cuando `valueKey="codigo_renipress"`
    y mantiene el comportamiento numérico por defecto (user-entity-profiles no-ipress).

- [x] **F0-9 — `components/crud/resource-form.tsx`: confirmar el path `optionsValueKey` (CodeSelect).**
  - Confirmar (sin reescribir, salvo bug) que un `FieldConfig` con `optionsValueKey:"codigo"` +
    `optionsEndpoint:"executing-units"` renderiza `CodeSelect` y emite el `codigo` string como valor
    del formulario (que va tal cual al payload). Documentar la **limitación**: `CodeSelect` usa
    `searchResource` **sin búsqueda incremental** (solo 1ª página, ~limit del backend) → no escala a
    catálogos grandes. **Decisión de diseño (ver Preguntas P1):** para selects FK de PK string usar,
    donde el catálogo pueda ser grande, `EntityCombobox` generalizado (F0-7) con `valueKey` en un
    campo `type:"custom"` **o** ampliar `optionsValueKey` para que use `EntityCombobox` con `valueKey`
    en lugar de `CodeSelect`. **Este spec propone**: mantener `optionsValueKey` → `CodeSelect` para
    catálogos pequeños (health-geographic-scopes ya string por otra vía), y en la config de
    executing-units/ipress usar el path que corresponda según decisión P1.
  - **Criterio:** queda documentado qué componente renderiza `optionsValueKey` y si sirve para
    executing-units/ipress; si se decide que `EntityCombobox`+`valueKey` es la vía, el implement lo
    cablea en `resource-form.tsx` (nueva prop de `FieldConfig`, p. ej.
    `optionsSearchable?: boolean`, ver P1) sin romper los usos actuales de `optionsValueKey`.

**Criterio de aceptación de la Fase 0:** `npm run build` y `npm run lint` limpios; **ningún** recurso
con PK numérica cambia de comportamiento (retrocompatibilidad); los componentes generalizados aceptan
`string | number` con `valueKey` opcional. No se toca ninguna config de recurso todavía.

---

## FASE A — executing-units (backend LISTO). Depende de Fase 0.

- [x] **A-1 — Reescribir la config CRUD `executing-units` en `lib/convenios/entities.ts` (L350-427).**
  - Añadir `pkField: "codigo"` y `defaultOrdering: "codigo"`.
  - **Campos (create + edit):**
    - `codigo` — `type:"text"`, `required:true`, label «Código (4 dígitos)», `uppercase:false`.
      Es la PK provista por el cliente. En **edición** la PK no cambia → marcarlo `disabled:true` en
      `editFields` (o excluirlo del `editFields`), y requerido solo en `createFields`.
    - `nombre` — `type:"text"`, `required:true`, `fullWidth:true`, `uppercase:false`.
    - `ambito_geografico_sanitario` — `type:"select"`, `required:true`,
      `optionsEndpoint:"health-geographic-scopes"`. (PK numérica del ámbito → `EntityCombobox` normal.)
    - `activo` — `type:"boolean"`, `defaultValue:true`.
  - **Eliminar** los campos: `codigo` (presupuestal antiguo si difiere), `gobierno_regional`,
    `tipo_organo`, `direccion`, `ubigeo`, y los separadores que queden huérfanos. Ajustar separadores.
  - **Eliminar** `logoColumn("executing-units")` de `columns` (el modelo ya no tiene `referencia_logo`
    ni endpoint de logo).
  - **Columnas:** `codigo`, `nombre`,
    `ambito_geografico_sanitario` → `render: (r) => detalleNombre(r.ambito_geografico_sanitario_detalle)`,
    `activo` → `siNo`.
  - **Filtros:** eliminar `gobierno_regional` y `tipo_organo`; dejar
    `{ name:"ambito_geografico_sanitario", type:"select", optionsEndpoint:"health-geographic-scopes" }`
    y `activoFilter`.
  - **Criterio:** `GET /executing-units/` se lista con `codigo`/`nombre`/ámbito/activo; el alta con
    `{codigo, nombre, ambito_geografico_sanitario, activo}` crea la UE (POST a `/executing-units/`);
    editar hace PATCH a `/executing-units/<codigo>/` sin permitir cambiar `codigo`; eliminar hace
    DELETE a `/executing-units/<codigo>/`; no aparece acción de logo.

- [x] **A-2 — Quitar la rama de inyección `organo` para executing-units en `[entidad]/page.tsx`.**
  - En `app/(app)/catalogos/entidades/[entidad]/page.tsx` (L47-60): quitar `executing-units` de
    `needsOrgan` y de la rama `injectOrganoParam(..., "tipo_organo", ...)` (el campo `tipo_organo` ya
    no existe). Mantener la rama de `universities.tipo_entidad` intacta.
  - **Criterio:** `/catalogos/entidades/executing-units` renderiza sin resolver `organs` ni inyectar
    `optionsParams:{organo:...}`; universities sigue funcionando igual.

- [x] **A-3 — Migrar el select `unidad_ejecutora` de `ipress` a valor string `codigo` (declarativo).**
  - En `lib/convenios/entities.ts`, config `ipress`:
    - **Campo** `unidad_ejecutora` (L270-276): añadir `optionsValueKey:"codigo"` (o la vía decidida en
      P1) + `optionsToLabel:(r)=>String(r.nombre ?? r.codigo ?? "")`. El valor emitido es el `codigo`
      string y va tal cual al payload.
    - **Filtro** `unidad_ejecutora` (L226-230): idem, `optionsValueKey:"codigo"` para que
      `?unidad_ejecutora=<codigo>` reciba el string.
  - **Criterio:** crear/editar una IPRESS envía `unidad_ejecutora:"<codigo>"`; filtrar IPRESS por UE
    envía `?unidad_ejecutora=<codigo>` y devuelve resultados.

- [x] **A-4 — Migrar el select `unidad_ejecutora` del alta de convenio (declarativo).**
  - En `lib/convenios/convention-fields.ts` L71-76: añadir `optionsValueKey:"codigo"` (o vía P1) +
    `optionsToLabel`. Verificar que el resto de la config de convenio (unidad_ejecutora requerida solo
    para Específico) no dependa de un id numérico.
  - **Criterio:** el alta de convenio declarativo (si aplica) envía `unidad_ejecutora:"<codigo>"`.

- [x] **A-5 — Migrar el `EntityCombobox` `unidad_ejecutora` del form custom de convenio.**
  - En `components/convenios/convenio-create-form.tsx` L270-285: pasar `valueKey="codigo"` al
    `EntityCombobox` de `unidad_ejecutora` y ajustar el tipo del campo del formulario
    (`field.value as string | null`). El payload de creación de convenio debe enviar el `codigo`
    string en `unidad_ejecutora`. Verificar el `key`/reset por universidad y que `facultad`
    (PK numérica) y `universidad` (PK numérica) **no** se toquen.
  - **Criterio:** al crear un Convenio Específico, el payload lleva `unidad_ejecutora:"<codigo>"`; el
    combo lista UEs por búsqueda y resuelve etiqueta al editar.

- [x] **A-6 — Representantes: UE como entidad del paso 2 con PK string.**
  - `lib/catalogos/representantes-entities.ts` L69-75 (`unidad-ejecutora`): sin cambios de contrato
    (endpoint sigue `executing-units`), pero la pantalla debe tratar su PK como string (ver A-7).
  - `app/(app)/catalogos/representantes/page.tsx`: el estado `entidadId` (hoy `number`, L~274) y el
    `idObjeto` que se envía a `user-entity-profiles`/representantes debe ser `string | number`. Al
    seleccionar una UE, `entidadId` es el `codigo` string; pasar `valueKey="codigo"` al
    `EntityCombobox` del paso 2 **cuando** `tipoOpt.endpoint === "executing-units"` (y, en Fase B,
    `=== "ipress"`). Para las demás entidades (organ-directories, universities, conapres — PK numérica)
    el `valueKey` queda por defecto `"id"`.
  - **Nota (Riesgo):** el paso 2 mezcla entidades de PK numérica y string según el tipo elegido → el
    `EntityCombobox` debe soportar ambos (F0-7) y la pantalla debe elegir `valueKey` según
    `tipoOpt.endpoint`. Verificar que el `id_objeto` enviado sea `str` para UE (y ipress en B).
  - **Criterio:** elegir «Unidad Ejecutora» en el paso 1 lista UEs por `codigo`; crear un representante
    asocia el `id_objeto`/`idObjeto` = `codigo` string; las demás entidades siguen usando su `id`.

- [x] **A-7 — Usuarios / user-entity-profiles: UE como entidad asignable con PK string.**
  - `lib/usuarios/entity-endpoints.ts` L26-29 (`executingunit`): sin cambio de endpoint. En la
    pantalla que asigna perfiles (usa `MultiEntityCombobox`), pasar `valueKey="codigo"` cuando el
    `tipo_entidad` sea `executingunit`, para que los `ids` enviados sean `codigo` string. Verificar
    que la lectura (`id_objeto`) de un perfil UE se resuelva por `codigo`.
  - **Criterio:** asignar un perfil sobre `executingunit` envía `ids:["<codigo>", ...]`; el listado de
    perfiles muestra la etiqueta de la UE por `codigo`.

- [x] **A-8 — Verificar `lib/api/storage.ts`: executing-units fuera de `LOGO_ENTITIES`.**
  - Confirmar que `executing-units` ya no está en `LOGO_ENTITIES`/`hasLogo` (según el contexto, ya se
    quitó). Si aparece, quitarlo.
  - **Criterio:** `hasLogo("executing-units") === false`; ninguna acción de logo se ofrece para UE.

- [x] **A-9 — `npm run gen:api`: regenerar `lib/api/schema.d.ts`.**
  - **Riesgo (ver Riesgos):** `gen:api` trae A **y** B juntos (mismo `schema/`). Si el backend de
    ipress está a medio migrar, la regeneración puede traer tipos inconsistentes de ipress. **Coordinar
    con el desbloqueo de B:** ejecutar `gen:api` solo cuando el backend esté estable (idealmente tras
    B desbloqueado). Si se debe regenerar en Fase A antes de B, verificar manualmente que los tipos de
    `executing-units` (codigo string, ambito_geografico_sanitario) queden correctos y que los de
    `ipress` no rompan el build (si rompen, congelar `schema.d.ts` de ipress hasta B).
  - **Criterio:** `lib/api/schema.d.ts` refleja `ExecutingUnit` con `codigo` string PK,
    `ambito_geografico_sanitario` (+detalle) y sin `tipo_organo`/`gobierno_regional`/`direccion`/
    `ubigeo`/`referencia_logo`; el build compila.

**Criterio de aceptación de la Fase A:** `npm run build`/`lint` limpios; CRUD de executing-units
funcional con PK string; todos los selects `unidad_ejecutora` (ipress, convenio declarativo, convenio
custom, representantes, user-profiles) emiten/filtran por `codigo` string; ninguna referencia a los
campos eliminados.

---

## FASE B — ipress PK string (backend BLOQUEADO). **⛔ NO IMPLEMENTAR hasta desbloqueo.**

> **Bloqueada por el backend:** `migrate` de `convenios/0046`→`internados/0047`→`actividades` falla
> (`foreign key mismatch - interno referencing ipress`; BD a medio migrar). Ejecutar estas tareas
> **solo** cuando el equipo de backend confirme que `0046`→`0051` aplican limpio y
> `python manage.py makemigrations --check` queda limpio. Depende de Fase 0.

- [ ] **B-1 — Reescribir la config CRUD `ipress` en `lib/convenios/entities.ts` (PK string).**
  - Añadir `pkField:"codigo_renipress"` y `defaultOrdering:"codigo_renipress"` (o el ordering válido).
  - `codigo_renipress` — `type:"text"`, `required:true` (PK provista por el cliente); `disabled` en
    `editFields` (la PK no cambia). Ya está en `fields` (L245) como requerido; ajustar a la semántica
    de PK.
  - Eliminar cualquier dependencia de `id` en columnas/render (usar `codigo_renipress` como key).
  - **Criterio:** alta de IPRESS con `codigo_renipress` requerido crea el recurso (POST
    `/ipress/`); editar/eliminar operan sobre `/ipress/<codigo_renipress>/`.

- [ ] **B-2 — Migrar las 7 FK a ipress a valor string `codigo_renipress` en sus selects.**
  - Para cada select/combobox con endpoint `ipress`, pasar `valueKey="codigo_renipress"` (custom) o
    `optionsValueKey:"codigo_renipress"` (declarativo) y `optionsToLabel:(r)=>String(r.nombre ?? r.codigo_renipress)`:
    1. `clinical-field-registrations.ipress` (`lib/campos-clinicos/*`).
    2. `clinical-field-allocations.campo_clinico_ipress` (campo `campo_clinico_ipress`, `lib/campos-clinicos/*`).
    3. `interns.ipress` (`lib/internados/*`).
    4. `rotations.ipress_origen` (`lib/internados/*`).
    5. `rotations.ipress_destino` (`lib/internados/*`).
    6. `tutors.ipress` (`lib/internados/*`).
    7. `teaching-activities.ipress` (`lib/actividades/*`).
  - El implement debe hacer **grep exhaustivo** de `ipress` para no dejar ningún select/filtro atrás.
  - **Criterio:** cada payload de escritura envía la FK ipress como `codigo_renipress` string; cada
    filtro `?ipress=`/`?ipress_origen=`/`?ipress_destino=`/`?campo_clinico_ipress=` envía el string.

- [ ] **B-3 — user-entity-profiles: ipress como entidad asignable con PK string.**
  - `lib/usuarios/entity-endpoints.ts` `ipress` (L17): sin cambio de endpoint; en la pantalla de
    perfiles pasar `valueKey="codigo_renipress"` cuando `tipo_entidad === "ipress"` (los `ids` van
    string). En representantes (A-6), el ramo ipress del paso 2 usa `valueKey="codigo_renipress"`.
  - **Criterio:** POST de perfil con `tipo_entidad:"ipress"` envía `ids:["<codigo_renipress>", ...]`;
    lectura de `id_objeto` como string.

- [ ] **B-4 — Verificar filtros/keys de ipress en internados/actividades/campos-clínicos.**
  - Revisar tablas y filtros que keyean o filtran por `ipress` (p. ej. `?ipress_origen=`) para que
    usen el string. Verificar que ninguna vista dependa de `ipress.id` numérico.
  - **Criterio:** los listados de rotaciones/actividades/campos filtran por ipress string sin error.

- [ ] **B-5 — `npm run gen:api`: regenerar `lib/api/schema.d.ts` (con B ya desbloqueado).**
  - Ejecutar tras el desbloqueo del backend. Verificar `Ipress` con `codigo_renipress` string PK, sin
    `id`, y las 7 FK como string.
  - **Criterio:** `schema.d.ts` refleja el contrato ipress final; el build compila.

**Criterio de aceptación de la Fase B:** (al desbloquear) `npm run build`/`lint` limpios; CRUD de
ipress con PK string; las 7 FK y user-entity-profiles ipress emiten/filtran por `codigo_renipress`.

---

## FASE D — Documentación

- [x] **D-1 — `docs/api-catalogos.md`:** actualizar `executing-units` (PK `codigo` string, campos
  eliminados, `ambito_geografico_sanitario` +detalle, filtros nuevos, sin logo), confirmar
  `health-geographic-scopes` (ya trae `gobierno_regional` +detalle) y, en Fase B, `ipress`
  (PK `codigo_renipress` string, sin `id`, alta requiere `codigo_renipress`).
  **Criterio:** el `.md` refleja el contrato vivo de A (y de B al desbloquear).
- [x] **D-2 — `docs/api-convenios.md`:** si menciona `unidad_ejecutora`/`ipress` como int, actualizar
  a string (breaking changes de las specs del backend). **Criterio:** sin referencias a id int para
  esas FK.
- [x] **D-3 — `CLAUDE.md`:** añadir fila a «Refactors de backend aplicados al frontend» (executing-units
  PK string + ambito; ipress PK string gated) y una nota de convención: «recursos con PK textual usan
  `ResourceConfig.pkField`; `EntityCombobox`/`MultiEntityCombobox` aceptan `value: string|number` con
  `valueKey`». **Criterio:** `CLAUDE.md` documenta la PK string y la infra generalizada.
- [x] **D-4 — `lib/api/schema.d.ts`:** cubierto por A-9/B-5 (`gen:api`). No editar a mano.

---

## Riesgos

- **`EntityCombobox` es el punto más delicado** (numérico → `string|number`): un cambio de firma mal
  hecho rompe decenas de selects FK numéricos. La generalización (F0-7) debe ser **retrocompatible**
  por defecto (`valueKey:"id"`, `value:number`) y probarse con al menos un select numérico y uno
  string antes de migrar configs.
- **`gen:api` trae A + B juntos** (mismo `/api/v1/schema/`): regenerar con B a medio migrar puede
  traer tipos ipress rotos/incoherentes y romper el build. **Coordinar `gen:api` con el desbloqueo de
  B**; si hay que regenerar en A antes de B, verificar que los tipos ipress no rompan (congelar si es
  necesario).
- **Representantes paso 2 mezcla PK numérica y string:** organ-directories/universities/conapres
  (numérica) vs executing-units/ipress (string). El combobox debe soportar ambos y la pantalla elegir
  `valueKey` según el tipo elegido; el `id_objeto`/`idObjeto` enviado debe ser `str` para UE/ipress.
- **`CodeSelect` (path `optionsValueKey`) no pagina** (solo 1ª página): si executing-units/ipress
  crecen por encima de un page-size, un select basado en `CodeSelect` ocultará opciones. Preferir
  `EntityCombobox`+`valueKey` (búsqueda server-side) para esas FK — ver P1.
- **PK en URL:** `codigo`/`codigo_renipress` con caracteres no numéricos o ceros a la izquierda deben
  ir sin transformar en la URL (`/executing-units/0032/`). No aplicar `Number()` en ningún punto.
- **`defaultOrdering` por `id`:** los recursos con PK string sin `defaultOrdering` explícito fallarían
  al ordenar por `id` inexistente → F0-4 usa `config.pkField` como fallback.

---

## Preguntas abiertas (para el humano)

- **P1 — ¿Qué componente para los selects FK de PK string (executing-units / ipress)?**
  Opción (a): reutilizar `optionsValueKey` → `CodeSelect` (dropdown, sin búsqueda, 1ª página). Simple
  pero no escala a catálogos grandes. Opción (b): usar `EntityCombobox`+`valueKey` (búsqueda
  server-side, escala) exponiendo una nueva bandera de `FieldConfig` (p. ej.
  `optionsSearchable:true` junto a `optionsValueKey`) para que `resource-form.tsx` renderice el
  combobox en lugar del `CodeSelect`. **Recomendación:** (b) para UE e ipress (pueden ser grandes).
  ¿Se aprueba (b)?
- **P2 — `codigo` de executing-units en edición:** ¿lo mostramos `disabled` (visible pero no editable)
  o lo ocultamos del `editFields`? (La PK no debe cambiar.) Recomendación: `disabled` visible.
- **P3 — Momento de `gen:api`:** ¿ejecutamos `gen:api` en la Fase A (asumiendo que los tipos ipress
  rotos no rompen el build) o esperamos al desbloqueo de B para una sola regeneración A+B?
  Recomendación: esperar a B si el gap temporal es corto; si no, regenerar en A y verificar ipress.
- **P4 — Alcance de Fase B ahora:** ¿dejamos la Fase B totalmente sin tocar (gated) o preparamos ya la
  parte de infra que no depende del backend (Fase 0) para que B sea solo cablear configs? (Fase 0 no
  depende del backend y este spec la ejecuta primero.) Confirmar que Fase 0 + Fase A se implementan
  ahora y Fase B queda en espera.

---

> **Recordatorio:** este spec **requiere aprobación humana** antes de pasar a `implement`. La **Fase B
> está bloqueada por el backend** y no debe implementarse hasta el desbloqueo confirmado de
> `convenios/0046`→`0051`.
