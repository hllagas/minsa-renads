"""Pruebas de generación de PDF del convenio (apps.convenios.pdf).

Las dependencias de sistema (LibreOffice ``soffice``, ``docxtpl``, ``pypdf``, storage
R2/boto3) se **mockean**: nunca se invocan de verdad. Se centra en la lógica pura
(``construir_contexto``, ``_seleccionar_plantilla``, orquestación de merge).
"""

import datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.convenios import pdf
from apps.convenios.tests import factories as f


class ConstruirContextoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("pdf_admin", is_superuser=True)

    def test_contexto_basico(self):
        # Happy: arma el contexto con datos básicos sin lanzar.
        conv = f.crear_convenio(creado_por=self.admin, titulo="Conv PDF",
                                fecha_fin=datetime.date(2028, 1, 1))
        ctx = pdf.construir_contexto(conv)
        self.assertEqual(ctx["titulo"], "Conv PDF")
        self.assertEqual(ctx["fecha_inicio"], "2026-03-01")
        self.assertEqual(ctx["carreras"], [])
        self.assertEqual(ctx["partes"], [])
        self.assertIsNone(ctx["convenio_marco"])
        self.assertIsNone(ctx["convenio_origen"])
        self.assertEqual(ctx["mes"], "marzo")

    def test_contexto_con_partes_y_carreras(self):
        # Happy: incluye partes firmantes y carreras de la facultad.
        uni = f.crear_universidad("Uni PDF", "UPDF")
        facultad = f.crear_facultad(universidad=uni)
        carrera = f.crear_carrera("Med PDF")
        f.crear_universidad_carrera(universidad=uni, carrera=carrera, facultad=facultad)
        ue = f.crear_unidad_ejecutora(codigo="7301", nombre="UE PDF")
        unidad = f.crear_unidad_organica(organo_nombre=f.ORGANO_DIRIS, nombre="DIRIS PDF")
        conv = f.crear_convenio(creado_por=self.admin, universidad=uni, tipo_codigo="ESPECIFICO",
                                unidad_organica=unidad, unidad_ejecutora=ue, facultad=facultad)
        from apps.convenios.models import ConventionParty
        ConventionParty.objects.create(convenio=conv, rol="UNIDAD_EJECUTORA",
                                       unidad_organica=unidad, orden=1)
        ctx = pdf.construir_contexto(conv)
        self.assertEqual(ctx["carreras"], ["Med PDF"])
        self.assertEqual(len(ctx["partes"]), 1)
        self.assertEqual(ctx["partes"][0]["rol"], "UNIDAD_EJECUTORA")

    def test_contexto_adenda(self):
        # Edge: una adenda referencia su origen en el contexto.
        origen = f.crear_convenio(creado_por=self.admin, titulo="Origen PDF")
        adenda = f.crear_convenio(creado_por=self.admin, universidad=origen.universidad,
                                  titulo="Adenda PDF")
        adenda.convenio_origen = origen
        adenda.es_adenda = True
        adenda.save()
        ctx = pdf.construir_contexto(adenda)
        self.assertTrue(ctx["es_adenda"])
        self.assertIsNotNone(ctx["convenio_origen"])
        self.assertEqual(ctx["convenio_origen"]["titulo"], "Origen PDF")


class SeleccionarPlantillaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("plt_admin", is_superuser=True)

    def test_adenda_usa_plantilla_adenda(self):
        conv = f.crear_convenio(creado_por=self.admin)
        conv.es_adenda = True
        ruta = pdf._seleccionar_plantilla(conv)
        self.assertEqual(ruta.name, "adenda.docx")

    def test_marco_gore(self):
        conv = f.crear_convenio(creado_por=self.admin, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE)
        ruta = pdf._seleccionar_plantilla(conv)
        self.assertEqual(ruta.name, "modelo_2_marco_region.docx")

    def test_especifico_diris(self):
        conv = f.crear_convenio(creado_por=self.admin, tipo_codigo="ESPECIFICO",
                                organo_nombre=f.ORGANO_DIRIS)
        ruta = pdf._seleccionar_plantilla(conv)
        self.assertEqual(ruta.name, "modelo_3_especifico_lima.docx")

    def test_combinacion_sin_plantilla_lanza(self):
        # Unhappy: combinación no mapeada → RuntimeError en español.
        conv = f.crear_convenio(creado_por=self.admin, tipo_codigo="ESPECIFICO",
                                organo_nombre=f.ORGANO_UNIVERSIDAD)
        with self.assertRaises(RuntimeError):
            pdf._seleccionar_plantilla(conv)


class ConvertirYGenerarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("gen_admin", is_superuser=True)

    def test_convertir_a_pdf_sin_soffice(self):
        # Unhappy: soffice no está en el PATH → RuntimeError en español.
        with patch("apps.convenios.pdf.shutil.which", return_value=None):
            with self.assertRaises(RuntimeError):
                pdf.convertir_a_pdf(b"docx bytes")

    def test_convertir_a_pdf_soffice_ok(self):
        # Happy: soffice convierte correctamente (subprocess mockeado).
        with patch("apps.convenios.pdf.shutil.which", return_value="/usr/bin/soffice"), \
             patch("apps.convenios.pdf.subprocess.run") as mock_run, \
             patch("apps.convenios.pdf.Path") as mock_path, \
             patch("apps.convenios.pdf.tempfile.mkdtemp", return_value="/tmp/x"), \
             patch("apps.convenios.pdf.shutil.rmtree"):
            mock_run.return_value = MagicMock(returncode=0)
            pdf_instance = MagicMock()
            pdf_instance.exists.return_value = True
            pdf_instance.read_bytes.return_value = b"%PDF-1.4"
            # Path(tmpdir) / "convenio.pdf" y "convenio.docx"
            mock_path.return_value.__truediv__.return_value = pdf_instance
            resultado = pdf.convertir_a_pdf(b"docx bytes")
            self.assertEqual(resultado, b"%PDF-1.4")

    def test_generar_proyecto_orquesta(self):
        # Happy: generar_proyecto encadena generar_docx + convertir_a_pdf (mockeados).
        conv = f.crear_convenio(creado_por=self.admin)
        with patch("apps.convenios.pdf.generar_docx", return_value=b"docx"), \
             patch("apps.convenios.pdf.convertir_a_pdf", return_value=b"%PDF-1.4"):
            self.assertEqual(pdf.generar_proyecto(conv), b"%PDF-1.4")

    def test_generar_expediente_merge(self):
        # Happy: expediente concatena el proyecto + adjuntos (pypdf mockeado).
        conv = f.crear_convenio(creado_por=self.admin)
        with patch("apps.convenios.pdf.generar_proyecto", return_value=b"%PDF-1.4"), \
             patch("apps.convenios.pdf._pdfs_adjuntos_del_expediente", return_value=[]), \
             patch("pypdf.PdfReader") as mock_reader, \
             patch("pypdf.PdfWriter") as mock_writer:
            mock_reader.return_value.pages = []
            writer_instance = MagicMock()
            mock_writer.return_value = writer_instance
            resultado = pdf.generar_expediente(conv)
            self.assertIsInstance(resultado, (bytes, bytearray))


class DescargarBinarioTests(TestCase):
    def test_referencia_vacia(self):
        # Edge: referencia vacía → None sin tocar el storage.
        self.assertIsNone(pdf._descargar_binario(""))

    def test_url_firmada_falla(self):
        # Unhappy: si el storage falla al firmar, se omite (None).
        with patch("apps.common.storage.get_document_storage") as mock_storage:
            mock_storage.return_value.url_firmada.side_effect = Exception("boom")
            self.assertIsNone(pdf._descargar_binario("ruta/x.pdf"))

    def test_url_http_descarga(self):
        # Happy: URL http descarga el binario por urllib.
        with patch("apps.common.storage.get_document_storage") as mock_storage, \
             patch("urllib.request.urlopen") as mock_urlopen:
            mock_storage.return_value.url_firmada.return_value = "https://x/doc.pdf"
            cm = MagicMock()
            cm.read.return_value = b"%PDF"
            mock_urlopen.return_value.__enter__.return_value = cm
            self.assertEqual(pdf._descargar_binario("ruta/x.pdf"), b"%PDF")

    def test_ruta_local_inexistente(self):
        # Edge: ruta local inexistente → None (se omite con log).
        with patch("apps.common.storage.get_document_storage") as mock_storage:
            mock_storage.return_value.url_firmada.return_value = "/tmp/no-existe.pdf"
            self.assertIsNone(pdf._descargar_binario("ruta/x.pdf"))


class GenerarDocxTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("gdx_admin", is_superuser=True)

    def test_generar_docx_renderiza(self):
        # Happy: renderiza la plantilla (docxtpl mockeado, sin tocar disco real).
        conv = f.crear_convenio(creado_por=self.admin, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE)
        fake_module = MagicMock()
        docx_instance = MagicMock()

        def _save(buffer):
            buffer.write(b"docx-bytes")

        docx_instance.save.side_effect = _save
        fake_module.DocxTemplate.return_value = docx_instance
        with patch.dict("sys.modules", {"docxtpl": fake_module}), \
             patch("apps.convenios.pdf._seleccionar_plantilla") as mock_plantilla:
            ruta = MagicMock()
            ruta.exists.return_value = True
            mock_plantilla.return_value = ruta
            resultado = pdf.generar_docx(conv)
        self.assertEqual(resultado, b"docx-bytes")

    def test_generar_docx_plantilla_faltante(self):
        # Unhappy: la plantilla no existe → RuntimeError.
        conv = f.crear_convenio(creado_por=self.admin, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE)
        fake_module = MagicMock()
        with patch.dict("sys.modules", {"docxtpl": fake_module}), \
             patch("apps.convenios.pdf._seleccionar_plantilla") as mock_plantilla:
            ruta = MagicMock()
            ruta.exists.return_value = False
            mock_plantilla.return_value = ruta
            with self.assertRaises(RuntimeError):
                pdf.generar_docx(conv)


class DomicilioYCargoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("dom_admin", is_superuser=True)

    def test_cargo_por_sexo(self):
        from apps.convenios.models import ExecutivePosition
        cargo = ExecutivePosition.objects.create(
            organo=f.crear_organo(f.ORGANO_MINSA), unidad_organica=None,
            nombre_masculino="Director", nombre_femenino="Directora",
        )
        self.assertEqual(pdf._cargo_por_sexo(cargo, "F"), "Directora")
        self.assertEqual(pdf._cargo_por_sexo(cargo, "M"), "Director")
        self.assertEqual(pdf._cargo_por_sexo(None, "M"), "")

    def test_domicilio_minsa_fijo(self):
        conv = f.crear_convenio(creado_por=self.admin)
        self.assertEqual(pdf._domicilio_entidad(conv, "MINSA"), pdf.DOMICILIO_MINSA)

    def test_domicilio_universidad_y_gore(self):
        gore = f.crear_gobierno_regional(nombre="GORE Dom")
        gore.direccion = "Av. Regional 100"
        gore.save()
        conv = f.crear_convenio(creado_por=self.admin, tipo_codigo="MARCO",
                                organo_nombre=f.ORGANO_GORE, gobierno_regional=gore)
        self.assertEqual(pdf._domicilio_entidad(conv, "GOBIERNO_REGIONAL"), "Av. Regional 100")
        self.assertEqual(pdf._domicilio_entidad(conv, "UNIDAD_EJECUTORA"), "")
        self.assertEqual(pdf._domicilio_entidad(conv, "OTRO"), "")


class PdfsAdjuntosExpedienteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("adj_admin", is_superuser=True)

    def test_sin_adjuntos(self):
        # Edge: convenio sin partes ni campos clínicos → lista vacía.
        conv = f.crear_convenio(creado_por=self.admin)
        self.assertEqual(pdf._pdfs_adjuntos_del_expediente(conv), [])
