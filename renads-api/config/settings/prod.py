"""Configuración de producción (PostgreSQL en Railway)."""

import dj_database_url
from decouple import Csv, config

from .base import *  # noqa: F401,F403

# En producción DEBUG siempre desactivado (no depende del entorno)
DEBUG = False

# Base de datos desde DATABASE_URL (Railway PostgreSQL)
DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True,
    )
}

# Orígenes confiables para CSRF (dominios de Railway)
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

# CORS — orígenes del frontend autorizados (dominio del frontend en producción)
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="", cast=Csv())

# WhiteNoise para servir estáticos en producción
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

# Almacenamiento documental (GCS):
# En producción se prevé GCS_ENABLED=True. El bucket y el flag se definen por
# variables de entorno (no se hardcodean aquí):
#   GCS_ENABLED=True
#   GCS_BUCKET_NAME=renads-cloud-media-prod
# Autenticación keyless: el runtime (Cloud Run / Railway) debe correr con ADC del
# principal que tenga `roles/iam.serviceAccountTokenCreator` sobre GCS_SIGNING_SA.

# Correo — SMTP en producción (credenciales por .env). Ver config/settings/base.py.
EMAIL_BACKEND = config(
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)

# Endurecimiento de seguridad
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
