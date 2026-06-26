# Validación — Módulo `auth`

**Resultado: ✅ APROBADO (sin errores altos/medios). Módulo cerrado.**

Revisado contra `spec/auth.md`, el contrato `docs/api-auth.md` y las convenciones del proyecto.

## Cobertura del spec
| Tarea | Estado | Evidencia |
|-------|--------|-----------|
| T1 deps + componentes | ✅ | rhf/zod/resolvers instalados; `components/ui/{input,label,card,form,sonner,dropdown-menu,avatar}.tsx` |
| T2 API layer | ✅ | `lib/api/auth.ts` → `login()` `POST /auth/token/`, `fetchMe()` `GET /auth/me/` |
| T3 hooks | ✅ | `lib/auth/hooks.ts` → `useLogin`, `useMe` (hidrata store), `useLogout` |
| T4 login | ✅ | `app/(auth)/login/page.tsx` rhf+zod, redirect si hay sesión, toast en error |
| T5 shell + guard | ✅ | `app/(app)/layout.tsx` guard cliente; `components/layout/app-shell.tsx` nav+menú+gating |
| T6 home protegida | ✅ | `app/(app)/page.tsx` muestra `me`; scaffold `app/page.tsx` removido |
| T7 verificación | ✅ | `npm run lint` 0 errores; `npm run build` limpio (rutas `/`, `/login`) |

## Conformidad
- **Contrato:** endpoints `/auth/token/`, `/auth/token/refresh/` (interceptor), `/auth/me/` correctos. Claves del payload en español preservadas (`nombre`, `grupos`, `perfiles`, `es_superusuario`). ✓
- **Stack:** toda petición vía TanStack Query; **0** usos de `fetch`/`axios` en `app/` o `components/`; Axios solo en `lib/api/` (único import de `@/lib/api/client` en `lib/api/auth.ts`). Tablas N/A en este módulo. ✓
- **Next/SOLID:** Server/Client correctos (`"use client"` solo donde hay estado/efectos); lógica de datos en hooks, no en vistas; componentes cohesivos. ✓
- **Gating:** `userHasRole` aplica a la navegación; menú refleja `me.grupos`. ✓
- **Guard:** sin token → `/login`; estados loading/error; logout limpia store + cache. ✓

## Hallazgos menores (no bloquean — opcionales)
- `app/(auth)/login/page.tsx`: redirección redundante (efecto `accessToken` + `onSuccess router.replace`). Inofensivo; se puede unificar.
- `components/ui/form.tsx`: adaptador propio (base-nova no trae `form`; sin Radix Slot, usa `cloneElement`). Funciona y compila; al actualizar shadcn, revisar que siga alineado.
- `components/ui/data-table.tsx`: warning de React Compiler sobre `useReactTable` (pre-existente, ajeno a auth). Sin impacto funcional.

## Comprobaciones técnicas
- `npm run lint` → 0 errores, 1 warning (DataTable, no-auth).
- `npm run build` → OK (tras limpiar `.next` por tipo stale del `app/page.tsx` removido).

## Smoke test del contrato contra backend real (`localhost:8000`)
Ejecutado vía API (usuario superusuario `hllagas`). **Todo pasa:**
- `POST /auth/token/` → `access` + `refresh`; claims `nombre` y `grupos` presentes. ✓
- `GET /auth/me/` → forma exacta de `AuthUser` (`id, username, email, nombre, es_superusuario, grupos[], perfiles[]`). ✓
- `POST /auth/token/refresh/` → nuevo `access` + `refresh` rotado (confirma `ROTATE_REFRESH_TOKENS`). ✓
- `me` con access refrescado → OK. ✓
- Bordes: token sin credenciales → `401`; `me` sin/ça con token inválido → `401`; refresh inválido → `401` (coincide con la lógica del interceptor y del guard). ✓

**Nota:** el usuario de prueba es superusuario (`grupos: []`), por lo que ve toda la navegación. La
verificación de **gating por rol** (ocultar ítems) requiere un usuario con rol acotado (p. ej. solo
`Universidad`) — pendiente de prueba manual en navegador (opción B).
