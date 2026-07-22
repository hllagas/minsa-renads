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

# Almacenamiento de imágenes (ImageField de logos):
# La selección del backend vive en base.py y honra `GCS_ENABLED` también en dev.
# - GCS_ENABLED=False (default) → `FileSystemStorage`: los logos se guardan en
#   MEDIA_ROOT y `.url` devuelve una ruta relativa MEDIA_URL (no van a GCP).
# - GCS_ENABLED=True + GCS_BUCKET_NAME + ADC → django-storages sobre GCS: los logos
#   se suben al bucket privado y `.url` firma un signed URL V4 absoluto.
# Para guardar los logos EN GCP desde dev, definir en .env:
#   GCS_ENABLED=True
#   GCS_BUCKET_NAME=renads-cloud-media-dev   (o GS_BUCKET_NAME)
# y autenticarse: `gcloud auth application-default login` (keyless, sin claves SA).
