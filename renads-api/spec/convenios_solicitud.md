# Spec — Mejora del Registro de Solicitud de Convenios

**Módulo:** Gestionar Convenios (`apps/convenios`)
**Fuentes de verdad:** `docs/arquitectura_desarrollo.md`, `docs/db_schema_modulo_01_convenios.md`, `docs/db_schema_modulo_02_internados.md`, reglas de negocio en `CLAUDE.md`.
**Plan:** aprobado por el usuario; este documento traduce el plan a tareas exactas por archivo. El agente **Implement** ejecuta; el agente **Validator** revisa contra este spec.

> Reglas de lenguaje del proyecto: **tabla / columna / `db_table` / `db_column` / `help_text` / verbose en español**; **código (clases, funciones, variables, endpoints, choices key) en inglés**; docstrings, comentarios y mensajes de error orientados al usuario en español.
> **NO se ejecuta testing automatizado** (fuera de alcance del MVP) ni `runserver`. Los comandos de verificación de esta spec se limitan a `makemigrations --check`, `migrate`, `check` y la generación de OpenAPI, y **cualquier ejecución la aprueba/corre el usuario**.

---

## 1. Objetivo

Enriquecer el registro de la **solicitud de convenio** (Marco, Específico y Adenda) con:

- **Partes firmantes estructuradas** por rol institucional (no polimórficas), con órgano + representante + cargo coherentes — nueva tabla `parte_convenio` (`ConventionParty`). **Se conservan** `ConventionParticipant` (`participante_convenio`) y `Signature` (`firma`); NO se reemplazan.
- **Resolución de facultades** del representante (`numero_resolucion_facultades`).
- **Nomenclatura oficial** del Convenio Marco (rename de `codigo` → `nomenclatura`), asignada al aprobar DIGEP.
- **Almacenamiento en Cloudflare R2** (S3-compatible) espejando la abstracción `DocumentStorage` existente, sin romper GCS.
- **Generación de PDF** del proyecto de convenio y del expediente (docxtpl + LibreOffice headless + pypdf).

## 2. Entidades cubiertas

`Convention` (`convenio`, models.py:738), nueva `ConventionParty` (`parte_convenio`), `OrganRepresentative` (`organo_representante`, models.py:449) + `OrganRepresentativeHistory` (models.py:494), `OrganDirectory` (models.py:303), `ExecutivePosition` (models.py:185), `ClinicalFieldRegistration` / `ClinicalFieldAllocation`, `Document` (`documento_adjunto`, models.py:1104), `AnnexDocument` (`documento_anexo`, `apps/internados/models.py:78`).

## 3. Orden de dependencias entre fases

```
FASE A (modelo de datos + API partes/nomenclatura)  ──►  FASE C (generación PDF)
FASE B (storage Cloudflare R2)  ── independiente de A ──►  FASE C (C usa R2 para subir/leer binarios)
```

- **A → C:** C consume `ConventionParty`, `numero_resolucion_facultades` y `nomenclatura` para construir el contexto de las plantillas.
- **B → C:** C sube los PDFs generados y descarga logos desde el storage (R2 si está habilitado).
- **B es independiente de A** (puede implementarse en paralelo). Recomendado: A, luego B, luego C.

---

# FASE A — Modelo de datos, servicios y API de la solicitud

## A1. Modelo `ConventionParty` (tabla `parte_convenio`)

**Archivo:** `apps/convenios/models.py` (nuevo modelo tras `ConventionParticipant`, ~models.py:817–839).

**Choices** (nuevo, junto al modelo, en inglés como key):
```
PARTY_ROLE = [
    ("MINSA", "MINSA"),
    ("UNIVERSIDAD", "Universidad"),
    ("GOBIERNO_REGIONAL", "Gobierno regional"),
    ("UNIDAD_EJECUTORA", "Unidad ejecutora"),
    ("FACULTAD", "Facultad"),
]
```

**Campos:**
| Campo (código) | Tipo | `db_column` | Notas |
|---|---|---|---|
| `convenio` | FK `Convention` `CASCADE` | `convenio_id` | `related_name="partes_firmantes"` |
| `rol` | `CharField(max_length=20, choices=PARTY_ROLE)` | `rol` | verbose "rol de la parte" |
| `organo_directorio` | FK `OrganDirectory` `PROTECT` | `organo_directorio_id` | `related_name="+"` |
| `organo_representante` | FK `OrganRepresentative` `PROTECT` | `organo_representante_id` | `related_name="+"` |
| `cargo_ejecutivo` | FK `ExecutivePosition` `PROTECT` | `cargo_ejecutivo_id` | `related_name="+"` |
| `orden` | `PositiveSmallIntegerField(default=1)` | `orden` | apoderado = `orden=2`; verbose "orden de firma" |
| `es_firmante` | `BooleanField(default=True)` | `es_firmante` | |
| `creado_en` | `DateTimeField(auto_now_add=True)` | `creado_en` | |

**Meta:** `db_table="parte_convenio"`, `verbose_name="parte de convenio"`, `verbose_name_plural="partes de convenio"`, `unique_together=(("convenio", "rol", "orden"),)`, `ordering=["convenio", "orden"]`.

**Coherencia (validada en el service `sincronizar_partes`, A4 — NO en `clean()` del modelo):**
- `organo_representante.organo_directorio_id == organo_directorio_id` (omitir el chequeo si `organo_representante` es nulo).
- `cargo_ejecutivo.organo_directivo_id == organo_directorio_id` (omitir si `cargo_ejecutivo.organo_directivo_id` es nulo — cargos legacy sin órgano directivo no se validan, igual que en `registrar_organo_representante`).

**Criterios de aceptación:**
- El modelo compila y `django check` no reporta errores.
- Todas las FK son `PROTECT` salvo `convenio` (`CASCADE`).
- `help_text` y verbose en español; nombres de campo/clase/choices en inglés.
- El modelo **no** contiene lógica de negocio (la coherencia vive en el service).

## A2. `numero_resolucion_facultades` en representante e historial

**Archivo:** `apps/convenios/models.py`.

- Agregar a `OrganRepresentative` (tras `numero_resolucion_designacion`, models.py:474):
  ```
  numero_resolucion_facultades = models.CharField(
      "número de resolución de facultades", max_length=100, blank=True,
      help_text="Número de resolución que otorga facultades al representante",
  )
  ```
- Agregar el mismo campo a `OrganRepresentativeHistory` (tras `numero_resolucion_designacion`, models.py:523).

**Serializers/servicios afectados:**
- `apps/convenios/serializers.py` — `OrganRepresentativeSerializer` (read/write) expone `numero_resolucion_facultades`.
- `apps/convenios/services.py` — `registrar_organo_representante`: al copiar un representante dado de baja a `OrganRepresentativeHistory` (snapshot), **incluir** `numero_resolucion_facultades` en el snapshot.

**Criterios de aceptación:**
- El campo aparece en la respuesta de `GET/POST/PATCH /api/v1/organ-representatives/`.
- Al designar un nuevo representante para el mismo `(organo_directorio, cargo_ejecutivo)`, el snapshot en `organ-representative-history` conserva `numero_resolucion_facultades`.
- Ambos campos son opcionales (`blank=True`), `max_length=100`.

## A3. Rename `Convention.codigo` → `nomenclatura` + gate de nomenclatura

**Archivos:** `apps/convenios/models.py`, `apps/convenios/services.py`, `apps/convenios/serializers.py`, `apps/convenios/filters.py` (si filtra por `codigo`).

- `Convention.codigo` (models.py:761) pasa a `nomenclatura` vía **`RenameField`** (no drop+add): `nomenclatura = models.CharField("nomenclatura", max_length=50, blank=True, help_text="Nomenclatura oficial del Convenio Marco (se asigna al aprobar DIGEP)")`. Mantener `db_column="nomenclatura"` (default por rename; el `db_column` cambia con el nombre — aceptable, la columna se renombra en la migración).
- **Actualizar todas las referencias a `codigo`** en:
  - `services.crear_convenio` (services.py:223 `codigo=datos.get("codigo", "")`) → `nomenclatura=datos.get("nomenclatura", "")`.
  - `services.crear_adenda` (services.py:277 `codigo=datos.get("codigo", "")`) → `nomenclatura=datos.get("nomenclatura", "")`.
  - `services.actualizar_convenio` (services.py:302 lista `editables` contiene `"codigo"`) → **quitar `codigo` de `editables`** (la nomenclatura NO se edita por PATCH libre; se asigna vía gate A3).
  - `serializers.ConventionReadSerializer.Meta.fields` (serializers.py:58 `"codigo"`) → `"nomenclatura"`.
  - `serializers.ConventionWriteSerializer.Meta.fields` (serializers.py:100 `"codigo"`) → **quitar** (no editable directamente) o dejar `read_only`. Decisión: **quitar de write**; se setea solo por el service del gate.
  - `serializers.AdendaWriteSerializer` (serializers.py:111 `codigo`) → renombrar a `nomenclatura` (opcional, `allow_blank`).
- **Gate helper `_validar_nomenclatura`** (nuevo en `services.py`):
  ```
  def _validar_nomenclatura(convenio, nomenclatura):
      # Solo aplica a Convenio Marco.
      if convenio.tipo_convenio.codigo != "MARCO":
          raise ValidationError({"nomenclatura": "La nomenclatura solo aplica a Convenios Marco."})
      if not (nomenclatura or "").strip():
          raise ValidationError({"nomenclatura": "Requerida para aprobar la validación técnica del Marco."})
  ```
- **Punto de asignación:** en `services.registrar_evaluacion_tecnica` (services.py:349). Cuando `evaluacion.resultado == "VALIDADO"` y `convenio.tipo_convenio.codigo == "MARCO"`, **antes** de `_set_estado(convenio, "VALIDADO_TECNICAMENTE", ...)`, exigir y persistir la `nomenclatura` recibida en `datos`:
  - Extender la firma/uso: `registrar_evaluacion_tecnica` recibe `nomenclatura` opcional en `datos` (la consume el serializer `TechnicalEvaluationSerializer` o un campo extra en la acción `validar-tecnica`).
  - Si es Marco y resultado VALIDADO: llamar `_validar_nomenclatura(convenio, nomenclatura)`, asignar `convenio.nomenclatura = nomenclatura`, `convenio.save(update_fields=["nomenclatura", "actualizado_en"])`, registrar auditoría (`nombre_campo="nomenclatura"`), y luego `_set_estado(... "VALIDADO_TECNICAMENTE")`.
  - Nota de flujo: `VALIDADO_TECNICAMENTE` (orden 6) precede a `PENDIENTE_OGAJ` (orden 11); la nomenclatura queda asignada previo a la ruta OGAJ, según el plan.
- **Serializer de la acción `validar-tecnica`:** agregar `nomenclatura = serializers.CharField(required=False, allow_blank=True)` a `TechnicalEvaluationSerializer` (write-only, no es campo del modelo `TechnicalEvaluation`) o crear un serializer de acción dedicado. El campo NO se persiste en `evaluacion_tecnica`.

**Criterios de aceptación:**
- `grep` de `codigo` en `apps/convenios/{models,services,serializers,filters,views}.py` no arroja referencias al campo del convenio (sí pueden quedar `codigo` de `ConventionStatus`, `Catalog`, etc. — no confundir).
- Aprobar DIGEP (`resultado=VALIDADO`) de un **Marco sin nomenclatura** → `400` con mensaje español.
- Aprobar DIGEP de un **Específico** ignora `nomenclatura` (no la exige ni la asigna).
- `GET /api/v1/conventions/{id}/` devuelve `nomenclatura`; `PATCH` a `nomenclatura` directo no la modifica (no está en write serializer / editables).
- La migración usa `RenameField` (preserva datos existentes).

## A4. Servicios de partes: `sincronizar_partes` + extensión de `_validar_partes_por_tipo`

**Archivo:** `apps/convenios/services.py`.

### A4.1 `sincronizar_partes(*, convenio, datos, usuario)`
Sincronización idempotente de las `ConventionParty` de un convenio (patrón de `sincronizar_carreras_facultad`):
- Entrada `datos` = lista de dicts `{rol, organo_directorio, organo_representante, cargo_ejecutivo, orden, es_firmante}`.
- Corre en `@transaction.atomic`.
- **Coherencia por parte** (ver A1): valida `representante.organo_directorio_id == organo_directorio_id` y `cargo.organo_directivo_id == organo_directorio_id` (omitir si nulos) → `ValidationError` en español si falla.
- **Reconciliación:** crea las partes enviadas, actualiza las existentes por `(convenio, rol, orden)`, y elimina (`delete`) las que ya no estén en el payload.
- **Auditoría:** registra `CREAR`/`ACTUALIZAR`/`ELIMINAR` por cada parte afectada vía `registrar_auditoria`.
- Devuelve el queryset resultante de partes del convenio.

### A4.2 Extensión de `_validar_partes_por_tipo` (services.py:112)
Además de la validación actual `unidad_ejecutora`/`facultad`, añadir **partes requeridas por tipo** (validar la composición de roles esperada). Firma extendida para recibir `organo_directorio`/`partes` o exponer un helper `_validar_composicion_partes(*, tipo_codigo, categoria_organo, roles_presentes)`:

| Escenario | Roles requeridos |
|---|---|
| **Marco Lima** (`organo_directorio.categoria == "MINSA_DIRIS"`) | `MINSA` + `UNIVERSIDAD` |
| **Marco región** (`organo_directorio.categoria == "GOBIERNO_REGIONAL"`) | `MINSA` + `GOBIERNO_REGIONAL` + `UNIVERSIDAD` |
| **Específico** | `UNIDAD_EJECUTORA` + `FACULTAD` (apoderado `orden=2` opcional) |

- La validación de composición se ejecuta en `crear_convenio` / `actualizar_convenio` **solo si** se envían partes en el payload; si el flujo crea la solicitud sin partes (registro incremental), la composición se exige al sincronizar/generar el proyecto (documentar la decisión: **exigir composición en `sincronizar_partes`**, no en la creación mínima del convenio).
- Mensajes de error en español, indicando el rol faltante.

**Criterios de aceptación:**
- `sincronizar_partes` es idempotente: reenviar el mismo payload no duplica ni deja partes huérfanas.
- Coherencia órgano↔representante↔cargo rechazada con `400` en español.
- Falta de un rol requerido según tipo/categoría → `400` en español nombrando el rol.
- Toda escritura registra auditoría.

## A5. Selector `campos_clinicos_del_especifico`

**Archivo:** `apps/convenios/selectors.py`.

```
def campos_clinicos_del_especifico(convenio):
    """Registros CONAPRES (ClinicalFieldRegistration) de las sedes docentes de la
    unidad ejecutora del Específico, filtrados por las carreras de la facultad del
    convenio (university_careers)."""
```
- Base: `ClinicalFieldRegistration` de `ipress__unidad_ejecutora_id == convenio.unidad_ejecutora_id` con `ipress__es_sede_docente=True`.
- Filtro adicional por las carreras de la facultad del convenio: `carrera_profesional_id IN (UniversityCareer.objects.filter(facultad=convenio.facultad, activo=True).values("carrera_profesional_id"))`.
- Reusa el gate existente `_exigir_campos_clinicos_conapres` (services.py:143) — no lo duplica; el selector es solo lectura para poblar la tabla de campos clínicos del expediente (C3).

**Criterios de aceptación:**
- Devuelve solo registros de la unidad ejecutora del convenio y de carreras de su facultad.
- No incluye registros de otras unidades ejecutoras ni de carreras fuera de la facultad.
- Función de lectura pura (sin efectos secundarios ni auditoría).

## A6. Serializer y endpoints de partes + exposición de `nomenclatura`

**Archivos:** `apps/convenios/serializers.py`, `apps/convenios/views.py`.

### A6.1 `ConventionPartySerializer`
- **Write:** `convenio` (read-only, de la URL), `rol`, `organo_directorio`, `organo_representante`, `cargo_ejecutivo`, `orden`, `es_firmante`.
- **Read:** los anteriores + `*_detalle` legibles vía `_detalle_fk` (serializers.py:174): `organo_directorio_detalle` (`{id, nombre, siglas}`), `organo_representante_detalle` (`{id, nombre, numero_documento_identidad}`), `cargo_ejecutivo_detalle` (`{id, nombre_masculino, nombre_femenino}`), `rol_display` (`get_rol_display`).

### A6.2 Acción `conventions/{id}/parties`
En `ConventionViewSet` (views.py:62), añadir acción `@action(detail=True, methods=["get", "post"], url_path="parties")`:
- **GET:** lista `partes_firmantes` del convenio (read serializer).
- **POST:** recibe lista de partes, delega en `services.sincronizar_partes(convenio=..., datos=..., usuario=request.user)`, devuelve la lista resultante.
- Respeta `permission_classes` del ViewSet y el gate `module_content_type = ("convenios", "convention")` (views.py:73) — POST es escritura y debe pasar `IsModuleEnabled`.

### A6.3 Exposición en el read serializer del convenio
- `ConventionReadSerializer` (serializers.py:33) agrega `partes_firmantes` (SerializerMethodField o nested read-only sobre `related_name="partes_firmantes"`) y `nomenclatura` (A3).

**Criterios de aceptación:**
- `GET /api/v1/conventions/{id}/parties/` lista las partes con `*_detalle`.
- `POST /api/v1/conventions/{id}/parties/` sincroniza (crear/actualizar/eliminar) y responde la lista final.
- `GET /api/v1/conventions/{id}/` incluye `partes_firmantes` y `nomenclatura`.
- El endpoint aparece en OpenAPI (`@extend_schema` con request/response).

## A7. Migración de la Fase A

**Archivo:** `apps/convenios/migrations/00XX_convention_parties_nomenclatura.py` (autogenerada por `makemigrations`, revisada a mano).

Operaciones, **en este orden**:
1. `RenameField(model_name="convention", old_name="codigo", new_name="nomenclatura")`.
2. `AddField` `OrganRepresentative.numero_resolucion_facultades`.
3. `AddField` `OrganRepresentativeHistory.numero_resolucion_facultades`.
4. `CreateModel` `ConventionParty` (con `unique_together` y `db_table="parte_convenio"`).

**Criterios de aceptación:**
- `python manage.py makemigrations --check` → sin cambios pendientes tras crear la migración.
- `python manage.py migrate` aplica sin error sobre una BD con datos (el `RenameField` preserva valores de `codigo`).
- `python manage.py check` limpio.

---

# FASE B — Almacenamiento en Cloudflare R2 (S3-compatible)

Espeja la abstracción existente (`DocumentStorage`, `apps/common/storage.py`) y el patrón de settings de GCS (`config/settings/base.py:137–226`). **No elimina GCS** (queda como legacy seleccionable).

## B1. Backend `CloudflareR2Storage`

**Archivo:** `apps/common/storage.py`.

- Nueva clase `CloudflareR2Storage` que cumple estructuralmente `DocumentStorage` (Protocol, storage.py:20) con métodos `subir(archivo, ruta) -> str`, `url_firmada(referencia) -> str`, `eliminar(referencia) -> None`, espejando `GoogleCloudStorage` (storage.py:129):
  - Cliente `boto3` S3 con `endpoint_url = settings.R2_ENDPOINT_URL`, `region_name="auto"`, `aws_access_key_id=settings.R2_ACCESS_KEY_ID`, `aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY`, `config=Config(signature_version="s3v4")`.
  - `subir`: reusa `_nombre_seguro` (storage.py:117); key = `{R2_OBJECT_PREFIX}/{uuid4}-{nombre_seguro}`; `put_object`/`upload_fileobj` con `ContentType`; `archivo.seek(0)` antes de subir; devuelve la key (nunca URL).
  - `url_firmada`: `generate_presigned_url("get_object", Params={Bucket, Key}, ExpiresIn=settings.R2_SIGNED_URL_EXPIRATION)`.
  - `eliminar`: `delete_object`; tolera inexistencia (log `warning`, no propaga), igual que GCS.
  - Construcción perezosa del cliente (como `_get_bucket` de GCS); import diferido de `boto3` con `RuntimeError` en español si falta.
  - Lee `R2_BUCKET`; si falta con `R2_ENABLED` → `RuntimeError` en español.
- Actualizar `get_document_storage()` (storage.py:241) — orden de selección:
  1. Si `settings.R2_ENABLED` y `settings.R2_BUCKET` → `CloudflareR2Storage()`.
  2. Elif `settings.GCS_ENABLED` y `settings.GCS_BUCKET_NAME` → `GoogleCloudStorage()` (legacy).
  3. Else → `ReferenciaExternaStorage()` (stub).
  - Mantener `@lru_cache(maxsize=1)`.

**Criterios de aceptación:**
- `CloudflareR2Storage` cumple el `Protocol` (métodos con firmas equivalentes a GCS).
- Con `R2_ENABLED=False` el comportamiento actual (GCS/stub) no cambia.
- Presigned URLs de descarga con `s3v4`; nunca se devuelve la key en crudo ni URL pública.
- Import de `boto3` diferido (no rompe el arranque sin la dependencia si R2 está deshabilitado).

## B2. `STORAGES["default"]` sobre S3 para logos (ImageField)

**Archivo:** `config/settings/base.py` (bloque de `STORAGES`, base.py:98 y el `if GCS_ENABLED` de base.py:209).

- Añadir selección de `STORAGES["default"]` a `storages.backends.s3.S3Boto3Storage` **cuando `R2_ENABLED and R2_BUCKET`**, con `OPTIONS`:
  - `endpoint_url=R2_ENDPOINT_URL`, `access_key=R2_ACCESS_KEY_ID`, `secret_key=R2_SECRET_ACCESS_KEY`, `bucket_name=R2_BUCKET` (default `renads-media`), `region_name="auto"`, `querystring_auth=True`, `location="logos"`, `default_acl=None`, `file_overwrite=False`, `signature_version="s3v4"`.
- La selección R2 tiene **precedencia** sobre el bloque GCS existente (`if R2_ENABLED and R2_BUCKET: ... elif GCS_ENABLED and GS_BUCKET_NAME: ...`). Mantener el `FileSystemStorage` por defecto cuando ninguno está habilitado.

**Criterios de aceptación:**
- Con `R2_ENABLED=True`, los `ImageField` de logos (`upload-logo`/`logo-url` en `LogoStorageMixin`, mixins.py:39) persisten en R2 y `.url` devuelve un presigned URL.
- Con `R2_ENABLED=False`, se conserva GCS (si habilitado) o `FileSystemStorage`.
- `querystring_auth=True` y `default_acl=None` (bucket privado, sin ACL pública).

## B3. Settings `R2_*`

**Archivos:** `config/settings/base.py`, `.env.example`.

Agregar (patrón `config(...)` de decouple, con comentarios dev/prod en español):
| Variable | Default | Rol |
|---|---|---|
| `R2_ENABLED` | `False` (bool) | Activa R2 como backend documental y de logos |
| `R2_ACCOUNT_ID` | `""` | Account ID de Cloudflare |
| `R2_ACCESS_KEY_ID` | `""` | Access key del token R2 |
| `R2_SECRET_ACCESS_KEY` | `""` | Secret del token R2 |
| `R2_BUCKET` | `"renads-media"` | Bucket |
| `R2_ENDPOINT_URL` | `""` (típ. `https://<account_id>.r2.cloudflarestorage.com`) | Endpoint S3 de R2 |
| `R2_OBJECT_PREFIX` | `""` | Prefijo de keys de documentos (PDFs) |
| `R2_SIGNED_URL_EXPIRATION` | `900` (int) | Vigencia del presigned URL, en segundos |
| `R2_MAX_UPLOAD_BYTES` | `26214400` (int) | Tamaño máx. de subida (25 MiB) |
| `R2_ALLOWED_CONTENT_TYPES` | lista fija `["application/pdf","image/png","image/jpeg","image/webp"]` | Content-types permitidos |

- Comentarios explicando que R2 es S3-compatible, que `region_name="auto"`, y que en dev puede quedar deshabilitado (stub).
- `.env.example`: agregar las variables sin secretos reales.

**Criterios de aceptación:**
- Con `.env` sin variables R2, `R2_ENABLED=False` y el sistema arranca con GCS/stub sin cambios.
- Las variables se leen vía `decouple.config()`; ningún secreto hardcodeado.
- `.env.example` versionado incluye todas las `R2_*`.

## B4. Dependencias `boto3` / `botocore`

**Vía:** skill **`/upgrade-python-deps`** (NO editar `requirements.txt` a mano — regla del proyecto).

- Agregar `boto3` y `botocore` (y `django-storages` ya presente para el backend S3 `storages.backends.s3.S3Boto3Storage`; verificar la variante S3 de django-storages).

**Criterios de aceptación:**
- Deps agregadas a través de la skill; `requirements.txt` actualizado por la herramienta.
- El import de `boto3` en `CloudflareR2Storage` resuelve tras instalar.

---

# FASE C — Generación de PDF (docxtpl + LibreOffice headless + pypdf)

Depende de A (partes, nomenclatura, resolución de facultades) y B (subir/leer binarios de R2).

## C1. Plantillas Word templatizadas (Jinja)

**Carpeta destino:** `apps/convenios/templates/convenio/`.
**Fuentes:** `docs/plantillas_convenio/*.docx` (modelos de convenio) y `docs/modelo_adenda/*.pdf` (adenda).

Cinco plantillas `.docx` templatizadas con sintaxis Jinja de `docxtpl`:
| Archivo | Uso | Selección |
|---|---|---|
| `modelo_1_marco_lima.docx` | Convenio Marco, Lima | `tipo=MARCO` + `es_adenda=False` + `organo_directorio.categoria == "MINSA_DIRIS"` |
| `modelo_2_marco_region.docx` | Convenio Marco, región | `tipo=MARCO` + `es_adenda=False` + `organo_directorio.categoria == "GOBIERNO_REGIONAL"` |
| `modelo_3_especifico_lima.docx` | Específico, Lima | `tipo=ESPECIFICO` + `es_adenda=False` + categoría `MINSA_DIRIS` |
| `modelo_4_especifico_region.docx` | Específico, región | `tipo=ESPECIFICO` + `es_adenda=False` + categoría `GOBIERNO_REGIONAL` |
| `adenda.docx` | Adenda (Marco o Específico) | `es_adenda=True` |

**Placeholders por modelo** (a documentar como contrato del contexto — Jinja `{{ ... }}` y `{% for %}`):
- **Encabezado / partes firmantes:** `{% for parte in partes %}` con `parte.rol_display`, `parte.organo.nombre`, `parte.organo.siglas`, `parte.representante.nombre`, `parte.representante.numero_documento_identidad`, `parte.cargo.nombre` (masculino/femenino según `representante.sexo`), `parte.representante.numero_resolucion_designacion`, `parte.representante.numero_resolucion_facultades`, `parte.domicilio` (dirección de la entidad: `RegionalGovernment.direccion` / `ExecutingUnit.direccion` / `University.direccion_legal` / `Faculty.direccion`; **MINSA fijo** — ver C2).
- **Nomenclatura:** `{{ nomenclatura }}` (solo Marco).
- **Antecedentes:** licenciamiento **SUNEDU** de la universidad; para el Específico, la **cadena de Convenio Marco** (nomenclatura + vigencia del Marco vía `selectors.vigencia_efectiva`); referencia a resolución **CONAPRES/COREPRES** de campos clínicos.
- **Objetivo:** listado de **carreras** de la facultad del convenio (`university_careers` de `convenio.facultad`).
- **Vigencia:** `fecha_inicio`, `fecha_fin`, vigencia efectiva de la cadena de adendas.
- **Adenda:** referencia al `convenio_origen` (nomenclatura/título), nuevo periodo.

**Criterios de aceptación:**
- Existen las 5 plantillas en `apps/convenios/templates/convenio/`.
- Cada placeholder usado por `construir_contexto` (C2) tiene correspondencia en la(s) plantilla(s).
- La selección de plantilla es determinista por `(tipo_convenio, es_adenda, organo_directorio.categoria)`.

## C2. Módulo `pdf.py` — contexto, DOCX y conversión a PDF

**Archivo:** `apps/convenios/pdf.py` (nuevo).

- `construir_contexto(convenio) -> dict`: arma el diccionario Jinja desde `Convention`, sus `partes_firmantes` (A1), `nomenclatura`, `university_careers` de la facultad, `selectors.vigencia_efectiva`, y `selectors.campos_clinicos_del_especifico` (A5). Resuelve el **domicilio** por rol: MINSA fijo **"Av. Salaverry 801, Jesús María, Lima"**; el resto desde la dirección de la entidad de cada parte.
- `generar_docx(convenio) -> bytes|ruta`: selecciona la plantilla (C1), renderiza con `docxtpl.DocxTemplate(...).render(construir_contexto(convenio))`.
- `convertir_a_pdf(docx_path) -> pdf_path`: invoca **LibreOffice headless** vía `subprocess` (`soffice --headless --convert-to pdf --outdir <tmp> <docx>`), en directorio temporal, con timeout y manejo de error en español si `soffice` no está disponible.

**Criterios de aceptación:**
- `construir_contexto` no lanza si faltan datos opcionales (usa valores vacíos/`""`).
- MINSA siempre usa el domicilio fijo, independiente de la entidad.
- La conversión corre en un tmpdir y limpia los temporales; error claro en español si LibreOffice no está instalado.
- Sin lógica de negocio de estado aquí (solo armado de documento); las reglas viven en services.

## C3. `generar_expediente` — proyecto + merge de PDFs

**Archivo:** `apps/convenios/pdf.py`.

- `generar_expediente(convenio) -> pdf_path`: genera el proyecto (C2) y hace **merge** con `pypdf` de los PDFs adjuntos:
  - Resoluciones de designación/facultades de los representantes firmantes (Documentos `Document` de los representantes / actor `REPRESENTANTE`).
  - Tabla de campos clínicos (de `campos_clinicos_del_especifico`, A5) — resoluciones CONAPRES (`RESOL_CONAPRES` / actor `CAMPO_CLINICO`).
  - Logos vía `docxtpl.InlineImage` descargando el binario del storage (R2, B1) con `url_firmada`/descarga temporal.
- Merge con `pypdf.PdfWriter`/`PdfReader`.

**Criterios de aceptación:**
- El expediente concatena el proyecto + los PDFs adjuntos existentes; omite (con log) los faltantes sin fallar.
- Logos se descargan del storage activo (R2 si habilitado) y se incrustan.
- Devuelve un único PDF.

## C4. Endpoints de generación

**Archivos:** `apps/convenios/views.py` (`ConventionViewSet`), `apps/convenios/serializers.py` (responses).

- `@action(detail=True, methods=["post"], url_path="generar-proyecto")`: genera el proyecto (C2), sube a R2 (`self.storage.subir`, mixins.py:146) y versiona vía `adjuntar_documento` con `documento_anexo` `PROYECTO_CONVENIO` (o `PROYECTO_ADENDA` si `es_adenda`). Devuelve `DocumentSerializer`.
- `@action(detail=True, methods=["post"], url_path="generar-expediente")`: genera el expediente (C3), sube a R2 y versiona con `documento_anexo` `EXPEDIENTE`. Devuelve `DocumentSerializer`.
- Ambas acciones son **escritura** → pasan el gate `IsModuleEnabled` (`module_content_type` en views.py:73) y respetan permisos del ViewSet; registran auditoría (vía `adjuntar_documento`).
- `@extend_schema` con response `DocumentSerializer` para OpenAPI.

**Criterios de aceptación:**
- `POST /api/v1/conventions/{id}/generar-proyecto/` crea/versióna un `Document` con el anexo correcto y responde `201`.
- `POST /api/v1/conventions/{id}/generar-expediente/` idem con anexo `EXPEDIENTE`.
- Los binarios quedan en R2 (o storage activo); el versionado por `(objeto, documento_anexo)` funciona (segunda generación → versión 2, previa `REEMPLAZADO`).

## C5. Seed de `documento_anexo` para los anexos de generación

**Archivo:** migración `RunPython` en `apps/internados/migrations/00XX_seed_anexos_proyecto.py` (los `AnnexDocument` viven en `apps/internados`, models.py:78).

- Insertar (idempotente) tres `AnnexDocument` con `tipo_actor="CONVENIO"`, `obligatorio=False`:
  - `PROYECTO_CONVENIO` — "Proyecto de convenio (PDF generado)".
  - `PROYECTO_ADENDA` — "Proyecto de adenda (PDF generado)".
  - `EXPEDIENTE` — "Expediente del convenio (PDF consolidado)".
- Usa `codigo`/`nombre` del catálogo (`Catalog`); patrón idempotente `get_or_create` por `codigo`.

**Criterios de aceptación:**
- La data migration es idempotente (re-ejecutable sin duplicar).
- Los tres anexos existen con `tipo_actor="CONVENIO"` tras `migrate`.
- El `AnnexAttachmentMixin` con `annex_actor="CONVENIO"` (views.py:71) los acepta.

## C6. Dependencias `docxtpl`, `pypdf` + LibreOffice

**Vía:** skill **`/upgrade-python-deps`** para `docxtpl` y `pypdf` (NO editar `requirements.txt` a mano).
- **LibreOffice** es **dependencia de sistema** (no pip): documentar en `.env.example`/README de despliegue (`soffice` en PATH; en contenedor, instalar `libreoffice-writer` o `--calc`/`--writer` mínimo). Documentar el comando `soffice --headless --convert-to pdf`.

**Criterios de aceptación:**
- `docxtpl` y `pypdf` agregados por la skill.
- La necesidad de LibreOffice queda documentada (dev y prod), con mensaje de error en español cuando `soffice` no está disponible (C2).

---

## 4. Reglas de negocio (RN) — dónde vive cada una

| Regla | Capa | Ubicación |
|---|---|---|
| Coherencia parte: representante.organo == organo, cargo.organo_directivo == organo (omitir nulos) | **service** | `services.sincronizar_partes` (A4.1) |
| Composición de roles requerida por tipo/categoría (Marco Lima/región, Específico) | **service** | `_validar_partes_por_tipo` / `_validar_composicion_partes` (A4.2) |
| Nomenclatura solo Marco, requerida al aprobar DIGEP | **service** | `_validar_nomenclatura` en `registrar_evaluacion_tecnica` (A3) |
| Campos clínicos CONAPRES con resolución antes de suscripción (existente) | **service** | `_exigir_campos_clinicos_conapres` (services.py:143) — reutilizado |
| `nomenclatura` no editable por PATCH libre | **serializer** | `ConventionWriteSerializer` / `editables` de `actualizar_convenio` (A3) |
| Solo PDF / tamaño / content-type en subida | **serializer/mixin** | `AnnexUploadSerializer` + `R2_ALLOWED_CONTENT_TYPES` (B3) |
| `numero_resolucion_facultades` opcional | **serializer/modelo** | `OrganRepresentativeSerializer` (A2) |

---

## 5. Checklist de verificación (la ejecuta/aprueba el usuario)

> **NO ejecutar testing automatizado sin consultar al usuario.** Estos comandos son de verificación estructural, con el venv activado (`.venv\Scripts\Activate.ps1`).

- [ ] **Migraciones consistentes:** `python manage.py makemigrations --check --dry-run` → sin cambios pendientes (Fase A y C5 ya migradas).
- [ ] **Aplicar migraciones:** `python manage.py migrate` → aplica el `RenameField codigo→nomenclatura`, `AddField numero_resolucion_facultades` (×2), `CreateModel ConventionParty`, seed de anexos.
- [ ] **Chequeo del sistema:** `python manage.py check` → limpio.
- [ ] **OpenAPI:** `python manage.py spectacular --file schema.yml` (o el endpoint `/api/schema/`) genera sin errores e incluye las acciones `conventions/{id}/parties`, `generar-proyecto`, `generar-expediente` y el campo `nomenclatura`/`partes_firmantes`.
- [ ] **Tipos:** ante errores de mypy/tipos, invocar la skill **`/fix-types`** (no corregir a mano).
- [ ] **Code review:** invocar **`/code-review`** antes de dar por terminada cada fase (modelos/serializers/vistas/migraciones).
- [ ] **Sincronía de docs:** actualizar `docs/db_schema_modulo_01_convenios.md` (nueva tabla `parte_convenio`, columna `nomenclatura`, `numero_resolucion_facultades`) en el mismo cambio de modelo.
- [ ] **Deps:** `boto3`/`botocore` (B4) y `docxtpl`/`pypdf` (C6) agregadas vía `/upgrade-python-deps`; LibreOffice documentado como dep de sistema.

---

## 6. Referencias de schema y código

- `Convention` — `apps/convenios/models.py:738` (tabla `convenio`); campo renombrado `codigo`→`nomenclatura` en `models.py:761`.
- `ConventionParticipant` — `models.py:817` (tabla `participante_convenio`, se conserva).
- `Signature` — `models.py:1047` (tabla `firma`, se conserva).
- `OrganDirectory` — `models.py:303` (tabla `organo_directorio`; choices `ORGAN_DIRECTORY_CATEGORY`).
- `ExecutivePosition` — `models.py:185` (tabla `cargo_ejecutivo`; FK `organo_directivo`).
- `OrganRepresentative` — `models.py:449`; `OrganRepresentativeHistory` — `models.py:494`.
- `Document` — `models.py:1104` (tabla `documento_adjunto`; versionado por `(objeto, documento_anexo)`).
- `AnnexDocument` / `ANNEX_ACTOR` — `apps/internados/models.py:69,78` (tabla `documento_anexo`).
- Servicios: `crear_convenio` `services.py:175`, `actualizar_convenio` `services.py:299`, `crear_adenda` `services.py:245`, `_validar_partes_por_tipo` `services.py:112`, `registrar_evaluacion_tecnica` `services.py:349`, `_exigir_campos_clinicos_conapres` `services.py:143`, `_set_estado` `services.py:55`, `_avanzar_estado` `services.py:72`.
- Estados y orden: `apps/convenios/migrations/0002_seed_catalogos.py:12` (`VALIDADO_TECNICAMENTE` orden 6, `PENDIENTE_OGAJ` orden 11).
- Serializers: `ConventionReadSerializer` `serializers.py:33`, `ConventionWriteSerializer` `serializers.py:96`, `AdendaWriteSerializer` `serializers.py:107`, `_detalle_fk` `serializers.py:174`.
- Storage: `DocumentStorage` `apps/common/storage.py:20`, `GoogleCloudStorage` `storage.py:129`, `get_document_storage` `storage.py:241`, `_nombre_seguro` `storage.py:117`.
- Settings storage: `config/settings/base.py:98` (`STORAGES`), `base.py:137–226` (bloque GCS/django-storages a espejar para R2).
- Mixins: `AnnexAttachmentMixin` `apps/convenios/mixins.py:133` (`annex_actor`), `LogoStorageMixin` `mixins.py:39`.
- ViewSet: `ConventionViewSet` `apps/convenios/views.py:62` (`annex_actor="CONVENIO"` views.py:71, `module_content_type` views.py:73, acción `adenda` views.py:197).
- Servicio documental: `adjuntar_documento` `apps/common/services.py:33`.
