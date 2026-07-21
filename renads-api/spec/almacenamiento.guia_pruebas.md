# Guía de pruebas manuales — Almacenamiento en Google Cloud Storage (GCS)

Guía para QA. Verifica la subida real de documentos (PDF e imágenes) a un bucket
privado de GCS con autenticación **keyless** (ADC + impersonación), la descarga por
**signed URL V4** y el rechazo de archivos no permitidos. No requiere leer el código.

URL base: `http://localhost:8000/api/v1/`
Alternativa interactiva: Swagger en `http://localhost:8000/api/v1/docs/`.

---

## 1. Prerrequisitos

### 1.1 Autenticación keyless con Google Cloud (ADC)

Antes de habilitar GCS, autenticarse una vez en la máquina que corre el servidor:

```bash
gcloud auth application-default login
```

El principal usado debe tener el rol
`roles/iam.serviceAccountTokenCreator` sobre
`renads-storage@renads-cloud.iam.gserviceaccount.com` (así puede impersonar la SA
para firmar). **No** se generan ni descargan claves JSON de service account
(la política de organización lo bloquea).

### 1.2 Habilitar GCS en `.env` (apuntando al bucket de desarrollo)

En el archivo `.env` (copiado de `.env.example`), definir:

```env
GCS_ENABLED=True
GCS_BUCKET_NAME=renads-cloud-media-dev
GCS_PROJECT_ID=renads-cloud
GCS_SIGNING_SA=renads-storage@renads-cloud.iam.gserviceaccount.com
GCS_SIGNED_URL_EXPIRATION=900
GCS_MAX_UPLOAD_BYTES=26214400
```

> Con `GCS_ENABLED=False` (default) el sistema usa el stub por referencia externa y
> **no** contacta GCS; para probar la integración real hay que ponerlo en `True`.

### 1.3 Levantar el servidor

Lo corre el usuario (nunca el agente):

```bash
.venv\Scripts\Activate.ps1
python manage.py runserver
```

### 1.4 Obtener token JWT

```bash
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "<usuario>", "password": "<contrasena>"}'
```

Respuesta esperada (200):

```json
{ "access": "<ACCESS_JWT>", "refresh": "<REFRESH_JWT>" }
```

Usar `Authorization: Bearer <ACCESS_JWT>` en todas las llamadas siguientes.

**Rol requerido:** el usuario debe tener **perfil institucional activo**
(permiso `IsInstitutionalMember`); los superusuarios pasan siempre. Sin perfil
institucional, `upload/` responde **403**.

---

## 2. Datos previos necesarios

Para adjuntar un documento se necesita un **objeto destino** (relación genérica) y su
`ContentType`:

1. **Un `DocumentType`** (catálogo, ya seedeado). Listar y anotar un `id`:
   ```bash
   curl http://localhost:8000/api/v1/document-types/ \
     -H "Authorization: Bearer <ACCESS_JWT>"
   ```
2. **Un objeto destino existente**, p. ej. un convenio. Listar y anotar su `id`:
   ```bash
   curl http://localhost:8000/api/v1/conventions/ \
     -H "Authorization: Bearer <ACCESS_JWT>"
   ```
3. **El `ContentType` (`tipo_contenido`) del objeto destino.** Para entidades
   solicitantes de convenio hay un endpoint auxiliar; para el modelo `Convention`
   se obtiene el `id` de su ContentType vía el admin de Django o consultando el
   esquema. Anotar el `id` numérico de `tipo_contenido` correspondiente al objeto
   destino elegido (p. ej. el ContentType de `convention`).

> Los `id` de `ContentType` dependen de la base de datos; usar los reales del entorno.

---

## 3. Flujo paso a paso

### Paso 3.1 — Subir un PDF (`POST /api/v1/documents/upload/`)

**Rol:** usuario institucional autenticado. Multipart/form-data.

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload/ \
  -H "Authorization: Bearer <ACCESS_JWT>" \
  -F "archivo=@/ruta/convenio.pdf;type=application/pdf" \
  -F "tipo_documento=<ID_DOCUMENT_TYPE>" \
  -F "tipo_contenido=<ID_CONTENT_TYPE>" \
  -F "id_objeto=<ID_OBJETO_DESTINO>" \
  -F "nombre_archivo=convenio.pdf"
```

Respuesta esperada (**201**): un `Document` con `referencia_externa` = **key de GCS**
(formato `{uuid4}-convenio.pdf`, no una URL), `version=1`, `estado=ACTIVO`:

```json
{
  "id": 10,
  "tipo_documento": 1,
  "tipo_contenido": 7,
  "id_objeto": 3,
  "referencia_externa": "3f2b...-convenio.pdf",
  "nombre_archivo": "convenio.pdf",
  "version": 1,
  "estado": "ACTIVO",
  "version_anterior": null,
  "cargado_por": 5,
  "cargado_en": "2026-07-19T10:00:00Z"
}
```

Anotar el `id` del documento devuelto (se usa en 3.3). La respuesta **no** debe
contener ninguna URL del bucket ni tokens.

### Paso 3.2 — Subir una imagen (PNG/JPEG/WEBP)

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload/ \
  -H "Authorization: Bearer <ACCESS_JWT>" \
  -F "archivo=@/ruta/sello.png;type=image/png" \
  -F "tipo_documento=<ID_DOCUMENT_TYPE>" \
  -F "tipo_contenido=<ID_CONTENT_TYPE>" \
  -F "id_objeto=<ID_OBJETO_DESTINO>"
```

Respuesta esperada (**201**). Al omitir `nombre_archivo`, se deriva del archivo subido
(`sello.png`). Si `tipo_documento` coincide con el del PDF sobre el mismo objeto, el
service versiona: el nuevo documento sale con `version=2`, `version_anterior` apuntando
al anterior, y el PDF anterior pasa a `estado=REEMPLAZADO` (RNF-DOC-04).

### Paso 3.3 — Obtener el signed URL de descarga (`GET .../{id}/url-descarga/`)

```bash
curl http://localhost:8000/api/v1/documents/<ID_DOCUMENTO>/url-descarga/ \
  -H "Authorization: Bearer <ACCESS_JWT>"
```

Respuesta esperada (**200**):

```json
{ "url": "https://storage.googleapis.com/renads-cloud-media-dev/3f2b...-convenio.pdf?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Signature=..." }
```

Verificar:
- La URL apunta a `storage.googleapis.com` con parámetros de firma **V4**
  (`X-Goog-Algorithm=GOOG4-RSA-SHA256`, `X-Goog-Signature`, `X-Goog-Expires`).
- Abrir la URL en el navegador **dentro de la ventana de 15 min** descarga el archivo.
- Pasados ~15 min (o alterando la firma), la URL responde **403** de GCS
  (`SignatureDoesNotMatch` / `ExpiredToken`): confirma que el objeto es privado y
  **no** hay acceso público.

### Paso 3.4 — Borrar el documento (`DELETE .../{id}/`)

```bash
curl -X DELETE http://localhost:8000/api/v1/documents/<ID_DOCUMENTO>/ \
  -H "Authorization: Bearer <ACCESS_JWT>"
```

Respuesta esperada (**204**). El binario se elimina del bucket. Repetir el borrado
(o si el objeto ya no está en GCS) **no** debe fallar: el backend tolera "objeto no
existe" y registra un aviso.

---

## 4. Casos de regla de negocio / validación (deben fallar)

### 4.1 Archivo no permitido (`.exe`) → 400

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload/ \
  -H "Authorization: Bearer <ACCESS_JWT>" \
  -F "archivo=@/ruta/malware.exe;type=application/octet-stream" \
  -F "tipo_documento=<ID_DOCUMENT_TYPE>" \
  -F "tipo_contenido=<ID_CONTENT_TYPE>" \
  -F "id_objeto=<ID_OBJETO_DESTINO>"
```

Esperado (**400**), mensaje en español:

```json
{ "archivo": ["Tipo de archivo no permitido. Se aceptan únicamente: application/pdf, image/png, image/jpeg, image/webp."] }
```

**Importante:** verificar que **no** se subió nada al bucket (la validación ocurre
antes de contactar GCS).

### 4.2 Extensión incoherente con el content-type → 400

Subir un archivo con `type=application/pdf` pero nombre `documento.png` (o viceversa):

Esperado (**400**):

```json
{ "archivo": ["La extensión del archivo no corresponde con su tipo de contenido."] }
```

### 4.3 Tamaño excedido (> 25 MiB) → 400

Subir un PDF/imagen mayor a `GCS_MAX_UPLOAD_BYTES`:

Esperado (**400**):

```json
{ "archivo": ["El archivo supera el tamaño máximo permitido (25 MiB)."] }
```

### 4.4 Objeto destino inexistente → 400

Enviar un `id_objeto` que no existe para el `tipo_contenido` dado:

Esperado (**400**):

```json
{ "id_objeto": ["El objeto destino indicado no existe."] }
```

### 4.5 Sin autenticación → 401

Llamar a `upload/` sin cabecera `Authorization`:

Esperado (**401**).

### 4.6 Autenticado sin perfil institucional → 403

Llamar a `upload/` con un usuario autenticado que no tiene perfil institucional activo:

Esperado (**403**), mensaje: `El usuario no tiene un perfil institucional activo.`

---

## 5. Verificación de que el stub sigue funcionando (opcional)

Con `GCS_ENABLED=False` en `.env` y reiniciando el servidor, `upload/` sigue
respondiendo **201** pero sin contactar GCS: `referencia_externa` será el nombre
saneado que envíe el cliente y `url-descarga/` devolverá esa referencia tal cual (no
un signed URL). Esto confirma que deshabilitar GCS no rompe el flujo.

---

## 6. Resumen de roles/permisos por endpoint

| Endpoint | Método | Permiso requerido |
|----------|--------|-------------------|
| `/api/v1/auth/token/` | POST | Público (credenciales válidas) |
| `/api/v1/document-types/` | GET | Autenticado |
| `/api/v1/conventions/` | GET | Autenticado + institucional + ámbito |
| `/api/v1/documents/upload/` | POST | Autenticado + institucional (`IsInstitutionalMember`) |
| `/api/v1/documents/{id}/url-descarga/` | GET | Autenticado + institucional |
| `/api/v1/documents/{id}/` | DELETE | Autenticado + institucional |

---

# Guía de pruebas manuales — Etapa 2 (logos + PDFs de anexos)

## Prerrequisitos
1. Servidor: `python manage.py runserver` (lo corre el usuario). Base:
   `http://localhost:8000/api/v1/`. Swagger interactivo en `/api/v1/docs/`.
2. Token JWT: `POST /api/v1/auth/token/` con `{username, password}` de un usuario
   `Administrador RENADS` (para logos y anexos de autoridad/representante).
   Usar `Authorization: Bearer <access>` en todas las llamadas.
3. Almacenamiento: por defecto `GCS_ENABLED=False` → stub (la `referencia_externa`/
   `referencia_logo` es la key/ruta recibida y las "URLs firmadas" devuelven la key
   tal cual). Para probar contra GCS real, definir en `.env`
   `GCS_ENABLED=True`, `GCS_BUCKET_NAME=renads-cloud-media-dev` y autenticar ADC
   (`gcloud auth application-default login`).

## Datos previos
- Una entidad con logo: p. ej. una universidad (`GET /api/v1/universities/` → toma un `id`).
- Anexos del catálogo maestro: `GET /api/v1/annex-documents/?tipo_actor=AUTORIDAD_UNIVERSIDAD`
  y `?tipo_actor=REPRESENTANTE` (seedeados). Anota los `id`.
- Una autoridad de universidad (`GET /api/v1/university-authorities/` → `id`) y un
  representante (`GET /api/v1/representatives/` → `id`).

## Flujo A — Logo institucional (imagen)
Rol requerido: `Administrador RENADS`.

1. Subir/reemplazar logo (multipart):
   ```
   POST /api/v1/universities/{id}/upload-logo/
   Content-Type: multipart/form-data
   archivo=@logo.png
   ```
   Esperado: `200` con `{"referencia_logo": "<key>", "url": "<signed_url>"}`.
   Un segundo `upload-logo` reemplaza la key y (con GCS) borra la anterior.

2. Obtener signed URL del logo:
   ```
   GET /api/v1/universities/{id}/logo-url/
   ```
   Esperado: `200` con `{"url": "<signed_url>"}`. Si la entidad no tiene logo → `404`
   `{"detail": "La entidad no tiene un logo cargado."}`.

3. Caso que debe fallar (tipo no imagen):
   ```
   POST /api/v1/universities/{id}/upload-logo/  con archivo=@doc.pdf
   ```
   Esperado: `400` "Tipo de imagen no permitido. Se aceptan únicamente: image/png, image/jpeg, image/webp."

4. Caso permiso (RNF-SEG): con token de un usuario NO admin →
   `POST .../upload-logo/` responde `403`.

## Flujo B — Anexo (PDF) de autoridad de universidad
Rol requerido: `Administrador RENADS`.

1. Checklist inicial:
   ```
   GET /api/v1/university-authorities/{id}/annex-checklist/
   ```
   Esperado: `200` con la lista de anexos `AUTORIDAD_UNIVERSIDAD` activos, cada uno con
   `adjuntado=false`, `documento_id=null`, `version=null`.

2. Adjuntar el PDF (multipart):
   ```
   POST /api/v1/university-authorities/{id}/annex-upload/
   documento_anexo=<id de un anexo AUTORIDAD_UNIVERSIDAD>
   archivo=@resolucion.pdf
   ```
   Esperado: `201` con el `Document` (`version=1`, `estado="ACTIVO"`, `documento_anexo`
   apuntando al anexo).

3. Re-subir el mismo anexo (versionado): repetir el paso 2 con otro PDF.
   Esperado: `201` con `version=2`; la versión previa queda `REEMPLAZADO`
   (verificable en `GET /api/v1/documents/?id_objeto={id}&tipo_contenido=<ct_authority>`).

4. Checklist tras adjuntar: el anexo aparece con `adjuntado=true`, `version=2`.

5. Caso que debe fallar (actor no coincide — RN de enforcement):
   ```
   POST /api/v1/university-authorities/{id}/annex-upload/
   documento_anexo=<id de un anexo tipo_actor=REPRESENTANTE>
   archivo=@x.pdf
   ```
   Esperado: `400` `{"documento_anexo": "El anexo seleccionado no corresponde a este tipo de actor."}`.

6. Caso que debe fallar (no PDF):
   ```
   POST .../annex-upload/  con archivo=@imagen.png
   ```
   Esperado: `400` "Tipo de archivo no permitido. El anexo debe adjuntarse en formato PDF."

## Flujo C — Anexo (PDF) de representante
Idéntico al Flujo B usando `representatives/{id}/annex-upload|annex-checklist` y anexos
de `tipo_actor=REPRESENTANTE`. Rol `Administrador RENADS`.

> Los anexos del actor `INTERNO` (estudiante) se prueban en
> `spec/internados.guia_pruebas.md` (sección F2/F3).
