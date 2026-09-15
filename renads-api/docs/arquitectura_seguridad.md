# RENADS — Arquitectura del Sistema y Seguridad

> Documento de referencia técnica para el equipo de desarrollo.  
> Cubre: arquitectura de capas (backend + frontend), librerías, patrones de diseño y características de seguridad implementadas.

---

## 1. Visión general del sistema

**RENADS** (Registro Nacional de Articulación Docencia-Servicio en Salud) es una plataforma del MINSA Perú que gestiona convenios, internados, actividades docente-asistenciales y calendario administrativo.

| Componente | Tecnología | Versión |
|---|---|---|
| API Backend | Django + Django REST Framework | 6.0.6 / 3.17.1 |
| Lenguaje Backend | Python | 3.14 |
| Frontend | Next.js + React + TypeScript | 16.2.9 / 19.2.4 / 5 |
| Base de datos (dev) | SQLite | — |
| Base de datos (prod) | PostgreSQL (Railway) | `psycopg2-binary 2.9.12` |
| Servidor producción | Gunicorn + WhiteNoise | 26.0.0 / 6.12.0 |

---

## 2. Arquitectura del Backend (Django)

### 2.1 Estructura de capas

El backend sigue una arquitectura de **capas explícitas** dentro de cada app Django:

```
config/
├── settings/
│   ├── base.py      ← Configuración común (INSTALLED_APPS, JWT, DRF, storages)
│   ├── dev.py       ← SQLite + consola email + CORS localhost
│   └── prod.py      ← PostgreSQL + SMTP + HTTPS forzado + CORS whitelist
├── urls.py          ← Raíz: /admin/ + /api/v1/
└── api_urls.py      ← Router con todos los endpoints REST

apps/
├── common/          ← Foundation: auth, 2FA, usuarios, auditoría, documentos
├── convenios/       ← Módulo 1: convenios, campos clínicos, órganos
├── internados/      ← Módulo 2: internados, estudiantes, tutores, rotaciones
├── actividades/     ← Módulo 3: actividades docente-asistenciales
└── calendario/      ← Módulo 4: ventanas temporales de acceso
```

**Capas por app (patrón uniforme):**

| Capa | Archivo | Responsabilidad |
|---|---|---|
| Modelos | `models.py` | Tablas, relaciones, constraints |
| Selectores | `selectors.py` | Consultas de lectura reutilizables (sin efectos secundarios) |
| Servicios | `services.py` | Lógica de negocio atómica (writes + validaciones) |
| Serializadores | `serializers.py` | Transformación y validación de datos de entrada/salida |
| Permisos | `permissions.py` | Clases de autorización DRF |
| Vistas | `views.py` | ViewSets + APIViews (HTTP, no lógica de negocio) |
| URLs | `urls.py` | Registro de rutas |

> **Regla del proyecto:** las vistas no contienen lógica de negocio. Toda regla de negocio vive en `services.py`. Las consultas de solo lectura reutilizables viven en `selectors.py`.

### 2.2 Stack de dependencias backend

**Autenticación y seguridad:**
- `djangorestframework-simplejwt 5.5.1` — tokens JWT (access + refresh, rotación activa)
- `pyotp 2.9.0` — TOTP para Google/Microsoft Authenticator, Authy
- `qrcode 8.0` — generación de URI QR para setup TOTP

**Documentos y almacenamiento:**
- `boto3 1.43.86` — cliente Cloudflare R2 (S3-compatible)
- `django-storages 1.14.6` — backends GCS + S3 para `ImageField`
- `google-cloud-storage 3.13.0` — cliente GCS (legacy, fallback)
- `docxtpl 0.20.2` — relleno de plantillas Word para PDFs de convenios
- `pypdf 6.14.2` — merge de PDFs (expediente)
- `openpyxl 3.1.5` — parsing Excel para carga masiva de estudiantes

**API y filtros:**
- `drf-spectacular 0.29.1` — schema OpenAPI 3.0 + Swagger UI + ReDoc
- `django-filter 25.2` — filtros por querystring (DjangoFilterBackend)
- `django-cors-headers 4.9.0` — gestión de CORS

**OCR (best-effort):**
- `google-cloud-documentai 3.6.0` — extracción de texto de PDFs post-upload

**Infraestructura:**
- `psycopg2-binary 2.9.12` — driver PostgreSQL
- `dj-database-url 3.1.2` — parser DATABASE_URL (Railway)
- `gunicorn 26.0.0` — servidor WSGI producción
- `whitenoise 6.12.0` — static files comprimidos + seguros
- `Pillow 11.3.0` — validación de imágenes (logos)
- `python-decouple 3.8` — lectura de `.env`

### 2.3 Stack de middleware

```python
MIDDLEWARE = [
    "whitenoise.middleware.WhiteNoiseMiddleware",      # prod: static files
    "django.middleware.security.SecurityMiddleware",   # X-Frame-Options, etc.
    "corsheaders.middleware.CorsMiddleware",           # CORS (antes de Session)
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

### 2.4 Módulos del dominio

#### `apps.common` — Fundación transversal

| Modelo | Tabla | Responsabilidad |
|---|---|---|
| `UserSecurity` | `seguridad_usuario` | Flags 2FA, OTP hash, TTL, secret TOTP, `password_changed_at`, `debe_cambiar_password` |
| `UserProfile` | `perfil_usuario` | Apellidos, DNI único, teléfono único, cargo, unidad orgánica |
| `UserEntityProfile` | `perfil_usuario_entidad` | Scope multitenant: usuario ↔ entidad institucional |
| `AuditLog` | `bitacora_auditoria` | Trazabilidad de todas las operaciones críticas |
| `Document` | `documento` | Versionado de adjuntos por `(objeto, documento_anexo)` |

**Servicios clave:**
- `generar_password_segura()` — 12 chars, `secrets`, sin `random`
- `generar_otp_email()` / `validar_otp_email()` — OTP hash SHA-256, timing-safe
- `generar_session_token()` / `validar_session_token()` — JWT efímero 5 min scope `2fa_pending`
- `activar_2fa_totp()` / `activar_2fa_email()` / `desactivar_2fa()` — doble verificación
- `solicitar_reset_password()` / `confirmar_reset_password()` — flujo OTP por correo
- `crear_usuario_con_perfil()` — onboarding con contraseña temporal
- `registrar_auditoria()` — fuente única de escritura al `AuditLog`

#### `apps.convenios` — Módulo 1

Gestión del ciclo de vida de Convenios Marco y Específicos: documentos, evaluaciones (DIGEP, CONAPRES, OGAJ), firmas, publicación, vigencia. Subcampos clínicos, partes firmantes, generación de PDF vía plantillas Word + LibreOffice headless.

**Modelos principales (32):** `Convention`, `ConventionParty`, `ClinicalFieldRegistration`, `ClinicalFieldAllocation`, `OrganDirectory`, `OrganRepresentative`, `ExecutingUnit`, `University`, `Faculty`, `Ipress` (PK = `codigo_renipress` varchar 8).

**Reglas de negocio críticas:** estado avanza solo hacia adelante (`_avanzar_estado` idempotente), nomenclatura asignada por DIGEP, composición de partes por tipo/categoría, disponibilidad de campos clínicos calculada en tiempo real.

#### `apps.internados` — Módulo 2

Registro individual y masivo (Excel) de internados. Modelos: `Internship`, `Student`, `Tutor`, `Rotation`. Reglas: unicidad de internado vigente por DNI (RN-21), onboarding automático de usuario (RN-22), declaraciones juradas (RN-23), tope de universidades por tutor (RN-24).

#### `apps.actividades` — Módulo 3

Actividades docente-asistenciales asociadas a: estudiante + sede + rotación + tutor. Gestionadas vía `TeachingActivityViewSet`.

#### `apps.calendario` — Módulo 4

Gobernanza temporal de escritura. Una `CalendarActivity` con `controla_acceso=True` habilita o bloquea los modelos que referencia por M2M `content_types`. Selectores: `esta_habilitado(ct_id, now)`, `content_types_habilitados(now)`.

### 2.5 Almacenamiento

**Precedencia:** R2 (Cloudflare) > GCS (Google) > FileSystemStorage

| Backend | Uso | Autenticación |
|---|---|---|
| Cloudflare R2 (`boto3`) | PDFs de documentos adjuntos | `R2_ACCESS_KEY_ID` + `R2_SECRET_ACCESS_KEY` (env) |
| Google Cloud Storage | Logos `ImageField` (legacy) | Keyless ADC + impersonación IAM `SignBlob` |
| FileSystemStorage | Dev sin configuración externa | N/A |

- **Presigned URLs:** expiran en 900 s (15 min)
- **Tamaño máximo:** 25 MiB por archivo
- **Tipos permitidos:** `application/pdf`, `image/png`, `image/jpeg`, `image/webp`
- **Buckets privados:** sin ACL pública; solo acceso por URL firmada

---

## 3. Arquitectura del Frontend (Next.js)

### 3.1 Stack de tecnologías

**Framework y core:**
- `Next.js 16.2.9` — App Router (RSC + Client Components)
- `React 19.2.4` — renderizado con nuevas características (concurrent)
- `TypeScript 5` — tipado estricto, `moduleResolution: bundler`, alias `@/*`

**Estado y datos:**
- `zustand ^5.0.14` — estado de sesión (access token, refresh token, user, 2FA pending)
- `@tanstack/react-query ^5.101.1` — cache de datos del servidor, refetch automático
- `@tanstack/react-table ^8.21.3` — tablas de datos con ordenamiento, filtros y paginación
- `axios ^1.18.1` — cliente HTTP con interceptores JWT

**Formularios y validación:**
- `react-hook-form ^7.80.0` — estado de formularios sin rerenders innecesarios
- `@hookform/resolvers ^5.4.0` — adaptadores de esquema (Zod)
- `zod ^4.4.3` — validación de esquemas en runtime

**UI y componentes:**
- `@base-ui/react ^1.6.0` — componentes headless (accesibilidad)
- `shadcn ^4.11.0` — sistema de componentes sobre Base UI (embedded en `/components/ui/`)
- `lucide-react ^1.21.0` — librería de iconos (240+)
- `recharts ^3.9.0` — gráficos composables (dashboard)
- `react-day-picker ^10.0.1` — selector de fechas
- `react-qr-code ^2.2.0` — generación de QR para setup TOTP

**Estilos:**
- `tailwindcss ^4` — utility-first CSS (JIT)
- `class-variance-authority ^0.7.1` — variantes de componentes (CVA)
- `tailwind-merge ^3.6.0` — resolución de conflictos de clases
- `clsx ^2.1.1` — utilidad de classNames

**UX:**
- `framer-motion ^12.42.0` — animaciones y transiciones
- `sonner ^2.0.7` — notificaciones toast
- `next-themes ^0.4.6` — modo claro/oscuro (preferencia del sistema + toggle manual)
- `date-fns ^4.4.0` — manipulación de fechas

**Dev tools:**
- `openapi-typescript ^7.13.0` — generación de tipos TypeScript desde el schema OpenAPI del backend
- `@tanstack/react-query-devtools ^5.101.1` — inspector de caché (solo dev)

### 3.2 Estructura de rutas (App Router)

```
app/
├── (auth)/                     ← Rutas públicas (sin token requerido)
│   └── login/
│       ├── page.tsx            ← Login + recuperar contraseña (3 vistas)
│       └── 2fa/page.tsx        ← Verificación OTP/TOTP
│
├── (app)/                      ← Rutas protegidas (token requerido)
│   ├── layout.tsx              ← Guard: hydration + token check + useMe()
│   ├── inicio/page.tsx
│   ├── dashboard/page.tsx
│   ├── perfil/page.tsx         ← Gestión de 2FA, cambio de contraseña
│   ├── convenios/              ← Módulo 1 (CRUD + detalle + campos clínicos)
│   │   ├── page.tsx
│   │   ├── nuevo/page.tsx
│   │   ├── [id]/page.tsx
│   │   ├── [id]/editar/page.tsx
│   │   └── maestros/
│   ├── internados/             ← Módulo 2 (CRUD + carga masiva)
│   │   ├── page.tsx
│   │   ├── nuevo/page.tsx
│   │   ├── [id]/page.tsx
│   │   ├── internos/page.tsx
│   │   └── personas/
│   ├── actividades/            ← Módulo 3 (CRUD)
│   ├── campos-clinicos/        ← Registros CONAPRES + Asignaciones regionales
│   │   ├── registros/page.tsx
│   │   └── asignaciones/page.tsx
│   ├── calendario/page.tsx     ← Ventanas temporales (Administrador RENADS)
│   ├── catalogos/              ← CRUD catálogos + representantes + auditoría
│   │   ├── listas/[catalogo]/
│   │   ├── entidades/
│   │   ├── representantes/
│   │   ├── documentos/
│   │   └── auditoria/page.tsx
│   └── usuarios/               ← Cuentas + roles + perfiles institucionales
│       ├── page.tsx
│       ├── cuentas/
│       ├── roles/
│       ├── perfiles/
│       └── permisos/
│
├── layout.tsx                  ← Root layout (providers, fuentes)
├── page.tsx                    ← Redirect a /inicio o /login
└── providers.tsx               ← TanStack Query + next-themes
```

### 3.3 Gestión de estado

**Zustand (estado de cliente):**
```typescript
interface AuthState {
  accessToken: string | null;    // persisted en localStorage
  refreshToken: string | null;   // persisted en localStorage
  user: AuthUser | null;         // NO persisted (recargado de /auth/me/)
  pendingTwoFactor: {            // NO persisted (transitorio)
    sessionToken: string;
    method: "TOTP" | "EMAIL";
  } | null;
}
```

**TanStack Query v5 (estado de servidor):**
- Caché por `queryKey` (ej. `["conventions", id]`, `["auth", "me"]`)
- `staleTime: 60s`, `retry: 1` (no reintenta en 4xx), `refetchOnWindowFocus: false`
- Invalidación explícita tras mutations (ej. después de cambiar 2FA → invalida `meQueryKey`)

**React Hook Form (estado de formularios):**
- Instancia por formulario, sin estado global
- Validación Zod + mensajes de error en español

### 3.4 Cliente HTTP (Axios)

**Base URL:** `process.env.NEXT_PUBLIC_API_BASE_URL` (default: `http://localhost:8000/api/v1`)

**Interceptor de request:**
```typescript
config.headers.Authorization = `Bearer ${accessToken}`; // desde Zustand
```

**Interceptor de response (401):**
1. Detecta 401 en rutas no-auth
2. Deduplica llamadas concurrentes a `/auth/token/refresh/` (promise compartida)
3. Si falla el refresh → limpia sesión + redirige a `/login`
4. Si tiene éxito → reintenta la request original (1 vez) con nuevo access token

---

## 4. Seguridad del Sistema

### 4.1 Autenticación — Flujo JWT completo

```
Cliente                    Backend
  │                           │
  ├──POST /auth/token/────────►│  username + password
  │                           │  check 2FA flag
  │                           │
  │◄── { requires_2fa: false, │  ← Sin 2FA: JWT completo
  │      access, refresh }    │
  │                           │
  │  ─── O con 2FA ───        │
  │◄── { requires_2fa: true,  │  ← Con 2FA: session_token (5 min, scope=2fa_pending)
  │      session_token,       │     método: TOTP o EMAIL
  │      method }             │     (EMAIL → envía OTP por correo en este punto)
  │                           │
  ├──POST /auth/2fa/verify/───►│  session_token + otp_code
  │                           │  validar_session_token() → scope check
  │                           │  validar_otp_email() o pyotp.TOTP.verify()
  │◄── { access, refresh }────│  JWT completo
  │                           │
  ├──GET /api/v1/... ─────────►│  Authorization: Bearer {access}
  │                           │  JWTAuthentication → User
```

**Claims del JWT:**
```json
{
  "user_id": 1,
  "username": "jperez",
  "nombre": "Pérez García, Juan",
  "grupos": ["Administrador RENADS"],
  "es_superusuario": false,
  "debe_cambiar_password": false
}
```

### 4.2 Autorización — 4 capas

| Capa | Mecanismo | Donde |
|---|---|---|
| **Autenticación** | `IsAuthenticated` (default DRF) | Todas las vistas |
| **Rol** | `IsSuperUser`, grupos Django | Gestión de usuarios/roles |
| **Scope institucional** | `HasEntityScope` + `UserEntityProfile` | Objetos por entidad |
| **Ventana temporal** | `IsModuleEnabled` + `CalendarActivity` | Convenios, Internados, Actividades |

**`IsSuperUser`:** solo `is_superuser=True` puede gestionar usuarios, roles y permisos.

**`HasEntityScope`:** cada ViewSet implementa `get_entity_reference(obj) → (ct_id, id_objeto_str)`. El permiso compara con `entidades_del_usuario(request.user)`. El `id_objeto` siempre se normaliza a `str` (FK de IPRESS es `varchar(8)`; otras FKs enteras se castean).

**`IsModuleEnabled`:**
- Opt-in por vista: atributo `module_content_type = ("app_label", "model")`
- Solo bloquea escritura (GET/HEAD/OPTIONS siempre libres)
- Exentos **únicamente**: superusuario + rol `Administrador RENADS`
- Respuesta fuera de ventana: `HTTP 403`, `code = "MODULO_FUERA_DE_VENTANA"`

### 4.3 Doble Factor (2FA / MFA)

#### Métodos disponibles

| Método | Librería | Storage del secreto | TTL |
|---|---|---|---|
| **TOTP** | `pyotp 2.9.0` | `totp_secret` (base32, nunca serializado) | 30 s por código |
| **Email OTP** | `django.core.mail` | `otp_code` (hash SHA-256, nunca en claro) | 10 min |

#### Configuración global

```python
FORCE_EMAIL_2FA = config("FORCE_EMAIL_2FA", default=True, cast=bool)
OTP_TTL_MINUTES = config("OTP_TTL_MINUTES", default=10, cast=int)
TOTP_ISSUER_NAME = config("TOTP_ISSUER_NAME", default="RENADS")
```

Con `FORCE_EMAIL_2FA=True` (default), **todos los usuarios** deben pasar OTP por correo al iniciar sesión, independientemente de su configuración individual.

#### Flujo de setup TOTP

```
POST /auth/2fa/setup/totp/     → { secret, otpauth_uri }  (QR en frontend)
POST /auth/2fa/confirm-totp/   → { otp_code }             → activa 2FA
```

#### Flujo de setup Email OTP

```
POST /auth/2fa/setup/email/    → { password }             → activa 2FA + envía OTP de prueba
```

#### Desactivar 2FA (doble verificación)

```
POST /auth/2fa/disable/        → { password, otp_code }   → verifica ambos antes de desactivar
```

#### Propiedades de seguridad del OTP

| Propiedad | Implementación |
|---|---|
| Almacenamiento | Hash SHA-256 en BD, nunca el código en claro |
| Comparación | `hmac.compare_digest()` — resistente a timing attacks |
| Generación | `secrets.token_hex()` — criptográficamente seguro |
| Rate-limit reenvío | Mínimo 1 min entre reenvíos → `HTTP 429` |
| Expiración | 10 min (configurable), campo `otp_expires_at` |

### 4.4 Gestión de contraseñas

#### Caducidad

```python
PASSWORD_EXPIRY_DAYS = config("PASSWORD_EXPIRY_DAYS", default=90, cast=int)
```

- Al hacer login, si `password_changed_at` es `NULL` o tiene más de 90 días → `HTTP 401`, `code = "PASSWORD_EXPIRADO"`
- El mensaje orienta al usuario a usar recuperar contraseña
- Superusuario **exento** de la caducidad
- Gate aplicado **antes** del flujo 2FA

#### Validadores Django activos

```python
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "...UserAttributeSimilarityValidator"},  # no parecida a username/nombre
    {"NAME": "...MinimumLengthValidator"},            # mínimo 8 caracteres
    {"NAME": "...CommonPasswordValidator"},           # lista de contraseñas comunes
    {"NAME": "...NumericPasswordValidator"},          # no solo numérica
]
```

#### Generador seguro (`generar_password_segura()`)

- 12 caracteres mínimo
- Garantiza: 1 minúscula + 1 mayúscula + 1 dígito + 2 especiales (`!@#$%^&*`)
- Shuffle con `secrets.SystemRandom()` (nunca `random.shuffle`)
- Usada en `crear_usuario_con_perfil()` (onboarding) y por el administrador en reset

#### Flujo de recuperación (forgot password)

```
POST /auth/password-reset/request/   → { username }
    → busca usuario silenciosamente (no revela si existe)
    → verifica rate-limit (1 min) antes de enviar
    → genera OTP por email
    → siempre retorna HTTP 200

POST /auth/password-reset/confirm/   → { username, otp_code, password_nueva }
    → valida OTP
    → valida nueva contraseña con Django validators
    → atómico: set_password + password_changed_at=now() + debe_cambiar_password=False
    → registra en AuditLog
```

#### Cambio de contraseña (`/auth/me/cambiar-password/`)

- Requiere contraseña actual
- Registra `password_changed_at = timezone.now()`
- Limpia `debe_cambiar_password = False`
- Registra en AuditLog sin exponer el valor

### 4.5 Onboarding de usuario (RN-22)

Al registrar un internado se crea automáticamente el usuario del interno:

1. `username = numero_documento`, contraseña generada con `generar_password_segura()`
2. `debe_cambiar_password = True` — fuerza cambio en el primer login
3. Grupo asignado: `Interno` (acceso de solo lectura a sus datos)
4. `perfil_usuario_entidad` sobre su `Student` (scope restringido)
5. Flag `debe_cambiar_password` expuesto como claim JWT y en `GET /auth/me/`
6. Notificación por correo (best-effort, no bloquea si falla SMTP)

### 4.6 Campos únicos sensibles

| Campo | Tabla | Constraint |
|---|---|---|
| `numero_documento` | `perfil_usuario` | `UNIQUE`, `NULL` cuando ausente (NULL no viola UNIQUE) |
| `telefono` | `perfil_usuario` | `UNIQUE`, `NULL` cuando ausente |
| `email` | `auth_user` | `UNIQUE`, `NULL` cuando ausente (migración convierte `""` → `NULL`) |
| `numero_documento` | `estudiante` | `UNIQUE` |
| `codigo_renipress` | `ipress` | PK (varchar 8) |

### 4.7 Bitácora de auditoría

Tabla `bitacora_auditoria` (`AuditLog`):

| Campo | Tipo | Descripción |
|---|---|---|
| `usuario` | FK nullable | Quién realizó la operación |
| `accion` | varchar | `CREAR`, `ACTUALIZAR`, `ELIMINAR`, `CAMBIO_ESTADO`, `ACTIVAR_2FA_*`, etc. |
| `tipo_contenido` | FK ContentType | Modelo afectado |
| `id_objeto` | varchar 64 | PK del objeto (texto: RENIPRESS para IPRESS, `str(pk)` para el resto) |
| `nombre_campo` | varchar | Campo modificado (en updates) |
| `valor_anterior` | text | Valor previo |
| `valor_nuevo` | text | Valor nuevo |
| `direccion_ip` | varchar | IP del cliente (opcional) |
| `creado_en` | datetime | Timestamp UTC |

**Operaciones auditadas:** CRUD de usuarios/grupos/roles/perfiles, cambios de contraseña, activación/desactivación de 2FA, transiciones de estado de convenios e internados, adjuntos documentales (versionado), sincronización de partes firmantes.

### 4.8 Versionado de documentos

Tabla `documento` — chain de versiones por `(objeto GFK, documento_anexo FK)`:

```
v1 (ACTIVO)
  └── v2 (ACTIVO)  ← v1 pasa a REEMPLAZADO
        └── v3 (ACTIVO) ← v2 pasa a REEMPLAZADO
```

`adjuntar_documento()` es la única función que escribe documentos (fuente única); ejecuta en transacción atómica y registra en AuditLog.

### 4.9 Seguridad de transporte (producción)

```python
SECURE_SSL_REDIRECT = True               # Redirige HTTP → HTTPS
SECURE_PROXY_SSL_HEADER = (              # Confía en X-Forwarded-Proto (Railway)
    "HTTP_X_FORWARDED_PROTO", "https"
)
SESSION_COOKIE_SECURE = True             # Cookie de sesión solo por HTTPS
CSRF_COOKIE_SECURE = True                # Cookie CSRF solo por HTTPS
CORS_ALLOWED_ORIGINS = [...]             # Lista blanca explícita
CSRF_TRUSTED_ORIGINS = [...]             # Lista blanca para CSRF
```

### 4.10 Seguridad en el frontend

| Característica | Implementación |
|---|---|
| **Almacenamiento de tokens** | `localStorage` vía `zustand/persist` (access + refresh) |
| **Inyección del token** | Interceptor Axios en request (`Authorization: Bearer`) |
| **Refresh automático** | Interceptor 401 → refresh → retry (1 vez, deduplica concurrentes) |
| **Guard de rutas** | `app/(app)/layout.tsx` — espera hydration de Zustand antes de verificar token |
| **Guard cambio de contraseña** | `<ChangePasswordGate />` bloquea toda la app hasta completar cambio (RN-22) |
| **Gate de módulo** | `<ModuleGate />` — refleja `modulos_bloqueados` de `/auth/me/` |
| **Prevención de enumeración** | `/auth/password-reset/request/` siempre responde HTTP 200 |
| **2FA en login** | Estado `pendingTwoFactor` en Zustand (NO persiste en localStorage) |
| **QR TOTP** | Generado con `react-qr-code`, URI del backend, secreto nunca expuesto post-setup |
| **Validación de formularios** | Zod + React Hook Form (validación en cliente antes de enviar) |

---

## 5. Resumen de endpoints de seguridad

| Método | Endpoint | Acceso | Función |
|---|---|---|---|
| `POST` | `/auth/token/` | Público | Login → JWT o session_token 2FA |
| `POST` | `/auth/token/refresh/` | Público | Renovar access token |
| `GET` | `/auth/me/` | Autenticado | Usuario actual + módulos habilitados/bloqueados |
| `POST` | `/auth/me/cambiar-password/` | Autenticado | Cambio de contraseña con actual requerida |
| `POST` | `/auth/password-reset/request/` | Público | Solicitar OTP de recuperación |
| `POST` | `/auth/password-reset/confirm/` | Público | Confirmar reset con OTP + nueva contraseña |
| `POST` | `/auth/2fa/verify/` | session_token | Verificar OTP → JWT completo |
| `POST` | `/auth/2fa/setup/totp/` | Autenticado | Iniciar setup TOTP → secret + QR |
| `POST` | `/auth/2fa/confirm-totp/` | Autenticado | Activar TOTP tras verificar código |
| `POST` | `/auth/2fa/setup/email/` | Autenticado | Activar Email OTP con contraseña |
| `POST` | `/auth/2fa/resend-otp/` | session_token | Reenviar OTP (rate-limit 1 min) |
| `POST` | `/auth/2fa/disable/` | Autenticado | Desactivar 2FA (contraseña + OTP) |

---

## 6. Variables de entorno de seguridad

```bash
# Contraseñas y tokens
SECRET_KEY=...                        # Clave Django (HS256, no compartir)
JWT_ACCESS_MINUTES=60                 # Vida del access token
JWT_REFRESH_DAYS=1                    # Vida del refresh token

# 2FA y contraseñas
FORCE_EMAIL_2FA=True                  # Forzar OTP email a todos en login
OTP_TTL_MINUTES=10                    # Expiración OTP email
TOTP_ISSUER_NAME=RENADS               # Nombre en app autenticadora
PASSWORD_EXPIRY_DAYS=90               # Días antes de expirar contraseña

# Almacenamiento (nunca en código)
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...

# Email (SMTP)
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...               # App password de Gmail, no contraseña real

# Producción
SECURE_SSL_REDIRECT=True
CORS_ALLOWED_ORIGINS=https://renads.minsa.gob.pe
CSRF_TRUSTED_ORIGINS=https://renads.minsa.gob.pe
```

---

*Documento generado el 2026-09-15. Mantener sincronizado con cambios en `apps/common/`, `config/settings/` y `apps/*/permissions.py`.*
