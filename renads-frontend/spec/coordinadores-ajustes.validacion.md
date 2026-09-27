# Validación — Coordinadores: ajustes post-migración 0033+0034

**Fecha:** 2026-09-26
**Resultado:** VALIDACIÓN: APROBADA

Todas las tareas T1–T8 están implementadas correctamente. No se encontraron errores altos ni medios.

## Resumen por tarea

**T1 — `lib/internados/types.ts`**
- `CoordinatorRead` expone `universidad: number` (línea 30) y `universidad_detalle: { id: number; nombre: string }` (línea 31). Correcto.
- `CoordinatorSedeRead` no tiene campo `universidad: number` de primer nivel — solo `id`, `coordinador`, `ipress`, `universidad_detalle`, `ipress_detalle`. Correcto.

**T2 — `lib/internados/coordinator.ts` — payload**
- `createCoordinatorSede` acepta `payload: { ipress: string }` (línea 50). Correcto.
- `useAddCoordinatorSede` mutationFn tipado como `(payload: { ipress: string })` (línea 153). Correcto.

**T3 — `lib/internados/coordinator.ts` — URLs tutores**
- `getCoordinatorTutors` usa `/coordinators/${coordinatorId}/sedes/${sedePk}/tutores/` (línea 80). Correcto.
- `createCoordinatorTutor` usa `/coordinators/${coordinatorId}/sedes/${sedePk}/tutores/` (línea 116). Correcto.
- `deleteCoordinatorTutor` usa `/coordinators/${coordinatorId}/sedes/${sedePk}/tutores/${tutorPk}/` (línea 132). Correcto.
- El `console.warn` también menciona `/tutores/`. Correcto.

**T4 — `lib/internados/coordinator.ts` — `useSedesDisponibles`**
- `SedeDisponible` exportada con `id: string` y `nombre: string` (líneas 221–224). Correcto.
- `getSedesDisponibles` llama `GET /coordinators/${coordinatorId}/sedes-disponibles/` (línea 231). Correcto.
- `useSedesDisponibles` exportada, habilitada solo si `coordinatorId != null` (líneas 237–243). Correcto.

**T5 — `lib/internados/persons.ts`**
- Filtro usa `name: "universidad"` (línea 428), no `sedes__universidad`. Correcto.
- Columna `universidad` renderiza `detalleNombre(r.universidad_detalle)` (línea 323). Correcto.
- Campo `universidad` en `fields`: `type: "select"`, `required: true`, `optionsEndpoint: "universities"` (líneas 368–374). Correcto.
- `editFields` incluye `"universidad"` en la condición `disabled: true` (línea 413). Correcto.

**T6 — `app/(app)/internados/personas/[entidad]/page.tsx`**
- `initialFilters` usa `{ universidad: String(universidad) }` (líneas 289–293). Correcto.
- `<ResourceCrud>` tiene `fixedValues={universidad != null ? { universidad } : undefined}` (línea 387). Correcto.

**T7 — `components/internados/coordinator-sedes-dialog.tsx`**
- No existe estado `univSeleccionada` ni selector de universidad en el JSX. Correcto.
- Sección «Agregar sede» usa `useSedesDisponibles(coordinatorId)` (línea 78). Correcto.
- IPRESS usa `<Select>` nativo (shadcn) poblado con `sedesDisponibles` (líneas 368–386), no `EntityCombobox<string>`. Correcto.
- Mensaje «No hay sedes disponibles para este coordinador.» cuando lista vacía (línea 389). Correcto.
- `handleAgregarSede` envía solo `{ ipress: ipressSeleccionada }` (línea 103). Correcto.
- Selector de tutores usa `EntityCombobox` con `params={{ universidades: String(universidad) }}` vía `tutorParams` (líneas 95–98, 309). Correcto.
- Botón «Agregar sede» deshabilitado si `ipressSeleccionada == null || addSedeMutation.isPending || loadingDisponibles` (líneas 398–401). Correcto.

**T8 — `docs/api-internados.md`**
- Tabla de rutas incluye `/tutores/`, `/tutores/{tutor_pk}/` y `sedes-disponibles` (líneas 159–161). Correcto.
- Filtros: `activo`, `universidad`, `sedes__ipress` (línea 163). Correcto.
- Coordinator lectura: incluye `universidad (FK req)` y `universidad_detalle {id, nombre}` (líneas 168–174). Correcto.
- Coordinator escritura: incluye `universidad (req)` (líneas 177–182). Correcto.
- CoordinatorSede lectura: sin campo `universidad` de primer nivel; tiene `universidad_detalle` (líneas 184–189). Correcto.
- CoordinatorSede escritura: solo `ipress (req)` con nota de migración 0033 (líneas 191–196). Correcto.
- Sección `CoordinatorSede — sedes disponibles` presente (líneas 198–204). Correcto.

## Criterios de aceptación globales

1. Listado filtra por `?universidad=<id>`. CUMPLIDO (T5+T6).
2. Alta de coordinador envía `universidad` en POST. CUMPLIDO (T5+T6 via `fixedValues`).
3. POST sedes envía solo `{ ipress }`. CUMPLIDO (T2+T7).
4. GET/POST/DELETE tutores usan `/tutores/`. CUMPLIDO (T3).
5. Dialog «Sedes» usa `sedes-disponibles`. CUMPLIDO (T4+T7).
6. `CoordinatorRead.universidad` y `universidad_detalle` existen y se usan en columna. CUMPLIDO (T1+T5).
7. `CoordinatorSedeRead` sin `universidad: number` de primer nivel. CUMPLIDO (T1).
8. `docs/api-internados.md` §Coordinadores coherente con backend. CUMPLIDO (T8).
9. No se detectaron errores de tipo en la revisión estática de los 6 archivos modificados.

Todas las tareas T1–T8 están implementadas correctamente. No se encontraron errores altos ni medios.

## Resumen por tarea

**T1 — `lib/internados/types.ts`**
- `CoordinatorRead` expone `universidad: number` (línea 30) y `universidad_detalle: { id: number; nombre: string }` (línea 31). Correcto.
- `CoordinatorSedeRead` no tiene campo `universidad: number` de primer nivel — solo `id`, `coordinador`, `ipress`, `universidad_detalle`, `ipress_detalle`. Correcto.

**T2 — `lib/internados/coordinator.ts` — payload**
- `createCoordinatorSede` acepta `payload: { ipress: string }` (línea 50). Correcto.
- `useAddCoordinatorSede` mutationFn tipado como `(payload: { ipress: string })` (línea 153). Correcto.

**T3 — `lib/internados/coordinator.ts` — URLs tutores**
- `getCoordinatorTutors` usa `/coordinators/${coordinatorId}/sedes/${sedePk}/tutores/` (línea 80). Correcto.
- `createCoordinatorTutor` usa `/coordinators/${coordinatorId}/sedes/${sedePk}/tutores/` (línea 116). Correcto.
- `deleteCoordinatorTutor` usa `/coordinators/${coordinatorId}/sedes/${sedePk}/tutores/${tutorPk}/` (línea 132). Correcto.
- El `console.warn` también menciona `/tutores/`. Correcto.

**T4 — `lib/internados/coordinator.ts` — `useSedesDisponibles`**
- `SedeDisponible` exportada con `id: string` y `nombre: string` (líneas 221–224). Correcto.
- `getSedesDisponibles` llama `GET /coordinators/${coordinatorId}/sedes-disponibles/` (línea 231). Correcto.
- `useSedesDisponibles` exportada, habilitada solo si `coordinatorId != null` (líneas 237–243). Correcto.

**T5 — `lib/internados/persons.ts`**
- Filtro usa `name: "universidad"` (línea 428), no `sedes__universidad`. Correcto.
- Columna `universidad` renderiza `detalleNombre(r.universidad_detalle)` (línea 323). Correcto.
- Campo `universidad` en `fields`: `type: "select"`, `required: true`, `optionsEndpoint: "universities"` (líneas 368–374). Correcto.
- `editFields` incluye `"universidad"` en la condición `disabled: true` (línea 413). Correcto.

**T6 — `app/(app)/internados/personas/[entidad]/page.tsx`**
- `initialFilters` usa `{ universidad: String(universidad) }` (líneas 289–293). Correcto.
- `<ResourceCrud>` tiene `fixedValues={universidad != null ? { universidad } : undefined}` (línea 387). Correcto.

**T7 — `components/internados/coordinator-sedes-dialog.tsx`**
- No existe estado `univSeleccionada` ni selector de universidad en el JSX. Correcto.
- Sección «Agregar sede» usa `useSedesDisponibles(coordinatorId)` (línea 78). Correcto.
- IPRESS usa `<Select>` nativo (shadcn) poblado con `sedesDisponibles` (líneas 368–386), no `EntityCombobox<string>`. Correcto.
- Mensaje «No hay sedes disponibles para este coordinador.» cuando lista vacía (línea 389). Correcto.
- `handleAgregarSede` envía solo `{ ipress: ipressSeleccionada }` (línea 103). Correcto.
- Selector de tutores usa `EntityCombobox` con `params={{ universidades: String(universidad) }}` vía `tutorParams` (líneas 95–98, 309). Correcto.
- Botón «Agregar sede» deshabilitado si `ipressSeleccionada == null || addSedeMutation.isPending || loadingDisponibles` (líneas 398–401). Correcto.

**T8 — `docs/api-internados.md`**
- Tabla de rutas incluye `/tutores/`, `/tutores/{tutor_pk}/` y `sedes-disponibles` (líneas 159–161). Correcto.
- Filtros: `activo`, `universidad`, `sedes__ipress` (línea 163). Correcto.
- Coordinator lectura: incluye `universidad (FK req)` y `universidad_detalle {id, nombre}` (líneas 168–174). Correcto.
- Coordinator escritura: incluye `universidad (req)` (líneas 177–182). Correcto.
- CoordinatorSede lectura: sin campo `universidad` de primer nivel; tiene `universidad_detalle` (líneas 184–189). Correcto.
- CoordinatorSede escritura: solo `ipress (req)` con nota de migración 0033 (líneas 191–196). Correcto.
- Sección `CoordinatorSede — sedes disponibles` presente (líneas 198–204). Correcto.

## Criterios de aceptación globales

1. Listado filtra por `?universidad=<id>`. CUMPLIDO (T5+T6).
2. Alta de coordinador envía `universidad` en POST. CUMPLIDO (T5+T6 — `fixedValues`).
3. POST sedes envía solo `{ ipress }`. CUMPLIDO (T2+T7).
4. GET/POST/DELETE tutores usan `/tutores/`. CUMPLIDO (T3).
5. Dialog «Sedes» usa `sedes-disponibles`. CUMPLIDO (T4+T7).
6. `CoordinatorRead.universidad` y `universidad_detalle` existen y se usan en columna. CUMPLIDO (T1+T5).
7. `CoordinatorSedeRead` sin `universidad: number` de primer nivel. CUMPLIDO (T1).
8. `docs/api-internados.md` §Coordinadores coherente con backend. CUMPLIDO (T8).
9. Compilación sin errores de tipo: pendiente de verificación con `npm run build` (no hay errores de tipo detectados en la revisión estática).
