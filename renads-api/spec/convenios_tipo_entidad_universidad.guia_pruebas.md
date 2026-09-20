# Guía de pruebas manuales — `convenios_tipo_entidad_universidad`

Módulo: **Gestionar Convenios** — Refactor `UniversityEntityType`.
Validación: EXITOSA (ver `spec/convenios_tipo_entidad_universidad.validacion.md`).

---

## 1. Prerrequisitos

1. Ejecutar la migración pendiente:
   ```
   .venv\Scripts\python.exe manage.py migrate
   ```
2. Levantar el servidor (lo corre el usuario):
   ```
   .venv\Scripts\python.exe manage.py runserver
   ```
3. URL base: `http://localhost:8000/api/v1/`
4. Obtener token JWT:
   ```
   POST http://localhost:8000/api/v1/auth/token/
   Content-Type: application/json

   { "username": "<usuario>", "password": "<clave>" }
   ```
   Respuesta: `{ "access": "...", "refresh": "..." }`.
   Usar `Authorization: Bearer <access>` en todas las llamadas siguientes.
5. Alternativa interactiva: `http://localhost:8000/api/v1/docs/` (Swagger UI).

---

## 2. Datos previos necesarios

- Al menos un usuario con cualquier rol (la lectura del catálogo requiere solo `IsAuthenticated`).
- Para las pruebas de `universities/`, debe existir al menos una universidad. Si la BD está vacía tras migrate, crear una (paso 5 abajo) o usar seed existente.
- La migración `0052` habrá sembrado los 4 tipos automáticamente; no se necesita fixture adicional.

---

## 3. Flujo paso a paso

### Paso 1 — Listar los tipos de entidad universitaria

```
GET http://localhost:8000/api/v1/university-entity-types/
Authorization: Bearer <access>
```

**Respuesta esperada:** `200 OK`

```json
[
  { "id": 1, "nombre": "Universidad", "activo": true },
  { "id": 2, "nombre": "Instituto", "activo": true },
  { "id": 3, "nombre": "Escuela superior", "activo": true },
  { "id": 4, "nombre": "Escuela de posgrado", "activo": true }
]
```

Verificar: exactamente 4 elementos, en ese orden, con los nombres exactos del seed.

---

### Paso 2 — Obtener detalle de un tipo

```
GET http://localhost:8000/api/v1/university-entity-types/1/
Authorization: Bearer <access>
```

**Respuesta esperada:** `200 OK`

```json
{ "id": 1, "nombre": "Universidad", "activo": true }
```

---

### Paso 3 — Filtrar por `activo`

```
GET http://localhost:8000/api/v1/university-entity-types/?activo=true
Authorization: Bearer <access>
```

**Respuesta esperada:** `200 OK` — los 4 tipos (todos están activos por defecto).

---

### Paso 4 — Buscar por nombre

```
GET http://localhost:8000/api/v1/university-entity-types/?search=posgrado
Authorization: Bearer <access>
```

**Respuesta esperada:** `200 OK`

```json
[{ "id": 4, "nombre": "Escuela de posgrado", "activo": true }]
```

---

### Paso 5 — Crear una universidad usando el nuevo `tipo_entidad`

Primero obtener los IDs necesarios:
- `tipo_gestion`: `GET /api/v1/university-management-types/` (ej. id del tipo `PUBLICA`)
- `tipo_autorizacion`: `GET /api/v1/authorization-types/` (ej. id del tipo `LICENCIADA`)
- `tipo_entidad`: usar el `id` del paso 1 (ej. `2` para `Instituto`)

```
POST http://localhost:8000/api/v1/universities/
Authorization: Bearer <access>
Content-Type: application/json

{
  "nombre": "Instituto de Prueba Validacion",
  "siglas": "IPV",
  "tipo_gestion": <id_tipo_gestion>,
  "tipo_entidad": 2,
  "tipo_autorizacion": <id_tipo_autorizacion>
}
```

**Respuesta esperada:** `201 Created` con el objeto universidad, incluyendo `tipo_entidad_detalle`:

```json
{
  "id": ...,
  "nombre": "Instituto de Prueba Validacion",
  "tipo_entidad": 2,
  "tipo_entidad_detalle": { "id": 2, "codigo": null, "nombre": "Instituto" },
  ...
}
```

Anotar el `id` de la universidad creada (llamarlo `<id_universidad>`) para el paso siguiente.

---

### Paso 6 — Verificar `tipo_entidad_detalle` en el listado de universidades

```
GET http://localhost:8000/api/v1/universities/<id_universidad>/
Authorization: Bearer <access>
```

**Respuesta esperada:** `200 OK`. Verificar que:
- `tipo_entidad` es `2` (el ID nuevo, no un ID de `organo_directorio`).
- `tipo_entidad_detalle` contiene `{ "id": 2, "codigo": null, "nombre": "Instituto" }`.
- No hay error 500.

---

### Paso 7 — Filtrar universidades por tipo de entidad

```
GET http://localhost:8000/api/v1/universities/?tipo_entidad=2
Authorization: Bearer <access>
```

**Respuesta esperada:** `200 OK` — lista con la universidad creada en el paso 5 (y cualquier otra con `tipo_entidad=2`). Confirmar que la universidad del paso 5 aparece.

---

### Paso 8 — Verificar `tipo_entidad_universidad` en un convenio

Si existe al menos un convenio cuya universidad tenga `tipo_entidad` seteado:

```
GET http://localhost:8000/api/v1/conventions/<id_convenio>/
Authorization: Bearer <access>
```

**Respuesta esperada:** `200 OK`. Verificar que el campo `tipo_entidad_universidad` en la respuesta devuelve el **nombre** del tipo como cadena (ej. `"Universidad"` o `"Instituto"`), no un ID ni null.

---

## 4. Casos de regla de negocio (deben fallar)

### RN-D6 — Solo lectura: `POST` en el catálogo devuelve 405

```
POST http://localhost:8000/api/v1/university-entity-types/
Authorization: Bearer <access>
Content-Type: application/json

{ "nombre": "Nuevo tipo", "activo": true }
```

**Respuesta esperada:** `405 Method Not Allowed`.
Verificar que `ReadOnlyModelViewSet` no expone `create`, `update` ni `delete`.

### RN-D6 — Solo lectura: `DELETE` en el catálogo devuelve 405

```
DELETE http://localhost:8000/api/v1/university-entity-types/1/
Authorization: Bearer <access>
```

**Respuesta esperada:** `405 Method Not Allowed`.

### RN-D7 — Sin autenticación devuelve 401

```
GET http://localhost:8000/api/v1/university-entity-types/
```

**Respuesta esperada:** `401 Unauthorized` (sin cabecera `Authorization`).

### Integridad referencial (PROTECT) — No se puede borrar un tipo en uso

Si hay universidades con `tipo_entidad=1`, intentar eliminar el tipo via Django Admin o shell provocará un error de integridad (`PROTECT`). No hay endpoint de delete (405), pero confirmar en Admin si se desea testear este caso.

---

## 5. Rol/permiso requerido por endpoint

| Endpoint | Método | Permiso mínimo |
|----------|--------|---------------|
| `/api/v1/university-entity-types/` | `GET` (lista / detalle) | `IsAuthenticated` — cualquier usuario autenticado |
| `/api/v1/university-entity-types/` | `POST` / `PUT` / `DELETE` | N/A — devuelve `405` (no implementado) |
| `/api/v1/universities/` | `GET` | `IsAuthenticated` |
| `/api/v1/universities/` | `POST` / `PUT` / `PATCH` / `DELETE` | `Administrador RENADS` (escritura de entidades) |
| `/api/v1/conventions/{id}/` | `GET` | `IsAuthenticated` (según alcance del usuario) |

---

## 6. Breaking change a comunicar al frontend

Antes de desplegar en un entorno con datos existentes:

- Los IDs del campo `tipo_entidad` de `universidad` cambiaron. Antes eran IDs de `organo_directorio`; ahora son IDs de `tipo_entidad_universidad` (1–4).
- El frontend debe llamar `GET /api/v1/university-entity-types/` para refrescar el catálogo con los nuevos IDs antes de usarlos en filtros o en formularios de creación/edición de universidades.
- El filtro `GET /api/v1/universities/?tipo_entidad=<id>` espera los nuevos IDs (1–4).
