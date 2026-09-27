# Spec — Coordinadores: ajustes post-migración 0033+0034

**Estado:** APROBADO

**Módulo:** Internados — Coordinadores (`/internados/personas/coordinators`)
**Tipo:** Corrección de discordancias entre el frontend y el contrato real del backend
tras las migraciones `0033` (FK `universidad` directa en `Coordinator`) y `0034`
(eliminación del campo `universidad` de `CoordinatorSede`).

---

## 1. Resumen del módulo

El frontend de coordinadores presenta 8 discordancias respecto al contrato real del
backend (`renads-api/apps/internados/serializers.py`, `views.py`, `models.py`):

- **Tipos incorrectos** (`CoordinatorRead` sin `universidad`; `CoordinatorSedeRead` con
  `universidad: number` que ya no existe en el modelo).
- **Payload de POST sede** envía `{ universidad, ipress }` cuando el backend solo
  acepta `{ ipress }`.
- **URLs de tutores** apuntan a `/tutors/` cuando el endpoint real es `/tutores/`.
- **Hook faltante** para `GET /coordinators/{id}/sedes-disponibles/`.
- **Filtro erróneo** `sedes__universidad` — el campo correcto desde la migración 0033
  es simplemente `universidad` (la FK vive ahora directamente en `Coordinator`).
- **`initialFilters` erróneo** en `CoordinatorsView` (mismo campo).
- **Dialog de agregar sede** incluye un selector de universidad innecesario y lo envía
  en el payload; el selector de IPRESS debe usar `sedes-disponibles` en lugar del
  catálogo general de `ipress?es_sede_docente=true`.
- **`docs/api-internados.md`** §Coordinadores desactualizado.

**Archivos a modificar: 6. No se crean archivos nuevos.**

---

## 2. Fuentes de verdad (contrato real del backend)

### `CoordinatorSerializer` (serializers.py líneas 213–246)

```python
fields = [
    "id", "tutor", "tutor_detalle", "universidad", "universidad_detalle",
    "tipo_documento_identidad", "numero_documento",
    "nombres", "apellido_paterno", "apellido_materno", "correo", "telefono",
    "numero_colegiatura", "direccion", "ubigeo", "especialidad", "profesion", "activo",
]
# universidad_detalle → { id: number; nombre: string }
```

Escritura POST/PATCH acepta `universidad` (FK requerida).

### `CoordinatorSedeSerializer` (serializers.py líneas 249–275)

```python
fields = ["id", "coordinador", "ipress", "universidad_detalle", "ipress_detalle"]
# universidad_detalle → { id: number; nombre: string }  (derivada de coordinador.universidad)
# SIN campo "universidad" de escritura
```

### `CoordinatorViewSet` (views.py líneas 499–619)

- `filterset_fields = ["activo", "universidad", "sedes__ipress"]`
  — el filtro `sedes__universidad` **ya no existe**; el correcto es `universidad`.
- `url_path="sedes-disponibles"` → `GET /coordinators/{id}/sedes-disponibles/`
  devuelve `[{ id: codigo_renipress, nombre }]` (IPRESS aptas que no están ya asignadas
  al coordinador y cuya UE tiene ≥1 Convenio Específico vigente para la universidad del
  coordinador).
- Acciones de tutores: `url_path=r"sedes/(?P<sede_pk>[^/.]+)/tutores"` y
  `url_path=r"sedes/(?P<sede_pk>[^/.]+)/tutores/(?P<tutor_pk>[^/.]+)"`.

### `CoordinatorSede` (models.py líneas 322–348)

Solo tiene dos campos propios: `coordinador` (FK) e `ipress` (FK).
**No tiene campo `universidad`.** La universidad se lee vía `coordinador.universidad`.

---

## 3. Lista de tareas

### T1 — Corregir `CoordinatorRead` y `CoordinatorSedeRead` en `lib/internados/types.ts`

- [x] **T1**

**Descripción:** El tipo `CoordinatorRead` carece de `universidad: number` y
`universidad_detalle: { id: number; nombre: string }`. El tipo `CoordinatorSedeRead`
declara `universidad: number` como campo de primer nivel, que ya no existe en el modelo
`CoordinatorSede` desde la migración 0033; ese campo debe eliminarse.

**Cambio en `CoordinatorRead` (añadir dos campos):**
```typescript
// ANTES (líneas 26-43 de lib/internados/types.ts):
export interface CoordinatorRead {
  id: number;
  tutor: number | null;
  tutor_detalle: { id: number; nombres: string; apellido_paterno: string } | null;
  tipo_documento_identidad: number;
  // ... (sin universidad)
  activo: boolean;
}

// DESPUÉS:
export interface CoordinatorRead {
  id: number;
  tutor: number | null;
  tutor_detalle: { id: number; nombres: string; apellido_paterno: string } | null;
  universidad: number;
  universidad_detalle: { id: number; nombre: string };
  tipo_documento_identidad: number;
  numero_documento: string;
  nombres: string;
  apellido_paterno: string;
  apellido_materno: string | null;
  correo: string | null;
  telefono: string | null;
  numero_colegiatura: string | null;
  direccion: string | null;
  ubigeo: string | null;
  especialidad: number | null;
  profesion: number | null;
  activo: boolean;
}
```

**Cambio en `CoordinatorSedeRead` (eliminar `universidad: number` de primer nivel):**
```typescript
// ANTES (líneas 45-53):
export interface CoordinatorSedeRead {
  id: number;
  coordinador: number;
  universidad: number;          // ← ELIMINAR (ya no existe en el modelo)
  ipress: string;
  universidad_detalle: { id: number; nombre: string };
  ipress_detalle: { codigo_renipress: string; nombre: string };
}

// DESPUÉS:
export interface CoordinatorSedeRead {
  id: number;
  coordinador: number;
  ipress: string;
  universidad_detalle: { id: number; nombre: string };
  ipress_detalle: { codigo_renipress: string; nombre: string };
}
```

**Criterio de aceptación:** `CoordinatorRead` expone `universidad: number` y
`universidad_detalle: {id,nombre}`. `CoordinatorSedeRead` no expone `universidad: number`.
El código que consume estos tipos compila sin errores TS.

---

### T2 — Corregir payload de `createCoordinatorSede` en `lib/internados/coordinator.ts`

- [x] **T2**

**Descripción:** La función `createCoordinatorSede` actualmente envía
`{ universidad: number; ipress: string }`. El backend `CoordinatorSedeSerializer` solo
acepta `{ ipress }` — `universidad` se deriva automáticamente del coordinador. Enviar
`universidad` no produce error HTTP (el campo es ignorado), pero el payload del hook
`useAddCoordinatorSede` tiene tipo incorrecto.

**Cambios:**

```typescript
// ANTES (línea 50):
export async function createCoordinatorSede(
  coordinatorId: number,
  payload: { universidad: number; ipress: string },
): Promise<CoordinatorSedeRead> { ... }

// DESPUÉS:
export async function createCoordinatorSede(
  coordinatorId: number,
  payload: { ipress: string },
): Promise<CoordinatorSedeRead> { ... }
```

```typescript
// ANTES (línea 153 — mutationFn del hook):
mutationFn: (payload: { universidad: number; ipress: string }) =>
  createCoordinatorSede(coordinatorId, payload),

// DESPUÉS:
mutationFn: (payload: { ipress: string }) =>
  createCoordinatorSede(coordinatorId, payload),
```

**Criterio de aceptación:** `createCoordinatorSede` y `useAddCoordinatorSede` aceptan
solo `{ ipress: string }`. El tipo no incluye `universidad`. Compila sin errores TS.

---

### T3 — Corregir URLs de tutores en `lib/internados/coordinator.ts`

- [x] **T3**

**Descripción:** Las tres funciones que usan el sub-recurso de tutores apuntan a
`/tutors/` cuando el `url_path` del backend es `tutores` (plural español). Esto produce
404 en todas las operaciones sobre tutores de coordinador.

**Cambios (3 ocurrencias):**

```typescript
// ANTES (línea 80):
`/coordinators/${coordinatorId}/sedes/${sedePk}/tutors/`

// DESPUÉS:
`/coordinators/${coordinatorId}/sedes/${sedePk}/tutores/`
```

```typescript
// ANTES (línea 117):
`/coordinators/${coordinatorId}/sedes/${sedePk}/tutors/`

// DESPUÉS:
`/coordinators/${coordinatorId}/sedes/${sedePk}/tutores/`
```

```typescript
// ANTES (línea 132):
`/coordinators/${coordinatorId}/sedes/${sedePk}/tutors/${tutorPk}/`

// DESPUÉS:
`/coordinators/${coordinatorId}/sedes/${sedePk}/tutores/${tutorPk}/`
```

Adicionalmente, corregir los `console.warn` internos que mencionan la URL en los
métodos `getCoordinatorTutors` para reflejar la URL correcta.

**Criterio de aceptación:** Las tres URLs usan `/tutores/`. Las peticiones GET, POST y
DELETE de tutores de coordinador devuelven las respuestas correctas del backend (no 404).

---

### T4 — Añadir `useSedesDisponibles` en `lib/internados/coordinator.ts`

- [x] **T4**

**Descripción:** Falta la función y el hook para `GET /coordinators/{id}/sedes-disponibles/`.
El backend devuelve `[{ id: codigo_renipress, nombre }]` — IPRESS aptas para el
coordinador (sede docente + convenio vigente + no asignada ya). El dialog de agregar
sede debe usar este endpoint en lugar del catálogo general `ipress?es_sede_docente=true`.

**Añadir al final de `lib/internados/coordinator.ts`:**

```typescript
/** Respuesta de /coordinators/{id}/sedes-disponibles/ */
export interface SedeDisponible {
  id: string;       // codigo_renipress (PK textual)
  nombre: string;
}

/** Obtiene las sedes docentes disponibles para asignar al coordinador. */
export async function getSedesDisponibles(
  coordinatorId: number,
): Promise<SedeDisponible[]> {
  const response = await api.get<SedeDisponible[]>(
    `/coordinators/${coordinatorId}/sedes-disponibles/`,
  );
  return Array.isArray(response.data) ? response.data : [];
}

/** Hook TanStack Query para listar las sedes disponibles del coordinador. */
export function useSedesDisponibles(coordinatorId: number | null) {
  return useQuery({
    queryKey: ["coordinators", coordinatorId, "sedes-disponibles"],
    queryFn: () => getSedesDisponibles(coordinatorId!),
    enabled: coordinatorId != null,
  });
}
```

**Criterio de aceptación:** `useSedesDisponibles(coordinatorId)` existe y exporta un
hook de TanStack Query. Cuando `coordinatorId` es `null`, la query no se ejecuta
(`enabled: false`). El tipo de retorno es `SedeDisponible[]`.

---

### T5 — Corregir filtro `sedes__universidad` → `universidad` en `lib/internados/persons.ts`

- [x] **T5**

**Descripción:** `buildCoordinatorsConfig()` declara el filtro con `name: "sedes__universidad"`.
El `filterset_fields` real del backend (`views.py` línea 514) es `["activo", "universidad",
"sedes__ipress"]`. El campo `sedes__universidad` ya no existe desde la migración 0033.
Además, deben añadirse:
- Columna «Universidad» en `coordinatorColumns` (lee `universidad_detalle.nombre`).
- Campo `universidad` en el formulario de alta (requerido, `type: "select"`,
  `optionsEndpoint: "universities"`).

**Cambio en `coordinatorColumns`:**
```typescript
// Añadir antes de la columna "activo":
{
  key: "universidad",
  header: "Universidad",
  render: (r) => detalleNombre(r.universidad_detalle),
},
```

**Cambio en el filtro de `buildCoordinatorsConfig`:**
```typescript
// ANTES:
{ name: "sedes__universidad", label: "Universidad", type: "select", optionsEndpoint: "universities" },

// DESPUÉS:
{ name: "universidad", label: "Universidad", type: "select", optionsEndpoint: "universities" },
```

**Añadir campo `universidad` en el array `fields` de `buildCoordinatorsConfig`**, en
la sección «Datos profesionales» (antes de `profesion`), con `type: "select"`,
`required: true`, `optionsEndpoint: "universities"`. En `editFields` el campo debe
quedar `disabled: true` (la universidad de un coordinador no debe cambiar por edición
directa, sino gestionarse con cuidado; si el backend lo permite en PATCH se puede
mantener editable, pero por coherencia UX se deshabilita igual que `tipo_documento_identidad`
y `numero_documento`).

**Criterio de aceptación:** El filtro de la barra de coordinadores usa `?universidad=<id>`.
El formulario de alta incluye el campo «Universidad» requerido. La tabla muestra la
columna «Universidad» con el nombre de la universidad leído de `universidad_detalle.nombre`.

---

### T6 — Corregir `initialFilters` y `fixedValues` en `CoordinatorsView`

- [x] **T6**

**Descripción:** `CoordinatorsView` en `app/(app)/internados/personas/[entidad]/page.tsx`
(líneas 289–293) usa `sedes__universidad` como clave del filtro inicial. Debe cambiarse
a `universidad`. Adicionalmente, como el formulario de alta ahora incluye el campo
`universidad`, debe añadirse `fixedValues={{ universidad }}` al `<ResourceCrud>` para
que la universidad se inyecte automáticamente en el alta sin que el usuario tenga que
elegirla.

**Cambio en `initialFilters`:**
```typescript
// ANTES (línea 290-292):
const initialFilters = useMemo<Record<string, string> | undefined>(
  () =>
    universidad != null ? { sedes__universidad: String(universidad) } : undefined,
  [universidad],
);

// DESPUÉS:
const initialFilters = useMemo<Record<string, string> | undefined>(
  () =>
    universidad != null ? { universidad: String(universidad) } : undefined,
  [universidad],
);
```

**Añadir `fixedValues` al `<ResourceCrud>` de coordinadores:**
```tsx
// ANTES:
<ResourceCrud
  key={universidad}
  config={config}
  initialFilters={initialFilters}
  hideHeader
  rowActions={rowActions}
/>

// DESPUÉS:
<ResourceCrud
  key={universidad}
  config={config}
  initialFilters={initialFilters}
  fixedValues={universidad != null ? { universidad } : undefined}
  hideHeader
  rowActions={rowActions}
/>
```

**Criterio de aceptación:** Al seleccionar una universidad en el gate, el listado de
coordinadores filtra correctamente por `?universidad=<id>`. El formulario de alta
pre-inyecta la universidad seleccionada (campo deshabilitado, no visible al usuario).

---

### T7 — Refactorizar `CoordinatorSedesDialog` para eliminar selector universidad y usar `useSedesDisponibles`

- [x] **T7**

**Descripción:** El dialog `components/internados/coordinator-sedes-dialog.tsx` tiene
tres problemas:

1. Estado `univSeleccionada` + selector de universidad en «Agregar sede» — ya no
   tiene sentido porque la universidad es fija en el coordinador.
2. `handleAgregarSede` envía `{ universidad: univSeleccionada, ipress: ipressSeleccionada }`.
3. El selector de IPRESS usa `ipress?es_sede_docente=true` (catálogo general) en lugar
   de `useSedesDisponibles` (sedes ya filtradas por el backend para ese coordinador
   específico).

**Cambios:**

a) Eliminar el estado `univSeleccionada` y `setUnivSeleccionada`.

b) Reemplazar el `useMemo` de `ipressParams` (que pasaba `es_sede_docente: "true"`)
   por la llamada a `useSedesDisponibles(coordinatorId)`:
```typescript
const { data: sedesDisponibles, isLoading: loadingDisponibles } =
  useSedesDisponibles(coordinatorId);
```

c) El selector de IPRESS en la sección «Agregar sede» ya no usa `<EntityCombobox>`.
   Debe renderizar un `<Select>` de shadcn poblado con `sedesDisponibles`, con
   `value={ipressSeleccionada ?? ""}` y `onValueChange={setIpressSeleccionada}`.
   Si `sedesDisponibles` está vacío y no está cargando, mostrar mensaje
   «No hay sedes disponibles para este coordinador.» y deshabilitar el botón «Agregar sede».

d) Eliminar el selector de universidad del JSX (todo el bloque `<div className="grid gap-1.5">` con `Label Universidad` y su `<EntityCombobox>`).

e) Eliminar la dependencia de `univSeleccionada` en `handleAgregarSede`:
```typescript
// ANTES:
function handleAgregarSede() {
  if (univSeleccionada == null || ipressSeleccionada == null) return;
  addSedeMutation.mutate(
    { universidad: univSeleccionada, ipress: ipressSeleccionada },
    ...
  );
}

// DESPUÉS:
function handleAgregarSede() {
  if (ipressSeleccionada == null) return;
  addSedeMutation.mutate(
    { ipress: ipressSeleccionada },
    ...
  );
}
```

f) El `tutorParams` para el selector de asignación de tutor dentro del dialog aún
   puede usar `universidad` de la prop `universidad` del dialog. Mantener ese bloque
   sin cambios (la prop `universidad: number | null` sigue siendo útil para filtrar
   tutores disponibles en la sección de asignación).

g) El botón «Agregar sede» se deshabilita si `ipressSeleccionada == null ||
   addSedeMutation.isPending || loadingDisponibles`.

**Criterio de aceptación:** El dialog «Agregar sede» no muestra selector de universidad.
El selector de IPRESS lista solo las sedes disponibles del endpoint
`/coordinators/{id}/sedes-disponibles/`. El payload POST enviado contiene únicamente
`{ ipress: string }`. Si no hay sedes disponibles, se muestra un mensaje informativo.

---

### T8 — Actualizar `docs/api-internados.md` §Coordinadores

- [x] **T8**

**Descripción:** La documentación (líneas 146–204) refleja el contrato anterior:

- §Coordinator — lectura: falta `universidad` y `universidad_detalle`; tiene `ubigeo_detalle` que el serializer no expone explícitamente (verificar y corregir).
- §CoordinatorSede — escritura: dice `universidad (req), ipress (req)` cuando desde la migración 0033 el backend solo acepta `ipress`.
- Tabla de filtros: lista `sedes__universidad` — debe ser `universidad`.
- URLs de tutores: deben usar `tutores` en lugar de `tutors`.
- Endpoint `sedes-disponibles` no está documentado.

**Cambios en la sección §Coordinadores:**

1. **Tabla de rutas:** actualizar las filas de tutores a `/sedes/{sede_pk}/tutores/`
   y `/sedes/{sede_pk}/tutores/{tutor_pk}/`; añadir fila para
   `GET /coordinators/{id}/sedes-disponibles/`.

2. **Filtros:** cambiar `sedes__universidad` → `universidad`.

3. **§Coordinator — lectura:** añadir `universidad (FK req)` y
   `universidad_detalle {id, nombre}` al bloque.

4. **§Coordinator — escritura:** añadir `universidad (req)`.

5. **§CoordinatorSede — lectura:** eliminar `universidad` del bloque de campos (no es
   un campo de primer nivel); mantener `universidad_detalle {id, nombre}`.

6. **§CoordinatorSede — escritura:** cambiar de
   `universidad (req), ipress (req)` → `ipress (req)`.

7. **Añadir sección §CoordinatorSede — sedes disponibles:**
```
### CoordinatorSede — sedes disponibles
GET /coordinators/{id}/sedes-disponibles/
Devuelve [{id: codigo_renipress, nombre}] — IPRESS con es_sede_docente=True,
con ≥1 Convenio Específico vigente para la universidad del coordinador y
que no están ya asignadas al coordinador.
```

**Criterio de aceptación:** `docs/api-internados.md` §Coordinadores refleja fielmente
el contrato real del backend (migraciones 0033+0034). Los filtros, payloads, URLs y
campos de lectura/escritura son exactamente los que el backend acepta y devuelve.

---

## 4. Criterios de aceptación globales

Tras implementar T1–T8:

1. El listado de coordinadores filtra por `?universidad=<id>` (no `sedes__universidad`).
2. El alta de coordinador envía `universidad` en el payload POST.
3. POST `/coordinators/{id}/sedes/` envía solo `{ ipress }` (sin `universidad`).
4. GET/POST/DELETE de tutores de coordinador usan la URL `/tutores/` (no `/tutors/`).
5. El dialog «Sedes» muestra las sedes disponibles del endpoint `sedes-disponibles`.
6. `CoordinatorRead.universidad` y `CoordinatorRead.universidad_detalle` existen y se
   usan en la columna «Universidad» de la tabla.
7. `CoordinatorSedeRead` no tiene campo `universidad: number` de primer nivel.
8. `docs/api-internados.md` §Coordinadores es coherente con el backend real.
9. El proyecto compila sin errores TypeScript (`npm run build` sin errores de tipo).

---

## 5. Gating por rol

Sin cambios respecto al módulo existente:
- Lectura: cualquier usuario autenticado.
- Escritura (alta/edición/eliminación de coordinadores, agregar/eliminar sedes, asignar/desasignar tutores): solo `Universidad` y `Administrador RENADS`.

---

## 6. Referencias a endpoints reales

| Endpoint | Fuente |
|----------|--------|
| `GET /coordinators/` | `views.py` línea 499; `filterset_fields` línea 514 |
| `POST /coordinators/` | `serializers.py` línea 213 (campos write) |
| `GET /coordinators/{id}/sedes/` | `views.py` línea 517 |
| `POST /coordinators/{id}/sedes/` | `views.py` línea 525–537 (acepta solo `ipress`) |
| `GET/DELETE /coordinators/{id}/sedes/{sede_pk}/` | `views.py` línea 543 |
| `GET/POST /coordinators/{id}/sedes/{sede_pk}/tutores/` | `views.py` línea 565 |
| `DELETE /coordinators/{id}/sedes/{sede_pk}/tutores/{tutor_pk}/` | `views.py` línea 590 |
| `GET /coordinators/{id}/sedes-disponibles/` | `views.py` línea 606 |

---

> **Este spec ha sido aprobado por el humano y puede pasar directamente a Implement.**
