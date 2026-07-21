# API de almacenamiento — Guía para el frontend

Guía de los endpoints de **adjunto real** de RENADS (logos de entidades y PDFs de
anexos por actor), servidos sobre el backend de almacenamiento (Google Cloud
Storage en producción; stub por referencia externa en desarrollo). Todas las rutas
cuelgan de `/api/v1/` y requieren autenticación (JWT institucional).

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

---

## Logos institucionales (5 entidades)

El logo se guarda como una única clave (`referencia_logo`) en la entidad: **no hay
versionado**. Al subir uno nuevo se reemplaza y se borra la clave anterior.

Entidades con logo: `universities`, `regional-governments`, `regional-organs`,
`executing-units`, `ipress`.

| Método | Ruta | Cuerpo (multipart) | Respuesta |
|--------|------|--------------------|-----------|
| `POST` | `/api/v1/{entidad}/{id}/upload-logo/` | `archivo`: imagen (PNG/JPEG/WEBP) | `200` `{ "referencia_logo": "...", "url": "https://storage.googleapis.com/..." }` |
| `GET`  | `/api/v1/{entidad}/{id}/logo-url/` | — | `200` `{ "url": "https://storage.googleapis.com/..." }` o `404` |

### Flujo de logo
1. `POST .../upload-logo/` con el campo `archivo` → sube/reemplaza y devuelve
   `referencia_logo` + un signed URL para mostrarlo de inmediato.
2. `GET .../logo-url/` cada vez que se necesite renderizar el logo (el signed URL
   caduca; se vuelve a pedir bajo demanda).

Ejemplo de respuesta de `upload-logo`:

```json
{
  "referencia_logo": "a1b2c3d4-uuid-logo.png",
  "url": "https://storage.googleapis.com/renads-cloud-media-prod/a1b2c3d4-uuid-logo.png?X-Goog-Signature=..."
}
```

---

## Anexos (PDFs de declaraciones juradas por actor, 3 entidades)

Cada anexo se guarda como un **`Document` versionado** por el par
`(entidad, documento_anexo)`: re-subir el **mismo** `documento_anexo` a la misma
entidad crea una **nueva versión** (`version = n+1`) y marca la anterior como
`REEMPLAZADO`. Anexos distintos mantienen cadenas de versión independientes.

Entidades con anexos y su actor:

| Entidad (`{entidad}`) | `tipo_actor` (anexos aceptados) |
|-----------------------|---------------------------------|
| `students`            | `INTERNO` |
| `university-authorities` | `AUTORIDAD_UNIVERSIDAD` |
| `representatives`     | `REPRESENTANTE` |

El `documento_anexo` sale del catálogo maestro `/api/v1/annex-documents/`
(filtrable por `?tipo_actor=`). Solo se aceptan anexos **activos** cuyo `tipo_actor`
coincida con la entidad.

| Método | Ruta | Cuerpo (multipart) | Respuesta |
|--------|------|--------------------|-----------|
| `POST` | `/api/v1/{entidad}/{id}/annex-upload/` | `documento_anexo`: id del anexo; `archivo`: PDF; `nombre_archivo` (opcional) | `201` `Document` |
| `GET`  | `/api/v1/{entidad}/{id}/annex-checklist/` | — | `200` lista de anexos con su estado |

### Flujo de anexos
1. `GET .../annex-checklist/` → devuelve **qué anexos requiere** el actor y cuáles
   están ya adjuntados (resaltar los `obligatorio=true` con `adjuntado=false`).
2. `POST .../annex-upload/` con `documento_anexo` + `archivo` (PDF) → adjunta.
3. Re-subir el mismo `documento_anexo` genera una **nueva versión** del `Document`.

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

Ejemplo de respuesta de `annex-upload` (`Document`):

```json
{
  "id": 129,
  "tipo_documento": 7,
  "tipo_documento_nombre": "Declaración jurada / anexo",
  "tipo_contenido": 42,
  "tipo_contenido_label": "student",
  "id_objeto": 55,
  "referencia_externa": "9a8b-uuid-dj.pdf",
  "nombre_archivo": "declaracion.pdf",
  "version": 1,
  "estado": "ACTIVO",
  "version_anterior": null,
  "cargado_por": 12,
  "cargado_en": "2026-07-20T10:15:00Z"
}
```

---

## Documentos generales (Etapa 1, referencia)

| Método | Ruta | Cuerpo | Respuesta |
|--------|------|--------|-----------|
| `POST` | `/api/v1/documents/upload/` | multipart: `archivo`, `tipo_documento`, `tipo_contenido`, `id_objeto`, `nombre_archivo?` | `201` `Document` |
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
| `annex-upload` (students) | `Universidad` / `Administrador RENADS` (alcance por la universidad del estudiante) | — |
| `annex-upload` (university-authorities, representatives) | `Administrador RENADS` | — |
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

> El bloqueo efectivo de endpoints hasta cambiar la clave es refuerzo del front (MVP): el backend
> solo expone el flag y el endpoint de cambio.

### Estado de las declaraciones juradas — `revisar-declaraciones`

`interno.estado_declaraciones` ∈ {`PENDIENTE`, `COMPLETAS`, `OBSERVADAS`, `VALIDADAS`}. Pasa de
`PENDIENTE` a `COMPLETAS` **automáticamente** al completar (vía `students/{id}/annex-upload/`) todas
las DJ obligatorias de `tipo_actor="INTERNO"`. La revisión humana la hace el rol `Universidad`/`Administrador RENADS`:

| Método | Ruta | Cuerpo | Respuesta |
|--------|------|--------|-----------|
| `POST` | `/api/v1/interns/{id}/revisar-declaraciones/` | `resultado`: `VALIDADAS`\|`OBSERVADAS`; `observacion` (opcional) | `200` internado |

`OBSERVADAS` vuelve a `COMPLETAS` al re-adjuntar y cumplir el checklist. **Gate:** el internado no
pasa a `ACTIVO` (`interns/{id}/cambiar-estado/`) salvo que `estado_declaraciones == "VALIDADAS"` (`400`).
