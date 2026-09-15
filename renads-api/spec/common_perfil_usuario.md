# Spec — common: Perfil de usuario y gestión de contraseñas seguras

**Módulo:** `apps/common`
**Ciclo SDD:** nuevo (independiente de `common_usuarios.md`)
**Fecha:** 2026-09-14

---

## 1. Resumen del módulo

Extiende la capa de identidad de `apps/common` con tres capacidades nuevas:

1. **Perfil de usuario (`UserProfile`)** — tabla `perfil_usuario`, OneToOne con `User`. Almacena datos personales adicionales (tipo y número de documento, apellidos, teléfono) y referencias institucionales (unidad orgánica → `organo_directorio`, cargo → `cargo_ejecutivo`).
2. **Caducidad de contraseña** — campo `password_changed_at` en `UserSecurity` + setting `PASSWORD_EXPIRY_DAYS`. El login bloquea con `401 PASSWORD_EXPIRADO` si la contraseña superó la vida útil.
3. **"Olvidé mi contraseña"** — flujo OTP por correo en dos pasos (`/auth/password-reset/request/` + `/auth/password-reset/confirm/`), reutilizando la infraestructura existente de `generar_otp_email` / `validar_otp_email`.

### Entidades que cubre

| Modelo Python | Tabla BD | Tipo |
|---|---|---|
| `UserProfile` | `perfil_usuario` | Modelo nuevo |
| `UserSecurity` | `seguridad_usuario` | Modelo existente — agregar campo |

### FKs externas (lectura, no se modifica su modelo)

| Campo | FK a | App |
|---|---|---|
| `UserProfile.unidad_organica` | `organo_directorio` (`OrganDirectory`) | `apps.convenios` |
| `UserProfile.cargo` | `cargo_ejecutivo` (`ExecutivePosition`) | `apps.convenios` |

---

## 2. Tareas por capa

---

### CAPA 0 — Dependencias / settings

#### T-01 — Agregar `PASSWORD_EXPIRY_DAYS` a `config/settings/base.py`

**Archivo:** `config/settings/base.py`

**Qué hacer:**
- Agregar la siguiente línea en el bloque de configuración de seguridad (junto a `FORCE_EMAIL_2FA` u otro setting análogo de seguridad), después de la sección de 2FA:
  ```
  PASSWORD_EXPIRY_DAYS = config("PASSWORD_EXPIRY_DAYS", default=90, cast=int)
  ```
- Agregar comentario en español explicando que es el número de días de vigencia de la contraseña antes de que el sistema la trate como caducada.
- No modificar ningún otro setting.

**Criterio de done:**
- `settings.PASSWORD_EXPIRY_DAYS` evalúa a `90` sin variable de entorno.
- Con `PASSWORD_EXPIRY_DAYS=30` en `.env`, evalúa a `30`.
- El import `from decouple import config` ya existe; no agregar imports.

**Referencias:** sin tablas BD involucradas.

---

### CAPA 1 — Modelos

#### T-02 — Agregar `password_changed_at` a `UserSecurity` en `apps/common/models.py`

**Archivo:** `apps/common/models.py`

**Qué hacer:**
- Agregar el campo `password_changed_at` a `UserSecurity`, **antes** del campo `actualizado_en`:
  - Nombre Python: `password_changed_at`
  - `db_column`: `fecha_cambio_password`
  - Tipo: `DateTimeField`
  - `verbose_name`: `"fecha de cambio de contraseña"`
  - `null=True, blank=True`
  - `help_text`: `"Fecha y hora del último cambio de contraseña; nulo si nunca se ha cambiado"`
- No modificar ningún otro campo ni Meta de `UserSecurity`.

**Criterio de done:**
- `UserSecurity._meta.get_field("password_changed_at")` no lanza error.
- La columna se llama `fecha_cambio_password` en la BD (verificable con `makemigrations --check`).

**Referencias:** tabla `seguridad_usuario`, columna `fecha_cambio_password`.

---

#### T-03 — Crear modelo `UserProfile` en `apps/common/models.py`

**Archivo:** `apps/common/models.py`

**Qué hacer:**
- Definir las choices `DOCUMENT_TYPE_CHOICES` como lista de tuplas antes de la clase:
  - `("DNI", "DNI")`, `("CE", "Carnet de Extranjería")`, `("PASAPORTE", "Pasaporte")`, `("RUC", "RUC")`
- Crear la clase `UserProfile(models.Model)` con:

| Campo Python | `db_column` | Tipo Django | Restricciones | `verbose_name` | `help_text` |
|---|---|---|---|---|---|
| `usuario` | `usuario_id` | `OneToOneField(settings.AUTH_USER_MODEL, CASCADE, related_name="perfil")` | non-null | `"usuario"` | `"Usuario propietario del perfil"` |
| `tipo_documento` | `tipo_documento` | `CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)` | `blank=True, default=""` | `"tipo de documento"` | `"Tipo de documento de identidad"` |
| `numero_documento` | `numero_documento` | `CharField(max_length=20)` | `null=True, blank=True, unique=True, default=None` | `"número de documento"` | `"Número de documento de identidad"` |
| `apellido_paterno` | `apellido_paterno` | `CharField(max_length=100)` | `blank=True, default=""` | `"apellido paterno"` | `"Apellido paterno del usuario"` |
| `apellido_materno` | `apellido_materno` | `CharField(max_length=100)` | `blank=True, default=""` | `"apellido materno"` | `"Apellido materno del usuario"` |
| `telefono` | `telefono` | `CharField(max_length=20)` | `null=True, blank=True, unique=True, default=None` | `"teléfono"` | `"Número de teléfono de contacto"` |
| `unidad_organica` | `unidad_organica_id` | `ForeignKey("convenios.OrganDirectory", PROTECT, null=True, blank=True, related_name="perfiles_usuarios")` | nullable | `"unidad orgánica"` | `"Órgano del directorio al que pertenece el usuario"` |
| `cargo` | `cargo_id` | `ForeignKey("convenios.ExecutivePosition", PROTECT, null=True, blank=True, related_name="perfiles_usuarios")` | nullable | `"cargo"` | `"Cargo ejecutivo del usuario"` |

- `Meta`:
  - `db_table = "perfil_usuario"`
  - `verbose_name = "perfil de usuario"`
  - `verbose_name_plural = "perfiles de usuario"`
- `__str__`: devolver `f"{self.apellido_paterno} {self.apellido_materno}, {self.usuario.get_username()}"` (sin imports extra).
- `numero_documento` y `telefono` llevan `null=True, unique=True`: se almacena `NULL` cuando el valor está ausente (no string vacío), así múltiples valores ausentes no generan conflicto de unicidad. En el serializer, recibir `""` o no enviar el campo debe convertirse a `None` antes de guardar (`allow_null=True, allow_blank=True`).
- `email` en `auth.User`: ver T-04b — migración que añade unicidad real al campo email del modelo User de Django.

**Criterio de done:**
- `UserProfile._meta.db_table == "perfil_usuario"`.
- `UserProfile._meta.get_field("unidad_organica").remote_field.model.__name__ == "OrganDirectory"`.
- `UserProfile._meta.get_field("cargo").remote_field.model.__name__ == "ExecutivePosition"`.
- `makemigrations --check` no reporta cambios pendientes tras aplicar T-04.

**Referencias:** tabla `perfil_usuario`; FK a `organo_directorio` y `cargo_ejecutivo`.

---

### CAPA 2 — Migraciones

#### T-04 — Migración `0004_usersecurity_password_changed_at.py`

**Archivo:** `apps/common/migrations/0004_usersecurity_password_changed_at.py`

**Qué hacer:**
- Generar (o escribir manualmente) la migración que agrega la columna `fecha_cambio_password` (`DateTimeField`, null, blank) a la tabla `seguridad_usuario`.
- Dependencia: `("common", "0003_usersecurity_otp_code_length")`.
- Solo operación `AddField` sobre `UserSecurity`.

**Criterio de done:**
- `python manage.py migrate` aplica sin errores.
- `python manage.py showmigrations common` lista `0004_usersecurity_password_changed_at` como `[X]`.

---

#### T-04b — Migración `0005_user_email_unique.py` (unicidad de email en `auth.User`)

**Archivo:** `apps/common/migrations/0005_user_email_unique.py`

**Qué hacer:**
- Generar una migración en la app `common` con dependencia en `("common", "0004_usersecurity_password_changed_at")` y `("auth", "<ultima_migracion_de_auth>")`.
- **Paso 1 — data migration:** ejecutar una función `forwards` que convierta a `NULL` todos los `auth.User.email` que sean `""` (string vacío), para que la restricción `unique` no falle con múltiples vacíos:
  ```python
  User = apps.get_model("auth", "User")
  User.objects.filter(email="").update(email=None)
  ```
- **Paso 2 — AlterField:** cambiar el campo `email` de `auth.User` a `EmailField(blank=True, null=True, unique=True)`.
- Usar `migrations.RunPython` para el paso 1 y `migrations.AlterField` para el paso 2, en ese orden.

**Criterio de done:**
- `python manage.py migrate` aplica sin errores.
- En la BD, la columna `email` de `auth_user` tiene restricción `UNIQUE` y acepta `NULL`.
- Intentar crear dos usuarios con el mismo email no-nulo → error de integridad.
- Dos usuarios con email `NULL` → sin error.

**Referencias:** tabla `auth_user`, columna `email`.

---

#### T-05 — Migración `0006_userprofile.py`

**Archivo:** `apps/common/migrations/0006_userprofile.py`

**Qué hacer:**
- Generar (o escribir manualmente) la migración que crea la tabla `perfil_usuario` con todos los campos de `UserProfile` definidos en T-03.
- Dependencia: `("common", "0005_user_email_unique")` y `("convenios", "<ultima_migracion_de_convenios>")` (resolución en tiempo de generación con `makemigrations`).
- Solo operación `CreateModel`.

**Criterio de done:**
- `python manage.py migrate` aplica sin errores.
- La tabla `perfil_usuario` existe en la BD con las columnas correctas; `numero_documento` y `telefono` admiten `NULL` y tienen restricción `UNIQUE`.
- `python manage.py showmigrations common` lista `0006_userprofile` como `[X]`.

---

### CAPA 3 — Services

#### T-06 — Función `generar_password_segura()` en `apps/common/services.py`

**Archivo:** `apps/common/services.py`

**Qué hacer:**
- Agregar la función `generar_password_segura() -> str` usando únicamente el módulo `secrets` (ya importado).
- Algoritmo exacto (sin variaciones):
  1. Definir pools: minúsculas (`string.ascii_lowercase`), mayúsculas (`string.ascii_uppercase`), dígitos (`string.digits`), especiales `"!@#$%^&*"`.
  2. Elegir obligatorios: 1 minúscula, 1 mayúscula, 1 dígito, 2 especiales = 5 caracteres.
  3. Rellenar los 7 restantes de la unión de los cuatro pools.
  4. Mezclar los 12 con `secrets.SystemRandom().shuffle()` sobre una lista.
  5. Retornar el string resultante.
- Sin efectos secundarios (no escribe en BD, no envía correo).
- Agregar import `import string` en la cabecera del archivo (si no existe).

**Criterio de done:**
- La función retorna un string de exactamente 12 caracteres.
- Contiene al menos 1 minúscula, 1 mayúscula, 1 dígito y exactamente 2 especiales del conjunto `!@#$%^&*`.
- No usa `random` (solo `secrets`).
- No lanza excepciones al llamarse sin argumentos.

**Referencias:** sin tablas BD involucradas; regla de negocio R-3.

---

#### T-07 — Función `crear_usuario_con_perfil(...)` en `apps/common/services.py`

**Archivo:** `apps/common/services.py`

**Qué hacer:**
- Agregar la función `crear_usuario_con_perfil(validated_data: dict, groups: list, profile_data: dict) -> tuple[User, str]`.
- Lógica dentro de `@transaction.atomic`:
  1. Extraer y quitar `password` de `validated_data` (si viene; si no, generarla con `generar_password_segura()`). Guardar la contraseña generada en `password_plain`.
  2. Crear el `User` con `User(**validated_data)`, llamar `user.set_password(password_plain)`, `user.save()`, `user.groups.set(groups)`.
  3. Crear o recuperar `UserSecurity` y setear `debe_cambiar_password=True`, `password_changed_at=timezone.now()`. Llamar `.save(update_fields=[...])`.
  4. Crear `UserProfile` con los campos de `profile_data` (todos opcionales). Llamar `.save()`.
  5. Retornar `(user, password_plain)`.
- Importar `UserProfile` (mismo módulo) y `timezone` (ya importado).
- Si `validated_data` no contiene `password`, la función la genera internamente. Si la contiene (flujo interno del onboarding de interno — RN-22), la usa tal cual y aún setea `password_changed_at`.

**Criterio de done:**
- La función crea una fila en `auth_user`, una en `seguridad_usuario` y una en `perfil_usuario` en la misma transacción.
- `user_security.debe_cambiar_password == True` tras la llamada.
- `user_security.password_changed_at` no es `None` tras la llamada.
- Si falla cualquier paso, se hace rollback completo (todo en un `atomic`).

**Referencias:** tablas `auth_user`, `seguridad_usuario`, `perfil_usuario`; regla R-5.

---

#### T-08 — Función `actualizar_perfil_usuario(user, profile_data: dict)` en `apps/common/services.py`

**Archivo:** `apps/common/services.py`

**Qué hacer:**
- Agregar la función `actualizar_perfil_usuario(user: User, profile_data: dict) -> UserProfile`.
- Lógica:
  1. Obtener o crear el `UserProfile` ligado a `user`.
  2. Iterar sobre los pares clave-valor de `profile_data` y setear con `setattr`.
  3. Llamar `.save()` pasando `update_fields` con las claves de `profile_data` si hay cambios.
  4. Retornar la instancia actualizada.
- No usa `transaction.atomic` (la transacción la maneja el caller — `UserViewSet.perform_update`).

**Criterio de done:**
- Llamar con `profile_data={"telefono": "999"}` actualiza solo `perfil_usuario.telefono`.
- Llamar con `profile_data={}` no genera un `UPDATE` innecesario.

**Referencias:** tabla `perfil_usuario`; requerimiento R-8/R-9.

---

#### T-09 — Función `solicitar_reset_password(username: str)` en `apps/common/services.py`

**Archivo:** `apps/common/services.py`

**Qué hacer:**
- Agregar la función `solicitar_reset_password(username: str) -> None`.
- Lógica:
  1. Buscar `User.objects.filter(username=username, is_active=True).first()`. Si no existe, **retornar silenciosamente** (no lanzar excepción — no revelar si el usuario existe).
  2. Si el usuario no tiene email, retornar silenciosamente.
  3. Obtener o crear `UserSecurity` del usuario.
  4. Verificar `puede_reenviar_otp(user_security)`. Si retorna `False`, lanzar `ValidationError("Debes esperar al menos 1 minuto antes de solicitar un nuevo código.")`.
  5. Llamar `generar_otp_email(user_security)` (genera, hashea, persiste y envía correo).
  6. No retornar nada. Best-effort: el error SMTP ya está contenido en `generar_otp_email`.

**Criterio de done:**
- Para un username inexistente la función retorna sin error.
- Para un username válido y con email, genera el OTP y envía correo.
- Respeta el rate-limit de reenvío ya implementado en `puede_reenviar_otp`.

**Referencias:** tabla `seguridad_usuario`; requerimiento R-6; reutiliza `generar_otp_email`, `puede_reenviar_otp`.

---

#### T-10 — Función `confirmar_reset_password(username, otp_code, password_nueva)` en `apps/common/services.py`

**Archivo:** `apps/common/services.py`

**Qué hacer:**
- Agregar la función `confirmar_reset_password(username: str, otp_code: str, password_nueva: str) -> None`.
- Lógica dentro de `@transaction.atomic`:
  1. Buscar `User.objects.filter(username=username, is_active=True).first()`. Si no existe, lanzar `ValidationError("Credenciales no válidas.")`.
  2. Obtener `UserSecurity` del usuario. Si no existe, lanzar `ValidationError("Credenciales no válidas.")`.
  3. Llamar `validar_otp_email(user_security, otp_code)`. Si retorna `False`, lanzar `ValidationError("El código OTP no es válido o ha expirado.")`.
  4. Validar `password_nueva` con `validate_password(password_nueva, user=user)` (importar de `django.contrib.auth.password_validation`). Propagar `DjangoValidationError` convertida a DRF `ValidationError`.
  5. Llamar `user.set_password(password_nueva)`, `user.save(update_fields=["password"])`.
  6. Setear `user_security.password_changed_at = timezone.now()`, `user_security.debe_cambiar_password = False`. Guardar con `update_fields`.
  7. Registrar auditoría con `registrar_auditoria(user, "ACTUALIZAR", user, nombre_campo="password")`.

**Criterio de done:**
- OTP inválido → `ValidationError("El código OTP no es válido o ha expirado.")`.
- OTP válido, contraseña débil → `ValidationError` de los validadores de Django.
- OTP válido, contraseña válida → contraseña actualizada, `password_changed_at` seteado, OTP limpiado (lo limpia `validar_otp_email`), `debe_cambiar_password=False`.
- Toda la operación es atómica.

**Referencias:** tabla `seguridad_usuario`; columnas `fecha_cambio_password`, `debe_cambiar_password`; requerimiento R-6.

---

#### T-11 — Modificar `MeChangePasswordView` para setear `password_changed_at`

**Archivo:** `apps/common/views.py`

**Qué hacer:**
- En `MeChangePasswordView.post()`, dentro del bloque `with transaction.atomic()`, después de `usuario.set_password(...)` y antes de `registrar_auditoria`, agregar:
  ```
  seguridad.password_changed_at = timezone.now()
  seguridad.debe_cambiar_password = False
  seguridad.save(update_fields=["debe_cambiar_password", "password_changed_at", "actualizado_en"])
  ```
- Eliminar el bloque `if seguridad.debe_cambiar_password:` que solo guardaba `debe_cambiar_password` condicionalmente; el nuevo bloque siempre setea ambos campos.
- Importar `timezone` de `django.utils` si no está importado (ya está vía `apps/common/services.py` pero la view lo necesita directamente).

**Criterio de done:**
- Después de cambiar la propia contraseña, `user_security.password_changed_at` se actualiza a `now()` (no queda `None`).
- `debe_cambiar_password` siempre se setea a `False` (no solo condicionalmente).

**Referencias:** tabla `seguridad_usuario`; columna `fecha_cambio_password`; requerimiento R-4 (coherencia).

---

### CAPA 4 — Caducidad en login

#### T-12 — Gate de caducidad en `CustomTokenObtainPairView.post()`

**Archivo:** `apps/common/views.py`

**Qué hacer:**
- Agregar import de `timedelta` al principio del archivo (o importar `from datetime import timedelta` si no existe; ya existe en `apps/common/services.py`, pero la view lo necesita).
- Agregar import `from django.utils import timezone` si no está presente.
- En `CustomTokenObtainPairView.post()`, inmediatamente después del paso 3 (creación/obtención de `user_security`) y **antes** del bloque de 2FA (paso 4), insertar el gate de caducidad:

  **Lógica del gate:**
  1. Omitir el gate si `user.is_superuser` (exención total de caducidad).
  2. Leer `PASSWORD_EXPIRY_DAYS` de `settings` (importar `from django.conf import settings` ya existe en el bloque `post` como `_settings`).
  3. Si `user_security.password_changed_at is None` → tratar como expirada.
  4. Si `timezone.now() - user_security.password_changed_at > timedelta(days=_settings.PASSWORD_EXPIRY_DAYS)` → tratar como expirada.
  5. Si expirada → retornar `Response({"detail": "Tu contraseña ha expirado. Usa la opción 'Olvidé mi contraseña' para obtener una nueva.", "code": "PASSWORD_EXPIRADO"}, status=HTTP_401_UNAUTHORIZED)`.

**Criterio de done:**
- Superusuario con contraseña expirada → login exitoso (exento).
- Usuario normal con `password_changed_at=None` → `401` + `code="PASSWORD_EXPIRADO"`.
- Usuario normal con `password_changed_at` hace 91 días (con `PASSWORD_EXPIRY_DAYS=90`) → `401` + `code="PASSWORD_EXPIRADO"`.
- Usuario normal con `password_changed_at` hace 89 días → login normal (no bloqueado).
- El gate se ejecuta **antes** del flujo 2FA (si la contraseña está expirada, no se genera session_token de 2FA).

**Referencias:** tabla `seguridad_usuario`; columna `fecha_cambio_password`; requerimiento R-4.

---

### CAPA 5 — Serializers

#### T-13 — `UserProfileSerializer` (lectura/escritura) en `apps/common/serializers.py`

**Archivo:** `apps/common/serializers.py`

**Qué hacer:**
- Importar `UserProfile` desde `apps.common.models`.
- Crear `UserProfileReadSerializer(serializers.ModelSerializer)`:
  - `Meta.model = UserProfile`
  - `Meta.fields`: `["tipo_documento", "numero_documento", "apellido_paterno", "apellido_materno", "telefono", "unidad_organica", "cargo"]`
  - Todos `read_only=True`.
  - Agregar campos `unidad_organica_detalle` (`SerializerMethodField`) y `cargo_detalle` (`SerializerMethodField`) que devuelvan `str(obj.unidad_organica)` y `str(obj.cargo)` respectivamente (o `""` si son `None`).
- Crear `UserProfileWriteSerializer(serializers.ModelSerializer)`:
  - `Meta.model = UserProfile`
  - `Meta.fields`: los mismos 7 campos más `unidad_organica` (PK write) y `cargo` (PK write).
  - `numero_documento`: agregar validación con `UniqueValidator` sobre `UserProfile.objects.all()`, con `message="Ya existe un perfil con este número de documento."`. Debe ser `required=False, allow_blank=True` (el campo es opcional).
  - `unidad_organica` y `cargo`: `PrimaryKeyRelatedField(queryset=..., required=False, allow_null=True)`.
  - No definir `create` ni `update` (los maneja el service).

**Criterio de done:**
- `UserProfileReadSerializer` serializa correctamente una instancia de `UserProfile`.
- `UserProfileWriteSerializer` valida unicidad de `numero_documento` cuando no está en blanco.
- `UniqueValidator` permite que dos perfiles tengan `numero_documento=""`.

**Referencias:** tabla `perfil_usuario`; FK `unidad_organica_id` → `organo_directorio`; FK `cargo_id` → `cargo_ejecutivo`.

---

#### T-14 — Extender `UserReadSerializer` con datos de perfil

**Archivo:** `apps/common/serializers.py`

**Qué hacer:**
- Modificar `UserReadSerializer`:
  - Agregar campo `perfil = UserProfileReadSerializer(read_only=True)` (nullable: si el usuario no tiene perfil, devuelve `null` sin error).
  - Agregar campo `password_generada = serializers.CharField(read_only=True, required=False, default=None)` — este campo es `None` por defecto; solo se populará explícitamente en la respuesta del `create` (ver T-16). No se expone en `GET` a menos que la instancia tenga el atributo `_password_generada` seteado.
  - Actualizar `Meta.fields` para incluir `"perfil"` y `"password_generada"`.

**Nota de implementación:** `password_generada` no es un campo de `User` ni de `UserProfile`. El `UserViewSet.create` seteará `user._password_generada = password_plain` antes de retornar, y el serializer lo leerá con `source="*"` o como `SerializerMethodField` que lee `getattr(obj, "_password_generada", None)`. Usar `SerializerMethodField` para esto.

**Criterio de done:**
- `GET /api/v1/users/{id}/` incluye `"perfil": {...}` o `"perfil": null` (nunca falla por ausencia de `UserProfile`).
- `GET /api/v1/users/{id}/` incluye `"password_generada": null` (no expone contraseña en lecturas normales).
- La respuesta del `POST /api/v1/users/` incluye `"password_generada": "<la_contraseña>"` (ver T-16).

**Referencias:** tabla `perfil_usuario`; requerimiento R-8.

---

#### T-15 — Extender `UserCreateSerializer` con campos de perfil

**Archivo:** `apps/common/serializers.py`

**Qué hacer:**
- Modificar `UserCreateSerializer`:
  - Agregar los 7 campos de perfil como campos opcionales de escritura en el serializer:
    - `tipo_documento`: `ChoiceField(choices=DOCUMENT_TYPE_CHOICES, required=False, allow_blank=True, default="")`
    - `numero_documento`: `CharField(max_length=20, required=False, allow_blank=True, default="")`
    - `apellido_paterno`: `CharField(max_length=100, required=False, allow_blank=True, default="")`
    - `apellido_materno`: `CharField(max_length=100, required=False, allow_blank=True, default="")`
    - `telefono`: `CharField(max_length=20, required=False, allow_blank=True, default="")`
    - `unidad_organica`: `PrimaryKeyRelatedField(queryset=OrganDirectory.objects.all(), required=False, allow_null=True, default=None)`
    - `cargo`: `PrimaryKeyRelatedField(queryset=ExecutivePosition.objects.all(), required=False, allow_null=True, default=None)`
  - Importar `OrganDirectory` y `ExecutivePosition` desde `apps.convenios.models` (ya importados en el archivo vía el bloque `ASSIGNABLE_PROFILE_MODELS`).
  - Importar `DOCUMENT_TYPE_CHOICES` desde `apps.common.models`.
  - Actualizar `Meta.fields` para incluir los 7 nuevos campos.
  - Reemplazar el método `create()` de `UserCreateSerializer` por una llamada al service `crear_usuario_con_perfil()`:
    - Extraer de `validated_data` los campos de perfil (los 7 nuevos) en un dict `profile_data`.
    - Extraer `groups` de `validated_data`.
    - Extraer `password` de `validated_data` (si viene).
    - Llamar `user, password_plain = crear_usuario_con_perfil(validated_data, groups, profile_data)`.
    - Setear `user._password_generada = password_plain` para que `UserReadSerializer` lo exponga.
    - Retornar `user`.
  - El campo `password` pasa a ser `required=False` (si no se envía, el service lo genera). El `validate_password` existente permanece pero aplica solo si se envía.
  - Importar `crear_usuario_con_perfil` desde `apps.common.services`.

**Criterio de done:**
- `POST /api/v1/users/` sin `password` en el body → crea usuario con contraseña generada automáticamente.
- `POST /api/v1/users/` con campos de perfil → crea `UserProfile` correctamente.
- `POST /api/v1/users/` sin campos de perfil → crea `UserProfile` con campos vacíos/null.
- La respuesta incluye `password_generada` con la contraseña en texto claro (solo en create).

**Referencias:** tabla `perfil_usuario`; tablas `auth_user`, `seguridad_usuario`; requerimientos R-3, R-5, R-8.

---

#### T-16 — Extender `UserUpdateSerializer` con campos de perfil

**Archivo:** `apps/common/serializers.py`

**Qué hacer:**
- Modificar `UserUpdateSerializer`:
  - Agregar los mismos 7 campos de perfil que en T-15 como campos opcionales de escritura (igual estructura, sin `UniqueValidator` en este serializer — la unicidad ya la valida el service).
  - Actualizar `Meta.fields` para incluir los 7 campos.
  - Modificar `update()`:
    - Extraer los 7 campos de perfil de `validated_data` en `profile_data`.
    - Actualizar los campos de `User` como hasta ahora.
    - Si `profile_data` no está vacío, llamar `actualizar_perfil_usuario(instance, profile_data)`.
    - Retornar `instance`.
  - Importar `actualizar_perfil_usuario` desde `apps.common.services`.

**Criterio de done:**
- `PATCH /api/v1/users/{id}/` con `{"telefono": "999"}` → actualiza `perfil_usuario.telefono` sin tocar otros campos.
- `PATCH /api/v1/users/{id}/` sin campos de perfil → no intenta actualizar `UserProfile`.
- `PATCH /api/v1/users/{id}/` con `{"unidad_organica": null}` → setea `unidad_organica=None` en el perfil.

**Referencias:** tabla `perfil_usuario`; requerimientos R-8, R-9.

---

#### T-17 — Actualizar claim `nombre` en `CustomTokenObtainPairSerializer`

**Archivo:** `apps/common/serializers.py`

**Qué hacer:**
- Modificar `CustomTokenObtainPairSerializer.get_token()`:
  - Reemplazar `token["nombre"] = user.get_full_name() or user.get_username()` por la lógica:
    1. Intentar `user.perfil` (acceso al `UserProfile` vía `related_name="perfil"`).
    2. Si existe y `apellido_paterno` no está vacío: `nombre = f"{perfil.apellido_paterno} {perfil.apellido_materno}, {user.first_name}".strip()`.
    3. Si no existe `UserProfile` o el perfil está incompleto: fallback a `user.get_full_name() or user.get_username()`.
    4. Usar `getattr(user, "perfil", None)` para no lanzar `RelatedObjectDoesNotExist`.
  - Aplicar el mismo cambio en `CustomTokenObtainPairSerializer.validate()` para el campo `nombre` del body de respuesta.
- **No** modificar `TwoFactorVerifyView` — ver T-18.

**Criterio de done:**
- Usuario con `UserProfile` completo (`apellido_paterno="Garcia"`, `apellido_materno="Lopez"`, `first_name="Juan"`) → claim `nombre = "Garcia Lopez, Juan"`.
- Usuario sin `UserProfile` → claim `nombre` usa `get_full_name() or get_username()` (comportamiento anterior).
- Ningún error si `UserProfile` no existe.

**Referencias:** tabla `perfil_usuario`; requerimiento R-7.

---

#### T-18 — Actualizar claim `nombre` en `TwoFactorVerifyView`

**Archivo:** `apps/common/views.py`

**Qué hacer:**
- En `TwoFactorVerifyView.post()`, en el bloque donde se construye `refresh` y luego el dict `datos`, reemplazar:
  ```
  refresh["nombre"] = user.get_full_name() or user.get_username()
  ```
  y
  ```
  "nombre": user.get_full_name() or user.get_username(),
  ```
  por la misma lógica de composición de nombre que T-17 (usando `getattr(user, "perfil", None)`).
- Extraer la lógica de composición de nombre a una función privada `_nombre_usuario(user) -> str` en `apps/common/views.py` o en `apps/common/serializers.py` y reutilizarla en ambos puntos (T-17 y T-18). La función debe vivir en `apps/common/serializers.py` y ser importada en `views.py`.

**Criterio de done:**
- Login con 2FA activo → el JWT generado en `TwoFactorVerifyView` incluye el mismo claim `nombre` que el generado en `CustomTokenObtainPairSerializer`.
- La lógica de composición de nombre no está duplicada (existe en un único lugar).

**Referencias:** tabla `perfil_usuario`; requerimiento R-7.

---

#### T-19 — Serializers para "olvidé mi contraseña"

**Archivo:** `apps/common/serializers.py`

**Qué hacer:**
- Agregar `PasswordResetRequestSerializer(serializers.Serializer)`:
  - Campo `username`: `CharField(required=True)`.
- Agregar `PasswordResetConfirmSerializer(serializers.Serializer)`:
  - Campo `username`: `CharField(required=True)`.
  - Campo `otp_code`: `CharField(max_length=6, required=True)`.
  - Campo `password_nueva`: `CharField(write_only=True, required=True)`.
  - Método `validate_password_nueva` que llama `_validar_password(value)` (función ya existente).

**Criterio de done:**
- `PasswordResetRequestSerializer(data={"username": "x"}).is_valid()` → `True`.
- `PasswordResetConfirmSerializer` rechaza `password_nueva` débil con los mismos mensajes que `SetPasswordSerializer`.
- Ningún campo expone hashes, OTPs ni passwords en la representación de salida.

**Referencias:** sin tablas BD directas; requerimiento R-6.

---

#### T-20 — Extender `MeSerializer` con datos de perfil

**Archivo:** `apps/common/serializers.py`

**Qué hacer:**
- Modificar `MeSerializer`:
  - Agregar campo `perfil = UserProfileReadSerializer(read_only=True)` (nullable).
  - Actualizar el método `get_nombre` para usar la misma función `_nombre_usuario` de T-18.
  - Actualizar los campos de `MeSerializer` para incluir `"perfil"`.

**Criterio de done:**
- `GET /api/v1/auth/me/` incluye `"perfil": {...}` o `"perfil": null`.
- El campo `nombre` en `/auth/me/` usa la misma lógica de composición que el claim del JWT.

**Referencias:** tabla `perfil_usuario`; requerimiento R-7.

---

### CAPA 6 — Views

#### T-21 — Refactorizar `UserViewSet.perform_create` para usar el service

**Archivo:** `apps/common/views.py`

**Qué hacer:**
- El `UserCreateSerializer.create()` ya llama a `crear_usuario_con_perfil()` (T-15), por lo que `perform_create` en `UserViewSet` solo necesita:
  1. Llamar `serializer.save()` (que internamente usa el service).
  2. Registrar auditoría: `registrar_auditoria(self.request.user, "CREAR", objeto)`.
- Modificar `perform_create` para que use el serializer de respuesta `UserReadSerializer` al construir la respuesta del `create`:
  - Sobreescribir `create()` (no solo `perform_create`) para devolver `Response(UserReadSerializer(user).data, status=HTTP_201_CREATED)` donde `user` es el objeto retornado por `serializer.save()`.
  - Esto garantiza que la respuesta del POST incluya `password_generada` (que está seteada en `user._password_generada`).
- No modificar `perform_update` (el `UserUpdateSerializer.update()` ya llama al service en T-16).

**Criterio de done:**
- `POST /api/v1/users/` devuelve `201` con el body de `UserReadSerializer` incluyendo `password_generada`.
- `GET /api/v1/users/{id}/` y `PATCH /api/v1/users/{id}/` devuelven `password_generada: null`.
- La auditoría `CREAR` se registra correctamente.

**Referencias:** requerimiento R-5.

---

### CAPA 7 — Views de "olvidé mi contraseña"

#### T-22 — `PasswordResetRequestView` en `apps/common/views.py`

**Archivo:** `apps/common/views.py`

**Qué hacer:**
- Crear `PasswordResetRequestView(APIView)`:
  - `permission_classes = [AllowAny]`
  - `serializer_class = PasswordResetRequestSerializer`
  - Método `post(self, request)`:
    1. Validar con `PasswordResetRequestSerializer`.
    2. Llamar `solicitar_reset_password(username)` (service T-09). Capturar `ValidationError` de DRF (rate-limit) y retornar `429` con el mensaje.
    3. Siempre retornar `200` con mensaje genérico: `{"detalle": "Si el usuario existe y tiene correo registrado, recibirá un código de verificación."}`.
  - Importar `solicitar_reset_password` desde `apps.common.services`.
  - Importar `PasswordResetRequestSerializer` desde `apps.common.serializers`.

**Criterio de done:**
- Username inexistente → `200` con mensaje genérico (no revelar si el usuario existe).
- Username válido con email → `200` con mensaje genérico; OTP enviado.
- Rate-limit activo → `429` con mensaje de espera.
- Endpoint accesible sin autenticación (`AllowAny`).

**Referencias:** tabla `seguridad_usuario`; requerimiento R-6.

---

#### T-23 — `PasswordResetConfirmView` en `apps/common/views.py`

**Archivo:** `apps/common/views.py`

**Qué hacer:**
- Crear `PasswordResetConfirmView(APIView)`:
  - `permission_classes = [AllowAny]`
  - `serializer_class = PasswordResetConfirmSerializer`
  - Método `post(self, request)`:
    1. Validar con `PasswordResetConfirmSerializer` (incluyendo fortaleza de contraseña).
    2. Llamar `confirmar_reset_password(username, otp_code, password_nueva)` (service T-10).
    3. Si lanza `ValidationError`, retornar `400` con el mensaje.
    4. Si tiene éxito → retornar `200` con `{"detalle": "Contraseña actualizada correctamente. Ya puedes iniciar sesión."}`.
  - Importar `confirmar_reset_password` desde `apps.common.services`.
  - Importar `PasswordResetConfirmSerializer` desde `apps.common.serializers`.

**Criterio de done:**
- OTP inválido → `400` con mensaje de error.
- OTP válido, contraseña débil → `400` con errores de validación de contraseña.
- OTP válido, contraseña válida → `200`; `user_security.password_changed_at` actualizado; `debe_cambiar_password=False`.
- Endpoint accesible sin autenticación (`AllowAny`).

**Referencias:** tablas `seguridad_usuario`, `auth_user`; requerimiento R-6.

---

### CAPA 8 — URLs

#### T-24 — Registrar endpoints de "olvidé mi contraseña" en `config/api_urls.py`

**Archivo:** `config/api_urls.py`

**Qué hacer:**
- Importar `PasswordResetConfirmView` y `PasswordResetRequestView` desde `apps.common.views`.
- Agregar en `urlpatterns`:
  ```
  path("auth/password-reset/request/", PasswordResetRequestView.as_view(), name="password-reset-request"),
  path("auth/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
  ```
- Colocarlas junto a las demás rutas de `auth/` (cerca de `auth/token/`, `auth/me/`).

**Criterio de done:**
- `POST /api/v1/auth/password-reset/request/` resuelve a `PasswordResetRequestView`.
- `POST /api/v1/auth/password-reset/confirm/` resuelve a `PasswordResetConfirmView`.
- `python manage.py check` no reporta errores de rutas.

**Referencias:** requerimiento R-6; convención de prefijo `/api/v1/` ya existente.

---

## 3. Criterios de aceptación globales

| ID | Criterio | Verificación |
|---|---|---|
| CA-01 | La tabla `perfil_usuario` existe con exactamente los campos de T-03. | `python manage.py showmigrations` + inspección de BD. |
| CA-02 | La columna `fecha_cambio_password` existe en `seguridad_usuario`. | `python manage.py showmigrations` + inspección de BD. |
| CA-03 | `POST /api/v1/users/` crea usuario + `UserSecurity` + `UserProfile` en una sola transacción y devuelve `password_generada`. | Manual: POST sin contraseña, verificar las 3 filas y el campo en la respuesta. |
| CA-04 | Login con contraseña expirada (`password_changed_at` hace >90 días) → `401` + `code="PASSWORD_EXPIRADO"`. | Manual: setear `password_changed_at` a 91 días atrás en la BD, intentar login. |
| CA-05 | Superusuario con contraseña expirada → login exitoso. | Manual: misma BD manipulada, login como superusuario. |
| CA-06 | `POST /api/v1/auth/password-reset/request/` siempre devuelve `200` (no revela existencia del usuario). | Manual: probar con username inexistente y existente. |
| CA-07 | `POST /api/v1/auth/password-reset/confirm/` con OTP válido y contraseña válida → `200`, contraseña actualizada, `password_changed_at` refrescado. | Manual: flujo completo request → confirm. |
| CA-08 | Claim `nombre` en JWT incluye apellido paterno + materno cuando el `UserProfile` existe y tiene `apellido_paterno` no vacío. | Manual: crear usuario con perfil, decodificar JWT. |
| CA-09 | `GET /api/v1/auth/me/` incluye el campo `perfil` (objeto o null). | Manual. |
| CA-10 | `PATCH /api/v1/users/{id}/` actualiza campos de perfil sin tocar campos de `User` no enviados. | Manual: PATCH solo con `telefono`. |
| CA-11 | `generar_password_segura()` genera exactamente 12 caracteres con los requisitos de composición. | Verificación directa desde shell de Django. |
| CA-12 | `MeChangePasswordView` setea `password_changed_at` al cambiar la propia contraseña. | Manual: cambiar password, revisar BD. |

---

## 4. Reglas de negocio involucradas

| RN / Req | Descripción | Capa de implementación |
|---|---|---|
| R-3 | Contraseña generada: 12 chars, 1 min/may/dígito, 2 especiales, solo `secrets`. | Service T-06 |
| R-4 | Caducidad a 90 días; bloqueo solo en login; exención para superusuario. | View T-12; Settings T-01 |
| R-5 | Al crear usuario: contraseña automática, `debe_cambiar_password=True`, `password_changed_at=now()`, `UserProfile` vacío. | Service T-07; Serializer T-15; View T-21 |
| R-6 | Flujo OTP reset: request silencioso + rate-limit; confirm atómico con validación de contraseña. | Services T-09, T-10; Views T-22, T-23; Serializers T-19 |
| R-7 | Claim `nombre` compuesto como `"{ap} {am}, {first_name}"` cuando hay `UserProfile`; fallback a `get_full_name()`. | Serializers T-17, T-20; View T-18 |
| R-8 | `UserProfile` expuesto en endpoints existentes de usuarios sin crear endpoints nuevos. | Serializers T-13, T-14, T-15, T-16; View T-21 |
| R-9 | Actualización de perfil vía `PATCH /api/v1/users/{id}/` (sin endpoint separado). | Serializer T-16; View T-21 |
| RN-22 (existente) | `debe_cambiar_password` se limpia al cambiar contraseña. | View T-11 (ya existía; se extiende con `password_changed_at`) |

---

## 5. Notas de coherencia y restricciones

- **Orden de ejecución estricto:** T-01 → T-02 → T-03 → T-04 → T-05 → T-06 → T-07 → T-08 → T-09 → T-10 → T-11 → T-12 → T-13 → T-14 → T-15 → T-16 → T-17 → T-18 → T-19 → T-20 → T-21 → T-22 → T-23 → T-24. Las migraciones deben aplicarse antes de ejecutar cualquier test de las capas superiores.
- **No crear endpoints adicionales:** el perfil se expone integrado en `UserViewSet` (GET, POST, PATCH de `users/`). No existe `GET /api/v1/users/{id}/profile/` separado.
- **`numero_documento` y `telefono` son `null=True, unique=True` en el modelo** (NULL para valores ausentes; múltiples NULL no violan la unicidad). El serializer convierte string vacío `""` a `None` antes de guardar. El `email` de `auth.User` también es único tras T-04b, almacenando `NULL` para cuentas sin correo.
- **Orden de ejecución ajustado:** T-04b se numera como migración `0005_user_email_unique` y T-05 como `0006_userprofile`, respetando la cadena de dependencias.
- **Las FK `unidad_organica` y `cargo` son `PROTECT`:** eliminar un `OrganDirectory` o `ExecutivePosition` referenciado falla con error 409; no se implementa soft-delete automático.
- **El campo `password_generada` es efímero:** nunca se persiste en BD; se setea como atributo temporal en la instancia `User` (`user._password_generada`) y se lee con `SerializerMethodField`. En todas las lecturas subsecuentes devuelve `null`.
- **Compatibilidad hacia atrás en login 2FA:** `TwoFactorVerifyView` ya genera el JWT completo; T-18 solo actualiza el campo `nombre`, no altera la estructura de la respuesta.
- **`MeChangePasswordView` ya existente (T-11):** no se reescribe; solo se agrega el seteo de `password_changed_at` y se elimina la condición `if debe_cambiar_password`.
- **Convenciones de idioma:** código Python en inglés; `db_column`, `verbose_name`, `help_text` y mensajes de error al usuario en español.
