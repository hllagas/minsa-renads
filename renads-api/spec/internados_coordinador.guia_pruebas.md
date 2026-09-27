# Guía de pruebas manuales — Coordinador de tutores (`internados`)

---

## 1. Prerrequisitos

1. Levantar el servidor: `python manage.py runserver` (lo corre el usuario).
2. URL base: `http://localhost:8000/api/v1/`
3. Documentación interactiva: `http://localhost:8000/api/v1/docs/` (Swagger).
4. Obtener token JWT:

```http
POST /api/v1/auth/token/
Content-Type: application/json

{
  "username": "<numero_documento_usuario>",
  "password": "<contraseña>"
}
```

Respuesta esperada `200`:
```json
{ "access": "<token_access>", "refresh": "..." }
```

5. Usar en todas las llamadas siguientes:
```
Authorization: Bearer <access>
```

**Roles requeridos para escritura:** `Universidad` o `Administrador RENADS`.
**Lectura:** cualquier usuario autenticado con perfil institucional.

---

## 2. Datos previos necesarios

Los siguientes catálogos/entidades deben existir antes de probar el coordinador. Si el proyecto tiene datos semilla (fixtures), ya están disponibles.

| Entidad | Endpoint de consulta | Necesario para |
|---------|---------------------|----------------|
| `IdentityDocumentType` | `GET /api/v1/identity-document-types/` | Crear coordinador |
| `University` | `GET /api/v1/universities/` | Asignar sede |
| `Ipress` (`es_sede_docente=True`) | `GET /api/v1/ipress/` | Asignar sede |
| `Convention` (Específico, VIGENTE, con `unidad_ejecutora` igual a la `ipress`) | `GET /api/v1/conventions/` | Validar RN-CRD-05 |
| `Tutor` | `GET /api/v1/tutors/` | Asignar tutor a sede |

Variables que se reutilizan en los pasos:
- `{tipo_documento_id}` — id de un `IdentityDocumentType` (p. ej. tipo DNI)
- `{universidad_id}` — id de una `University`
- `{ipress_codigo}` — código RENIPRESS de 8 chars de una IPRESS sede docente
- `{tutor_id}` — id de un `Tutor`

---

## 3. Flujo paso a paso

### Paso 1 — Crear un coordinador

```http
POST /api/v1/coordinators/
Authorization: Bearer <access>
Content-Type: application/json

{
  "tipo_documento_identidad": {tipo_documento_id},
  "numero_documento": "12345678",
  "nombres": "Ana",
  "apellido_paterno": "Torres",
  "apellido_materno": "Vega",
  "correo": "ana.torres@ejemplo.pe",
  "telefono": "987654321",
  "activo": true
}
```

**Respuesta esperada `201`:**
```json
{
  "id": 1,
  "tutor": null,
  "tutor_detalle": null,
  "tipo_documento_identidad": {tipo_documento_id},
  "numero_documento": "12345678",
  "nombres": "Ana",
  "apellido_paterno": "Torres",
  "apellido_materno": "Vega",
  "correo": "ana.torres@ejemplo.pe",
  "telefono": "987654321",
  "numero_colegiatura": null,
  "direccion": null,
  "ubigeo": null,
  "especialidad": null,
  "profesion": null,
  "activo": true
}
```

Guardar el `id` devuelto como `{coordinador_id}` para los pasos siguientes.

---

### Paso 2 — Listar coordinadores

```http
GET /api/v1/coordinators/
Authorization: Bearer <access>
```

**Respuesta esperada `200`:** array con el coordinador creado.

Filtros disponibles: `?activo=true`, `?sedes__universidad={universidad_id}`, `?sedes__ipress={ipress_codigo}`.
Búsqueda: `?search=Torres`.

---

### Paso 3 — Obtener detalle de un coordinador

```http
GET /api/v1/coordinators/{coordinador_id}/
Authorization: Bearer <access>
```

**Respuesta esperada `200`:** objeto del coordinador.

---

### Paso 4 — Actualizar un coordinador (PATCH parcial)

```http
PATCH /api/v1/coordinators/{coordinador_id}/
Authorization: Bearer <access>
Content-Type: application/json

{
  "telefono": "999000111"
}
```

**Respuesta esperada `200`:** objeto actualizado con `telefono: "999000111"`.

---

### Paso 5 — Asignar una sede al coordinador

Requiere una IPRESS con `es_sede_docente=True` cuya `unidad_ejecutora` tenga un Convenio Específico VIGENTE para la `universidad` indicada (RN-CRD-04/05).

```http
POST /api/v1/coordinators/{coordinador_id}/sedes/
Authorization: Bearer <access>
Content-Type: application/json

{
  "universidad": {universidad_id},
  "ipress": "{ipress_codigo}"
}
```

**Respuesta esperada `201`:**
```json
{
  "id": 1,
  "coordinador": {coordinador_id},
  "universidad": {universidad_id},
  "ipress": "{ipress_codigo}",
  "universidad_detalle": {"id": {universidad_id}, "nombre": "Universidad Nacional..."},
  "ipress_detalle": {"id": "{ipress_codigo}", "nombre": "Hospital..."}
}
```

Guardar el `id` como `{sede_id}`.

---

### Paso 6 — Listar sedes del coordinador

```http
GET /api/v1/coordinators/{coordinador_id}/sedes/
Authorization: Bearer <access>
```

**Respuesta esperada `200`:** array con la sede asignada.

---

### Paso 7 — Obtener detalle de una sede

```http
GET /api/v1/coordinators/{coordinador_id}/sedes/{sede_id}/
Authorization: Bearer <access>
```

**Respuesta esperada `200`:** objeto de la asignación coordinador-sede.

---

### Paso 8 — Asignar un tutor a la sede del coordinador (RN-CRD-06)

```http
POST /api/v1/coordinators/{coordinador_id}/sedes/{sede_id}/tutores/
Authorization: Bearer <access>
Content-Type: application/json

{
  "tutor": {tutor_id}
}
```

**Respuesta esperada `201`:**
```json
{
  "id": 1,
  "coordinador_sede": {sede_id},
  "tutor": {tutor_id},
  "tutor_detalle": {
    "id": {tutor_id},
    "nombres": "Carlos",
    "apellido_paterno": "Quispe",
    "numero_documento": "87654321"
  }
}
```

Guardar el `tutor_id` asignado para el paso de desasignación.

---

### Paso 9 — Listar tutores de la sede del coordinador

```http
GET /api/v1/coordinators/{coordinador_id}/sedes/{sede_id}/tutores/
Authorization: Bearer <access>
```

**Respuesta esperada `200`:** array con el tutor asignado.

---

### Paso 10 — Desasignar tutor de la sede

```http
DELETE /api/v1/coordinators/{coordinador_id}/sedes/{sede_id}/tutores/{tutor_id}/
Authorization: Bearer <access>
```

**Respuesta esperada `204 No Content`.**

---

### Paso 11 — Desasignar sede (CASCADE → tutores)

Primero reasignar el tutor del paso 8 si fue eliminado. Luego:

```http
DELETE /api/v1/coordinators/{coordinador_id}/sedes/{sede_id}/
Authorization: Bearer <access>
```

**Respuesta esperada `204 No Content`.**

Verificar que la sede ya no aparece en `GET /api/v1/coordinators/{coordinador_id}/sedes/` y que los `CoordinatorTutor` de esa sede fueron eliminados por CASCADE.

---

### Paso 12 — Eliminar coordinador

```http
DELETE /api/v1/coordinators/{coordinador_id}/
Authorization: Bearer <access>
```

**Respuesta esperada `204 No Content`.**

---

### Paso 13 — Vincular un coordinador con un tutor existente (RN-CRD-02)

Crear un segundo coordinador que sea también tutor:

```http
POST /api/v1/coordinators/
Authorization: Bearer <access>
Content-Type: application/json

{
  "tutor": {tutor_id},
  "tipo_documento_identidad": {tipo_documento_id},
  "numero_documento": "99887766",
  "nombres": "Luis",
  "apellido_paterno": "Mamani",
  "activo": true
}
```

**Respuesta esperada `201`** con `"tutor_detalle": {"id": {tutor_id}, "nombres": "...", "apellido_paterno": "..."}`.

---

## 4. Casos de regla de negocio — deben fallar

### RN-CRD-02 — `tutor_id` único entre coordinadores

Intentar crear un segundo coordinador con el mismo `tutor` que el creado en el Paso 13:

```http
POST /api/v1/coordinators/
Authorization: Bearer <access>
Content-Type: application/json

{
  "tutor": {tutor_id},
  "tipo_documento_identidad": {tipo_documento_id},
  "numero_documento": "11223344",
  "nombres": "Otro",
  "apellido_paterno": "Coordinador",
  "activo": true
}
```

**Respuesta esperada `400`** con mensaje indicando que el tutor ya está vinculado a otro coordinador (constraint `OneToOneField`).

---

### RN-CRD-04 — IPRESS no es sede docente

Usar el código de una IPRESS cuyo campo `es_sede_docente=False`:

```http
POST /api/v1/coordinators/{coordinador_id}/sedes/
Authorization: Bearer <access>
Content-Type: application/json

{
  "universidad": {universidad_id},
  "ipress": "{ipress_no_sede_codigo}"
}
```

**Respuesta esperada `400`:**
```json
{
  "detail": "La IPRESS indicada no es una sede docente autorizada."
}
```

---

### RN-CRD-05 — Sin Convenio Específico vigente para la universidad

Usar una IPRESS sede docente cuya `unidad_ejecutora` no tenga Convenio Específico VIGENTE para la `universidad` indicada (p. ej. combinación universidad–ipress sin convenio activo):

```http
POST /api/v1/coordinators/{coordinador_id}/sedes/
Authorization: Bearer <access>
Content-Type: application/json

{
  "universidad": {universidad_sin_convenio_id},
  "ipress": "{ipress_codigo}"
}
```

**Respuesta esperada `400`:**
```json
{
  "detail": "La sede docente no pertenece a una unidad ejecutora con Convenio Específico vigente para la universidad indicada."
}
```

---

### RN-CRD-05 + CRD-04 — Asignación duplicada de sede

Después de asignar una sede en el Paso 5, intentar asignarla de nuevo:

```http
POST /api/v1/coordinators/{coordinador_id}/sedes/
Authorization: Bearer <access>
Content-Type: application/json

{
  "universidad": {universidad_id},
  "ipress": "{ipress_codigo}"
}
```

**Respuesta esperada `400`:**
```json
{
  "detail": "El coordinador ya está asignado a esta sede para esta universidad."
}
```

---

### RN-CRD-06 — Tutor ya asignado a otro coordinador en la misma (universidad, sede)

1. Crear un segundo coordinador (`{coordinador_id_2}`).
2. Asignarle la misma sede (`{sede_id_2}` del segundo coordinador, misma universidad + ipress).
3. Intentar asignar el mismo tutor (ya asignado al `{coordinador_id}`) al `{coordinador_id_2}`:

```http
POST /api/v1/coordinators/{coordinador_id_2}/sedes/{sede_id_2}/tutores/
Authorization: Bearer <access>
Content-Type: application/json

{
  "tutor": {tutor_id}
}
```

**Respuesta esperada `400`:**
```json
{
  "detail": "El tutor ya está asignado a un coordinador en esta sede para esta universidad."
}
```

---

### Permiso — escritura sin rol

Con un usuario autenticado sin grupo `Universidad` ni `Administrador RENADS`:

```http
POST /api/v1/coordinators/
Authorization: Bearer <access_sin_rol_escritura>
Content-Type: application/json

{ "numero_documento": "11111111", "nombres": "Test", "apellido_paterno": "Test",
  "tipo_documento_identidad": {tipo_documento_id}, "activo": true }
```

**Respuesta esperada `403`:**
```json
{
  "detail": "La escritura requiere el rol Universidad o Administrador RENADS."
}
```

---

## 5. Roles y permisos por endpoint

| Endpoint | Método | Rol mínimo requerido |
|----------|--------|-----------------------|
| `GET /api/v1/coordinators/` | GET | Autenticado |
| `POST /api/v1/coordinators/` | POST | `Universidad` o `Administrador RENADS` |
| `GET /api/v1/coordinators/{id}/` | GET | Autenticado |
| `PATCH /api/v1/coordinators/{id}/` | PATCH | `Universidad` o `Administrador RENADS` |
| `DELETE /api/v1/coordinators/{id}/` | DELETE | `Universidad` o `Administrador RENADS` |
| `GET /api/v1/coordinators/{id}/sedes/` | GET | Autenticado |
| `POST /api/v1/coordinators/{id}/sedes/` | POST | `Universidad` o `Administrador RENADS` |
| `GET /api/v1/coordinators/{id}/sedes/{sede_pk}/` | GET | Autenticado |
| `DELETE /api/v1/coordinators/{id}/sedes/{sede_pk}/` | DELETE | `Universidad` o `Administrador RENADS` |
| `GET /api/v1/coordinators/{id}/sedes/{sede_pk}/tutores/` | GET | Autenticado |
| `POST /api/v1/coordinators/{id}/sedes/{sede_pk}/tutores/` | POST | `Universidad` o `Administrador RENADS` |
| `DELETE /api/v1/coordinators/{id}/sedes/{sede_pk}/tutores/{tutor_pk}/` | DELETE | `Universidad` o `Administrador RENADS` |
