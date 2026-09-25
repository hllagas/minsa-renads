"""Pruebas de FilterSets del módulo Internados."""

from django.test import TestCase

from apps.internados.filters import InternshipFilter, StudentFilter
from apps.internados.models import Internship, Student
from apps.internados.tests import factories as f


class StudentFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("filt_stu")
        cls.nivel_pre = f.crear_nivel("PREGRADO", "Pregrado")
        cls.nivel_esp = f.crear_nivel("MAESTRIA", "Maestría")
        cls.carrera_pre = f.crear_carrera("Medicina", cls.nivel_pre)
        cls.carrera_esp = f.crear_carrera("Cardio", cls.nivel_esp)
        cls.uni = f.crear_universidad()
        cls.est_pre = f.crear_estudiante(creado_por=cls.user, universidad=cls.uni,
                                         carrera=cls.carrera_pre, numero_documento="80000001")
        cls.est_esp = f.crear_estudiante(creado_por=cls.user, universidad=cls.uni,
                                         carrera=cls.carrera_esp, numero_documento="80000002")

    def test_filtra_por_nivel_academico(self):
        # Filtro derivado: nivel_academico de la carrera (RN-19).
        fs = StudentFilter({"nivel_academico": self.nivel_pre.id}, queryset=Student.objects.all())
        self.assertEqual(list(fs.qs), [self.est_pre])

    def test_filtra_por_numero_documento(self):
        fs = StudentFilter({"numero_documento": "80000002"}, queryset=Student.objects.all())
        self.assertEqual(list(fs.qs), [self.est_esp])

    def test_filtra_por_universidad(self):
        fs = StudentFilter({"universidad": self.uni.id}, queryset=Student.objects.all())
        self.assertEqual(fs.qs.count(), 2)


class InternshipFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("filt_int")
        cls.internado = f.crear_internado(creado_por=cls.user)

    def test_filtra_por_estudiante(self):
        fs = InternshipFilter(
            {"estudiante": self.internado.estudiante_id}, queryset=Internship.objects.all()
        )
        self.assertEqual(list(fs.qs), [self.internado])

    def test_rango_fecha_inicio(self):
        fs = InternshipFilter(
            {"fecha_inicio_desde": "2026-01-01", "fecha_inicio_hasta": "2026-12-31"},
            queryset=Internship.objects.all(),
        )
        self.assertIn(self.internado, list(fs.qs))

    def test_rango_fecha_excluye(self):
        fs = InternshipFilter(
            {"fecha_inicio_desde": "2027-01-01"}, queryset=Internship.objects.all()
        )
        self.assertEqual(fs.qs.count(), 0)
