# Spec — Feature: Coordinadores de tutores (`internados`)

**Módulo:** Internados (`/internados`)
**Fecha:** 2026-09-26
**Estado:** PENDIENTE DE APROBACION HUMANA

---

## 1. Resumen del módulo

El **Coordinador** es una persona a cargo de los tutores de una universidad en una o varias
sedes docentes. Se registra bajo `/internados/personas/coordinators` integrándose al patrón
de personas existente (Estudiantes / Tutores). Tiene su propio CRUD y un panel de sedes
(dialog modal) desde el cual se gestionan las IPRESS asignadas al coordinador y los tutores
bajo cada sede.

### Pantallas que cubre

| Pantalla | Descripción |
|---------|-------------|
| `/internados/personas/coordinators` | CRUD de coordinadores (lista, alta, edición, eliminación) con gate de universidad |
| Dialog «Sedes del coordinador» | Abre desde la row action «Sedes»; lista de sedes + agregar/eliminar sede; dentro de cada sede, lista de tutores + asignar/desasignar |

### Endpoints del backend (contrato verificado)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET / POST | `/coordinators/` | Lista / alta |
| GET / PATCH / DELETE | `/coordinators/{id}/` | Detalle / edición / borrado |
| GET / POST | `/coordinators/{id}/sedes/` | Lista sedes / agregar sede |
| GET / DELETE | `/coordinators/{id}/sedes/{sede_pk}/` | Detalle sede / eliminar sede (cascade tutores) |
| GET / POST | `/coordinators/{id}/sedes/{sede_pk}/tutors/` | Lista tutores de la sede / asignar tutor |
| DELETE | `/coordinators/{id}/sedes/{sede_pk}/tutors/{tutor_pk}/` | Desasignar tutor |

### Roles

- Lectura: todos los autenticados del alcance institucional.
- Escritura (POST / PATCH / DELETE): `Universidad` / `Administrador RENADS`.

### Reglas de negocio UX

| Regla | Descripción | Capa de aplicación |
|-------|-------------|-------------------|
| RN-CRD-02 | `tutor` FK nullable y único (un tutor → un coordinador) | Backend (400); el front muestra `extractApiError` |
| RN-CRD-03 | Un coordinador puede tener múltiples sedes sin límite | Sin validación de front |
| RN-CRD-04 | IPRESS debe tener `es_sede_docente=True` | Backend (400); el front filtra el selector con `?es_sede_docente=true` |
| RN-CRD-05 | La IPRESS debe pertenecer a una unidad ejecutora con Convenio Específico vigente para la universidad | Backend (400); el front muestra `extractApiError` |
| RN-CRD-06 | En (universidad, sede) un tutor pertenece a un solo coordinador | Backend (400); el front muestra `extractApiError` |

---

## 2. Lista de tareas

### Capa 1 — Tipos / contratos TypeScript

- [x] **T1 — Añadir tipos `CoordinatorRead`, `CoordinatorSedeRead`, `CoordinatorTutorRead` en `lib/internados/types.ts`**

  Archivo: `lib/internados/types.ts`

  Añadir al final del archivo:

  ```ts
  /** Lectura de un coordinador (endpoint GET /coordinators/ y /coordinators/{id}/). */
  export interface CoordinatorRead {
    id: number;
    tutor: number | null;
    tutor_detalle: { id: number; nombres: string; apellido_paterno: string } | null;
    tipo_documento_identidad: number;
    numero_documento: string;
    nombres: string;
    apellido_paterno: string;
    apellido_materno: string | null;
    correo: string | null;
    telefono: string | null;
    numero_colegiatura: string | null;
    direccion: string | null;
    ubigeo: string | null;       // PK textual (codigo — mig 0048-0049)
    especialidad: number | null;
    profesion: number | null;
    activo: boolean;
  }

  /** Lectura de una sede asignada a un coordinador (endpoint /coordinators/{id}/sedes/). */
  export interface CoordinatorSedeRead {
    id: number;
    coordinador: number;
    universidad: number;
    ipress: string;              // PK textual (codigo_renipress)
    universidad_detalle: { id: number; nombre: string };
    ipress_detalle: { codigo_renipress: string; nombre: string };
  }

  /** Lectura de un tutor asignado a una sede de coordinador (/coordinators/{id}/sedes/{sede_pk}/tutors/). */
  export interface CoordinatorTutorRead {
    id: number;
    coordinador_sede: number;
    tutor: number;
    tutor_detalle: {
      id: number;
      nombres: string;
      apellido_paterno: string;
      numero_documento: string;
    };
  }
  ```

  **Criterio de aceptación (CA-1):** Los tres interfaces exportados coinciden exactamente con
  los campos del contrato de lectura del backend (`renads-api/spec/internados_coordinador.md`
  §Capa 2). TypeScript no emite errores al importarlos. Las claves del API van en español sin
  traducción.

---

### Capa 2 — API layer (funciones Axios + hooks TanStack Query)

- [x] **T2 — Crear `lib/internados/coordinator.ts` con funciones de acceso a la API**

  Archivo: `lib/internados/coordinator.ts` (nuevo)

  Funciones de acceso (patrón `tutor-convenio.ts`):

  - `getCoordinatorSedes(coordinatorId: number): Promise<CoordinatorSedeRead[]>` — GET
    `/coordinators/{id}/sedes/`; maneja array directo o paginado DRF (`results`).
  - `createCoordinatorSede(coordinatorId: number, payload: { universidad: number; ipress: string }): Promise<CoordinatorSedeRead>` — POST `/coordinators/{id}/sedes/`.
  - `deleteCoordinatorSede(coordinatorId: number, sedePk: number): Promise<void>` — DELETE
    `/coordinators/{id}/sedes/{sede_pk}/`; respuesta 204.
  - `getCoordinatorTutors(coordinatorId: number, sedePk: number): Promise<CoordinatorTutorRead[]>` — GET `/coordinators/{id}/sedes/{sede_pk}/tutors/`; maneja array directo o paginado.
  - `createCoordinatorTutor(coordinatorId: number, sedePk: number, payload: { tutor: number }): Promise<CoordinatorTutorRead>` — POST `/coordinators/{id}/sedes/{sede_pk}/tutors/`.
  - `deleteCoordinatorTutor(coordinatorId: number, sedePk: number, tutorPk: number): Promise<void>` — DELETE `/coordinators/{id}/sedes/{sede_pk}/tutors/{tutor_pk}/`; respuesta 204.

  **Criterio de aceptación (CA-2a):** cada función usa `api` de `lib/api/client`; ninguna
  función usa `fetch` directamente. Las URLs coinciden exactamente con los endpoints del
  backend. Los tipos de retorno coinciden con los definidos en T1.

- [x] **T3 — Añadir hooks de TanStack Query en `lib/internados/coordinator.ts`**

  En el mismo archivo, añadir los hooks siguientes (patrón de `tutor-convenio.ts`):

  - `useCoordinatorSedes(coordinatorId: number | null)` — `useQuery` con `queryKey: ["coordinators", coordinatorId, "sedes"]`; `enabled: coordinatorId != null`.
  - `useAddCoordinatorSede(coordinatorId: number)` — `useMutation` que llama `createCoordinatorSede`; en `onSuccess` invalida `["coordinators", coordinatorId, "sedes"]`.
  - `useDeleteCoordinatorSede(coordinatorId: number)` — `useMutation` que llama `deleteCoordinatorSede(coordinatorId, sedePk)`; en `onSuccess` invalida sedes y tutores de la sede eliminada: `["coordinators", coordinatorId, "sedes"]`.
  - `useCoordinatorTutors(coordinatorId: number | null, sedePk: number | null)` — `useQuery` con `queryKey: ["coordinators", coordinatorId, "sedes", sedePk, "tutors"]`; `enabled: coordinatorId != null && sedePk != null`.
  - `useAddCoordinatorTutor(coordinatorId: number, sedePk: number)` — `useMutation`; en `onSuccess` invalida `["coordinators", coordinatorId, "sedes", sedePk, "tutors"]`.
  - `useDeleteCoordinatorTutor(coordinatorId: number, sedePk: number)` — `useMutation`; en `onSuccess` invalida la misma queryKey de tutores.

  **Criterio de aceptación (CA-3):** los seis hooks exportados. Las queryKeys son jerárquicas
  y consistentes. Las mutaciones invalidan exactamente la caché afectada al completarse con
  éxito. El archivo compila sin errores de tipo.

---

### Capa 3 — Config CRUD (`persons.ts`)

- [x] **T4 — Añadir `buildCoordinatorsConfig()` en `lib/internados/persons.ts`**

  Archivo: `lib/internados/persons.ts`

  Añadir la función `buildCoordinatorsConfig()` que devuelve un `ResourceConfig`. Los campos
  del formulario son equivalentes a los del tutor más el campo `tutor` (FK opcional). Orden
  y secciones propuestos:

  **Sección «Identificación»:**
  - `tipo_documento_identidad` — select, `required: true`, `optionsEndpoint: "identity-document-types"`
  - `numero_documento` — text, `required: true`, `docNumberFor: "tipo_documento_identidad"`

  **Sección «Datos personales»:**
  - `nombres` — text, `required: true`, `uppercase: true`
  - `apellido_paterno` — text, `required: true`, `uppercase: true`
  - `apellido_materno` — text, `required: false`, `uppercase: true`

  **Sección «Vínculo con tutor» (opcional):**
  - `tutor` — select, `required: false`, `optionsEndpoint: "tutors"`,
    `optionsToLabel: (r) => apellidosNombres(r)` (helper ya existente en el archivo)

  **Sección «Datos profesionales»:**
  - `profesion` — select, `required: false`, `optionsEndpoint: "professional-careers"`
  - `especialidad` — select, `required: false`, `optionsEndpoint: "specialties"`
  - `numero_colegiatura` — text, `required: false`, `uppercase: false`

  **Sección «Contacto»:**
  - `correo` — email, `required: false`
  - `telefono` — text, `required: false`, `uppercase: false`, `numericOnly: true`
  - `direccion` — text, `required: false`, `uppercase: true`
  - `ubigeo` — select, `required: false`, `optionsEndpoint: "ubigeos"`,
    `optionsValueKey: "codigo"`, `optionsSearchable: true`,
    `optionsToLabel: (r) => [r.codigo, [r.distrito, r.provincia, r.departamento].filter(Boolean).join(", ")].filter(Boolean).join(" — ")`

  **Campo de estado:**
  - `activo` — boolean, `defaultValue: true`

  **Columnas del listado:**
  - `tipo_documento_identidad` — render `tipoDocLabel(r)` (helper existente)
  - `numero_documento` — texto plano
  - `apellidos_nombres` — render `apellidosNombres(r)` (helper existente)
  - `tutor` — render: `r.tutor_detalle ? apellidosNombresInline(r.tutor_detalle) : "—"` (muestra el tutor vinculado)
  - `activo` — render `siNo(r.activo)` (helper existente)

  **Filtros del listado:**
  - `activo` — boolean
  - `sedes__universidad` — select, `optionsEndpoint: "universities"`, label «Universidad»
  - `sedes__ipress` — select, `optionsEndpoint: "ipress"`,
    `optionsValueKey: "codigo_renipress"`, `optionsSearchable: true`, label «IPRESS»

  **Configuración general:**
  - `endpoint: "coordinators"`
  - `title: "Coordinadores"`, `singular: "coordinador"`
  - `description: "Coordinadores de tutores por sede docente."`
  - `searchPlaceholder: "Buscar por documento o nombres…"`
  - `writeRoles: ["Universidad", "Administrador RENADS"]`
  - `dialogClassName: "sm:max-w-2xl"`
  - En `editFields`: `tipo_documento_identidad` y `numero_documento` con `disabled: true`
    (identificador no editable una vez creado, igual que tutores)

  **Actualizar `PERSON_MENU`** al final del archivo: añadir `{ slug: "coordinators", title: "Coordinadores" }`.

  **Criterio de aceptación (CA-4):** `buildCoordinatorsConfig()` exportada y tipada como
  `() => ResourceConfig`. Todos los campos referencian endpoints reales del contrato.
  `PERSON_MENU` incluye la entrada `coordinators`. El archivo compila sin errores.

---

### Capa 4 — Componente dialog de sedes

- [x] **T5 — Crear `components/internados/coordinator-sedes-dialog.tsx`**

  Archivo: `components/internados/coordinator-sedes-dialog.tsx` (nuevo)

  Patrón de referencia: `components/internados/tutor-convenio-dialog.tsx`.

  **Props de la interfaz `CoordinatorSedesDialogProps`:**
  - `coordinatorId: number`
  - `coordinatorNombre: string`
  - `open: boolean`
  - `onOpenChange: (open: boolean) => void`
  - `universidad: number | null`
  - `canWrite: boolean`

  **Estructura del dialog (`sm:max-w-2xl`):**

  **Sección 1 — Lista de sedes actuales:**
  - Mientras carga: spinner + texto «Cargando sedes asignadas…»
  - Sin sedes: texto «Este coordinador no tiene sedes asignadas.»
  - Con sedes: tabla con columnas «Universidad», «IPRESS (sede docente)», «Tutores», «Acciones».
    - Columna «Tutores»: texto `n tutor(es)` donde `n` es el conteo de `CoordinatorTutor` de esa sede (se obtiene de la misma respuesta de sedes o con un query secundario — ver nota en T5).
    - Columna «Acciones» (solo `canWrite`): botón «Eliminar sede» (`variant="destructive"` `size="sm"`) con confirmación inline o tooltip.
  - Cada fila de sede es expandible o tiene un botón «Ver tutores» que muestra la sub-sección de tutores de esa sede (ver abajo).

  **Sub-sección de tutores por sede (se muestra al expandir / elegir una sede):**
  - Título: «Tutores — [nombre IPRESS]»
  - Lista de `CoordinatorTutor` con columnas: «Apellidos y nombres», «N° documento», acción «Desasignar» (solo `canWrite`, `variant="destructive"` `size="sm"`).
  - Si no hay tutores: «No hay tutores asignados a esta sede.»
  - Formulario de asignación de tutor (solo `canWrite`):
    - Selector `EntityCombobox<number>` sobre `tutors`, filtrado por `?universidades=<universidad>` (la universidad del alcance actual). `toLabel: (r) => apellidosNombresInline(r)`. Placeholder «Buscar tutor…».
    - Botón «Asignar» (disabled mientras no hay tutor seleccionado o mutación en curso).
    - Al asignar con éxito: `toast.success("Tutor asignado correctamente.")` + limpiar selector.
    - Al error: `toast.error(extractApiError(e))` (cubre RN-CRD-06).

  **Sección 2 — Formulario para agregar sede (solo `canWrite`):**
  - Separador visual con etiqueta «Agregar sede».
  - Selector `EntityCombobox<number>` sobre `universities`, `toLabel: (r) => String(r.nombre ?? r.siglas ?? r.id)`. Valor por defecto: la universidad del alcance actual (`universidad` prop), pero el usuario puede cambiarlo si es Admin.
  - Selector `EntityCombobox<string>` sobre `ipress`, `valueKey="codigo_renipress"`, filtrado con `?es_sede_docente=true`. Deshabilitado hasta que haya universidad seleccionada. `toLabel: (r) => String(r.nombre ?? r.codigo_renipress ?? r.id)`.
  - Botón «Agregar sede» (disabled mientras falta selección o mutación en curso).
  - Al agregar con éxito: `toast.success("Sede agregada correctamente.")` + limpiar selectores.
  - Al error: `toast.error(extractApiError(e))` (cubre RN-CRD-04 y RN-CRD-05).

  **Estado local:**
  - `sedeExpandida: number | null` — id de la sede cuya sub-sección de tutores está abierta.
  - `tutorSeleccionado: number | null` — tutor elegido en el selector de asignación.
  - `univSeleccionada: number | null` — universidad elegida para nueva sede (default: prop `universidad`).
  - `ipressSeleccionada: string | null` — IPRESS elegida para nueva sede.

  **Hooks usados:**
  - `useCoordinatorSedes(coordinatorId)` — carga la lista de sedes.
  - `useAddCoordinatorSede(coordinatorId)` — mutación para agregar sede.
  - `useDeleteCoordinatorSede(coordinatorId)` — mutación para eliminar sede.
  - `useCoordinatorTutors(coordinatorId, sedeExpandida)` — carga tutores de la sede abierta.
  - `useAddCoordinatorTutor(coordinatorId, sedeExpandida!)` — mutación para asignar tutor.
  - `useDeleteCoordinatorTutor(coordinatorId, sedeExpandida!)` — mutación para desasignar tutor.

  **Nota sobre conteo de tutores en columna «Tutores»:** el endpoint `GET /sedes/` no devuelve
  un campo `total_tutores`. El conteo se puede obtener cargando los tutores de cada sede en
  background (un query por sede visible) o mostrar simplemente un badge «Ver» sin conteo. Se
  prefiere mostrar un badge «Ver tutores» clickable sin conteo numérico para evitar N+1
  queries en el montaje del dialog; el implementador puede ajustar si el backend agrega el
  campo en el futuro.

  **Criterio de aceptación (CA-5):**
  - El dialog se abre y muestra la lista de sedes del coordinador.
  - Se puede agregar una sede (universidad + IPRESS sede docente); el error 400 del backend se muestra con `extractApiError`.
  - Se puede eliminar una sede (con su cascade de tutores).
  - Al expandir una sede se muestran sus tutores asignados.
  - Se puede asignar un tutor a la sede expandida.
  - Se puede desasignar un tutor.
  - El selector de IPRESS para agregar sede filtra con `?es_sede_docente=true`.
  - El selector de tutores para asignar filtra con `?universidades=<universidad>`.
  - Todas las mutaciones con error muestran `toast.error(extractApiError(e))`.
  - El componente no tiene referencias a TypeScript `any` suelto (puede usar `WithId` o tipos de T1).

---

### Capa 5 — Vista de coordinadores en la página de personas

- [x] **T6 — Añadir rama `coordinators` → `CoordinatorsView` en `app/(app)/internados/personas/[entidad]/page.tsx`**

  Archivo: `app/(app)/internados/personas/[entidad]/page.tsx`

  Cambios:

  1. En la función `PersonaPage`, añadir la rama:
     ```ts
     if (entidad === "coordinators") return <CoordinatorsView />;
     ```
     antes del bloque de fallback «Recurso no encontrado».

  2. Añadir imports:
     - `import { buildCoordinatorsConfig } from "@/lib/internados/persons";` (ya importado el archivo; solo añadir la función)
     - `import { CoordinatorSedesDialog } from "@/components/internados/coordinator-sedes-dialog";`

  3. Implementar `CoordinatorsView` siguiendo el patrón de `TutorsView`:
     - Usa `useUniversityGate()` para el paso de universidad.
     - El config se obtiene de `buildCoordinatorsConfig()` (sin parámetros).
     - `initialFilters`: cuando hay universidad elegida, pasa `{ sedes__universidad: String(universidad) }` para filtrar coordinadores de esa universidad en el listado.
     - **Row action «Sedes»** (visible para todos los roles autenticados):
       ```ts
       { key: "sedes", label: "Sedes", variant: "outline", onClick: (row) => setSedesCoordinador({ id: Number(row.id), nombre: apellidosNombresInline(row) }) }
       ```
     - Estado local `sedesCoordinador: { id: number; nombre: string } | null`.
     - Renderiza `<CoordinatorSedesDialog>` cuando `sedesCoordinador != null`.
     - El header no incluye wizard separado (el alta estándar de `ResourceCrud` es suficiente, a diferencia de tutores que usa `TutorCreateWizard`).
     - `hideHeader: true` para que el `PageHeader` lo gestione la vista.
     - Muestra `<EmptyPick label="Selecciona una universidad para ver sus coordinadores." />` cuando `universidad == null`.
     - Muestra `<UniversityLogoDisplay id={universidad} />` en el `PageHeader` cuando hay universidad.

  **Criterio de aceptación (CA-6):**
  - Navegar a `/internados/personas/coordinators` carga la vista de coordinadores.
  - El gate de universidad funciona (acotado al alcance del usuario, igual que Estudiantes/Tutores).
  - El listado se filtra por `sedes__universidad` cuando hay universidad elegida.
  - La row action «Sedes» abre el `CoordinatorSedesDialog` con el coordinador correcto.
  - El alta y edición de coordinadores funcionan con el formulario del CRUD estándar.
  - No hay errores de compilación.

---

### Capa 6 — Menú de navegación

- [x] **T7 — Añadir «Coordinadores» al grupo «Internado» en `components/layout/app-shell.tsx`**

  Archivo: `components/layout/app-shell.tsx`

  En el array `NAV_ITEMS`, dentro del nodo `label: "Internado"` (children), añadir después de
  la entrada «Tutores»:

  ```ts
  { label: "Coordinadores", icon: Users, href: "/internados/personas/coordinators" },
  ```

  El nodo padre «Internado» ya tiene los roles `["Administrador RENADS", "Universidad", "Autoridad de convenio"]`, por lo que «Coordinadores» hereda visibilidad correcta.

  **Criterio de aceptación (CA-7):**
  - El menú lateral muestra «Coordinadores» bajo el grupo «Internado» para los roles
    `Administrador RENADS` y `Universidad`.
  - El enlace activa la ruta `/internados/personas/coordinators`.
  - El elemento se resalta (clases `active`) cuando la ruta actual comienza con esa URL.

---

### Capa 7 — Documentación del contrato

- [x] **T8 — Añadir sección §Coordinadores en `docs/api-internados.md`**

  Archivo: `docs/api-internados.md`

  Añadir al final del documento una nueva sección:

  ```markdown
  ## Coordinadores (`coordinators`) — escritura `Universidad` / `Administrador RENADS`

  Coordinadores de tutores por sede docente. Un coordinador puede ser también tutor (FK
  opcional y única — RN-CRD-02). Puede representar múltiples sedes sin límite (RN-CRD-03).

  | Método | Ruta | Rol | Notas |
  |--------|------|-----|-------|
  | GET | `/coordinators/` | autenticado (alcance) | filtros abajo |
  | GET | `/coordinators/{id}/` | autenticado | |
  | POST | `/coordinators/` | `Universidad` / `Admin RENADS` | |
  | PATCH / DELETE | `/coordinators/{id}/` | `Universidad` / `Admin RENADS` | |
  | GET / POST | `/coordinators/{id}/sedes/` | GET: autenticado; POST: `Universidad` / `Admin RENADS` | Agregar sede (RN-CRD-04/05) |
  | GET / DELETE | `/coordinators/{id}/sedes/{sede_pk}/` | GET: autenticado; DELETE: `Universidad` / `Admin RENADS` | CASCADE elimina tutores |
  | GET / POST | `/coordinators/{id}/sedes/{sede_pk}/tutors/` | GET: autenticado; POST: `Universidad` / `Admin RENADS` | Asignar tutor (RN-CRD-06) |
  | DELETE | `/coordinators/{id}/sedes/{sede_pk}/tutors/{tutor_pk}/` | `Universidad` / `Admin RENADS` | Desasignar tutor |

  **Filtros** (`CoordinatorFilter`): `activo`, `sedes__universidad`, `sedes__ipress`.
  **Search:** `nombres`, `apellido_paterno`, `numero_documento`.

  ### Coordinator — lectura
  ```
  id, tutor (FK nullable), tutor_detalle {id, nombres, apellido_paterno},
  tipo_documento_identidad, numero_documento,
  nombres, apellido_paterno, apellido_materno,
  correo, telefono, numero_colegiatura, direccion,
  ubigeo, ubigeo_detalle, especialidad, profesion, activo
  ```

  ### Coordinator — escritura (POST/PATCH)
  ```
  tutor (nullable), tipo_documento_identidad, numero_documento,
  nombres, apellido_paterno, apellido_materno,
  correo, telefono, numero_colegiatura, direccion,
  ubigeo, especialidad, profesion, activo
  ```

  ### CoordinatorSede — lectura
  ```
  id, coordinador, universidad, ipress,
  universidad_detalle {id, nombre},
  ipress_detalle {codigo_renipress, nombre}
  ```

  ### CoordinatorSede — escritura (POST)
  ```
  universidad (req), ipress (req — código RENIPRESS, es_sede_docente=True, RN-CRD-04/05)
  ```

  ### CoordinatorTutor — lectura
  ```
  id, coordinador_sede, tutor,
  tutor_detalle {id, nombres, apellido_paterno, numero_documento}
  ```

  ### CoordinatorTutor — escritura (POST)
  ```
  tutor (req — id numérico; unicidad global por sede+universidad validada en backend — RN-CRD-06)
  ```
  ```

  **Criterio de aceptación (CA-8):**
  - La sección existe y describe los 10 endpoints con métodos, roles y campos exactos del contrato del backend (`renads-api/spec/internados_coordinador.md`).
  - Los campos de lectura/escritura coinciden con los serializers del backend.
  - No se inventan campos ni endpoints que no estén en el contrato validado.

---

## 3. Criterios de aceptación consolidados

| Tarea | CA | Descripción |
|-------|----|-------------|
| T1 | CA-1 | Tipos TS exportados; claves en español; sin errores de tipo |
| T2 | CA-2a | Funciones API usando `api` de `lib/api/client`; URLs exactas del contrato |
| T3 | CA-3 | 6 hooks exportados; queryKeys jerárquicas; invalidación correcta |
| T4 | CA-4 | `buildCoordinatorsConfig()` exportada; `PERSON_MENU` actualizado |
| T5 | CA-5 | Dialog funcional: sedes, tutores, agregar, eliminar, errores con `extractApiError` |
| T6 | CA-6 | `CoordinatorsView` con gate universidad, filtro, row action «Sedes» |
| T7 | CA-7 | Entrada «Coordinadores» visible en menú «Internado» con los roles correctos |
| T8 | CA-8 | Sección §Coordinadores en `docs/api-internados.md` alineada al contrato |

## 4. Referencias explícitas al contrato del backend

- `renads-api/spec/internados_coordinador.md` — modelos, serializers, services, views, endpoints, RN.
- `renads-api/spec/internados_coordinador.validacion.md` — verificación del backend completada (todos OK).
- `docs/api-internados.md` — contrato de lectura del módulo (debe actualizarse en T8).
- Endpoints confirmados en `apps/internados/urls.py` y `apps/internados/views.py` del backend.

## 5. Gating por rol

| Acción | Roles visibles | Nota |
|--------|---------------|------|
| Ver listado de coordinadores | Todos los autenticados del alcance | Gate de universidad igual que Tutores/Estudiantes |
| Alta / edición / borrado de coordinador | `Universidad`, `Administrador RENADS` | `writeRoles` en `ResourceConfig` |
| Botón «Sedes» (row action) | Todos los autenticados | Solo lectura para quien no tenga `canWrite` |
| Agregar / eliminar sede | `Universidad`, `Administrador RENADS` | `canWrite` prop del dialog |
| Asignar / desasignar tutor en sede | `Universidad`, `Administrador RENADS` | `canWrite` prop del dialog |

> La autoridad final es el backend. El gating de UI es UX; el backend devuelve 403 para
> peticiones no autorizadas independientemente de lo que muestre el front.

## 6. Estado / separación Query vs Zustand

- **TanStack Query** (servidor): lista de coordinadores, sedes por coordinador, tutores por sede.
- **Zustand** (cliente): nada nuevo; el usuario (`me`) ya vive en `useAuthStore`.
- Estado local (`useState`): id del coordinador cuyo dialog de sedes está abierto, sede expandida dentro del dialog, selecciones de form dentro del dialog.

## 7. Archivos a crear / modificar

| Archivo | Operación |
|---------|-----------|
| `lib/internados/types.ts` | Añadir `CoordinatorRead`, `CoordinatorSedeRead`, `CoordinatorTutorRead` |
| `lib/internados/coordinator.ts` | Nuevo — funciones API + 6 hooks TanStack Query |
| `lib/internados/persons.ts` | Añadir `buildCoordinatorsConfig()` + entrada en `PERSON_MENU` |
| `components/internados/coordinator-sedes-dialog.tsx` | Nuevo — dialog de sedes y tutores anidados |
| `app/(app)/internados/personas/[entidad]/page.tsx` | Añadir rama `coordinators` → `CoordinatorsView` |
| `components/layout/app-shell.tsx` | Añadir «Coordinadores» al grupo «Internado» |
| `docs/api-internados.md` | Añadir sección §Coordinadores |

---

> **Este spec requiere aprobacion humana antes de pasar al agente `implement`.**
