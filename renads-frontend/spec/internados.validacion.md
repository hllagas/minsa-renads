# Validación — Módulo `internados`

## ✅ APROBADO (sin errores altos/medios). **MÓDULO CERRADO.**

Revisado contra `spec/internados.md`, contrato `docs/api-internados.md` y convenciones del proyecto.

### Cobertura del spec
| Tarea | Estado | Evidencia |
|-------|--------|-----------|
| T0.1 Tipos OpenAPI | ✅ | `npm run gen:api`; alias en `lib/internados/hooks.ts` (InternshipRead/Write, RotationRead) |
| T0.2 Flow genérico | ✅ | `lib/api/flow.ts` (`useResourceAction`/`useResourceSubList`); convenios refactorizado para delegar |
| T1.1 interns CRUD | ✅ | `persons.ts` + `/internados/personas/interns` (writeRoles Universidad/Admin) |
| T1.2 tutors CRUD | ✅ | `persons.ts` + `/internados/personas/tutors` |
| T1.3 catálogos selects | ✅ | `EntityCombobox` a internship-statuses, rotation-statuses, service-areas, identity-document-types |
| T2.1 hooks internships | ✅ | `internshipHooks` (read/write tipados) |
| T2.2 lista | ✅ | `/internados` DataTable + filtros convenio/estado + búsqueda + paginación |
| T2.3 alta/edición | ✅ | `/internados/nuevo`, `/internados/[id]/editar` (edición = subconjunto) |
| T2.4 detalle | ✅ | Tabs Datos/Rotaciones/Historial + acciones cambiar-estado/cambiar-tutor |
| T3.1 rotaciones hooks/acciones | ✅ | `useResourceAction` base `rotations` (autorizar/iniciar/cambiar-estado) |
| T3.2 UI rotaciones | ✅ | `RotationsPanel` (lista + acciones por rol + crear vía acción del internado) |
| T4.1 lint/build | ✅ | `npm run lint` 0 errores; `npm run build` 15 rutas |
| T4.2 guía pruebas | ✅ | `spec/internados.guia_pruebas.md` |

### Conformidad
- **Stack:** 0 `axios`/`fetch` en `app/`/`components/` (flujo y combobox usan `lib/api/flow.ts` y `lib/api/lookup.ts`). Toda petición vía TanStack Query; tablas vía `<DataTable>`. ✓
- **Contrato (backend real):** 8 endpoints del módulo responden con forma paginada DRF. **CRUD roundtrip POST→PATCH→DELETE** en `tutors` con el payload del front → OK. ✓
- **Reuso (SOLID/DRY):** CRUD genérico (`ResourceCrud`+`writeRoles`), `EntityCombobox`, `ResourceForm`, `FlowActionDialog` y flujo genérico reutilizados sin duplicar. ✓
- **Roles:** interns/tutors escritura Universidad/Admin; internado cambiar-tutor → Universidad, cambiar-estado → Admin; rotación autorizar → Autoridad de convenio, iniciar → Universidad. ✓

### Hallazgos / limitaciones (aceptados MVP, no bloquean)
- **Datos no seedeados:** `service-areas`, `interns`, `tutors`, `internships`, `rotations` = 0 en el
  backend actual. El flujo completo internado→rotación no es probable end-to-end sin crear datos
  (incl. `service-areas`, requerido para crear rotación). Es un **gap de datos del backend**, no del
  front. La guía de pruebas indica el orden de carga.
- **Editar internado:** `ipress` arranca vacío (el read da el nombre, no el id); PATCH lo omite si no
  se cambia. El tutor se cambia con la acción `cambiar-tutor`. Documentado.
- **`campo_clinico` / `participante_convenio`** como número (id) — misma deuda polimórfica de
  Convenios (sin endpoint dependiente/ContentTypes). Documentado.
- **Enums:** `sexo` (M/F) y rotación `resultado` (APROBADO/OBSERVADO/RECHAZADO) con choices; el resto
  texto libre (el backend valida).

### Comprobaciones técnicas
- `npm run lint` → 0 errores, 1 warning (DataTable/React Compiler, ajeno).
- `npm run build` → 15 rutas OK (6 nuevas de internados).
- Smoke API: 8 listas paginadas; roundtrip `tutors` OK.

---

## Validación — Actualización de contrato (2026-07-17)

### ✅ APROBADO (sin errores altos/medios). Delta D1–D12 completo; el módulo sigue cerrado.

Revisado contra `spec/internados.md` §«Actualización de contrato (2026-07-17)», `docs/api-internados.md`
(sincronizado) y `lib/api/schema.d.ts` (regenerado).

### Cobertura del delta
| Tarea | Estado | Evidencia |
|-------|--------|-----------|
| D1 hooks base `interns` | ✅ | `lib/internados/hooks.ts:12` (`createResourceHooks(..., "interns")`); 0 referencias a `"internships"` en código |
| D2 detalle `/interns` | ✅ | `app/(app)/internados/[id]/page.tsx:34` (`useResourceSubList("interns", ...)`), `:71` (`endpoint="interns"`), `:56`/`:96` (`it.estudiante`, label «Estudiante») |
| D3 RotationsPanel | ✅ | `components/internados/rotations-panel.tsx:12-17` — prop `internId`, sub-list base `"interns"` + `"rotaciones"`; uso actualizado en el detalle (`internId={it.id}`) |
| D4 comentario flow-actions | ✅ | `lib/internados/flow-actions.ts:7` (`interns/{id}/{key}/`); campos de `cambiar-estado`/`cambiar-tutor`/`rotaciones` intactos |
| D5 config `students` | ✅ | `lib/internados/persons.ts:14-19` (clave/`endpoint: "students"`, `title: "Estudiantes"`, `singular: "estudiante"`); `PERSON_MENU` con slug `students` (`:131-134`) |
| D6 campos nuevos de estudiante | ✅ | `persons.ts:67-90`: `nota_promedio_ponderado` (number, opcional), `contacto_emergencia_nombre`/`_telefono` (text), `_parentesco` (select `relationship-types`); ninguno `required` — coherente con `Student` del schema (opcionales; `relationship-types` existe en `schema.d.ts:1463`) |
| D7 índice de personas | ✅ | `app/(app)/internados/personas/page.tsx:18` («Estudiantes y tutores.») |
| D8 campo `estudiante` en alta | ✅ | `lib/internados/internship-fields.ts:13-19` (`name: "estudiante"`, label «Estudiante», `optionsEndpoint: "students"`); `INTERNSHIP_EDIT_FIELDS` sin cambios |
| D9 lista de internados | ✅ | `app/(app)/internados/page.tsx:33` (`accessorKey: "estudiante"`, header «Estudiante»), `:78` («Buscar por estudiante…»); filtros `convenio`/`estado_actual` intactos |
| D10 dashboard `interns` | ✅ | `lib/dashboard/hooks.ts:161` (comentario), `:182`, `:201`, `:342-343` (`rawQueryKey("interns", ...)` — `useAggregated` deriva la queryKey del endpoint en `:65`); 0 `"internships"` en `lib/dashboard/` |
| D11 terminología UI | ✅ | `components/landing/landing.tsx:214,220,240,269` usan «estudiante(s)»; grep de «interno» en `app/`+`components/` solo devuelve el campo proceso de actividades y «contenedor interno» (comentario, permitido) |
| D12 verificación | ✅ | `npx tsc --noEmit` → 0 errores; `npm run lint` → 0 errores, 1 warning preexistente (`data-table.tsx`, react-hooks/incompatible-library) |

### Conformidad de contrato
- Schema regenerado coherente: `InternshipRead.estudiante` (string legible), `InternshipWrite.estudiante`
  (id), `Student` con los 4 campos nuevos, catálogo `relationship-types`; **cero** ocurrencias del
  campo/filtro viejo `internado` en `schema.d.ts` ni en el código.
- Las menciones restantes a `internships`/`interns`-persona están solo en specs/validaciones
  históricas y `docs/dashboard-graficos.md` (documentación, no contrato; no bloquea).

### Nota
- El smoke manual contra el backend en ejecución (lista → detalle → historial → rotaciones → alta →
  CRUD estudiante) queda reportado por Implement; este validador verificó contrato, código estático,
  tsc y lint (no ejecuta `npm run dev`).
