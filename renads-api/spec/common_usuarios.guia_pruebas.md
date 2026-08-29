# Guía de pruebas manuales — Gestión de usuarios, roles y permisos (superadministrador)

Esta guía permite a QA validar manualmente la feature sin leer el código. Cubre el login enriquecido y
el CRUD de usuarios, grupos (roles) y permisos, todo restringido a **superusuario** (`is_superuser`).

## 1. Prerrequisitos

1. **Levantar el servidor** (lo corre el usuario, no QA):
   ```bash
   .venv\Scripts\Activate.ps1
   python manage.py runserver
   ```
2. **URL base:** `http://localhost:8000/api/v1/`
3. **Swagger interactivo (alternativa):** `http://localhost:8000/api/v1/docs/`
4. **Usuarios de prueba:**
   - Un **superusuario** (p. ej. el creado con `python manage.py createsuperuser`).
   - Un **usuario normal** autenticable (no superusuario) para los casos de rechazo 403.
5. **Obtener token JWT** (paso previo a todo lo demás):
   ```http
   POST http://localhost:8000/api/v1/auth/token/
   Content-Type: application/json

   { "username": "admin", "password": "TuPasswordSegura" }
   ```
   **Respuesta esperada (200)** — incluye los campos enriquecidos:
   ```json
   {
     "refresh": "<jwt>",
     "access": "<jwt>",
     "es_superusuario": true,
     "nombre": "Administrador RENADS",
     "grupos": []
   }
   ```
   Verificación adicional: decodificar el `access` (p. ej. en jwt.io) y confirmar que el payload
   contiene el claim `"es_superusuario": true`.
6. En **todas** las llamadas siguientes usar la cabecera:
   `Authorization: Bearer <access>` (el `access` del superusuario, salvo en los casos de 403 donde se
   usa el del usuario normal).

> **Rol/permiso requerido:** todos los endpoints de `users/`, `groups/` y `permissions/` exigen
> `is_superuser=True`. No basta con pertenecer a un grupo; debe ser superusuario.

## 2. Datos previos necesarios

- No se requieren catálogos: la feature usa los modelos nativos de Django (`User`, `Group`,
  `Permission`). Los `Permission` ya están seedeados por Django (uno por modelo/acción de cada app).
- Para el flujo de grupos se crearán roles nuevos durante la prueba.

---

## 3. Flujo paso a paso

### 3.1 Login con `es_superusuario` (verificación de identidad)

Ya cubierto en el Prerrequisito 5. Repetir con el **usuario normal** y confirmar que su respuesta trae
`"es_superusuario": false`.

### 3.2 Crear un usuario — contraseña válida (201)

```http
POST http://localhost:8000/api/v1/users/
Authorization: Bearer <access-superusuario>
Content-Type: application/json

{
  "username": "jperez",
  "email": "jperez@minsa.gob.pe",
  "first_name": "Juan",
  "last_name": "Pérez",
  "password": "Rng7$ClaveLarga2026",
  "is_active": true,
  "is_staff": false,
  "is_superuser": false,
  "groups": []
}
```
**Esperado: 201 Created.** La respuesta incluye `id` y los datos del usuario, **sin** `password` ni
hash. Anotar el `id` devuelto (p. ej. `id = 5`) para los pasos siguientes.

Verificación de auditoría: en `bitacora_auditoria` debe aparecer un registro `CREAR` para este usuario.

### 3.3 Crear/actualizar con contraseña débil (400)

```http
POST http://localhost:8000/api/v1/users/
Authorization: Bearer <access-superusuario>
Content-Type: application/json

{ "username": "debil", "email": "debil@minsa.gob.pe", "password": "123" }
```
**Esperado: 400 Bad Request** con mensajes en español en el campo `password`, p. ej.:
`"La contraseña es demasiado corta. Debe contener por lo menos 8 caracteres."`,
`"Esta contraseña es demasiado común."`, `"Esta contraseña es completamente numérica."`.

### 3.4 Listar / consultar usuarios

```http
GET http://localhost:8000/api/v1/users/?is_active=true&search=jperez&ordering=username
Authorization: Bearer <access-superusuario>
```
**Esperado: 200** con resultados paginados. Confirmar que **ningún** objeto incluye `password`/hash y
que aparece `groups_detalle` con `{id, name}`. Filtros disponibles: `is_active`, `is_superuser`,
`is_staff`, `groups`. Búsqueda por `username/email/first_name/last_name`.

### 3.5 Asignar grupos a un usuario (M2M) — 200

Primero crear un grupo (ver 3.8) y anotar su `id` (p. ej. `grupo_id = 3`). Luego:
```http
PATCH http://localhost:8000/api/v1/users/5/
Authorization: Bearer <access-superusuario>
Content-Type: application/json

{ "groups": [3] }
```
**Esperado: 200.** En la respuesta (o con un `GET /users/5/`) `groups` debe contener `[3]` y
`groups_detalle` el nombre del rol. Registro `ACTUALIZAR` en `bitacora_auditoria`.

### 3.6 Cambiar contraseña — acción dedicada (set-password)

Caso válido:
```http
POST http://localhost:8000/api/v1/users/5/set-password/
Authorization: Bearer <access-superusuario>
Content-Type: application/json

{ "password": "Nv2$OtraClaveValida2026" }
```
**Esperado: 200** con `{ "detalle": "Contraseña actualizada." }`. Registro `ACTUALIZAR`
(`nombre_campo=password`) en `bitacora_auditoria` — **sin** registrar el valor de la contraseña.

Caso débil:
```http
POST http://localhost:8000/api/v1/users/5/set-password/
Authorization: Bearer <access-superusuario>
Content-Type: application/json

{ "password": "12345" }
```
**Esperado: 400** con mensajes en español (misma validación que 3.3).

### 3.7 Desactivar un usuario (DELETE = is_active=False)

```http
DELETE http://localhost:8000/api/v1/users/5/
Authorization: Bearer <access-superusuario>
```
**Esperado: 204 No Content.** Verificar con `GET /users/5/`: el usuario **sigue existiendo** con
`"is_active": false` (no fue borrado físicamente). Registro `DESACTIVAR` en `bitacora_auditoria`
(`is_active`: anterior `True`, nuevo `False`).

### 3.8 CRUD de grupos (roles) + asignar permisos

Crear rol:
```http
POST http://localhost:8000/api/v1/groups/
Authorization: Bearer <access-superusuario>
Content-Type: application/json

{ "name": "Coordinador de Sede", "permissions": [] }
```
**Esperado: 201**, anotar `id` (p. ej. `3`). Registro `CREAR`.

Asignar permisos al rol (obtener ids de `permissions/` primero, ver 3.9):
```http
PATCH http://localhost:8000/api/v1/groups/3/
Authorization: Bearer <access-superusuario>
Content-Type: application/json

{ "permissions": [12, 13] }
```
**Esperado: 200.** La respuesta incluye `permissions` (PKs) y `permissions_detalle`
(`{id, name, codename, app_label, model}`). Registro `ACTUALIZAR`.

Eliminar rol:
```http
DELETE http://localhost:8000/api/v1/groups/3/
Authorization: Bearer <access-superusuario>
```
**Esperado: 204** (los grupos **sí** se borran físicamente). Registro `ELIMINAR`.

### 3.9 Listar permisos (solo lectura)

```http
GET http://localhost:8000/api/v1/permissions/?content_type__app_label=convenios&search=add
Authorization: Bearer <access-superusuario>
```
**Esperado: 200** con permisos filtrados por app y búsqueda por `name`/`codename`. Cada item expone
`app_label` y `model`. Confirmar que escritura no está permitida:
```http
POST http://localhost:8000/api/v1/permissions/
Authorization: Bearer <access-superusuario>
```
**Esperado: 405 Method Not Allowed.**

---

## 4. Casos de regla de negocio / seguridad que DEBEN fallar

| Caso | Petición | Esperado |
|------|----------|----------|
| No-superusuario lista usuarios | `GET /users/` con `Bearer <access-usuario-normal>` | **403** — `"Solo un superadministrador puede acceder a la gestión de usuarios, roles y permisos."` |
| No-superusuario crea usuario | `POST /users/` con token de usuario normal | **403** (mismo mensaje) |
| No-superusuario cambia contraseña ajena | `POST /users/5/set-password/` con token de usuario normal | **403** |
| No-superusuario sobre grupos | `GET`/`POST`/`PUT`/`DELETE` en `/groups/` con token normal | **403** |
| No-superusuario sobre permisos | `GET /permissions/` con token normal | **403** |
| Anónimo (sin token) | cualquier endpoint de `users/`, `groups/`, `permissions/` | **401 Unauthorized** |
| Contraseña débil (alta) | `POST /users/` con `password` débil | **400** con mensaje español |
| Contraseña débil (set-password) | `POST /users/{id}/set-password/` con `password` débil | **400** con mensaje español |
| Email duplicado | `POST /users/` con un `email` ya usado | **400** — `"Ya existe un usuario con este correo electrónico."` |
| Escritura en permisos | `POST/PUT/DELETE` en `/permissions/` (superusuario) | **405 Method Not Allowed** |

## 5. Verificación final de auditoría

Tras ejecutar el flujo, comprobar en `bitacora_auditoria` que existen los registros:
`CREAR`/`ACTUALIZAR`/`DESACTIVAR` para usuarios y `CREAR`/`ACTUALIZAR`/`ELIMINAR` para grupos, cada uno
con `usuario` (quién), fecha/hora, acción, entidad afectada y, donde aplica, valor anterior/nuevo. El
cambio de contraseña aparece como `ACTUALIZAR` con `nombre_campo=password` **sin** exponer el valor.

---

## 6. Scope por objeto — perfiles institucionales (T10)

Sub-recurso de usuarios para **otorgar/revocar** a un usuario el acceso a una o varias entidades
institucionales (universidades, IPRESS, etc.) bajo un **rol** (`Group`). Endpoint:
`GET/POST/DELETE /api/v1/users/{id}/profiles/`. **Rol/permiso requerido: superusuario** (`IsSuperUser`);
cualquier otro rol o anónimo → `403`/`401`.

### 6.1 Datos previos necesarios

- Un **usuario objetivo** al que se le otorgará el scope (anota su `id`, p. ej. `12`) — se crea en la
  sección 2 (`POST /users/`).
- Un **rol** (`Group`) existente, p. ej. `Universidad` (anota su `id`, p. ej. `4`) — se crea en la
  sección 3 (`POST /groups/`).
- Al menos una **entidad** existente del tipo a otorgar. Ejemplos de `tipo_entidad` (nombre de modelo en
  minúscula, de las apps `convenios`/`internados`/`actividades`): `university`, `ipress`, `student`.
  Anota los `id` reales (p. ej. universidades `3` y `7`). Verifícalos con los catálogos del módulo
  (p. ej. `GET /api/v1/universities/`).
- Token `access` del **superusuario** en `Authorization: Bearer <access>`.

### 6.2 Flujo paso a paso

**Paso 1 — Estado inicial (GET, criterio 1).**
```http
GET http://localhost:8000/api/v1/users/12/profiles/
Authorization: Bearer <access-superadmin>
```
Esperado **200** con la lista de perfiles **activos** del usuario (probablemente vacía al inicio).

**Paso 2 — Otorgar scope (POST, criterio 1).**
```http
POST http://localhost:8000/api/v1/users/12/profiles/
Authorization: Bearer <access-superadmin>
Content-Type: application/json

{ "rol": 4, "tipo_entidad": "university", "ids": [3, 7] }
```
Esperado **201** con la lista materializada; cada elemento con la forma:
```json
{ "id": 1, "tipo_entidad": "university", "id_objeto": 3, "entidad": "UNMSM", "rol": "Universidad", "activo": true }
```
Anota los `id` de perfil devueltos (p. ej. `1` y `2`) para el DELETE.

**Paso 3 — Comprobar en `/auth/me/` del usuario objetivo (criterio 1).**
Inicia sesión como el usuario `12` (`POST /auth/token/`) y consulta:
```http
GET http://localhost:8000/api/v1/auth/me/
Authorization: Bearer <access-usuario-12>
```
Esperado **200**: en `perfiles` aparecen las entidades otorgadas con exactamente 4 campos
(`tipo_entidad`, `id_objeto`, `entidad`, `rol`).

**Paso 4 — Idempotencia (criterio 2).**
Reenvía **el mismo POST** del Paso 2. Esperado **201** y el conteo de filas activas **no cambia** (no se
duplican); no se generan registros de auditoría nuevos (verificar en sección 6.4).

**Paso 5 — Baja lógica (DELETE, criterio 4).**
```http
DELETE http://localhost:8000/api/v1/users/12/profiles/?profile_id=2
Authorization: Bearer <access-superadmin>
```
Esperado **204**. El perfil `2` queda `activo=false` (no borrado). Verificaciones:
- `GET /users/12/profiles/` → ya **no** lista el perfil `2` (solo activos por defecto).
- `GET /users/12/profiles/?incluir_inactivos=true` → el perfil `2` **sí** aparece con `"activo": false`.
- `GET /auth/me/` del usuario `12` → el perfil dado de baja **desaparece** de `perfiles`.
- Repetir el mismo DELETE → **204 idempotente** (sin nueva auditoría).

**Paso 6 — Reactivación (criterio 3).**
Reenvía el POST del Paso 2 con `"ids": [7]` (la entidad del perfil dado de baja). Esperado **201**; el
perfil se reactiva (`activo` `false→true`) y vuelve a aparecer en `GET .../profiles/` y en `/auth/me/`.
Se audita como `ACTIVAR` (sección 6.4).

**Paso 7 — Genericidad (criterio 9).**
Repite el Paso 2 con otro tipo admitido, p. ej.:
```http
POST http://localhost:8000/api/v1/users/12/profiles/
Authorization: Bearer <access-superadmin>
Content-Type: application/json

{ "rol": 4, "tipo_entidad": "ipress", "ids": [1] }
```
Esperado **201** sin cambios de código (sustituye `ids` por identificadores reales de IPRESS).

### 6.3 Casos que deben fallar (criterios 5 y 6)

| Caso | Petición | Esperado |
|------|----------|----------|
| `rol` inexistente | `POST .../profiles/` con `"rol": 99999` | **400** — `"El rol indicado no existe."` |
| `tipo_entidad` no admitida/desconocida | `"tipo_entidad": "planeta"` | **400** — `"El tipo de entidad indicado no es válido."` |
| `ids` vacío | `"ids": []` | **400** (mensaje de lista no vacía) |
| Algún `id` inexistente | `"tipo_entidad": "university", "ids": [3, 999999]` | **400** — `"No existen entidades del tipo indicado con los siguientes identificadores: 999999."` |
| DELETE sin `profile_id` | `DELETE .../profiles/` (sin query ni body) | **400** — `"Debe indicar el identificador del perfil a revocar."` |
| DELETE `profile_id` ajeno al usuario | `DELETE /users/12/profiles/?profile_id=<pk-de-otro-usuario>` | **404** — `"El perfil indicado no pertenece al usuario."` |
| No-superusuario | `GET`/`POST`/`DELETE .../profiles/` con token de usuario normal | **403** — mensaje de `IsSuperUser` |
| Anónimo | cualquier método de `.../profiles/` sin token | **401** |

### 6.4 Verificación de auditoría (criterio 7)

Tras el flujo, comprobar en `bitacora_auditoria` (`tipo_contenido` = `UserEntityProfile`, `id_objeto` =
PK del perfil):
- Alta nueva → `CREAR`.
- Reactivación de un perfil dado de baja → `ACTIVAR` (`nombre_campo=activo`, `valor_anterior=False`,
  `valor_nuevo=True`).
- Baja lógica → `DESACTIVAR` (`nombre_campo=activo`, `valor_anterior=True`, `valor_nuevo=False`).
- El reenvío idempotente del POST (Paso 4) **no** agrega registros nuevos.


---

## 7. Lookup de tipos de entidad asignables (T11)

Endpoint: `GET /api/v1/profile-entity-types/` — alimenta el selector «Tipo de entidad» del alta de
perfiles. Rol requerido: **superadministrador** (`is_superuser`). Usar el `access` de un superadmin
(ver Paso 1 de esta guía) en `Authorization: Bearer <access>`.

### 7.1 Listar tipos como superadmin (200 + forma)

```bash
curl -s http://localhost:8000/api/v1/profile-entity-types/ \
  -H "Authorization: Bearer $ACCESS_SUPERADMIN"
```

Esperado: **200** con 8 items ordenados por `label` (alfabético en español). Forma de cada item:

```json
[
  {"id": 12, "tipo_entidad": "conapres",           "label": "CONAPRES",          "app_label": "convenios"},
  {"id": 8,  "tipo_entidad": "student",            "label": "estudiante",         "app_label": "internados"},
  {"id": 5,  "tipo_entidad": "regionalgovernment", "label": "gobierno regional",  "app_label": "convenios"},
  {"id": 3,  "tipo_entidad": "ipress",             "label": "IPRESS",             "app_label": "convenios"},
  {"id": 9,  "tipo_entidad": "minsaorgan",         "label": "órgano del MINSA","app_label": "convenios"},
  {"id": 6,  "tipo_entidad": "regionalorgan",      "label": "órgano regional","app_label": "convenios"},
  {"id": 4,  "tipo_entidad": "executingunit",      "label": "unidad ejecutora",   "app_label": "convenios"},
  {"id": 2,  "tipo_entidad": "university",         "label": "universidad",        "app_label": "convenios"}
]
```

Verificar: exactamente 8 entradas; `tipo_entidad` en minúscula
(`university`, `ipress`, `regionalgovernment`, `regionalorgan`, `executingunit`, `conapres`,
`minsaorgan`, `student`); `label` en español (verbose_name); `app_label` = `convenios` salvo `student`
(= `internados`). Los `id` (ContentType) dependen de la BD; el frontend debe usar `tipo_entidad`, no `id`.

> Alternativa interactiva: Swagger en `http://localhost:8000/api/v1/docs/` → operación
> `profile_entity_types_list`.

### 7.2 No superadmin → 403 / anónimo → 401

```bash
# Con token de un usuario normal (no superusuario)
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/profile-entity-types/ \
  -H "Authorization: Bearer $ACCESS_USUARIO_NORMAL"
# Esperado: 403 (mensaje de IsSuperUser en español)

# Sin token
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/profile-entity-types/
# Esperado: 401
```

### 7.3 Contrato reutilizable — un `tipo_entidad` del lookup es aceptado por el POST de perfiles

Tomar un `tipo_entidad` del lookup (p. ej. `"student"`, RN-22) y usarlo en el alta de perfiles de T10.
Requiere un `<user_id>` objetivo, un `<group_id>` (rol) válido y `ids` de estudiantes existentes.

```bash
curl -s -X POST http://localhost:8000/api/v1/users/<user_id>/profiles/ \
  -H "Authorization: Bearer $ACCESS_SUPERADMIN" \
  -H "Content-Type: application/json" \
  -d '{"rol": <group_id>, "tipo_entidad": "student", "ids": [<student_id>]}'
```

Esperado: **201** con la lista de perfiles materializados (`{id, tipo_entidad, id_objeto, entidad, rol,
activo}`). El valor `tipo_entidad` del lookup se reenvía tal cual, sin transformación.

### 7.4 `tipo_entidad` fuera de la allowlist → 400 (validación endurecida)

Un modelo no institucional (fuera de `ASSIGNABLE_PROFILE_MODELS`) debe rechazarse, aunque exista como
modelo de las apps del proyecto:

```bash
curl -s -X POST http://localhost:8000/api/v1/users/<user_id>/profiles/ \
  -H "Authorization: Bearer $ACCESS_SUPERADMIN" \
  -H "Content-Type: application/json" \
  -d '{"rol": <group_id>, "tipo_entidad": "document", "ids": [1]}'
```

Esperado: **400** —
`{"tipo_entidad": ["El tipo de entidad indicado no es válido o no es asignable a un perfil."]}`.
Repetir con `"auditlog"` o `"campoclinico"` → mismo **400**. Esto confirma que lookup (T11) y validación
del write (T10) comparten la única fuente `ASSIGNABLE_PROFILE_MODELS`: solo los tipos que devuelve el
lookup son aceptados por el POST de perfiles.

### 7.5 Matriz de casos T11

| Caso | Petición | Esperado |
|------|----------|----------|
| Listar (superadmin) | `GET /profile-entity-types/` | **200**, 8 items ordenados por `label` |
| No superadmin | `GET` con token normal | **403** |
| Anónimo | `GET` sin token | **401** |
| Contrato reutilizable | `POST /users/{id}/profiles/` con `tipo_entidad` del lookup | **201** |
| Fuera de allowlist | `POST` con `tipo_entidad:"document"` | **400** en español |
