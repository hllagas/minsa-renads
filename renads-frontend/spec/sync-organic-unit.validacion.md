# Validación — `sync-organic-unit.md`

> Validador SDD. **2ª pasada — Fecha: 2026-09-24.** Estado: **CERRADO (OK).** Los 3 hallazgos de la
> 1ª pasada (1 ALTO + 2 MEDIOS, todos en CAMBIO 2 lado lectura/edición) están **resueltos**. CAMBIO 1
> (rename `OrganDirectory → OrganicUnit`) seguía completo y correcto.

## 2ª PASADA — Verificación de correcciones (OK)

- **H1 [ALTO] — Pre-relleno de la ficha en edición: RESUELTO.** Se añadió `mapEditingToInitial?:
  (row) => Record<string, unknown>` a `ResourceConfig` (`lib/crud/types.ts:242`). `resource-crud.tsx:420-426`
  lo aplica **solo en edición** (`editing ? (config.mapEditingToInitial ? config.mapEditingToInitial(editing)
  : editing) : null`), con fallback a la fila cruda ⇒ no altera el `initial` de otros configs.
  `usersConfig.mapEditingToInitial = (row) => ({ ...row, ...(row.perfil ?? {}) })` (`configs.ts:101`)
  aplana `perfil` al nivel superior ⇒ los 7 campos + `tiene_ficha_usuario` (`name` planos en `editFields`)
  pre-rellenan. Correcto y no rompe el default del resto.
- **H2 [MEDIO] — Tipo de lectura `User`: RESUELTO.** `lib/usuarios/types.ts` modela ahora
  `perfil: UserFichaRead | null` (`types.ts:64`), con `unidad_organica_detalle`/`cargo_detalle` como
  `string` (no objeto) — alineado con `str(obj.*)` del serializer. La interfaz nueva se llamó
  `UserFichaRead` para NO colisionar con `UserProfileRead` preexistente (alcance por objeto); ambas
  coexisten sin colisión. `assign-profiles-dialog.tsx` y `lib/api/user-profiles.ts` siguen usando
  `UserProfileRead` sin rotura (compilan).
- **H3 [MEDIO] — Columnas de usuarios: RESUELTO.** `usersConfig.columns` leen `r.perfil?.numero_documento`
  y `r.perfil?.unidad_organica_detalle` (string legible directo, sin `detalleNombre`) y
  `r.perfil?.tiene_ficha_usuario`. `detalleNombre` **eliminado** de `configs.ts` sin usos colgando
  (`rg detalleNombre lib/usuarios` = 0).

### Sanidad técnica (2ª pasada)
- **Build:** `npm run build` OK (compila sin errores de tipos; todas las rutas generadas).
- **Lint:** `npm run lint` → **7 errores + 14 warnings**, idéntico al baseline preexistente
  (incompatible-library en `data-table.tsx`/`convenio-create-form.tsx`, set-state-in-effect en
  campos-clinicos, exhaustive-deps y no-unused-vars varios). **Sin regresiones.**
- **`rg "organ-directories|organo_directorio|organo_directivo|organdirectory"`** sobre `lib/ app/
  components/` (excluye `schema.d.ts`): **0 ocurrencias.** (Las restantes viven solo en `CLAUDE.md`,
  `docs/*.md`, `spec/*.md` — narrativa/histórico, fuera de código de app.)

### Tareas marcadas en esta pasada
- **T16** ✅ (tipo de lectura `User.perfil` correcto), **T18** ✅ (pre-relleno + payload R7),
  **T19** ✅ (columnas funcionales), **T22** ✅ (lint/build limpios, `rg` = 0).
- **T20** (`/perfil`, opcional) queda fuera de alcance con acuerdo del equipo (sin objeción).

## Veredicto final: OK — MÓDULO CERRADO

---

## [1ª PASADA — histórico] Veredicto: HALLAZGOS (bloqueaba cierre)

- **Build:** `npm run build` OK (compila sin errores de tipos).
- **Lint:** `npm run lint` → 7 errores + 14 warnings, **todos preexistentes** (react-hooks
  set-state-in-effect en `campos-clinicos/editar-sede-dialog.tsx`, `incompatible-library` en
  `data-table.tsx` / `convenio-create-form.tsx`, exhaustive-deps y no-unused-vars varios). **Ningún
  error/warning nuevo introducido por este cambio.**
- **`rg "organ-directories|organo_directorio|organo_directivo|organdirectory|tipo_organo_directorio"`**
  sobre `lib/ components/ app/` (excluye `schema.d.ts`, `spec/*.md`): **0 ocurrencias.** Rename mecánico
  limpio. `schema.d.ts` regenerado (34 ocurrencias `organic-units`/`unidad_organica`, 0 del nombre viejo).

## CAMBIO 1 — Rename (T1–T15): OK

Verificado uno a uno: `entity-endpoints.ts` (`organicunit`→`organic-units`), `solicitante.ts`
(`organicunit`), `representantes-entities.ts` (3 opciones `model:"organicunit"` + prop `esOrganicUnit`),
`convention-fields.ts`, `convenio-create-form.tsx` (defaultValues/useEffect/payload/Controller/filtros
`unidad_organica__isnull`), `flow-actions.ts`, `convenios/page.tsx` (`unidad_organica_nombre`),
`convenios/[id]/page.tsx` (`unidad_organica_nombre`/`tipo_unidad_organica`/parties
`unidad_organica_detalle`), `editar/page.tsx` (`initial.unidad_organica`), `entities.ts` (config+slug
`organic-units`), `catalogos/entities.ts` (slug), `catalogs.ts` (executive-positions
`unidad_organica_detalle`/`unidad_organica` + cascada `organo→unidad_organica`), `representantes/page.tsx`
(fallback `organic-units`, filtros `unidad_organica*`, `esOrganicUnit`). `schema.d.ts` regenerado.

Nota (no es hallazgo): `schema.d.ts` tipa `unidad_organica_detalle` de executive-positions / parties como
`string`, pero el backend (`_detalle_unidad_organica`, `views.py:510`) devuelve un objeto
`{id, nombre, organo}`. Es la imprecisión habitual de openapi-typescript para `SerializerMethodField` sin
anotación; `detalleNombre(...)` funciona correctamente contra el objeto real. Sin impacto.

## CAMBIO 2 — Ficha de usuario endurecida

### Lado de ESCRITURA (alta/edición) — OK
- **T17 (createFields):** OK. Los 7 campos con `required:true`, `tipo_documento` select estático
  DNI/CE/PASAPORTE/RUC, `unidad_organica`→`organic-units`, `cargo`→`executive-positions` con `cargoLabel`
  sobre `nombre_masculino ?? nombre_femenino ?? id`, `tiene_ficha_usuario` opcional. Coincide con
  `UserCreateSerializer` (7 required + `tiene_ficha_usuario` opcional).
- **editFields (parte de T18):** los mismos campos con `required:false`. `buildPayload`
  (`resource-form.tsx:127-131`) **omite** los opcionales vacíos/nulos y solo fuerza el envío de un campo
  vacío si es `required` ⇒ un PATCH que no toca la ficha NO manda blank/null ⇒ no dispara el 400 de
  `allow_blank/allow_null=False`. **R7 correctamente resuelto para el caso "no editar la ficha".**

### HALLAZGOS

- **[ALTO] Edición de usuario: la ficha NO se pre-rellena (T18 incompleto).**
  Ubicación: `components/crud/resource-crud.tsx:420` → `initial={editing}` (fila cruda de `GET /users/`);
  `components/crud/resource-form.tsx:76-88` (`defaultFor` lee `initial[field.name]`).
  Problema: `UserReadSerializer` (`apps/common/serializers.py:351-384`) **NO expone** los campos de ficha en
  el nivel superior; los anida bajo `perfil` (`perfil.unidad_organica`, `perfil.numero_documento`, etc. vía
  `UserProfileReadSerializer`). Como `editFields` usa `name:"unidad_organica"`, `defaultFor` busca
  `editing["unidad_organica"]` → `undefined` → los campos de ficha aparecen **vacíos** al editar. El PATCH no
  degrada el perfil (se omiten por vacíos), pero el admin no ve ni puede confirmar los valores actuales.
  Corrección sugerida: mapear el `initial` de edición desde `editing.perfil.*` a las claves planas del form
  (p. ej. `toEditInitial(user)` que aplane `perfil`), o exponer `config.editInitial`/`renderForm` en la
  config de usuarios; alternativamente, que el backend devuelva los campos también en el nivel raíz de
  `UserReadSerializer`. Requiere decisión (front-flatten vs. contrato).

- **[MEDIO] `lib/usuarios/types.ts` — `User` declara campos de ficha planos que no existen en la respuesta.**
  Ubicación: `lib/usuarios/types.ts:52-61` (`tipo_documento`, `numero_documento`, …, `unidad_organica`,
  `cargo`, `unidad_organica_detalle`, `cargo_detalle` como propiedades de nivel superior de `User`).
  Problema: `GET /users/` los devuelve bajo `perfil` (objeto `UserProfileReadSerializer`), no en raíz.
  Además `unidad_organica_detalle`/`cargo_detalle` del backend son **strings** (`get_*_detalle -> str`,
  `serializers.py:250-254`), no objetos `{id, nombre}` como asume `FichaDetalle`. El tipo miente sobre la
  forma real ⇒ induce el hallazgo ALTO y el MEDIO de columnas. Corrección sugerida: modelar
  `User.perfil?: { …; unidad_organica_detalle: string; cargo_detalle: string }` (o `null`) en lugar de
  campos planos, alineado con `UserReadSerializer`.

- **[MEDIO] Columnas de usuarios muestran «—» para N.º documento y Unidad orgánica (T19).**
  Ubicación: `lib/usuarios/configs.ts:109-114`. `render: (r) => String(r.numero_documento ?? "—")` y
  `detalleNombre(r.unidad_organica_detalle)` leen del nivel superior, que está vacío (los datos están en
  `r.perfil.*`). Además `perfil.unidad_organica_detalle` es un **string**, no un objeto ⇒ `detalleNombre`
  (que espera `{nombre}`) devolvería «—» aunque se corrigiera la ruta. Corrección sugerida: leer
  `r.perfil?.numero_documento` y `r.perfil?.unidad_organica_detalle` (este último ya es string legible; no
  usar `detalleNombre`, usar `String(... ?? "—")`).

### Fuera de alcance / no bloqueantes
- **T16:** parcialmente hecho — `UserCreatePayload`/`UserUpdatePayload` (lado escritura) correctos y compilan;
  el defecto está en el tipo de **lectura** `User` (hallazgo MEDIO). No marcar hasta corregir la forma de lectura.
- **T18:** la parte de payload (R7) está resuelta; el **pre-relleno** está roto (hallazgo ALTO). No marcar.
- **T19:** implementado pero **no funcional** (hallazgo MEDIO). No marcar.
- **T20 (`/perfil`, opcional):** no implementado; el spec lo permite como "fuera de alcance con acuerdo del
  equipo". Sin objeción del validador.
- **T22:** no cerrable mientras existan los hallazgos anteriores (aunque lint/build y el `rg` del rename
  están limpios).

## Inconsistencias narrativas en `CLAUDE.md` (informativo — NO corregir sin decisión del usuario)

La fila de refactors `2026-09-24` (línea 177) está **correcta y completa**. Pero el **cuerpo narrativo** del
bloque de módulos conserva menciones vivas al nombre viejo que ahora contradicen el contrato; se reportan
para que el usuario decida si actualizarlas (son texto narrativo/histórico, no código):
- Línea 53: «`organ-directory-positions` ELIMINADO … FK directa `executive-positions.organo_directivo → OrganDirectory`».
- Sección «Catálogos con CRUD completo» / «Representantes multi-entidad»: citan `OrganDirectory`,
  `organo_directorio`, `organo_directivo`, endpoint `organ-directories` como vigentes.
- Línea 52 quedó en estado mixto: ya renombrada a `unidad_organica_detalle`/`organic-units` en el ejemplo de
  executive-positions, pero describe el detalle como `{id, nombre, categoria}` (hoy es `{id, nombre, organo}`).
- Filas históricas 2026-08-3x / 09-0x mantienen `OrganDirectory`/`organ-directories` (esperado en registros
  históricos; no requieren cambio).

## Resumen
- **CAMBIO 1 (rename):** CERRADO.
- **CAMBIO 2 (ficha):** escritura CERRADA; **lectura/edición con 1 ALTO + 2 MEDIOS** → devolver a Implement.
- Build OK · Lint sin regresiones · `rg` del nombre viejo = 0.
