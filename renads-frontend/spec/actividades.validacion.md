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
