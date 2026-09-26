"""Pruebas de FilterSets del módulo Convenios."""

import datetime

from django.test import TestCase

from apps.convenios.filters import (
    ClinicalFieldAllocationFilter,
    ClinicalFieldRegistrationFilter,
    ConventionFilter,
)
from apps.convenios.models import Convention
from apps.convenios.tests import factories as f


class ConventionFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("cf_admin", is_superuser=True)
        cls.marco = f.crear_convenio(
            creado_por=cls.admin, tipo_codigo="MARCO", organo_nombre=f.ORGANO_GORE,
            titulo="Marco F", fecha_fin=datetime.date(2029, 1, 1),
        )
        cls.especifico = f.crear_convenio(
            creado_por=cls.admin, tipo_codigo="ESPECIFICO", titulo="Especifico F",
        )

    def test_filtra_por_tipo_convenio(self):
        # Happy: filtra por el tipo de convenio.
        fs = ConventionFilter({"tipo_convenio": self.marco.tipo_convenio_id},
                              queryset=Convention.objects.all())
        self.assertIn(self.marco, fs.qs)
        self.assertNotIn(self.especifico, fs.qs)

    def test_filtra_por_es_adenda(self):
        # Edge: sin adendas, es_adenda=true devuelve vacío.
        fs = ConventionFilter({"es_adenda": True}, queryset=Convention.objects.all())
        self.assertEqual(fs.qs.count(), 0)

    def test_filtra_por_rango_fecha_fin(self):
        # Happy: rango de fecha_fin acota los resultados.
        fs = ConventionFilter(
            {"fecha_fin_desde": "2028-06-01", "fecha_fin_hasta": "2029-12-31"},
            queryset=Convention.objects.all(),
        )
        self.assertIn(self.marco, fs.qs)
        self.assertNotIn(self.especifico, fs.qs)

    def test_filtro_invalido_ignora(self):
        # Unhappy: un valor de fecha inválido invalida el filterset (no rompe).
        fs = ConventionFilter({"fecha_fin_desde": "no-es-fecha"},
                              queryset=Convention.objects.all())
        self.assertFalse(fs.is_valid())


class ClinicalFieldFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("cff_admin", is_superuser=True)
        cls.reg = f.crear_registro_campo_clinico()
        cls.conv = f.crear_convenio(creado_por=cls.admin)
        cls.asig = f.crear_asignacion_campo_clinico(
            convenio=cls.conv, registro=cls.reg, ipress=cls.reg.ipress,
            carrera=cls.reg.carrera_profesional,
        )

    def test_registro_filtra_por_ipress(self):
        from apps.convenios.models import ClinicalFieldRegistration
        fs = ClinicalFieldRegistrationFilter(
            {"ipress": self.reg.ipress_id}, queryset=ClinicalFieldRegistration.objects.all()
        )
        self.assertIn(self.reg, fs.qs)

    def test_asignacion_filtra_por_convenio_y_universidad(self):
        from apps.convenios.models import ClinicalFieldAllocation
        fs = ClinicalFieldAllocationFilter(
            {"convenio": self.conv.id, "universidad": self.conv.universidad_id},
            queryset=ClinicalFieldAllocation.objects.all(),
        )
        self.assertIn(self.asig, fs.qs)

    def test_asignacion_filtra_por_carrera_inexistente(self):
        # Unhappy: filtra por carrera que no coincide → vacío.
        from apps.convenios.models import ClinicalFieldAllocation
        otra = f.crear_carrera("Carrera Otra Filt")
        fs = ClinicalFieldAllocationFilter(
            {"carrera_profesional": otra.id},
            queryset=ClinicalFieldAllocation.objects.all(),
        )
        self.assertEqual(fs.qs.count(), 0)
