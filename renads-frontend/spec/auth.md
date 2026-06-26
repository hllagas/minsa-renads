# Spec — Módulo `auth` (Autenticación y shell autenticado)

Primer módulo del MVP (ver `docs/mvp.md`). **No es CRUD**: sesión JWT + guard de rutas + shell con
gating por rol. Base de todos los módulos siguientes. Contrato del backend: `docs/api-auth.md`.

> **Estado:** ✅ aprobado por humano, implementado y **validado sin errores** (ver
> `spec/auth.validacion.md` y `spec/auth.guia_pruebas.md`).

## Decisiones (resueltas)
- **Guard:** del lado del cliente, en el layout autenticado (el token vive en localStorage vía
  Zustand persist; el middleware Edge no lo ve). Sin `middleware.ts` en este módulo.
- **Persistencia:** `localStorage` (Zustand persist, solo tokens). Cookie httpOnly queda fuera de alcance MVP.
- **Validación de formularios:** `react-hook-form` + `zod` + `@hookform/resolvers` (patrón estándar de shadcn `form`).

## Resumen / pantallas
- `/login` — formulario de acceso (público).
- Shell autenticado — layout con guard, carga de `me`, navegación con gating por rol, menú de usuario + logout.
- Home protegida mínima (placeholder) que confirme sesión y muestre datos de `me`.

## Reutilización (ya existe — Fase 0)
- `lib/api/client.ts` — Axios + inyección de Bearer + refresh en 401 + `Paginated<T>`.
- `lib/auth/store.ts` — `useAuthStore` (tokens persistidos, `user` en memoria), tipos `AuthUser`/`UserProfile`, helper `userHasRole`.
- `app/providers.tsx` — `QueryClientProvider`.

---

## T1 — Dependencias y componentes shadcn
- [x] **T1.1** Instalar `react-hook-form zod @hookform/resolvers`.
- [x] **T1.2** Agregar componentes shadcn: `input`, `label`, `card`, `form`, `sonner`, `dropdown-menu`, `avatar`.
  - **Criterio:** `npm run build` limpio; componentes en `components/ui/`.

## T2 — API layer (`lib/api/auth.ts`)
- [x] **T2.1** `login(credentials: { username: string; password: string }): Promise<{ access: string; refresh: string }>` → `POST /auth/token/`.
- [x] **T2.2** `fetchMe(): Promise<AuthUser>` → `GET /auth/me/`.
  - **Criterio:** usa el cliente `api` de `lib/api/client.ts`; tipos importados de `lib/auth/store.ts`; sin Axios suelto fuera de `lib/api/`. Claves del payload en español (no traducir).

## T3 — Hooks de datos (`lib/auth/hooks.ts`)
- [x] **T3.1** `useLogin()` (mutation): llama `login` → `setTokens` en store → invalida/precarga `me`. Expone `error`/`isPending` para la UI.
- [x] **T3.2** `useMe()` (query, key `["auth","me"]`): habilitada solo si hay `accessToken`; al resolver, hidrata `store.setUser`. `staleTime` alto.
- [x] **T3.3** `useLogout()`: `store.clear()` + `queryClient.clear()` + redirige a `/login`.
  - **Criterio:** toda petición pasa por TanStack Query; no hay `fetch`/Axios en componentes; loading/error manejados.

## T4 — Pantalla de login (`app/(auth)/login/page.tsx`)
- [x] **T4.1** Form `react-hook-form` + `zod` (campos `username`, `password`, requeridos) usando componentes shadcn `Form`/`Input`/`Label`/`Card`/`Button`.
- [x] **T4.2** Submit → `useLogin`; en éxito redirige a la home protegida; en error muestra mensaje (credenciales inválidas) vía `sonner`/inline.
- [x] **T4.3** Si ya hay sesión (token), redirige fuera de `/login`.
  - **Criterio:** `"use client"`; estados de carga y error visibles; sin lógica de red en el componente (usa el hook).

## T5 — Shell autenticado + guard (`app/(app)/layout.tsx` + componentes)
- [x] **T5.1** Guard cliente: sin `accessToken` → `redirect`/`router.replace("/login")`. Con token, dispara `useMe`; mientras carga, estado de carga; si `me` falla por sesión inválida → `clear()` + a `/login`.
- [x] **T5.2** Layout: sidebar/topbar con navegación a los módulos (Convenios, Internados, Actividades — placeholders por ahora) + menú de usuario (`dropdown-menu` + `avatar`) con `nombre` y **logout**.
- [x] **T5.3** Gating por rol con `userHasRole(user, ...)`: ítems de nav/acciones visibles según `me.grupos`. (El backend es la autoridad final; esto es UX.)
  - **Criterio:** rutas bajo `(app)` quedan protegidas; el menú refleja `grupos`; logout limpia sesión.

## T6 — Home protegida mínima (`app/(app)/page.tsx` o `dashboard`)
- [x] **T6.1** Página placeholder que muestre `nombre`, `grupos` y `perfiles` del usuario (confirma sesión end-to-end). Sustituye/retira la home scaffold actual (`app/page.tsx`).
  - **Criterio:** tras login, se ve el usuario real del backend.

## T7 — Verificación
- [x] **T7.1** `npm run lint` y `npm run build` limpios.
- [x] **T7.2** El validador deja `spec/auth.guia_pruebas.md` (flujo manual contra backend real) al cerrar.

---

## Criterios de aceptación del módulo (de `docs/mvp.md`)
- Login funciona contra el backend real (`/auth/token/`).
- El refresh renueva la sesión en `401` (interceptor ya existente).
- Las rutas protegidas redirigen a `/login` sin sesión.
- El menú/acciones se ocultan según rol (`me.grupos`).

## Fuera de alcance
- Recuperación/cambio de contraseña, registro de usuarios (los gestiona el admin del backend).
- Cookie httpOnly / SSR auth. Tablas/CRUD de negocio (módulos siguientes).

## Referencias
- Endpoints, claims y forma de `me`: `docs/api-auth.md`.
- Roles/grupos y alcance: `docs/backend-overview.md`.
- Convenciones (idioma, stack, estructura): `docs/frontend-conventions.md`, `CLAUDE.md`.
