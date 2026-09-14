# Guía de pruebas manuales — Módulo 2FA

Versión generada por el agente Validator tras validación exitosa.

---

## 1. Prerrequisitos

1. Levantar el servidor de desarrollo (lo ejecuta el usuario):
   ```
   python manage.py runserver
   ```
2. URL base: `http://localhost:8000/api/v1/`
3. Documentación interactiva (alternativa a los curl): `http://localhost:8000/api/v1/docs/`
4. Obtener token JWT de un usuario existente (sin 2FA activo para empezar):
   ```
   POST http://localhost:8000/api/v1/auth/token/
   Content-Type: application/json

   {
     "username": "admin",
     "password": "contraseña_del_admin"
   }
   ```
   Respuesta esperada (`200`):
   ```json
   {
     "access": "<access_jwt>",
     "refresh": "<refresh_jwt>",
     "nombre": "...",
     "grupos": [...],
     "es_superusuario": true,
     "debe_cambiar_password": false
   }
   ```
5. Usar `Authorization: Bearer <access_jwt>` en todas las llamadas que requieran JWT.

---

## 2. Datos previos necesarios

- Al menos un usuario activo en la BD con correo electrónico válido (para 2FA-EMAIL).
- `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'` en settings de desarrollo para ver los OTP en la consola.
- No se requieren catálogos adicionales; los campos 2FA viven en `seguridad_usuario` y se crean o recuperan automáticamente.

---

## 3. Flujo de pruebas por criterio de aceptación

### G-1 — Login sin 2FA: respuesta JWT normal

**Rol requerido:** cualquier usuario activo sin 2FA activado.

```
POST /api/v1/auth/token/
Content-Type: application/json

{
  "username": "admin",
  "password": "mi_contraseña"
}
```

**Respuesta esperada (`200`):** contiene `access`, `refresh`, `nombre`, `grupos`, `es_superusuario`, `debe_cambiar_password`. **No** debe contener `requires_2fa`.

---

### G-7 — Iniciar setup TOTP

**Rol requerido:** cualquier usuario autenticado (JWT válido).

```
POST /api/v1/auth/2fa/setup/totp/
Authorization: Bearer <access_jwt>
```

**Respuesta esperada (`200`):**
```json
{
  "otpauth_uri": "otpauth://totp/RENADS:usuario@ejemplo.com?secret=XXXXXXXX&issuer=RENADS",
  "secret": "BASETHIRTYTWOSECRETSTRING"
}
```

- Copiar el `secret` o escanear el URI con Google Authenticator / Authy.
- `two_factor_enabled` **no** cambia todavía.
- Un segundo `POST` sobreescribe el secreto anterior (idempotente).

---

### G-8 — Confirmar TOTP y activar 2FA

**Rol requerido:** usuario autenticado que haya realizado el paso anterior.

```
POST /api/v1/auth/2fa/confirm-totp/
Authorization: Bearer <access_jwt>
Content-Type: application/json

{
  "otp_code": "123456"
}
```

(Usar el código de 6 dígitos generado por la app autenticadora en el momento.)

**Respuesta esperada (`200`):**
```json
{
  "detalle": "Autenticación TOTP activada correctamente."
}
```

**Caso de fallo (RN-2FA-08):** enviar un código incorrecto o el campo vacío debe devolver `400`:
```json
{
  "El código TOTP no es válido."
}
```

---

### G-2 — Login con 2FA-TOTP activo: recibe session_token

Después de activar TOTP, volver a hacer login:

```
POST /api/v1/auth/token/
Content-Type: application/json

{
  "username": "admin",
  "password": "mi_contraseña"
}
```

**Respuesta esperada (`200`, sin `access` ni `refresh`):**
```json
{
  "requires_2fa": true,
  "session_token": "<jwt_corto_duracion>",
  "method": "TOTP"
}
```

Guardar el `session_token` para el paso siguiente.

---

### G-5 y G-6 — Verificar OTP TOTP (código incorrecto y correcto)

**Rol requerido:** ninguno (el endpoint es `AllowAny`).

**G-5 — OTP incorrecto:**
```
POST /api/v1/auth/2fa/verify/
Content-Type: application/json

{
  "session_token": "<session_token_del_paso_anterior>",
  "otp_code": "000000"
}
```
**Respuesta esperada (`401`):**
```json
{
  "detalle": "El código OTP no es válido.",
  "code": "OTP_INVALIDO"
}
```

**G-6 — OTP correcto:**
```
POST /api/v1/auth/2fa/verify/
Content-Type: application/json

{
  "session_token": "<session_token>",
  "otp_code": "654321"
}
```
(Código actual de la app autenticadora.)

**Respuesta esperada (`200`, JWT completo):**
```json
{
  "access": "<access_jwt>",
  "refresh": "<refresh_jwt>",
  "access_token": "<access_jwt>",
  "token_type": "bearer",
  "nombre": "Admin RENADS",
  "grupos": ["Administrador RENADS"],
  "es_superusuario": true,
  "debe_cambiar_password": false
}
```

---

### G-4 — Session token expirado devuelve SESSION_EXPIRADA

Esperar 5 minutos desde que se obtuvo el `session_token` (o construir un token expirado manualmente) y llamar a `verify/`:

```
POST /api/v1/auth/2fa/verify/
Content-Type: application/json

{
  "session_token": "<token_expirado>",
  "otp_code": "123456"
}
```

**Respuesta esperada (`401`):**
```json
{
  "detail": "La sesión de verificación ha expirado. Inicia sesión nuevamente.",
  "code": "SESSION_EXPIRADA"
}
```

---

### G-9 — Activar 2FA por email

Primero desactivar el TOTP (ver G-11 abajo) o usar un usuario sin 2FA activo.

```
POST /api/v1/auth/2fa/setup/email/
Authorization: Bearer <access_jwt>
Content-Type: application/json

{
  "password": "mi_contraseña"
}
```

**Respuesta esperada (`200`):**
```json
{
  "detalle": "Autenticación por correo electrónico activada correctamente."
}
```

**Caso de fallo:** contraseña incorrecta → `400`:
```json
{
  "La contraseña no es correcta."
}
```

---

### G-3 — Login con 2FA-EMAIL activo: OTP enviado al correo

Hacer login con un usuario que tiene 2FA-EMAIL activo:

```
POST /api/v1/auth/token/
Content-Type: application/json

{
  "username": "usuario",
  "password": "mi_contraseña"
}
```

**Respuesta esperada (`200`):**
```json
{
  "requires_2fa": true,
  "session_token": "<jwt_corto>",
  "method": "EMAIL"
}
```

En la **consola de Django** (con `EMAIL_BACKEND=console`) debe aparecer un mensaje con el asunto `"Código de verificación RENADS"` y el código de 6 dígitos en el cuerpo.

---

### G-10 — Rate-limit de reenvío OTP (429)

Inmediatamente después del login con 2FA-EMAIL (el OTP ya fue enviado), intentar reenviar:

```
POST /api/v1/auth/2fa/resend-otp/
Content-Type: application/json

{
  "session_token": "<session_token>"
}
```

**Respuesta esperada (`429`, dentro del primer minuto):**
```json
{
  "detalle": "Debes esperar al menos 1 minuto antes de solicitar un nuevo código."
}
```

Esperar 1 minuto y repetir la llamada — debe devolver `200`:
```json
{
  "detalle": "Código reenviado al correo registrado."
}
```

**Caso de fallo — método no EMAIL:**
Si el usuario tiene 2FA-TOTP activo y se intenta reenviar, esperar `400`:
```json
{
  "detalle": "El reenvío de OTP solo aplica para el método EMAIL."
}
```

---

### G-11 — Desactivar 2FA

**Rol requerido:** usuario autenticado con JWT válido y 2FA activo.

**Sub-caso A: método TOTP**

```
DELETE /api/v1/auth/2fa/disable/
Authorization: Bearer <access_jwt>
Content-Type: application/json

{
  "password": "mi_contraseña",
  "otp_code": "123456"
}
```
(Código actual de la app autenticadora.)

**Respuesta esperada (`200`):**
```json
{
  "detalle": "Doble factor desactivado."
}
```

**Sub-caso B: método EMAIL (flujo de dos pasos)**

Primer `DELETE` sin OTP previo — el sistema lo genera y envía:
```
DELETE /api/v1/auth/2fa/disable/
Authorization: Bearer <access_jwt>
Content-Type: application/json

{
  "password": "mi_contraseña",
  "otp_code": ""
}
```
**Respuesta esperada (`200`, instrucción de reenviar con código):**
```json
{
  "detalle": "Se ha enviado un código de verificación a tu correo. Reenvía esta petición incluyendo el código recibido."
}
```

Segundo `DELETE` con el código recibido:
```
DELETE /api/v1/auth/2fa/disable/
Authorization: Bearer <access_jwt>
Content-Type: application/json

{
  "password": "mi_contraseña",
  "otp_code": "456789"
}
```
**Respuesta esperada (`200`):**
```json
{
  "detalle": "Doble factor desactivado."
}
```

**Caso de fallo — 2FA ya inactivo:**
```
DELETE /api/v1/auth/2fa/disable/
Authorization: Bearer <access_jwt>
Content-Type: application/json

{
  "password": "mi_contraseña",
  "otp_code": "123456"
}
```
**Respuesta esperada (`400`):**
```json
{
  "detalle": "El doble factor no está activo."
}
```

---

### G-12 — totp_secret y otp_code no aparecen en ninguna respuesta

Verificar manualmente que ninguno de los endpoints (verify, setup/totp, confirm-totp, setup/email, resend-otp, disable) devuelve los campos `totp_secret` ni `otp_code` (hash SHA-256) en su respuesta JSON.

---

### G-13 — Migración reversible

```
python manage.py migrate common 0001_initial
```
Debe revertir 0002 y 0003 sin error, eliminando las cinco columnas 2FA de `seguridad_usuario`.

Para volver a aplicar:
```
python manage.py migrate common
```

---

### G-14 — Auditoría registrada

Tras activar TOTP (G-8), activar EMAIL (G-9) y desactivar (G-11), verificar en la tabla `bitacora_auditoria` (o en el admin de Django en `/admin/`) que existen filas con:

| `accion` | Cuándo se genera |
|---|---|
| `ACTIVAR_2FA_TOTP` | Tras `POST /auth/2fa/confirm-totp/` exitoso |
| `ACTIVAR_2FA_EMAIL` | Tras `POST /auth/2fa/setup/email/` exitoso |
| `DESACTIVAR_2FA` | Tras `DELETE /auth/2fa/disable/` exitoso |

Cada fila debe tener `tipo_contenido` apuntando al modelo `UserSecurity` y `id_objeto` con el PK del registro de seguridad del usuario.

---

## 4. Resumen de permisos por endpoint

| Endpoint | Método | Permission class | Requiere |
|---|---|---|---|
| `/api/v1/auth/token/` | POST | `AllowAny` (SimpleJWT) | Credenciales usuario/contraseña |
| `/api/v1/auth/2fa/verify/` | POST | `AllowAny` | `session_token` + `otp_code` |
| `/api/v1/auth/2fa/setup/totp/` | POST | `IsAuthenticated` | JWT válido |
| `/api/v1/auth/2fa/confirm-totp/` | POST | `IsAuthenticated` | JWT válido + código TOTP |
| `/api/v1/auth/2fa/setup/email/` | POST | `IsAuthenticated` | JWT válido + contraseña |
| `/api/v1/auth/2fa/resend-otp/` | POST | `AllowAny` | `session_token` |
| `/api/v1/auth/2fa/disable/` | DELETE | `IsAuthenticated` | JWT válido + contraseña + OTP |
