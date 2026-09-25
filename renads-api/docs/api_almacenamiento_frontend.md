# API de almacenamiento — Guía para el frontend

Guía de los endpoints de **adjunto real** de RENADS (logos de entidades y PDFs de
anexos por actor), servidos sobre el backend de almacenamiento (Google Cloud
Storage en producción; stub por referencia externa en desarrollo). Todas las rutas
cuelgan de `/api/v1/` y requieren autenticación (JWT institucional).

> **Versionado por anexo:** cada adjunto se guarda como `documento_adjunto` (tabla
> `documento_adjunto`, ex `documento`) versionado por el par `(objeto,
> documento_anexo)`. La FK `documento_anexo` es **obligatoria** (único
> discriminador). El nombre de archivo se usa solo como ruta de storage; no se
> persiste en `documento_adjunto`.

> **Seguridad:** los binarios se guardan en un bucket **privado** (sin acceso
> público). La única forma de leerlos es un **signed URL V4 de corta duración**
> (`GCS_SIGNED_URL_EXPIRATION`, 15 min por defecto). Nunca se expone una URL
> pública ni la clave cruda del objeto.

## Content-types y tamaño

| Tipo de adjunto | Content-types aceptados | Extensiones |
|-----------------|-------------------------|-------------|
| **Logo** (imagen) | `image/png`, `image/jpeg`, `image/webp` | `.png`, `.jpg`, `.jpeg`, `.webp` |
| **Anexo** (declaración jurada) | `application/pdf` | `.pdf` |
| **Documento** (Etapa 1) | `application/pdf`, `image/png`, `image/jpeg`, `image/webp` | ídem |

- Tamaño máximo por archivo: **25 MiB** (`GCS_MAX_UPLOAD_BYTES`).
- Las subidas van como **`multipart/form-data`**.

## Autenticación

Todas las rutas requieren el header `Authorization: Bearer <access>`. El token se obtiene en
`POST /api/v1/auth/token/`:

```bash
curl -X POST https://api.renads.minsa.gob.pe/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "12345678", "password": "mi-clave"}'
# → { "access": "...", "refresh": "...", "debe_cambiar_password": false }
```

```js
const { access } = await fetch("/api/v1/auth/token/", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ username: "12345678", password: "mi-clave" }),
}).then((r) => r.json());
```

> En los ejemplos siguientes, `$TOKEN` / `access` es ese `access` token. En `multipart/form-data`
> **no** fijes manualmente `Content-Type`: el navegador (o curl con `-F`) pone el `boundary`.

---

## Logos institucionales (5 entidades)

El logo se guarda en un campo **`ImageField`** (`referencia_logo`) de la entidad:
**no hay versionado**. Al subir uno nuevo se reemplaza y se borra el binario
anterior. Desde la Etapa 4 el binario lo escribe Django a través de
`STORAGES["default"]` (django-storages sobre el bucket privado de GCS en producción;
`FileSystemStorage` en dev), usando una carpeta por entidad (`upload_to`). El valor
`referencia_logo` que devuelve el API es ahora el **path/URL del `ImageField`** (ya no
una clave opaca), y `url` es su `.url` = un **signed URL V4 efímero**. **El contrato de
los endpoints no cambia:** `upload-logo` sigue devolviendo `{referencia_logo, url}` y
`logo-url` sigue devolviendo `{url}`.

> Cambio de forma del campo: en los **serializers CRUD** de las 5 entidades,
> `referencia_logo` se serializa ahora como **URL de lectura** (`.url` o `null` si no
> hay logo), no como clave. El logo **no** se sube por el CRUD (`POST/PUT` de la
> entidad ignoran ese campo): se sube por `upload-logo`.

Entidades con logo: `universities`, `regional-governments`, `regional-organs`,
`executing-units`, `ipress`.

| Método | Ruta | Cuerpo (multipart) | Respuesta |
|--------|------|--------------------|-----------|
| `POST` | `/api/v1/{entidad}/{id}/upload-logo/` | `archivo`: imagen (PNG/JPEG/WEBP) | `200` `{ "referencia_logo": "<path>", "url": "https://storage.googleapis.com/..." }` |
| `GET`  | `/api/v1/{entidad}/{id}/logo-url/` | — | `200` `{ "url": "https://storage.googleapis.com/..." }` o `404` |

### Flujo de logo
1. `POST .../upload-logo/` con el campo `archivo` → sube/reemplaza y devuelve
   `referencia_logo` + un signed URL para mostrarlo de inmediato.
2. `GET .../logo-url/` cada vez que se necesite renderizar el logo (el signed URL
   caduca; se vuelve a pedir bajo demanda).

Ejemplo de request de `upload-logo` (subir logo de la universidad `10`):

```bash
curl -X POST https://api.renads.minsa.gob.pe/api/v1/universities/10/upload-logo/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "archivo=@logo-unmsm.png;type=image/png"
```

```js
const fd = new FormData();
fd.append("archivo", fileInput.files[0]); // File PNG/JPEG/WEBP
const res = await fetch("/api/v1/universities/10/upload-logo/", {
  method: "POST",
  headers: { Authorization: `Bearer ${access}` }, // sin Content-Type manual
  body: fd,
}).then((r) => r.json());
// res.url → signed URL listo para <img src>
```

Obtener el signed URL bajo demanda (`logo-url`):

```bash
curl https://api.renads.minsa.gob.pe/api/v1/universities/10/logo-url/ \
  -H "Authorization: Bearer $TOKEN"
```

Ejemplo de respuesta de `upload-logo`:

```json
{
  "referencia_logo": "logos/universidad/logo-unmsm.png",
  "url": "https://storage.googleapis.com/renads-cloud-media-prod/logos/universidad/logo-unmsm.png?X-Goog-Signature=..."
}
```

> `referencia_logo` es el path del `ImageField` (prefijo `GS_LOCATION` = `logos/` +
> `upload_to` de la entidad, p. ej. `universidad/`). `url` es un signed URL V4 que
> caduca (`GS_EXPIRATION`); vuelve a pedirse por `logo-url` cuando expire.

---

## Anexos (PDFs de declaraciones juradas por actor, 2 entidades)

Cada anexo se guarda como un **`documento_adjunto` versionado** por el par
`(entidad, documento_anexo)`: re-subir el **mismo** `documento_anexo` a la misma
entidad crea una **nueva versión** (`version = n+1`) y marca la anterior como
`REEMPLAZADO`. Anexos distintos mantienen cadenas de versión independientes.

Entidades con anexos y su actor:

| Entidad (`{entidad}`) | `tipo_actor` (anexos aceptados) |
|-----------------------|---------------------------------|
| `interns`             | `INTERNO` |
| `organ-representatives` | `REPRESENTANTE` (cubre autoridades de universidad y CONAPRES) |
| `conventions`         | `CONVENIO` (resoluciones `RESOL_MARCO`/`RESOL_ESPECIFICO`/`RESOL_ADENDA`; PDF generados `PROYECTO_CONVENIO`/`PROYECTO_ADENDA`/`EXPEDIENTE`) |
| `clinical-field-registrations` | `CAMPO_CLINICO` (resolución `RESOL_CONAPRES`) |

> **Cambio de refactor:** las declaraciones juradas del interno (actor `INTERNO`) se
> adjuntan sobre el **internado** (`interns/{id}/…`), **no** sobre el estudiante
> (`students/{id}/…`). El endpoint de estudiantes ya **no** expone `annex-upload`/`annex-checklist`.

El `documento_anexo` sale del catálogo maestro `/api/v1/annex-documents/`
(filtrable por `?tipo_actor=`). Solo se aceptan anexos **activos** cuyo `tipo_actor`
coincida con la entidad.

| Método | Ruta | Cuerpo (multipart) | Respuesta |
|--------|------|--------------------|-----------|
| `POST` | `/api/v1/{entidad}/{id}/annex-upload/` | `documento_anexo`: id del anexo; `archivo`: PDF | `201` `documento_adjunto` |
| `GET`  | `/api/v1/{entidad}/{id}/annex-checklist/` | — | `200` lista de anexos con su estado |

### Flujo de anexos
1. `GET .../annex-checklist/` → devuelve **qué anexos requiere** el actor y cuáles
   están ya adjuntados (resaltar los `obligatorio=true` con `adjuntado=false`).
2. `POST .../annex-upload/` con `documento_anexo` + `archivo` (PDF) → adjunta.
3. Re-subir el mismo `documento_anexo` genera una **nueva versión** del `documento_adjunto`.

Ejemplo de request de `annex-upload` (internado `55` adjunta el anexo `3`, PDF):

```bash
curl -X POST https://api.renads.minsa.gob.pe/api/v1/interns/55/annex-upload/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "documento_anexo=3" \
  -F "archivo=@declaracion-salud.pdf;type=application/pdf"
```

```js
const fd = new FormData();
fd.append("documento_anexo", 3);
fd.append("archivo", pdfInput.files[0]); // File application/pdf
const doc = await fetch("/api/v1/interns/55/annex-upload/", {
  method: "POST",
  headers: { Authorization: `Bearer ${access}` },
  body: fd,
}).then((r) => r.json());
```

Consultar el checklist (`annex-checklist`):

```bash
curl https://api.renads.minsa.gob.pe/api/v1/interns/55/annex-checklist/ \
  -H "Authorization: Bearer $TOKEN"
```

Ejemplo de respuesta de `annex-checklist`:

```json
[
  {
    "documento_anexo": 3,
    "codigo": "DJ_SALUD",
    "nombre": "Declaración jurada de salud",
    "obligatorio": true,
    "adjuntado": true,
    "documento_id": 128,
    "version": 2,
    "referencia_externa": "e5f6-uuid-dj-salud.pdf"
  },
  {
    "documento_anexo": 4,
    "codigo": "DJ_ANTECEDENTES",
    "nombre": "Declaración jurada de antecedentes",
    "obligatorio": true,
    "adjuntado": false,
    "documento_id": null,
    "version": null,
    "referencia_externa": null
  }
]
```

Ejemplo de respuesta de `annex-upload` (`documento_adjunto`):

```json
{
  "id": 129,
  "documento_anexo": 3,
  "documento_anexo_nombre": "Declaración jurada de aptitud de salud",
  "tipo_contenido": 42,
  "tipo_contenido_label": "internship",
  "id_objeto": 55,
  "referencia_externa": "9a8b-uuid-dj.pdf",
  "version": 1,
  "estado": "ACTIVO",
  "version_anterior": null,
  "cargado_por": 12,
  "cargado_en": "2026-07-20T10:15:00Z"
}
```

---

## Generación de PDF del convenio (proyecto y expediente)

El módulo Convenios genera el PDF del **proyecto de convenio/adenda** y del
**expediente consolidado** a partir de plantillas Word templatizadas (docxtpl),
convertidas a PDF con **LibreOffice headless** (`soffice --headless --convert-to
pdf`) y — en el expediente — concatenadas con los adjuntos vía **pypdf**. El PDF
resultante se sube al storage activo (Cloudflare R2/GCS/stub) y se versiona como
`documento_adjunto` con el `documento_anexo` correspondiente (actor `CONVENIO`).

| Método | Ruta | Cuerpo | Respuesta | Anexo (`documento_anexo`) |
|--------|------|--------|-----------|---------------------------|
| `POST` | `/api/v1/conventions/{id}/generar-proyecto/` | — | `201` `documento_adjunto` | `PROYECTO_ADENDA` si `es_adenda`, si no `PROYECTO_CONVENIO` |
| `POST` | `/api/v1/conventions/{id}/generar-expediente/` | — | `201` `documento_adjunto` | `EXPEDIENTE` |

- Ambos endpoints son **escritura**: pasan el gate temporal `IsModuleEnabled`
  (módulo `convenios/convention`) y los permisos del ViewSet (`ConventionScope`).
  Fuera de la ventana del calendario administrativo devuelven `403`
  (`MODULO_FUERA_DE_VENTANA`), salvo superusuario/`Administrador RENADS`.
- El versionado sigue la regla `(objeto, documento_anexo)`: una segunda generación
  del mismo anexo crea `version = n+1` y marca la anterior `REEMPLAZADO`.
- El **expediente** concatena el proyecto + las resoluciones de los representantes
  firmantes (`REPRESENTANTE`) y las resoluciones CONAPRES de los campos clínicos
  (`CAMPO_CLINICO`); los adjuntos faltantes o ilegibles se **omiten** sin fallar.
- Requiere **LibreOffice** instalado en el servidor (dependencia de sistema, no pip).
  Si `soffice` no está en el PATH la respuesta es `500` con mensaje en español.

Descarga: el `referencia_externa` del `documento_adjunto` devuelto se resuelve a un
signed URL vía `GET /api/v1/documents/{id}/url-descarga/`.

---

## Documentos generales (Etapa 1, referencia)

| Método | Ruta | Cuerpo | Respuesta |
|--------|------|--------|-----------|
| `POST` | `/api/v1/documents/upload/` | multipart: `archivo`, `documento_anexo`, `tipo_contenido`, `id_objeto`, `nombre_archivo?` (solo ruta de storage) | `201` `documento_adjunto` |
| `GET`  | `/api/v1/documents/{id}/url-descarga/` | — | `200` `{ "url": "..." }` (signed URL) |

---

## Errores (mensajes en español)

| Código | Situación |
|--------|-----------|
| `400` | Content-type no permitido (p. ej. PDF en `upload-logo`, imagen en `annex-upload`). |
| `400` | Extensión incoherente con el tipo de contenido. |
| `400` | El archivo supera el tamaño máximo permitido (25 MiB). |
| `400` | El anexo seleccionado no corresponde a este tipo de actor (`annex-upload`). |
| `401` | Usuario no autenticado. |
| `403` | Usuario autenticado sin permiso (rol/alcance insuficiente). |
| `404` | La entidad no tiene un logo cargado (`logo-url`). |

## Roles por acción

| Acción | Escritura | Lectura |
|--------|-----------|---------|
| `upload-logo` (5 entidades) | `Administrador RENADS` | — |
| `logo-url` | — | Autenticados |
| `annex-upload` (interns) | `Universidad` / `Administrador RENADS` (alcance por la universidad del estudiante) o el propio `Interno` (RN-22) | — |
| `annex-upload` (organ-representatives) | `Administrador RENADS` | — |
| `annex-upload` (conventions) | Miembro institucional con alcance del convenio (`ConventionScope`) | — |
| `generar-proyecto` / `generar-expediente` (conventions) | Miembro institucional con alcance del convenio (`ConventionScope`) + gate temporal `IsModuleEnabled` | — |
| `annex-upload` (clinical-field-registrations) | `CONAPRES` | — |
| `annex-checklist` | — | Autenticados con alcance |
| `documents/upload` | Miembro institucional autenticado | — |
| `revisar-declaraciones` (interns) | `Universidad` / `Administrador RENADS` | — |

---

## Onboarding del interno y declaraciones juradas (Feature F3)

Al registrar un internado (`POST /api/v1/interns/`, rol `Universidad`) el backend crea el
usuario del interno (`username = numero_documento`, contraseña temporal, grupo `Interno`),
inicializa `interno.estado_declaraciones = "PENDIENTE"` y notifica por correo al estudiante
(sede docente, fechas, tutor, link al checklist de DJ).

### Flag de cambio de contraseña — `debe_cambiar_password`

El interno recibe una contraseña temporal y **debe** cambiarla. El flag es consultable por el front:

- **Claim del JWT** (respuesta de `POST /api/v1/auth/token/`): campo `debe_cambiar_password` (bool),
  también incluido dentro del `access` token.
- **`GET /api/v1/auth/me/`**: campo `debe_cambiar_password` (bool).
- **`POST /api/v1/auth/me/cambiar-password/`** — cambia la propia contraseña y limpia el flag:

  | Cuerpo | Descripción |
  |--------|-------------|
  | `password_actual` | Contraseña actual (temporal). `400` si no coincide. |
  | `password_nueva` | Nueva contraseña (valida fortaleza de Django). |

  Responde `200` con el payload de `/me/` (ya con `debe_cambiar_password=false`).

  ```bash
  curl -X POST https://api.renads.minsa.gob.pe/api/v1/auth/me/cambiar-password/ \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"password_actual": "clave-temporal", "password_nueva": "mi-clave-nueva-fuerte"}'
  ```

  ```js
  await fetch("/api/v1/auth/me/cambiar-password/", {
    method: "POST",
    headers: { Authorization: `Bearer ${access}`, "Content-Type": "application/json" },
    body: JSON.stringify({ password_actual: "clave-temporal", password_nueva: "mi-clave-nueva-fuerte" }),
  });
  ```

> El bloqueo efectivo de endpoints hasta cambiar la clave es refuerzo del front (MVP): el backend
> solo expone el flag y el endpoint de cambio.

### Estado de las declaraciones juradas — `revisar-declaraciones`

`interno.estado_declaraciones` ∈ {`PENDIENTE`, `COMPLETAS`, `OBSERVADAS`, `VALIDADAS`}. Pasa de
`PENDIENTE` a `COMPLETAS` **automáticamente** al completar (vía `interns/{id}/annex-upload/`) todas
las DJ obligatorias de `tipo_actor="INTERNO"`. La revisión humana la hace el rol `Universidad`/`Administrador RENADS`:

| Método | Ruta | Cuerpo | Respuesta |
|--------|------|--------|-----------|
| `POST` | `/api/v1/interns/{id}/revisar-declaraciones/` | `resultado`: `VALIDADAS`\|`OBSERVADAS`; `observacion` (opcional) | `200` internado |

```bash
curl -X POST https://api.renads.minsa.gob.pe/api/v1/interns/8/revisar-declaraciones/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"resultado": "VALIDADAS", "observacion": "Conforme."}'
```

```js
await fetch("/api/v1/interns/8/revisar-declaraciones/", {
  method: "POST",
  headers: { Authorization: `Bearer ${access}`, "Content-Type": "application/json" },
  body: JSON.stringify({ resultado: "OBSERVADAS", observacion: "Falta la firma en la DJ de salud." }),
});
```

`OBSERVADAS` vuelve a `COMPLETAS` al re-adjuntar y cumplir el checklist. **Gate:** el internado no
pasa a `ACTIVO` (`interns/{id}/cambiar-estado/`) salvo que `estado_declaraciones == "VALIDADAS"` (`400`).

---

## Tipos de entidad universitaria — `GET /api/v1/university-entity-types/`

Catálogo de solo lectura con los 4 tipos de entidad universitaria del sistema.

### Respuesta

```json
[
  { "id": 1, "nombre": "Universidad", "activo": true },
  { "id": 2, "nombre": "Instituto", "activo": true },
  { "id": 3, "nombre": "Escuela superior", "activo": true },
  { "id": 4, "nombre": "Escuela de posgrado", "activo": true }
]
```

### Uso

- Poblar el selector de tipo de entidad al crear o editar una universidad
  (`POST /api/v1/universities/` body `tipo_entidad: <id>`).
- Filtrar universidades por tipo: `GET /api/v1/universities/?tipo_entidad=<id>`.

### Breaking change — IDs de `tipo_entidad`

> Los IDs del campo `tipo_entidad` de `universidad` **cambiaron** tras la migración `0052`.
> Antes referenciaban filas de `unidad_organica`; ahora referencian filas de
> `tipo_entidad_universidad`. Los IDs numéricos son distintos.
>
> Si el frontend guardaba IDs de `tipo_entidad` en caché o en URLs, debe refrescar el
> catálogo llamando a `GET /api/v1/university-entity-types/` para obtener los nuevos IDs.
> Los filtros `?tipo_entidad=<id>` en `GET /api/v1/universities/` esperan los nuevos IDs.
