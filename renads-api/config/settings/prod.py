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

# Endurecimiento de seguridad
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
