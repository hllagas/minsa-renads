"""Configuración de desarrollo (SQLite)."""

from .base import BASE_DIR, INSTALLED_APPS  # noqa: F401
from .base import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# CORS — solo para desarrollo local
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
