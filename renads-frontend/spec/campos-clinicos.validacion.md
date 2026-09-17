# Validación — Módulo Campos de Formación (`/campos-clinicos`)

**Fecha:** 2026-09-16  
**Resultado final:** MÓDULO CERRADO — sin errores altos ni medios. Las 3 tareas cumplen todos sus criterios de aceptación.

---

## T1 — `app/(app)/campos-clinicos/layout.tsx`

| Criterio | Estado | Observación |
|----------|--------|-------------|
| Archivo existe en la ruta correcta | PASS | `app/(app)/campos-clinicos/layout.tsx` presente |
| Exporta `default function CamposClinicosLayout` | PASS | línea 6 |
| Importa `ModuleGate` de `@/components/auth/module-gate` | PASS | línea 4 |
| Pasa exactamente `[{appLabel:"convenios",model:"clinicalfieldregistration"},{appLabel:"convenios",model:"clinicalfieldallocation"}]` | PASS | líneas 9-12 |
| Envuelve `{children}` con el gate | PASS | línea 13 |
| Tiene `"use client"` (requerido por `ModuleGate` que usa `useAuthStore`) | PASS | línea 1 |
| No rompe rutas hijas (`/registros`, `/asignaciones`) | PASS | build exitoso, ambas rutas presentes |

**Veredicto T1: APROBADO**

---

## T2 — `app/(app)/campos-clinicos/page.tsx`

| Criterio | Estado | Observación |
|----------|--------|-------------|
| Selector de nivel académico con datos reales de `academic-levels` | PASS | `useQuery` con `queryKey: ["academic-levels","all"]`, `staleTime: 30min`, mapea resultados al `<Select>` |
| Al cambiar nivel, los 3 KPI de determinaciones incluyen `nivelId` en query key | PASS | `queryKey: ["clinical-field-registrations","kpi",resolvedNivelId]` — `resolvedNivelId` cambia al cambiar el selector |
| Los 2 KPI de asignaciones tienen query key independiente del nivel | PASS | `queryKey: ["clinical-field-allocations","kpi"]` — sin `nivelId` |
| Skeleton mientras carga | PASS | `KpiCard` retorna `<Skeleton>` cuando `loading=true`; `registrosLoading` cubre el caso `resolvedNivelId==null` |
| Tarjetas de nav existentes siguen presentes debajo | PASS | `NAV_CARDS` renderizadas al final de la página, sin cambios |
| Sin datos hardcodeados en KPI | PASS | todos los valores se calculan de `registrosQuery.data` y `asignacionesQuery.data` |
| Total asignaciones usa `count` del envelope DRF | PASS | `kpiAsignaciones.total = data?.count ?? 0` |
| Total cupos autorizados usa `Σ campos_clinicos_autorizados` | PASS | `reduce` sobre `data.results` |
| Layout top→bottom correcto (header → selector → det. KPI × 3 → asig. KPI × 2 → nav cards) | PASS | orden visual confirmado en el JSX |
| Usa `useQuery` de TanStack Query (no fetch/Axios suelto) | PASS | `api.get` solo dentro de `queryFn` de `useQuery`; patrón aceptado en la base de código |
| UI con shadcn: `Card`, `Skeleton`, `Select`, `Label` | PASS | todos importados de `@/components/ui/` |

**Veredicto T2: APROBADO**

---

## T3 — `lib/internados/internship-fields.ts` + consumidores

| Criterio | Estado | Observación |
|----------|--------|-------------|
| Exporta `buildInternshipFields(universidadId: number \| null): FieldConfig[]` (función, no constante) | PASS | línea 15 |
| `campo_clinico` es `type: "select"` | PASS | línea 34 |
| `optionsEndpoint: "clinical-field-allocations"` | PASS | línea 38 |
| Cuando `universidadId != null`, `optionsParams` incluye `{universidad: String(universidadId)}` | PASS | línea 39 |
| `optionsToLabel` compone sede + carrera + cupos | PASS | líneas 40-51, idéntico al spec |
| `INTERNSHIP_EDIT_FIELDS` intacto como array literal (sin `campo_clinico`) | PASS | líneas 90-95 |
| `app/(app)/internados/internos/page.tsx` importa `buildInternshipFields` (no `INTERNSHIP_FIELDS`) | PASS | línea 11 |
| Llama `buildInternshipFields(universidad)` con el `universidad` del gate | PASS | línea 102 — `buildInternshipFields(universidad)` dentro de `useMemo` |
| `app/(app)/internados/nuevo/page.tsx` usa `buildInternshipFields(null)` | PASS | línea 23 — llama `buildInternshipFields(null)` |
| TypeScript compila sin errores | PASS | `npx tsc --noEmit` sin salida; `npm run build` exitoso |

**Veredicto T3: APROBADO**

---

## Build / Lint

- `npx tsc --noEmit`: sin errores.
- `npm run build`: compilación exitosa; todas las rutas del módulo presentes (`/campos-clinicos`, `/campos-clinicos/asignaciones`, `/campos-clinicos/registros`, `/internados/internos`, `/internados/nuevo`).

---

## Confirmación de cierre

El módulo **Campos de Formación** (`/campos-clinicos`) queda **CERRADO (v1)**. Los 3 gaps del spec (T1, T2, T3) están implementados y verificados. No se detectaron errores altos ni medios.
