# Validación — Módulo Gestión de Usuarios (`/usuarios`)

> Validación contra `spec/usuarios.md` (APROBADO) y `docs/api-usuarios.md`. §6 (R-Q1..R-Q5)
> autoritativa. Comprobaciones técnicas: `npx tsc --noEmit` (limpio), `npm run lint` (solo 2
> hallazgos PRE-EXISTENTES), `npm run build` (OK, 5 rutas `/usuarios` generadas, sin regresión).

## Veredicto final: APROBADO

El módulo cumple el spec y el contrato. No hay hallazgos altos ni medios. Un (1) hallazgo bajo
no bloqueante (informativo). Todas las tareas T1–T21 marcadas en `spec/usuarios.md`.

## Estado por tarea

| Tarea | Estado | Nota |
|-------|--------|------|
| T1 Tipos | OK | `lib/usuarios/types.ts`: claves sin traducir; `password` solo en `UserCreatePayload`/`SetPasswordPayload`, ausente en `User`/`UserUpdatePayload` (`Omit<...,"password">`). `UserEntityProfile` = `id,usuario,tipo_contenido,id_objeto,grupo,activo` (R-Q1). |
| T2 password field | OK | `FieldType` incluye `"password"`; `resource-form.tsx:125` → `type="password"` + `autoComplete="new-password"`. |
| T3 multiselect | OK | `"multiselect"` en `FieldType`; default `[]`; render `MultiEntityCombobox`. |
| T4 create/editFields | OK | `ResourceConfig.createFields`/`editFields` opcionales; `resource-crud.tsx:251-255` elige el set según crear/editar; fallback a `fields`. |
| T5 rowActions + soft delete | OK | `RowAction` tipado; render junto a Editar/Eliminar solo si `canWrite`; copy `deleteActionLabel`/`softDelete`/`deleteSuccessMessage`. |
| T6 MultiEntityCombobox | OK | `components/form/multi-entity-combobox.tsx`: search server-side, resuelve labels de ids ausentes (`getResourceItem`), badges removibles, reusa `lib/api/lookup.ts`. |
| T7 buildPayload | OK | `resource-form.tsx:44-52`: multiselect siempre array (incl. `[]`); password solo si presente y no vacío, nunca impreso. |
| T8 set-password API + hook | OK | `lib/api/users.ts` `setUserPassword` (Axios solo en `lib/api/`); `useSetPassword` invalida `resourceKeys.all("users")`. |
| T9 usersConfig | OK | endpoint `users`, `defaultOrdering:"id"`, `requireSuperuser`, `softDelete`, `deleteActionLabel:"Desactivar"`; columnas y filtros `is_active`/`is_superuser`/`is_staff`/`groups`; createFields con `password`, editFields sin. |
| T10 página cuentas | OK | guard superusuario + `rowActions` "Contraseña" + `SetPasswordDialog`; enlace ← Gestión de Usuarios. |
| T11 groupsConfig + página | OK | `name` + `permissions` multiselect (label `name (app_label.codename)`); columna nº de permisos; `defaultOrdering:"name"`, `requireSuperuser`. |
| T12 permissionsConfig | OK | `readOnly:true`, `defaultOrdering:"id"` (R-Q3), filtro `content_type__app_label` texto (R-Q2, sin `content_type` id), columnas name/codename/app_label/model. |
| T13 set-password dialog | OK | `components/usuarios/set-password-dialog.tsx`: confirmación cliente, no envía si no coinciden, toast "Contraseña actualizada.", error vía `extractApiError`; estado local (no Zustand/Query). |
| T14 índice | OK | `app/(app)/usuarios/page.tsx` tarjetas por acceso; superuser ve 4, `Administrador RENADS` no-super ve solo Perfiles. |
| T15 páginas + configs | OK | `lib/usuarios/configs.ts` exporta las 4 configs; 4 páginas con guard + ← Usuarios. |
| T16 perfiles | OK | `disableCreate` + `// TODO(v2 content-types)`; editFields solo `activo`; `tipo_contenido`/`id_objeto`/`usuario`/`grupo` solo lectura; aviso visible de alta diferida; `writeRoles:["Administrador RENADS"]`. |
| T17 nav | OK | `app-shell.tsx:47` `/usuarios` con `roles:["Administrador RENADS"]`; `userHasRole` da true a superusuario. |
| T18 isSuperuser + guards | OK | `lib/auth/store.ts:75` `isSuperuser`; `requireSuperuser` condiciona `canWrite`/`canCreate` (`resource-crud.tsx:56-60`); `UsuariosAccessGuard` superuser/admin con placeholder "No autorizado". |
| T19 errores/estados | OK | reusa manejo de `ResourceCrud` (reintentar, toasts `extractApiError`); errores backend legibles. |
| T20 seguridad password | OK | `password` ausente de tipos de lectura/tablas; sin `console.*` de password; inputs `type=password`; no en Zustand ni cache. |
| T21 lint/typecheck | OK | tsc limpio; lint sin hallazgos nuevos del módulo. |

## Contrato — sin discrepancias

- `users`: create≠edit, DELETE=desactivar (copy «Desactivar»), `set-password` en `lib/api/`, filtros y `groups_detalle` solo lectura. OK.
- `groups`: `name`+`permissions` (ids), `permissions_detalle` solo lectura. OK.
- `permissions`: solo lectura, R-Q2/R-Q3 respetados. OK.
- `user-entity-profiles`: R-Q1/R-Q4 respetados (alta diferida). OK.
- R-Q5: gating coherente nav/rutas/escritura. OK.

## Hallazgos

- BAJO (informativo) — `lib/usuarios/configs.ts:156` `permissionsConfig` no fija `requireSuperuser:true`
  (el spec R-Q5 dice "usuarios/roles/permisos lo activan"). Funcionalmente equivalente: `readOnly:true`
  ya desactiva toda escritura y la ruta exige superusuario vía `UsuariosAccessGuard`. No es defecto;
  añadir el flag por consistencia documental queda opcional.

## Sanidad técnica

- `npx tsc --noEmit`: sin errores.
- `npm run lint`: solo PRE-EXISTENTES — `components/layout/theme-toggle.tsx:18` (set-state-in-effect) y
  `components/ui/data-table.tsx:43` (incompatible-library). Ningún hallazgo nuevo del módulo.
- `npm run build`: OK; rutas `/usuarios`, `/usuarios/cuentas`, `/usuarios/roles`, `/usuarios/permisos`,
  `/usuarios/perfiles` generadas; `/convenios/maestros` y `/catalogos` intactos (sin regresión por la
  extensión de `ResourceCrud`/`resource-form`; todos los campos nuevos de `ResourceConfig` son opcionales).

## Conclusión

Módulo **CERRADO / APROBADO**. Sin acciones requeridas para Implement.
