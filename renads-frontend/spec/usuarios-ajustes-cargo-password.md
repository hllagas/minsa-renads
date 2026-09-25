# Spec — Usuarios: cargo en cascada por unidad orgánica + política de contraseña

> **Estado:** IMPLEMENTADO — decisiones aprobadas por humano (AskUserQuestion). Ajustes menores
> sobre el módulo ya cerrado (`spec/usuarios-form-unificado.md`).
> **Alcance:** `/usuarios/cuentas` (frontend) + política de alta en `apps/common` (backend).

---

## 1. Cambios solicitados (usuario)

1. En el form de usuario, el campo **Cargo** debe listarse **según la Unidad Orgánica** previamente
   seleccionada (cascada).
2. Al generar la contraseña, el tamaño debe ser **12 caracteres** (antes 16).
3. La **edición NO debe cambiar la contraseña**. Verificado: ni el front (`editFields` sin
   `password`; `buildPayload` no lo envía) ni el back (`UserUpdateSerializer`/`perform_update` no
   tocan el hash; sin signals) la modifican. La causa de la percepción era la política de onboarding:
   el alta marcaba `debe_cambiar_password=True` → el usuario debía cambiarla en el primer login.
   **Decisión aprobada:** la contraseña autogenerada en el alta por administrador es **definitiva**
   (`debe_cambiar_password=False`); solo cambia por la acción «Restablecer contraseña» o por el
   propio usuario.

---

## 2. Tareas

- [x] **T1 — Cascada Cargo ← Unidad Orgánica (frontend).**
  En `lib/usuarios/configs.ts`, campo `cargo` de `fichaUsuarioFields()` (compartido por alta y
  edición): añadir
  `optionsParamsFrom: (v) => v.unidad_organica ? { unidad_organica: String(v.unidad_organica) } : {}`
  + `resetsOn: ["unidad_organica"]`. Filtra `executive-positions?unidad_organica=<id>`.
  **AC:** al elegir una Unidad Orgánica, el combo Cargo lista solo los cargos de esa unidad; al
  cambiar la unidad, el cargo se resetea. En **edición**, el cargo pre-cargado NO debe borrarse en el
  montaje inicial (solo al cambiar la unidad por acción del usuario) — verificar en runtime.

- [x] **T2 — Largo de contraseña = 12 (frontend).**
  En `lib/usuarios/password.ts`, `generarPassword(longitud = 12)` (antes 16) + JSDoc. Ambos call
  sites (`resource-form.tsx` líneas ~348, ~419) usan `generarPassword()` sin argumento → heredan el
  default.
  **AC:** la contraseña autogenerada en el alta tiene 12 caracteres y conserva ≥1 de cada grupo
  (minúscula/mayúscula/dígito/símbolo).

- [x] **T3 — Contraseña de alta admin definitiva (backend).**
  En `renads-api/apps/common/services.py`, `crear_usuario_con_perfil`: `debe_cambiar_password=False`
  (antes `True`). Solo afecta el alta admin `/users/` (único caller; el onboarding del interno usa
  otro flujo y conserva su contraseña temporal).
  **AC:** un usuario creado por el admin inicia sesión con la contraseña autogenerada sin que se le
  exija cambiarla en el primer login; el cambio solo ocurre vía `set-password` o por el usuario.

- [x] **T4 — Build.** `npm run build` exit 0 (frontend). Backend sin migración (cambio de valor en
  runtime, no de esquema).

---

## 3. Riesgos

- **R-1 (T1, verificar runtime):** `resetsOn` en edición podría borrar el `cargo` pre-cargado si se
  dispara en el montaje. El patrón `resetsOn` debe resetear solo ante cambio del padre por el usuario,
  no en la hidratación inicial. Confirmar editando un usuario con cargo asignado (no debe vaciarse al
  abrir el diálogo).
- **R-2 (T3, política):** relajar `debe_cambiar_password` reduce la fricción de onboarding pero baja
  la exigencia de rotación inicial. Es decisión de producto (aprobada). El reset por «Restablecer
  contraseña» (`confirmar_reset_password`) sigue poniendo `debe_cambiar_password=False`; coherente.
