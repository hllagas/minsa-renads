# API — Gestión de Usuarios (usuarios, roles/grupos y permisos)

Contrato de la administración transversal de **usuarios, grupos (roles) y permisos** (`apps/common`).
Alimenta la ruta **`/usuarios`** (Módulo 7 del MVP). Base: `/api/v1/`. JWT requerido.

> Fuente de verdad backend: `apps/common/{urls,views,serializers}.py`. Auth/sesión: `docs/api-auth.md`.
> **Acceso:** los tres recursos exigen **`IsSuperUser`** → solo **superadministrador** (`es_superusuario`).
> Es más estricto que `Administrador RENADS`; el menú/rutas de `/usuarios` se gatean a superusuario.

## Recursos

| Endpoint | Tipo | Acceso |
|----------|------|--------|
| `users` | CRUD (DELETE = desactiva) | Superusuario |
| `groups` | CRUD (roles + permisos) | Superusuario |
| `permissions` | Solo lectura (catálogo) | Superusuario |

> `user-entity-profiles` (perfil institucional usuario↔entidad) sigue en `apps/convenios`
> (`ENTITY_VIEWSETS`, `Administrador RENADS`). Es **polimórfico** (`tipo_contenido` + `id_objeto`) y su
> **alta** depende del endpoint `content-types` (aún inexistente) — ver §"Perfiles institucionales".

---

## 1. Usuarios — `users`

ModelViewSet. **`DELETE` desactiva** (`is_active=False`), no borra (conserva trazabilidad).

| Método | Ruta | Notas |
|--------|------|-------|
| GET | `/users/` , `/users/{id}/` | lista/detalle |
| POST | `/users/` | alta (incluye `password`) |
| PUT/PATCH | `/users/{id}/` | edición (sin `password`) |
| DELETE | `/users/{id}/` | desactiva (`is_active=False`) |
| POST | `/users/{id}/set-password/` | `{ "password": "…" }` → cambia contraseña |

**Filtros:** `is_active`, `is_superuser`, `is_staff`, `groups`. **Search:** `username`, `email`,
`first_name`, `last_name`. **Ordering:** `id`, `username`, `date_joined`, `last_login` (default `id`).

### User — lectura (`GET`)
```
id, username, email, first_name, last_name, is_active, is_staff, is_superuser,
date_joined, last_login, groups (ids), groups_detalle ([{ id, name }])
```
Todos read-only en lectura.

### User — alta (`POST`)
```
username, email*, first_name, last_name, password* (write-only, validada),
is_active, is_staff, is_superuser, groups (ids)
```
`email` único (valida duplicado). `password` se hashea con `set_password` y nunca se devuelve.

### User — edición (`PUT/PATCH`)
```
username, email*, first_name, last_name, is_active, is_staff, is_superuser, groups (ids)
```
La contraseña **no** se edita aquí: usar la acción `set-password`.

(\* = requerido.)

---

## 2. Roles / Grupos — `groups`

ModelViewSet (roles con asignación de permisos). **Search:** `name`. **Ordering:** `id`, `name`
(default `name`).

| Método | Ruta | Notas |
|--------|------|-------|
| GET | `/groups/` , `/groups/{id}/` | lista/detalle |
| POST·PUT·PATCH·DELETE | `/groups/…` | CRUD |

### Group — lectura/escritura
```
id, name*, permissions (ids), permissions_detalle ([{ id, name, codename, content_type, app_label, model }])
```
Escritura: `name` + `permissions` (lista de ids de permiso). `permissions_detalle` es read-only.

---

## 3. Permisos — `permissions` (solo lectura)

Catálogo de permisos de Django (ReadOnly). Para poblar el selector de permisos de un rol.

| Método | Ruta |
|--------|------|
| GET | `/permissions/` , `/permissions/{id}/` |

**Filtros:** `content_type`, `content_type__app_label`. **Search:** `name`, `codename`.
**Ordering:** `id`, `codename` (default `content_type`, `codename`).

### Permission — lectura
```
id, name, codename, content_type, app_label, model
```
Todos read-only.

---

## Perfiles institucionales — `user-entity-profiles` (parcial)

Vincula un usuario con una entidad concreta (alcance) y un `grupo`/rol. Escritura `Administrador
RENADS`. Filtros: `usuario`, `grupo`, `activo`. **Polimórfico** (`tipo_contenido` + `id_objeto`).

- **v1 viable:** list + filtros (`usuario`, `grupo`, `activo`) + editar `activo` + eliminar.
- **Alta diferida:** requiere resolver `tipo_contenido` (ContentType) → depende de un endpoint
  `content-types` (aún inexistente). Registrar requerimiento backend para habilitar el alta.

---

## Gating (UX; el backend es la autoridad)

- **`/usuarios` completo** (usuarios/grupos/permisos): **solo superusuario** (`es_superusuario`).
- **Perfiles institucionales:** escritura `Administrador RENADS`.
- Las contraseñas nunca se muestran; el alta envía `password` write-only y el cambio usa
  `set-password`. No registrar el valor de la contraseña en la auditoría (el backend ya lo evita).

## Pendiente (SDD)

Documento de contexto/contrato. Siguiente paso: `spec/usuarios.md` (aprobación humana antes de
implementar). Ver `docs/mvp.md` (módulo 7).
