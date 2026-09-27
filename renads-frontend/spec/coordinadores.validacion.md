# Validación — Feature: Coordinadores de tutores

**Módulo:** Internados (`/internados`)
**Fecha de validación:** 2026-09-26
**Resultado:** CERRADO — sin errores altos ni medios. Todas las tareas T1–T8 cumplen sus criterios de aceptación.

---

## Resultado por tarea

| Tarea | CA | Estado | Observaciones |
|-------|----|--------|---------------|
| T1 | CA-1 | OK | Los tres interfaces (`CoordinatorRead`, `CoordinatorSedeRead`, `CoordinatorTutorRead`) exportados en `lib/internados/types.ts`. Claves en español. Coinciden exactamente con el spec. |
| T2 | CA-2a | OK | Seis funciones API en `lib/internados/coordinator.ts`. Usan `api` de `lib/api/client`. URLs exactas del contrato (`/coordinators/{id}/sedes/`, `/coordinators/{id}/sedes/{sede_pk}/`, `/coordinators/{id}/sedes/{sede_pk}/tutors/`, etc.). Manejo de respuesta paginada y array directo. |
| T3 | CA-3 | OK | Seis hooks exportados: `useCoordinatorSedes`, `useAddCoordinatorSede`, `useDeleteCoordinatorSede`, `useCoordinatorTutors`, `useAddCoordinatorTutor`, `useDeleteCoordinatorTutor`. QueryKeys jerárquicas consistentes. Invalidaciones correctas en `onSuccess`. |
| T4 | CA-4 | OK | `buildCoordinatorsConfig()` exportada sin parámetros, retorna `ResourceConfig`. Todos los campos referencian endpoints reales del contrato. `editFields` deshabilita `tipo_documento_identidad` y `numero_documento`. `PERSON_MENU` incluye `{ slug: "coordinators", title: "Coordinadores" }`. |
| T5 | CA-5 | OK | `CoordinatorSedesDialog` con props correctas. Sección 1: spinner de carga, mensaje vacío, tabla de sedes con botón «Ver tutores» expandible, botón «Eliminar sede» (`variant="destructive"`). Sub-sección de tutores: lista, «Desasignar» por ítem, formulario de asignación con `EntityCombobox<number>` filtrado por `?universidades=<id>`. Sección 2: selectores universidad + IPRESS filtrado con `?es_sede_docente=true`. Todos los errores con `extractApiError`. Sin `any` suelto. |
| T6 | CA-6 | OK | Rama `if (entidad === "coordinators") return <CoordinatorsView />;` añadida antes del fallback. `CoordinatorsView` usa `useUniversityGate()`, `buildCoordinatorsConfig()`, `initialFilters: { sedes__universidad }`, row action «Sedes» (`variant="outline"`), `CoordinatorSedesDialog` condicional, `EmptyPick` cuando `universidad == null`, `UniversityLogoDisplay` en `PageHeader`. |
| T7 | CA-7 | OK | Entrada `{ label: "Coordinadores", icon: UserCheck, href: "/internados/personas/coordinators" }` bajo el nodo «Internado» en `app-shell.tsx`, después de «Tutores». `UserCheck` importado de `lucide-react`. |
| T8 | CA-8 | OK | Sección §Coordinadores añadida al final de `docs/api-internados.md`. Describe los 8 entradas de la tabla de endpoints (10 métodos totales: GET/GET/POST/PATCH/DELETE/GET/POST/GET/DELETE/GET/POST/DELETE), filtros, search y campos de lectura/escritura para los tres modelos. |

---

## Hallazgos menores (sin bloqueo)

- `coordinator-sedes-dialog.tsx:187`: el `map` sobre `sedes` usa un Fragment `<>` como wrapper de dos `<tr>` dentro de `<tbody>`, sin `key` explícita en el Fragment. La clave `key={sede.id}` está en el `<tr>` interno en lugar del Fragment exterior. Esto genera una advertencia de React (`Each child in a list should have a unique "key" prop`). Es un defecto de lint/runtime menor, no bloquea el build ni el funcionamiento.
  - Corrección sugerida: mover `key={sede.id}` al Fragment (`<React.Fragment key={sede.id}>`) o cambiar a `<React.Fragment>` explícito con la clave.

---

## Conformidad con convenciones

- Stack correcto: peticiones via TanStack Query + `api` de `lib/api/`; sin `fetch` suelto en componentes.
- UI con shadcn (`Dialog`, `Button`, `Label`). La tabla de sedes es HTML nativo (`<table>`) — aceptable para un sub-componente que no es el listado principal (el listado principal sí usa `ResourceCrud`/`DataTable`).
- Server/Client: `coordinator-sedes-dialog.tsx` y `page.tsx` tienen `"use client"`. `coordinator.ts` y `persons.ts` son módulos de librería (sin directiva, correcto).
- Gating por rol: `canWrite` propagado desde `userHasRole` en `CoordinatorsView` al dialog. `writeRoles` declarados en `buildCoordinatorsConfig`. Correcto.
- Claves de API en español (sin traducción). Correcto.

---

**Módulo CERRADO.** El feature Coordinadores de tutores está completamente implementado y cumple todos los criterios de aceptación del spec. El único hallazgo es un defecto menor de `key` en Fragment que no bloquea el cierre.
