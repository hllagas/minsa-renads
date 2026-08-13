# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este proyecto

Frontend (Next.js) de **RENADS** — Registro Nacional de Articulación Docencia-Servicio en Salud
(MINSA, Perú). Consume el backend **RENADS API** (Django + DRF) ubicado en `D:\dev\renads\renads-api`
(monorepo: back y front comparten el repo raíz `D:\dev\renads`, con historial de commits común).

**Antes de construir cualquier vista, leer `docs/`** — contiene el contrato del backend (endpoints,
campos, roles, estados) sin necesidad de abrir el repo del backend:

| Doc | Contenido |
|-----|-----------|
| `docs/README.md` | Índice y fuentes de verdad |
| `docs/mvp.md` | **Orden obligatorio de módulos** y alcance de cada uno |
| `docs/backend-overview.md` | Stack, base URL (`http://localhost:8000/api/v1/`), paginación, filtros, roles, OpenAPI |
| `docs/api-auth.md` | JWT (`/auth/token`, `/refresh`, `/me`), roles/grupos, alcance institucional |
| `docs/api-convenios.md` | Módulo 1 — Gestionar Convenios (núcleo) |
| `docs/api-catalogos.md` | Módulo 1 — CRUD transversales: catálogos, entidades, representantes, documentos, auditoría (rutas `/catalogos` y `/usuarios`) |
| `docs/api-internados.md` | Módulo 2 — Registrar Internados |
| `docs/api-actividades.md` | Módulo 3 — Registrar Actividades docente-asistenciales |
| `docs/api-usuarios.md` | Gestión de Usuarios — usuarios, roles/grupos y permisos (`apps/common`, ruta `/usuarios`, solo superusuario) |
| `docs/api-almacenamiento.md` | **Transversal** — adjuntos reales: logos de entidades (`upload-logo`/`logo-url`) y PDFs de anexos por actor (`annex-checklist`/`annex-upload`), sobre GCS + signed URLs; incluye Feature F3 (contraseña temporal + declaraciones juradas) |
| `docs/frontend-conventions.md` | Idioma, SDD, cliente HTTP, gating por rol, estructura propuesta |

### Módulos del backend

1. **Gestionar Convenios** (`apps/convenios`) — convenios Marco/Específicos, evaluaciones, opiniones (DIGEP/CONAPRES/OGAJ), firmas, publicación, vigencia.
   - **CRUD transversales del Módulo 1** (`apps/convenios` + `apps/common`): catálogos, entidades organizacionales/académicas (CRUD, escritura `Administrador RENADS`), representantes, `user-entity-profiles`, **documentos** (`documents`, gestión documental polimórfica con versionado) y **bitácora de auditoría** (`audit-logs`, solo lectura, `Administrador RENADS`/Auditor). Contrato: `docs/api-catalogos.md`. Rutas front: `/catalogos` y `/usuarios`.
   - **Catálogos promovidos a CRUD** (antes solo lectura; ahora escritura `Administrador RENADS`, filtro `activo`, search `codigo`/`nombre`): `document-types`, `university-entity-types`, `authorization-types`, `academic-levels`, `regional-organ-types`, `minsa-organ-types`.
   - **Borrado protegido → HTTP 409** (`ProtectedDeleteConflict`): al eliminar un registro referenciado por FK protegida, el backend devuelve 409 con mensaje legible (no 500). El front debe mostrar el detalle (`extractApiError`).
2. **Registrar Internados** (`apps/internados`) — internos, tutores, internados, rotaciones, autorizaciones.
   Incluye Feature F3: onboarding del interno con contraseña temporal (`debe_cambiar_password` +
   `/auth/me/cambiar-password/`) y declaraciones juradas (`estado_declaraciones`, `revisar-declaraciones`).
   - **Tutor ↔ universidades** (RN-24): `tutors.universidades` es M2M de **1 a 2** universidades (400 si 0 o >2); filtro `?universidades=<id>`. Los tutores no están acotados por universidad en lectura (son compartidos).
   - **Contacto de emergencia** movido de `students` → **`interns`/internado** (`contacto_emergencia_nombre`/`_telefono`/`_parentesco` FK `relationship-types`). `students.anio_academico` **eliminado** (y de la trama de carga masiva).
   - **Anexos DJ del interno** (actor `INTERNO`, `annex-upload`/`annex-checklist`) se adjuntan **sobre el internado** (`interns/{id}/...`), **no** sobre el estudiante. Puede adjuntar el rol `Universidad`/`Administrador RENADS` o el propio `Interno`.
   - **Accesos y alcance por universidad** (contrato backend `docs/api_accesos_frontend.md`): la UI resuelve el selector de universidad desde `perfiles` de `/auth/me/` (una → fija; varias → elegir; global → catálogo). Reflejado en `lib/auth/scope.ts`.
3. **Registrar Actividades** (`apps/actividades`) — actividades docente-asistenciales y su validación.

**Adjuntos reales (transversal, Módulos 1–2):** subida/visualización de **logos** de entidades
(`universities`, `regional-governments`, `regional-organs`, `executing-units`, `ipress`) con fallback
institucional, y **anexos PDF** (declaraciones juradas por actor: `students`, `university-authorities`,
`representatives`). Contrato: `docs/api-almacenamiento.md`. Capa API en `lib/api/storage.ts`; UI en
`components/ui/entity-logo.tsx`, `components/catalogos/logo-upload-dialog.tsx`,
`components/almacenamiento/annex-checklist-dialog.tsx`.

Más auth/transversal (`apps/common`): login JWT, `/auth/me`, alcance institucional, auditoría, y
**administración de usuarios/roles/permisos** (`users`, `groups`, `permissions` — solo superusuario;
contrato en `docs/api-usuarios.md`, ruta front `/usuarios`).

### Convenciones de idioma

- **UI/comentarios/docs en español; código en inglés.** Las claves del API van en español
  (`fecha_inicio`, `estado_codigo`) — no traducirlas al tipar.
- El backend es la fuente de verdad del contrato; preferir tipos generados de OpenAPI
  (`/api/v1/schema/`). Mantener `docs/` sincronizada cuando cambie un contrato del backend.

## Metodología SDD (obligatoria)

El frontend se desarrolla con **Spec Driven Development (SDD)**, coordinado por el agente
**`orchestrator`** (`.claude/agents/orchestrator.md`). **Para todo desarrollo de un módulo o feature,
usar SIEMPRE el flujo del orquestador:**

```
orchestrator → spec → (APROBACIÓN HUMANA) → implement → validator → (repetir implement↔validator hasta OK)
```

- **`orchestrator`** — coordina; no escribe código ni specs. Elige el siguiente módulo según `docs/mvp.md`.
- **`spec`** — analiza el módulo y crea las tareas en `spec/<modulo>.md`. **La lista debe aprobarla un humano antes de Implement.**
- **`implement`** — escribe el código según el spec, con buenas prácticas Next.js (App Router) y SOLID.
- **`validator`** — verifica que el código cumpla el spec/contrato, **marca tareas hechas** en `spec/<modulo>.md` y genera `spec/<modulo>.validacion.md`.

**Regla de oro: un módulo a la vez.** El orden lo define `docs/mvp.md` (Auth → Convenios →
Internados → Actividades). No iniciar un módulo sin cerrar (validar) el anterior. Antes de
especificar o implementar, **leer siempre `docs/*.md`** (contrato del backend).

## Commands

- `npm run dev` — start dev server at http://localhost:3000 (hot reload)
- `npm run build` — production build
- `npm start` — serve the production build (run `build` first)
- `npm run lint` — ESLint

No test runner is configured yet — there are no tests to run until one is added.

## Stack

Base: Next.js 16 (App Router) · React 19 · TypeScript 5 (strict) · Tailwind CSS v4 · ESLint 9 (flat config).

Librerías del proyecto (rol fijo por convención):

- **shadcn/ui** — todos los componentes de UI (Radix + Tailwind). No escribir UI a mano si existe componente shadcn.
- **TanStack Query** (`@tanstack/react-query`) — server-state: toda petición al backend (fetch, cache, invalidación, mutaciones). No usar `fetch`/Axios suelto en componentes.
- **TanStack Table** (`@tanstack/react-table`) — todas las tablas/listados, vía el wrapper `components/ui/data-table.tsx`.
- **Axios** — cliente HTTP único en `lib/api/` (JWT + refresh + unwrap de paginación DRF). Axios solo se usa dentro de `lib/api/`.
- **Zustand** — estado global de cliente (sesión/token, `me`, UI). No duplicar datos de servidor (eso es TanStack Query).

## Architecture notes

- **App Router**: all app code lives in `app/`. `app/layout.tsx` is the root layout — it loads Geist / Geist Mono via `next/font/google` and sets the html/body flex-column shell. `app/page.tsx` is the home route.
- **Tailwind v4 is configured in CSS, not JS** — there is no `tailwind.config.js`. Design tokens live in `app/globals.css` via `@import "tailwindcss"` and an `@theme inline` block. To add colors/fonts/tokens, edit `globals.css`, not a JS config. The PostCSS wiring is in `postcss.config.mjs`.
- **Dark mode** uses `prefers-color-scheme` with CSS variables (`--background` / `--foreground`) defined in `app/globals.css`.
- **Path alias**: `@/*` maps to the repo root (see `tsconfig.json`), e.g. `import x from "@/app/..."`.
- **ESLint** uses flat config in `eslint.config.mjs`, extending `eslint-config-next` core-web-vitals + typescript.
