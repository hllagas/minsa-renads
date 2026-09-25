# Validación — Usuarios: cargo en cascada + política de contraseña

> **Veredicto: OK — MÓDULO CERRADO.** Sin hallazgos altos/medios. T1–T4 verificados y marcados.
> Validado: 2026-09-25.

## Resultado por tarea

- **T1 — Cascada Cargo ← Unidad Orgánica** ✅
  - `lib/usuarios/configs.ts:87-89`: campo `cargo` tiene
    `optionsParamsFrom: (v) => v.unidad_organica ? { unidad_organica: String(v.unidad_organica) } : {}`
    + `resetsOn: ["unidad_organica"]`.
  - `fichaCargo` y `fichaUnidadOrganica` se destructuran de `fichaUsuarioFields()` (`:105-111`) y se
    reutilizan **la misma instancia** en `createFields` (`:211-212`) y `editFields` (`:247-248`) → el
    filtro y el reset aplican en alta y edición.
  - `SelectFieldRow` (`resource-form.tsx:493-529`) computa `dynamicParams` desde `optionsParamsFrom`
    con `useWatch` → `executive-positions?unidad_organica=<id>` (o sin filtro si no hay unidad).

- **R-1 (crítico) — reset NO borra el cargo precargado en edición** ✅ MITIGADO
  - `ResetOnParentChange` (`resource-form.tsx:620-646`) usa `previous.current === null` como
    centinela de primer render: en el montaje **solo fija la línea base** (`previous.current =
    parentValues`) y retorna **sin** llamar `onReset`. El reset (`f.onChange(null)`) se dispara
    únicamente cuando `parentValues` cambia respecto al valor previo (comparación por índice,
    `:638`). Al abrir «Editar» un usuario con `unidad_organica`+`cargo` precargados, el componente
    no vacía el cargo en la hidratación. R-1 no se materializa; se comporta según AC.
  - El watch de padres (`useWatch({ control, name: parents })`) recibe los `defaultValues`
    hidratados desde `initial` (`useForm defaultValues`, `:159-163`), por lo que la línea base ya
    refleja la unidad precargada. Correcto.

- **T2 — Largo de contraseña = 12** ✅
  - `lib/usuarios/password.ts:49`: `generarPassword(longitud = 12)` (JSDoc actualizado `:44-48`).
  - `total = Math.max(4, ...)`; garantiza ≥1 minúscula/mayúscula/dígito/símbolo (`:52`) y rellena
    hasta 12 con `TODOS` (`:54`) → min efectivo 4 ≤ 12, se preservan los 4 grupos.
  - Ambos call sites usan `generarPassword()` sin argumento → heredan el default 12:
    `resource-form.tsx:348` (botón «Regenerar») y `:419` (`AutogenPasswordPrefill` al montar el alta).

- **T3 — Contraseña de alta admin definitiva (backend)** ✅
  - `apps/common/services.py:421-424`: `crear_usuario_con_perfil` hace
    `get_or_create(UserSecurity)` y setea `debe_cambiar_password=False` +
    `password_changed_at=now()`.
  - **Único caller del alta admin `/users/`:** `UserCreateSerializer.create` lo invoca en
    `serializers.py:559`. No hay otros callers de negocio (los demás matches son docstrings/specs).
  - **Onboarding del interno NO afectado:** usa `apps/internados/services.py:329`
    (`seguridad.debe_cambiar_password = True`) en su propio flujo, no `crear_usuario_con_perfil`.
  - **Edición no cambia el hash:** `UserUpdateSerializer` (`serializers.py:565-679`) no declara
    campo `password` (ausente de `Meta.fields`); su `update()` solo setea atributos de
    `validated_data` + perfil + groups; nunca llama `set_password`. `perform_update`
    (`views.py:223`) delega en el serializer. Intactos.

- **T4 — Build** ✅ `npm run build` → **exit 0**. Todas las rutas compilan (incl. `/usuarios/cuentas`).

## Notas
- R-2 (política de producto: `debe_cambiar_password=False` relaja rotación inicial) es decisión
  aprobada; coherente con el reset por «Restablecer contraseña».
- Sin migración de esquema en backend (cambio de valor en runtime).
