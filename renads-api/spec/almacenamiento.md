# Spec — Feature transversal `almacenamiento` (Google Cloud Storage)

Lista de tareas exactas para integrar el **almacenamiento real en Google Cloud
Storage (GCS)** de documentos/adjuntos (PDF e imágenes) de RENADS, reemplazando
el stub `ReferenciaExternaStorage`. Producido por el agente **spec** (SDD). El
agente **implement** ejecuta estas tareas en orden; el **validator** revisa
contra este documento.

## Resumen

Los documentos de RENADS (`Document`, relación genérica, versionado RNF-DOC-04)
se guardan hoy solo como `referencia_externa` (stub sin backend). Esta feature
introduce un backend `GoogleCloudStorage` que cumple el `Protocol`
`DocumentStorage` de `apps/common/storage.py`, con:

- **Subida real** del binario a un bucket privado de GCS (`renads-cloud-media-dev`
  / `renads-cloud-media-prod`), devolviendo la key del objeto como
  `referencia_externa`.
- **Descarga por signed URL V4** de corta duración (nunca URLs públicas — el
  bucket tiene Public Access Prevention = enforced).
- **Borrado** del objeto.
- **Autenticación keyless (sin claves de SA):** ADC + impersonación de la SA
  `renads-storage@renads-cloud.iam.gserviceaccount.com` vía
  `google.auth.impersonated_credentials`, firmando signed URLs con el endpoint
  IAM SignBlob.

La infraestructura GCP (proyecto, buckets, SA, roles) **ya está provisionada**;
este spec NO incluye tareas de creación de infraestructura. Se agrega una
**acción de subida real** (`upload`, multipart) al `DocumentViewSet` que valida
tipo/tamaño, sube vía `storage.subir(...)` y luego llama
`adjuntar_documento(...)`. El `create` por `referencia_externa` se conserva para
adjuntos subidos externamente. La selección de backend (GCS vs stub) se decide
por settings.

**Convenciones:** clases y endpoints en inglés; docstrings, comentarios y `.md`
en español; variables de entorno `GCS_*`. No crear archivos de testing (fuera de
alcance MVP).

**Archivos a tocar:**
- `requirements.txt` (nueva dependencia).
- `config/settings/base.py`, `config/settings/dev.py`, `config/settings/prod.py`.
- `apps/common/storage.py` (backend `GoogleCloudStorage` + factory de selección).
- `apps/common/serializers.py` *(nuevo, si no existe)* o el serializer de subida
  donde corresponda (ver T4).
- `apps/convenios/views.py` (`DocumentViewSet`: acción `upload` + uso del factory).
- `.env.example` / documentación de variables.

---

## T1 — Dependencia `google-cloud-storage`

- **T1.1** Agregar `google-cloud-storage` a `requirements.txt` (incluye
  transitivamente `google-auth`, que aporta `google.auth.impersonated_credentials`).
- **T1.2** Instalar en el entorno virtual (`.venv\Scripts\Activate.ps1`) y
  fijar la versión resuelta en `requirements.txt`.
- **T1.3** **Nota de proceso:** CLAUDE.md pide usar `/upgrade-python-deps` para
  tocar `requirements.txt`; al tratarse del **alta de una dependencia nueva** se
  instala y se agrega la línea explícitamente, y el implement debe **señalar en
  su reporte** que este add no pasó por la skill (se reserva la skill para
  upgrades masivos/pre-release).

**Criterio de aceptación:** `pip show google-cloud-storage` responde con la
versión instalada; la línea figura en `requirements.txt`; `python -c "import
google.cloud.storage, google.auth.impersonated_credentials"` no lanza error.

---

## T2 — Settings `GCS_*` por entorno (`config/settings/`)

Todas las variables se leen con `decouple.config` (ya disponible en `base.py`).

- **T2.1** En `config/settings/base.py` añadir un bloque de configuración GCS con
  defaults seguros (backend deshabilitado si no está configurado):
  - `GCS_ENABLED = config("GCS_ENABLED", default=False, cast=bool)` — flag que
    elige backend GCS vs stub.
  - `GCS_PROJECT_ID = config("GCS_PROJECT_ID", default="renads-cloud")`.
  - `GCS_BUCKET_NAME = config("GCS_BUCKET_NAME", default="")` — bucket del
    entorno (obligatorio si `GCS_ENABLED`).
  - `GCS_SIGNING_SA = config("GCS_SIGNING_SA", default="renads-storage@renads-cloud.iam.gserviceaccount.com")`
    — SA objetivo de la impersonación (firma signed URLs vía IAM SignBlob).
  - `GCS_OBJECT_PREFIX = config("GCS_OBJECT_PREFIX", default="")` — prefijo/carpeta
    opcional para organizar las keys.
  - `GCS_SIGNED_URL_EXPIRATION = config("GCS_SIGNED_URL_EXPIRATION", default=900, cast=int)`
    — segundos de validez del signed URL (default 15 min).
  - `GCS_MAX_UPLOAD_BYTES = config("GCS_MAX_UPLOAD_BYTES", default=26214400, cast=int)`
    — tamaño máximo de subida (default 25 MiB).
  - `GCS_ALLOWED_CONTENT_TYPES` — lista fija/constante de content-types
    permitidos: `application/pdf`, `image/png`, `image/jpeg`, `image/webp`.
- **T2.2** En `config/settings/dev.py`: dejar que `GCS_ENABLED` se controle por
  `.env` (default `False` → stub). Documentar que para probar GCS en dev se pone
  `GCS_ENABLED=True` y `GCS_BUCKET_NAME=renads-cloud-media-dev`.
- **T2.3** En `config/settings/prod.py`: previsto `GCS_ENABLED=True` con
  `GCS_BUCKET_NAME=renads-cloud-media-prod`. No sobrescribir valores; solo se
  documenta el `.env` de producción (no hardcodear el bucket).

**Criterio de aceptación:** `manage.py check` limpio con y sin las variables
definidas; con `GCS_ENABLED=False` el sistema arranca usando el stub; ningún
valor sensible queda hardcodeado (no hay claves de SA en el repo — auth keyless).

---

## T3 — Backend `GoogleCloudStorage` (`apps/common/storage.py`)

Implementar la clase `GoogleCloudStorage` cumpliendo estructuralmente el
`Protocol` `DocumentStorage` (métodos `subir`, `url_firmada`, `eliminar`). No
modificar la firma del `Protocol` ni del stub `ReferenciaExternaStorage`.

- **T3.1** **Credenciales impersonadas (keyless):** construir credenciales base
  con ADC (`google.auth.default(...)`) y derivar credenciales impersonadas con
  `google.auth.impersonated_credentials.Credentials`:
  - `target_principal = settings.GCS_SIGNING_SA`.
  - `target_scopes = ["https://www.googleapis.com/auth/devstorage.read_write"]`.
  - Estas credenciales permiten obtener tokens efímeros y **firmar signed URLs
    V4 vía IAM SignBlob** sin necesidad de una clave de SA.
  - Construir el cliente `storage.Client(project=settings.GCS_PROJECT_ID,
    credentials=impersonated_credentials)`. Cachear cliente/credenciales a nivel
    de instancia (crear el backend una sola vez, ver T5).
- **T3.2** `subir(self, archivo, ruta: str) -> str`:
  - Genera/usa una **key organizada**: `f"{prefijo}/{uuid4()}-{nombre_seguro}"`
    (prefijo = `GCS_OBJECT_PREFIX`; sanear el nombre para evitar separadores de
    ruta). El parámetro `ruta` puede usarse como key propuesta o como nombre base
    — el implement fija el criterio y lo documenta en el docstring.
  - Sube el binario con `blob.upload_from_file(archivo, content_type=...)` o
    `upload_from_string`, **fijando el content-type** correcto.
  - Devuelve la **key del objeto** (no una URL) como `referencia_externa`.
- **T3.3** `url_firmada(self, referencia: str) -> str`:
  - Genera un **signed URL V4** de descarga: `blob.generate_signed_url(version="v4",
    expiration=timedelta(seconds=settings.GCS_SIGNED_URL_EXPIRATION), method="GET")`.
  - Debe firmar usando las credenciales impersonadas (IAM SignBlob), sin clave.
  - Nunca devuelve URL pública ni la key en crudo.
- **T3.4** `eliminar(self, referencia: str) -> None`:
  - `bucket.blob(referencia).delete()`; tolerar de forma controlada el caso
    "objeto no existe" (log/no-op) para que el borrado del `Document` no falle si
    el binario ya no está.
- **T3.5** Docstrings en español describiendo el mecanismo keyless (ADC +
  impersonación) y que los objetos son privados servidos solo por signed URLs.

**Criterio de aceptación:** `GoogleCloudStorage` es asignable a una variable
tipada `DocumentStorage` (cumple el Protocol); `subir` retorna una key, no una
URL; `url_firmada` retorna una URL `https://storage.googleapis.com/...` con
parámetros de firma V4; no se instancia ninguna clave/JSON de SA en ningún punto.

---

## T4 — Selección de backend / factory (`apps/common/storage.py`)

- **T4.1** Añadir `get_document_storage() -> DocumentStorage`: devuelve una
  instancia de `GoogleCloudStorage` cuando `settings.GCS_ENABLED` es `True` y
  `GCS_BUCKET_NAME` está definido; en caso contrario devuelve el stub
  `ReferenciaExternaStorage`. Debe cachear la instancia (una sola construcción del
  cliente GCS por proceso).
- **T4.2** Mantener `storage_por_defecto` compatible: puede redefinirse para que
  resuelva vía el factory (p. ej. lazy) **sin romper** los imports existentes en
  `apps/convenios/views.py` (que hoy importan `storage_por_defecto`). Alternativa
  aceptable: dejar `storage_por_defecto` como stub y que el ViewSet use el factory
  (ver T5.2); el implement elige una y la documenta, pero el `DocumentViewSet`
  debe terminar usando el backend seleccionado por settings.

**Criterio de aceptación:** con `GCS_ENABLED=False`, el ViewSet opera con el stub
(comportamiento actual intacto); con `GCS_ENABLED=True` + bucket, el ViewSet
opera contra GCS. La construcción del cliente GCS ocurre una sola vez.

---

## T5 — Acción de subida real en `DocumentViewSet` (`apps/convenios/views.py`)

- **T5.1** **Serializer de subida** (`DocumentUploadSerializer`, en el módulo de
  serializers correspondiente): campos `archivo` (`FileField`), `tipo_documento`,
  `tipo_contenido`, `id_objeto`, `nombre_archivo` (opcional; si falta, derivar del
  nombre del archivo subido). Validaciones **de serializer**:
  - **Content-type / extensión permitidos:** solo `application/pdf`, `image/png`,
    `image/jpeg`, `image/webp` (validar contra `GCS_ALLOWED_CONTENT_TYPES`;
    contemplar extensión como refuerzo). Mensaje de error **en español**.
  - **Tamaño máximo:** `archivo.size <= GCS_MAX_UPLOAD_BYTES`; error en español si
    excede.
  - Reusar la validación existente de `DocumentWriteSerializer` sobre
    `tipo_contenido`+`id_objeto` (que el objeto destino exista).
- **T5.2** Acción `@action(detail=False, methods=["post"], url_path="upload",
  parser_classes=[MultiPartParser])` llamada `upload`:
  - Resuelve el `storage` del ViewSet vía el factory de T4 (o
    `self.storage = get_document_storage()`).
  - Valida con `DocumentUploadSerializer`; obtiene el objeto destino
    (`tipo_contenido.get_object_for_this_type(pk=id_objeto)`).
  - Llama `referencia = self.storage.subir(archivo, ruta=<nombre>)`.
  - Llama `adjuntar_documento(objeto, tipo_documento=..., nombre_archivo=...,
    referencia_externa=referencia, usuario=request.user)` (versionado + auditoría
    ya cubiertos por el service).
  - Devuelve `DocumentSerializer(documento).data` con `status=201`.
  - Registrar `upload` en `http_method_names` no es necesario (POST ya está
    permitido). Documentar la ruta resultante:
    `POST /api/v1/documents/upload/` (multipart).
- **T5.3** Conservar el `create` actual por `referencia_externa` (adjuntos ya
  subidos externamente) y `perform_destroy` (que llama `self.storage.eliminar`) y
  la acción `url-descarga` (que llama `self.storage.url_firmada`) — todos deben
  quedar apuntando al backend seleccionado por settings.

**Criterio de aceptación:** subir un PDF por `upload/` crea un `Document` con
`referencia_externa` = key de GCS; `GET .../{id}/url-descarga/` devuelve un signed
URL válido y descargable durante la ventana de expiración; subir un `.exe` (o
content-type no permitido) responde **400** con mensaje en español y **no** sube
nada al bucket; superar el tamaño máximo responde 400.

---

## T6 — Seguridad y permisos

- **T6.1** La acción `upload` **reutiliza** los `permission_classes` del
  `DocumentViewSet` (`[IsAuthenticated, IsInstitutionalMember]`): subida
  restringida a usuarios institucionales autenticados. No relajar permisos.
- **T6.2** **Nunca** exponer URLs públicas: el bucket es privado (UBLA +
  Public Access Prevention enforced); la única vía de lectura es el signed URL V4
  de corta duración de `url-descarga`.
- **T6.3** Verificar que la respuesta de `upload` y `create` no filtre la URL del
  bucket ni tokens; solo se expone la `referencia_externa` (key) y, bajo demanda,
  el signed URL efímero.

**Criterio de aceptación:** un usuario no autenticado recibe 401 en `upload`; un
autenticado no institucional recibe 403; ninguna respuesta contiene URLs públicas
del objeto.

---

## T7 — Documentación de variables (`.env` / docs)

- **T7.1** Documentar en `.env.example` (o el archivo de ejemplo del proyecto) las
  variables `GCS_ENABLED`, `GCS_PROJECT_ID`, `GCS_BUCKET_NAME`, `GCS_SIGNING_SA`,
  `GCS_OBJECT_PREFIX`, `GCS_SIGNED_URL_EXPIRATION`, `GCS_MAX_UPLOAD_BYTES`, con
  valores de ejemplo por entorno (dev → `renads-cloud-media-dev`, prod →
  `renads-cloud-media-prod`).
- **T7.2** Nota explícita (comentario en `.env.example` y/o docstring): la
  autenticación es **ADC + impersonación (keyless)**. Requisitos del entorno:
  - El usuario/CI corre `gcloud auth application-default login`.
  - El principal ADC tiene `roles/iam.serviceAccountTokenCreator` sobre
    `renads-storage@renads-cloud.iam.gserviceaccount.com`.
  - **No** se generan ni almacenan claves JSON de service account
    (`constraints/iam.disableServiceAccountKeyCreation` bloquea su creación).

**Criterio de aceptación:** el `.env.example` lista todas las variables `GCS_*`
con comentarios en español y la nota de auth keyless; ningún secreto real
commiteado.

---

## Referencias

- **Código existente:**
  - `apps/common/storage.py` — `Protocol DocumentStorage`, stub
    `ReferenciaExternaStorage`, `storage_por_defecto` (T3, T4).
  - `apps/common/services.py` — `adjuntar_documento(...)` (versionado RNF-DOC-04,
    transacción + auditoría) reutilizado por la acción `upload` (T5).
  - `apps/convenios/views.py` `DocumentViewSet` — atributo `storage`, `create`,
    `perform_destroy`, acción `url-descarga` (T5).
  - `apps/convenios/models.py` `Document` — `referencia_externa`, `nombre_archivo`,
    `version`, `estado`, `version_anterior`, `tipo_contenido`+`id_objeto`.
  - `config/settings/{base,dev,prod}.py` — `decouple.config` (T2).
- **Infraestructura GCP (ya provisionada, no crear):** proyecto `renads-cloud`;
  buckets `renads-cloud-media-dev` / `renads-cloud-media-prod` (us-central1,
  STANDARD, UBLA ON, Public Access Prevention enforced, cifrado Google-managed);
  SA `renads-storage@renads-cloud.iam.gserviceaccount.com` con
  `roles/storage.objectAdmin` solo en esos buckets.
- **Requerimientos no funcionales:** RNF-DOC-01/02/03 (gestión documental PDF),
  RNF-DOC-04 (versionado), RNF-SEG-01/02/03 (auth/autorización por rol/perfil),
  RNF-AUD-01/02 (auditoría — cubierta por `adjuntar_documento`).
- **Librerías:** `google-cloud-storage`, `google.auth.impersonated_credentials`
  (firma V4 vía IAM SignBlob, keyless).

## Fuera de alcance (este spec)

- Testing automatizado (fuera de alcance MVP).
- Creación/aprovisionamiento de infraestructura GCP (buckets, SA, roles, IAM,
  políticas de organización) — ya provisionada.
- Migración/copia de documentos históricos ya guardados como `referencia_externa`
  hacia GCS.
- Generación de miniaturas, antivirus/escaneo de contenido, deduplicación.
- CDN, URLs públicas o resumable/multipart uploads del lado cliente.
- Cambios en el modelo `Document` o su schema (se reutiliza `referencia_externa`
  como key del objeto; no se agregan columnas).

> **Nota:** el alcance de la **Etapa 1** (arriba) no toca el modelo `Document`. La
> **Etapa 2** (abajo) sí agrega una columna nueva (`documento_anexo`) a `Document`
> y una columna `referencia_logo` a `Ipress`; ver esa sección para el detalle.

---

# Etapa 2 — Flujo de adjunto real: logos (imágenes) y PDFs de anexos por entidad

Lista de tareas exactas para el **flujo de adjunto real** que consume el backend
de almacenamiento de la Etapa 1 (`get_document_storage()` → GCS o stub). Cubre
dos capacidades independientes que comparten infraestructura:

1. **Logos institucionales (imágenes)** para 5 entidades, guardados como una key
   simple en la columna `referencia_logo` de cada entidad (sin versionado, sin
   `Document`): se sube la imagen, se borra la anterior y se guarda la nueva key.
2. **PDFs de anexos (declaraciones juradas / documentos por actor)** ligados al
   catálogo `documentos_anexos` (`internados.AnnexDocument`), guardados como
   `Document` versionado (reutiliza `adjuntar_documento`) discriminando por el
   anexo concreto adjuntado.

**Decisiones ya confirmadas por el usuario (no re-decidir):** validación de
imágenes por MIME + extensión (sin Pillow / sin `ImageField`); logos sin
versionado; anexos versionados por `(objeto, documento_anexo)`; `annex-upload`
solo acepta PDF; enforcement de `tipo_actor` del anexo contra el tipo de entidad.

**Convenciones RENADS:** clases y endpoints en inglés (`upload-logo`, `logo-url`,
`annex-upload`, `annex-checklist`); `db_table`/columnas/`help_text`/docstrings/`.md`
en español; mixins y serializers reutilizables. No crear tests (fuera de alcance
MVP). Cada acción nueva lleva `@extend_schema` para OpenAPI/Swagger.

**Archivos a tocar (Etapa 2):**
- `apps/convenios/models.py` (`Ipress.referencia_logo`; `Document.documento_anexo`).
- `apps/common/services.py` (`adjuntar_documento`: parámetro `documento_anexo`).
- `apps/common/storage.py` — sin cambios de firma (se reutiliza el backend).
- `apps/convenios/serializers.py` (`LogoUploadSerializer`, `AnnexUploadSerializer`).
- `apps/convenios/mixins.py` *(nuevo)* — `LogoStorageMixin`, `AnnexAttachmentMixin`.
- `apps/convenios/views.py` (`_entity_viewset` params `logo=`/`annex_actor=`;
  `IpressViewSet`, `RepresentativeViewSet`).
- `apps/internados/views.py` (`StudentViewSet` — ver también `spec/internados.md`).
- Migraciones a mano en `apps/convenios/migrations/` (AddField ×2 + seed
  `DocumentType ANEXO`).
- Documentación: `docs/api_almacenamiento_frontend.md` *(nuevo)* + sincronización
  de `docs/db_schema_*`, `docs/db_schema.html`, `docs/diccionario_datos.docx`,
  `CLAUDE.md`, `spec/almacenamiento.md`, `spec/internados.md`.

---

## E2.T1 — Columna `referencia_logo` en `Ipress` (`apps/convenios/models.py`)

- **E2.T1.1** Agregar a `Ipress` el campo, homogéneo con las 4 entidades que ya lo
  tienen (`University`, `RegionalGovernment`, `RegionalOrgan`, `ExecutingUnit`):
  ```
  referencia_logo = models.CharField(
      "referencia del logo", max_length=500, blank=True,
      help_text="Referencia externa del logo (repositorio externo)",
  )
  ```
  Ubicarlo antes de `activo`, con el mismo verbose/`help_text` en español que las
  demás entidades (no inventar variantes).

**Criterio de aceptación:** las **5** entidades (universidad, gobierno regional,
órgano regional, unidad ejecutora, IPRESS) exponen `referencia_logo`;
`makemigrations --check` detecta el AddField; el resto del modelo `Ipress` intacto.

---

## E2.T2 — FK `documento_anexo` en `Document` (`apps/convenios/models.py`)

- **E2.T2.1** Agregar a `Document` una FK **nullable** al catálogo maestro de
  anexos, con referencia por string para no crear import circular
  `convenios`↔`internados`:
  ```
  documento_anexo = models.ForeignKey(
      "internados.AnnexDocument", on_delete=models.SET_NULL,
      db_column="documento_anexo_id", null=True, blank=True, related_name="+",
      help_text="Anexo (declaración jurada) al que corresponde este documento; nulo para documentos que no son anexos",
  )
  ```
- **E2.T2.2** Es **retrocompatible**: los documentos existentes (convenios, etc.)
  quedan con `documento_anexo = NULL`. No se altera `referencia_externa`,
  `version`, `estado`, `version_anterior`, `tipo_documento`.

**Criterio de aceptación:** `Document.documento_anexo` es opcional; `SET_NULL`
preserva documentos si se borra un `AnnexDocument`; el schema del módulo 1 y el ER
global reflejan la nueva columna; `makemigrations --check` detecta el AddField.

---

## E2.T3 — Versionado por anexo en `adjuntar_documento` (`apps/common/services.py`)

- **E2.T3.1** Agregar a `adjuntar_documento(...)` un parámetro **opcional**
  `documento_anexo=None`. Firma resultante (kw-only, tras los actuales):
  `adjuntar_documento(objeto, *, tipo_documento, nombre_archivo, referencia_externa, usuario, documento_anexo=None)`.
- **E2.T3.2** Regla de versionado:
  - Si `documento_anexo` **is None** → comportamiento **actual intacto**: busca el
    activo previo por `(tipo_contenido, id_objeto, tipo_documento)`.
  - Si `documento_anexo` **no es None** → busca el activo previo por
    `(tipo_contenido, id_objeto, documento_anexo)` (el discriminador pasa a ser el
    anexo, no el `tipo_documento`). El `select_for_update()` y el marcado del
    anterior como `REEMPLAZADO` se mantienen igual.
  - En ambos casos, `Document.objects.create(...)` persiste `documento_anexo`
    (None o la instancia). La auditoría (`registrar_auditoria`) no cambia.
- **E2.T3.3** No romper llamadas existentes (`DocumentViewSet.create`,
  `DocumentViewSet.upload`): al no pasar `documento_anexo`, siguen versionando por
  `tipo_documento`.

**Criterio de aceptación:** subir dos PDFs del **mismo** `documento_anexo` al mismo
estudiante ⇒ el 1.º pasa a `REEMPLAZADO` y el 2.º queda `ACTIVO` `version=2`
enlazado por `version_anterior`; subir PDFs de **anexos distintos** al mismo
estudiante ⇒ cadenas de versión independientes; las llamadas sin `documento_anexo`
mantienen exactamente el comportamiento previo (regresión nula).

---

## E2.T4 — Seed `DocumentType ANEXO` (`apps/convenios/migrations/`)

- **E2.T4.1** Migración de datos que crea/actualiza (`get_or_create` idempotente) un
  `DocumentType` con `codigo="ANEXO"`, `nombre="Declaración jurada / anexo"`,
  `activo=True`. Es el `tipo_documento` por defecto del flujo de anexos (E2.T7).
- **E2.T4.2** El código resuelve el `DocumentType` `ANEXO` por `codigo` (no por PK)
  para que el mixin de anexos no dependa de ids de la BD.

**Criterio de aceptación:** tras migrar existe un único `DocumentType` con
`codigo="ANEXO"`; re-ejecutar la migración no duplica ni falla; `document-types`
lo lista.

---

## E2.T5 — `LogoUploadSerializer` (`apps/convenios/serializers.py`)

- **E2.T5.1** `LogoUploadSerializer(serializers.Serializer)` con un único campo
  `archivo = serializers.FileField(...)`. Validación **de serializer** en
  `validate_archivo` (mensajes en español), reutilizando las constantes de la
  Etapa 1:
  - Content-type ∈ **solo imágenes**: `image/png`, `image/jpeg`, `image/webp`
    (subconjunto de `GCS_ALLOWED_CONTENT_TYPES`; **excluir** `application/pdf`).
    Definir una constante local `LOGO_CONTENT_TYPES` para no aceptar PDF.
  - Extensión coherente con el MIME vía `EXTENSIONES_POR_CONTENT_TYPE` (reutilizar
    el dict existente).
  - Tamaño `archivo.size <= settings.GCS_MAX_UPLOAD_BYTES`.

**Criterio de aceptación:** un PNG/JPEG/WEBP válido pasa; un PDF o `.exe` responde
**400** en español; superar el tamaño responde 400; no requiere Pillow.

---

## E2.T6 — Mixin `LogoStorageMixin` (`apps/convenios/mixins.py`)

Mixin reusable para ViewSets de entidades con columna `referencia_logo`. No asume
serializer del modelo; usa el storage por settings y la auditoría transversal.

- **E2.T6.1** Atributos/utilidades del mixin:
  - Resuelve el backend vía `get_document_storage()` (property `storage`, igual que
    `DocumentViewSet`).
  - Opera sobre `self.get_object()` (entidad con atributo `referencia_logo`).
- **E2.T6.2** Acción `POST {id}/upload-logo/`
  (`@action(detail=True, methods=["post"], url_path="upload-logo",
  parser_classes=[MultiPartParser, FormParser])`, `@extend_schema(request=LogoUploadSerializer,
  responses=...)`):
  - Valida con `LogoUploadSerializer`.
  - `nueva_key = self.storage.subir(archivo, ruta=archivo.name)`.
  - Si `entidad.referencia_logo` ya tenía valor → `self.storage.eliminar(logo_anterior)`
    (tolerante a inexistencia, como el backend). El borrado del anterior ocurre
    **después** de subir la nueva (no dejar la entidad sin logo si la subida falla).
  - Guarda `entidad.referencia_logo = nueva_key`
    (`save(update_fields=["referencia_logo"])`) y registra auditoría
    (`registrar_auditoria(request.user, "ACTUALIZAR", entidad, nombre_campo="referencia_logo", valor_anterior=logo_anterior, valor_nuevo=nueva_key)`).
  - Responde `200` con `{"referencia_logo": <key>, "url": <signed_url>}` (llama
    `self.storage.url_firmada(nueva_key)`).
- **E2.T6.3** Acción `GET {id}/logo-url/`
  (`@action(detail=True, methods=["get"], url_path="logo-url")`, `@extend_schema`):
  - Si la entidad no tiene `referencia_logo` → **404** con
    `{"detail": "La entidad no tiene un logo cargado."}`.
  - En otro caso → `200` con `{"url": self.storage.url_firmada(referencia_logo)}`.
- **E2.T6.4** Permisos: hereda los `permission_classes` del ViewSet destino
  (entidades: `[IsAuthenticated, IsAdminRoleOrReadOnly]`). La subida/borrado es
  escritura ⇒ solo `Administrador RENADS`; `logo-url` es lectura para autenticados.
  No relajar permisos en el mixin.

**Criterio de aceptación:** con `GCS_ENABLED=True`, `upload-logo` sube la imagen,
borra la key anterior si existía, persiste la nueva key y devuelve un signed URL
descargable; un segundo `upload-logo` reemplaza y borra el binario previo;
`logo-url` sin logo devuelve 404; un usuario no-admin recibe 403 en `upload-logo`.

---

## E2.T7 — `AnnexUploadSerializer` + Mixin `AnnexAttachmentMixin`

### E2.T7.1 — Serializer (`apps/convenios/serializers.py`)
- `AnnexUploadSerializer(serializers.Serializer)`:
  - `documento_anexo = serializers.PrimaryKeyRelatedField(queryset=AnnexDocument.objects.filter(activo=True), ...)`
    (import perezoso de `apps.internados.models.AnnexDocument` dentro del módulo
    para evitar ciclo; o queryset resuelto en `__init__`).
  - `archivo = serializers.FileField(...)` con `validate_archivo`: **solo**
    `application/pdf` (no imágenes), extensión `.pdf`, tamaño
    `<= settings.GCS_MAX_UPLOAD_BYTES`. Mensajes en español.
  - `nombre_archivo` opcional (si falta, se deriva de `archivo.name`).
  - La validación de que `documento_anexo.tipo_actor` coincide con la entidad se
    hace en el **mixin** (necesita `annex_actor` del ViewSet), no en el serializer.

### E2.T7.2 — Mixin (`apps/convenios/mixins.py`)
Mixin reusable con atributo de clase **`annex_actor`** (valor de `ANNEX_ACTOR`:
`"INTERNO"` / `"AUTORIDAD_UNIVERSIDAD"` / `"REPRESENTANTE"`). Property `storage`
vía `get_document_storage()`.

- **Acción `POST {id}/annex-upload/`** (`@action(detail=True, methods=["post"],
  url_path="annex-upload", parser_classes=[MultiPartParser, FormParser])`,
  `@extend_schema(request=AnnexUploadSerializer, responses=DocumentSerializer)`):
  - Valida con `AnnexUploadSerializer`.
  - **Enforcement de actor:** si `documento_anexo.tipo_actor != self.annex_actor`
    → **400** con mensaje en español (p. ej. "El anexo seleccionado no corresponde
    a este tipo de actor."). (El `queryset` ya exige `activo=True`.)
  - Resuelve el `DocumentType` `ANEXO` por `codigo` (E2.T4).
  - `referencia = self.storage.subir(archivo, ruta=nombre_archivo)`.
  - `adjuntar_documento(entidad, tipo_documento=<ANEXO>, nombre_archivo=...,
    referencia_externa=referencia, usuario=request.user, documento_anexo=<anexo>)`
    (versionado por anexo — E2.T3; auditoría incluida).
  - Responde `201` con `DocumentSerializer(documento).data`.
- **Acción `GET {id}/annex-checklist/`** (`@action(detail=True, methods=["get"],
  url_path="annex-checklist")`, `@extend_schema`):
  - Lista los `AnnexDocument` activos de `tipo_actor == self.annex_actor`.
  - Para cada uno, cruza con los `Document` `ACTIVO` de esa entidad
    (`tipo_contenido`+`id_objeto`) que apuntan a ese `documento_anexo`, devolviendo
    por item: `documento_anexo` (id), `codigo`, `nombre`, `obligatorio`,
    `adjuntado` (bool), `documento_id`, `version`, `referencia_externa`.
  - `200` con la lista. Es la base del **checklist requeridos vs. adjuntados**: el
    front resalta los `obligatorio=True` con `adjuntado=False`.
- **Permisos:** hereda los del ViewSet destino. `annex-upload` es escritura;
  `annex-checklist` lectura.

**Criterio de aceptación:** `annex-upload` con un anexo cuyo `tipo_actor` no
coincide con `annex_actor` → 400; con anexo correcto y PDF → 201 y `Document`
versionado por `documento_anexo`; subir con content-type no PDF → 400;
`annex-checklist` devuelve todos los anexos activos del actor con su estado
`adjuntado`/`version`; los anexos `obligatorio` sin adjuntar son identificables.

---

## E2.T8 — Aplicar mixins a los ViewSets destino

### Logos (5 entidades)
- **E2.T8.1** Extender `_entity_viewset(...)` en `apps/convenios/views.py` con un
  parámetro `logo: bool = False`: cuando `True`, incluir `LogoStorageMixin` en las
  bases del ViewSet generado. Aplicar `logo=True` a: `regional-governments`,
  `regional-organs`, `executing-units`, `universities`.
- **E2.T8.2** `IpressViewSet` (custom, ya subclase de `_entity_viewset(m.Ipress, ...)`):
  agregar `LogoStorageMixin` a sus bases (herencia directa), sin perder la acción
  existente `autorizar-sede-docente`.

### Anexos (3 entidades)
- **E2.T8.3** Extender `_entity_viewset(...)` con un parámetro
  `annex_actor: str | None = None`: cuando se define, incluir `AnnexAttachmentMixin`
  y fijar el atributo `annex_actor`. Aplicar `annex_actor="AUTORIDAD_UNIVERSIDAD"`
  a `university-authorities`.
- **E2.T8.4** `RepresentativeViewSet` (custom): agregar `AnnexAttachmentMixin` con
  `annex_actor = "REPRESENTANTE"`.
- **E2.T8.5** `StudentViewSet` (`apps/internados/views.py`): agregar
  `AnnexAttachmentMixin` con `annex_actor = "INTERNO"` (detalle en
  `spec/internados.md`, tarea **T-F2.2**). El mixin vive en `apps/convenios/mixins.py`
  y se importa desde internados (patrón ya usado con `_entity_viewset`).

**Criterio de aceptación:** los 8 endpoints objetivo aparecen en OpenAPI:
- `POST/GET /api/v1/{universities|regional-governments|regional-organs|executing-units|ipress}/{id}/upload-logo/` y `.../logo-url/`.
- `POST/GET /api/v1/{students|university-authorities|representatives}/{id}/annex-upload/` y `.../annex-checklist/`.
`manage.py check` y `spectacular` sin error; las acciones preexistentes de esos
ViewSets siguen funcionando.

---

## E2.T9 — Migraciones a mano (`apps/convenios/migrations/`)

- **E2.T9.1** Migración de estructura: `AddField Ipress.referencia_logo`
  (E2.T1) + `AddField Document.documento_anexo` (E2.T2). La FK apunta a
  `internados.AnnexDocument`, por lo que la migración debe declarar en
  `dependencies` la migración `("internados", "0008_academicperiod_annexdocument_student_fks")`
  (donde vive `AnnexDocument`). Nombre sugerido:
  `00XX_ipress_logo_document_annex.py` (ajustar al último número disponible).
- **E2.T9.2** Migración de datos: seed `DocumentType` `ANEXO` (E2.T4),
  idempotente (`get_or_create`), dependiente de E2.T9.1.
- **E2.T9.3** Tras aplicarlas, `makemigrations --check` no debe reportar cambios
  pendientes.

**Criterio de aceptación:** `migrate` aplica ambas sin error; el orden respeta la
dependencia con `internados`; re-`migrate` es idempotente; `makemigrations --check`
limpio.

---

## E2.T10 — Documentación para el front (OBLIGATORIA) y sincronización de docs

- **E2.T10.1** **Nuevo** `docs/api_almacenamiento_frontend.md` (en español) con:
  - **Tabla de endpoints**: método, ruta, cuerpo (multipart `archivo` / campos),
    respuesta JSON de ejemplo, para los 8 endpoints (`upload-logo`, `logo-url`,
    `annex-upload`, `annex-checklist`) y una referencia a `documents/upload`,
    `documents/{id}/url-descarga` de la Etapa 1.
  - **Content-types y tamaño**: logos → PNG/JPEG/WEBP; anexos y documentos → PDF;
    máximo `GCS_MAX_UPLOAD_BYTES` (25 MiB).
  - **Flujo de logo**: `upload-logo` (sube/reemplaza) → `logo-url` (signed URL
    efímero para mostrar el logo).
  - **Flujo de anexos**: `annex-checklist` (qué falta) → `annex-upload` (adjuntar)
    → nueva versión al re-subir el mismo anexo.
  - **Errores en español** (400 tipo/tamaño/actor no coincide; 401/403; 404 sin
    logo) y **roles** por acción (escritura `Administrador RENADS`; universidad
    donde aplique; lectura autenticados).
  - Nota de seguridad: los binarios son privados; nunca URL pública; los signed URL
    caducan (`GCS_SIGNED_URL_EXPIRATION`).
- **E2.T10.2** `@extend_schema` en **todas** las acciones nuevas
  (`upload-logo`, `logo-url`, `annex-upload`, `annex-checklist`) para que Swagger
  documente request/response.
- **E2.T10.3** Sincronizar el schema del proyecto:
  - `docs/db_schema_modulo_01_convenios.md`: columna `documento`.`documento_anexo_id`
    y `ipress`.`referencia_logo`.
  - `docs/db_schema_modulo_02_internados.md`: referencia al flujo de anexos por
    estudiante (ahora **en alcance**) y su relación con `documento`.
  - `docs/db_schema_er_global.md` y `docs/db_schema.html`: nueva arista
    `documento → documentos_anexos` y la columna de logo en `ipress`.
  - Regenerar `docs/diccionario_datos.docx` con las dos columnas nuevas.
- **E2.T10.4** `CLAUDE.md`: **levantar el "fuera de alcance"** del adjunto real de
  declaraciones juradas — la nota de `AnnexDocument` decía "el flujo de adjunto
  real por estudiante queda fuera de alcance del MVP"; actualizarla para indicar
  que el adjunto real de PDFs de anexos (por estudiante, autoridad de universidad y
  representante) **ya está cubierto** vía `annex-upload`/`annex-checklist`.
- **E2.T10.5** Sincronizar `spec/almacenamiento.md` (este documento — Etapa 2) y
  `spec/internados.md` (tarea `annex-upload`/`annex-checklist` de `StudentViewSet`,
  ver **T-F2.2**).

**Criterio de aceptación:** `docs/api_almacenamiento_frontend.md` existe y lista los
8 endpoints con ejemplos; Swagger muestra las 8 acciones; los `.md`/`.html`/`.docx`
de schema reflejan `documento_anexo` e `ipress.referencia_logo`; `CLAUDE.md` ya no
declara el adjunto real de anexos como fuera de alcance.

---

## Referencias (Etapa 2)

- **Código existente:** `apps/common/storage.py` (`get_document_storage`),
  `apps/common/services.py` (`adjuntar_documento`, `registrar_auditoria`),
  `apps/convenios/serializers.py` (`DocumentUploadSerializer`,
  `EXTENSIONES_POR_CONTENT_TYPE`, `DocumentSerializer`), `apps/convenios/views.py`
  (`_entity_viewset`, `IpressViewSet`, `RepresentativeViewSet`, `DocumentViewSet`),
  `apps/internados/views.py` (`StudentViewSet`), `apps/internados/models.py`
  (`AnnexDocument`, `ANNEX_ACTOR`).
- **Modelos con `referencia_logo` (ya existente):** `University`,
  `RegionalGovernment`, `RegionalOrgan`, `ExecutingUnit` — se añade `Ipress`.
- **Requerimientos no funcionales:** RNF-DOC-01/02/03 (gestión documental PDF/
  imágenes), RNF-DOC-04 (versionado — reutilizado por `adjuntar_documento` en el
  flujo de anexos), RNF-SEG-01/02/03 (auth/autorización por rol/perfil),
  RNF-AUD-01/02 (auditoría de logo y de anexo).
- **Settings/constantes:** `GCS_ALLOWED_CONTENT_TYPES`, `GCS_MAX_UPLOAD_BYTES`,
  `GCS_SIGNED_URL_EXPIRATION` (Etapa 1).

## Fuera de alcance (Etapa 2)

- Testing automatizado (fuera de alcance MVP).
- Validación de imágenes con Pillow (dimensiones, recorte) o `ImageField`: la
  validación es por MIME + extensión + tamaño.
- Miniaturas/thumbnails, conversión de formato, antivirus, deduplicación.
- Estados de presentación/aprobación del anexo (revisado/observado): el checklist
  solo distingue `adjuntado` vs. no adjuntado por versión activa.
- Logos versionados en `Document`: los logos viven como una única key en
  `referencia_logo` (se reemplaza y se borra la anterior).
- Adjuntar anexos a entidades distintas de las 3 indicadas (estudiante, autoridad
  de universidad, representante).
