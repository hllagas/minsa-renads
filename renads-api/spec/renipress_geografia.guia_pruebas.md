# Guía de pruebas manuales — Jerarquía geográfica sanitaria (RENIPRESS) — `ipress`

Prueba del refactor de los 3 ajustes de `spec/renipress_geografia.md` sobre el endpoint `/api/v1/ipress/`:
- **A** — `codigo_renipress` único y requerido.
- **B** — coherencia `microred.red.ambito_geografico_sanitario == ipress.ambito_geografico_sanitario` (si `microred` no es nula).
- Verificación de que la lectura sigue exponiendo los `*_detalle` y la URL del logo.

---

## 1. Prerrequisitos

1. **Levantar el servidor** (lo corre el usuario, no el agente):
   ```
   python manage.py runserver
   ```
2. **URL base:** `http://localhost:8000/api/v1/`
3. **Swagger interactivo (alternativa):** `http://localhost:8000/api/v1/docs/`
4. **Obtener token JWT.** El CRUD de `ipress` es escritura solo para el rol **`Administrador RENADS`** (o superusuario); usar un usuario con ese rol:
   ```
   POST http://localhost:8000/api/v1/auth/token/
   Content-Type: application/json

   {
     "username": "<usuario_admin>",
     "password": "<contraseña>"
   }
   ```
   Respuesta esperada `200`: `{ "access": "<jwt>", "refresh": "<jwt>" }`.
5. En todas las llamadas siguientes enviar el header:
   ```
   Authorization: Bearer <access>
   ```

**Rol/permiso por operación:**
- `GET /api/v1/ipress/` y `GET /api/v1/ipress/{id}/` — cualquier usuario autenticado (lectura libre).
- `POST` / `PUT` / `PATCH` / `DELETE /api/v1/ipress/` — solo **`Administrador RENADS`** o superusuario (`IsAdminRoleOrReadOnly`).

---

## 2. Datos previos necesarios

La `ipress` referencia por id varias entidades. Antes de crear una IPRESS deben existir (ya seedeadas o creadas vía API/admin):

1. **Unidad ejecutora** (`unidad_ejecutora`, obligatoria) — `GET /api/v1/executing-units/` para tomar un `id`.
2. **Ámbito geográfico sanitario** (`ambito_geografico_sanitario`, obligatorio) — listar el catálogo correspondiente y tomar dos ids de **ámbitos distintos** (llamémoslos `AMBITO_A` y `AMBITO_B`) para la prueba de coherencia.
3. **Jerarquía red → microred** para la prueba B:
   - Una `red` cuyo `ambito_geografico_sanitario` sea `AMBITO_A` → de ella una `microred` (id `MICRORED_A`).
   - Una `red` cuyo `ambito_geografico_sanitario` sea `AMBITO_B` → de ella una `microred` (id `MICRORED_B`).
   > Nota: `red`/`microred` se pueblan por carga (loader RENIPRESS futuro) o por el admin de Django; no hay endpoint CRUD público en el alcance de este cambio. Si no hay microreds sembradas, la prueba B-1/B-2 se hace sobre `MICRORED_A`/`MICRORED_B` creadas por el admin.
4. (Opcional) `ubigeo`, `categoria`, `tipo_clasificacion` — nullable, no requeridos.

Sustituir en los payloads: `<UE_ID>`, `<AMBITO_A>`, `<AMBITO_B>`, `<MICRORED_A>` (cuelga de `AMBITO_A`), `<MICRORED_B>` (cuelga de `AMBITO_B`).

---

## 3. Flujo paso a paso

### Paso 1 — Crear IPRESS válida sin microred (ámbito directo autoritativo)

```
POST http://localhost:8000/api/v1/ipress/
Authorization: Bearer <access>
Content-Type: application/json

{
  "unidad_ejecutora": <UE_ID>,
  "nombre": "IPRESS de prueba RENIPRESS",
  "codigo_renipress": "12345678",
  "ambito_geografico_sanitario": <AMBITO_A>,
  "es_sede_docente": false,
  "activo": true
}
```
**Esperado `201`.** `microred` es nula ⇒ no se valida coherencia. Anotar el `id` devuelto (`<IPRESS_ID>`) para los siguientes pasos.
La respuesta debe incluir los campos de lectura `ambito_geografico_sanitario_detalle`, `microred_detalle` (null), `categoria_detalle`, `tipo_clasificacion_detalle`, `ubigeo_detalle` y `referencia_logo` (URL o null).

### Paso 2 — Crear IPRESS válida con microred del mismo ámbito

```
POST http://localhost:8000/api/v1/ipress/
Authorization: Bearer <access>
Content-Type: application/json

{
  "unidad_ejecutora": <UE_ID>,
  "nombre": "IPRESS con microred coherente",
  "codigo_renipress": "22222222",
  "ambito_geografico_sanitario": <AMBITO_A>,
  "microred": <MICRORED_A>,
  "activo": true
}
```
**Esperado `201`.** `microred.red.ambito == ipress.ambito` (`AMBITO_A`) ⇒ pasa. La respuesta muestra `microred_detalle` con `{id, nombre}`.

### Paso 3 — Lectura (list/retrieve) mantiene detalles y logo

```
GET http://localhost:8000/api/v1/ipress/<IPRESS_ID>/
Authorization: Bearer <access>
```
**Esperado `200`** con `*_detalle` y `referencia_logo` (URL firmada o `null`). Confirma que la lectura no cambió.

### Paso 4 — Filtros

```
GET http://localhost:8000/api/v1/ipress/?ambito_geografico_sanitario=<AMBITO_A>&activo=true
GET http://localhost:8000/api/v1/ipress/?search=12345678
```
**Esperado `200`.** El filtro por ámbito y la búsqueda por `codigo_renipress`/`nombre` devuelven la(s) IPRESS creada(s).

---

## 4. Casos de regla de negocio (deben fallar)

### Caso A-1 — `codigo_renipress` requerido (ajuste A)

```
POST http://localhost:8000/api/v1/ipress/
Authorization: Bearer <access>
Content-Type: application/json

{
  "unidad_ejecutora": <UE_ID>,
  "nombre": "Sin código RENIPRESS",
  "ambito_geografico_sanitario": <AMBITO_A>
}
```
**Esperado `400`** con error en la clave `codigo_renipress` (campo requerido).

### Caso A-2 — `codigo_renipress` duplicado (ajuste A / unicidad)

```
POST http://localhost:8000/api/v1/ipress/
Authorization: Bearer <access>
Content-Type: application/json

{
  "unidad_ejecutora": <UE_ID>,
  "nombre": "Código duplicado",
  "codigo_renipress": "12345678",
  "ambito_geografico_sanitario": <AMBITO_A>
}
```
**Esperado `400`** en la clave `codigo_renipress` (ya usado en el Paso 1; violación de unicidad).

### Caso B-1 — Crear con microred de otro ámbito (ajuste B)

```
POST http://localhost:8000/api/v1/ipress/
Authorization: Bearer <access>
Content-Type: application/json

{
  "unidad_ejecutora": <UE_ID>,
  "nombre": "Microred de otro ámbito",
  "codigo_renipress": "33333333",
  "ambito_geografico_sanitario": <AMBITO_A>,
  "microred": <MICRORED_B>
}
```
**Esperado `400`** en la clave `microred` con el mensaje:
`"La microred seleccionada pertenece a un ámbito geográfico sanitario distinto al de la IPRESS."`
(`MICRORED_B` cuelga de `AMBITO_B` ≠ `AMBITO_A`.)

### Caso B-2 — PATCH parcial que cambia solo `microred` a otro ámbito (ajuste B, resolución de estado final)

Partiendo de la IPRESS del Paso 1 (`<IPRESS_ID>`, ámbito `AMBITO_A`, sin microred), enviar **solo** `microred`:

```
PATCH http://localhost:8000/api/v1/ipress/<IPRESS_ID>/
Authorization: Bearer <access>
Content-Type: application/json

{
  "microred": <MICRORED_B>
}
```
**Esperado `400`** en la clave `microred` con el mismo mensaje del Caso B-1.
Verifica que el `validate()` reconstruye el estado final combinando la instancia (`ambito = AMBITO_A`) con el payload parcial (`microred = MICRORED_B`).

### Caso B-3 (control positivo) — PATCH parcial con microred del mismo ámbito

```
PATCH http://localhost:8000/api/v1/ipress/<IPRESS_ID>/
Authorization: Bearer <access>
Content-Type: application/json

{
  "microred": <MICRORED_A>
}
```
**Esperado `200`.** `MICRORED_A` cuelga de `AMBITO_A` (mismo ámbito de la instancia) ⇒ pasa.

### Caso de permiso — Escritura sin rol Administrador RENADS

Con un token de un usuario **sin** rol `Administrador RENADS` (p. ej. `Universidad`), repetir el `POST` del Paso 1.
**Esperado `403`** (`IsAdminRoleOrReadOnly`). El mismo usuario **sí** puede hacer `GET` (lectura libre).

---

## 5. Resumen de resultados esperados

| Caso | Método/Ruta | Estado | Clave/mensaje |
|------|-------------|--------|---------------|
| Paso 1 | `POST /ipress/` (sin microred) | 201 | — |
| Paso 2 | `POST /ipress/` (microred mismo ámbito) | 201 | — |
| Paso 3 | `GET /ipress/{id}/` | 200 | incluye `*_detalle` + `referencia_logo` |
| Paso 4 | `GET /ipress/?...` | 200 | filtros/búsqueda operan |
| A-1 | `POST` sin `codigo_renipress` | 400 | `codigo_renipress` requerido |
| A-2 | `POST` `codigo_renipress` duplicado | 400 | `codigo_renipress` unicidad |
| B-1 | `POST` microred de otro ámbito | 400 | `microred`: mensaje de coherencia |
| B-2 | `PATCH` solo `microred` a otro ámbito | 400 | `microred`: mensaje de coherencia |
| B-3 | `PATCH` microred del mismo ámbito | 200 | — |
| Permiso | `POST` sin rol admin | 403 | prohibido |
