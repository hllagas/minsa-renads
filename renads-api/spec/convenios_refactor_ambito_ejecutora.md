# Spec — Refactor Ámbito Geográfico Sanitario + Unidad Ejecutora

**Módulo:** `apps/convenios`  
**Próxima migración base:** `0042_executiveposition_organo` (el refactor comienza en `0043`).  
**Modelos afectados:** `HealthGeographicScope`, `ExecutingUnit`, `Ipress`, `Convention`.  
**App internados:** no referencia `ExecutingUnit`; la FK de `Internship.campo_clinico` apunta a `ClinicalFieldAllocation`, no a `ExecutingUnit` directamente.

---

## Resumen

Dos refactors independientes pero relacionados en la jerarquía geográfica del módulo:

1. **Refactor 1 — `HealthGeographicScope`:** añadir FK nullable `gobierno_regional` al ámbito geográfico sanitario para registrar qué GORE corresponde a cada DISA/GERESA/DIRESA (los 4 DIRIS de Lima Metropolitana quedan en NULL). Con data migration de backfill.

2. **Refactor 2 — `ExecutingUnit`:** rediseño estructural de la tabla `unidad_ejecutora`. Reemplaza la PK `id` (AutoField) por `codigo` (CharField 4), elimina los campos `tipo_organo`, `gobierno_regional`, `direccion`, `ubigeo`, `referencia_logo` (incluidas las FKs a `OrganDirectory` y `RegionalGovernment`) y agrega FK `ambito_geografico_sanitario` como único vínculo geográfico. Las dos tablas que referencian `ExecutingUnit` por su PK entera (`ipress.unidad_ejecutora_id` y `convenio.unidad_ejecutora_id`) deben migrarse al nuevo PK textual.

**Separación en tres migraciones:**

- `0043` — Refactor 1: campo `gobierno_regional` en `HealthGeographicScope` + backfill.
- `0044` — Refactor 2 parte A: añadir `codigo_nuevo` a `ExecutingUnit`, columnas transitorias en `ipress`/`convenio`, backfill de datos; mantiene la tabla en su estado actual para no romper el servidor durante el deploy.
- `0045` — Refactor 2 parte B: promover `codigo_nuevo` a PK, redireccionar FKs, eliminar campos obsoletos, renombrar columna.

La razón de separar `0044` y `0045` es que SQLite no soporta DROP COLUMN en versiones anteriores a 3.35 ni ALTER TABLE para cambiar tipo de PK en una sola operación; Django necesita reconstruir la tabla. Dos migraciones distintas permiten hacer el backfill de datos en `0044` (RunPython sin DDL de riesgo) y la restructuración DDL en `0045` (que Django traduce a recreación de tabla en SQLite).

---

## Análisis del estado actual

### `HealthGeographicScope` (`ambito_geografico_sanitario`)

Modelo actual (`models.py:41`):
- Hereda de `Catalog`: campos `codigo` (varchar 50, único), `nombre` (varchar 255), `activo`.
- `db_table = "ambito_geografico_sanitario"`.
- No tiene FK a `RegionalGovernment`. La relación semántica GORE↔ámbito existe en los datos pero no está modelada.

Tablas que la referencian: `red` (PROTECT), `ipress` (PROTECT) — ninguna requiere cambio por este refactor.

### `ExecutingUnit` (`unidad_ejecutora`)

Modelo actual (`models.py:347`):
- PK: `id` AutoField (implícita de Django).
- `codigo` CharField(50), blank=True — ya existe como dato, pero NO es PK.
- `nombre` CharField(255).
- `tipo_organo` FK → `OrganDirectory` (PROTECT, `limit_choices_to` Unidad Ejecutora).
- `gobierno_regional` FK → `RegionalGovernment` (PROTECT, `related_name='unidades_ejecutoras'`).
- `direccion` CharField(500, blank=True).
- `ubigeo` FK → `Ubigeo` (PROTECT, null=True).
- `referencia_logo` ImageField (null=True).
- `activo` BooleanField(default=True).

Tablas que la referencian:
- `ipress.unidad_ejecutora_id` FK(PROTECT, not null) — tabla `ipress`.
- `convenio.unidad_ejecutora_id` FK(PROTECT, null=True) — tabla `convenio`.
- `internados`: ninguna referencia directa a `ExecutingUnit` (verificado en `apps/internados/models.py`).

### Campos de `pdf.py` afectados

`pdf.py:72` — `_domicilio_entidad`: rama `"UNIDAD_EJECUTORA"` hace `getattr(convenio.unidad_ejecutora, "direccion", "") or ""`. El campo `direccion` se elimina. Sustituir por `""` (cadena vacía): la unidad ejecutora ya no tiene dirección propia; la dirección del expediente se toma del ámbito geográfico sanitario si se requiere (fuera del alcance MVP, la plantilla Word simplemente recibirá cadena vacía en ese campo).

### Campos del viewset `executing-units` afectados

`views.py:856` — `filterset_fields=["tipo_organo", "gobierno_regional", "activo"]`. Filtros `tipo_organo` y `gobierno_regional` desaparecen; se reemplaza por `ambito_geografico_sanitario`.

`views.py:861` — `detalles={"tipo_organo": ..., "gobierno_regional": ..., "ubigeo": ...}`. Los tres detalles FK desaparecen; se añade `ambito_geografico_sanitario`.

`views.py:859` — `logo=True` desaparece: el modelo ya no tiene `referencia_logo`.

### Impacto en serializer `ConventionReadSerializer`

`serializers.py:75` — `get_unidad_ejecutora_detalle`: hace `_detalle_fk(obj.unidad_ejecutora, "nombre", "codigo")`. Sigue funcionando porque `nombre` y `codigo` permanecen. Sin cambio material.

---

## Lista de tareas

---

### MIGRACIÓN 0043 — Refactor 1: FK `gobierno_regional` en `HealthGeographicScope`

#### T-01. Modelo: añadir campo `gobierno_regional` a `HealthGeographicScope`

**Cambio en `apps/convenios/models.py`:**

En la clase `HealthGeographicScope` (tabla `ambito_geografico_sanitario`), añadir el campo:

```
gobierno_regional — FK → RegionalGovernment (PROTECT, null=True, blank=True,
    db_column="gobierno_regional_id",
    related_name="ambitos",
    help_text="Gobierno regional al que corresponde el ámbito sanitario
               (nulo para los 4 DIRIS de Lima Metropolitana)")
```

No requiere `unique`: varios ámbitos pueden corresponder al mismo GORE en caso de que en el futuro se subdividan, aunque en la práctica el seed tiene 25 ámbitos regionales (uno por GORE) + 4 DIRIS (NULL).

**Criterio de aceptación:** `makemigrations` genera un `AddField` sobre `ambito_geografico_sanitario` con la columna `gobierno_regional_id` nullable (FK a `gobierno_regional`, PROTECT). El modelo pasa `python manage.py check` sin errores.

---

#### T-02. Migración 0043: `AddField` + `RunPython` de backfill

**Archivo:** `apps/convenios/migrations/0043_healthgeographicscope_gobierno_regional.py`

Operaciones en orden:

1. `AddField` de `gobierno_regional` sobre `HealthGeographicScope` (nullable, PROTECT).

2. `RunPython(poblar_gobierno_regional, reverse_code=RunPython.noop)` — lógica de backfill:
   - **Criterio de mapeo:** comparar `HealthGeographicScope.nombre` con `RegionalGovernment.nombre`. La coincidencia es por nombre normalizado (strip + lower o similaridad suficiente). Los 25 ámbitos regionales deben mapearse a su GORE por nombre de región. Los 4 ámbitos DIRIS (nombre contiene "DIRIS" o "Lima Norte"/"Lima Sur"/"Lima Este"/"Lima Ciudad" o variante) quedan `gobierno_regional_id = NULL`.
   - **Estrategia concreta:** para cada `HealthGeographicScope` cuyo `nombre` NO contenga "DIRIS" (case-insensitive), buscar el `RegionalGovernment` cuyo `nombre` contenga el mismo texto clave de región. Si no se encuentra match, **no lanzar error**: dejar `NULL` y registrar un warning al log (los datos reales pueden tener inconsistencias de nombre que se resuelven manualmente). El validator deberá verificar manualmente el resultado tras la migración.
   - **Identificación de DIRIS:** un ámbito es DIRIS si su `nombre` contiene la cadena "DIRIS" (case-insensitive). Estos quedan explícitamente en NULL.

**Criterio de aceptación:** la migración aplica sin error. Tras `migrate`, los 25 ámbitos regionales tienen `gobierno_regional_id` no nulo (o los que haya matcheado el criterio de nombre) y los 4 DIRIS tienen NULL. El `RegionalGovernment` referenciado existe en la tabla.

---

#### T-03. Serializer: exponer `gobierno_regional_id` y `gobierno_regional_detalle` en `HealthGeographicScope`

El endpoint `/api/v1/health-geographic-scopes/` usa `_entity_viewset` con `_auto_serializer`. El `_auto_serializer` ya expone todos los campos; `gobierno_regional_id` aparece automáticamente como FK integer de escritura. Para el detalle de lectura:

**Cambio en `views.py`**, en la entrada `"health-geographic-scopes"` de `ENTITY_VIEWSETS`:

- Añadir `detalles={"gobierno_regional": _detalle_nombre}` a la llamada de `_entity_viewset`.
- El campo de escritura `gobierno_regional` (id FK) sigue expuesto por `fields="__all__"`.
- El campo de lectura `gobierno_regional_detalle` expone `{id, nombre}` (sin `codigo` porque `RegionalGovernment` no tiene `codigo`; `_detalle_nombre` usa `getattr(rel, "codigo", None)` → `None`).

No se añaden filtros de escritura al endpoint: sigue siendo solo lectura (el endpoint es `ReadOnlyModelViewSet` implícito de `_entity_viewset` con `IsAdminRoleOrReadOnly`; la escritura solo la hace el Administrador RENADS si necesita corregir el mapeo).

**Criterio de aceptación:** `GET /api/v1/health-geographic-scopes/` devuelve `gobierno_regional` (int o null) y `gobierno_regional_detalle` (`{id, codigo, nombre}` o null) en cada ítem.

---

#### T-04. Actualizar `docs/db_schema_modulo_01_convenios.md` — tabla `ambito_geografico_sanitario`

Añadir la fila correspondiente al campo nuevo en la tabla de definición de `ambito_geografico_sanitario` (sección 2, fila del catálogo):

```
| `gobierno_regional_id` | FK → `gobierno_regional` (PROTECT) | Sí | Gobierno regional al que corresponde el ámbito sanitario (nulo para los 4 DIRIS de Lima Metropolitana) |
```

Convertir la entrada de `ambito_geografico_sanitario` de línea simple en la tabla de catálogos a una sub-sección propia (análoga a `red` y `microred`) para poder listar sus columnas. Actualizar también el mapa de relaciones (sección 12):

```
gobierno_regional ──< ambito_geografico_sanitario (gobierno_regional_id, nullable)
```

**Criterio de aceptación:** el `.md` refleja exactamente la estructura de la tabla en BD tras `0043`.

---

### MIGRACIÓN 0044 — Refactor 2 parte A: campo transitorio `codigo_nuevo` en `ExecutingUnit` + backfill + columnas transitorias en `ipress`/`convenio`

#### T-05. Verificación previa de datos: unicidad y formato del campo `codigo` actual

Antes de escribir la migración, el implementador debe verificar (con una consulta directa a la BD) que:

a) El campo `codigo` en `unidad_ejecutora` es único entre todos los registros activos. Si hay duplicados, la migración de datos falla.
b) El campo `codigo` tiene exactamente 4 caracteres numéricos en todos los registros con datos. Si hay registros con `codigo` vacío o con más de 4 caracteres, aplicar el fallback: `f"{id:04d}"` (id zero-padded a 4 dígitos).

El implementador debe documentar qué filas usaron el fallback y si `f"{id:04d}"` genera colisión con algún `codigo` no vacío ya existente; en ese caso, escalar al usuario antes de implementar.

**Criterio de aceptación:** el análisis de datos queda registrado en un comentario al inicio de la migración `0044` (como docstring del módulo o en la función `poblar_codigo_nuevo`).

---

#### T-06. Migración 0044: columnas transitorias + backfill

**Archivo:** `apps/convenios/migrations/0044_executingunit_codigo_nuevo_transitorio.py`

Operaciones en orden:

1. **`AddField ExecutingUnit.codigo_nuevo`** — CharField(4, null=True, blank=True, db_column="codigo_nuevo"). Sin `unique` aún (para poder hacer backfill).

2. **`RunPython(poblar_codigo_nuevo, reverse_code=RunPython.noop)`:**
   - Para cada `ExecutingUnit`:
     - Si `codigo` no está vacío y `len(codigo) <= 4`: `codigo_nuevo = codigo.strip().zfill(4)` — zero-pad a 4 chars si tiene menos de 4.
     - Si `codigo` tiene más de 4 chars o está vacío: `codigo_nuevo = f"{id:04d}"`.
     - Si `f"{id:04d}"` colisiona con un `codigo_nuevo` ya asignado: lanzar `RuntimeError` con mensaje en español describiendo la colisión.
   - Después del backfill, verificar unicidad: `assert len(set) == count` — si falla, lanzar `RuntimeError`.

3. **`AddField Ipress.unidad_ejecutora_codigo`** — CharField(4, null=True, blank=True, db_column="unidad_ejecutora_codigo_nuevo"). Nombre transitorio de columna para no colisionar con la columna FK existente `unidad_ejecutora_id`.

4. **`RunPython(poblar_ipress_codigo, reverse_code=RunPython.noop)`:**
   - Para cada `Ipress`, leer `unidad_ejecutora_id` → buscar el `ExecutingUnit` con ese `id` → copiar su `codigo_nuevo` a `ipress.unidad_ejecutora_codigo`.
   - Si algún `Ipress` tiene `unidad_ejecutora_id` no nulo pero no hay `ExecutingUnit` con ese id: lanzar `RuntimeError` (integridad rota).

5. **`AddField Convention.unidad_ejecutora_codigo`** — CharField(4, null=True, blank=True, db_column="convenio_unidad_ejecutora_codigo_nuevo"). Transitorio.

6. **`RunPython(poblar_convenio_codigo, reverse_code=RunPython.noop)`:**
   - Para cada `Convention` con `unidad_ejecutora_id` no nulo: copiar `codigo_nuevo` del `ExecutingUnit` referenciado.
   - Si `unidad_ejecutora_id` es nulo: dejar `unidad_ejecutora_codigo = None`.

**Por qué no hacer AddField + FK directo en un solo paso:** SQLite no permite agregar una FK NOT NULL sin valor por defecto sobre filas existentes. El proceso de "agregar transitorio → backfill → convertir a FK real" es el mismo patrón que `0042`.

**Criterio de aceptación:** la migración aplica sin error. Tras `migrate`: `ExecutingUnit.codigo_nuevo` no tiene nulos; todas las `Ipress.unidad_ejecutora_codigo` coinciden con el `codigo_nuevo` del `ExecutingUnit` padre; los `Convention` con `unidad_ejecutora` tienen `unidad_ejecutora_codigo` no nulo.

---

### MIGRACIÓN 0045 — Refactor 2 parte B: reestructuración DDL de `ExecutingUnit` + FKs

#### T-07. Modelo: rediseñar `ExecutingUnit`

**Cambio en `apps/convenios/models.py`**, clase `ExecutingUnit`:

Reemplazar la definición completa del modelo. Estructura resultante:

```
class ExecutingUnit(models.Model):
    codigo — CharField(4, primary_key=True,
        db_column="codigo",
        help_text="Código presupuestal de 4 dígitos (PK)")
    nombre — CharField(255,
        help_text="Nombre de la unidad ejecutora")
    ambito_geografico_sanitario — FK → HealthGeographicScope (PROTECT, not null,
        db_column="ambito_geografico_sanitario_id",
        related_name="unidades_ejecutoras",
        help_text="Ámbito geográfico sanitario al que pertenece")
    activo — BooleanField(default=True,
        help_text="Indica si está activa")

    class Meta:
        db_table = "unidad_ejecutora"
        verbose_name = "unidad ejecutora"
```

**Campos eliminados respecto al modelo actual:** `tipo_organo`, `gobierno_regional`, `direccion`, `ubigeo`, `referencia_logo`.

**FKs referenciantes que cambian:** `Ipress.unidad_ejecutora` y `Convention.unidad_ejecutora` pasarán a referenciar `ExecutingUnit` por `codigo` (CharField 4) en lugar de por el antiguo `id` (int).

**Cambio en `Ipress`:**

```
unidad_ejecutora — FK → ExecutingUnit (PROTECT, not null,
    db_column="unidad_ejecutora_id",
    to_field="codigo",
    related_name="ipress",
    help_text="Unidad ejecutora a la que pertenece")
```

Nota: `db_column="unidad_ejecutora_id"` se mantiene por compatibilidad de nombre de columna en la BD, pero el valor almacenado cambia de int a varchar(4).

**Cambio en `Convention`:**

```
unidad_ejecutora — FK → ExecutingUnit (PROTECT, null=True, blank=True,
    db_column="unidad_ejecutora_id",
    to_field="codigo",
    related_name="convenios",
    help_text="Unidad ejecutora parte del Convenio Específico")
```

**Criterio de aceptación:** el modelo pasa `python manage.py check`; `makemigrations --check` no genera cambios adicionales tras aplicar todas las migraciones; las FK `ipress.unidad_ejecutora_id` y `convenio.unidad_ejecutora_id` almacenan el código varchar(4) del `ExecutingUnit`.

---

#### T-08. Migración 0045: reestructuración DDL

**Archivo:** `apps/convenios/migrations/0045_executingunit_nueva_estructura.py`

**Consideración crítica sobre SQLite:** SQLite no soporta `ALTER TABLE DROP COLUMN` antes de la versión 3.35 (2021-03-12), ni `ALTER TABLE RENAME COLUMN` antes de 3.25 (2018-09-15). Django maneja esto mediante la operación `SeparateDatabaseAndState` o recreando la tabla con `AlterField` + field renaming. El plan más seguro con Django es la secuencia `RenameField` + `RemoveField` + `AlterField`, que en SQLite se traduce a recreación completa de la tabla. En PostgreSQL, las mismas operaciones se ejecutan como DDL directo. **No usar** `SeparateDatabaseAndState` innecesariamente; Django ORM maneja la recreación.

Operaciones en orden:

**Paso A — Preparar `ExecutingUnit` como nueva tabla:**

1. `AddField ExecutingUnit.ambito_geografico_sanitario` — FK → `HealthGeographicScope` (PROTECT, null=True transitoriamente, db_column="ambito_geografico_sanitario_id"). Null para poder agregar sobre datos existentes.

2. `RunPython(poblar_ambito_desde_gore, reverse_code=RunPython.noop)`:
   - Para cada `ExecutingUnit`, derivar el `ambito_geografico_sanitario_id` desde `gobierno_regional_id`:
     - `ExecutingUnit.gobierno_regional` → `RegionalGovernment` → buscar el `HealthGeographicScope` que tiene ese `gobierno_regional_id` (gracias al Refactor 1 ya aplicado en `0043`).
     - Si el GORE no tiene ámbito mapeado (gobierno_regional_id no aparece en ningún HealthGeographicScope): lanzar `RuntimeError` con mensaje en español.
   - Guardar `ambito_geografico_sanitario_id` en el registro.

3. `AlterField ExecutingUnit.ambito_geografico_sanitario` → NOT NULL (quitar `null=True`).

**Paso B — Promocionar `codigo_nuevo` a PK:**

4. `AlterField ExecutingUnit.codigo_nuevo` → `CharField(4, unique=True, null=False)` (todavía no es PK; se hace unique para poder usar como `to_field` en el siguiente paso).

5. `AlterField Ipress.unidad_ejecutora_codigo` → FK → `ExecutingUnit` via `to_field="codigo_nuevo"` (not null, PROTECT). En este momento la columna `unidad_ejecutora_id` (int) y la columna `unidad_ejecutora_codigo_nuevo` (varchar4 FK) coexisten.

6. `AlterField Convention.unidad_ejecutora_codigo` → FK → `ExecutingUnit` via `to_field="codigo_nuevo"` (null=True, PROTECT). Misma coexistencia.

**Paso C — Eliminar campos obsoletos y columnas transitorias:**

7. `RemoveField ExecutingUnit.id` — eliminar el AutoField PK (Django recrea la tabla en SQLite).

8. `RemoveField ExecutingUnit.tipo_organo`.

9. `RemoveField ExecutingUnit.gobierno_regional`.

10. `RemoveField ExecutingUnit.direccion`.

11. `RemoveField ExecutingUnit.ubigeo`.

12. `RemoveField ExecutingUnit.referencia_logo`.

13. `RemoveField ExecutingUnit.codigo` — el campo `codigo` antiguo (CharField 50, no PK).

14. `RenameField ExecutingUnit.codigo_nuevo → codigo` — hacer que el campo promocionado tome el nombre canónico.

15. `AlterField ExecutingUnit.codigo` → `CharField(4, primary_key=True, db_column="codigo")`.

16. `RemoveField Ipress.unidad_ejecutora` (la FK int original, columna `unidad_ejecutora_id`).

17. `RenameField Ipress.unidad_ejecutora_codigo → unidad_ejecutora` (renombra la columna transitoria al nombre canónico; Django la mantiene con `db_column="unidad_ejecutora_id"` si así lo indica el modelo).

18. `RemoveField Convention.unidad_ejecutora` (la FK int original).

19. `RenameField Convention.unidad_ejecutora_codigo → unidad_ejecutora`.

**Nota sobre el orden:** los pasos C.16-19 deben ocurrir DESPUÉS de los pasos B.5-6 (las FK transitorias ya están activas apuntando a `codigo_nuevo`). Si Django reordena operaciones automáticamente, usar `dependencies` internas o separar en sub-migraciones adicionales si se producen errores de integridad referencial durante el test.

**Criterio de aceptación:** la migración aplica sin error en SQLite dev. La tabla `unidad_ejecutora` resultante tiene exactamente las columnas `codigo` (PK varchar4), `nombre`, `ambito_geografico_sanitario_id`, `activo`. Las columnas `tipo_organo_id`, `gobierno_regional_id`, `direccion`, `ubigeo_id`, `referencia_logo`, `id` no existen. Las columnas `unidad_ejecutora_id` en `ipress` y `convenio` almacenan varchar(4).

---

### CÓDIGO DE APLICACIÓN

#### T-09. Vistas: rediseñar `executing-units` en `ENTITY_VIEWSETS`

**Cambio en `apps/convenios/views.py`**, entrada `"executing-units"` de `ENTITY_VIEWSETS`:

Reemplazar la llamada actual:
```python
"executing-units": _entity_viewset(
    m.ExecutingUnit,
    filterset_fields=["tipo_organo", "gobierno_regional", "activo"],
    search_fields=["nombre", "codigo"],
    logo=True,
    detalles={"tipo_organo": ..., "gobierno_regional": ..., "ubigeo": ...},
),
```

Por:
```python
"executing-units": _entity_viewset(
    m.ExecutingUnit,
    filterset_fields=["ambito_geografico_sanitario", "activo"],
    search_fields=["nombre", "codigo"],
    detalles={"ambito_geografico_sanitario": _detalle_nombre},
),
```

Cambios:
- **Eliminar** `logo=True`: el modelo ya no tiene `referencia_logo`.
- **Eliminar** filtros `tipo_organo`, `gobierno_regional`.
- **Añadir** filtro `ambito_geografico_sanitario`.
- **Eliminar** detalles `tipo_organo`, `gobierno_regional`, `ubigeo`.
- **Añadir** detalle `ambito_geografico_sanitario`.

El campo `codigo` pasa a ser PK CharField; el auto-serializer lo expone como `string` en lugar de `integer`. El write serializer generado por `_auto_serializer` expone `fields="__all__"`, que incluirá `codigo` (PK), `nombre`, `ambito_geografico_sanitario` (id string), `activo`. El campo `codigo` es editable en create (es la PK que el usuario provee); en update, la PK no se cambia (DRF excluye las PKs del write por defecto con `pk_field`).

**Criterio de aceptación:** `GET /api/v1/executing-units/` devuelve lista con `codigo` (string 4 chars), `nombre`, `ambito_geografico_sanitario` (id string), `ambito_geografico_sanitario_detalle` (`{id, codigo, nombre}`) y `activo`. Los filtros `/api/v1/executing-units/?ambito_geografico_sanitario=<id>` y `?activo=true` funcionan. El endpoint NO ofrece `upload-logo` ni `logo-url` (sin mixin de logo). Los filtros antiguos `tipo_organo` y `gobierno_regional` retornan 400 si se envían (django-filter los ignora por no estar declarados).

---

#### T-10. pdf.py: eliminar referencia a `direccion` de `ExecutingUnit`

**Cambio en `apps/convenios/pdf.py`**, función `_domicilio_entidad`:

Rama `"UNIDAD_EJECUTORA"` actual:
```python
if rol == "UNIDAD_EJECUTORA":
    return getattr(convenio.unidad_ejecutora, "direccion", "") or ""
```

Reemplazar por:
```python
if rol == "UNIDAD_EJECUTORA":
    return ""
```

El campo `direccion` desaparece del modelo; devolver cadena vacía es el comportamiento correcto para el MVP (la dirección de la UE no se incluye en la plantilla de convenio en esta versión).

**Criterio de aceptación:** `apps/convenios/pdf.py` no hace `getattr` sobre `direccion` ni sobre ningún campo eliminado de `ExecutingUnit`. La función `_domicilio_entidad` devuelve `""` para el rol `UNIDAD_EJECUTORA`.

---

#### T-11. Serializer: verificar `get_unidad_ejecutora_detalle` en `ConventionReadSerializer`

**Archivo:** `apps/convenios/serializers.py`, método `get_unidad_ejecutora_detalle`.

Estado actual: `return _detalle_fk(obj.unidad_ejecutora, "nombre", "codigo")`. Los campos `nombre` y `codigo` permanecen en `ExecutingUnit` tras el refactor. **No requiere cambio de código**, pero el `codigo` ahora es `str` de 4 chars (antes era `str` también, aunque de longitud variable). El serializer sigue funcionando.

**Criterio de aceptación:** `GET /api/v1/conventions/<id>/` incluye `unidad_ejecutora_detalle: {"nombre": "...", "codigo": "0123"}` cuando el convenio tiene unidad ejecutora. El `codigo` es string de 4 chars.

---

#### T-12. Services: verificar referencias a `unidad_ejecutora` en `services.py`

**Archivo:** `apps/convenios/services.py`.

Las referencias identificadas son:
- `datos.get("unidad_ejecutora")` — accede a la instancia FK, no a campos internos.
- `convenio.unidad_ejecutora_id` — accede al valor de la FK (ahora string), comparación con `ipress.unidad_ejecutora_id`.
- `ipress.unidad_ejecutora_id != convenio.unidad_ejecutora_id` — comparación de dos strings tras el refactor.

Ninguna de estas referencias accede a `tipo_organo`, `gobierno_regional`, `direccion`, `ubigeo` o `referencia_logo`. **No requieren cambio de código.**

Sin embargo, el implementador debe verificar que Django ORM acepta la comparación `ipress.unidad_ejecutora_id != convenio.unidad_ejecutora_id` cuando ambos son `str` (CharField PK). Con Django, cuando la FK apunta a un CharField PK, el campo `*_id` devuelve el string; la comparación es correcta.

**Criterio de aceptación:** `services.py` no hace referencia a ningún campo eliminado de `ExecutingUnit`. La regla `_exigir_campos_clinicos_conapres` y `crear_registro_campo_clinico` siguen funcionando correctamente con la PK string.

---

#### T-13. Filtros: verificar impacto en `ConventionFilter`

**Archivo:** `apps/convenios/filters.py`.

`ConventionFilter` no referencia `unidad_ejecutora` ni `HealthGeographicScope`. No requiere cambio.

`IpressViewSet` en `views.py` usa `filterset_fields=["unidad_ejecutora", ...]` — este filtro sigue funcionando porque `Ipress.unidad_ejecutora` sigue existiendo (como FK a `ExecutingUnit`); el valor del filtro ahora es el código string de 4 chars en lugar de un int. **Cambio en el contrato de API:** los clientes que filtraban `?unidad_ejecutora=1` (int) ahora deben pasar `?unidad_ejecutora=0001` (string). Documentar este breaking change en el spec.

**Criterio de aceptación:** `GET /api/v1/ipress/?unidad_ejecutora=0001` devuelve las IPRESS de esa unidad ejecutora. Los filtros de IPRESS no retornan error 400 con el nuevo formato de clave.

---

#### T-14. Actualizar `docs/db_schema_modulo_01_convenios.md` — tabla `unidad_ejecutora`

Reemplazar la tabla de columnas de `unidad_ejecutora` (sección 3, bajo "Entidades — Gobiernos Regionales") con la nueva estructura:

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `codigo` | varchar(4) **PK** | No | Código presupuestal de 4 dígitos (PK textual) |
| `nombre` | varchar(255) | No | Nombre |
| `ambito_geografico_sanitario_id` | FK → `ambito_geografico_sanitario` (PROTECT) | No | Ámbito geográfico sanitario al que pertenece |
| `activo` | bool | No | |

**Columnas eliminadas respecto a la versión anterior:** `id`, `tipo_organo_id`, `gobierno_regional_id`, `direccion`, `ubigeo_id`, `referencia_logo`.

Actualizar también:
- La descripción del endpoint `/api/v1/executing-units/` (filtros, detalles expuestos).
- La nota sobre `ipress.unidad_ejecutora_id` y `convenio.unidad_ejecutora_id` (ahora varchar 4, no int).
- El mapa de relaciones (sección 12): eliminar `unidad_ejecutora >── gobierno_regional / tipo_organo (→ organo_directorio, categoría UNIDAD_EJECUTORA) / ubigeo`; añadir `unidad_ejecutora >── ambito_geografico_sanitario`.

**Criterio de aceptación:** el `.md` refleja exactamente la estructura de la tabla en BD tras `0045`.

---

## Criterios de aceptación globales

1. Las tres migraciones (`0043`, `0044`, `0045`) aplican en secuencia sin error en SQLite dev.
2. `python manage.py check` no reporta errores tras las tres migraciones y los cambios de código.
3. `GET /api/v1/health-geographic-scopes/` incluye `gobierno_regional` y `gobierno_regional_detalle` en la respuesta.
4. Los 4 DIRIS tienen `gobierno_regional: null` y el resto de los 25 ámbitos tienen `gobierno_regional` con el id del GORE correspondiente (al menos los que matchearon por nombre en el backfill).
5. `GET /api/v1/executing-units/` devuelve `codigo` (string 4 chars) como identificador principal. No existe `id` integer en la respuesta.
6. `POST /api/v1/executing-units/` con body `{"codigo": "0032", "nombre": "...", "ambito_geografico_sanitario": <id>}` crea la unidad ejecutora.
7. La tabla `unidad_ejecutora` en BD no contiene columnas `tipo_organo_id`, `gobierno_regional_id`, `direccion`, `ubigeo_id`, `referencia_logo`, `id`.
8. Las tablas `ipress` y `convenio` mantienen la columna `unidad_ejecutora_id` con valores varchar(4) (en lugar de int).
9. `apps/convenios/pdf.py` devuelve `""` para el domicilio de la parte `UNIDAD_EJECUTORA` sin `AttributeError`.
10. `docs/db_schema_modulo_01_convenios.md` refleja ambos cambios (Refactor 1 y Refactor 2).

---

## Reglas de negocio involucradas

- **RN-UE-01 (ámbito de la UE):** la unidad ejecutora pertenece a un ámbito geográfico sanitario; los campos clínicos que registra CONAPRES se filtran por `ipress.ambito_geografico_sanitario` y `convenio.unidad_ejecutora.ambito_geografico_sanitario` debe ser coherente (no es una restricción explícita de BD en el MVP, pero es la semántica).
- **RN-exigir-campos-clinicos:** `ipress.unidad_ejecutora_id == convenio.unidad_ejecutora_id` — comparación de strings tras el refactor; misma lógica de negocio, distinto tipo de dato.
- No se introducen reglas de negocio nuevas. Los refactors son estructurales.

---

## Breaking changes de API (para informar al frontend)

| Endpoint | Campo | Cambio |
|----------|-------|--------|
| `/api/v1/executing-units/` | `id` (int) | **Desaparece**. El identificador pasa a ser `codigo` (string 4 chars). |
| `/api/v1/executing-units/` | `tipo_organo`, `gobierno_regional`, `direccion`, `ubigeo`, `referencia_logo` | **Desaparecen** de la respuesta. |
| `/api/v1/executing-units/` | Filtros `?tipo_organo=`, `?gobierno_regional=` | **Desaparecen**. |
| `/api/v1/executing-units/` | Filtro `?ambito_geografico_sanitario=<id>` | **Nuevo.** |
| `/api/v1/executing-units/` | Campo `ambito_geografico_sanitario_detalle` | **Nuevo** en la respuesta. |
| `/api/v1/executing-units/<pk>/` | La PK en la URL es ahora un string de 4 chars (p. ej. `0032`) en lugar de un entero. | **Breaking.** |
| `/api/v1/ipress/?unidad_ejecutora=` | El valor del filtro pasa de int a string 4 chars. | **Breaking.** |
| `/api/v1/conventions/` respuesta `unidad_ejecutora` field | Sigue siendo el código string (sin cambio de valor semántico); `unidad_ejecutora_detalle.codigo` era string antes también. | Sin cambio visible para el frontend. |
| `/api/v1/health-geographic-scopes/` | `gobierno_regional` (int FK, nullable) | **Nuevo** campo de escritura. |
| `/api/v1/health-geographic-scopes/` | `gobierno_regional_detalle` | **Nuevo** campo de lectura. |

---

## Referencias a tablas y columnas del schema

- `docs/db_schema_modulo_01_convenios.md` §3 — tabla `unidad_ejecutora` (columnas a reemplazar).
- `docs/db_schema_modulo_01_convenios.md` §2 — catálogo `ambito_geografico_sanitario` (columna nueva `gobierno_regional_id`).
- `docs/db_schema_modulo_01_convenios.md` §3 — tabla `ipress`, columna `unidad_ejecutora_id` (tipo cambia a varchar).
- `docs/db_schema_modulo_01_convenios.md` §8 — tabla `convenio`, columna `unidad_ejecutora_id` (tipo cambia a varchar).
- `apps/convenios/models.py:41` — `HealthGeographicScope`.
- `apps/convenios/models.py:347` — `ExecutingUnit`.
- `apps/convenios/models.py:378` — `Ipress.unidad_ejecutora`.
- `apps/convenios/models.py:853` — `Convention.unidad_ejecutora`.
- `apps/convenios/views.py:856` — entrada `"executing-units"` en `ENTITY_VIEWSETS`.
- `apps/convenios/views.py:824` — entrada `"health-geographic-scopes"` en `ENTITY_VIEWSETS`.
- `apps/convenios/pdf.py:72` — `_domicilio_entidad`, rama `"UNIDAD_EJECUTORA"`.
- `apps/convenios/serializers.py:75` — `ConventionReadSerializer.get_unidad_ejecutora_detalle`.
