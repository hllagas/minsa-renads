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

## Módulos transversales / administrativos

Estos módulos **no forman parte de la secuencia obligatoria** (no bloquean el orden 1→4): son
transversales o de administración y se construyen una vez que el core lo permite. Sus rutas ya están
**habilitadas** en el frontend.

### 5. Dashboard (transversal) — analítica
Ruta `/dashboard`. Visibilidad estadística del proceso docencia-servicio.
- Pantallas: tablero con barra de filtros global (rango de fechas, tipo, estado, entidad, ámbito),
  fila de KPIs y gráficos por módulo (Convenios, Internados, Actividades).
- Datos: **Vía A** (agregación en cliente sobre los endpoints de lista existentes) en v1; **Vía B**
  (endpoints `/stats/` del backend) pendiente para escalar.
- Librería de gráficos: shadcn charts (Recharts) con tokens `--chart-1..5`.
- Gating por rol: visible a todo usuario autenticado (cada gráfico respeta el alcance del backend).
- Endpoints/campos: reutiliza `docs/api-convenios.md`, `docs/api-internados.md`,
  `docs/api-actividades.md`. Diseño y lista de gráficos: `docs/dashboard-graficos.md`; spec:
  `spec/dashboard.md`.
- **Estado:** v1 implementado (KPIs + C1/C2/C3 · I1/I2/I5 · A1/A2/A3). Pendiente v2 y migración a `/stats/`.

### 6. Catálogos — mantenimiento de tablas maestras
Ruta `/catalogos`. CRUD de las tablas maestras del sistema.
- Pantallas: lista/alta/edición/baja de cada maestro vía el CRUD declarativo (`ResourceCrud`).
- Recursos: catálogos de solo lectura del backend (p. ej. `convention-statuses`, `specialties`,
  `regions`, `service-areas`, `activity-types`, `internship-statuses`, `rotation-statuses`,
  `document-types`, etc.) y entidades organizacionales/académicas con escritura
  (`universities`, `ipress`, `faculties`, `professional-careers`, `minsa-organs`, ...).
- Gating por rol: **Administrador RENADS** (la autoridad final es el backend).
- Endpoints/campos: catálogos y entidades listados en `docs/api-convenios.md` (secciones
  «Catálogos» y «Entidades organizacionales/académicas»); también `internship-statuses`/
  `rotation-statuses`/`service-areas` (`docs/api-internados.md`) y `activity-types`/`activity-statuses`
  (`docs/api-actividades.md`).
- **Estado:** ruta habilitada (placeholder). Pendiente spec/implementación.

### 7. Gestión de Usuarios — usuarios, perfiles y roles
Ruta `/usuarios`. Administración de usuarios y su alcance institucional.
- Pantallas: lista/alta/edición de usuarios; asignación de **grupos/roles** y de **perfiles
  institucionales** (vínculo usuario↔entidad para el alcance).
- Recursos: `user-entity-profiles` (escritura solo `Administrador RENADS`, sin lectura abierta),
  grupos/roles del backend, y datos de usuario expuestos por `GET /auth/me/`.
- Gating por rol: **Administrador RENADS**.
- Endpoints/campos: `docs/api-auth.md` (roles/grupos, alcance institucional, `user-entity-profiles`).
- **Estado:** ruta habilitada (placeholder). Pendiente spec/implementación.

---

## Resumen

| # | Módulo | Tipo | Depende de | Doc contrato | Estado |
|---|--------|------|------------|--------------|--------|
| 1 | Auth | Base (no CRUD) | — | `docs/api-auth.md` | Hecho |
| 2 | Convenios | CRUD + flujo | Auth | `docs/api-convenios.md` | — |
| 3 | Internados | CRUD + flujo | Convenios | `docs/api-internados.md` | — |
| 4 | Actividades | CRUD + flujo | Internados | `docs/api-actividades.md` | — |
| 5 | Dashboard | Transversal (analítica) | Convenios/Internados/Actividades | `docs/dashboard-graficos.md` · `spec/dashboard.md` | v1 hecho |
| 6 | Catálogos | CRUD maestros | Auth | `docs/api-convenios.md` (catálogos/entidades) | Ruta habilitada |
| 7 | Gestión de Usuarios | Administración | Auth | `docs/api-auth.md` | Ruta habilitada |
