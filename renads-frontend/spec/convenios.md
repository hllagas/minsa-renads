# Spec — Módulo `convenios` (Gestionar Convenios)

Módulo 2 del MVP (`docs/mvp.md`). CRUD + flujo del ciclo de vida de convenios Marco/Específicos.
Contrato del backend: **`docs/api-convenios.md`** (endpoints, métodos, campos read/write, roles por
acción, catálogos). Estructura/convenios de stack: `docs/frontend-conventions.md`, `CLAUDE.md`.

> **Estado:** ✅ **MÓDULO CERRADO.** Implementado en 2 pases (Pase 1 = Bloques 0–2; Pase 2 = Bloque 3
> flujo), validado sin errores. Ver `spec/convenios.validacion.md` y `spec/convenios.guia_pruebas.md`.
> Deuda saldada: combobox server-side. Pendiente futuro: selector de solicitante/firmante polimórfico
> (requiere endpoint de ContentTypes inexistente).

## Resumen / pantallas
- **Lista** de convenios (`/convenios`): `<DataTable>` con filtros del backend, paginación, búsqueda.
- **Detalle** (`/convenios/[id]`): datos + pestañas de flujo (campos clínicos, participantes, historial) + acciones por rol.
- **Alta/edición** (`/convenios/nuevo`, `/convenios/[id]/editar`): formulario rhf+zod.
- **Acciones de flujo**: cambiar-estado, evaluación técnica, opinión CONAPRES, campos clínicos, opinión jurídica, firma, publicación, participantes (cada una restringida por rol).
- **Maestros** (entidades) y **catálogos** como apoyo: catálogos = selects de solo lectura; entidades organizacionales/académicas = CRUD (escritura solo `Administrador RENADS`).

## Reglas de negocio relevantes para UX/validación (de `docs/api-convenios.md`)
- Convenio **Específico** exige **Convenio Marco vigente** (`VIGENTE`/`PUBLICADO`/`SUSCRITO`).
- CONAPRES y campos clínicos **solo** para Específicos.
- No permitir disparar **firma** si hay observaciones pendientes (la UI advierte; el backend bloquea).
- `fecha_fin` la calcula el backend → **no** enviarla ni editarla.
- `solicitante` es polimórfico: `solicitante_tipo_contenido` (id ContentType) + `solicitante_id_objeto`.

---

## Bloque 0 — Infraestructura del módulo

- [x] **T0.1 Tipos desde OpenAPI.** Agregar `openapi-typescript` (dev) y un script `gen:api`
  (`openapi-typescript http://localhost:8000/api/v1/schema/ -o lib/api/schema.d.ts`). Generar
  `lib/api/schema.d.ts`. Evita tipar a mano las ~30 entidades/catálogos. Claves en español se
  preservan automáticamente.
  - **Criterio:** `schema.d.ts` generado; tipos de `Convention`, catálogos y entidades disponibles.
- [x] **T0.2 Helpers de query reutilizables** (`lib/api/query.ts`): helper para listas paginadas DRF
  (`Paginated<T>` ya en `lib/api/client.ts`) y para construir query params (page, ordering, search,
  filtros). Hook genérico `usePaginatedQuery` o convención de keys por recurso.
  - **Criterio:** un patrón único para listas con filtros/paginación reutilizable por los CRUD.
- [x] **T0.3 Componentes de apoyo** (en `components/`): `DataTablePagination` (controles prev/next +
  conteo), un `Combobox`/`Select` que carga un catálogo por hook (para FKs), y `PageHeader`.
  - **Criterio:** reutilizables por convenios y por los módulos siguientes.

## Bloque 1 — Catálogos y entidades de apoyo

- [x] **T1.1 Hooks de catálogos** (`lib/convenios/catalogos.ts`): hooks de solo lectura para los
  catálogos usados como selects (al menos `convention-types`, `convention-statuses`, `specialties`,
  `academic-levels`, `regions`, `document-types`, y razones de observación/rechazo/cierre). Filtro
  `activo=true`. Cache larga (catálogos cambian poco).
  - **Criterio:** un select de convenio puede poblarse desde el catálogo real.
- [x] **T1.2 API + hooks de entidades** (`lib/convenios/entidades.ts`): funciones CRUD y hooks para
  las entidades que el alta de convenios necesita como FK/solicitante: `universities`, `ipress`,
  `faculties`, `professional-careers`, `regional-governments`, `executing-units`, `minsa-organs`,
  `conapres`. Reutilizar el patrón de listas paginadas (T0.2).
  - **Criterio:** listar/crear/editar/eliminar una entidad (p. ej. `universities`) funciona contra el backend.
- [x] **T1.3 UI de maestros** (`/convenios/maestros/...` o sección admin): CRUD (lista `<DataTable>` +
  alta/edición) para el conjunto acordado: **`universities`, `ipress`, `regional-governments`,
  `executing-units`, `regional-organs`, `minsa-organs`, `conapres`**. Las entidades académicas
  (`faculties`, `professional-careers`, `university-authorities`, `university-campuses`) se difieren a
  un pase posterior, pero sus **hooks de lectura** deben existir si algún select los necesita.
  - **Criterio:** CRUD visible de las 7 entidades acordadas; escritura gateada a `Administrador RENADS`;
    respeta los FK/filtros de cada una (ver `docs/api-convenios.md`).

## Bloque 2 — Convenios (núcleo CRUD)

- [x] **T2.1 API layer** (`lib/convenios/api.ts`): `listConventions(params)`, `getConvention(id)`,
  `createConvention(data)`, `updateConvention(id, data)`, `deleteConvention(id)` → recurso
  `conventions`. Tipos de `schema.d.ts`. Payload de escritura según `ConventionWriteSerializer`.
- [x] **T2.2 Hooks** (`lib/convenios/hooks.ts`): `useConventions(filters)`, `useConvention(id)`,
  `useCreateConvention`, `useUpdateConvention`, `useDeleteConvention` (con invalidación de keys).
- [x] **T2.3 Lista** (`app/(app)/convenios/page.tsx`): `<DataTable>` con columnas (código, título,
  tipo, estado, fechas), filtros backend (`tipo_convenio`, `estado_actual`, `convenio_marco`, rangos
  de fecha), búsqueda (`titulo`/`codigo`), orden y paginación. Botón "Nuevo" gateado.
  - **Criterio:** la tabla refleja datos reales, filtra/pagina vía backend (no en cliente).
- [x] **T2.4 Alta/edición** (`convenios/nuevo`, `convenios/[id]/editar`): formulario rhf+zod con los
  campos de escritura; selects de catálogos/entidades (T1); `solicitante` polimórfico (selector de
  tipo + entidad). **No** exponer `fecha_fin`, `estado_actual`, `creado_por`. Validar RN-3 en UX
  (si tipo=Específico, exigir `convenio_marco`).
  - **Criterio:** crear y editar un convenio funciona; errores del backend se muestran al usuario.
- [x] **T2.5 Detalle** (`convenios/[id]/page.tsx`): muestra datos legibles (tipo, estado, solicitante)
  y enlaza a editar + acciones de flujo (Bloque 3).
  - **Criterio:** el detalle carga vía `useConvention` y muestra `estado_codigo`/`estado_actual`.

## Bloque 3 — Flujo del convenio (acciones por rol)

- [x] **T3.1 API + hooks de acciones**: una mutation por acción contra los sub-endpoints de
  `conventions/{id}/...`: `cambiar-estado`, `evaluacion-tecnica`, `opinion-conapres`,
  `campos-clinicos` (GET+POST), `opinion-juridica`, `firma`, `publicacion`, `participantes`
  (GET+POST), `historial` (GET). Invalidar el detalle al mutar.
- [x] **T3.2 UI de acciones**: en el detalle, botones/diálogos (shadcn `dialog`/`form`) por acción,
  **cada uno visible solo para su rol** (ver tabla de roles en `docs/api-convenios.md`): evaluación
  técnica→`DIGEP`; opinión CONAPRES y campos clínicos→`CONAPRES`; opinión jurídica→`OGAJ`;
  firma/publicación→`Secretaría General`; cambiar-estado/participantes→`Administrador RENADS`.
  Usar `userHasRole`.
- [x] **T3.3 Pestañas**: `campos-clinicos`, `participantes`, `historial` como listas (`<DataTable>` o
  lista) en el detalle. Campos clínicos/CONAPRES solo si el convenio es Específico.
  - **Criterio:** cada acción dispara su endpoint, respeta el rol, refresca el detalle; las pestañas
    muestran datos reales.

## Bloque 4 — Verificación
- [x] **T4.1** `npm run lint` y `npm run build` limpios.
- [x] **T4.2** El validador deja `spec/convenios.validacion.md` y, si OK, `spec/convenios.guia_pruebas.md`.

---

## Criterios de aceptación del módulo (de `docs/mvp.md`)
- CRUD de convenios + entidades funciona contra el backend real.
- Las acciones de flujo respetan el rol (UI oculta; backend autoriza).
- Las tablas usan filtros/paginación del backend.
- Los selects se alimentan de catálogos reales.

## Decisiones (resueltas)
1. **Tipos:** generar de OpenAPI (`openapi-typescript`, T0.1). ✅
2. **Alcance de maestros (CRUD UI ahora):** `universities`, `ipress`, `regional-governments`,
   `executing-units`, `regional-organs`, `minsa-organs`, `conapres`. Académicas y demás → pase
   posterior (solo hooks de lectura si hacen falta). ✅
3. **Pases de implementación:** dividir en 2 — Pase 1 = Bloques 0–2; Pase 2 = Bloque 3 (flujo). ✅

## Fuera de alcance
- Generación/preview real de PDF de convenios (el backend solo guarda `referencia_externa`).
- Reportes/exportación. Tests automatizados.

## Referencias
- Endpoints/campos/roles: `docs/api-convenios.md`.
- Roles y alcance institucional: `docs/backend-overview.md`, `docs/api-auth.md`.
- Stack y patrones (DataTable, Query, Axios, Zustand): `CLAUDE.md`, `docs/frontend-conventions.md`.
- Reutilizar del módulo Auth: `lib/api/client.ts`, hooks/patrón de `lib/auth/`, `<DataTable>`, `userHasRole`.
