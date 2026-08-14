# Spec — Refactor de BD del Módulo 1 (Convenios): jerarquía Red/Microred, catálogos de clasificación de IPRESS y refactor de `ipress`

> Fuente de verdad: `apps/convenios/models.py`, `apps/convenios/views.py`, `apps/convenios/urls.py`,
> `docs/db_schema_modulo_01_convenios.md`, `docs/db_schema_er_global.md`,
> `docs/arquitectura_desarrollo.md`, `CLAUDE.md`.
> Este documento es la lista de tareas para el agente **implement**. **No contiene código de aplicación.**

## Resumen del refactor

Se amplía el modelo geográfico-sanitario del Módulo 1 (app `apps/convenios`, `app_label = convenios`) con:

1. **Nueva jerarquía geográfica** que cuelga de `ambito_geografico_sanitario` (modelo existente `HealthGeographicScope`, `apps/convenios/models.py:39`):
   `ambito_geografico_sanitario` → **`red`** (nuevo) → **`microred`** (nuevo).
2. **Dos catálogos nuevos de clasificación de IPRESS**: **`categoria`** (`Category`) y **`tipo_clasificacion`** (`ClassificationType`), ambos heredan de `Catalog` (`apps/convenios/models.py:15`).
3. **Refactor de `ipress`** (`Ipress`, `apps/convenios/models.py:255`): nuevas FK opcionales `categoria`, `tipo_clasificacion`, `microred` y nuevos campos escalares `latitud`, `longitud`, `cantidad_camas`, `numero_ruc`. Conserva su FK actual `ambito_geografico_sanitario`.

Entidades cubiertas: `Red`, `Microred`, `Category`, `ClassificationType`, `Ipress` (refactor).

## Decisiones fijadas (NO reabrir)

- **D1 — CRUD completo con auditoría:** los 4 modelos nuevos son catálogos con CRUD; escritura solo `Administrador RENADS` (patrón `IsAdminRoleOrReadOnly`), lectura para autenticados. Se registran en `ENTITY_VIEWSETS` (mismo patrón que `document-types`, `annex-documents`, etc.) y heredan la auditoría de `AuditedModelViewSet` (create/update/delete en `bitacora_auditoria`, RNF-AUD-01).
- **D2 — `ipress` ↔ jerarquía:** `ipress` recibe FK **opcional** `microred` → `Microred` (`on_delete=PROTECT`, `null=True`, `blank=True`, `db_column="microred_id"`). Conserva su FK `ambito_geografico_sanitario`. La jerarquía red/microred cuelga de `ambito_geografico_sanitario`, no de `ipress`.
- **D3 — `red`/`microred` con código único por padre:** NO heredan de `Catalog` (cuyo `codigo` es `unique` global). Modelo propio con campos `codigo`, `nombre`, `activo` y `unique_together`:
  - `red` → (`ambito_geografico_sanitario`, `codigo`).
  - `microred` → (`red`, `codigo`).
  - FK con `on_delete=PROTECT` y `db_column`. Jerarquía: `red.ambito_geografico_sanitario` → `microred.red`.
- **`categoria`/`tipo_clasificacion`:** SÍ heredan de `Catalog` (`codigo` unique global, `nombre`, `activo`).
- **Convenciones de idioma (CLAUDE.md):** clase en inglés (`Red`, `Microred`, `Category`, `ClassificationType`); `db_table`, `verbose_name`, `help_text`, `verbose_name` de campos y descripciones de columnas en **español**; `related_name` explícito en todas las FK.

---

## Capa: Modelos (`apps/convenios/models.py`)

### T1 — Modelo `Red` (tabla `red`)

Crear la clase `Red(models.Model)` (NO hereda de `Catalog`), en la sección de catálogos/entidades geográficas de `apps/convenios/models.py`, con:

- `ambito_geografico_sanitario`: `ForeignKey(HealthGeographicScope, on_delete=models.PROTECT, db_column="ambito_geografico_sanitario_id", related_name="redes", help_text="Ámbito geográfico sanitario al que pertenece la red")`.
- `codigo`: `CharField("código", max_length=50, help_text="Código de la red (único dentro del ámbito)")` — **sin** `unique=True`.
- `nombre`: `CharField("nombre", max_length=255, help_text="Nombre de la red")`.
- `activo`: `BooleanField("activo", default=True)`.
- `Meta`: `db_table="red"`, `verbose_name="red"`, `verbose_name_plural="redes"`, `unique_together=(("ambito_geografico_sanitario", "codigo"),)`, `ordering=["ambito_geografico_sanitario", "codigo"]`.
- `__str__` devuelve `self.nombre`.

**Criterios de aceptación:**
- No hereda de `Catalog`. `codigo` NO es `unique` global; la unicidad es por (`ambito_geografico_sanitario`, `codigo`).
- La FK usa `on_delete=PROTECT` y `db_column` en español (`ambito_geografico_sanitario_id`).
- `related_name="redes"` accesible desde `HealthGeographicScope`.

### T2 — Modelo `Microred` (tabla `microred`)

Crear la clase `Microred(models.Model)` (NO hereda de `Catalog`) con:

- `red`: `ForeignKey(Red, on_delete=models.PROTECT, db_column="red_id", related_name="microredes", help_text="Red a la que pertenece la microred")`.
- `codigo`: `CharField("código", max_length=50, help_text="Código de la microred (único dentro de la red)")` — **sin** `unique=True`.
- `nombre`: `CharField("nombre", max_length=255, help_text="Nombre de la microred")`.
- `activo`: `BooleanField("activo", default=True)`.
- `Meta`: `db_table="microred"`, `verbose_name="microred"`, `verbose_name_plural="microredes"`, `unique_together=(("red", "codigo"),)`, `ordering=["red", "codigo"]`.
- `__str__` devuelve `self.nombre`.

**Criterios de aceptación:**
- No hereda de `Catalog`. Unicidad por (`red`, `codigo`).
- FK a `Red` con `on_delete=PROTECT` y `db_column="red_id"`; `related_name="microredes"`.
- `Microred` se define **después** de `Red` en el archivo (orden de dependencia).

### T3 — Modelo `Category` (tabla `categoria`)

Crear `class Category(Catalog)` con `Meta`: `db_table="categoria"`, `verbose_name="categoría"`, `verbose_name_plural="categorías"`.

**Criterios de aceptación:**
- Hereda de `Catalog` (campos `codigo` unique global, `nombre`, `activo` provienen de la base abstracta).
- No añade campos propios.

### T4 — Modelo `ClassificationType` (tabla `tipo_clasificacion`)

Crear `class ClassificationType(Catalog)` con `Meta`: `db_table="tipo_clasificacion"`, `verbose_name="tipo de clasificación"`, `verbose_name_plural="tipos de clasificación"`.

**Criterios de aceptación:**
- Hereda de `Catalog`. No añade campos propios.

### T5 — Refactor del modelo `Ipress` (`apps/convenios/models.py:255`)

Sobre la clase `Ipress` existente, **conservar** todos los campos actuales (`unidad_ejecutora`, `nombre`, `codigo_renipress`, `direccion`, `ubigeo`, `ambito_geografico_sanitario`, `es_sede_docente`, `referencia_logo`, `activo`) y **agregar**:

FK nuevas (todas `null=True, blank=True, on_delete=models.PROTECT, db_column=...`; justificación: `db.sqlite3` ya tiene filas de `ipress`, se migra sin default forzado):
- `categoria`: `ForeignKey(Category, on_delete=models.PROTECT, db_column="categoria_id", null=True, blank=True, related_name="ipress", help_text="Categoría del establecimiento")`.
- `tipo_clasificacion`: `ForeignKey(ClassificationType, on_delete=models.PROTECT, db_column="tipo_clasificacion_id", null=True, blank=True, related_name="ipress", help_text="Tipo de clasificación del establecimiento")`.
- `microred`: `ForeignKey(Microred, on_delete=models.PROTECT, db_column="microred_id", null=True, blank=True, related_name="ipress", help_text="Microred a la que pertenece el establecimiento")`.

Campos escalares nuevos:
- `latitud`: `DecimalField("latitud", max_digits=9, decimal_places=6, null=True, blank=True, help_text="Latitud (coordenada geográfica)")`.
- `longitud`: `DecimalField("longitud", max_digits=9, decimal_places=6, null=True, blank=True, help_text="Longitud (coordenada geográfica)")`.
- `cantidad_camas`: `PositiveIntegerField("cantidad de camas", null=True, blank=True, help_text="Número de camas del establecimiento")`.
- `numero_ruc`: `CharField("número de RUC", max_length=11, blank=True, help_text="RUC (11 dígitos; texto para conservar ceros a la izquierda)")`. **No** `unique` en el MVP; solo validación de formato (ver T14).

**Criterios de aceptación:**
- Las 3 FK nuevas son opcionales (`null=True, blank=True`), `on_delete=PROTECT`, con `db_column` en español.
- `latitud`/`longitud` = `DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)`.
- `cantidad_camas` = `PositiveIntegerField(null=True, blank=True)`.
- `numero_ruc` = `CharField(max_length=11, blank=True)` (no unique).
- Los `related_name` de las 3 FK a `ipress` no colisionan con el `related_name="ipress"` existente de `unidad_ejecutora`; usar nombres distintos si Django lo exige (p. ej. `related_name="ipress_por_categoria"`, `"ipress_por_clasificacion"`, `"ipress_por_microred"`). Documentar el nombre elegido en el mismo cambio.
- Definir `Category`, `ClassificationType`, `Red`, `Microred` **antes** de `Ipress` en el archivo, o usar referencia por string en las FK.

---

## Capa: Migración

### T6 — Migración de schema

Generar y aplicar la migración con el entorno virtual activado (`.venv\Scripts\Activate.ps1`):
`python manage.py makemigrations convenios` y `python manage.py migrate`.

**Criterios de aceptación:**
- Una sola migración nueva en `apps/convenios/migrations/` que: crea las tablas `red`, `microred`, `categoria`, `tipo_clasificacion`; añade a `ipress` las columnas `categoria_id`, `tipo_clasificacion_id`, `microred_id`, `latitud`, `longitud`, `cantidad_camas`, `numero_ruc`.
- `python manage.py migrate` corre **limpio** sobre el `db.sqlite3` existente sin exigir default para las filas de `ipress` ya presentes (todas las columnas nuevas son nullable/blank).
- La migración incluye las restricciones `unique_together` de `red` y `microred`.
- `python manage.py makemigrations --check --dry-run` no reporta cambios pendientes tras aplicar.

---

## Capa: Serializers, Filters, Selectors/Views

> Patrón vigente: los catálogos-entidad CRUD usan `_entity_viewset(model, filterset_fields=..., search_fields=...)` con `_auto_serializer` (ambos en `apps/convenios/views.py`). No se requieren serializers manuales salvo para exponer campos derivados. Seguir ese patrón salvo indicación.

### T7 — ViewSets CRUD de los 4 catálogos nuevos

En `apps/convenios/views.py`, añadir entradas a `ENTITY_VIEWSETS` usando `_entity_viewset(...)`:
- `Red`: `filterset_fields=["ambito_geografico_sanitario", "activo"]`, `search_fields=["codigo", "nombre"]`.
- `Microred`: `filterset_fields=["red", "activo"]`, `search_fields=["codigo", "nombre"]`.
- `Category`: `filterset_fields=["activo"]`, `search_fields=["codigo", "nombre"]`.
- `ClassificationType`: `filterset_fields=["activo"]`, `search_fields=["codigo", "nombre"]`.

**Criterios de aceptación:**
- Los 4 usan `permission_classes` por defecto de `_entity_viewset` (`[IsAuthenticated, IsAdminRoleOrReadOnly]`): escritura solo `Administrador RENADS`, lectura para autenticados.
- Heredan de `AuditedModelViewSet` (auditoría en create/update/delete) por construcción de `_entity_viewset`.
- Al ser catálogos por-padre (`red`, `microred`), el `filterset_fields` permite filtrar por el padre (`ambito_geografico_sanitario`, `red`).
- NO se registran en `CATALOG_VIEWSETS` (que es solo lectura); van en `ENTITY_VIEWSETS`.

### T8 — Actualizar el CRUD de `ipress` para exponer/aceptar los nuevos campos

`IpressViewSet` (`apps/convenios/views.py:315`) ya usa `_auto_serializer(m.Ipress)` con `fields="__all__"`, por lo que los campos nuevos quedan expuestos automáticamente. Verificar y ajustar:
- Añadir a los `filterset_fields` de `IpressViewSet`: `categoria`, `tipo_clasificacion`, `microred` (junto a los existentes `unidad_ejecutora`, `ambito_geografico_sanitario`, `es_sede_docente`, `activo`).
- Verificar que el serializer auto-generado acepta en escritura (create/update) las FK nuevas y los escalares.

**Criterios de aceptación:**
- `GET /api/v1/ipress/` devuelve en cada item: `categoria`, `tipo_clasificacion`, `microred`, `latitud`, `longitud`, `cantidad_camas`, `numero_ruc`.
- `POST`/`PATCH /api/v1/ipress/` acepta y persiste esos campos (respetando la validación de RUC de T14).
- Se puede filtrar por `?microred=`, `?categoria=`, `?tipo_clasificacion=` en el listado de `ipress`.

### T9 — Selectors (si aplica)

Revisar `apps/convenios/selectors.py`. No se requiere selector nuevo para los 4 catálogos (los viewsets CRUD usan `_default_manager.all()`). Si algún selector existente de `ipress` usa `select_related`, incluir `categoria`, `tipo_clasificacion`, `microred` para evitar N+1.

**Criterios de aceptación:**
- No se introduce lógica de alcance institucional nueva para estos catálogos (son catálogos maestros globales).
- Si se toca un selector de `ipress`, las FK nuevas se cargan con `select_related`.

---

## Capa: URLs / Router

### T10 — Registro en el router (`apps/convenios/urls.py`)

El router ya itera `ENTITY_VIEWSETS` (`apps/convenios/urls.py:23-24`), por lo que basta con registrar los viewsets nuevos en `ENTITY_VIEWSETS` (T7) con estos `basename`/`url_path` (kebab-case, inglés), consistentes con la convención existente del router:
- `red` → `networks`
- `microred` → `micro-networks`
- `categoria` → `categories`
- `tipo_clasificacion` → `classification-types`

**Criterios de aceptación:**
- Quedan disponibles bajo `/api/v1/`: `/api/v1/networks/`, `/api/v1/micro-networks/`, `/api/v1/categories/`, `/api/v1/classification-types/` (list/retrieve/create/update/partial_update/destroy).
- Los `basename` no colisionan con rutas ya registradas en `CATALOG_VIEWSETS`/`ENTITY_VIEWSETS`/núcleo.
- No se edita manualmente el bucle del router; el registro se hace por el diccionario `ENTITY_VIEWSETS`.

---

## Capa: Filters (django-filter)

### T11 — Filtros de los catálogos nuevos y de `ipress`

Los filtros simples se cubren con `filterset_fields` en los viewsets (T7, T8). No se requiere `FilterSet` dedicado salvo que se necesite un lookup por rango o por campo del padre no soportado por `filterset_fields`.

**Criterios de aceptación:**
- `networks` filtra por `ambito_geografico_sanitario` y `activo`.
- `micro-networks` filtra por `red` y `activo`.
- `categories` y `classification-types` filtran por `activo`.
- `ipress` filtra por `categoria`, `tipo_clasificacion`, `microred` (además de los filtros previos).

---

## Capa: Permissions

### T12 — Permisos por rol

No se crean clases de permiso nuevas: reutilizar `IsAdminRoleOrReadOnly` (escritura solo `Administrador RENADS`, lectura autenticados) que `_entity_viewset` aplica por defecto.

**Criterios de aceptación:**
- Un usuario autenticado sin rol `Administrador RENADS` puede hacer `GET` pero recibe 403 en `POST`/`PUT`/`PATCH`/`DELETE` sobre `networks`, `micro-networks`, `categories`, `classification-types`.
- Superusuario y `Administrador RENADS` pueden escribir.
- Estos catálogos son globales (sin alcance institucional): no se aplica `IsInstitutionalMember` ni scope por entidad.

---

## Capa: Admin (`apps/convenios/admin.py`)

### T13 — Registro en Django admin

**Nota:** actualmente NO existe `apps/convenios/admin.py`. Crear el archivo si no existe y registrar los 4 modelos nuevos (`Red`, `Microred`, `Category`, `ClassificationType`) con `admin.site.register(...)` o `@admin.register(...)`.

**Criterios de aceptación:**
- Los 4 modelos aparecen en `/admin/` bajo la app Convenios.
- `RedAdmin` muestra al menos `codigo`, `nombre`, `ambito_geografico_sanitario`, `activo` (con `list_filter`/`search_fields` razonables).
- `MicroredAdmin` muestra `codigo`, `nombre`, `red`, `activo`.
- `CategoryAdmin` y `ClassificationTypeAdmin` muestran `codigo`, `nombre`, `activo`.
- Si se crea `admin.py` desde cero, no rompe otros registros existentes de la app (verificar que ninguna otra parte ya registraba estos modelos).

---

## Capa: Validación de negocio / serializer

### T14 — Validación de formato de `numero_ruc` (RUC peruano)

Marcar como **validación de serializer** (no service): el `numero_ruc` de `ipress`, si viene no vacío, debe ser exactamente **11 dígitos numéricos** (permitiendo ceros a la izquierda porque es texto). Vacío/blank es válido (campo opcional).

**Criterios de aceptación:**
- Enviar `numero_ruc` con longitud distinta de 11 o con caracteres no numéricos devuelve 400 con mensaje en español.
- `numero_ruc=""` o ausente es aceptado.
- Como el CRUD de `ipress` usa `_auto_serializer`, la validación se implementa donde corresponda para no perderse al autogenerar (p. ej. `validators` a nivel de campo del modelo con `RegexValidator`, o un serializer explícito para `Ipress` en lugar del auto). Elegir la opción que mantenga la capa delgada y documentar la decisión.
- **RN:** no hay reglas de negocio de escritura en service para este refactor; toda la validación es de serializer/modelo. Las FK `categoria`/`tipo_clasificacion`/`microred` son opcionales y no imponen reglas cruzadas en el MVP.

---

## Documentación

### T15 — Sincronizar `docs/db_schema_modulo_01_convenios.md`

En el mismo cambio, actualizar:
- **§2 Catálogos:** añadir filas para `red`, `microred` (aclarando que NO son `Catalog`: `codigo` único por padre vía `unique_together`), `categoria` y `tipo_clasificacion`.
- **§3 tabla `ipress`** (líneas ~102-115): añadir las columnas `categoria_id` (FK, Sí), `tipo_clasificacion_id` (FK, Sí), `microred_id` (FK, Sí), `latitud` (decimal 9,6, Sí), `longitud` (decimal 9,6, Sí), `cantidad_camas` (int positivo, Sí), `numero_ruc` (varchar(11), Sí, 11 dígitos).
- **§12 Mapa de relaciones:** añadir `ambito_geografico_sanitario ──< red ──< microred ──< ipress` y `ipress >── categoria / tipo_clasificacion / microred`.

**Criterios de aceptación:**
- El `.md` refleja exactamente los tipos, nullability y `unique_together` implementados.
- Las descripciones de columnas quedan en español.

### T16 — Sincronizar `docs/db_schema_er_global.md`

Actualizar el diagrama Mermaid (§1) y el mapa textual: añadir `ambito_geografico_sanitario ||--o{ red`, `red ||--o{ microred`, `microred ||--o{ ipress`, y `categoria ||--o{ ipress`, `tipo_clasificacion ||--o{ ipress`. Conservar la relación existente `unidad_ejecutora ||--o{ ipress` y `ambito_geografico_sanitario ||--o{ ipress`.

**Criterios de aceptación:**
- El diagrama global incluye la nueva jerarquía red/microred y las FK de clasificación de `ipress`.

---

## Pruebas (services/selectors/API)

### T17 — Pruebas de los catálogos nuevos y de los campos de `ipress`

Añadir pruebas (fuera del alcance de testing automatizado del MVP **solo si el orquestador lo exige**; aquí se listan como parte del cierre porque el enunciado del refactor las pide explícitamente):
- API CRUD de `networks`, `micro-networks`, `categories`, `classification-types`: `Administrador RENADS` puede crear/editar/borrar; usuario sin rol solo lee (403 en escritura).
- `unique_together`: crear dos `red` con mismo `codigo` bajo el mismo `ambito_geografico_sanitario` falla; con distinto ámbito es válido. Ídem `microred` por `red`.
- `ipress`: crear/actualizar con `categoria`, `tipo_clasificacion`, `microred`, `latitud`, `longitud`, `cantidad_camas`, `numero_ruc` válidos persiste correctamente; `numero_ruc` inválido (≠11 dígitos / no numérico) devuelve 400.
- `PROTECT`: intentar borrar una `red` referenciada por una `microred`, o una `microred`/`categoria`/`tipo_clasificacion` referenciada por una `ipress`, devuelve 409 (`ProtectedDeleteConflict`).

**Criterios de aceptación:**
- Todas las pruebas pasan con `python manage.py test convenios`.

---

## Cierre de calidad

### T18 — `/code-review` y `/fix-types`

- Ejecutar **`/code-review`** antes de dar por terminada la implementación (obligatorio al tocar modelos, serializers, migraciones, vistas — CLAUDE.md).
- Si mypy reporta errores de tipos, invocar **`/fix-types`** (no corregir tipos manualmente).

**Criterios de aceptación:**
- `/code-review` sin observaciones bloqueantes.
- Sin errores de mypy (o resueltos vía `/fix-types`).
- Migración aplicada, `makemigrations --check` limpio, y docs (`db_schema_modulo_01_convenios.md`, `db_schema_er_global.md`) sincronizadas en el mismo cambio.

---

## Referencias de schema y reglas

- Modelos base y objetivo: `apps/convenios/models.py` — `Catalog` (L15), `HealthGeographicScope` (L39), `Ipress` (L255).
- Patrón CRUD catálogo-entidad con auditoría: `apps/convenios/views.py` — `_entity_viewset` (L278), `AuditedModelViewSet` (L200), `ENTITY_VIEWSETS` (L354), `IpressViewSet` (L315).
- Router: `apps/convenios/urls.py` (L23-24 iteran `ENTITY_VIEWSETS`).
- Permisos: `IsAdminRoleOrReadOnly` (`apps/convenios/permissions.py`).
- Schema del módulo: `docs/db_schema_modulo_01_convenios.md` §2 (catálogos), §3 (`ipress`, L102-115), §12 (mapa de relaciones).
- ER global: `docs/db_schema_er_global.md` §1 (Mermaid).
- Convenciones de idioma y catálogos CRUD con auditoría / `ENTITY_VIEWSETS`: `CLAUDE.md`.
- Arquitectura (capas delgadas, catálogos, auditoría): `docs/arquitectura_desarrollo.md`.
