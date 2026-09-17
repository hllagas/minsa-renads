# Spec — Módulo Campos de Formación (`/campos-clinicos`)

**Estado:** gaps pendientes de cerrar. Las tres vistas principales ya están implementadas
(`registros/`, `asignaciones/`, `determinacion-view.tsx`, `asignacion-view.tsx`,
`lib/convenios/clinical-fields.ts`). Este spec cubre únicamente los 3 gaps identificados.

**Aprobación requerida:** este spec debe ser aprobado por un humano antes de pasar a Implement.

---

## 1. Resumen del módulo y pantallas

| Ruta | Estado |
|------|--------|
| `/campos-clinicos` | Implementado — solo tarjetas de nav. **GAP T2:** agregar KPI cards con totales estadísticos. |
| `/campos-clinicos/registros` | Implementado y cerrado. |
| `/campos-clinicos/asignaciones` | Implementado y cerrado. |
| `app/(app)/campos-clinicos/layout.tsx` | **No existe.** GAP T1: crear con `ModuleGate`. |
| `lib/internados/internship-fields.ts` — campo `campo_clinico` | Implementado como `type: "number"`. **GAP T3:** convertir a `type: "select"` filtrado por universidad. |

---

## 2. Tareas

### T1 — Layout con ModuleGate

- [x] **T1** Crear `app/(app)/campos-clinicos/layout.tsx` con bloqueo `ModuleGate` para el módulo de campos clínicos.

**Qué crear:** un archivo de layout Next.js App Router que envuelva `{children}` en `<ModuleGate>`.

**Archivo a crear:** `app/(app)/campos-clinicos/layout.tsx`

**Patrón a seguir:** idéntico a `app/(app)/convenios/layout.tsx` (1 content-type) e
`app/(app)/internados/layout.tsx` (2 content-types). El layout debe ser `"use client"` (porque
`ModuleGate` usa `useAuthStore`).

**Content types a usar:**
```
[
  { appLabel: "convenios", model: "clinicalfieldregistration" },
  { appLabel: "convenios", model: "clinicalfieldallocation" }
]
```
Ambos modelos viven en `apps/convenios` del backend. Se incluyen los dos porque el gate debe
activarse si cualquiera de los dos está fuera de su ventana. La semántica es: si
`modulos_bloqueados` de `/auth/me/` incluye al menos uno de ellos, se muestra el aviso de módulo
bloqueado. `Administrador RENADS` y superusuario quedan exentos (lógica en `moduloBloqueado` de
`lib/auth/store.ts`).

**Criterio de aceptación:**
- El archivo existe en `app/(app)/campos-clinicos/layout.tsx`.
- Exporta `default function CamposClinicosLayout`.
- Importa `ModuleGate` de `@/components/auth/module-gate`.
- Pasa exactamente los dos `contentTypes` listados arriba.
- Envuelve `{children}` con el gate.
- No rompe las rutas hijas (`/registros`, `/asignaciones`).

---

### T2 — Índice `/campos-clinicos` con KPI estadístico

- [x] **T2** Refactorizar `app/(app)/campos-clinicos/page.tsx` para añadir: selector de nivel académico, KPI cards de determinaciones y KPI cards de asignaciones.

**Archivo a modificar:** `app/(app)/campos-clinicos/page.tsx`

**Descripción completa:**

La página actualmente solo renderiza las dos tarjetas de navegación. Debe añadir encima:

#### T2-A — Selector de nivel académico

- Componente `EntityCombobox` (o `select` nativo con shadcn `Select`) que lista todos los niveles
  de `GET /academic-levels/` (catálogo solo lectura, filtro `activo`).
- Un nivel a la vez; estado local `nivelId: number | null` con default al id de «Pregrado»
  (resuelto en runtime: buscar en los resultados el que contiene «pregrado» en `nombre` o `codigo`,
  igual que el patrón usado en `app/(app)/internados/personas/[entidad]/page.tsx` para `pregradoId`).
- Al cambiar el nivel, se invalidan las queries de KPI de determinaciones (no las de asignaciones,
  que son globales).
- Query key: `["academic-levels", "all"]`, `staleTime: 30 min`.

#### T2-B — KPI cards de determinaciones

Endpoint: `GET /clinical-field-registrations/?carrera_profesional__nivel_academico=<nivelId>&page_size=500`

Campos relevantes en `ClinicalFieldRegistration` (lectura, `docs/api-convenios.md §campos-clínicos`):
- `campos_clinicos_registrados` — entero
- `campos_clinicos_asignados` — entero (solo lectura, acumulador)
- `disponibilidad` — calculado: `registrados − asignados`

Mostrar 3 KPI cards:

| Card | Cálculo | Icono sugerido |
|------|---------|----------------|
| Total determinados | `Σ campos_clinicos_registrados` de todos los resultados | `Layers` |
| Total asignados | `Σ campos_clinicos_asignados` | `CheckSquare` |
| Total disponibles | `Σ disponibilidad` | `ArrowRightSquare` |

Si `nivelId` es `null` (aún no resuelto), mostrar `Skeleton` en las 3 cards.

Query key: `["clinical-field-registrations", "kpi", nivelId]`, `staleTime: 2 min`.

> Nota: `page_size=500` es suficiente para el total de determinaciones del sistema en el MVP.
> Si en el futuro crece, se paginará; por ahora no es necesario.

#### T2-C — KPI cards de asignaciones

Endpoint: `GET /clinical-field-allocations/?page_size=500`

Campos relevantes en `ClinicalFieldAllocation` (lectura, `docs/api-convenios.md §asignaciones`):
- `campos_clinicos_autorizados` — entero
- Cada resultado es una asignación activa (el backend no expone campo `activo` en este endpoint;
  el count de filas es el total de asignaciones registradas).

Mostrar 2 KPI cards:

| Card | Cálculo |
|------|---------|
| Total asignaciones | `count` de la respuesta paginada (campo `count` del envelope DRF) |
| Total cupos autorizados | `Σ campos_clinicos_autorizados` |

Query key: `["clinical-field-allocations", "kpi"]`, `staleTime: 2 min`.

#### T2-D — Layout general de la página

Orden visual (top → bottom):
1. `PageHeader` existente.
2. Selector de nivel académico (label + combo).
3. Grid de 3 KPI cards de determinaciones (título de sección: «Determinación de campos»).
4. Grid de 2 KPI cards de asignaciones (título de sección: «Asignación de campos»).
5. Grid de 2 tarjetas de navegación existentes (sin cambios).

UI: usar componentes shadcn `Card`, `CardHeader`, `CardTitle`, `CardContent`. Skeleton de
shadcn (`Skeleton`) mientras las queries cargan. El skeleton debe ocupar el mismo espacio que
las cards reales (no collapsing layout).

**Criterio de aceptación:**
- La página muestra un selector funcional de nivel académico con datos reales de `academic-levels`.
- Al cambiar el nivel, los 3 KPI de determinaciones se recalculan.
- Los 2 KPI de asignaciones son independientes del nivel y no se recargan al cambiarlo.
- Los valores reflejan datos reales del backend (no hardcodeados).
- Mientras las queries cargan, se muestran Skeletons (no pantalla en blanco).
- Las dos tarjetas de nav (`/registros`, `/asignaciones`) siguen funcionando debajo de los KPI.
- No se rompen las rutas hijas.

---

### T3 — Selector `campo_clinico` en el form de internado

- [x] **T3** Modificar `lib/internados/internship-fields.ts`: convertir el campo `campo_clinico` de `type: "number"` a `type: "select"` filtrado por `universidad` del alcance.

**Archivo a modificar:** `lib/internados/internship-fields.ts`

**Contexto actual:**

```ts
// línea 32 — estado actual
{ name: "campo_clinico", label: "Campo clínico (id)", type: "number", required: true },
```

El campo `campo_clinico` es FK a `ClinicalFieldAllocation` (endpoint `clinical-field-allocations`).
Su PK es un entero (`id`). El backend usa `campo_clinico` (id) como campo write en `InternshipWrite`.

**Cambio requerido:**

1. Convertir `INTERNSHIP_FIELDS` de array literal a función `buildInternshipFields(universidadId: number | null): FieldConfig[]`, siguiendo el patrón de `buildStudentsConfig` en `lib/internados/persons.ts`.

2. El campo `campo_clinico` pasa a:

```ts
{
  name: "campo_clinico",
  label: "Campo de formación",
  type: "select",
  required: true,
  optionsEndpoint: "clinical-field-allocations",
  optionsParams: universidadId != null ? { universidad: String(universidadId) } : undefined,
  optionsToLabel: (r) => {
    const sede = r.ipress_detalle && typeof r.ipress_detalle === "object"
      ? String((r.ipress_detalle as Record<string, unknown>).nombre ?? "—")
      : "—";
    const carrera = r.carrera_profesional_detalle && typeof r.carrera_profesional_detalle === "object"
      ? String((r.carrera_profesional_detalle as Record<string, unknown>).nombre ?? "—")
      : "—";
    const cupos = r.campos_clinicos_autorizados ?? "—";
    return `${sede} — ${carrera} (${cupos} cupos)`;
  },
}
```

Los campos `ipress_detalle`, `carrera_profesional_detalle` y `campos_clinicos_autorizados` están
confirmados en la respuesta de lectura de `clinical-field-allocations` (ver `clinical-fields.ts`
columnas que ya los usan).

3. Renombrar la exportación de `INTERNSHIP_FIELDS` a `buildInternshipFields` (función) y actualizar
`INTERNSHIP_EDIT_FIELDS` si usa la misma función (actualmente no usa `campo_clinico`, así que
`INTERNSHIP_EDIT_FIELDS` permanece como array literal sin cambio).

**Actualización del consumidor:**

`app/(app)/internados/internos/page.tsx` actualmente importa `INTERNSHIP_FIELDS` como constante.
Debe actualizarse para llamar `buildInternshipFields(universidad)` donde `universidad` viene de
`useUniversityGate` (ya disponible en esa página como `const { universidad, gateUI } = useUniversityGate(...)`).

El array derivado `INTERNSHIP_DIALOG_FIELDS` (línea 41 de la página) debe derivarse también de la
llamada a `buildInternshipFields(universidad)`, no de la constante importada.

Si `universidad` es `null` (aún no elegida), `buildInternshipFields(null)` omite `optionsParams`
en el campo `campo_clinico`, quedando sin filtro de universidad — el backend aún restringe por
alcance. El dialogo de alta ya requiere que `universidad != null` (el botón «Nuevo interno» solo
aparece cuando `convenio != null`, lo que implica que `universidad != null`).

**Criterio de aceptación:**
- `lib/internados/internship-fields.ts` exporta `buildInternshipFields(universidadId: number | null): FieldConfig[]` en lugar de la constante `INTERNSHIP_FIELDS`.
- El campo `campo_clinico` es de `type: "select"` con `optionsEndpoint: "clinical-field-allocations"`.
- Cuando `universidadId` no es `null`, el select filtra por `?universidad=<universidadId>`.
- La etiqueta de cada opción incluye: sede docente (`ipress_detalle.nombre`), carrera (`carrera_profesional_detalle.nombre`) y cupos autorizados (`campos_clinicos_autorizados`).
- `app/(app)/internados/internos/page.tsx` llama `buildInternshipFields(universidad)` con el `universidad` del gate.
- `INTERNSHIP_EDIT_FIELDS` permanece sin cambios (array literal).
- El formulario de alta de internado muestra el select funcional (no el input numérico).
- TypeScript compila sin errores (`npm run build` o `tsc --noEmit`).

---

## 3. Referencias al contrato del backend

| Recurso | Endpoint | Campos usados en este spec |
|---------|----------|---------------------------|
| Niveles académicos | `GET /academic-levels/` | `id`, `nombre`, `codigo`, `activo` |
| Determinaciones | `GET /clinical-field-registrations/` | `campos_clinicos_registrados`, `campos_clinicos_asignados`, `disponibilidad` |
| Asignaciones | `GET /clinical-field-allocations/` | `count` (envelope), `campos_clinicos_autorizados`, `ipress_detalle.nombre`, `carrera_profesional_detalle.nombre` |
| Internado (write) | `POST /internships/` | `campo_clinico` (FK → `ClinicalFieldAllocation.id`) |

Filtro confirmado para T3: `clinical-field-allocations?universidad=<id>` — el filtro `universidad`
está declarado en `clinicalFieldAllocationsConfig.filters` en `lib/convenios/clinical-fields.ts`
(línea 162), lo que confirma que el backend lo soporta.

Filtro confirmado para T2-B: `clinical-field-registrations?carrera_profesional__nivel_academico=<id>`
— el backend `ClinicalFieldRegistrationFilter` soporta este lookup ORM (doble guion bajo); confirmar
con el backend si no está declarado explícitamente en el filter (si falta, registrar como
REQ-BACK pendiente y usar `carrera_profesional` como fallback).

---

## 4. Estado del módulo tras cerrar los 3 gaps

Una vez validadas las 3 tareas, el módulo `/campos-clinicos` puede considerarse **CERRADO** (v1).
