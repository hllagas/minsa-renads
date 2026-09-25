# Guía de pruebas manuales — Refactor `username = numero_documento` + apellidos a `auth_user`

**Spec:** `spec/common_username_dni_apellidos.md`
**Estado de validación:** APROBADA (sin errores altos/medios). Detalle en la sección "Resultado de validación" al final.
**Módulos afectados:** `apps/common` (usuarios/perfil), `apps/internados` (onboarding del interno).

Esta guía permite a un QA verificar manualmente, vía API, los cuatro cambios aprobados:
1. `username = numero_documento` (autogenerado/read-only) para todo usuario no-superusuario; superusuario con username libre.
2. Apellidos combinados en `auth_user.last_name`; nombre en `auth_user.first_name`; el perfil ya no tiene columnas de apellido.
3. Obligatoriedad total para no-super (`first_name`, `last_name` + 5 campos de perfil); superusuario exento.
4. Endpoints de administración de usuarios bajo `/api/v1/users/`.

---

## 1. Prerrequisitos

1. **Levantar el servidor** (lo ejecuta el usuario, nunca el validador):
   ```
   .venv\Scripts\Activate.ps1
   $env:DATABASE_URL="postgresql://renads:renads@localhost:5433/renads"
   python manage.py runserver --settings=config.settings.docker
   ```
2. **URL base:** `http://localhost:8000/api/v1/`
3. **Swagger interactivo (alternativa):** `http://localhost:8000/api/v1/docs/` — usar el botón *Authorize* con el `access_token` que devuelve el login (flujo OAuth2 password ya cableado).
4. **Obtener token JWT** (usuario superadministrador, para administrar usuarios):
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/token/ \
     -H "Content-Type: application/json" \
     -d '{"username":"hllagas","password":"<CONTRASEÑA_SUPERUSER>"}'
   ```
   Respuesta (extracto):
   ```json
   {
     "access": "<ACCESS_JWT>",
     "refresh": "<REFRESH_JWT>",
     "es_superusuario": true,
     "nombre": "Castro Flores",
     "grupos": [],
     "debe_cambiar_password": false
   }
   ```
   En las llamadas siguientes usar el header:
   ```
   Authorization: Bearer <ACCESS_JWT>
   ```

> **Rol/permiso requerido:** todos los endpoints `/api/v1/users/` (CRUD de usuarios) exigen **superadministrador** (`is_superuser=True`). Ningún otro rol puede crear/editar usuarios.

---

## 2. Datos previos necesarios

Para crear un usuario no-superusuario con perfil obligatorio se necesitan IDs reales de:

- **`unidad_organica`** — un `OrganicUnit` existente. Listar:
  ```bash
  curl -s "http://localhost:8000/api/v1/organic-units/?activo=true" \
    -H "Authorization: Bearer <ACCESS_JWT>"
  ```
  Anotar un `id` (→ `<UNIDAD_ID>`).
- **`cargo`** — un `ExecutivePosition` coherente con esa unidad. Listar filtrando por la unidad:
  ```bash
  curl -s "http://localhost:8000/api/v1/executive-positions/?unidad_organica=<UNIDAD_ID>" \
    -H "Authorization: Bearer <ACCESS_JWT>"
  ```
  Anotar un `id` (→ `<CARGO_ID>`).
- **(opcional) `groups`** — IDs de roles a asignar. Listar en `GET /api/v1/groups/`.

Estos catálogos ya están seedeados en la BD postgres de trabajo (`localhost:5433`).

---

## 3. Flujo paso a paso por escenario

### Paso 3.1 — Verificar el estado del usuario existente `universidad` (renombrado)

El refactor renombró el login del usuario `universidad` a su `numero_documento` (`17668077`) y movió sus apellidos a `last_name`. Confirmar vía login:

```bash
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"17668077","password":"<CONTRASEÑA>"}'
```

- **Esperado:** `200 OK` con token. `"nombre"` refleja `first_name`+`last_name` (`"Usuario de prueba Universidad"`).
- **Regresión:** intentar login con el username antiguo `universidad` → `401 Unauthorized` (ya no existe ese username).

Alternativa (con token superuser) — verificar el usuario por API:
```bash
curl -s "http://localhost:8000/api/v1/users/2/" \
  -H "Authorization: Bearer <ACCESS_JWT>"
```
- **Esperado:** `username == "17668077"`, `last_name` no vacío, y `perfil` **sin** claves `apellido_paterno`/`apellido_materno`, con `numero_documento == "17668077"`.

### Paso 3.2 — Crear un usuario NO superusuario (camino feliz)

`username` **NO** se envía: lo deriva el backend del `numero_documento`.

```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Authorization: Bearer <ACCESS_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jperez@example.com",
    "first_name": "Juan",
    "last_name": "Pérez Quispe",
    "is_active": true,
    "is_staff": false,
    "is_superuser": false,
    "groups": [],
    "tipo_documento": "DNI",
    "numero_documento": "45678912",
    "telefono": "987654321",
    "unidad_organica": <UNIDAD_ID>,
    "cargo": <CARGO_ID>,
    "tiene_ficha_usuario": false
  }'
```

- **Esperado:** `201 Created`. En la respuesta:
  - `"username": "45678912"` (== `numero_documento`, **autogenerado**).
  - `"first_name": "Juan"`, `"last_name": "Pérez Quispe"`.
  - `"perfil"` anidado con `numero_documento`, `telefono`, `tipo_documento`, `unidad_organica`, `cargo` — **sin** apellidos.
  - `"password_generada"`: contraseña temporal en texto claro (solo en esta respuesta de creación).
- Guardar el `id` devuelto (→ `<USER_ID>`) para los pasos siguientes.

### Paso 3.3 — Confirmar que `username` es read-only (se ignora si se envía)

Repetir el POST del paso 3.2 con otro `numero_documento`/`email` y agregando `"username": "loquesea"`:

```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Authorization: Bearer <ACCESS_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "IGNORAME",
    "email": "mlopez@example.com",
    "first_name": "María",
    "last_name": "López Ramos",
    "is_superuser": false,
    "tipo_documento": "DNI",
    "numero_documento": "45678913",
    "telefono": "987654322",
    "unidad_organica": <UNIDAD_ID>,
    "cargo": <CARGO_ID>
  }'
```

- **Esperado:** `201 Created` con `"username": "45678913"` (== `numero_documento`). El `"IGNORAME"` enviado se **descarta**.

### Paso 3.4 — Crear un superusuario (exento de perfil y con username libre)

El superusuario **sí** define su username y **no** requiere perfil ni apellidos:

```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Authorization: Bearer <ACCESS_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin2",
    "email": "admin2@example.com",
    "is_superuser": true,
    "is_staff": true
  }'
```

- **Esperado:** `201 Created`. `"username": "admin2"` (respetado, no derivado). Sin `perfil` (o `perfil: null`), sin `first_name`/`last_name` obligatorios.

### Paso 3.5 — Editar apellidos/nombre de un usuario (van a `auth_user`)

Los apellidos se editan en el nivel `User` (no en el perfil):

```bash
curl -X PATCH http://localhost:8000/api/v1/users/<USER_ID>/ \
  -H "Authorization: Bearer <ACCESS_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jperez@example.com",
    "first_name": "Juan Carlos",
    "last_name": "Pérez Quispe"
  }'
```

- **Esperado:** `200 OK` con `first_name`/`last_name` actualizados. `username` **no cambia** (read-only).

---

## 4. Casos que DEBEN fallar (reglas de negocio)

### 4.1 — No-super sin `first_name`/`last_name` → 400 (obligatoriedad total)

```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Authorization: Bearer <ACCESS_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "sinnombre@example.com",
    "is_superuser": false,
    "tipo_documento": "DNI",
    "numero_documento": "45678999",
    "telefono": "987650000",
    "unidad_organica": <UNIDAD_ID>,
    "cargo": <CARGO_ID>
  }'
```

- **Esperado:** `400 Bad Request`. Cuerpo con `first_name` y `last_name`:
  `"Este campo es obligatorio para usuarios que no son superadministrador."`

### 4.2 — No-super sin campos de perfil → 400

```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Authorization: Bearer <ACCESS_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "sinperfil@example.com",
    "first_name": "Ana",
    "last_name": "Torres Vega",
    "is_superuser": false
  }'
```

- **Esperado:** `400 Bad Request`. Cuerpo con `tipo_documento`, `numero_documento`, `telefono`, `unidad_organica`, `cargo`:
  `"Este campo es obligatorio para usuarios que no son superadministrador."`

### 4.3 — Superusuario sin `username` → 400

```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Authorization: Bearer <ACCESS_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin3@example.com","is_superuser":true}'
```

- **Esperado:** `400 Bad Request`, campo `username`:
  `"El nombre de usuario es obligatorio para el superadministrador."`

### 4.4 — Superusuario con `username` ya existente → 400

```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Authorization: Bearer <ACCESS_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"username":"hllagas","email":"otro@example.com","is_superuser":true}'
```

- **Esperado:** `400 Bad Request`, campo `username`:
  `"Ya existe un usuario con este nombre de usuario."`

### 4.5 — `numero_documento` duplicado (unicidad del perfil) → 400

Reenviar el POST del paso 3.2 con el mismo `numero_documento` (`45678912`) y otro `email`:

- **Esperado:** `400 Bad Request`, campo `numero_documento`:
  `"Ya existe un perfil con este número de documento."`

### 4.6 — `telefono` duplicado → 400

Análogo a 4.5 reusando un `telefono` ya registrado:

- **Esperado:** `400 Bad Request`, campo `telefono`:
  `"Ya existe un perfil con este número de teléfono."`

---

## 5. Onboarding del interno (impacto en `apps/internados`)

Al registrar un internado (rol `Universidad` / `Administrador RENADS`) se aprovisiona automáticamente el `User` del estudiante. Para verificar el efecto del refactor sobre este flujo:

1. Registrar un interno vía el flujo de `POST /api/v1/interns/` (ver `spec/internados.md` / su guía de pruebas para el payload completo). Rol requerido: `Universidad`.
2. Tras el registro, con token superuser, buscar el usuario del interno por su documento:
   ```bash
   curl -s "http://localhost:8000/api/v1/users/?search=<DNI_ESTUDIANTE>" \
     -H "Authorization: Bearer <ACCESS_JWT>"
   ```
   - **Esperado:**
     - `username == <DNI_ESTUDIANTE>`.
     - `first_name` = nombres del estudiante; `last_name` = `"<apellido_paterno> <apellido_materno>"` combinado.
     - `perfil` presente **sin** columnas de apellido; `unidad_organica`/`cargo` = placeholders "No aplica"; `telefono` real o sintético.
3. **Reingreso idempotente:** si el estudiante ya tenía usuario (internado previo liberado), no se resetea su contraseña ni se duplica el perfil.

Rol/permiso: el interno resultante (grupo `Interno`) solo puede leer sus datos y adjuntar sus DJ sobre su propio internado.

---

## 6. Verificación transversal (opcional)

- **`/auth/me/`** con el token de un no-super recién creado:
  ```bash
  curl -s http://localhost:8000/api/v1/auth/me/ -H "Authorization: Bearer <ACCESS_NOSUPER>"
  ```
  - `"nombre"` se deriva de `first_name`+`last_name` (`auth_user`), no del perfil.
  - `"perfil"` no expone `apellido_paterno`/`apellido_materno`.
- **Django admin** (`/admin/`, con superuser staff): abrir el changelist de "perfiles de usuario" → carga sin `FieldError` (search por `usuario__last_name`/`usuario__first_name`).

---

## Resultado de validación

Todos los criterios de la §5 del spec se verificaron OK:

1. `manage.py check --settings=config.settings.docker` → **0 issues**.
2. `makemigrations --check --dry-run` → **No changes detected** (modelo y migración sincronizados).
3. Postgres real (`localhost:5433`): `perfil_usuario` **sin** columnas `apellido_paterno`/`apellido_materno`; `hllagas` (superuser) `username` intacto y `last_name='Castro Flores'`; usuario id=2 `username='17668077' == numero_documento`, `last_name='Universidad'` poblado.
4. Modelo `UserProfile`: sin campos de apellido, `__str__` deriva de `auth_user.get_full_name()`/`get_username()`, docstring coherente.
5. Migración `0011`: `RunPython` (forwards+reverse noop) con `apps.get_model`, combina apellidos→`last_name`, renombra `username` solo de no-super (excluye `is_superuser`), guarda de colisión, `RemoveField` **después** del `RunPython`.
6. Serializers: sin apellidos en read/write/create/update ni en `_nombre_usuario`; `username` read-only; `validate()` condicional a `is_superuser` con mensajes en español; superuser exento.
7. Services (`crear_usuario_con_perfil`, `actualizar_perfil_usuario`): derivan username del documento para no-super, respetan superuser, no crean perfil vacío, 5 campos obligatorios.
8. Onboarding interno (`aprovisionar_interno`/`_crear_perfil_interno`): apellidos/nombre en `auth_user`, perfil sin apellidos, `username = numero_documento`.
9. Sin residuos: grep de `apellido_paterno`/`apellido_materno` en `apps/` solo aparece en migraciones históricas (0006/0009/0011) y en `Student` de internados (que los conserva legítimamente); ningún código vivo de `common` lee los campos eliminados del perfil.
10. Admin (`UserProfileAdmin`): `list_display`/`search_fields` sin columnas eliminadas.
11. Docs: `CLAUDE.md` (RN-username + perfil obligatorio), `docs/arquitectura_seguridad.md` (§4.6 y §4.6.1 sin filas de apellido, regla de username), `spec/common_perfil_usuario_obligatorio.md` (nota de actualización) — todos actualizados.
