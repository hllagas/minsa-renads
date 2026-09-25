# Spec — Usuarios: `username = DNI` + apellidos en `auth_user` (sync migración common 0011)

> **Estado:** BORRADOR — requiere **aprobación humana** antes de pasar a Implement.
> **Alcance:** SOLO el módulo Usuarios (`/users`). Delta de la migración backend
> `common/0011_userprofile_drop_apellidos_username_dni.py` (HEAD backend `209e4ef`, ya aplicada y
> commiteada). El rename `OrganicUnit` + ficha obligatoria ya fue sincronizado (`spec/sync-organic-unit.md`,
> cerrado); **esta spec NO lo re-toca**.

---

## 1. Resumen del módulo

Pantalla cubierta: **Gestión de Usuarios** (`/usuarios`, config `usersConfig` en `lib/usuarios/configs.ts`),
tabla + alta + edición de cuentas (`users`). NO se tocan `groups`, `permissions` ni
`user-entity-profiles` (fuera del delta). NO se tocan `students`/`tutors` (conservan sus propios
apellidos).

### Qué cambió en el backend (contrato verificado en `apps/common/serializers.py`, `migrations/0011`)

1. **`UserProfile` elimina `apellido_paterno` y `apellido_materno`** (RemoveField en 0011). Los
   apellidos ahora viven en `auth_user.last_name`; el nombre en `auth_user.first_name`.
2. **`username` = `numero_documento`** para todo usuario **no-superusuario** (lo deriva el service; el
   cliente NO lo envía). El **superusuario** define su `username` libremente (obligatorio, único).
3. **`UserCreateSerializer`**: `username` es **read-only** (autogenerado — `serializers.CharField(read_only=True)`,
   línea 391). `first_name`/`last_name` son `required=False, allow_blank=False` a nivel campo pero
   **obligatorios para no-super** vía `validate()` (líneas 472-513). Campos de perfil obligatorios
   **solo para no-super**: `tipo_documento`, `numero_documento`, `telefono`, `unidad_organica`, `cargo`
   (+ `tiene_ficha_usuario` opcional, default False). **Superusuario exento total** (sin perfil, sin
   first/last obligatorios) pero DEBE enviar `username` (validado sobre `initial_data`, líneas 500-507).
4. **`UserProfileReadSerializer`** (anidado bajo `perfil` en `UserReadSerializer`): campos =
   `tipo_documento`, `numero_documento`, `telefono`, `unidad_organica`, `cargo`, `tiene_ficha_usuario`,
   `unidad_organica_detalle` (string), `cargo_detalle` (string). **SIN apellidos.**
5. **Nombre de presentación** = `auth_user.get_full_name()` (first+last) con fallback a `username`
   (`_display_name`, serializers.py líneas 24-28).
6. **`UserUpdateSerializer`**: `username` read-only; campos de perfil `required=False, allow_blank=False,
   allow_null=False` (no se degradan en PATCH parcial); `first_name`/`last_name` presentes en `fields`.

---

## 2. Lista de tareas

### Capa: Tipos/contratos — `lib/usuarios/types.ts`

- [x] **T1 — Quitar apellidos de la ficha de lectura (`UserFichaRead`).**
  Eliminar los campos `apellido_paterno` y `apellido_materno` de la interfaz `UserFichaRead`
  (líneas ~36-37). Los campos restantes deben coincidir 1:1 con `UserProfileReadSerializer.Meta.fields`:
  `tipo_documento`, `numero_documento`, `telefono`, `unidad_organica`, `cargo`, `tiene_ficha_usuario`,
  `unidad_organica_detalle`, `cargo_detalle`.
  **Criterio de aceptación:** `UserFichaRead` NO contiene `apellido_paterno`/`apellido_materno`; sus 8
  claves son exactamente las de `UserProfileReadSerializer`. `grep -n "apellido" lib/usuarios/types.ts`
  devuelve 0 coincidencias.

- [x] **T2 — Quitar apellidos del payload de escritura (`UserCreatePayload`).**
  Eliminar `apellido_paterno` y `apellido_materno` de `UserCreatePayload` (líneas ~85-86). Quitar
  `username` como campo obligatorio del payload de creación NO-super (el backend lo autogenera y es
  read-only); dejar `username` como **opcional** (solo lo envía el superusuario). `first_name`/`last_name`
  se conservan (obligatorios para no-super, se validan en el form vía `showWhen`, no aquí).
  Ajustar el JSDoc para reflejar: username autogenerado (no-super) / libre (super); apellidos viven en
  `last_name`.
  **Criterio de aceptación:** `UserCreatePayload` no contiene apellidos; `username` es opcional
  (`username?: string`). `UserUpdatePayload` (derivado con `Omit<..., "password">`) hereda el cambio.

### Capa: Configs / Formularios — `lib/usuarios/configs.ts`

- [x] **T3 — Quitar apellidos de `fichaUsuarioFields()`.**
  Eliminar las dos entradas `apellido_paterno` y `apellido_materno` (líneas ~51-52) de
  `fichaUsuarioFields(required)`. El resto de la ficha (`tipo_documento`, `numero_documento`, `telefono`,
  `unidad_organica`, `cargo`, `tiene_ficha_usuario`) se conserva.
  **Criterio de aceptación:** `grep -n "apellido" lib/usuarios/configs.ts` = 0 coincidencias. El form de
  alta/edición ya no muestra los inputs de apellidos.

- [x] **T4 — Regla de negocio en `createFields`: `username` solo para superusuario; `first_name`/`last_name`
  obligatorios para no-super; ficha solo para no-super.**
  En `createFields`:
  - `username`: quitar `required: true` estático; añadir `showWhen: (v) => v.is_superuser === true`.
    Mantener `uppercase: false`. (El backend lo exige solo para super y es read-only para no-super, que
    lo autogenera del documento.)
  - `first_name` (label "Nombres"): añadir `required: true` + `showWhen: (v) => v.is_superuser !== true`.
  - `last_name` (label "Apellidos"): añadir `required: true` + `showWhen: (v) => v.is_superuser !== true`.
  - Envolver los campos de la ficha (`...fichaUsuarioFields(true)` + su separador `_ficha`) para que se
    muestren **solo cuando no es superusuario**. Como `fichaUsuarioFields` devuelve un array, aplicar
    `showWhen: (v) => v.is_superuser !== true` a **cada** `FieldConfig` que retorna (incluido el
    `separator` `_ficha`), p. ej. mapeando el resultado: `fichaUsuarioFields(true).map((f) => ({ ...f,
    showWhen: (v) => v.is_superuser !== true }))`. Así, si el operador marca "Superusuario", los 6 campos
    de ficha desaparecen y NO se envían al backend (buildPayload los omite por `showWhen`).
  **Criterio de aceptación:**
  - Con `is_superuser = false` (default): se ven **Nombres**, **Apellidos** (ambos `*`), NO se ve
    **Usuario**, SÍ se ve la sección **Ficha de usuario** con sus 6 campos obligatorios. El payload NO
    incluye `username`.
  - Con `is_superuser = true`: se ve **Usuario** (`*`), NO se ven Nombres/Apellidos como obligatorios ni
    la sección Ficha. El payload incluye `username` y NO incluye campos de perfil.
  - Alta no-super OK: el backend responde 201 y `username` del usuario creado == `numero_documento`.
  - Alta super OK: el backend responde 201 con el `username` tecleado.

- [x] **T5 — Misma regla en `editFields`.**
  Aplicar el mismo patrón de `showWhen` que en T4 a `editFields`:
  - `username`: quitar `required: true`; `showWhen: (v) => v.is_superuser === true`.
  - `first_name`/`last_name`: `required: true` + `showWhen: (v) => v.is_superuser !== true`.
  - Ficha (`...fichaUsuarioFields(false)`): `showWhen: (v) => v.is_superuser !== true` sobre cada
    `FieldConfig`. (En edición la ficha es opcional; el `ResourceForm` omite del payload los opcionales
    vacíos — ver R7 histórico del spec de sync-organic-unit.)
  **Criterio de aceptación:** editar un usuario no-super pre-rellena Nombres/Apellidos + ficha (vía
  `mapEditingToInitial`, que aplana `perfil`); editar un superusuario muestra Usuario. PATCH que no toca
  la ficha no la degrada (no 400). Nota: el backend NO re-deriva `username` al cambiar `numero_documento`
  en edición (username read-only en update) — ver Riesgo R-2.

### Capa: Etiqueta de usuario — `lib/usuarios/entity-endpoints.ts`

- [x] **T6 — Corregir el label del selector de usuario (perfiles institucionales / student).**
  Línea ~41: el `toLabel` de `student` usa `r.apellido_paterno`. **Este es el catálogo de `students`,
  NO de usuarios** — `students` conserva su `apellido_paterno` (fuera del delta 0011). **Verificar** que
  el `student.toLabel` referencia el modelo `students` (sí lo hace: `endpoint: "students"`). Por tanto
  **NO cambiarlo**. Buscar en el módulo Usuarios cualquier label de **usuario** (`users`) que lea
  `r.apellido_paterno`/`r.apellido_materno` y sustituirlo por `r.last_name` (o
  `[r.first_name, r.last_name].filter(Boolean).join(" ")`).
  **Criterio de aceptación:** ningún `toLabel` que apunte al endpoint `users` lee `apellido_paterno`.
  El `student.toLabel` (endpoint `students`) queda intacto. Confirmar con
  `grep -rn "apellido_paterno" lib/usuarios/` que la única aparición restante corresponde al catálogo
  `students`, no a `users`.

  > **Nota para el implementador / pregunta abierta:** el enunciado de la tarea original indicó
  > `entity-endpoints.ts:41` como un label de usuario a cambiar a `r.last_name`. Al verificar, esa línea
  > es el `toLabel` del catálogo **`students`** (mapa `ENTITY_ENDPOINTS`, usado para asignar perfiles
  > institucionales por entidad), no del usuario. Como `students` conserva sus apellidos, **NO debe
  > cambiarse**. Si existe otro punto que renderice el nombre de un `user` a partir de apellidos de perfil,
  > ahí sí aplica `r.last_name`. Confirmar con el humano antes de tocar `entity-endpoints.ts`.

### Capa: Columnas de tabla — `lib/usuarios/configs.ts`

- [x] **T7 — Verificar la columna "Nombre".**
  La columna `nombre` ya usa `nombreCompleto(r)` = `[r.first_name, r.last_name].filter(Boolean).join(" ")`
  (líneas 13-14, 105), coherente con `_display_name` del backend. **No requiere cambios**; solo verificar
  que sigue leyendo `first_name`/`last_name` (no `perfil.apellido_*`).
  **Criterio de aceptación:** la columna "Nombre" muestra `first_name + last_name`; para un superusuario
  sin nombre, muestra "—" (fallback). Las columnas `numero_documento`, `unidad_organica_detalle`, `ficha`
  siguen leyendo de `r.perfil?.*`.

### Capa: Contrato OpenAPI + build

- [x] **T8 — Regenerar tipos OpenAPI.**
  Ejecutar `npm run gen:api` (contra el backend vivo en `http://localhost:8000/api/v1/schema/`) para
  regenerar `lib/api/schema.d.ts`. Requiere el backend corriendo con la migración 0011 aplicada.
  **Criterio de aceptación:** `lib/api/schema.d.ts` regenerado; el schema del perfil (`UserProfileRead`
  o equivalente) NO contiene `apellido_paterno`/`apellido_materno`; `username` figura como read-only en
  el create serializer. Si el backend no está disponible, marcar la tarea como bloqueada (no inventar el
  schema).

- [x] **T9 — Verificación de build.**
  Ejecutar `npm run build` y confirmar que compila sin errores de TypeScript (los cambios en
  `types.ts`/`configs.ts` no deben dejar referencias colgantes a los campos eliminados).
  **Criterio de aceptación:** `npm run build` termina con exit code 0.

---

## 3. Reglas de negocio a cubrir (resumen verificable)

| RN | Regla | Verificación |
|----|-------|--------------|
| RN-U1 | `username` = `numero_documento` para no-super (autogenerado por el service; el front NO lo envía). | Alta no-super → `username` creado == documento; el form no muestra el campo Usuario. (T2, T4) |
| RN-U2 | Superusuario define `username` libremente (obligatorio, único). | Alta super → el form exige Usuario; el backend responde 400 si falta o colisiona. (T4) |
| RN-U3 | `first_name`/`last_name` obligatorios para no-super. | Form no-super marca Nombres/Apellidos como `*`; backend 400 si faltan. (T4, T5) |
| RN-U4 | Superusuario exento de ficha + de nombres obligatorios. | Marcar Superusuario oculta ficha y no exige nombres; payload sin campos de perfil. (T4) |
| RN-U5 | Ficha SIN apellidos (viven en `auth_user`). | `UserFichaRead` y `fichaUsuarioFields` sin `apellido_*`; grep = 0. (T1, T3) |

---

## 4. Riesgos y preguntas abiertas

- **R-1 (verificado — no es riesgo): `showWhen` + `required` no bloquea el submit.**
  En `components/crud/resource-form.tsx`, `ConditionalFieldWrapper` (líneas 178-194) retorna `null`
  cuando `showWhen` es `false`, **desmontando** el `Controller`. React-hook-form (con `shouldUnregister`
  por defecto en v7) desregistra los campos desmontados, por lo que su regla `required` (línea 271) NO
  se evalúa. Además `buildPayload` (línea 98) excluye del payload los campos ocultos por `showWhen`.
  **Conclusión:** el patrón de T4/T5 (campo `required` oculto por `showWhen`) es seguro; el campo oculto
  ni bloquea el submit ni se envía. El implementador debe **confirmar en runtime** el toggle
  Superusuario (marcar/desmarcar) para validar que RHF no retiene el estado de validación del campo
  desmontado.

- **R-2 (informativo, fuera de alcance): `username` no se re-deriva al editar el documento.**
  `UserUpdateSerializer.username` es read-only (líneas 572-575). Si en edición se cambia
  `numero_documento` de un usuario no-super, su `username` NO se actualiza automáticamente (queda el
  anterior). El propio backend documenta esto como fuera de alcance del refactor. **No es un cambio de
  front**; solo dejar constancia. NO añadir tareas al respecto salvo indicación humana.

- **R-3 (pregunta abierta): `entity-endpoints.ts:41`.**
  Ver la nota de **T6**. La línea señalada corresponde al catálogo `students`, no a `users`. Confirmar
  con el humano si el objetivo real era otro punto de render del nombre de usuario. Por defecto, **no
  tocar** `entity-endpoints.ts`.

---

## 5. Referencias del contrato (backend, verificadas)

- `apps/common/migrations/0011_userprofile_drop_apellidos_username_dni.py` — RemoveField de apellidos +
  RunPython `username = numero_documento` (no-super).
- `apps/common/serializers.py`:
  - `UserProfileReadSerializer` (líneas 241-265) — 8 campos, sin apellidos.
  - `UserReadSerializer` (líneas 344-378) — `first_name`/`last_name` + `perfil` anidado.
  - `UserCreateSerializer` (líneas 380-563) — `username` read-only (391), first/last `required=False`
    a nivel campo (403-404), `validate()` exige nombres+perfil para no-super y `username` para super
    (472-513, 555-557).
  - `UserUpdateSerializer` (líneas 565-664) — `username` read-only (575), perfil `allow_blank/null=False`.
  - `_display_name(user)` (líneas 24-28) — `get_full_name()` con fallback a `get_username()`.

---

> **Aprobación humana requerida antes de Implement.** No iniciar la implementación hasta que un humano
> valide esta lista (en particular T6/R-3 y el patrón de `showWhen` de T4/T5).
