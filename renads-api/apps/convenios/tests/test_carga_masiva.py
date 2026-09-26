"""Pruebas de la carga masiva (Excel) de convenios y campos clínicos (services)."""

import datetime
import io

import openpyxl
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from apps.convenios import services
from apps.convenios.models import Convention
from apps.convenios.tests import factories as f


def _xlsx(cabecera, filas):
    """Arma un .xlsx en memoria con la cabecera y filas dadas."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(cabecera)
    for fila in filas:
        ws.append(fila)
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


class RegistrarConveniosMasivoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = f.crear_usuario("bm_user", is_superuser=True)
        cls.uni = f.crear_universidad("Uni Bulk", "UBLK")
        cls.gore = f.crear_gobierno_regional(nombre="GORE Bulk")
        cls.unidad_gore = f.crear_unidad_organica(organo_nombre=f.ORGANO_GORE, nombre="GERESA Bulk")

    def test_crear_marco_valido(self):
        # Happy: una fila válida de Marco crea el convenio en estado destino.
        archivo = _xlsx(
            ["tipo_convenio", "titulo", "unidad_organica_id", "universidad_id",
             "fecha_solicitud", "gobierno_regional_id", "estado_destino"],
            [["MARCO", "Marco Bulk", self.unidad_gore.id, self.uni.id,
              "2026-03-01", self.gore.id, "VIGENTE"]],
        )
        resumen = services.registrar_convenios_masivo(archivo=archivo, usuario=self.usuario)
        self.assertEqual(resumen["creados"], 1)
        self.assertEqual(resumen["omitidos"], 0)
        self.assertTrue(Convention.objects.filter(titulo="Marco Bulk").exists())

    def test_fila_invalida_se_reporta(self):
        # Unhappy: fila con tipo inexistente se reporta sin abortar el lote.
        archivo = _xlsx(
            ["tipo_convenio", "titulo", "unidad_organica_id", "universidad_id", "fecha_solicitud"],
            [["INEXISTENTE", "Malo", self.unidad_gore.id, self.uni.id, "2026-03-01"]],
        )
        resumen = services.registrar_convenios_masivo(archivo=archivo, usuario=self.usuario)
        self.assertEqual(resumen["creados"], 0)
        self.assertEqual(resumen["omitidos"], 1)
        self.assertEqual(resumen["errores"][0]["fila"], 2)

    def test_falta_columna_requerida(self):
        # Unhappy: falta una columna requerida → ValidationError.
        archivo = _xlsx(["tipo_convenio", "titulo"], [["MARCO", "X"]])
        with self.assertRaises(ValidationError):
            services.registrar_convenios_masivo(archivo=archivo, usuario=self.usuario)

    def test_archivo_vacio(self):
        # Edge: workbook sin filas → error de archivo vacío.
        wb = openpyxl.Workbook()
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        # Un workbook nuevo tiene una hoja con una fila None; se lee como cabecera vacía
        # y faltan columnas requeridas.
        with self.assertRaises(ValidationError):
            services.registrar_convenios_masivo(archivo=buffer, usuario=self.usuario)

    def test_fila_vacia_se_omite(self):
        # Edge: una fila completamente vacía no cuenta como error.
        archivo = _xlsx(
            ["tipo_convenio", "titulo", "unidad_organica_id", "universidad_id",
             "fecha_solicitud", "gobierno_regional_id", "estado_destino"],
            [
                [None, None, None, None, None, None, None],
                ["MARCO", "Marco Bulk2", self.unidad_gore.id, self.uni.id,
                 "2026-03-01", self.gore.id, "VIGENTE"],
            ],
        )
        resumen = services.registrar_convenios_masivo(archivo=archivo, usuario=self.usuario)
        self.assertEqual(resumen["creados"], 1)
        self.assertEqual(resumen["omitidos"], 0)

    def test_estado_destino_invalido(self):
        # Unhappy: estado_destino fuera de {VIGENTE, PUBLICADO} se reporta.
        archivo = _xlsx(
            ["tipo_convenio", "titulo", "unidad_organica_id", "universidad_id",
             "fecha_solicitud", "gobierno_regional_id", "estado_destino"],
            [["MARCO", "Marco Bulk3", self.unidad_gore.id, self.uni.id,
              "2026-03-01", self.gore.id, "SOLICITUD_REGISTRADA"]],
        )
        resumen = services.registrar_convenios_masivo(archivo=archivo, usuario=self.usuario)
        self.assertEqual(resumen["omitidos"], 1)


class RegistrarDeterminacionMasivaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = f.crear_usuario("dm_user", is_superuser=True)
        cls.ipress = f.crear_ipress(codigo="84010001", es_sede_docente=True)
        cls.carrera = f.crear_carrera("Medicina DM")

    def test_determinacion_valida(self):
        # Happy: crea un registro de campos clínicos.
        archivo = _xlsx(
            ["ipress_id", "carrera_profesional_id", "campos_clinicos_registrados"],
            [[self.ipress.codigo_renipress, self.carrera.id, 6]],
        )
        resumen = services.registrar_determinacion_masiva(archivo=archivo, usuario=self.usuario)
        self.assertEqual(resumen["creados"], 1)

    def test_ipress_inexistente(self):
        # Unhappy: IPRESS que no existe se reporta.
        archivo = _xlsx(
            ["ipress_id", "carrera_profesional_id", "campos_clinicos_registrados"],
            [["99999999", self.carrera.id, 6]],
        )
        resumen = services.registrar_determinacion_masiva(archivo=archivo, usuario=self.usuario)
        self.assertEqual(resumen["omitidos"], 1)

    def test_campos_no_positivo(self):
        # Unhappy: campos_clinicos_registrados no positivo se reporta.
        archivo = _xlsx(
            ["ipress_id", "carrera_profesional_id", "campos_clinicos_registrados"],
            [[self.ipress.codigo_renipress, self.carrera.id, 0]],
        )
        resumen = services.registrar_determinacion_masiva(archivo=archivo, usuario=self.usuario)
        self.assertEqual(resumen["omitidos"], 1)

    def test_falta_columna(self):
        archivo = _xlsx(["ipress_id"], [["84010001"]])
        with self.assertRaises(ValidationError):
            services.registrar_determinacion_masiva(archivo=archivo, usuario=self.usuario)


class RegistrarAsignacionMasivaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = f.crear_usuario("am_user", is_superuser=True)
        cls.carrera = f.crear_carrera("Medicina AM")
        cls.ipress = f.crear_ipress(codigo="85010001", es_sede_docente=True)
        cls.reg = f.crear_registro_campo_clinico(ipress=cls.ipress, carrera=cls.carrera,
                                                registrados=10)
        cls.conv = f.crear_convenio(creado_por=cls.usuario, tipo_codigo="ESPECIFICO",
                                    estado_codigo="VIGENTE")

    def test_asignacion_valida(self):
        # Happy: crea una asignación desde una fila.
        archivo = _xlsx(
            ["campo_clinico_ipress_id", "convenio_id", "campos_clinicos_autorizados",
             "fecha_inicio", "fecha_fin"],
            [[self.reg.id, self.conv.id, 4, "2026-03-01", "2027-03-01"]],
        )
        resumen = services.registrar_asignacion_masiva(archivo=archivo, usuario=self.usuario)
        self.assertEqual(resumen["creados"], 1)

    def test_asignacion_excede_disponibilidad(self):
        # Unhappy: excede la disponibilidad → se reporta.
        archivo = _xlsx(
            ["campo_clinico_ipress_id", "convenio_id", "campos_clinicos_autorizados",
             "fecha_inicio", "fecha_fin"],
            [[self.reg.id, self.conv.id, 999, "2026-03-01", "2027-03-01"]],
        )
        resumen = services.registrar_asignacion_masiva(archivo=archivo, usuario=self.usuario)
        self.assertEqual(resumen["omitidos"], 1)

    def test_registro_inexistente(self):
        archivo = _xlsx(
            ["campo_clinico_ipress_id", "convenio_id", "campos_clinicos_autorizados"],
            [[999999, self.conv.id, 1]],
        )
        resumen = services.registrar_asignacion_masiva(archivo=archivo, usuario=self.usuario)
        self.assertEqual(resumen["omitidos"], 1)

    def test_falta_columna(self):
        archivo = _xlsx(["convenio_id"], [[self.conv.id]])
        with self.assertRaises(ValidationError):
            services.registrar_asignacion_masiva(archivo=archivo, usuario=self.usuario)
