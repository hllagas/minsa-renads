# Validación — Módulo `actividades`

## ✅ APROBADO (sin errores altos/medios). **MÓDULO CERRADO.**

Revisado contra `spec/actividades.md`, contrato `docs/api-actividades.md` y convenciones del proyecto.

### Cobertura del spec
| Tarea | Estado | Evidencia |
|-------|--------|-----------|
| T1 tipos/hooks | ✅ | `lib/actividades/hooks.ts` (`teachingActivityHooks`, read/write tipados) |
| T2 campos | ✅ | `activity-fields.ts` (alta + edición subconjunto) |
| T3 acciones | ✅ | `flow-actions.ts`: validar (Tutor), subsanar (Universidad/Tutor/Sede), cambiar-estado (Admin) |
| T4 lista | ✅ | `/actividades` DataTable + filtros tipo/estado + búsqueda + paginación |
| T5 alta/edición | ✅ | `/actividades/nueva`, `/actividades/[id]/editar` |
| T6 detalle | ✅ | Tabs Datos/Historial + acciones gateadas por rol |
| T7 nav + lint/build | ✅ | ítem "Actividades" del shell → `/actividades`; `npm run lint` 0 errores, `npm run build` 18 rutas |
| T8 guía pruebas | ✅ | `spec/actividades.guia_pruebas.md` |

### Conformidad
- **Stack:** 0 `axios`/`fetch` en `app/`/`components/`; toda petición vía TanStack Query; tablas vía `<DataTable>`; flujo vía `useResourceAction`. ✓
- **Contrato (backend real):** 3 endpoints con forma paginada DRF (`count/next/previous/results`); `POST /teaching-activities/` con datos incompletos → `400` (validación, no 500): el payload del front alcanza correctamente la validación del backend. ✓
- **Reuso (DRY/SOLID):** sin plomería nueva — reutiliza CRUD genérico, `EntityCombobox`, `ResourceForm`, `FlowActionDialog`, flujo genérico y `SimpleObjectTable`. ✓
- **Roles:** registrar → Universidad/Tutor/Sede docente; validar → Tutor; subsanar → Universidad/Tutor/Sede; cambiar-estado → Administrador RENADS. ✓

### Hallazgos / limitaciones (aceptados MVP, no bloquean)
- **Datos no seedeados:** `activity-types` = 0 y `teaching-activities` = 0 en el backend actual (también
  faltan interns/internships/service-areas — ver módulo Internados). El registro real requiere crear
  esos datos primero. **Gap de datos del backend**, no del front. La guía indica los prerrequisitos.
- **Editar:** `tipo_actividad` arranca vacío (el read da el nombre, no el id); PATCH lo omite si no se
  cambia. Documentado.
- **Enums:** `validar.resultado` con choices VALIDADA/OBSERVADA/RECHAZADA; el resto texto/numérico.

### Comprobaciones técnicas
- `npm run lint` → 0 errores, 1 warning (DataTable/React Compiler, ajeno).
- `npm run build` → 18 rutas OK (3 nuevas de actividades).
- Smoke API: 3 listas paginadas; POST validación → 400.

---

## Validación — Actualización de contrato (2026-07-17)

### ✅ APROBADO (sin errores altos/medios). Delta D1–D6 completo; el módulo sigue cerrado.

Revisado contra `spec/actividades.md` §«Actualización de contrato (2026-07-17)», `docs/api-actividades.md`
(sincronizado) y `lib/api/schema.d.ts` (regenerado).

### Cobertura del delta
| Tarea | Estado | Evidencia |
|-------|--------|-----------|
| D1 campos del alta | ✅ | `lib/actividades/activity-fields.ts:13-27`: `estudiante` (select `students`, `personaLabel`) e `interno` (select `interns`, label «Interno (proceso de internado)»); `internadoLabel` lee `row.estudiante` (`:6-7`); `ACTIVITY_EDIT_FIELDS` sin cambios |
| D2 lista | ✅ | `app/(app)/actividades/page.tsx:36` (`accessorKey: "estudiante"`, header «Estudiante»), `:66` («…de los estudiantes.»); filtros `tipo_actividad`/`estado_actual`/búsqueda intactos |
| D3 detalle | ✅ | `app/(app)/actividades/[id]/page.tsx:55` (`Actividad de ${a.estudiante}`), `:94` (`<Dato label="Estudiante" value={a.estudiante} />`); sin usos de `a.interno` como texto |
| D4 hooks/flow sin cambios | ✅ | `lib/actividades/hooks.ts` (`teaching-activities`) y `flow-actions.ts` (`validar`/`subsanar`/`cambiar-estado`) intactos; compilan con el schema regenerado (tsc limpio) |
| D5 dashboard sin cambios | ✅ | grep de `internado`/`.interno` en `lib/dashboard/` y `components/dashboard/` sin resultados referidos a campos de `TeachingActivity` (solo módulo «internados» y proceso) |
| D6 verificación | ✅ | `npx tsc --noEmit` → 0 errores; `npm run lint` → 0 errores, 1 warning preexistente (`data-table.tsx`, react-hooks/incompatible-library) |

### Conformidad de contrato
- `TeachingActivityRead.estudiante` (etiqueta legible) y `Write.estudiante`/`interno` (ids) verificados
  en `schema.d.ts` (`:4585-4587`, `:4637-4639`); el endpoint `/teaching-activities/` y sus acciones no
  cambiaron.

### Nota
- El smoke manual (alta con selects `students`/`interns` → validar/subsanar contra el backend) queda
  reportado por Implement; este validador verificó contrato, código estático, tsc y lint.
