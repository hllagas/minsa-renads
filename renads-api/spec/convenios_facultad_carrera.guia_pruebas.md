# Guía de pruebas manuales — `convenios_facultad_carrera`

Prueba manual del refactor de **carreras por facultad**: la FK `facultad` en `universidad_carrera`, el CRUD `university-careers` con validación de coherencia facultad↔universidad, y la acción en lote `POST /api/v1/faculties/{id}/careers`.

Un QA puede seguir esta guía sin leer el código. Todos los cuerpos son JSON de ejemplo con los campos reales del schema.

---

## 1. Prerrequisitos

1. **Levantar el servidor** (lo corre el usuario, no el QA por automatización):
   ```
   python manage.py runserver
   ```
2. **URL base:** `http://localhost:8000/api/v1/`
3. **Swagger interactivo (alternativa):** `http://localhost:8000/api/v1/docs/`
4. **Obtener token JWT** con un usuario que tenga el rol **`Administrador RENADS`** (o superusuario):
   ```
   POST http://localhost:8000/api/v1/auth/token/
   Content-Type: application/json

   {
     "username": "admin",
     "password": "TU_PASSWORD"
   }
   ```
   Respuesta esperada `200`:
   ```
   { "access": "<access_jwt>", "refresh": "<refresh_jwt>" }
   ```
5. **Cabecera de autenticación** en todas las llamadas siguientes:
   ```
   Authorization: Bearer <access_jwt>
   ```

---

## 2. Datos previos necesarios

Deben existir (crearlos vía API con el mismo token de `Administrador RENADS` si no están seedeados):

- **Una universidad** (`GET /api/v1/universities/` para tomar un `id`; suele estar seedeada).
- **Al menos una facultad** de esa universidad (`facultad.universidad` = universidad elegida):
  ```
  POST http://localhost:8000/api/v1/faculties/
  Authorization: Bearer <access_jwt>
  Content-Type: application/json

  {
    "universidad": 1,
    "nombre": "Facultad de Medicina Humana",
    "activo": true
  }
  ```
  Respuesta `201` → guardar `id` como **FACULTAD_A**.
- **Una segunda facultad de la MISMA universidad** (para el caso de alcance por facultad):
  ```
  POST http://localhost:8000/api/v1/faculties/
  { "universidad": 1, "nombre": "Facultad de Enfermería", "activo": true }
  ```
  Respuesta `201` → guardar `id` como **FACULTAD_B**.
- **Una facultad de OTRA universidad** (para el caso de coherencia que debe fallar):
  ```
  POST http://localhost:8000/api/v1/faculties/
  { "universidad": 2, "nombre": "Facultad de Odontología", "activo": true }
  ```
  Respuesta `201` → guardar `id` como **FACULTAD_OTRA_UNIV**.
- **Carreras profesionales** (`GET /api/v1/professional-careers/` para tomar ids; suelen estar seedeadas). Elegir tres ids: **CARRERA_A**, **CARRERA_B**, **CARRERA_C**.

> Rol requerido para crear facultades/carreras y para toda escritura de este módulo: **`Administrador RENADS`** (o superusuario). La lectura (`GET`) solo requiere estar autenticado.

---

## 3. Flujo paso a paso — CRUD `university-careers`

### Paso 3.1 — Crear una carrera por universidad (con facultad válida)

```
POST http://localhost:8000/api/v1/university-careers/
Authorization: Bearer <access_jwt>
Content-Type: application/json

{
  "universidad": 1,
  "carrera_profesional": <CARRERA_A>,
  "facultad": <FACULTAD_A>,
  "activo": true
}
```
Esperado `201`. La respuesta incluye los detalles de solo lectura:
```
{
  "id": 10,
  "universidad": 1,
  "carrera_profesional": <CARRERA_A>,
  "facultad": <FACULTAD_A>,
  "activo": true,
  "universidad_detalle": { "id": 1, "nombre": "..." },
  "carrera_profesional_detalle": { "id": <CARRERA_A>, "nombre": "..." },
  "facultad_detalle": { "id": <FACULTAD_A>, "nombre": "Facultad de Medicina Humana" }
}
```
Guardar `id` como **UC_ID**.

### Paso 3.2 — Leer y filtrar por facultad

```
GET http://localhost:8000/api/v1/university-careers/?facultad=<FACULTAD_A>
Authorization: Bearer <access_jwt>
```
Esperado `200`; la lista incluye la fila de 3.1 con sus `*_detalle`. Verificar también los filtros previos:
```
GET .../university-careers/?universidad=1
GET .../university-careers/?carrera_profesional=<CARRERA_A>
GET .../university-careers/?activo=true
```
Todos deben responder `200` y filtrar correctamente.

### Paso 3.3 — Actualizar (PATCH) la carrera

```
PATCH http://localhost:8000/api/v1/university-careers/<UC_ID>/
Authorization: Bearer <access_jwt>
Content-Type: application/json

{ "activo": true }
```
Esperado `200` (no falla por no reenviar `facultad`, porque en PATCH parcial la validación toma el valor de la instancia).

---

## 4. Flujo paso a paso — acción en lote `POST /faculties/{id}/careers`

### Paso 4.1 — Sincronizar carreras de FACULTAD_A: `[A, B]`

```
POST http://localhost:8000/api/v1/faculties/<FACULTAD_A>/careers
Authorization: Bearer <access_jwt>
Content-Type: application/json

{ "carreras": [<CARRERA_A>, <CARRERA_B>] }
```
Esperado `200`:
```
{
  "carreras": [
    { "id": ..., "carrera_profesional": <CARRERA_A>, "facultad": <FACULTAD_A>, "activo": true, ... },
    { "id": ..., "carrera_profesional": <CARRERA_B>, "facultad": <FACULTAD_A>, "activo": true, ... }
  ]
}
```
Nota: la `universidad` de las filas resultantes es la de FACULTAD_A (se deriva de la facultad; **no** se envía en el body).

### Paso 4.2 — Re-sincronizar FACULTAD_A: `[B, C]` (alta de C, baja de A)

```
POST http://localhost:8000/api/v1/faculties/<FACULTAD_A>/careers
{ "carreras": [<CARRERA_B>, <CARRERA_C>] }
```
Esperado `200`. La respuesta lista **solo las activas**: `{B, C}`. La carrera `A` queda `activo=false` (no se borra). Verificar:
```
GET .../university-careers/?facultad=<FACULTAD_A>&activo=false
```
→ debe aparecer la fila de `A` con `activo=false`.

### Paso 4.3 — Idempotencia: repetir `[B, C]`

```
POST http://localhost:8000/api/v1/faculties/<FACULTAD_A>/careers
{ "carreras": [<CARRERA_B>, <CARRERA_C>] }
```
Esperado `200` con las mismas `{B, C}` activas; no cambia el estado ni genera auditoría redundante.

### Paso 4.4 — Alcance por facultad: FACULTAD_B con `[A]`

```
POST http://localhost:8000/api/v1/faculties/<FACULTAD_B>/careers
{ "carreras": [<CARRERA_A>] }
```
Esperado `200`. Registra `A` bajo FACULTAD_B. Como RN-FC-01 exige unicidad por universidad, la fila `(universidad, A)` existente (dada de baja en FACULTAD_A en el paso 4.2) se **reactiva y reasigna** a FACULTAD_B; no se crea duplicado. Verificar:
```
GET .../university-careers/?universidad=1&carrera_profesional=<CARRERA_A>
```
→ una sola fila, con `facultad = FACULTAD_B` y `activo=true`.

### Paso 4.5 — Baja total: FACULTAD_B con `[]`

```
POST http://localhost:8000/api/v1/faculties/<FACULTAD_B>/careers
{ "carreras": [] }
```
Esperado `200` con `{"carreras": []}`. Todas las carreras activas de FACULTAD_B quedan `activo=false` (sin borrado físico).

---

## 5. Casos que DEBEN fallar (reglas de negocio)

### 5.1 — RN-FC-03: `facultad` requerida en escritura del CRUD unitario

```
POST http://localhost:8000/api/v1/university-careers/
Authorization: Bearer <access_jwt>
Content-Type: application/json

{ "universidad": 1, "carrera_profesional": <CARRERA_A>, "activo": true }
```
Esperado `400`. Mensaje del campo `facultad` indicando que es requerido (`"Este campo es requerido."`).

### 5.2 — RN-FC-02: facultad de otra universidad (CRUD unitario)

```
POST http://localhost:8000/api/v1/university-careers/
{ "universidad": 1, "carrera_profesional": <CARRERA_B>, "facultad": <FACULTAD_OTRA_UNIV>, "activo": true }
```
Esperado `400` con mensaje en español:
```
"La facultad seleccionada no pertenece a la universidad indicada."
```
Repetir en PATCH sobre una fila existente asignando `facultad = FACULTAD_OTRA_UNIV` → mismo `400`.

### 5.3 — Acción en lote con carrera inexistente

```
POST http://localhost:8000/api/v1/faculties/<FACULTAD_A>/careers
{ "carreras": [999999] }
```
Esperado `400` (validación del `PrimaryKeyRelatedField`: `"Pk inválida \"999999\" - objeto no existe."`).

### 5.4 — Permiso: usuario sin rol `Administrador RENADS`

Con un token de un usuario **sin** el rol `Administrador RENADS` (p. ej. rol `Universidad`):
```
POST http://localhost:8000/api/v1/faculties/<FACULTAD_A>/careers
{ "carreras": [<CARRERA_A>] }
```
Esperado `403`.

Igualmente, escritura del CRUD unitario con ese mismo token:
```
POST http://localhost:8000/api/v1/university-careers/
{ "universidad": 1, "carrera_profesional": <CARRERA_A>, "facultad": <FACULTAD_A> }
```
Esperado `403`. (La lectura `GET` con ese token sí debe responder `200`.)

---

## 6. Rol/permiso por endpoint

| Endpoint | Método | Rol requerido |
|---|---|---|
| `/api/v1/university-careers/` | `GET` (list/retrieve) | Cualquier usuario autenticado |
| `/api/v1/university-careers/` | `POST`/`PUT`/`PATCH`/`DELETE` | `Administrador RENADS` (o superusuario) |
| `/api/v1/faculties/` | `GET` | Cualquier usuario autenticado |
| `/api/v1/faculties/` | `POST`/`PUT`/`PATCH`/`DELETE` | `Administrador RENADS` (o superusuario) |
| `/api/v1/faculties/{id}/careers` | `POST` | `Administrador RENADS` (o superusuario) |

Toda escritura queda registrada en `bitacora_auditoria` (usuario, acción, entidad); en la acción en lote se audita cada alta/reactivación/baja real.
