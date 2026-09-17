"""Configuración Docker — PostgreSQL local vía docker-compose."""

import dj_database_url
from decouple import config

from .base import *  # noqa: F401,F403

DEBUG = True

DATABASES = {
    "default": dj_database_url.config(
        default=config(
            "DATABASE_URL",
            default="postgresql://renads:renads@db:5432/renads",
        )
    )
}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
]

EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
