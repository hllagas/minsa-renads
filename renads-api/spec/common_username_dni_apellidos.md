# Spec — Refactor de usuario/perfil: `username = numero_documento`, apellidos a `auth_user`

**App principal:** `apps/common` — **Impacto:** `apps/internados` (onboarding del interno).
**Metodología:** SDD. Este archivo es la fuente de tareas exactas para el agente `implement`.
**NO** contiene código de aplicación; solo la especificación.

---

## 1. Resumen del refactor

Se unifica la identidad del usuario y se simplifica el perfil:

1. **`username = numero_documento`** (DNI/CE) para **todos los usuarios no-superusuario**. Extiende la regla RN-22 (hoy solo aplicada al interno) a **todos** los usuarios. El superusuario queda **exento** (username libre). `username` pasa a **autogenerado / read-only** en la API: el cliente no lo envía. **El algoritmo de generación por apellidos QUEDA DESCARTADO** (no se implementa).
2. **Se eliminan `apellido_paterno` y `apellido_materno` de `perfil_usuario`** (`UserProfile`). Los apellidos pasan a `auth_user.last_name` como **un solo campo combinado** `"Paterno Materno"`; el nombre a `auth_user.first_name`.
3. **Obligatoriedad total para no-superusuario:** `first_name`, `last_name`, `numero_documento`, `tipo_documento`, `telefono`, `unidad_organica`, `cargo`. **El superusuario está exento de TODAS** esas obligaciones (username libre, sin `last_name`/`first_name`, sin perfil completo).
4. **Renombrar el usuario existente `universidad`** → su `numero_documento` (cambia su login). El superuser `hllagas` queda **intacto**.

### Entidades afectadas

| Entidad | Tabla | Cambio |
|---|---|---|
| `UserProfile` (`apps/common/models.py:107`) | `perfil_usuario` | Se eliminan columnas `apellido_paterno` y `apellido_materno`. Resto sin cambios. |
| `auth.User` (Django default, tabla `auth_user`) | `auth_user` | Sin cambio de esquema. `last_name` pasa a alojar `"Paterno Materno"`; `first_name` el nombre. Obligatoriedad forzada en serializer/service (no en BD — `auth_user` no admite `NOT NULL` sin custom user). |

### Estado actual verificado (código real)

- Django usa `auth.User` default; sin custom user. 2 usuarios reales en postgres: `hllagas` (superuser) y `universidad` (grupo Universidad, no super).
- `UserProfile` hoy tiene todos los campos `NOT NULL` (migraciones `0009`/`0010`). Última migración common = **`0010_userprofile_not_null`**.
- `_nombre_usuario` (`serializers.py:21-31`) lee `perfil.apellido_paterno`/`apellido_materno` con fallback a `get_full_name()`/`get_username()`.
- `_crear_perfil_interno` (`internados/services.py:417-445`) hoy setea `apellido_paterno`/`apellido_materno` **en el perfil**; `aprovisionar_interno` (`services.py:312-321`) ya crea `User` con `username = numero_documento` y setea `first_name`/`last_name` en `auth_user`.
- `Student` (internados) conserva `apellido_paterno`/`apellido_materno`/`nombres` separados — **NO se toca**.

---

## 2. Tareas por archivo (ordenadas)

> Orden recomendado de ejecución: T-1 (modelo) → T-2/T-3 (serializers/service, sin correr aún) → T-4 (migración de datos+schema+rename) → T-5 (onboarding interno) → T-6 (admin) → T-7 (docs). El `implement` corre `makemigrations`/`migrate` tras T-1..T-6.

### T-1 — Modelo `apps/common/models.py`

- **T-1.1** Eliminar el campo `apellido_paterno` (`models.py:140-145`).
- **T-1.2** Eliminar el campo `apellido_materno` (`models.py:146-151`).
- **T-1.3** Actualizar `__str__` (`models.py:187-188`) — hoy usa `self.apellido_paterno`/`self.apellido_materno`. Reescribir para no depender de columnas eliminadas. Nuevo comportamiento sugerido: derivar de `auth_user`, p. ej. `return f"{self.usuario.get_full_name() or self.usuario.get_username()}".strip()` o `f"{self.usuario.last_name}, {self.usuario.first_name}".strip(", ")` con fallback a `get_username()` cuando ambos vacíos (superuser).
- **T-1.4** Actualizar el docstring de `UserProfile` (`models.py:107-116`): quitar la mención a "apellidos" en la enumeración de campos; el perfil ya no almacena apellidos (viven en `auth_user`).

**Criterio:** el modelo `UserProfile` no referencia `apellido_paterno`/`apellido_materno` en ningún atributo, docstring ni `__str__`.

### T-2 — Service `apps/common/services.py`

- **T-2.1** `crear_usuario_con_perfil` (`services.py:365-400`):
  - Derivar `username = validated_data["numero_documento"]` **para no-superusuario**. El `numero_documento` llega dentro de `profile_data` (lo extrae el serializer); el service debe tomarlo desde `profile_data` **antes** de construir el `User` y asignarlo como `username`.
  - **Ignorar cualquier `username` enviado por el cliente** para no-super (el serializer ya lo marca read-only; el service no debe confiar en él).
  - **Superusuario** (`validated_data.get("is_superuser")` truthy): respetar el `username` explícito recibido; **no** exigir `numero_documento` ni perfil completo. Si el superuser no trae `profile_data` completo, **no** crear `UserProfile` (evitar violar `NOT NULL` del perfil). Documentar en el docstring esta exención total.
  - Setear `user.first_name` / `user.last_name` desde `validated_data` (los provee el serializer; ver T-3). No perder el flujo actual de `UserSecurity` (`debe_cambiar_password=True`).
  - Ajustar el docstring: perfil sin apellidos; los apellidos van a `auth_user.last_name`.
- **T-2.2** `actualizar_perfil_usuario` (`services.py:403-447`):
  - Quitar `"apellido_paterno"` y `"apellido_materno"` del set `campos_obligatorios` (`services.py:429-432`) → queda `{tipo_documento, numero_documento, telefono, unidad_organica, cargo}` (5 campos).
  - El flujo de edición de `last_name`/`first_name` NO vive aquí (son campos de `auth_user`, no de `UserProfile`): se aplican en el `update()` del `UserUpdateSerializer` sobre la instancia `User` (ya lo hace el bucle `setattr` de `serializers.py:639-641`). Documentar que la edición de apellidos/nombre pasa por el flujo de `User`, no por el perfil.

**Criterio:** `services.py` no menciona `apellido_paterno`/`apellido_materno`; `crear_usuario_con_perfil` deriva `username` del documento para no-super y respeta el username del superuser; el superuser no requiere perfil completo.

### T-3 — Serializers `apps/common/serializers.py`

Cambios por serializer (todos con mensajes en español):

- **T-3.1** `_nombre_usuario` (`serializers.py:21-31`): reescribir para no leer `perfil.apellido_paterno`/`apellido_materno`. Nueva lógica: usar `user.get_full_name()` (combina `first_name` + `last_name`) y si está vacío, `user.get_username()`. Actualizar el docstring (quita la referencia a `UserProfile`/apellidos).
- **T-3.2** `UserProfileReadSerializer` (`serializers.py:244-270`): quitar `"apellido_paterno"` y `"apellido_materno"` de `fields` (`serializers.py:261-262`).
- **T-3.3** `UserProfileWriteSerializer` (`serializers.py:305-348`): quitar `"apellido_paterno"` y `"apellido_materno"` de `fields` (`serializers.py:342-343`). (No hay declaraciones de campo explícitas de apellidos aquí; solo la lista de `fields`.)
- **T-3.4** `UserReadSerializer` (`serializers.py:351-384`): sin cambios estructurales — ya expone `first_name`/`last_name` de `auth_user` (`serializers.py:372-373`) y anida `perfil`. Verificar que sigue leyendo el `perfil` (que ya no traerá apellidos). Ningún campo de apellidos que quitar aquí.
- **T-3.5** `UserCreateSerializer` (`serializers.py:387-519`):
  - **Quitar** las declaraciones de campo `apellido_paterno` (`serializers.py:424-427`) y `apellido_materno` (`serializers.py:428-431`).
  - **Quitar** `"apellido_paterno"` y `"apellido_materno"` de `Meta.fields` (`serializers.py:472-473`).
  - **Quitar** `"apellido_paterno"`/`"apellido_materno"` de la lista `campos_perfil` en `_extraer_profile_data` (`serializers.py:489-498`).
  - **`username`**: marcar **read-only** (`serializers.CharField(read_only=True)` o `extra_kwargs`), para que el cliente no lo envíe y aparezca autogenerado en la respuesta. El service lo deriva del documento.
  - **`first_name`** y **`last_name`**: declarar explícitamente. `required=True` para no-super (nombre y apellidos combinados obligatorios). Ver T-3.7 para la exención condicional del superusuario.
  - `numero_documento` (`serializers.py:414-423`) permanece `required=True` con `UniqueValidator` sobre `UserProfile` — **pero** debe hacerse condicional a no-super (ver T-3.7).
- **T-3.6** `UserUpdateSerializer` (`serializers.py:522-646`):
  - **Quitar** las declaraciones de campo `apellido_paterno` (`serializers.py:562-566`) y `apellido_materno` (`serializers.py:567-571`).
  - **Quitar** `"apellido_paterno"`/`"apellido_materno"` de `Meta.fields` (`serializers.py:608-609`).
  - **Quitar** `"apellido_paterno"`/`"apellido_materno"` de `campos_perfil` en `_extraer_profile_data` (`serializers.py:617-626`).
  - `first_name`/`last_name` ya editables vía `Meta.fields` (`serializers.py:598-599`) y el bucle `setattr` (`serializers.py:639-641`). Dejarlos editables. `username` permanece read-only (PATCH no debe permitir cambiarlo libremente — el username lo gobierna el documento; si el flujo de edición de documento debe re-derivar username queda fuera de alcance de este spec y se anota como riesgo, ver §6).
- **T-3.7 — Exención condicional del superusuario (required condicional):** en `UserCreateSerializer` (y donde aplique en `UserUpdateSerializer`) los campos `first_name`, `last_name` y de perfil (`tipo_documento`, `numero_documento`, `telefono`, `unidad_organica`, `cargo`) deben ser **obligatorios solo si `is_superuser` es falsy**. Implementar en un `validate(self, attrs)` que, cuando `attrs.get("is_superuser")` sea falsy, verifique la presencia de esos campos y levante `serializers.ValidationError` en español si falta alguno; cuando sea superusuario, omita la exigencia (y el service no cree perfil). Declarar los campos como `required=False` a nivel de field y trasladar la exigencia al `validate` condicional, para que el superuser pueda crearse sin ellos. Mensaje sugerido: `"Este campo es obligatorio para usuarios que no son superadministrador."`.
- **T-3.8** `MeSerializer` (`serializers.py:76-181`): no declara apellidos directamente; su `get_nombre` usa `_nombre_usuario` (ya corregido en T-3.1) y `get_perfil` usa `UserProfileReadSerializer` (ya sin apellidos por T-3.2). **Verificar** que tras los cambios `perfil` no exponga apellidos y `nombre` se derive de `auth_user`. Sin cambios de código propios más allá de la dependencia.

**Criterio:** ningún serializer de `common` declara ni lista `apellido_paterno`/`apellido_materno`; `username` es read-only en create/update; `first_name`/`last_name` obligatorios para no-super y omitibles para superuser; validaciones condicionales con mensajes en español.

### T-4 — Migración `apps/common/0011_*`

Nombre sugerido: `0011_userprofile_drop_apellidos_username_dni`. Depende de `("common", "0010_userprofile_not_null")`.

**Estrategia (orden de operaciones dentro de la migración — importa por el "pending trigger events" de PostgreSQL, mismo problema que motivó separar 0009/0010):**

1. **`RunPython` forwards (datos), reverse `noop`.** Debe correr **antes** de cualquier `RemoveField`, para poder leer `apellido_paterno`/`apellido_materno` del perfil mientras las columnas aún existen:
   - **(a) Combinar apellidos → `last_name`:** para cada `UserProfile`, componer `last_name = f"{apellido_paterno} {apellido_materno}".strip()` y escribirlo en `user.last_name` **solo si** el perfil trae apellidos y `user.last_name` está vacío (idempotente, sin sobrescribir datos reales ya presentes). Truncar a 150 caracteres (límite `auth_user.last_name`).
   - **(b) Rellenar `first_name`** si procede: si `user.first_name` está vacío, dejarlo vacío (no hay fuente de nombre en el perfil; no inventar). No es bloqueante.
   - **(c) Renombrar `username` del usuario `universidad`:** para cada `User` **no superusuario** cuyo `username` no coincida con su `perfil.numero_documento`, setear `username = perfil.numero_documento`. En la práctica cubre a `universidad`. **Excluir superusuarios** (`is_superuser=True` intacto → `hllagas` no se toca). Guardas: si el perfil no existe o `numero_documento` vacío, omitir (no romper). Si el nuevo username colisiona con otro usuario, abortar con `RuntimeError` explicativo (no debería ocurrir con 2 usuarios).
   - Usar **modelos históricos** (`apps.get_model("auth", "User")`, `apps.get_model("common", "UserProfile")`). Nunca borrar usuarios.
2. **`RemoveField`** `apellido_paterno`.
3. **`RemoveField`** `apellido_materno`.

> Si `makemigrations` no puede autogenerar el `RunPython`, el `implement` debe insertarlo manualmente **antes** de los `RemoveField` (Django autogenera solo los `RemoveField`; el `RunPython` se añade a mano en la lista `operations`). Documentar el porqué del orden en el encabezado de la migración (como hacen 0009/0010).

**Backfill cubre los 2 usuarios reales:** `hllagas` (superuser → username intacto; su `last_name` se rellena solo si el perfil trae apellidos y está vacío) y `universidad` (no-super → username pasa a su `numero_documento`; `last_name` combinado desde el perfil).

**Pseudocódigo del `RunPython` forwards:**

```
def forwards(apps, schema_editor):
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("common", "UserProfile")

    for perfil in UserProfile.objects.select_related("usuario").all():
        user = perfil.usuario
        cambios = []

        # (a) combinar apellidos -> last_name (idempotente, no sobrescribe)
        combinado = f"{perfil.apellido_paterno or ''} {perfil.apellido_materno or ''}".strip()
        if combinado and not (user.last_name or "").strip():
            user.last_name = combinado[:150]
            cambios.append("last_name")

        # (c) username = numero_documento para NO superusuarios
        if not user.is_superuser:
            ndoc = (perfil.numero_documento or "").strip()
            if ndoc and user.username != ndoc:
                if User.objects.exclude(pk=user.pk).filter(username=ndoc).exists():
                    raise RuntimeError(
                        f"Colisión de username al renombrar {user.username!r} -> {ndoc!r}"
                    )
                user.username = ndoc
                cambios.append("username")

        if cambios:
            user.save(update_fields=cambios)

def reverse(apps, schema_editor):
    pass  # noop: no se revierten datos
```

**Criterio:** `makemigrations --check` limpio tras aplicar; `migrate` OK; `last_name` poblado para `universidad`; `username == numero_documento` para `universidad`; `hllagas` (superuser) intacto; columnas `apellido_paterno`/`apellido_materno` ausentes de `perfil_usuario`.

### T-5 — Onboarding interno `apps/internados/services.py`

- **T-5.1** `_crear_perfil_interno` (`services.py:417-445`):
  - **Quitar** `apellido_paterno=estudiante.apellido_paterno` (`services.py:439`) y `apellido_materno=estudiante.apellido_materno or ""` (`services.py:440`) del `UserProfile.objects.create(...)`.
  - Actualizar el docstring (`services.py:417-429`): quitar la línea de `apellido_paterno`/`apellido_materno` (`services.py:422`); el perfil ya no almacena apellidos.
- **T-5.2** `aprovisionar_interno` (`services.py:291-340`): ya setea `first_name = estudiante.nombres[:150]` (`services.py:315`) y `last_name = f"{estudiante.apellido_paterno} {estudiante.apellido_materno}".strip()[:150]` (`services.py:316`) en `auth_user` — **esto es exactamente lo deseado; se conserva**. Verificar que sigue siendo la única fuente de apellidos/nombre del interno tras quitarlos del perfil. `username = numero_documento` ya es la regla (`services.py:306,313`).

**Criterio:** el interno se crea con apellidos combinados en `user.last_name`, nombre en `user.first_name`, `username = numero_documento`, y su `UserProfile` **sin** columnas de apellido. Reingreso idempotente sigue funcionando.

### T-6 — Admin `apps/common/admin.py`

- **T-6.1** `UserProfileAdmin` (`admin.py:19,21`): quitar `"apellido_paterno"`/`"apellido_materno"` de `list_display` y de `search_fields`. Sustituir por campos existentes (p. ej. `usuario__last_name`, `usuario__first_name` en `search_fields`; `usuario` ya está en `list_display`).

**Criterio:** el admin no referencia columnas eliminadas (evita `FieldError` al abrir el changelist).

### T-7 — Documentación

- **T-7.1** `CLAUDE.md`: ampliar RN-22 a una **regla de username general** (nueva mención, p. ej. "RN-username"): *`username = numero_documento` para todos los usuarios salvo superusuario (exento, username libre); `username` autogenerado/read-only en la API; el algoritmo por apellidos descartado*. Actualizar la descripción del **Perfil de usuario obligatorio**: `perfil_usuario` ya no tiene `apellido_paterno`/`apellido_materno`; los apellidos viven en `auth_user.last_name` (combinado `"Paterno Materno"`), el nombre en `auth_user.first_name`; **exención total del superusuario** en todas las capas. Actualizar el recuento de campos obligatorios del perfil (baja de 7 a 5 en el perfil, más `first_name`/`last_name` en `auth_user` para no-super). Referenciar migración `common 0011`.
- **T-7.2** `docs/arquitectura_seguridad.md`: (a) tabla de la §4.6 (`arquitectura_seguridad.md:114`) — quitar "Apellidos" de la descripción de `UserProfile`; (b) §4.6.1 tabla `perfil_usuario` (`arquitectura_seguridad.md:484-495`) — eliminar las filas `apellido_paterno` (`:494`) y `apellido_materno` (`:495`); (c) documentar la **regla username = numero_documento** (no-super) y la relación `auth_user.last_name` ↔ perfil; el onboarding (`:463`) ya menciona `username = numero_documento` — generalizarlo a todos los usuarios.
- **T-7.3** `spec/common_perfil_usuario_obligatorio.md`: agregar una **nota** al inicio indicando que este refactor (`spec/common_username_dni_apellidos.md`, migración `0011`) elimina `apellido_paterno`/`apellido_materno` del perfil (pasan a `auth_user.last_name`) y fija `username = numero_documento` para no-super; el conteo de "7 campos obligatorios" del perfil baja a 5.

**Criterio:** los tres documentos reflejan el esquema final sin apellidos en el perfil, la regla de username y la exención del superusuario.

---

## 3. Tabla de serializers / endpoints afectados

| Serializer / símbolo | Archivo:línea | Cambio | Endpoint(s) |
|---|---|---|---|
| `_nombre_usuario` | `serializers.py:21-31` | No leer apellidos del perfil; usar `get_full_name()`/`get_username()` | JWT `token`, `/auth/me/` |
| `CustomTokenObtainPairSerializer` | `serializers.py:34-61` | Sin cambio propio (depende de `_nombre_usuario`) | `POST /api/v1/auth/token/` |
| `MeSerializer` | `serializers.py:76-181` | Sin cambio propio (perfil sin apellidos vía dependencia) | `GET /api/v1/auth/me/` |
| `UserProfileReadSerializer` | `serializers.py:244-270` | Quitar apellidos de `fields` (`:261-262`) | lectura anidada en `/users/`, `/auth/me/` |
| `UserProfileWriteSerializer` | `serializers.py:305-348` | Quitar apellidos de `fields` (`:342-343`) | escritura de perfil |
| `UserReadSerializer` | `serializers.py:351-384` | Sin cambio (ya expone `first_name`/`last_name`) | `GET /api/v1/users/`, respuesta de POST |
| `UserCreateSerializer` | `serializers.py:387-519` | Quitar declaraciones+`fields`+`campos_perfil` de apellidos; `username` read-only; `first_name`/`last_name` obligatorios no-super; required condicional (T-3.7) | `POST /api/v1/users/` |
| `UserUpdateSerializer` | `serializers.py:522-646` | Quitar declaraciones+`fields`+`campos_perfil` de apellidos; `username` read-only | `PUT/PATCH /api/v1/users/{id}/` |
| `UserViewSet` | `views.py:190-256` | Sin cambio (usa los serializers anteriores) | `/api/v1/users/` |

> Rutas: el router registra `UserViewSet` bajo `/api/v1/users/`; `MeSerializer` sirve `/api/v1/auth/me/`; el token en `/api/v1/auth/token/` (verificar en `apps/common/urls.py`/`config/urls.py` al implementar).

---

## 4. Manejo de la exención del superusuario (todas las capas)

| Capa | Regla de exención |
|---|---|
| **Serializer** (`UserCreateSerializer`/`UserUpdateSerializer`) | Campos `first_name`, `last_name`, `tipo_documento`, `numero_documento`, `telefono`, `unidad_organica`, `cargo` declarados `required=False`; exigencia trasladada a `validate()` condicional: obligatorios **solo si** `is_superuser` es falsy (T-3.7). Superuser puede crearse/editarse sin ellos. Mensajes en español. |
| **Service** (`crear_usuario_con_perfil`) | Si `is_superuser` truthy: respeta `username` explícito, **no** deriva de documento, **no** exige ni crea `UserProfile` completo. No-super: `username = numero_documento`, crea perfil. |
| **Service** (`actualizar_perfil_usuario`) | `campos_obligatorios` reducido a 5 (sin apellidos). No fuerza perfil en superuser (solo actúa si llega `profile_data`). |
| **Migración `0011`** | El renombrado de `username` excluye `is_superuser=True`. `hllagas` (superuser) intacto; solo `universidad` (no-super) se renombra. |

---

## 5. Criterios de validación (para el `validator`)

Entorno: activar venv `.venv\Scripts\Activate.ps1`; postgres docker `DATABASE_URL="postgresql://renads:renads@localhost:5433/renads"` con `--settings=config.settings.docker`. **Nunca** `runserver`.

1. **Migraciones limpias:** `python manage.py makemigrations --check --dry-run` no reporta cambios pendientes tras crear `0011` (modelo y migración sincronizados).
2. **`migrate` OK:** `python manage.py migrate` aplica `0011` sin error (sin "pending trigger events"; el `RunPython` corre antes de los `RemoveField`).
3. **`last_name` poblado:** el usuario `universidad` tiene `auth_user.last_name` = combinación de sus antiguos apellidos del perfil (no vacío).
4. **Perfil sin columnas de apellido:** la tabla `perfil_usuario` no tiene columnas `apellido_paterno` ni `apellido_materno` (verificar con `\d perfil_usuario` o inspección del modelo/estado de migración).
5. **`username == numero_documento` (no-super):** el usuario `universidad` tiene `username` igual a su `numero_documento`.
6. **Superuser exento:** `hllagas` conserva su `username` original; puede existir/crearse sin perfil completo ni apellidos.
7. **Unicidad:** `numero_documento` sigue `UNIQUE` en `perfil_usuario`; ningún renombrado de `username` produce colisión.
8. **Serializers:** ninguna referencia a `apellido_paterno`/`apellido_materno` en `apps/common/serializers.py` ni `apps/internados/services.py` (grep vacío). `username` read-only en create/update; POST de usuario no-super sin `username` funciona y devuelve `username == numero_documento`; POST sin `first_name`/`last_name` para no-super devuelve 400 en español; POST de superuser sin perfil funciona.
9. **Onboarding interno:** aprovisionar un interno crea `User` con `last_name` combinado, `first_name` = nombres, `username` = documento, y `UserProfile` sin apellidos; reingreso idempotente.
10. **Admin:** abrir el changelist de `UserProfile` no lanza `FieldError`.

---

## 6. Impacto en el frontend (coordinar aparte — fuera de este spec de backend)

**Romperá** la UI actual de `/users` del frontend:

- La UI **lee** `r.perfil.apellido_paterno` / `r.perfil.apellido_materno` (según memoria "usuarios-ficha-write-flat-read-nested"): esos campos **desaparecen** del payload de lectura (`UserProfileReadSerializer`). El frontend debe leer los apellidos combinados desde `last_name` de `auth_user` (nivel `User`, no `perfil`).
- La UI **envía** `username`: pasa a **read-only autogenerado**; el frontend debe **dejar de enviarlo** en el alta de usuario no-super (el backend lo deriva de `numero_documento`).
- La UI debe **enviar** `first_name` (nombre) y `last_name` (apellidos combinados) para no-super, y tratarlos como obligatorios; para superuser, opcionales.

**Riesgo anotado (fuera de alcance):** si el frontend permite editar `numero_documento` de un usuario ya creado, el `username` **no** se re-deriva automáticamente en este refactor (el service solo deriva username en la creación). Definir política de re-derivación de username al editar documento queda para una iteración posterior.

---

## 7. Referencias

- Modelo: `apps/common/models.py:107-188` (`UserProfile`), campos apellidos `:140-151`, `__str__` `:187-188`.
- Serializers: `apps/common/serializers.py` — `_nombre_usuario` `:21-31`, `UserProfileReadSerializer` `:244-270`, `UserProfileWriteSerializer` `:305-348`, `UserCreateSerializer` `:387-519`, `UserUpdateSerializer` `:522-646`, `MeSerializer` `:76-181`.
- Services common: `apps/common/services.py` — `crear_usuario_con_perfil` `:365-400`, `actualizar_perfil_usuario` `:403-447`.
- Services internados: `apps/internados/services.py` — `aprovisionar_interno` `:291-340`, `_crear_perfil_interno` `:417-445`.
- Views: `apps/common/views.py` — `UserViewSet` `:190-256`.
- Admin: `apps/common/admin.py:19,21`.
- Migraciones precedentes (patrón de separación datos/schema por "pending trigger events"): `apps/common/migrations/0009_userprofile_campos_obligatorios.py`, `0010_userprofile_not_null.py`.
- Docs: `docs/arquitectura_seguridad.md` (§4.6 `:114`, §4.6.1 `:484-495`, onboarding `:463`), `CLAUDE.md` (RN-22, Perfil de usuario obligatorio), `spec/common_perfil_usuario_obligatorio.md`.
- Reglas de negocio: **RN-22** (onboarding interno, se generaliza a username=DNI para todos salvo superuser).
