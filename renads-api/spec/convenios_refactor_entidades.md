# Spec — Refactor de entidades del módulo Convenios

> Metodología SDD. Este archivo es la **lista exacta de tareas** para el agente `implement`.
> No contiene código de aplicación (los pasos del `RunPython` son pseudo-pasos).
> Idioma: nombres de tabla/columna/`help_text` en **español**; código en **inglés**.

## Objetivo

Reestructurar las entidades del módulo Convenios:

1. Eliminar el modelo/tabla `OrganType` (`tipo_organo`) y su endpoint `organ-types`.
2. Convertir `OrganDirectory` (`organo_directorio`) en el catálogo unificado de tipos/directorio, discriminado por un nuevo `categoria` (choices), eliminando los FK `organo`, `ubigeo` y el campo `referencia_logo`, y el FK `tipo_organo`.
3. Reapuntar a `OrganDirectory` las FKs que hoy apuntan a `OrganType`: `ExecutingUnit.tipo_organo` y `University.tipo_entidad`.
4. Enriquecer `RegionalGovernment` (`ubigeo`, `sigla`), `Faculty` (`referencia_logo`, `ubigeo`) y `ExecutivePosition` (drop `codigo`, rename `nombre`→`nombre_masculino`, add `nombre_femenino`).
5. Preservar los datos existentes en la migración (RunPython) sin romper FKs `PROTECT`.
6. Actualizar serializers/views/urls/filtros y la documentación en el mismo cambio.

Fuentes de verdad: `docs/db_schema_modulo_01_convenios.md`, `docs/db_schema_er_global.md`, `apps/convenios/models.py`, `serializers.py`, `views.py`, `urls.py`, `services.py`, `selectors.py`.

---

## RESUELTO — decisión de negocio (RN-1 / GERESA-DIRESA-DIRIS) — el usuario la cerró

`apps/convenios/services.py::crear_convenio` (línea ~181) derivaba el tipo de órgano regional para RN-1 (solo GERESA/DIRESA pueden solicitar Marco; DIRIS no requiere Marco) desde `organo.tipo_organo.codigo`. Este refactor **elimina `OrganDirectory.tipo_organo`**.

**Decisión del usuario:** el discriminador `categoria` de `organo_directorio` toma como base los nombres de la tabla `organo` y **colapsa** el sub-tipo regional en dos categorías, suficientes para RN-1 (que trata GERESA y DIRESA igual):

| `categoria` (code) | label / valor | Cubre | RN-1 |
|---|---|---|---|
| `ORGANO_MINSA` | "Órgano del MINSA" | órganos del MINSA | — |
| `UNIVERSIDAD` | "Universidad" | universidades | — |
| `GOBIERNO_REGIONAL` | "Gobierno Regional" | **GERESA + DIRESA** | pueden solicitar Marco |
| `MINSA_DIRIS` | "MINSA DIRIS" | **DIRIS** | **exenta** de Marco |
| `UNIDAD_EJECUTORA` | "Unidad Ejecutora" | unidades ejecutoras | — |

**Reglas resultantes (T-SVC-1):**
- Convenio **Marco**: solo si `organo_directorio.categoria == "GOBIERNO_REGIONAL"` (antes `{"GERESA","DIRESA"}`).
- Convenio **Específico**: si `categoria == "MINSA_DIRIS"` → no requiere Marco; en otro caso requiere Marco vigente (igual que hoy la rama `!= "DIRIS"`).

**Backfill (T-MIG-2):** para los `organo_directorio` regionales, derivar la nueva `categoria` desde el `tipo_organo.codigo` **actual** antes de borrarlo: `GERESA`/`DIRESA` → `GOBIERNO_REGIONAL`; `DIRIS` → `MINSA_DIRIS`. El resto por `organo.nombre` (MINSA/Universidad/Unidad Ejecutora).

**Seed `organo` (T-CMD/T-MIG):** actualizar la tabla `organo` para reflejar las categorías: renombrar la fila "Órgano Regional" → "Gobierno Regional" y **agregar** "MINSA DIRIS". Mantener "Órgano del MINSA", "Universidad", "Unidad Ejecutora". (Se usa como fuente de verdad de los labels y la valida `OrganRepresentativeSerializer`.)

**Coherencia cargo↔categoría (T-SER-2):** `ExecutivePosition.organo` (FK→`Organ`) se conserva. La validación cruzada compara `cargo.organo.nombre` contra el **label** de `organo_directorio.categoria` (`get_categoria_display()`); si no coinciden → error. (Con el seed actualizado, los nombres de `organo` y los labels de `categoria` son idénticos.)

Tareas afectadas: **T-SVC-1**, **T-SER-1**, **T-SER-2**, **T-MOD-2** (5 choices), **T-MIG-2** (backfill regional), **T-CMD/seed `organo`**, y `docs`.

---

## 1. Cambios de modelo por tabla — `apps/convenios/models.py`

### T-MOD-1 — Eliminar `OrganType` (`tipo_organo`)
- Borrar la clase `OrganType` completa (líneas ~172-199).
- No dejar imports ni referencias colgando. Ver §3 (FKs reapuntadas) y §4 (endpoints).

### T-MOD-2 — `OrganDirectory` (`organo_directorio`)
- **DROP** los campos `organo` (FK→`Organ`, `db_column="organo_id"`), `tipo_organo` (FK→`OrganType`), `ubigeo` (FK→`Ubigeo`), `referencia_logo` (`ImageField`).
- **ADD** `categoria`:
  - `CharField(max_length=20, choices=ORGAN_DIRECTORY_CATEGORY, db_column="categoria")`.
  - Definir la constante de choices (code → label español) **a nivel de módulo** — **5 valores** (los labels replican los nombres de la tabla `organo`):
    - `ORGANO_MINSA` → "Órgano del MINSA"
    - `UNIVERSIDAD` → "Universidad"
    - `GOBIERNO_REGIONAL` → "Gobierno Regional"  *(GERESA + DIRESA)*
    - `MINSA_DIRIS` → "MINSA DIRIS"  *(DIRIS)*
    - `UNIDAD_EJECUTORA` → "Unidad Ejecutora"
  - `help_text` en español: "Categoría del órgano (discriminador)".
- **Conservar sin cambios:** `gobierno_regional`, `nombre`, `siglas`, `activo`.
- Actualizar el docstring de la clase (ya no discrimina por `organo`, sino por `categoria`; ya no lleva logo/ubigeo).
- **Criterio de aceptación:** `OrganDirectory` expone `categoria` con las 5 choices; no expone `organo`, `tipo_organo`, `ubigeo`, `referencia_logo`.

### T-MOD-3 — `ExecutingUnit.tipo_organo` reapunta a `OrganDirectory`
- FK → `OrganDirectory`, `on_delete=models.PROTECT`, `db_column="tipo_organo_id"`, `related_name="+"`, **requerido** (sin `null/blank`).
- `limit_choices_to={"categoria": "UNIDAD_EJECUTORA"}`.
- Actualizar `help_text` (español): "Tipo de unidad ejecutora del directorio (categoría UNIDAD_EJECUTORA)".
- **Criterio:** la FK apunta a `organo_directorio`, columna `tipo_organo_id` sin cambio de nombre.

### T-MOD-4 — `University.tipo_entidad` reapunta a `OrganDirectory`
- FK → `OrganDirectory`, `on_delete=models.PROTECT`, `db_column="tipo_entidad_id"`, **requerido**.
- `limit_choices_to={"categoria": "UNIVERSIDAD"}`.
- Actualizar `help_text` (español): "Tipo de entidad del directorio (categoría UNIVERSIDAD)".
- **Criterio:** la FK apunta a `organo_directorio`, columna `tipo_entidad_id` sin cambio de nombre.

### T-MOD-5 — `RegionalGovernment` (`gobierno_regional`)
- **ADD** `ubigeo`: FK → `Ubigeo`, `on_delete=models.PROTECT`, `db_column="ubigeo_id"`, `null=True`, `blank=True`, `related_name="+"`, `help_text` español: "Ubicación geográfica (UBIGEO)".
- **ADD** `sigla`: `CharField(max_length=50, blank=True)`, `help_text` español: "Sigla del gobierno regional".
- **Criterio:** ambos campos existen; `ubigeo` opcional; consistente con el patrón `related_name="+"` del resto del schema.

### T-MOD-6 — `Faculty` (`facultad`)
- **ADD** `referencia_logo`: `ImageField(upload_to="facultad/", max_length=500, null=True, blank=True)`, `help_text` español (mismo patrón que `University`/`OrganDirectory` actuales): "Logo institucional (imagen almacenada en el repositorio de medios)".
- **ADD** `ubigeo`: FK → `Ubigeo`, `on_delete=models.PROTECT`, `db_column="ubigeo_id"`, `null=True`, `blank=True`, `related_name="+"`, `help_text` español: "Ubicación geográfica (UBIGEO)".
- **Criterio:** `faculties` puede subir logo (via `LogoStorageMixin`, ver T-VIEW-6) y expone `ubigeo`.

### T-MOD-7 — `ExecutivePosition` (`cargo_ejecutivo`)
- **RENAME** `nombre` → `nombre_masculino` (en la migración usar `RenameField`, no drop+add). Mantener `verbose_name`/`help_text` acordes ("Nombre del cargo en masculino").
- **ADD** `nombre_femenino`: `CharField(max_length=255, blank=True)`, `help_text` español: "Nombre del cargo en femenino".
- **DROP** `codigo`.
- **Meta:** reemplazar `unique_together=(("organo","codigo"),)` por `unique_together=(("organo","nombre_masculino"),)` (decisión tomada: por `nombre_masculino`).
- **Meta:** ajustar `ordering` (usa `codigo`) → `["organo", "nombre_masculino"]`.
- **Criterio:** el modelo no tiene `codigo`; unicidad y orden por `nombre_masculino`; `__str__` devuelve `self.nombre_masculino`.

> `ExecutivePosition.organo` (FK → `Organ`) se **conserva**. La categoría `Organ` sigue existiendo (no se elimina).

---

## 2. Plan de migración — `apps/convenios/migrations/`

Última migración existente: **`0027_move_contact_fields_to_regional_government.py`**. Las nuevas migraciones dependen de `0027`.

> Dividir en **tres** migraciones para respetar el orden schema→datos→schema y no romper `PROTECT`. Nombrar de forma descriptiva (p. ej. `0028_*`, `0029_*`, `0030_*`). Alternativamente, una sola migración con `RunPython` intercalado entre `SeparateDatabaseAndState`/operaciones — se recomienda **tres migraciones** por claridad y reversibilidad.

### T-MIG-1 — `0028_refactor_entities_schema_prep` (schema aditivo, sin destruir nada)
Operaciones (todas AddField/AlterField/RenameField que NO rompen FKs existentes):
1. `AddField` `OrganDirectory.categoria` — **nullable temporal** (`null=True`) para permitir backfill. (Se hará no-nullable en T-MIG-3.)
2. `AddField` `RegionalGovernment.ubigeo` (FK, null=True) y `RegionalGovernment.sigla` (CharField blank; usar `default=""` + `preserve_default=False`, patrón de `0027`).
3. `AddField` `Faculty.referencia_logo` (ImageField null) y `Faculty.ubigeo` (FK null=True).
4. `RenameField` `ExecutivePosition.nombre` → `nombre_masculino`.
5. `AddField` `ExecutivePosition.nombre_femenino` (CharField blank; `default=""` + `preserve_default=False`).
   - **Nota:** NO borrar `ExecutivePosition.codigo` aquí ni tocar su `unique_together`/`ordering` todavía (se hace en T-MIG-3), porque el `RenameField` cambia el estado que `unique_together` referencia; el cambio de constraint va después del backfill para evitar choques.

**Reverse:** operaciones inversas automáticas de Django (los AddField/RenameField son reversibles).

### T-MIG-2 — `0029_migrate_organ_type_data` (RunPython — datos)
Depende de `0028`. Una sola operación `migrations.RunPython(forwards, reverse=noop)`.

Pseudo-pasos de `forwards(apps, schema_editor)`:
1. Resolver modelos históricos: `Organ = apps.get_model("convenios","Organ")`, `OrganType = apps.get_model("convenios","OrganType")`, `OrganDirectory = apps.get_model("convenios","OrganDirectory")`, `ExecutingUnit`, `University`.
2. Construir mapa `organo.nombre → categoria`:
   - "Órgano del MINSA" → `ORGANO_MINSA`
   - "Universidad" → `UNIVERSIDAD`
   - "Órgano Regional" → `GOBIERNO_REGIONAL`  *(fallback si la fila regional no tiene `tipo_organo`)*
   - "Gobierno Regional" → `GOBIERNO_REGIONAL`  *(si el seed ya se actualizó)*
   - "MINSA DIRIS" → `MINSA_DIRIS`
   - "Unidad Ejecutora" → `UNIDAD_EJECUTORA`
   - (Si aparece un `organo.nombre` fuera del mapa: abortar con mensaje claro; no adivinar.)
3. **Backfill de `organo_directorio.categoria`** desde su `organo_id` + `tipo_organo` actuales (ambos aún existen en este punto):
   - Regla regional (prioritaria): si `org.nombre` ∈ {"Órgano Regional","Gobierno Regional"}, mirar el `tipo_organo.codigo` de la fila `OrganDirectory`: `GERESA`/`DIRESA` → `GOBIERNO_REGIONAL`; `DIRIS` → `MINSA_DIRIS`. Si no tiene `tipo_organo`, usar el fallback del mapa (`GOBIERNO_REGIONAL`).
   - Resto: `categoria = mapa[org.nombre]`.
   - **Seed `organo`**: en este mismo `forwards` (o uno previo), renombrar la fila `organo` "Órgano Regional" → "Gobierno Regional" y `get_or_create` de "MINSA DIRIS" (para coherencia con los labels de `categoria` y `OrganRepresentativeSerializer`).
4. **Migrar filas de `tipo_organo` a `organo_directorio`:** por cada fila de `OrganType`, crear una fila nueva en `OrganDirectory` con:
   - `categoria =` misma regla del paso 3: si `organtype.organo.nombre` es regional, derivar de `organtype.codigo` (`GERESA`/`DIRESA`→`GOBIERNO_REGIONAL`, `DIRIS`→`MINSA_DIRIS`); si no, `mapa[organtype.organo.nombre]`.
   - `nombre = organtype.nombre`
   - `siglas = organtype.codigo`
   - `gobierno_regional = None`
   - `activo = organtype.activo`
   - Guardar `dict {organtype.id → nuevo organo_directorio.id}`.
5. **Reapuntar FKs:** para cada `ExecutingUnit`, `tipo_organo_id = dict[tipo_organo_id_actual]`; para cada `University`, `tipo_entidad_id = dict[tipo_entidad_id_actual]`.
   - En este punto las columnas `unidad_ejecutora.tipo_organo_id` y `universidad.tipo_entidad_id` todavía apuntan (a nivel de BD) a `tipo_organo`; la reapuntación de la **constraint FK** ocurre en T-MIG-3 con `AlterField`. Aquí solo se actualizan los **valores** de las columnas a los nuevos ids de `organo_directorio`.
   - **Cuidado con el orden real de la constraint:** si la FK de BD apunta a `tipo_organo` en este momento, escribir un id de `organo_directorio` violaría la constraint. Por eso T-MIG-3 debe hacer el `AlterField` de las 2 FKs **antes** de que se validen, o bien realizar el `AlterField` de las FKs en `0028` como paso previo. **Decisión recomendada:** mover el `AlterField` de las 2 FKs (`ExecutingUnit.tipo_organo`, `University.tipo_entidad`) a `0028` usando `SeparateDatabaseAndState` NO es viable porque `OrganType` aún existe. **Solución robusta:** ejecutar la reapuntación de valores (paso 5) **en T-MIG-3, después** del `AlterField` de las FKs, no en T-MIG-2. Ver reorganización abajo.

> **Reorganización obligatoria del orden (crítica para PROTECT/constraints):** el agente `implement` debe garantizar esta secuencia efectiva:
> 1. Add `categoria` nullable + backfill `categoria` (T-MIG-1 + parte de T-MIG-2).
> 2. Crear las filas nuevas de `organo_directorio` a partir de `tipo_organo` y construir el dict (T-MIG-2).
> 3. `AlterField` de `ExecutingUnit.tipo_organo` y `University.tipo_entidad` para que apunten a `OrganDirectory` (T-MIG-3).
> 4. **Inmediatamente después del AlterField**, `RunPython` que reescribe `tipo_organo_id`/`tipo_entidad_id` con el dict guardado (guardar el dict en un modelo temporal o recomputarlo por clave natural `nombre`/`codigo`, ya que entre migraciones no se comparte estado Python).
> 5. `RemoveField` `organo_directorio.tipo_organo`, `organo`, `ubigeo`, `referencia_logo`.
> 6. `DeleteModel OrganType`.
> 7. `AlterField` `categoria` a no-nullable.
> 8. `RemoveField` `ExecutivePosition.codigo` + `AlterUniqueTogether` + `AlterModelOptions(ordering)`.
>
> Como el `dict` en memoria **no persiste entre migraciones**, la reapuntación de valores (paso 4) debe hacerse por **clave natural**: la fila nueva de `organo_directorio` se identifica por `(categoria, nombre, siglas)` = `(mapa[organo], organtype.nombre, organtype.codigo)`. Por eso conviene **fusionar T-MIG-2 y T-MIG-3 en una única migración** con `RunPython` intercalado entre las operaciones de schema, de modo que el `dict` viva en un solo `forwards`. **Decisión recomendada final:** ver T-MIG-2+3 fusionadas.

### T-MIG-2+3 (recomendada) — `0029_migrate_and_repoint_organ_types` (schema + datos en una migración)
Estructura de `operations` (en este orden exacto):
1. `RunPython` **backfill_categoria** — rellena `organo_directorio.categoria` desde `organo.nombre` (y valida el mapa).
2. `RunPython` **create_directory_from_organtype_and_repoint** — un único `forwards` que:
   - crea las filas nuevas de `organo_directorio` desde `tipo_organo` (construye `dict {organtype_id → nuevo id}` en memoria);
   - **antes** de reapuntar valores, ejecuta `schema_editor` NO es necesario: en este `RunPython` las FKs de BD siguen apuntando a `tipo_organo`. Por eso este paso **solo** crea las filas y guarda el mapeo en una **tabla puente temporal** o retorna; la reapuntación real de valores se hace tras el `AlterField`.
   - **Alternativa más simple y segura (recomendada):** NO reapuntar por id sino dejar que el `AlterField` posterior y un segundo `RunPython` reasignen por **clave natural**. Concretamente:
3. `AlterField` `ExecutingUnit.tipo_organo` → FK a `OrganDirectory` (PROTECT, requerido, limit_choices_to UNIDAD_EJECUTORA).
4. `AlterField` `University.tipo_entidad` → FK a `OrganDirectory` (PROTECT, requerido, limit_choices_to UNIVERSIDAD).
   - **Importante:** en SQLite (dev) `AlterField` de FK recrea la tabla; en PostgreSQL (prod) cambia la constraint. En ambos, los **valores** de la columna aún son ids de `tipo_organo` (que ya no coinciden con `organo_directorio`), por lo que la constraint podría fallar al validarse. Para evitarlo, el paso 2 debe **reescribir los valores** de `tipo_organo_id`/`tipo_entidad_id` a los nuevos ids **antes** del `AlterField`, aprovechando que en ese instante la FK todavía apunta a `tipo_organo` — lo cual también fallaría.
   - **Conclusión de diseño (resolver la circularidad):** usar `SeparateDatabaseAndState` para el `AlterField` de las 2 FKs: primero cambiar **solo el estado** (state) a `OrganDirectory`, dejando la **BD** con la FK vieja; luego el `RunPython` reescribe los valores; luego un `AlterField` de **solo BD** (`database_operations`) que apunta la constraint a `organo_directorio`. El agente `implement` debe implementar esta secuencia con `SeparateDatabaseAndState` para romper la dependencia circular constraint↔valores.

> **Instrucción neta para `implement`:** El resultado correcto es: (a) `organo_directorio` gana `categoria` poblada; (b) cada `tipo_organo` origina una fila `organo_directorio` de la categoría correspondiente; (c) `unidad_ejecutora.tipo_organo_id` y `universidad.tipo_entidad_id` quedan apuntando a esas nuevas filas y con la constraint FK hacia `organo_directorio`; (d) se elimina `tipo_organo`. Implementarlo con `SeparateDatabaseAndState` + `RunPython` respetando que ninguna constraint `PROTECT`/FK se viole en ningún punto intermedio. Validar con `python manage.py migrate` sobre una copia con datos reales antes de cerrar.

**Reverse de los `RunPython`:** `migrations.RunPython.noop` documentado con comentario ("refactor no reversible a nivel de datos").

### T-MIG-3 — `0030_finalize_refactor` (schema destructivo final)
Operaciones (en este orden):
1. `RemoveField` `OrganDirectory.tipo_organo`.
2. `RemoveField` `OrganDirectory.organo`.
3. `RemoveField` `OrganDirectory.ubigeo`.
4. `RemoveField` `OrganDirectory.referencia_logo`.
5. `DeleteModel` `OrganType`.
6. `AlterField` `OrganDirectory.categoria` → no-nullable (quitar `null=True`).
7. `RemoveField` `ExecutivePosition.codigo`.
8. `AlterUniqueTogether` `ExecutivePosition` → `{("organo","nombre_masculino")}`.
9. `AlterModelOptions` `ExecutivePosition` → `ordering=["organo","nombre_masculino"]`.

> El agente debe validar el orden real que produzca `makemigrations` y **fundir/renumerar** las 3 migraciones si Django lo exige, siempre preservando la secuencia lógica de arriba. `DeleteModel OrganType` solo puede ejecutarse cuando **ninguna** FK (state ni BD) apunte a `tipo_organo`.

**Criterio de aceptación de la migración:**
- `python manage.py makemigrations --check --dry-run` → sin cambios pendientes tras aplicar.
- `python manage.py migrate` → OK sobre BD con datos (dev SQLite y, si es posible, un dump PostgreSQL).
- Post-migración: 0 filas huérfanas; `unidad_ejecutora.tipo_organo_id` y `universidad.tipo_entidad_id` resuelven a filas `organo_directorio` con la `categoria` esperada.

---

## 3. Serializers — `apps/convenios/serializers.py`

### T-SER-1 — `ConventionReadSerializer` (líneas ~39-46)
- Campo `tipo_organo_directorio` hoy usa `source="organo_directorio.tipo_organo.nombre"` → **inválido** tras el drop.
  - Reemplazar por `source="organo_directorio.get_categoria_display"` (label español de la categoría). Documentar el nuevo significado (categoría del directorio, no sub-tipo).
- `tipo_entidad_universidad` usa `source="universidad.tipo_entidad.nombre"` → sigue válido (`tipo_entidad` ahora es `OrganDirectory`, que tiene `nombre`). Sin cambio funcional; verificar.
- **Criterio:** el serializer no referencia `organo_directorio.tipo_organo`.

### T-SER-2 — `OrganRepresentativeSerializer.validate` (líneas ~352-360)
- La validación `cargo.organo_id != organo_directorio.organo_id` usa `organo_directorio.organo_id`, **eliminado**.
- Redefinir la coherencia cargo↔órgano en términos del nuevo modelo (decisión cerrada):
  - `ExecutivePosition` conserva `organo` (FK→`Organ`). `OrganDirectory` ya no tiene `organo`, ahora tiene `categoria`.
  - Comparar `cargo.organo.nombre` contra `organo_directorio.get_categoria_display()` (el label de la categoría replica el nombre de `organo` gracias al seed actualizado). Si difieren → `ValidationError` en español ("El cargo no corresponde a la categoría del órgano del directorio.").
- **Criterio:** el serializer no accede a `organo_directorio.organo_id`; la validación usa `categoria`.

### T-SER-3 — (sin cambio de archivo) `UniversityCareerSerializer` no se toca. Verificar que `Faculty.objects.all()` sigue válido tras añadir `referencia_logo`/`ubigeo` a `Faculty` (sí).

> Los serializers de las entidades CRUD genéricas (`_auto_serializer` con `fields="__all__"`) se ajustan automáticamente al nuevo modelo; los cambios explícitos van en `views.py` (detalles/filtros). Ver §4.

---

## 4. Views / URLs / filtros — `apps/convenios/views.py`, `urls.py`

### T-VIEW-1 — Retirar `organ-types`
- En `ENTITY_VIEWSETS` borrar la entrada `"organ-types": _entity_viewset(m.OrganType, ...)` (líneas ~593-598).
- Eliminar cualquier import/referencia a `m.OrganType`.
- **Criterio:** `GET /api/v1/organ-types/` → 404. No aparece en OpenAPI.

### T-VIEW-2 — `organ-directories` (entrada `ENTITY_VIEWSETS`, líneas ~616-626)
- `filterset_fields`: quitar `organo` y `tipo_organo`; conservar `gobierno_regional`, `activo`; **añadir** `categoria`.
- `search_fields`: quitar `numero_ruc` (ese campo ya fue retirado en 0027; hoy referencia campo inexistente — verificar y limpiar). Mantener `nombre`, `siglas`.
- `logo=True`: **quitar** (el campo `referencia_logo` se elimina de `OrganDirectory`). Retirar el mixin de logo para este viewset.
- `detalles`: quitar `organo` y `tipo_organo` (y `gobierno_regional` se conserva). No hay `_detalle` para un choice; exponer `categoria` como campo plano (el `_auto_serializer` ya lo incluye por `fields="__all__"`).
- **Criterio:** `organ-directories` filtra por `categoria`/`gobierno_regional`/`activo`; ya no acepta `organo`/`tipo_organo`; sin acciones `upload-logo`/`logo-url`.

> **Verificar** que `search_fields=["nombre","siglas","numero_ruc"]` no rompa: `numero_ruc` ya no existe en `organo_directorio` (retirado en `0027`). Corregir a `["nombre","siglas"]`.

### T-VIEW-3 — `executing-units` (líneas ~627-637)
- `filterset_fields`: mantiene `tipo_organo`, `gobierno_regional`, `activo` (el filtro por `tipo_organo` ahora resuelve contra `organo_directorio`; funciona igual, es un id).
- `detalles["tipo_organo"]`: sigue `_detalle_nombre` (ahora extrae de `OrganDirectory.nombre`). Correcto.
- **Criterio:** `executing-units` filtra por `tipo_organo` (id de `organo_directorio` categoría UNIDAD_EJECUTORA); `tipo_organo_detalle` muestra `{id, nombre}` del directorio.

### T-VIEW-4 — `universities` (líneas ~640-650)
- `filterset_fields` incluye `tipo_entidad` — sigue válido (id de `organo_directorio`).
- `detalles["tipo_entidad"]`: `_detalle_nombre` (extrae `OrganDirectory.nombre`). Correcto.
- **Criterio:** `universities` filtra por `tipo_entidad` (categoría UNIVERSIDAD) y expone `tipo_entidad_detalle`.

### T-VIEW-5 — `regional-governments` (líneas ~613-615)
- Exponer los nuevos campos `ubigeo` y `sigla`: el `_auto_serializer` los incluye por `fields="__all__"`.
- **Añadir detalle** de `ubigeo`: pasar `detalles={"ubigeo": _detalle_ubigeo}` y usar `select_related("ubigeo")` (patrón de `executing-units`/`ipress`). Opcional pero recomendado para el frontend.
- Filtros: conservar `region`, `activo`. (Opcional: añadir filtro por `ubigeo`.)
- **Criterio:** lectura de `regional-governments` incluye `ubigeo`, `ubigeo_detalle` y `sigla`.

### T-VIEW-6 — `faculties` (`FacultyViewSet`, líneas ~506-541)
- Añadir soporte de logo: incluir `LogoStorageMixin` en el viewset (hoy `FacultyViewSet` extiende solo `_entity_viewset(m.Faculty, ...)` sin `logo=True`). Cambiar la construcción a `_entity_viewset(m.Faculty, ..., logo=True)` **o** añadir `LogoStorageMixin` como base explícita (mismo patrón que `IpressViewSet`).
- El `_auto_serializer` ya expondrá `referencia_logo` como URL de solo lectura al detectar el `ImageField`, y `ubigeo` por `fields="__all__"`.
- Añadir `detalles={"ubigeo": _detalle_ubigeo}` + `select_related("ubigeo")` (opcional, recomendado).
- **Criterio:** `faculties/{id}/upload-logo` y `logo-url` disponibles; lectura expone `referencia_logo` (URL) y `ubigeo`.

### T-VIEW-7 — `executive-positions` (líneas ~581-586)
- `search_fields`: quitar `codigo`; usar `["nombre_masculino", "nombre_femenino"]`.
- `filterset_fields`: mantener `organo`, `activo`.
- `detalles={"organo": _detalle_nombre}`: se conserva.
- **Criterio:** el CRUD `executive-positions` ya no expone `codigo`; expone `nombre_masculino`/`nombre_femenino`; búsqueda por ambos nombres; unicidad `(organo, nombre_masculino)`.

### T-VIEW-8 — `SOLICITANTE_MODELS` (líneas ~816-823)
- Contiene `m.OrganDirectory` — sigue válido (no se elimina el modelo). Sin cambios; verificar que no referencia `OrganType`.

### T-URL-1 — `urls.py`
- No hay registro explícito de `organ-types` (se registra por el loop sobre `ENTITY_VIEWSETS`). Al quitarlo de `ENTITY_VIEWSETS` (T-VIEW-1) la ruta desaparece. **No** requiere edición manual salvo verificación.

---

## 5. Services — `apps/convenios/services.py`

### T-SVC-1 — `crear_convenio` (línea ~181) [RESUELTO]
- `tipo_organo = organo.tipo_organo.codigo if organo.tipo_organo_id else ""` → **inválido** tras el drop.
- Reescribir usando `categoria = organo.categoria`:
  - Marco: permitir solo si `categoria == "GOBIERNO_REGIONAL"` (reemplaza `tipo_organo in {"GERESA","DIRESA"}`). Mensaje en español acorde.
  - Específico: rama DIRIS pasa a `if categoria == "MINSA_DIRIS":` (exenta de Marco); el `else` (requiere Marco vigente) queda igual.
- Buscar cualquier otra lectura de `organo_directorio.tipo_organo` en todo `services.py` y aplicar el mismo criterio.
- **Criterio:** RN-1 sigue vigente leyendo `categoria`; `services.py` no accede a `organo_directorio.tipo_organo`; `python manage.py check` limpio.

### T-SVC-2 — `actualizar_convenio` / `_validar_partes_por_tipo`
- Verificar que no lean `organo_directorio.tipo_organo`/`.organo`. (De la lectura actual, la validación de partes usa `facultad`/`unidad_ejecutora`, sin `tipo_organo` del directorio — confirmar.)

---

## 6. Selectors — `apps/convenios/selectors.py`

### T-SEL-1 — `convenios_visibles` / queryset con `select_related` (línea ~25)
- `select_related("organo_directorio__tipo_organo", "universidad__tipo_entidad", ...)`:
  - **Quitar** `organo_directorio__tipo_organo` (relación eliminada).
  - `universidad__tipo_entidad` sigue válido (ahora es `OrganDirectory`); conservar.
- **Criterio:** el selector no referencia `organo_directorio__tipo_organo`; sin errores al listar convenios.

---

## 7. Otros consumidores fuera de `apps/convenios`

### T-EXT-1 — `apps/common/serializers.py` (`MeSerializer` / perfiles)
- Las coincidencias de `tipo_entidad` en `apps/common/serializers.py` se refieren a `tipo_contenido.model` (perfiles institucionales), **no** al FK `University.tipo_entidad`. **No requieren cambios.** Verificar y dejar constancia.

### T-EXT-2 — `apps/common/views.py`
- Verificar la coincidencia detectada (`tipo_organo`/`tipo_entidad`) y confirmar que no accede a `OrganType`/`organo_directorio.tipo_organo`. Ajustar solo si toca esas relaciones.

---

## 8. Comandos de management y seeds a revisar

### T-CMD-1 — `apps/convenios/management/commands/load_universidades.py`
- Importa y usa `OrganType` (líneas 29, 95, 122-123, 145) para validar `tipo_entidad_id` (`OrganType.objects.filter(organo__nombre="Universidad")`).
- Reescribir para resolver `tipo_entidad` contra `OrganDirectory.objects.filter(categoria="UNIVERSIDAD")`:
  - `entidades = {o.id: o for o in OrganDirectory.objects.filter(categoria="UNIVERSIDAD")}`
  - Ajustar el mensaje de error ("no es tipo de entidad UNIVERSIDAD del directorio").
  - Actualizar el docstring de mapeo (`tipo_entidad_id` → `organo_directorio`, categoría UNIVERSIDAD).
  - **Ojo:** tras la migración, los ids de `tipo_entidad_id` en los Excel existentes apuntan a las **nuevas** filas de `organo_directorio` migradas — documentar que los Excel deben usar los nuevos ids del directorio.
- **Criterio:** `load_universidades --dry-run` valida contra `organo_directorio` categoría UNIVERSIDAD; no importa `OrganType`.

### T-CMD-2 — `load_gobiernos_regionales.py`
- Revisar si setea `ubigeo`/`sigla` (nuevos campos de `RegionalGovernment`). Si el Excel/seed los trae, mapearlos; si no, dejarlos opcionales. Documentar en el docstring.

### T-CMD-3 — Seeds en migraciones (`0002_seed_catalogos.py`, `0016`, `0018`, `0019`)
- Estas migraciones ya están aplicadas y **no deben editarse** (historial). No requieren cambio. Anotar que los datos que sembraron (tipos de órgano) quedan **migrados** por T-MIG-2+3 a `organo_directorio`.

---

## 9. Documentación a actualizar (mismo cambio)

### T-DOC-1 — `docs/db_schema_modulo_01_convenios.md`
- **`cargo_ejecutivo`** (línea ~42 y su sección): quitar `codigo`; renombrar `nombre`→`nombre_masculino`; añadir `nombre_femenino`; unicidad `(organo_id, nombre_masculino)`.
- **`tipo_organo`** (sección ~89-121): **eliminar** la tabla del documento; anotar que fue retirada y sus filas migradas a `organo_directorio`.
- **`organo_directorio`** (sección ~133-142): quitar `organo_id`, `tipo_organo_id`, `ubigeo_id`, `referencia_logo`; añadir `categoria` (choices: ORGANO_MINSA/UNIVERSIDAD/GOBIERNO_REGIONAL/MINSA_DIRIS/UNIDAD_EJECUTORA); actualizar el filtro del endpoint (`categoria`, `gobierno_regional`, `activo`); quitar la mención al logo.
- **`organo`** (tabla de categorías): renombrar "Órgano Regional" → "Gobierno Regional"; agregar "MINSA DIRIS".
- **`unidad_ejecutora`** (línea ~162, ~169, ~171): `tipo_organo_id` → FK a `organo_directorio` (categoría UNIDAD_EJECUTORA via `limit_choices_to`).
- **`universidad`** (línea ~231): `tipo_entidad_id` → FK a `organo_directorio` (categoría UNIVERSIDAD).
- **`gobierno_regional`** (sección ~123): añadir `ubigeo_id` (FK opcional) y `sigla`.
- **`facultad`** (sección ~246): añadir `referencia_logo` y `ubigeo_id`; anotar endpoint con logo (`upload-logo`/`logo-url`).
- **`convenio`** (línea ~423, ~377): actualizar la nota "su tipo se deriva de la entidad (`organo_directorio → tipo_organo`)" → refleja el nuevo modelo (categoría / decisión BLOQUEANTE).

### T-DOC-2 — `docs/db_schema_er_global.md`
- Eliminar `tipo_organo` del ER; redibujar las FKs `unidad_ejecutora.tipo_organo_id` y `universidad.tipo_entidad_id` hacia `organo_directorio`; añadir `organo_directorio.categoria`; añadir `gobierno_regional.ubigeo_id`/`sigla`, `facultad.referencia_logo`/`ubigeo_id`; actualizar `cargo_ejecutivo`.

### T-DOC-3 — `CLAUDE.md`
- Sección **catálogos parametrizables** (lista de `ENTITY_VIEWSETS`): quitar `organ-types`; actualizar `executive-positions` (ya no unicidad `(organo,codigo)` ni FK con `codigo` → ahora `(organo, nombre_masculino)`, sin `codigo`, con `nombre_masculino`/`nombre_femenino`); quitar la mención de `organ-types` como filtrable por `organo`.
- Sección **Directorio de órganos y representantes (Módulo 1)**: `organ-directories` ahora lleva `categoria` (sin `organo`/`tipo_organo`/`ubigeo`/`referencia_logo`, sin logo); filtros `categoria`/`gobierno_regional`. `executing-units`: `tipo_organo` es FK a `organo_directorio` (categoría UNIDAD_EJECUTORA). `universities`: `tipo_entidad` es FK a `organo_directorio` (categoría UNIVERSIDAD).
- Donde se liste `organ-types`/`tipo_entidad` como `OrganType`: actualizar a `organo_directorio`.
- Añadir `gobierno_regional` (ubigeo/sigla) y `faculties` (logo/ubigeo) donde corresponda.
- Marcar endpoint retirado (404): `organ-types`.

---

## 10. Checklist de verificación (cierre del módulo)

- [x] **Decisión de negocio resuelta** (5 categorías; GOBIERNO_REGIONAL=GERESA/DIRESA, MINSA_DIRIS=DIRIS) aplicada en T-SVC-1, T-SER-1/T-SER-2, T-MIG-2 (backfill) y seed `organo`.
- [ ] `python manage.py makemigrations --check --dry-run` → **sin cambios pendientes** (modelos y migraciones sincronizados).
- [ ] `python manage.py migrate` → OK sobre BD con datos (dev SQLite; validar también con dump PostgreSQL si es posible). Ninguna violación de `PROTECT`/FK en pasos intermedios.
- [ ] `python manage.py check` → 0 errores.
- [ ] OpenAPI (`drf-spectacular`) genera con **0 errores/warnings** nuevos; `organ-types` ausente del schema.
- [ ] `/code-review` ejecutado (skill obligatoria para modelos/migraciones/serializers/views).
- [ ] **Escenarios de prueba manuales (smoke):**
  - `GET /api/v1/organ-types/` → **404**.
  - `GET /api/v1/organ-directories/?categoria=UNIVERSIDAD` → filtra por categoría; sin campos `organo`/`tipo_organo`/`ubigeo`/`referencia_logo`.
  - `GET /api/v1/executing-units/?tipo_organo=<id>` → resuelve contra `organo_directorio`; `tipo_organo_detalle` presente.
  - `GET /api/v1/universities/?tipo_entidad=<id>` → resuelve contra `organo_directorio`; `tipo_entidad_detalle` presente.
  - `GET /api/v1/regional-governments/` → incluye `ubigeo`, `ubigeo_detalle`, `sigla`.
  - `POST /api/v1/faculties/{id}/upload-logo/` → sube logo; `GET` expone `referencia_logo` (URL) y `ubigeo`.
  - `GET /api/v1/executive-positions/` → sin `codigo`; con `nombre_masculino`/`nombre_femenino`; búsqueda por ambos.
  - `POST /api/v1/conventions/` (Marco por GERESA/DIRESA y Específico DIRIS) → RN-1 sigue funcionando según la decisión BLOQUEANTE.
  - `GET /api/v1/conventions/` (list) → sin errores de `select_related` (T-SEL-1); `tipo_entidad_universidad` presente.
  - `load_universidades --dry-run` → valida `tipo_entidad_id` contra `organo_directorio` categoría UNIVERSIDAD.
- [ ] Datos migrados verificados: cada fila `tipo_organo` original tiene su fila `organo_directorio` equivalente; `unidad_ejecutora`/`universidad` reapuntadas sin huérfanos.
- [ ] `docs/db_schema_modulo_01_convenios.md`, `docs/db_schema_er_global.md` y `CLAUDE.md` actualizados en el mismo cambio.
