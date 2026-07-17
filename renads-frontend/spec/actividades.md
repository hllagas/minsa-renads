# Spec — Módulo `actividades` (Registrar Actividades Docente-Asistenciales)

Módulo 4 (último) del MVP (`docs/mvp.md`). El más pequeño: 2 catálogos + `TeachingActivity` con
validación e historial. Contrato del backend: **`docs/api-actividades.md`**. Reutiliza toda la infra
de los módulos previos (CRUD genérico, `EntityCombobox`, `ResourceForm`, `FlowActionDialog`,
`useResourceAction`/`useResourceSubList`, `SimpleObjectTable`, detalle con `Tabs`).

> **Estado:** ✅ **MÓDULO CERRADO.** Implementado y validado sin errores. Ver
> `spec/actividades.validacion.md` y `spec/actividades.guia_pruebas.md`.
> ⚠️ **Pendiente:** aplicar la sección «Actualización de contrato (2026-07-17)» (abajo).

## Resumen / pantallas
- **Actividades** `/actividades`: lista (DataTable + filtros + paginación), detalle con pestaña
  Historial + acciones de flujo, alta/edición.
- Sin maestros propios (reusa interns, internships, rotations, tutors, ipress, service-areas como selects).

## Reglas de negocio relevantes (UX; el backend es autoridad)
- Registrar solo si el **internado está activo**; `fecha_actividad` dentro del periodo del internado.
- Si se envía `rotacion`, debe pertenecer al internado y estar autorizada/en curso.
- No duplicar por (`interno`, `fecha_actividad`, `ipress`, `servicio_area`).
- Una actividad `VALIDADA` no se modifica; subsanar solo si está `OBSERVADA`.

## Reutilización (ya existe)
- `createResourceHooks`, `ResourceForm`, `EntityCombobox`, `FlowActionDialog`, `SimpleObjectTable`,
  `lib/api/flow.ts` (`useResourceAction`/`useResourceSubList`), patrón detalle con `Tabs`.
- Tipos: `lib/api/schema.d.ts` (`TeachingActivityRead/Write/Update`, `ActivityTypeAuto`, `ActivityStatusAuto`).

---

## Bloque único

- [x] **T1 Tipos/hooks** (`lib/actividades/hooks.ts`): regenerar tipos (`npm run gen:api`);
  `teachingActivityHooks = createResourceHooks<TeachingActivityRead, TeachingActivityWrite>("teaching-activities")`.
- [x] **T2 Campos** (`lib/actividades/activity-fields.ts`):
  - **Alta** (TeachingActivityWrite): `interno` (select interns), `internado` (select internships),
    `ipress` (select ipress), `rotacion` (select rotations, opcional), `tutor` (select tutors),
    `servicio_area` (select service-areas), `tipo_actividad` (select activity-types),
    `fecha_actividad` (date), `descripcion` (text), `carga_horaria` (number).
  - **Edición** (TeachingActivityUpdate, subconjunto): `descripcion`, `carga_horaria`,
    `tipo_actividad`, `servicio_area`.
- [x] **T3 Acciones** (`lib/actividades/flow-actions.ts`) vía `useResourceAction` base
  `teaching-activities`:
  - `validar` (rol `Tutor`): `resultado` (choices VALIDADA/OBSERVADA/RECHAZADA), `comentario` (text).
  - `subsanar` (rol Universidad/Tutor/Sede docente): `descripcion`, `carga_horaria`.
  - `cambiar-estado` (rol Administrador RENADS): `estado_codigo`, `observacion`.
- [x] **T4 Lista** (`app/(app)/actividades/page.tsx`): `<DataTable>` con columnas (interno, ipress,
  tipo, estado, fecha), filtros backend (`interno`, `internado`, `ipress`, `tutor`, `rotacion`,
  `tipo_actividad`, `estado_actual`, rango `fecha_actividad`), búsqueda por `descripcion`, paginación.
  "Nueva" gateada a Universidad/Tutor/Sede docente.
- [x] **T5 Alta/edición** (`/actividades/nueva`, `/actividades/[id]/editar`): `ResourceForm`.
- [x] **T6 Detalle** (`/actividades/[id]`): datos legibles + pestaña **Historial**
  (`useResourceSubList(... "historial")` + `SimpleObjectTable`) + acciones de flujo gateadas por rol.
- [x] **T7 Navegación**: el ítem "Actividades" del shell ya existe (`/actividades`); asegurar enlaces
  detalle/alta. Verificar `npm run lint` y `npm run build` limpios.
- [x] **T8** El validador deja `spec/actividades.validacion.md` y, si OK, `spec/actividades.guia_pruebas.md`.

---

## Criterios de aceptación (de `docs/mvp.md`)
- Registrar/validar/subsanar una actividad respetando las RN (internado activo, fecha en periodo,
  rotación autorizada, sin duplicados) y el rol correspondiente.
- Tablas con filtros/paginación del backend; selects desde recursos reales.

## Decisiones a confirmar antes de Implement
1. **Filtros de la lista:** ¿incluir todos (interno/internado/ipress/tutor/rotacion/tipo/estado) o un
   subconjunto (estado + tipo + búsqueda) para no recargar? **Recomendado: subconjunto** (estado,
   tipo, búsqueda), añadir más si se necesitan.
2. **`rotacion` en alta:** select de todas las rotaciones (no hay endpoint filtrado por internado en
   el contrato). **Recomendado:** select simple opcional; el backend valida pertenencia.

## Fuera de alcance
- Evidencia documental/PDF; reportes/exportación; tests automatizados.

## Referencias
- Endpoints/campos/roles: `docs/api-actividades.md`; roles/alcance: `docs/backend-overview.md`.
- Patrones y stack: `CLAUDE.md`, `docs/frontend-conventions.md`; reutilización de Convenios/Internados.

---

## Actualización de contrato (2026-07-17)

Mantenimiento del módulo (ya validado) por cambio de contrato del backend. Fuentes de verdad:
`docs/api-actividades.md` (ya sincronizado) y `lib/api/schema.d.ts` (ya regenerado — los nombres de
tipos `TeachingActivityRead/Write/Update` no cambian; cambian **campos y recursos relacionados**).

**Resumen del cambio (afecta a este módulo):**
- En `TeachingActivity`: el campo `interno` (persona) → **`estudiante`**; el campo `internado`
  (proceso) → **`interno`**. Filtros: `estudiante`, `interno` (resto igual). El endpoint
  `/teaching-activities/` y sus acciones **no cambian**.
- Recursos relacionados renombrados (módulo internados): personas ahora en **`/students/`** (antes
  `/interns/`) y el proceso de internado en **`/interns/`** (antes `/internships/`).
- Terminología UI: **«estudiante»** = la persona; **«interno»** = el registro del proceso de
  internado. La RN-9 de duplicados ahora se enuncia por (`estudiante`, `fecha_actividad`, `ipress`,
  `servicio_area`).

> Los cambios en archivos compartidos (`components/landing/landing.tsx`, dashboard de internados,
> CRUD de `students`) están especificados en `spec/internados.md` §«Actualización de contrato» —
> no duplicar aquí.

### Tareas

- [x] **D1** `lib/actividades/activity-fields.ts` — renombrar campos del alta (`ACTIVITY_FIELDS`,
  payload de `TeachingActivityWrite`):
  - `interno` (persona) → `estudiante`, `label: "Estudiante"`, `optionsEndpoint: "students"`
    (antes `interns`), mismo `personaLabel`.
  - `internado` (proceso) → `interno`, `label: "Interno (proceso de internado)"`,
    `optionsEndpoint: "interns"` (antes `internships`).
  - `internadoLabel`: leer `row.estudiante` en lugar de `row.interno` (el read de `/interns/`
    ahora expone `estudiante` como etiqueta legible).
  - `ACTIVITY_EDIT_FIELDS` no cambia (`descripcion`, `carga_horaria`, `tipo_actividad`,
    `servicio_area` — igual que `TeachingActivityUpdate`).
  - **Criterio:** el POST a `/teaching-activities/` envía `estudiante` e `interno` (ids) y es
    aceptado; los selects cargan de `/students/` y `/interns/`; las opciones de interno muestran
    el nombre del estudiante.
- [x] **D2** `app/(app)/actividades/page.tsx` — lista:
  - Columna `accessorKey: "interno"` → `"estudiante"` con header «Estudiante» (en el read,
    `estudiante` es la etiqueta legible; `interno` ahora es un id numérico).
  - Descripción del header: «Actividades docente-asistenciales de los internos.» →
    «…de los estudiantes.».
  - Los filtros actuales (`tipo_actividad`, `estado_actual`, búsqueda) no cambian de nombre; si en
    el futuro se agregan filtros por persona/proceso, usar `estudiante` / `interno`.
  - **Criterio:** la columna muestra el nombre del estudiante (sin celdas vacías); textos coherentes.
- [x] **D3** `app/(app)/actividades/[id]/page.tsx` — detalle:
  - Título: `` `Actividad de ${a.interno}` `` → `` `Actividad de ${a.estudiante}` `` (línea ~55).
  - `<Dato label="Interno" value={a.interno} />` → `<Dato label="Estudiante" value={a.estudiante} />`
    (línea ~94).
  - **Criterio:** el detalle muestra el nombre del estudiante; sin usos de `a.interno` como texto
    (si se quisiera mostrar el proceso, sería el id `a.interno` con etiqueta «Interno (id)» —
    opcional, no requerido).
- [x] **D4** `lib/actividades/hooks.ts` y `lib/actividades/flow-actions.ts` — verificación sin
  cambios de código: el endpoint `teaching-activities` y las acciones `validar` / `subsanar` /
  `cambiar-estado` no cambiaron en el contrato. Confirmar que compilan con el schema regenerado.
  - **Criterio:** cero errores TS en `lib/actividades/`; ningún cambio funcional necesario.
- [x] **D5** Dashboard de actividades — verificación sin cambios: `lib/dashboard/hooks.ts` (sección
  actividades) usa solo `estado_codigo`, `fecha_actividad`, `carga_horaria` y `tipo_actividad`,
  que no fueron renombrados; el endpoint `teaching-activities` tampoco. Confirmar que no queda
  ninguna referencia a los campos viejos `interno`/`internado` de actividades en `lib/dashboard/`
  ni en `components/dashboard/`.
  - **Criterio:** `grep` de `internado`/`.interno` en `lib/dashboard/` y `components/dashboard/`
    sin resultados referidos a campos de `TeachingActivity`.
- [x] **D6** Verificación final del módulo: `npx tsc --noEmit` y `npm run lint` limpios; smoke
  manual: lista → detalle → alta de actividad (selects `students`/`interns`) → validar/subsanar.
  - **Criterio:** cero errores de TypeScript y ESLint; alta y acciones responden 2xx.

> **Aprobación humana requerida:** esta lista de tareas delta debe ser aprobada antes de pasar al
> agente Implement.
