# Spec — Feature «OrganDirectory: FK `organo` (reemplaza `categoria`) + unicidad por (organo, gobierno_regional, nombre)»

> **✅ ESTADO: APROBADO (2026-09-07) — en `implement`.**
> Decisiones §8: P1=`Organ.nombre` tal cual; P2=`organo__nombre`+validación front; P3=renombrar clave `categoria`→`organo`; P4=implement verifica `EntityCombobox`/`ResourceForm`; P5=fallar ante colisiones (no dedupe auto).
> Flujo SDD: `spec` → **(APROBACIÓN HUMANA ✅)** → `implement` → `validator`.
> Este feature incluye **migración de BD en el backend** (`D:\dev\renads\renads-api`, monorepo).
> Fuentes de verdad: `docs/api-catalogos.md` §2, `apps/convenios/{models,serializers,views,pdf,filters,urls}.py`,
> `lib/convenios/entities.ts`, `lib/catalogos/representantes-entities.ts`.
> **Nada de este documento debe implementarse sin la aprobación humana de la lista de tareas y de las decisiones §3.**

---

## 1. Resumen del feature

Hoy `OrganDirectory` (directorio unificado: órganos del MINSA, Universidades, Gobiernos Regionales,
DIRIS, Unidades Ejecutoras) se discrimina por un **CharField `categoria`** con choices
`ORGAN_DIRECTORY_CATEGORY` (`models.py:158-164`, `models.py:312`). Además, una `UniqueConstraint`
parcial (`uniq_organo_directorio_por_gore`, migración 0037) exige **un solo órgano por
`gobierno_regional`**.

El objetivo es doble:

1. **Reemplazar el CharField `categoria` por una FK `organo → Organ`** (tabla `organo` ya existente,
   5 filas canónicas — `models.py:167`). El manejo pasa a ser **por id**, no por texto.
2. **Cambiar la regla de unicidad** de «uno por GORE» a **único por `(organo, gobierno_regional,
   nombre)`**: un GORE puede tener varios órganos del directorio siempre que difieran en `organo`
   y/o `nombre`.

### Pantallas / superficies que cubre

- **Backend:** modelo, migración+data migration, serializer (validación + `organo_detalle`), viewset
  (filterset + detalle), `pdf.py` (selección de plantilla), `_detalle_organo_directorio` (afecta
  `executive-positions.organo_directivo_detalle`), `limit_choices_to` de `University.tipo_entidad` y
  `ExecutingUnit.tipo_organo`.
- **Frontend:** `/catalogos/entidades/organ-directories` (columna/filtro/campo `categoria` →
  `organo`), selects de `University.tipo_entidad` y `ExecutingUnit.tipo_organo` (hoy con
  `optionsParams:{categoria:...}`), pantalla `/catalogos/representantes` (hoy `params:{categoria:...}`),
  util nuevo de resolución de id de `Organ`.

### Fuera de alcance (NO tocar)

- **`Ipress.categoria`** (`lib/convenios/entities.ts` líneas ~202,264) — es una FK **distinta** a
  `Category` (catálogo de categorías de establecimiento), no tiene relación con `OrganDirectory.categoria`.
- `executive-positions.organo_directivo` (FK a `OrganDirectory`, no a categoría) — no cambia su
  contrato; solo cambia el **contenido** de su `*_detalle` (ver B6).
- Tests automatizados (no hay runner configurado).

---

## 2. Estado actual (contexto verificado)

### Backend (`apps/convenios`)

- **`ORGAN_DIRECTORY_CATEGORY`** (`models.py:158-164`): choices `ORGANO_MINSA | UNIVERSIDAD |
  GOBIERNO_REGIONAL | MINSA_DIRIS | UNIDAD_EJECUTORA` con labels display.
- **`Organ`** (`models.py:167-183`): tabla `organo`, campos `nombre` + `estado` (bool). 5 filas
  canónicas. **Solo lectura** vía endpoint `organs` (`views.py:755`, filterset `estado`, search
  `nombre`).
- **`OrganDirectory`** (`models.py:304-341`): CharField `categoria` (choices), FK opcional
  `gobierno_regional → RegionalGovernment` (PROTECT, `related_name="organos_directorio"`), `nombre`,
  `siglas`, `activo`. `Meta.constraints` = `[uniq_organo_directorio_por_gore]`
  (`UniqueConstraint(fields=["gobierno_regional"], condition=Q(gobierno_regional__isnull=False))`).
- **`University.tipo_entidad`** (`models.py:619-623`): FK a `OrganDirectory`,
  `limit_choices_to={"categoria": "UNIVERSIDAD"}`.
- **`ExecutingUnit.tipo_organo`** (`models.py:347-351`): FK a `OrganDirectory`,
  `limit_choices_to={"categoria": "UNIDAD_EJECUTORA"}`.
- **`_detalle_organo_directorio`** (`views.py:447-449`): `{id, nombre, categoria: rel.get_categoria_display()}`
  — usado en `executive-positions.organo_directivo_detalle` (`views.py:765`).
- **`_OrganDirectorySerializer`** (`views.py:690-722`): auto-serializer con `detalles={"gobierno_regional":
  _detalle_nombre}`; `validate()` implementa la RN «uno por GORE» y devuelve 400 en `gobierno_regional`.
- **`OrganDirectoryViewSet`** (`views.py:725-736`): `filterset_fields=["categoria", "gobierno_regional",
  "activo"]`, `search_fields=["nombre", "siglas"]`, `detalles={"gobierno_regional": _detalle_nombre}`,
  `queryset.select_related("gobierno_regional")`.
- **`pdf.py:_seleccionar_plantilla`** (`pdf.py:209-235`): **load-bearing** — mapea
  `(tipo_convenio.codigo, categoria)` → nombre de `.docx`. Lee
  `getattr(convenio.organo_directorio, "categoria", "")` (línea 220). Mapa usa los **codes** de
  categoría (`MINSA_DIRIS`, `GOBIERNO_REGIONAL`). Si queda mal, se rompe la generación de PDF.
- **Comentarios** que mencionan `categoria` en `views.py:1027`/`1044` (endpoint
  `representante-content-types`; NO usa `categoria` en lógica — es texto de comentario que hay que
  actualizar). **La validación de representantes usa `tipo_contenido.model=="organdirectory"`
  (ContentType), NO `categoria`** — no se ve afectada (confirmar con grep en B: ver T-VERIF).

### Mapeo `categoria code → Organ` (verificado en BD dev — los nombres NO coinciden con los labels de categoría)

| `categoria` code | `Organ.nombre` (en BD) | `Organ.id` (dev) |
|------------------|------------------------|------------------|
| `ORGANO_MINSA` | `MINSA Administrativo` | 1 |
| `UNIVERSIDAD` | `Universidad` | 2 |
| `GOBIERNO_REGIONAL` | `Gobierno Regional` | 3 |
| `UNIDAD_EJECUTORA` | `Unidad Ejecutora` | 4 |
| `MINSA_DIRIS` | `MINSA DIRIS` | 5 |

> **Los ids son de la BD dev y NO deben hardcodearse** (ni en migración ni en front). La data
> migration mapea por **`Organ.nombre`**; el front resuelve el id dinámicamente vía el endpoint
> `organs`.

### Frontend

- **`lib/convenios/entities.ts`**:
  - `ORGAN_DIRECTORY_CATEGORY` (líneas 59-65) + `categoriaLabel()` (67-70).
  - `organ-directories` config (442-496): columna `categoria` con `categoriaLabel`, filtro `categoria`
    (`choices: ORGAN_DIRECTORY_CATEGORY`), campo `categoria` (select con `choices`).
  - `universities.tipo_entidad`: filtro (líneas 120-126) y campo (151-158) con
    `optionsEndpoint:"organ-directories", optionsParams:{categoria:"UNIVERSIDAD"}`.
  - `executing-units.tipo_organo`: filtro (392-398) y campo (416-423) con
    `optionsEndpoint:"organ-directories", optionsParams:{categoria:"UNIDAD_EJECUTORA"}`.
  - **`ipress.categoria`** (líneas 202, 264): FK a `Category` — **NO tocar**.
- **`lib/catalogos/representantes-entities.ts`**: `REPRESENTANTE_ENTITIES` (32-85); los 3 tipos de
  OrganDirectory usan `params:{categoria:"ORGANO_MINSA"|"GOBIERNO_REGIONAL"|"MINSA_DIRIS"}` (líneas
  38, 45, 53). El campo `params` alimenta el filtro del combobox del paso 2.
- **`lib/api/schema.d.ts`**: tipos generados; se regeneran con `npm run gen:api`.
- **`docs/api-catalogos.md`**: §2 tabla de filtros (`organ-directories`: `categoria` — línea 94), y
  §«`organ-directories` — campo `categoria`» (líneas 108-120+).

---

## 3. Decisiones de diseño (ya tomadas por el usuario — no re-preguntar)

- **D1 — Reemplazar `categoria` por FK `organo` (opción B).** Eliminar el CharField `categoria`;
  añadir `organo = ForeignKey(Organ, on_delete=PROTECT, db_column="organo_id")` (NOT NULL tras data
  migration). Manejar por **id**, no por texto.
- **D2 — Unicidad = `(organo, gobierno_regional, nombre)`, con caso NULL.** Dos `UniqueConstraint`
  parciales:
  - `UniqueConstraint(fields=["organo","gobierno_regional","nombre"], condition=Q(gobierno_regional__isnull=False), name="uniq_organo_dir_organo_gore_nombre")`
  - `UniqueConstraint(fields=["organo","nombre"], condition=Q(gobierno_regional__isnull=True), name="uniq_organo_dir_organo_nombre_sin_gore")`
  - **Eliminar** la constraint anterior `uniq_organo_directorio_por_gore` (0037).
- **D3 — Comparación de nombre EXACTA** (tal cual se guarda; sin normalizar mayúsculas/espacios).
  Coincide con el resto de catálogos y con la comparación que hará la BD en la `UniqueConstraint`.
- **D4 — Front por id puro (B2).** El front **NO** hardcodea ids ni usa `?categoria=`. Resuelve
  dinámicamente el id de `Organ` (fetch al endpoint de solo lectura `organs`, mapa por `nombre`) y
  filtra con `?organo=<id>`. Aplica a **todas** las pantallas que hoy usan `?categoria=` o
  `optionsParams:{categoria:...}`.
- **D5 — Display del label en la UI (decidido dentro de este spec):** dado que `Organ.nombre` **no
  coincide** con los labels de categoría (`MINSA Administrativo` ≠ `Órgano del MINSA`), la columna
  y el select de `organo` en `organ-directories` mostrarán **`organo_detalle.nombre`** (el nombre
  real de `Organ`, tal cual está en BD). No se mantiene un mapa de display alternativo en el front:
  la fuente de verdad del label es `Organ.nombre`. (Ver §7 R6 y §8 P1 por si el usuario prefiere un
  mapa de display.)

---

## 4. Tareas — BACKEND (`D:\dev\renads\renads-api`)

> Escritura solo `Administrador RENADS` (autoridad final: backend). Todo cambio de contrato debe
> reflejarse en `docs/api-catalogos.md` §2 y regenerar `lib/api/schema.d.ts` en el front (T1).
> **Orden obligatorio dentro de la migración:** add nullable `organo` → data migration
> (`categoria`→`Organ` por nombre) → verificación/dedupe de colisiones → set NOT NULL →
> drop `categoria` → drop constraint 0037 → add 2 constraints nuevas.

- [x] **B0 — Verificación previa de blast radius (grep antes de tocar).**
  Antes de cualquier cambio, `grep` en todo `apps/` por usos de `OrganDirectory.categoria` /
  `.categoria` / `get_categoria_display` / `"categoria"` / `ORGAN_DIRECTORY_CATEGORY` que involucren
  `OrganDirectory`. Confirmar explícitamente:
  - `pdf.py:220` (selección de plantilla) — **debe** remapearse (B7).
  - `views.py:447-449` (`_detalle_organo_directorio`) — **debe** cambiar (B6).
  - `views.py:728` (filterset) — **debe** cambiar (B6).
  - `University.tipo_entidad` (`models.py:621`) y `ExecutingUnit.tipo_organo` (`models.py:349`)
    `limit_choices_to` — **deben** migrarse (B4).
  - **`OrganRepresentativeSerializer`** (coherencia cargo↔entidad): confirmar que usa
    `tipo_contenido.model=="organdirectory"` (ContentType) y **NO** `categoria` → NO se ve afectado.
  - Filters/services/PDF/reportes que lean `categoria` de un `OrganDirectory`.
  - **Criterio:** lista completa de usos documentada en el PR; ningún uso queda sin remapear a
    `organo`. Si aparece un uso no previsto (p. ej. un reporte), se añade una subtarea antes de
    continuar (no romper silenciosamente).

- [x] **B1 — Modelo `OrganDirectory`: FK `organo` + nuevas constraints.**
  En `apps/convenios/models.py`:
  - Añadir `organo = models.ForeignKey(Organ, on_delete=models.PROTECT, db_column="organo_id",
    related_name="organos_directorio_por_categoria")` (verificar que el `related_name` no colisione).
  - **Eliminar** el CharField `categoria` (tras la data migration — ver B2; en el código del modelo
    queda ya sin `categoria`, la migración maneja el orden).
  - `Meta.constraints`: eliminar `uniq_organo_directorio_por_gore`; añadir las **dos**
    `UniqueConstraint` de D2 (con GORE / sin GORE).
  - Ajustar `__str__` si mencionaba categoría (hoy devuelve `self.nombre` — probablemente no cambia).
  - **Criterio:** el modelo tiene FK `organo` NOT NULL y las 2 constraints; `makemigrations` genera
    la migración de esquema; no rompe imports.

- [x] **B2 — Migración de esquema + data migration + dedupe/verificación.**
  Una o varias migraciones encadenadas en `apps/convenios/migrations/`:
  1. **Add** `organo` **nullable temporal** (FK a `Organ`).
  2. **Data migration (`RunPython`):** para cada `OrganDirectory`, resolver
     `Organ.objects.get(nombre=<mapa[categoria_code]>)` usando el mapa **por nombre** de §2
     (`ORGANO_MINSA→"MINSA Administrativo"`, `UNIVERSIDAD→"Universidad"`,
     `GOBIERNO_REGIONAL→"Gobierno Regional"`, `UNIDAD_EJECUTORA→"Unidad Ejecutora"`,
     `MINSA_DIRIS→"MINSA DIRIS"`) y asignar `obj.organo`. **No hardcodear ids.** Si algún `Organ` no
     existe por nombre, la migración debe **fallar con mensaje claro** (no crear filas silenciosas).
  3. **Verificación de colisiones** antes de crear las constraints de unicidad: comprobar que no haya
     duplicados de `(organo, gobierno_regional, nombre)` (ni de `(organo, nombre)` para `gobierno_regional`
     NULL). Con ~15 filas actuales, se espera 0 colisiones. **Decisión (D-mig):** si hay colisiones,
     **fallar** la migración con un mensaje que liste las filas en conflicto y pida limpieza manual
     (NO dedupe automático que borre datos). Documentar en el PR el resultado del chequeo sobre la BD
     real.
  4. **Set NOT NULL** en `organo`.
  5. **Drop** el CharField `categoria`.
  6. **Drop** constraint `uniq_organo_directorio_por_gore` (0037) y **add** las 2 constraints de D2.
  - **`reverse_code`:** repoblar `categoria` desde `organo.nombre` (mapa inverso por nombre) para
    reversibilidad.
  - **Criterio:** `migrate` corre limpio sobre la BD dev con datos; cada fila queda con `organo`
    correcto (verificable: `ORGANO_MINSA` → organo `MINSA Administrativo`, etc.); la columna
    `categoria` ya no existe; las 2 constraints existen; `migrate convenios <prev>` revierte
    repoblando `categoria` sin pérdida. El PR reporta el nº de filas migradas y 0 colisiones (o la
    lista de colisiones si las hubiera).

- [x] **B3 — Serializer `_OrganDirectorySerializer`: `organo_detalle` + validación D2.**
  En `views.py` (`_OrganDirectorySerializer`, ~690):
  - Añadir `organo` a `detalles` (`detalles={"gobierno_regional": _detalle_nombre, "organo":
    _detalle_nombre}`) para exponer `organo_detalle: {id, codigo?, nombre}`. (`_detalle_nombre` sirve;
    `Organ` no tiene `codigo`, así que devolverá `{id, codigo: None, nombre}` — aceptable; el front
    usa `nombre`.)
  - **Reescribir `validate()`** a la nueva RN (D2/D3), reemplazando la de «uno por GORE»:
    - Calcular estado final de `organo`, `gobierno_regional`, `nombre` (soporta PATCH parcial partiendo
      de `self.instance`).
    - Si `gobierno_regional` **no es NULL:** rechazar si existe otro `OrganDirectory` con el mismo
      `(organo, gobierno_regional, nombre)` (comparación **exacta** de `nombre`, D3), excluyendo
      `self.instance`. 400 legible (campo `nombre` o `non_field_errors`, mensaje: «Ya existe un órgano
      del directorio con este nombre para el mismo órgano y gobierno regional.»).
    - Si `gobierno_regional` **es NULL:** rechazar si existe otro con el mismo `(organo, nombre)` y
      `gobierno_regional` NULL, excluyendo `self.instance`. 400 legible análogo.
  - **Criterio:** el auto-serializer expone `organo` (PK, write) + `organo_detalle` (read); crear un
    duplicado exacto `(organo, gore, nombre)` → 400 legible (no IntegrityError 500); un GORE con dos
    órganos de **nombre distinto** o de **`organo` distinto** se acepta; el caso NULL valida
    `(organo, nombre)`.

- [x] **B4 — `limit_choices_to` de `University.tipo_entidad` y `ExecutingUnit.tipo_organo`.**
  Migrar el `limit_choices_to={"categoria": "..."}` (que ya no existe) a la nueva FK:
  - **Opción recomendada (decidir en implement, ver §8 P2):** `limit_choices_to={"organo__nombre":
    "Universidad"}` y `{"organo__nombre": "Unidad Ejecutora"}` respectivamente. `limit_choices_to`
    solo afecta al admin/forms de Django (no al serializer DRF ni a la validación de negocio); dado
    que el front filtra por `?organo=<id>` (D4), el `limit_choices_to` es cosmético.
  - Como la restricción real la impone la **UI del front** (`?organo=<id>`) y NO el serializer DRF, si
    se requiere validación dura backend, dejarlo documentado como trabajo futuro (no se pide aquí).
  - **Criterio:** ningún `limit_choices_to` referencia `categoria`; el admin de Django (si se usa)
    filtra por `organo__nombre`; los serializers de `universities`/`executing-units` no rompen.

- [x] **B5 — `pdf.py:_seleccionar_plantilla`: remapear a `organo.nombre`.** *(LOAD-BEARING)*
  En `pdf.py:209-235`: reemplazar `categoria = getattr(convenio.organo_directorio, "categoria", "")`
  por leer el nombre del órgano (`getattr(getattr(convenio.organo_directorio, "organo", None),
  "nombre", "")`). Reescribir el `mapa` para usar los **`Organ.nombre`** en vez de los codes de
  categoría:
  - `("MARCO", "MINSA DIRIS"): "modelo_1_marco_lima.docx"`
  - `("MARCO", "Gobierno Regional"): "modelo_2_marco_region.docx"`
  - `("ESPECIFICO", "MINSA DIRIS"): "modelo_3_especifico_lima.docx"`
  - `("ESPECIFICO", "Gobierno Regional"): "modelo_4_especifico_region.docx"`
  - Actualizar el mensaje de `RuntimeError` (habla de «categoría del órgano»).
  - **Criterio:** generar el PDF de un convenio Marco de GORE devuelve `modelo_2_marco_region.docx`;
    un Específico de DIRIS devuelve `modelo_3_especifico_lima.docx`; una combinación sin plantilla
    lanza el `RuntimeError` en español. **Probar los 4 casos + adenda + un caso no mapeado** antes de
    cerrar la tarea (riesgo alto R1).

- [x] **B6 — `_detalle_organo_directorio` + viewset filterset.**
  - `views.py:447-449` (`_detalle_organo_directorio`): cambiar `get_categoria_display()` por leer el
    órgano — devolver `{"id": rel.id, "nombre": rel.nombre, "organo": getattr(rel.organo, "nombre",
    None)}`. **Nota:** este dict alimenta `executive-positions.organo_directivo_detalle`, hoy
    documentado como `{id, nombre, categoria}`. **Decisión:** renombrar la clave `categoria` → `organo`
    (más honesto) **o** conservar la clave `categoria` poblada con `rel.organo.nombre` para no romper
    consumidores del front. **Recomendación:** conservar la clave `organo` nueva y actualizar el front
    (columna de `executive-positions` — verificar `lib/catalogos` que consuma
    `organo_directivo_detalle.categoria`). Ver §8 P3.
  - `OrganDirectoryViewSet` (`views.py:725-736`): `filterset_fields` de `["categoria",
    "gobierno_regional", "activo"]` → `["organo", "gobierno_regional", "activo"]`. Añadir `organo` a
    `detalles` del `_entity_viewset` (`detalles={"gobierno_regional": _detalle_nombre, "organo":
    _detalle_nombre}`) y `select_related("gobierno_regional", "organo")`.
  - Actualizar comentarios de `views.py:1027`/`1044` (mencionan `categoria` como discriminador de
    OrganDirectory).
  - **Criterio:** `GET /organ-directories/?organo=<id>` filtra por órgano; la respuesta trae
    `organo_detalle: {id, nombre}`; `executive-positions.organo_directivo_detalle` ya no llama a
    `get_categoria_display()` (no rompe con la columna eliminada).

- [x] **B7 — Docs backend + contrato + regen tipos.**
  - `docs/api-catalogos.md` §2: cambiar el filtro de `organ-directories` de `categoria` → `organo`
    (línea 94); reescribir la sección «`organ-directories` — campo `categoria`» a «campo `organo` (FK
    a `organs`)»; documentar la nueva RN de unicidad `(organo, gobierno_regional, nombre)` (con caso
    NULL) y el 400 legible. Ajustar la sección de la RN «uno por GORE» (líneas 108-120) — ya no aplica.
  - Reflejar el cambio de `University.tipo_entidad` / `ExecutingUnit.tipo_organo` (siguen apuntando a
    `organ-directories`, ahora filtrables por `?organo=<id de Universidad / Unidad Ejecutora>`).
  - **Criterio:** la doc no menciona `categoria` como campo de `OrganDirectory`; describe `organo`
    (FK) y la nueva unicidad.

---

## 5. Tareas — FRONTEND (`D:\dev\renads\renads-frontend`)

> **Orden de despliegue:** el backend (B1-B7) debe estar mergeado y migrado **antes** de T1.

- [x] **T1 — Regenerar tipos OpenAPI.** Tras B1-B7 en el backend vivo, `npm run gen:api` para
  actualizar `lib/api/schema.d.ts` (`OrganDirectory` con `organo`/`organo_detalle`, sin `categoria`;
  filterset `organo`).
  - **Criterio:** `schema.d.ts` refleja `organo`/`organo_detalle` y ya no tiene `categoria` en
    `OrganDirectory`; `npx tsc --noEmit` compila.

- [x] **T2 — Util de resolución de id de `Organ` (`lib/catalogos/organs.ts`).** *(clave para D4)*
  Nuevo módulo reutilizable:
  - `useOrgans()` — query TanStack de `organs` (`staleTime` alto: la tabla es canónica, 5 filas y no
    cambia). Devuelve la lista `[{id, nombre}]`.
  - `organIdByNombre(organs, nombre)` — helper puro que mapea `nombre → id` (búsqueda exacta por
    `nombre`). Constante con los **nombres canónicos** (`ORGAN_NOMBRE = { MINSA: "MINSA Administrativo",
    UNIVERSIDAD: "Universidad", GORE: "Gobierno Regional", UE: "Unidad Ejecutora", DIRIS: "MINSA
    DIRIS" }`) para no repetir strings mágicos. **Sin hardcodear ids.**
  - (Opcional) `useOrganId(nombre)` — hook de conveniencia que combina ambos.
  - Axios solo dentro de `lib/api/` (usar el hook de recurso / `api` client existente); server-state
    solo con TanStack Query.
  - **Criterio:** el módulo compila; `useOrgans()` trae las 5 filas; `organIdByNombre` resuelve el id
    correcto para cada nombre canónico y `undefined` si no existe; ningún id hardcodeado.

- [x] **T3 — `organ-directories` en `lib/convenios/entities.ts`: columna/filtro/campo `organo`.**
  - **Eliminar** `ORGAN_DIRECTORY_CATEGORY` y `categoriaLabel` **si dejan de usarse** (verificar: los
    usa `organ-directories` y los `optionsParams` de University/UE — todos migran en T3/T4; entonces
    se pueden borrar). Si algún otro archivo los importa, dejar constante o migrarlo.
  - Columna `categoria` → `organo`: `render: (r) => detalleNombre(r.organo_detalle)` (muestra
    `Organ.nombre`, D5). Nunca `String(r.organo_detalle)`.
  - Filtro `categoria` → `organo`: `type:"select", optionsEndpoint:"organs",
    optionsToLabel:(o)=>o.nombre` (select server-side contra `organs`; NO `choices` estáticos).
  - Campo `categoria` → `organo`: `type:"select", required:true, optionsEndpoint:"organs",
    optionsToLabel:(o)=>o.nombre`.
  - **Criterio:** la tabla de `/catalogos/entidades/organ-directories` muestra la columna «Órgano» con
    el nombre real de `Organ`; el filtro y el alta/edición seleccionan `organo` desde el catálogo
    `organs` (no un enum estático); el POST/PATCH envía `organo: <id>` (verificable en Network) y NO
    `categoria`.

- [x] **T4 — `University.tipo_entidad` y `ExecutingUnit.tipo_organo`: `?organo=<id>` dinámico.**
  Reemplazar los `optionsParams:{categoria:"UNIVERSIDAD"}` (líneas ~125, 157) y
  `{categoria:"UNIDAD_EJECUTORA"}` (~397, 422) por un filtro **por id de Organ resuelto en runtime**:
  - Dado que `ResourceConfig`/`EntityCombobox` reciben `optionsParams` estáticos, **decidir el
    mecanismo** (ver §8 P4): (a) que el componente de filtro/campo resuelva el id vía `useOrgans()` y
    pase `optionsParams:{organo:<id>}` dinámicamente, o (b) extender la config para aceptar
    `optionsParams` como función/async. Verificar qué soporta hoy `EntityCombobox`/`ResourceForm`
    antes de elegir; **no inventar** una API de config que no exista.
  - En ambos casos el resultado es `optionsEndpoint:"organ-directories", optionsParams:{organo:<id de
    "Universidad" | "Unidad Ejecutora">}` con el id resuelto dinámicamente (nunca hardcodeado, nunca
    `?categoria=`).
  - **Criterio:** el select «Tipo de entidad» de universidades lista solo `organ-directories` con
    `organo = Universidad`; el «Tipo de unidad ejecutora» solo los de `organo = Unidad Ejecutora`; en
    Network se ve `?organo=<id>` (no `?categoria=`); el id no está hardcodeado en el código.

- [x] **T5 — `lib/catalogos/representantes-entities.ts` + pantalla `/catalogos/representantes`.**
  Los 3 tipos de OrganDirectory (`organo-minsa`, `gobierno-regional`, `diris`) usan hoy
  `params:{categoria:"..."}` para filtrar el combobox del paso 2. Migrar a `params:{organo:"<id>"}`
  resuelto por nombre:
  - **Opción (decidir, §8 P4):** cambiar `params` de valor estático a algo resoluble en runtime. Como
    `RepresentanteEntityOption.params` es `Record<string,string>` estático, lo más limpio es que la
    **pantalla** `/catalogos/representantes` resuelva el id vía `useOrgans()` y construya
    `params:{organo:String(id)}` al armar los `optionsParams` del `EntityCombobox` del paso 2 (en
    lugar de leer `opt.params` tal cual). Reemplazar el campo `params:{categoria}` de las 3 opciones
    por un discriminador estable (p. ej. `organoNombre: ORGAN_NOMBRE.MINSA | .GORE | .DIRIS`) que la
    pantalla mapea a `organo` id.
  - Mantener las 7 opciones de UI y su semántica; solo cambia **cómo se filtra la entidad concreta**.
  - **Criterio:** en `/catalogos/representantes`, elegir «Órgano del MINSA»/«Gobierno Regional»/«DIRIS»
    filtra `organ-directories?organo=<id>` (verificable en Network, NO `?categoria=`); las otras 4
    opciones (Universidad/UE/CONAPRES/IPRESS) siguen igual; el id se resuelve dinámicamente.

- [x] **T6 — Consumidores de `organo_directivo_detalle.categoria` (si los hay).**
  Según la decisión de B6 (clave `categoria` → `organo` en `_detalle_organo_directorio`), buscar en el
  front (`lib/catalogos`, `components`) cualquier lectura de `organo_directivo_detalle.categoria` (p.
  ej. columnas de `executive-positions`) y actualizarla a la nueva clave.
  - **Criterio:** ninguna columna/label del front lee la clave eliminada; `executive-positions`
    muestra el órgano correctamente; `npx tsc --noEmit` limpio.

- [x] **T7 — Docs front + `CLAUDE.md`.**
  - `CLAUDE.md`: actualizar la descripción de `organ-directories` (ya no discriminado por CharField
    `categoria`; ahora FK `organo → Organ`; nueva unicidad `(organo, gobierno_regional, nombre)`);
    actualizar las menciones de `?categoria=` / `optionsParams:{categoria:...}` (University/UE,
    representantes); actualizar `_detalle_organo_directorio` (`organo_directivo_detalle` clave nueva);
    añadir fila a «Refactors de backend aplicados al frontend» con fecha 2026-09-07.
  - **Criterio:** `CLAUDE.md` y `docs/api-catalogos.md` describen la FK `organo` y la nueva RN; no
    quedan menciones de `?categoria=` para `OrganDirectory` (salvo `Ipress.categoria`, que es otra
    cosa).

- [x] **T8 — Verificación final.**
  `npx tsc --noEmit` y `npm run lint` limpios. Smoke manual (rol `Administrador RENADS`):
  - Crear/editar un `organ-directory` seleccionando `organo` desde el catálogo; verificar POST/PATCH
    con `organo:<id>`.
  - Crear un GORE con **dos** órganos de nombre distinto (debe permitir); intentar duplicar
    `(organo, gore, nombre)` exacto → 400 legible.
  - Verificar los selects de University.tipo_entidad y ExecutingUnit.tipo_organo (`?organo=<id>`).
  - Registrar un representante de MINSA/GORE/DIRIS (`?organo=<id>` en el combobox del paso 2).
  - **Generar el PDF** de un convenio Marco/GORE y otro Específico/DIRIS (verificar plantilla correcta
    — B5).
  - **Criterio:** cero errores TS/ESLint; todos los flujos responden 2xx; la nueva unicidad rechaza
    duplicados exactos y permite nombres distintos; el PDF usa la plantilla correcta.

---

## 6. Reglas de negocio / validación (RN)

| RN | Descripción | Dónde vive |
|----|-------------|------------|
| RN-OD1 | `OrganDirectory` referencia **una** categoría vía FK `organo → Organ` (PROTECT), NOT NULL. | Backend (B1) |
| RN-OD2 | **Unicidad (con GORE):** no dos `OrganDirectory` con el mismo `(organo, gobierno_regional, nombre)` cuando `gobierno_regional` no es NULL. Un GORE puede tener varios órganos con distinto `organo` y/o `nombre`. | BD (D2) + serializer (B3) |
| RN-OD3 | **Unicidad (sin GORE):** no dos `OrganDirectory` con el mismo `(organo, nombre)` cuando `gobierno_regional` es NULL (MINSA/DIRIS/tipos Universidad/UE). | BD (D2) + serializer (B3) |
| RN-OD4 | Comparación de `nombre` **exacta** (sin normalizar). | BD + serializer (D3) |
| RN-OD5 | El front resuelve `organo` **por id** (fetch `organs`, mapa por `nombre`), nunca `?categoria=` ni ids hardcodeados. | Front (D4/T2-T5) |
| RN-OD6 | Escritura solo `Administrador RENADS`; lectura para miembro institucional autenticado. | Backend + UX gating |

---

## 7. Riesgos y puntos de atención

- **R1 — PDF template selection (`pdf.py`) — MÁS CRÍTICO.** `_seleccionar_plantilla` es load-bearing;
  un mapeo mal hecho rompe la generación de todos los convenios. El mapa debe usar `Organ.nombre`
  **exacto** (`"MINSA DIRIS"`, `"Gobierno Regional"`) — cuidado con tildes/espacios. Probar los 4
  casos + adenda + no-mapeado (B5).
- **R2 — Ids de `Organ` dependientes de la BD.** Nunca hardcodear ids (ni en migración ni en front).
  La migración mapea por `Organ.nombre`; el front resuelve vía endpoint `organs` (T2).
- **R3 — Colisiones al crear la constraint.** Con ~15 filas se esperan 0, pero la migración DEBE
  verificar `(organo, gobierno_regional, nombre)` (y el caso NULL) antes de crear las constraints y
  **fallar con lista de conflictos** si los hay (no dedupe destructivo — D-mig en B2).
- **R4 — Reversibilidad.** `reverse_code` repobla `categoria` desde `organo.nombre` (mapa inverso).
  Correr la migración sobre una copia con datos antes de mergear; verificar `migrate convenios <prev>`.
- **R5 — `Organ.nombre` ≠ labels de categoría.** `MINSA Administrativo` ≠ `Órgano del MINSA`. La UI
  muestra `Organ.nombre` tal cual (D5). Si el usuario prefiere los labels «bonitos» de categoría, hay
  que un mapa de display en el front (§8 P1) — pero eso reintroduce acoplamiento nombre↔label. Se
  recomienda usar `Organ.nombre`.
- **R6 — Orden de despliegue.** Backend (B1-B7) mergeado y migrado **antes** de `npm run gen:api` (T1)
  y del resto del front; de lo contrario los tipos/filtros no existen.
- **R7 — `_detalle_organo_directorio` compartido.** Alimenta `executive-positions.organo_directivo_detalle`;
  cambiar su forma afecta a esa columna (T6). No romper esa pantalla.
- **R8 — `optionsParams` estáticos.** El CRUD declarativo del front usa `optionsParams` fijos; la
  resolución dinámica del id de Organ (T4/T5) requiere verificar qué soporta `EntityCombobox`/
  `ResourceForm` hoy — **no inventar** una API de config inexistente (§8 P4).

---

## 8. Preguntas abiertas para la aprobación humana

1. **P1 (D5) — Display del label de `organo` en la UI:** ¿usar `Organ.nombre` tal cual (recomendado,
   menos acoplamiento) o mantener un mapa de display en el front que muestre los labels «bonitos» de
   categoría (`Órgano del MINSA`, etc.)? Propuesta: **`Organ.nombre` tal cual**.
2. **P2 (B4) — `limit_choices_to`:** ¿basta `limit_choices_to={"organo__nombre": "..."}` (cosmético,
   admin/forms) dado que la restricción real la impone el front por `?organo=<id>`, o se requiere
   validación dura en el serializer DRF de `universities`/`executing-units`? Propuesta:
   `organo__nombre` + validación front; validación dura backend como trabajo futuro si se pide.
3. **P3 (B6) — Clave del `*_detalle`:** en `_detalle_organo_directorio`, ¿renombrar la clave
   `categoria` → `organo` (más honesto, requiere T6) o conservar la clave `categoria` poblada con
   `organo.nombre` (menos cambios en el front)? Propuesta: **renombrar a `organo`** y actualizar
   consumidores (T6).
4. **P4 (T4/T5) — Mecanismo de `optionsParams` dinámico:** verificar qué soporta hoy el CRUD
   declarativo (`EntityCombobox`/`ResourceForm`) para pasar `optionsParams` resueltos en runtime
   (id de Organ). ¿Se resuelve en la pantalla y se pasan props ya calculados, o se extiende la config
   para aceptar `optionsParams` como función? El agente `implement` debe verificarlo antes de elegir;
   **no inventar** API de config.
5. **P5 (B2, D-mig) — Colisiones:** confirmar que ante colisiones `(organo, gobierno_regional, nombre)`
   la migración debe **fallar** pidiendo limpieza manual (propuesta) en vez de dedupe automático.

---

> **Recordatorio: este spec REQUIERE APROBACIÓN HUMANA antes de pasar al agente `implement`.**
> Resolver §8 (P1-P5) y confirmar §3 (D1-D5) antes de codificar. El orden es backend (B0-B7, con
> migración probada sobre datos y PDF verificado) → `npm run gen:api` (T1) → frontend (T2-T8).
