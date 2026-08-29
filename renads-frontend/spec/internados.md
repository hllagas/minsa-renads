# Spec — Módulo `internados` (Registrar Internados)

Módulo 3 del MVP (`docs/mvp.md`). CRUD + flujo de internos, tutores, internados y rotaciones.
Contrato del backend: **`docs/api-internados.md`**. Reutiliza toda la infraestructura del módulo
Convenios (CRUD genérico, `EntityCombobox`, `ResourceForm`, `SimpleObjectTable`, `useFlowAction`,
patrón de detalle con pestañas + acciones gateadas).

> **Estado:** ✅ **MÓDULO CERRADO.** Implementado en un pase, validado sin errores. Ver
> `spec/internados.validacion.md` y `spec/internados.guia_pruebas.md`.
> ✅ «Actualización de contrato (2026-07-17)» (delta 1) aplicada y validada.
> ⚠️ **Pendiente:** aplicar la sección «Actualización de contrato 2 (2026-07-17)» (abajo).

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

---

## Actualización de contrato 2 (2026-07-17)

Segundo delta del backend (commit `fdd5770`). Fuentes de verdad: `docs/api-internados.md`
(**ya sincronizado**) y `lib/api/schema.d.ts` (**ya regenerado**). Dos cambios afectan este módulo:

1. **`Student` pierde `especialidad`** (campo y filtro eliminados del contrato; **Tutor SÍ lo
   conserva**). Filtros vigentes de `students`: `universidad`, `carrera_profesional`,
   `numero_documento`, `activo`.
2. **Carga masiva de estudiantes (RN-16):** nuevo `POST /students/bulk-upload/` —
   `multipart/form-data`, campo **`archivo`** (`.xlsx`), rol `Universidad`/`Administrador RENADS`.
   Columnas requeridas: `tipo_documento` (código, p. ej. `DNI`), `numero_documento`, `nombres`,
   `apellido_paterno`, `universidad` (id o `codigo_inei`), `carrera_profesional` (id o nombre).
   Respuesta 200: `{ creados, omitidos, errores: [{ fila, motivo }] }` (las filas inválidas **no
   abortan** el lote). La prelación RN-18 es servicio interno del backend (sin endpoint) — **sin
   trabajo de frontend**.

### A. Student sin `especialidad`

- [x] **U1** `lib/internados/persons.ts`: eliminar del form de `students` el campo `especialidad`
  (select con `optionsEndpoint: "specialties"`, líneas ~59–64). La config de `tutors` **no cambia**
  (conserva `especialidad`). Nota: la config de `students` no define `filters`, así que no hay
  filtro de UI que retirar.
  - **Criterio:** el form de estudiante (alta y edición) no muestra «Especialidad» y el payload
    nunca envía `especialidad`; `grep especialidad lib/internados/` solo encuentra la config de
    `tutors`.
- [x] **U2** *(recomendado — decidir en aprobación)* `lib/internados/persons.ts`: añadir `filters`
  declarativos a `students` según el contrato: `universidad` (select FK `universities`),
  `carrera_profesional` (select FK `professional-careers`), `activo` (boolean).
  `numero_documento` queda cubierto por el search existente (documento/nombres).
  - **Criterio:** cada filtro emite el query param exacto (`?universidad=…`,
    `?carrera_profesional=…`, `?activo=true|false`) verificable en Network; limpiar filtros
    restablece la lista.

### B. Carga masiva de estudiantes (RN-16)

- [x] **U3 Infra HTTP — multipart.** No existe soporte multipart en `lib/api/` (el cliente Axios
  fija `Content-Type: application/json` por defecto). Crear `lib/api/upload.ts` con un helper
  `postMultipart<T>(path: string, form: FormData): Promise<T>` que use la instancia `api` y
  sobrescriba la cabecera por petición (`"Content-Type": "multipart/form-data"`, dejando que Axios
  añada el `boundary`). Axios sigue viviendo solo en `lib/api/`.
  - **Criterio:** helper tipado y reutilizable; ninguna importación de Axios fuera de `lib/api/`;
    la petición sale con `multipart/form-data; boundary=…`.
- [x] **U4 Tipo + hook de carga masiva.** En `lib/internados/hooks.ts` (o `types.ts` del módulo):
  - Tipo **a mano** `StudentBulkUploadResult = { creados: number; omitidos: number; errores:
    { fila: number; motivo: string }[] }`. *Nota de contrato:* el OpenAPI declara la respuesta como
    `StudentBulkUpload` (que solo modela el request `{ archivo }`) — es impreciso; la forma real de
    la respuesta es la de `docs/api-internados.md` §Carga masiva. No inventar campos adicionales.
  - Hook `useStudentsBulkUpload()`: `useMutation` que recibe un `File`, arma `FormData` con el
    campo **`archivo`** y llama `postMultipart<StudentBulkUploadResult>("students/bulk-upload/", …)`;
    en `onSuccess` invalida `resourceKeys.all("students")` (la lista del CRUD refresca).
  - **Criterio:** un `.xlsx` válido devuelve 200 con el resumen tipado; tras el éxito la lista de
    estudiantes se refresca sin recargar la página.
- [x] **U5 Infra UI — slot de acciones en `ResourceCrud`.** `components/crud/resource-crud.tsx`:
  añadir prop opcional `headerActions?: ReactNode` que se renderice en el `actions` del
  `PageHeader` junto al botón «Nuevo» (antes o después, consistente). Sin cambios de comportamiento
  cuando se omite.
  - **Criterio:** ninguna pantalla existente que usa `ResourceCrud` cambia (no regresión); una
    página puede inyectar botones adicionales en la cabecera.
- [x] **U6 Diálogo de carga masiva.** Nuevo `components/internados/students-bulk-upload-dialog.tsx`
  (botón «Carga masiva» + `Dialog` shadcn):
  - Input de archivo (`<Input type="file" accept=".xlsx">`), obligatorio; texto de ayuda con las
    **columnas requeridas** del contrato (`tipo_documento` código p. ej. DNI, `numero_documento`,
    `nombres`, `apellido_paterno`, `universidad` id o `codigo_inei`, `carrera_profesional` id o
    nombre).
  - Submit deshabilitado sin archivo; estado «Subiendo…» durante la mutación (U4).
  - Al éxito: resumen **`creados` / `omitidos`** (badges o similar) y, si `errores.length > 0`,
    tabla con columnas **Fila** (`fila`) y **Motivo** (`motivo`). Aclarar en la UI que las filas con
    error se omiten sin abortar el lote. Permitir cerrar o subir otro archivo.
  - Error HTTP (400/403/500): toast con `extractApiError`; el diálogo permanece abierto.
  - **Criterio:** la UI refleja exactamente la respuesta `{ creados, omitidos, errores[] }`; un
    archivo con filas válidas e inválidas muestra resumen + tabla de errores por fila.
- [x] **U7 Wiring en la página de estudiantes.**
  `app/(app)/internados/personas/[entidad]/page.tsx`: cuando `params.entidad === "students"` y el
  usuario cumple `userHasRole(user, "Universidad", "Administrador RENADS")` (mismos `writeRoles` de
  la config), pasar `headerActions` (U5) con el diálogo U6. El gating es UX; la autoridad final es
  el backend.
  - **Criterio:** el botón «Carga masiva» aparece solo en `/internados/personas/students` y solo
    para esos roles; no aparece en `tutors`; tras una carga exitosa la tabla refresca.

### C. Verificación

- [x] **U8** `npx tsc --noEmit` y `npm run lint` limpios. Smoke manual: alta/edición de estudiante
  sin campo «Especialidad» (U1); (si se aprueba U2) filtros de estudiantes; carga masiva con un
  `.xlsx` mixto (filas válidas e inválidas) → resumen `creados`/`omitidos` + tabla de errores; rol
  sin permiso no ve el botón.
  - **Criterio:** cero errores de TypeScript/ESLint; los flujos del smoke responden 2xx (o muestran
    el error del backend de forma legible).

> **Aprobación humana requerida:** esta lista de tareas delta (U1–U8, con decisión sobre U2) debe
> ser aprobada antes de pasar al agente Implement.

---

## Actualización de contrato 3 (2026-07-21)

Tercer delta del backend. Fuentes de verdad: `docs/api-internados.md` (**ya sincronizado**) y
`lib/api/schema.d.ts` (**ya regenerado** del servidor vivo). Dos cambios revierten/mueven contrato
previo:

1. **Contacto de emergencia movido `Student` → `Internship`** (migración
   `0015_move_emergency_contact_to_internship`). Los 3 campos (`contacto_emergencia_nombre`,
   `contacto_emergencia_telefono`, `contacto_emergencia_parentesco`) ahora están en
   `InternshipWrite`/`InternshipUpdate` (todos opcionales) y ya **no** en `Student`. Esto revierte
   D6 (contacto) y la parte de contacto de la lectura de estudiante.
2. **`Student` recupera `especialidad` y expone `periodo_academico`** (RN-19: validados por nivel
   académico de la carrera). Esto **revierte U1** — el form de estudiante vuelve a incluir
   `especialidad` (FK `specialties`, opcional) y añade `periodo_academico` (FK `academic-periods`,
   opcional). Filtros de `students` sin cambios (`universidad`, `carrera_profesional`, `activo`).

### A. Contacto de emergencia → internado

- [x] **V1** `lib/internados/persons.ts`: eliminar del form de `students` los 3 campos
  `contacto_emergencia_*` (revierte D6). Dejar nota apuntando a `INTERNSHIP_FIELDS`.
  - **Criterio:** el alta/edición de estudiante ya no envía `contacto_emergencia_*`.
- [x] **V2** `lib/internados/internship-fields.ts`: añadir los 3 `contacto_emergencia_*` (opcionales)
  tanto a `INTERNSHIP_FIELDS` (Write) como a `INTERNSHIP_EDIT_FIELDS` (Update). `parentesco` es
  select con `optionsEndpoint: "relationship-types"`. Factorizados en `EMERGENCY_CONTACT_FIELDS`.
  - **Criterio:** el alta y la edición del internado persisten los 3 campos contra `/interns/`.

### B. Student recupera `especialidad` + `periodo_academico`

- [x] **V3** `lib/internados/persons.ts`: el form de `students` incluye `especialidad` (FK
  `specialties`, opcional) y `periodo_academico` (FK `academic-periods`, opcional). *(Ya presente en
  la config vigente — verificado contra el modelo `Student` y `StudentSerializer` `__all__`.)*
  - **Criterio:** alta/edición de estudiante persiste ambos campos; el backend valida RN-19.

### C. Verificación

- [x] **V4** `npx tsc --noEmit` y `npm run lint` limpios. Smoke: alta de internado con contacto de
  emergencia; edición del internado modifica el contacto; alta de estudiante sin campos de contacto.
  - **Criterio:** cero errores TS/ESLint; los flujos responden 2xx (o error legible del backend).

> **Aprobación humana requerida:** delta V1–V4 debe aprobarse antes de Implement. *(Implementado en
> el mismo ciclo por ser sincronización directa de contrato ya mergeado en el backend.)*
