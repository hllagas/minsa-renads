# Spec — Refactor Convenios: modelo dedicado `UniversityEntityType` para `universidad.tipo_entidad`

> **Metodología SDD.** Este archivo es la fuente de tareas para el agente `implement`.
> `implement` desarrolla en `apps/convenios/` y actualiza `docs/`; `validator` revisa contra
> este spec, la arquitectura y el schema. No se avanza sin spec ni se cierra sin validación.

---

## 1. Resumen del módulo

Refactor del módulo **Gestionar Convenios** (app `apps/convenios`). La columna
`universidad.tipo_entidad_id` actualmente es FK a `organo_directorio` con
`limit_choices_to={"organo__nombre": "Universidad"}`, lo que acopla un catálogo semántico
propio del dominio universitario a la tabla genérica de directorio de órganos.

Se reemplaza esa FK por un modelo dedicado `UniversityEntityType` (tabla
`tipo_entidad_universidad`), con 4 tipos fijos sembrados en migración. El endpoint es de
**solo lectura**; ningún actor del MVP necesita crear ni modificar tipos de entidad
universitaria en tiempo de ejecución.

### Entidades cubiertas

| Entidad / Tabla | Rol en este refactor |
|----------------|----------------------|
| `UniversityEntityType` / `tipo_entidad_universidad` | **Nueva**. Catálogo de 4 tipos fijos |
| `University` / `universidad` | FK `tipo_entidad_id` apunta al nuevo modelo (antes → `organo_directorio`) |
| `OrganDirectory` / `organo_directorio` | Solo deja de ser destino de la FK de `universidad`; sin otros cambios |

### Tipos semilla (exactamente 4, en ese orden)

| nombre |
|--------|
| Universidad |
| Instituto |
| Escuela superior |
| Escuela de posgrado |

### Alcance y decisiones confirmadas por el usuario

1. **Endpoint solo lectura:** `GET /api/v1/university-entity-types/`. Sin CRUD. Sin paginación especial.
2. **Seed fijo en migración:** los 4 tipos se siembran en la misma migración que crea la tabla.
3. **Criterio de migración de datos:** el backfill de `universidad.tipo_entidad_id` se realiza
   por **nombre coincidente** entre `organo_directorio.nombre` y `UniversityEntityType.nombre`.
4. **Documentación:** actualizar `docs/db_schema_modulo_01_convenios.md` y
   `docs/api_almacenamiento_frontend.md` (referencia de endpoints del frontend).

### Fuera de alcance

- No tocar la tabla `organo_directorio` ni sus filas.
- No modificar el endpoint `/api/v1/universities/` más allá de cambiar la FK interna y
  ajustar los `detalles` y `filterset_fields`.
- No añadir lógica de negocio en `services.py` (este refactor no incorpora nuevas RN).
- No ejecutar `migrate` ni `test` (los corre el usuario).
- No corregir la discrepancia `organo_directorio.categoria` fuera de alcance (solo reportar
  si impide `check`/`makemigrations`).

---

## 2. Estado actual verificado

- `University.tipo_entidad` (`apps/convenios/models.py` aprox. L647-651):
  FK a `OrganDirectory`, `on_delete=PROTECT`, `db_column="tipo_entidad_id"`,
  `limit_choices_to={"organo__nombre": "Universidad"}`.
- Vista `universities` en `ENTITY_VIEWSETS` (`views.py` aprox. L935-945):
  `filterset_fields=["tipo_gestion", "tipo_entidad", "tipo_autorizacion", "activo"]`,
  `detalles={"tipo_gestion": _detalle_nombre, "tipo_entidad": _detalle_nombre, ...}`.
- `ConventionReadSerializer` (`serializers.py` aprox. L47-49): campo de solo lectura
  `tipo_entidad_universidad = serializers.CharField(source="universidad.tipo_entidad.nombre")`.
  Depende de que el objeto relacionado tenga atributo `nombre` — se preserva sin cambios
  funcionales (el nuevo modelo también tiene `nombre`).
- Selector `convenios_visibles` (`selectors.py` aprox. L24-28):
  `select_related("universidad__tipo_entidad", ...)`. El nombre del campo no cambia; solo
  cambia el modelo destino del JOIN.
- Última migración de la app `convenios`: `0051_remove_campo_clinico_ipress_convenio.py`.
  La nueva migración será **`0052`**.

---

## 3. Tareas por capa

### Capa Modelo — `apps/convenios/models.py`

**T1 — Nuevo modelo `UniversityEntityType`.**

Añadir el modelo inmediatamente antes de la clase `University` (o junto a los catálogos, según
el orden lógico del archivo). No debe heredar de `Catalog` (no tiene campo `codigo`).

```python
class UniversityEntityType(models.Model):
    """Tipo de entidad universitaria (catálogo fijo: Universidad, Instituto, etc.)."""

    nombre = models.CharField(
        "nombre", max_length=100, unique=True,
        help_text="Nombre del tipo de entidad universitaria",
    )
    activo = models.BooleanField(
        "activo", default=True,
        help_text="Indica si el tipo está activo",
    )

    class Meta:
        db_table = "tipo_entidad_universidad"
        verbose_name = "tipo de entidad universitaria"
        verbose_name_plural = "tipos de entidad universitaria"
        ordering = ["id"]

    def __str__(self):
        return self.nombre
```

**Criterio de aceptación:** `python manage.py check` pasa; `db_table` es
`tipo_entidad_universidad`; campos `id` (auto), `nombre` (varchar 100, unique), `activo`
(bool, default True).

---

**T2 — Actualizar FK `University.tipo_entidad`.**

Reemplazar la FK actual a `OrganDirectory` por una FK al nuevo modelo:

```python
tipo_entidad = models.ForeignKey(
    UniversityEntityType,
    on_delete=models.PROTECT,
    db_column="tipo_entidad_id",
    help_text="Tipo de entidad universitaria",
)
```

Eliminar el `limit_choices_to`. Conservar `on_delete=PROTECT` y `db_column="tipo_entidad_id"`.

**Criterio de aceptación:** `python manage.py check` pasa; la FK apunta a
`UniversityEntityType`; no existe `limit_choices_to`; `db_column` permanece `tipo_entidad_id`.

---

### Capa Migración — `apps/convenios/migrations/0052_*.py`

**T3 — Migración integral de 4 pasos.**

Crear una única migración `0052` dependiente de `0051` con las siguientes operaciones en orden:

**Paso 1 — Crear tabla `tipo_entidad_universidad`** (`CreateModel`):
- Campos: `id` (AutoField PK), `nombre` (varchar 100, unique), `activo` (bool default True).

**Paso 2 — Sembrar los 4 tipos** (`RunPython`, `reverse_code=RunPython.noop`):
- Insertar los 4 tipos en el orden exacto indicado:
  `"Universidad"`, `"Instituto"`, `"Escuela superior"`, `"Escuela de posgrado"`.
- Usar modelos históricos (`apps.get_model("convenios", "UniversityEntityType")`).
- Código de muestra del `RunPython`:

  ```python
  def seed_tipos(apps, schema_editor):
      UET = apps.get_model("convenios", "UniversityEntityType")
      for nombre in ["Universidad", "Instituto", "Escuela superior", "Escuela de posgrado"]:
          UET.objects.get_or_create(nombre=nombre, defaults={"activo": True})
  ```

**Paso 3 — Migrar datos de `universidad.tipo_entidad_id`** (`RunPython`, `reverse_code=RunPython.noop`):
- Para cada fila de `universidad`, buscar en `tipo_entidad_universidad` la fila cuyo
  `nombre` coincide exactamente con `organo_directorio.nombre` del `tipo_entidad_id`
  actual.
- Actualizar `universidad.tipo_entidad_id` al nuevo `id` encontrado.
- Si una universidad no tiene coincidencia por nombre, asignarla al tipo `"Universidad"`
  (primera fila sembrada) como default de seguridad, y **registrar un warning** (con
  `print()` o `logging.warning`) que incluya el id de la universidad y el nombre del
  directorio que no coincidió.
- Usar modelos históricos:

  ```python
  def migrar_tipo_entidad(apps, schema_editor):
      Universidad = apps.get_model("convenios", "University")
      UET = apps.get_model("convenios", "UniversityEntityType")
      OD = apps.get_model("convenios", "OrganDirectory")
      default_tipo = UET.objects.get(nombre="Universidad")
      for univ in Universidad.objects.select_related("tipo_entidad").all():
          od = OD.objects.filter(pk=univ.tipo_entidad_id).first()
          nombre_od = od.nombre if od else None
          nuevo = UET.objects.filter(nombre=nombre_od).first() if nombre_od else None
          if nuevo is None:
              print(
                  f"[WARN] Universidad id={univ.pk} nombre={univ.nombre!r}: "
                  f"tipo_entidad organo_directorio.nombre={nombre_od!r} sin coincidencia "
                  f"-> asignando default 'Universidad'."
              )
              nuevo = default_tipo
          univ.tipo_entidad_id = nuevo.pk
          univ.save(update_fields=["tipo_entidad_id"])
  ```

  > Nota: durante la ejecución del paso 3, la columna `tipo_entidad_id` todavía apunta
  > al schema antiguo (FK a `organo_directorio`). El paso 4 es el que cambia el
  > constraint de FK. Usar `update_fields=["tipo_entidad_id"]` para evitar cambios
  > colaterales. En SQLite `RunPython` puede actualizar la columna sin que Django exija
  > que el nuevo valor sea válido según el constraint antiguo; en PostgreSQL tampoco es
  > problema porque el `AlterField` del paso 4 reemplaza el constraint completo.

**Paso 4 — Cambiar la FK** (`AlterField`):
- Alterar `universidad.tipo_entidad` para que apunte a `tipo_entidad_universidad` en lugar
  de `organo_directorio`. Estado final: `ForeignKey("UniversityEntityType", on_delete=PROTECT,
  db_column="tipo_entidad_id")` — coincidente con el modelo de T2.
- La columna `tipo_entidad_id` **no cambia de nombre** (sigue siendo `tipo_entidad_id`);
  solo cambia la FK constraint que la referencia.

**Criterios de aceptación de T3:**
- `python manage.py makemigrations --check --dry-run` no reporta cambios pendientes tras
  crear la migración.
- `python manage.py check` pasa.
- La migración es nominalmente reversible (los `RunPython` tienen `reverse_code=noop`, los
  `CreateModel`/`AlterField` son reversibles por Django).
- **No ejecutar `migrate`** (lo corre el usuario).

---

### Capa Serializers — `apps/convenios/serializers.py`

**T4 — Ajuste en `ConventionReadSerializer`.**

El campo `tipo_entidad_universidad` (aprox. L47-49) usa
`source="universidad.tipo_entidad.nombre"`. Como el nuevo modelo también tiene el atributo
`nombre`, **no se requiere cambio funcional**. Sin embargo, verificar que el `select_related`
del selector (`selectors.py` L26: `"universidad__tipo_entidad"`) sigue siendo correcto tras el
cambio de destino de FK — no se modifica la cadena de `select_related` porque el nombre del
campo de acceso (`tipo_entidad`) es el mismo.

No se crea un serializer específico para `UniversityEntityType` en este archivo; vive en
`views.py` (ver T6).

**Criterio de aceptación:** `ConventionReadSerializer` serializa sin error; el campo
`tipo_entidad_universidad` en la respuesta de `GET /api/v1/conventions/{id}/` sigue devolviendo
el nombre del tipo como cadena de texto.

---

### Capa ViewSets / Serializer del catálogo — `apps/convenios/views.py`

**T5 — Importar `UniversityEntityType` en `views.py`.**

Añadir `UniversityEntityType` a los modelos importados desde `apps.convenios.models` (alias `m`)
o al bloque de importaciones explícitas, según el patrón existente.

**Criterio de aceptación:** `from apps.convenios import models as m` es suficiente si el
modelo está en `models.py`; verificar que `m.UniversityEntityType` resuelve sin `AttributeError`.

---

**T6 — Serializer `UniversityEntityTypeSerializer` y viewset `UniversityEntityTypeViewSet`.**

Seguir el patrón de `_catalog_viewset` para catálogos de solo lectura. No usar `_catalog_viewset`
directamente (ese helper añade el filtro `activo` y la búsqueda `codigo`, y asume el campo
`codigo` del modelo `Catalog`). Crear una clase explícita:

```python
class UniversityEntityTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """Tipos de entidad universitaria (catálogo fijo, solo lectura)."""

    queryset = m.UniversityEntityType.objects.all()
    serializer_class = _auto_serializer(m.UniversityEntityType)
    permission_classes = [IsAuthenticated]
    filterset_fields = ["activo"]
    search_fields = ["nombre"]
    ordering_fields = ["id", "nombre"]
    ordering = ["id"]
```

El serializer generado por `_auto_serializer(m.UniversityEntityType)` expone los campos
`id`, `nombre`, `activo` (todos los del modelo). No se necesita serializer de escritura.

**Criterios de aceptación:**
- `GET /api/v1/university-entity-types/` devuelve lista de objetos `{id, nombre, activo}`.
- `GET /api/v1/university-entity-types/{id}/` devuelve el detalle de un tipo.
- `POST /api/v1/university-entity-types/` devuelve 405 (ReadOnlyModelViewSet).
- El permiso mínimo es `IsAuthenticated` (sin rol especial para lectura).
- La respuesta no usa paginación especial (la paginación global del proyecto aplica si
  está configurada globalmente; de lo contrario, sin paginación).

---

**T7 — Registrar `university-entity-types` en `CATALOG_VIEWSETS`.**

En `views.py`, añadir la entrada en el diccionario `CATALOG_VIEWSETS` (o crear una entrada
directa en el router si la semántica de solo lectura difiere de los catálogos existentes).
Dado que `UniversityEntityTypeViewSet` es un `ReadOnlyModelViewSet` explícito, añadirlo
**directamente** a `CATALOG_VIEWSETS`:

```python
CATALOG_VIEWSETS = {
    ...
    "university-entity-types": UniversityEntityTypeViewSet,
}
```

**Criterio de aceptación:** el router de `apps/convenios/urls.py` registra el viewset al
iterar `CATALOG_VIEWSETS`; el endpoint está accesible en `/api/v1/university-entity-types/`.

---

**T8 — Actualizar el viewset `universities` en `ENTITY_VIEWSETS`.**

La entrada `"universities"` en `ENTITY_VIEWSETS` (aprox. L935-945) tiene:
- `filterset_fields=["tipo_gestion", "tipo_entidad", "tipo_autorizacion", "activo"]`
- `detalles={"tipo_gestion": _detalle_nombre, "tipo_entidad": _detalle_nombre, "tipo_autorizacion": _detalle_nombre}`

Estos dos puntos **no requieren cambio de código** porque:
1. `filterset_fields` filtra por el nombre del campo Django (`tipo_entidad`), no por el modelo
   destino. El filtro `?tipo_entidad=<id>` seguirá funcionando con los nuevos IDs.
2. `_detalle_nombre` extrae `{id, codigo, nombre}`; como `UniversityEntityType` no tiene
   `codigo`, el extractor devuelve `{id, codigo: None, nombre}`. Esto es aceptable para el
   frontend (ya ocurre con otros catálogos sin código).

**Acción requerida:** verificar que `_detalle_nombre` no falla ante un modelo sin `codigo`
(usa `getattr(rel, "codigo", None)` — debería devolver `None` sin error). Si falla, ajustar
el extractor del detalle `tipo_entidad` a una lambda explícita:
`lambda rel: {"id": rel.pk, "nombre": rel.nombre}`.

**Criterio de aceptación:** `GET /api/v1/universities/` devuelve `tipo_entidad` (id) y
`tipo_entidad_detalle` (`{id, nombre}` o `{id, codigo: None, nombre}`) sin error 500.

---

### Capa URLs — `apps/convenios/urls.py`

**T9 — Sin cambios en `urls.py`.**

El archivo `apps/convenios/urls.py` itera `CATALOG_VIEWSETS` y registra todos los basenames
automáticamente:

```python
for basename, viewset in views.CATALOG_VIEWSETS.items():
    router.register(basename, viewset, basename=basename)
```

Al agregar `"university-entity-types"` a `CATALOG_VIEWSETS` en T7, el router lo recoge sin
modificar `urls.py`. Verificar que no haya registro manual duplicado.

**Criterio de aceptación:** el endpoint `/api/v1/university-entity-types/` está accesible
tras el cambio en `CATALOG_VIEWSETS`; `urls.py` no requiere edición.

---

### Capa Docs — sincronizar en el mismo cambio

**T10 — `docs/db_schema_modulo_01_convenios.md`.**

Realizar los siguientes cambios en el documento:

1. **Sección de catálogos** (tabla de la sección 2, aprox. L28-48): agregar fila para el nuevo
   catálogo:
   ```
   | `tipo_entidad_universidad` | Tipo de entidad universitaria. Seed fijo: 4 tipos. | — |
   ```

2. **Tabla `tipo_organo` — RETIRADA** (aprox. L105-111): actualizar la fila que describe
   la reapuntación de `universidad.tipo_entidad_id`. Reemplazar:
   > `universidad.tipo_entidad_id` → `organo_directorio` (categoría `UNIVERSIDAD`).

   Por:
   > `universidad.tipo_entidad_id` → `tipo_entidad_universidad` (refactorizado en migración
   > `0052`; antes apuntaba a `organo_directorio`).

3. **Sección `universidad`** (tabla de columnas, aprox. L248): actualizar la fila:
   ```
   | `tipo_entidad_id` | FK → `tipo_entidad_universidad` (PROTECT) | No | Tipo de entidad universitaria |
   ```
   (antes decía `FK → organo_directorio (PROTECT)` con `limit_choices_to`).

4. **Agregar sección nueva** `tipo_entidad_universidad` (puede ir en la sección 2 de
   catálogos, o como subsección de la sección 6 Universidades):
   ```
   ### `tipo_entidad_universidad`

   Catálogo fijo de tipos de entidad universitaria. Seed en migración `0052`.

   | Columna | Tipo | Null | Descripción |
   |---------|------|------|-------------|
   | `id` | PK | No | |
   | `nombre` | varchar(100) | No | Nombre del tipo (único) |
   | `activo` | bool | No | |

   Valores seed: `Universidad`, `Instituto`, `Escuela superior`, `Escuela de posgrado`.

   Endpoint: `/api/v1/university-entity-types/` (solo lectura, `IsAuthenticated`;
   filtros `activo`; búsqueda `nombre`).
   ```

5. **Resumen de relaciones** (aprox. L716): actualizar la línea de `universidad` para que
   referencie `tipo_entidad_universidad` en lugar de `organo_directorio`:
   > `universidad >── tipo_gestion_universidad / tipo_entidad_universidad / tipo_autorizacion`

**Criterio de aceptación:** el `.md` describe correctamente la nueva tabla, la columna FK
actualizada y el endpoint de solo lectura.

---

**T11 — `docs/api_almacenamiento_frontend.md` — sección `university-entity-types`.**

Añadir una sección (o una nota al final de la sección de catálogos de universidades si ya
existe) con el siguiente contenido:

```markdown
## Tipos de entidad universitaria — `GET /api/v1/university-entity-types/`

Catálogo de solo lectura con los 4 tipos de entidad universitaria del sistema.

### Respuesta

```json
[
  { "id": 1, "nombre": "Universidad", "activo": true },
  { "id": 2, "nombre": "Instituto", "activo": true },
  { "id": 3, "nombre": "Escuela superior", "activo": true },
  { "id": 4, "nombre": "Escuela de posgrado", "activo": true }
]
```

### Uso

- Poblar el selector de tipo de entidad al crear o editar una universidad
  (`POST /api/v1/universities/` body `tipo_entidad: <id>`).
- Filtrar universidades por tipo: `GET /api/v1/universities/?tipo_entidad=<id>`.

### Breaking change — IDs de `tipo_entidad`

> Los IDs del campo `tipo_entidad` de `universidad` **cambiaron** tras la migración `0052`.
> Antes referenciaban filas de `organo_directorio`; ahora referencian filas de
> `tipo_entidad_universidad`. Los IDs numéricos son distintos.
>
> Si el frontend guardaba IDs de `tipo_entidad` en caché o en URLs, debe refresar el
> catálogo llamando a `GET /api/v1/university-entity-types/` para obtener los nuevos IDs.
> Los filtros `?tipo_entidad=<id>` en `GET /api/v1/universities/` esperan los nuevos IDs.
```

**Criterio de aceptación:** el archivo documenta el endpoint, su respuesta, su uso como
filtro y el breaking change de IDs.

---

## 4. Mapa Regla → Capa

| # | Regla / decisión | Capa de implementación |
|---|------------------|------------------------|
| D1 | La tabla `tipo_entidad_universidad` tiene exactamente 4 filas fijas | Migración paso 2 (`RunPython` seed) |
| D2 | La FK `universidad.tipo_entidad_id` apunta al nuevo modelo | Modelo T2 + Migración paso 4 (`AlterField`) |
| D3 | Datos existentes se migran por nombre coincidente | Migración paso 3 (`RunPython` backfill) |
| D4 | Universidad sin coincidencia → default `"Universidad"` + warning | Migración paso 3 (`RunPython`) |
| D5 | Integridad referencial: no borrar tipo usado | Modelo (`on_delete=PROTECT`) |
| D6 | Solo lectura en API | ViewSet `ReadOnlyModelViewSet` (T6) |
| D7 | `IsAuthenticated` mínimo para leer | `permission_classes` del ViewSet (T6) |

**No hay reglas de negocio (RN) nuevas:** este refactor es estructural (reapuntar una FK);
ninguna validación de negocio cambia. No se toca `services.py`.

---

## 5. Referencias schema / código

- Modelo nuevo a crear: `apps/convenios/models.py` — clase `UniversityEntityType` antes de
  `University`.
- FK a actualizar: `University.tipo_entidad` (`models.py` aprox. L647-651).
- Selector a verificar (sin modificar): `apps/convenios/selectors.py` —
  `select_related("universidad__tipo_entidad", ...)` (aprox. L26).
- Serializer a verificar (sin modificar funcionalmente): `apps/convenios/serializers.py` —
  `ConventionReadSerializer.tipo_entidad_universidad` (aprox. L47-49).
- ViewSet nuevo: `apps/convenios/views.py` — `UniversityEntityTypeViewSet` + entrada en
  `CATALOG_VIEWSETS`.
- ViewSet a verificar: `apps/convenios/views.py` — entrada `"universities"` en `ENTITY_VIEWSETS`
  (aprox. L935-945); `_detalle_nombre` helper (aprox. L499-507).
- URLs: `apps/convenios/urls.py` — iteración de `CATALOG_VIEWSETS` (sin edición directa).
- Migraciones: última = `0051`; nueva = `0052`.
- Tablas/columnas: nueva tabla `tipo_entidad_universidad` (`id`, `nombre`, `activo`);
  columna `universidad.tipo_entidad_id` conserva nombre, cambia FK constraint.
- Docs a sincronizar: `docs/db_schema_modulo_01_convenios.md`,
  `docs/api_almacenamiento_frontend.md`.

---

## 6. Checklist de verificación para `validator`

- [ ] `UniversityEntityType` existe en `models.py`: `db_table="tipo_entidad_universidad"`,
      campos `id` (auto PK), `nombre` (varchar 100, unique), `activo` (bool default True);
      no hereda de `Catalog`; `__str__` devuelve `nombre`.
- [ ] `University.tipo_entidad` apunta a `UniversityEntityType`, `on_delete=PROTECT`,
      `db_column="tipo_entidad_id"`, sin `limit_choices_to`.
- [ ] Migración `0052` contiene los 4 pasos en orden: `CreateModel` → seed `RunPython` →
      backfill `RunPython` → `AlterField`; depende de `0051`.
- [ ] Seed: exactamente 4 filas — `"Universidad"`, `"Instituto"`, `"Escuela superior"`,
      `"Escuela de posgrado"` — en ese orden (o al menos con esos nombres).
- [ ] Backfill: matching por nombre con default `"Universidad"` + warning si no coincide.
- [ ] `python manage.py makemigrations --check --dry-run` sin cambios pendientes.
- [ ] `python manage.py check` pasa.
- [ ] `UniversityEntityTypeViewSet` es `ReadOnlyModelViewSet`; `permission_classes=[IsAuthenticated]`;
      `filterset_fields=["activo"]`; `search_fields=["nombre"]`; serializer expone `id/nombre/activo`.
- [ ] `university-entity-types` registrado en `CATALOG_VIEWSETS`; accesible vía
      `GET /api/v1/university-entity-types/`.
- [ ] `POST /api/v1/university-entity-types/` devuelve 405.
- [ ] `GET /api/v1/universities/` devuelve `tipo_entidad` (id) y `tipo_entidad_detalle`
      (`{id, nombre}`) sin error 500 con los nuevos IDs.
- [ ] `GET /api/v1/universities/?tipo_entidad=<id>` filtra correctamente con nuevos IDs.
- [ ] `ConventionReadSerializer.tipo_entidad_universidad` sigue devolviendo el nombre como
      cadena en `GET /api/v1/conventions/{id}/`.
- [ ] `docs/db_schema_modulo_01_convenios.md` actualizado: nueva tabla `tipo_entidad_universidad`,
      columna `universidad.tipo_entidad_id` actualizada, sección de relaciones actualizada.
- [ ] `docs/api_almacenamiento_frontend.md` contiene sección `university-entity-types` con
      endpoint, respuesta ejemplo y nota de breaking change de IDs.
- [ ] `services.py` **no modificado**.
- [ ] `apps/convenios/urls.py` **no modificado directamente** (el router recoge la entrada
      nueva de `CATALOG_VIEWSETS` automáticamente).
- [ ] `migrate` y `test` **no ejecutados** por `implement`.

---

## 7. Notas y bloqueantes

- **Posible bloqueante de datos:** si existen universidades con `tipo_entidad_id` apuntando a
  un `organo_directorio` cuyo `nombre` no coincide con ninguno de los 4 tipos seed, el backfill
  las asigna al default `"Universidad"` y emite un warning. `implement` debe reportar al usuario
  si se producen esos warnings al ejecutar la migración; no es un error fatal, pero el usuario
  debe verificar la asignación final.
- **Breaking change de IDs:** los IDs de `tipo_entidad` en `universidad` cambian tras la
  migración. El frontend debe refrescar el catálogo `university-entity-types` y no usar IDs
  cacheados de `organo_directorio`. Este cambio debe comunicarse al equipo de frontend antes
  de desplegar.
- **`_detalle_nombre` y campo `codigo` ausente:** `_detalle_nombre` usa `getattr(rel, "codigo", None)`.
  Si por algún motivo falla en lugar de devolver `None`, la solución es un lambda explícito
  `{"id": rel.pk, "nombre": rel.nombre}` para el detalle de `tipo_entidad` en el viewset
  `universities`. `implement` debe verificarlo y aplicar el ajuste si es necesario.
- **Convenciones:** nombres de tabla/columna, `help_text`, `verbose_name` y mensajes de error
  en **español**; identificadores de código en **inglés**.
- **Comandos permitidos a `implement`:** `.venv\Scripts\Activate.ps1`, `makemigrations`,
  `makemigrations --check`, `check`. **Prohibidos:** `migrate`, `test`, `runserver`.
