"""Pruebas del extractor de texto de PDFs con Document AI (best-effort).

Todo el I/O externo (Document AI / ADC) se mockea: nunca se contacta un backend real.
"""

import io
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from apps.common import documentai
from apps.common.documentai import (
    DocumentAIProcessor,
    extraer_texto_pdf,
    get_document_ai_processor,
)


class DocumentAIProcessorTests(SimpleTestCase):
    """Cliente perezoso ``DocumentAIProcessor``."""

    @override_settings(DOCAI_PROCESSOR_ID="")
    def test_init_sin_processor_falla(self):
        # Unhappy: sin DOCAI_PROCESSOR_ID → RuntimeError en español.
        with self.assertRaises(RuntimeError):
            DocumentAIProcessor()

    @override_settings(
        DOCAI_PROCESSOR_ID="proc", DOCAI_LOCATION="us",
        DOCAI_PROJECT_ID="proj", GCS_SIGNING_SA="sa@x",
    )
    def test_extraer_texto_delega_en_cliente(self):
        # Happy: extraer_texto arma el request y devuelve el texto del documento.
        proc = DocumentAIProcessor()
        cliente = MagicMock()
        resultado = MagicMock()
        resultado.document.text = "texto extraído"
        cliente.process_document.return_value = resultado
        proc._client = cliente
        proc._processor_name = "processors/1"
        texto = proc.extraer_texto(b"%PDF-1.4")
        self.assertEqual(texto, "texto extraído")
        cliente.process_document.assert_called_once()


class ExtraerTextoPdfTests(SimpleTestCase):
    """Función best-effort ``extraer_texto_pdf``."""

    def setUp(self):
        get_document_ai_processor.cache_clear()

    def tearDown(self):
        get_document_ai_processor.cache_clear()

    @override_settings(DOCAI_ENABLED=False)
    def test_deshabilitado_devuelve_vacio(self):
        # Edge: Document AI deshabilitado → "" sin llamar al processor.
        self.assertEqual(extraer_texto_pdf(io.BytesIO(b"x")), "")

    @override_settings(DOCAI_ENABLED=True)
    def test_habilitado_extrae_texto(self):
        # Happy: habilitado → delega en el processor y devuelve el texto.
        fake_proc = MagicMock()
        fake_proc.extraer_texto.return_value = "contenido OCR"
        with patch.object(documentai, "get_document_ai_processor", return_value=fake_proc):
            texto = extraer_texto_pdf(io.BytesIO(b"%PDF-1.4"))
        self.assertEqual(texto, "contenido OCR")

    @override_settings(DOCAI_ENABLED=True)
    def test_falla_devuelve_vacio(self):
        # Unhappy: cualquier fallo del processor → "" (no propaga la excepción).
        with patch.object(
            documentai, "get_document_ai_processor", side_effect=Exception("boom")
        ):
            self.assertEqual(extraer_texto_pdf(io.BytesIO(b"x")), "")
