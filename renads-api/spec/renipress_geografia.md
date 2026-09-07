# Spec — Normalización de la jerarquía geográfica sanitaria (RENIPRESS/SUSALUD) — Módulo 1 `convenios`

## 1. Resumen del módulo

Refactor de normalización (mínimo, sin rehacer tablas) de la jerarquía geográfica sanitaria del Módulo 1 (`apps/convenios`) para alinearla con los valores de **RENIPRESS/SUSALUD**, conservando el idioma Django de FKs por PK entera surrogate.

**Jerarquía (ya existente, sin cambio estructural):**

```
HealthGeographicScope (ambito_geografico_sanitario)  ← codigo_DISA / DISA
   └──< Red (red)                                     ← Codigo_Red  → red.codigo (único dentro del ámbito)
          └──< Microred (microred)                    ← Codigo_Microred → microred.codigo (único dentro de la red)
                 └──< Ipress (ipress)                 ← código único 8 dígitos → ipress.codigo_renipress
```

**Decisión de diseño confirmada (no reabrir):** los FK jerárquicos siguen siendo PK enteras surrogate. NO se encadena por el `codigo` varchar porque los códigos RENIPRESS de red/microred no son únicos a nivel nacional (se repiten entre DISAs; únicos solo dentro del padre vía `unique_together`), y usar varchar como FK penaliza joins/índices y no soporta FK compuesta en Django. El `codigo` natural RENIPRESS se conserva como columna de negocio única por nivel; el loader resuelve `codigo → id` durante la carga.

**Entidades cubiertas:** `HealthGeographicScope`, `Red`, `Microred`, `Ipress` (todas en `apps/convenios/models.py`).

### Alcance de los 3 ajustes (NO rehacer tablas)

| # | Ajuste | Entidad |
|---|--------|---------|
| A | `codigo_renipress` → único y requerido | `Ipress` |
| B | Coherencia `microred.red.ambito == ipress.ambito` (denormalización deliberada) | `Ipress` |
| C | Confirmar/especificar mapeo del loader RENIPRESS (no existe hoy) | loader / docs |

**Sin cambio de modelo:** `HealthGeographicScope`, `Red`, `Microred` ya calzan con `codigo_DISA/DISA`, `Codigo_Red`, `Codigo_Microred` respectivamente. No tocar sus modelos.

### Estado de anclaje verificado

- `apps/convenios/models.py:364` — `class Ipress`.
- `apps/convenios/models.py:370` — `codigo_renipress = CharField(max_length=20, blank=True)` (HOY: sin `unique`, no requerido).
- `apps/convenios/models.py:376-379` — FK `ambito_geografico_sanitario` (PROTECT, requerido, directo).
- `apps/convenios/models.py:388-391` — FK `microred` (PROTECT, **nullable**).
- La tabla `ipress` tiene **0 filas** hoy (verificado) → migración `AlterField` directa, **sin** data migration de limpieza.
- `IpressViewSet` (`apps/convenios/views.py:554-596`) usa serializer **auto-generado** por `_auto_serializer(m.Ipress, detalles={...})` (`views.py:576-585`) con `fields="__all__"`. **No existe** un serializer de Ipress escrito a mano ni un `service`/`selector` de Ipress dedicado (verificado: `services.py` solo referencia `Ipress` en campos clínicos y `autorizar_sede_docente`).
- **No existe** loader (`management/command`) para `ipress`/`red`/`microred`/`ambito`. Los únicos loaders son `load_ubigeo.py`, `load_universidades.py`, `load_gobiernos_regionales.py`.
- Última migración de la app: `0035_convention_parties_nomenclatura.py` → la nueva será `0036_*`.
- Schema doc a actualizar: `docs/db_schema_modulo_01_convenios.md:174-198` (tabla `ipress`) y `:49-75` (jerarquía `red`/`microred`).

---

## 2. Lista de tareas

### Modelo — `apps/convenios/models.py`

#### Tarea 1 — `Ipress.codigo_renipress` → único y requerido

Editar el campo en `apps/convenios/models.py:370`.

- **Antes:** `codigo_renipress = models.CharField("código RENIPRESS", max_length=20, blank=True, help_text="Código RENIPRESS")`
- **Después:** `codigo_renipress = models.CharField("código RENIPRESS", max_length=20, unique=True, help_text="Código único RENIPRESS del establecimiento")`
- Quitar `blank=True` (pasa a requerido en formularios/serializer); añadir `unique=True`; actualizar el `help_text` a `"Código único RENIPRESS del establecimiento"`.
- NO añadir `default` ni data migration: la tabla tiene 0 filas.

**Criterios de aceptación:**
- El campo queda `unique=True` y sin `blank=True`.
- `python manage.py makemigrations` genera un único `AlterField` sobre `ipress.codigo_renipress` (sin `RunPython`).
- Dos IPRESS con el mismo `codigo_renipress` provocan `IntegrityError`/error de validación 400.

**Referencia:** `apps/convenios/models.py:370`; RN → ajuste A.

#### Tarea 2 — Validación de coherencia `microred ↔ ámbito` en `Ipress.clean()`

Añadir/definir el método `clean()` en `class Ipress` (`apps/convenios/models.py:364-424`, insertar antes de `__str__` en `models.py:423`).

- Regla (denormalización deliberada): **si** `self.microred_id` está seteado, entonces `self.microred.red.ambito_geografico_sanitario_id` **debe** ser igual a `self.ambito_geografico_sanitario_id`. Si difieren → `ValidationError` en español.
- Si `microred` es `None` → no valida (muchas IPRESS RENIPRESS no cuelgan de microred; el `ambito` directo es la fuente autoritativa, RN-25 deriva de `ipress.ambito_geografico_sanitario_id`).
- Mensaje sugerido (español, orientado al usuario): `"La microred seleccionada pertenece a un ámbito geográfico sanitario distinto al de la IPRESS."` — asociado a la clave `microred`.
- Acceder al ámbito de la microred vía `self.microred.red.ambito_geografico_sanitario_id` (una sola cadena de FKs; el loader/serializer deben tener `microred` y `red` cargados o Django hará la query — aceptable en el volumen del MVP).
- Guardar la referencia al `ambito` **directo** como fuente autoritativa: nunca sobrescribir `ambito_geografico_sanitario` a partir de la microred; solo validar coherencia.

**Criterios de aceptación:**
- `Ipress(...).full_clean()` con `microred` de ámbito distinto lanza `ValidationError` con la clave `microred` y mensaje en español.
- `full_clean()` con `microred=None` (y `ambito` seteado) pasa sin error.
- `full_clean()` con `microred` cuyo `red.ambito == ipress.ambito` pasa sin error.
- No se modifica `ambito_geografico_sanitario` dentro de `clean()`.

**Referencia:** `apps/convenios/models.py:376-391`; RN → ajuste B.

### Serializers — `apps/convenios/views.py` (serializer auto-generado del `IpressViewSet`)

#### Tarea 3 — Enganchar la validación de coherencia en el serializer del `IpressViewSet`

El `IpressViewSet` usa un serializer auto-generado (`_auto_serializer`, `views.py:576-585`) que NO ejecuta `Model.clean()`. Hay que garantizar que la RN del ajuste B se dispare en la API (create y update, incluido PATCH parcial).

Opción de implementación (elegir la primera viable; documentar cuál se usó):
- **Preferida:** hacer que el serializer del `IpressViewSet` invoque la validación del modelo. Definir una clase de serializer explícita para Ipress (sustituyendo el `_auto_serializer` inline en `views.py:576-585`, o creándola en `apps/convenios/serializers.py`) que:
  - mantenga `fields="__all__"` y los mismos campos `*_detalle` (`categoria`, `tipo_clasificacion`, `ambito_geografico_sanitario`, `microred`, `ubigeo`) y el `referencia_logo` como URL de solo lectura, tal como hoy;
  - agregue `def validate(self, attrs)` que resuelva el estado final del objeto (para PATCH parcial, combinando `self.instance` + `attrs`) y ejecute la regla de coherencia `microred ↔ ámbito` (reusar el `Ipress.clean()` construyendo una instancia en memoria y llamando `instance.clean()`, o replicar la comparación de ids). Convertir `django.core.exceptions.ValidationError` a `rest_framework.serializers.ValidationError` para responder 400.
- **Alternativa mínima** (si no se quiere clase explícita): añadir el método `validate` al `_auto_serializer` mediante el mapa de atributos, o llamar `instance.full_clean(exclude=[...])` en el flujo. Debe cubrir igualmente create y PATCH parcial.

- El serializer debe exponer `codigo_renipress` como **requerido** (efecto automático al quitar `blank=True` en el modelo; verificar que `_auto_serializer`/`ModelSerializer` lo marque `required=True`).

**Criterios de aceptación:**
- `POST /api/v1/ipress/` con `microred` de otro ámbito → 400 con mensaje español en la clave `microred`.
- `PATCH /api/v1/ipress/{id}/` que cambia solo `microred` a una de ámbito distinto → 400 (resuelve el estado final combinando instancia + payload parcial).
- `POST` sin `codigo_renipress` → 400 (campo requerido).
- `POST` con `codigo_renipress` duplicado → 400 (unicidad).
- La lectura sigue exponiendo los `*_detalle` y la URL de logo sin cambios.

**Referencia:** `apps/convenios/views.py:554-596` (viewset), `views.py:576-585` (serializer inline), `views.py:462-496` (`_auto_serializer`); RN → ajustes A y B.

### Migración — `apps/convenios/migrations/`

#### Tarea 4 — Generar migración `0036` (AlterField de `codigo_renipress`)

- Ejecutar `python manage.py makemigrations convenios` tras la Tarea 1.
- Debe producir **una** operación `migrations.AlterField` sobre `ipress.codigo_renipress` (nuevo `unique=True`, sin `blank`, `help_text` actualizado). Sin `RunPython`/data migration (tabla vacía).
- La Tarea 2 (`clean()`) **no** genera migración (es lógica Python, no cambia el schema).
- Nombre esperado: `0036_alter_ipress_codigo_renipress.py` (o el que asigne Django); depende de `0035_convention_parties_nomenclatura`.

**Criterios de aceptación:**
- `python manage.py makemigrations --check --dry-run` no reporta cambios pendientes tras crear la migración.
- `python manage.py migrate` aplica sin error sobre BD de desarrollo (0 filas en `ipress`).

**Referencia:** `apps/convenios/migrations/0035_convention_parties_nomenclatura.py`; RN → ajuste A.

### Loader RENIPRESS — `apps/convenios/management/commands/` (opcional / documental)

#### Tarea 5 — Especificar el mapeo del loader (NO existe hoy — no inventar el comando)

**Verificado:** no hay ningún management command que cargue `ipress`/`red`/`microred`/`ambito_geografico_sanitario` (solo `load_ubigeo`, `load_universidades`, `load_gobiernos_regionales`). Por tanto esta tarea es **documental/opcional**, no se implementa un loader nuevo salvo confirmación del usuario.

Especificación del mapeo que **debe** respetar un futuro loader RENIPRESS/SUSALUD (documentarla en el docstring del comando cuando exista, o en `docs/db_schema_modulo_01_convenios.md`):

- `codigo_DISA` / `DISA` → `HealthGeographicScope.codigo` / `.nombre` (buscar/crear por `codigo`, único global).
- `Codigo_Red` → `Red.codigo`, resuelto contra `(ambito_geografico_sanitario, codigo)` (`unique_together`) → `Red.id`.
- `Codigo_Microred` → `Microred.codigo`, resuelto contra `(red, codigo)` (`unique_together`) → `Microred.id`.
- Código único de la IPRESS (8 dígitos RENIPRESS) → `Ipress.codigo_renipress` (**siempre poblado**, ahora requerido + único).
- El loader **resuelve `codigo → id`** para poblar los FK (`red_id`, `microred_id`, `ambito_geografico_sanitario_id`), NO encadena por varchar.
- Debe respetar la coherencia del ajuste B: `microred.red.ambito == ipress.ambito` (o llamar `full_clean()` / el `service`/serializer antes de guardar).
- `ipress.ambito_geografico_sanitario_id` se puebla **directo** desde el `codigo_DISA` de la fila IPRESS (fuente autoritativa), no derivado de la microred.

**Criterios de aceptación:**
- Existe una nota clara (en spec y/o schema doc) que fija el mapeo `codigo_* → id` y la obligatoriedad de `codigo_renipress`.
- Si en el futuro se implementa el loader, poblar `codigo_renipress` en todas las filas y respetar la coherencia B.
- NO se crea un comando nuevo en este cambio a menos que el usuario lo pida.

**Referencia:** `apps/convenios/management/commands/{load_ubigeo,load_universidades,load_gobiernos_regionales}.py` (patrón); RN → ajuste C.

### Documentación — `docs/db_schema_modulo_01_convenios.md`

#### Tarea 6 — Actualizar el schema doc en el mismo cambio

- Fila `codigo_renipress` (`docs/db_schema_modulo_01_convenios.md:181`): cambiar `Null` de `Sí` a **`No`**; descripción a `"Código único RENIPRESS del establecimiento (unique, requerido)"`.
- Fila `ambito_geografico_sanitario_id` (`:184`) y `microred_id` (`:187`): añadir una **nota de coherencia** debajo de la tabla `ipress`: "Si `microred_id` no es nulo, `microred.red.ambito_geografico_sanitario` debe coincidir con `ipress.ambito_geografico_sanitario` (denormalización deliberada; el ámbito directo es la fuente autoritativa, RN-25 deriva de `ipress.ambito_geografico_sanitario_id`)."
- En la sección "Jerarquía geográfica sanitaria" (`:49-75`): añadir nota RENIPRESS del mapeo `codigo_DISA/Codigo_Red/Codigo_Microred/código único → codigo`/`codigo_renipress`, y que los FK se enlazan por **id surrogate** (no por varchar; los códigos de red/microred no son únicos a nivel nacional).

**Criterios de aceptación:**
- El `.md` refleja `codigo_renipress` unique+requerido y la nota de coherencia `microred ↔ ámbito`.
- El `.md` documenta el mapeo RENIPRESS y la decisión de enlace por id surrogate.
- El cambio del `.md` va en el **mismo commit** que el cambio de modelo/migración.

**Referencia:** `docs/db_schema_modulo_01_convenios.md:49-75`, `:174-198`; RN → ajustes A, B, C.

---

## 3. Tabla RN → capa

| Ajuste | Regla | Modelo | Serializer | Service | Migración | Loader | Docs |
|--------|-------|--------|-----------|---------|-----------|--------|------|
| A | `codigo_renipress` único + requerido | ✅ `Ipress.codigo_renipress` (T1) | ✅ requerido (efecto auto, T3) | — | ✅ `0036` AlterField (T4) | Nota: poblar siempre (T5) | ✅ `:181` (T6) |
| B | Coherencia `microred.red.ambito == ipress.ambito` (si microred no nula) | ✅ `Ipress.clean()` (T2) | ✅ `validate()` create+PATCH (T3) | — (no hay service de Ipress) | — (sin cambio de schema) | Respetar en carga (T5) | ✅ nota `:184/:187` (T6) |
| C | Mapeo RENIPRESS `codigo → id`, enlace por id surrogate | — | — | — | — | ✅ documental/opcional, no inventar (T5) | ✅ `:49-75` (T6) |

**Marcado modelo vs. serializer para la RN B:** la validación es **de negocio/integridad** (relación entre FKs), va en `Ipress.clean()` (modelo) como fuente única y se **replica/invoca** desde el `validate()` del serializer del `IpressViewSet` para que la API responda 400 (el serializer auto-generado no llama `clean()` por sí solo). La RN A es **validación de campo** (unicidad + requerido): la resuelve el propio `unique=True`/no-`blank` del modelo, propagado automáticamente al serializer.

---

## 4. Checklist de verificación

- [ ] `apps/convenios/models.py:370` — `codigo_renipress` con `unique=True`, sin `blank=True`, `help_text` actualizado.
- [ ] `apps/convenios/models.py` — `Ipress.clean()` implementa la coherencia `microred ↔ ámbito` (solo si `microred` no nula), mensaje en español, sin sobrescribir `ambito`.
- [ ] `IpressViewSet` — el serializer expone `codigo_renipress` requerido y ejecuta la validación de coherencia en create **y** PATCH parcial (traduciendo a `serializers.ValidationError` → 400).
- [ ] `python manage.py makemigrations convenios` → una sola `AlterField` (`0036_*`), sin `RunPython`.
- [ ] `python manage.py makemigrations --check --dry-run` → sin cambios pendientes.
- [ ] `python manage.py migrate` → aplica sin error (BD dev, `ipress` con 0 filas).
- [ ] `python manage.py check` → sin errores.
- [ ] OpenAPI/`drf-spectacular` (`python manage.py spectacular --file schema.yml` o el gate del proyecto) → genera sin errores; el schema de `ipress` muestra `codigo_renipress` requerido.
- [ ] `docs/db_schema_modulo_01_convenios.md` actualizado (`:181` unique+requerido, nota de coherencia bajo la tabla `ipress`, nota RENIPRESS en `:49-75`) en el mismo commit.
- [ ] **NO ejecutar tests automatizados** — el usuario pidió consultar antes de testing. Detenerse y preguntar antes de correr `python manage.py test`.

---

## 5. Referencias (tablas/columnas y reglas)

- Tabla `ipress` — columnas: `codigo_renipress` (T1/T4), `ambito_geografico_sanitario_id` + `microred_id` (T2/T3). Schema: `docs/db_schema_modulo_01_convenios.md:174-198`. Modelo: `apps/convenios/models.py:364-424`.
- Tablas `red` / `microred` — `unique_together (ambito, codigo)` y `(red, codigo)`. Schema: `docs/db_schema_modulo_01_convenios.md:49-75`. Modelos: `apps/convenios/models.py` (`class Red`, `class Microred`).
- Tabla `ambito_geografico_sanitario` (`HealthGeographicScope(Catalog)`) — `codigo` único global = `codigo_DISA`. Sin cambio.
- `IpressViewSet` y serializer auto-generado: `apps/convenios/views.py:554-596`, `:576-585`, `:462-496`.
- RN-25 (interno → ámbito derivado de `ipress.ambito_geografico_sanitario_id`): `CLAUDE.md` (reglas Módulo 1) — sustenta la denormalización del ajuste B.
- Loaders existentes (patrón): `apps/convenios/management/commands/{load_ubigeo,load_universidades,load_gobiernos_regionales}.py`.

---

## 6. Notas para el agente Implement

- **No rehacer tablas** ni cambiar los FK a varchar. Solo los 3 ajustes (A, B, C) de esta spec.
- **No inventar** el loader RENIPRESS (T5 es documental); consultar al usuario si se quiere implementarlo.
- El `ambito_geografico_sanitario` directo de `ipress` es **siempre** la fuente autoritativa; `clean()` valida, no reescribe.
- Tras la implementación de modelo/serializer/migración: ejecutar `/code-review` (regla del proyecto para tareas Django/DRF) **antes** de dar por terminado, pero **NO** ejecutar la suite de tests (consultar primero).
