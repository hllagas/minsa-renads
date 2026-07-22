# Validación — Feature transversal `almacenamiento` (Google Cloud Storage)

**Resultado: APROBADO — sin errores altos/medios.**

Fecha: 2026-07-19. Revisión del `validator` (SDD) contra `spec/almacenamiento.md`,
`docs/arquitectura_desarrollo.md` y `CLAUDE.md`. No se modificó código de la app.

## Sanidad técnica ejecutada

- `manage.py check` (settings `dev`): **0 issues**.
- `manage.py spectacular --file schema.yml`: **0 errores** (46 warnings preexistentes
  en otros ViewSets por `AnonymousUser` en `get_queryset`, ajenos a esta feature).
  El path `POST /api/v1/documents/upload/` aparece en el esquema con
  `requestBody` `multipart/form-data` (`$ref DocumentUpload`) y `security: jwtAuth`.
  `schema.yml` eliminado tras la verificación.
- Verificado en runtime que `google.auth.impersonated_credentials.Credentials`
  expone `signer_email` y `sign_bytes` (firma V4 keyless vía IAM SignBlob);
  `google-cloud-storage==3.13.0` instalado.

## Cobertura del spec (T1..T7)

- **T1** OK — `google-cloud-storage==3.13.0` en `requirements.txt` con comentario.
- **T2** OK — bloque `GCS_*` en `config/settings/base.py` con defaults seguros
  (`GCS_ENABLED=False`, `GCS_BUCKET_NAME=""`, SA de firma, prefijo, expiración 900,
  máx. 25 MiB, `GCS_ALLOWED_CONTENT_TYPES` fija PDF/PNG/JPEG/WEBP). `dev.py` y
  `prod.py` documentan el `.env` sin hardcodear el bucket.
- **T3** OK — `GoogleCloudStorage` cumple el Protocol (`subir`/`url_firmada`/`eliminar`).
  Credenciales impersonadas keyless (ADC → `impersonated_credentials.Credentials`,
  `target_scopes=[devstorage.read_write]`); cliente/bucket perezosos y cacheados;
  `subir` fija `content_type`, rebobina el archivo y devuelve la key (no URL);
  `url_firmada` genera signed URL V4 GET (firma automática por `signer_email`/
  `sign_bytes` de las credenciales impersonadas, sin key); `eliminar` tolera
  `NotFound` con log. Mensajes en español ante falta de ADC / config / librería.
- **T4** OK — `get_document_storage()` con `@lru_cache(maxsize=1)`: GCS si
  `GCS_ENABLED` y `GCS_BUCKET_NAME`, si no el stub; `storage_por_defecto` conservado
  como stub (import en `views.py` no se rompe, aunque ya usa el factory).
- **T5** OK — `DocumentUploadSerializer` (archivo + metadatos, validación tipo/tamaño);
  acción `upload` (`detail=False`, `POST`, `url_path="upload"`,
  `parser_classes=[MultiPartParser, FormParser]`) valida → `storage.subir` →
  `adjuntar_documento` → `DocumentSerializer` 201. `create` por referencia externa,
  `perform_destroy` y `url-descarga` conservados y apuntando al backend por settings.
- **T6** OK — `upload` hereda `permission_classes=[IsAuthenticated, IsInstitutionalMember]`;
  nunca se generan URLs públicas (solo signed URL V4); las respuestas exponen solo
  la key (`referencia_externa`), no la URL del bucket ni tokens.
- **T7** OK — `.env.example` lista todas las `GCS_*` con comentarios en español y la
  nota de auth keyless (ADC + `serviceAccountTokenCreator`, sin claves JSON).

## Corrección técnica y seguridad

- Firma keyless correcta: no se instancia ninguna clave/JSON de SA en ningún punto;
  la firma V4 la resuelve `blob.generate_signed_url` apoyándose en las credenciales
  impersonadas. No es necesario pasar `service_account_email`/`access_token`
  explícitos con `google-cloud-storage` 3.x (las credenciales impersonadas ya
  implementan el mixin de firma).
- Con `GCS_ENABLED=False` (o bucket vacío) el sistema opera con el stub sin romper
  imports ni comportamiento actual.
- Mínimo privilegio respetado: `objectAdmin` a nivel de objeto es suficiente
  (`bucket.blob(...)` para subir/firmar/borrar; no se piden operaciones de bucket-admin).
- Validación de tipo/tamaño en el serializer: rechaza content-type no permitido,
  extensión incoherente y tamaño excedido, con mensajes en español y **antes** de
  contactar el bucket (no sube nada si falla la validación).

## Convenciones RENADS

- Clases y endpoints en inglés; docstrings/comentarios en español; variables `GCS_*`.
- Vistas delgadas: la lógica de almacenamiento vive en `apps/common/storage.py` y el
  versionado/auditoría en `adjuntar_documento` (service); la acción `upload` solo
  orquesta.

## Observaciones menores (severidad baja — no bloquean)

- `[BAJA]` `apps/convenios/serializers.py:298` — cuando `nombre_archivo` no se envía,
  se deriva de `archivo.name` sin sanear; el saneo real ocurre luego en
  `_nombre_seguro` dentro de `storage.subir`, por lo que no hay riesgo de path
  injection. Sin acción requerida.
- `[BAJA]` `config/api_urls.py` / esquema — la respuesta declarada de `upload/` en
  OpenAPI referencia `DocumentUpload` (esquema de entrada) en lugar de `Document`.
  Es cosmético del esquema; la vista responde `DocumentSerializer`. Puede anotarse
  con `@extend_schema(responses=DocumentSerializer)` en una iteración futura.

Ambas son de severidad baja; conforme a la regla del validator, se genera la guía de
pruebas manuales en `spec/almacenamiento.guia_pruebas.md`.

---

# Validación — Etapa 2 (adjunto real: logos + PDFs de anexos)

**Resultado: APROBADO — sin errores altos/medios.**

Fecha: 2026-07-20. Revisión del `validator` (SDD) contra `spec/almacenamiento.md`
(Etapa 2, E2.T1..E2.T10), `docs/db_schema_modulo_01/02`, ER global y `CLAUDE.md`.
No se modificó código de la app.

## Sanidad técnica ejecutada

- `manage.py check` (settings `dev`): **0 issues**.
- `manage.py makemigrations --check --dry-run`: **No changes detected**.
- `manage.py spectacular --file schema.tmp.yml`: **0 errores** (49 warnings
  preexistentes por `AnonymousUser` en `get_queryset`, ajenos a esta feature).
  Temporal eliminado tras verificar.
- **16 rutas F2 confirmadas** en el esquema:
  `upload-logo`/`logo-url` para `universities`, `regional-governments`,
  `regional-organs`, `executing-units`, `ipress` (5×2); `annex-upload`/`annex-checklist`
  para `students`, `university-authorities`, `representatives` (3×2).
- **BD fresca**: `migrate` sobre un sqlite nuevo (settings temporal, eliminado tras
  la prueba) aplica todo el grafo sin error, incluyendo el orden
  `internados.0008 → convenios.0010 (FK a AnnexDocument) → convenios.0011 (seed ANEXO)`.

## Cobertura del spec (E2.T1..E2.T10)

- **E2.T1** OK — `Ipress.referencia_logo` (`CharField(500, blank)`, verbose/help_text
  homogéneos con las 4 entidades existentes), antes de `activo`.
- **E2.T2** OK — `Document.documento_anexo` FK string `internados.AnnexDocument`,
  `SET_NULL`, `null/blank`, `related_name="+"`, `db_column="documento_anexo_id"`.
  Retrocompatible (documentos existentes con `NULL`).
- **E2.T3** OK — `adjuntar_documento(..., documento_anexo=None)` kw-only tras los
  actuales; discriminador por `documento_anexo` cuando viene, por `tipo_documento`
  cuando `None`; `select_for_update` y marcado `REEMPLAZADO` intactos; persiste
  `documento_anexo`. Retrocompatibilidad de `DocumentViewSet.create`/`upload` (sin anexo).
- **E2.T4** OK — seed idempotente `DocumentType codigo="ANEXO"` (`get_or_create`),
  resuelto por `codigo` en el mixin.
- **E2.T5** OK — `LogoUploadSerializer` con `LOGO_CONTENT_TYPES` (solo PNG/JPEG/WEBP,
  excluye PDF), extensión coherente y tamaño `<= GCS_MAX_UPLOAD_BYTES`. Sin Pillow.
- **E2.T6** OK — `LogoStorageMixin`: property `storage` vía `get_document_storage()`;
  `upload-logo` sube primero y borra la key anterior después (no deja sin logo si
  falla), persiste con `update_fields`, audita `ACTUALIZAR` y responde
  `{referencia_logo, url}`; `logo-url` 404 en español sin logo. `@extend_schema` en ambas.
- **E2.T7** OK — `AnnexUploadSerializer` (solo `application/pdf`, `.pdf`, tamaño) con
  `ActiveAnnexDocumentField` (queryset perezoso `activo=True`); `AnnexAttachmentMixin`
  con enforcement `documento_anexo.tipo_actor != annex_actor` → 400 en español;
  `annex-upload` versiona por `(objeto, documento_anexo)` vía `adjuntar_documento`;
  `annex-checklist` cruza el catálogo activo del actor con los `Document` `ACTIVO`,
  devolviendo `adjuntado`/`documento_id`/`version`/`referencia_externa`. `@extend_schema` en ambas.
- **E2.T8** OK — `_entity_viewset(..., logo=, annex_actor=)` inyecta los mixins;
  `logo=True` en 4 entidades + `IpressViewSet` hereda `LogoStorageMixin` directo (sin
  perder `autorizar-sede-docente`); `annex_actor` en `university-authorities`,
  `RepresentativeViewSet` y `StudentViewSet` (INTERNO). Sin duplicación de mixin en
  `IpressViewSet` (el factory no pasa `logo=True`).
- **E2.T9** OK — `convenios/0010` (AddField ×2, `dependencies` con
  `internados.0008`) + `convenios/0011` (seed ANEXO). Grafo válido en BD fresca.
- **E2.T10** OK — `docs/api_almacenamiento_frontend.md` presente; schema M1
  (`documento.documento_anexo_id`, `ipress.referencia_logo`), M2 (flujo de anexos por
  estudiante), ER global y `db_schema.html` sincronizados; `CLAUDE.md` ya no declara
  el adjunto real de anexos como fuera de alcance.

## Seguridad y convenciones

- Mixins heredan `permission_classes` del ViewSet destino: logos → `IsAdminRoleOrReadOnly`
  (escritura solo `Administrador RENADS`); anexos de estudiante →
  `IsUniversityOrReadOnly` con excepción del rol `Interno` para sus propias DJ.
- Nunca URL pública: solo signed URL V4 efímero (`logo-url`, `annex-upload` response,
  `url-descarga`). No se expone la URL del bucket ni tokens.
- Clases/acciones en inglés; `db_table`/columnas/`help_text`/docstrings/`.md` en español.

## Observaciones menores (severidad baja — no bloquean)

- `[BAJA]` `apps/convenios/mixins.py:95` — `upload-logo` responde `200` (Response por
  defecto). El spec E2.T6.2 indica `200`, correcto; se documenta por claridad.
- `[BAJA]` `annex-checklist` no restringe con object-scope propio en
  `university-authorities`/`representatives` (heredan `IsAdminRoleOrReadOnly`, lectura
  para autenticados), coherente con el resto de entidades master-data. Sin acción.

Conforme a la regla del validator, se actualiza la guía de pruebas manuales en
`spec/almacenamiento.guia_pruebas.md` (sección Etapa 2).

---

# Validación — Etapa 4 (migrar `referencia_logo` a `ImageField`)

**Resultado: APROBADO — sin errores altos/medios.**

Fecha: 2026-07-21. Revisión del `validator` (SDD) contra `spec/almacenamiento.md`
(Etapa 4), `docs/arquitectura_desarrollo.md`, `CLAUDE.md` y el schema del módulo 1.
No se modificó código de la app. Decisiones del usuario (Opción A django-storages,
firma keyless impersonada, sin backfill) se toman como fijadas, no como hallazgos.

## Sanidad técnica ejecutada

- `manage.py check` (settings `dev`): **System check identified no issues (0 silenced)**.
- `manage.py makemigrations --check --dry-run`: **No changes detected** (los 5 modelos
  concuerdan con la migración `0013_logo_imagefield`).
- Import de `config.settings.prod` con `GCS_ENABLED=False`: **STORAGES["default"] =
  FileSystemStorage** y el import NO construye credenciales impersonadas ni falla.
- Dependencias en el venv: `django-storages==1.14.6`, `Pillow==11.3.0` (import OK);
  `storages` presente en `INSTALLED_APPS`.

## Cobertura del spec (Etapa 4)

- **Modelos** OK — las **5** entidades (`RegionalGovernment` L181, `RegionalOrgan`
  L211, `ExecutingUnit` L241, `Ipress` L275, `University` L392) usan
  `models.ImageField("logo", upload_to="<carpeta_entidad>/", max_length=500, null=True,
  blank=True, help_text=...)`. `max_length=500` explícito (no el default 100), columna
  DB `referencia_logo` preservada (sin `db_column`, por convención), `upload_to` por
  entidad (`gobierno_regional/`, `organo_regional/`, `unidad_ejecutora/`, `ipress/`,
  `universidad/`). `verbose_name`/`help_text` en español y homogéneos entre las 5.
- **Migración 0013** OK — `dependencies=[('convenios','0012_document_texto_extraido')]`;
  5 `AlterField` (`CharField`→`ImageField`), no destructiva, **sin `RunPython`**; nota
  de backfill documentada en el docstring. `makemigrations --check` limpio.
- **`LogoStorageMixin`** OK — ya **no** usa `get_document_storage()` para logos: asigna
  el binario al `ImageField` y `save(update_fields=["referencia_logo"])`; Django persiste
  vía `STORAGES["default"]`. Borrado del binario anterior **después** de guardar el nuevo,
  **solo si difiere** (`logo_anterior != nueva_key`) y **tolerante a fallo**
  (`try/except` con `logger.warning`), obtenido del `storage` del propio campo. Contrato
  `{referencia_logo, url}` preservado (`url = entidad.referencia_logo.url`); `logo-url`
  devuelve 404 en español si el campo está vacío. `@extend_schema` en ambas acciones.
- **`AnnexAttachmentMixin` (PDFs)** OK — sin regresión: sigue resolviendo el backend
  documental custom vía `get_document_storage()` (property `storage`, L146-148), sube por
  `self.storage.subir(...)`, extrae texto (Document AI) y versiona por
  `(objeto, documento_anexo)`. No comparte ruta con el flujo de logos.
- **Settings** OK — `base.py`: `STORAGES["default"] = FileSystemStorage`; bloque `GS_*`
  (`GS_BUCKET_NAME`/`GS_PROJECT_ID` heredan de `GCS_*`, `GS_LOCATION="logos"`,
  `GS_QUERYSTRING_AUTH=True`, `GS_DEFAULT_ACL=None`, `GS_EXPIRATION=GCS_SIGNED_URL_EXPIRATION`,
  `GS_FILE_OVERWRITE=False`), `MEDIA_URL`/`MEDIA_ROOT`, `storages` en `INSTALLED_APPS`.
  `prod.py`: solo pasa a `storages.backends.gcloud.GoogleCloudStorage` cuando
  `GCS_ENABLED and GS_BUCKET_NAME`; en ese ramo inyecta `credentials=get_impersonated_credentials()`
  (import perezoso dentro del `if`, no en tiempo de módulo). Con GCS off → FileSystemStorage.
- **Firma keyless centralizada** OK — `apps/common/storage.get_impersonated_credentials()`
  construye ADC + `impersonated_credentials.Credentials` (`target_principal=GCS_SIGNING_SA`,
  scope `devstorage.read_write`), reutilizado por el backend documental custom
  (`GoogleCloudStorage._get_bucket`, L170) y por django-storages (`OPTIONS["credentials"]`
  en prod). Errores en español si faltan librerías/ADC.
- **Convivencia de backends** OK — PDFs/anexos por el custom bajo `GCS_OBJECT_PREFIX`;
  imágenes por django-storages bajo `GS_LOCATION="logos"`. Mismo bucket, prefijos
  distintos, sin colisión.
- **Logo fuera del CRUD de escritura** OK — `_auto_serializer` expone `referencia_logo`
  como `SerializerMethodField` (solo lectura, `.url` o `None`); no hay campo de escritura
  de logo en los serializers CRUD. La subida es exclusiva de `upload-logo`. `LogoUploadSerializer`
  solo tiene el campo `archivo`.
- **Docs** OK — `docs/db_schema_modulo_01_convenios.md` documenta las 5 columnas
  `referencia_logo varchar(500)` como `ImageField`/nullable; `docs/api_almacenamiento_frontend.md`
  actualizado (sección logos = `ImageField`, `.url` = signed URL V4, contrato de endpoints
  sin cambios, prefijo `GS_LOCATION`). `.env.example` lista las vars `GS_*`.
- **Idioma** OK — `verbose_name`/`help_text`/docstrings/mensajes/`.md` en español; código,
  clases y endpoints en inglés; columna `referencia_logo` y descripciones en español.

## Observaciones menores (severidad baja — no bloquean)

- `[BAJA]` `dev.py` mantiene `FileSystemStorage`; para probar `.url` como signed URL real
  hay que replicar el bloque `STORAGES["default"]` de `prod.py` (ya documentado en dev.py).
- `[BAJA]` Sin backfill por decisión del usuario: si existieran logos productivos con el
  layout de keys del backend custom (`{GCS_OBJECT_PREFIX}/{uuid4}-...`), `.url` no
  resolvería el binario (paths no coinciden con `GS_LOCATION`/`upload_to`). No aplica hoy
  (no hay logos cargados); ya advertido en el docstring de la migración 0013.

Conforme a la regla del validator, se actualiza la guía de pruebas manuales de logos en
`spec/almacenamiento.guia_pruebas.md` (Flujo A) para el comportamiento de la Etapa 4.
