# Validación — Gestión de 2FA en /perfil (`spec/2fa-gestion.md`)

**Fecha:** 2026-09-14
**Estado:** BLOQUEADO — 1 error medio pendiente de corrección (T19).

---

## Tareas verificadas: T1–T18 OK (17/19)

| Tarea | Estado | Notas |
|-------|--------|-------|
| T1 | OK | Q1 resuelta con Opción A: `MeSerializer` backend parchado, campos en `AuthUser`. |
| T2 | OK | `TotpSetupResponse`, `TotpConfirmPayload`, `EmailSetupPayload`, `DisablePayload`, `TwoFactorMessageResponse` en `lib/api/auth.ts`. Claves en español. `password` solo en tipos de escritura. |
| T3 | OK | `two_factor_enabled?: boolean` y `two_factor_method?: "TOTP" \| "EMAIL" \| ""` añadidos a `AuthUser` en `lib/auth/store.ts`. |
| T4 | OK (SKIP) | No implementado según decisión tomada (Opción A elegida). Marcado OK por skip acordado. |
| T5 | OK | `setupTotp()` → `POST /auth/2fa/setup/totp/` sin body; `confirmTotp()` → `POST /auth/2fa/confirm-totp/` con `{otp_code}`. |
| T6 | OK | `setupEmail2fa()` → `POST /auth/2fa/setup/email/`; `disable2fa()` → `api.delete("/auth/2fa/disable/", {data: payload})`. |
| T7 | OK | Estado leído de Zustand store (`user.two_factor_enabled`/`user.two_factor_method`). Sin fetch separado (Opción A). |
| T8 | OK | `useSetupTotp` no invalida nada; `useConfirmTotp` invalida `meQueryKey` (`["auth","me"]`) en `onSuccess`. |
| T9 | OK | `useSetupEmail2fa` y `useDisable2fa` invalidan `meQueryKey` en `onSuccess`. |
| T10 | OK | `TwoFactorStatus` renderiza badge "No activado" si `!enabled`; badge verde con método si `enabled`. Props tipadas. aria-label correcto. No es Client Component (correcto: solo props + render). |
| T11 | OK | `react-qr-code@2.2.0` instalado y usado (`import QRCode from "react-qr-code"`). `secret` copiable. Flujo 2 pasos. Campo OTP con `inputMode="numeric"` y `maxLength={6}`. Backtrack sin re-llamar `setupTotp`. |
| T12 | OK | Campo `password` con `type="password"` y `autoComplete="current-password"`. Muestra `userEmail`. Deshabilita botón si sin correo. |
| T13 | OK | TOTP: 1 paso (contraseña + OTP). EMAIL: 2 pasos (paso 1 con `otp_code:""` → backend envía OTP; paso 2 con OTP recibido). Distinción por estado local del componente (Q2, Opción A: sin parsear `detalle`). |
| T14 | OK | EMAIL deshabilitada si `!userEmail` (con `disabled` prop y texto descriptivo). Cierra selector antes de abrir sub-diálogo. |
| T15 | OK | Card "Seguridad" con `CardTitle`/`CardDescription` correctos. Renderizada al final (después de perfiles institucionales). Botones condicionales según `two_factor_enabled`. |
| T16 | OK | Los 3 hooks de mutación (`useConfirmTotp`, `useSetupEmail2fa`, `useDisable2fa`) invalidan `meQueryKey` en `onSuccess`. |
| T17 | OK | Sin `console.log`. `password` solo en tipos de escritura. Campos sensibles con `type="password"` y `autoComplete="current-password"`. `otp_code` con `autoComplete="one-time-code"`. |
| T18 | OK | `extractApiError` usado en todos los `onError`. Botones con `isPending` para prevenir dobles peticiones. Errores de red cubiertos por `extractApiError` (línea 67: "No se pudo conectar con el servidor."). |
| T19 | **FALLO** | Ver hallazgo H1 abajo. |

---

## Hallazgos

### H1 — ERROR MEDIO — `totp-setup-dialog.tsx:47` — `react-hooks/set-state-in-effect`

**Archivo:** `components/auth/totp-setup-dialog.tsx:47`
**Regla:** `react-hooks/set-state-in-effect`
**Mensaje ESLint:** "Avoid calling setState() directly within an effect"

**Código afectado:**
```ts
useEffect(() => {
  if (!open) return;
  setStep("scan");   // <-- línea 47: setState síncrono en efecto
  setOtpCode("");
  setError("");
  setupM.mutate(undefined, { ... });
}, [open]);
```

**Problema:** Tres llamadas a `setState` síncronas dentro del cuerpo del efecto (no en callbacks). El linter de React prohíbe este patrón porque puede causar renders en cascada.

**Corrección sugerida:** Mover el reset de estado a la función `onOpenChange` recibida como prop (cuando `value === false`) y al momento de apertura usando un estado derivado o inicializando el estado con un `key` prop en el `Dialog`. Alternativa mínima: extraer el reset a una función separada llamada fuera del efecto al abrir, por ejemplo inicializando los estados en la declaración (`useState<Step>("scan")`) y reseteando en `onOpenChange`:

```ts
function handleOpenChange(value: boolean) {
  if (!value) {
    setStep("scan");
    setOtpCode("");
    setError("");
  }
  onOpenChange(value);
}
// En el useEffect, solo dejar la mutación:
useEffect(() => {
  if (!open) return;
  setupM.mutate(undefined, { ... });
}, [open]);
```

**Impacto en criterio T19:** El error es nuevo (introducido por este módulo; el archivo no existía en HEAD). Bloquea T19.

---

## Build

`npm run build` completa sin errores. El error es solo de lint (eslint), no bloquea compilación TS.

---

## Conclusión

El módulo está funcionalmente completo (T1–T18 correctamente implementados). Hay **1 error de lint medio (H1)** introducido en `totp-setup-dialog.tsx` que impide cerrar T19. Una vez corregido H1 y verificado que `npm run lint` no reporta nuevos errores, el módulo puede marcarse como cerrado.
