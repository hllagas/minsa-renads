# Validación — Frontend PK string (executing-units + infra)

> Fecha: 2026-09-08 · **Fase 0 + Fase A IMPLEMENTADAS y verificadas** (tsc + lint limpios).
> **Fase B (ipress) GATED** — bloqueada por el backend (migración `promote` falla).

## Fase 0 — Infra PK `string|number` (retrocompatible)

| Tarea | Resultado |
|-------|-----------|
| F0-1 | `createResourceApi.retrieve/update/remove` + `resourceKeys.detail` aceptan `string|number`. `HasId.id` se mantuvo `number` (back-compat); la PK textual se resuelve vía `pkField` + index signature de `WithId`. ✅ |
| F0-2 | `useDetail/useUpdate/useRemove` aceptan `string|number`. ✅ |
| F0-3 | `ResourceConfig.pkField?` + `FieldConfig`/`FilterConfig` `optionsValueKey`+`optionsSearchable`. ✅ |
| F0-4 | `ResourceCrud` usa `pkOf(row)=row[pkField]` para editar/eliminar/keyear; ordering fallback a `pkField`. ✅ |
| F0-5 | `data-table` keyea por índice (no `getRowId`) → sin cambios necesarios. ✅ |
| F0-6 | `getResourceItem(endpoint, id: string|number)`. ✅ |
| F0-7 | `EntityCombobox<T extends string|number = number>` + prop `valueKey`. Genérico → los usos numéricos infieren `number` (back-compat total). ✅ |
| F0-8 | `MultiEntityCombobox<T … = number>` + `valueKey`. ✅ |
| F0-9 | `resource-form`: `optionsValueKey + optionsSearchable` → `EntityCombobox` con `valueKey` (búsqueda); solo `optionsValueKey` → `CodeSelect`. ✅ |

## Fase A — executing-units (backend LISTO)

| Tarea | Resultado |
|-------|-----------|
| A-1 | Config CRUD reescrita: `pkField:"codigo"`, `defaultOrdering:"codigo"`, `codigo` requerido (create) / `disabled` (edit), `ambito_geografico_sanitario` columna/filtro/campo; fuera logo/tipo_organo/gobierno_regional/direccion/ubigeo. ✅ |
| A-2 | `[entidad]/page.tsx`: quitada la rama `injectOrganoParam` de executing-units (tipo_organo ya no existe); universities intacto. ✅ |
| A-3 | ipress `unidad_ejecutora` (campo + filtro) → `optionsValueKey:"codigo"` + `optionsSearchable`. ✅ |
| A-4 | `convention-fields` `unidad_ejecutora` → `optionsValueKey:"codigo"` + `optionsSearchable`. ✅ |
| A-5 | `convenio-create-form` (custom): `EntityCombobox valueKey="codigo"`, value string, payload sin `Number()`. ✅ |
| A-6 | representantes paso 2: `entidadId: string|number`, `valueKey` por tipo (executing-units→`codigo`; ipress→`codigo_renipress` en B); diálogo `idObjeto: string|number`. ✅ |
| A-7 | user-entity-profiles: `ENTITY_ENDPOINTS.valueKey` (UE `codigo`, ipress `codigo_renipress`); `assign-profiles-dialog` `ids: (string|number)[]` + `valueKey`; payload `ids` string|number. ✅ |
| A-8 | `storage.ts`: executing-units fuera de `LOGO_ENTITIES`. ✅ |
| A-9 | `gen:api` **diferido** (P3) hasta desbloquear B — el front usa tipos genéricos `WithId`, no requiere regen para A. schema.d.ts congelado (executing-units viejo) sin romper build. ⏸ |

**Fase D:** `docs/api-catalogos.md` (executing-units PK codigo + ambito; health-geographic-scopes gobierno_regional) + `CLAUDE.md` (fila refactor + nota de infra PK string). ✅

**Verificación:** `npx tsc --noEmit` limpio; `npm run lint` sin errores nuevos (2 pre-existentes en `university-careers/page.tsx`).

## Fase B — ipress (GATED) — NO implementada
Bloqueada: `migrate` del backend falla (`foreign key mismatch - interno referencing ipress`; 0047/0022/0007 sin aplicar). Tareas B-1..B-5 listas para ejecutar al desbloqueo.

## Gaps de backend detectados (fuera del alcance del front)
1. **Migración ipress rota** (`convenios/0047` + `internados/0022` + `actividades/0007`): `foreign key mismatch` en rebuild SQLite. Bloquea Fase B y un `migrate` limpio.
2. **`OrganRepresentative.id_objeto` sigue `PositiveIntegerField`**: los refactors de PK string (executing-units, ipress) NO lo actualizaron (solo `UserEntityProfile`/`AuditLog`). → registrar un representante de una **Unidad Ejecutora** o **IPRESS** enviará un `id_objeto` string (codigo) que el backend rechazará (400). El front ya emite el valor correcto (`valueKey`); requiere que el backend haga `OrganRepresentative.id_objeto` (e history) `CharField`, como se hizo con `UserEntityProfile`.
