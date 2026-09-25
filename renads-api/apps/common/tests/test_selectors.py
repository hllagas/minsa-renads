"""Pruebas de los selectors transversales de alcance institucional."""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.common import selectors
from apps.common.tests.factories import crear_grupo, crear_usuario
from apps.convenios.models import Conapres, UserEntityProfile


class SelectorsTests(TestCase):
    """``grupos_del_usuario`` / ``perfiles_del_usuario`` / ``entidades_del_usuario`` /
    ``usuario_pertenece_a_entidad``."""

    @classmethod
    def setUpTestData(cls):
        cls.user = crear_usuario(username="sel", grupos=["Universidad"])
        cls.grupo = crear_grupo("Universidad")
        cls.uni = Conapres.objects.create(nombre="Entidad Uno")
        cls.uni2 = Conapres.objects.create(nombre="Entidad Dos")
        cls.ct = ContentType.objects.get_for_model(Conapres)
        # Perfil activo sobre uni; perfil inactivo sobre uni2.
        cls.perfil_activo = UserEntityProfile.objects.create(
            usuario=cls.user, tipo_contenido=cls.ct, id_objeto=str(cls.uni.pk),
            grupo=cls.grupo, activo=True,
        )
        cls.perfil_inactivo = UserEntityProfile.objects.create(
            usuario=cls.user, tipo_contenido=cls.ct, id_objeto=str(cls.uni2.pk),
            grupo=cls.grupo, activo=False,
        )

    def test_grupos_del_usuario(self):
        # Happy: lista los nombres de grupo.
        self.assertIn("Universidad", selectors.grupos_del_usuario(self.user))

    def test_perfiles_solo_activos(self):
        # Happy: perfiles_del_usuario solo devuelve activos.
        perfiles = list(selectors.perfiles_del_usuario(self.user))
        self.assertEqual(len(perfiles), 1)
        self.assertEqual(perfiles[0].pk, self.perfil_activo.pk)

    def test_entidades_del_usuario_castea_a_str(self):
        # Edge: id_objeto se devuelve como str.
        entidades = selectors.entidades_del_usuario(self.user)
        self.assertEqual(entidades, [(self.ct.id, str(self.uni.pk))])

    def test_usuario_pertenece_a_entidad_true(self):
        # Happy: pertenece a la entidad activa.
        self.assertTrue(
            selectors.usuario_pertenece_a_entidad(self.user, self.ct.id, str(self.uni.pk))
        )

    def test_usuario_no_pertenece_a_entidad_inactiva(self):
        # Unhappy: no pertenece a la entidad con perfil inactivo.
        self.assertFalse(
            selectors.usuario_pertenece_a_entidad(self.user, self.ct.id, str(self.uni2.pk))
        )

    def test_pertenencia_normaliza_int_a_str(self):
        # Edge: acepta id numérico y lo normaliza a str para comparar.
        self.assertTrue(
            selectors.usuario_pertenece_a_entidad(self.user, self.ct.id, self.uni.pk)
        )
