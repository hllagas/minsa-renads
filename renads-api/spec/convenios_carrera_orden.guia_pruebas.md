# Guía de pruebas manuales — campo `orden` en `ProfessionalCareer`

Spec de referencia: `spec/convenios_carrera_orden.md`

---

## 1. Prerrequisitos

1. Levantar el servidor (lo ejecuta el usuario):
   ```
   python manage.py runserver
   ```
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
   Usar el campo `access` de la respuesta como `Authorization: Bearer <access>` en todas las llamadas siguientes.
4. Alternativa interactiva: `http://localhost:8000/api/v1/docs/` (Swagger UI — permite ejecutar las llamadas directamente con el token).

---

## 2. Datos previos necesarios

- Al menos una `ProfessionalCareer` (carrera profesional) existente en la base de datos. Las carreras se crean por el endpoint `POST /api/v1/professional-careers/` con un usuario de rol **Administrador RENADS**, o pueden haberse sembrado con fixtures.
- Un usuario con grupo **Administrador RENADS** (escritura).
- Un usuario sin ese grupo, p. ej. rol **Universidad** o solo `IsAuthenticated` (lectura).

Si no hay ninguna carrera:
```
POST http://localhost:8000/api/v1/professional-careers/
Authorization: Bearer <access_admin>
Content-Type: application/json

{
  "nombre": "Medicina Humana",
  "nivel_academico": <id_nivel>,
  "orden": 0,
  "activo": true
}
```
Guardar el `id` devuelto en la respuesta (llamado `{id}` en los pasos siguientes).

---

## 3. Flujo paso a paso

### Paso 1 — Verificar que el campo `orden` aparece en la lista

```
GET http://localhost:8000/api/v1/professional-careers/
Authorization: Bearer <access>
```

Respuesta esperada: `200 OK`. Cada objeto del array debe incluir el campo `"orden"` con un valor entero (default `0` para registros existentes).

Ejemplo de un objeto en la respuesta:
```json
{
  "id": 1,
  "nombre": "Medicina Humana",
  "nivel_academico": 1,
  "orden": 0,
  "activo": true
}
```

### Paso 2 — Verificar orden por defecto (orden ASC, luego nombre ASC)

```
GET http://localhost:8000/api/v1/professional-careers/
Authorization: Bearer <access>
```

Si existen varias carreras con distintos `orden`, la lista debe aparecer ordenada: primero las de `orden` menor; entre las de igual `orden`, alfabéticamente por `nombre`.

### Paso 3 — Verificar que `orden` aparece también en el detalle

```
GET http://localhost:8000/api/v1/professional-careers/{id}/
Authorization: Bearer <access>
```

Respuesta esperada: `200 OK`. El objeto incluye `"orden"`.

### Paso 4 — Ordenar explícitamente por `orden` ASC

```
GET http://localhost:8000/api/v1/professional-careers/?ordering=orden
Authorization: Bearer <access>
```

Respuesta esperada: `200 OK`. Resultados ordenados por `orden` de menor a mayor.

### Paso 5 — Ordenar explícitamente por `orden` DESC

```
GET http://localhost:8000/api/v1/professional-careers/?ordering=-orden
Authorization: Bearer <access>
```

Respuesta esperada: `200 OK`. Resultados ordenados por `orden` de mayor a menor.

### Paso 6 — Ordenar explícitamente por `nombre`

```
GET http://localhost:8000/api/v1/professional-careers/?ordering=nombre
Authorization: Bearer <access>
```

Respuesta esperada: `200 OK`. Resultados ordenados alfabéticamente por `nombre`.

### Paso 7 — Actualizar `orden` como Administrador RENADS (debe funcionar)

```
PATCH http://localhost:8000/api/v1/professional-careers/{id}/
Authorization: Bearer <access_admin>
Content-Type: application/json

{
  "orden": 5
}
```

Respuesta esperada: `200 OK`. El cuerpo devuelve la carrera con `"orden": 5`.

Confirmar con una llamada de detalle:
```
GET http://localhost:8000/api/v1/professional-careers/{id}/
Authorization: Bearer <access_admin>
```
El campo `"orden"` debe ser `5`.

Restaurar a `0` si se desea (opcional):
```
PATCH http://localhost:8000/api/v1/professional-careers/{id}/
Authorization: Bearer <access_admin>
Content-Type: application/json

{ "orden": 0 }
```

---

## 4. Casos que deben fallar (reglas de permiso)

### Caso F1 — PATCH de `orden` sin rol Administrador RENADS

Usar un token de usuario **sin** el grupo `Administrador RENADS` (p. ej. rol `Universidad`):

```
PATCH http://localhost:8000/api/v1/professional-careers/{id}/
Authorization: Bearer <access_no_admin>
Content-Type: application/json

{
  "orden": 99
}
```

Respuesta esperada: `403 Forbidden`.

### Caso F2 — POST de nueva carrera sin rol Administrador RENADS

```
POST http://localhost:8000/api/v1/professional-careers/
Authorization: Bearer <access_no_admin>
Content-Type: application/json

{
  "nombre": "Test",
  "nivel_academico": 1,
  "orden": 1,
  "activo": true
}
```

Respuesta esperada: `403 Forbidden`.

### Caso F3 — Acceso sin token

```
GET http://localhost:8000/api/v1/professional-careers/
```

Respuesta esperada: `401 Unauthorized`.

---

## 5. Rol/permiso requerido por endpoint

| Operación | Endpoint | Rol mínimo |
|-----------|----------|------------|
| Listar carreras | `GET /api/v1/professional-careers/` | Cualquier usuario autenticado |
| Detalle de carrera | `GET /api/v1/professional-careers/{id}/` | Cualquier usuario autenticado |
| Crear carrera | `POST /api/v1/professional-careers/` | Administrador RENADS |
| Actualizar `orden` (u otro campo) | `PATCH /api/v1/professional-careers/{id}/` | Administrador RENADS |
| Reemplazar carrera | `PUT /api/v1/professional-careers/{id}/` | Administrador RENADS |
| Eliminar carrera | `DELETE /api/v1/professional-careers/{id}/` | Administrador RENADS |
