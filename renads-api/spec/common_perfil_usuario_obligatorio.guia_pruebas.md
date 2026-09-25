# Guía de pruebas manuales — Endurecimiento de `perfil_usuario` obligatorio

**Módulo:** `apps/common` (+ RN-22 en `apps/internados`)
**Spec:** `spec/common_perfil_usuario_obligatorio.md`
**Estado de validación:** exitosa (12/12 criterios §7). Ver detalle al pie.

Esta guía verifica manualmente que el perfil de usuario (`perfil_usuario`) quedó
obligatorio: los 7 campos de identidad/institucionales son `NOT NULL`, el flag
`tiene_ficha_usuario` se expone y persiste, la unicidad de documento/teléfono se
respeta, el PATCH parcial no se rompe y el onboarding del interno (RN-22) crea su
`UserProfile` sin violar las constraints.

---

## 1. Prerrequisitos

1. **Levantar el servidor** (lo ejecuta el usuario, nunca el validador/agente):

   ```powershell
   .venv\Scripts\Activate.ps1
   $env:DATABASE_URL = "postgresql://renads:renads@localhost:5433/renads"
   python manage.py runserver --settings=config.settings.docker
   ```

2. **URL base:** `http://localhost:8000/api/v1/`
3. **Swagger (alternativa interactiva):** `http://localhost:8000/api/v1/docs/` — permite
   ejecutar todas las llamadas con el token ya configurado tras el login.
4. **Obtener token JWT** (usuario administrador / superusuario):

   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/token/ \
     -H "Content-Type: application/json" \
     -d '{"username": "<admin>", "password": "<clave>"}'
   ```

   Respuesta (200): `{ "access": "...", "refresh": "...", "access_token": "..." }`.
   Usar en todas las llamadas siguientes:

   ```
   Authorization: Bearer <access>
   ```

**Rol/permiso requerido:** la gestión de usuarios (`/users/`) es solo para
**superusuario / Administrador RENADS**. El endpoint `/auth/me/` lo puede usar
cualquier usuario autenticado.

---

## 2. Datos previos necesarios

El perfil obligatorio referencia dos catálogos que **deben existir** (ya seedeados en
postgres docker: 14 `unidad_organica` y 12 `cargo_ejecutivo`):

- **Unidad orgánica** (`unidad_organica`) — obtener un `id` válido:

  ```bash
  curl http://localhost:8000/api/v1/organic-units/ -H "Authorization: Bearer <access>"
  ```

- **Cargo ejecutivo** (`cargo_ejecutivo`) — obtener un `id` válido:

  ```bash
  curl http://localhost:8000/api/v1/executive-positions/ -H "Authorization: Bearer <access>"
  ```

Anotar un `unidad_organica_id` y un `cargo_id` reales para los pasos de creación.
Usar un `numero_documento` y un `telefono` **que no existan** aún (ambos son únicos;
los dos usuarios seed usan `12049474`/`974989260` y `17668077`/`937328418`).

---

## 3. Flujo paso a paso

### Paso 3.1 — Lectura del perfil propio (`GET /auth/me/`)

Verifica que el perfil anidado expone `tiene_ficha_usuario` y los apellidos.

```bash
curl http://localhost:8000/api/v1/auth/me/ -H "Authorization: Bearer <access>"
```

**Esperado (200):** el objeto incluye `perfil` con, al menos:

```json
{
  "perfil": {
    "tipo_documento": "DNI",
    "numero_documento": "...",
    "apellido_paterno": "...",
    "apellido_materno": "...",
    "telefono": "...",
    "unidad_organica": 14,
    "cargo": 2,
    "tiene_ficha_usuario": false,
    "unidad_organica_detalle": "...",
    "cargo_detalle": "..."
  }
}
```

> Nota: si el usuario autenticado no tuviera perfil, `perfil` sería `null` sin romper la
> respuesta (criterio 9 / T-`MeSerializer.get_perfil`).

---

### Paso 3.2 — Crear un usuario completo (`POST /users/`)

Crea `User` + `UserSecurity` + `UserProfile` en una transacción. Usa un
`unidad_organica`/`cargo` reales del Paso 2 y documento/teléfono libres.

```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Authorization: Bearer <access>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "jperez",
    "email": "jperez@minsa.gob.pe",
    "first_name": "Juan",
    "last_name": "Perez",
    "tipo_documento": "DNI",
    "numero_documento": "40506070",
    "apellido_paterno": "Perez",
    "apellido_materno": "Quispe",
    "telefono": "988776655",
    "unidad_organica": 14,
    "cargo": 2
  }'
```

**Esperado (201):** el `User` creado con `perfil` completo y `perfil.tiene_ficha_usuario = false`.
La respuesta incluye `password_generada` (contraseña temporal, solo en este POST).
Anotar el `id` devuelto para los pasos siguientes.

> `tiene_ficha_usuario` es opcional (default `false`); enviarlo como `true` para probar
> que persiste.

---

### Paso 3.3 — Verificar la lectura del usuario creado (`GET /users/{id}/`)

```bash
curl http://localhost:8000/api/v1/users/<id>/ -H "Authorization: Bearer <access>"
```

**Esperado (200):** `perfil.tiene_ficha_usuario` presente y todos los campos del perfil
poblados con los valores enviados en 3.2.

---

### Paso 3.4 — PATCH parcial que NO toca el perfil (criterio 10)

Cambiar solo un dato del `User` (p. ej. `first_name`) sin enviar campos de perfil.

```bash
curl -X PATCH http://localhost:8000/api/v1/users/<id>/ \
  -H "Authorization: Bearer <access>" \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Juan Carlos"}'
```

**Esperado (200):** actualiza `first_name`; el perfil permanece intacto. **No** debe
responder `400` por campos de perfil faltantes.

---

### Paso 3.5 — PATCH parcial que actualiza `tiene_ficha_usuario`

```bash
curl -X PATCH http://localhost:8000/api/v1/users/<id>/ \
  -H "Authorization: Bearer <access>" \
  -H "Content-Type: application/json" \
  -d '{"tiene_ficha_usuario": true}'
```

**Esperado (200):** `perfil.tiene_ficha_usuario = true` en la respuesta.

---

## 4. Casos de regla de negocio que DEBEN fallar

### Caso 4.1 — Crear usuario SIN campos de perfil obligatorios (criterio 8)

```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Authorization: Bearer <access>" \
  -H "Content-Type: application/json" \
  -d '{"username": "incompleto", "email": "inc@minsa.gob.pe"}'
```

**Esperado (400):** errores `required` en español para `tipo_documento`,
`numero_documento`, `apellido_paterno`, `apellido_materno`, `telefono`,
`unidad_organica` y `cargo` (mensaje del tipo *"Este campo es requerido."*).
No se crea ningún `User` (rollback atómico).

### Caso 4.2 — Documento duplicado (unicidad, criterio 5)

Repetir el POST de 3.2 con el mismo `numero_documento` (`40506070`) y otro username/email/telefono.

**Esperado (400):** `numero_documento`: *"Ya existe un perfil con este número de documento."*

### Caso 4.3 — Teléfono duplicado

POST con el mismo `telefono` (`988776655`) y otro documento.

**Esperado (400):** `telefono`: *"Ya existe un perfil con este número de teléfono."*

### Caso 4.4 — PATCH que intenta anular un campo obligatorio del perfil (criterio de T-09)

```bash
curl -X PATCH http://localhost:8000/api/v1/users/<id>/ \
  -H "Authorization: Bearer <access>" \
  -H "Content-Type: application/json" \
  -d '{"unidad_organica": null}'
```

**Esperado (400):** `unidad_organica` no admite `null`. Igual comportamiento con
`{"numero_documento": ""}` o `{"telefono": ""}` (blank rechazado).

---

## 5. RN-22 — Onboarding del interno crea su `UserProfile` (criterio 9/3.9)

Al **registrar un internado**, el sistema crea (o reutiliza) el `User` del interno con
grupo `Interno` **y su `UserProfile`** satisfaciendo las constraints `NOT NULL` + `UNIQUE`:

- `numero_documento` = el del estudiante (coincide con el `username`).
- `telefono` = móvil del estudiante; si falta o colisiona, uno **sintético único**
  (9 dígitos, empieza en 9).
- `unidad_organica` / `cargo` = filas placeholder **"No aplica"** idempotentes
  (creadas la primera vez; coherencia `cargo.organo == unidad.organo`).
- `tipo_documento` mapeado desde el catálogo del estudiante (DNI/CE/PASAPORTE/RUC;
  fallback a `DNI` si el número tiene 8 dígitos, `CE` en otro caso).
- `tiene_ficha_usuario = false` (ficha incompleta).

**Prueba:** registrar un internado por el flujo del módulo Internados
(`POST /api/v1/interns/` — rol `Universidad`; ver `spec/internados.guia_pruebas.md`
para el flujo completo de estudiante + campo clínico + internado). Tras el registro:

1. Autenticarse como el interno recién creado:

   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/token/ \
     -H "Content-Type: application/json" \
     -d '{"username": "<numero_documento_del_estudiante>", "password": "<clave_temporal>"}'
   ```

2. Consultar su perfil:

   ```bash
   curl http://localhost:8000/api/v1/auth/me/ -H "Authorization: Bearer <access_interno>"
   ```

   **Esperado (200):** `perfil` no nulo, con `numero_documento` = DNI del estudiante,
   `unidad_organica_detalle`/`cargo_detalle` = **"No aplica"**, `telefono` poblado y
   `tiene_ficha_usuario = false`. `debe_cambiar_password = true`.

3. **Idempotencia (reingreso):** dar de baja el internado a un estado liberador
   (`RETIRADO`/`CULMINADO`) y registrar uno nuevo para el mismo estudiante. El `User` y
   su `UserProfile` se reutilizan (no se duplican perfiles ni fallan las constraints, y
   no se crean nuevos placeholders "No aplica").

---

## 6. Rol/permiso por endpoint (resumen)

| Endpoint | Método | Rol requerido |
|---|---|---|
| `/auth/token/` | POST | Público (credenciales) |
| `/auth/me/` | GET | Cualquier autenticado |
| `/users/` | POST | Superusuario / Administrador RENADS |
| `/users/{id}/` | GET/PATCH/PUT | Superusuario / Administrador RENADS |
| `/organic-units/`, `/executive-positions/` | GET | Cualquier autenticado (lectura) |
| `/interns/` (registro) | POST | Universidad (crea el `User`+`UserProfile` del interno) |

---

## 7. Resultado de la validación (referencia)

Verificado contra los 12 criterios de la §7 del spec:

1. `manage.py check` (settings docker) — sin issues.
2. `makemigrations --check --dry-run` (settings docker) — *No changes detected*.
3. Postgres: `User.count() == UserProfile.count() == 2`; 0 nulos en las 8 columnas
   obligatorias; sin duplicados en `numero_documento`/`telefono`.
4. Schema postgres: las 8 columnas `NOT NULL`; índices UNIQUE en `numero_documento`
   y `telefono`; `tiene_ficha_usuario boolean NOT NULL`.
5. Modelo `UserProfile`: 7 campos obligatorios, FKs `PROTECT` con `db_column`,
   `tiene_ficha_usuario default False`.
6. Migraciones `0009` (AddField + RunPython backfill con `apps.get_model`, reverse noop,
   no borra usuarios) y `0010` (7 AlterField NOT NULL, después del backfill). División
   correcta por el error de PostgreSQL *pending trigger events* (desviación esperada, no
   es hallazgo).
7. Serializers: `tiene_ficha_usuario` en read/create/update; create exige los 7 campos;
   update tolera PATCH parcial pero rechaza blank/null; `UniqueValidator` en español.
8. Services: `crear_usuario_con_perfil` y `actualizar_perfil_usuario` no crean perfiles
   vacíos que violen NOT NULL.
9. RN-22 `aprovisionar_interno` → `_crear_perfil_interno` satisface NOT NULL + UNIQUE;
   placeholders "No aplica" idempotentes y coherentes; teléfono real/sintético; mapeo de
   tipo de documento documentado.
10. Docs sincronizadas: `docs/arquitectura_seguridad.md`, `CLAUDE.md`,
    `spec/common_perfil_usuario.md`.
11. `MeSerializer.get_perfil` tolera perfil ausente (`return None`).
