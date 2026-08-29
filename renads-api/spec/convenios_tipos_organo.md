# Spec — Unificación de catálogos de tipo de órgano (`convenios_tipos_organo`)

Producido por el agente **spec** (SDD). El agente **implement** ejecuta estas tareas en orden; el **validator** revisa contra este documento.

## Resumen

Cuatro tablas de catálogo con estructura idéntica (`tipo_entidad_universidad`, `tipo_organo_regional`, `tipo_unidad_ejecutora`, `tipo_organo_minsa`) se unifican en una sola tabla `tipo_organo` con un campo discriminador `organo` (`TextChoices`). La unicidad pasa de `codigo UNIQUE` global (heredada de `Catalog`) a `unique_together = ('organo', 'codigo')`.

**Impacto en modelos referenciantes:**

| Modelo | Campo FK actual | Tabla FK actual | Nueva FK |
|---|---|---|---|
| `University` | `tipo_entidad` | `tipo_entidad_universidad` | `tipo_organo` (discriminador `UNIVERSIDAD`) |
| `RegionalOrgan` | `tipo_organo_regional` | `tipo_organo_regional` | `tipo_organo` (discriminador `ORGANO_REGIONAL`) |
| `ExecutingUnit` | `tipo_unidad_ejecutora` | `tipo_unidad_ejecutora` | `tipo_organo` (discriminador `UNIDAD_EJECUTORA`) |
| `MinsaOrgan` | `tipo_organo_minsa` | `tipo_organo_minsa` | `tipo_organo` (discriminador `MINSA`) |

**Endpoint nuevo:** `/api/v1/organ-types/` (CRUD, escritura `Administrador RENADS`).  
**Endpoints eliminados:** `/api/v1/university-entity-types/`, `/api/v1/regional-organ-types/`, `/api/v1/minsa-organ-types/` y el catálogo de solo lectura `/api/v1/executing-unit-types/`.

**Archivos modificados:** `models.py`, `views.py`, `serializers.py` (ajuste de import), `urls.py` (ningún cambio directo; el router ya es dinámico), `migrations/0016_unify_organ_types.py` (nueva), `docs/db_schema_modulo_01_convenios.md`, `docs/db_schema_er_global.md`, `CLAUDE.md`.

---

## Dependencias entre tareas

```
T1 (modelo) → T2 (migración) → T3 (views) → T4 (serializers) → T5 (docs/CLAUDE.md)
```

Las tareas T3, T4 y T5 no tienen dependencias entre sí; pueden ejecutarse en cualquier orden una vez completadas T1 y T2.

---

## T1 — Modelo `OrganType` y ajuste de modelos referenciantes (`apps/convenios/models.py`)

### T1.1 — Eliminar los cuatro modelos de catálogo a reemplazar

Ubicación aproximada: líneas 135–181 de `apps/convenios/models.py`.

Eliminar completamente las siguientes clases (incluidos sus `class Meta`):

- `UniversityEntityType` (actualmente ~línea 135–139, `db_table = "tipo_entidad_universidad"`)
- `RegionalOrganType` (actualmente ~línea 165–169, `db_table = "tipo_organo_regional"`)
- `ExecutingUnitType` (actualmente ~línea 171–175, `db_table = "tipo_unidad_ejecutora"`)
- `MinsaOrganType` (actualmente ~línea 177–181, `db_table = "tipo_organo_minsa"`)

**Criterio:** después de eliminar estas cuatro clases no debe quedar ninguna referencia a sus nombres en `models.py`. La migración las eliminará de la BD.

---

### T1.2 — Agregar `OrganCategory` (TextChoices) y el modelo `OrganType`

Insertar inmediatamente antes de la sección de catálogos (o justo después del bloque de `Catalog`, alrededor de la línea donde estaban los cuatro modelos eliminados).

```python
class OrganCategory(models.TextChoices):
    MINSA = "MINSA", "MINSA"
    UNIVERSIDAD = "UNIVERSIDAD", "Universidad"
    ORGANO_REGIONAL = "ORGANO_REGIONAL", "Órgano regional"
    UNIDAD_EJECUTORA = "UNIDAD_EJECUTORA", "Unidad ejecutora"


class OrganType(models.Model):
    """Tipo de órgano/entidad institucional (unifica cuatro tablas de catálogo previas).

    No hereda de ``Catalog`` porque la unicidad de ``codigo`` es por
    ``organo``, no global — ver ``unique_together``.
    """

    organo = models.CharField(
        "categoría de órgano",
        max_length=20,
        choices=OrganCategory.choices,
        help_text="Categoría del órgano: MINSA, UNIVERSIDAD, ORGANO_REGIONAL o UNIDAD_EJECUTORA",
    )
    codigo = models.CharField("código", max_length=50, help_text="Código del tipo (único dentro de la categoría)")
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre")
    activo = models.BooleanField("activo", default=True, help_text="Indica si está activo")

    class Meta:
        db_table = "tipo_organo"
        verbose_name = "tipo de órgano"
        verbose_name_plural = "tipos de órgano"
        unique_together = (("organo", "codigo"),)
        ordering = ["organo", "codigo"]

    def __str__(self):
        return self.nombre
```

**Criterio:** la clase `OrganType` existe en `models.py`; `OrganCategory` es importable desde `apps.convenios.models`; `db_table = "tipo_organo"`.

---

### T1.3 — Actualizar la FK en `RegionalOrgan`

Ubicación: ~línea 267 (campo `tipo_organo_regional`).

Reemplazar:
```python
tipo_organo_regional = models.ForeignKey(
    RegionalOrganType, on_delete=models.PROTECT, db_column="tipo_organo_regional_id",
    help_text="GERESA / DIRESA / DIRIS",
)
```
Por:
```python
tipo_organo = models.ForeignKey(
    OrganType, on_delete=models.PROTECT, db_column="tipo_organo_id",
    help_text="GERESA / DIRESA / DIRIS (discriminador: ORGANO_REGIONAL)",
)
```

**Criterio:** el campo se llama `tipo_organo`, apunta a `OrganType`, `db_column="tipo_organo_id"`. Ninguna referencia a `RegionalOrganType` queda en el modelo.

---

### T1.4 — Actualizar la FK en `ExecutingUnit`

Ubicación: ~línea 297 (campo `tipo_unidad_ejecutora`).

Reemplazar:
```python
tipo_unidad_ejecutora = models.ForeignKey(
    ExecutingUnitType, on_delete=models.PROTECT, db_column="tipo_unidad_ejecutora_id",
    help_text="Hospital / Instituto / Red",
)
```
Por:
```python
tipo_organo = models.ForeignKey(
    OrganType, on_delete=models.PROTECT, db_column="tipo_organo_id",
    help_text="Hospital / Instituto especializado / Red de salud (discriminador: UNIDAD_EJECUTORA)",
)
```

**Criterio:** el campo se llama `tipo_organo`, apunta a `OrganType`, `db_column="tipo_organo_id"`.

---

### T1.5 — Actualizar la FK en `MinsaOrgan`

Ubicación: ~línea 389 (campo `tipo_organo_minsa`).

Reemplazar:
```python
tipo_organo_minsa = models.ForeignKey(
    MinsaOrganType, on_delete=models.PROTECT, db_column="tipo_organo_minsa_id",
    help_text="DIGEP / OGAJ / SG / VICEPAS",
)
```
Por:
```python
tipo_organo = models.ForeignKey(
    OrganType, on_delete=models.PROTECT, db_column="tipo_organo_id",
    help_text="DIGEP / OGAJ / SG / VICEPAS (discriminador: MINSA)",
)
```

**Criterio:** el campo se llama `tipo_organo`, apunta a `OrganType`, `db_column="tipo_organo_id"`.

---

### T1.6 — Actualizar la FK en `University`

Ubicación: ~línea 468 (campo `tipo_entidad`).

Reemplazar:
```python
tipo_entidad = models.ForeignKey(
    UniversityEntityType, on_delete=models.PROTECT, db_column="tipo_entidad_id",
    help_text="Universidad / Escuela posgrado / Escuela superior / Instituto",
)
```
Por:
```python
tipo_entidad = models.ForeignKey(
    OrganType, on_delete=models.PROTECT, db_column="tipo_entidad_id",
    help_text="Universidad / Escuela posgrado / Escuela superior / Instituto (discriminador: UNIVERSIDAD)",
)
```

Nota: el nombre del campo (`tipo_entidad`) y el `db_column` (`tipo_entidad_id`) se **conservan** para no romper el serializer `ConventionReadSerializer` que referencia `universidad.tipo_entidad.nombre`. Solo cambia el modelo apuntado.

**Criterio:** `University.tipo_entidad` apunta a `OrganType`; el `db_column` sigue siendo `tipo_entidad_id`.

---

## T2 — Migración `0016_unify_organ_types` (`apps/convenios/migrations/`)

Crear el archivo `apps/convenios/migrations/0016_unify_organ_types.py`.

La migración es **irreversible** (`reverse_code=migrations.RunPython.noop` en el sentido contrario para las data migrations; los `DeleteModel` no tienen reversa útil).

### Orden de operaciones dentro de la migración

#### Paso 1 — Crear el modelo `OrganType`

```python
migrations.CreateModel(
    name="OrganType",
    fields=[
        ("id", models.BigAutoField(..., primary_key=True)),
        ("organo", models.CharField(
            verbose_name="categoría de órgano",
            max_length=20,
            choices=[
                ("MINSA", "MINSA"),
                ("UNIVERSIDAD", "Universidad"),
                ("ORGANO_REGIONAL", "Órgano regional"),
                ("UNIDAD_EJECUTORA", "Unidad ejecutora"),
            ],
            help_text="Categoría del órgano: MINSA, UNIVERSIDAD, ORGANO_REGIONAL o UNIDAD_EJECUTORA",
        )),
        ("codigo", models.CharField(verbose_name="código", max_length=50,
            help_text="Código del tipo (único dentro de la categoría)")),
        ("nombre", models.CharField(verbose_name="nombre", max_length=255, help_text="Nombre")),
        ("activo", models.BooleanField(verbose_name="activo", default=True,
            help_text="Indica si está activo")),
    ],
    options={
        "verbose_name": "tipo de órgano",
        "verbose_name_plural": "tipos de órgano",
        "db_table": "tipo_organo",
        "ordering": ["organo", "codigo"],
        "unique_together": {("organo", "codigo")},
    },
)
```

#### Paso 2 — Seed de los 14 registros

`RunPython(seed_organ_types, migrations.RunPython.noop)`

Función `seed_organ_types(apps, schema_editor)`:

```python
ORGAN_TYPE_SEED = [
    # (organo, codigo, nombre)
    ("UNIVERSIDAD",      "UNIVERSIDAD",          "Universidad"),
    ("UNIVERSIDAD",      "ESCUELA_POSGRADO",     "Escuela de posgrado"),
    ("UNIVERSIDAD",      "ESCUELA_SUPERIOR",     "Escuela superior"),
    ("UNIVERSIDAD",      "INSTITUTO",            "Instituto"),
    ("ORGANO_REGIONAL",  "GERESA",               "Gerencia Regional de Salud"),
    ("ORGANO_REGIONAL",  "DIRESA",               "Dirección Regional de Salud"),
    ("ORGANO_REGIONAL",  "DIRIS",                "Dirección de Redes Integradas de Salud"),
    ("UNIDAD_EJECUTORA", "HOSPITAL",             "Hospital"),
    ("UNIDAD_EJECUTORA", "INSTITUTO_ESPECIALIZADO", "Instituto especializado"),
    ("UNIDAD_EJECUTORA", "RED_SALUD",            "Red de salud"),
    ("MINSA",            "DIGEP",                "Dirección General de Personal de la Salud"),
    ("MINSA",            "OGAJ",                 "Oficina General de Asesoría Jurídica"),
    ("MINSA",            "SG",                   "Secretaría General"),
    ("MINSA",            "VICEPAS",              "Despacho Viceministerial de Prestaciones y Aseguramiento en Salud"),
]
```

Usar `get_or_create(organo=organo, codigo=codigo, defaults={"nombre": nombre})`.

**Criterio:** después del seed, `tipo_organo` contiene exactamente 14 filas con los valores listados.

#### Paso 3 — Agregar columnas FK temporales (nullable) en los cuatro modelos referenciantes

Cuatro operaciones `AddField`, una por modelo. Todas con `null=True` (temporal):

- `RegionalOrgan.tipo_organo_nuevo` → FK `tipo_organo`, `db_column="tipo_organo_id_nuevo"`, null=True, on_delete=PROTECT
- `ExecutingUnit.tipo_organo_nuevo` → FK `tipo_organo`, `db_column="tipo_organo_id_nuevo"`, null=True, on_delete=PROTECT
- `MinsaOrgan.tipo_organo_nuevo` → FK `tipo_organo`, `db_column="tipo_organo_id_nuevo"`, null=True, on_delete=PROTECT
- `University.tipo_entidad_nuevo` → FK `tipo_organo`, `db_column="tipo_entidad_id_nuevo"`, null=True, on_delete=PROTECT

Nota: se usan nombres intermedios con sufijo `_nuevo` para evitar colisión con los campos existentes antes de que sean borrados. Si la BD está limpia (sin filas), el implementador puede omitir los pasos 3 y 4 y hacer directamente `AlterField` en paso 5.

#### Paso 4 — Data migration: mapear registros existentes

`RunPython(migrar_fks, migrations.RunPython.noop)`

Función `migrar_fks(apps, schema_editor)`: para cada modelo, recorrer todas las filas y asignar la FK nueva buscando el `OrganType` correspondiente por `(organo, codigo)`:

- `RegionalOrgan`: origen `RegionalOrganType` (código del objeto apuntado por `tipo_organo_regional_id`) → `OrganType` con `organo="ORGANO_REGIONAL"` y mismo `codigo`.
- `ExecutingUnit`: origen `ExecutingUnitType` → `OrganType` con `organo="UNIDAD_EJECUTORA"`.
- `MinsaOrgan`: origen `MinsaOrganType` → `OrganType` con `organo="MINSA"`.
- `University`: origen `UniversityEntityType` (código del objeto apuntado por `tipo_entidad_id`) → `OrganType` con `organo="UNIVERSIDAD"`.

Si la BD está limpia, esta función puede ser un no-op.

**Criterio:** todas las filas de los cuatro modelos tienen la columna `_nuevo` poblada (o la BD estaba vacía).

#### Paso 5 — Eliminar columnas viejas y renombrar las nuevas a los nombres definitivos

Para cada modelo, en orden:

1. `RemoveField` del campo viejo (`tipo_organo_regional`, `tipo_unidad_ejecutora`, `tipo_organo_minsa`, `tipo_entidad`).
2. `RenameField` del campo `_nuevo` al nombre definitivo — pero además se requiere ajustar el `db_column` al valor definitivo. Usar `AlterField` tras el rename para fijar `null=False` y el `db_column` correcto:

Nombres definitivos y `db_column`:

| Modelo | Nombre campo definitivo | `db_column` definitivo |
|---|---|---|
| `RegionalOrgan` | `tipo_organo` | `tipo_organo_id` |
| `ExecutingUnit` | `tipo_organo` | `tipo_organo_id` |
| `MinsaOrgan` | `tipo_organo` | `tipo_organo_id` |
| `University` | `tipo_entidad` | `tipo_entidad_id` |

Tras rename, aplicar `AlterField` para quitar `null=True` (→ `null=False`) y corregir `db_column`.

#### Paso 6 — Eliminar los cuatro modelos viejos

```python
migrations.DeleteModel(name="UniversityEntityType"),
migrations.DeleteModel(name="RegionalOrganType"),
migrations.DeleteModel(name="ExecutingUnitType"),
migrations.DeleteModel(name="MinsaOrganType"),
```

Esto elimina las tablas `tipo_entidad_universidad`, `tipo_organo_regional`, `tipo_unidad_ejecutora` y `tipo_organo_minsa`.

**Criterio de toda T2:** `python manage.py migrate` aplica sin errores; la tabla `tipo_organo` existe con 14 filas; las cuatro tablas viejas no existen; los cuatro modelos referenciantes tienen `tipo_organo_id` (o `tipo_entidad_id` para `University`) como columna NOT NULL apuntando a `tipo_organo`.

---

## T3 — Actualización de `views.py` (`apps/convenios/views.py`)

### T3.1 — Eliminar entradas de los cuatro catálogos/entidades viejas

En el diccionario `CATALOG_VIEWSETS` (~línea 469–481), eliminar la entrada:
```python
"executing-unit-types": _catalog_viewset(m.ExecutingUnitType),
```

En el diccionario `ENTITY_VIEWSETS` (~línea 484–570), eliminar las tres entradas:
```python
"university-entity-types": _entity_viewset(
    m.UniversityEntityType, filterset_fields=["activo"], search_fields=["codigo", "nombre"]
),
"regional-organ-types": _entity_viewset(
    m.RegionalOrganType, filterset_fields=["activo"], search_fields=["codigo", "nombre"]
),
"minsa-organ-types": _entity_viewset(
    m.MinsaOrganType, filterset_fields=["activo"], search_fields=["codigo", "nombre"]
),
```

**Criterio:** ninguna de las cuatro claves eliminadas aparece en `CATALOG_VIEWSETS` ni `ENTITY_VIEWSETS`.

---

### T3.2 — Agregar entrada `organ-types` en `ENTITY_VIEWSETS`

En `ENTITY_VIEWSETS`, dentro del bloque de catálogos maestros con CRUD (junto a `health-geographic-scopes`, `document-types`, etc.), agregar:

```python
"organ-types": _entity_viewset(
    m.OrganType,
    filterset_fields=["organo", "activo"],
    search_fields=["codigo", "nombre"],
),
```

El `_entity_viewset` ya usa `IsAdminRoleOrReadOnly` por defecto — no se necesita sobreescribir `permission_classes`.

**Criterio:** `GET /api/v1/organ-types/` devuelve la lista de los 14 tipos; `POST /api/v1/organ-types/` requiere rol `Administrador RENADS`; filtrar por `?organo=MINSA` devuelve solo los 4 de MINSA; `?activo=true` filtra por activo; búsqueda por `?search=DIGEP` funciona.

---

### T3.3 — Actualizar filterset_fields de entidades que cambian el nombre de su FK

Las entradas de `ENTITY_VIEWSETS` que filtran por el campo FK renombrado deben actualizarse:

- `"regional-organs"` (~línea 524–529): cambiar `"tipo_organo_regional"` → `"tipo_organo"` en `filterset_fields`.
- `"executing-units"` (~línea 530–535): cambiar `"tipo_unidad_ejecutora"` → `"tipo_organo"` en `filterset_fields`.
- `"minsa-organs"` (~línea 537–539): cambiar `"tipo_organo_minsa"` → `"tipo_organo"` en `filterset_fields`.
- `"universities"` (~línea 541–546): cambiar `"tipo_entidad"` → `"tipo_entidad"` (nombre del campo en `University` se mantiene igual, no cambia; verificar que el filterset_field siga siendo `"tipo_entidad"` — no se modifica).

**Criterio:** `GET /api/v1/regional-organs/?tipo_organo=<id>` filtra correctamente. Los endpoints de `executing-units` y `minsa-organs` filtran por `tipo_organo`. El endpoint `universities` sigue filtrando por `tipo_entidad` (campo conservado en `University`).

---

### T3.4 — Actualizar imports de modelos en `views.py`

`views.py` importa `apps.convenios.models as m` y accede a los modelos como `m.UniversityEntityType`, `m.RegionalOrganType`, etc. Tras T1 esos modelos ya no existen, pero las referencias en `CATALOG_VIEWSETS`/`ENTITY_VIEWSETS` fueron eliminadas en T3.1, por lo que no quedan referencias directas. Verificar que no quede ningún uso de los cuatro modelos eliminados en todo el archivo.

**Criterio:** `python -c "from apps.convenios import views"` no lanza `AttributeError` ni `ImportError`.

---

## T4 — Ajuste de `serializers.py` (`apps/convenios/serializers.py`)

### T4.1 — Actualizar referencias en `ConventionReadSerializer`

El `ConventionReadSerializer` (~líneas 41–47) tiene:
```python
tipo_organo_regional = serializers.CharField(
    source="organo_regional.tipo_organo_regional.nombre", read_only=True
)
tipo_entidad_universidad = serializers.CharField(
    source="universidad.tipo_entidad.nombre", read_only=True
)
```

El campo `tipo_entidad` de `University` conserva su nombre, por lo que `universidad.tipo_entidad.nombre` sigue siendo válido. Sin embargo, `tipo_organo_regional` en `RegionalOrgan` cambia a `tipo_organo`. Actualizar la `source`:

```python
tipo_organo_regional = serializers.CharField(
    source="organo_regional.tipo_organo.nombre", read_only=True
)
```

El campo serializado expuesto al cliente sigue llamándose `tipo_organo_regional` (nombre de salida del campo en el response). Solo cambia la `source`.

**Criterio:** `GET /api/v1/conventions/<id>/` devuelve `tipo_organo_regional` con el nombre del tipo de órgano regional; no lanza `AttributeError`.

---

### T4.2 — Verificar ausencia de imports de modelos eliminados

El bloque de imports al inicio de `serializers.py` no importa ninguno de los cuatro modelos eliminados (`UniversityEntityType`, `RegionalOrganType`, `ExecutingUnitType`, `MinsaOrganType`). Verificar y eliminar si existen.

**Criterio:** `python -c "from apps.convenios import serializers"` no lanza ningún error.

---

## T5 — Actualización de documentación

### T5.1 — `docs/db_schema_modulo_01_convenios.md`

Sección 2 (Catálogos), tabla de catálogos (~líneas 44–46 del documento):

Eliminar las tres filas:
```
| `tipo_entidad_universidad` | Tipo de entidad educativa | valores: `UNIVERSIDAD`, `ESCUELA_POSGRADO`, `ESCUELA_SUPERIOR`, `INSTITUTO` |
| `tipo_organo_regional` | Tipo de órgano regional | valores: `GERESA`, `DIRESA`, `DIRIS` |
| `tipo_unidad_ejecutora` | Tipo de unidad ejecutora | valores: `HOSPITAL`, `INSTITUTO_ESPECIALIZADO`, `RED_SALUD` |
| `tipo_organo_minsa` | Órgano del MINSA | valores: `DIGEP`, `OGAJ`, `SG`, `VICEPAS` |
```

Agregar en su lugar (fuera del bloque de catálogos `Catalog`, en una sección propia o al pie de la sección 2):

```
### `tipo_organo` — catálogo unificado de tipos de órgano

No hereda de `Catalog` (unicidad por `(organo, codigo)`, no global).

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `organo` | varchar(20) | No | Categoría: `MINSA`, `UNIVERSIDAD`, `ORGANO_REGIONAL`, `UNIDAD_EJECUTORA` |
| `codigo` | varchar(50) | No | Código del tipo (único dentro de la categoría) |
| `nombre` | varchar(255) | No | Nombre |
| `activo` | bool | No | |

`unique_together = (organo, codigo)`. Seed: 14 registros (ver detalle en spec).

Valores por categoría:
- `UNIVERSIDAD`: `UNIVERSIDAD`, `ESCUELA_POSGRADO`, `ESCUELA_SUPERIOR`, `INSTITUTO`
- `ORGANO_REGIONAL`: `GERESA`, `DIRESA`, `DIRIS`
- `UNIDAD_EJECUTORA`: `HOSPITAL`, `INSTITUTO_ESPECIALIZADO`, `RED_SALUD`
- `MINSA`: `DIGEP`, `OGAJ`, `SG`, `VICEPAS`
```

Actualizar las descripciones de FK en las tablas de entidades:

- Sección 3 (`organo_regional`): `tipo_organo_regional_id` → `tipo_organo_id FK → tipo_organo (PROTECT) | No | GERESA / DIRESA / DIRIS (discriminador ORGANO_REGIONAL)`.
- Sección 3 (`unidad_ejecutora`): `tipo_unidad_ejecutora_id` → `tipo_organo_id FK → tipo_organo (PROTECT) | No | Hospital / Instituto / Red (discriminador UNIDAD_EJECUTORA)`.
- Sección 4 (`organo_minsa`): `tipo_organo_minsa_id` → `tipo_organo_id FK → tipo_organo (PROTECT) | No | DIGEP / OGAJ / SG / VICEPAS (discriminador MINSA)`.
- Sección 6 (`universidad`): `tipo_entidad_id FK → tipo_entidad_universidad` → `tipo_entidad_id FK → tipo_organo (PROTECT) | No | Universidad / Escuela posgrado / ... (discriminador UNIVERSIDAD)`.

**Criterio:** el documento refleja exactamente la tabla `tipo_organo` con sus 14 valores y las FKs actualizadas en las cuatro entidades.

---

### T5.2 — `docs/db_schema_er_global.md`

Localizar las referencias a `tipo_entidad_universidad`, `tipo_organo_regional`, `tipo_unidad_ejecutora` y `tipo_organo_minsa` en el diagrama ER o tablas de relaciones. Reemplazar por `tipo_organo` con el discriminador apropiado.

**Criterio:** el diagrama ER no menciona las cuatro tablas eliminadas; menciona `tipo_organo`.

---

### T5.3 — `CLAUDE.md`, sección §catálogos (bajo "Requerimientos no funcionales clave para el API")

Localizar la enumeración de catálogos maestros con CRUD. Actualmente incluye:
> `university-entity-types`, `regional-organ-types`, `minsa-organ-types`

Reemplazar esas tres entradas por `organ-types`. Eliminar también `executing-unit-types` de la mención de catálogos de solo lectura si aparece explícitamente.

**Criterio:** `CLAUDE.md` menciona `organ-types` en lugar de las cuatro entradas eliminadas.

---

## Criterios de aceptación globales

1. `python manage.py makemigrations --check` no genera nuevas migraciones (el estado de los modelos coincide con la última migración `0016`).
2. `python manage.py migrate` aplica `0016` sin errores sobre una BD limpia.
3. `GET /api/v1/organ-types/` devuelve 200 con los 14 registros seed.
4. `GET /api/v1/organ-types/?organo=MINSA` devuelve exactamente 4 registros.
5. `GET /api/v1/organ-types/?organo=ORGANO_REGIONAL` devuelve exactamente 3 registros.
6. `POST /api/v1/organ-types/` con token de usuario no-admin devuelve 403.
7. `POST /api/v1/organ-types/` con token de `Administrador RENADS` y body `{"organo":"MINSA","codigo":"NUEVO","nombre":"Nuevo","activo":true}` devuelve 201 y el registro aparece en la BD.
8. `GET /api/v1/university-entity-types/` devuelve 404 (endpoint eliminado).
9. `GET /api/v1/regional-organ-types/` devuelve 404.
10. `GET /api/v1/minsa-organ-types/` devuelve 404.
11. `GET /api/v1/executing-unit-types/` devuelve 404.
12. `GET /api/v1/regional-organs/?tipo_organo=<id>` filtra correctamente.
13. `GET /api/v1/executing-units/?tipo_organo=<id>` filtra correctamente.
14. `GET /api/v1/minsa-organs/?tipo_organo=<id>` filtra correctamente.
15. `GET /api/v1/universities/?tipo_entidad=<id>` sigue filtrando correctamente.
16. `GET /api/v1/conventions/<id>/` devuelve `tipo_organo_regional` (nombre del tipo) sin `AttributeError`.
17. `python -c "from apps.convenios import models, views, serializers"` no lanza ningún error.

---

## Referencias

- Schema M1: `docs/db_schema_modulo_01_convenios.md` §2 (Catálogos), §3 (órgano_regional, unidad_ejecutora), §4 (organo_minsa), §6 (universidad).
- Modelos actuales: `apps/convenios/models.py` líneas ~135–181 (modelos eliminados), ~267 (`RegionalOrgan.tipo_organo_regional`), ~297 (`ExecutingUnit.tipo_unidad_ejecutora`), ~389 (`MinsaOrgan.tipo_organo_minsa`), ~468 (`University.tipo_entidad`).
- Views actuales: `apps/convenios/views.py` líneas ~469–570 (`CATALOG_VIEWSETS`, `ENTITY_VIEWSETS`).
- Serializers: `apps/convenios/serializers.py` líneas ~41–47 (`ConventionReadSerializer`).
- Última migración existente: `apps/convenios/migrations/0015_clinical_field_registration_allocation.py` — la nueva migración se numera `0016`.
- Patrón `Red`/`Microred` en `models.py` (líneas ~46–96): referencia de cómo implementar un modelo con `unique_together` sin heredar de `Catalog`.
- Patrón `_entity_viewset` en `views.py` (~líneas 386–420): referencia para el nuevo viewset de `OrganType`.
