# Validación — Almacenamiento (logos + anexos + F3)

Fecha: 2026-07-20. Contrato: `docs/api-almacenamiento.md`. Estado: **OK** (todas las tareas
cumplidas y verificadas contra el backend en vivo).

## Verificación técnica

- `npx tsc --noEmit`: **limpio** (0 errores).
- `npm run lint`: 0 errores; 1 warning **preexistente** (`components/ui/data-table.tsx:43`,
  `react-hooks/incompatible-library` de TanStack Table). No introducido por esta iteración.
- `npm run dev`: rutas afectadas responden `200` — `/login`, `/catalogos/entidades/{universities,
  ipress,university-authorities}`, `/catalogos/representantes`, `/internados/personas/students`,
  `/convenios/maestros/universities`, `/internados`.

## Smoke contra backend (`localhost:8000`, usuario `smoke_admin`, rol Administrador RENADS)

### Logos
- `GET universities/1/logo-url/` sin logo → `404` «La entidad no tiene un logo cargado.» ✔
- `POST universities/1/upload-logo/` (PNG) → `200` `{ referencia_logo, url }` ✔
- `GET universities/1/logo-url/` tras subir → `200` ✔
- `POST upload-logo` con `type=application/pdf` → `400` (content-type no permitido) ✔
- Nota dev: el stub devuelve `url = <nombre-archivo>` (referencia externa, no un signed URL real).
  `EntityLogo` cae al **fallback institucional** cuando la imagen no carga → comportamiento correcto
  en dev; en prod la `url` es un signed URL GCS válido.

### Anexos
- `GET students/1/annex-checklist/` → lista con la forma de `AnnexChecklistItem` ✔
- `POST students/1/annex-upload/` (PDF, `documento_anexo=1`) → `201` `Document` (`version=1`) ✔
- Re-subir el mismo `documento_anexo` → `version=2` (versionado) ✔
- `POST annex-upload` con `type=image/png` → `400` ✔
- `annex-checklist` tras subir → `adjuntado=true`, `version=2` ✔

### F3
- `debe_cambiar_password` presente en `/auth/me/` y en `TokenPair`; gate bloqueante montado en el
  layout autenticado. `POST /auth/me/cambiar-password/` cableado (no probado destructivamente sobre
  `smoke_admin` para no invalidar sus credenciales).
- `revisar-declaraciones` añadido como `FlowAction` de `interns` (roles Universidad/Admin);
  `estado_declaraciones` mostrado en el detalle del internado. Endpoints confirmados en el OpenAPI.

## Cobertura de tareas

Todas las secciones 1–7 del spec quedan `[x]`. Capa API en `lib/api/storage.ts`; visualización con
fallback en `components/ui/entity-logo.tsx`; subida de logo en
`components/catalogos/logo-upload-dialog.tsx`; checklist/subida de anexos en
`components/almacenamiento/annex-checklist-dialog.tsx`; F3 en `components/auth/change-password-gate.tsx`
+ `lib/auth/*`. Configs de entidad con columna «Logo» y sin el campo manual `referencia_logo`.

## Pendiente / notas para v2

- Validación real del signed URL de logo requiere entorno con GCS (prod); en dev el stub no sirve
  binarios, por eso se ve el fallback.
- `documents/upload` genérico (Etapa 1) queda fuera de alcance, solo documentado.
