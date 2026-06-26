# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este proyecto

Frontend (Next.js) de **RENADS** — Registro Nacional de Articulación Docencia-Servicio en Salud
(MINSA, Perú). Consume el backend **RENADS API** (Django + DRF) ubicado en `D:\dev\renaes\renaes-api`.

**Antes de construir cualquier vista, leer `docs/`** — contiene el contrato del backend (endpoints,
campos, roles, estados) sin necesidad de abrir el repo del backend:

| Doc | Contenido |
|-----|-----------|
| `docs/README.md` | Índice y fuentes de verdad |
| `docs/mvp.md` | **Orden obligatorio de módulos** y alcance de cada uno |
| `docs/backend-overview.md` | Stack, base URL (`http://localhost:8000/api/v1/`), paginación, filtros, roles, OpenAPI |
| `docs/api-auth.md` | JWT (`/auth/token`, `/refresh`, `/me`), roles/grupos, alcance institucional |
| `docs/api-convenios.md` | Módulo 1 — Gestionar Convenios |
| `docs/api-internados.md` | Módulo 2 — Registrar Internados |
| `docs/api-actividades.md` | Módulo 3 — Registrar Actividades docente-asistenciales |
| `docs/frontend-conventions.md` | Idioma, SDD, cliente HTTP, gating por rol, estructura propuesta |

### Módulos del backend

1. **Gestionar Convenios** (`apps/convenios`) — convenios Marco/Específicos, evaluaciones, opiniones (DIGEP/CONAPRES/OGAJ), firmas, publicación, vigencia.
2. **Registrar Internados** (`apps/internados`) — internos, tutores, internados, rotaciones, autorizaciones.
3. **Registrar Actividades** (`apps/actividades`) — actividades docente-asistenciales y su validación.

Más auth/transversal (`apps/common`): login JWT, `/auth/me`, alcance institucional, auditoría.

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
