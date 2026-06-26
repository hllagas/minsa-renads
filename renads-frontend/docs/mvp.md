# MVP — Frontend RENADS (alcance y orden de módulos)

Este documento es la **fuente de verdad del orden de trabajo** del frontend. Define qué se
construye en cada módulo y en qué secuencia. El agente **`orchestrator`** lo consulta para decidir
el siguiente módulo.

## Regla de oro

> **Un módulo a la vez.** No se inicia un módulo nuevo hasta que el anterior esté **validado**
> (cerrado por el agente `validator`). El orden de abajo es obligatorio: respeta las dependencias
> de datos del backend (un módulo reutiliza catálogos/entidades del anterior).

## Metodología

Cada módulo pasa por el ciclo SDD: **spec → (aprobación humana) → implement → validator**
(ver `.claude/agents/` y la sección SDD de `CLAUDE.md`). El spec de cada módulo vive en
`spec/<modulo>.md`. Antes de espec­ificar o implementar, **leer siempre `docs/*.md`** (contrato del
backend).

## Stack del módulo (aplica a todos)

- **shadcn/ui** — todos los componentes de UI.
- **TanStack Query** — toda petición al backend (fetching, cache, invalidación, mutaciones).
- **TanStack Table** — todas las tablas/listados (vía wrapper `<DataTable>`).
- **Axios** — cliente HTTP único (`lib/api/client.ts`) con JWT + refresh.
- **Zustand** — estado global de cliente (sesión, `me`, UI). No duplica datos de servidor.

Convenciones de idioma y patrones: ver `docs/frontend-conventions.md`.

---

## Orden de módulos

### 1. Auth (base — NO es CRUD)
**Primero, obligatorio.** Todo lo demás depende de la sesión.
- Pantallas: login.
- Funcionalidad: obtener token (`POST /auth/token/`), refresh automático (`/auth/token/refresh/`),
  cargar usuario (`GET /auth/me/`), persistir sesión, **route guard** (redirige a login sin token),
  **shell/layout** autenticado (navegación + gating por rol según `me.grupos`).
- Estado: token + `me` en store Zustand; `me` cacheado con Query.
- Endpoints: ver `docs/api-auth.md`.
- **Terminado cuando:** login funciona contra el backend real, el refresh renueva sesión en `401`,
  las rutas protegidas redirigen sin sesión, y el menú/acciones se ocultan según rol.

### 2. Convenios (CRUD + flujo) — Módulo 1 del backend
Se hace **antes que los demás** porque define catálogos y entidades reutilizadas (universidades,
IPRESS, regiones, especialidades, etc.).
- Pantallas: lista (tabla con filtros/paginación), detalle, alta/edición, acciones de flujo
  (cambiar-estado, evaluación técnica, opinión CONAPRES, campos clínicos, opinión jurídica, firma,
  publicación, participantes, historial).
- CRUD: `conventions`, `convention-templates`, `representatives` y entidades organizacionales/
  académicas (universities, ipress, faculties, professional-careers, ...). Catálogos en solo lectura
  (selects).
- Gating por rol: DIGEP, CONAPRES, OGAJ, Secretaría General, Administrador RENADS (ver tabla en
  `docs/api-convenios.md`).
- Endpoints/campos: `docs/api-convenios.md`.
- **Terminado cuando:** CRUD de convenios + entidades funciona, las acciones de flujo respetan rol,
  las tablas usan filtros del backend, y los selects se alimentan de catálogos reales.

### 3. Internados (CRUD + flujo) — Módulo 2 del backend
Depende de convenios/IPRESS/universidades (módulo 2).
- Pantallas: lista/detalle/alta/edición de internados; subpantallas de rotaciones; CRUD de
  `interns` y `tutors`; acciones (cambiar-estado, cambiar-tutor, rotaciones: crear/autorizar/iniciar/
  cambiar-estado, historiales).
- Gating por rol: Universidad, Autoridad de convenio, Administrador RENADS.
- Endpoints/campos: `docs/api-internados.md`.
- **Terminado cuando:** se registra un internado sobre convenio específico vigente, se gestionan
  rotaciones con su flujo de autorización, y los CRUD de internos/tutores funcionan con alcance.

### 4. Actividades (CRUD + flujo) — Módulo 3 del backend
Depende de internados/rotaciones (módulo 3, el más pequeño).
- Pantallas: lista/detalle/alta/edición de actividades docente-asistenciales; acciones (validar,
  subsanar, cambiar-estado, historial).
- Gating por rol: Universidad/Tutor/Sede docente (registrar), Tutor (validar), Administrador RENADS.
- Endpoints/campos: `docs/api-actividades.md`.
- **Terminado cuando:** se registra/valida/subsana una actividad respetando las RN (internado activo,
  fecha en periodo, rotación autorizada, sin duplicados) y el rol correspondiente.

---

## Resumen

| # | Módulo | Tipo | Depende de | Doc contrato |
|---|--------|------|------------|--------------|
| 1 | Auth | Base (no CRUD) | — | `docs/api-auth.md` |
| 2 | Convenios | CRUD + flujo | Auth | `docs/api-convenios.md` |
| 3 | Internados | CRUD + flujo | Convenios | `docs/api-internados.md` |
| 4 | Actividades | CRUD + flujo | Internados | `docs/api-actividades.md` |
