# Guía de pruebas manuales — Refactor Red/Microred, catálogos de clasificación y `ipress`

Cubre los endpoints nuevos del refactor del Módulo 1: `networks` (`red`), `micro-networks` (`microred`), `categories` (`categoria`), `classification-types` (`tipo_clasificacion`) y los campos nuevos de `ipress`.

> Un QA puede seguir esta guía sin leer el código. Cada llamada es un bloque copiable (ejemplos con `curl`; reemplazar valores entre `<>`).

## 1. Prerrequisitos

1. El **usuario** levanta el servidor (no el agente): `python manage.py runserver`.
2. URL base: `http://localhost:8000/api/v1/`.
3. Documentación interactiva alternativa: `http://localhost:8000/api/v1/docs/` (Swagger).
4. Obtener token JWT:

```bash
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "<usuario>", "password": "<password>"}'
```

Respuesta esperada (`200`): `{"access": "<access>", "refresh": "<refresh>"}`. Usar `Authorization: Bearer <access>` en todas las llamadas siguientes.

Prepara dos usuarios para probar permisos:
- **ADMIN**: superusuario o miembro del grupo `Administrador RENADS` (puede escribir).
- **LECTOR**: usuario autenticado sin ese rol (solo lectura). Obtén su propio `access`.

## 2. Datos previos necesarios

- Debe existir al menos un **ámbito geográfico sanitario** (`GET /api/v1/health-geographic-scopes/`) para crear una `red`. Anota un `id` → `<AMBITO_ID>`. Si no hay ninguno, créalo por `/admin/` o el seed correspondiente (catálogo de solo lectura por API).
- Para probar los campos de `ipress` necesitas una IPRESS existente (`GET /api/v1/ipress/`, anota `<IPRESS_ID>`) o crear una (requiere `unidad_ejecutora` y `ambito_geografico_sanitario` válidos).

## Rol/permiso por endpoint

| Endpoint | Lectura (GET) | Escritura (POST/PUT/PATCH/DELETE) |
|----------|---------------|-----------------------------------|
| `networks`, `micro-networks`, `categories`, `classification-types` | Autenticado | `Administrador RENADS` / superusuario |
| `ipress` | Autenticado | `Administrador RENADS` / superusuario |

## 3. Flujo paso a paso por endpoint nuevo

### 3.1 Crear una `categoria` (ADMIN)

```bash
curl -X POST http://localhost:8000/api/v1/categories/ \
  -H "Authorization: Bearer <ACCESS_ADMIN>" -H "Content-Type: application/json" \
  -d '{"codigo": "II-1", "nombre": "Categoria II-1", "activo": true}'
```

Esperado `201`. Anota `id` → `<CATEGORIA_ID>`.

### 3.2 Crear un `tipo_clasificacion` (ADMIN)

```bash
curl -X POST http://localhost:8000/api/v1/classification-types/ \
  -H "Authorization: Bearer <ACCESS_ADMIN>" -H "Content-Type: application/json" \
  -d '{"codigo": "HOSP", "nombre": "Hospital", "activo": true}'
```

Esperado `201`. Anota `id` → `<TIPOCLAS_ID>`.

### 3.3 Crear una `red` bajo un ámbito (ADMIN)

```bash
curl -X POST http://localhost:8000/api/v1/networks/ \
  -H "Authorization: Bearer <ACCESS_ADMIN>" -H "Content-Type: application/json" \
  -d '{"ambito_geografico_sanitario": <AMBITO_ID>, "codigo": "R01", "nombre": "Red Norte", "activo": true}'
```

Esperado `201`. Anota `id` → `<RED_ID>`.

Filtrado por padre:

```bash
curl "http://localhost:8000/api/v1/networks/?ambito_geografico_sanitario=<AMBITO_ID>&activo=true" \
  -H "Authorization: Bearer <ACCESS_ADMIN>"
```

Esperado `200` con la red creada en `results`.

### 3.4 Crear una `microred` bajo la red (ADMIN)

```bash
curl -X POST http://localhost:8000/api/v1/micro-networks/ \
  -H "Authorization: Bearer <ACCESS_ADMIN>" -H "Content-Type: application/json" \
  -d '{"red": <RED_ID>, "codigo": "MR01", "nombre": "Microred A", "activo": true}'
```

Esperado `201`. Anota `id` → `<MICRORED_ID>`.

Filtrado por red:

```bash
curl "http://localhost:8000/api/v1/micro-networks/?red=<RED_ID>" \
  -H "Authorization: Bearer <ACCESS_ADMIN>"
```

### 3.5 Actualizar una `ipress` con los campos nuevos (ADMIN)

```bash
curl -X PATCH http://localhost:8000/api/v1/ipress/<IPRESS_ID>/ \
  -H "Authorization: Bearer <ACCESS_ADMIN>" -H "Content-Type: application/json" \
  -d '{"categoria": <CATEGORIA_ID>, "tipo_clasificacion": <TIPOCLAS_ID>, "microred": <MICRORED_ID>, "latitud": "-12.046374", "longitud": "-77.042793", "cantidad_camas": 120, "numero_ruc": "20123456789"}'
```

Esperado `200`. El cuerpo devuelve los campos `categoria`, `tipo_clasificacion`, `microred`, `latitud`, `longitud`, `cantidad_camas`, `numero_ruc` persistidos.

Verificación por GET y filtros:

```bash
curl "http://localhost:8000/api/v1/ipress/?microred=<MICRORED_ID>" -H "Authorization: Bearer <ACCESS_ADMIN>"
curl "http://localhost:8000/api/v1/ipress/?categoria=<CATEGORIA_ID>" -H "Authorization: Bearer <ACCESS_ADMIN>"
curl "http://localhost:8000/api/v1/ipress/?tipo_clasificacion=<TIPOCLAS_ID>" -H "Authorization: Bearer <ACCESS_ADMIN>"
```

Esperado `200` con la IPRESS en `results`.

## 4. Casos que DEBEN fallar (reglas y validaciones)

### 4.1 RUC con formato inválido → `400`

```bash
curl -X PATCH http://localhost:8000/api/v1/ipress/<IPRESS_ID>/ \
  -H "Authorization: Bearer <ACCESS_ADMIN>" -H "Content-Type: application/json" \
  -d '{"numero_ruc": "12345"}'
```

Esperado `400` con mensaje en español: `El RUC debe tener exactamente 11 dígitos numéricos.` (también falla con no numéricos, p. ej. `"2012345678A"`).
RUC vacío es válido: `{"numero_ruc": ""}` debe devolver `200`.

### 4.2 `unique_together` de `red` → `400`

Crear una segunda `red` con el **mismo** `codigo` bajo el **mismo** `ambito_geografico_sanitario`:

```bash
curl -X POST http://localhost:8000/api/v1/networks/ \
  -H "Authorization: Bearer <ACCESS_ADMIN>" -H "Content-Type: application/json" \
  -d '{"ambito_geografico_sanitario": <AMBITO_ID>, "codigo": "R01", "nombre": "Red Duplicada"}'
```

Esperado `400` (error de unicidad). Con un `ambito_geografico_sanitario` **distinto** y el mismo `codigo` debe devolver `201`.

### 4.3 `unique_together` de `microred` → `400`

Repetir `codigo` bajo la misma `red`:

```bash
curl -X POST http://localhost:8000/api/v1/micro-networks/ \
  -H "Authorization: Bearer <ACCESS_ADMIN>" -H "Content-Type: application/json" \
  -d '{"red": <RED_ID>, "codigo": "MR01", "nombre": "Microred Duplicada"}'
```

Esperado `400`. Con otra `red` y el mismo `codigo` → `201`.

### 4.4 Escritura sin rol `Administrador RENADS` → `403`

Con el token del usuario **LECTOR**:

```bash
curl -X POST http://localhost:8000/api/v1/categories/ \
  -H "Authorization: Bearer <ACCESS_LECTOR>" -H "Content-Type: application/json" \
  -d '{"codigo": "X", "nombre": "No permitido"}'
```

Esperado `403` con `La escritura requiere el rol Administrador RENADS.` La lectura (`GET /api/v1/categories/`) con el mismo token debe devolver `200`. Repetir contra `networks`, `micro-networks`, `classification-types`.

### 4.5 `PROTECT` al borrar referenciados → `409`

- Borrar la `red` referenciada por una `microred`:

```bash
curl -X DELETE http://localhost:8000/api/v1/networks/<RED_ID>/ -H "Authorization: Bearer <ACCESS_ADMIN>"
```

Esperado `409` (`No se puede eliminar: el registro está referenciado por ...`).

- Borrar la `microred` / `categoria` / `tipo_clasificacion` referenciada por la `ipress` del paso 3.5:

```bash
curl -X DELETE http://localhost:8000/api/v1/micro-networks/<MICRORED_ID>/ -H "Authorization: Bearer <ACCESS_ADMIN>"
curl -X DELETE http://localhost:8000/api/v1/categories/<CATEGORIA_ID>/ -H "Authorization: Bearer <ACCESS_ADMIN>"
curl -X DELETE http://localhost:8000/api/v1/classification-types/<TIPOCLAS_ID>/ -H "Authorization: Bearer <ACCESS_ADMIN>"
```

Esperado `409` en cada uno mientras la `ipress` los referencie. Tras desasociarlos de la IPRESS (PATCH a `null`) el DELETE debe devolver `204`.

## 5. Limpieza (opcional)

Desasocia los campos de la `ipress` (PATCH con `null`) y luego borra `microred`, `red`, `categoria`, `classification-types` con DELETE (`204`).
