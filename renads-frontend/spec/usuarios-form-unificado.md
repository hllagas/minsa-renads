# Spec — Usuarios: formulario de alta/edición unificado (mismo form para todo rol)

> **Estado:** BORRADOR — requiere **aprobación humana** antes de pasar a Implement.
> **Alcance:** SOLO el módulo Usuarios (`usersConfig` en `lib/usuarios/configs.ts`, pantalla
> `/usuarios/cuentas`). NO se tocan `groups`, `permissions`, `user-entity-profiles`, `students`,
> `tutors`. **NO backend** (el contrato de `apps/common/serializers.py` ya soporta todo lo aquí
> descrito; verificado — no proponer cambios de backend).
> **Antecede:** `spec/usuarios-username-dni.md` (cerrado) introdujo el condicional por
> `is_superuser` con `showWhen`. Esta spec lo **revierte** hacia un form uniforme.

---

## 1. Resumen del módulo

**Objetivo:** que el formulario de alta/edición de usuarios sea **idéntico indistintamente del rol**
(superusuario o no). Se eliminan TODOS los `showWhen` del form de usuarios; todos los campos se
muestran siempre, en un orden fijo 1–15. La ficha de usuario se marca visualmente como requerida
(asterisco) pero **sin validación dura de cliente** (el backend valida por rol). Al **crear**, el
frontend **autogenera** una contraseña segura, la prellena en el campo `password` (oculto, con
botón mostrar/ocultar y regenerar) para que el admin la vea/copie antes de guardar. En **editar**,
el campo `password` NO aparece (el cambio de contraseña sigue por la row action «Contraseña» →
`set-password`).

Pantalla cubierta: **Cuentas de usuario** (`/usuarios/cuentas`, monta `ResourceCrud` con
`usersConfig`). Row actions existentes intactas: «Entidades» (asignar alcance) y «Contraseña»
(`SetPasswordDialog`).

### Orden fijo de campos requerido (literal del usuario)

| # | name | tipo | Crear | Editar | Notas |
|---|------|------|-------|--------|-------|
| 1 | `username` | text (uppercase:false) | editable | **disabled** | read-only en backend; helper en Crear |
| 2 | `password` | custom (autogen+reveal+regenerar) | visible | **oculto** | solo en Crear |
| 3 | `first_name` | text (uppercase:false) | ✓ | ✓ | asterisco visual, `required:false` cliente |
| 4 | `last_name` | text (uppercase:false) | ✓ | ✓ | asterisco visual, `required:false` cliente |
| 5 | `tipo_documento` | select (choices estáticos) | ✓ | ✓ | ficha — asterisco visual, `required:false` |
| 6 | `numero_documento` | text | ✓ | ✓ | ficha — asterisco visual, `required:false` |
| 7 | `email` | email | ✓ | ✓ | `required:true` (backend lo exige a todos) |
| 8 | `telefono` | text (numericOnly) | ✓ | ✓ | ficha — asterisco visual, `required:false` |
| 9 | `unidad_organica` | select (`organic-units`) | ✓ | ✓ | ficha — asterisco visual, `required:false` |
| 10 | `cargo` | select (`executive-positions`) | ✓ | ✓ | ficha — asterisco visual, `required:false` |
| 11 | `tiene_ficha_usuario` | boolean | ✓ | ✓ | |
| 12 | `is_staff` | boolean | ✓ | ✓ | |
| 13 | `is_superuser` | boolean | ✓ | ✓ | |
| 14 | `is_active` | boolean (default true) | ✓ | ✓ | |
| 15 | `groups` | multiselect (`groups`) | ✓ | ✓ | al final (ocupa ancho completo) |

### Contrato backend (verificado — NO cambia)

- **Create** (`UserCreateSerializer`): `password` write-only opcional; `username` **read-only**
  (autogenerado = `numero_documento` para no-super; para super el service lo rescata de
  `initial_data`). `first_name`/`last_name` + ficha obligatorios **solo para no-super** vía
  `validate()`; super exento (la ficha se descarta). Respuesta expone `password_generada`
  (informativo; con D2 el front ya conoce la contraseña que envió).
- **Update** (`UserUpdateSerializer`): `username` **read-only** (PATCH no lo cambia). NO acepta
  `password`. Ficha `required=False` pero `allow_blank/allow_null=False` (no degradar en PATCH
  parcial). `first_name`/`last_name` presentes.
- **Read** (`UserReadSerializer`): ficha anidada bajo `perfil` (strings en `*_detalle`);
  `mapEditingToInitial` ya aplana `perfil` para el pre-relleno.

---

## 2. Lista de tareas

### Capa: Utilidad de contraseña — nuevo `lib/usuarios/password.ts`

- [x] **T1 — Crear `generarPassword()`.**
  Nuevo archivo `lib/usuarios/password.ts` que exporta `generarPassword(longitud = 16): string`.
  Debe generar una contraseña **segura**: usar `crypto.getRandomValues` (Web Crypto, disponible en
  el navegador — es código `"use client"`), longitud por defecto 16, y garantizar al menos 1
  minúscula, 1 mayúscula, 1 dígito y 1 símbolo del conjunto seguro (evitar caracteres ambiguos si
  se desea, p. ej. `l/1/I`, `O/0`, pero no es obligatorio). No usar `Math.random()`.
  **Criterio de aceptación:** función pura, sin dependencias de red; llamadas sucesivas devuelven
  cadenas distintas; toda salida cumple los 4 grupos de caracteres y tiene la longitud pedida;
  `npm run build` compila; no usa `Math.random`.

### Capa: Tipos de infraestructura CRUD — `lib/crud/types.ts`

- [x] **T2 — Verificar/soportar el campo password autogenerado.**
  El campo password con autogeneración + reveal + regenerar se implementará como
  `type: "custom"` con `render(control)` y `payloadKeys: ["password"]` (así `buildPayload` toma la
  clave `password` del form). Verificar que `FieldConfig` **ya** soporta lo necesario:
  `type: "custom"`, `render`, `payloadKeys` existen (sí, confirmado en `lib/crud/types.ts`
  líneas 120-125). **Riesgo (ver R-1):** `buildPayload` serializa las `payloadKeys` de un `custom`
  como **número** (`Number(kv)`, `resource-form.tsx` línea 123) — eso rompería la contraseña (la
  convertiría en `NaN`). Por tanto **NO** basta con `payloadKeys` sobre el genérico `custom`.
  Decidir e implementar UNA de estas dos vías (documentar la elegida en la PR):
  - **Vía A (preferida):** extender el input `type: "password"` del `ResourceForm` para soportar
    autogeneración/regenerar, controlado por nuevas props de `FieldConfig` (p. ej.
    `autogenerate?: boolean` que al montar en modo Crear prellena con `generarPassword()`, y añade
    un botón «Regenerar» junto al ojo ya existente). Requiere añadir la flag a `FieldConfig` y
    ampliar `InputFieldRow`. El campo sigue siendo `type: "password"` → `buildPayload` lo trata
    como string write-only (líneas 109-112), correcto.
  - **Vía B:** dejar `type: "custom"` pero **ajustar** `buildPayload` para NO forzar `Number()`
    cuando el valor no es numérico / cuando el custom lo indique (p. ej. una flag
    `stringPayload?: boolean` en `FieldConfig`). Más invasivo en la serialización genérica.
  **Recomendación:** Vía A (menos superficie de cambio en la serialización compartida; reutiliza el
  ojo ya presente). Señalar en la implementación qué campos de `FieldConfig` se añadieron.
  **Criterio de aceptación:** el enfoque elegido queda documentado; si se añaden flags a
  `FieldConfig`, van con JSDoc en español; la contraseña llega al payload como **string** (no
  `Number`/`NaN`).

### Capa: Componente / render del campo password (según vía elegida en T2)

- [x] **T3 — Password autogenerado con ojo + regenerar (solo Crear).**
  Implementar el control de contraseña que, en el form de **alta**:
  - Al montar, **prellena** el campo con `generarPassword()` (T1).
  - Renderiza el input **oculto (dots)** con botón **mostrar/ocultar (ojo)** — reutilizar el patrón
    ya presente en `InputFieldRow` (`Eye`/`EyeOff`, `resource-form.tsx` líneas 293-317).
  - Añade un botón **«Regenerar»** que sustituye el valor por una nueva `generarPassword()`.
  - `autoComplete="new-password"`, `data-lpignore="true"` (ya presentes en el input password
    actual — conservarlos).
  - El valor se envía en el POST como `password` (string).
  Este campo **solo** existe en `createFields`; NO en `editFields` (D3).
  **Criterio de aceptación:** al abrir «Nuevo usuario», el campo Contraseña aparece ya relleno con
  una contraseña oculta; el ojo alterna visible/oculto; «Regenerar» cambia el valor; el POST envía
  esa contraseña (verificable en Network) y el usuario creado puede iniciar sesión con ella. En
  edición no aparece ningún campo de contraseña.

### Capa: Configs / Formularios — `lib/usuarios/configs.ts`

- [x] **T4 — Reescribir `createFields` al orden 1–15, sin `showWhen`.**
  Sustituir `createFields` por la lista plana en el orden exacto de la tabla §1 (1..15). Reglas:
  - **1. `username`** — `type:"text"`, `uppercase:false`, `required:false`. Añadir helper de texto
    (ver T6) «Para usuarios no-superadmin se genera del número de documento» (input-helper-text).
    NO `disabled` en Crear (es editable; lo usa el super, el backend lo ignora para no-super).
  - **2. `password`** — el control autogenerado de T3 (vía A: `type:"password"` + flag
    `autogenerate`; vía B: `type:"custom"` + `payloadKeys:["password"]`). Solo en Crear.
  - **3. `first_name`** (label «Nombres») — `type:"text"`, `uppercase:false`, `required:false`,
    con **asterisco visual** (ver T7).
  - **4. `last_name`** (label «Apellidos») — igual que first_name.
  - **5. `tipo_documento`** — `type:"select"`, `choices: TIPO_DOCUMENTO_CHOICES`, `required:false` +
    asterisco visual.
  - **6. `numero_documento`** — `type:"text"`, `uppercase:false`, `required:false` + asterisco visual.
  - **7. `email`** — `type:"email"`, `required:true` (backend lo exige a todos).
  - **8. `telefono`** — `type:"text"`, `numericOnly:true`, `uppercase:false`, `required:false` +
    asterisco visual.
  - **9. `unidad_organica`** — `type:"select"`, `optionsEndpoint:"organic-units"`, `required:false` +
    asterisco visual.
  - **10. `cargo`** — `type:"select"`, `optionsEndpoint:"executive-positions"`,
    `optionsToLabel: cargoLabel`, `required:false` + asterisco visual.
  - **11. `tiene_ficha_usuario`** — `type:"boolean"`.
  - **12. `is_staff`** — `type:"boolean"`.
  - **13. `is_superuser`** — `type:"boolean"`.
  - **14. `is_active`** — `type:"boolean"`, `defaultValue:true`.
  - **15. `groups`** — `type:"multiselect"`, `optionsEndpoint:"groups"`, `optionsToLabel: groupLabel`.
  Separadores (`_cuenta`, `_ficha`, `_roles`): **eliminarlos** si rompen el orden pedido; se admite
  conservarlos SOLO si no alteran el orden 1–15 (recomendado: lista plana sin separadores para no
  intercalar encabezados en medio de la secuencia). Documentar la decisión.
  **NINGÚN campo** debe llevar `showWhen`.
  **Criterio de aceptación:** `createFields` produce exactamente los 15 campos en el orden 1..15;
  `grep -n "showWhen" lib/usuarios/configs.ts` = 0 coincidencias en `usersConfig`; ningún campo de
  ficha tiene `required:true`; `email` sí; el orden visual en el diálogo coincide con la tabla §1.

- [x] **T5 — Reescribir `editFields` al mismo orden 1–15 SIN `password`, con `username` disabled.**
  `editFields` = mismos campos que `createFields` **salvo**:
  - **Quitar** el campo `password` (posición 2). El resto conserva su posición relativa (1,
    3,4,5,…,15).
  - **`username`** — `disabled:true` (read-only en backend; PATCH no lo cambia). Añadir helper/estilo
    de solo-lectura. **No** enviar `username` en el payload de edición. (Nota: `buildPayload` de
    `resource-form.tsx` no excluye por `disabled`; ver R-2 — decidir cómo evitar enviarlo:
    marcar el campo `disabled` no basta. Opciones: (a) que el backend lo ignore por ser read-only
    —es el caso, `UserUpdateSerializer.username` es read-only, así que enviarlo es **inocuo**—; o
    (b) omitirlo del payload. **Preferencia:** dado que el serializer lo ignora, basta `disabled`
    visual; documentar que enviarlo no causa efecto. Si se prefiere no enviarlo, usar `virtual`
    NO sirve —quitaría el valor precargado del display—; en su lugar dejarlo `disabled` y confiar
    en el read-only del backend.)
  - Ficha (`tipo_documento`, `numero_documento`, `telefono`, `unidad_organica`, `cargo`):
    `required:false` (en edición el `ResourceForm` omite del payload los opcionales vacíos, evitando
    el 400 por `allow_blank/allow_null=False`). Asterisco visual igual que en Crear.
  - `email` `required:true`.
  **NINGÚN** `showWhen`.
  **Criterio de aceptación:** `editFields` = 14 campos (sin password) en el orden 1,3..15; el campo
  Usuario aparece **deshabilitado** con estilo de solo-lectura; editar un usuario no-super pre-rellena
  Nombres/Apellidos + ficha (vía `mapEditingToInitial`); un PATCH que no toca la ficha no la degrada
  (no 400); `grep -n "showWhen"` en `usersConfig` = 0.

- [x] **T6 — Helper text de `username` (input-helper-text) en Crear.**
  Bajo el input `username` (solo en Crear) mostrar el texto guía: «Para usuarios no-superadmin se
  genera del número de documento». Requiere soporte de texto de ayuda por campo. Si `FieldConfig`
  no tiene una prop de helper, añadir `helperText?: string` (JSDoc en español) y renderizarlo en
  `InputFieldRow` bajo el input (texto pequeño, `text-muted-foreground`). Reutilizable por otros
  campos. En Editar, el `username` va `disabled`; puede opcionalmente mostrar un helper «No editable»
  o simplemente el estilo disabled (decidir; mínimo: disabled visual claro).
  **Criterio de aceptación:** en «Nuevo usuario» aparece el helper bajo Usuario; si se añadió
  `helperText`, está documentado y no rompe otros forms; `npm run build` OK.

- [x] **T7 — Asterisco visual (required-indicators) sin bloqueo de cliente para la ficha + nombres.**
  Los campos `first_name`, `last_name`, `tipo_documento`, `numero_documento`, `telefono`,
  `unidad_organica`, `cargo` deben mostrar un asterisco «*» (indicador de requerido) **sin** activar
  la validación dura de cliente (`required:false`). Hoy el `*` en `resource-form.tsx` se renderiza
  **solo** cuando `field.required` es `true` (líneas 283-285, 382-384, 477-479). Para mostrar el
  asterisco sin bloquear el submit, añadir una prop a `FieldConfig` (p. ej.
  `requiredMark?: boolean`) que fuerza el «*» en el label independientemente de `required`, y
  usarla en el render de label de los tres tipos de control (input/select/multiselect). Aplicarla a
  los 7 campos citados (y a `email` no hace falta: ya es `required:true` → ya muestra `*`).
  **Criterio de aceptación:** los 7 campos muestran «*» en su label; al enviar el form con esos
  campos vacíos, el cliente **NO** bloquea (no aparece «Campo obligatorio.» de cliente); si el
  backend los exige (no-super), devuelve 400 y el error se muestra (ver T9/error-clarity). `email`
  conserva su `*` por `required:true`.

### Capa: Tipos/contratos — `lib/usuarios/types.ts`

- [x] **T8 — Ajustar el JSDoc de payloads (sin cambios de forma).**
  Verificar que `UserCreatePayload` (username opcional, password, ficha plana) y `UserUpdatePayload`
  (`Omit<..., "password">`) siguen siendo correctos para el form uniforme. **No** deben requerir
  cambios de forma (ya contemplan `username?` y `password`). Actualizar el JSDoc si aún describe el
  comportamiento condicional por `showWhen` (mencionar que el form es uniforme; el backend valida por
  rol). Si la respuesta del POST se consume para mostrar `password_generada`, tipar opcionalmente ese
  campo en la respuesta (informativo; con D2 el front ya conoce la contraseña — no es obligatorio).
  **Criterio de aceptación:** los payloads compilan sin cambios de forma; el JSDoc no menciona
  ocultamiento por rol en el front; `npm run build` OK.

### Capa: Verificación

- [x] **T9 — Error-clarity (validación del backend visible).**
  Verificar que, al crear un usuario **no-super** sin ficha completa, el 400 del backend se muestra
  al operador de forma legible (el `ResourceCrud`/mutation ya usa `extractApiError`). No requiere
  código nuevo salvo confirmar el comportamiento; si el error de ficha no se ve, dejarlo como
  hallazgo (no ampliar alcance).
  **Criterio de aceptación:** alta no-super sin ficha → el diálogo muestra el mensaje de error del
  backend (campo(s) faltante(s)); alta super sin ficha → 201 (backend exime). No hay bloqueo de
  cliente que impida llegar al backend.

- [x] **T10 — Limpieza de imports/símbolos muertos.**
  Al quitar todos los `showWhen`, verificar que no queden imports/helpers sin uso en
  `lib/usuarios/configs.ts` (p. ej. si algún helper existía solo para las condiciones por rol).
  Verificar también que `fichaUsuarioFields(required)` sigue teniendo sentido: como ahora la ficha
  se marca con `required:false` + asterisco visual en ambos modos, puede simplificarse a
  `fichaUsuarioFields()` sin parámetro (o mantenerse con `required:false` fijo). Documentar la
  decisión y no dejar el parámetro `required` sin uso real.
  **Criterio de aceptación:** ESLint sin warnings de variables/imports sin uso en los archivos
  tocados; `fichaUsuarioFields` no recibe un `required` que ya no aporta.

- [x] **T11 — Build.**
  Ejecutar `npm run build` y confirmar exit code 0 (los cambios en `configs.ts`, `types.ts`,
  `crud/types.ts`, `resource-form.tsx`, `password.ts` no dejan referencias colgantes).
  **Criterio de aceptación:** `npm run build` termina con exit code 0.

---

## 3. Reglas UX a cubrir (skill ui-ux-pro-max §8) — verificables

| Regla | Dónde | Verificación |
|-------|-------|--------------|
| `password-toggle` | campo `password` (Crear) | ojo mostrar/ocultar funciona; contraseña oculta por defecto (T3) |
| `required-indicators` | ficha + nombres | «*» visible sin bloqueo de cliente (T7) |
| `input-helper-text` | `username` (Crear) | helper «se genera del número de documento» visible (T6) |
| `input-type-keyboard` | `email`→email, `telefono`→numericOnly, `numero_documento`→text | teclado/inputMode correcto por campo (T4) |
| `disabled-states` | `username` (Editar) | campo deshabilitado con estilo de solo-lectura (T5) |
| `error-clarity` | alta no-super sin ficha | 400 del backend visible y legible (T9) |

---

## 4. Decisiones aprobadas (humano, vía AskUserQuestion) — respetadas

- **D1:** form uniforme, todos los campos siempre visibles; ficha con `required:false` en cliente +
  asterisco visual; backend valida por rol. Quitar TODOS los `showWhen`. → T4, T5, T7.
- **D2:** al abrir «Nuevo usuario», el front autogenera y prellena `password` (oculto + ojo +
  regenerar); se envía en el POST. → T1, T3.
- **D3:** `password` solo en Crear; en Editar no se muestra (cambio por row action «Contraseña» →
  `set-password`, ya existente). Los otros 14 campos idénticos en Crear/Editar (con `username`
  disabled en Editar). → T5.

---

## 5. Riesgos y preguntas abiertas

- **R-1 (bloqueante para vía B): `buildPayload` fuerza `Number()` en `payloadKeys` de `custom`.**
  `resource-form.tsx` línea 123 hace `out[key] = Number(kv)` para cada `payloadKey` de un campo
  `custom` con valor no vacío. Una contraseña string se convertiría en `NaN`. Por eso la vía A
  (extender `type:"password"`) es preferida; si se elige la vía B, hay que ajustar `buildPayload`
  para no numerizar la clave `password` (o añadir flag `stringPayload`). Ver T2.

- **R-2 (informativo): enviar `username` en PATCH es inocuo.**
  `UserUpdateSerializer.username` es read-only → aunque `buildPayload` lo incluya (no se excluye por
  `disabled`), el backend lo ignora. Por eso en Editar basta `disabled:true` visual; no hace falta
  excluirlo del payload. Si se quisiera excluir, NO usar `virtual` (borraría el valor mostrado).
  Confirmar en runtime que el PATCH no altera el `username`.

- **R-3 (confirmar en implementación): nuevas props de `FieldConfig`.**
  Se prevén hasta 3 flags nuevas en `FieldConfig`: `autogenerate?` (T2/T3, vía A), `helperText?`
  (T6), `requiredMark?` (T7). Cada una con JSDoc en español y renderizado en `resource-form.tsx`.
  Son genéricas (reutilizables) y no deben alterar el comportamiento de otros forms que no las usen.
  Si el implementador encuentra una forma equivalente con menos superficie, documentarla.

- **R-4 (pregunta abierta): asterisco «*» en booleanos/multiselect de ficha.**
  Los 7 campos con asterisco visual son text/select. No aplica a booleanos (`tiene_ficha_usuario`) ni
  a `groups`. Confirmado por la tabla §1. Sin acción.

- **R-5 (pregunta abierta): `password_generada` en la respuesta.**
  El backend devuelve `password_generada` en el POST. Con D2 el front ya conoce la contraseña. ¿Se
  desea mostrar un toast/diálogo post-creación con la contraseña para copiar? **No** está en el
  alcance literal del usuario (pide mostrarla **antes** de grabar, ya cubierto por T3). Dejar como
  mejora opcional; **no** implementar salvo indicación humana.

---

## 6. Referencias del contrato (backend, verificadas)

- `apps/common/serializers.py`:
  - `UserCreateSerializer` — `username` read-only (autogenerado/rescatado de `initial_data`);
    `password` write-only opcional; `validate()` exige nombres+ficha solo a no-super; respuesta con
    `password_generada`.
  - `UserUpdateSerializer` — `username` read-only; NO acepta `password`; ficha `required=False`,
    `allow_blank/allow_null=False`.
  - `UserReadSerializer` / `UserProfileReadSerializer` — ficha anidada bajo `perfil` (`*_detalle`
    strings).
- Front tocado: `lib/usuarios/configs.ts` (`usersConfig.createFields`/`editFields`),
  `lib/usuarios/types.ts` (JSDoc), nuevo `lib/usuarios/password.ts`, `lib/crud/types.ts`
  (flags nuevas), `components/crud/resource-form.tsx` (autogen/helper/requiredMark). Row action
  `set-password` y `SetPasswordDialog` (`/usuarios/cuentas/page.tsx`) **sin cambios**.

---

> **Aprobación humana requerida antes de Implement.** No iniciar la implementación hasta que un
> humano valide esta lista — en particular T2 (vía A vs B del campo password) y las flags nuevas de
> `FieldConfig` (R-3).
