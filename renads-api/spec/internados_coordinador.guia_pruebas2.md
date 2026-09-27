# Guía de pruebas manuales — Rediseño Coordinator.universidad

Módulo: Registrar Internados — Coordinador de tutores (RN-CRD-01..06)
Validación: `internados_coordinador.validacion2.md` — APROBADO

---

## 1. Prerrequisitos

1. Levantar el servidor: `python manage.py runserver` (lo ejecuta el usuario).
2. URL base: `http://localhost:8000/api/v1/`
3. Obtener token JWT:
```
POST http://localhost:8000/api/v1/auth/token/
Content-Type: application/json

{
  "username": "<usuario>",
  "password": "<contraseña>"
}
```
Respuesta: `{ "access": "...", "refresh": "..." }`. Usar en las siguientes llamadas:
```
Authorization: Bearer <access>
```
4. Alternativa interactiva: `http://localhost:8000/api/v1/docs/` (Swagger).

---

## 2. Datos previos necesarios

Antes de probar los endpoints del coordinador deben existir:

| Entidad | Cómo verificar/crear |
|---------|----------------------|
| Universidad | `GET /api/v1/universities/` — anotar `id` de la universidad a usar |
| Tipo de documento de identidad | `GET /api/v1/identity-document-types/` — anotar `id` de DNI |
| IPRESS sede docente | `GET /api/v1/ipress/?es_sede_docente=true` — anotar `codigo_renipress` de una sede con `es_sede_docente=true` |
| Unidad ejecutora de esa IPRESS | El campo `unidad_ejecutora_id` de la IPRESS anterior |
| Convenio Específico VIGENTE | `GET /api/v1/conventions/?tipo_convenio__codigo=ESPECIFICO&estado_actual__codigo=VIGENTE&universidad=<id>` — debe existir uno para la universidad y la unidad ejecutora de la IPRESS elegida |
| Tutor (opcional para RN-CRD-02) | `GET /api/v1/tutors/` — anotar `id` si se quiere vincular un tutor al coordinador |

Si no existen convenios vigentes para la universidad y sede elegida, `sedes-disponibles` devolverá lista vacía y `sedes` fallará RN-CRD-05.

---

## 3. Flujo paso a paso

### Paso 1 — Crear coordinador con universidad (campo ahora obligatorio)

**Rol requerido:** `Universidad` o `Administrador RENADS`

```
POST http://localhost:8000/api/v1/coordinators/
Authorization: Bearer <access>
Content-Type: application/json

{
  "universidad": <id_universidad>,
  "tipo_documento_identidad": <id_tipo_doc>,
  "numero_documento": "12345678",
  "nombres": "Juan",
  "apellido_paterno": "Pérez",
  "apellido_materno": "García",
  "activo": true
}
```

Respuesta esperada: `201 Created`
```json
{
  "id": 1,
  "universidad": <id_universidad>,
  "universidad_detalle": { "id": <id_universidad>, "nombre": "Universidad X" },
  "tipo_documento_identidad": <id_tipo_doc>,
  "numero_documento": "12345678",
  "nombres": "Juan",
  "apellido_paterno": "Pérez",
  ...
}
```
Anotar el `id` devuelto (ejemplo: `1`) — se usa en todos los pasos siguientes.

---

### Paso 2 — Verificar filtro por universidad

```
GET http://localhost:8000/api/v1/coordinators/?universidad=<id_universidad>
Authorization: Bearer <access>
```

Respuesta esperada: `200 OK` con lista que incluye el coordinador creado en el paso 1. Antes del rediseño este filtro no funcionaba si el coordinador no tenía sede asignada.

---

### Paso 3 — Listar sedes disponibles para el coordinador (nuevo endpoint)

```
GET http://localhost:8000/api/v1/coordinators/1/sedes-disponibles/
Authorization: Bearer <access>
```

Respuesta esperada: `200 OK`
```json
[
  { "id": "12345678", "nombre": "IPRESS Sede Docente X" }
]
```
Si la lista está vacía, verificar que existe un Convenio Específico VIGENTE para la universidad del coordinador y la unidad ejecutora de esa IPRESS (prerrequisito §2).

Anotar el `id` (código RENIPRESS, 8 chars) de una sede de la lista — se usa en el paso 4.

---

### Paso 4 — Asignar sede al coordinador (sin campo `universidad` en el cuerpo)

**Rol requerido:** `Universidad` o `Administrador RENADS`

```
POST http://localhost:8000/api/v1/coordinators/1/sedes/
Authorization: Bearer <access>
Content-Type: application/json

{
  "ipress": "<codigo_renipress>"
}
```

Respuesta esperada: `201 Created`
```json
{
  "id": 1,
  "coordinador": 1,
  "ipress": "<codigo_renipress>",
  "universidad_detalle": { "id": <id_universidad>, "nombre": "Universidad X" },
  "ipress_detalle": { "id": "<codigo_renipress>", "nombre": "IPRESS Sede Docente X" }
}
```
Notar que `universidad_detalle` se deriva del coordinador, no del cuerpo del POST.

Anotar el `id` de la asignación devuelta (ejemplo: `1`).

---

### Paso 5 — Verificar que la sede ya NO aparece en sedes disponibles

```
GET http://localhost:8000/api/v1/coordinators/1/sedes-disponibles/
Authorization: Bearer <access>
```

Respuesta esperada: `200 OK` con lista que ya NO incluye la sede asignada en el paso 4.

---

### Paso 6 — Listar sedes del coordinador

```
GET http://localhost:8000/api/v1/coordinators/1/sedes/
Authorization: Bearer <access>
```

Respuesta esperada: `200 OK` con lista que incluye la sede asignada. Cada ítem muestra `universidad_detalle` correcto.

---

### Paso 7 — Asignar tutor a la sede del coordinador (RN-CRD-06)

**Rol requerido:** `Universidad` o `Administrador RENADS`

Reemplazar `1` por el `id` de la asignación de sede del paso 4.

```
POST http://localhost:8000/api/v1/coordinators/1/sedes/1/tutores/
Authorization: Bearer <access>
Content-Type: application/json

{
  "tutor": <id_tutor>
}
```

Respuesta esperada: `201 Created`
```json
{
  "id": 1,
  "coordinador_sede": 1,
  "tutor": <id_tutor>,
  "tutor_detalle": { "id": <id_tutor>, "nombres": "...", "apellido_paterno": "...", "numero_documento": "..." }
}
```

---

## 4. Casos de regla de negocio que deben fallar

### RN-CRD-F1 — Crear coordinador sin `universidad` → 400

```
POST http://localhost:8000/api/v1/coordinators/
Authorization: Bearer <access>
Content-Type: application/json

{
  "tipo_documento_identidad": <id_tipo_doc>,
  "numero_documento": "99999999",
  "nombres": "Sin",
  "apellido_paterno": "Universidad",
  "activo": true
}
```
Respuesta esperada: `400 Bad Request` con `{ "universidad": ["Este campo es requerido."] }` (o similar).

---

### RN-CRD-F2 — Asignar sede que no es sede docente → 400

```
POST http://localhost:8000/api/v1/coordinators/1/sedes/
Authorization: Bearer <access>
Content-Type: application/json

{
  "ipress": "<codigo_renipress_no_sede_docente>"
}
```
Respuesta esperada: `400 Bad Request` con `"La IPRESS indicada no es una sede docente autorizada."`.

---

### RN-CRD-F3 — Asignar sede cuya unidad ejecutora no tiene Convenio Específico VIGENTE para la universidad del coordinador → 400

```
POST http://localhost:8000/api/v1/coordinators/1/sedes/
Authorization: Bearer <access>
Content-Type: application/json

{
  "ipress": "<codigo_ipress_unidad_ejecutora_sin_convenio_vigente>"
}
```
Respuesta esperada: `400 Bad Request` con `"La sede docente no pertenece a una unidad ejecutora con Convenio Específico vigente para la universidad indicada."`.

---

### RN-CRD-F4 — Asignar sede ya asignada al mismo coordinador → 400 (duplicado)

Repetir el mismo cuerpo del paso 4:
```
POST http://localhost:8000/api/v1/coordinators/1/sedes/
Authorization: Bearer <access>
Content-Type: application/json

{
  "ipress": "<codigo_renipress>"
}
```
Respuesta esperada: `400 Bad Request` con `"El coordinador ya está asignado a esta sede."`.

---

### RN-CRD-F5 — Asignar tutor ya asignado en otro coordinador de la misma (universidad, sede) → 400 (RN-CRD-06)

Crear un segundo coordinador para la misma universidad, asignarle la misma sede, e intentar asignarle el mismo tutor:
```
POST http://localhost:8000/api/v1/coordinators/2/sedes/2/tutores/
Authorization: Bearer <access>
Content-Type: application/json

{
  "tutor": <id_tutor_ya_asignado>
}
```
Respuesta esperada: `400 Bad Request` con `"El tutor ya está asignado a un coordinador en esta sede para esta universidad."`.

---

## 5. Rol/permiso requerido por endpoint

| Endpoint | Lectura | Escritura |
|----------|---------|-----------|
| `GET /api/v1/coordinators/` | `IsAuthenticated` + `IsInstitutionalMember` | — |
| `POST /api/v1/coordinators/` | — | Grupo `Universidad` o `Administrador RENADS` |
| `GET /api/v1/coordinators/{id}/sedes-disponibles/` | `IsAuthenticated` + `IsInstitutionalMember` | — |
| `GET /api/v1/coordinators/{id}/sedes/` | `IsAuthenticated` + `IsInstitutionalMember` | — |
| `POST /api/v1/coordinators/{id}/sedes/` | — | Grupo `Universidad` o `Administrador RENADS` |
| `DELETE /api/v1/coordinators/{id}/sedes/{sede_pk}/` | — | Grupo `Universidad` o `Administrador RENADS` |
| `POST /api/v1/coordinators/{id}/sedes/{sede_pk}/tutores/` | — | Grupo `Universidad` o `Administrador RENADS` |
| `DELETE /api/v1/coordinators/{id}/sedes/{sede_pk}/tutores/{tutor_pk}/` | — | Grupo `Universidad` o `Administrador RENADS` |
