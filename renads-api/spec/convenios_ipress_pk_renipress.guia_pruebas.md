# Guía de pruebas manuales — Refactor PK de `Ipress` (`codigo_renipress`)

Objetivo: validar manualmente que la PK de `Ipress` es ahora el **código RENIPRESS textual (8 chars)**, que las FK y el alcance institucional funcionan por string, y que la migración se aplica en el orden correcto. Un QA puede seguir estos pasos sin leer el código.

> **Cambio de contrato clave:** las IPRESS ya no tienen `id` entero. Su identificador (PK, URL de detalle, y valor de FK/filtros/alcance) es el **`codigo_renipress`** — un string de hasta 8 caracteres que **provee el cliente** al crear.

---

## 0. Prerrequisitos

1. **Aplicar la migración en secuencia** (el usuario corre `migrate`; el agente no):
   ```
   .venv\Scripts\Activate.ps1
   python manage.py migrate
   ```
   El plan aplica en este orden (sin ciclos): `convenios/0046` → `internados/0021` → `actividades/0006` → `convenios/0047` → `actividades/0007` → `internados/0022`. Debe terminar sin error. Verificación previa opcional del orden:
   ```
   python manage.py showmigrations --plan
   ```
   Los backfills (`0046`, `internados/0021`, `actividades/0006`) corren **antes** del drop de `Ipress.id` en `0047`. En una BD con datos reales de `ipress`, si alguna FK apunta a un `Ipress` inexistente la migración aborta con `RuntimeError` en español ("Integridad referencial rota...") — comportamiento esperado (corregir datos antes de migrar).

2. **Levantar el servidor** (lo corre el usuario):
   ```
   python manage.py runserver
   ```
   URL base: `http://localhost:8000/api/v1/`. Alternativa interactiva: Swagger en `http://localhost:8000/api/v1/docs/`.

3. **Obtener token JWT** (usuario con rol adecuado según cada paso):
   ```
   POST http://localhost:8000/api/v1/auth/token/
   Content-Type: application/json

   { "username": "<usuario>", "password": "<contraseña>" }
   ```
   Respuesta `200`: `{ "access": "...", "refresh": "...", "access_token": "..." }`. Usar en todas las llamadas siguientes:
   ```
   Authorization: Bearer <access>
   ```

---

## 1. Datos previos necesarios

Deben existir (seedeados o creados vía API por `Administrador RENADS`):
- Catálogos de `Ipress`: **categoría** (`categories`), **tipo de clasificación** (`classification-types`), **ámbito geográfico sanitario** (`health-geographic-scopes`), **microred** (`micro-networks`) y opcionalmente `ubigeo` — coherentes entre microred y ámbito.
- Al menos una **unidad ejecutora** (`executing-units`) si se va a filtrar por ella.
- Para el alcance: un **usuario objetivo** (p. ej. `Interno` o un operador de sede) y el rol/grupo a otorgar.
- Para internos/actividades: un `Student`, un `ClinicalFieldAllocation` (asignación por universidad) sobre la IPRESS sede docente, y las entidades que exija cada flujo (fuera del foco de esta guía; reutilizar datos existentes).

---

## 2. Alta de IPRESS por código string (rol: `Administrador RENADS`)

El `codigo_renipress` es ahora **obligatorio** (es la PK; ya no se autogenera un `id`).

```
POST http://localhost:8000/api/v1/ipress/
Authorization: Bearer <access-admin>
Content-Type: application/json

{
  "codigo_renipress": "00012345",
  "nombre": "Centro de Salud San Juan",
  "categoria": 1,
  "tipo_clasificacion": 1,
  "ambito_geografico_sanitario": 1,
  "microred": 1,
  "unidad_ejecutora": 1,
  "activo": true
}
```
Esperado `201`. La respuesta **no** incluye `id`; el identificador es `codigo_renipress = "00012345"`.

**Detalle por PK string:**
```
GET http://localhost:8000/api/v1/ipress/00012345/
Authorization: Bearer <access-admin>
```
Esperado `200` — resuelve por el código, no por entero.

**Búsqueda / orden:**
```
GET http://localhost:8000/api/v1/ipress/?search=00012345
GET http://localhost:8000/api/v1/ipress/?ordering=codigo_renipress
```
Esperado `200`; el listado se ordena por `codigo_renipress`.

**Caso que debe fallar (RN de alta):** POST sin `codigo_renipress` →
```json
{ "codigo_renipress": ["Este campo es requerido."] }
```
Esperado `400`.

---

## 3. Autorizar como sede docente + auditoría (rol: `CONAPRES`)

CONAPRES autoriza la IPRESS como sede docente; la acción registra una entrada de auditoría cuyo `id_objeto` es el **código string**.

```
POST http://localhost:8000/api/v1/ipress/00012345/autorizar-sede-docente/
Authorization: Bearer <access-conapres>
Content-Type: application/json

{ "autorizar": true }
```
Esperado `200`; la IPRESS queda con `es_sede_docente = true`.

**Verificar la auditoría** (rol con acceso a `audit-logs`):
```
GET http://localhost:8000/api/v1/audit-logs/?entidad=ipress
Authorization: Bearer <access-admin>
```
Esperado `200`; la fila de la acción `ACTUALIZAR` sobre `ipress` tiene `id_objeto = "00012345"` (string, no entero). Confirma que `AuditLog.id_objeto` es `varchar(64)` y almacena el código sin error.

**Caso que debe fallar (permiso):** el mismo POST con un token que **no** sea `CONAPRES` →
esperado `403` (rol requerido `CONAPRES`).

---

## 4. Otorgar alcance IPRESS por código (rol: `Administrador RENADS`)

Se asigna a un usuario el alcance sobre una o más IPRESS mediante `ids` como **códigos string**.

Primero, obtener el `id` (PK entera) del **rol/grupo** a otorgar:
```
GET http://localhost:8000/api/v1/groups/
Authorization: Bearer <access-admin>
```

Luego otorgar el perfil de alcance (`<user_id>` = PK del usuario objetivo):
```
POST http://localhost:8000/api/v1/users/<user_id>/profiles/
Authorization: Bearer <access-admin>
Content-Type: application/json

{
  "rol": 5,
  "tipo_entidad": "ipress",
  "ids": ["00012345"]
}
```
Esperado `201`. La respuesta expone el perfil con `id_objeto = "00012345"` (string).

**Verificar el alcance otorgado:**
```
GET http://localhost:8000/api/v1/users/<user_id>/profiles/
Authorization: Bearer <access-admin>
```
Esperado `200`; el perfil sobre `ipress` muestra `id_objeto` como código string.

**Caso que debe fallar (código inexistente):**
```json
{ "rol": 5, "tipo_entidad": "ipress", "ids": ["99999999"] }
```
Esperado `400` con mensaje: "No existen entidades del tipo indicado con los siguientes identificadores: 99999999."

---

## 5. Un usuario con alcance IPRESS ve solo sus internos/actividades

Con el usuario del paso 4 (que tiene alcance sobre la IPRESS `00012345` y **no** es superusuario ni `Administrador RENADS`), autenticarse (`POST /auth/token/`) y listar:

**Internos filtrados por su ámbito:**
```
GET http://localhost:8000/api/v1/interns/
Authorization: Bearer <access-usuario-alcance>
```
Esperado `200`; **solo** aparecen internos cuya `ipress` (código RENIPRESS) esté dentro de su alcance (`00012345`). Internos de otras sedes **no** deben aparecer.

**Actividades filtradas por su ámbito:**
```
GET http://localhost:8000/api/v1/teaching-activities/
Authorization: Bearer <access-usuario-alcance>
```
Esperado `200`; solo actividades cuya `ipress` esté en su alcance.

**Filtro explícito por código string (contrato de FK/filtro):**
```
GET http://localhost:8000/api/v1/interns/?ipress=00012345
GET http://localhost:8000/api/v1/teaching-activities/?ipress=00012345
GET http://localhost:8000/api/v1/rotations/?ipress_origen=00012345
GET http://localhost:8000/api/v1/clinical-field-registrations/?ipress=00012345
```
Esperado `200` en todos; el parámetro es el **código string de 8 chars**, no un entero.

**Confirmación cruzada del alcance:** con el mismo usuario, un `GET /interns/?ipress=<otro_codigo>` (una IPRESS fuera de su alcance) debe devolver lista **vacía** (el scope filtra por `str(ipress_id)`), aunque existan internos en esa otra sede.

---

## 6. Escritura de FK por código string (contrato de payloads)

Al crear/editar un interno, rotación, tutor, actividad o registro/asignación de campo clínico, el campo `ipress` (y `ipress_origen`/`ipress_destino`) se envía como **código RENIPRESS string**:

```
POST http://localhost:8000/api/v1/clinical-field-registrations/
Authorization: Bearer <access-conapres>
Content-Type: application/json

{
  "convenio": 1,
  "ipress": "00012345",
  "carrera_profesional": 1,
  "campos_clinicos_registrados": 10
}
```
Esperado `201`; `ipress` acepta el string. Enviar `ipress` como entero inexistente (p. ej. `"99999999"`) debe devolver `400` (FK inválida).

---

## Resumen de roles por endpoint

| Endpoint / acción | Rol requerido para escritura |
|---|---|
| `POST/PATCH/DELETE /ipress/` | `Administrador RENADS` |
| `POST /ipress/{codigo}/autorizar-sede-docente/` | `CONAPRES` |
| `POST/DELETE /users/{id}/profiles/` | `Administrador RENADS` |
| `POST /clinical-field-registrations/` | `CONAPRES` |
| `POST /clinical-field-allocations/` | grupo `Gobierno Regional` |
| Lecturas (`GET`) de listados/detalle | usuario autenticado (con alcance institucional aplicado) |
