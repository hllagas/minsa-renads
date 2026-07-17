# Spec — Módulo `internados` (Registrar Internados)

Módulo 3 del MVP (`docs/mvp.md`). CRUD + flujo de internos, tutores, internados y rotaciones.
Contrato del backend: **`docs/api-internados.md`**. Reutiliza toda la infraestructura del módulo
Convenios (CRUD genérico, `EntityCombobox`, `ResourceForm`, `SimpleObjectTable`, `useFlowAction`,
patrón de detalle con pestañas + acciones gateadas).

> **Estado:** ✅ **MÓDULO CERRADO.** Implementado en un pase, validado sin errores. Ver
> `spec/internados.validacion.md` y `spec/internados.guia_pruebas.md`.
> ⚠️ **Pendiente:** aplicar la sección «Actualización de contrato (2026-07-17)» (abajo).

## Resumen / pantallas
- **Internados** `/internados`: lista (DataTable + filtros + paginación), detalle con pestañas
  (Datos, Rotaciones, Historial) + acciones de flujo, alta/edición.
- **Rotaciones**: gestionadas desde el detalle del internado (lista + crear) y con acciones propias
  (autorizar, iniciar, cambiar-estado, historial).
- **Maestros del módulo**: `interns` y `tutors` (CRUD); catálogos como selects.

## Reglas de negocio relevantes (UX; el backend es autoridad)
- Internado solo sobre **Convenio Específico vigente** (`VIGENTE`/`PUBLICADO`/`SUSCRITO`); `tutor` obligatorio.
- Duración ≤ 1 año; rotación entre IPRESS del **mismo ámbito geográfico sanitario**; **máx. 4 rotaciones**.
- Autorizar rotación: solo **autoridad firmante** del Convenio Específico; no inicia sin autorización aprobada.

## Reutilización (ya existe — módulo Convenios)
- CRUD declarativo: `lib/crud/*`, `components/crud/*`, `ResourceCrud`, `ResourceForm`.
- `EntityCombobox` (búsqueda server-side), `lib/api/lookup.ts`, `lib/api/query.ts`.
- Flujo: `useFlowAction` (genérico; sirve para internados/rotaciones cambiando el recurso base),
  `FlowActionDialog`, `SimpleObjectTable`, patrón de detalle con `Tabs`.
- Tipos: regenerar/usar `lib/api/schema.d.ts` (`InternshipRead/Write`, `RotationRead/Write`, `Intern`, `Tutor`, ...).

---

## Bloque 0 — Infra del módulo
- [x] **T0.1** Regenerar tipos (`npm run gen:api`) y exponer alias de internados desde `schema.d.ts`.
- [x] **T0.2** Generalizar `useFlowAction` para aceptar el recurso base (hoy fijo a `conventions`):
  parametrizar a `internships`/`rotations`. Criterio: reutilizable sin duplicar lógica.

## Bloque 1 — Personas (CRUD maestros)
- [x] **T1.1** Config + UI CRUD de **`interns`** (filtros: universidad, carrera, especialidad,
  documento; búsqueda por documento/nombres). FKs vía `EntityCombobox` (universities,
  professional-careers, specialties, identity-document-types). Escritura rol `Universidad`/`Administrador RENADS`.
- [x] **T1.2** Config + UI CRUD de **`tutors`** (filtros: especialidad, ipress, documento). FKs:
  specialties, ipress, identity-document-types.
- [x] **T1.3** Catálogos como selects: `internship-statuses`, `rotation-statuses`, `service-areas`,
  `identity-document-types` (vía `EntityCombobox`, sin CRUD propio).
  - **Criterio:** CRUD de interns/tutors funciona contra el backend con alcance/rol correctos.

## Bloque 2 — Internados (núcleo CRUD + flujo)
- [x] **T2.1 API/hooks** `internships` (read/write tipados) con `createResourceHooks`.
- [x] **T2.2 Lista** `/internados`: `<DataTable>` con columnas (interno, convenio, ipress, tutor,
  estado, fechas), filtros backend (`convenio`, `ipress`, `tutor`, `estado_actual`,
  `ambito_geografico_sanitario`, rangos de fecha), búsqueda por interno, paginación. "Nuevo" gateado a `Universidad`.
- [x] **T2.3 Alta/edición**: form rhf (`ResourceForm`) con campos de escritura (interno, convenio,
  campo_clinico, ipress, tutor, ambito_geografico_sanitario, fechas, observaciones). Edición usa el
  subconjunto editable (`ipress`, `observaciones`, `fecha_inicio`, `fecha_fin`); el tutor se cambia
  con la acción `cambiar-tutor`.
- [x] **T2.4 Detalle** con pestañas **Datos / Rotaciones / Historial** y acciones de flujo:
  `cambiar-estado` (Administrador RENADS), `cambiar-tutor` (Universidad). Rotaciones: GET lista +
  POST crear (Universidad) desde la pestaña.
  - **Criterio:** alta/edición/flujo del internado contra el backend; rotaciones listadas/creadas.

## Bloque 3 — Rotaciones (acciones)
- [x] **T3.1 Hooks** `rotations` (lectura) + acciones vía `useFlowAction` con base `rotations`:
  `autorizar` (Autoridad de convenio), `iniciar` (Universidad), `cambiar-estado` (Administrador RENADS),
  `historial` (GET).
- [x] **T3.2 UI** de rotación: en la pestaña Rotaciones del internado (o vista/diálogo de rotación),
  botones gateados por rol + historial (`SimpleObjectTable`). Crear rotación con
  `ipress_origen`/`ipress_destino`/`servicio_area`/fechas/observaciones.
  - **Criterio:** flujo de rotación (crear→autorizar→iniciar) respeta rol y refresca datos.

## Bloque 4 — Verificación
- [x] **T4.1** `npm run lint` y `npm run build` limpios.
- [x] **T4.2** Validador deja `spec/internados.validacion.md` y, si OK, `spec/internados.guia_pruebas.md`.

---

## Criterios de aceptación del módulo (de `docs/mvp.md`)
- Se registra un internado sobre convenio específico vigente; rotaciones con su flujo de autorización.
- CRUD de internos/tutores con alcance/rol.
- Tablas con filtros/paginación del backend; selects desde catálogos reales.

## Decisiones (resueltas)
1. **Pases:** un solo pase (todo el módulo). ✅
2. **Rotaciones:** embebidas en el detalle del internado (diálogos). ✅
3. **`campo_clinico`:** capturado como número (id) por ahora (igual que solicitante); selector
   dependiente del convenio queda pendiente. ✅

## Fuera de alcance
- Documentos/adjuntos; reportes/exportación; tests automatizados.

## Referencias
- Endpoints/campos/roles: `docs/api-internados.md`; roles/alcance: `docs/backend-overview.md`.
- Patrones y stack: `CLAUDE.md`, `docs/frontend-conventions.md`; reutilización de Convenios (arriba).

---

## Actualización de contrato (2026-07-17)

Mantenimiento del módulo (ya validado) por cambio de contrato del backend. Fuentes de verdad:
`docs/api-internados.md` (ya sincronizado) y `lib/api/schema.d.ts` (ya regenerado — los nombres de
tipos `InternshipRead/Write`, `RotationRead`, `Student` no cambian; cambian **rutas y campos**).

**Resumen del cambio:**
- Rutas: `/internships/` → **`/interns/`** (proceso de internado; mismas acciones `cambiar-estado`,
  `cambiar-tutor`, `historial`, `rotaciones`) y `/interns/` (personas) → **`/students/`**.
- Campos: en `InternshipRead/Write` `interno` → **`estudiante`** (y filtro `estudiante`); en
  `Rotation` el campo/filtro `internado` → **`interno`**.
- `Student` gana campos opcionales: `nota_promedio_ponderado` (decimal string 0–20),
  `contacto_emergencia_nombre`, `contacto_emergencia_telefono`, `contacto_emergencia_parentesco`
  (FK al catálogo nuevo **`relationship-types`**, solo lectura).
- Terminología UI: **«estudiante»** = la persona (antes «interno»); **«interno»** = el registro del
  proceso de internado (antes «internado»).

### A. Endpoints y hooks (renombre `internships` → `interns`)

- [x] **D1** `lib/internados/hooks.ts`: cambiar la base de `internshipHooks` de `"internships"` a
  `"interns"`. `rotationHooks` no cambia.
  - **Criterio:** la lista/detalle/alta/edición de `/internados` pegan a `/api/v1/interns/` (verificable
    en la pestaña Network); sin referencias restantes a `"internships"` en `lib/internados/`.
- [x] **D2** `app/(app)/internados/[id]/page.tsx`: cambiar `useResourceSubList("internships", id, "historial")`
  y `FlowActionDialog endpoint="internships"` a `"interns"`. Además corregir los errores TS ya
  detectados: `it.interno` → `it.estudiante` (líneas 56 y 96) y la etiqueta del `<Dato>` «Interno» →
  «Estudiante».
  - **Criterio:** detalle, historial y acciones de flujo (`cambiar-estado`, `cambiar-tutor`,
    `rotaciones`) funcionan contra `/interns/{id}/...`; el título muestra el nombre del estudiante;
    sin errores TS en el archivo.
- [x] **D3** `components/internados/rotations-panel.tsx`: cambiar la base del sub-list de
  `"internships"` a `"interns"` (GET `/interns/{id}/rotaciones/`). Renombrar la prop `internshipId` →
  `internId` (y su uso en el detalle) para alinear con la terminología nueva.
  - **Criterio:** la pestaña Rotaciones lista y refresca contra `/interns/{id}/rotaciones/`.
- [x] **D4** `lib/internados/flow-actions.ts`: actualizar el comentario doc
  (`internships/{id}/{key}/` → `interns/{id}/{key}/`). Las acciones y sus campos no cambian
  (`cambiar-estado`, `cambiar-tutor`, `rotaciones` — ver `docs/api-internados.md`).
  - **Criterio:** sin menciones a `internships` en el archivo; campos intactos.

### B. Personas — `interns` → `students` (+ campos nuevos)

- [x] **D5** `lib/internados/persons.ts`: renombrar la config de personas `interns` → `students`
  (clave del record, `endpoint: "students"`, `title: "Estudiantes"`, `singular: "estudiante"`,
  `description` acorde) y actualizar `PERSON_MENU` (`slug: "students"`, `title: "Estudiantes"`).
  La ruta resultante es `/internados/personas/students` (la página `[entidad]` la resuelve sola).
  - **Criterio:** el CRUD de personas opera contra `/api/v1/students/`; la ruta vieja
    `/internados/personas/interns` cae en el fallback «Recurso no encontrado» (aceptable; no hay
    enlaces internos a ella tras D5).
- [x] **D6** `lib/internados/persons.ts` — agregar al form de `students` los campos nuevos del
  contrato (`docs/api-internados.md` §Personas):
  - `nota_promedio_ponderado` — número decimal 0–20, opcional (el API lo serializa como string).
  - `contacto_emergencia_nombre` — texto, opcional.
  - `contacto_emergencia_telefono` — texto, opcional.
  - `contacto_emergencia_parentesco` — select opcional con `optionsEndpoint: "relationship-types"`
    (catálogo nuevo, solo lectura).
  - **Criterio:** alta/edición de estudiante persiste los 4 campos; el select de parentesco carga
    del catálogo real; los campos son opcionales (el form no los exige).
- [x] **D7** `app/(app)/internados/personas/page.tsx`: actualizar textos del índice
  («Internos y tutores.» → «Estudiantes y tutores.»).
  - **Criterio:** ninguna pantalla de personas usa ya la palabra «Internos» para referirse a la persona.

### C. Campos y pantallas del recurso `interns` (proceso)

- [x] **D8** `lib/internados/internship-fields.ts`: en `INTERNSHIP_FIELDS`, renombrar el campo
  `interno` → `estudiante` (clave del payload de `InternshipWrite`), con `label: "Estudiante"` y
  `optionsEndpoint: "students"`. `INTERNSHIP_EDIT_FIELDS` no cambia (`ipress`, fechas,
  `observaciones`).
  - **Criterio:** el alta de internado envía `estudiante` (id) y el POST a `/interns/` es aceptado;
    el select busca en `/students/`.
- [x] **D9** `app/(app)/internados/page.tsx`: columna `accessorKey: "interno"` → `"estudiante"` con
  header «Estudiante»; placeholder de búsqueda «Buscar por interno…» → «Buscar por estudiante…»
  (el search del backend es por documento/nombres del estudiante). Los filtros existentes
  (`convenio`, `estado_actual`) no cambian de nombre.
  - **Criterio:** la columna muestra el nombre del estudiante (campo read `estudiante`); sin
    columnas vacías.

### D. Dashboard (consumidor de `internships`)

- [x] **D10** `lib/dashboard/hooks.ts`: cambiar el endpoint `"internships"` → `"interns"` en los 3
  puntos que lo usan (`useInternadosPorEstado`, `useInternadosEnTiempo` y la query de KPIs en
  `useKpis`), incluidas sus `queryKey` (`rawQueryKey("interns", ...)`), y actualizar el comentario
  de sección («endpoint `interns`»). Los campos usados (`estado_codigo`, `fecha_inicio`) no
  cambiaron; `lib/dashboard/types.ts` y `use-dashboard-filters.ts` no requieren cambios de contrato
  (solo etiquetas de presentación, cubiertas en D11).
  - **Criterio:** las gráficas y KPIs de internados cargan contra `/api/v1/interns/`; sin referencias
    a `"internships"` en `lib/dashboard/`.

### E. Terminología UI (barrido de etiquetas)

- [x] **D11** Barrido de etiquetas según la terminología nueva (persona = «Estudiante»; proceso =
  «interno/internado»). **Decisión recomendada:** mantener «Internados» como nombre del módulo/
  proceso en navegación y títulos (natural en español y coincide con `docs/mvp.md`), y renombrar a
  «Estudiante(s)» toda mención a la persona. Alcance mínimo:
  - `components/layout/app-shell.tsx`: ítem «Internados» se mantiene (ruta `/internados` sin cambio).
  - `components/landing/landing.tsx`: «Internos, tutores, internados y rotaciones…» →
    «Estudiantes, tutores, internados y rotaciones…»; «registra al interno y su tutor» →
    «registra al estudiante y su tutor»; «actividades de los internos» → «actividades de los
    estudiantes» (líneas ~214, ~240, ~220/~269).
  - `app/(app)/internados/[id]/page.tsx` y `app/(app)/internados/page.tsx`: cubiertos por D2/D9.
  - **Criterio:** `grep -i "interno"` en `app/` y `components/` no devuelve usos que se refieran a
    la persona (solo al proceso o a texto no relacionado, p. ej. «contenedor interno»).

### F. Verificación

- [x] **D12** `npx tsc --noEmit` y `npm run lint` limpios; smoke manual: lista → detalle →
  historial → rotaciones → alta de internado → CRUD de estudiante con campos nuevos.
  - **Criterio:** cero errores de TypeScript y ESLint; los flujos del smoke responden 2xx.

> **Aprobación humana requerida:** esta lista de tareas delta debe ser aprobada antes de pasar al
> agente Implement.
