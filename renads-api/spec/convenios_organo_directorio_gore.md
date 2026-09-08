# Spec — Refactor: trasladar `gobierno_regional` de `organo_directorio` a `convenio`

> Módulo: **Gestionar Convenios** (`apps/convenios`)
> Tipo: refactor de esquema + servicios + serializers/views + PDF + docs.
> Estado: **decisión del usuario confirmada** — implementar según este spec.
> Este archivo NO contiene código de aplicación; es la lista de tareas para el agente `implement`.

---

## 1. Resumen del refactor

Hoy la identidad del **Gobierno Regional (GORE)** de un órgano regional vive en
`organo_directorio.gobierno_regional_id` (FK a `RegionalGovernment` / tabla `gobierno_regional`).
El `OrganDirectory` pasa a depender **solo** de su FK `organo_id` (FK a `Organ`), y la identidad
del GORE se **traslada al convenio**:

- **Se elimina** el campo/columna `gobierno_regional_id` de `organo_directorio` (`OrganDirectory`).
- **Se agrega** un FK `gobierno_regional` (nullable, `PROTECT`) directo a `convenio` (`Convention`),
  con `db_column="gobierno_regional_id"`.
- La unicidad de `organo_directorio` **colapsa** de dos `UniqueConstraint` parciales
  (con GORE / sin GORE) a un único `UniqueConstraint(fields=["organo", "nombre"])`.

**Entidades afectadas:** `OrganDirectory` (tabla `organo_directorio`), `Convention` (tabla `convenio`).

**NO se toca:** `ExecutingUnit.gobierno_regional` (`unidad_ejecutora.gobierno_regional_id`) — es un
FK propio e independiente, con su propia semántica; queda intacto.

### Nota previa importante (fuera del alcance de este refactor)

El código actual (`services.py`, `serializers.py`) referencia `organo_directorio.categoria` /
`get_categoria_display`, pero la migración `0039_organdirectory_organo_fk` **retiró** el campo
`categoria` y lo reemplazó por el FK `organo`. Esta posible discrepancia **NO forma parte de este
refactor**: `implement` NO debe corregir ni tocar la lógica de `categoria`/`organo`. Si `makemigrations`
o el arranque revelan que ese estado ya es inconsistente, **reportar al usuario** en lugar de resolverlo
aquí. El presente spec se limita estrictamente al traslado de `gobierno_regional`.

---

## 2. Reglas de negocio → capa

| Regla | Descripción | Capa donde vive |
|-------|-------------|-----------------|
| RN-GORE-1 | El `gobierno_regional` del convenio solo aplica conceptualmente a **Convenio Marco regional** (órgano de categoría/organo `GOBIERNO_REGIONAL`). | **Services** (`crear_convenio` / `actualizar_convenio`) — validación recomendada; ver Tarea 6.2 |
| RN-GORE-2 | Un Convenio **Marco regional** debe llevar `gobierno_regional` no nulo. Marco Lima (MINSA_DIRIS) y Convenios Específicos: `gobierno_regional` nulo. | **Services** (decisión del usuario en Tarea 6.2: validar o dejar nullable libre) |
| RN-GORE-3 | Unicidad de `organo_directorio`: única por `(organo, nombre)` (sin GORE). | **Model** (`UniqueConstraint`) + **Serializer** `_OrganDirectorySerializer.validate()` |
| RN-GORE-4 | La adenda hereda `gobierno_regional` de su `convenio_origen`. | **Services** (`crear_adenda`) |
| RN-GORE-5 | El domicilio de la parte `GOBIERNO_REGIONAL` en el PDF se deriva de `convenio.gobierno_regional`. | **PDF** (`_domicilio_entidad`) |
| RN-GORE-6 (data) | El GORE existente en `organo_directorio.gobierno_regional_id` no debe perderse: se copia a los convenios que referencian ese órgano **antes** de borrar la columna. | **Migración** (RunPython, ver §7 y Tarea 2) |

> `_OrganDirectorySerializer` usa `_auto_serializer`, que **NO** ejecuta `Model.clean()`.
> Toda validación de unicidad debe ir en `validate()` del serializer (además del constraint de BD).

---

## 3. Fuentes de verdad consultadas

- Modelo: `apps/convenios/models.py` — `OrganDirectory` (L304-348), `ExecutingUnit` (L351, **no tocar**), `Convention` (L806-879).
- Views: `apps/convenios/views.py` — `_OrganDirectorySerializer` (L694-735), `OrganDirectoryViewSet` (L738-751).
- Serializers: `apps/convenios/serializers.py` — `ConventionReadSerializer` (L34-98), `ConventionWriteSerializer` (L101-111), `AdendaWriteSerializer` (L114-121).
- Services: `apps/convenios/services.py` — `crear_convenio` (L217+), `crear_adenda` (L287-337), `actualizar_convenio` (L341-364), `_validar_composicion_partes` (L154-181), `sincronizar_partes` (L849+).
- PDF: `apps/convenios/pdf.py` — `_domicilio_entidad` (L59-77).
- Schema docs: `docs/db_schema_modulo_01_convenios.md` (tablas `organo_directorio` L127-140 y `convenio` L437+), `docs/db_schema_er_global.md` (L685-717).
- Última migración: `0040_alter_executingunit_tipo_organo_and_more.py` → la nueva migración es **`0041`**.

---

## 4. Tareas — Capa MODELO (`apps/convenios/models.py`)

### Tarea 1.1 — `OrganDirectory`: eliminar el campo `gobierno_regional`

- Eliminar el bloque `gobierno_regional = models.ForeignKey(RegionalGovernment, ...)` (L317-321).
- Actualizar el docstring de la clase (L305-310): quitar la frase "Los órganos regionales pueden llevar `gobierno_regional`."
- **Criterio de aceptación:** `OrganDirectory` ya no expone atributo `gobierno_regional`; el único FK es `organo`.

### Tarea 1.2 — `OrganDirectory.Meta.constraints`: colapsar a un único `UniqueConstraint`

- Reemplazar los dos `UniqueConstraint` parciales (`uniq_organo_dir_organo_gore_nombre` y
  `uniq_organo_dir_organo_nombre_sin_gore`, L335-344) por **uno solo**:
  - `UniqueConstraint(fields=["organo", "nombre"], name="uniq_organo_dir_organo_nombre")`.
- Actualizar el comentario (L331-334) para reflejar la regla `(organo, nombre)` sin GORE.
- **Criterio de aceptación:** existe un único constraint de unicidad por `(organo, nombre)`; ya no hay
  `condition=Q(gobierno_regional__...)`.

### Tarea 1.3 — `Convention`: agregar FK `gobierno_regional`

- Agregar en `Convention` (junto a los demás FKs de partes, p. ej. después de `organo_directorio`, L842-846):
  - `gobierno_regional = models.ForeignKey(RegionalGovernment, on_delete=models.PROTECT, db_column="gobierno_regional_id", null=True, blank=True, related_name="convenios", help_text="Gobierno Regional del convenio (solo Convenio Marco regional).")`
  - Verificar que `related_name="convenios"` no colisione con el `related_name` que `ExecutingUnit`/otros
    ya usan sobre `RegionalGovernment`. `ExecutingUnit` usa `related_name="unidades_ejecutoras"` y el
    `OrganDirectory` retirado usaba `related_name="organos_directorio"`; **`convenios` está libre** — usarlo.
    Si hubiera colisión, usar `related_name="convenios_por_gore"`.
- **Criterio de aceptación:** `Convention.gobierno_regional` existe como FK nullable `PROTECT` con
  `db_column="gobierno_regional_id"` y help_text en español; `ExecutingUnit.gobierno_regional` intacto.

---

## 5. Tareas — Capa MIGRACIÓN (`apps/convenios/migrations/0041_*.py`)

### Tarea 2 — Migración de esquema + data migration del GORE

Crear **una** migración `0041_convention_gobierno_regional_drop_organdirectory_gore` (nombre descriptivo)
que dependa de `0040_...`. **Orden estricto de operaciones:**

1. `AddField` `Convention.gobierno_regional` (nullable — tal como el modelo).
2. **RunPython (data migration RN-GORE-6)** — copiar el GORE del órgano al convenio **antes** de borrar
   la columna origen:
   - Para cada `Convention` cuyo `organo_directorio.gobierno_regional_id` no sea nulo, asignar
     `convention.gobierno_regional_id = organo_directorio.gobierno_regional_id`.
   - Implementación sugerida: iterar `Convention.objects.select_related("organo_directorio")` (usar los
     modelos históricos vía `apps.get_model`) y `bulk_update` del campo.
   - `reverse_code`: best-effort (`migrations.RunPython.noop` es aceptable, dado que la columna origen
     se elimina; documentar la irreversibilidad en el comentario).
   - **Antes de escribir la data migration, `implement` DEBE verificar el conteo de filas** de
     `organo_directorio` con `gobierno_regional_id` no nulo (p. ej. en `manage.py shell` o inspección):
     - Si **hay filas con GORE**: incluir la RunPython (obligatoria) para no perder el dato.
     - Si **no hay ninguna**: la RunPython puede ser un `noop` documentado, pero **igual debe existir el
       paso** (comentado como "sin datos que migrar al momento del refactor") para dejar constancia.
   - **Reportar el conteo al usuario** en el resumen de implementación.
3. `RemoveConstraint` `uniq_organo_dir_organo_gore_nombre`.
4. `RemoveConstraint` `uniq_organo_dir_organo_nombre_sin_gore`.
5. `AddConstraint` `uniq_organo_dir_organo_nombre` (`fields=["organo","nombre"]`).
6. `RemoveField` `OrganDirectory.gobierno_regional` (elimina la columna `gobierno_regional_id`).

> El `RemoveField` del paso 6 debe ir **después** de la RunPython del paso 2 (que aún necesita leer
> `organo_directorio.gobierno_regional_id`) y después de retirar las constraints que la referencian
> (pasos 3-4). Respetar este orden dentro de la lista `operations`.

- **Criterio de aceptación:**
  - `python manage.py makemigrations --check` no detecta cambios pendientes tras crear la migración.
  - La migración es autoconsistente en orden (no falla por columna/constraint inexistente).
  - Si había GORE en `organo_directorio`, queda copiado en los convenios correspondientes.
  - **No** se ejecuta `migrate` en este spec (lo corre el usuario).

---

## 6. Tareas — Capa SERIALIZERS / VIEWS

### Tarea 3.1 — `_OrganDirectorySerializer` (`views.py` L694-735)

- Quitar `"gobierno_regional"` del dict `detalles` (L697) → dejar solo `{"organo": _detalle_nombre}`.
- Reescribir el docstring (L700-707): la RN de unicidad pasa a `(organo, nombre)` sin GORE.
- Reescribir `validate()` (L709-735): eliminar toda referencia a `gobierno_regional`/`gore`; la
  validación de duplicado queda:
  - `qs = OrganDirectory._default_manager.filter(organo=organo, nombre=nombre)`
  - excluir `self.instance.pk` en update; si `exists()`, lanzar `ValidationError` en español sobre `nombre`
    ("Ya existe un órgano del directorio con este nombre para el mismo órgano.").
- **Criterio de aceptación:** el serializer no menciona `gobierno_regional`; crear/editar dos órganos con
  igual `(organo, nombre)` devuelve **400** legible (no IntegrityError 500).

### Tarea 3.2 — `OrganDirectoryViewSet` (`views.py` L738-751)

- Quitar `"gobierno_regional"` de `filterset_fields` (L741) → `["organo", "activo"]`.
- Quitar `"gobierno_regional"` del dict `detalles` (L743).
- Quitar `"gobierno_regional"` del `select_related` (L749) → `select_related("organo")`.
- **Criterio de aceptación:** `/api/v1/organ-directories/` ya no acepta filtro `gobierno_regional` ni lo
  expone en lectura; el listado no rompe (sin `select_related` inválido).

### Tarea 3.3 — `ConventionReadSerializer` (`serializers.py` L34-98)

- Agregar el nuevo campo de solo lectura para el GORE del convenio:
  - `gobierno_regional_detalle = serializers.SerializerMethodField()` con
    `get_gobierno_regional_detalle(self, obj)` → `_detalle_fk(obj.gobierno_regional, "nombre", "sigla")`
    (usar el helper `_detalle_fk` ya presente; verificar campos disponibles en `RegionalGovernment` —
    `nombre` y `sigla`).
  - Incluir `"gobierno_regional"` (el id) y `"gobierno_regional_detalle"` en `Meta.fields`
    (junto a `organo_directorio*`).
- **Criterio de aceptación:** `GET` de un convenio expone `gobierno_regional` (id) y
  `gobierno_regional_detalle` (id + nombre/sigla, o `null`).

### Tarea 3.4 — `ConventionWriteSerializer` (`serializers.py` L101-111)

- Agregar `"gobierno_regional"` a `Meta.fields` para que sea escribible en `POST`/`PATCH` de convenio.
- El campo es opcional a nivel serializer (nullable en el modelo); la obligatoriedad por tipo la impone
  el service (Tarea 6.2).
- **Criterio de aceptación:** se puede enviar `gobierno_regional` al crear/editar un convenio y persiste.

### Tarea 3.5 — Confirmar serializers que referencian `organo_directorio` sin `gobierno_regional`

- Revisar `EvaluacionTecnicaSerializer` (`serializers.py` ~L211) y cualquier otro serializer que use
  `organo_directorio`: **no deben** referenciar `gobierno_regional`. Confirmado en la inspección previa
  que no lo hacen — no requiere cambios, solo verificación.
- **Criterio de aceptación:** no queda ninguna referencia a `organo_directorio.gobierno_regional` en
  `serializers.py`.

---

## 7. Tareas — Capa PDF / SERVICES

### Tarea 4 — `apps/convenios/pdf.py` `_domicilio_entidad` (L59-77)

- Cambiar la rama `GOBIERNO_REGIONAL` (L68-70):
  - De `gore = getattr(convenio.organo_directorio, "gobierno_regional", None)`
  - A `gore = convenio.gobierno_regional`
  - Mantener el resto: `return getattr(gore, "direccion", "") or "" if gore else ""`.
- **Criterio de aceptación:** el domicilio de la parte `GOBIERNO_REGIONAL` en el PDF se deriva de
  `convenio.gobierno_regional.direccion`; nunca lanza si es `None`.

### Tarea 5 — `apps/convenios/pdf.py` `construir_contexto` / usos indirectos

- Buscar en `pdf.py` cualquier otro uso de `organo_directorio.gobierno_regional` (grep). Si `construir_contexto`
  arma datos del GORE (razón social / RUC / domicilio de la parte regional) a partir del órgano, repuntar a
  `convenio.gobierno_regional`.
- **Criterio de aceptación:** ninguna referencia a `organo_directorio.gobierno_regional` permanece en `pdf.py`.

### Tarea 6.1 — `services.crear_adenda` (L287-337): heredar `gobierno_regional`

- En `Convention.objects.create(...)` (L312-332) agregar
  `gobierno_regional=convenio_origen.gobierno_regional,` para que la adenda herede el GORE del origen (RN-GORE-4).
- Actualizar el docstring (L290-297) para listar `gobierno_regional` entre los campos heredados.
- **Criterio de aceptación:** una adenda creada vía `crear_adenda` copia el `gobierno_regional` del `convenio_origen`.

### Tarea 6.2 — `services.crear_convenio` y `actualizar_convenio`: regla del GORE por tipo (RN-GORE-1 / RN-GORE-2)

- **Decisión recomendada (regla en services):** validar que un Convenio **Marco regional** lleve
  `gobierno_regional` no nulo y que Marco Lima / Específico lo dejen nulo. Implementación sugerida:
  - En `crear_convenio` (tras determinar tipo y categoría/`organo` del órgano):
    - Si `tipo.codigo == "MARCO"` y el órgano es `GOBIERNO_REGIONAL` ⇒ exigir `datos.get("gobierno_regional")`
      no nulo; si falta, `ValidationError({"gobierno_regional": "Requerido para un Convenio Marco regional."})`.
    - Si `tipo.codigo == "MARCO"` y órgano `MINSA_DIRIS` (Lima) ⇒ `gobierno_regional` debe ser nulo
      (o ignorarse); definir mensaje si se envía.
    - Si `tipo.codigo == "ESPECIFICO"` ⇒ `gobierno_regional` nulo (se deriva del Marco; no se guarda en el
      Específico salvo decisión contraria).
  - Persistir `gobierno_regional` en el `Convention.objects.create(...)` de `crear_convenio`.
  - En `actualizar_convenio`: agregar `"gobierno_regional"` a la lista `editables` (L345-349) y revalidar la
    regla contra el estado final del objeto (igual patrón que `_validar_partes_por_tipo`).
- **Alternativa (si el usuario prefiere):** dejar `gobierno_regional` **nullable libre** sin validación de
  obligatoriedad — en ese caso, solo persistirlo en create/update sin gate. `implement` debe **confirmar con
  el usuario** cuál de las dos variantes aplicar antes de codificar el gate; por defecto, implementar la
  **regla en services** (recomendada).
- Considerar encapsular la validación en un helper `_validar_gobierno_regional_por_tipo(...)` reutilizado por
  `crear_convenio` y `actualizar_convenio` (coherente con `_validar_partes_por_tipo`).
- **Criterio de aceptación:**
  - Marco regional sin `gobierno_regional` ⇒ 400 (si se implementa la regla recomendada).
  - `gobierno_regional` persiste en create y update; `actualizar_convenio` lo revalida en PATCH parcial.

### Tarea 6.3 — `services`: verificar `_validar_composicion_partes` y `sincronizar_partes`

- `_validar_composicion_partes` (L154-181) y `sincronizar_partes` (L849+) usan
  `convenio.organo_directorio.categoria` para decidir la composición de partes GORE; **NO** dependen de
  `organo_directorio.gobierno_regional`. Confirmar por grep que no hay uso de
  `organo_directorio.gobierno_regional` en `services.py`. La composición de partes por categoría se mantiene igual.
- Si `construir_contexto`/partes del PDF necesitaran el GORE, ya se cubre en Tareas 4-5.
- **Criterio de aceptación:** no queda ninguna referencia a `organo_directorio.gobierno_regional` en `services.py`;
  la composición de partes GORE sigue funcionando por categoría del órgano.

### Tarea 6.4 — Barrido final de referencias

- Grep global en `apps/convenios/` de `organo_directorio.gobierno_regional` y de
  `gobierno_regional` sobre `OrganDirectory` (fuera de migraciones históricas) para asegurar que no queda
  ningún acceso vivo. Las migraciones antiguas (`0019`, `0037`, `0039`, etc.) **no se modifican**.
- **Criterio de aceptación:** cero referencias vivas a `OrganDirectory.gobierno_regional` en el código de
  aplicación (excluyendo migraciones históricas y la nueva `0041`).

---

## 8. Tareas — Capa DOCUMENTACIÓN (mismo cambio)

### Tarea 7.1 — `docs/db_schema_modulo_01_convenios.md`

- Tabla `organo_directorio` (§L127-140):
  - Quitar la frase "Los órganos regionales pueden llevar `gobierno_regional_id`." (L129).
  - Eliminar la fila `| gobierno_regional_id | ... |` (L135).
  - Actualizar el endpoint (L140): quitar `gobierno_regional` de los filtros y quitar
    `gobierno_regional_detalle` de lo que expone la lectura. Actualizar la nota de unicidad a `(organo, nombre)`.
  - Actualizar la nota L204 ("con `gobierno_regional_id` nulo y `categoria = ORGANO_MINSA`") — ya no existe
    esa columna; reformular a "categoría `ORGANO_MINSA`".
- Tabla `convenio` (§L437+):
  - Agregar la fila `| gobierno_regional_id | FK → gobierno_regional (PROTECT) | Sí (nullable) | Gobierno Regional del convenio (solo Convenio Marco regional) |`.
- **Criterio de aceptación:** el schema del módulo describe el nuevo `convenio.gobierno_regional_id` y ya no
  lista `organo_directorio.gobierno_regional_id`.

### Tarea 7.2 — `docs/db_schema_er_global.md`

- Eliminar/ajustar las relaciones (L685-717):
  - Quitar `gobierno_regional ──< organo_directorio` (L685).
  - Ajustar `organo_directorio (categoria: ...) >── gobierno_regional (opcional, solo regionales)` (L688):
    eliminar el `>── gobierno_regional`.
  - En el bloque de `convenio` (L714), agregar la relación `convenio >── gobierno_regional (opcional, solo Marco regional)`.
- **Criterio de aceptación:** el ER global refleja `convenio → gobierno_regional` y ya no `organo_directorio → gobierno_regional`.

### Tarea 7.3 — `CLAUDE.md`

- En la sección "Directorio de órganos y representantes (Módulo 1)": donde `organ-directories` se describe
  "filtrable por `categoria`/`gobierno_regional`/`activo`", quitar `gobierno_regional` → "filtrable por
  `categoria`/`activo`". Quitar mención a que lectura expone `gobierno_regional_detalle`.
- En el bloque de partes/PDF que menciona que el domicilio GORE se deriva del órgano: actualizar para indicar
  que el GORE del convenio vive en `convenio.gobierno_regional` (y de ahí se deriva el domicilio de la parte
  `GOBIERNO_REGIONAL`).
- **Criterio de aceptación:** `CLAUDE.md` no atribuye `gobierno_regional` a `organo_directorio`; describe el
  nuevo FK en `convenio`.

---

## 9. Checklist de verificación (para `validator`)

- [ ] `OrganDirectory` no tiene campo `gobierno_regional`; único constraint = `(organo, nombre)`.
- [ ] `ExecutingUnit.gobierno_regional` intacto (no modificado).
- [ ] `Convention.gobierno_regional` FK nullable `PROTECT`, `db_column="gobierno_regional_id"`, help_text español.
- [ ] Migración `0041` con orden correcto: AddField → RunPython(copiar GORE) → RemoveConstraint x2 → AddConstraint → RemoveField.
- [ ] Conteo de filas `organo_directorio` con GORE verificado y **reportado**; RunPython presente (real o noop documentado).
- [ ] `makemigrations --check` limpio tras la migración.
- [ ] `_OrganDirectorySerializer`: sin `gobierno_regional`; `validate()` por `(organo, nombre)`; 400 legible en duplicado.
- [ ] `OrganDirectoryViewSet`: sin `gobierno_regional` en filtros/detalles/`select_related`.
- [ ] `ConventionReadSerializer`: expone `gobierno_regional` + `gobierno_regional_detalle`.
- [ ] `ConventionWriteSerializer`: acepta `gobierno_regional`.
- [ ] `pdf.py`: `_domicilio_entidad` GORE usa `convenio.gobierno_regional`; sin refs a `organo_directorio.gobierno_regional`.
- [ ] `services.crear_adenda`: hereda `gobierno_regional` del origen.
- [ ] `services.crear_convenio`/`actualizar_convenio`: persisten `gobierno_regional`; regla por tipo aplicada (o nullable libre, según decisión confirmada).
- [ ] `_validar_composicion_partes`/`sincronizar_partes` verificados (sin dependencia de `organo_directorio.gobierno_regional`).
- [ ] Grep global: cero referencias vivas a `OrganDirectory.gobierno_regional` (excluyendo migraciones históricas).
- [ ] Docs sincronizadas: `db_schema_modulo_01_convenios.md`, `db_schema_er_global.md`, `CLAUDE.md`.
- [ ] Idioma: tablas/columnas/help_text/mensajes de error en español; código en inglés.

---

## 10. Nota explícita — Data migration del GORE existente (RN-GORE-6)

**Riesgo:** al borrar `organo_directorio.gobierno_regional_id` se pierde la única fuente del GORE de los
órganos regionales. Si existen convenios cuyos órganos tenían GORE, ese dato desaparece salvo que se copie
al nuevo `convenio.gobierno_regional_id` **antes** del `RemoveField`.

**Instrucción a `implement`:**

1. Antes de escribir la RunPython, **verificar el conteo** de `organo_directorio` con `gobierno_regional_id`
   no nulo y el conteo de `convenio` que referencian esos órganos. Reportar ambos al usuario.
2. Si hay datos: la RunPython (paso 2 de la migración) es **obligatoria** — copiar
   `organo_directorio.gobierno_regional_id` → `convenio.gobierno_regional_id` para cada convenio afectado,
   usando modelos históricos (`apps.get_model`). Ejecutarla **antes** de `RemoveField`.
3. Si no hay datos: dejar la RunPython como `noop` **documentado** ("sin datos que migrar al momento del
   refactor"), pero mantener el paso para constancia y reversibilidad.
4. **No** ejecutar `migrate` (lo corre el usuario). Solo `makemigrations` + `makemigrations --check`.

---

## Archivos que tocará `implement`

- `apps/convenios/models.py`
- `apps/convenios/migrations/0041_*.py` (nuevo)
- `apps/convenios/views.py`
- `apps/convenios/serializers.py`
- `apps/convenios/pdf.py`
- `apps/convenios/services.py`
- `docs/db_schema_modulo_01_convenios.md`
- `docs/db_schema_er_global.md`
- `CLAUDE.md`
