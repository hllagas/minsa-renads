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
