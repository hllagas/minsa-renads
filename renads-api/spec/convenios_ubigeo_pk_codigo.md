# Spec — Refactor de la PK de `Ubigeo`: `codigo` como PK texto (6 chars)

## Resumen del módulo

Refactor transversal que convierte `Ubigeo.codigo` (`apps/convenios/models.py:278`, hoy
`CharField(max_length=6, unique=True)`, requerido) en la **PK de tipo texto de 6 caracteres**
(`CharField(max_length=6, primary_key=True)`), eliminando el `id` autoincremental implícito de la
tabla `ubigeo`.

Impacto directo:

- **7 FK** en 2 apps que referencian `Ubigeo` pasan de columna `integer` → `varchar(6)`. Todas son
  `null=True, blank=True, on_delete=PROTECT`, `db_column="ubigeo_id"`.
- Código de aplicación: `_detalle_ubigeo` (usa `rel.id`, crítico), `UbigeoViewSet` (opera con PK
  string) y los tres viewsets que exponen `ubigeo_detalle`.
- Documentación: 3 schemas + ER global.

Entidades cubiertas: `Ubigeo` (dueña de la PK), y las 7 FK que la referencian:

| App | Modelo | Campo | `models.py` | `on_delete` | Nullable |
|---|---|---|---|---|---|
| convenios | `RegionalGovernment` | `ubigeo` | L307 | PROTECT | Sí |
| convenios | `Ipress` | `ubigeo` | L396 | PROTECT | Sí |
| convenios | `University` | `ubigeo` | L645 | PROTECT | Sí |
| convenios | `Faculty` | `ubigeo` | L672 | PROTECT | Sí |
| convenios | `UniversityCampus` | `ubigeo` | L745 | PROTECT | Sí |
| internados | `Student` | `ubigeo` | L115 | PROTECT | Sí |
| internados | `Tutor` | `ubigeo` | L170 | PROTECT | Sí |

Metodología SDD. Migración base actual: `convenios/0047_ipress_pk_renipress_promote`,
`internados/0022_ipress_fk_renipress`. Nuevas migraciones: **convenios desde `0048`**, **internados
desde `0023`**. El patrón multi-paso transitorio cross-app ya se ejecutó para `ExecutingUnit`
(`0044`/`0045`) y para `Ipress` (`0046`/`0047` convenios + `0021`/`0022` internados) — este spec lo
imita, con la simplificación de que las 7 FK son nullable.

> **Decisiones ya tomadas por el usuario (NO reabrir):** (1) `codigo` es PK texto de 6 caracteres;
> (2) NO ejecutar `migrate`, `runserver` ni tests — solo escribir código y migraciones.

---

## Confirmación de ausencia de impacto en alcance/auditoría (a diferencia de `Ipress`)

Regla rectora: un GFK apunta a `Ubigeo` **solo si** algún flujo escribe su `tipo_contenido`/`id_objeto`
con el `ContentType` de `Ubigeo`.

| Mecanismo | ¿Referencia a `Ubigeo`? | Evidencia |
|---|---|---|
| `ASSIGNABLE_PROFILE_MODELS` (`apps/common/serializers.py:378`) | **No** | La tupla contiene `University`, `Ipress`, `RegionalGovernment`, `OrganDirectory`, `ExecutingUnit`, `Conapres`, `Student` — **`Ubigeo` no está**. No hay alcance institucional sobre ubigeos. |
| `UserEntityProfile.id_objeto` (GFK de alcance) | **No** | No se asigna perfil sobre `Ubigeo` (no está en el allowlist). |
| `AuditLog.id_objeto` (GFK de auditoría) | **No** | `Ubigeo` no tiene CRUD de escritura (es `ReadOnlyModelViewSet`); no se audita. |
| `Document.id_objeto` (`documento_adjunto`) | **No** | `Ubigeo` no lleva anexos ni logos (`ImageField`). |
| `ConventionParticipant` / `Firma` / `Convention.solicitante` | **No** | Nunca referencian una ubicación geográfica. |

**Conclusión:** a diferencia del refactor de `Ipress` (que sí cambió `UserEntityProfile.id_objeto` y
`AuditLog.id_objeto` a `CharField(64)`), este refactor **NO toca ningún GFK, alcance institucional ni
auditoría**. El único cambio de tipo son las **7 FK directas** (`integer` → `varchar(6)`). El implement
debe dejar constancia explícita de esta verificación en el docstring de la primera migración
(`convenios/0048`).

---

## Fase 0 — Verificación de datos (T-01, obligatoria ANTES de escribir migraciones)

**T-01 — Auditar los datos de `ubigeo` antes de tocar el schema.**

`codigo` ya es `CharField(max_length=6, unique=True)`, por lo que la superficie de riesgo es mínima.
Con el venv activado (`.venv\Scripts\Activate.ps1`), abrir `python manage.py shell` y ejecutar:

1. **Longitud y no-vacíos:**
   `Ubigeo.objects.exclude(codigo__regex=r'^.{1,6}$').values_list('pk','codigo')`
   — debe devolver **vacío**. Cualquier fila con `codigo` de más de 6 chars, vacío o nulo es
   bloqueante.
2. **Unicidad** (ya garantizada por `unique=True`, revalidar):
   contar `Ubigeo.objects.count()` vs. `Ubigeo.objects.values('codigo').distinct().count()` — deben
   coincidir.
3. **FK colgantes (integridad de las 7 FK):** confirmar que ninguna FK entera apunta a un `Ubigeo`
   inexistente antes del backfill. En dev, con tabla vacía o pocas filas, es trivial.

**Criterios de aceptación T-01:**
- Si alguna fila tiene `codigo` > 6 chars, vacío, nulo o duplicado → **DETENER y escalar al usuario**.
  **No truncar** ni auto-corregir códigos (el usuario definió 6; truncar altera el identificador
  INEI).
- El resultado real de las consultas (conteos incluidos) se documenta en el **docstring de la
  migración `convenios/0048`**, siguiendo el patrón de `0046` (`Ipress.objects.count() → 0 filas`).
- En dev el resultado esperado es 0 filas problemáticas; los `RunPython` deben quedar correctos para
  producción (backfill real + `RuntimeError` ante integridad rota).

---

## Regla rectora de la secuencia de migraciones

**Ninguna FK entera puede quedar apuntando al `id` de `Ubigeo` cuando este se elimine.** Como el
cambio es de tipo (`integer` → `varchar(6)`) y se dropea el `id` autoincremental, se usa el patrón
transitorio ya validado en `Ipress`:

1. Cada operación de campo vive en la migración de la **app dueña del modelo** (las 5 FK de convenios
   en migraciones de convenios; las 2 de internados en migraciones de internados).
2. Se añaden **columnas transitorias `ubigeo_codigo`** (varchar 6, nullable) por cada FK, se rellenan
   por backfill leyendo `Ubigeo.id → Ubigeo.codigo` **mientras el `id` aún existe**, y solo después se
   promueve `codigo` a PK y se dropea el `id`.
3. **Aristas cross-app explícitas** (`dependencies`) fijan el grafo para que Django ordene:
   - Los backfills transitorios (que construyen el mapa `id → codigo` leyendo la columna `id`) deben
     ejecutarse **ANTES** del drop del `id` de `Ubigeo`.
   - La migración que promueve el PK y dropea el `id` (`convenios/0049`) debe **depender** de las
     migraciones transitorias de internados (`internados/0023`) para que el mapa `id → codigo` sea
     construible en internados **antes** de que desaparezca `Ubigeo.id`.
   - Las FK reales de internados (`internados/0024`) dependen de `convenios/0049` (donde `Ubigeo` ya
     tiene PK textual y sin `id`).
   - Sin ciclo: `internados/0024` depende de `convenios/0049` (posterior), mientras `convenios/0049`
     depende solo del transitorio `internados/0023` (anterior).

---

## Grafo de migraciones (secuencia exacta)

```
convenios/0047 (base actual, Ipress PK)
        │
        ▼
convenios/0048_ubigeo_codigo_transitorio ──────────┐
   Fase 0 (docstring) + AddField ubigeo_codigo x5   │
   + backfill (5 FK de convenios)                   │
        │                                           │
        ▼                                           ▼
internados/0022 (base actual) ─► internados/0023_ubigeo_codigo_transitorio
                                    AddField ubigeo_codigo x2 (Student, Tutor)
                                    + backfill (lee Ubigeo.id → codigo)
                                    dependencies: [internados/0022, convenios/0048]
        │
        ▼
convenios/0049_ubigeo_pk_codigo_promote
   PASO A: codigo → primary_key=True + RemoveField Ubigeo.id
   PASO B–D: 5 FK transitorias → FK reales, drop enteras, rename, db_column="ubigeo_id"
   dependencies: [convenios/0048, internados/0023]   ← evita FK entera colgando al drop
        │
        ▼
internados/0024_ubigeo_fk_codigo
   PASO B–D: 2 FK transitorias → FK reales, drop enteras, rename, db_column="ubigeo_id"
   dependencies: [internados/0023, convenios/0049]
```

### T-02 — `convenios/0048_ubigeo_codigo_transitorio` (app dueña, parte prep)

- **Docstring:** documentar el resultado real de la Fase 0 (T-01) y la **confirmación explícita de
  ausencia de impacto de alcance/auditoría** (`Ubigeo` fuera de `ASSIGNABLE_PROFILE_MODELS`, sin GFK,
  sin auditoría, sin anexos/logo).
- **Operaciones:**
  1. `AddField` columna transitoria `ubigeo_codigo` (`CharField(max_length=6, null=True, blank=True)`)
     en los 5 modelos de convenios: `RegionalGovernment`, `Ipress`, `University`, `Faculty`,
     `UniversityCampus`. Usar `db_column` **distintos** para evitar colisión (p. ej.
     `ubigeo_codigo`, `ubigeo_codigo_ip`, `ubigeo_codigo_uni`, `ubigeo_codigo_fac`,
     `ubigeo_codigo_loc`).
  2. `RunPython` backfill (`reverse_code=migrations.RunPython.noop`): para cada modelo, copiar
     `Ubigeo.codigo` en `ubigeo_codigo` leyendo el mapa `{Ubigeo.id: Ubigeo.codigo}`. Solo filas con
     `ubigeo_id__isnull=False`. Si el `ubigeo_id` no existe en el mapa → `RuntimeError` con mensaje en
     español (patrón de `0046`).
- **`dependencies`:** `[("convenios", "0047_ipress_pk_renipress_promote")]`.
- **Criterios de aceptación:** las 5 columnas transitorias existen y quedan rellenas; ninguna FK
  entera se toca todavía; `Ubigeo.id` sigue existiendo.

### T-03 — `internados/0023_ubigeo_codigo_transitorio` (parte prep internados)

- **Operaciones:**
  1. `AddField` `ubigeo_codigo` (`CharField(max_length=6, null=True, blank=True)`) en `Student` y
     `Tutor`, con `db_column` distintos (p. ej. `ubigeo_codigo`, `tutor_ubigeo_codigo`).
  2. `RunPython` backfill leyendo `apps.get_model("convenios", "Ubigeo")` con el mapa
     `{ip.id: ip.codigo}` — **este mapa requiere que `Ubigeo.id` aún exista**, de ahí la dependencia a
     `0048` (no a `0049`). Solo filas con `ubigeo_id__isnull=False`; `RuntimeError` ante integridad
     rota.
- **`dependencies`:** `[("internados", "0022_ipress_fk_renipress"), ("convenios",
  "0048_ubigeo_codigo_transitorio")]`.
- **Criterios de aceptación:** `Student.ubigeo_codigo` y `Tutor.ubigeo_codigo` rellenas; FK enteras
  intactas.

### T-04 — `convenios/0049_ubigeo_pk_codigo_promote` (parte crítica, drop del `id`)

Imitar el patrón A→B→C→D de `0047`:

- **PASO A — promocionar `codigo` a PK y eliminar el `id`:**
  - `AlterField` `Ubigeo.codigo` → `CharField(max_length=6, primary_key=True, serialize=False)`,
    conservando `verbose_name="código"` y `help_text`.
  - `RemoveField` `Ubigeo.id`.
- **PASO B — convertir las 5 transitorias en FK reales al PK textual:** `AlterField`
  `<modelo>.ubigeo_codigo` → `ForeignKey(to="convenios.ubigeo", on_delete=PROTECT, null=True,
  blank=True, db_column=<db_column transitorio>, related_name="+")`.
- **PASO C — eliminar las FK enteras y renombrar las transitorias:**
  - `RemoveField` `<modelo>.ubigeo` (FK int) × 5.
  - `RenameField` `<modelo>.ubigeo_codigo` → `ubigeo` × 5.
- **PASO D — ajuste final al `db_column` canónico `ubigeo_id`:** `AlterField` `<modelo>.ubigeo` →
  `ForeignKey(to="convenios.ubigeo", on_delete=PROTECT, null=True, blank=True, db_column="ubigeo_id",
  related_name="+", help_text="Ubicación geográfica (UBIGEO)")` × 5.
- **Docstring:** explicar el orden A→B→C→D y la razón de las dependencias cross-app (mismo aprendizaje
  de `0047`: el drop del `id` debe ir después de los backfills transitorios de internados).
- **`dependencies`:** `[("convenios", "0048_ubigeo_codigo_transitorio"), ("internados",
  "0023_ubigeo_codigo_transitorio")]`.
- **Criterios de aceptación:** `ubigeo.codigo` es PK varchar(6); la tabla `ubigeo` ya no tiene `id`;
  las 5 columnas `ubigeo_id` de convenios son varchar(6) y apuntan al PK textual; ninguna FK entera
  queda colgando.

### T-05 — `internados/0024_ubigeo_fk_codigo` (parte final internados)

- **PASO B–D** análogos a T-04 para `Student.ubigeo` (PROTECT) y `Tutor.ubigeo` (PROTECT). Ambas
  `null=True, blank=True`, `db_column="ubigeo_id"`, `related_name="+"`, `help_text` original.
- **`dependencies`:** `[("internados", "0023_ubigeo_codigo_transitorio"), ("convenios",
  "0049_ubigeo_pk_codigo_promote")]`.
- **Criterios de aceptación:** `estudiante.ubigeo_id` y `tutor.ubigeo_id` son varchar(6) apuntando al
  PK textual; sin FK entera colgante; `makemigrations` no detecta cambios pendientes.

> **Nota SQLite:** Django recrea la tabla `ubigeo` automáticamente en el `AlterField primary_key=True`
> / `RemoveField id`, y recrea las tablas hijas al alterar sus FK. Imitar el patrón de `0047` (que ya
> funcionó en SQLite dev).

---

## Cambios en el modelo (`apps/convenios/models.py`)

### T-06 — `Ubigeo.codigo` a PK

- **`apps/convenios/models.py:278`:** cambiar
  `codigo = models.CharField("código", max_length=6, unique=True, help_text="Código UBIGEO INEI (6 dígitos)")`
  por
  `codigo = models.CharField("código", max_length=6, primary_key=True, help_text="Código UBIGEO INEI (6 dígitos, clave primaria)")`.
- Eliminar `unique=True` (redundante con `primary_key=True`). Conservar `ordering = ["codigo"]` en
  `Meta` (ya está).
- **Criterios de aceptación:** el modelo declara `codigo` como PK; `makemigrations` no genera
  operaciones fuera de las de T-02/T-04 (el estado final del modelo coincide con la migración de
  promoción).

### T-07 — Las 7 FK (sin cambio de declaración en el modelo)

Las 7 FK ya declaran `db_column="ubigeo_id"`, `null=True, blank=True`, `PROTECT`. **No cambia la
declaración en `models.py`** (Django resuelve `to_field` a la PK automáticamente ahora que `codigo` es
PK). El cambio de tipo lo aplican las migraciones (T-02..T-05).

- **Criterios de aceptación:** `makemigrations` tras T-06 no propone operaciones adicionales sobre las
  7 FK más allá de las de las migraciones de este spec.

---

## Cambios en código de aplicación

### T-08 — `_detalle_ubigeo` (`apps/convenios/views.py:456`, CRÍTICO)

- **`views.py:459`:** cambiar `"id": rel.id,` por `"id": rel.pk,`. Cuando `codigo` es PK, `rel.id`
  deja de existir (`AttributeError` en runtime). `rel.pk` devuelve el `codigo` (string 6 chars).
- Conservar el resto del detalle (`codigo`, `distrito`, `provincia`, `departamento`).
- **Criterios de aceptación:** el detalle expone `id == codigo` (string) sin `AttributeError`;
  consumido correctamente por `IpressViewSet` (L568), `FacultyViewSet` (L642/653) y
  `regional-governments` (L860).

> **Nota:** el `id` del detalle ahora es igual al `codigo`. Se conserva la clave `id` por
> compatibilidad del contrato de detalle, pero su valor pasa de int a string 6 chars (ver Breaking
> Changes).

### T-09 — `UbigeoViewSet` (`apps/convenios/views.py:902`)

- **`ordering_fields` / `ordering`:** el viewset ya ordena por `["codigo"]` y **no** usa `ordering =
  ["id"]`. Verificar que `ordering` no referencie `id`. Como es `ReadOnlyModelViewSet` con
  `_auto_serializer(m.Ubigeo)` y `lookup_field` por defecto (`pk`), el retrieve pasa a operar por PK
  string: `/api/v1/ubigeos/<codigo>/` (p. ej. `/api/v1/ubigeos/150101/`).
- No requiere `lookup_value_regex` obligatorio; opcionalmente documentar que la PK es un string de 6
  dígitos. No añadir regex restrictivo salvo que el usuario lo pida.
- **Criterios de aceptación:** `GET /api/v1/ubigeos/` lista; `GET /api/v1/ubigeos/<codigo>/` resuelve
  por código; los filtros `departamento`/`provincia`/`distrito`/`activo` y la búsqueda siguen
  operando.

### T-10 — `get_or_create` / `filter` / `get` por `codigo` (sin cambio funcional)

Las siguientes referencias **siguen igual** porque `codigo` sigue siendo el mismo campo (ahora PK):

- `apps/convenios/management/commands/load_ubigeo.py:110` — `Ubigeo.objects.get_or_create(codigo=…)`
  sigue idempotente (la clave es ahora la PK). Verificar que el `defaults` no intente escribir `id`.
- `apps/convenios/management/commands/load_universidades.py:132` — `Ubigeo.objects.filter(codigo=…)`
  intacto.
- `apps/internados/services.py:767` — `Ubigeo.objects.get(codigo=…)` intacto.

- **Criterios de aceptación:** ninguna de estas tres referencias requiere modificación; el implement
  las revisa y confirma que no dependen de `Ubigeo.id`.

### T-11 — Barrido de usos de `Ubigeo.id` / `.ubigeo_id` como entero

- Buscar en `apps/` cualquier lectura de `.id` sobre una instancia de `Ubigeo` o comparación de
  `ubigeo_id` como entero. Confirmado: la única lectura de `.id` sobre `Ubigeo` es `_detalle_ubigeo`
  (T-08). No hay alcance/auditoría/GFK que lo lea (ver sección de confirmación).
- **Criterios de aceptación:** no queda ningún `Ubigeo(...).id` ni comparación entera de `ubigeo_id`
  en el código de aplicación fuera del ya corregido en T-08.

---

## Documentación

### T-12 — `docs/db_schema_modulo_01_convenios.md`

- **L32** (tabla `ubigeo`): actualizar la descripción — `codigo` (6 dígitos) es ahora **PK de tipo
  texto**; la tabla **ya no tiene columna `id`**.
- **L135, L197, L257, L271, L313** (las 5 FK `ubigeo_id` de convenios): indicar que el tipo pasa a
  **`varchar(6)`** (antes entero).
- **L697, L699, L716** (ER textual): reflejar `ubigeo` PK `codigo`.

### T-13 — `docs/db_schema_modulo_02_internados.md`

- Actualizar las 2 FK `ubigeo_id` (`estudiante`, `tutor`) a **`varchar(6)`** apuntando a
  `ubigeo.codigo`.

### T-14 — `docs/db_schema_er_global.md`

- Reflejar la tabla `ubigeo` con PK `codigo varchar(6)` **sin `id`**, y las 7 FK `ubigeo_id` como
  `varchar(6)`.

- **Criterios de aceptación (T-12..T-14):** los 3 docs describen `ubigeo.codigo` como PK varchar(6)
  sin `id`, y las 7 FK como varchar(6). No queda ninguna mención a un `id` autoincremental de
  `ubigeo`.

---

## Tabla de breaking changes de API

| # | Superficie | Antes | Después | Impacto frontend |
|---|---|---|---|---|
| BC-1 | `GET /api/v1/ubigeos/<pk>/` | PK entera (`/api/v1/ubigeos/1234/`) | PK string 6 chars (`/api/v1/ubigeos/150101/`) | El retrieve por id entero deja de resolver; usar el código INEI. |
| BC-2 | Serializer de `Ubigeo` (list/retrieve) | expone `id` entero | ya **no** hay campo `id`; `codigo` es la PK | El frontend debe usar `codigo` como identificador. |
| BC-3 | `ubigeo_detalle.id` (en Ipress/Faculty/RegionalGovernment) | int | string 6 chars (== `codigo`) | El valor de `id` en el detalle pasa a string; usar `codigo`. |
| BC-4 | Payloads de escritura con FK `ubigeo` (Ipress, Faculty, University, RegionalGovernment, UniversityCampus, Student, Tutor) | `"ubigeo": 1234` (int) | `"ubigeo": "150101"` (string 6 chars) | El frontend envía el código INEI como string en el campo `ubigeo`. |
| BC-5 | Filtros `?ubigeo=` en los viewsets que filtran por `ubigeo` | int | string 6 chars | Los filtros por `ubigeo` reciben el código INEI. |

> Todos los cambios son consistentes con el refactor previo de `Ipress` (PK textual). El frontend ya
> conoce el patrón por `codigo_renipress`.

---

## Fuera de alcance

- No se ejecuta `migrate`, `runserver` ni tests (regla del proyecto y del encargo).
- No se toca ningún GFK, `ASSIGNABLE_PROFILE_MODELS`, permiso, selector de alcance ni auditoría
  (verificado: `Ubigeo` no participa).
- No se añaden validaciones de formato del `codigo` más allá de las existentes en `load_ubigeo`
  (zfill(6) + `isdigit`).
- Testing automatizado (fuera de alcance del MVP).

---

## Checklist de cierre

- [ ] T-01 Fase 0 ejecutada y documentada en docstring de `convenios/0048`.
- [ ] T-02..T-05 migraciones creadas con el grafo cross-app exacto; `makemigrations` sin cambios
      pendientes.
- [ ] T-06 modelo `Ubigeo.codigo` como PK.
- [ ] T-08 `_detalle_ubigeo` usa `rel.pk`.
- [ ] T-09 `UbigeoViewSet` opera por PK string.
- [ ] T-10/T-11 barrido de usos de `.id` confirmado.
- [ ] T-12..T-14 docs actualizados.
- [ ] `/code-review` ejecutado antes de dar por terminada la implementación.
