# Guía de pruebas manuales — Soporte transversal (Documento + Bitácora)

Pruebas manuales de los endpoints nuevos del Módulo 1: gestión documental polimórfica con
versionado (`/documents/`) y consulta de bitácora de auditoría (`/audit-logs/`).
Un QA puede seguir esta guía sin leer el código. La validación previa
(`spec/convenios_transversales.validacion.md`) resultó **APROBADA**.

## 1. Prerrequisitos

1. El usuario levanta el servidor (Claude no lo ejecuta):
   ```
   .venv\Scripts\Activate.ps1
   python manage.py runserver
   ```
2. URL base: `http://localhost:8000/api/v1/`
3. Alternativa interactiva: Swagger UI en `http://localhost:8000/api/v1/docs/`
4. Obtener token JWT:
   ```http
   POST http://localhost:8000/api/v1/auth/token/
   Content-Type: application/json

   {"username": "<usuario>", "password": "<contraseña>"}
   ```
   Respuesta `200`:
   ```json
   {"access": "<access>", "refresh": "<refresh>"}
   ```
   En todas las llamadas siguientes enviar la cabecera:
   ```
   Authorization: Bearer <access>
   ```

### Roles / permisos por endpoint

| Endpoint | Permiso requerido |
|----------|-------------------|
| `GET/POST/DELETE /documents/`, `GET /documents/{id}/url-descarga/` | Usuario autenticado **con perfil institucional activo** (`IsInstitutionalMember`); superusuario pasa siempre |
| `GET /audit-logs/`, `GET /audit-logs/{id}/` | Superusuario o grupo **«Administrador RENADS»** (`IsAdminRole`) |

> Para los pasos de Documento conviene un usuario con perfil institucional (o superusuario).
> Para Bitácora se requiere Administrador RENADS / superusuario, además de un usuario **sin** ese
> rol para el caso de fallo.

## 2. Datos previos necesarios

- Debe existir al menos un **tipo de documento** (`tipo_documento`). Listar:
  ```http
  GET http://localhost:8000/api/v1/document-types/
  Authorization: Bearer <access>
  ```
  Anotar un `id` (lo llamaremos `TIPO_DOC_ID`). Si no hay registros, deben seedearse vía admin.
- Debe existir un **objeto destino real** al que adjuntar el documento (relación genérica). Lo más
  simple es un **convenio**:
  ```http
  GET http://localhost:8000/api/v1/conventions/
  Authorization: Bearer <access>
  ```
  Anotar un `id` (lo llamaremos `OBJETO_ID`). Si no hay, crear uno según
  `spec/convenios.guia_pruebas.md`.
- Obtener el **`tipo_contenido` (ContentType id)** del modelo destino. La forma fiable es vía Swagger
  (`/api/v1/docs/`) probando el filtro, o consultando el admin de Django en
  `django_content_type` el registro con `model = convention` y app `convenios`. Anotar ese id como
  `TIPO_CONTENIDO_ID`.

## 3. Flujo paso a paso — Documento

### Paso 3.1 — Primer adjunto (version 1)

```http
POST http://localhost:8000/api/v1/documents/
Authorization: Bearer <access>
Content-Type: application/json

{
  "tipo_contenido": TIPO_CONTENIDO_ID,
  "id_objeto": OBJETO_ID,
  "tipo_documento": TIPO_DOC_ID,
  "nombre_archivo": "convenio_marco_v1.pdf",
  "referencia_externa": "s3://renads/convenios/OBJETO_ID/marco_v1.pdf"
}
```

Esperado: `201 Created`.
```json
{
  "id": 1,
  "tipo_documento": TIPO_DOC_ID,
  "tipo_documento_nombre": "<nombre del tipo>",
  "tipo_contenido": TIPO_CONTENIDO_ID,
  "tipo_contenido_label": "convention",
  "id_objeto": OBJETO_ID,
  "referencia_externa": "s3://renads/convenios/OBJETO_ID/marco_v1.pdf",
  "nombre_archivo": "convenio_marco_v1.pdf",
  "version": 1,
  "estado": "ACTIVO",
  "version_anterior": null,
  "cargado_por": <id usuario>,
  "cargado_en": "<timestamp>"
}
```
Anotar `id` del documento como `DOC1_ID`.

### Paso 3.2 — Segundo adjunto del mismo (objeto, tipo_documento) → version 2

Repetir el `POST` anterior con el **mismo** `tipo_contenido`, `id_objeto` y `tipo_documento`,
cambiando el archivo:

```http
POST http://localhost:8000/api/v1/documents/
Authorization: Bearer <access>
Content-Type: application/json

{
  "tipo_contenido": TIPO_CONTENIDO_ID,
  "id_objeto": OBJETO_ID,
  "tipo_documento": TIPO_DOC_ID,
  "nombre_archivo": "convenio_marco_v2.pdf",
  "referencia_externa": "s3://renads/convenios/OBJETO_ID/marco_v2.pdf"
}
```

Esperado: `201 Created` con `"version": 2`, `"estado": "ACTIVO"`,
`"version_anterior": DOC1_ID`. Anotar `id` como `DOC2_ID`.

Verificar que el documento previo quedó **REEMPLAZADO**:
```http
GET http://localhost:8000/api/v1/documents/DOC1_ID/
Authorization: Bearer <access>
```
Esperado: `200` con `"estado": "REEMPLAZADO"`.

### Paso 3.3 — URL de descarga

```http
GET http://localhost:8000/api/v1/documents/DOC2_ID/url-descarga/
Authorization: Bearer <access>
```
Esperado: `200`
```json
{"url": "s3://renads/convenios/OBJETO_ID/marco_v2.pdf"}
```
(El stub devuelve la `referencia_externa` tal cual.)

### Paso 3.4 — Filtros del listado

```http
GET http://localhost:8000/api/v1/documents/?tipo_contenido=TIPO_CONTENIDO_ID&id_objeto=OBJETO_ID&estado=ACTIVO
Authorization: Bearer <access>
```
Esperado: `200`; la lista incluye `DOC2_ID` (ACTIVO) y **no** `DOC1_ID` (REEMPLAZADO).
Probar también `?estado=REEMPLAZADO` → debe aparecer `DOC1_ID`.
Filtros adicionales válidos: `tipo_documento`.

### Paso 3.5 — Eliminar (auditoría ELIMINAR)

```http
DELETE http://localhost:8000/api/v1/documents/DOC1_ID/
Authorization: Bearer <access>
```
Esperado: `204 No Content`. Se invoca `storage.eliminar` (stub no-op) y se registra `ELIMINAR`
en la bitácora.

> Nota: `PUT`/`PATCH` sobre `/documents/{id}/` deben responder `405 Method Not Allowed`
> (las nuevas versiones se crean con un nuevo `POST`).

## 4. Casos que deben fallar (reglas / validación)

### 4.1 — Objeto destino inexistente (T3.2)

```http
POST http://localhost:8000/api/v1/documents/
Authorization: Bearer <access>
Content-Type: application/json

{
  "tipo_contenido": TIPO_CONTENIDO_ID,
  "id_objeto": 999999,
  "tipo_documento": TIPO_DOC_ID,
  "nombre_archivo": "x.pdf",
  "referencia_externa": "s3://x.pdf"
}
```
Esperado: `400 Bad Request`
```json
{"id_objeto": ["El objeto destino indicado no existe."]}
```

### 4.2 — Usuario sin perfil institucional

Con un token de usuario autenticado **sin** perfil institucional (y no superusuario), llamar
`GET /api/v1/documents/`.
Esperado: `403 Forbidden`, mensaje «El usuario no tiene un perfil institucional activo.»

## 5. Flujo paso a paso — Bitácora de auditoría

### 5.1 — Consulta como Administrador RENADS

```http
GET http://localhost:8000/api/v1/audit-logs/
Authorization: Bearer <access-admin>
```
Esperado: `200`, lista ordenada por `creado_en` descendente. Cada registro incluye
`usuario`, `usuario_nombre`, `accion`, `tipo_contenido`, `tipo_contenido_label`, `id_objeto`,
`nombre_campo`, `valor_anterior`, `valor_nuevo`, `direccion_ip`, `creado_en`.

### 5.2 — Verificar trazas del flujo de Documento

Tras los pasos 3.1–3.2 deben existir registros:
- `CREAR` sobre el documento (entidad `document`) — uno por cada adjunto creado.
- `CAMBIO_ESTADO` sobre `DOC1_ID` con `nombre_campo="estado"`, `valor_anterior="ACTIVO"`,
  `valor_nuevo="REEMPLAZADO"` (generado al crear la v2).
- `ELIMINAR` sobre `DOC1_ID` tras el paso 3.5.

Filtrar para confirmarlo (usar el ContentType de `document` como `tipo_contenido`):
```http
GET http://localhost:8000/api/v1/audit-logs/?accion=CAMBIO_ESTADO&id_objeto=DOC1_ID
Authorization: Bearer <access-admin>
```

### 5.3 — Filtros y búsqueda (T7)

```http
GET http://localhost:8000/api/v1/audit-logs/?usuario=<id>&accion=CREAR
GET http://localhost:8000/api/v1/audit-logs/?accion_contiene=CAMBIO
GET http://localhost:8000/api/v1/audit-logs/?creado_en_desde=2026-06-29T00:00:00Z&creado_en_hasta=2026-06-29T23:59:59Z
GET http://localhost:8000/api/v1/audit-logs/?tipo_contenido=<ct_id>&id_objeto=<id>
GET http://localhost:8000/api/v1/audit-logs/?search=CREAR
```
Esperado: `200` con resultados acordes a cada filtro.

### 5.4 — Caso que debe fallar: usuario sin rol Administrador

Con un token de usuario autenticado **sin** el grupo «Administrador RENADS» (y no superusuario):
```http
GET http://localhost:8000/api/v1/audit-logs/
Authorization: Bearer <access-no-admin>
```
Esperado: `403 Forbidden`, mensaje «Requiere el rol Administrador RENADS.»

## 6. Resumen de resultados esperados

| Paso | Endpoint | Esperado |
|------|----------|----------|
| 3.1 | `POST /documents/` | `201`, `version=1`, `ACTIVO`, `version_anterior=null` |
| 3.2 | `POST /documents/` (mismo par) | `201`, `version=2`, `version_anterior=DOC1_ID`; DOC1 → `REEMPLAZADO` |
| 3.3 | `GET /documents/{id}/url-descarga/` | `200`, `{"url": <referencia_externa>}` |
| 3.4 | `GET /documents/?...` | `200`, filtrado por `tipo_contenido`/`id_objeto`/`estado`/`tipo_documento` |
| 3.5 | `DELETE /documents/{id}/` | `204`; traza `ELIMINAR` |
| 4.1 | `POST /documents/` id inexistente | `400` mensaje en español |
| 4.2 | `GET /documents/` sin perfil | `403` |
| 5.1 | `GET /audit-logs/` (admin) | `200` orden `creado_en` desc |
| 5.4 | `GET /audit-logs/` (sin rol) | `403` |
