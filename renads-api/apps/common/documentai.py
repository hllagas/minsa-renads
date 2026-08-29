"""Procesamiento de PDFs con Google Cloud Document AI (RNF-DOC-01/02/03).

Expone `extraer_texto_pdf(archivo)`, que envía los bytes del PDF a un processor
de Document AI (OCR genérico / Document OCR) y devuelve el texto extraído.

Diseño **best-effort**: si Document AI está deshabilitado (`DOCAI_ENABLED=False`),
mal configurado o la llamada falla, la función devuelve `""` y registra el error
en logs — nunca lanza, de modo que la subida del PDF no se bloquea. Sigue el
mismo patrón de autenticación KEYLESS que `apps.common.storage.GoogleCloudStorage`
(ADC + impersonación de la SA de firma vía IAM SignBlob). Ver `spec/almacenamiento.md`.
"""

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


class DocumentAIProcessor:
    """Cliente perezoso de Document AI para extraer texto de PDFs.

    El cliente y las credenciales se construyen una sola vez por instancia (el
    factory `get_document_ai_processor()` cachea la instancia por proceso). La
    autenticación es keyless: se parte de ADC y se impersona
    `settings.GCS_SIGNING_SA` para obtener tokens efímeros.
    """

    def __init__(self) -> None:
        from django.conf import settings

        if not settings.DOCAI_PROCESSOR_ID:
            raise RuntimeError(
                "Document AI está habilitado (DOCAI_ENABLED=True) pero falta "
                "DOCAI_PROCESSOR_ID. Defina el processor del entorno en el .env."
            )
        self._settings = settings
        self._client = None
        self._processor_name = None

    def _get_client(self):
        """Construye (perezosamente) el cliente de Document AI con credenciales impersonadas."""
        if self._client is not None:
            return self._client, self._processor_name

        try:
            import google.auth
            from google.api_core.client_options import ClientOptions
            from google.auth import impersonated_credentials
            from google.cloud import documentai
        except ImportError as exc:  # pragma: no cover - dependencia obligatoria
            raise RuntimeError(
                "La librería google-cloud-documentai no está instalada; "
                "no es posible procesar PDFs con Document AI."
            ) from exc

        try:
            credenciales_base, _ = google.auth.default()
        except Exception as exc:
            raise RuntimeError(
                "No se encontraron credenciales de Google Cloud (ADC). "
                "Ejecute `gcloud auth application-default login` o configure el "
                "runtime con una identidad autorizada."
            ) from exc

        credenciales = impersonated_credentials.Credentials(
            source_credentials=credenciales_base,
            target_principal=self._settings.GCS_SIGNING_SA,
            target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )

        # api_endpoint regional según la ubicación del processor (p. ej. us / eu).
        location = self._settings.DOCAI_LOCATION
        opciones = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
        self._client = documentai.DocumentProcessorServiceClient(
            credentials=credenciales, client_options=opciones
        )
        self._processor_name = self._client.processor_path(
            self._settings.DOCAI_PROJECT_ID,
            location,
            self._settings.DOCAI_PROCESSOR_ID,
        )
        return self._client, self._processor_name

    def extraer_texto(self, contenido: bytes) -> str:
        """Procesa los bytes del PDF y devuelve el texto extraído (o `""`)."""
        from google.cloud import documentai

        client, processor_name = self._get_client()
        raw_document = documentai.RawDocument(
            content=contenido, mime_type="application/pdf"
        )
        request = documentai.ProcessRequest(
            name=processor_name, raw_document=raw_document
        )
        resultado = client.process_document(request=request)
        return resultado.document.text or ""


@lru_cache(maxsize=1)
def get_document_ai_processor() -> "DocumentAIProcessor":
    """Devuelve el processor de Document AI (cacheado por proceso)."""
    return DocumentAIProcessor()


def extraer_texto_pdf(archivo) -> str:
    """Extrae el texto de un PDF con Document AI (best-effort).

    Devuelve `""` cuando Document AI está deshabilitado o cualquier paso falla; en
    ese caso registra el motivo en logs y NO propaga la excepción, de modo que la
    subida del PDF no se bloquee. Rebobina `archivo` tras leer los bytes.
    """
    from django.conf import settings

    if not getattr(settings, "DOCAI_ENABLED", False):
        return ""

    try:
        if hasattr(archivo, "seek"):
            archivo.seek(0)
        contenido = archivo.read()
        if hasattr(archivo, "seek"):
            archivo.seek(0)
        texto = get_document_ai_processor().extraer_texto(contenido)
        logger.info("Document AI extrajo %d caracteres del PDF.", len(texto))
        return texto
    except Exception:
        logger.exception(
            "Falló la extracción de texto con Document AI; se continúa sin texto extraído."
        )
        return ""
