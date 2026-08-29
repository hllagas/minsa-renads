# Validación — Módulo Catálogos (`/catalogos`)

> Revisión del Validator contra `spec/catalogos.md` (APROBADO) y el contrato del backend
> (`docs/api-catalogos.md`, `docs/api-convenios.md`, `docs/api-auth.md`,
> `docs/frontend-conventions.md`). **§5 (R1–R5) es autoritativa.**
>
> **Veredicto: APROBADO — módulo cerrado.** Sin hallazgos altos/medios. 24/24 tareas cumplidas.
> Sanidad técnica: `npx tsc --noEmit` OK, `npm run build` OK, `npm run lint` solo con los **2
> hallazgos PRE-EXISTENTES** ajenos al módulo.

## Sanidad técnica

- `npx tsc --noEmit`: **OK** (sin errores).
- `npm run build`: **OK** (compila; rutas `/catalogos`, `/catalogos/auditoria`,
  `/catalogos/documentos`, `/catalogos/representantes`, `/catalogos/entidades/[entidad]`,
  `/catalogos/listas/[catalogo]` presentes).
- `npm run lint`: 1 error + 1 warning, **ambos PRE-EXISTENTES y fuera del módulo**:
  - `components/layout/theme-toggle.tsx:18` — `react-hooks/set-state-in-effect` (conocido).
  - `components/ui/data-table.tsx:43` — `react-hooks/incompatible-library` (conocido, TanStack Table).
  - **Ningún hallazgo de lint nuevo introducido por el módulo Catálogos.**

## Estado por tarea

| Tarea | Estado | Nota |
|------|--------|------|
| T1 Tipos TS | OK | `Documento`/`AuditLog`/`Representante` con campos read-only exactos del contrato; entidades/catálogos vía `WithId` (patrón declarativo existente). Claves API sin traducir. |
| T2 Filtros declarativos | OK | `FilterConfig` en `lib/crud/types.ts`; `ResourceFilters` + `useList({filters})`; resetea `page`; limpia filtros. |
| T3 `readOnly` explícito | OK | Flag en `ResourceConfig`; `canWrite=!readOnly && userHasRole(...)`; Badge «Solo lectura». |
| T4 Hooks TanStack Query | OK | `createResourceHooks` reusado; `documents`/`audit-logs` con hooks propios; invalidación por `resourceKeys.all`. |
| T5 Centralizar entidades | OK | Origen único `lib/convenios/entities.ts` (`ENTITY_CONFIGS`); `/convenios/maestros` y `/catalogos` lo consumen; sin duplicación. |
| T6 Filtros 7 entidades | OK | `filterset_fields` exactos por entidad; `activo` boolean; FK con `EntityCombobox`. |
| T7 `university-authorities` | OK | Endpoint/filtros/search y campos R1 exactos (incl. `fecha_inicio_cargo`*, `referencia_documento_resolucion`). |
| T8 `faculties` / `professional-careers` | OK | Filtros y campos R1 exactos; `especialidad` opcional; FK a catálogos correctos. |
| T9 `university-campuses` | OK | Filtros `universidad`/`region`/`activo`; campos R1 exactos (`region`/`ubigeo` opcionales). |
| T10 `representatives` (v1) | OK | `disableCreate:true` (ALTA diferida); edición solo campos NO polimórficos (`nombre`,`cargo_ejecutivo`,`origen`,`fecha_inicio`,`fecha_fin`,`activo`); `tipo_contenido`/`id_objeto` solo lectura vía `renderEditInfo`; `// TODO(v2 content-types)` presente; filtros `tipo_contenido`/`id_objeto`/`cargo_ejecutivo`/`activo`. |
| T11 18 catálogos readOnly | OK | Los 18 slugs registrados con `readOnly:true`, columnas `codigo`/`nombre`/`activo`, filtro `activo`. |
| T12 `ubigeos` readOnly | OK | Filtros `departamento`/`provincia`/`distrito`/`activo`; columnas geográficas; paginación backend. |
| T13 API+hooks `documents` | OK | `lib/api/documents.ts` (Axios); POST `DocumentoWrite` solo 5 campos de escritura (nunca read-only); `url-descarga` como mutation; remove invalida lista; `// TODO(v2 content-types)`. |
| T14 Pantalla documentos (v1) | OK | List + filtros (`tipo_documento`,`estado`,`tipo_contenido`,`id_objeto`) + descargar (`window.open`) + eliminar; **sin ALTA** (R2); accesible a autenticado. |
| T15 API+hook `audit-logs` | OK | Solo lectura; filtros R3 (`usuario`,`accion_contiene`,`tipo_contenido`,`id_objeto`,`creado_en_desde`,`creado_en_hasta`); sin mutaciones. |
| T16 Pantalla auditoría | OK | Columnas del contrato; filtros R3 con date pickers; gating `Administrador RENADS`/`Auditor` con placeholder si no; orden `creado_en` desc (default backend). |
| T17 Índice `/catalogos` | OK | Tarjetas shadcn por sección; «Auditoría» solo Admin/Auditor. |
| T18 Ruta entidades | OK | Resuelve config por slug; estado «no encontrada» + volver. |
| T19 Ruta listas | OK | Contra `CATALOG_CONFIGS` (incluye `ubigeos`), `readOnly`. |
| T20 Rutas dedicadas | OK | `/representantes`, `/documentos`, `/auditoria` existen y montan su componente. |
| T21 Navegación | OK | `app-shell.tsx:46` ítem `/catalogos` con `["Administrador RENADS","Auditor"]` (R4). |
| T22 Estados carga/error/vacío | OK | Reutiliza `DataTable`/`DataTablePagination`; error con reintento; toasts `extractApiError`; mensajes de vacío. |
| T23 Idioma/convenciones | OK | UI español, claves API sin traducir; Axios solo en `lib/api/`; server-state solo TanStack Query; tablas vía `<DataTable>`; lint/build pasan. |
| T24 Gating UX | OK | Entidades/representantes escritura solo Admin (default `WRITE_ROLES`); documentos autenticado; auditoría Admin/Auditor; catálogos solo lectura. |

## Conformidad de contrato (§5)

- **R1 (campos exactos):** verificado entidad por entidad; todos los `fields` coinciden con R1
  (requeridos `*`, FK→endpoint correcto, `date`/`email`/`boolean`, `referencia_*` como texto).
- **R2 (polimorfismo / ALTA diferida):** confirmado. Representantes y documentos **sin create activo**
  en UI; `// TODO(v2 content-types)` en `lib/catalogos/representatives.tsx:43`,
  `lib/api/documents.ts:49`. El método `documentsApi.create` queda como andamiaje v2 (no cableado a UI)
  y nunca envía campos read-only.
- **R3 (audit-logs):** filtros y orden `creado_en` desc correctos.
- **R4 (menú):** ítem nav y gating por sección del índice correctos.
- **R5 (rutas):** segmentos `entidades`/`listas` correctos; sin `/catalogos/catalogos`; sin colisión
  con `/convenios/maestros`.

## Observaciones menores (BAJAS — no bloquean el cierre)

1. `app/(app)/catalogos/documentos/page.tsx` — la columna `cargado_por` (sugerida en T14) no se
   muestra; sí se incluyen tipo/archivo/destino/versión/estado/cargado_en. Sugerencia: añadir columna
   `cargado_por` si se desea trazabilidad de carga. (Cosmético.)
2. `lib/catalogos/entities.ts` (`university-authorities`) — la columna «universidad (etiqueta)»
   sugerida en T7 no se renderiza (requiere `universidad_nombre`/label del backend). Columnas son
   «sugeridas», no obligatorias. (Cosmético.)
3. `lib/api/audit-logs.ts` / pantalla auditoría — el filtro exacto `accion` (igualdad) no se expone en
   UI; se usa `accion_contiene` (icontains), más útil. Sin impacto funcional. (Informativo.)
4. La bitácora no envía `ordering` explícito; depende del default backend (`creado_en` desc), que el
   contrato garantiza. Aceptable; podría enviarse explícito para robustez. (Informativo.)

---

## Validación — Actualización de contrato 2 (2026-07-17)

Delta backend commit `fdd5770`. Verificado contra `docs/api-catalogos.md` §2 y `lib/api/schema.d.ts`.
**Resultado: CERRADO — sin hallazgos altos/medios. U1–U4 marcadas.**

| Tarea | Estado | Verificación |
|-------|--------|--------------|
| U1 Config `ipress` columna+filtro | OK | `lib/convenios/entities.ts` (compartida): columna «Sede docente» con render `siNo(es_sede_docente)`; filtro boolean `es_sede_docente`; `es_sede_docente` NO expuesto en `fields` (autorización solo por acción). Aplica a `/catalogos/entidades/ipress` y `/convenios/maestros/ipress` vía `CATALOGO_ENTITY_CONFIGS`. |
| U2 Acción sede docente | OK | `components/catalogos/ipress-sede-docente-action.tsx`: `useResourceAction("ipress", row.id, "autorizar-sede-docente")` con body `{ autorizar }` (autorizar=`!es_sede_docente`); onSuccess invalida además `resourceKeys.all("ipress")`; errores con `extractApiError`. Endpoint y body coinciden con `schema.d.ts` (`ipress_autorizar_sede_docente_create`). |
| U3 Inyección + navegación | OK | `catalogos/entidades/[entidad]/page.tsx`: `rowActions` solo si `entidad==="ipress"` y `userHasRole(user,"CONAPRES")`; en otros slugs/roles no se pasa. `app-shell.tsx` línea 46: ítem `/catalogos` incluye `"CONAPRES"`. Admin/Auditor no ven la acción (solo CONAPRES). |
| U4 Verificación | OK | `npx tsc --noEmit` limpio (exit 0); `npm run lint` limpio salvo warning preexistente de TanStack Table en `data-table.tsx`. |

Sanidad del cambio compartido (`resource-crud.tsx`): la columna de acciones aparece con
`canWrite || rowActions`. En `/catalogos/entidades/ipress`, CONAPRES no tiene escritura CRUD
(`writeRoles` default `Administrador RENADS`), por lo que Editar/Eliminar no se muestran y solo aparece
la acción «Sede docente» — comportamiento deseado. Sin regresión en el resto de entidades (sin
`rowActions` la columna solo aparece bajo `canWrite`, como antes).

---

## Validación — Delta Categorías / Clasificaciones / Redes / Microrredes (2026-08-13)

Delta APROBADO (humano) en `spec/catalogos.md` §«Actualización de contrato … (2026-08-13)», tareas
N1–N11. Verificado contra `docs/api-catalogos.md` §1.1/§1.2 y `lib/api/schema.d.ts`
(`RedAuto{codigo,nombre,activo?,ambito_geografico_sanitario}`,
`MicroredAuto{codigo,nombre,activo?,red}`; filtros `networks`=`ambito_geografico_sanitario`/`activo`,
`micro-networks`=`red`/`activo`). Claves del API sin traducir. **Resultado: APROBADO — sin hallazgos
altos/medios. N1–N11 marcadas.**

| Tarea | Estado | Evidencia |
|-------|--------|-----------|
| N1 `categories` catálogo CRUD | OK | `lib/catalogos/catalogs.ts:173` `writableCatalog("categories","Categorías","categoría")`; `writableCatalog` (l.40–60) genera columnas `codigo`/`nombre`/`activo(siNo)`, filtro `activo`, search, `activo` boolean `defaultValue:true`. Aparece en `CATALOG_MENU` (derivado, l.183–185). |
| N2 `classification-types` catálogo CRUD | OK | `lib/catalogos/catalogs.ts:174-178` `writableCatalog("classification-types","Tipos de clasificación","tipo de clasificación")`. Mismo patrón que N1. |
| N3 `networks` CRUD con FK ámbito | OK | `lib/catalogos/entities.ts:176-208`: endpoint/title/singular/searchPlaceholder correctos; columns `codigo`/`nombre`/`activo(siNo)`; filters `ambito_geografico_sanitario`(select→`health-geographic-scopes`)+`activoFilter`; fields orden `codigo`,`nombre`,`ambito_geografico_sanitario`(select req),`activo`(boolean `defaultValue:true`). Sin `writeRoles` (default Admin). |
| N4 `micro-networks` CRUD + cascada | OK | `lib/catalogos/entities.ts:210-249`: filtro lista plano `red`+`activoFilter` (l.222-225); field virtual `_ambito` (`virtual:true`, l.229-234); `red` (req) con `optionsParamsFrom` que emite `{ambito_geografico_sanitario:String(v._ambito)}` solo si hay `_ambito` (l.241-242) y `resetsOn:["_ambito"]` (l.243); orden `_ambito`,`red`,`codigo`,`nombre`,`activo`. `buildPayload` excluye `_ambito` → POST body `{codigo,nombre,red,activo}`. |
| N5 Menú entidades | OK | `lib/catalogos/entities.ts:274-275`: `{slug:"networks",title:"Redes"}` y `{slug:"micro-networks",title:"Microrredes"}` tras `minsa-organs` (bloque sanitario), antes de CONAPRES. `categories`/`classification-types` NO se añaden aquí (van por `CATALOG_MENU`). |
| N6 Resolución de slug | OK | `catalogos/entidades/[entidad]/page.tsx:21` resuelve contra `CATALOGO_ENTITY_CONFIGS` (incluye `...SANITARY_ENTITY_CONFIGS`, entities.ts:259); `catalogos/listas/[catalogo]/page.tsx:13` contra `CATALOG_CONFIGS`. Sin ramas especiales; los 4 slugs montan config. Ninguno de los 4 dispara `rowActions` (no logo/anexos/CONAPRES). |
| N7 Docs | OK | `docs/api-catalogos.md:60-63`: nota de §1.2 indica que `networks`/`micro-networks` ya tienen config en `lib/catalogos/entities.ts` y `categories`/`classification-types` en `lib/catalogos/catalogs.ts` (§1.1). Sin contradicción con el front. |
| N9 Extender `FieldConfig` | OK | `lib/crud/types.ts:34` `optionsParamsFrom?`; l.39 `resetsOn?:string[]`; l.44 `virtual?:boolean`. Todos opcionales/retrocompatibles. Compila (tsc limpio). |
| N10 Consumir params + reset | OK | `components/crud/resource-form.tsx:298-303`: `watchesValues=!!field.optionsParamsFrom`; `useWatch({control, disabled:!watchesValues})`; `dynamicParams` prioriza `optionsParamsFrom` sobre `optionsParams`. Reset vía `ResetOnParentChange` (l.321-327, l.377-403): baseline en primer render (no borra precargados en edición), resetea solo ante cambio real del padre, sin bucles. `EntityCombobox` incluye `params` en su `queryKey` (entity-combobox.tsx:50) → refresca opciones al cambiar el padre. |
| N11 Excluir `virtual` del payload | OK | `components/crud/resource-form.tsx:78-79` `buildPayload`: `if (f.virtual) continue;`. `buildPayload` se usa en el único `onSubmit` (l.139), común a create y update → `_ambito` excluido en POST y PATCH. |
| N8 Verificación final | OK | `npx tsc --noEmit` limpio (exit 0). `npm run lint`: 0 errores, 1 warning preexistente ajeno al módulo (`components/ui/data-table.tsx:43`, TanStack Table). |

### Auditoría de puntos críticos

- **N4 cascada:** confirmado que `optionsParamsFrom` filtra `red` por `?ambito_geografico_sanitario=<id>`
  solo cuando `_ambito` tiene valor (si no, `{}` → todas las redes); `resetsOn:["_ambito"]` limpia `red`
  al cambiar el ámbito; el POST NO incluye `_ambito` (`buildPayload` salta `virtual`). Payload =
  `{codigo,nombre,red,activo}`. Coincide con `MicroredAuto` del schema.
- **N9–N11 retrocompatibilidad:** formularios sin `optionsParamsFrom` → `useWatch` deshabilitado
  (`disabled:!watchesValues`), params idénticos (`field.optionsParams`), sin observación del form. Sin
  `resetsOn` → `ResetOnParentChange` no se monta (condicional l.321), no hay reset ni useWatch de padres.
  Sin `virtual` → payload idéntico. No se detectan bucles de reset ni borrado de valores precargados: el
  `useRef` de baseline (l.387-393) evita reset en el primer render de edición.
- **N11 create Y update:** `buildPayload` es el único constructor de body y se invoca en el `onSubmit`
  compartido, por lo que `virtual` se excluye tanto en alta como en edición.

### Veredicto

**APROBADO.** Las 11 tareas cumplen su criterio de aceptación. No se requieren correcciones. Módulo
delta cerrado.
