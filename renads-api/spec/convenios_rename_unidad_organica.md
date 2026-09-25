# Spec — Refactor de rename: `OrganDirectory` → `OrganicUnit` (unidad orgánica)

> Módulo: **Gestionar Convenios** (`apps/convenios`) — con impacto en `apps/common`.
> Tipo: **refactor de rename in-place** (sin pérdida de datos). BD real en PostgreSQL.
> Proceso: **SDD**. Este spec debe ser aprobado por el usuario antes de implementar.

---

## 1. Resumen del refactor

Renombrar por completo la entidad hoy llamada `OrganDirectory` a la nueva nomenclatura
**unidad orgánica** (`OrganicUnit`), incluyendo modelo, tabla, columnas FK entrantes,
`related_name`, endpoint del router y documentación.

| Elemento | Actual | Nuevo |
|---|---|---|
| Modelo Django | `OrganDirectory` | `OrganicUnit` |
| Tabla | `organo_directorio` | `unidad_organica` |
| Endpoint (slug router) | `organ-directories` | `organic-units` |
| Atributo FK «directorio» | `organo_directorio` | `unidad_organica` |
| Atributo FK «directivo» | `organo_directivo` (en `ExecutivePosition`) | `unidad_organica` |
| `db_column` FK entrantes | `organo_directorio_id` / `organo_directivo_id` | `unidad_organica_id` |

**Alcance NO tocado (importante):**
- `Organ` (tabla `organo`) — es la tabla canónica de categorías; NO se renombra. La FK
  `OrganDirectory.organo` (db_column `organo_id`, related_name `organos_directorio_por_categoria`)
  se conserva salvo el ajuste opcional de `related_name` (ver T2).
- `ipress` tiene **PK textual** (`codigo_renipress`), no tiene columna `id`. Este refactor
  **no** toca ninguna FK a `Ipress`.
- Los **GFK** (`GenericForeignKey` vía `tipo_contenido`/`id_objeto` o `solicitante_tipo_contenido`/
  `solicitante_id_objeto`) que apuntan a esta entidad **NO tienen columna FK dedicada**: se
  resuelven por `ContentType`. Se ven afectados solo en las **listas de modelos** (`REPRESENTANTE_MODELS`,
  `SOLICITANTE_MODELS`, `ASSIGNABLE_PROFILE_MODELS`) por el cambio de nombre de clase, no por columnas.

---

## 2. Hallazgos de código (fuente de verdad medida)

### 2.1 Definición del modelo
- `apps/convenios/models.py:325` — `class OrganDirectory(models.Model)`, `db_table="organo_directorio"`
  (línea 351), `verbose_name="órgano del directorio"`.
- Constraint: `UniqueConstraint(fields=["organo","nombre"], name="uniq_organo_dir_organo_nombre")` (línea 358).
- Propiedad **`categoria`** (líneas 367-375) — es un `@property` derivado de `self.organo.nombre`
  (mapeo `_NOMBRE_A_CATEGORIA`), **NO una columna**. `get_categoria_display()` idem.

### 2.2 FK entrantes REALES a `OrganDirectory` (columnas a renombrar)

Solo **4 FK con columna dedicada** apuntan hoy a `OrganDirectory`:

| # | Modelo (archivo:línea) | Atributo actual | `db_column` actual | `related_name` actual | `on_delete` |
|---|---|---|---|---|---|
| F1 | `ExecutivePosition` (`apps/convenios/models.py:215`) | `organo_directivo` | `organo_directivo_id` | `cargos` | PROTECT (null=True) |
| F2 | `Convention` (`apps/convenios/models.py:891`) | `organo_directorio` | `organo_directorio_id` | `convenios` | PROTECT |
| F3 | `ConventionParty` (`apps/convenios/models.py:994`) | `organo_directorio` | `organo_directorio_id` | `+` | PROTECT |
| F4 | `TechnicalEvaluation` (`apps/convenios/models.py:1069`) | `organo_directorio` | `organo_directorio_id` | `+` | SET_NULL (null=True) |
| F5 | `UserProfile` (`apps/common/models.py:169`) | `unidad_organica` | `unidad_organica_id` | `perfiles_usuarios` | PROTECT (null=True) |

> **Nota clave 1:** El atributo/columna de `UserProfile` (F5) **ya se llama `unidad_organica` /
> `unidad_organica_id`** (adelantado en migración `common 0006`). Solo hay que actualizar la
> referencia de string del modelo (`"convenios.OrganDirectory"` → `"convenios.OrganicUnit"`);
> **no requiere `RenameField` ni `AlterField` de columna** para F5.
>
> **Nota clave 2:** `ExecutivePosition` tiene `unique_together=(("organo_directivo","nombre_masculino"))`
> y `ordering=["organo_directivo","nombre_masculino"]` (líneas 233-234) que deben actualizarse al
> nuevo nombre de campo `unidad_organica`.

### 2.3 FK que la tarea mencionaba pero que **YA NO** apuntan a esta entidad (verificado)
- `OrganRepresentative.organo_representante` / `organo_directorio`: **no existe FK directa** — es
  **polimórfica** (GFK `entidad` vía `tipo_contenido`/`id_objeto`, migración 0038). Solo aparece en
  listas de modelos y validaciones por ContentType.
- `University.tipo_entidad`: apunta a **`UniversityEntityType`** (migración 0052), **no** a
  `OrganDirectory`. **No tocar.**
- `ExecutingUnit.tipo_organo`: **ese campo ya no existe** en el modelo actual (`ExecutingUnit`
  hoy tiene `ambito_geografico_sanitario`, no `tipo_organo`). **No tocar.**
- `ConventionParty.organo_representante`: FK a `OrganRepresentative` (no a esta entidad). **No tocar.**

### 2.4 Referencias de código no-FK (call sites a actualizar)
- `apps/convenios/models.py` — docstrings/comentarios (líneas 167, 202-204, 515-516) + F1..F4.
- `apps/convenios/views.py` (27) — `_OrganDirectorySerializer` (764), `OrganDirectoryViewSet` (798-811),
  `_detalle_organo_directorio` (510), `ExecutivePositionViewSet`/serializer usa `organo_directivo`
  (819, 836-840, 859, 865, 872), slug `"organ-directories"` (941), `SOLICITANTE_MODELS` (1135),
  `REPRESENTANTE_MODELS` (1175), select_related `organo_directorio`/`organo_representante` (221),
  comentarios (1172, 1188).
- `apps/convenios/serializers.py` (14) — `organo_directorio_nombre`/`tipo_organo_directorio`
  (41-44), campos en `Meta.fields` (63, 137, 198, 240), `organo_directorio_detalle` +
  `get_organo_directorio_detalle` (190, 205-206), validación de parte por `organo_directivo_id`
  (500, 505), docstrings (436, 498).
- `apps/convenios/services.py` (34) — `import OrganDirectory` (31), lecturas de
  `datos["organo_directorio"]`/`convenio.organo_directorio` (255, 309, 364, 388, 407, 929, 972,
  977, 1145, 1177), `_validar_coherencia_parte(organo_directorio=...)` (858-879), `sincronizar_partes`
  (890, 902, 906, 918, 946, 952), `_bc_resolver_organo`/`_bc_solicitante` (1021-1029, 1116-1119),
  `.categoria` lecturas (256, 407, 929, 1092 — property, ver §6).
- `apps/convenios/filters.py:29` — filter `"organo_directorio": ["exact"]`.
- `apps/convenios/selectors.py:26` — `select_related("organo_directorio", "universidad__tipo_entidad")`.
- `apps/convenios/pdf.py` — `parte.organo_directorio` (84, 87), `convenio.organo_directorio.organo` (220).
- `apps/convenios/admin.py` (7) — import (33), `@admin.register(OrganDirectory)` +
  `OrganDirectoryAdmin` (204-205), `list_display` con `organo_directivo` (192),
  `organo_directorio` en Convention/ConventionParty admin (307, 323, 325).
- `apps/convenios/management/commands/load_universidades.py` (4) — import (32),
  `OrganDirectory.objects.filter(categoria="UNIVERSIDAD")` (98) — ver §6.
- `apps/common/models.py:170` — string `"convenios.OrganDirectory"` → `"convenios.OrganicUnit"` (F5).
- `apps/common/serializers.py` (5) — `_organ_directory_queryset` import diferido (273-275),
  `ASSIGNABLE_PROFILE_MODELS` (683, 701). (Los atributos `unidad_organica*` en 247-266, 319, 432,
  464, 479, 552, 581, 593 ya usan el nombre nuevo — NO se tocan.)
- `docs/tramas/generar_tramas.py` (4) — labels/ayudas con `organo_directorio` y `organ-directories`
  (638-640, 763, 775).

### 2.5 Migración
- Última migración en `apps/convenios/migrations/`: **`0053_professionalcareer_orden.py`**.
  La nueva será **`0054`**. En `apps/common/migrations/`, si F5 cambia solo el `to=` del string,
  Django genera un `AlterField` menor (dependiente de la 0054 de convenios).

---

## 3. Tareas de implementación (ordenadas, archivo por archivo)

> Ejecutar en este orden. Los cambios de modelo (T1-T2) preceden a la migración (T10);
> el resto de call sites (T3-T9) pueden hacerse en paralelo pero antes de correr tests.

### T1 — `apps/convenios/models.py`: renombrar la clase y la tabla
- Renombrar `class OrganDirectory` → `class OrganicUnit`.
- `db_table = "organo_directorio"` → `"unidad_organica"`.
- `verbose_name = "unidad orgánica"`, `verbose_name_plural = "unidades orgánicas"`.
- Renombrar el `UniqueConstraint.name` `"uniq_organo_dir_organo_nombre"` →
  `"uniq_unidad_organica_organo_nombre"` (opcional pero recomendado por coherencia; requiere
  `RemoveConstraint`+`AddConstraint` en la migración — ver T10).
- Conservar la propiedad `categoria` y `get_categoria_display()` sin cambios funcionales
  (solo actualizar el comentario de la línea 167).
- **Criterio de aceptación:** `OrganicUnit` es la única definición; no queda `OrganDirectory`
  en el archivo; `db_table` = `unidad_organica`.

### T2 — `apps/convenios/models.py`: renombrar las FK entrantes F1-F4
- **F1 `ExecutivePosition.organo_directivo`** → `unidad_organica`:
  - `to="OrganicUnit"`, `db_column="unidad_organica_id"`, `related_name="cargos"` (mantener),
    `verbose_name="unidad orgánica"`.
  - Actualizar `unique_together=(("unidad_organica","nombre_masculino"),)`.
  - Actualizar `ordering=["unidad_organica","nombre_masculino"]`.
- **F2 `Convention.organo_directorio`** → `unidad_organica`:
  `to=OrganicUnit`, `db_column="unidad_organica_id"`, `related_name="convenios"` (mantener).
- **F3 `ConventionParty.organo_directorio`** → `unidad_organica`:
  `to=OrganicUnit`, `db_column="unidad_organica_id"`, `related_name="+"`.
- **F4 `TechnicalEvaluation.organo_directorio`** → `unidad_organica`:
  `to=OrganicUnit`, `db_column="unidad_organica_id"`, `related_name="+"`, `on_delete=SET_NULL`.
- Actualizar docstrings/comentarios que mencionen «órgano del directorio»/`organo_directorio`.
- **Criterio de aceptación:** las 4 FK usan atributo `unidad_organica`, `db_column`
  `unidad_organica_id`, `to` = `OrganicUnit`; `related_name` sin colisiones.

### T3 — `apps/common/models.py`: reapuntar F5 (solo el string `to`)
- `UserProfile.unidad_organica`: cambiar `"convenios.OrganDirectory"` → `"convenios.OrganicUnit"`.
  **No** cambiar atributo, `db_column` ni `related_name` (ya son `unidad_organica` /
  `unidad_organica_id` / `perfiles_usuarios`).
- **Criterio de aceptación:** no queda `OrganDirectory` en `apps/common`; F5 apunta a `OrganicUnit`.

### T4 — `apps/convenios/views.py`
- Renombrar `_OrganDirectorySerializer` → `_OrganicUnitSerializer` y `OrganDirectoryViewSet`
  → `OrganicUnitViewSet`; actualizar todas las referencias `m.OrganDirectory` → `m.OrganicUnit`.
- `_detalle_organo_directorio` → `_detalle_unidad_organica` (renombrar función y sus usos en
  detalles de `ExecutivePositionViewSet`/serializer).
- `ExecutivePosition` serializer/viewset: `organo_directivo` → `unidad_organica` en
  `detalles`, `validate` (attrs.get / getattr / `unidad_organica.organo_id`), `filterset`
  (`"unidad_organica": ["exact","isnull"]`) y `select_related`.
- `select_related("organo_directorio", ...)` (línea 221) → `select_related("unidad_organica", ...)`.
- Router `ENTITY_VIEWSETS`: **slug `"organ-directories"` → `"organic-units"`** (línea 941), valor
  `OrganicUnitViewSet`.
- `SOLICITANTE_MODELS` y `REPRESENTANTE_MODELS`: `m.OrganDirectory` → `m.OrganicUnit`.
  Actualizar comentarios (1172, 1188).
- **Criterio de aceptación:** `GET /api/v1/organic-units/` responde; `organ-directories` ya no
  existe en el router; el serializer de cargos usa `unidad_organica`.

### T5 — `apps/convenios/serializers.py`
- Read serializer de partes: renombrar `organo_directorio_nombre` →
  `unidad_organica_nombre` (`source="unidad_organica.nombre"`), `tipo_organo_directorio` →
  `tipo_unidad_organica` (`source="unidad_organica.get_categoria_display"`).
- Read serializer de evaluación técnica: `organo_directorio_detalle` →
  `unidad_organica_detalle`, método `get_organo_directorio_detalle` →
  `get_unidad_organica_detalle` (`_detalle_fk(obj.unidad_organica, ...)`).
- Todos los `Meta.fields` que listen `organo_directorio` → `unidad_organica` (63, 137, 198, 240)
  y los campos derivados renombrados.
- Validación de parte firmante: `cargo.organo_directivo_id` → `cargo.unidad_organica_id` (500, 505);
  actualizar docstrings (436, 498).
- **Nota de contrato de API (documentar en el PR):** el rename de los campos de lectura
  (`organo_directorio` → `unidad_organica`, `*_detalle`, `*_nombre`) es un **cambio de contrato**
  para el frontend. Confirmar con el usuario si se mantienen alias temporales o se rompe limpio.
- **Criterio de aceptación:** serializers referencian solo `unidad_organica`; no hay
  `SerializerMethodField` huérfano.

### T6 — `apps/convenios/services.py`
- `from ...models import OrganDirectory` → `OrganicUnit` (línea 31) y todos los usos.
- Todas las lecturas de `datos["organo_directorio"]` / `convenio.organo_directorio` /
  `organo_directorio=...` (create/update de convenio, `crear_adenda`, campos `editables`,
  mapeo `EDITABLE_FIELD_MAP` línea 977, `_bc_*`) → `unidad_organica`.
- `_validar_coherencia_parte(organo_directorio=...)` → parámetro `unidad_organica` y su cuerpo
  (comparaciones `id_objeto == unidad_organica.id`, `cargo_ejecutivo.unidad_organica_id`).
- `sincronizar_partes`: claves de dict `"organo_directorio"` → `"unidad_organica"` (890, 902-918,
  946, 952).
- `_bc_resolver_organo` / `_bc_solicitante`: retorno `OrganicUnit`, mensajes de error que
  citan `organo_directorio` — mantener el **texto del error orientado al usuario** coherente con
  la nueva nomenclatura («unidad orgánica») salvo que el frontend dependa de la clave literal
  `organo_directorio` en el payload de entrada (ver T5 nota de contrato).
- `ContentType.get_for_model(OrganicUnit)` (1119).
- **NO** modificar la lógica de `.categoria` (property) — solo el nombre de la variable/atributo
  contenedor si aplica.
- **Criterio de aceptación:** `services.py` no importa ni referencia `OrganDirectory`; las reglas
  de negocio (RN-1 Convenio Marco, composición de partes, coherencia parte↔representante) siguen
  intactas.

### T7 — `apps/convenios/filters.py` y `selectors.py`
- `filters.py:29`: filter key `"organo_directorio"` → `"unidad_organica"` (mantener `["exact"]`).
- `selectors.py:26`: `select_related("organo_directorio", ...)` → `"unidad_organica"`.
- **Criterio de aceptación:** el filtro del endpoint de convenios opera sobre `unidad_organica`;
  los selectores no lanzan `FieldError`.

### T8 — `apps/convenios/pdf.py`
- `parte.organo_directorio` (84, 87) → `parte.unidad_organica`.
- `convenio.organo_directorio.organo` (220) → `convenio.unidad_organica.organo`.
- **Criterio de aceptación:** `construir_contexto` arma el contexto de PDF con `unidad_organica`
  sin `AttributeError`.

### T9 — `apps/convenios/admin.py`, `apps/common/serializers.py`, comando de carga
- `admin.py`: import `OrganDirectory` → `OrganicUnit`; `@admin.register(OrganicUnit)`;
  `class OrganicUnitAdmin`; `list_display` de `ExecutivePosition` `organo_directivo` →
  `unidad_organica` (192); `list_display`/`search_fields` de Convention/ConventionParty
  `organo_directorio` → `unidad_organica` (307, 323, 325).
- `apps/common/serializers.py`: renombrar helper `_organ_directory_queryset` →
  `_organic_unit_queryset` con import diferido de `OrganicUnit`; `ASSIGNABLE_PROFILE_MODELS`
  `OrganDirectory` → `OrganicUnit` (683, 701).
- `management/commands/load_universidades.py`: import `OrganicUnit`;
  `OrganicUnit.objects.filter(categoria="UNIVERSIDAD")` (98) — ver §6 (bug latente, NO arreglar
  salvo que el rename lo obligue a compilar; conservar el mismo comportamiento actual).
- **Criterio de aceptación:** el admin carga sin errores; ninguna referencia a `OrganDirectory`
  en `apps/common`; el comando importa la clase nueva.

### T10 — Migración de datos segura `apps/convenios/migrations/0054_rename_organic_unit.py`
Rename **in-place** preservando datos (BD PostgreSQL). Orden recomendado de operaciones:

1. `migrations.RenameModel(old_name="OrganDirectory", new_name="OrganicUnit")`
   — Django renombra el `db_table` autogenerado; como aquí hay `db_table` explícito, **añadir
   después** `migrations.AlterModelTable(name="organicunit", table="unidad_organica")` para
   fijar la tabla física `organo_directorio` → `unidad_organica` (ALTER TABLE ... RENAME, no
   recreación).
2. `migrations.AlterModelOptions` para `verbose_name`/`verbose_name_plural`.
3. `RemoveConstraint(model_name="organicunit", name="uniq_organo_dir_organo_nombre")` +
   `AddConstraint(... name="uniq_unidad_organica_organo_nombre" ...)` (si se renombró el constraint en T1).
4. Por cada FK entrante F1-F4 (RenameField + AlterField del `db_column`/`to`):
   - **F1** `RenameField(model_name="executiveposition", old_name="organo_directivo", new_name="unidad_organica")`
     + `AlterField(... db_column="unidad_organica_id", to="convenios.OrganicUnit", ...)`.
     Actualizar también `AlterUniqueTogether` (executiveposition → `{("unidad_organica","nombre_masculino")}`)
     y `AlterModelOptions(ordering=["unidad_organica","nombre_masculino"])`.
   - **F2** `RenameField(model_name="convention", "organo_directorio" → "unidad_organica")` +
     `AlterField(db_column="unidad_organica_id", to="convenios.OrganicUnit")`.
   - **F3** `RenameField(model_name="conventionparty", ...)` + `AlterField(...)`.
   - **F4** `RenameField(model_name="technicalevaluation", ...)` + `AlterField(...)`.
5. `AlterField` de `OrganicUnit.organo` **solo si** se ajusta `related_name`
   (`organos_directorio_por_categoria`); si se deja igual, omitir.

**Reglas de la migración:**
- **NO** usar `CreateModel`/`DeleteModel` — es rename in-place; recrear tablas perdería datos.
- Usar `RenameField`/`RenameModel`/`AlterModelTable`/`AlterField` (todas ejecutan `ALTER TABLE ... RENAME`).
- `dependencies`: `("convenios", "0053_professionalcareer_orden")`.
- Verificar que la migración es **reversible** (Django genera reverse de estas operaciones).
- **F5 (`apps/common`)**: generar la migración correspondiente en `apps/common/migrations/`
  (`AlterField` del `to` de `UserProfile.unidad_organica`), con `dependencies` sobre
  `("convenios", "0054_rename_organic_unit")`. No renombra columna (ya es `unidad_organica_id`).
- **Criterio de aceptación:** `python manage.py makemigrations --check` no detecta cambios
  pendientes tras aplicar; `migrate` corre sin errores sobre la BD PostgreSQL; los datos de
  `organo_directorio` quedan en `unidad_organica` con las mismas filas/PK y las FK repuntan
  automáticamente por rename de columna (no hay backfill).

### T11 — `docs/tramas/generar_tramas.py`
- Labels/ayudas y URLs de ayuda: `organo_directorio` → `unidad_organica` y
  `GET /api/v1/organ-directories/` → `GET /api/v1/organic-units/` (638-640, 763, 775).
- **Criterio de aceptación:** las tramas generadas citan el endpoint y la columna nuevos.

---

## 4. Cambios en el router / URLconf

- `apps/convenios/views.py` — `ENTITY_VIEWSETS["organ-directories"]` → clave `"organic-units"`,
  valor `OrganicUnitViewSet` (el diccionario alimenta el `DefaultRouter`/registro en `/api/v1/`).
- Verificar que **no** existan registros manuales adicionales del slug en `config/` ni en
  `apps/convenios/urls.py` (búsqueda confirmó que solo aparece en `views.py:941`).
- Resultado: endpoint público **`/api/v1/organic-units/`**; **`/api/v1/organ-directories/`**
  responde **404** (ruptura deliberada, documentar para el frontend).

---

## 5. Documentación a sincronizar (misma entrega)

| Archivo | Nº menciones | Qué actualizar |
|---|---|---|
| `docs/db_schema_modulo_01_convenios.md` | 31 | tabla `organo_directorio` → `unidad_organica`, columnas `organo_directorio_id`/`organo_directivo_id` → `unidad_organica_id`, endpoint |
| `docs/db_schema_er_global.md` | 8 | entidad/tabla y relaciones en el ER |
| `docs/er_diagram.md` | 13 | diagrama ER |
| `docs/flujo_convenios.md` | 3 | referencias al órgano del directorio / endpoint |
| `docs/api_almacenamiento_frontend.md` | 1 | endpoint/campo |
| `docs/arquitectura_seguridad.md` | 1 | referencia de alcance por entidad |
| `docs/generar_documento_analisis.py` | 3 | strings del generador |
| `CLAUDE.md` | múltiples | todas las menciones a `organo_directorio` / `organ-directories` / `organo_directivo` (categorías, partes firmantes, directorio de órganos y representantes, PDF, `UserProfile`) |

> El archivo del schema del módulo debe quedar sincronizado con los modelos Django en la misma
> entrega (regla del proyecto: si el modelo altera tablas/columnas, actualizar el `.md`).

---

## 6. Bug latente conocido (NO arreglar en este refactor)

- **`OrganDirectory.categoria` es un `@property`** derivado de `organo.nombre` (models.py:367),
  no una columna (fue retirada como campo en migración 0039). Hay call sites que la **leen**
  (`services.py:256,407,929,1092`; `models.py:374`) — esas lecturas funcionan (property).
- **Uso incorrecto en ORM:** `load_universidades.py:98` hace
  `OrganDirectory.objects.filter(categoria="UNIVERSIDAD")`, y `services.py:1026` usa
  `.get(nombre__iexact=...)`. `.filter(categoria=...)` sobre un property **lanzaría `FieldError`**
  en tiempo de ejecución (bug preexistente, ya reportado en memoria del proyecto).
- **Decisión del usuario:** NO arreglar en este refactor. Al renombrar la clase, **conservar el
  comportamiento actual** (solo cambiar `OrganDirectory` → `OrganicUnit`, sin corregir el `.filter`).
  Dejar constancia en el PR de que el bug persiste y queda fuera de alcance.

---

## 7. Criterios de validación (para el `validator`)

1. **Sin residuos de nombre viejo en código de app:** `Grep` de
   `OrganDirectory|organo_directorio|organo_directivo|organ-directories` en `apps/` devuelve **0**
   coincidencias (excepto dentro de migraciones históricas `00xx`, que son inmutables, y comentarios
   que citen el rename intencionalmente).
2. **Modelo/tabla:** `OrganicUnit` con `db_table="unidad_organica"`; `OrganDirectory` no existe.
3. **FK entrantes:** F1-F5 usan atributo `unidad_organica` y `db_column="unidad_organica_id"`;
   `related_name` sin colisiones (`cargos`, `convenios`, `+`, `+`, `perfiles_usuarios`).
4. **Migración:** `0054` usa solo operaciones de rename/alter (sin `CreateModel`/`DeleteModel`);
   `makemigrations --check` limpio; `migrate` aplica sin pérdida de datos en PostgreSQL; migración
   `common` dependiente presente.
5. **Router:** `/api/v1/organic-units/` operativo; `/api/v1/organ-directories/` → 404.
6. **Reglas de negocio intactas:** RN-1 (quién solicita Marco), composición de partes firmantes,
   coherencia parte↔representante↔cargo, derivación del solicitante, generación de PDF — sin
   cambios de comportamiento (solo rename).
7. **GFK no rotos:** `SOLICITANTE_MODELS`, `REPRESENTANTE_MODELS`, `ASSIGNABLE_PROFILE_MODELS`
   incluyen `OrganicUnit`; los endpoints de tipos de contenido solicitante/representante siguen
   resolviendo el ContentType.
8. **Docs sincronizados:** los `.md` de §5 y `CLAUDE.md` actualizados.
9. **Bug latente `.categoria`:** sigue presente exactamente igual que antes (no se introdujo ni
   se corrigió); documentado en el PR.
10. **`/code-review`** ejecutado antes de cerrar (regla del proyecto para modelos/serializers/
    vistas/migraciones).
