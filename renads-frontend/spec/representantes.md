# Spec — Feature «Representantes/Autoridades multi-entidad»

> **✅ ESTADO: APROBADO (2026-09-07) — en `implement`.**
> Decisiones §8 resueltas: D2 = **eliminar `organo_directorio`** (opción A); D3-sub = **NO** cargos por entidad para no-OrganDirectory; D5 = **endpoint nuevo** `representante-content-types`; `ConventionParty` = **fuera de alcance**; B8 = verificar/añadir filtro `organo_directivo__isnull`.
> Flujo SDD: `spec` → **(APROBACIÓN HUMANA ✅)** → `implement` → `validator`.
> Este feature incluye **migración de BD en el backend** (`D:\dev\renads\renads-api`, monorepo).
> Fuentes de verdad: `docs/api-catalogos.md` §3, `docs/api-convenios.md`, `apps/convenios/{models,serializers,views,services,filters,urls}.py`.
> **Nada de este documento debe implementarse sin la aprobación humana de la lista de tareas y de las decisiones marcadas «(aprobar)».**

---

## 1. Resumen del feature

Hoy `/catalogos/representantes` («Autoridades Representantes por Entidad») solo registra
representantes de **Gobiernos Regionales**: el usuario elige un gobierno regional, la UI filtra
`organ-directories?gobierno_regional=<id>` y lista/gestiona los representantes de esos órganos. El
modelo backend `OrganRepresentative` tiene una **FK directa** `organo_directorio → OrganDirectory`
(PROTECT), por lo que solo puede apuntar a órganos del directorio.

El objetivo es **ampliar el registro de autoridades/representantes a todas las entidades del proceso
docencia-servicio**: Órganos del MINSA, Gobiernos Regionales, DIRIS, Universidades, Unidades
Ejecutoras, CONAPRES e IPRESS. Para lograrlo se migra `OrganRepresentative` a un modelo
**polimórfico** (GenericForeignKey) y se rediseña la pantalla `/catalogos/representantes` a un flujo
de **2 pasos** (tipo de entidad → entidad concreta → representantes).

### Mapa «tipo de entidad» → modelo/endpoint (7 tipos del alcance)

| Tipo UI | Modelo Django | `categoria` (si aplica) | Endpoint front | ContentType `model` |
|---------|---------------|-------------------------|----------------|---------------------|
| Órgano del MINSA | `OrganDirectory` | `ORGANO_MINSA` | `organ-directories?categoria=ORGANO_MINSA` | `organdirectory` |
| Gobierno Regional | `OrganDirectory` | `GOBIERNO_REGIONAL` | `organ-directories?categoria=GOBIERNO_REGIONAL` | `organdirectory` |
| DIRIS | `OrganDirectory` | `MINSA_DIRIS` | `organ-directories?categoria=MINSA_DIRIS` | `organdirectory` |
| Universidad | `University` | — | `universities` | `university` |
| Unidad Ejecutora | `ExecutingUnit` | — | `executing-units` | `executingunit` |
| CONAPRES | `Conapres` | — | `conapres` | `conapres` |
| IPRESS | `Ipress` | — | `ipress` | `ipress` |

> **Nota clave (verificada en `apps/convenios/models.py`):** MINSA, GORE y DIRIS son la **misma
> tabla** `OrganDirectory` discriminada por el CharField `categoria`. A nivel de `ContentType` los
> tres son el **mismo** `model=organdirectory`; se distinguen en la UI por el filtro `categoria` del
> paso 2. Por tanto los ContentTypes distintos son solo **5**: `organdirectory`, `university`,
> `executingunit`, `conapres`, `ipress`. Estos 5 coinciden exactamente con `SOLICITANTE_MODELS`
> (`apps/convenios/views.py`, `SolicitanteContentTypeView`) salvo `RegionalGovernment` (que en
> solicitante sí aparece, pero aquí GORE se modela como `OrganDirectory`).

### Pantallas que cubre

- `/catalogos/representantes` — **rediseño** a flujo de 2 pasos:
  1. **Paso 1 — Tipo de entidad** (MINSA / GORE / DIRIS / Universidad / UE / CONAPRES / IPRESS).
  2. **Paso 2 — Entidad concreta** (combobox contra el endpoint del tipo; para MINSA/GORE/DIRIS con
     filtro `categoria`).
  3. **Listado** de representantes de esa entidad + alta/edición/baja adaptados (entidad polimórfica
     + cargo global ∪ cargo por entidad).

### Fuera de alcance (NO tocar en este feature)

- **`ConventionParty`** (parte firmante de un convenio). Ver §7 (Riesgos): la parte firmante
  seguirá referenciando `organo_directorio` + `organo_representante`. **Decisión (aprobar):** este
  feature NO modifica `ConventionParty` ni el flujo de firma; se registra como trabajo futuro (una
  parte firmante que apunte a representantes de universidades/UE requiere su propio ciclo SDD).
- Tests automatizados (no hay runner configurado).
- Cambios en `documents` / `audit-logs` / otros CRUD de catálogos.

---

## 2. Estado actual (contexto verificado)

**Backend (`apps/convenios`):**
- `OrganRepresentative` (models.py ~481): FK `organo_directorio → OrganDirectory` (PROTECT,
  `related_name="representantes"`), `nombre`, `tipo_documento_identidad` (FK), `numero_documento_identidad`,
  `sexo` (M/F), `cargo_ejecutivo` (FK `ExecutivePosition`, PROTECT), `fecha_inicio_designacion`,
  `numero_resolucion_designacion` (blank), `numero_resolucion_facultades` (blank),
  `fecha_inicio_facultades` (null/blank), `activo`.
- `OrganRepresentativeHistory` (models.py ~530): snapshot de bajas con los mismos campos +
  `fecha_baja`, `motivo`, `creado_en`. **Debe evolucionar en paralelo** con el mismo esquema
  polimórfico.
- `ExecutivePosition` (models.py ~186): `organo_directivo → OrganDirectory` **nullable**,
  `nombre_masculino` (req), `nombre_femenino` (blank), `activo`; `unique_together
  (organo_directivo, nombre_masculino)`. **Ya soporta cargos globales** (org nulo).
- `OrganRepresentativeSerializer` (serializers.py ~370): `fields = "__all__"`; `validate()` chequea
  (a) unicidad de documento entre activos y (b) coherencia `cargo.organo_directivo == organo_directorio`.
- `OrganRepresentativeViewSet` (views.py ~847): `AnnexAttachmentMixin` + `AuditedModelViewSet`;
  `permission_classes = [IsAuthenticated, IsAdminRoleOrReadOnly]`; `filterset_fields =
  ["organo_directorio", "cargo_ejecutivo", "activo"]`; `search_fields = ["nombre",
  "numero_documento_identidad"]`; `annex_actor = "REPRESENTANTE"`; `perform_create` delega en el
  service.
- `services.registrar_organo_representante` (services.py ~668): baja automática del anterior activo
  del par `(organo_directorio, cargo_ejecutivo)` → snapshot en `OrganRepresentativeHistory` +
  auditoría. `_CAMPOS_SNAPSHOT_REPRESENTANTE` (~658) lista los campos copiados.
- `SolicitanteContentTypeView` (views.py ~992) + `SolicitanteContentTypeSerializer`: expone
  `[{ id, app_label, model }]` para `SOLICITANTE_MODELS` (University, Ipress, RegionalGovernment,
  ExecutingUnit, OrganDirectory, Conapres). Endpoint `GET /solicitante-content-types/`
  (urls.py ~45). **Patrón reutilizable** para resolver `ContentType.id` desde el front.
- `urls.py`: router registra `organ-representatives` (basename `organ-representative`) y
  `organ-representative-history` (~24-29).

**Frontend:**
- `app/(app)/catalogos/representantes/page.tsx`: dialog custom con `react-hook-form` (NO usa el CRUD
  declarativo). Payload actual: `nombre`, `tipo_documento_identidad`, `numero_documento_identidad`,
  `sexo`, `organo_directorio`, `cargo_ejecutivo`, `fecha_inicio_designacion`,
  `numero_resolucion_designacion`, `numero_resolucion_facultades`, `fecha_inicio_facultades`,
  `activo`. El select de cargo consulta `executive-positions?organo_directivo=<id>&activo=true`.
- `lib/catalogos/representatives.tsx` (`REPRESENTATIVES_CONFIG`): **DEAD CODE** (sin importadores;
  verificado). Ver T19.
- `lib/convenios/solicitante.ts`: consume `/solicitante-content-types/` y mapea `model →
  { label, endpoint }` (`SOLICITANTE_ENTITIES`). **Patrón a reutilizar/adaptar** para este feature.
- `lib/api/schema.d.ts`: tipos generados; se regenera con `npm run gen:api`.

---

## 3. Decisiones de diseño (APROBAR antes de Implement)

- **D1 — Modelo polimórfico con GenericForeignKey (ya decidido por el usuario).**
  `OrganRepresentative` (y `OrganRepresentativeHistory`) ganan `tipo_contenido` (FK a
  `contenttypes.ContentType`, PROTECT) + `id_objeto` (`PositiveIntegerField`) + `entidad`
  (`GenericForeignKey("tipo_contenido", "id_objeto")`).

- **D2 — Eliminar `organo_directorio` tras la data migration (limpio), NO dejar nulleable.**
  **Justificación:** (a) `organo_directorio` es la única FK obligatoria hoy; mantenerla nulleable
  crea dos fuentes de verdad y obliga a validar «uno u otro» indefinidamente; (b) la data migration
  puede poblar `tipo_contenido`/`id_objeto` de forma determinista (todas las filas actuales son
  `organdirectory`); (c) el service de baja y el snapshot pasan a operar sobre `(tipo_contenido,
  id_objeto, cargo_ejecutivo)`. **Riesgo mitigado:** `ConventionParty.organo_representante` sigue
  apuntando por PK al representante (no a `organo_directorio` del representante), así que eliminar la
  columna del representante **no rompe** la FK de la parte firmante (ver §7). **Alternativa
  descartada:** mantener nulleable «una transición» — se descarta porque no hay consumidores externos
  del campo `organo_directorio` del representante (solo la UI de esta pantalla, que se reescribe).
  > **Punto a aprobar:** confirmar que ningún reporte/PDF/consulta del backend lee
  > `OrganRepresentative.organo_directorio` directamente. Búsqueda inicial no encontró usos fuera de
  > la pantalla y el service; el agente Implement DEBE re-verificar con grep antes de borrar la
  > columna (ver T2, criterio de aceptación).

- **D3 — Cargo ejecutivo: globales ∪ por entidad (ya decidido por el usuario).**
  El selector de cargo del formulario ofrece la **unión** de: (a) cargos del órgano concreto —solo
  cuando la entidad es un `OrganDirectory` (MINSA/GORE/DIRIS)—, y (b) cargos **globales**
  (`organo_directivo` nulo, reutilizables por cualquier entidad). Para entidades que **no** son
  `OrganDirectory` (Universidad/UE/CONAPRES/IPRESS) hoy no hay FK `organo_directivo` que las enlace,
  por lo que solo aplican los **cargos globales**.
  > **Sub-decisión (aprobar):** ¿se permite además crear cargos «por entidad» para
  > Universidad/UE/CONAPRES/IPRESS? Eso exigiría que `ExecutivePosition.organo_directivo` dejara de
  > ser FK exclusiva a `OrganDirectory` (volverse polimórfica también). **Propuesta:** NO en este
  > feature — para no-OrganDirectory se usan solo cargos globales; los cargos por órgano quedan
  > restringidos a `OrganDirectory`. Registrar como trabajo futuro si se necesita.

- **D4 — Coherencia cargo↔entidad (regla de validación).** El serializer valida:
  - Si `cargo_ejecutivo.organo_directivo_id` **no es nulo** (cargo por órgano) ⇒ la entidad debe ser
    un `OrganDirectory` y `cargo.organo_directivo_id == id_objeto` (con `tipo_contenido = organdirectory`).
  - Si `cargo_ejecutivo.organo_directivo_id` **es nulo** (cargo global) ⇒ válido para cualquier
    entidad.
  (Generaliza la validación actual de `serializers.py:406-413`.)

- **D5 — Endpoint de tipos de entidad: crear `representante-content-types` (NO reutilizar
  `solicitante-content-types` tal cual).** **Justificación:** el conjunto de modelos difiere
  (representantes usa `OrganDirectory` para MINSA/GORE/DIRIS y **no** usa `RegionalGovernment`;
  solicitante sí usa `RegionalGovernment`). Reutilizar el mismo endpoint mezclaría semánticas.
  **Propuesta:** nuevo `GET /representante-content-types/` (misma forma `[{ id, app_label, model }]`,
  filtrado a los 5 modelos: `OrganDirectory`, `University`, `ExecutingUnit`, `Conapres`, `Ipress`),
  clonando el patrón de `SolicitanteContentTypeView`. El front mapea `model + categoria → label +
  endpoint` en una constante análoga a `SOLICITANTE_ENTITIES`.
  > **Alternativa (aprobar si se prefiere):** parametrizar `SolicitanteContentTypeView` con un query
  > param `contexto=representante` que cambie el set de modelos. Se descarta por claridad (dos vistas
  > pequeñas y explícitas > una vista con ramas).

- **D6 — Serializer expone `entidad_detalle` polimórfico.** Añadir
  `entidad_detalle: { tipo: <model>, id: <id_objeto>, nombre: <str(entidad)> }` (SerializerMethodField,
  read-only) para que la UI muestre la entidad sin joins manuales. El `tipo_contenido` se mantiene
  como PK (int) en escritura; `tipo_contenido_label` (read-only) opcional para debug.

- **D7 — Reescritura de la pantalla como componente custom (no CRUD declarativo).** La pantalla
  actual ya es custom por su cascada (entidad → cargo dependiente de sexo y órgano). Se mantiene
  custom, reutilizando `EntityCombobox`, `DatePicker`, `AnnexChecklistAction`, shadcn `Select/
  Dialog/AlertDialog`, `useAuthStore`/`userHasRole`, TanStack Query. No se fuerza `ResourceCrud`.

- **D8 — Idioma/convenciones.** UI/labels/comentarios en español; claves del API sin traducir
  (`tipo_contenido`, `id_objeto`, `cargo_ejecutivo`). Axios solo en `lib/api/`; server-state solo con
  TanStack Query; sin duplicar en Zustand.

---

## 4. Tareas — BACKEND (`D:\dev\renads\renads-api`)

> Escritura solo `Administrador RENADS` (autoridad final: backend). Todo cambio de contrato debe
> reflejarse en `docs/api-catalogos.md` §3 y regenerar `lib/api/schema.d.ts` en el front (T18).

- [x] **B1 — Modelo `OrganRepresentative` polimórfico.**
  En `apps/convenios/models.py`: añadir `tipo_contenido = ForeignKey(ContentType, on_delete=PROTECT,
  db_column="tipo_contenido_id", related_name="+")`, `id_objeto = PositiveIntegerField()`, y
  `entidad = GenericForeignKey("tipo_contenido", "id_objeto")`. Importar
  `django.contrib.contenttypes`. Añadir índice `(tipo_contenido, id_objeto)`. Ajustar `__str__`.
  - **Criterio:** el modelo enlaza a cualquiera de los 5 modelos; `makemigrations` genera la
    migración de esquema; no rompe imports.

- [x] **B2 — Migración de esquema + data migration + eliminación de `organo_directorio`.**
  Migración en tres pasos dentro del mismo `RunPython` o migraciones encadenadas:
  1. Agregar `tipo_contenido` (nullable temporal) + `id_objeto` (nullable temporal).
  2. **Data migration:** para cada `OrganRepresentative` existente, `tipo_contenido =
     ContentType.objects.get_for_model(OrganDirectory)`, `id_objeto = organo_directorio_id`.
     Hacer lo mismo para `OrganRepresentativeHistory` (B3).
  3. Volver `tipo_contenido`/`id_objeto` **not null** y **eliminar** la FK `organo_directorio`
     (D2). `reverse_code` que repueble `organo_directorio` desde `id_objeto` cuando
     `tipo_contenido == organdirectory` (para reversibilidad).
  - **Antes de borrar la columna:** el Implement DEBE `grep` en todo `apps/` por
    `\.organo_directorio` sobre `OrganRepresentative`/`OrganRepresentativeHistory` y confirmar que
    solo el service y el serializer/viewset la usan (todos migrados en B4-B6).
  - **Criterio:** `migrate` corre limpio en una BD con datos; toda fila queda con `tipo_contenido =
    organdirectory` + `id_objeto = <antiguo organo_directorio_id>`; la columna `organo_directorio_id`
    ya no existe; `migrate <app> <prev>` revierte sin pérdida.

- [x] **B3 — Modelo + snapshot `OrganRepresentativeHistory` polimórfico.**
  Mismos campos genéricos que B1 en `OrganRepresentativeHistory`; actualizar
  `_CAMPOS_SNAPSHOT_REPRESENTANTE` (services.py ~658) para copiar `tipo_contenido` + `id_objeto` en
  vez de `organo_directorio`. Eliminar la FK `organo_directorio` del history en la misma migración
  (B2) tras poblar.
  - **Criterio:** al dar de baja un representante, el snapshot conserva la entidad polimórfica; el
    histórico se lista igual.

- [x] **B4 — Generalizar `services.registrar_organo_representante` al par (entidad × cargo).**
  Cambiar el filtro del «anterior activo» de `(organo_directorio, cargo_ejecutivo)` a
  `(tipo_contenido, id_objeto, cargo_ejecutivo)` (services.py ~678-686). Ajustar el snapshot para
  copiar los campos genéricos.
  - **Criterio:** designar un representante para una entidad+cargo que ya tiene uno activo baja al
    anterior (mismo par entidad+cargo) y lo mueve al histórico; entidades distintas con el mismo
    cargo NO se afectan entre sí.

- [x] **B5 — Serializer `OrganRepresentativeSerializer`: campos genéricos + `entidad_detalle` +
  validación D4.**
  - Exponer `tipo_contenido` (PK, write), `id_objeto` (write), y `entidad_detalle`
    (SerializerMethodField read-only, `{ tipo, id, nombre }`, D6).
  - Reescribir `validate()` (serializers.py ~382-414): mantener unicidad de documento entre activos;
    reemplazar la coherencia cargo↔`organo_directorio` por la coherencia **D4** (cargo por órgano ⇒
    entidad debe ser ese `OrganDirectory`; cargo global ⇒ cualquiera). Validar que
    `(tipo_contenido, id_objeto)` referencia un objeto existente de uno de los 5 modelos permitidos
    (rechazar ContentTypes no permitidos con 400).
  - **Criterio:** POST con entidad+cargo coherentes crea; cargo por órgano de otro órgano → 400;
    ContentType no permitido → 400; `entidad_detalle.nombre` es el `str()` de la entidad.

- [x] **B6 — ViewSet: filtros por entidad polimórfica.**
  En `OrganRepresentativeViewSet` (views.py ~847): reemplazar `filterset_fields` `organo_directorio`
  por `tipo_contenido` + `id_objeto` (mantener `cargo_ejecutivo`, `activo`). Ajustar
  `select_related`/`prefetch` (quitar `organo_directorio`; el GFK no admite `select_related` — usar
  `prefetch_related` sobre `tipo_contenido` si aplica). Actualizar `perform_create` (sigue delegando
  en el service). Mismo cambio de filtros en `OrganRepresentativeHistoryViewSet` (`tipo_contenido`,
  `id_objeto`, `representante`).
  - **Criterio:** `GET /organ-representatives/?tipo_contenido=<id>&id_objeto=<id>&activo=true`
    devuelve solo los representantes de esa entidad; el histórico filtra igual.

- [x] **B7 — Endpoint `representante-content-types` (D5).**
  Nueva `RepresentanteContentTypeView` (clon de `SolicitanteContentTypeView`, views.py ~992) sobre
  `REPRESENTANTE_MODELS = (OrganDirectory, University, ExecutingUnit, Conapres, Ipress)`; registrar
  en `urls.py` como `GET /representante-content-types/`. Reutilizar `SolicitanteContentTypeSerializer`
  (misma forma `{ id, app_label, model }`).
  - **Criterio:** `GET /representante-content-types/` responde 200 con los 5 ContentTypes (ids reales
    de la BD); no incluye `RegionalGovernment`.

- [x] **B8 — Selector de cargos globales ∪ por entidad (soporte de datos).**
  Confirmar que `executive-positions` ya permite `organo_directivo` nulo (verificado: sí, modelo
  ~194) y que se puede filtrar por él. El front necesita dos consultas:
  (a) cargos del órgano `executive-positions?organo_directivo=<id>&activo=true` (solo OrganDirectory),
  (b) cargos globales `executive-positions?organo_directivo__isnull=true&activo=true`.
  Verificar/añadir soporte del filtro `organo_directivo__isnull` (o un alias, p. ej.
  `solo_globales=true`) en el `ExecutivePositionViewSet`/filterset.
  - **Criterio:** existe una forma documentada de listar (a) cargos por órgano y (b) cargos globales;
    ambas responden 200 con el filtro correcto. Si `__isnull` no está soportado, añadir el filtro y
    documentarlo.
  - **❓Pregunta de contrato:** ¿el `filterset` de `executive-positions` acepta hoy
    `organo_directivo__isnull`? El Implement debe verificarlo; si no, añadirlo (django-filter
    `BooleanFilter`) — **no inventar el nombre del param sin verificar**.

- [x] **B9 — Docs backend + contrato.**
  Actualizar `docs/api-catalogos.md` §3 (representantes): campos nuevos (`tipo_contenido`,
  `id_objeto`, `entidad_detalle`), filtros nuevos (`tipo_contenido`, `id_objeto`), baja de
  `organo_directorio`, nuevo endpoint `representante-content-types`, y la regla D4. Actualizar
  `docs/api-convenios.md` si menciona `OrganRepresentative.organo_directorio`.
  - **Criterio:** la doc describe el modelo polimórfico y no menciona `organo_directorio` como campo
    del representante; el nuevo endpoint aparece documentado.

---

## 5. Tareas — FRONTEND (`D:\dev\renads\renads-frontend`)

- [x] **T1 — Regenerar tipos OpenAPI.** Tras B1-B8 mergeados en el backend vivo, ejecutar
  `npm run gen:api` para actualizar `lib/api/schema.d.ts` (`OrganRepresentative` con
  `tipo_contenido`/`id_objeto`/`entidad_detalle`; nuevo path `representante-content-types`).
  - **Criterio:** `schema.d.ts` refleja los campos nuevos; `npx tsc --noEmit` compila.

- [x] **T2 — Módulo de datos `lib/catalogos/representantes-entities.ts` (patrón `solicitante.ts`).**
  - Tipo `RepresentanteContentType { id; app_label; model }`.
  - `listRepresentanteTypes()` → `GET /representante-content-types/`.
  - Constante `REPRESENTANTE_ENTITIES: EntityTypeOption[]` con las **7** opciones de UI (mapeando
    `model + categoria → { key, label, endpoint, params }`):
    - MINSA → `{ label: "Órgano del MINSA", model: "organdirectory", endpoint: "organ-directories", params: { categoria: "ORGANO_MINSA" } }`
    - GORE → `{ label: "Gobierno Regional", model: "organdirectory", endpoint: "organ-directories", params: { categoria: "GOBIERNO_REGIONAL" } }`
    - DIRIS → `{ label: "DIRIS", model: "organdirectory", endpoint: "organ-directories", params: { categoria: "MINSA_DIRIS" } }`
    - Universidad → `{ label: "Universidad", model: "university", endpoint: "universities" }`
    - Unidad Ejecutora → `{ label: "Unidad Ejecutora", model: "executingunit", endpoint: "executing-units" }`
    - CONAPRES → `{ label: "CONAPRES", model: "conapres", endpoint: "conapres" }`
    - IPRESS → `{ label: "IPRESS", model: "ipress", endpoint: "ipress" }`
  - Helper `resolveTipoContenidoId(model, types)` que resuelve el `ContentType.id` a partir del
    `model` (los 3 de OrganDirectory comparten el mismo id).
  - **Criterio:** el módulo compila; expone las 7 opciones y resuelve el `ContentType.id` para cada
    una a partir de la respuesta del endpoint; sin Axios fuera de `lib/api/` (usar `api` de
    `lib/api/client`).

- [x] **T3 — Hooks TanStack Query del feature.**
  - `useRepresentanteTypes()` — query de `/representante-content-types/` (`staleTime` alto; los ids
    no cambian).
  - `useRepresentativesByEntity(tipoContenidoId, idObjeto)` — lista
    `organ-representatives?tipo_contenido=<>&id_objeto=<>` (paginada; puede usar `fetchAllPages`
    existente o el hook de recurso). `enabled` solo con ambos ids.
  - `useExecutivePositions({ organoDirectivoId })` — devuelve **globales ∪ por órgano**: dispara (a)
    `?organo_directivo=<id>&activo=true` (solo si hay órgano) + (b) `?organo_directivo__isnull=true&
    activo=true`, y fusiona resultados sin duplicar por `id`.
  - Mutations: `createRepresentative`, `updateRepresentative`, `deleteRepresentative` con
    invalidación de la lista por entidad.
  - **Criterio:** cambiar de entidad refresca la lista; crear/editar/eliminar invalida y refresca sin
    recarga; el select de cargo muestra globales + (si aplica) los del órgano.

- [x] **T4 — Rediseño de la pantalla `/catalogos/representantes` (2 pasos).**
  Reescribir `app/(app)/catalogos/representantes/page.tsx`:
  - **Paso 1 — Tipo de entidad:** `Select` shadcn con las 7 opciones de `REPRESENTANTE_ENTITIES`.
    Al cambiar, resetea el paso 2 y la búsqueda.
  - **Paso 2 — Entidad concreta:** `EntityCombobox` contra `opt.endpoint` con `params: opt.params`
    (p. ej. `categoria` para MINSA/GORE/DIRIS). Deshabilitado hasta elegir tipo.
  - **Listado:** tabla de representantes de esa entidad. Columnas: `entidad_detalle.nombre` (o la
    entidad seleccionada), `nombre`, `cargo` (resuelto con género, patrón `resolveCargoLabel`
    actual), `fecha_inicio_designacion`, `numero_resolucion_designacion`, `activo`, acciones
    (editar / `AnnexChecklistAction entidad="organ-representatives"` / eliminar).
  - Buscador cliente por `nombre`/`numero_documento_identidad` (como hoy) o server-side vía `search`.
  - **Gating:** «Nuevo/Editar/Eliminar» solo `userHasRole(user, "Administrador RENADS")`.
  - **Criterio:** con cualquiera de los 7 tipos, elegir una entidad concreta lista sus representantes;
    el título/subtítulo dejan de decir «gobierno regional» y hablan de «entidad»; un no-Admin ve solo
    lectura.

- [x] **T5 — Diálogo alta/edición polimórfico + cargo global∪entidad.**
  Adaptar `RepresentativeDialog`:
  - En vez de recibir `gobRegId`, recibe `{ model, tipoContenidoId, idObjeto, esOrganDirectory }` de
    la entidad seleccionada en el paso 2.
  - El payload de create/update usa `tipo_contenido` (= `tipoContenidoId`) + `id_objeto` (= `idObjeto`)
    en lugar de `organo_directorio`. Resto de campos igual (`nombre`, `tipo_documento_identidad`,
    `numero_documento_identidad`, `sexo`, `cargo_ejecutivo`, `fecha_inicio_designacion`,
    `numero_resolucion_designacion`, `numero_resolucion_facultades`, `fecha_inicio_facultades`,
    `activo`).
  - **Selector de cargo (D3):** usa `useExecutivePositions({ organoDirectivoId: esOrganDirectory ?
    idObjeto : undefined })` → globales ∪ (si OrganDirectory) por órgano. El label respeta el género
    (`nombre_masculino`/`nombre_femenino` según `sexo`). Deshabilitado hasta elegir `sexo`.
  - **Criterio:** crear un representante de una Universidad/UE/CONAPRES/IPRESS funciona usando cargos
    globales; crear uno de un OrganDirectory ofrece globales + cargos del órgano; el POST envía
    `tipo_contenido`/`id_objeto` (verificable en Network) y NO envía `organo_directorio`; edición
    precarga la entidad (solo lectura en el diálogo, no re-elegible) y el cargo.

- [x] **T6 — Coherencia de errores del backend.** Mostrar los 400 de D4/unicidad vía
  `extractApiError` (toast). El diálogo no re-implementa la validación de coherencia (la autoridad es
  el backend), pero SÍ evita ofrecer cargos incoherentes (solo muestra globales ∪ por órgano).
  - **Criterio:** un intento incoherente (si ocurriera) muestra el mensaje del backend; el caso feliz
    no dispara 400 de coherencia.

- [x] **T7 — Limpieza de `lib/catalogos/representatives.tsx` (dead code).**
  **Decisión (aprobar):** **eliminar** `REPRESENTATIVES_CONFIG` (sin importadores; su forma no sirve
  para el flujo polimórfico de 2 pasos). Verificar con grep que nadie lo importa antes de borrar.
  - **Criterio:** el archivo se elimina (o queda vacío/reexport); `npx tsc --noEmit` y `npm run lint`
    siguen limpios; no hay imports rotos.

- [x] **T8 — Actualizar `lib/convenios/solicitante.ts` si procede (NO duplicar).**
  No modificar la semántica de solicitante; solo confirmar que `SOLICITANTE_ENTITIES` y
  `REPRESENTANTE_ENTITIES` conviven sin colisión (dos constantes distintas, dos endpoints distintos).
  - **Criterio:** ninguna regresión en el flujo de convenio (solicitante sigue igual).

- [x] **T9 — Docs front + `CLAUDE.md`.**
  - `CLAUDE.md`: actualizar la fila de `organ-representatives` (modelo polimórfico; entidad genérica;
    endpoint `representante-content-types`; cargos globales) y añadir una fila a la tabla «Refactors
    de backend aplicados al frontend» con fecha.
  - **Criterio:** `CLAUDE.md` describe el nuevo modelo y la pantalla de 2 pasos; `docs/api-catalogos.md`
    §3 (T/B9) queda consistente con el front.

- [x] **T10 — Verificación final.**
  `npx tsc --noEmit` y `npm run lint` limpios. Smoke manual (rol `Administrador RENADS`):
  registrar un representante para cada uno de los 7 tipos (MINSA/GORE/DIRIS/Universidad/UE/CONAPRES/
  IPRESS); verificar en Network que el POST envía `tipo_contenido`/`id_objeto` correctos y que el
  cargo seleccionado es global o por órgano según el tipo; comprobar baja automática al re-designar el
  mismo par entidad+cargo; con rol no-Admin, solo lectura.
  - **Criterio:** cero errores TS/ESLint; los 7 flujos responden 2xx; la baja automática funciona por
    entidad; el gating UX es correcto.

---

## 6. Reglas de negocio / validación (RN)

| RN | Descripción | Dónde vive |
|----|-------------|------------|
| RN-R1 | Un representante enlaza a **una** entidad de los 5 modelos permitidos (`OrganDirectory`, `University`, `ExecutingUnit`, `Conapres`, `Ipress`) vía `tipo_contenido` + `id_objeto`. ContentType fuera de esa lista → 400. | Backend (B5) |
| RN-R2 | **Coherencia cargo↔entidad (D4):** cargo por órgano ⇒ entidad debe ser ese `OrganDirectory`; cargo global ⇒ cualquier entidad. | Backend (B5) + UX (T5) |
| RN-R3 | **Unicidad del representante vigente por (entidad × cargo):** designar un nuevo representante para un par `(tipo_contenido, id_objeto, cargo_ejecutivo)` con uno activo baja al anterior (snapshot a history, `fecha_baja=hoy`). | Backend (B4) |
| RN-R4 | **Unicidad de documento entre activos:** no dos representantes activos con el mismo `(tipo_documento_identidad, numero_documento_identidad)`. (Se conserva de hoy.) | Backend (B5) |
| RN-R5 | Cargos disponibles en el form = **globales ∪ (por órgano si OrganDirectory)**. | UX (T3/T5) |
| RN-R6 | Escritura solo `Administrador RENADS`; lectura para miembro institucional autenticado. | Backend + UX gating |

---

## 7. Riesgos y puntos de atención

- **R1 — `ConventionParty` (fuera de alcance, verificar impacto).** `ConventionParty`
  (models.py ~894) referencia `organo_representante → OrganRepresentative` (por PK) y **por separado**
  `organo_directorio → OrganDirectory`. Eliminar `OrganRepresentative.organo_directorio` (D2) **no**
  afecta a `ConventionParty.organo_directorio` (son campos distintos, en tablas distintas). **Riesgo
  real:** si en algún punto el flujo de firma asume que el representante «pertenece» a un
  `OrganDirectory` vía el campo eliminado, habría que leerlo por `entidad`. El Implement DEBE grep en
  `services.py`/`serializers.py` por usos de `organo_representante.organo_directorio`. **Decisión:**
  este feature NO amplía `ConventionParty` a representantes de universidades/UE (queda para otro
  ciclo).
- **R2 — Borrado PROTECT.** `OrganRepresentative` es referenciado con PROTECT por
  `ConventionParty.organo_representante` y por `OrganRepresentativeHistory.representante`. Eliminar un
  representante usado por una parte/historial devuelve 409 (`ProtectedDeleteConflict`); el front ya lo
  maneja con `extractApiError`. Mantener ese manejo en T4/T6.
- **R3 — ContentType ids dependientes de la BD.** Nunca hardcodear `tipo_contenido` en el front;
  resolver siempre vía `/representante-content-types/` (T2). Los 3 tipos de OrganDirectory comparten
  el **mismo** `ContentType.id` (se distinguen por `categoria` en el filtro del paso 2, no por
  ContentType).
- **R4 — Data migration en producción.** La migración debe ser idempotente y reversible; correrla en
  una copia con datos antes de mergear. Verificar que no queden filas con `id_objeto` huérfano.
- **R5 — `executive-positions` filtro `__isnull`.** Si el filterset no soporta `organo_directivo__isnull`
  (B8), añadirlo; no asumir el nombre del param sin verificar el filterset real.
- **R6 — Orden de despliegue.** El backend (B1-B9) debe estar mergeado y migrado **antes** de
  `npm run gen:api` (T1) y del resto del front; de lo contrario los tipos y endpoints no existen.

---

## 8. Preguntas abiertas para la aprobación humana

1. **D2 — eliminación limpia de `organo_directorio`** (vs. nulleable transitorio): confirmar. La
   recomendación es eliminación limpia con data migration reversible (justificada en §3).
2. **D3 sub-decisión** — ¿permitir cargos «por entidad» también para Universidad/UE/CONAPRES/IPRESS
   (haría `ExecutivePosition.organo_directivo` polimórfico)? Propuesta: **NO** en este feature (solo
   cargos globales para no-OrganDirectory).
3. **D5** — ¿nuevo endpoint `representante-content-types` (propuesto) o parametrizar
   `solicitante-content-types`? Propuesta: endpoint nuevo.
4. **Alcance `ConventionParty`** — confirmar que queda **fuera** de este feature (R1).
5. **B8** — confirmar/añadir el filtro `organo_directivo__isnull` en `executive-positions`.

---

> **Recordatorio: este spec requiere APROBACIÓN HUMANA antes de pasar al agente `implement`.**
> Marcar las decisiones §3 (D1-D8) y resolver §8 antes de codificar. El orden es backend
> (B1-B9, con migración probada sobre datos) → `npm run gen:api` (T1) → frontend (T2-T10).
