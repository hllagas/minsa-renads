# Guía de pruebas manuales — Refactor Ámbito Geográfico Sanitario + Unidad Ejecutora

**Módulo:** `apps/convenios`
**Endpoints nuevos/modificados:** `health-geographic-scopes`, `executing-units`
**Breaking changes de API documentados:** ver spec §"Breaking changes de API"

---

## 1. Prerrequisitos

1. Levantar el servidor (ejecutado por el usuario):
   ```
   python manage.py runserver
   ```
   URL base: `http://localhost:8000/api/v1/`

2. Obtener token JWT:
   ```
   POST http://localhost:8000/api/v1/auth/token/
   Content-Type: application/json

   {
     "username": "admin",
     "password": "<contraseña>"
   }
   ```
   Respuesta: `{"access": "<token>", "refresh": "..."}`.
   Usar `Authorization: Bearer <access>` en todas las llamadas siguientes.

3. Alternativa interactiva: `http://localhost:8000/api/v1/docs/` (Swagger UI).

4. El usuario que hace escritura debe pertenecer al grupo **Administrador RENADS**.

---

## 2. Datos previos necesarios

- Al menos un `RegionalGovernment` existente (ya debería estar seedeado). Obtener un id con:
  ```
  GET http://localhost:8000/api/v1/regional-governments/
  ```
  Anotar `id` de alguno (p. ej. `id=1`, nombre "Gobierno Regional de Amazonas").

- Al menos un `HealthGeographicScope` existente (ya debería estar seedeado). Obtener un id con:
  ```
  GET http://localhost:8000/api/v1/health-geographic-scopes/
  ```
  Anotar `id` de alguno (p. ej. `id=1`, nombre "Amazonas").

---

## 3. Flujo de prueba: Refactor 1 — `HealthGeographicScope` con `gobierno_regional`

### Paso 3.1 — Verificar que `gobierno_regional` aparece en la respuesta

```
GET http://localhost:8000/api/v1/health-geographic-scopes/
Authorization: Bearer <access>
```

Respuesta esperada (200 OK), cada ítem debe incluir:
```json
{
  "id": 1,
  "codigo": "01",
  "nombre": "Amazonas",
  "activo": true,
  "gobierno_regional": 1,
  "gobierno_regional_detalle": {
    "id": 1,
    "codigo": null,
    "nombre": "Gobierno Regional de Amazonas"
  }
}
```

Verificar:
- Los 4 ámbitos DIRIS (nombre contiene "DIRIS") tienen `"gobierno_regional": null` y `"gobierno_regional_detalle": null`.
- Los ámbitos regionales (25) tienen `"gobierno_regional"` no nulo con el GORE correspondiente.

### Paso 3.2 — Actualizar `gobierno_regional` de un ámbito (escritura, rol Administrador RENADS)

```
PATCH http://localhost:8000/api/v1/health-geographic-scopes/1/
Authorization: Bearer <access>
Content-Type: application/json

{
  "gobierno_regional": 1
}
```

Respuesta esperada: 200 OK con el ámbito actualizado incluyendo `gobierno_regional_detalle`.

### Paso 3.3 — RN: DIRIS con gobierno_regional nulo (caso informativo)

Si un DIRIS tiene `gobierno_regional: null` no es un error de negocio sino el estado correcto. Verificar que el endpoint acepta `PATCH {"gobierno_regional": null}` sobre un DIRIS sin rechazar (es un campo nullable).

---

## 4. Flujo de prueba: Refactor 2 — `ExecutingUnit` con PK textual y ámbito

### Paso 4.1 — Listar unidades ejecutoras con nueva estructura

```
GET http://localhost:8000/api/v1/executing-units/
Authorization: Bearer <access>
```

Verificar que la respuesta NO incluye los campos `id` (int), `tipo_organo`, `gobierno_regional`, `direccion`, `ubigeo`, `referencia_logo`.

Verificar que SÍ incluye:
```json
{
  "codigo": "0001",
  "nombre": "...",
  "activo": true,
  "ambito_geografico_sanitario": 1,
  "ambito_geografico_sanitario_detalle": {
    "id": 1,
    "codigo": "01",
    "nombre": "Amazonas"
  }
}
```

El identificador en la URL es el código de 4 chars: `GET /api/v1/executing-units/0001/`.

### Paso 4.2 — Crear una unidad ejecutora (con PK textual)

Requiere: `ambito_geografico_sanitario` id existente (del paso 2).

```
POST http://localhost:8000/api/v1/executing-units/
Authorization: Bearer <access>
Content-Type: application/json

{
  "codigo": "0099",
  "nombre": "Unidad Ejecutora de Prueba",
  "ambito_geografico_sanitario": 1,
  "activo": true
}
```

Respuesta esperada: 201 Created.
```json
{
  "codigo": "0099",
  "nombre": "Unidad Ejecutora de Prueba",
  "activo": true,
  "ambito_geografico_sanitario": 1,
  "ambito_geografico_sanitario_detalle": { "id": 1, "codigo": "01", "nombre": "Amazonas" }
}
```

Verificar que el `pk` en la URL es `0099`: `GET /api/v1/executing-units/0099/` devuelve el registro.

### Paso 4.3 — Editar unidad ejecutora (PATCH parcial)

```
PATCH http://localhost:8000/api/v1/executing-units/0099/
Authorization: Bearer <access>
Content-Type: application/json

{
  "nombre": "Unidad Ejecutora Actualizada"
}
```

Respuesta esperada: 200 OK con el nombre actualizado.

### Paso 4.4 — Filtro por `ambito_geografico_sanitario`

```
GET http://localhost:8000/api/v1/executing-units/?ambito_geografico_sanitario=1
Authorization: Bearer <access>
```

Respuesta esperada: 200 OK con solo las unidades ejecutoras del ámbito `id=1`.

### Paso 4.5 — Filtro por `activo`

```
GET http://localhost:8000/api/v1/executing-units/?activo=true
Authorization: Bearer <access>
```

Respuesta esperada: 200 OK con solo las unidades ejecutoras activas.

### Paso 4.6 — Verificar que no existen `upload-logo` ni `logo-url`

```
POST http://localhost:8000/api/v1/executing-units/0099/upload-logo/
Authorization: Bearer <access>
```

Respuesta esperada: **404 Not Found** (la acción ya no existe).

---

## 5. Casos de regla de negocio que deben fallar (400/403/404)

### RN-01: Filtros obsoletos retornan resultados vacíos (no 400)

django-filter ignora los campos no declarados sin lanzar error. Los filtros `?tipo_organo=1` y `?gobierno_regional=1` sobre `executing-units` devuelven la lista completa sin filtrar (no 400), porque no están declarados en `filterset_fields`.

```
GET http://localhost:8000/api/v1/executing-units/?tipo_organo=1
```
Resultado esperado: 200 OK (lista completa, el filtro es ignorado). Este es el comportamiento estándar de django-filter cuando el campo no está en `filterset_fields`.

### RN-02: Código duplicado al crear (unicidad de PK)

```
POST http://localhost:8000/api/v1/executing-units/
Authorization: Bearer <access>
Content-Type: application/json

{
  "codigo": "0099",
  "nombre": "Duplicado",
  "ambito_geografico_sanitario": 1
}
```

Respuesta esperada: **400 Bad Request** con mensaje de violación de unicidad en `codigo` (es PK).

### RN-03: Crear unidad ejecutora sin código (PK requerida)

```
POST http://localhost:8000/api/v1/executing-units/
Authorization: Bearer <access>
Content-Type: application/json

{
  "nombre": "Sin código",
  "ambito_geografico_sanitario": 1
}
```

Respuesta esperada: **400 Bad Request** indicando que `codigo` es requerido.

### RN-04: Acceder a unidad ejecutora por id entero (rompe con API anterior)

```
GET http://localhost:8000/api/v1/executing-units/1/
Authorization: Bearer <access>
```

Respuesta esperada: **404 Not Found** si `"1"` (como string de 1 char) no existe como `codigo`. Los clientes que usaban el int autoincremental deben migrar a usar el código de 4 chars.

### RN-05: Escritura sin autenticación

```
POST http://localhost:8000/api/v1/executing-units/
Content-Type: application/json

{"codigo": "0088", "nombre": "Test", "ambito_geografico_sanitario": 1}
```

Respuesta esperada: **401 Unauthorized**.

### RN-06: Escritura con rol no-admin

Si el usuario tiene un rol distinto de `Administrador RENADS` (p. ej. `Universidad`):
```
POST http://localhost:8000/api/v1/executing-units/
Authorization: Bearer <token_universidad>
Content-Type: application/json

{"codigo": "0088", "nombre": "Test", "ambito_geografico_sanitario": 1}
```

Respuesta esperada: **403 Forbidden**.

---

## 6. Prueba de impacto en convenios: `unidad_ejecutora_detalle` con PK string

Si existe un `Convention` con `unidad_ejecutora` asignada:

```
GET http://localhost:8000/api/v1/conventions/<id>/
Authorization: Bearer <access>
```

Verificar que la respuesta incluye:
```json
{
  "unidad_ejecutora": "0099",
  "unidad_ejecutora_detalle": {
    "codigo": "0099",
    "nombre": "Unidad Ejecutora de Prueba"
  }
}
```

El `codigo` es string de 4 chars (antes era string de longitud variable; ahora es exactamente 4).

---

## 7. Prueba de impacto en IPRESS: filtro por unidad ejecutora con código string

Si existen IPRESS con `unidad_ejecutora` asignada:

```
GET http://localhost:8000/api/v1/ipress/?unidad_ejecutora=0099
Authorization: Bearer <access>
```

Respuesta esperada: 200 OK con las IPRESS de esa unidad ejecutora. **Breaking change:** los clientes que antes enviaban `?unidad_ejecutora=1` (int) deben cambiar a `?unidad_ejecutora=0001` (string de 4 chars).

---

## 8. Prueba de generación de PDF (si aplica)

Si se genera un PDF de convenio con parte `UNIDAD_EJECUTORA`:

```
POST http://localhost:8000/api/v1/conventions/<id>/generar-proyecto/
Authorization: Bearer <access>
```

Verificar que la generación no lanza `AttributeError` sobre el campo `direccion` (que ya no existe en `ExecutingUnit`). El domicilio de la parte `UNIDAD_EJECUTORA` en el PDF debe aparecer en blanco (cadena vacía) sin error.

---

## 9. Rol requerido por endpoint

| Endpoint | Lectura | Escritura (POST/PATCH/DELETE) |
|----------|---------|-------------------------------|
| `GET /api/v1/health-geographic-scopes/` | Cualquier usuario autenticado | Administrador RENADS |
| `GET /api/v1/executing-units/` | Cualquier usuario autenticado | Administrador RENADS |
| `POST /api/v1/executing-units/` | — | Administrador RENADS |
| `PATCH /api/v1/executing-units/<codigo>/` | — | Administrador RENADS |
| `DELETE /api/v1/executing-units/<codigo>/` | — | Administrador RENADS |
