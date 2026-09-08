# Guía de pruebas manuales — Refactor `organo` en `cargo_ejecutivo` (`executive-positions`)

> Validación **exitosa** (sin errores altos/medios). `python manage.py check` y
> `makemigrations --check --dry-run` quedaron limpios. Esta guía cubre el CRUD de
> `/api/v1/executive-positions/` con el nuevo FK `organo` y su regla de coherencia
> `organo == organo_directivo.organo`.

## 1. Prerrequisitos

1. El usuario levanta el servidor (no lo hace QA):
   ```
   python manage.py runserver
   ```
2. URL base: `http://localhost:8000/api/v1/`
3. Aplicar la migración pendiente (la corre el usuario, no esta guía):
   ```
   python manage.py migrate convenios
   ```
4. Obtener token JWT (usuario con rol `Administrador RENADS` para escritura):
   ```http
   POST http://localhost:8000/api/v1/auth/token/
   Content-Type: application/json

   {
     "username": "<usuario_admin>",
     "password": "<contraseña>"
   }
   ```
   Respuesta `200`: usar `access` en las siguientes llamadas como
   `Authorization: Bearer <access>`.
5. Alternativa interactiva: Swagger en `http://localhost:8000/api/v1/docs/`.

## 2. Datos previos necesarios

Deben existir (seed o creados vía API):

- **Órganos canónicos** (`/api/v1/organs/`): al menos dos categorías distintas, p. ej.
  "MINSA Administrativo" y "Gobierno Regional". Anota sus `id` (`ORGANO_A`, `ORGANO_B`).
- **Órgano del directorio** (`/api/v1/organ-directories/`): al menos uno cuyo `organo`
  sea `ORGANO_A`. Anota su `id` (`ORGDIR_A`) y confirma en su lectura que
  `organo_detalle`/`organo` apunta a `ORGANO_A`.

Consulta rápida de órganos:
```http
GET http://localhost:8000/api/v1/organs/
Authorization: Bearer <access>
```
```http
GET http://localhost:8000/api/v1/organ-directories/
Authorization: Bearer <access>
```

## 3. Flujo paso a paso

### Paso 3.1 — Listar cargos y verificar la nueva salida de lectura

```http
GET http://localhost:8000/api/v1/executive-positions/
Authorization: Bearer <access>
```
Esperado `200`. Cada ítem incluye ahora:
- `organo` (id del FK) y `organo_detalle` = `{ id, codigo, nombre }`.
- `organo_directivo` (id, puede ser `null`) y `organo_directivo_detalle`
  = `{ id, nombre, organo }` (o `null` si el cargo es global).

### Paso 3.2 — Crear un cargo global (sin `organo_directivo`) — CASO OK

Rol requerido: `Administrador RENADS`.
```http
POST http://localhost:8000/api/v1/executive-positions/
Authorization: Bearer <access>
Content-Type: application/json

{
  "organo": ORGANO_A,
  "nombre_masculino": "Director de Prueba QA",
  "nombre_femenino": "Directora de Prueba QA",
  "activo": true
}
```
Esperado `201`. Al no enviar `organo_directivo`, la coherencia no aplica y solo se
exige `organo`. Anota el `id` devuelto (`CARGO_GLOBAL_ID`).

### Paso 3.3 — Crear un cargo con `organo_directivo` coherente — CASO OK

`organo` debe coincidir con el `organo` del `organo_directivo` (`ORGDIR_A` → `ORGANO_A`).
```http
POST http://localhost:8000/api/v1/executive-positions/
Authorization: Bearer <access>
Content-Type: application/json

{
  "organo": ORGANO_A,
  "organo_directivo": ORGDIR_A,
  "nombre_masculino": "Director Coherente QA",
  "nombre_femenino": "Directora Coherente QA",
  "activo": true
}
```
Esperado `201`. Anota el `id` (`CARGO_COHERENTE_ID`).

### Paso 3.4 — Filtrar por `organo`

```http
GET http://localhost:8000/api/v1/executive-positions/?organo=ORGANO_A
Authorization: Bearer <access>
```
Esperado `200`: solo cargos con `organo = ORGANO_A` (incluye los creados arriba).

### Paso 3.5 — Filtrar cargos globales por `organo_directivo` nulo

```http
GET http://localhost:8000/api/v1/executive-positions/?organo_directivo__isnull=true
Authorization: Bearer <access>
```
Esperado `200`: incluye `CARGO_GLOBAL_ID` y **no** `CARGO_COHERENTE_ID`.

### Paso 3.6 — PATCH parcial que revalida contra el estado final — CASO OK

Cambiar solo `organo_directivo` en un cargo cuyo `organo` ya es coherente:
```http
PATCH http://localhost:8000/api/v1/executive-positions/CARGO_GLOBAL_ID/
Authorization: Bearer <access>
Content-Type: application/json

{
  "organo_directivo": ORGDIR_A
}
```
Esperado `200` **solo si** el `organo` actual del cargo (`ORGANO_A`) coincide con
`ORGDIR_A.organo` (`ORGANO_A`). Confirma que el serializer combina `attrs` + instancia.

## 4. Casos de regla de negocio que deben fallar

### RN-CE-02 — `organo` incoherente con `organo_directivo` (create) → 400

Usa un `organo` distinto del `organo` del órgano directivo:
```http
POST http://localhost:8000/api/v1/executive-positions/
Authorization: Bearer <access>
Content-Type: application/json

{
  "organo": ORGANO_B,
  "organo_directivo": ORGDIR_A,
  "nombre_masculino": "Cargo Incoherente QA"
}
```
Esperado `400` con:
```json
{ "organo": ["El órgano del cargo debe coincidir con el órgano del órgano directivo seleccionado."] }
```
(No debe devolver `500` ni `IntegrityError`.)

### RN-CE-02 — Incoherencia introducida por PATCH → 400

Sobre `CARGO_COHERENTE_ID` (organo `ORGANO_A`, directivo `ORGDIR_A`), cambiar solo el
`organo` a uno que ya no coincide:
```http
PATCH http://localhost:8000/api/v1/executive-positions/CARGO_COHERENTE_ID/
Authorization: Bearer <access>
Content-Type: application/json

{
  "organo": ORGANO_B
}
```
Esperado `400` con el mismo mensaje de coherencia (revalidación del estado final).

### RN-CE-01 — `organo` obligatorio omitido → 400

```http
POST http://localhost:8000/api/v1/executive-positions/
Authorization: Bearer <access>
Content-Type: application/json

{
  "nombre_masculino": "Cargo Sin Organo QA"
}
```
Esperado `400`: el campo `organo` es requerido (`null=False`).

### Unicidad `(organo_directivo, nombre_masculino)` → 400

Repetir `nombre_masculino` para el mismo `organo_directivo` (usa `CARGO_COHERENTE_ID`
como referencia del par existente):
```http
POST http://localhost:8000/api/v1/executive-positions/
Authorization: Bearer <access>
Content-Type: application/json

{
  "organo": ORGANO_A,
  "organo_directivo": ORGDIR_A,
  "nombre_masculino": "Director Coherente QA"
}
```
Esperado `400` por unicidad (el `unique_together` no cambió con este refactor).

### Escritura sin rol `Administrador RENADS` → 403

Repite cualquier `POST`/`PATCH`/`DELETE` con un token de usuario **sin** rol
`Administrador RENADS`. Esperado `403` (permiso `IsAdminRoleOrReadOnly`, no alterado).
La lectura (`GET`) sí debe funcionar para cualquier usuario autenticado.

## 5. Rol/permiso por endpoint

| Método | Endpoint | Rol requerido |
|--------|----------|---------------|
| `GET` (list/detail) | `/api/v1/executive-positions/` | Cualquier usuario autenticado |
| `POST`/`PUT`/`PATCH`/`DELETE` | `/api/v1/executive-positions/` | `Administrador RENADS` (o superusuario) |
