# Spec — Refactor de la PK de `Ipress`: `codigo_renipress` como PK texto (8 chars)

## Resumen del módulo

Refactor transversal que convierte `Ipress.codigo_renipress`
(`apps/convenios/models.py:391`, hoy `CharField(max_length=20, unique=True)`, requerido) en la
**PK de tipo texto de 8 caracteres** (`CharField(max_length=8, primary_key=True)`), eliminando el
`id` autoincremental implícito de la tabla `ipress`.

Impacto directo:

- **7 FK** en 3 apps que referencian `Ipress` pasan de columna `integer` → `varchar(8)`.
- El mecanismo genérico de **alcance institucional** (`UserEntityProfile.id_objeto`,
  `GenericForeignKey`) y de **auditoría** (`AuditLog.id_objeto`) — hoy `PositiveBigIntegerField` —
  pasan a `CharField(max_length=64)`, y **todas las comparaciones de alcance se normalizan a `str`**.
- Código de aplicación (permisos ×2, selectores ×2, views ×1, serializers) y documentación.

Entidades cubiertas: `Ipress` (dueña de la PK), `ClinicalFieldRegistration`,
`ClinicalFieldAllocation` (convenios), `Internship`, `Rotation`, `Tutor` (internados),
`TeachingActivity` (actividades), `UserEntityProfile` y `AuditLog` (GFK genérico).

Metodología SDD. Migración base actual: `0045_executingunit_nueva_estructura` (convenios). Nuevas
migraciones desde `0046`. El patrón multi-paso transitorio cross-app ya se ejecutó para el refactor
de `ExecutingUnit` en `0044`/`0045` — este spec lo imita.

> **Decisiones ya tomadas por el usuario (NO reabrir):** (1) `codigo_renipress` es PK texto de 8
> caracteres; (2) el alcance IPRESS se conserva — `UserEntityProfile.id_objeto` → `CharField(64)` y
> todas las comparaciones se normalizan a `str`; (3) `AuditLog.id_objeto` → `CharField(64)` también.

---

## Confirmación de GFK que apuntan a `Ipress`

Regla rectora del análisis: un GFK apunta a `Ipress` **solo si** algún flujo escribe su
`tipo_contenido`/`id_objeto` con el `ContentType` de `Ipress`.

| GFK (`id_objeto`) | Modelo / tabla | ¿Apunta a `Ipress`? | Acción en este refactor |
|---|---|---|---|
| `UserEntityProfile.id_objeto` | `perfil_usuario_entidad` (`models.py:771`) | **Sí** — `Ipress` está en `ASSIGNABLE_PROFILE_MODELS` (`apps/common/serializers.py:378`); permisos y selectores comparan `(ct_ip, ipress_id) in refs` | **Cambia** a `CharField(64)` + backfill + normalización a `str` |
| `AuditLog.id_objeto` | `bitacora_auditoria` (`models.py:1288`) | **Sí** — `services.autorizar_sede_docente` (`services.py:753`) y el CRUD de IPRESS auditan `Ipress` | **Cambia** a `CharField(64)` + backfill |
| `Document.id_objeto` | `documento_adjunto` (`models.py:1251`) | **No** — el logo de IPRESS es `ImageField` (R2), no `documento_adjunto`; los anexos (`AnnexAttachmentMixin`) actúan sobre `CONVENIO`, `CAMPO_CLINICO`, `INTERNO`, `REPRESENTANTE`, nunca sobre `Ipress`. | **Sin cambio** (queda constancia explícita) |
| `ConventionParticipant.id_objeto` | `participante_convenio` (`models.py:906`) | **No** — participantes/partes firmantes son MINSA/Universidad/GORE/Unidad Ejecutora/Facultad (`PARTY_ROLE`), no IPRESS | **Sin cambio** |
| `Firma.firmante_id_objeto` | `firma` (`models.py:1198`) | **No** — el firmante es una autoridad institucional, no una sede IPRESS | **Sin cambio** |
| `Convention.solicitante_id_objeto` | `convenio` (`models.py:841`) | **No** — el solicitante es GERESA/DIRESA/DIRIS/Universidad (RN-1), nunca IPRESS | **Sin cambio** |

**Conclusión:** solo `UserEntityProfile` y `AuditLog` requieren cambio de tipo de `id_objeto`. Los
otros 4 GFK **no se tocan** y conservan `PositiveBigIntegerField`. El implement debe dejar constancia
de esta verificación en el docstring de la migración `0046`.

> **Nota de coherencia de tipo:** al dejar `Document`, `ConventionParticipant`, `Firma` y
> `Convention.solicitante` con `id_objeto` entero, ninguno de ellos podrá referenciar `Ipress` a
> futuro (su PK ya no es entera). Esto es correcto por diseño — ninguno lo hace hoy ni debe hacerlo.

---

## Fase 0 — Verificación de datos (T-01, obligatoria ANTES de escribir migraciones)

**T-01 — Auditar los datos de `ipress` antes de tocar el schema.**

Con el venv activado (`.venv\Scripts\Activate.ps1`), abrir `python manage.py shell` y ejecutar:

1. **Longitud y no-vacíos:**
   `Ipress.objects.exclude(codigo_renipress__regex=r'^.{1,8}$').values_list('pk','codigo_renipress')`
   — debe devolver **vacío**. Cualquier fila con `codigo_renipress` de más de 8 chars, vacío o nulo
   es bloqueante.
2. **Unicidad** (ya garantizada por `unique=True`, revalidar):
   contar `Ipress.objects.count()` vs. `Ipress.objects.values('codigo_renipress').distinct().count()`
   — deben coincidir.
3. **Filas GFK a remapear:** resolver `ct_ipress = ContentType.objects.get_for_model(Ipress).id` y
   contar `UserEntityProfile.objects.filter(tipo_contenido_id=ct_ipress).count()` y
   `AuditLog.objects.filter(tipo_contenido_id=ct_ipress).count()`.

**Criterios de aceptación T-01:**
- Si alguna fila tiene `codigo_renipress` > 8 chars, vacío o nulo → **DETENER y escalar al usuario**.
  **No truncar** ni auto-corregir códigos (el usuario definió 8; truncar altera el identificador).
- El resultado real de las 3 consultas (conteos incluidos) se documenta en el **docstring de la
  migración `0046`**, como en `0044` (`ExecutingUnit.objects.count() → 0 filas`).
- En dev el resultado esperado es 0 filas en `ipress`, `perfil_usuario_entidad` y `AuditLog` con
  `tipo_contenido=Ipress`, pero los `RunPython` deben quedar correctos para prod.

---

## Fase A — Modelos (`apps/*/models.py`)

**T-02 — `Ipress.codigo_renipress` → PK texto de 8 chars** (`apps/convenios/models.py:391`).
- `codigo_renipress = models.CharField("código RENIPRESS", max_length=8, primary_key=True, help_text=...)`.
- Quitar `unique=True` explícito (implícito por PK). Se elimina el `id` AutoField implícito.
- Ajustar el `help_text` a algo como `"Código RENIPRESS de 8 caracteres (clave primaria)"`.
- **Criterio:** el modelo no declara ningún `id`; `Ipress._meta.pk.name == "codigo_renipress"`.

**T-03 — Las 7 FK a `Ipress` referencian el PK por defecto** (sin `to_field` explícito, ya que
`codigo_renipress` es la PK; Django omite `to_field` del deconstruct cuando apunta a la PK destino).
`db_column` se conserva → **solo cambia el tipo de columna a `varchar(8)`**. FKs:

| App / archivo | Campo | `db_column` | `on_delete` |
|---|---|---|---|
| convenios `models.py:1066` | `ClinicalFieldRegistration.ipress` | `ipress_id` | PROTECT |
| convenios `models.py:1131` | `ClinicalFieldAllocation.ipress` | `ipress_id` | PROTECT |
| internados `models.py:239` | `Internship.ipress` | `ipress_id` | PROTECT |
| internados `models.py:329` | `Rotation.ipress_origen` | `ipress_origen_id` | PROTECT |
| internados `models.py:332` | `Rotation.ipress_destino` | `ipress_destino_id` | PROTECT |
| internados `models.py:178` | `Tutor.ipress` | `ipress_id` | SET_NULL (null) |
| actividades `models.py:41` | `TeachingActivity.ipress` | `ipress_id` | PROTECT |

- **Criterio:** ninguna de las 7 declaraciones agrega `to_field`; el `related_name` y `on_delete`
  actuales se conservan sin cambios.

**T-04 — `id_objeto` genérico a `CharField(64)`.**
- `UserEntityProfile.id_objeto` (`models.py:771`) → `models.CharField("id objeto", max_length=64, help_text="Identificador de la entidad asociada")`.
- `AuditLog.id_objeto` (`models.py:1288`) → `models.CharField("id objeto", max_length=64, help_text="Registro afectado")`.
- **NO tocar** `Document.id_objeto`, `ConventionParticipant.id_objeto`, `Firma.firmante_id_objeto`
  ni `Convention.solicitante_id_objeto` (siguen `PositiveBigIntegerField`, ver tabla de GFK).
- **Criterio:** el `unique_together` de `UserEntityProfile` (`(usuario, tipo_contenido, id_objeto, grupo)`)
  se conserva; `max_length=64` cubre PKs enteras casteadas a `str` y códigos texto de 8.

---

## Fase B — Migraciones (patrón multi-paso, cross-app, estilo `0044`/`0045`)

**Regla rectora:** ninguna FK entera puede quedar apuntando al `id` de `Ipress` cuando este se
elimine; cada operación de campo vive en la migración de la app dueña del modelo; las FK de
`internados`/`actividades` se repuntan **antes** de que `convenios` elimine el `id` de `Ipress`.

Secuencia de 6 migraciones (números guía; el implement puede reordenar operaciones **dentro** de una
migración pero debe respetar la regla rectora y las `dependencies` cross-app):

### T-05 — `convenios/0046` — verificación + columnas transitorias propias + swap de GFK

Depende de `("convenios", "0045_executingunit_nueva_estructura")`. Docstring: incluir el resultado
de Fase 0 (T-01) y la confirmación de GFK (solo `UserEntityProfile`/`AuditLog`).

Operaciones, en orden:
1. `AlterField Ipress.codigo_renipress` → `max_length=8`, aún **no** PK (sigue `unique=True`,
   `CharField`). Precondición: Fase 0 confirmó `≤ 8` chars.
2. `AddField ClinicalFieldRegistration.ipress_codigo` — `CharField(max_length=8, null=True, blank=True,
   db_column="ipress_codigo")` (transitorio, `db_column` distinto para no colisionar con `ipress_id`).
3. `AddField ClinicalFieldAllocation.ipress_codigo` — idem, `db_column="ipress_codigo_asig"` (o
   cualquier `db_column` no usado en esa tabla).
4. `RunPython backfill_ipress_codigo_convenios` (reverse `noop`) — para cada fila de ambos modelos con
   `ipress_id` no nulo, copiar `Ipress.objects.get(pk=ipress_id).codigo_renipress` en `ipress_codigo`.
   Con FK PROTECT no nula en ambos modelos, todas las filas tienen `ipress_id`; si falta el `Ipress`
   destino → `RuntimeError` (integridad rota), como en `0044`.
5. `RunPython remapear_gfk_ipress` (reverse `noop`) — remapea `id_objeto` **antes** del `AlterField`:
   resolver `ct_ipress = ContentType.objects.get_for_model(Ipress).id`; para cada
   `UserEntityProfile` y `AuditLog` con `tipo_contenido_id == ct_ipress`, tomar el `id_objeto`
   entero actual → `Ipress.objects.get(pk=<entero>).codigo_renipress` → guardar en una **columna
   transitoria** o directamente tras el `AlterField`. **Enfoque recomendado (evita coerción SQLite):**
   hacer primero el `AlterField id_objeto → CharField` (paso 6) y luego el `RunPython` que sobre-escribe
   `id_objeto` de las filas Ipress con el código correcto; para las filas **no-Ipress** el
   `AlterField` casteará el entero a su representación `str` automáticamente. Documentar en el
   docstring que en dev es noop (0 filas). *Ordenar 6 antes de 5 si se adopta este enfoque.*
6. `AlterField UserEntityProfile.id_objeto` → `CharField(max_length=64)`.
7. `AlterField AuditLog.id_objeto` → `CharField(max_length=64)`.

> **Nota de orden 5/6:** el `RunPython` de remapeo debe leer el mapa `id_entero → codigo_renipress`
> **mientras `Ipress` todavía tiene su `id` entero** (paso 9 lo elimina en `0049`). Como `0046` no
> elimina el `id`, el `RunPython` puede ejecutarse en `0046` tras el `AlterField` sin problema.

### T-06 — `internados/0047` — columnas transitorias + backfill

Depende de `[("internados", "<última de internados>"), ("convenios", "0046_...")]`.
1. `AddField Internship.ipress_codigo` — `CharField(8, null=True, db_column="ipress_codigo")`.
2. `AddField Rotation.ipress_origen_codigo` — `CharField(8, null=True, db_column="ipress_origen_codigo")`.
3. `AddField Rotation.ipress_destino_codigo` — `CharField(8, null=True, db_column="ipress_destino_codigo")`.
4. `AddField Tutor.ipress_codigo` — `CharField(8, null=True, db_column="tutor_ipress_codigo")` (`Tutor.ipress` es SET_NULL null → el backfill respeta nulos).
5. `RunPython backfill_ipress_codigo_internados` (reverse `noop`) — copiar `codigo_renipress` desde el
   `Ipress` referenciado por cada FK entera no nula; nulos quedan nulos (`Tutor.ipress`).

### T-07 — `actividades/0048` — columna transitoria + backfill

Depende de `[("actividades", "<última de actividades>"), ("convenios", "0046_...")]`.
1. `AddField TeachingActivity.ipress_codigo` — `CharField(8, null=True, db_column="ipress_codigo")`.
2. `RunPython backfill_ipress_codigo_actividades` (reverse `noop`) — copiar `codigo_renipress`.

### T-08 — `convenios/0049` — promoción del PK + FKs propias reales + drop `id`

Depende de `("convenios", "0046_...")`. **Esta es la migración crítica.**
1. `AlterField Ipress.codigo_renipress` → `CharField(max_length=8, primary_key=True, serialize=False)`.
   (Django recrea la tabla `ipress` en SQLite; el `id` AutoField desaparece del estado del modelo.)
2. `RemoveField Ipress.id` — eliminar explícitamente el AutoField PK (como C1 en `0045`). *Si el
   `AlterField primary_key=True` ya lo elimina en el estado, verificar con `makemigrations --check`
   que no queda un `id` huérfano; incluir el `RemoveField` si Django lo pide.*
3. `AlterField ClinicalFieldRegistration.ipress_codigo` → FK real a `convenios.Ipress`
   (`on_delete=PROTECT`, `db_column="ipress_codigo"`, sin `to_field`).
4. `AlterField ClinicalFieldAllocation.ipress_codigo` → FK real a `convenios.Ipress` (PROTECT).
5. `RemoveField ClinicalFieldRegistration.ipress` (la FK entera `ipress_id`).
6. `RemoveField ClinicalFieldAllocation.ipress`.
7. `RenameField ClinicalFieldRegistration.ipress_codigo → ipress`.
8. `RenameField ClinicalFieldAllocation.ipress_codigo → ipress`.
9. `AlterField` final de ambas `ipress` → estado canónico del modelo (`db_column="ipress_id"`,
   PROTECT, sin `to_field`; ver D1/D2 de `0045`). Esto renombra la columna transitoria al
   `db_column="ipress_id"` canónico.
   - **Precondición de unicidad:** el `unique_together` de `ClinicalFieldRegistration`
     (`(convenio, ipress, carrera_profesional, especialidad)`, `models.py:1112`) se preserva
     automáticamente porque el campo `ipress` conserva su nombre lógico.

### T-09 — `internados/0050` — FKs reales + drop enteras

Depende de `[("internados", "0047_..."), ("convenios", "0049_...")]`.
1. `AlterField` de `Internship.ipress_codigo`, `Rotation.ipress_origen_codigo`,
   `Rotation.ipress_destino_codigo`, `Tutor.ipress_codigo` → FK real a `convenios.Ipress`
   (PROTECT / SET_NULL null para `Tutor`).
2. `RemoveField` de las 4 FK enteras (`Internship.ipress`, `Rotation.ipress_origen`,
   `Rotation.ipress_destino`, `Tutor.ipress`).
3. `RenameField` de las 4 transitorias a su nombre canónico (`ipress`, `ipress_origen`,
   `ipress_destino`, `ipress`).
4. `AlterField` final de las 4 → `db_column` canónico (`ipress_id`, `ipress_origen_id`,
   `ipress_destino_id`, `ipress_id`), `related_name` y `on_delete` originales.

### T-10 — `actividades/0051` — FK real + drop entera

Depende de `[("actividades", "0048_..."), ("convenios", "0049_...")]`.
1. `AlterField TeachingActivity.ipress_codigo` → FK real a `convenios.Ipress` (PROTECT).
2. `RemoveField TeachingActivity.ipress`.
3. `RenameField ipress_codigo → ipress`.
4. `AlterField` final → `db_column="ipress_id"`, `related_name="actividades"`, PROTECT.

**Criterios de aceptación de la Fase B:**
- `python manage.py makemigrations --check` limpio tras aplicar (sin migraciones pendientes).
- `python manage.py migrate` aplica `0046`→`0051` en secuencia sin error en SQLite (ejecutado por el
  usuario, no por el agente).
- Cada `RunPython` tiene `reverse_code=migrations.RunPython.noop` y `RuntimeError` explícito en
  español ante integridad rota (patrón `0044`).
- Ninguna FK entera a `Ipress` sobrevive a `convenios/0049`.
- Los `db_column` finales de las 7 FK son idénticos a los de hoy (`ipress_id`, `ipress_origen_id`,
  `ipress_destino_id`).

---

## Fase C — Código de aplicación

**T-11 — `apps/common/selectors.py`: alcance como `str`.**
- `entidades_del_usuario` — anotar retorno `list[tuple[int, str]]` (era `tuple[int, int]`);
  castear el segundo elemento a `str`: `[(tc, str(oid)) for tc, oid in perfiles...values_list(...)]`.
  (Tras el cambio de `id_objeto` a `CharField`, el ORM ya devuelve `str`; el cast explícito lo blinda.)
- `usuario_pertenece_a_entidad(usuario, tipo_contenido_id: int, id_objeto: str) -> bool` — cambiar la
  firma a `id_objeto: str` y filtrar con `id_objeto=str(id_objeto)`.
- **Criterio:** ambas funciones devuelven/comparan `id_objeto` como `str`.

**T-12 — `apps/internados/permissions.py:62-66` (`InternshipScope`): normalizar a `str`.**
- Las 3 ramas comparan `refs` (ya `str` por T-11) contra `internado.estudiante.universidad_id`,
  `internado.ipress_id`, `internado.estudiante_id`. Envolver **cada** valor en `str(...)`:
  `(ct_uni, str(internado.estudiante.universidad_id)) in refs`,
  `(ct_ip, str(internado.ipress_id)) in refs`,
  `(ct_student, str(internado.estudiante_id)) in refs`.
- **Criterio:** ambos lados de las 3 comparaciones de tupla son `str`; `internado.ipress_id` sigue
  siendo el código RENIPRESS (string) tras el refactor.

**T-13 — `apps/actividades/permissions.py:24` (`ActivityScope`): normalizar a `str`.**
- `(ct_uni, str(obj.estudiante.universidad_id)) in refs or (ct_ip, str(obj.ipress_id)) in refs`.

**T-14 — `apps/actividades/views.py:61` (`_verificar_ambito`): `.id`→`.pk` + `str`.**
- Reemplazar `usuario_pertenece_a_entidad(user, ct_ip, ipress.id)` por
  `usuario_pertenece_a_entidad(user, ct_ip, str(ipress.pk))` (el atributo `.id` desaparece al no
  existir el AutoField; `.pk` resuelve a `codigo_renipress`).
- La rama de universidad: `usuario_pertenece_a_entidad(user, ct_uni, str(estudiante.universidad_id))`.

**T-15 — `apps/actividades/selectors.py:23-31` y `apps/internados/selectors.py:63-74`: ramas de tuplas
con `str`.**
- En ambos, las listas `universidades`/`propios` provienen de `refs` (`str` por T-11) mientras la
  columna en BD es entera → castear en el filtro: `Q(estudiante__universidad_id__in=[int(x) for x in universidades])`
  y `Q(estudiante_id__in=[int(x) for x in propios])`. La rama `sedes` (`ipress_id__in=sedes`) queda
  **sin cast** porque `ipress_id` ahora es texto y `sedes` ya es `str`.
- **Criterio:** `universidades`/`propios` (comparan contra columnas enteras) se castean a `int` en el
  filtro; `sedes` (compara contra `ipress_id` texto) permanece `str`. Verificar que no queden
  comparaciones de tipos mezclados.

**T-16 — `apps/common/serializers.py`: `id_objeto`/`ids` como `str`.**
- `UserEntityProfileSerializer.id_objeto` (`serializers.py:50`): `IntegerField()` → `CharField()`
  (expone el `id_objeto` como string; para IPRESS es el código, para el resto el pk casteado).
- `UserEntityProfileWriteSerializer.ids` (`serializers.py:411`): `child=serializers.IntegerField()`
  → `child=serializers.CharField()` (acepta códigos string y pks numéricos como texto).
- `UserEntityProfileWriteSerializer.validate` (`serializers.py:438-461`): el filtro
  `modelo.objects.filter(pk__in=ids)` sigue funcionando (para modelos de PK entera Django coacciona
  el string numérico; para `Ipress` compara contra `codigo_renipress`). Verificar que el listado de
  `faltantes` compare por `str(pk)`.
- `UserEntityProfileWriteReadSerializer` (`serializers.py:464`) hereda la exposición de
  `id_objeto` de `UserEntityProfileSerializer` → automáticamente string; no requiere cambio.
- `AssignableEntityTypeView`/`AssignableEntityTypeSerializer` (`serializers.py:479`): **sin cambio
  funcional** (operan sobre `ContentType`, no sobre ids). `ASSIGNABLE_PROFILE_MODELS` conserva `Ipress`.
- **Criterio:** un POST de perfil con `ids: ["00012345"]` sobre `tipo_entidad: "ipress"` crea el
  `UserEntityProfile` con `id_objeto = "00012345"`; el read expone `id_objeto` como string.

**T-17 — `apps/convenios/views.py` (`IpressViewSet` / `_IpressSerializer`): PK string.**
- Verificar que el auto-serializer opere con `codigo_renipress` como PK: el alta debe **exigir**
  `codigo_renipress` (ya no hay `id` autogenerado); el detalle `/api/v1/ipress/<codigo>/` resuelve por
  string. `search_fields=["nombre", "codigo_renipress"]` (`views.py:605`) y los `*_detalle` no cambian.
- El `_IpressSerializer.validate` (coherencia microred↔ámbito) no toca la PK → sin cambio.
- `services.autorizar_sede_docente` (`services.py:753`): `registrar_auditoria(usuario, "ACTUALIZAR",
  ipress, ...)` escribe `AuditLog.id_objeto = str(ipress.pk)` (el helper `registrar_auditoria` toma
  el pk del objeto). Verificar que `registrar_auditoria` castee/acepte el pk string sin error tras
  T-04 (si construye `id_objeto=obj.pk`, con `CharField` ya acepta string).
- **Criterio:** CRUD de IPRESS funciona con PK string; `autorizar-sede-docente` audita sin error.

**T-18 — Filtros `ipress` (django-filter): sin cambio de declaración.**
- `apps/convenios/filters.py:39,49-51`, `apps/internados/filters.py:18,32-33`,
  `apps/actividades/filters.py:17` — los filtros `exact` sobre `ipress`/`ipress_origen`/
  `ipress_destino`/`campo_clinico_ipress` aceptan el string sin cambio; django-filter deriva el tipo
  del campo del modelo. **Verificar** (no editar salvo que `makemigrations`/`check` lo requiera).
- `apps/convenios/pdf.py:141` usa `cc.ipress.nombre` → **sin cambio**.

---

## Fase D — Documentación

**T-19 — `docs/db_schema_modulo_01_convenios.md`:** tabla `ipress` con PK `codigo_renipress`
`varchar(8)` y **sin** columna `id`; nota de tipo `varchar(8)` en `campo_clinico_ipress.ipress_id`
y `campo_clinico_ipress_universidad.ipress_id`; `perfil_usuario_entidad.id_objeto` y
`bitacora_auditoria.id_objeto` como `varchar(64)`.

**T-20 — `docs/db_schema_modulo_02_internados.md`:** `interno.ipress_id`, `rotacion.ipress_origen_id`,
`rotacion.ipress_destino_id`, `tutor.ipress_id` ahora `varchar(8)`.

**T-21 — `docs/db_schema_modulo_03_actividades.md`:** `actividad.ipress_id` ahora `varchar(8)`.

**T-22 — `docs/arquitectura_desarrollo.md`** (§alcance por entidad): documentar `id_objeto` como texto
y la normalización a `str` en permisos/selectores/serializers.

**T-23 — `CLAUDE.md`:** nota del PK textual de `ipress` (`codigo_renipress` `varchar(8)`, PK) y del
`id_objeto` genérico (`UserEntityProfile`/`AuditLog`) como texto con comparaciones normalizadas a `str`.

**Criterio Fase D:** los `.md` de schema quedan sincronizados con los modelos en el mismo cambio
(exigencia de `CLAUDE.md`).

---

## Breaking changes de API (informar al frontend)

| Endpoint / contrato | Antes | Después |
|---|---|---|
| `GET/PATCH/DELETE /api/v1/ipress/<pk>/` | `<pk>` es `int` | `<pk>` es **string de 8 chars** (código RENIPRESS) |
| `GET /api/v1/ipress/` (item) | expone `id` (int) autogenerado | **no** hay `id`; el identificador es `codigo_renipress` |
| `POST /api/v1/ipress/` | `codigo_renipress` opcional-único, `id` autogenerado | `codigo_renipress` **requerido** (es la PK; lo provee el cliente) |
| `?ipress=`, `?ipress_origen=`, `?ipress_destino=`, `?campo_clinico_ipress=` (convenios/internados/actividades) | valor `int` | valor **string de 8 chars** |
| FKs `ipress` en payloads de escritura (`clinical-field-registrations`, `clinical-field-allocations`, `interns`, `rotations`, `tutors`, `teaching-activities`) | id entero | **código RENIPRESS string** |
| `POST .../user-entity-profiles` (`ids`) y lectura (`id_objeto`) para `tipo_entidad: "ipress"` | int | **string** (código); para el resto de entidades, el pk casteado a `str` |

---

## Criterios de aceptación (globales)

1. **T-01** confirma datos aptos (`codigo_renipress` ≤ 8 chars, no vacío/nulo, único) y el resultado
   queda en el docstring de `0046`.
2. `python manage.py makemigrations --check` limpio; `migrate` aplica `0046`→`0051` sin error en
   SQLite; `python manage.py check` OK; el schema OpenAPI se genera sin errores. (Ejecución a cargo
   del usuario — el agente **no** corre `migrate`/`runserver`/tests.)
3. `Ipress._meta.pk.name == "codigo_renipress"` y la tabla `ipress` no tiene columna `id`.
4. Las 7 columnas FK a `Ipress` son `varchar(8)` con sus `db_column` originales; ninguna FK entera a
   `Ipress` sobrevive.
5. `UserEntityProfile.id_objeto` y `AuditLog.id_objeto` son `varchar(64)`; los otros 4 GFK quedan
   `PositiveBigIntegerField` sin cambio.
6. Alcance IPRESS end-to-end: crear `UserEntityProfile` con `ids=["<codigo>"]` sobre `ipress`; el
   usuario ve solo internos/actividades de esa sede (comparación por `str`).
7. `autorizar-sede-docente` escribe `AuditLog.id_objeto` como string sin error.
8. Los 4 `.md` de docs + `CLAUDE.md` quedan sincronizados con los modelos.
9. No se introducen comparaciones de tipos mezclados (`int` vs `str`) en permisos/selectores.

---

## Riesgos / notas para el implement

- **Cross-app PK swap:** ordenamiento estricto de `dependencies` entre 3 apps. `internados`/
  `actividades` repuntan sus FK **solo después** de `convenios/0049`. Es la primera vez que un PK
  textual alimenta el GFK genérico.
- **`AuditLog.id_objeto` como texto:** todas las filas futuras guardan el pk casteado a `str` (enteros
  como `"5"`); las consultas por `(tipo_contenido, id_objeto)` deben usar `str`. Bajo riesgo (log).
- **Dev sin datos:** 0 filas esperadas en `ipress`, `perfil_usuario_entidad` y `AuditLog` con
  `tipo_contenido=Ipress` → los `RunPython` son noop efectivos pero deben quedar **correctos para
  prod** (backfill real + `RuntimeError` ante integridad rota).
- **SQLite:** Django recrea la tabla automáticamente en `AlterField primary_key=True`/`RemoveField`/
  `RenameField`; imitar exactamente el patrón de `0045` (pasos A→B→C→D).
- **Confirmar antes de aplicar** que los códigos RENIPRESS reales caben en 8 chars (Fase 0).
- **No incluir** tareas de testing automatizado (fuera de alcance MVP).
