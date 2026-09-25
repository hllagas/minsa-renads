"""Pruebas de selectors del módulo Internados (alcance institucional y lecturas)."""

from django.test import TestCase

from apps.internados import selectors
from apps.internados.tests import factories as f


class EstudiantesVisiblesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("sel_admin", is_superuser=True)
        cls.uni_a = f.crear_universidad("UA", "A")
        cls.uni_b = f.crear_universidad("UB", "B")
        cls.est_a = f.crear_estudiante(creado_por=cls.admin, universidad=cls.uni_a,
                                       numero_documento="10000001")
        cls.est_b = f.crear_estudiante(creado_por=cls.admin, universidad=cls.uni_b,
                                       numero_documento="10000002")

    def test_superusuario_ve_todos(self):
        self.assertEqual(selectors.estudiantes_visibles(self.admin).count(), 2)

    def test_usuario_universidad_ve_los_suyos(self):
        user = f.crear_usuario("sel_uni")
        f.dar_ambito(user, self.uni_a, "Universidad")
        qs = selectors.estudiantes_visibles(user)
        self.assertEqual(list(qs), [self.est_a])

    def test_interno_ve_solo_su_estudiante(self):
        user = f.crear_usuario("sel_interno")
        f.dar_ambito(user, self.est_b, "Interno")
        qs = selectors.estudiantes_visibles(user)
        self.assertEqual(list(qs), [self.est_b])

    def test_sin_perfil_ninguno(self):
        user = f.crear_usuario("sel_nada")
        self.assertEqual(selectors.estudiantes_visibles(user).count(), 0)


class InternadosVisiblesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = f.crear_usuario("iv_admin", is_superuser=True)
        cls.uni = f.crear_universidad("UIV", "IV")
        cls.internado = f.crear_internado(
            creado_por=cls.admin,
            estudiante=f.crear_estudiante(creado_por=cls.admin, universidad=cls.uni,
                                          numero_documento="20000001"),
        )

    def test_superusuario_ve_todos(self):
        self.assertEqual(selectors.internados_visibles(self.admin).count(), 1)

    def test_sin_perfil_ninguno(self):
        user = f.crear_usuario("iv_nada")
        self.assertEqual(selectors.internados_visibles(user).count(), 0)

    def test_universidad_ve_por_estudiante(self):
        user = f.crear_usuario("iv_uni")
        f.dar_ambito(user, self.uni, "Universidad")
        self.assertIn(self.internado, list(selectors.internados_visibles(user)))

    def test_sede_ve_por_ipress(self):
        user = f.crear_usuario("iv_sede")
        f.dar_ambito(user, self.internado.ipress, "CONAPRES")
        self.assertIn(self.internado, list(selectors.internados_visibles(user)))

    def test_interno_ve_por_estudiante(self):
        user = f.crear_usuario("iv_int")
        f.dar_ambito(user, self.internado.estudiante, "Interno")
        self.assertIn(self.internado, list(selectors.internados_visibles(user)))


class OtrosSelectorsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = f.crear_usuario("otros_sel")
        cls.internado = f.crear_internado(creado_por=cls.user)

    def test_rotaciones_count(self):
        self.assertEqual(selectors.rotaciones_count(self.internado), 0)

    def test_historial_internado_ordenado(self):
        # crear_internado directo por ORM no genera historial; queda vacío.
        self.assertEqual(selectors.historial_internado(self.internado).count(), 0)

    def test_convenios_del_tutor(self):
        from apps.internados.models import TutorConvenio
        convenio = f.crear_convenio(creado_por=self.user)
        ipress = f.crear_ipress(codigo="30000001")
        tutor = f.crear_tutor(universidades=[convenio.universidad])
        TutorConvenio.objects.create(tutor=tutor, convenio=convenio, ipress=ipress)
        self.assertEqual(selectors.convenios_del_tutor(tutor).count(), 1)
