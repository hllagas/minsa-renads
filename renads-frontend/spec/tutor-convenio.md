# Spec — Feature: TutorConvenio (asignación tutor × convenio × IPRESS)

**Fecha:** 2026-09-26
**Módulo:** Internados (feature incremental — base CERRADA)
**Estado:** ⏳ Pendiente aprobación humana antes de `implement`

---

## 1. Resumen del feature y pantallas cubiertas

Cada tutor puede estar asignado a uno o varios **Convenios Específicos vigentes + IPRESS** (tabla
`tutor_convenio`). Actualmente esta asignación no tiene interfaz; se implementa aquí como una
**row action** en el listado de tutores que abre un dialog de gestión.

**Pantalla afectada:** `/internados/personas/tutors`
(`app/(app)/internados/personas/[entidad]/page.tsx` → componente `TutorsView`)

**UX del dialog:**
1. Lista de vínculos actuales del tutor (tabla simple: nomenclatura + título del convenio, nombre
   de la IPRESS, botón «Eliminar» por fila).
2. Formulario de alta con dos selects encadenados:
   - **Convenio Específico** — filtrado por la universidad del alcance + `tipo_convenio`=Específico
     + `estado_actual` vigente.
   - **IPRESS** — filtrado por la universidad del alcance; PK textual `codigo_renipress`.
3. Botón «Agregar» que llama `POST /tutors/{id}/convenios/`.
4. Al agregar o eliminar un vínculo, invalidar la lista de TutorConvenio del tutor.

**No se navega a otra ruta.** Todo ocurre en el dialog.

---

## 2. Contrato del backend (fuente: `docs/api-internados.md` §TutorConvenio)

```
GET    /tutors/{id}/convenios/               → lista TutorConvenio[]
POST   /tutors/{id}/convenios/               → crea vínculo { convenio, ipress }
GET    /tutors/{id}/convenios/{convenio_pk}/ → detalle (no necesario para la UI)
DELETE /tutors/{id}/convenios/{convenio_pk}/ → elimina vínculo (204)
```

**Lectura de cada `TutorConvenio`:**
```
id (= convenio_pk),
tutor,
convenio,
convenio_detalle { id, titulo, nomenclatura },
ipress,
ipress_detalle { codigo_renipress, nombre }
```

**Escritura (POST):**
```
convenio  (req — FK a Convenio Específico vigente)
ipress    (req — FK a IPRESS, valor = string `codigo_renipress`)
```

**Roles con permiso de escritura:** `Universidad` / `Administrador RENADS`

**Regla de negocio (backend valida):**
- Solo convenios de tipo Específico y en estado vigente (`VIGENTE`/`PUBLICADO`/`SUSCRITO`).
- La IPRESS debe pertenecer al ámbito del convenio (400 si no). El frontend no valida esto.
- **RN-CRD-03:** un tutor puede representar múltiples pares (universidad, sede) sin límite.
  No hay tope de cardinalidad (ver `renads-api/spec/internados_coordinador.md §2`).

---

## 3. Tareas

### Bloque A — Tipos / contratos

- [x] **A1 — Tipo `TutorConvenioRead`** en `lib/internados/types.ts` (crear el archivo si no existe,
  o añadir al existente).

  ```ts
  export interface TutorConvenioRead {
    id: number;                        // convenio_pk
    tutor: number;
    convenio: number;
    convenio_detalle: {
      id: number;
      titulo: string;
      nomenclatura: string | null;
    };
    ipress: string;                    // codigo_renipress (PK textual)
    ipress_detalle: {
      codigo_renipress: string;
      nombre: string;
    };
  }
  ```

  **Criterio:** el tipo refleja exactamente el contrato de lectura de `docs/api-internados.md`
  §TutorConvenio. No inventar campos adicionales.

---

### Bloque B — Capa API / hooks

- [x] **B1 — Función de lista `getTutorConvenios(tutorId)`** en `lib/internados/tutor-convenio.ts`
  (archivo nuevo).

  Llama `GET /tutors/{tutorId}/convenios/`. Retorna `TutorConvenioRead[]`.
  La respuesta puede ser un array directo o un objeto paginado; manejar ambos casos (el endpoint de
  sub-recurso usualmente devuelve array o paginado — usar `results` si hay `results`, sino asumir
  array).

  **Criterio:** la función usa `api` de `lib/api/client.ts` y tipifica la respuesta con
  `TutorConvenioRead`.

- [x] **B2 — Función de creación `createTutorConvenio(tutorId, payload)`** en
  `lib/internados/tutor-convenio.ts`.

  Llama `POST /tutors/{tutorId}/convenios/` con `{ convenio: number, ipress: string }`.
  Retorna `TutorConvenioRead`.

  **Criterio:** la función tipifica payload y respuesta correctamente.

- [x] **B3 — Función de eliminación `deleteTutorConvenio(tutorId, convenioPk)`** en
  `lib/internados/tutor-convenio.ts`.

  Llama `DELETE /tutors/{tutorId}/convenios/{convenioPk}/`. Retorna `void`.

  **Criterio:** la función no retorna cuerpo (204); no tipifica respuesta.

- [x] **B4 — Hook `useTutorConvenios(tutorId)`** en `lib/internados/tutor-convenio.ts`.

  Usa `useQuery` de TanStack Query.
  - `queryKey: ["tutors", tutorId, "convenios"]`
  - `queryFn: () => getTutorConvenios(tutorId)`
  - `enabled: tutorId != null && tutorId > 0`

  **Criterio:** el hook retorna `{ data: TutorConvenioRead[], isLoading, error }`.

- [x] **B5 — Hook `useAddTutorConvenio(tutorId)`** en `lib/internados/tutor-convenio.ts`.

  Usa `useMutation` de TanStack Query.
  - `mutationFn: (payload) => createTutorConvenio(tutorId, payload)`
  - `onSuccess`: invalida `["tutors", tutorId, "convenios"]`.

  **Criterio:** tras una mutación exitosa, la lista se refresca automáticamente.

- [x] **B6 — Hook `useDeleteTutorConvenio(tutorId)`** en `lib/internados/tutor-convenio.ts`.

  Usa `useMutation`.
  - `mutationFn: (convenioPk: number) => deleteTutorConvenio(tutorId, convenioPk)`
  - `onSuccess`: invalida `["tutors", tutorId, "convenios"]`.

  **Criterio:** al eliminar, la lista se refresca automáticamente.

---

### Bloque C — Componente dialog

- [x] **C1 — Componente `TutorConvenioDialog`** en
  `components/internados/tutor-convenio-dialog.tsx` (archivo nuevo).

  **Props:**
  ```ts
  interface TutorConvenioDialogProps {
    tutorId: number;
    tutorNombre: string;   // para el título del dialog
    open: boolean;
    onOpenChange: (open: boolean) => void;
    universidad: number | null;  // id de la universidad del alcance actual
    canWrite: boolean;           // gating: `Universidad` / `Administrador RENADS`
  }
  ```

  **Estructura interna:**
  - Usa `Dialog` / `DialogContent` / `DialogHeader` / `DialogTitle` de shadcn/ui.
  - Título: «Convenios asignados — {tutorNombre}».
  - Cuerpo dividido en dos secciones:

    **Sección 1 — Lista de vínculos actuales:**
    - Consume `useTutorConvenios(tutorId)`.
    - Mientras carga: estado de carga (spinner o skeleton).
    - Sin vínculos: mensaje «Este tutor no tiene convenios asignados.»
    - Con vínculos: tabla simple (no `DataTable` con paginación — la lista es corta) con columnas:
      - «Convenio» — `convenio_detalle.nomenclatura ?? ""` + `" — "` +
        `convenio_detalle.titulo` (truncar si muy largo).
      - «IPRESS» — `ipress_detalle.nombre`.
      - «Acción» — botón «Eliminar» (destructivo, solo si `canWrite`).
    - Al pulsar «Eliminar»: llamar `useDeleteTutorConvenio` con `id` del vínculo; mostrar
      toast de éxito/error con `extractApiError`.

    **Sección 2 — Formulario de alta (solo si `canWrite`):**
    - Separador visual con etiqueta «Agregar convenio».
    - Select **Convenio Específico**: llama `GET /conventions/?universidad={universidad}&tipo_convenio=<específico_id>&estado_actual=<vigente_ids>` donde los ids de tipo y estado se resuelven en runtime por nombre (patrón ya implementado en `app/(app)/internados/internos/page.tsx`).
      - Label de opción: `r.nomenclatura ? r.nomenclatura + " — " + r.titulo : r.titulo`.
      - Usa `EntityCombobox` de `components/form/entity-combobox.tsx`.
      - Si `universidad` es `null`, el select está deshabilitado con tooltip «Selecciona una
        universidad primero».
    - Select **IPRESS**: `EntityCombobox` con `optionsEndpoint="ipress"`,
      `valueKey="codigo_renipress"`, `optionsSearchable`.
      - Filtro: `?universidad={universidad}` (si disponible).
      - Deshabilitado mientras no haya convenio seleccionado (UX; el backend valida el ámbito).
    - Botón «Agregar»: llama `useAddTutorConvenio`; limpia los selects al tener éxito; muestra
      toast de éxito/error con `extractApiError`. Deshabilitado si `convenio` o `ipress` vacíos.

  **Criterio de aceptación:**
  - El dialog abre correctamente desde la row action.
  - La lista de vínculos carga y refleja el estado real del backend.
  - Agregar: el POST se ejecuta con los valores correctos (`convenio: number`, `ipress: string`);
    la lista se actualiza sin recargar la página.
  - Eliminar: el DELETE se ejecuta con el `convenio_pk` correcto; la lista se actualiza.
  - Si el backend devuelve 400/409, el error se muestra en un toast legible.
  - Con `canWrite=false`: los controles de alta y el botón «Eliminar» no se renderizan.

---

### Bloque D — Resolución de ids de tipo y estado de convenio

- [x] **D1 — Resolver ids de `tipo_convenio` «Específico» y estados vigentes en el dialog.**

  El select de convenios del form necesita filtrar por `tipo_convenio` (id del tipo «Específico»)
  y `estado_actual` (ids de estados vigentes: `VIGENTE`/`PUBLICADO`/`SUSCRITO`). Estos ids no se
  hardcodean; se resuelven en runtime.

  Patrón de referencia: `app/(app)/internados/internos/page.tsx` (ver CLAUDE.md §2026-09-09 UI
  internos y §2026-09-10 UX internos).

  Implementar dentro de `TutorConvenioDialog` o en un hook auxiliar
  `useConveniosEspecificosVigentes(universidadId)` en `lib/internados/tutor-convenio.ts`:

  - Query a `GET /convention-types/` (o `classification-types` según el endpoint correcto — ver
    `docs/api-convenios.md`) para encontrar el tipo «Específico» por nombre.
  - Query a `GET /convention-statuses/` (o `internship-statuses`; confirmar endpoint correcto en
    `docs/api-convenios.md`) para encontrar los ids de `VIGENTE`, `PUBLICADO`, `SUSCRITO`.
  - Si el endpoint de convenios acepta `estado_actual` como lista CSV o múltiples params,
    construir los params correctamente (ver `docs/api-convenios.md`).

  > **Pregunta abierta D1-P1 (ver §5):** confirmar el nombre exacto del endpoint de tipos de
  > convenio y el formato del filtro `estado_actual` (¿id único o lista?). Si `estado_actual`
  > admite solo un valor, usar el estado «VIGENTE» como representativo (consultar con el usuario).

  **Criterio:** los convenios que aparecen en el select son solo Específicos y en estado vigente
  de la universidad del alcance. Nunca se hardcodea un id numérico.

---

### Bloque E — Integración en la vista de tutores

- [x] **E1 — Row action «Convenios asignados» en `TutorsView`.**

  En `app/(app)/internados/personas/[entidad]/page.tsx`, función `TutorsView`:

  1. Añadir estado local:
     ```ts
     const [conveniosTutor, setConveniosTutor] = useState<{ id: number; nombre: string } | null>(null);
     ```
  2. Definir la row action:
     ```ts
     const rowActions: RowAction<WithId>[] = [
       {
         key: "convenios",
         label: "Convenios asignados",
         variant: "outline",
         onClick: (row) =>
           setConveniosTutor({
             id: Number(row.id),
             nombre: apellidosNombres(row),  // helper ya definido en lib/internados/persons.ts
           }),
       },
     ];
     ```
     La action se muestra para todos los roles (lectura no requiere permiso especial).
  3. Pasar `rowActions` a `<ResourceCrud ... rowActions={rowActions} />`.
  4. Renderizar `<TutorConvenioDialog>` fuera del `ResourceCrud`:
     ```tsx
     {conveniosTutor && (
       <TutorConvenioDialog
         tutorId={conveniosTutor.id}
         tutorNombre={conveniosTutor.nombre}
         open={conveniosTutor !== null}
         onOpenChange={(open) => { if (!open) setConveniosTutor(null); }}
         universidad={universidad}
         canWrite={canWrite}
       />
     )}
     ```

  **Criterio de aceptación:**
  - En el listado de tutores, cada fila muestra el botón «Convenios asignados» en la columna de
    acciones.
  - Pulsar el botón abre el dialog con el tutor correcto (nombre en el título, lista del tutor).
  - Cerrar el dialog limpia el estado (`conveniosTutor = null`).
  - El botón es visible para todos los roles autenticados (lectura sin restricción).
  - `canWrite` llega correctamente al dialog (gatea los controles de escritura dentro).

---

### Bloque F — Gating por rol

- [x] **F1 — Gating de escritura en `TutorConvenioDialog`.**

  La prop `canWrite` del dialog se calcula en `TutorsView`:
  ```ts
  const canWrite = userHasRole(user, "Universidad", "Administrador RENADS");
  ```
  (misma constante ya disponible en `TutorsView`).

  Dentro del dialog:
  - `canWrite=true` → muestra la sección «Agregar convenio» y los botones «Eliminar».
  - `canWrite=false` → oculta la sección de alta y los botones «Eliminar»; el dialog es solo
    lectura (lista de vínculos sin acciones).

  **Criterio:** un usuario con rol `Interno` u otro sin permiso puede ver la lista de convenios
  asignados al tutor, pero no puede agregar ni eliminar. El backend es la autoridad final (devuelve
  403/401 si se intenta igual).

---

## 4. Criterios de aceptación globales

| # | Criterio |
|---|----------|
| CA-1 | La row action «Convenios asignados» aparece en cada fila del listado de tutores. |
| CA-2 | El dialog muestra la lista de vínculos actuales del tutor desde `GET /tutors/{id}/convenios/`. |
| CA-3 | El POST se ejecuta con `{ convenio: <id>, ipress: "<codigo_renipress>" }` y la lista se refresca sin recargar la página. |
| CA-4 | El DELETE se ejecuta contra `/tutors/{id}/convenios/{convenio_pk}/` y la lista se refresca. |
| CA-5 | Los selects del form muestran solo Convenios Específicos vigentes de la universidad del alcance. |
| CA-6 | El select de IPRESS usa `codigo_renipress` (string) como valor enviado al backend. |
| CA-7 | Errores 400/409 del backend se muestran en toast legible (`extractApiError`). |
| CA-8 | Con `canWrite=false`, los controles de escritura no se renderizan. |
| CA-9 | No se hardcodean ids numéricos de tipos de convenio ni de estados; se resuelven en runtime. |
| CA-10 | El listado de tutores (`ResourceCrud`) y sus demás funcionalidades no se ven afectados. |

---

## 5. Preguntas abiertas (resolver antes o durante `implement`)

- **D1-P1 — Endpoint y filtros de convenios en el form:**
  ¿Qué endpoint y params exactos usa el select de Convenio Específico vigente? Patrón de referencia
  en `app/(app)/internados/internos/page.tsx`. Confirmar que `conventions?universidad=<id>` acepta
  filtro `tipo_convenio` (id) y `estado_actual` (id o CSV). Si `estado_actual` solo admite un valor,
  usar un solo estado (`VIGENTE`) o consultar con el usuario.

- **D1-P2 — Respuesta paginada vs. array de `/tutors/{id}/convenios/`:**
  El endpoint de sub-recurso puede devolver array directo o `{ count, results, ... }`. Verificar
  con el backend antes de implementar `getTutorConvenios`; la función debe manejar ambos casos.

- **D1-P3 — Filtro de IPRESS por universidad:**
  ¿El endpoint `ipress` acepta `?universidad=<id>` para filtrar las IPRESS vinculadas a un convenio
  de esa universidad? Si no existe ese filtro, el select puede mostrar todas las IPRESS (el backend
  valida el ámbito del convenio al hacer POST).

---

## 6. Archivos a crear / modificar

| Archivo | Operación | Descripción |
|---------|-----------|-------------|
| `lib/internados/types.ts` | Crear (o añadir) | Tipo `TutorConvenioRead` (tarea A1) |
| `lib/internados/tutor-convenio.ts` | Crear | Funciones API + hooks (tareas B1–B6, D1) |
| `components/internados/tutor-convenio-dialog.tsx` | Crear | Dialog de gestión de vínculos (tarea C1) |
| `app/(app)/internados/personas/[entidad]/page.tsx` | Modificar | Row action + render del dialog en `TutorsView` (tarea E1) |

---

## 7. Referencias explícitas al contrato

- `docs/api-internados.md` — §«TutorConvenio — vínculo tutor × convenio × IPRESS» (endpoints,
  campos lectura/escritura, roles, reglas de negocio).
- `docs/api-internados.md` — §`tutors` (alcance por universidad, filtro `universidades`).
- `lib/api/flow.ts` — `useResourceSubList` y `useResourceAction` (patrón de sub-recurso genérico;
  este feature lo reemplaza con hooks propios para tipificación correcta de `TutorConvenioRead`).
- `lib/auth/scope.ts` — `useUniversityScope()` (derivar `universidad` del alcance).
- `lib/auth/store.ts` — `useAuthStore`, `userHasRole` (gating).
- `lib/api/errors.ts` — `extractApiError` (manejo de errores en toasts).
- `components/form/entity-combobox.tsx` — `EntityCombobox` con `valueKey` para IPRESS (PK textual).
- `app/(app)/internados/internos/page.tsx` — patrón de resolución de ids de tipo de convenio y
  estados vigentes en runtime.
- `lib/crud/types.ts` — `RowAction` (estructura de la row action de tutores).
- `components/crud/resource-crud.tsx` — prop `rowActions` de `ResourceCrud`.

---

## 8. Aprobación

> **Este spec requiere aprobación humana antes de pasar al agente `implement`.**
>
> Revisar especialmente:
> - Las preguntas abiertas D1-P1, D1-P2, D1-P3 (contrato de endpoints).
> - Si la UX del dialog es la deseada (lista + form en el mismo dialog vs. dos dialogs separados).
> - Si el botón «Convenios asignados» debe mostrarse solo a roles con escritura o a todos.

- [ ] Aprobación humana del spec
