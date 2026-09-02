"""Abstracción de almacenamiento documental (RNF-DOC-01/02/03).

Define la interfaz `DocumentStorage` (Protocol) y un stub de almacenamiento por
referencia externa. El stub NO contacta ningún backend real (S3/MinIO/etc.): el
cliente envía la clave/URL externa del archivo y aquí solo se gestiona esa
referencia. Sirve como punto de integración hasta conectar el repositorio real.
Ver `docs/arquitectura_desarrollo.md` §9.
"""

import logging
import re
from datetime import timedelta
from functools import lru_cache
from typing import Protocol
from uuid import uuid4

logger = logging.getLogger(__name__)


class DocumentStorage(Protocol):
    """Interfaz estructural de un backend de almacenamiento de documentos."""

    def subir(self, archivo, ruta: str) -> str:
        """Sube un archivo y devuelve la `referencia_externa` resultante."""
        ...

    def url_firmada(self, referencia: str) -> str:
        """Devuelve una URL de descarga (firmada) para la referencia indicada."""
        ...

    def eliminar(self, referencia: str) -> None:
        """Elimina el archivo asociado a la referencia indicada."""
        ...


class ReferenciaExternaStorage:
    """Stub de almacenamiento por referencia externa (sin backend real).

    Cumple estructuralmente el `Protocol` `DocumentStorage`. En este stub el
    cliente ya envía la `referencia_externa` (clave/URL del archivo en el
    repositorio externo), de modo que no se manejan binarios ni hay I/O de red.
    """

    def subir(self, archivo, ruta: str) -> str:
        """Devuelve la `ruta`/referencia recibida sin contactar ningún backend.

        En el stub el cliente ya gestiona la subida del binario al repositorio
        externo y nos envía la referencia; este método solo la propaga.
        """
        return ruta

    def url_firmada(self, referencia: str) -> str:
        """Devuelve la `referencia` tal cual (ya es una clave/URL externa).

        Es un stub: no firma criptográficamente la URL. Se reemplazará cuando se
        integre el repositorio documental real.
        """
        return referencia

    def eliminar(self, referencia: str) -> None:
        """No-op: no hay backend que contactar (stub hasta integrar el repositorio real)."""
        return None


def get_impersonated_credentials(signing_sa: str | None = None):
    """Construye credenciales impersonadas (keyless) de la SA de firma.

    Parte de las credenciales ADC (`google.auth.default`) y deriva credenciales
    impersonadas de la SA de firma con `impersonated_credentials.Credentials`.
    Estas credenciales obtienen tokens efímeros y firman los signed URLs V4 vía el
    endpoint IAM SignBlob, sin necesidad de una clave JSON de service account.

    `signing_sa` es el email de la SA objetivo. Si es `None` (uso en runtime) se
    lee de `settings.GCS_SIGNING_SA`. **En tiempo de import de los settings** (p.
    ej. al construir `STORAGES` en `config/settings/base.py`) hay que pasarlo
    EXPLÍCITO: `django.conf.settings` aún no está poblado durante ese import y
    acceder a él lanzaría `AttributeError`.

    Se centraliza aquí para reutilizarla tanto en el backend documental custom
    (`GoogleCloudStorage._get_bucket`) como en el backend de imágenes
    `storages.backends.gcloud.GoogleCloudStorage` de django-storages (que recibe
    estas credenciales vía `credentials`/`GS_CREDENTIALS` para poder firmar `.url`).

    Levanta `RuntimeError` con mensaje en español si faltan las librerías o las
    credenciales ADC.
    """
    if signing_sa is None:
        from django.conf import settings

        signing_sa = settings.GCS_SIGNING_SA

    try:
        import google.auth
        from google.auth import impersonated_credentials
    except ImportError as exc:  # pragma: no cover - dependencia obligatoria
        raise RuntimeError(
            "La librería google-auth no está instalada; "
            "no es posible construir las credenciales impersonadas de Google Cloud."
        ) from exc

    try:
        credenciales_base, _ = google.auth.default()
    except Exception as exc:
        raise RuntimeError(
            "No se encontraron credenciales de Google Cloud (ADC). "
            "Ejecute `gcloud auth application-default login` o configure el "
            "runtime con una identidad autorizada."
        ) from exc

    return impersonated_credentials.Credentials(
        source_credentials=credenciales_base,
        target_principal=signing_sa,
        target_scopes=["https://www.googleapis.com/auth/devstorage.read_write"],
    )


def _nombre_seguro(nombre: str) -> str:
    """Sanea un nombre de archivo para usarlo como parte de una key de objeto.

    Elimina separadores de ruta y caracteres problemáticos, evitando que el
    cliente pueda inyectar rutas (`../`) o prefijos arbitrarios en el bucket.
    """
    base = (nombre or "").strip().replace("\\", "/").split("/")[-1]
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    base = base.strip("._") or "archivo"
    return base[:120]


class GoogleCloudStorage:
    """Backend de almacenamiento documental sobre Google Cloud Storage (GCS).

    Cumple estructuralmente el `Protocol` `DocumentStorage`. Los objetos se
    guardan en un bucket privado (UBLA + Public Access Prevention enforced): la
    única vía de lectura es un signed URL V4 de corta duración.

    Autenticación KEYLESS (sin claves de service account):
    - Se parte de las credenciales ADC (`google.auth.default`).
    - Se derivan credenciales impersonadas de la SA de firma
      (`settings.GCS_SIGNING_SA`) con `impersonated_credentials.Credentials`.
      Estas credenciales obtienen tokens efímeros y firman los signed URLs V4
      vía el endpoint IAM SignBlob, sin necesidad de una clave JSON.

    El cliente y las credenciales se construyen una sola vez por instancia; el
    factory `get_document_storage()` cachea la instancia por proceso.
    """

    def __init__(self) -> None:
        from django.conf import settings

        if not settings.GCS_BUCKET_NAME:
            raise RuntimeError(
                "GCS está habilitado (GCS_ENABLED=True) pero falta GCS_BUCKET_NAME. "
                "Defina el bucket del entorno en el archivo .env."
            )
        self._settings = settings
        self._client = None
        self._bucket = None

    def _get_bucket(self):
        """Construye (perezosamente) el cliente GCS con credenciales impersonadas.

        Se difiere hasta el primer uso para no exigir credenciales ADC en el
        arranque/import; los errores de credenciales se traducen a un mensaje en
        español para el operador.
        """
        if self._bucket is not None:
            return self._bucket

        try:
            from google.cloud import storage
        except ImportError as exc:  # pragma: no cover - dependencia obligatoria
            raise RuntimeError(
                "La librería google-cloud-storage no está instalada; "
                "no es posible usar el almacenamiento en Google Cloud Storage."
            ) from exc

        # Credenciales impersonadas de la SA de firma (keyless, IAM SignBlob).
        credenciales = get_impersonated_credentials()
        self._client = storage.Client(
            project=self._settings.GCS_PROJECT_ID,
            credentials=credenciales,
        )
        self._bucket = self._client.bucket(self._settings.GCS_BUCKET_NAME)
        return self._bucket

    def subir(self, archivo, ruta: str) -> str:
        """Sube el binario a GCS y devuelve la key del objeto (`referencia_externa`).

        `ruta` se usa como nombre base propuesto (típicamente el nombre del
        archivo original); la key final se organiza como
        `{prefijo}/{uuid4}-{nombre_seguro}` para evitar colisiones y garantizar
        unicidad. Devuelve la key del objeto, nunca una URL.
        """
        bucket = self._get_bucket()
        nombre = _nombre_seguro(ruta)
        prefijo = (self._settings.GCS_OBJECT_PREFIX or "").strip("/")
        partes = [p for p in (prefijo, f"{uuid4()}-{nombre}") if p]
        key = "/".join(partes)

        content_type = getattr(archivo, "content_type", None)
        blob = bucket.blob(key)
        # Rebobina el archivo por si ya fue leído durante la validación.
        if hasattr(archivo, "seek"):
            archivo.seek(0)
        blob.upload_from_file(archivo, content_type=content_type)
        return key

    def url_firmada(self, referencia: str) -> str:
        """Devuelve un signed URL V4 de descarga (GET) de corta duración.

        Firma con las credenciales impersonadas (IAM SignBlob), sin clave de SA.
        Nunca devuelve una URL pública ni la key en crudo.
        """
        bucket = self._get_bucket()
        blob = bucket.blob(referencia)
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=self._settings.GCS_SIGNED_URL_EXPIRATION),
            method="GET",
        )

    def eliminar(self, referencia: str) -> None:
        """Elimina el objeto del bucket; tolera que el binario ya no exista.

        Si el objeto no está (por ejemplo, ya fue borrado), se registra un aviso
        y no se propaga el error, de modo que el borrado del `Document` no falle.
        """
        from google.api_core import exceptions as gcloud_exceptions

        bucket = self._get_bucket()
        try:
            bucket.blob(referencia).delete()
        except gcloud_exceptions.NotFound:
            logger.warning(
                "El objeto '%s' no existe en el bucket '%s'; se omite el borrado.",
                referencia,
                self._settings.GCS_BUCKET_NAME,
            )


class CloudflareR2Storage:
    """Backend de almacenamiento documental sobre Cloudflare R2 (S3-compatible).

    Cumple estructuralmente el `Protocol` `DocumentStorage`. R2 expone una API
    compatible con S3, por lo que se usa el cliente `boto3` apuntando al endpoint
    de R2 (`settings.R2_ENDPOINT_URL`) con `region_name="auto"` y firma `s3v4`.
    Los objetos viven en un bucket privado: la única vía de lectura es un
    presigned URL de corta duración (nunca URL pública ni la key en crudo).

    El cliente boto3 se construye perezosamente (una sola vez por instancia); el
    factory `get_document_storage()` cachea la instancia por proceso. El import de
    `boto3` se difiere hasta el primer uso para no exigir la dependencia en el
    arranque cuando R2 está deshabilitado.
    """

    def __init__(self) -> None:
        from django.conf import settings

        if not settings.R2_BUCKET:
            raise RuntimeError(
                "R2 está habilitado (R2_ENABLED=True) pero falta R2_BUCKET. "
                "Defina el bucket del entorno en el archivo .env."
            )
        self._settings = settings
        self._client = None

    def _get_client(self):
        """Construye (perezosamente) el cliente S3 de boto3 para Cloudflare R2.

        Se difiere hasta el primer uso para no importar `boto3` en el arranque; si
        la librería no está instalada se traduce a un mensaje en español para el
        operador.
        """
        if self._client is not None:
            return self._client

        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:  # pragma: no cover - dependencia obligatoria
            raise RuntimeError(
                "La librería boto3 no está instalada; "
                "no es posible usar el almacenamiento en Cloudflare R2."
            ) from exc

        self._client = boto3.client(
            "s3",
            endpoint_url=self._settings.R2_ENDPOINT_URL,
            region_name="auto",
            aws_access_key_id=self._settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=self._settings.R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
        )
        return self._client

    def subir(self, archivo, ruta: str) -> str:
        """Sube el binario a R2 y devuelve la key del objeto (`referencia_externa`).

        `ruta` se usa como nombre base propuesto (típicamente el nombre del
        archivo original); la key final se organiza como
        `{prefijo}/{uuid4}-{nombre_seguro}` para evitar colisiones y garantizar
        unicidad. Devuelve la key del objeto, nunca una URL.
        """
        client = self._get_client()
        nombre = _nombre_seguro(ruta)
        prefijo = (self._settings.R2_OBJECT_PREFIX or "").strip("/")
        partes = [p for p in (prefijo, f"{uuid4()}-{nombre}") if p]
        key = "/".join(partes)

        content_type = getattr(archivo, "content_type", None)
        extra_args = {"ContentType": content_type} if content_type else {}
        # Rebobina el archivo por si ya fue leído durante la validación.
        if hasattr(archivo, "seek"):
            archivo.seek(0)
        client.upload_fileobj(
            archivo,
            self._settings.R2_BUCKET,
            key,
            ExtraArgs=extra_args,
        )
        return key

    def url_firmada(self, referencia: str) -> str:
        """Devuelve un presigned URL de descarga (GET) de corta duración.

        Firma con `s3v4`; nunca devuelve una URL pública ni la key en crudo.
        """
        client = self._get_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._settings.R2_BUCKET, "Key": referencia},
            ExpiresIn=self._settings.R2_SIGNED_URL_EXPIRATION,
        )

    def eliminar(self, referencia: str) -> None:
        """Elimina el objeto del bucket; tolera que el binario ya no exista.

        Si el objeto no está (por ejemplo, ya fue borrado), se registra un aviso
        y no se propaga el error, de modo que el borrado del `Document` no falle.
        """
        client = self._get_client()
        try:
            client.delete_object(Bucket=self._settings.R2_BUCKET, Key=referencia)
        except Exception:
            logger.warning(
                "No se pudo eliminar el objeto '%s' del bucket R2 '%s'; se omite el borrado.",
                referencia,
                self._settings.R2_BUCKET,
            )


@lru_cache(maxsize=1)
def get_document_storage() -> DocumentStorage:
    """Devuelve el backend de almacenamiento según la configuración del proyecto.

    Precedencia de selección:
    1. `CloudflareR2Storage` cuando `R2_ENABLED=True` y `R2_BUCKET` está definido.
    2. `GoogleCloudStorage` (legacy) cuando `GCS_ENABLED=True` y `GCS_BUCKET_NAME`
       está definido.
    3. En cualquier otro caso, el stub `ReferenciaExternaStorage`.

    La instancia se cachea (una sola construcción del cliente por proceso).
    """
    from django.conf import settings

    if getattr(settings, "R2_ENABLED", False) and getattr(settings, "R2_BUCKET", ""):
        return CloudflareR2Storage()
    if getattr(settings, "GCS_ENABLED", False) and getattr(settings, "GCS_BUCKET_NAME", ""):
        return GoogleCloudStorage()
    return ReferenciaExternaStorage()


# Instancia por defecto reutilizable para inyectar en services y ViewSets.
# Se mantiene el stub como valor por defecto para compatibilidad con imports
# existentes; los ViewSets que requieran el backend real deben resolverlo vía
# `get_document_storage()`.
storage_por_defecto: DocumentStorage = ReferenciaExternaStorage()
