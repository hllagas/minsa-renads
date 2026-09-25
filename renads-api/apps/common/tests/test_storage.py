"""Pruebas de la abstracción de almacenamiento documental (RNF-DOC).

Todo el I/O externo (GCS/R2/boto3) se mockea: nunca se contacta un backend real.
"""

import io
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from apps.common import storage
from apps.common.storage import (
    CloudflareR2Storage,
    GoogleCloudStorage,
    ReferenciaExternaStorage,
    _nombre_seguro,
    get_document_storage,
)


class NombreSeguroTests(SimpleTestCase):
    """Saneado de nombres de archivo para keys de objeto."""

    def test_elimina_ruta(self):
        # Happy: elimina prefijos de ruta.
        self.assertEqual(_nombre_seguro("carpeta/sub/archivo.pdf"), "archivo.pdf")

    def test_bloquea_traversal(self):
        # Unhappy: intenta path traversal → se limpia a un nombre plano.
        resultado = _nombre_seguro("../../etc/passwd")
        self.assertNotIn("/", resultado)
        self.assertNotIn("..", resultado)

    def test_reemplaza_caracteres_problematicos(self):
        # Edge: caracteres no permitidos → "_".
        self.assertEqual(_nombre_seguro("a b#c.pdf"), "a_b_c.pdf")

    def test_vacio_devuelve_default(self):
        # Edge: nombre vacío → "archivo".
        self.assertEqual(_nombre_seguro(""), "archivo")
        self.assertEqual(_nombre_seguro("..."), "archivo")

    def test_trunca_a_120(self):
        # Edge: nombre largo se trunca a 120 caracteres.
        largo = "a" * 300 + ".pdf"
        self.assertLessEqual(len(_nombre_seguro(largo)), 120)


class ReferenciaExternaStorageTests(SimpleTestCase):
    """Stub por referencia externa (sin backend)."""

    def setUp(self):
        self.st = ReferenciaExternaStorage()

    def test_subir_propaga_ruta(self):
        self.assertEqual(self.st.subir(io.BytesIO(b"x"), "ref/1.pdf"), "ref/1.pdf")

    def test_url_firmada_devuelve_referencia(self):
        self.assertEqual(self.st.url_firmada("ref/1.pdf"), "ref/1.pdf")

    def test_eliminar_noop(self):
        self.assertIsNone(self.st.eliminar("ref/1.pdf"))


class CloudflareR2StorageTests(SimpleTestCase):
    """Backend R2 (S3-compatible) con boto3 mockeado."""

    @override_settings(
        R2_BUCKET="renads-media", R2_ENDPOINT_URL="https://r2.example",
        R2_ACCESS_KEY_ID="k", R2_SECRET_ACCESS_KEY="s",
        R2_OBJECT_PREFIX="docs", R2_SIGNED_URL_EXPIRATION=300,
    )
    def test_subir_construye_key_y_sube(self):
        # Happy: sube el binario y devuelve una key con prefijo y nombre seguro.
        st = CloudflareR2Storage()
        cliente = MagicMock()
        st._client = cliente
        archivo = io.BytesIO(b"contenido")
        archivo.content_type = "application/pdf"
        key = st.subir(archivo, "informe.pdf")
        self.assertTrue(key.startswith("docs/"))
        self.assertTrue(key.endswith("-informe.pdf"))
        cliente.upload_fileobj.assert_called_once()

    @override_settings(R2_BUCKET="", R2_ENDPOINT_URL="", R2_ACCESS_KEY_ID="",
                       R2_SECRET_ACCESS_KEY="")
    def test_init_sin_bucket_falla(self):
        # Unhappy: sin R2_BUCKET → RuntimeError en español.
        with self.assertRaises(RuntimeError):
            CloudflareR2Storage()

    @override_settings(
        R2_BUCKET="renads-media", R2_ENDPOINT_URL="https://r2.example",
        R2_ACCESS_KEY_ID="k", R2_SECRET_ACCESS_KEY="s",
        R2_OBJECT_PREFIX="", R2_SIGNED_URL_EXPIRATION=300,
    )
    def test_url_firmada_delega_en_presigned(self):
        # Happy: url_firmada delega en generate_presigned_url.
        st = CloudflareR2Storage()
        cliente = MagicMock()
        cliente.generate_presigned_url.return_value = "https://firmada"
        st._client = cliente
        self.assertEqual(st.url_firmada("k1"), "https://firmada")

    @override_settings(
        R2_BUCKET="renads-media", R2_ENDPOINT_URL="https://r2.example",
        R2_ACCESS_KEY_ID="k", R2_SECRET_ACCESS_KEY="s",
        R2_OBJECT_PREFIX="", R2_SIGNED_URL_EXPIRATION=300,
    )
    def test_eliminar_tolera_error(self):
        # Edge: fallo de borrado no propaga excepción.
        st = CloudflareR2Storage()
        cliente = MagicMock()
        cliente.delete_object.side_effect = Exception("boom")
        st._client = cliente
        st.eliminar("k1")  # no debe lanzar


class GoogleCloudStorageTests(SimpleTestCase):
    """Backend GCS (legacy) con cliente mockeado."""

    @override_settings(GCS_BUCKET_NAME="", GCS_SIGNING_SA="sa@x")
    def test_init_sin_bucket_falla(self):
        # Unhappy: sin GCS_BUCKET_NAME → RuntimeError.
        with self.assertRaises(RuntimeError):
            GoogleCloudStorage()

    @override_settings(
        GCS_BUCKET_NAME="bucket-dev", GCS_PROJECT_ID="proj",
        GCS_OBJECT_PREFIX="docs", GCS_SIGNED_URL_EXPIRATION=300,
    )
    def test_subir_delega_en_blob(self):
        # Happy: sube el binario vía blob.upload_from_file.
        st = GoogleCloudStorage()
        bucket = MagicMock()
        blob = MagicMock()
        bucket.blob.return_value = blob
        st._bucket = bucket
        archivo = io.BytesIO(b"contenido")
        key = st.subir(archivo, "doc.pdf")
        self.assertTrue(key.startswith("docs/"))
        blob.upload_from_file.assert_called_once()


class GetDocumentStorageTests(SimpleTestCase):
    """Factory ``get_document_storage`` (precedencia R2 → GCS → stub)."""

    def setUp(self):
        get_document_storage.cache_clear()

    def tearDown(self):
        get_document_storage.cache_clear()

    @override_settings(R2_ENABLED=False, GCS_ENABLED=False)
    def test_default_stub(self):
        self.assertIsInstance(get_document_storage(), ReferenciaExternaStorage)

    @override_settings(R2_ENABLED=True, R2_BUCKET="renads-media")
    def test_r2_tiene_precedencia(self):
        self.assertIsInstance(get_document_storage(), CloudflareR2Storage)

    @override_settings(R2_ENABLED=False, GCS_ENABLED=True, GCS_BUCKET_NAME="bucket-dev")
    def test_gcs_cuando_r2_deshabilitado(self):
        self.assertIsInstance(get_document_storage(), GoogleCloudStorage)


class GetImpersonatedCredentialsTests(SimpleTestCase):
    """``get_impersonated_credentials`` (keyless GCS)."""

    def test_falla_sin_credenciales_adc(self):
        # Unhappy: sin ADC disponibles → RuntimeError en español.
        with patch("google.auth.default", side_effect=Exception("no adc")):
            with self.assertRaises(RuntimeError):
                storage.get_impersonated_credentials(signing_sa="sa@x")

    def test_construye_credenciales(self):
        # Happy: con ADC disponible construye credenciales impersonadas.
        fake_base = MagicMock()
        with patch("google.auth.default", return_value=(fake_base, "proj")), patch(
            "google.auth.impersonated_credentials.Credentials"
        ) as cred_cls:
            cred_cls.return_value = "cred"
            resultado = storage.get_impersonated_credentials(signing_sa="sa@x")
        self.assertEqual(resultado, "cred")
