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
