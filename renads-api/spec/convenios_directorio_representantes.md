# Spec — Reorganización de directorio de órganos, representantes y gestión documental

> **Fuente de verdad:** plan aprobado «Reorganización de directorio de órganos, representantes y gestión documental»
> (`C:\Users\Henry\.claude\plans\silly-drifting-squirrel.md`) + schemas `docs/db_schema_modulo_01_convenios.md`,
> `docs/db_schema_modulo_02_internados.md`, `docs/db_schema_er_global.md`.
>
> **Alcance:** módulos `apps/convenios` y `apps/internados`. **BD de dev recreable limpia**: las migraciones
> dropean/recrean tablas y resiembran catálogos, **sin transferencia fila por fila** de datos reales.
>
> **Convenciones (CLAUDE.md):** clases/campos/endpoints en inglés; `db_table`, columnas, `verbose_name`,
> `help_text`, docstrings y mensajes de error en español. Toda escritura crítica con auditoría
> (`registrar_auditoria`) dentro de `transaction.atomic()`.
>
> **Fuera de alcance:** frontend (`renads-frontend`) — se migra en tarea aparte. No incluir tests automatizados.

## Resumen del módulo

Se consolidan tablas dispersas de órganos, representantes/autoridades y documentos aprovechando el FK
discriminador `organo` (→ `Organ`) ya normalizado. Cuatro bloques de cambio:

1. **`cargo_ejecutivo` (`ExecutivePosition`)** deja de heredar `Catalog` y gana FK `organo` (unicidad por órgano).
2. **`organo_regional` + `organo_minsa` → `organo_directorio` (`OrganDirectory`)**: directorio general standalone
   discriminado por `organo`. Se repuntan las FKs entrantes.
3. **`representante` + `autoridad_universidad` → `organo_representante` (`OrganRepresentative`)**: reemplaza la
   relación polimórfica (`GenericForeignKey`) por FK directo a `OrganDirectory`, con histórico de bajas.
4. **Gestión documental**: `documento → documento_adjunto`, `documentos_anexos → documento_anexo`, se fusiona
   `tipo_documento` dentro de `documento_anexo` (se elimina `DocumentType`).

**Entidades cubiertas:** `ExecutivePosition`, `OrganDirectory` (nueva), `OrganRepresentative` (nueva),
`OrganRepresentativeHistory` (nueva), `Document` (renombrada), `AnnexDocument` (renombrada). **Eliminadas:**
`RegionalOrgan`, `MinsaOrgan`, `Representative`, `UniversityAuthority`, `DocumentType`.

---

## Orden de ejecución (por dependencia)

Modelos → services → serializers → mixins → views → urls → migraciones → documentación. Las tareas están
numeradas en ese orden. Los cambios de modelo (T1–T14) deben completarse antes de las migraciones (T30–T31)
porque `makemigrations` lee el estado final de los modelos.

---

## Bloque A — Modelos (`apps/convenios/models.py`)

### T1 — `ExecutivePosition`: añadir `organo`, dejar de heredar `Catalog`

**Archivo:** `apps/convenios/models.py` (clase `ExecutivePosition`, líneas ~208-211).
**Acción:** reemplazar la definición actual (`class ExecutivePosition(Catalog)`) por un modelo que **no** hereda
`Catalog`, con estos campos exactos:

- `organo` — `ForeignKey("Organ", on_delete=models.PROTECT, db_column="organo_id", related_name="cargos", verbose_name="órgano", help_text="Categoría del órgano al que pertenece el cargo")`.
- `codigo` — `CharField("código", max_length=50, help_text="Código del cargo (único dentro del órgano)")` (sin `unique=True` global).
- `nombre` — `CharField("nombre", max_length=255, help_text="Nombre del cargo")`.
- `activo` — `BooleanField("activo", default=True, help_text="Indica si está activo")`.
- `Meta`: `db_table = "cargo_ejecutivo"`, `verbose_name = "cargo ejecutivo"`, `unique_together = (("organo", "codigo"),)`, `ordering = ["organo", "codigo"]`.
- `__str__` → `self.nombre`.

**Referencia de patrón:** `OrganType` (líneas 178-205) — misma estructura FK + `codigo`/`nombre`/`activo` + `unique_together`.
**Criterio de aceptación:** `ExecutivePosition.objects.filter(organo__nombre="Universidad")` es válido; `codigo` ya no es unique global; la clase no aparece en la lista de subclases de `Catalog`.
**Riesgo:** `RepresentativeSerializer` y `_catalog_viewset(m.ExecutivePosition)` referencian este modelo — se resuelven en T18 y T23.

### T2 — Crear `OrganDirectory` (tabla `organo_directorio`)

**Archivo:** `apps/convenios/models.py`. Ubicar el modelo tras `RegionalGovernment` (antes de `ExecutingUnit`), ya que `ExecutingUnit`/`Convention` lo referenciarán.
**Acción:** crear `class OrganDirectory(models.Model)` con estos campos exactos:

- `organo` — `FK → "Organ"`, `on_delete=PROTECT`, `db_column="organo_id"`, `related_name="directorios"`, `verbose_name="órgano"`, `help_text="Categoría del órgano (discriminador)"`.
- `tipo_organo` — `FK → OrganType`, `on_delete=PROTECT`, `db_column="tipo_organo_id"`, `null=True, blank=True`, `related_name="+"`, `help_text="Tipo de órgano (GERESA/DIRESA/DIGEP…); nulo para órganos sin tipo"`.
- `gobierno_regional` — `FK → RegionalGovernment`, `on_delete=PROTECT`, `db_column="gobierno_regional_id"`, `null=True, blank=True`, `related_name="organos_directorio"`, `help_text="GORE (solo órganos regionales)"`.
- `nombre` — `CharField("nombre", max_length=255, help_text="Nombre del órgano")`.
- `siglas` — `CharField("siglas", max_length=50, blank=True, help_text="Siglas")`.
- `direccion` — `CharField("dirección", max_length=500, blank=True, help_text="Dirección")`.
- `numero_ruc` — `CharField("número de RUC", max_length=11, blank=True, help_text="RUC (11 dígitos; texto para conservar ceros a la izquierda)")`. *(Sin `RegexValidator` obligatorio; opcional replicar el de `Ipress` si se decide — dejar sin validator para no bloquear blanks.)*
- `correo` — `EmailField("correo", blank=True, help_text="Correo institucional")`.
- `telefono_institucional` — `CharField("teléfono institucional", max_length=30, blank=True, help_text="Teléfono institucional")`.
- `ubigeo` — `FK → Ubigeo`, `on_delete=PROTECT`, `db_column="ubigeo_id"`, `null=True, blank=True`, `related_name="+"`, `help_text="Ubicación geográfica (UBIGEO)"`.
- `referencia_logo` — `ImageField("logo", upload_to="organo_directorio/", max_length=500, null=True, blank=True, help_text="Logo institucional (imagen almacenada en el repositorio de medios)")`.
- `activo` — `BooleanField("activo", default=True)`.
- `Meta`: `db_table = "organo_directorio"`, `verbose_name = "órgano del directorio"`, `verbose_name_plural = "órganos del directorio"`.
- `__str__` → `self.nombre`.

**Referencia de patrón:** `RegionalOrgan` (líneas 287-314) + campos nuevos del plan (§Cambio 2).
**Criterio de aceptación:** modelo standalone (sin FK inverso desde `University`/`Ipress`/`Conapres`); tiene `referencia_logo` (habilita `LogoStorageMixin`).
**Riesgo:** `SOLICITANTE_MODELS` (views.py líneas 701-709) incluye `RegionalOrgan` y `MinsaOrgan` que se eliminan — sustituir por `OrganDirectory` en T27.

### T3 — Repuntar `ExecutingUnit.organo_regional → organo_directorio`

**Archivo:** `apps/convenios/models.py` (clase `ExecutingUnit`, líneas 317-321).
**Acción:** renombrar el campo `organo_regional` a `organo_directorio`:
`FK → OrganDirectory`, `on_delete=PROTECT`, `db_column="organo_directorio_id"`, `related_name="unidades_ejecutoras"`, `help_text="Órgano del directorio que la administra"`.
**Criterio de aceptación:** `ExecutingUnit.organo_directorio` referencia `OrganDirectory`; ya no existe `organo_regional`.
**Riesgo:** filtro `regional-organ` de `executing-units` (`ENTITY_VIEWSETS`, views.py línea 528: `filterset_fields=["organo_regional", ...]`) → actualizar a `organo_directorio` en T25.

### T4 — Repuntar `Convention.organo_regional → organo_directorio`

**Archivo:** `apps/convenios/models.py` (clase `Convention`, líneas 681-685).
**Acción:** renombrar el campo `organo_regional` a `organo_directorio`:
`FK → OrganDirectory`, `on_delete=PROTECT`, `db_column="organo_directorio_id"`, `related_name="convenios"`, `help_text="Órgano del directorio (GERESA/DIRESA/DIRIS) parte del convenio."`.
**Criterio de aceptación:** `Convention.organo_directorio` referencia `OrganDirectory`.
**Riesgo:** `ConventionFilter`, `ConventionWriteSerializer`/`ConventionReadSerializer`, selectors y services de convenios pueden referenciar `organo_regional`. **Verificar y actualizar** todos los usos (ver T28 «Barrido de referencias»). El campo es obligatorio (no null): la migración de repunte en BD limpia no requiere default.

### T5 — Repuntar `TechnicalEvaluation.organo_minsa → organo_directorio`

**Archivo:** `apps/convenios/models.py` (clase `TechnicalEvaluation`, líneas 781-784).
**Acción:** renombrar el campo `organo_minsa` a `organo_directorio`:
`FK → OrganDirectory`, `on_delete=models.SET_NULL`, `db_column="organo_directorio_id"`, `null=True, blank=True`, `related_name="+"`, `help_text="Unidad evaluadora (DIGEP) del directorio"`.
**Criterio de aceptación:** `TechnicalEvaluation.organo_directorio` referencia `OrganDirectory` con `SET_NULL`.
**Riesgo:** `TechnicalEvaluationSerializer` (fields `__all__`) y el service `registrar_evaluacion_tecnica` pueden nombrar `organo_minsa` — verificar en T28.

### T6 — Eliminar `RegionalOrgan` y `MinsaOrgan`

**Archivo:** `apps/convenios/models.py`.
**Acción:** eliminar por completo las clases `RegionalOrgan` (líneas 287-314) y `MinsaOrgan` (líneas 413-427).
**Criterio de aceptación:** ambas clases no son importables (`from apps.convenios.models import RegionalOrgan` falla).
**Riesgo:** cualquier import residual rompe el arranque. Barrido T28 obligatorio antes de correr `check`.

### T7 — Crear `OrganRepresentative` (tabla `organo_representante`)

**Archivo:** `apps/convenios/models.py`. Ubicar tras `OrganDirectory` o en la sección de representantes (reemplazando `Representative`, líneas 446-480).
**Acción:** crear `class OrganRepresentative(models.Model)` con estos campos exactos:

- `organo_directorio` — `FK → OrganDirectory`, `on_delete=PROTECT`, `db_column="organo_directorio_id"`, `related_name="representantes"`, `help_text="Órgano del directorio representado"`.
- `nombre` — `CharField("nombre", max_length=255, help_text="Nombre del representante")`.
- `tipo_documento_identidad` — `FK → "internados.IdentityDocumentType"`, `on_delete=PROTECT`, `db_column="tipo_documento_identidad_id"`, `related_name="+"`, `help_text="Tipo de documento de identidad"`.
- `numero_documento_identidad` — `CharField("número de documento de identidad", max_length=20, help_text="Número de documento de identidad")`.
- `sexo` — `CharField("sexo", max_length=1, choices=SEX, help_text="Sexo (M/F)")` — definir `SEX = [("M", "Masculino"), ("F", "Femenino")]` en `apps/convenios/models.py` (o reusar patrón de `internados.models.SEX`; **no** importar cruzado sólo por la constante, definirla localmente).
- `cargo_ejecutivo` — `FK → ExecutivePosition`, `on_delete=PROTECT`, `db_column="cargo_ejecutivo_id"`, `related_name="+"`, `help_text="Cargo ejecutivo"`.
- `fecha_inicio_designacion` — `DateField("fecha de inicio de designación", help_text="Inicio de la designación")`.
- `numero_resolucion_designacion` — `CharField("número de resolución de designación", max_length=100, blank=True, help_text="Número de resolución de designación")`.
- `fecha_inicio_facultades` — `DateField("fecha de inicio de facultades", null=True, blank=True, help_text="Otorgamiento de facultades")`.
- `activo` — `BooleanField("activo", default=True)`.
- `Meta`: `db_table = "organo_representante"`, `verbose_name = "representante de órgano"`, `verbose_name_plural = "representantes de órgano"`, `ordering = ["id"]`.
- `__str__` → `self.nombre`.

**Nota `IdentityDocumentType`:** vive en `apps.internados.models`. Referenciar por string `"internados.IdentityDocumentType"` (evita import circular convenios↔internados). El PDF de la resolución **no** es columna: se adjunta vía `annex-upload` (actor `REPRESENTANTE`).
**Criterio de aceptación:** FK directo a `OrganDirectory` (sin `GenericForeignKey`); reusa `IdentityDocumentType`; sexo con choices M/F.

### T8 — Crear `OrganRepresentativeHistory` (tabla `historial_organo_representante`)

**Archivo:** `apps/convenios/models.py`, tras `OrganRepresentative`.
**Acción:** crear `class OrganRepresentativeHistory(models.Model)` — snapshot de todos los campos de `OrganRepresentative` (denormalizado, para preservar el histórico aunque cambie el maestro) + baja:

- `representante` — `FK → OrganRepresentative`, `on_delete=PROTECT`, `db_column="representante_id"`, `related_name="historial"`, `help_text="Representante dado de baja"`.
- `organo_directorio` — `FK → OrganDirectory`, `on_delete=PROTECT`, `db_column="organo_directorio_id"`, `related_name="+"`.
- `nombre` — `CharField(max_length=255)`.
- `tipo_documento_identidad` — `FK → "internados.IdentityDocumentType"`, `on_delete=PROTECT`, `db_column="tipo_documento_identidad_id"`, `related_name="+"`.
- `numero_documento_identidad` — `CharField(max_length=20)`.
- `sexo` — `CharField(max_length=1, choices=SEX)`.
- `cargo_ejecutivo` — `FK → ExecutivePosition`, `on_delete=PROTECT`, `db_column="cargo_ejecutivo_id"`, `related_name="+"`.
- `fecha_inicio_designacion` — `DateField()`.
- `numero_resolucion_designacion` — `CharField(max_length=100, blank=True)`.
- `fecha_inicio_facultades` — `DateField(null=True, blank=True)`.
- `fecha_baja` — `DateField("fecha de baja", help_text="Fecha en que se dio de baja al representante")`.
- `motivo` — `CharField("motivo", max_length=255, blank=True, help_text="Motivo de la baja")`.
- `creado_en` — `DateTimeField("creado en", auto_now_add=True)`.
- `Meta`: `db_table = "historial_organo_representante"`, `verbose_name = "historial de representante de órgano"`, `verbose_name_plural = "historiales de representante de órgano"`, `ordering = ["-fecha_baja", "-id"]`.

**Todos los campos snapshot con sus `verbose_name`/`help_text` en español** (replicar los de `OrganRepresentative`).
**Criterio de aceptación:** al dar de baja un representante se puede reconstruir su estado completo desde la fila histórica.

### T9 — Eliminar `Representative` y `UniversityAuthority`

**Archivo:** `apps/convenios/models.py`.
**Acción:** eliminar las clases `Representative` (líneas 453-480, incluida la constante `REPRESENTATIVE_ORIGIN` líneas 446-450 si no se usa en otro sitio — **verificar** con grep) y `UniversityAuthority` (líneas 526-547).
**Criterio de aceptación:** ninguna de las dos clases es importable.
**Riesgo:** `RepresentativeSerializer`, `RepresentativeViewSet`, `ENTIDADES_REPRESENTABLES`, endpoint `university-authorities` — resueltos en T18, T24, T25.

### T10 — `Document`: quitar columnas y volver `documento_anexo` obligatorio; renombrar tabla

**Archivo:** `apps/convenios/models.py` (clase `Document`, líneas 995-1032).
**Acción:**

1. Eliminar el campo `nombre_archivo` (línea 1008).
2. Eliminar el campo `texto_extraido` (líneas 1009-1012).
3. Eliminar el campo `tipo_documento` (FK, líneas 996-998).
4. Modificar `documento_anexo` (líneas 1019-1023): pasar a **NOT NULL** → `FK → "internados.AnnexDocument"`, `on_delete=models.PROTECT`, `db_column="documento_anexo_id"`, `null=False, blank=False`, `related_name="documentos"`, `help_text="Anexo/tipo al que corresponde este documento (único discriminador de versionado)"`.
   > Nota: pasa de `SET_NULL` (por ser nullable) a `PROTECT` (obligatorio, no se quiere que borrar un `AnnexDocument` borre documentos). Confirmar `PROTECT` con el implementador; si el schema del módulo pide `SET_NULL`, mantener consistencia con `docs/`.
5. `Meta.db_table = "documento_adjunto"` (era `"documento"`). Mantener `verbose_name = "documento"` o cambiar a `"documento adjunto"` (usar `"documento adjunto"` para coherencia con la tabla).

**Criterio de aceptación:** `Document` ya no tiene `tipo_documento`, `nombre_archivo`, `texto_extraido`; `documento_anexo` es obligatorio; tabla física `documento_adjunto`.
**Riesgo:** `DocumentSerializer`/`DocumentWriteSerializer`/`DocumentUploadSerializer` (T19), `adjuntar_documento` (T15), `DocumentViewSet` (T26), `AnnexAttachmentMixin` (T21), `internados.services` (T16). El versionado por defecto que discriminaba por `tipo_documento` desaparece: **todo adjunto** requiere ahora `documento_anexo`.

### T11 — Eliminar `DocumentType`

**Archivo:** `apps/convenios/models.py` (clase `DocumentType`, líneas 123-127).
**Acción:** eliminar la clase completa.
**Criterio de aceptación:** `DocumentType` no importable.
**Riesgo:** referencias en views (`document-types` en `ENTITY_VIEWSETS`, T25), serializers (`DocumentUploadSerializer.tipo_documento`, T19), mixins (`_tipo_documento_anexo`, T21), y la migración `0011_seed_document_type_anexo` (queda obsoleta — la nueva migración la neutraliza, T30). No borrar el archivo `0011`; su `RunPython` sigue en el historial pero se sustituye por reseed en la nueva migración.

---

## Bloque B — Modelos (`apps/internados/models.py`)

### T12 — `AnnexDocument`: quitar `descripcion`, `tipo_actor` admite blank, renombrar tabla

**Archivo:** `apps/internados/models.py` (clase `AnnexDocument`, líneas 76-93).
**Acción:**

1. Eliminar el campo `descripcion` (líneas 84-86).
2. Modificar `tipo_actor` (líneas 80-83): añadir `blank=True` (mantener `choices=ANNEX_ACTOR`, `max_length=30`, `default="INTERNO"`). Los tipos genéricos absorbidos de `tipo_documento` (ANEXO/CONVENIO/RESOLUCION) no tienen actor → `tipo_actor=""`.
3. `Meta.db_table = "documento_anexo"` (era `"documentos_anexos"`). `verbose_name` sigue `"documento anexo"`.

**Criterio de aceptación:** `AnnexDocument` sin `descripcion`; `tipo_actor` puede quedar en blanco; tabla física `documento_anexo`.
**Riesgo:** `AnnexAttachmentMixin.annex_checklist` filtra `tipo_actor=self.annex_actor` (sigue válido); `internados.services._declaraciones_completas` filtra `tipo_actor="INTERNO"` (sigue válido). Ningún serializer expone `descripcion` de forma obligatoria — verificar `_auto_serializer` de `annex-documents` (usa `fields="__all__"`, se ajusta solo al quitar el campo).

---

## Bloque C — Services

### T13 — `services.registrar_organo_representante` (nuevo, `apps/convenios/services.py`)

**Archivo:** `apps/convenios/services.py`.
**Acción:** crear el service que aplica la **regla de negocio del histórico**:

```
registrar_organo_representante(*, datos: dict, usuario) -> OrganRepresentative
```

- Decorado con `@transaction.atomic`.
- Al crear un representante para un par `(organo_directorio, cargo_ejecutivo)` que ya tiene uno **activo**:
  1. Marcar el anterior `activo=False` (`save(update_fields=["activo"])`).
  2. Copiar el anterior a `OrganRepresentativeHistory` (snapshot de todos los campos) con `fecha_baja=datetime.date.today()` y `motivo=datos.get("motivo", "")` (o motivo por defecto «Reemplazo de representante»).
  3. `registrar_auditoria(usuario, "CAMBIO_ESTADO", anterior, nombre_campo="activo", valor_anterior="True", valor_nuevo="False")` y `registrar_auditoria(usuario, "CREAR", historial)`.
- Crear el nuevo `OrganRepresentative` con los `datos` validados.
- `registrar_auditoria(usuario, "CREAR", nuevo)`.
- Devolver el nuevo representante.

**Regla:** RN de histórico de representantes — **va en el service** (no en serializer), porque implica escritura transaccional multi-tabla + auditoría.
**Criterio de aceptación:** crear A `(X, Rector)` → activo; crear B `(X, Rector)` → A `activo=False`, aparece fila en `historial_organo_representante` con `fecha_baja=hoy`; todo en una transacción.
**Nota:** el `OrganRepresentativeViewSet.perform_create` debe llamar a este service (T24) en vez de al `serializer.save()` por defecto, para no duplicar auditoría.

### T14 — (reservado) — consolidado en T13.

### T15 — `common/services.adjuntar_documento`: simplificar firma

**Archivo:** `apps/common/services.py`.
**Acción:** modificar `adjuntar_documento`:

- **Quitar** los parámetros `tipo_documento`, `nombre_archivo`, `texto_extraido`.
- **Volver obligatorio** `documento_anexo` (parámetro keyword-only, sin default): `def adjuntar_documento(objeto, *, referencia_externa, usuario, documento_anexo) -> Document`.
- El **discriminador de versionado es siempre `documento_anexo`**: el filtro del activo previo pasa a ser `{tipo_contenido, id_objeto, estado="ACTIVO", documento_anexo}` (eliminar la rama `else` que filtraba por `tipo_documento`).
- En `Document.objects.create(...)`: eliminar `tipo_documento`, `nombre_archivo`, `texto_extraido`; mantener `referencia_externa`, `tipo_contenido`, `id_objeto`, `version`, `estado`, `version_anterior`, `documento_anexo`, `cargado_por`.
- El nombre de archivo se usa **solo como ruta de storage** en la vista/mixin que llama a `storage.subir(...)`; **no se persiste** en `Document`.
- Actualizar el docstring (español): un solo discriminador `documento_anexo`, obligatorio.

**Criterio de aceptación:** `adjuntar_documento(objeto, referencia_externa=..., usuario=..., documento_anexo=anexo)` crea el `Document`; llamar sin `documento_anexo` es un `TypeError`.
**Riesgo:** todos los llamadores (`DocumentViewSet.create`/`upload` T26, `AnnexAttachmentMixin.annex_upload` T21) deben actualizarse en el mismo cambio o el arranque/las requests fallan.

### T16 — `internados/services.py`: verificar tras rename

**Archivo:** `apps/internados/services.py`.
**Acción:** **verificar (no cambiar salvo compilación)** `_declaraciones_completas` (líneas 366-389) y `recalcular_estado_declaraciones` (líneas 392-406):

- Filtran `Document.objects.filter(..., documento_anexo__isnull=False)` — sigue válido (ahora `documento_anexo` es NOT NULL, el filtro `__isnull=False` es redundante pero no rompe).
- Filtran `AnnexDocument.objects.filter(activo=True, tipo_actor="INTERNO", obligatorio=True)` — sigue válido.
- El import `from apps.convenios.models import Document` sigue válido (misma clase, tabla renombrada).

**Criterio de aceptación:** `python manage.py check` OK; el flujo de DJ del interno (`interns/{id}/annex-upload` → `recalcular_estado_declaraciones`) sigue funcionando sobre `documento_anexo`/`documento_adjunto`.
**Nota:** opcional simplificar quitando `documento_anexo__isnull=False` — dejar a criterio del implementador; no es obligatorio.

---

## Bloque D — Serializers (`apps/convenios/serializers.py`)

### T17 — `OrganRepresentativeSerializer` (nuevo)

**Archivo:** `apps/convenios/serializers.py`.
**Acción:** crear `OrganRepresentativeSerializer(serializers.ModelSerializer)`:

- `Meta.model = OrganRepresentative`, `fields = "__all__"`.
- **Validación de unicidad de documento** (`validate`): rechazar si ya existe otro `OrganRepresentative` **activo** con el mismo `(tipo_documento_identidad, numero_documento_identidad)` (excluir `self.instance` en update). Mensaje español.
- **Coherencia** opcional: `cargo_ejecutivo.organo` debe coincidir con `organo_directorio.organo` (el cargo pertenece al mismo tipo de órgano). Mensaje español: «El cargo ejecutivo no corresponde al órgano del directorio.». Marcar como validación **de serializer** (no de service).
- Exponer detalles legibles de FKs de solo lectura si conviene (patrón `_detalle_nombre`), opcional.

**Criterio de aceptación:** documento duplicado activo → 400; cargo de otro órgano → 400.
**Regla:** unicidad + coherencia órgano/cargo son **validaciones de serializer**. La baja del anterior (histórico) es **regla de service** (T13).

### T18 — Eliminar `RepresentativeSerializer` y `ENTIDADES_REPRESENTABLES`

**Archivo:** `apps/convenios/serializers.py`.
**Acción:** eliminar `RepresentativeSerializer` (líneas 279-303) y la constante `ENTIDADES_REPRESENTABLES` (línea 27). Quitar el import de `Representative` en el encabezado del módulo.
**Criterio de aceptación:** no quedan referencias a `Representative` en serializers.

### T19 — `DocumentSerializer` / `DocumentWriteSerializer` / `DocumentUploadSerializer`: quitar campos eliminados

**Archivo:** `apps/convenios/serializers.py`.
**Acción:**

- **`DocumentSerializer`** (líneas 309-327): quitar `tipo_documento`, `tipo_documento_nombre`, `nombre_archivo`, `texto_extraido` de `fields` y `read_only_fields`; quitar el `SerializerMethodField`/`CharField` `tipo_documento_nombre` (línea 312). Añadir `documento_anexo` a `fields` (ahora obligatorio) y opcionalmente `documento_anexo_nombre` (`source="documento_anexo.nombre"`, read_only). `tipo_contenido_label` se conserva.
- **`DocumentWriteSerializer`** (líneas 330-349): en `fields` quitar `tipo_documento` y `nombre_archivo`; añadir `documento_anexo` (obligatorio). Mantener `validate` (verifica que el objeto destino existe).
- **`DocumentUploadSerializer`** (líneas 361-416): quitar el campo `tipo_documento` (líneas 371-373). Mantener `nombre_archivo` **solo** si se usa como ruta de storage — **el plan pide quitar `nombre_archivo` de `AnnexUploadSerializer` (T20)**, pero para `DocumentUploadSerializer` el nombre de archivo sigue siendo necesario como ruta de storage. **Decisión:** conservar `nombre_archivo` en `DocumentUploadSerializer` como campo de ruta (opcional, se deriva del archivo), y **añadir** `documento_anexo` (obligatorio, usar `ActiveAnnexDocumentField`). Actualizar el `validate` para no depender de `tipo_documento`.
  > Riesgo/decisión: el plan dice explícitamente «`DocumentSerializer` (quitar `tipo_documento*`, `nombre_archivo`), `AnnexUploadSerializer` (quitar `nombre_archivo`)». Para `DocumentUploadSerializer` no menciona `nombre_archivo`; mantenerlo como ruta de storage. Confirmar con validator si se desea quitarlo también.

**Criterio de aceptación:** ningún serializer de documento referencia `tipo_documento`, `texto_extraido`; `documento_anexo` es requerido para crear/subir documentos.

### T20 — `AnnexUploadSerializer`: quitar `nombre_archivo`

**Archivo:** `apps/convenios/serializers.py` (líneas 473-493+).
**Acción:** eliminar el campo `nombre_archivo` (líneas 488-493). El nombre de la ruta de storage se deriva del archivo subido (`archivo.name`) dentro del mixin. Mantener `documento_anexo` (`ActiveAnnexDocumentField`) y `archivo`. Ajustar el `validate` si asignaba `nombre_archivo`.
**Criterio de aceptación:** `AnnexUploadSerializer` solo expone `documento_anexo` y `archivo`.
**Riesgo:** `AnnexAttachmentMixin.annex_upload` lee `ser.validated_data["nombre_archivo"]` (mixin línea 185) — actualizar en T21.

### T21 — `AnnexAttachmentMixin.annex_upload`: simplificar

**Archivo:** `apps/convenios/mixins.py`.
**Acción:**

- Eliminar el método `_tipo_documento_anexo` (líneas 150-154) y el import `from apps.convenios.models import DocumentType`.
- Eliminar el import `from apps.common.documentai import extraer_texto_pdf` (línea 28) y la llamada `texto_extraido = extraer_texto_pdf(archivo)` (línea 189).
- En `annex_upload` (líneas 167-199): derivar la ruta de storage del archivo (`ruta = archivo.name` o un nombre construido), subir con `self.storage.subir(archivo, ruta=ruta)`, y llamar:
  `adjuntar_documento(entidad, referencia_externa=referencia, usuario=request.user, documento_anexo=anexo)`.
  Quitar los kwargs `tipo_documento`, `nombre_archivo`, `texto_extraido`.
- Mantener el enforcement `if anexo.tipo_actor != self.annex_actor: raise ValidationError(...)`.

**Criterio de aceptación:** `POST {entidad}/annex-upload/` crea un `documento_adjunto` con `documento_anexo` (actor correcto) sin columnas `nombre_archivo`/`texto_extraido`; el mixin no importa `DocumentType` ni `extraer_texto_pdf`.
**Riesgo:** `annex_checklist` (líneas 220-263) lee `Document.objects.filter(..., documento_anexo__isnull=False)` — sigue válido; sin cambios de fondo.

---

## Bloque E — Views (`apps/convenios/views.py`)

### T22 — `OrganRepresentativeViewSet` (nuevo)

**Archivo:** `apps/convenios/views.py`.
**Acción:** crear `class OrganRepresentativeViewSet(AnnexAttachmentMixin, AuditedModelViewSet)`:

- `queryset = m.OrganRepresentative.objects.select_related("organo_directorio", "cargo_ejecutivo", "tipo_documento_identidad")`.
- `serializer_class = OrganRepresentativeSerializer`.
- `permission_classes = [IsAuthenticated, IsAdminRoleOrReadOnly]`.
- `filterset_fields = ["organo_directorio", "cargo_ejecutivo", "activo"]`.
- `search_fields = ["nombre", "numero_documento_identidad"]`.
- `ordering = ["id"]`.
- `annex_actor = "REPRESENTANTE"`.
- **`perform_create`**: llamar a `services.registrar_organo_representante(datos=serializer.validated_data, usuario=self.request.user)` y asignar `serializer.instance` (evita doble auditoría de `AuditedModelViewSet`; ver patrón `ClinicalFieldRegistrationViewSet.perform_create`, views.py líneas 250-253).
- `perform_update`/`perform_destroy`: heredados de `AuditedModelViewSet` (auditoría estándar). Si un update cambia `(organo_directorio, cargo_ejecutivo)` y debe disparar histórico, documentarlo; **por defecto** el histórico solo aplica en create (según el plan). Mantener update simple.

**Criterio de aceptación:** endpoint CRUD con annex-upload/checklist actor REPRESENTANTE; create dispara la regla de histórico vía service.

### T23 — `OrganRepresentativeHistoryViewSet` (nuevo, read-only)

**Archivo:** `apps/convenios/views.py`.
**Acción:** crear `class OrganRepresentativeHistoryViewSet(viewsets.ReadOnlyModelViewSet)`:

- `queryset = m.OrganRepresentativeHistory.objects.select_related("representante", "organo_directorio", "cargo_ejecutivo").all()`.
- `serializer_class = _auto_serializer(m.OrganRepresentativeHistory)` (o un serializer explícito con detalles legibles).
- `permission_classes = [IsAuthenticated]`.
- `filterset_fields = ["organo_directorio", "cargo_ejecutivo", "representante"]`.
- `ordering = ["-fecha_baja", "-id"]`.

**Criterio de aceptación:** solo lectura; filtrable por `organo_directorio`/`cargo_ejecutivo`.

### T24 — Eliminar `RepresentativeViewSet`

**Archivo:** `apps/convenios/views.py` (líneas 580-593).
**Acción:** eliminar la clase `RepresentativeViewSet` y su import `RepresentativeSerializer` del bloque de imports (línea 54). Quitar del router en T29.
**Criterio de aceptación:** `RepresentativeViewSet` no existe.

### T25 — Ajustar `CATALOG_VIEWSETS` y `ENTITY_VIEWSETS`

**Archivo:** `apps/convenios/views.py`.
**Acción:**

1. **Mover `executive-positions`** de `CATALOG_VIEWSETS` (línea 476) a `ENTITY_VIEWSETS` como entidad CRUD:
   `"executive-positions": _entity_viewset(m.ExecutivePosition, filterset_fields=["organo", "activo"], search_fields=["codigo", "nombre"])`.
   Eliminar la línea de `CATALOG_VIEWSETS`.
2. **Eliminar `document-types`** de `ENTITY_VIEWSETS` (líneas 489-491).
3. **Eliminar `regional-organs`** de `ENTITY_VIEWSETS` (líneas 520-525).
4. **Eliminar `minsa-organs`** de `ENTITY_VIEWSETS` (líneas 533-535).
5. **Añadir `organ-directories`** a `ENTITY_VIEWSETS`:
   `"organ-directories": _entity_viewset(m.OrganDirectory, filterset_fields=["organo", "tipo_organo", "gobierno_regional", "activo"], search_fields=["nombre", "siglas", "numero_ruc"], logo=True)`.
6. **Actualizar `executing-units`** (línea 526-531): cambiar `filterset_fields=["organo_regional", ...]` → `["organo_directorio", "tipo_organo", "activo"]`.
7. **Eliminar `university-authorities`** de `ENTITY_VIEWSETS` (líneas 543-548).

**Criterio de aceptación:** `executive-positions` es CRUD con filtro `organo`; `document-types`, `regional-organs`, `minsa-organs`, `university-authorities` ya no se registran; `organ-directories` disponible con logo.

### T26 — `DocumentViewSet`: quitar `tipo_documento` y actualizar llamadas a `adjuntar_documento`

**Archivo:** `apps/convenios/views.py` (líneas 599-685).
**Acción:**

- `queryset`: quitar `"tipo_documento"` del `select_related` (línea 607).
- `filterset_fields` (línea 610): quitar `"tipo_documento"` → `["tipo_contenido", "id_objeto", "documento_anexo", "estado"]`.
- `create` (líneas 626-638): quitar `tipo_documento=` y `nombre_archivo=` de la llamada a `adjuntar_documento`; añadir `documento_anexo=ser.validated_data["documento_anexo"]`. La ruta de storage no aplica aquí (referencia externa provista por el cliente).
- `upload` (líneas 640-675): quitar `tipo_documento=`, `texto_extraido=`, `extraer_texto_pdf`; llamar `adjuntar_documento(objeto, referencia_externa=referencia, usuario=request.user, documento_anexo=datos["documento_anexo"])`. La ruta de storage se deriva de `nombre_archivo`/`archivo.name` (`storage.subir(archivo, ruta=...)`). Quitar el import `extraer_texto_pdf` si ya no se usa en el módulo (verificar).

**Criterio de aceptación:** `documents` filtra por `documento_anexo`, no por `tipo_documento`; `create`/`upload` pasan `documento_anexo`.

### T27 — `SOLICITANTE_MODELS`: sustituir órganos eliminados

**Archivo:** `apps/convenios/views.py` (líneas 701-709).
**Acción:** en `SOLICITANTE_MODELS`, reemplazar `m.RegionalOrgan` y `m.MinsaOrgan` por `m.OrganDirectory` (una sola entrada). Verificar `ENTIDADES_REPRESENTABLES` ya eliminada (T18) no se referencia aquí.
**Criterio de aceptación:** `solicitante-content-types/` no referencia clases eliminadas; incluye `OrganDirectory`.
**Riesgo:** un convenio existente que apuntaba a `regionalorgan`/`minsaorgan` como solicitante — BD limpia, sin datos reales, no aplica.

### T28 — Barrido de referencias residuales (obligatorio antes de `check`)

**Archivos:** todo `apps/convenios/` y `apps/internados/`.
**Acción:** grep y corregir toda referencia a: `RegionalOrgan`, `MinsaOrgan`, `Representative`, `UniversityAuthority`, `DocumentType`, `organo_regional`, `organo_minsa`, `tipo_documento`, `nombre_archivo`, `texto_extraido`, `descripcion` (en AnnexDocument), `REPRESENTATIVE_ORIGIN`, `ENTIDADES_REPRESENTABLES`. Revisar en particular:

- `apps/convenios/filters.py` (`ConventionFilter` — campo `organo_regional`).
- `apps/convenios/selectors.py` (convenios: joins/`select_related` con `organo_regional`).
- `apps/convenios/services.py` (`crear_convenio`/`actualizar_convenio`/`registrar_evaluacion_tecnica` — `organo_regional`/`organo_minsa`).
- Serializers de convenio (`ConventionReadSerializer`/`ConventionWriteSerializer`, `TechnicalEvaluationSerializer`).
- `apps/convenios/permissions.py` (`ConventionScope` — si deriva ámbito de `organo_regional`).
- `apps/common/serializers.py`, `apps/common/*` (si referencian `Document.tipo_documento`, etc.).

**Criterio de aceptación:** `python manage.py check` sin errores; `rg "organo_regional|organo_minsa|DocumentType|tipo_documento"` en `apps/` solo devuelve coincidencias en migraciones históricas y comentarios.

---

## Bloque F — URLs (`apps/convenios/urls.py`)

### T29 — Router: quitar `representatives`, añadir `organ-representatives` y `organ-representative-history`

**Archivo:** `apps/convenios/urls.py`.
**Acción:**

- Eliminar `router.register("representatives", views.RepresentativeViewSet)` (línea 23).
- Añadir `router.register("organ-representatives", views.OrganRepresentativeViewSet, basename="organ-representative")`.
- Añadir `router.register("organ-representative-history", views.OrganRepresentativeHistoryViewSet, basename="organ-representative-history")`.
- Los basenames `document-types`, `regional-organs`, `minsa-organs`, `university-authorities`, `executive-positions` (como catálogo) se registran vía los diccionarios `CATALOG_VIEWSETS`/`ENTITY_VIEWSETS` (T25) — no requieren cambio manual en `urls.py`, salvo verificar que `organ-directories` y `executive-positions` (ahora entidad) queden registrados por el bucle de `ENTITY_VIEWSETS`.

**Criterio de aceptación:** `GET /api/v1/organ-representatives/`, `/api/v1/organ-representative-history/`, `/api/v1/organ-directories/`, `/api/v1/executive-positions/` (CRUD) responden; `/api/v1/representatives/`, `/api/v1/university-authorities/`, `/api/v1/regional-organs/`, `/api/v1/minsa-organs/`, `/api/v1/document-types/` → 404.

---

## Bloque G — Migraciones

### T30 — Migración `apps/convenios/migrations/0019_reorg_directorio_representantes_documentos.py`

**Archivo:** nueva migración. **Número real:** la última es `0018_normalize_organ_table` → **`0019`**. `dependencies = [("convenios", "0018_normalize_organ_table")]` + `("internados", "<última internados>")` si hay FKs cruzadas nuevas (verificar; `OrganRepresentative.tipo_documento_identidad` → `internados.IdentityDocumentType`, así que **añadir dependencia a la última migración de internados**, que será la nueva `0018` de internados — ver T31; ambas se coordinan por `run_before`/`dependencies`).

**Operaciones (orden):**

1. `cargo_ejecutivo`: `RemoveField`/`AlterField` para quitar herencia `Catalog` (quitar `unique` de `codigo`), `AddField organo`, `AddField`/`AlterField` `activo`, `AlterUniqueTogether(("organo", "codigo"))`, `AlterModelOptions(ordering)`.
2. `CreateModel OrganDirectory` (tabla `organo_directorio`).
3. Repuntar FKs (BD limpia, sin transferencia):
   - `ExecutingUnit`: `RemoveField organo_regional` + `AddField organo_directorio`.
   - `Convention`: `RemoveField organo_regional` + `AddField organo_directorio`.
   - `TechnicalEvaluation`: `RemoveField organo_minsa` + `AddField organo_directorio`.
4. `DeleteModel RegionalOrgan`, `DeleteModel MinsaOrgan`.
5. `CreateModel OrganRepresentative` (tabla `organo_representante`) + `CreateModel OrganRepresentativeHistory` (tabla `historial_organo_representante`).
6. `DeleteModel Representative`, `DeleteModel UniversityAuthority`.
7. `Document`: `RemoveField nombre_archivo`, `RemoveField texto_extraido`, `RemoveField tipo_documento`; `AlterField documento_anexo` (NOT NULL, `PROTECT`); `AlterModelTable → documento_adjunto`.
8. `DeleteModel DocumentType`.
9. `RunPython` **reseed** (con `reverse_code` o `migrations.RunPython.noop`):
   - **Cargos ejecutivos** por órgano (resolver `Organ` por `nombre`):
     - UNIVERSIDAD: Rector, Vicerrector, Decano, Secretario General.
     - ORGANO_REGIONAL (Órgano Regional): Director General, Gerente General, Director Regional de Salud, Director de Hospital III, Director de DIRIS.
     - MINSA (Órgano del MINSA): Ministro, Viceministro, Director General de Personal de Salud.
     - Usar `get_or_create(organo=..., codigo=...)` con `codigo` derivado (slug/uppercase estable) y `nombre` legible.
   - **`documento_anexo`** (vía `apps.get_model("internados", "AnnexDocument")`): mantener/crear anexos por actor (DJ_*, RESOL_*, DNI_*) y **añadir** los tipos genéricos absorbidos de `tipo_documento` con `tipo_actor=""`: `ANEXO`, `CONVENIO`, `RESOLUCION` (`get_or_create(codigo=...)`).
   - **Nota:** el `DocumentType` `ANEXO` sembrado por `0011_seed_document_type_anexo` queda obsoleto; no borrar el archivo `0011`, la nueva migración lo suplanta funcionalmente. `AnnexAttachmentMixin` ya no resuelve `DocumentType` (T21).

**Riesgo:** `makemigrations` puede generar operaciones distintas al orden manual — preferir **autogenerar** con `python manage.py makemigrations convenios` y luego **insertar** los `RunPython` de reseed y verificar el orden de `DeleteModel`/repunte. En BD limpia no hay conflicto de datos. Usar `apps.get_model` en los `RunPython` (nunca importar los modelos reales).
**Criterio de aceptación:** `python manage.py makemigrations --check --dry-run` limpio tras aplicar; `python manage.py migrate` sin errores; catálogos resembrados.

### T31 — Migración `apps/internados/migrations/0018_annexdocument_documento_anexo.py`

**Archivo:** nueva migración internados. **Número real:** última es `0017_internship_campo_clinico_allocation` → **`0018`**. `dependencies = [("internados", "0017_internship_campo_clinico_allocation")]`.

**Operaciones:**

1. `RemoveField AnnexDocument.descripcion`.
2. `AlterField AnnexDocument.tipo_actor` (añadir `blank=True`).
3. `AlterModelTable AnnexDocument → documento_anexo`.

**Coordinación con convenios:** la migración de convenios `0019` referencia `internados.AnnexDocument` (FK en `Document.documento_anexo`, `OrganRepresentative.tipo_documento_identidad`). Añadir a `0019` una dependencia sobre esta `0018` de internados (o usar `run_before`). **Verificar** el orden con `makemigrations --check`.
**Criterio de aceptación:** tabla física `documento_anexo` en internados; `AnnexDocument` sin `descripcion`; `tipo_actor` opcional.

---

## Bloque H — Documentación

### T32 — Actualizar docs y CLAUDE.md

**Archivos y cambios:**

- **`docs/db_schema_modulo_01_convenios.md`** — reemplazar secciones `organo_regional`, `organo_minsa`, `representante`, `autoridad_universidad`, `cargo_ejecutivo`, `documento`, `tipo_documento` por: `cargo_ejecutivo` (con `organo`), `organo_directorio`, `organo_representante`, `historial_organo_representante`, `documento_adjunto`. Listar columnas exactas de las tablas nuevas (español).
- **`docs/db_schema_modulo_02_internados.md`** — sección `documento_anexo` (renombrada de `documentos_anexos`): sin `descripcion`, `tipo_actor` opcional, absorbe tipos genéricos (ANEXO/CONVENIO/RESOLUCION).
- **`docs/db_schema_er_global.md`** — actualizar FKs (`ExecutingUnit`/`Convention` → `organo_directorio`, `TechnicalEvaluation` → `organo_directorio`, `OrganRepresentative` → `organo_directorio`, `Document` → `documento_anexo`) y el diagrama Mermaid; eliminar nodos `organo_regional`/`organo_minsa`/`representante`/`autoridad_universidad`/`tipo_documento`.
- **`docs/api_almacenamiento_frontend.md`** — endpoints/campos de upload sin `nombre_archivo` (en `annex-upload`); `documento_anexo` obligatorio; renombrar `documents` sobre tabla `documento_adjunto`; nuevo actor de `organ-representatives`.
- **`CLAUDE.md`** — §catálogos: quitar `document-types` de la lista de catálogos con CRUD; quitar referencias a `regional-organ`/`minsa`; añadir `executive-positions` y `organ-directories` como entidades CRUD. §Convenios: representantes por directorio (`organ-representatives`) + histórico. §Internados: tabla `documento_anexo`.

**Criterio de aceptación:** los `docs/*.md` reflejan el estado final de modelos/endpoints; `CLAUDE.md` sin referencias a endpoints/modelos eliminados.

---

## Verificación final (checklist de cierre)

1. `python manage.py makemigrations --check --dry-run` → sin cambios pendientes.
2. `python manage.py migrate` y `python manage.py check` → OK.
3. Shell: `OrganDirectory`, `OrganRepresentative`, `OrganRepresentativeHistory`, `ExecutivePosition.organo` existen; `RegionalOrgan`/`MinsaOrgan`/`Representative`/`UniversityAuthority`/`DocumentType` **no** importables.
4. `ExecutivePosition.objects.filter(organo__nombre="Universidad")` incluye Rector/Decano.
5. Crear representante A `(organo_directorio X, cargo Rector)` → activo; crear B mismo `(X, Rector)` → A `activo=False` y aparece fila en `historial_organo_representante` con `fecha_baja`.
6. `POST /api/v1/organ-representatives/{id}/annex-upload/` (PDF resolución) → `documento_adjunto` creado con `documento_anexo` (actor REPRESENTANTE), sin columnas `nombre_archivo`/`texto_extraido`.
7. Endpoints viejos (`regional-organs`, `minsa-organs`, `university-authorities`, `document-types`, `representatives`) → 404.
8. Flujo de DJ del interno (`interns/{id}/annex-upload` + `recalcular_estado_declaraciones`) sigue funcionando sobre `documento_anexo`/`documento_adjunto`.
9. Ejecutar `/code-review` y `/fix-types` antes de cerrar.

---

## Referencias (tablas/columnas y reglas)

- **Tablas afectadas:** `cargo_ejecutivo`, `organo_directorio` (nueva), `organo_representante` (nueva), `historial_organo_representante` (nueva), `documento_adjunto` (ex `documento`), `documento_anexo` (ex `documentos_anexos`); **eliminadas:** `organo_regional`, `organo_minsa`, `representante`, `autoridad_universidad`, `tipo_documento`.
- **FKs repuntadas:** `unidad_ejecutora.organo_directorio_id`, `convenio.organo_directorio_id`, `evaluacion_tecnica.organo_directorio_id`, `documento_adjunto.documento_anexo_id` (NOT NULL).
- **Reglas de negocio:**
  - **Histórico de representantes** (baja del anterior al designar uno nuevo para el mismo `(organo_directorio, cargo_ejecutivo)`) → **service** `registrar_organo_representante` (T13).
  - **Unicidad de documento del representante** + **coherencia órgano/cargo** → **validaciones de serializer** (T17).
  - **Versionado documental por `documento_anexo`** (único discriminador) → **service** `adjuntar_documento` (T15).
  - **RN-23 (estado de DJ del interno)** — no cambia de lógica; se valida que compila sobre `documento_anexo`/`documento_adjunto` (T16).
- **RNF:** RNF-AUD-01/02 (auditoría en `bitacora_auditoria` en cada create/update/delete y en la baja de representantes), RNF-DOC-01/02/03/04 (gestión documental versionada), RNF-MAN-01 (catálogos parametrizables: `cargo_ejecutivo`, `documento_anexo`).
