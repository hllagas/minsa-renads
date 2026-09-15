# Spec — Gestión de 2FA en el perfil del usuario (`/perfil`)

> **Estado: PENDIENTE DE APROBACIÓN HUMANA.**
> Flujo SDD: `spec` → **(APROBACIÓN HUMANA REQUERIDA)** → `implement` → `validator`.
> Fuente de verdad: `apps/common/{views,serializers,services}.py` (verificado en redacción del spec).
> Pantallas afectadas: `/perfil` (ampliación), sin módulos nuevos de navegación.

---

## 1. Resumen del módulo

Amplía la página **`/perfil`** (ya existente en `app/(app)/perfil/page.tsx`) con una sección
**"Seguridad"** que permite a cualquier usuario autenticado gestionar su segundo factor de
autenticación (2FA): activar, confirmar y desactivar TOTP o EMAIL 2FA.

### Pantallas que cubre

- `/perfil` — agrega tarjeta "Seguridad" con el widget de gestión de 2FA debajo de las tarjetas
  existentes (identidad, roles, perfiles institucionales). No se modifica la estructura actual.

### Alcance por rol

Accesible a **todos los roles** (el backend requiere solo `IsAuthenticated`). No hay acciones
administrativas sobre otros usuarios.

### Fuera de alcance

- Flujo de 2FA durante el **login** (`/auth/2fa/verify/`) — ya implementado en Auth.
- `resend-otp` para login pendiente — ya implementado en Auth.
- Gestión de 2FA de **otros usuarios** (superusuario) — no existe endpoint backend para esto.
- Tests automatizados (no hay runner configurado).

---

## 2. Hallazgos de contrato (verificados contra el backend)

### 2.1 `GET /auth/me/` — estado 2FA no expuesto

`MeSerializer` (verificado en `apps/common/serializers.py`, líneas 75–163) **no expone**
`two_factor_enabled` ni `two_factor_method`. Estos campos viven en el modelo `UserSecurity`
(tabla separada `seguridad_usuario`), no en `User`, y el serializer no los incluye.

**Consecuencia:** el frontend no puede conocer el estado 2FA actual del usuario sin un endpoint
dedicado. Se requiere un endpoint nuevo `GET /auth/2fa/status/` o ampliar `MeSerializer`.
Ver §6 (Pregunta abierta Q1).

### 2.2 `DELETE /auth/2fa/disable/` — acepta JWT (IsAuthenticated)

`TwoFactorDisableView` usa `permission_classes = [IsAuthenticated]` (views.py línea 668),
por lo que la desactivación se hace con el Bearer token del usuario activo, **no** con
`session_token`. El flujo para EMAIL es:

1. Primer `DELETE` sin `otp_code` en curso → el backend genera y envía el OTP por correo y
   devuelve HTTP 200 con `{"detalle": "Se ha enviado un código..."}` (views.py líneas 688–699).
2. Segundo `DELETE` con `otp_code` recibido → desactiva el 2FA y devuelve `{"detalle": "Doble factor desactivado."}`.

El front debe detectar si la primera respuesta es HTTP 200 con `otp_code` en cuerpo o el mensaje
de instrucción para mostrar el campo OTP en el diálogo.

### 2.3 `POST /auth/2fa/resend-otp/` — requiere `session_token`, NO JWT

`TwoFactorResendView` usa `permission_classes = [AllowAny]` y espera `{ session_token }` (no JWT).
Solo aplica para el login diferido, **no** para el flujo de desactivación con usuario autenticado.
En el flujo de desactivación el re-envío no existe como endpoint separado: el propio primer
`DELETE` genera el OTP. No se debe llamar `resend-otp` desde la gestión de perfil.

### 2.4 `POST /auth/2fa/setup/totp/` — devuelve `{otpauth_uri, secret}` (verificado)

El secreto base32 se expone **solo** en esta respuesta (nunca en GET). El frontend debe generar
el QR a partir de `otpauth_uri` usando una librería cliente (p.ej. `qrcode.react`). La librería
`qrcode` (Node) no es válida aquí porque es SSR; usar `qrcode.react` o `react-qr-code`.

---

## 3. Tareas

### A. Endpoint de estado 2FA (bloqueo: Q1)

- [x] **T1 — Resolver cómo exponer `two_factor_enabled`/`two_factor_method` al frontend.**
  La tarea es **coordinación con el backend**, no escritura de código front. Dos opciones:
  - **Opción A (preferida):** añadir `two_factor_enabled` y `two_factor_method` a `MeSerializer`
    para que `GET /auth/me/` los devuelva. El frontend los lee del caché de TanStack Query
    (key `["me"]`) sin petición adicional.
  - **Opción B (sin cambio backend):** nuevo endpoint `GET /auth/2fa/status/` (IsAuthenticated)
    que devuelve `{ two_factor_enabled: bool, two_factor_method: "TOTP"|"EMAIL"|"" }`.
  - **Criterio de aceptación:** el frontend puede mostrar el estado 2FA actual (activo/inactivo +
    método) antes de que el usuario haga clic en ningún botón.
  - **Bloquea:** T5 (widget de estado), T7 (botón desactivar), T10 (hook de estado).
  - **Nota:** hasta que Q1 se resuelva, los demás hooks/componentes pueden asumir Opción A
    (campos en `AuthUser`) o usar un fetch separado. Implementar según la decisión tomada.

### B. Tipos / contrato

- [x] **T2 — Tipos TS para el contrato 2FA.**
  En `lib/api/auth.ts` (ampliar el archivo existente) o en `lib/auth/two-factor.ts`:
  ```typescript
  // Respuesta de GET /auth/2fa/status/ (Opción B) o de GET /auth/me/ ampliado (Opción A)
  interface TwoFactorStatus {
    two_factor_enabled: boolean;
    two_factor_method: "TOTP" | "EMAIL" | "";
  }

  // POST /auth/2fa/setup/totp/ → { otpauth_uri, secret }
  interface TotpSetupResponse {
    otpauth_uri: string;
    secret: string;
  }

  // POST /auth/2fa/confirm-totp/ body
  interface TotpConfirmPayload {
    otp_code: string; // 6 dígitos
  }

  // POST /auth/2fa/setup/email/ body
  interface EmailSetupPayload {
    password: string;
  }

  // DELETE /auth/2fa/disable/ body
  interface DisablePayload {
    password: string;
    otp_code: string; // campo presente siempre; vacío en la primera llamada EMAIL
  }

  // Respuesta de éxito genérica del backend (detalle textual)
  interface TwoFactorMessageResponse {
    detalle: string;
  }
  ```
  - **Criterio:** compila en TS strict; claves exactas del backend en español (`otp_code`,
    `otpauth_uri`, `two_factor_enabled`, etc.); `password` solo en tipos de escritura; nunca en
    lectura.
  - **Referencia:** `apps/common/serializers.py` líneas 811–876; `apps/common/views.py` líneas
    524–565, 597–613, 659–707.

- [x] **T3 — Ampliar `AuthUser` con campos 2FA (condicional a Q1 Opción A).**
  Si se elige Opción A, añadir a `AuthUser` en `lib/auth/store.ts`:
  ```typescript
  two_factor_enabled?: boolean;
  two_factor_method?: "TOTP" | "EMAIL" | "";
  ```
  - **Criterio:** `AuthUser` compila; los campos son opcionales (son nuevos, evita romper
    usuarios sin `UserSecurity`); `MeSerializer` del backend expone los campos; el hook `useMe`
    (o equivalente) refresca el store tras activar/desactivar 2FA.
  - **No aplicar si se elige Opción B** (habrá un fetch separado).

### C. Capa API

- [x] **T4 — Función de estado 2FA (condicional a Q1 Opción B).**
  Si se elige Opción B, añadir en `lib/api/auth.ts`:
  ```typescript
  export async function fetch2faStatus(): Promise<TwoFactorStatus> {
    const { data } = await api.get<TwoFactorStatus>("/auth/2fa/status/");
    return data;
  }
  ```
  - **Criterio:** Axios solo dentro de `lib/api/`; si el endpoint aún no existe en el backend,
    dejar la función pero no llamarla hasta que el backend la exponga.
  - **No implementar si se elige Opción A.**

- [x] **T5 — Funciones API para setup TOTP.**
  En `lib/api/auth.ts`:
  ```typescript
  // Genera el secreto TOTP: POST /auth/2fa/setup/totp/
  export async function setupTotp(): Promise<TotpSetupResponse>

  // Confirma el secreto TOTP: POST /auth/2fa/confirm-totp/
  export async function confirmTotp(payload: TotpConfirmPayload): Promise<TwoFactorMessageResponse>
  ```
  - **Criterio:** Axios solo en `lib/api/`; `setupTotp` no acepta body (body vacío o `{}`);
    `confirmTotp` envía `{ otp_code }` (string de 6 dígitos).
  - **Referencia:** views.py líneas 543–594.

- [x] **T6 — Funciones API para setup Email y desactivación.**
  En `lib/api/auth.ts`:
  ```typescript
  // Activa 2FA email: POST /auth/2fa/setup/email/
  export async function setupEmail2fa(payload: EmailSetupPayload): Promise<TwoFactorMessageResponse>

  // Desactiva 2FA: DELETE /auth/2fa/disable/
  // Primera llamada EMAIL (sin otp en curso): envía password + otp_code vacío → 200 + instrucción
  // Segunda llamada EMAIL (con otp): envía password + otp_code → 200 "desactivado"
  // Llamada TOTP: envía password + otp_code TOTP → 200 "desactivado"
  export async function disable2fa(payload: DisablePayload): Promise<TwoFactorMessageResponse>
  ```
  - **Criterio:** `disable2fa` usa `api.delete` con body (`{ data: payload }` en Axios).
    La respuesta HTTP 200 no implica siempre desactivación: el front debe distinguir entre
    "enviado código por correo" y "desactivado" leyendo `detalle` o un campo extra del backend.
    Ver Q2 (§6) — actualmente ambas respuestas son HTTP 200 con `detalle` distinto.
  - **Referencia:** views.py líneas 597–613, 659–707.

### D. Hooks TanStack Query

- [x] **T7 — Hook de estado 2FA.**
  En `lib/auth/two-factor.ts` (nuevo) o `lib/auth/hooks.ts` (ampliar):
  - **Opción A:** leer `two_factor_enabled`/`two_factor_method` del store Zustand
    (`useAuthStore((s) => s.user?.two_factor_enabled)`). No hay hook de Query separado.
  - **Opción B:** `use2faStatus()` → `useQuery({ queryKey: ["2fa-status"], queryFn: fetch2faStatus })`.
  - **Criterio:** el componente widget obtiene el estado sin petición extra (Opción A) o con
    una petición cacheada (Opción B); sin cargar el estado en cada render.

- [x] **T8 — Mutaciones para activar TOTP (setup + confirm).**
  En `lib/auth/two-factor.ts`:
  ```typescript
  // useMutation que llama setupTotp()
  export function useSetupTotp(): UseMutationResult<TotpSetupResponse, ...>

  // useMutation que llama confirmTotp(payload)
  // En éxito: invalidar query "me" (Opción A) o "2fa-status" (Opción B) + cerrar diálogo
  export function useConfirmTotp(): UseMutationResult<TwoFactorMessageResponse, ...>
  ```
  - **Criterio:** `useSetupTotp` no invalida nada (aún no activó 2FA); `useConfirmTotp` invalida
    el query del estado 2FA tras éxito para refrescar el widget; maneja errores con `extractApiError`.

- [x] **T9 — Mutaciones para activar Email 2FA y desactivar.**
  En `lib/auth/two-factor.ts`:
  ```typescript
  // useMutation que llama setupEmail2fa(payload)
  // En éxito: invalidar query "me" / "2fa-status"
  export function useSetupEmail2fa(): UseMutationResult<TwoFactorMessageResponse, ...>

  // useMutation que llama disable2fa(payload)
  // En éxito completo: invalidar query "me" / "2fa-status"
  export function useDisable2fa(): UseMutationResult<TwoFactorMessageResponse, ...>
  ```
  - **Criterio:** `useDisable2fa` devuelve la respuesta del backend; el componente que lo llama
    debe distinguir la respuesta "enviado código" de la respuesta "desactivado" para controlar el
    estado del diálogo. Ver Q2.

### E. Componentes / UI

- [x] **T10 — Widget `TwoFactorStatus` (solo lectura).**
  Componente `components/auth/two-factor-status.tsx`: muestra el estado actual del 2FA del
  usuario autenticado.
  - Si `two_factor_enabled === false` (o campo ausente): texto "No activado" con badge neutral.
  - Si `two_factor_enabled === true`:
    - Método TOTP: badge verde "Activo · App autenticadora".
    - Método EMAIL: badge verde "Activo · Correo electrónico".
  - Mientras carga (Opción B con `isLoading`): skeleton o spinner de 1 línea.
  - **Criterio:** solo lectura; no botones propios; recibe el estado por props o lo lee del
    hook T7; accesible (aria-label legible).

- [x] **T11 — Diálogo de activación TOTP (`TotpSetupDialog`).**
  Componente `components/auth/totp-setup-dialog.tsx` (shadcn `Dialog`).
  Flujo en 2 pasos dentro del mismo diálogo:

  **Paso 1 — "Escanear QR":**
  - Al abrir, llamar automáticamente `useSetupTotp` (mutación T8) para obtener
    `{ otpauth_uri, secret }`.
  - Mostrar el QR generado desde `otpauth_uri` usando `qrcode.react` (componente cliente).
  - Mostrar el `secret` en texto monoespaciado con botón "Copiar" (para ingreso manual en
    la app autenticadora).
  - Botón "Continuar" pasa al Paso 2.

  **Paso 2 — "Confirmar código":**
  - Campo `otp_code` (input numérico, max 6 dígitos, `inputmode="numeric"`, `pattern="[0-9]*"`).
  - Botón "Activar" llama `useConfirmTotp({ otp_code })`.
  - En éxito: cerrar diálogo + toast "Autenticación TOTP activada correctamente.".
  - En error: mostrar error del backend (`extractApiError`).
  - Botón "Atrás" regresa al Paso 1 sin re-llamar `setupTotp` (el secreto ya está almacenado
    en el backend).

  - **Criterio:** el QR es visible; el secreto textual es copiable; el campo OTP solo acepta
    dígitos; `password` no aparece en ningún momento; el diálogo cierra y el estado 2FA
    se refresca en el widget tras éxito.
  - **Dependencia de librería:** añadir `qrcode.react` o `react-qr-code` a `package.json`.
    Ver Q3 (§6).

- [x] **T12 — Diálogo de activación por Email (`EmailSetupDialog`).**
  Componente `components/auth/email-setup-dialog.tsx` (shadcn `Dialog`).
  - Texto informativo: "Se usará el correo `<user.email>` para enviar códigos de verificación.".
  - Campo `password` (type password, required): "Contraseña actual".
  - Botón "Activar" llama `useSetupEmail2fa({ password })`.
  - En éxito: cerrar diálogo + toast "Autenticación por correo electrónico activada correctamente.".
  - En error (contraseña incorrecta u otro): mostrar error del backend.
  - Si `user.email` está vacío: mostrar aviso "Tu cuenta no tiene correo registrado. Contacta al
    administrador." y deshabilitar el botón.
  - **Criterio:** el campo contraseña es `type=password`; no se loguea ni persiste; el diálogo
    cierra y el widget se refresca tras éxito.
  - **Referencia:** serializers.py líneas 840–849; services.py líneas 269–286.

- [x] **T13 — Diálogo de desactivación (`DisableDialog`).**
  Componente `components/auth/two-factor-disable-dialog.tsx` (shadcn `Dialog`).

  El comportamiento varía según el método activo:

  **Método TOTP:**
  - Campo `password` (type password, required).
  - Campo `otp_code` (6 dígitos, required): "Código de tu app autenticadora".
  - Botón "Desactivar" llama `useDisable2fa({ password, otp_code })`.
  - En éxito: cerrar + toast "Doble factor desactivado.".

  **Método EMAIL — flujo en 2 pasos:**
  - **Paso 1:** solo campo `password` + botón "Enviar código". Al hacer clic llama
    `useDisable2fa({ password, otp_code: "" })` (primera llamada). El backend responde
    HTTP 200 con `detalle` sobre el envío del código (ver Q2).
    - En éxito de paso 1: mostrar campo `otp_code` con texto "Introduce el código enviado a
      tu correo." y botón "Desactivar".
  - **Paso 2:** llama `useDisable2fa({ password, otp_code })` con el código recibido.
    - En éxito final: cerrar + toast "Doble factor desactivado.".

  - **Criterio:** los campos contraseña son `type=password`; no se loguean; el diálogo cierra
    y el widget se refresca tras éxito definitivo; el flujo de EMAIL no llama dos veces al
    backend si ya tiene el OTP en curso (la lógica de pasos la gestiona el estado local del
    diálogo).
  - **Referencia:** views.py líneas 659–707 (TwoFactorDisableView); services.py líneas 289–328.

- [x] **T14 — Selector de método (`MethodSelectorDialog`).**
  Componente `components/auth/two-factor-method-selector.tsx` (shadcn `Dialog` o inline
  en la sección de seguridad).
  - Muestra dos opciones:
    - **App autenticadora (TOTP)** — descrición: "Usa Google Authenticator, Authy u otra app."
    - **Correo electrónico (EMAIL)** — descripción: "Recibirás un código en `<user.email>`."
  - Al seleccionar TOTP: cierra el selector y abre `TotpSetupDialog`.
  - Al seleccionar EMAIL: cierra el selector y abre `EmailSetupDialog`.
  - Si `user.email` está vacío: la opción EMAIL aparece deshabilitada con tooltip "Sin correo
    registrado".
  - **Criterio:** presentación clara de las diferencias entre métodos; no permite seleccionar
    EMAIL sin correo registrado; accesible con teclado (Tab/Enter).

- [x] **T15 — Sección "Seguridad" en `/perfil`.**
  Ampliar `app/(app)/perfil/page.tsx`:
  - Añadir una nueva `<Card>` con:
    - `CardTitle`: "Seguridad".
    - `CardDescription`: "Gestión del segundo factor de autenticación."
    - `CardContent`: widget `TwoFactorStatus` + botones de acción condicionales.
  - **Botones visibles según estado:**
    - `two_factor_enabled === false`: botón "Activar 2FA" → abre `MethodSelectorDialog`.
    - `two_factor_enabled === true`: botón "Desactivar 2FA" → abre `DisableDialog`.
  - Los botones de apertura de diálogos poseen el estado (`open`/`setOpen`) de sus diálogos
    correspondientes (lifting state up en la página o en la tarjeta de seguridad).
  - **Criterio:** la tarjeta de seguridad se renderiza al final de la página (después de
    "Perfiles institucionales"); no modifica las tarjetas existentes; el estado 2FA refleja
    el valor real (no hardcodeado); accesible sin JS (degradación graciosa con skeleton).

### F. Invalidación de estado tras mutaciones

- [x] **T16 — Invalidar y refrescar el estado 2FA tras cada mutación con éxito.**
  En `useConfirmTotp`, `useSetupEmail2fa` y `useDisable2fa` (hooks T8/T9):
  - **Opción A:** invalidar la query key `["me"]` (TanStack Query) para que `GET /auth/me/`
    se re-ejecute; el store Zustand se actualiza desde el resultado del refetch (según el
    patrón de `fetchMe` ya implementado en el auth flow).
  - **Opción B:** invalidar la query key `["2fa-status"]` para `use2faStatus`.
  - En ambos casos: el widget `TwoFactorStatus` refleja el cambio sin recarga de página.
  - **Criterio:** tras activar TOTP, el widget muestra "Activo · App autenticadora" sin F5;
    tras desactivar, muestra "No activado". El store Zustand NO almacena `two_factor_enabled`
    como estado derivado adicional (ya vive en la query cache o en `user` dependiendo de la
    opción elegida).

### G. Calidad / UX

- [x] **T17 — Seguridad de contraseñas (transversal al módulo).**
  Verificar en toda la implementación 2FA:
  - Los campos `password` usan `type=password` y `autoComplete="current-password"`.
  - El valor de `password` no se persiste en Zustand ni en la cache de TanStack Query.
  - No hay `console.log` del valor de `password` ni `otp_code`.
  - Los tipos de lectura (`TotpSetupResponse`, `TwoFactorMessageResponse`, `TwoFactorStatus`)
    no incluyen campos de contraseña.
  - **Criterio:** búsqueda en el diff no revela `console.log(password)` ni el campo en tipos
    de lectura o tablas; todos los campos sensibles son `type=password`.

- [x] **T18 — Manejo de errores: backend, red y estados de carga.**
  - Todos los errores de mutación usan `extractApiError` (ya implementado en el proyecto).
  - Los mensajes de error del backend (contraseña incorrecta, OTP inválido, OTP expirado,
    rate-limit de email) se muestran legibles al usuario.
  - Los botones de mutación muestran estado de carga (`isPending`) y se deshabilitan durante
    el envío para evitar dobles peticiones.
  - Errores de red: toast genérico "Error de conexión. Inténtalo de nuevo."
  - **Criterio:** todos los estados (loading/error/success) tienen feedback visual; sin
    estados rotos al cerrar y reabrir diálogos.

- [x] **T19 — Lint/typecheck verdes.**
  `npm run lint` y build TS strict sin errores nuevos introducidos por las tareas T2–T18.
  - **Criterio:** sin warnings/errores nuevos; tipos sin `any` salvo justificación puntual;
    `qrcode.react` (u alternativa) tiene tipos TS disponibles.

---

## 4. Mapa pantalla → endpoint

| Sección / Acción | Método / Endpoint | Auth | Notas |
|------------------|-------------------|------|-------|
| Leer estado 2FA (Opción A) | `GET /auth/me/` | JWT | Solo si backend amplía `MeSerializer` |
| Leer estado 2FA (Opción B) | `GET /auth/2fa/status/` | JWT | Endpoint nuevo pendiente |
| Iniciar setup TOTP | `POST /auth/2fa/setup/totp/` | JWT | Devuelve `{otpauth_uri, secret}` |
| Confirmar código TOTP | `POST /auth/2fa/confirm-totp/` | JWT | Body `{otp_code}` (6 dígitos) |
| Activar 2FA Email | `POST /auth/2fa/setup/email/` | JWT | Body `{password}` |
| Desactivar (TOTP) | `DELETE /auth/2fa/disable/` | JWT | Body `{password, otp_code}` |
| Desactivar (Email, paso 1) | `DELETE /auth/2fa/disable/` | JWT | Body `{password, otp_code:""}` → 200 + envío OTP |
| Desactivar (Email, paso 2) | `DELETE /auth/2fa/disable/` | JWT | Body `{password, otp_code}` → 200 "desactivado" |

> `resend-otp` (`POST /auth/2fa/resend-otp/`) **no se usa** en este flujo:
> requiere `session_token` y solo aplica para el login diferido, no para el perfil autenticado.

---

## 5. Dependencias entre tareas

- T1 (Q1 resuelta) → desbloquea T3/T4 (según opción) y T7 (hook de estado).
- T2 (tipos) → precede a T5/T6/T8/T9 (API y hooks).
- T5 + T8 → desbloquean T11 (diálogo TOTP).
- T6 + T9 → desbloquean T12 (diálogo Email) y T13 (diálogo desactivar).
- T10 (widget estado) + T11/T12/T13/T14 (diálogos) → desbloquean T15 (sección en `/perfil`).
- T16 (invalidación) es transversal a T8/T9 (se implementa dentro de los hooks).
- T17/T18/T19 son transversales, se verifican al final.

---

## 6. Preguntas abiertas (requieren decisión antes de Implement)

### Q1 — ¿Cómo expone el estado 2FA `GET /auth/me/`? (BLOQUEANTE)

`MeSerializer` **no incluye** `two_factor_enabled` ni `two_factor_method` (verificado en
`apps/common/serializers.py`). El frontend necesita saber si el usuario tiene 2FA activo y
qué método usa para mostrar el widget correctamente.

**Opciones:**
- **A (mínimo cambio):** añadir los dos campos a `MeSerializer` (`source="seguridad.two_factor_enabled"`,
  con `default=False` si no existe `UserSecurity`). Sin endpoint nuevo; el front lee del cache
  `["me"]` ya existente.
- **B (endpoint separado):** nuevo `GET /auth/2fa/status/` (`IsAuthenticated`). El front hace
  una petición adicional.

Se recomienda **Opción A**: es más simple, el campo ya carga con `/auth/me/` que el front hace en
cada login/refresh, y `MeSerializer` ya accede a `UserSecurity` vía `UserSecurity.objects.get_or_create`
en `CustomTokenObtainPairView` (el objeto existe siempre para usuarios que loguearon).

**Acción requerida:** confirmar con el backend cuál opción se implementa antes de escribir T3/T7.

### Q2 — Distinción de respuesta de `DELETE /auth/2fa/disable/` (paso 1 EMAIL)

`TwoFactorDisableView.delete` devuelve HTTP 200 tanto cuando "enviamos el código" (paso 1 EMAIL)
como cuando "desactivamos exitosamente" (paso 2). El front distingue solo por el campo `detalle`
(texto libre) o por la presencia de un campo semántico adicional.

**Opciones:**
- **A (sin cambio backend):** el frontend compara `detalle` con strings fijos (frágil).
- **B (recomendado):** el backend añade un campo `step: "otp_sent" | "disabled"` a las
  respuestas de `TwoFactorDisableView` para que el front distinga sin parsear texto.

**Acción requerida:** confirmar con el backend antes de implementar T13.

### Q3 — Librería QR para el flujo TOTP

El front necesita renderizar un QR desde `otpauth_uri` en el navegador (componente cliente).
La librería `qrcode` (Node.js) no funciona en browser/App Router sin wrapper.

**Opciones evaluadas:**
- `qrcode.react` (npm: `qrcode.react`) — más usada, `<QRCodeSVG uri={...} />`.
- `react-qr-code` (npm: `react-qr-code`) — alternativa más ligera.

**Acción requerida:** decidir cuál instalar y confirmar que no existe ya en `package.json`
(no está listada en el proyecto actualmente). El agente Implement la instala con `npm install`.

---

> **Este spec requiere aprobación humana antes de pasar a Implement.**
> Puntos críticos que requieren decisión:
> 1. **Q1** (bloqueante): ¿Opción A (ampliar `MeSerializer`) u Opción B (endpoint nuevo)?
> 2. **Q2**: ¿el backend añade campo `step` a la respuesta de `disable` o el front parsea `detalle`?
> 3. **Q3**: ¿`qrcode.react` o `react-qr-code`?
>
> Una vez aprobadas las 3 decisiones, el agente Implement puede ejecutar todas las tareas T1–T19.
