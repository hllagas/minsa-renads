# Guía de pruebas manuales — Campos clínicos: Registro (CONAPRES) y Asignación (Órgano Regional)

Valida los endpoints nuevos del refactor de campos clínicos:
- `clinical-field-registrations` — registro del total por sede + carrera (rol **CONAPRES**).
- `clinical-field-allocations` — asignación de cupos por universidad (rol **Gobierno Regional**).

> Estado de la validación: **APROBADA** (sin errores altos/medios). Resultado en `spec/convenios_campos_clinicos.validacion.md`.

---

## 1. Prerrequisitos

1. Levantar el servidor (lo corre el usuario):
   ```
   python manage.py runserver
   ```
2. URL base: `http://localhost:8000/api/v1/`
3. Alternativa interactiva: Swagger en `http://localhost:8000/api/v1/docs/`.
4. Obtener token JWT:
   ```
   POST http://localhost:8000/api/v1/auth/token/
   Content-Type: application/json

   { "username": "<usuario>", "password": "<contraseña>" }
   ```
   Respuesta: `{ "access": "...", "refresh": "..." }`. En las siguientes llamadas usar el header:
   ```
   Authorization: Bearer <access>
   ```

### Roles por endpoint

| Endpoint | Lectura (GET) | Escritura (POST/PUT/PATCH/DELETE) |
|----------|---------------|-----------------------------------|
| `clinical-field-registrations` | Cualquier autenticado | Superusuario o grupo **CONAPRES** |
| `clinical-field-allocations`   | Cualquier autenticado | Superusuario o grupo **Gobierno Regional** |

> Un usuario sin el rol de escritura recibe `403` con mensaje: "La escritura requiere el rol CONAPRES." / "La escritura requiere el rol Gobierno Regional.".

---

## 2. Datos previos necesarios

Deben existir (ya seedeados o creados vía sus CRUD):

1. Una **IPRESS** con `es_sede_docente = true`. Si no lo está, autorizarla como CONAPRES:
   ```
   POST /api/v1/ipress/{id_ipress}/autorizar-sede-docente/
   Authorization: Bearer <access CONAPRES>
   Content-Type: application/json

   { "autorizar": true }
   ```
2. Un **Convenio Específico VIGENTE** (`tipo_convenio = ESPECIFICO`, estado en `VIGENTE`/`PUBLICADO`/`SUSCRITO`) con su **universidad** asociada. Anotar `id_convenio`, `id_universidad`.
3. Una **carrera profesional** (`id_carrera`) y, opcionalmente, una **especialidad** (`id_especialidad`).
4. Dos usuarios de prueba: uno del grupo `CONAPRES` y otro del grupo `Gobierno Regional`.

---

## 3. Flujo paso a paso

### Paso 1 — CONAPRES registra el total de campos clínicos por sede + carrera

```
POST /api/v1/clinical-field-registrations/
Authorization: Bearer <access CONAPRES>
Content-Type: application/json

{
  "convenio": 4,
  "ipress": 12,
  "carrera_profesional": 3,
  "especialidad": null,
  "campos_clinicos_registrados": 10
}
```

Respuesta esperada: `201 Created`.
```
{
  "id": 20,
  "convenio": 4,
  "ipress": 12,
  "carrera_profesional": 3,
  "especialidad": null,
  "campos_clinicos_registrados": 10,
  "campos_clinicos_asignados": 0,
  "disponibilidad": 10,
  "creado_en": "...", "creado_por": <id>, "actualizado_en": "...", "actualizado_por": null
}
```
Anotar `id` del registro (aquí `20`) → se usa como `campo_clinico_ipress` en las asignaciones.

> `campos_clinicos_asignados` es de solo lectura (acumulador); enviarlo en el body no lo altera. `disponibilidad = registrados − asignados`.

### Paso 2 — Consultar el registro creado

```
GET /api/v1/clinical-field-registrations/20/
Authorization: Bearer <access cualquiera>
```
Esperado: `200 OK` con `disponibilidad: 10`.

Filtros disponibles (todos `exact`): `convenio`, `ipress`, `carrera_profesional`, `especialidad`. Ej.:
```
GET /api/v1/clinical-field-registrations/?convenio=4&ipress=12
```

### Paso 3 — Gobierno Regional asigna una primera cuota (6) a la universidad

```
POST /api/v1/clinical-field-allocations/
Authorization: Bearer <access Gobierno Regional>
Content-Type: application/json

{
  "campo_clinico_ipress": 20,
  "convenio": 4,
  "ipress": 12,
  "carrera_profesional": 3,
  "especialidad": null,
  "universidad": 7,
  "fecha_inicio": "2026-01-01",
  "fecha_fin": "2026-12-31",
  "campos_clinicos_autorizados": 6
}
```
Esperado: `201 Created`. Tras esto, el registro padre queda con `campos_clinicos_asignados = 6`, `disponibilidad = 4` (verificar con `GET /clinical-field-registrations/20/`).

### Paso 4 — Segunda asignación (4) — completa el total

Repetir el POST del Paso 3 con `campos_clinicos_autorizados: 4` (misma sede/carrera; distinta universidad o distinto convenio para respetar el `unique_together (campo_clinico_ipress, universidad, convenio)`).
Esperado: `201 Created`. El registro queda `campos_clinicos_asignados = 10`, `disponibilidad = 0`.

### Paso 5 — Consultar / filtrar asignaciones

```
GET /api/v1/clinical-field-allocations/?campo_clinico_ipress=20
Authorization: Bearer <access cualquiera>
```
Filtros disponibles (`exact`): `campo_clinico_ipress`, `convenio`, `ipress`, `carrera_profesional`, `universidad`.

### Paso 6 — Actualizar una asignación

```
PATCH /api/v1/clinical-field-allocations/{id_asignacion}/
Authorization: Bearer <access Gobierno Regional>
Content-Type: application/json

{ "campos_clinicos_autorizados": 5 }
```
Esperado: `200 OK` si respeta la disponibilidad (excluyendo la propia); el acumulador del registro se recalcula.

### Paso 7 — Eliminar una asignación

```
DELETE /api/v1/clinical-field-allocations/{id_asignacion}/
Authorization: Bearer <access Gobierno Regional>
```
Esperado: `204 No Content`. El `campos_clinicos_asignados` del registro se recalcula (baja). Si la asignación tiene internados asociados, ver Caso RN-6.

---

## 4. Casos de regla de negocio (deben fallar)

### RN-1 — Sede docente no autorizada (registro)
Crear un registro con una `ipress` que tenga `es_sede_docente = false`:
```
POST /api/v1/clinical-field-registrations/
{ "convenio": 4, "ipress": <ipress no autorizada>, "carrera_profesional": 3, "campos_clinicos_registrados": 5 }
```
Esperado: `400` → `{"ipress": "La IPRESS debe estar autorizada como sede docente por CONAPRES."}`

### RN-2 — No bajar el total por debajo de lo ya asignado (registro)
Con el registro `20` teniendo `campos_clinicos_asignados = 10`:
```
PATCH /api/v1/clinical-field-registrations/20/
{ "campos_clinicos_registrados": 8 }
```
Esperado: `400` → `{"campos_clinicos_registrados": "No puede ser menor que los campos ya asignados a universidades."}`

### RN-3 — Exceder la disponibilidad (asignación)
Con el registro `20` en `disponibilidad = 0`, intentar una asignación adicional de 1:
```
POST /api/v1/clinical-field-allocations/
{ "campo_clinico_ipress": 20, "convenio": 4, "ipress": 12, "carrera_profesional": 3, "universidad": 9, "fecha_inicio": "2026-01-01", "fecha_fin": "2026-12-31", "campos_clinicos_autorizados": 1 }
```
Esperado: `400` → `{"campos_clinicos_autorizados": "Excede los campos clínicos disponibles del registro."}`

### RN-4 — Convenio no específico / no vigente (asignación)
Usar un `convenio` que no sea Específico o cuyo estado no esté vigente:
Esperado: `400` → `{"convenio": "... solo aplica a Convenios Específicos."}` o `{"convenio": "El Convenio Específico debe estar vigente."}`

### RN-5 — Universidad distinta a la del convenio (asignación)
Enviar `universidad` distinta a `convenio.universidad`:
Esperado: `400` → `{"universidad": "La universidad debe coincidir con la del convenio."}`

### RN-6 — Coherencia con el registro padre (asignación)
Enviar `ipress`, `carrera_profesional` o `especialidad` distintos a los del registro `campo_clinico_ipress`:
Esperado: `400` con la clave correspondiente, p. ej. `{"ipress": "Debe coincidir con la IPRESS del registro de campos clínicos."}`

### RN-7 — Fechas invertidas (serializer)
```
POST /api/v1/clinical-field-allocations/  ... "fecha_inicio": "2026-12-31", "fecha_fin": "2026-01-01"
```
Esperado: `400` → `{"fecha_fin": "La fecha de fin no puede ser anterior a la de inicio."}`

### RN-8 — Eliminar asignación con internados asociados
Si un internado referencia la asignación (`Internship.campo_clinico`), el `PROTECT` la protege:
```
DELETE /api/v1/clinical-field-allocations/{id_con_internos}/
```
Esperado: `409 Conflict` con mensaje "No se puede eliminar: el registro está referenciado por ...".

### RN-9 — RN-13 en Internados (cupo agotado)
Al registrar internados contra una asignación hasta alcanzar `campos_clinicos_autorizados`, el siguiente registro:
```
POST /api/v1/interns/  ... "campo_clinico": <id_asignacion agotada>
```
Esperado: `400` → `{"campo_clinico": "Se alcanzó el máximo de campos clínicos autorizados."}`

### RN-10 — Escritura sin rol
`POST`/`PATCH`/`DELETE` a `clinical-field-registrations` sin grupo `CONAPRES`, o a `clinical-field-allocations` sin grupo `Gobierno Regional`:
Esperado: `403` con el mensaje del permiso. La lectura (`GET`) sí responde `200` para cualquier autenticado.
