# Spec — Autenticación de dos factores (2FA) sobre JWT

## 1. Resumen del módulo

Añade autenticación de dos factores (2FA) sobre el sistema JWT existente
(SimpleJWT + `CustomTokenObtainPairView`). El módulo es transversal y vive
íntegramente en `apps/common/`. No crea una app Django nueva.

Entidades afectadas:

- `UserSecurity` (`seguridad_usuario`) — se amplía con 5 columnas nuevas.
- Ninguna tabla nueva; la migración altera la tabla existente (`0002_...`).

Métodos 2FA soportados:

- **TOTP** — contraseña de un solo uso basada en tiempo (Google Authenticator,
  Authy, etc.); usa la librería `pyotp`.
- **EMAIL** — código OTP de 6 dígitos enviado al correo del usuario; usa
  `django.core.mail.send_mail`.

Flujo de login modificado: si el usuario tiene 2FA activo, `POST /auth/token/`
no devuelve el par JWT completo sino un `session_token` de corta duración (5
min, scope `2fa_pending`). El cliente lo intercambia por el JWT real en
`POST /auth/2fa/verify/` tras ingresar el código OTP.

---

## 2. Lista de tareas por capa

### Capa 0 — Dependencias

#### T-01: Agregar `pyotp` y `qrcode` a `requirements.txt`

**Archivo:** `D:\dev\renads\renads-api\requirements.txt`

**Qué modificar:**

Añadir al final del archivo (antes del bloque de base de datos/despliegue o en
una sección propia `# 2FA`) las siguientes dos líneas:

```
pyotp==2.9.0
qrcode==8.0
```

`qrcode` se necesita solo si en el futuro se quiere devolver la imagen QR
como PNG; en el MVP basta con devolver `otpauth_uri` y la librería se incluye
como dependencia de producción para no bloquearlo.

**Criterio de done:**

- Las dos entradas aparecen en `requirements.txt` con versión fijada.
- `pip install -r requirements.txt` resuelve sin conflictos con el entorno
  existente (verificar manualmente con el venv activo).

---

### Capa 1 — Settings

#### T-02: Agregar constantes 2FA en `config/settings/base.py`

**Archivo:** `D:\dev\renads\renads-api\config\settings\base.py`

**Qué modificar:**

Agregar, a continuación del bloque de correo electrónico (después de
`DEFAULT_FROM_EMAIL`), una nueva sección claramente delimitada con comentario:

```
# ---------------------------------------------------------------------------
# Autenticación de dos factores (2FA)
# ---------------------------------------------------------------------------
```

Dentro de esa sección, leer dos variables del entorno vía `decouple.config`:

- `OTP_TTL_MINUTES` — entero, default `10`. Tiempo de vida del OTP de email
  en minutos.
- `TOTP_ISSUER_NAME` — string, default `"RENADS"`. Nombre del emisor que
  aparece en la app autenticadora al escanear el código QR.

Ambas variables se exponen como `settings.OTP_TTL_MINUTES` y
`settings.TOTP_ISSUER_NAME`.

**Criterio de done:**

- `from django.conf import settings; settings.OTP_TTL_MINUTES` devuelve `10`
  con `.env` sin esa variable.
- `settings.TOTP_ISSUER_NAME` devuelve `"RENADS"` con `.env` sin esa variable.
- El bloque sigue el patrón `config("VAR", default=..., cast=tipo)` ya
  establecido en el resto del archivo.

---

### Capa 2 — Modelo

#### T-03: Ampliar `UserSecurity` con campos 2FA en `apps/common/models.py`

**Archivo:** `D:\dev\renads\renads-api\apps\common\models.py`

**Qué modificar:**

Agregar los siguientes cinco campos al modelo `UserSecurity`, respetando la
convención del proyecto: nombres de campo en inglés, `verbose_name` y
`help_text` en español, `db_column` en español.

| Campo Python | `db_column` | Tipo | Parámetros |
|---|---|---|---|
| `two_factor_enabled` | `autenticacion_doble_factor` | `BooleanField` | `default=False`, verbose_name `"doble factor activo"`, help_text `"Indica si el usuario tiene activado el segundo factor de autenticación"` |
| `two_factor_method` | `metodo_doble_factor` | `CharField(max_length=10)` | `choices=[("TOTP","Aplicación TOTP"),("EMAIL","Correo electrónico")]`, `blank=True`, `default=""`, verbose_name `"método de doble factor"`, help_text `"Método de segundo factor: TOTP (app autenticadora) o EMAIL (código por correo)"` |
| `totp_secret` | `secreto_totp` | `CharField(max_length=64)` | `blank=True`, `default=""`, verbose_name `"secreto TOTP"`, help_text `"Secreto base32 para generar códigos TOTP; nunca se expone en la API"` |
| `otp_code` | `codigo_otp` | `CharField(max_length=8)` | `blank=True`, `default=""`, verbose_name `"código OTP transitorio"`, help_text `"Hash del código OTP de email en tránsito; vacío cuando no hay OTP pendiente"` |
| `otp_expires_at` | `otp_expira_en` | `DateTimeField` | `null=True`, `blank=True`, verbose_name `"OTP expira en"`, help_text `"Fecha y hora de expiración del OTP de email; nulo si no hay OTP pendiente"` |

Restricciones importantes para los campos sensibles:

- `totp_secret` y `otp_code` **nunca** se incluyen en ningún serializer de
  respuesta (restricción documentada en el modelo con comentario).
- `otp_code` almacenará el hash SHA-256 del código real, no el código en
  texto claro (la lógica de hash vive en el service `T-07`).

No modificar los campos existentes (`debe_cambiar_password`, `actualizado_en`,
`usuario`). No modificar `Meta`.

**Criterio de done:**

- `UserSecurity` tiene exactamente los cinco campos nuevos con los `db_column`
  indicados.
- El modelo pasa `makemigrations --check` (sin migración pendiente antes de
  la T-04).
- Ningún serializer existente expone `totp_secret` ni `otp_code`.

---

### Capa 3 — Migración

#### T-04: Crear migración `0002_usersecurity_2fa.py` en `apps/common/migrations/`

**Archivo:** `D:\dev\renads\renads-api\apps\common\migrations\0002_usersecurity_2fa.py`

**Qué modificar:**

Generar (vía `makemigrations apps.common`) la migración automática que aplica
los cinco campos de T-03 sobre la tabla `seguridad_usuario`. La migración
debe:

- Depender de `('common', '0001_initial')`.
- Contener exactamente una operación `AlterModelOptions` si fuera necesario y
  cinco `AddField`, una por cada campo nuevo.
- Ser reversible (`database_backwards` no requiere código manual; `RemoveField`
  lo maneja Django por defecto).
- No contener datos de seed (no es una data migration).

El nombre de archivo puede usar el sufijo generado automáticamente por
`makemigrations`; renombrar si el nombre generado difiere del convenio
`0002_usersecurity_2fa.py`.

**Criterio de done:**

- `python manage.py migrate` aplica la migración sin error.
- `python manage.py showmigrations common` muestra `[X] 0002_...`.
- La tabla `seguridad_usuario` en la BD tiene las cinco columnas nuevas con
  los nombres de columna en español indicados en T-03.

---

### Capa 4 — Services

#### T-05: Agregar `generar_session_token(user)` en `apps/common/services.py`

**Archivo:** `D:\dev\renads\renads-api\apps\common\services.py`

**Qué agregar:**

Función `generar_session_token(user) -> str` que genera un JWT firmado con
`settings.SECRET_KEY` (no con las claves de SimpleJWT) usando `PyJWT` (ya
disponible como dependencia transitiva de `djangorestframework-simplejwt`).

El token debe tener los siguientes claims:

- `sub` — `str(user.pk)`.
- `scope` — literal `"2fa_pending"`.
- `exp` — `datetime.utcnow() + timedelta(minutes=5)`.

Algoritmo: `HS256`.

La función devuelve el token como `str`. No tiene efectos secundarios (no
escribe en BD, no envía correo).

**Criterio de done:**

- La función existe en `services.py` y devuelve un string no vacío.
- El token decodificado con `jwt.decode(token, settings.SECRET_KEY,
  algorithms=["HS256"])` contiene `scope="2fa_pending"` y el `sub` correcto.
- La función no importa ni usa modelos de SimpleJWT.

---

#### T-06: Agregar `validar_session_token(token)` en `apps/common/services.py`

**Archivo:** `D:\dev\renads\renads-api\apps\common\services.py`

**Qué agregar:**

Función `validar_session_token(token: str) -> User` que decodifica y valida el
`session_token` generado por T-05.

Validaciones:

1. El token es un JWT válido firmado con `settings.SECRET_KEY` y algoritmo
   `HS256`.
2. No ha expirado (`exp` vigente; PyJWT lo valida automáticamente).
3. El claim `scope` es exactamente `"2fa_pending"`.
4. El `sub` corresponde a un `User` activo en la BD (`is_active=True`).

En caso de error (token inválido, expirado, scope incorrecto o usuario no
encontrado), la función lanza `rest_framework.exceptions.AuthenticationFailed`
con un mensaje en español y el `code` semántico correspondiente:

| Condición | `code` |
|---|---|
| Token malformado o firma inválida | `"SESSION_INVALIDA"` |
| Token expirado (`ExpiredSignatureError`) | `"SESSION_EXPIRADA"` |
| Scope distinto de `"2fa_pending"` | `"SESSION_INVALIDA"` |
| Usuario no encontrado o inactivo | `"SESSION_INVALIDA"` |

Devuelve la instancia `User` si la validación es exitosa.

**Criterio de done:**

- La función devuelve el `User` correcto para un token válido.
- Lanza `AuthenticationFailed` con los `code` correctos para cada escenario
  de fallo.
- No levanta excepciones no controladas de PyJWT al exterior.

---

#### T-07: Agregar `generar_otp_email(user_security)` en `apps/common/services.py`

**Archivo:** `D:\dev\renads\renads-api\apps\common\services.py`

**Qué agregar:**

Función `generar_otp_email(user_security: UserSecurity) -> None` que:

1. Genera un código OTP de 6 dígitos aleatorio usando `secrets.randbelow(10**6)`
   formateado con `zfill(6)` para garantizar 6 dígitos.
2. Calcula el hash SHA-256 del código en texto claro usando `hashlib.sha256`.
3. Guarda el hash en `user_security.otp_code` (no el código en claro).
4. Calcula `otp_expires_at = timezone.now() + timedelta(minutes=settings.OTP_TTL_MINUTES)`.
5. Guarda `user_security.otp_code` y `user_security.otp_expires_at` con
   `save(update_fields=["otp_code", "otp_expires_at", "actualizado_en"])`.
6. Envía el correo con `django.core.mail.send_mail`:
   - `subject`: `"Código de verificación RENADS"`.
   - `message`: texto plano con el código (no el hash) e instrucciones breves
     en español.
   - `from_email`: `settings.DEFAULT_FROM_EMAIL`.
   - `recipient_list`: `[user_security.usuario.email]`.
   - `fail_silently=True` (best-effort; no bloquea la respuesta si el SMTP
     falla).
7. Retorna `None`.

La función no registra auditoría (el OTP es transitorio; las acciones
auditables son activar/desactivar 2FA, no cada envío).

**Criterio de done:**

- Después de llamar a la función, `user_security.otp_code` contiene el hash
  SHA-256 del código y `otp_expires_at` está en el futuro.
- La función no almacena el código en texto claro en ningún campo.
- Con `EMAIL_BACKEND = console`, el correo aparece en la consola de Django.

---

#### T-08: Agregar `validar_otp_email(user_security, code)` en `apps/common/services.py`

**Archivo:** `D:\dev\renads\renads-api\apps\common\services.py`

**Qué agregar:**

Función `validar_otp_email(user_security: UserSecurity, code: str) -> bool` que:

1. Verifica que `user_security.otp_expires_at` no sea `None` y que
   `timezone.now() <= user_security.otp_expires_at`. Si expiró, retorna `False`
   (no lanza excepción; la vista se encarga del mensaje).
2. Calcula el hash SHA-256 del `code` recibido.
3. Compara el hash calculado con `user_security.otp_code` usando
   `hmac.compare_digest` (comparación resistente a timing attacks).
4. Si el código es válido:
   - Limpia `user_security.otp_code = ""` y `user_security.otp_expires_at = None`.
   - Guarda con `save(update_fields=["otp_code", "otp_expires_at", "actualizado_en"])`.
   - Retorna `True`.
5. Si el código es inválido retorna `False` (no limpia los campos).

**Criterio de done:**

- Retorna `True` para el código correcto dentro del TTL.
- Retorna `False` para código incorrecto o expirado.
- Los campos `otp_code` y `otp_expires_at` quedan limpios tras un código válido.

---

#### T-09: Agregar `puede_reenviar_otp(user_security)` en `apps/common/services.py`

**Archivo:** `D:\dev\renads\renads-api\apps\common\services.py`

**Qué agregar:**

Función `puede_reenviar_otp(user_security: UserSecurity) -> bool` que implementa
el rate-limit de reenvío: se permite un nuevo OTP solo si han pasado más de
1 minuto desde el último envío.

Lógica:

- Si `user_security.otp_expires_at is None` → `True` (no hay OTP en curso).
- Si `timezone.now() > user_security.otp_expires_at - timedelta(minutes=settings.OTP_TTL_MINUTES - 1)` → `True` (ha pasado más de 1 minuto desde el envío).

Equivalente a: si `(otp_expires_at - timezone.now()).total_seconds() <
(settings.OTP_TTL_MINUTES - 1) * 60` → puede reenviar.

Retorna `bool`. Sin efectos secundarios.

**Criterio de done:**

- Retorna `True` si no hay OTP en curso o si ha pasado más de 1 minuto desde
  el envío.
- Retorna `False` si el OTP fue emitido hace menos de 1 minuto.
- La lógica es puramente temporal, sin consultas adicionales a la BD.

---

#### T-10: Agregar `activar_2fa_totp(user_security, otp_code)` en `apps/common/services.py`

**Archivo:** `D:\dev\renads\renads-api\apps\common\services.py`

**Qué agregar:**

Función `activar_2fa_totp(user_security: UserSecurity, otp_code: str, usuario) -> None`
envuelta en `transaction.atomic` que:

1. Verifica que `user_security.totp_secret` no esté vacío. Si está vacío,
   lanza `rest_framework.exceptions.ValidationError` con mensaje
   `"Debes iniciar la configuración TOTP antes de confirmarla."`.
2. Verifica el código OTP con `pyotp.TOTP(user_security.totp_secret).verify(otp_code)`.
   Si es inválido, lanza `rest_framework.exceptions.ValidationError` con
   mensaje `"El código TOTP no es válido."`.
3. Actualiza `user_security.two_factor_enabled = True`,
   `user_security.two_factor_method = "TOTP"`.
4. Guarda con `save(update_fields=["two_factor_enabled", "two_factor_method", "actualizado_en"])`.
5. Llama a `registrar_auditoria(usuario, "ACTIVAR_2FA_TOTP", user_security)`.

**Criterio de done:**

- Tras la llamada exitosa, `user_security.two_factor_enabled` es `True` y
  `two_factor_method` es `"TOTP"`.
- Lanza `ValidationError` para código incorrecto o secret vacío.
- La operación es atómica (error en auditoría revierte el update).

---

#### T-11: Agregar `activar_2fa_email(user_security, password, usuario)` en `apps/common/services.py`

**Archivo:** `D:\dev\renads\renads-api\apps\common\services.py`

**Qué agregar:**

Función `activar_2fa_email(user_security: UserSecurity, password: str, usuario) -> None`
envuelta en `transaction.atomic` que:

1. Verifica la contraseña con `user_security.usuario.check_password(password)`.
   Si es incorrecta, lanza `rest_framework.exceptions.ValidationError` con
   mensaje `"La contraseña no es correcta."`.
2. Actualiza `user_security.two_factor_enabled = True`,
   `user_security.two_factor_method = "EMAIL"`.
3. Limpia `user_security.totp_secret = ""` (no aplica para email).
4. Guarda con `save(update_fields=["two_factor_enabled", "two_factor_method",
   "totp_secret", "actualizado_en"])`.
5. Llama a `registrar_auditoria(usuario, "ACTIVAR_2FA_EMAIL", user_security)`.

**Criterio de done:**

- Tras la llamada exitosa, `two_factor_enabled` es `True` y `two_factor_method`
  es `"EMAIL"`.
- Lanza `ValidationError` para contraseña incorrecta.
- `totp_secret` queda limpio.

---

#### T-12: Agregar `desactivar_2fa(user_security, password, otp_code, usuario)` en `apps/common/services.py`

**Archivo:** `D:\dev\renads\renads-api\apps\common\services.py`

**Qué agregar:**

Función `desactivar_2fa(user_security: UserSecurity, password: str, otp_code: str, usuario) -> None`
envuelta en `transaction.atomic` que:

1. Verifica la contraseña con `user_security.usuario.check_password(password)`.
   Si es incorrecta, lanza `rest_framework.exceptions.ValidationError` con
   mensaje `"La contraseña no es correcta."`.
2. Verifica el OTP según el método activo:
   - Si `two_factor_method == "TOTP"`: usa `pyotp.TOTP(user_security.totp_secret).verify(otp_code)`.
     Si inválido → `ValidationError("El código TOTP no es válido.")`.
   - Si `two_factor_method == "EMAIL"`: usa `validar_otp_email(user_security, otp_code)`.
     Si retorna `False` → `ValidationError("El código OTP no es válido o ha expirado.")`.
3. Limpia todos los campos 2FA: `two_factor_enabled = False`,
   `two_factor_method = ""`, `totp_secret = ""`, `otp_code = ""`,
   `otp_expires_at = None`.
4. Guarda con `save(update_fields=["two_factor_enabled", "two_factor_method",
   "totp_secret", "otp_code", "otp_expires_at", "actualizado_en"])`.
5. Llama a `registrar_auditoria(usuario, "DESACTIVAR_2FA", user_security)`.

**Criterio de done:**

- Tras la llamada exitosa, `two_factor_enabled` es `False` y todos los campos
  2FA quedan con sus valores por defecto.
- Lanza `ValidationError` para contraseña incorrecta o OTP inválido.
- Requiere tanto la contraseña como el OTP (doble verificación).

---

### Capa 5 — Serializers

#### T-13: Agregar serializers 2FA en `apps/common/serializers.py`

**Archivo:** `D:\dev\renads\renads-api\apps\common\serializers.py`

**Qué agregar:**

Cinco serializers nuevos al final del archivo (después de
`AssignableEntityTypeSerializer`). Todos son `serializers.Serializer` (no
`ModelSerializer`). Ninguno expone `totp_secret` ni `otp_code`.

**T-13a `TwoFactorVerifySerializer`**

Campos:

- `session_token` — `CharField()`, requerido. Token obtenido en el login
  diferido.
- `otp_code` — `CharField(max_length=8)`, requerido. Código ingresado por
  el usuario (TOTP de 6 dígitos o OTP de email de 6 dígitos).

**T-13b `TotpSetupConfirmSerializer`**

Campos:

- `otp_code` — `CharField(max_length=6)`, requerido. Código TOTP generado
  por la app autenticadora para confirmar que el secreto fue escaneado
  correctamente.

**T-13c `TwoFactorSetupEmailSerializer`**

Campos:

- `password` — `CharField(write_only=True)`, requerido. Contraseña actual
  del usuario para autorizar la activación del 2FA por email.

**T-13d `TwoFactorDisableSerializer`**

Campos:

- `password` — `CharField(write_only=True)`, requerido.
- `otp_code` — `CharField(max_length=8)`, requerido.

**T-13e `TwoFactorResendSerializer`**

Campos:

- `session_token` — `CharField()`, requerido.

**Criterio de done:**

- Los cinco serializers existen y son importables desde `apps.common.serializers`.
- Ninguno incluye `totp_secret`, `otp_code` (columna de BD) ni ningún campo
  sensible de `UserSecurity` en la salida.
- `TwoFactorVerifySerializer` y `TwoFactorResendSerializer` no requieren
  autenticación previa en el serializer (la validación del token ocurre en
  el service).

---

### Capa 6 — Views

#### T-14: Modificar `CustomTokenObtainPairView.post()` en `apps/common/views.py`

**Archivo:** `D:\dev\renads\renads-api\apps\common\views.py`

**Qué modificar:**

Sobreescribir el método `post(self, request, *args, **kwargs)` en
`CustomTokenObtainPairView` para interceptar el resultado del login y
bifurcar según si el usuario tiene 2FA activo.

Flujo:

1. Llamar a `super().post(request, *args, **kwargs)` para ejecutar la
   validación de credenciales normal (usuario/contraseña).
2. Si el status de la respuesta NO es `200`, retornarla tal cual (error de
   credenciales).
3. Identificar el usuario: leerlo desde `self.get_serializer().user` (el
   serializer de SimpleJWT lo guarda tras `validate`). Alternativa: releer
   el usuario por `username` del request data (evitar doble validación).
4. Obtener o crear `UserSecurity` para el usuario: `UserSecurity.objects.get_or_create(usuario=user)`.
5. Si `user_security.two_factor_enabled` es `False`:
   - Devolver la respuesta original sin modificar (flujo sin 2FA).
6. Si `two_factor_enabled` es `True`:
   - Si `two_factor_method == "EMAIL"`, llamar a `generar_otp_email(user_security)`
     (best-effort; el correo sale en background; no bloquear la respuesta si
     falla).
   - Llamar a `generar_session_token(user)` (T-05) para obtener el
     `session_token`.
   - Construir y devolver una respuesta `200` con el siguiente cuerpo (NO
     incluir `access`, `refresh` ni datos del JWT real):

     ```json
     {
       "requires_2fa": true,
       "session_token": "<token>",
       "method": "TOTP" | "EMAIL"
     }
     ```

**Restricción:** el envío de OTP por email (paso 6.a) debe hacerse en
`try/except Exception` con `pass` o logging silencioso para que un fallo del
SMTP no rompa el login.

**Criterio de done:**

- Un usuario sin 2FA recibe la respuesta habitual (con `access`, `refresh`,
  `grupos`, etc.) sin cambios.
- Un usuario con 2FA TOTP activo recibe `{"requires_2fa": true, "session_token": "...", "method": "TOTP"}` y no recibe `access` ni `refresh`.
- Un usuario con 2FA EMAIL activo recibe `{"requires_2fa": true, "session_token": "...", "method": "EMAIL"}` y el OTP es enviado a su correo.

---

#### T-15: Agregar `TwoFactorVerifyView` en `apps/common/views.py`

**Archivo:** `D:\dev\renads\renads-api\apps\common\views.py`

**Qué agregar:**

Clase `TwoFactorVerifyView(APIView)` con:

- `permission_classes = [AllowAny]` — la autenticación se basa en
  `session_token`, no en JWT.
- Método `post(self, request)`:
  1. Validar `TwoFactorVerifySerializer(data=request.data)`.
  2. Llamar a `validar_session_token(data["session_token"])` (T-06) para
     obtener el `user`. Si lanza `AuthenticationFailed`, propagar la
     excepción (DRF la convierte a `401`).
  3. Obtener `user_security = UserSecurity.objects.get(usuario=user)`.
  4. Verificar el OTP según `user_security.two_factor_method`:
     - `"TOTP"`: `pyotp.TOTP(user_security.totp_secret).verify(data["otp_code"])`.
       Si `False` → `401` con `code="OTP_INVALIDO"`.
     - `"EMAIL"`: llamar a `validar_otp_email(user_security, data["otp_code"])`.
       Si `False` → `401` con `code="OTP_INVALIDO"`.
  5. Generar el par JWT completo usando el serializer de SimpleJWT:
     Instanciar `CustomTokenObtainPairSerializer` e invocar `get_token(user)`
     para obtener el token de refresco y derivar el access token. Construir la
     respuesta con los mismos campos que devuelve el login normal (`access`,
     `refresh`, `access_token`, `token_type`, `nombre`, `grupos`,
     `es_superusuario`, `debe_cambiar_password`).
  6. Devolver `Response(datos, status=200)`.

**Criterio de done:**

- Con un `session_token` válido y el OTP correcto devuelve `200` con el JWT
  completo.
- Con OTP incorrecto devuelve `401` y `code="OTP_INVALIDO"`.
- Con `session_token` expirado devuelve `401` y `code="SESSION_EXPIRADA"`.
- No requiere ningún header `Authorization` en el request.

---

#### T-16: Agregar `TotpSetupView` en `apps/common/views.py`

**Archivo:** `D:\dev\renads\renads-api\apps\common\views.py`

**Qué agregar:**

Clase `TotpSetupView(APIView)` con:

- `permission_classes = [IsAuthenticated]`.
- Método `post(self, request)`:
  1. Obtener o crear `UserSecurity` del usuario autenticado.
  2. Generar un nuevo secreto TOTP: `secret = pyotp.random_base32()`.
  3. Guardar el secreto en `user_security.totp_secret` con
     `save(update_fields=["totp_secret", "actualizado_en"])`. No activar 2FA
     todavía (la activación ocurre en T-17 tras confirmación).
  4. Construir el URI de aprovisionamiento:
     `pyotp.totp.TOTP(secret).provisioning_uri(name=request.user.email, issuer_name=settings.TOTP_ISSUER_NAME)`.
  5. Devolver `Response({"otpauth_uri": uri, "secret": secret}, status=200)`.

**Nota:** el `secret` se devuelve en texto claro en esta respuesta para que
el usuario pueda ingresarlo manualmente si no puede escanear el QR. El
frontend es responsable de mostrar el QR a partir del URI.

**Criterio de done:**

- Devuelve `200` con `otpauth_uri` y `secret` para el usuario autenticado.
- `user_security.totp_secret` contiene el nuevo secreto tras la llamada.
- `two_factor_enabled` no cambia en esta operación.
- Un segundo `POST` sobreescribe el secreto previo (el setup es idempotente
  y reiniciable).

---

#### T-17: Agregar `TotpConfirmView` en `apps/common/views.py`

**Archivo:** `D:\dev\renads\renads-api\apps\common\views.py`

**Qué agregar:**

Clase `TotpConfirmView(APIView)` con:

- `permission_classes = [IsAuthenticated]`.
- Método `post(self, request)`:
  1. Validar `TotpSetupConfirmSerializer(data=request.data)`.
  2. Obtener `user_security` del usuario autenticado. Si no existe, devolver
     `400` con mensaje `"Inicia el setup TOTP antes de confirmar."`.
  3. Llamar a `activar_2fa_totp(user_security, data["otp_code"], request.user)`
     (T-10). Si lanza `ValidationError`, propagar.
  4. Devolver `Response({"detalle": "Autenticación TOTP activada correctamente."}, status=200)`.

**Criterio de done:**

- Con código TOTP correcto devuelve `200` y `two_factor_enabled` es `True`.
- Con código incorrecto devuelve `400` con el mensaje del service.
- Requiere JWT válido.

---

#### T-18: Agregar `TwoFactorSetupEmailView` en `apps/common/views.py`

**Archivo:** `D:\dev\renads\renads-api\apps\common\views.py`

**Qué agregar:**

Clase `TwoFactorSetupEmailView(APIView)` con:

- `permission_classes = [IsAuthenticated]`.
- Método `post(self, request)`:
  1. Validar `TwoFactorSetupEmailSerializer(data=request.data)`.
  2. Obtener o crear `user_security` del usuario autenticado.
  3. Llamar a `activar_2fa_email(user_security, data["password"], request.user)`
     (T-11). Si lanza `ValidationError`, propagar.
  4. Devolver `Response({"detalle": "Autenticación por correo electrónico activada correctamente."}, status=200)`.

**Criterio de done:**

- Con contraseña correcta devuelve `200` y `two_factor_enabled` es `True` con
  `two_factor_method = "EMAIL"`.
- Con contraseña incorrecta devuelve `400`.
- Requiere JWT válido.

---

#### T-19: Agregar `TwoFactorResendView` en `apps/common/views.py`

**Archivo:** `D:\dev\renads\renads-api\apps\common\views.py`

**Qué agregar:**

Clase `TwoFactorResendView(APIView)` con:

- `permission_classes = [AllowAny]`.
- Método `post(self, request)`:
  1. Validar `TwoFactorResendSerializer(data=request.data)`.
  2. Llamar a `validar_session_token(data["session_token"])` para obtener el
     `user`. Si falla, propagar el `401`.
  3. Obtener `user_security` del usuario. Si `two_factor_method != "EMAIL"`,
     devolver `400` con mensaje `"El reenvío de OTP solo aplica para el método EMAIL."`.
  4. Llamar a `puede_reenviar_otp(user_security)` (T-09). Si devuelve `False`,
     devolver `429` con mensaje
     `"Debes esperar al menos 1 minuto antes de solicitar un nuevo código."`.
  5. Llamar a `generar_otp_email(user_security)` (T-07) para generar y enviar
     un nuevo código.
  6. Devolver `Response({"detalle": "Código reenviado al correo registrado."}, status=200)`.

**Criterio de done:**

- Reenvía el OTP si `puede_reenviar_otp` es `True`.
- Devuelve `429` si el usuario solicita el reenvío demasiado pronto.
- Devuelve `400` si el método no es EMAIL.
- No requiere JWT real; basta el `session_token`.

---

#### T-20: Agregar `TwoFactorDisableView` en `apps/common/views.py`

**Archivo:** `D:\dev\renads\renads-api\apps\common\views.py`

**Qué agregar:**

Clase `TwoFactorDisableView(APIView)` con:

- `permission_classes = [IsAuthenticated]`.
- Método `delete(self, request)`:
  1. Validar `TwoFactorDisableSerializer(data=request.data)`.
  2. Obtener `user_security` del usuario autenticado. Si `two_factor_enabled`
     es `False`, devolver `400` con mensaje `"El doble factor no está activo."`.
  3. Si `two_factor_method == "EMAIL"`, se requiere que haya un OTP vigente en
     `user_security`. Si `otp_code` está vacío, llamar primero a
     `generar_otp_email(user_security)` para enviarlo y devolver `200` con
     mensaje `"Se ha enviado un código de verificación a tu correo. Reenvía esta petición incluyendo el código recibido."`. Si `otp_code` ya existe
     (el usuario ya lo solicitó), proceder a la verificación.
  4. Llamar a `desactivar_2fa(user_security, data["password"], data["otp_code"], request.user)`
     (T-12). Si lanza `ValidationError`, propagar.
  5. Devolver `Response({"detalle": "Doble factor desactivado."}, status=200)`.

**Criterio de done:**

- Con contraseña y OTP correctos devuelve `200` y `two_factor_enabled` es `False`.
- Con contraseña incorrecta o OTP inválido devuelve `400`.
- Si el 2FA ya estaba inactivo devuelve `400`.
- Requiere JWT válido.

---

### Capa 7 — URLs

#### T-21: Registrar rutas 2FA en `apps/common/urls.py`

**Archivo:** `D:\dev\renads\renads-api\apps\common\urls.py`

**Qué modificar:**

Añadir las siguientes importaciones desde `apps.common.views` (una vez
implementadas las vistas en T-15 a T-20):

```
TotpConfirmView
TotpSetupView
TwoFactorDisableView
TwoFactorResendView
TwoFactorSetupEmailView
TwoFactorVerifyView
```

Añadir la siguiente lista de rutas al `urlpatterns` existente (no crear un
router nuevo; usar `path()` al igual que los demás endpoints de `common`):

| Ruta | Vista | `name` |
|---|---|---|
| `2fa/verify/` | `TwoFactorVerifyView` | `"2fa-verify"` |
| `2fa/setup/totp/` | `TotpSetupView` | `"2fa-setup-totp"` |
| `2fa/confirm-totp/` | `TotpConfirmView` | `"2fa-confirm-totp"` |
| `2fa/setup/email/` | `TwoFactorSetupEmailView` | `"2fa-setup-email"` |
| `2fa/resend-otp/` | `TwoFactorResendView` | `"2fa-resend-otp"` |
| `2fa/disable/` | `TwoFactorDisableView` | `"2fa-disable"` |

Las rutas se agregan dentro del `urlpatterns` del archivo; el prefijo `auth/`
se aplica en T-22.

**Criterio de done:**

- Las seis rutas existen en `urlpatterns` de `apps/common/urls.py`.
- Los `name` son exactamente los indicados (usados para pruebas de integración
  con `reverse()`).

---

#### T-22: Registrar el prefijo `auth/2fa/` en `config/api_urls.py`

**Archivo:** `D:\dev\renads\renads-api\config\api_urls.py`

**Qué modificar:**

Las rutas 2FA se sirven desde el prefijo `auth/`. Dado que `apps.common.urls`
ya se incluye sin prefijo en `config/api_urls.py` (línea `path("", include("apps.common.urls"))`), las rutas de T-21 (con prefijo `2fa/`) quedarán accesibles bajo `/api/v1/2fa/` en lugar de `/api/v1/auth/2fa/`.

Para exponer los endpoints bajo el prefijo correcto (`/api/v1/auth/2fa/`), hay
dos opciones; elegir la que menos altere el archivo:

**Opción A (preferida):** mover las seis rutas 2FA a un nuevo include con
prefijo `auth/` agregando en `config/api_urls.py`:

```python
path("auth/", include("apps.common.urls_2fa")),
```

y crear `apps/common/urls_2fa.py` con solo las seis rutas `2fa/*`.

**Opción B:** mantener todo en `apps/common/urls.py` pero agregar la inclusión
a `config/api_urls.py` con prefijo `auth/` y quitar las rutas 2FA del include
sin prefijo (ajustar la separación de urlpatterns dentro de `common`).

La decisión de Opción A vs. B se deja al agente Implement, con preferencia por
A por ser más limpia. Lo obligatorio es que las URLs finales sean:

- `POST /api/v1/auth/2fa/verify/`
- `POST /api/v1/auth/2fa/setup/totp/`
- `POST /api/v1/auth/2fa/confirm-totp/`
- `POST /api/v1/auth/2fa/setup/email/`
- `POST /api/v1/auth/2fa/resend-otp/`
- `DELETE /api/v1/auth/2fa/disable/`

**Criterio de done:**

- Los seis endpoints responden (no dan 404) bajo `/api/v1/auth/2fa/`.
- Las rutas existentes (`/api/v1/auth/token/`, `/api/v1/auth/me/`, etc.) no
  se ven afectadas.

---

## 3. Criterios de aceptación globales

| # | Criterio |
|---|---|
| G-1 | Un usuario sin 2FA activo puede hacer login en `POST /auth/token/` y recibe el JWT normal; la respuesta no incluye `requires_2fa`. |
| G-2 | Un usuario con 2FA-TOTP activo recibe `{"requires_2fa": true, "method": "TOTP", "session_token": "..."}` al hacer login; sin `access` ni `refresh`. |
| G-3 | Un usuario con 2FA-EMAIL activo recibe `{"requires_2fa": true, "method": "EMAIL", "session_token": "..."}` y el correo con el OTP es enviado (visible en consola con backend de consola). |
| G-4 | El `session_token` expira exactamente a los 5 minutos; `POST /auth/2fa/verify/` con token expirado devuelve `401` y `code="SESSION_EXPIRADA"`. |
| G-5 | `POST /auth/2fa/verify/` con OTP incorrecto devuelve `401` y `code="OTP_INVALIDO"`. |
| G-6 | `POST /auth/2fa/verify/` con OTP correcto devuelve `200` con JWT completo idéntico en estructura al login normal. |
| G-7 | `POST /auth/2fa/setup/totp/` requiere JWT; devuelve `otpauth_uri` válido y `secret` base32. |
| G-8 | `POST /auth/2fa/confirm-totp/` con código TOTP correcto activa `two_factor_enabled=True` y `two_factor_method="TOTP"`. |
| G-9 | `POST /auth/2fa/setup/email/` con contraseña correcta activa `two_factor_enabled=True` y `two_factor_method="EMAIL"`. |
| G-10 | `POST /auth/2fa/resend-otp/` dentro del primer minuto devuelve `429`. |
| G-11 | `DELETE /auth/2fa/disable/` con contraseña y OTP correctos desactiva 2FA y limpia todos los campos 2FA en `seguridad_usuario`. |
| G-12 | `totp_secret` y `otp_code` (hash) **nunca** aparecen en ninguna respuesta de la API. |
| G-13 | La migración `0002_usersecurity_2fa` aplica limpiamente sobre la migración inicial y es reversible. |
| G-14 | `registrar_auditoria` se llama con las acciones `ACTIVAR_2FA_TOTP`, `ACTIVAR_2FA_EMAIL` y `DESACTIVAR_2FA` en las operaciones correspondientes. |

---

## 4. Referencias

### Tablas / columnas afectadas

| Tabla | Columna | Tipo | Descripción |
|---|---|---|---|
| `seguridad_usuario` | `autenticacion_doble_factor` | `boolean default false` | 2FA activo |
| `seguridad_usuario` | `metodo_doble_factor` | `varchar(10) default ''` | `'TOTP'` o `'EMAIL'` |
| `seguridad_usuario` | `secreto_totp` | `varchar(64) default ''` | Secreto base32 TOTP |
| `seguridad_usuario` | `codigo_otp` | `varchar(8) default ''` | Hash SHA-256 del OTP de email |
| `seguridad_usuario` | `otp_expira_en` | `timestamptz null` | Expiración del OTP de email |

### Dependencias de librería

| Librería | Versión | Uso |
|---|---|---|
| `pyotp` | `2.9.0` | Generar y verificar códigos TOTP; `random_base32()`, `TOTP.verify()`, `TOTP.provisioning_uri()` |
| `qrcode` | `8.0` | Potencial generación de imagen QR (no requerida en MVP; se incluye como dependencia) |
| `PyJWT` | transitiva de `simplejwt` | Firmar y decodificar el `session_token` con HS256 |
| `hashlib` | stdlib | Hash SHA-256 del OTP email |
| `hmac` | stdlib | Comparación resistente a timing attacks en `validar_otp_email` |
| `secrets` | stdlib | Generación segura del código OTP de 6 dígitos |

### Reglas de negocio aplicadas

| RN | Descripción | Capa |
|---|---|---|
| RN-2FA-01 | Sin 2FA activo → flujo de login sin cambios | Service / View (T-14) |
| RN-2FA-02 | Con 2FA activo → login devuelve `session_token` transitorio (5 min, scope `2fa_pending`), no el JWT final | Service / View (T-05, T-14) |
| RN-2FA-03 | `session_token` con scope distinto de `2fa_pending` es inválido | Service (T-06) |
| RN-2FA-04 | OTP email expira a los `OTP_TTL_MINUTES` minutos (default 10) | Service (T-07) |
| RN-2FA-05 | Rate-limit de reenvío OTP: mínimo 1 minuto entre envíos | Service (T-09) |
| RN-2FA-06 | `totp_secret` y `otp_code` (hash) nunca se exponen en la API | Serializer (T-13) / Modelo (T-03) |
| RN-2FA-07 | La desactivación de 2FA exige contraseña + OTP vigente (doble verificación) | Service (T-12) |
| RN-2FA-08 | La activación de TOTP requiere confirmación con un código válido antes de habilitar el flag | Service (T-10) |
| RN-AUD-01 | Las acciones de activación y desactivación de 2FA se registran en `bitacora_auditoria` | Service (T-10, T-11, T-12) |

### Archivos modificados / creados

| Archivo | Acción |
|---|---|
| `requirements.txt` | Modificar — agregar `pyotp==2.9.0` y `qrcode==8.0` |
| `config/settings/base.py` | Modificar — agregar `OTP_TTL_MINUTES` y `TOTP_ISSUER_NAME` |
| `apps/common/models.py` | Modificar — agregar 5 campos a `UserSecurity` |
| `apps/common/migrations/0002_usersecurity_2fa.py` | Crear — migración automática |
| `apps/common/services.py` | Modificar — agregar 8 funciones nuevas |
| `apps/common/serializers.py` | Modificar — agregar 5 serializers nuevos |
| `apps/common/views.py` | Modificar — 1 método sobreescrito + 6 vistas nuevas |
| `apps/common/urls.py` | Modificar — agregar 6 rutas `2fa/*` |
| `apps/common/urls_2fa.py` | Crear (si se elige Opción A en T-22) |
| `config/api_urls.py` | Modificar — registrar el prefijo `auth/` para las rutas 2FA |
