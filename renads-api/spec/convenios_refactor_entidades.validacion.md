# Validación — Refactor de entidades del módulo Convenios

Fecha: 2026-08-31 · Fuente de verdad: `spec/convenios_refactor_entidades.md`, `docs/db_schema_modulo_01_convenios.md`, `docs/db_schema_er_global.md`, modelos/serializers/views/services/selectors de `apps/convenios`.

## Veredicto: OK — validado (sin errores altos/medios)

Re-validación focalizada tras corregir el único hallazgo ALTO previo: la migración `0029` fallaba en PostgreSQL al reescribir los valores de las FKs mientras la constraint hacia `tipo_organo` seguía viva. Corregido con el patrón bridge `db_constraint=False`. Se genera la guía de pruebas manuales en `spec/convenios_refactor_entidades.guia_pruebas.md`.

### Diagnósticos ejecutados (solo lectura)
- `python manage.py check` → **0 issues** (exit 0).
- `python manage.py makemigrations --check --dry-run` → **No changes detected** (exit 0): el estado de los modelos coincide con el árbol de migraciones; no hay migraciones pendientes.

## 1. Migración `0029_migrate_and_repoint_organ_types.py` — patrón bridge (hallazgo ALTO previo: RESUELTO)

Orden de `operations` confirmado:

1. `AlterField(executingunit.tipo_organo → _EU_TIPO_ORGANO_BRIDGE)` con `db_constraint=False`.
2. `AlterField(university.tipo_entidad → _UNI_TIPO_ENTIDAD_BRIDGE)` con `db_constraint=False`.
3. `RunPython(forwards, noop)` — normaliza nombres de `organo`, backfill de `organo_directorio.categoria`, crea una fila de `organo_directorio` por cada `tipo_organo` y reescribe los valores de `unidad_ejecutora.tipo_organo_id` y `universidad.tipo_entidad_id` a los nuevos ids de directorio.
4. `AlterField(executingunit.tipo_organo → _EU_TIPO_ORGANO)` con `db_constraint=True`.
5. `AlterField(university.tipo_entidad → _UNI_TIPO_ENTIDAD)` con `db_constraint=True`.

**Comportamiento en PostgreSQL:**
- Pasos 1-2 → `ALTER TABLE ... DROP CONSTRAINT` de las FKs viejas hacia `tipo_organo`. Con `db_constraint=False` **no** se agrega una nueva constraint; la columna queda como entero suelto. El `db_column` se preserva (`tipo_organo_id`, `tipo_entidad_id`) → no hay rename ni recreación de columna.
- Paso 3 → los `UPDATE` de reapuntado ocurren **sin FK viva** → no se dispara validación aunque las columnas contengan ids de `tipo_organo` al inicio del RunPython.
- Pasos 4-5 → `ALTER TABLE ... ADD CONSTRAINT ... REFERENCES organo_directorio`; los valores ya fueron reescritos en el paso 3 → la validación pasa.

Secuencia neta: **DROP (1-2) → UPDATE sin FK (3) → ADD (4-5)**. En ningún punto se viola una FK. En SQLite el chequeo de FK está desactivado durante la transacción atómica y el `foreign_key_check` de cierre valida el estado final. Patrón portátil.

Los campos puente (`_*_BRIDGE`) y finales difieren únicamente en `db_constraint`; `to`, `on_delete=PROTECT`, `db_column`, `related_name`, `limit_choices_to` y `help_text` son idénticos.

## 2. Coherencia de `0028` y `0030`

- **`0028` (aditivo):** solo `AddField`/`RenameField`/`AlterField` no destructivos; deja `categoria` nullable para el backfill de 0029; no toca constraints de FK. Coherente.
- **`0030` (destructivo final):** `RemoveField` de `organo_directorio.{tipo_organo,organo,ubigeo,referencia_logo}` y `DeleteModel(OrganType)`. **`DeleteModel OrganType` es seguro**: tras 0029 ninguna FK (state ni BD) referencia ya `tipo_organo`; la FK propia `organo_directorio.tipo_organo` se elimina en el paso 1 de 0030 antes del `DeleteModel`. Luego fija `categoria` no-nullable (ya poblada) y finaliza `cargo_ejecutivo` (drop `codigo`, unicidad/orden por `nombre_masculino`).
- Modelos coherentes con el estado final: `ExecutivePosition` con `nombre_masculino`/`nombre_femenino`, `unique_together (organo, nombre_masculino)`, sin `codigo`.

## 3. Reverse (observación BAJA — aceptable por diseño)

Al revertir `0030`, `RemoveField(executiveposition.codigo)` recrea `codigo` con su definición histórica (`0001_initial`: `CharField(max_length=50, unique=True)` — NOT NULL, único, sin default), lo que **aborta** sobre una tabla con filas. `0029` usa `noop` en reverse (los `tipo_organo` ya no existen). Es un refactor *forward-only*: la reversibilidad completa no es objetivo y el reverse aborta limpiamente sin corromper datos. Recomendación no bloqueante: añadir una línea en el docstring de `0030` advirtiendo el abort del reverse por `cargo_ejecutivo.codigo`.

## Conclusión

El patrón bridge `db_constraint=False` resuelve el hallazgo ALTO previo; migraciones coherentes y portátiles (SQLite + PostgreSQL); `check` y `makemigrations --check` limpios. **Módulo validado.**
