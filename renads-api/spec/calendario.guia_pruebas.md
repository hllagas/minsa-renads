# Guía de pruebas manuales — Feature "Calendario de actividades administrativas"

> Requiere que la validación esté **aprobada** (ver `spec/calendario.validacion.md`).
> Objetivo: que QA verifique, sin leer código, el CRUD de `calendar-activities`, el endpoint `content-types`, el gate temporal `IsModuleEnabled` sobre los 3 módulos instrumentados y los campos `modulos_habilitados`/`modulos_bloqueados` de `/auth/me/`.

---

## 0. Prerrequisitos

1. **Levantar el servidor** (lo corre el usuario, no el agente):
   ```
   .venv\Scripts\Activate.ps1
   python manage.py runserver
   ```
2. **URL base:** `http://localhost:8000/api/v1/`
3. **Swagger interactivo (alternativa):** `http://localhost:8000/api/v1/docs/`
4. **Obtener token JWT** (repetir por cada usuario que se pruebe):
   ```
   POST http://localhost:8000/api/v1/auth/token/
   Content-Type: application/json

   { "username": "<usuario>", "password": "<contraseña>" }
   ```
   Respuesta `200`:
   ```json
   { "access": "<jwt>", "refresh": "<jwt>", "es_superusuario": true, "nombre": "...", "grupos": ["Administrador RENADS"], "debe_cambiar_password": false }
   ```
   En las siguientes llamadas añade la cabecera:
   ```
   Authorization: Bearer <access>
   ```

### Usuarios necesarios (roles)

| Alias | Rol / condición | Se usa para |
|---|---|---|
| **ADMIN** | Superusuario **o** grupo `Administrador RENADS` | Crear/editar `calendar-activities`; verificar exención del gate. |
| **NORMAL** | Usuario con perfil institucional que **no** sea admin (p. ej. rol `Universidad` con perfil sobre una universidad; para convenios, un rol que pueda crear convenios en su ámbito) | Verificar que el gate temporal lo **bloquea** fuera de ventana. |

> Si no existe un ADMIN, créalo con `python manage.py createsuperuser`. El rol `Administrador RENADS` es un `auth.Group`; asígnalo desde `/api/v1/groups/` (solo superusuario) o el admin de Django.

### Datos previos

- No hace falta seed específico del calendario: se crean las actividades en la propia prueba.
- Para el paso 5 (bloqueo real de un módulo) necesitas un endpoint funcional donde el NORMAL pueda **crear** algo dentro de su ámbito. Se ilustra con **convenios** (`POST /api/v1/conventions/`), pero el comportamiento del gate es idéntico para internados y actividades.

---

## 1. `content-types` (poblar el selector del frontend) — rol: cualquier autenticado

```
GET http://localhost:8000/api/v1/content-types/
Authorization: Bearer <ADMIN o NORMAL>
```
Esperado `200`: lista de `{ id, app_label, model, verbose_name }`. **Anota el `id`** de:
- `convenios` / `convention`  → lo llamaremos `CT_CONVENTION`
- `internados` / `internship` → `CT_INTERNSHIP`
- `actividades` / `teachingactivity` → `CT_TEACHINGACTIVITY`

Estos ids alimentan el campo `content_types[]` del CRUD (paso 2) y aparecen en `/auth/me/` (paso 4).

---

## 2. CRUD `calendar-activities` — rol: `Administrador RENADS`/superusuario para escritura

### 2.1 Crear una actividad meramente informativa (no controla acceso)
```
POST http://localhost:8000/api/v1/calendar-activities/
Authorization: Bearer <ADMIN>
Content-Type: application/json

{
  "nombre": "Difusión del proceso de internado 2026",
  "detalle": "Charlas informativas a universidades.",
  "numero_orden": 1,
  "fecha_inicio": "2026-02-01",
  "fecha_fin": "2026-02-15",
  "controla_acceso": false,
  "activo": true,
  "responsables": [],
  "content_types": []
}
```
Esperado `201` con el `id` creado. **Anota `id`** (= `ACT_INFO`).

### 2.2 Leer y verificar el shape de lectura
```
GET http://localhost:8000/api/v1/calendar-activities/{ACT_INFO}/
Authorization: Bearer <ADMIN>
```
Esperado `200`: incluye `responsables_detalle` (lista `{id, name}`) y `content_types_detalle` (lista `{id, app_label, model, verbose_name}`), además de `creado_por`/`actualizado_por` seteados con el ADMIN.

### 2.3 Listado ordenado por `numero_orden`
```
GET http://localhost:8000/api/v1/calendar-activities/?ordering=numero_orden
Authorization: Bearer <NORMAL>
```
Esperado `200` (lectura permitida a cualquier autenticado), resultados ascendentes por `numero_orden`.

### 2.4 Filtros
```
GET http://localhost:8000/api/v1/calendar-activities/?controla_acceso=true
GET http://localhost:8000/api/v1/calendar-activities/?activo=false
GET http://localhost:8000/api/v1/calendar-activities/?content_types={CT_CONVENTION}
GET http://localhost:8000/api/v1/calendar-activities/?fecha_desde=2026-01-01&fecha_hasta=2026-12-31
```
Esperado `200`; cada filtro acota el resultado y son combinables.

---

## 3. Casos que **deben fallar** (reglas y permisos)

### 3.1 RN — `fecha_fin` anterior a `fecha_inicio` (Serializer)
```
POST http://localhost:8000/api/v1/calendar-activities/
Authorization: Bearer <ADMIN>
Content-Type: application/json

{ "nombre": "Ventana inválida", "fecha_inicio": "2026-05-10", "fecha_fin": "2026-05-01", "controla_acceso": false }
```
Esperado `400`:
```json
{ "fecha_fin": ["La fecha de fin no puede ser anterior a la fecha de inicio."] }
```
> `fecha_fin` nula (omitida) **sí** es válida (ventana abierta).

### 3.2 Permiso — usuario no admin no puede escribir
```
POST http://localhost:8000/api/v1/calendar-activities/
Authorization: Bearer <NORMAL>
Content-Type: application/json

{ "nombre": "Intento no autorizado", "fecha_inicio": "2026-03-01" }
```
Esperado `403` (solo `Administrador RENADS`/superusuario escriben; `IsAdminRoleOrReadOnly`).

---

## 4. `/auth/me/` — `modulos_habilitados` / `modulos_bloqueados`

### 4.1 Estado inicial (sin actividades controladoras)
```
GET http://localhost:8000/api/v1/auth/me/
Authorization: Bearer <NORMAL>
```
Esperado `200`: `modulos_habilitados: []` y `modulos_bloqueados: []` (mientras no exista ninguna `CalendarActivity` con `controla_acceso=true`, `activo=true`).

*(Los siguientes sub-pasos dependen de crear la actividad controladora del paso 5; vuelve aquí tras el 5.)*

### 4.2 Con un módulo controlado fuera de ventana
Tras crear la actividad controladora del paso 5 (ventana ya cerrada sobre `convenios/convention`):
```
GET http://localhost:8000/api/v1/auth/me/
Authorization: Bearer <NORMAL>
```
Esperado: `modulos_bloqueados` contiene `{ "app_label": "convenios", "model": "convention", "content_type_id": CT_CONVENTION }` y `modulos_habilitados` **no** lo contiene.
> Nota: para ADMIN/superusuario el mismo módulo también aparece en `modulos_bloqueados` (los campos reflejan el estado temporal del módulo, no la exención del admin); aun así el ADMIN **sí** puede escribir.

---

## 5. Gate temporal `IsModuleEnabled` sobre un módulo instrumentado (convenios)

> Los 3 módulos instrumentados son: `conventions` (`convenios.convention`), `internships` (`internados.internship`) y `teaching-activities` (`actividades.teachingactivity`). Se ilustra con **convenios**; el comportamiento es idéntico en los otros dos.

### 5.1 Crear actividad controladora con ventana **cerrada** (fuera de hoy)
```
POST http://localhost:8000/api/v1/calendar-activities/
Authorization: Bearer <ADMIN>
Content-Type: application/json

{
  "nombre": "Ventana de registro de convenios (cerrada)",
  "fecha_inicio": "2026-01-01",
  "fecha_fin": "2026-01-31",
  "controla_acceso": true,
  "activo": true,
  "content_types": [ CT_CONVENTION ]
}
```
Esperado `201`. **Anota `id`** (= `ACT_GATE`).

### 5.2 Lectura sigue libre (no la bloquea el gate)
```
GET http://localhost:8000/api/v1/conventions/
Authorization: Bearer <NORMAL>
```
Esperado `200`.

### 5.3 Escritura de usuario normal fuera de ventana ⇒ bloqueada
```
POST http://localhost:8000/api/v1/conventions/
Authorization: Bearer <NORMAL>
Content-Type: application/json

{ ...payload válido de convenio dentro del ámbito del NORMAL... }
```
Esperado `403` con mensaje:
```json
{ "detail": "El módulo está fuera de su ventana de registro." }
```
(internamente `code = "MODULO_FUERA_DE_VENTANA"`).

### 5.4 ADMIN/superusuario exento (escribe aunque esté fuera de ventana)
```
POST http://localhost:8000/api/v1/conventions/
Authorization: Bearer <ADMIN>
Content-Type: application/json

{ ...payload válido... }
```
Esperado: **no** devuelve `403 MODULO_FUERA_DE_VENTANA` (el resultado depende de las demás validaciones de convenios, no del gate).

### 5.5 Abrir la ventana ⇒ el normal puede escribir
Edita la actividad para que la ventana incluya hoy (o hazla abierta con `fecha_fin: null`):
```
PATCH http://localhost:8000/api/v1/calendar-activities/{ACT_GATE}/
Authorization: Bearer <ADMIN>
Content-Type: application/json

{ "fecha_inicio": "2026-01-01", "fecha_fin": null }
```
Luego repite 5.3 con el NORMAL: ya **no** debe devolver `403 MODULO_FUERA_DE_VENTANA`.

### 5.6 OR entre ventanas (opcional)
Crea una **segunda** actividad controladora sobre `CT_CONVENTION` con ventana vigente hoy, dejando la primera cerrada: basta una vigente para habilitar. Verifica con 5.3 que el NORMAL ya puede escribir y con 4.2 que `convention` pasa a `modulos_habilitados`.

### 5.7 Desactivar el control ⇒ vuelve a pass-through
Pon `controla_acceso: false` (o `activo: false`) en todas las actividades sobre `CT_CONVENTION`:
```
PATCH http://localhost:8000/api/v1/calendar-activities/{ACT_GATE}/
Authorization: Bearer <ADMIN>
Content-Type: application/json

{ "controla_acceso": false }
```
Repite 5.3: el NORMAL escribe sin restricción temporal y `/auth/me/` (4.1) vuelve a `modulos_bloqueados: []`.

---

## 6. Verificación de que NO se gatearon otros endpoints

Con la actividad controladora del paso 5 activa y **cerrada**, confirma que endpoints **no instrumentados** siguen funcionando para el NORMAL (no devuelven `MODULO_FUERA_DE_VENTANA`):
```
GET  http://localhost:8000/api/v1/content-types/
GET  http://localhost:8000/api/v1/calendar-activities/
```
Esperado `200` en ambos (el propio calendario y los catálogos/auth nunca se gatean).

---

## 7. Rol/permiso requerido por endpoint (resumen)

| Endpoint | Método | Rol requerido |
|---|---|---|
| `/auth/token/`, `/auth/me/` | POST / GET | Autenticado |
| `/content-types/` | GET | Autenticado |
| `/calendar-activities/` | GET | Autenticado |
| `/calendar-activities/` | POST/PATCH/PUT/DELETE | `Administrador RENADS` o superusuario |
| `/conventions/`, `/internships/`, `/teaching-activities/` | GET | Según permisos existentes del módulo (sin cambio) |
| `/conventions/`, `/internships/`, `/teaching-activities/` | POST/PATCH/PUT/DELETE | Permisos existentes del módulo **+** módulo dentro de ventana (salvo admin/superuser) |
