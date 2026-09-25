# Validación — Usuarios: `username = DNI` + apellidos en `auth_user` (sync common 0011)

> **Fecha:** 2026-09-24 · **Validador:** agente Validator · **Spec:** `spec/usuarios-username-dni.md`
> **Veredicto:** ✅ **OK — MÓDULO CERRADO**. Sin hallazgos altos/medios. Todas las tareas (T1–T9)
> cumplen su criterio de aceptación. `npm run build` exit 0.

---

## Resumen de conformidad

| Tarea | Estado | Evidencia |
|-------|--------|-----------|
| T1 — `UserFichaRead` sin apellidos | ✅ | `types.ts:33-42` — 8 claves exactas: `tipo_documento`, `numero_documento`, `telefono`, `unidad_organica`, `cargo`, `tiene_ficha_usuario`, `unidad_organica_detalle`, `cargo_detalle`. Coinciden 1:1 con `UserProfileReadSerializer.Meta.fields` (`serializers.py:255-264`). Sin `apellido_*`. |
| T2 — `UserCreatePayload` sin apellidos; `username?` opcional | ✅ | `types.ts:73-90` — `username?: string` (74), sin apellidos. `UserUpdatePayload = Omit<...,"password">` hereda el cambio (98). JSDoc actualizado. |
| T3 — `fichaUsuarioFields()` sin apellidos | ✅ | `configs.ts:41-68` — separador `_ficha` + `tipo_documento`, `numero_documento`, `telefono`, `unidad_organica`, `cargo`, `tiene_ficha_usuario`. Sin `apellido_*`. |
| T4 — RN en `createFields` | ✅ | `configs.ts:150-184` — `username` con `showWhen: (v)=>v.is_superuser===true` (155), sin `required`; `first_name`/`last_name` `required:true` + `showWhen: (v)=>v.is_superuser!==true` (159-174); ficha mapeada con `showWhen: (v)=>v.is_superuser!==true` en cada FieldConfig incl. separador (181-184). |
| T5 — RN en `editFields` | ✅ | `configs.ts:201-232` — mismo patrón; ficha `fichaUsuarioFields(false)` mapeada con `showWhen` (229-232). |
| T6 — Label selector usuario | ✅ | `entity-endpoints.ts:41` es el catálogo `students` (endpoint `students`, línea 39), legítimo y fuera del delta 0011. No se tocó (correcto, per R-3). Ningún `toLabel` de `users` lee `apellido_paterno`. |
| T7 — Columna "Nombre" | ✅ | `configs.ts:13-14,103` — `nombreCompleto(r)` = `[r.first_name, r.last_name].filter(Boolean).join(" ") \|\| "—"`, coherente con `_display_name` del backend. No lee `perfil.apellido_*`. |
| T8 — Regenerar OpenAPI | ✅ | `schema.d.ts` — `UserProfileRead` (8142-8177) sin apellidos, 8 campos `readonly`; `UserCreate` (8066-8097) con `readonly username`, sin apellidos. |
| T9 — Build | ✅ | `npm run build` → exit 0, sin errores TypeScript. |

## Reglas de negocio

| RN | Estado | Nota |
|----|--------|------|
| RN-U1 (`username`=documento no-super; front no lo envía) | ✅ | Campo `username` oculto por `showWhen` para no-super ⇒ `buildPayload` lo excluye. |
| RN-U2 (super teclea `username` obligatorio) | ✅ | Visible solo si `is_superuser===true`; unicidad la valida el backend. |
| RN-U3 (`first_name`/`last_name` obligatorios no-super) | ✅ | `required:true` + `showWhen` no-super en create/edit. |
| RN-U4 (super exento de ficha y nombres) | ✅ | Ficha y nombres ocultos si super ⇒ no se envían. |
| RN-U5 (ficha sin apellidos) | ✅ | `UserFichaRead` y `fichaUsuarioFields` sin `apellido_*`; schema idem. |

## Auditoría de puntos críticos

- **grep `apellido` en `lib/usuarios/`:** 2 apariciones, ambas benignas:
  - `entity-endpoints.ts:41` → catálogo `students` (fuera del delta 0011, legítimo).
  - `types.ts:69` → mención en JSDoc ("los apellidos viven en `auth_user.last_name`"), no es un campo.
  - **Ningún** campo `apellido_*` en tipos/configs de `users`. Criterio de T1/T3 (0 campos) cumplido.
- **`components/usuarios/**`:** sin referencias a `apellido`.
- **`schema.d.ts`:** hits de `apellido_paterno`/`apellido_materno` (6981+, 7079+, 7640+, 7862+) pertenecen
  a modelos `Student`/derivados, NO a `UserProfileRead`/`UserCreate`. Correcto.
- **`showWhen` + `required` (R-1 del spec):** patrón confirmado seguro por el spec (ConditionalFieldWrapper
  desmonta el Controller; RHF con `shouldUnregister` no evalúa `required` de campos ocultos; `buildPayload`
  los excluye). Sin código a corregir.

## Notas informativas (sin acción)

- **R-2:** `username` no se re-deriva al editar `numero_documento` (read-only en `UserUpdateSerializer`).
  Documentado por el backend como fuera de alcance. No es cambio de front.
- La verificación funcional en runtime (toggle Superusuario, altas 201 con `username`=documento / `username`
  tecleado) queda como recomendación de smoke-test manual; no bloquea el cierre (contrato y tipos verificados).

---

**Cierre:** el módulo Usuarios queda sincronizado con la migración backend common 0011. Sin hallazgos
que impidan el cierre. **MÓDULO CERRADO.**
