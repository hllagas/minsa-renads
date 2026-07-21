"""Configuración común a todos los entornos (RENADS API)."""

from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

# Raíz del proyecto: config/settings/base.py -> config/ -> raíz
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Seguridad — valores sensibles desde el entorno (.env / variables de Railway)
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=Csv())


# Aplicaciones
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceros
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "django_filters",
    # RENADS
    "apps.common",
    "apps.convenios",
    "apps.internados",
    "apps.actividades",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# Validación de contraseñas
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internacionalización
LANGUAGE_CODE = "es"
TIME_ZONE = "America/Lima"
USE_I18N = True
USE_TZ = True


# Archivos estáticos
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": config("PAGE_SIZE", default=20, cast=int),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}


# JWT (djangorestframework-simplejwt)
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=config("JWT_ACCESS_MINUTES", default=60, cast=int)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=config("JWT_REFRESH_DAYS", default=1, cast=int)
    ),
    "ROTATE_REFRESH_TOKENS": True,
}


# ---------------------------------------------------------------------------
# Almacenamiento documental — Google Cloud Storage (RNF-DOC-01/02/03)
# ---------------------------------------------------------------------------
# Autenticación KEYLESS: ADC (Application Default Credentials) + impersonación de
# la service account de firma vía IAM SignBlob. NO se usan claves JSON de SA (la
# política de organización bloquea su creación). El principal ADC debe tener
# `roles/iam.serviceAccountTokenCreator` sobre `GCS_SIGNING_SA`.
#
# Con `GCS_ENABLED=False` (default) el sistema usa el stub por referencia externa
# (`ReferenciaExternaStorage`), sin contactar ningún backend.
GCS_ENABLED = config("GCS_ENABLED", default=False, cast=bool)
GCS_PROJECT_ID = config("GCS_PROJECT_ID", default="renads-cloud")
# Bucket del entorno (obligatorio si GCS_ENABLED). dev: renads-cloud-media-dev,
# prod: renads-cloud-media-prod. Se define por .env, nunca se hardcodea aquí.
GCS_BUCKET_NAME = config("GCS_BUCKET_NAME", default="")
# SA objetivo de la impersonación: firma los signed URLs V4 vía IAM SignBlob.
GCS_SIGNING_SA = config(
    "GCS_SIGNING_SA",
    default="renads-storage@renads-cloud.iam.gserviceaccount.com",
)
# Prefijo/carpeta opcional para organizar las keys de los objetos.
GCS_OBJECT_PREFIX = config("GCS_OBJECT_PREFIX", default="")
# Vigencia del signed URL de descarga, en segundos (default 15 minutos).
GCS_SIGNED_URL_EXPIRATION = config("GCS_SIGNED_URL_EXPIRATION", default=900, cast=int)
# Tamaño máximo de subida, en bytes (default 25 MiB).
GCS_MAX_UPLOAD_BYTES = config("GCS_MAX_UPLOAD_BYTES", default=26214400, cast=int)
# Content-types permitidos para subida (PDF e imágenes). Lista fija, no parametrizable.
GCS_ALLOWED_CONTENT_TYPES = [
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
]


# ---------------------------------------------------------------------------
# Correo electrónico (notificaciones — RN-22 onboarding del interno)
# ---------------------------------------------------------------------------
# Backend por defecto: consola (dev lo confirma; prod lo sobreescribe con SMTP).
EMAIL_BACKEND = config(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="no-reply@renads.minsa.gob.pe")


# OpenAPI (drf-spectacular)
SPECTACULAR_SETTINGS = {
    "TITLE": "RENADS API",
    "DESCRIPTION": "Registro Nacional de Articulación Docencia-Servicio en Salud",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
