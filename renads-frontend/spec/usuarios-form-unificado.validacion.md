# Validación — Usuarios: formulario de alta/edición unificado

> **Veredicto:** **OK — MÓDULO CERRADO.** Sin hallazgos altos/medios. Las 11 tareas (T1–T11)
> cumplen su criterio de aceptación. `npm run build` → exit 0. Sin regresiones de lint nuevas.
> Fecha: 2026-09-24.

## Resultado por tarea

| Tarea | Estado | Evidencia |
|-------|--------|-----------|
| T1 | OK | `lib/usuarios/password.ts`: `generarPassword(longitud=16)` usa `crypto.getRandomValues` (NO `Math.random`), `randomInt` sin sesgo de módulo, garantiza 4 grupos (1 min + 1 may + 1 dígito + 1 símbolo) y completa con `TODOS`, mezcla Fisher–Yates seguro. Función pura, sin red. |
| T2 | OK | Vía A elegida (preferida): campo sigue `type:"password"` → `buildPayload` lo trata como string write-only (`resource-form.tsx:112-115`), sin `Number()`. 3 flags nuevas en `FieldConfig` con JSDoc en español (`autogenerate`, `helperText`, `requiredMark`, `types.ts:104-121`). |
| T3 | OK | `InputFieldRow`: `autogen = type==="password" && autogenerate && isCreate`. `AutogenPasswordPrefill` prellena solo al montar vía `useRef` (no sobrescribe ediciones manuales). Botón «Regenerar» (`RefreshCw`) + ojo `Eye/EyeOff`. `autoComplete="new-password"`, `data-lpignore`. Solo en `createFields`. |
| T4 | OK | `createFields` = 15 campos en orden exacto 1..15 (username, password, first_name, last_name, tipo_documento, numero_documento, email, telefono, unidad_organica, cargo, tiene_ficha_usuario, is_staff, is_superuser, is_active, groups). Sin separadores. Ficha `required:false`; `email` `required:true`. |
| T5 | OK | `editFields` = 14 campos (sin password), orden relativo 1,3..15. `username` con `disabled:true` + helper «No editable». Ficha `required:false`+`requiredMark`. `mapEditingToInitial` aplana `perfil`. |
| T6 | OK | `helperText` en `username` (create): «Para usuarios no-superadmin se genera del número de documento». Renderizado bajo el input en `InputFieldRow` (`text-xs text-muted-foreground`). |
| T7 | OK | `requiredMark:true` en first_name, last_name, tipo_documento, numero_documento, telefono, unidad_organica, cargo. `showAsterisk = required===true \|\| requiredMark===true` en input/select/multiselect. Sin `rules.required` para estos → no bloquea. `email` conserva `*` por `required:true`. |
| T8 | OK | `types.ts`: JSDoc de `UserCreatePayload`/`UserUpdatePayload` describe form uniforme, sin mención a ocultamiento por rol; `UserUpdatePayload = Omit<..., "password">`. Compila. |
| T9 | OK | Ningún bloqueo de cliente en ficha; el 400 del backend llega vía `ResourceCrud`/`extractApiError` (infra existente). Cliente no impide llegar al backend. |
| T10 | OK | `fichaUsuarioFields()` sin parámetro `required`. Sin imports/símbolos muertos en los archivos tocados (ESLint limpio sobre ellos). |
| T11 | OK | `npm run build` → exit 0. |

## Auditoría de puntos críticos

- **Orden T4/T5:** confirmado literal. createFields=15, editFields=14 (sin password), username disabled en edición.
- **Sin `showWhen` funcional:** `grep showWhen lib/usuarios/configs.ts` → 1 sola coincidencia, en comentario (línea 172). 0 funcionales.
- **Ficha sin bloqueo de cliente:** los 7 campos `required:false`+`requiredMark:true`; `email` `required:true`. Correcto.
- **Password seguro:** `crypto.getRandomValues`, 4 grupos garantizados, prellenado solo en create y sin sobrescribir ediciones manuales (`AutogenPasswordPrefill` con `useRef`).
- **Flags genéricas no invasivas:** asterisco solo con `required===true || requiredMark===true`; `helperText` solo si definido; `autogen` solo con `type:"password" && autogenerate && isCreate`. No alteran otros forms.
- **username en edit inocuo:** `UserUpdateSerializer.username = serializers.CharField(read_only=True)` (`apps/common/serializers.py:575`). Enviarlo en PATCH no altera nada. Confirmado.
- **set-password/SetPasswordDialog intactos:** `app/(app)/usuarios/cuentas/page.tsx` conserva las row actions «Entidades» y «Contraseña» + `SetPasswordDialog`. Sin cambios.

## Sanidad técnica

- **Build:** `npm run build` exit 0 (Next.js 16.2.9, TypeScript OK).
- **Lint:** `npx eslint` sobre los 5 archivos tocados → 0 errores/warnings. El `npm run lint` global reporta 7 errores preexistentes, TODOS en `components/campos-clinicos/*` (setState en useMemo/effect) + warnings de baseline (data-table.tsx, lib/catalogos/entities.ts, lib/internados/persons.ts). Ninguno introducido por este cambio.
- Sin referencias colgantes.

## Conclusión

Módulo **CERRADO**. Implementación conforme al spec y a las decisiones D1/D2/D3. Sin acciones pendientes para Implement.
