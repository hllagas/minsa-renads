# Spec — Refactor Convenios: FK `organo` en `cargo_ejecutivo` (`ExecutivePosition`)

> **Metodología SDD.** Este archivo es la fuente de tareas para el agente `implement`.
> `implement` desarrolla en `apps/convenios/` y actualiza `docs/`; `validator` revisa contra
> este spec, la arquitectura y el schema. No se avanza sin spec ni se cierra sin validación.

## 1. Resumen del módulo

Refactor del módulo **Gestionar Convenios** (app `apps/convenios`). Se agrega una nueva
columna `organo_id` a la tabla `cargo_ejecutivo` (modelo `ExecutivePosition`), como **FK
obligatoria** al catálogo canónico `organo` (`Organ`), con una **regla de coherencia**
respecto del `organo_directivo` del cargo.

### Entidades cubiertas

| Entidad | Tabla | Rol en este refactor |
|---------|-------|----------------------|
| `ExecutivePosition` | `cargo_ejecutivo` | Recibe el nuevo FK `organo` (columna `organo_id`) |
| `Organ` | `organo` | Catálogo destino del FK (categorías canónicas) |
| `OrganDirectory` | `organo_directorio` | Fuente para derivar `organo` (`organo_directivo.organo_id`) y término de la coherencia |

### Alcance y contexto de decisiones (ya confirmadas por el usuario)

- `organo` es **FK a `Organ`** (`on_delete=PROTECT`, `db_column="organo_id"`), **obligatorio**
  (`null=False`), con `help_text` en español.
- **Coherencia:** si `organo_directivo` está seteado en el cargo, debe cumplirse
  `organo_id == organo_directivo.organo_id`. Si `organo_directivo` es nulo, no hay término
  de comparación y la coherencia no aplica (solo se exige que `organo` esté presente).
- La validación de coherencia va en el **serializer** (`validate()`), porque el CRUD de
  entidades usa `_entity_viewset`/`_auto_serializer`, que construye un `ModelSerializer`
  automático y **NO** ejecuta `Model.clean()`.

### Fuera de alcance (no tocar)

- La coherencia de partes firmantes en `services._validar_coherencia_parte`
  (`services.py` L862-887) compara `cargo_ejecutivo.organo_directivo_id` contra el
  `organo_directorio` de la parte; **no** depende de `organo`. **Solo verificar, no cambiar.**
- **Discrepancia pre-existente conocida:** `services.py` (~L250/L401) y `serializers.py`
  (~L43-44) leen `organo_directorio.categoria`, atributo retirado en la migración `0039`
  (ahora es el FK `organo`). **`implement` NO la corrige aquí**; solo la reporta si estorba
  la ejecución de este refactor. Este refactor usa `organo_directivo.organo`, que es un FK
  real y vigente (`models.py` L312-316), no `categoria`.
- No modificar el `unique_together` de `cargo_ejecutivo` (ver Tarea 3).

---

## 2. Estado actual verificado

- `ExecutivePosition` (`apps/convenios/models.py` L186-216): FK `organo_directivo`
  (→`OrganDirectory`, `PROTECT`, **nullable**, `related_name="cargos"`, `db_column="organo_directivo_id"`),
  `nombre_masculino`, `nombre_femenino`, `activo`.
  `unique_together = (("organo_directivo", "nombre_masculino"),)`,
  `ordering = ["organo_directivo", "nombre_masculino"]`.
- `Organ` (`models.py` L167-183): tabla `organo`, campos `nombre`, `estado`.
- `OrganDirectory.organo` (`models.py` L312-316): FK a `Organ`, `db_column="organo_id"`,
  `related_name="organos_directorio_por_categoria"`. **Fuente para derivar `cargo.organo`.**
- Endpoint `executive-positions` (`views.py` L764-771): construido con `_entity_viewset(...)`,
  `filterset_fields={"organo_directivo": ["exact", "isnull"], "activo": ["exact"]}`,
  `search_fields=["nombre_masculino", "nombre_femenino"]`,
  `detalles={"organo_directivo": _detalle_organo_directorio}`. **Usa el serializer
  automático de `_auto_serializer` (sin `validate()` de coherencia).**
- Helpers confirmados en `views.py`: `_detalle_nombre` (L437), `_detalle_organo_directorio`
  (L447), `_auto_serializer` (L467), `_entity_viewset` (L521). `_auto_serializer` acepta
  `detalles={fk: extractor}` y genera `{fk}_detalle` (SerializerMethodField de solo lectura).
- **Patrón de referencia** para serializer custom + viewset con `serializer_class`:
  `_OrganDirectorySerializer` (`views.py` L694-725) + `OrganDirectoryViewSet` (L728-741).
- Última migración de la app: `0041_convention_gobierno_regional_drop_organdirectory_gore.py`.
  La nueva migración será **`0042`**.

---

## 3. Tareas por capa

### Capa Modelo — `apps/convenios/models.py`

**T1 — Agregar el campo `organo` a `ExecutivePosition`.**
- Insertar el FK en el modelo `ExecutivePosition` (L186-216), preferentemente como primer
  campo o junto a `organo_directivo`:
  ```python
  organo = models.ForeignKey(
      "Organ", on_delete=models.PROTECT, db_column="organo_id",
      related_name="cargos_ejecutivos", null=False,
      verbose_name="órgano",
      help_text="Categoría de órgano (FK a la tabla canónica `organo`) a la que pertenece el cargo",
  )
  ```
  - `on_delete=PROTECT`, `db_column="organo_id"`, `null=False` (obligatorio).
  - `help_text` y `verbose_name` en español.
  - Elegir un `related_name` no colisionante (sugerido `cargos_ejecutivos`; verificar que no
    choque con `organos_directorio_por_categoria` de `OrganDirectory` ni con otro `related_name`
    sobre `Organ`).
- **NO** agregar `Model.clean()` como única defensa (el CRUD no lo ejecuta); la validación
  de coherencia vive en el serializer (T4). Se permite añadir `clean()` como refuerzo, pero
  no sustituye al `validate()`.
- **Criterio de aceptación:** `python manage.py check` pasa; el campo aparece en
  `ExecutivePosition._meta.get_fields()`; `db_column` es `organo_id`.

**T2 — No modificar `unique_together`.**
- Mantener `unique_together = (("organo_directivo", "nombre_masculino"),)` **sin cambios**.
- **Nota de diseño:** no se incluye `organo` en la unicidad porque `organo` se deriva de
  `organo_directivo` (mismo `organo`), por lo que añadirlo sería redundante para las filas
  con `organo_directivo` no nulo. Documentarlo en el spec/commit; si el usuario pidiera lo
  contrario, sería un cambio aparte.
- **Criterio de aceptación:** el `Meta.unique_together` permanece idéntico al actual.

### Capa Migración — `apps/convenios/migrations/0042_*.py`

**T3 — Diagnóstico previo obligatorio (conteos).** *(Precede a la escritura de la migración.)*
- Con el venv activado (`.venv\Scripts\Activate.ps1`), obtener y **reportar al usuario** tres
  conteos sobre `cargo_ejecutivo` (vía shell de Django o consulta directa):
  1. Total de filas de `cargo_ejecutivo`.
  2. Filas con `organo_directivo_id` **NO nulo**.
  3. Filas con `organo_directivo_id` **nulo** (cargos globales legacy).
- **Criterio de aceptación:** los tres conteos quedan reportados explícitamente al usuario
  antes de crear la migración.

**T4 — BLOQUEANTE CONDICIONAL (filas con `organo_directivo` nulo).**
- `organo` es **NOT NULL nuevo** sobre una tabla con datos, y las filas con
  `organo_directivo IS NULL` **no tienen de dónde derivar** el `organo_id`.
- **Si el conteo (3) de T3 es > 0:** `implement` **DEBE DETENERSE** y reportar al usuario
  para que decida qué `organo` asignar a esas filas (o si deben eliminarse/reasignarse un
  `organo_directivo`). **NO inventar un default.** No proceder con `AlterField` a `null=False`
  hasta que el usuario decida.
- **Si el conteo (3) es 0** (no hay filas nulas o la tabla está vacía): proceder con T5.
- **Criterio de aceptación:** si hay filas con `organo_directivo` nulo, existe un reporte al
  usuario y **no** se generó una migración que ponga NOT NULL sin resolverlas.

**T5 — Migración de 3 pasos (solo si T4 no bloquea).**
- Crear una única migración `0042` (dependiente de `0041`) con estas operaciones en orden:
  1. **`AddField`** `organo` como **nullable temporal** (`null=True`) — o `AddField` con
     `preserve_default=False` y un default provisional que no persista. Objetivo: poder
     añadir la columna sobre filas existentes sin violar NOT NULL.
  2. **`RunPython`** (con `reverse_code=migrations.RunPython.noop`) que, usando modelos
     históricos (`apps.get_model("convenios", "ExecutivePosition")`), pueble
     `organo_id = organo_directivo.organo_id` para todas las filas con `organo_directivo`
     no nulo. (Por T4, en este punto no debe haber filas con `organo_directivo` nulo.)
  3. **`AlterField`** de `organo` a `null=False` (estado final coincidente con el modelo T1).
- No usar `RunSQL` específico de un motor si puede evitarse (BD dev = SQLite; prod previsto
  PostgreSQL); preferir ORM histórico en el `RunPython`.
- **Criterios de aceptación:**
  - `python manage.py makemigrations --check --dry-run` **no** reporta cambios pendientes
    tras crear la migración (el estado del modelo y el de las migraciones coinciden).
  - `python manage.py check` pasa.
  - La migración es reversible de forma segura (el `RunPython` tiene `reverse_code` noop; el
    `AlterField`/`AddField` son reversibles por Django).
  - **No** ejecutar `migrate` (lo corre el usuario).

### Capa Serializers / Views — `apps/convenios/views.py`

**T6 — Serializer custom con validación de coherencia.**
- Crear un serializer siguiendo el patrón de `_OrganDirectorySerializer` (L694-725):
  ```python
  class _ExecutivePositionSerializer(
      _auto_serializer(
          m.ExecutivePosition,
          detalles={
              "organo": _detalle_nombre,
              "organo_directivo": _detalle_organo_directorio,
          },
      )
  ):
      def validate(self, attrs):
          attrs = super().validate(attrs)
          # Estado final del objeto (soporta PATCH parcial partiendo de la instancia).
          organo = attrs.get("organo", getattr(self.instance, "organo", None))
          organo_directivo = attrs.get(
              "organo_directivo", getattr(self.instance, "organo_directivo", None)
          )
          if organo_directivo is not None and organo is not None:
              if organo.id != organo_directivo.organo_id:
                  raise drf_serializers.ValidationError({
                      "organo": (
                          "El órgano del cargo debe coincidir con el órgano del "
                          "órgano directivo seleccionado."
                      )
                  })
          return attrs
  ```
  - Soportar **PATCH parcial** combinando `attrs` + `self.instance` (patrón exacto del
    serializer de referencia).
  - Mensaje de error **en español**.
  - Si `organo_directivo` es nulo (cargo global), la coherencia no aplica; el FK `organo`
    obligatorio ya lo garantiza el propio `ModelSerializer` (campo requerido por `null=False`).
- **Criterios de aceptación:**
  - Crear/actualizar un cargo con `organo` incoherente respecto de `organo_directivo` devuelve
    **400** con el mensaje en español (no un 500 ni un IntegrityError).
  - Un PATCH que cambia solo `organo_directivo` (dejando `organo` en la instancia) revalida
    contra el estado final.
  - Un cargo con `organo_directivo` nulo y `organo` presente se acepta.

**T7 — Registrar el serializer en el viewset `executive-positions`.**
- Actualizar la entrada `"executive-positions"` de `ENTITY_VIEWSETS` (`views.py` L764-771).
  Como `_entity_viewset` genera su propio `serializer_class` automático, hay que **sobrescribir
  `serializer_class`** con `_ExecutivePositionSerializer`. Seguir el patrón de
  `OrganDirectoryViewSet` (L728-741): declarar una subclase explícita del viewset generado por
  `_entity_viewset(...)` y fijar `queryset` (con `select_related("organo", "organo_directivo")`)
  y `serializer_class`. Alternativamente, si `_entity_viewset` permite pasar el serializer,
  usar esa vía; de lo contrario, definir la subclase.
- En la llamada a `_entity_viewset(m.ExecutivePosition, ...)`:
  - **Filtros:** agregar `organo` a `filterset_fields`. Estado final sugerido:
    `{"organo": ["exact"], "organo_directivo": ["exact", "isnull"], "activo": ["exact"]}`.
  - **Detalles:** cambiar a
    `detalles={"organo": _detalle_nombre, "organo_directivo": _detalle_organo_directorio}`.
  - `search_fields` sin cambios (`["nombre_masculino", "nombre_femenino"]`).
  - Optimizar el `queryset` con `select_related("organo", "organo_directivo")`.
- **Criterios de aceptación:**
  - `GET /api/v1/executive-positions/` expone en cada ítem `organo` (id) y `organo_detalle`
    (`{id, codigo, nombre}` vía `_detalle_nombre`), además de `organo_directivo` y
    `organo_directivo_detalle`.
  - `GET /api/v1/executive-positions/?organo=<id>` filtra por FK.
  - El filtro `organo_directivo__isnull` sigue disponible.
  - La escritura sigue restringida a `Administrador RENADS` (permiso `IsAdminRoleOrReadOnly`,
    heredado de `_entity_viewset`); no se altera el permiso.

**T8 — Verificar (sin cambiar) `services._validar_coherencia_parte`.**
- Confirmar que la coherencia de partes firmantes (`services.py` L862-887) **no** requiere
  ajustes por este refactor (compara `organo_directivo_id`, no `organo`). No modificar.
- **Criterio de aceptación:** el service permanece intacto; se deja constancia de la
  verificación en el reporte de implementación.

### Capa Docs — sincronizar en el mismo cambio

**T9 — `docs/db_schema_modulo_01_convenios.md`.**
- Sección `cargo_ejecutivo` (tabla de columnas L147-153): añadir fila
  `| organo_id | FK → organo (PROTECT, related_name='cargos_ejecutivos') | No | Categoría de órgano a la que pertenece el cargo; debe coincidir con organo_directivo.organo cuando este está seteado |`.
- Actualizar la fila-resumen de `cargo_ejecutivo` en la tabla índice (L42) para mencionar el
  nuevo FK `organo_id` y la coherencia.
- Actualizar la descripción del endpoint (L155): agregar el filtro `organo` y que la lectura
  expone `organo_detalle`.
- **Criterio de aceptación:** el `.md` refleja columna, filtro y detalle nuevos.

**T10 — `docs/db_schema_er_global.md`.**
- La relación `organo ||--o{ cargo_ejecutivo : ""` ya figura (L41), pero como aspiracional/
  inconsistente con el estado previo. Verificar que quede correcta tras el refactor y, si
  procede, etiquetarla `"organo (organo_id)"`.
- **Nota pre-existente (reportar, no obligatorio corregir aquí):** el comentario L24 dice que
  `organo_directorio` no tiene FK a `organo`, lo cual quedó obsoleto tras la migración `0039`.
  Corregir solo si es trivial y no expande el alcance.
- **Criterio de aceptación:** el diagrama ER refleja `cargo_ejecutivo >── organo` de forma
  consistente.

**T11 — `CLAUDE.md`.**
- En la sección de catálogos (bullet de `executive-positions`, ~L102), agregar el nuevo FK
  `organo` (id → `organs`), el filtro `organo` y la lectura con `organo_detalle`, más la
  regla de coherencia `organo == organo_directivo.organo` cuando `organo_directivo` está
  seteado.
- **Criterio de aceptación:** la descripción de `executive-positions` en `CLAUDE.md` menciona
  el nuevo FK, filtro, detalle y la regla de coherencia.

---

## 4. Mapa Regla → Capa

| Regla | Enunciado | Capa donde se implementa |
|-------|-----------|--------------------------|
| RN-CE-01 | `cargo_ejecutivo.organo` es obligatorio (NOT NULL) | Modelo (`null=False`) + serializer (campo requerido) + migración (paso 3 `AlterField`) |
| RN-CE-02 | `organo == organo_directivo.organo` cuando `organo_directivo` no es nulo | **Serializer** `validate()` (T6) — el CRUD no ejecuta `Model.clean()` |
| RN-CE-03 | Cargo global (`organo_directivo` nulo): `organo` presente, sin coherencia | Serializer (T6): coherencia se omite si `organo_directivo` es nulo |
| RN-CE-04 | Data legacy: derivar `organo_id` de `organo_directivo.organo_id` | **Migración** `RunPython` (T5, paso 2) |
| RN-CE-05 | Integridad referencial ante borrado de `organo` | Modelo (`on_delete=PROTECT`) |

**Distribución explícita (regla del proyecto):**
- **Va en el serializer (`validate()`):** coherencia `organo == organo_directivo.organo`
  (RN-CE-02, RN-CE-03) y la obligatoriedad expuesta en API (RN-CE-01, parte API).
- **Va en el modelo:** obligatoriedad a nivel de esquema (`null=False`) y `PROTECT` (RN-CE-01,
  RN-CE-05).
- **Va en la migración:** backfill de datos (RN-CE-04) y el `AlterField` a NOT NULL.
- **NO va en `services`:** este refactor no añade lógica de negocio de escritura a services.

---

## 5. Referencias schema / código

- Modelo a modificar: `apps/convenios/models.py` → `ExecutivePosition` (L186-216); catálogo
  `Organ` (L167-183); fuente de derivación `OrganDirectory.organo` (L312-316).
- Endpoint/serializer: `apps/convenios/views.py` → entrada `"executive-positions"` en
  `ENTITY_VIEWSETS` (L764-771); helpers `_auto_serializer` (L467), `_entity_viewset` (L521),
  `_detalle_nombre` (L437), `_detalle_organo_directorio` (L447); patrón de serializer/viewset
  custom `_OrganDirectorySerializer` (L694) + `OrganDirectoryViewSet` (L728).
- Verificación sin cambio: `apps/convenios/services.py` → `_validar_coherencia_parte`
  (L862-887).
- Migraciones: última = `0041`; nueva = `0042`.
- Tablas/columnas: `cargo_ejecutivo` (nueva columna `organo_id`), `organo`, `organo_directorio`
  (`organo_id`).
- Docs a sincronizar: `docs/db_schema_modulo_01_convenios.md` (L42, L143-155),
  `docs/db_schema_er_global.md` (L41 y comentario L24), `CLAUDE.md` (~L102).

---

## 6. Checklist de verificación para `validator`

- [ ] `ExecutivePosition.organo` existe: FK a `Organ`, `PROTECT`, `db_column="organo_id"`,
      `null=False`, `help_text`/`verbose_name` en español, `related_name` sin colisión.
- [ ] `unique_together` de `cargo_ejecutivo` **sin cambios** (`(organo_directivo, nombre_masculino)`).
- [ ] Diagnóstico de conteos (total / con `organo_directivo` / sin `organo_directivo`)
      reportado al usuario.
- [ ] **Bloqueante:** si existían filas con `organo_directivo` nulo, la implementación se
      detuvo y consultó al usuario; **no** se forzó NOT NULL sin resolverlas.
- [ ] Migración `0042` con 3 pasos (`AddField` nullable → `RunPython` backfill → `AlterField`
      NOT NULL), reversible, dependiente de `0041`, usando modelos históricos en el `RunPython`.
- [ ] `python manage.py makemigrations --check --dry-run` sin cambios pendientes.
- [ ] `python manage.py check` pasa.
- [ ] Serializer custom `_ExecutivePositionSerializer` con `validate()` de coherencia,
      soporta PATCH parcial (instance + attrs), mensaje en español; coherencia omitida si
      `organo_directivo` es nulo.
- [ ] Viewset `executive-positions` usa el serializer custom; `filterset_fields` incluye
      `organo` (exact) y conserva `organo_directivo` (exact/isnull) y `activo`; `detalles`
      incluye `organo` (`_detalle_nombre`) y `organo_directivo` (`_detalle_organo_directorio`).
- [ ] Lectura de `/api/v1/executive-positions/` expone `organo` (id) + `organo_detalle`.
- [ ] Escritura sigue restringida a `Administrador RENADS` (permiso no alterado).
- [ ] `services._validar_coherencia_parte` intacto (verificado, no modificado).
- [ ] Docs sincronizados: `db_schema_modulo_01_convenios.md`, `db_schema_er_global.md`,
      `CLAUDE.md`.
- [ ] `migrate` y tests NO ejecutados por `implement` (los corre el usuario).
- [ ] No se corrigió la discrepancia `organo_directorio.categoria` fuera de alcance (solo
      reportada si estorbó).

---

## 7. Notas y bloqueantes

- **Bloqueante condicional (crítico):** el paso a `NOT NULL` de `cargo_ejecutivo.organo` solo
  es seguro si **todas** las filas existentes pueden derivar `organo_id` desde
  `organo_directivo.organo_id`. Las filas con `organo_directivo IS NULL` (cargos globales
  legacy, listables hoy vía `organo_directivo__isnull=true`) **no** pueden derivarlo. Ante
  cualquiera de ellas, `implement` **debe detenerse y consultar al usuario** antes de fijar
  NOT NULL. No inventar defaults.
- **Discrepancia `categoria` (fuera de alcance):** `services.py`/`serializers.py` leen
  `organo_directorio.categoria` (retirado en `0039`). No se corrige en este refactor; solo se
  reporta si impide `check`/`makemigrations`. Este refactor usa `organo_directivo.organo`
  (FK vigente), no `categoria`.
- **Convenciones:** nombres de tabla/columna, `help_text`, `verbose_name` y mensajes de error
  en **español**; identificadores de código en **inglés**.
- **Comandos permitidos a `implement`:** `.venv\Scripts\Activate.ps1`, `makemigrations`,
  `makemigrations --check`, `check`. **Prohibidos:** `migrate`, `test`, `runserver`.
