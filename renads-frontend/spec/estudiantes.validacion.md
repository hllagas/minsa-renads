# Validación — Mejoras UI Estudiantes

> Fecha: 2026-09-09 · **IMPLEMENTADO y verificado** (tsc + lint limpios; smoke backend). Decisiones:
> backend hecho por este flujo; nivel virtual; universidad oculta; carga masiva avisa alcance.

## Backend (sin migración)
- `StudentFilter` (`apps/internados/filters.py`): filtro `nivel_academico` → `carrera_profesional__nivel_academico`. `StudentViewSet.filterset_class = StudentFilter`. ✅
- `StudentSerializer`: `carrera_profesional_detalle {id,nombre,nivel_academico}` + `especialidad_detalle {id,nombre}` (SerializerMethodField, read-only). ✅
- `manage.py check` OK; `GET /students/?nivel_academico=1` → **401** (auth), no 500 → el filtro aplica. ✅ · `gen:api` regenerado.

## Frontend
| Req | Resultado |
|-----|-----------|
| 1 — filtro nivel default Pregrado | Filtro `nivel_academico` (academic-levels); la página resuelve el id de «Pregrado» en runtime y lo pasa como `initialFilters`; `key` de ResourceCrud incluye `pregradoId` para aplicarlo tras la carga. ✅ |
| 2/3 — elegir universidad por alcance antes de listar | `StudentsView`: `useUniversityScope` → single (auto), scoped (Select acotado a sus ids), admin (EntityCombobox todas). El listado no se muestra hasta elegir. ✅ |
| 4 — columnas | carrera (`carrera_profesional_detalle`), N° documento, «Apellidos y nombres» (compuesto), nota promedio. ✅ |
| 5 — form | universidad **oculta** vía `fixedValues`; nivel **virtual** `_nivel` (academic-levels) alterna `carrera_profesional` (Pregrado, filtrada por `nivel_academico=pregradoId`) ↔ `especialidad` (otro nivel) vía `showWhen`+`resetsOn`. ✅ |
| 6 — carga masiva | `StudentsBulkUploadDialog` recibe `scoped` y muestra aviso de alcance (backend valida por fila). ✅ |

`students` config ahora es `buildStudentsConfig(pregradoId)`; `tutors` intacto (ruta compartida no rota).

**Verificación:** `npx tsc --noEmit` limpio; `npm run lint` sin errores nuevos (2 pre-existentes en `university-careers/page.tsx`).

## Nota
- En **edición**, `_nivel` (virtual) no viene en el registro → el usuario re-elige el nivel para que aparezca carrera/especialidad (prefilladas del registro). Aceptado por diseño (patrón de cascada). Si se desea prefill automático del nivel en edición, requeriría derivarlo de `carrera_profesional_detalle.nivel_academico` (mejora futura).
