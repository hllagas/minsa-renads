# Spec — Almacenamiento (adjuntos reales: logos + anexos)

Módulo transversal. Contrato: `docs/api-almacenamiento.md`. Cubre la subida/visualización de
**logos institucionales** (5 entidades) y **anexos PDF** (declaraciones juradas por actor,
3 entidades). Reutiliza el CRUD declarativo (`ResourceCrud` + `rowActions`/`columns.render`).

> **Regla de oro:** una tarea = un cambio verificable. El validador marca `[x]` al cumplir el
> contrato. Gating de rol en el front es UX; el backend es la autoridad final.

## Alcance

- **Logos** (`upload-logo`/`logo-url`): `universities`, `regional-governments`, `regional-organs`,
  `executing-units`, `ipress`. Escritura `Administrador RENADS`; lectura autenticados.
- **Anexos** (`annex-checklist`/`annex-upload`): `students` (INTERNO), `university-authorities`
  (AUTORIDAD_UNIVERSIDAD), `representatives` (REPRESENTANTE).
- **Fallback**: toda tabla/form que muestre un logo usa una imagen/placeholder cuando la entidad
  no tiene logo (o el signed URL falla).
- **Feature F3 (en alcance, aprobado)**: gate por `debe_cambiar_password`, pantalla de cambio de
  contraseña (`/auth/me/cambiar-password/`), y `revisar-declaraciones` en el detalle del internado
  (más mostrar `estado_declaraciones`).
- **Fuera de alcance (v2)**: `documents/upload` genérico. Solo se documenta.

## Tareas

### 1. Capa API (`lib/api/storage.ts`, solo Axios en `lib/api/`)

- [x] T1.1 — Tipos: `LogoUploadResult { referencia_logo: string; url: string }`,
  `LogoUrlResult { url: string }`, `AnnexChecklistItem` (según ejemplo del contrato),
  `AnnexUploadResult = Documento` (reusar de `lib/api/documents.ts`).
- [x] T1.2 — `storageApi`: `uploadLogo(entidad, id, file)`, `getLogoUrl(entidad, id)`,
  `getAnnexChecklist(entidad, id)`, `uploadAnnex(entidad, id, { documento_anexo, archivo, nombre_archivo? })`.
  Multipart vía `postMultipart`; campo de archivo = `archivo`.
- [x] T1.3 — Hooks TanStack Query:
  `useLogoUrl(entidad, id, enabled)` (query, key `["logo", entidad, id]`, `retry:false`,
  `staleTime` < expiración del signed URL, no romper si `404`),
  `useUploadLogo(entidad, id)` (mutation; invalida `["logo", entidad, id]` + lista de la entidad),
  `useAnnexChecklist(entidad, id)` (query),
  `useUploadAnnex(entidad, id)` (mutation; invalida checklist + lista de la entidad).

### 2. Visualización de logo con fallback (`components/ui/entity-logo.tsx`)

- [x] T2.1 — `EntityLogo({ entidad, id, referenciaLogo?, size?, className? })`: si `referenciaLogo`
  vacío → fallback directo (sin pedir URL). Si hay referencia → `useLogoUrl` y `<img>`; `onError` y
  ausencia de URL → fallback. Fallback = ícono `Building2`/iniciales en contenedor `bg-muted`
  redondeado. Accesible (`alt`).
- [x] T2.2 — Columna «Logo» (render con `EntityLogo`, tamaño chico) en las 5 configs de entidad con
  logo (`ENTITY_CONFIGS`). No romper las que no tienen logo.

### 3. Subida/gestión de logo (`components/catalogos/logo-upload-dialog.tsx`)

- [x] T3.1 — Diálogo (patrón `IpressSedeDocenteAction`): previsualiza el logo actual (`EntityLogo`),
  `Input type=file accept="image/png,image/jpeg,image/webp"`, valida tamaño ≤ 25 MiB en cliente,
  sube con `useUploadLogo`, `toast` éxito/error (`extractApiError`), refresca.
- [x] T3.2 — `RowAction` «Logo» inyectada en la página de entidades
  (`app/(app)/catalogos/entidades/[entidad]/page.tsx` y `convenios/maestros/[entidad]`) solo para las
  5 entidades con logo y rol `Administrador RENADS`.

### 4. Anexos — checklist + subida (`components/almacenamiento/annex-checklist-dialog.tsx`)

- [x] T4.1 — Diálogo con `useAnnexChecklist`: tabla de anexos (nombre, obligatorio, estado
  adjuntado/versión). Resaltar `obligatorio=true && adjuntado=false`.
- [x] T4.2 — Por fila del checklist: `Input type=file accept="application/pdf"` + botón subir
  (`useUploadAnnex` con `documento_anexo`), valida tamaño ≤ 25 MiB, re-subir = nueva versión.
  `toast` éxito/error; refresca checklist.
- [x] T4.3 — `RowAction` «Anexos» inyectada en:
  `students` (`internados/personas/[entidad]`, rol `Universidad`/`Administrador RENADS`),
  `university-authorities` y `representatives` (`/catalogos`, rol `Administrador RENADS`).

### 5. Formularios — quitar referencia manual

- [x] T5.1 — Quitar el campo de texto `referencia_logo` de los `fields` de las 5 entidades con logo
  (se gestiona por el diálogo de subida, no a mano). Verificar que el resto del form sigue OK.

### 7. Feature F3 — declaraciones juradas y contraseña temporal

- [x] T7.1 — `AuthUser` (`lib/auth/store.ts`) + `TokenPair` (`lib/api/auth.ts`): añadir
  `debe_cambiar_password: boolean`. `fetchMe` ya lo trae.
- [x] T7.2 — `changePassword({ password_actual, password_nueva })` en `lib/api/auth.ts`
  (`POST /auth/me/cambiar-password/` → `AuthUser`) + `useChangePassword` en `lib/auth/hooks.ts`
  (al éxito hidrata `store.user` e invalida `me`).
- [x] T7.3 — `components/auth/change-password-gate.tsx`: diálogo **bloqueante** (no se cierra) que se
  muestra cuando `user.debe_cambiar_password`. Form `password_actual` + `password_nueva`
  (+ confirmación cliente). Montado en `app/(app)/layout.tsx` tras cargar `me`.
- [x] T7.4 — `revisar-declaraciones` como `FlowAction` de `interns` (`lib/internados/flow-actions.ts`),
  roles `Universidad`/`Administrador RENADS`, `resultado` (VALIDADAS/OBSERVADAS) + `observacion`.
- [x] T7.5 — Mostrar `estado_declaraciones` en el detalle del internado
  (`app/(app)/internados/[id]/page.tsx`).

### 6. Documentación / cierre

- [x] T6.1 — `docs/api-almacenamiento.md` creado + índice `docs/README.md` actualizado.
- [x] T6.2 — `CLAUDE.md` (raíz) actualizado: añadir fila de `docs/api-almacenamiento.md` a la tabla y
  nota del transversal de adjuntos en la descripción del Módulo 1/2.
- [x] T6.3 — `npx tsc --noEmit` limpio y `npm run lint` sin nuevos errores.
- [x] T6.4 — Smoke manual (`npm run dev`): subir logo a una entidad, verse en tabla; entidad sin
  logo muestra fallback; subir un anexo PDF a un estudiante y verlo `adjuntado`.
