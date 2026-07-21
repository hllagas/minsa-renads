"""Configuración de desarrollo (SQLite)."""

from .base import BASE_DIR, INSTALLED_APPS  # noqa: F401
from .base import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Correo — en desarrollo se imprime en la consola (RN-22).
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CORS — solo para desarrollo local
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Almacenamiento documental (GCS):
# Por defecto GCS_ENABLED=False → se usa el stub por referencia externa.
# Para probar GCS real en desarrollo, definir en .env:
#   GCS_ENABLED=True
#   GCS_BUCKET_NAME=renads-cloud-media-dev
# y autenticarse con ADC: `gcloud auth application-default login` (auth keyless,
# sin claves de SA). Ver config/settings/base.py y .env.example.
