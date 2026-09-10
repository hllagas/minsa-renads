# Guia de pruebas manuales — Refactor Tutor ↔ Convenio ↔ Ipress

## 1. Prerrequisitos

- Levantar el servidor: `python manage.py runserver` (lo ejecuta el usuario).
- URL base: `http://localhost:8000/api/v1/`
- Obtener token JWT:

```http
POST /api/v1/auth/token/
Content-Type: application/json

{
  "username": "admin",
  "password": "<password>"
}
```

Respuesta esperada: `200` con `{ "access": "...", "refresh": "..." }`.

Usar en todas las llamadas siguientes:

```
Authorization: Bearer <access>
```

- Alternativa interactiva: `http://localhost:8000/api/v1/docs/` (Swagger).

---

## 2. Datos previos necesarios

Los siguientes objetos deben existir antes de ejecutar los flujos. Crearlos via API o confirmar que estan sembrados:

| Objeto | Endpoint | Rol minimo |
|--------|----------|-----------|
| Universidad | `GET /api/v1/universities/` | cualquier autenticado |
| Tutor | `POST /api/v1/tutors/` | Universidad |
| Convenio Especifico vigente | `GET /api/v1/conventions/?tipo_convenio=ESPECIFICO` | cualquier autenticado |
| Convenio Marco (cualquier tipo) | `GET /api/v1/conventions/?tipo_convenio=MARCO` | cualquier autenticado |
| IPRESS (sede docente) | `GET /api/v1/ipress/` | cualquier autenticado |

Anotar los ids devueltos (se usan en los pasos siguientes):

- `<TUTOR_ID>` — PK del tutor creado
- `<CONVENIO_ESP_ID>` — PK del Convenio Especifico vigente
- `<CONVENIO_MARCO_ID>` — PK de cualquier Convenio Marco
- `<IPRESS_COD>` — `codigo_renipress` de 8 caracteres de la IPRESS (PK textual)

---

## 3. Flujo paso a paso por endpoint nuevo

### Paso 1 — Crear un tutor sin ipress (verificar que el campo no existe)

```http
POST /api/v1/tutors/
Authorization: Bearer <access>
Content-Type: application/json

{
  "tipo_documento_identidad": 1,
  "numero_documento": "12345678",
  "nombres": "Juan",
  "apellido_paterno": "Perez",
  "universidades": [<UNIVERSIDAD_ID>]
}
```

Respuesta esperada: `201`. El JSON de respuesta **no** debe contener el campo `ipress` ni `ipress_detalle`.

Anotar: `<TUTOR_ID>` = valor del campo `id` en la respuesta.

---

### Paso 2 — Listar convenios del tutor (lista vacia)

```http
GET /api/v1/tutors/<TUTOR_ID>/convenios/
Authorization: Bearer <access>
```

Respuesta esperada: `200` con `[]` (lista vacia — el tutor no tiene vinculos aun).

---

### Paso 3 — Vincular tutor a un Convenio Especifico e IPRESS

Rol requerido: `Universidad` o `Administrador RENADS`.

```http
POST /api/v1/tutors/<TUTOR_ID>/convenios/
Authorization: Bearer <access>
Content-Type: application/json

{
  "convenio": <CONVENIO_ESP_ID>,
  "ipress": "<IPRESS_COD>"
}
```

Respuesta esperada: `201` con estructura:

```json
{
  "id": <TC_ID>,
  "tutor": <TUTOR_ID>,
  "convenio": <CONVENIO_ESP_ID>,
  "ipress": "<IPRESS_COD>",
  "convenio_detalle": {
    "id": <CONVENIO_ESP_ID>,
    "titulo": "...",
    "tipo": "ESPECIFICO"
  },
  "ipress_detalle": {
    "id": "<IPRESS_COD>",
    "nombre": "..."
  }
}
```

Anotar: `<TC_ID>` = valor del campo `id` en la respuesta.

---

### Paso 4 — Listar convenios del tutor (muestra el vinculo)

```http
GET /api/v1/tutors/<TUTOR_ID>/convenios/
Authorization: Bearer <access>
```

Respuesta esperada: `200` con un array de un elemento; el elemento tiene los campos `convenio_detalle` e `ipress_detalle` poblados.

---

### Paso 5 — Obtener el vinculo individual

```http
GET /api/v1/tutors/<TUTOR_ID>/convenios/<CONVENIO_ESP_ID>/
Authorization: Bearer <access>
```

Respuesta esperada: `200` con el mismo objeto del Paso 3.

---

### Paso 6 — Eliminar el vinculo

Rol requerido: `Universidad` o `Administrador RENADS`.

```http
DELETE /api/v1/tutors/<TUTOR_ID>/convenios/<CONVENIO_ESP_ID>/
Authorization: Bearer <access>
```

Respuesta esperada: `204` sin cuerpo.

Verificar que el vinculo desaparecio repitiendo el Paso 2 (lista vacia).

---

## 4. Casos de regla de negocio (deben fallar)

### RN-TC-01 — Convenio Marco no admitido

```http
POST /api/v1/tutors/<TUTOR_ID>/convenios/
Authorization: Bearer <access>
Content-Type: application/json

{
  "convenio": <CONVENIO_MARCO_ID>,
  "ipress": "<IPRESS_COD>"
}
```

Respuesta esperada: `400` con mensaje:

```json
"Solo se pueden asociar Convenios Especificos a un tutor."
```

### RN-TC-02 — Duplicado (tutor ya asociado al mismo convenio)

Ejecutar el Paso 3 nuevamente (sin haber eliminado el vinculo o recreando uno), luego intentar:

```http
POST /api/v1/tutors/<TUTOR_ID>/convenios/
Authorization: Bearer <access>
Content-Type: application/json

{
  "convenio": <CONVENIO_ESP_ID>,
  "ipress": "<IPRESS_COD>"
}
```

Respuesta esperada: `400` con mensaje:

```json
"El tutor ya esta asociado a este convenio."
```

### Control de rol — escritura sin permiso

Usar un token de un usuario **sin** roles `Universidad` ni `Administrador RENADS` (p. ej. rol `Auditor` o usuario sin grupo):

```http
POST /api/v1/tutors/<TUTOR_ID>/convenios/
Authorization: Bearer <token_sin_rol>
Content-Type: application/json

{
  "convenio": <CONVENIO_ESP_ID>,
  "ipress": "<IPRESS_COD>"
}
```

Respuesta esperada: `403`.

```http
DELETE /api/v1/tutors/<TUTOR_ID>/convenios/<CONVENIO_ESP_ID>/
Authorization: Bearer <token_sin_rol>
```

Respuesta esperada: `403`.

### Vinculo inexistente

```http
GET /api/v1/tutors/<TUTOR_ID>/convenios/99999/
Authorization: Bearer <access>
```

Respuesta esperada: `404`.

---

## 5. Rol/permiso requerido por endpoint

| Endpoint | Metodo | Rol requerido |
|----------|--------|---------------|
| `GET /api/v1/tutors/{id}/convenios/` | GET | `IsAuthenticated` + `IsInstitutionalMember` (lectura libre para autenticados con perfil) |
| `POST /api/v1/tutors/{id}/convenios/` | POST | `Universidad` o `Administrador RENADS` |
| `GET /api/v1/tutors/{id}/convenios/{convenio_pk}/` | GET | `IsAuthenticated` + `IsInstitutionalMember` (lectura libre) |
| `DELETE /api/v1/tutors/{id}/convenios/{convenio_pk}/` | DELETE | `Universidad` o `Administrador RENADS` |

> El permiso `IsUniversityOrReadOnly` del `TutorViewSet` permite GET sin restriccion de rol adicional; la restriccion de escritura (`exigir_roles`) la aplica explicitamente cada accion de escritura (`POST`/`DELETE`) dentro de los metodos `convenios` y `convenio_detail`.

---

## 6. Verificacion del campo ipress eliminado del tutor

Confirmar que el endpoint de tutores ya no acepta ni devuelve `ipress`:

```http
GET /api/v1/tutors/<TUTOR_ID>/
Authorization: Bearer <access>
```

El JSON de respuesta **no** debe contener los campos `ipress` ni `ipress_detalle`.

```http
PATCH /api/v1/tutors/<TUTOR_ID>/
Authorization: Bearer <access>
Content-Type: application/json

{
  "ipress": "<IPRESS_COD>"
}
```

El campo `ipress` enviado debe ser ignorado o devolver `400` (campo desconocido segun la politica del serializer); en ningun caso debe persistirse en la tabla `tutor`.

---

## 7. Verificacion del filtro eliminado

El parametro de filtro `ipress` ya no existe en `GET /api/v1/tutors/`:

```http
GET /api/v1/tutors/?ipress=<IPRESS_COD>
Authorization: Bearer <access>
```

Respuesta esperada: el filtro debe ser ignorado (lista todos los tutores visibles) — el backend no lo reconoce como campo de filtro valido y no lo aplica.
