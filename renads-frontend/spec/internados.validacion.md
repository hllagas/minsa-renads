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
