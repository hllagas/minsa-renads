# Spec (frontend) — Alta de perfiles institucionales (v2): asignar usuario a entidades

> **Estado:** PROPUESTA — pendiente de **aprobación humana** antes de `implement` (SDD del frontend).
> **Módulo:** `usuarios` (incremento v2 sobre `spec/usuarios.md`, sección F "Perfiles institucionales").
> **Depende de:** backend `common_usuarios` T10 + T11 (ya implementados y validados en `renads-api`).

## Contexto

La pantalla `app/(app)/usuarios/perfiles/` existe con el **alta deshabilitada**
(`userEntityProfilesConfig.disableCreate = true`) y un aviso *"pendiente del endpoint content-types"*
(`lib/usuarios/configs.ts:182-226`). El backend ya cerró ese hueco:

- **Write (alta/baja de alcance):** `GET/POST/DELETE /api/v1/users/{id}/profiles/` — asigna un usuario a
  **una o varias** entidades bajo un rol, en una sola operación (idempotente). Payload:
  `{ rol: <group_id>, tipo_entidad: "university", ids: [3, 7] }`. `DELETE ?profile_id=<pk>` = baja lógica.
  Solo `IsSuperUser`.
- **Lookup de tipos asignables:** `GET /api/v1/profile-entity-types/` → lista
  `[{ id, tipo_entidad, label, app_label }]` de los 8 tipos institucionales asignables. Solo `IsSuperUser`.

El objetivo de este incremento es **habilitar el alta** consumiendo esos endpoints, con la UX de
"asignar un usuario a universidades (u otras entidades)".

## Decisiones de diseño

- **D1 — UX principal: diálogo por usuario "Asignar entidades".** Se lanza desde la lista de cuentas
  (`/usuarios/cuentas`) como acción de fila. Reutiliza el write **bulk** de T10
  (`POST /users/{id}/profiles/`): elegir rol + tipo de entidad + multiselección de entidades → un POST.
  Es más natural que el alta fila-a-fila del CRUD genérico, y es idempotente.
- **D2 — Fuente del selector de tipo:** `GET /profile-entity-types/` (no hardcodear "university"). El
  `tipo_entidad` devuelto es el mismo string que acepta el POST (contrato end-to-end verificado en backend).
- **D3 — Selector de entidades concretas:** `MultiEntityCombobox` (`components/form/multi-entity-combobox.tsx`)
  apuntando al endpoint del catálogo según el tipo elegido, vía un **mapa estático**
  `tipo_entidad → endpoint` (los 8 tipos son un conjunto cerrado). Búsqueda server-side ya soportada.
- **D4 — Gating: SOLO superusuario.** Backend T10/T11 = `IsSuperUser`. El diálogo y la acción de fila se
  ocultan/deshabilitan salvo `isSuperuser(user)`. **Ver "Riesgo/decisión abierta"** por la inconsistencia
  con la pantalla actual de perfiles (`access="admin"`).
- **D5 — Pantalla `/usuarios/perfiles`:** se mantiene como **lista global** (ver/editar `activo`/eliminar);
  se **retira el aviso** de alta deshabilitada y se sustituye por una nota que indica que el alta se hace
  por usuario desde *Cuentas* (evita duplicar el flujo de creación). Alternativa en "Fuera de alcance".
- **D6 — Claves del API en español, sin traducir** (`tipo_entidad`, `id_objeto`, `entidad`, `rol`, `activo`).

## Mapa `tipo_entidad → endpoint` (D3)

| `tipo_entidad` (model) | Endpoint front (catálogo) |
|------------------------|---------------------------|
| `university`           | `universities`            |
| `ipress`               | `ipress`                  |
| `regionalgovernment`   | `regional-governments`    |
| `regionalorgan`        | `regional-organs`         |
| `executingunit`        | `executing-units`         |
| `minsaorgan`           | `minsa-organs`            |
| `conapres`             | `conapres`                |
| `student`              | `students`                |

> Verificar en `implement` que el endpoint front `students` existe (módulo internados) y que la etiqueta
> mostrada usa el campo legible de cada entidad (`nombre`/`siglas`/`numero_documento` según el caso).

## Tareas

### T1 — Capa API (`lib/api/user-profiles.ts` — NUEVO)
Usar el cliente axios único (`lib/api/client.ts`) y los helpers existentes. Funciones:
- `listUserProfiles(userId: number, opts?: { incluirInactivos?: boolean }): Promise<UserProfileRead[]>`
  → `GET /users/{userId}/profiles/` (+ `?incluir_inactivos=true`). Devuelve array (endpoint **no** paginado).
- `assignUserProfiles(userId, payload: AssignProfilesPayload): Promise<UserProfileRead[]>`
  → `POST /users/{userId}/profiles/` con `{ rol, tipo_entidad, ids }`. Devuelve la lista resultante.
- `revokeUserProfile(userId: number, profileId: number): Promise<void>`
  → `DELETE /users/{userId}/profiles/?profile_id={profileId}`.
- `listAssignableEntityTypes(): Promise<AssignableEntityType[]>` → `GET /profile-entity-types/`.
- **Criterio:** manejo de error vía `extractApiError` (`lib/api/errors.ts`); nunca `fetch`/axios suelto en componentes.

### T2 — Tipos (`lib/usuarios/types.ts` — EDITAR)
```ts
export interface UserProfileRead {
  id: number; tipo_entidad: string; id_objeto: number; entidad: string; rol: string; activo: boolean;
}
export interface AssignableEntityType { id: number; tipo_entidad: string; label: string; app_label: string; }
export interface AssignProfilesPayload { rol: number; tipo_entidad: string; ids: number[]; }
```

### T3 — Hooks TanStack Query (`lib/usuarios/hooks.ts` — EDITAR)
- `useAssignableEntityTypes()` → `useQuery(["profile-entity-types"], listAssignableEntityTypes)` (staleTime alto: es casi estático).
- `useUserProfiles(userId, incluirInactivos?)` → `useQuery(["users", userId, "profiles", { incluirInactivos }], ...)`, `enabled: userId != null`.
- `useAssignUserProfiles(userId)` → `useMutation` → en éxito invalida `["users", userId, "profiles"]` (y `["users"]` si aplica) + toast de éxito.
- `useRevokeUserProfile(userId)` → `useMutation` → misma invalidación + toast.
- **Criterio:** claves de query consistentes con el patrón existente (`resourceKeys`); invalidación tras cada mutación.

### T4 — Mapa de endpoints (`lib/usuarios/entity-endpoints.ts` — NUEVO)
`Record<string, { endpoint: string; toLabel: (r: unknown) => string }>` con los 8 tipos de la tabla D3.
`toLabel` resuelve la etiqueta legible por entidad (reutilizar helpers de `lib/convenios/entities.ts` si existen).

### T5 — Componente `AssignProfilesDialog` (`components/usuarios/assign-profiles-dialog.tsx` — NUEVO)
Props: `{ userId: number; username?: string; open: boolean; onOpenChange: (o: boolean) => void }`.
- **Sección "Alcance actual":** `useUserProfiles(userId)` → lista agrupada por `tipo_entidad`, cada ítem con
  `entidad`, `rol`, badge `activo` y botón **Revocar** (`useRevokeUserProfile`, confirmación shadcn `AlertDialog`).
- **Sección "Asignar":** formulario shadcn:
  - `rol` → `EntityCombobox` (single) sobre `groups` (etiqueta `groupLabel` ya existente).
  - `tipo_entidad` → `Select` poblado por `useAssignableEntityTypes()` (muestra `label`).
  - `entidades` → `MultiEntityCombobox` con `endpoint = ENTITY_ENDPOINTS[tipo_entidad].endpoint`
    (deshabilitado hasta elegir tipo; se resetea al cambiar de tipo).
  - Botón **Asignar** → `useAssignUserProfiles({ rol, tipo_entidad, ids })`; al éxito limpia el form,
    refresca la lista y muestra toast. Validación cliente: rol e `ids` no vacíos.
- Usa componentes shadcn (`Dialog`, `Select`, `Button`, `Badge`, `AlertDialog`). Sin UI a mano.

### T6 — Acción de fila en Cuentas (`app/(app)/usuarios/cuentas/**` + `lib/usuarios/configs.ts` — EDITAR)
- Añadir a la tabla de usuarios una **rowAction** "Asignar entidades" (icono, p. ej. `Building2`) que abre
  `AssignProfilesDialog` para ese usuario. Visible **solo si** `isSuperuser(user)` (D4).
- Estado local en la página de cuentas para el usuario seleccionado + `open` del diálogo.

### T7 — Ajuste de `/usuarios/perfiles` (`app/(app)/usuarios/perfiles/page.tsx` + config — EDITAR)
- Retirar el aviso "alta deshabilitada" (D5). Mantener `disableCreate` en el CRUD global (el alta se hace
  desde Cuentas) y añadir una nota corta enlazando a *Cuentas → Asignar entidades*.
- (Opcional) mejorar columnas para mostrar `entidad` legible en vez de ids crudos si el backend ya lo expone.

## Riesgo / decisión abierta (requiere confirmación)

**Inconsistencia de permisos.** El backend T10/T11 exige `IsSuperUser`, pero la pantalla actual de perfiles
y el CRUD genérico `user-entity-profiles` conceden escritura a `Administrador RENADS`
(`writeRoles: ["Administrador RENADS"]`, `access="admin"`). Con este plan, un `Administrador RENADS`
**vería** la pantalla pero recibiría **403** al asignar vía `/users/{id}/profiles/`.
Opciones:
1. **(Recomendada)** Gatear el alta a **superusuario** (D4) y dejar claro en la UI que el alcance solo lo
   asigna un superadministrador. Coherente con la decisión anti-escalación del backend.
2. Alinear el backend para permitir también `Administrador RENADS` en T10/T11 (cambio de spec backend).

## Verificación (manual, no hay test runner)

1. `npm run lint` y `npm run build` sin errores nuevos.
2. Como **superusuario**: en `/usuarios/cuentas`, acción "Asignar entidades" → elegir rol +
   `tipo_entidad: Universidad` + 2 universidades → **Asignar** → aparecen en "Alcance actual" y en
   `GET /auth/me/` de ese usuario (si es el propio) / en `/usuarios/perfiles`.
3. Reasignar los mismos ids → sin duplicados (idempotencia del backend).
4. **Revocar** un ítem → baja lógica; desaparece de la lista por defecto.
5. Probar con `tipo_entidad: IPRESS` → el multiselect consume `ipress` sin cambios de código.
6. Como **no superusuario** → la acción "Asignar entidades" no está visible.

## Fuera de alcance

- Alta directa fila-a-fila en el CRUD global de `/usuarios/perfiles` (se centraliza el alta por usuario).
- Edición del `rol` de un perfil existente (se revoca y se reasigna).
- Filtro por ámbito para `Administrador RENADS` (depende de la decisión abierta de permisos).
