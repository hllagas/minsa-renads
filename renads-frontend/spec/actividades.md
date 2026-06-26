# Spec — Módulo `actividades` (Registrar Actividades Docente-Asistenciales)

Módulo 4 (último) del MVP (`docs/mvp.md`). El más pequeño: 2 catálogos + `TeachingActivity` con
validación e historial. Contrato del backend: **`docs/api-actividades.md`**. Reutiliza toda la infra
de los módulos previos (CRUD genérico, `EntityCombobox`, `ResourceForm`, `FlowActionDialog`,
`useResourceAction`/`useResourceSubList`, `SimpleObjectTable`, detalle con `Tabs`).

> **Estado:** ✅ **MÓDULO CERRADO.** Implementado y validado sin errores. Ver
> `spec/actividades.validacion.md` y `spec/actividades.guia_pruebas.md`.

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
