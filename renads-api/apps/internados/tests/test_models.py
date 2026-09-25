"""Pruebas de modelos del módulo Internados: __str__, defaults y restricciones de unicidad."""

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.internados.models import TutorConvenio, TutorUniversity
from apps.internados.tests import factories as f


class StudentModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("stu_model")

    def test_str_combina_apellidos_y_nombres(self):
        # __str__ arma "paterno materno nombres".
        est = f.crear_estudiante(creado_por=self.user)
        self.assertEqual(str(est), "PEREZ GOMEZ JUAN")

    def test_unique_together_tipo_documento_numero(self):
        # Edge: no se admiten dos estudiantes con el mismo (tipo_documento, numero).
        tipo = f.crear_tipo_documento()
        uni = f.crear_universidad()
        f.crear_estudiante(creado_por=self.user, universidad=uni, tipo_documento=tipo,
                           numero_documento="11111111")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                f.crear_estudiante(creado_por=self.user, universidad=uni, tipo_documento=tipo,
                                   numero_documento="11111111")


class TutorModelTests(TestCase):
    def test_str_tutor(self):
        tutor = f.crear_tutor(nombres="LUIS", apellido_paterno="RAMOS")
        # apellido_materno vacío por defecto → "RAMOS  LUIS" (doble espacio interno).
        self.assertIn("RAMOS", str(tutor))
        self.assertIn("LUIS", str(tutor))

    def test_tutor_university_unique_together(self):
        uni = f.crear_universidad()
        tutor = f.crear_tutor(universidades=[uni])
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TutorUniversity.objects.create(tutor=tutor, universidad=uni)


class TutorConvenioModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("tc_model")

    def test_str_incluye_ids(self):
        convenio = f.crear_convenio(creado_por=self.user)
        ipress = f.crear_ipress()
        tutor = f.crear_tutor(universidades=[convenio.universidad])
        tc = TutorConvenio.objects.create(tutor=tutor, convenio=convenio, ipress=ipress)
        self.assertIn(f"Tutor {tutor.id}", str(tc))
        self.assertIn(f"Convenio {convenio.id}", str(tc))

    def test_unique_together_tutor_convenio(self):
        convenio = f.crear_convenio(creado_por=self.user)
        ipress = f.crear_ipress()
        tutor = f.crear_tutor(universidades=[convenio.universidad])
        TutorConvenio.objects.create(tutor=tutor, convenio=convenio, ipress=ipress)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TutorConvenio.objects.create(tutor=tutor, convenio=convenio, ipress=ipress)


class InternshipModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("int_model")

    def test_estado_declaraciones_default_pendiente(self):
        # Happy: el default de estado_declaraciones es PENDIENTE.
        internado = f.crear_internado(creado_por=self.user)
        self.assertEqual(internado.estado_declaraciones, "PENDIENTE")
